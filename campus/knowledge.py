
"""从本地指南读取、验证材料规则并构建 BM25 索引。"""
import hashlib
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from rank_bm25 import BM25Okapi

GUIDES = Path(__file__).resolve().parents[1] / "guides"
SAFE_ID = r"^[a-z][a-z0-9-]*$"
CONDITION_VALUES = {"补办原因": {"遗失", "损坏"}}


SECTION_TERMS = {
    "办理流程": r"流程|怎么办|怎么补|怎么申请|如何办理|如何申请|怎么报修|如何报修|办理步骤|处理步骤|(?:查|看)(?:一下)?(?:申请|审核|办理|处理)?进度|(?:查|看)(?:一下)?(?:申请|审核|办理|处理)结果|怎么(?:取消|改期|补件)",
    "办理地点": r"去哪|在哪儿?办|办理地点|哪个窗口|到哪[儿里]?办|在哪[儿里]?找(?:到)?(?:窗口|服务点)",
    "申请入口": r"入口|在哪儿?申请|在哪儿?报修|哪里提交|哪[儿里]下载|哪里申请|在哪[儿里]?查|哪[儿里]查|哪里看|哪里能查",
    "领取地点": r"领取|在哪儿?取|哪里取|怎么取|哪里拿|在哪儿?下载电子",
}

DETAIL_TERMS = {
    "开放时间": r"周末|周六|周日|几点|开放时间|营业时间|上班时间|关门|开门|时刻表",
    "办理费用": r"收费|多少钱|怎么计费|费用|价格|应缴金额|学费.{0,4}多少|多少.{0,3}学费",
    "办理时限": r"多久|几天|时限",
}


def requested_sections(query: str) -> set[str]:
    return {section for section, pattern in SECTION_TERMS.items() if re.search(pattern, query)}


def requested_details(query: str) -> set[str]:
    return {section for section, pattern in DETAIL_TERMS.items() if re.search(pattern, query)}


def normalize(value: str) -> str:
    return re.sub(r"[\s，。！？、；：,.!?]+", "", unicodedata.normalize("NFKC", value)).casefold()


class Material(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=SAFE_ID)
    name: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    when: dict[str, str] = Field(default_factory=dict)


class Metadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=SAFE_ID)
    name: str = Field(min_length=1)
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    simulated: bool
    aliases: list[str]
    conditions: dict[str, list[str]]
    materials: list[Material]

    @model_validator(mode="after")
    def validate_rules(self):
        if not self.simulated:
            raise ValueError("指南必须声明模拟资料")
        for name, values in self.conditions.items():
            if not values or set(values) - CONDITION_VALUES.get(name, set()):
                raise ValueError(f"conditions.{name} 存在非法取值")
        ids = set()
        aliases = set()
        for item in self.materials:
            keys = {normalize(name) for name in [item.name, *item.aliases]}
            if item.id in ids or "" in keys or keys & aliases:
                raise ValueError(f"materials.{item.id} 的 ID 或材料别名冲突")
            ids.add(item.id)
            aliases.update(keys)
            for name, value in item.when.items():
                if value not in self.conditions.get(name, []):
                    raise ValueError(f"materials.{item.id}.when.{name} 存在非法取值")
        return self


@dataclass(frozen=True)
class Passage:
    guide_id: str
    guide_name: str
    version: str
    section: str
    ref: str
    source_sha256: str
    text: str


def failure(status: str, **fields) -> dict:
    return {"status": status, "evidence": [], **fields}


class Knowledge:
    def __init__(self, directory: Path = GUIDES):
        self.directory = directory
        self.rebuild()

    def _load(self, guide_id: str):
        path = self.paths.get(guide_id)
        if path is None:
            return failure("unknown_guide")
        try:
            raw = path.read_bytes()
        except OSError:
            return failure("unavailable", guide_id=guide_id)
        try:
            opening, front, body = raw.decode("utf-8-sig").replace("\r\n", "\n").split("---\n", 2)
            if opening.strip() or "模拟资料" not in body:
                raise ValueError("指南格式或模拟资料标记错误")
            meta = Metadata.model_validate(yaml.safe_load(front))
            if meta.id != guide_id or guide_id in self.duplicates:
                raise ValueError("事项 ID 与文件名不符或存在重复")
            parts = re.split(r"^## +(.+)$", body, flags=re.M)
            headings = parts[1::2]
            if len(set(headings)) != len(headings) or "所需材料" in headings:
                raise ValueError("重复章节或手写材料章节")
            sections = dict(zip(headings, (part.strip() for part in parts[2::2])))
            lines = []
            for item in meta.materials:
                conditions = "、".join(f"{name}为{value}" for name, value in item.when.items())
                lines.append(f"- {item.name}" + (f"（{conditions}时提交）" if conditions else "（必交）"))
            sections["所需材料"] = "\n".join(lines) or "指南没有列出需提交的材料。"
            return meta, parts[0].strip(), sections, hashlib.sha256(raw).hexdigest()
        except (ValidationError, UnicodeError, ValueError, yaml.YAMLError) as exc:
            detail = exc.errors()[0]["msg"] if isinstance(exc, ValidationError) else str(exc)
            return failure("rule_error", guide_id=guide_id, detail=detail)

    def rebuild(self):
        self.paths = {path.stem: path for path in sorted(self.directory.glob("*.md"))}
        self.catalog = {}
        self.errors = {}
        self.duplicates = set()
        declared = set()
        for path in self.paths.values():
            try:
                metadata = yaml.safe_load(path.read_text(encoding="utf-8-sig").split("---\n", 2)[1])
                name = metadata.get("id") if isinstance(metadata, dict) else None
                if isinstance(name, str):
                    if name in declared:
                        self.duplicates.add(name)
                    declared.add(name)
            except (OSError, UnicodeError, IndexError, yaml.YAMLError):
                continue
        for guide_id in self.paths:
            result = self._load(guide_id)
            if isinstance(result, dict):
                self.errors[guide_id] = result["status"]
                continue
            meta, _, _, _ = result
            self.catalog[guide_id] = meta
        alias_groups = {}
        for meta in self.catalog.values():
            for alias in {meta.name, *meta.aliases}:
                alias_groups.setdefault(normalize(alias), set()).add(meta.id)
        self.aliases = alias_groups
        self.canonical_aliases = [
            (alias, next(iter(ids))) for alias, ids in
            sorted(alias_groups.items(), key=lambda item: len(item[0]), reverse=True)
            if alias and len(ids) == 1
        ]
        self.passages = [p for guide_id in self.catalog for p in self.read(guide_id)["evidence"]]
        self.corpus = [self.tokens(f'{p["guide_name"]} {p["section"]} {p["text"]}') for p in self.passages]
        self.index = BM25Okapi(self.corpus) if self.corpus else None

    def tokens(self, value: str) -> list[str]:
        text = unicodedata.normalize("NFKC", value).casefold()
        for alias, guide_id in self.canonical_aliases:
            text = text.replace(alias, guide_id)
        tokens = []
        for word in re.findall(r"[\u3400-\u9fff]+|[a-z0-9-]+", text):
            if re.fullmatch(r"[a-z0-9-]+", word) or len(word) == 1:
                tokens.append(word)
            else:
                tokens.extend(word[i:i + 2] for i in range(len(word) - 1))
        return tokens

    def search(self, query: str) -> dict:
        text = normalize(query)
        spans = sorted(
            (match.start(), -match.end(), alias)
            for alias in self.aliases if alias and alias in text
            for match in re.finditer(re.escape(alias), text)
        )
        matches = set()
        furthest_end = 0
        for _, negative_end, alias in spans:
            end = -negative_end
            if end > furthest_end:
                matches.add(alias)
                furthest_end = end
        specific = {alias for alias in matches if len(self.aliases[alias]) == 1}
        chosen = specific or matches
        ids = set().union(*(self.aliases[alias] for alias in chosen))
        return {
            "status": "ok" if ids else "no_match",
            "candidates": [{"guide_id": gid, "name": self.catalog[gid].name} for gid in sorted(ids)],
            "evidence": [],
        }

    def read(self, guide_id: str) -> dict:
        result = self._load(guide_id)
        if isinstance(result, dict):
            return result
        meta, intro, sections, digest = result
        evidence = [
            asdict(Passage(meta.id, meta.name, meta.version, title, f"{meta.id}.{i}.{digest[:12]}", digest, body))
            for i, (title, body) in enumerate(sections.items(), 1)
        ]
        return {
            "status": "ok",
            "body": intro + "\n\n" + "\n\n".join(f"## {title}\n{body}" for title, body in sections.items()),
            "conditions": meta.conditions,
            "evidence": evidence,
        }

    def check(self, guide_id: str, provided_items: list[str], conditions: dict[str, str] | None = None) -> dict:
        result = self._load(guide_id)
        if isinstance(result, dict):
            return result
        meta, _, _, _ = result
        conditions = conditions or {}
        if any(value not in meta.conditions.get(name, []) for name, value in conditions.items()):
            return failure("invalid_conditions", allowed=meta.conditions)
        provided = {normalize(name) for name in provided_items}
        buckets = {"complete": [], "missing": [], "pending": []}
        for item in meta.materials:
            if any(name in conditions and conditions[name] != value for name, value in item.when.items()):
                continue
            if any(name not in conditions for name in item.when):
                buckets["pending"].append({"material": item.name, "when": item.when})
                continue
            names = {normalize(name) for name in [item.name, *item.aliases]}
            buckets["complete" if provided & names else "missing"].append(item.name)
        guide = self.read(guide_id)
        if guide["status"] != "ok":
            return guide
        return {"status": "ok", **buckets, "evidence": [guide["evidence"][-1]]}

    def retrieve(self, query: str, guide_id: str | None = None) -> dict:
        candidates = [guide_id] if guide_id else [row["guide_id"] for row in self.search(query)["candidates"]]
        if len(candidates) > 1:
            return failure("ambiguous", candidates=candidates)
        if not candidates:
            return failure("no_match")
        guide_id = candidates[0]
        current = self.read(guide_id)
        if current["status"] != "ok":
            return current
        if not self.index:
            return failure("index_stale", guide_id=guide_id)
        preferred = requested_sections(query) | requested_details(query)
        tokens = self.tokens(query) + self.tokens(" ".join(sorted(preferred)))
        specific = set(tokens) - {guide_id, "补办", "申请", "请问", "怎么", "哪里", "在哪", "哪里", "需要", "什么"}
        scores = self.index.get_scores(tokens)
        indexed = [i for i, p in enumerate(self.passages) if p["guide_id"] == guide_id]
        live_hash = current["evidence"][0]["source_sha256"]
        if not indexed or any(self.passages[i]["source_sha256"] != live_hash for i in indexed):
            return failure("index_stale", guide_id=guide_id)
        matched = [i for i in indexed if specific.intersection(self.corpus[i])]
        if not matched:
            return failure("no_match", guide_id=guide_id)
        ranked = sorted(
            matched,
            key=lambda i: (self.passages[i]["section"] not in preferred, -float(scores[i]), i),
        )[:3]
        return {"status": "ok", "evidence": [self.passages[i] for i in ranked]}
