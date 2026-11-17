
"""运行冻结评测。真实模型输出保留给人工核对业务断言。"""
import argparse
import hashlib
import importlib.metadata
import json
import math
import shutil
import statistics
import sys
import tempfile
from pathlib import Path

import httpx

from campus.knowledge import GUIDES, Knowledge
from campus.service import Offline, Session

HERE = Path(__file__).resolve().parent
CASES = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))
FROZEN = HERE / "freeze.json"
PII = ("fixture@example.invalid", "123456789012")


def fingerprint():
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [HERE / "cases.json", *sorted(GUIDES.glob("*.md"))]}


def rubric(turn, expected, mode):
    # Frozen assertions are regression checks. Semantic citation grading is separate.
    output = all(word in turn["answer"] for word in expected["contains"])
    observed_sections = {e["section"] for e in turn["citations"]
                         if e["guide_id"] == expected.get("guide")}
    wanted = set(expected["sections"])
    references = wanted <= observed_sections and all(
        e["guide_id"] == expected.get("guide") for e in turn["citations"]
    ) if wanted else not turn["citations"]
    calls = turn["tools"]
    if "material" in expected:
        material = expected["material"]
        eligible = [c for c in calls if c["tool"] == "check_materials" and
                    c["params"]["guide_id"] == expected["guide"]]
        tool = any(
            set(c["params"]["provided_items"]) == set(material["provided_items"])
            and (c["params"]["conditions"] or {}) == material["conditions"]
            and c["result"].get("missing") == material["missing"]
            and [r["material"] for r in c["result"].get("pending", [])] == material["pending"]
            for c in eligible
        )
    elif "status" in expected:
        tool = any(c["result"]["status"] == expected["status"] and
                   c["params"].get("guide_id") == expected["guide"] for c in calls)
    elif expected.get("guide"):
        paths = [c["tool"] for c in calls if c["params"].get("guide_id") == expected["guide"]]
        tool = "read_guide" in paths if mode == "full" or not wanted else (
            "retrieve_guide_passages" in paths or "read_guide" in paths
        )
    else:
        tool = any(c["tool"] == "search_guides" and
                   len(c["result"]["candidates"]) in (0, 2) for c in calls)
    return {"answer_assertions": output, "reference_location": references, "tool": tool,
            "passed": output and references and tool and turn["error"] is None}


class Fixture:
    """OpenAI 兼容 HTTP 测试桩。固定工具调用及输出，验证真实客户端与中间件。"""

    def __init__(self):
        self.timeout = False
        self.status = None
        self.requests = []

    def __call__(self, request):
        body = json.loads(request.read())
        messages = body["messages"]
        role = "main" if body.get("tools") else "summary"
        serialized = json.dumps(messages, ensure_ascii=False)
        self.requests.append({"role": role, "contains_fixture_email": PII[0] in serialized,
                              "contains_fixture_student_number": PII[1] in serialized,
                              "contains_redaction": "REDACTED" in serialized,
                              "message_count": len(messages)})
        if self.timeout:
            raise httpx.ReadTimeout("injected timeout", request=request)
        if self.status:
            return httpx.Response(self.status, json={"error": {"message": "injected HTTP status"}})
        message = {"role": "assistant", "content": ""}
        finish = "stop"
        last = messages[-1]
        if role == "summary":
            message["content"] = "测试桩摘要。"
        elif last["role"] == "tool":
            result = json.loads(last["content"])
            rows = result["evidence"]
            message["content"] = json.dumps({
                "status": "answer", "answer": rows[0]["text"], "refs": [rows[0]["ref"]]
            }, ensure_ascii=False)
        else:
            material = "还差什么" in last["content"]
            name = "check_materials" if material else "read_guide"
            args = {"guide_id": "student-id"}
            if material:
                args["provided_items"] = ["申请表", "证件照"]
            message["tool_calls"] = [{"id": f"tool_{len(self.requests)}", "type": "function",
                                      "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)}}]
            finish = "tool_calls"
        return httpx.Response(200, json={
            "id": f"fixture_{len(self.requests)}", "object": "chat.completion", "created": 0,
            "model": "fixture-http", "choices": [{"index": 0, "message": message, "finish_reason": finish}],
        })


def fixture_run(case, summarize=True):
    from campus.live import Live

    fixture = Fixture()
    knowledge = Knowledge()
    if case["id"] == "D1":
        original_read = knowledge.read

        def read_with_fixture(guide_id):
            result = original_read(guide_id)
            if result["status"] == "ok":
                result["body"] += f"\n模拟测试邮箱 {PII[0]}，学号：{PII[1]}"
            return result

        knowledge.read = read_with_fixture
    session = Session()
    live = Live(knowledge, "full", api_key="fixture-only", transport=httpx.MockTransport(fixture),
                summarize=summarize)
    records = []
    for expected in case["turns"]:
        fixture.timeout = expected.get("fault") == "timeout"
        records.append(live.ask(expected["input"], session).record())
    live.client.close()
    if case["id"] == "C3":
        failed = records[1]
        checks = {
            "two_attempts": [request["attempt"] for request in failed["requests"]] == [1, 2],
            "error": failed["error"] in {"APITimeoutError", "OpenAITimeoutError"} and "超时" in failed["answer"],
            "same_thread": len({row["thread_id"] for row in records}) == 1,
            "recovered": "缺少：遗失说明" in records[-1]["answer"],
        }
    elif case["id"] == "D1":
        serialized = json.dumps(records, ensure_ascii=False)
        checks = {
            "both_roles": {r["role"] for r in fixture.requests} == {"main", "summary"},
            "requests_redacted": not any(r["contains_fixture_email"] or r["contains_fixture_student_number"]
                                         for r in fixture.requests),
            "redaction_seen_in_both_roles": {r["role"] for r in fixture.requests if r["contains_redaction"]}
            == {"main", "summary"},
            "log_redacted": all(value not in serialized for value in PII) and "REDACTED" in serialized,
        }
    else:
        summary_calls = sum(r["role"] == "summary" for r in fixture.requests)
        checks = {
            "summary_calls_expected": summary_calls > 0 if summarize else summary_calls == 0,
            "context_preserved": "缺少：遗失说明" in records[-1]["answer"]
            and session.guide_id == "student-id" and session.conditions == {"补办原因": "遗失"},
        }
    return {"turns": records, "checks": checks, "observed_http": fixture.requests,
            "passed": all(checks.values()), "summarize": summarize}


def local_case(case, mode, engine, kb):
    session = Session()
    checks = []
    path = kb.directory / "student-id.md"
    before = path.read_bytes()
    fault = case.get("fault")
    if fault == "remove_guide":
        path.unlink()
    if fault == "invalid_rule":
        path.write_bytes(before.replace('"补办原因": "遗失"'.encode(), '"补办原因": "无效"'.encode()))
    try:
        turns = []
        for expected in case["turns"]:
            record = engine.ask(expected["input"], session).record()
            record["automated_rubric"] = rubric(record, expected, mode)
            turns.append(record)
        if fault in ("remove_guide", "invalid_rule"):
            path.write_bytes(before)
            kb.rebuild()
            retry = engine.ask(case["turns"][0]["input"], session).record()
            checks.append({"restored": bool(retry["citations"]), "turn": retry})
        return {"turns": turns, "retests": checks, "passed":
                all(row["automated_rubric"]["passed"] for row in turns)
                and all(row["restored"] for row in checks)}
    finally:
        if fault in ("remove_guide", "invalid_rule") and (not path.exists() or path.read_bytes() != before):
            path.write_bytes(before)


def retrieval_check(kb):
    rows = []
    for case in CASES:
        if not case.get("retrieval_query"):
            continue
        turn = case["turns"][0]
        result = kb.retrieve(case["retrieval_query"], turn["guide"])
        expected = {row["ref"] for row in kb.read(turn["guide"])["evidence"] if row["section"] in turn["sections"]}
        assert len(expected) == len(turn["sections"])
        found = {row["ref"] for row in result["evidence"]}
        rows.append({"case": case["id"], "query": case["retrieval_query"], "expected": sorted(expected),
                     "retrieved": [{"ref": r["ref"], "section": r["section"]} for r in result["evidence"]],
                     "hits": sorted(found & expected), "misses": sorted(expected - found)})
    return rows


def stats(times):
    times = sorted(times)
    return {"n": len(times), "median_ms": statistics.median(times), "p95_ms": times[math.ceil(len(times) * .95) - 1]
            } if times else {"n": 0}


def summary(runs, retrieval):
    def counts(rows):
        return {"passed": sum(row["passed"] for row in rows), "total": len(rows)}

    def latency(rows):
        return stats([t["elapsed_ms"] for row in rows for t in row["turns"]])

    offline = [row for row in runs if row["environment"] == "offline"]
    live = [row for row in runs if row["environment"] == "deepseek_api"]
    fixture = [row for row in runs if row["environment"] == "fixture_http"]
    hits = sum(len(row["hits"]) for row in retrieval)
    total = sum(len(row["expected"]) for row in retrieval)
    groups = {}
    for mode in ("rag", "full"):
        group = [r for r in offline if r["mode"] == mode]
        e = [r for r in group if r["case"].startswith("E")]
        answered = [r for r in e if r["passed"] and r["case"] not in ("E11", "E12")]
        groups[mode] = {"all": counts(group), "E": counts(e), "E_latency": latency(e),
                        "tool_accurate_runs": sum(all(t["automated_rubric"]["tool"] for t in r["turns"]) for r in group),
                        "E_answered_without_fallback": sum(not r["turns"][0]["fallbacks"] for r in answered),
                        "E_answered_after_fallback": sum(bool(r["turns"][0]["fallbacks"]) for r in answered)}
    return {"offline": groups, "fixture_http": counts(fixture), "live_attempted": len(live),
            "live_semantic_review": "pending" if live else "not_run",
            "retrieval": {"hits": hits, "total": total}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="发送真实请求并记录待人工审查的原始结果")
    parser.add_argument("--case", action="append", help="只运行指定用例，可重复")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    digest = fingerprint()
    if digest != json.loads(FROZEN.read_text(encoding="utf-8")):
        parser.error("指南或评测脚本与冻结哈希不符")
    runs = []
    selected = {case["id"] for case in CASES} if not args.case else set(args.case)
    if selected - {case["id"] for case in CASES}:
        parser.error("存在未知用例 ID")
    versions = {name: importlib.metadata.version(name) for name in
                ("langchain", "langgraph", "langchain-deepseek", "pydantic", "rank-bm25", "PyYAML", "httpx", "openai")}
    with tempfile.TemporaryDirectory(dir=HERE) as temp:
        directory = Path(temp) / "guides"
        shutil.copytree(GUIDES, directory)
        kb = Knowledge(directory)
        retrieval = retrieval_check(kb)
        for mode in ("rag", "full"):
            engine = Offline(kb, mode)
            if args.live:
                from campus.live import Live
                try:
                    engine = Live(kb, mode)
                except ValueError as exc:
                    parser.error(str(exc))
            for case in CASES:
                cid = case["id"]
                if cid not in selected or cid in ("C3", "D1", "D2"):
                    continue
                if mode == "full" and cid != "C2" and not cid.startswith("E"):
                    continue
                for rep in range(1, 4):
                    observed = local_case(case, mode, engine, kb)
                    if args.live:
                        observed["automated_precheck_passed"] = observed.pop("passed")
                        observed["passed"] = None
                    runs.append({"case": cid, "mode": mode, "repeat": rep,
                                 "environment": "deepseek_api" if args.live else "offline", **observed})
            if args.live:
                engine.client.close()
        if args.live and "D2" in selected:
            script = next(case for case in CASES if case["id"] == "D2")
            for enabled in (True, False):
                engine = Live(kb, "rag", summarize=enabled)
                for repeat in range(1, 4):
                    session = Session()
                    turns = [engine.ask(step["input"], session).record() for step in script["turns"]]
                    runs.append({"case": "D2", "mode": "rag" if enabled else "rag_no_summary",
                                 "repeat": repeat, "environment": "deepseek_api", "summarize": enabled,
                                 "passed": None, "turns": turns})
                engine.client.close()
        for case in CASES:
            if case["id"] not in selected.intersection({"C3", "D1", "D2"}):
                continue
            for repeat in range(1, 4):
                for enabled in ([True, False] if case["id"] == "D2" else [True]):
                    result = fixture_run(case, enabled)
                    runs.append({"case": case["id"], "mode": "full", "repeat": repeat,
                                 "environment": "fixture_http", **result})

    result = {"versions": {"python": sys.version.split()[0], **versions}, "fingerprint": digest,
              "summary": summary(runs, retrieval), "retrieval": retrieval, "runs": runs}
    args.out.parent.mkdir(exist_ok=True, parents=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
