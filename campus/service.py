
"""共享业务工具、脱敏记录和本地演示路径。"""
import re
from dataclasses import dataclass, field
from time import perf_counter
from uuid import uuid4

from .knowledge import Knowledge, failure, requested_details, requested_sections

EMAIL = r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"
STUDENT_NUMBER = r"学号[ \t]*[:：]?[ \t]*[0-9]{5,24}(?![0-9])"

STATUS_TEXT = {
    "unknown_guide": "目前没有该事项的模拟指南，无法核实。",
    "no_match": "目前没有该事项的模拟指南或对应条款，无法核实。",
    "unavailable": "该事项的指南文件暂时不可用，无法核实。",
    "rule_error": "该事项的指南或材料规则校验失败，暂时无法核对。",
    "invalid_conditions": "补办条件无法识别，请确认是遗失还是损坏。",
    "ambiguous": "请确认具体事项。",
}


def redact(value):
    if isinstance(value, str):
        return re.sub(STUDENT_NUMBER, "[REDACTED_STUDENT_NUMBER]", re.sub(EMAIL, "[REDACTED_EMAIL]", value))
    if isinstance(value, dict):
        return {redact(key): redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


@dataclass
class Session:
    thread_id: str = field(default_factory=lambda: str(uuid4()))
    guide_id: str | None = None
    conditions: dict = field(default_factory=dict)
    candidates: list = field(default_factory=list)


@dataclass
class Turn:
    text: str
    mode: str
    environment: str
    thread_id: str
    run_id: str = field(default_factory=lambda: str(uuid4()))
    calls: list = field(default_factory=list)
    evidence: dict = field(default_factory=dict)
    citations: list = field(default_factory=list)
    requests: list = field(default_factory=list)
    fallbacks: list = field(default_factory=list)
    started: float = field(default_factory=perf_counter)
    error: str | None = None
    answer: str = ""

    def record(self):
        return redact({
            "run_id": self.run_id, "thread_id": self.thread_id, "environment": self.environment,
            "mode": self.mode, "input": self.text, "answer": self.answer,
            "tools": self.calls, "citations": self.citations, "fallbacks": self.fallbacks,
            "requests": self.requests, "error": self.error,
            "elapsed_ms": round((perf_counter() - self.started) * 1000, 2),
        })


def invoke_tool(knowledge: Knowledge, turn: Turn, name: str, **params):
    routes = {
        "search_guides": knowledge.search,
        "read_guide": knowledge.read,
        "check_materials": knowledge.check,
        "retrieve_guide_passages": knowledge.retrieve,
    }
    result = redact(routes[name](**params))
    turn.evidence.update({row["ref"]: row for row in result.get("evidence", [])})
    turn.calls.append({"tool": name, "params": redact(params), "result": result})
    return result


def cite(turn: Turn, refs: list[str]) -> str:
    lines = []
    for number, ref in enumerate(dict.fromkeys(refs), 1):
        item = turn.evidence[ref]
        turn.citations.append(item)
        lines.append(
            f'[{number}] {item["guide_name"]}｜{item["version"]}｜{item["section"]}'
            f'（guides/{item["guide_id"]}.md）'
        )
    return "\n来源（模拟资料）\n" + "\n".join(f"- {line}" for line in lines) if lines else ""


def material_answer(turn: Turn, result: dict, *, include_citations=True) -> str:
    if result["status"] != "ok":
        return STATUS_TEXT[result["status"]]
    evidence = result["evidence"]
    refs = [row["ref"] for row in evidence]
    if not any(result[bucket] for bucket in ("complete", "missing", "pending")):
        return "模拟指南没有列出需提交的材料。请在办理入口核对当期要求。" + (cite(turn, refs) if include_citations else "")
    pending = []
    for row in result["pending"]:
        rule = "、".join(f"{key}为{value}" for key, value in row["when"].items())
        pending.append(f'{row["material"]}（{rule}时提交）')
    lines = [
        "已齐：" + ("、".join(result["complete"]) or "无"),
        "缺少：" + ("、".join(result["missing"]) or "无"),
        "待确认：" + ("、".join(pending) or "无"),
    ]
    if pending:
        lines.append("请确认补办原因是遗失还是损坏。")
    return "\n".join(lines) + (cite(turn, refs) if include_citations else "")


def material_with_details(knowledge: Knowledge, turn: Turn, result: dict, mode: str) -> str:
    """Render checked materials and every additional requested guide section."""
    desired = requested_sections(turn.text) | requested_details(turn.text)
    if result["status"] != "ok" or not desired:
        return material_answer(turn, result)
    guide_id = result["evidence"][0]["guide_id"]
    refs = [row["ref"] for row in result["evidence"]]
    parts = [material_answer(turn, result, include_citations=False)]
    if mode == "rag":
        details = invoke_tool(knowledge, turn, "retrieve_guide_passages", query=turn.text, guide_id=guide_id)
        if not desired <= {row["section"] for row in details["evidence"]}:
            turn.fallbacks.append("Additional requested sections require the full guide")
            details = invoke_tool(knowledge, turn, "read_guide", guide_id=guide_id)
    else:
        details = invoke_tool(knowledge, turn, "read_guide", guide_id=guide_id)
    if details["status"] != "ok":
        parts.append(STATUS_TEXT[details["status"]])
    else:
        selected = [row for row in details["evidence"] if row["section"] in desired]
        parts.extend(f'{row["section"]}\n{row["text"]}' for row in selected)
        refs.extend(row["ref"] for row in selected)
        missing = desired - {row["section"] for row in selected}
        if missing:
            parts.append("现有模拟指南未提供" + "、".join(sorted(missing)) + "，无法核实。")
    return "\n\n".join(parts) + cite(turn, refs)


def condition_from(text: str):
    text = re.sub(r"遗失说明|丢失说明|(?:没有|并未|没有发生|未|不是)(?:遗失|丢失|损坏|破损)", "", text)
    loss = re.search(r"遗失|丢失|丢了|找不到", text)
    damage = re.search(r"损坏|坏了|破损", text)
    if bool(loss) != bool(damage):
        return {"补办原因": "遗失" if loss else "损坏"}
    return {}


def topic_query(text: str) -> str:
    """Keep items listed for material checking out of topic matching."""
    if re.search(r"还差|还缺|够吗|齐了吗|缺什么", text):
        return re.split(r"我(?:已经|已)?有|我(?:已经|已)?准备了|我(?:只)?带了|已有|只带", text, maxsplit=1)[0]
    return text


class Offline:
    """关键词与规则驱动的课程演示，直接运行同一组业务工具。"""

    def __init__(self, knowledge: Knowledge, mode: str):
        self.knowledge, self.mode = knowledge, mode

    def ask(self, text: str, session: Session) -> Turn:
        turn = Turn(redact(text), self.mode, "offline", session.thread_id)
        turn.answer = self._answer(turn, session)
        return turn

    def _answer(self, turn: Turn, session: Session) -> str:
        text = turn.text
        call = lambda name, **params: invoke_tool(self.knowledge, turn, name, **params)
        found = call("search_guides", query=topic_query(text))["candidates"]
        if len(found) > 1:
            session.candidates = found
            return "请确认要办理哪一项：" + "、".join(row["name"] for row in found) + "？"
        if found:
            gid = found[0]["guide_id"]
            if gid != session.guide_id:
                session.guide_id, session.conditions = gid, {}
            session.candidates = []
        elif session.candidates:
            return "请确认要办理哪一项：" + "、".join(row["name"] for row in session.candidates) + "？"
        elif not session.guide_id or re.search(r"护照|签证|驾驶证", text):
            return STATUS_TEXT["no_match"]

        gid = session.guide_id
        meta = self.knowledge.catalog[gid]
        if meta.conditions:
            session.conditions.update(condition_from(text))
        if re.search(r"材料|需要准备什么|要带什么|已有|我有|我带|只带|还差|还缺|齐了", text):
            provided = []
            submitted = re.split(r"还差|还缺|够吗|齐了吗|需要", text, maxsplit=1)[0]
            if re.search(r"已有|我有|我带|只带|准备了|带了|还差|还缺", text):
                # Match the longest alias once, then use the final mention and its local context.
                for material in meta.materials:
                    aliases = sorted({material.name, *material.aliases}, key=len, reverse=True)
                    mentions = list(re.finditer("|".join(re.escape(alias) for alias in aliases), submitted))
                    if not mentions:
                        continue
                    mention = mentions[-1]
                    prefix = re.split(r"[，。；！？,;!?]|但是|不过|但", submitted[:mention.start()])[-1]
                    signals = re.findall(r"没有带|没有准备|没有|没带|没准备|尚未准备|未准备|缺少|还缺|已有|带了|准备了|有", prefix)
                    negative_prefix = bool(signals) and signals[-1] not in {"已有", "带了", "准备了", "有"}
                    negative_suffix = re.match(
                        r"\s*(?:都|也|还)?(?:没有(?:带|准备)?|没带|没准备|未带|未准备|缺少)"
                        r"(?=$|[，。；！？,;!?、]|但是|不过|但|而|和|也)",
                        submitted[mention.end():],
                    )
                    if not negative_prefix and not negative_suffix:
                        provided.append(mention.group())
            result = call("check_materials", guide_id=gid,
                          provided_items=provided, conditions=session.conditions.copy())
            return material_with_details(self.knowledge, turn, result, self.mode)

        desired = requested_sections(text) | requested_details(text)
        if found and not desired:
            desired = {"办理流程"}
        if self.mode == "rag":
            result = call("retrieve_guide_passages", query=text, guide_id=gid)
            if result["status"] in ("unavailable", "rule_error", "unknown_guide"):
                return STATUS_TEXT[result["status"]]
            if not desired or not desired <= {row["section"] for row in result["evidence"]}:
                turn.fallbacks.append("片段未覆盖全部问题" if result["status"] == "ok" else result["status"])
                result = call("read_guide", guide_id=gid)
        else:
            result = call("read_guide", guide_id=gid)
        if result["status"] != "ok":
            return STATUS_TEXT[result["status"]]
        selected = [row for row in result["evidence"] if row["section"] in desired]
        absent = desired - {row["section"] for row in selected}
        parts = [f'{row["section"]} [{number}]\n{row["text"]}'
                 for number, row in enumerate(selected, 1)]
        missing = sorted(absent)
        if missing:
            parts.append("现有模拟指南未提供" + "、".join(missing) + "，无法核实。")
        if not parts:
            return "当前模拟指南无法核实你问的内容。请说明要查的事项、办理步骤、入口或材料。"
        return "\n\n".join(parts) + cite(turn, [row["ref"] for row in selected])
