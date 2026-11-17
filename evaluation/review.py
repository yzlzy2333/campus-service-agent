
"""生成真实 API 人工评分模板，或从已填评分汇总实验指标。"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

from .run import stats


def key(run):
    return f'{run["case"]}/{run["mode"]}/{run["repeat"]}'


def aggregate(runs, labels):
    groups = defaultdict(list)
    for run in runs:
        groups[run["mode"]].append(run)
    result = {}
    for mode, group in groups.items():
        reviewed = []
        for run in group:
            label = labels.get(key(run))
            if not label or label.get("task") is None or label.get("tool") is None:
                continue
            if not isinstance(label["task"], bool) or not isinstance(label["tool"], bool):
                raise ValueError(f"{key(run)} 的 task 和 tool 必须为布尔值")
            good, total = label["supported_claims"], label["claims_needing_citation"]
            if type(good) is not int or type(total) is not int or not 0 <= good <= total:
                raise ValueError(f"{key(run)} 的引用断言计数无效")
            reviewed.append((run, label))
        token_by_run = {}
        for run in group:
            requests = [q for t in run["turns"] for q in t["requests"] if q.get("http_status") == 200]
            token_by_run[key(run)] = {
                f"{direction}_tokens": (
                    sum(q[f"{direction}_tokens"] for q in requests)
                    if requests and all(q.get(f"{direction}_tokens") is not None for q in requests)
                    else "未返回"
                ) for direction in ("input", "output")
            }
        e_answered = [(r, l) for r, l in reviewed if r["case"].startswith("E")
                      and r["case"] not in ("E11", "E12") and l["task"]]
        result[mode] = {
            "attempted": len(group),
            "reviewed": len(reviewed),
            "task_success": [sum(l["task"] for _, l in reviewed), len(reviewed)],
            "tool_accuracy": [sum(l["tool"] for _, l in reviewed), len(reviewed)],
            "citation_accuracy": [sum(l["supported_claims"] for _, l in reviewed),
                                  sum(l["claims_needing_citation"] for _, l in reviewed)],
            "E_passed_direct_rag": sum(
                mode == "rag" and not any(t["fallbacks"] for t in r["turns"]) for r, _ in e_answered
            ),
            "E_passed_after_rag_fallback": sum(
                mode == "rag" and any(t["fallbacks"] for t in r["turns"]) for r, _ in e_answered
            ),
            "per_turn_latency": stats([t["elapsed_ms"] for r in group for t in r["turns"]]),
            "usage_by_run": token_by_run,
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("observed", type=Path)
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--template", action="store_true")
    args = parser.parse_args()
    observed = json.loads(args.observed.read_text(encoding="utf-8"))
    runs = [r for r in observed["runs"] if r["environment"] == "deepseek_api"]
    if not runs:
        parser.error("该文件没有真实 API 运行记录")
    if args.template:
        if args.labels.exists():
            parser.error("评分文件已存在，请选择其他路径")
        template = {key(run): {"task": None, "tool": None, "supported_claims": None,
                               "claims_needing_citation": None, "note": ""} for run in runs}
        args.labels.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        labels = json.loads(args.labels.read_text(encoding="utf-8"))
        print(json.dumps(aggregate(runs, labels), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
