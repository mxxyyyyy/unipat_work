"""
schema.py — 数据契约 (single source of truth for data shapes)

所有 stage 的产物与所有 LLM 结构化输出都遵循这里的定义。
领域特定 prompt 由 fan-out 生成, 但它们的**输出格式**必须匹配这里的 *_SCHEMA,
以保证 query_gen / qc / rubric_gen / grader 跨领域一致、可被下游直接消费。

对齐 GDPval schema (task_id/sector→domain/occupation/prompt/reference_files/
deliverable_files/rubric_pretty/rubric_json) + 我们的超集字段。
详见 ../README.md 六、输出格式
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional
import hashlib
import json


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------
def stable_id(*parts: str) -> str:
    """由内容派生稳定 id (可复现, 不依赖时间/随机)。"""
    h = hashlib.sha1("".join(parts).encode("utf-8")).hexdigest()
    return h[:16]


def to_jsonl(objs) -> str:
    return "\n".join(json.dumps(asdict(o), ensure_ascii=False) for o in objs)


# ---------------------------------------------------------------------------
# S1 切分
# ---------------------------------------------------------------------------
@dataclass
class Segment:
    text: str
    label: str                 # data | analysis | conclusion
    page: Optional[int] = None
    section: Optional[str] = None


@dataclass
class CleanedDoc:
    doc_id: str
    domain: str
    source: str                # worldbank / fed / ...
    title: str
    reference_text: str        # 只留 data 层 (solver 输入)
    reference_tables: list = field(default_factory=list)  # 抽出的数据表 (csv 路径或内联)
    answer_key_text: str = ""  # analysis + conclusion (隐藏锚点)
    has_tables: bool = False
    provenance: dict = field(default_factory=dict)  # {pdf, pages, sections}


# ---------------------------------------------------------------------------
# S2 近邻成组 (neighbor_grouping, 非 cluster)
# ---------------------------------------------------------------------------
@dataclass
class Bundle:
    bundle_id: str
    domain: str
    seed: str                  # 种子 doc_id
    files: list = field(default_factory=list)        # doc_id[], <= cap(3)
    supported_deliverables: list = field(default_factory=list)  # 门控后的交付物类型


# ---------------------------------------------------------------------------
# S3 query
# ---------------------------------------------------------------------------
@dataclass
class Query:
    query_id: str
    bundle_id: str
    domain: str
    occupation: str            # occupation id (见 domains.yaml)
    deliverable_type: str      # prose_md | prose_docx | prose_pdf | data_xlsx
    prompt: str                # GDPval 式完整 request (含多子任务/格式要求)
    subtasks: list = field(default_factory=list)     # 拆出的子任务列表 (便于 rubric/grader)
    format_spec: str = ""      # 交付物格式硬要求 (文件名/sheet/结构)
    reference_files: list = field(default_factory=list)  # 相对路径 (指向 cleaned/tables)


# ---------------------------------------------------------------------------
# S4 QC
# ---------------------------------------------------------------------------
QC_GATES = ["solvable", "zero_leakage", "on_domain", "has_deliverable",
            "non_trivial", "unambiguous", "representative", "coherent"]


@dataclass
class QCResult:
    query_id: str
    gates: dict = field(default_factory=dict)   # {gate_id: 0|1}
    passed: bool = False                         # 全 1 才 True
    reasons: dict = field(default_factory=dict)  # {gate_id: 简短理由}
    grader_model: str = ""                       # 打这份 QC 的模型

    def finalize(self) -> "QCResult":
        self.passed = all(int(self.gates.get(g, 0)) == 1 for g in QC_GATES)
        return self


# ---------------------------------------------------------------------------
# S5 rubric
# ---------------------------------------------------------------------------
@dataclass
class RubricItem:
    rubric_item_id: str
    score: int                 # 权重 (+N), GDPval 累加式
    criterion: str
    kind: str                  # objective | judgment | gdpval_dim
    gdpval_dim: Optional[str] = None   # accuracy | instruction_following | formatting_aesthetics | structure_style_relevance
    anchor_ref: Optional[str] = None   # judgment 项: 指向 answer_key 的支撑片段
    required: bool = False             # 是否为"必须满足"项 (不满足则整体大扣)


@dataclass
class Rubric:
    query_id: str
    items: list = field(default_factory=list)   # RubricItem[]
    max_score: int = 0

    def render_pretty(self) -> str:
        lines = []
        for it in self.items:
            it = it if isinstance(it, dict) else asdict(it)
            lines.append(f"[+{it['score']}] {it['criterion']}")
        return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# S7/S8 交付物与打分
# ---------------------------------------------------------------------------
@dataclass
class Deliverable:
    deliverable_id: str
    query_id: str
    generator: str             # glm | deepseek
    rollout_idx: int
    deliverable_type: str
    path: str                  # 交付物文件路径
    agent_trace_path: Optional[str] = None


@dataclass
class Score:
    deliverable_id: str
    query_id: str
    grader_model: str          # 跨家族
    total: float
    max_score: int
    per_item: dict = field(default_factory=dict)   # {rubric_item_id: got_score}
    dim_scores: dict = field(default_factory=dict)  # {gdpval_dim: 0..1}
    arbitrated: bool = False
    is_best: bool = False


# ---------------------------------------------------------------------------
# 最终落盘: GDPval schema 超集
# ---------------------------------------------------------------------------
@dataclass
class Item:
    task_id: str
    domain: str
    occupation: str
    deliverable_type: str
    prompt: str
    reference_files: list = field(default_factory=list)
    reference_file_urls: list = field(default_factory=list)
    deliverable_files: list = field(default_factory=list)   # 6 份 rollout
    rubric_pretty: str = ""
    rubric_json: list = field(default_factory=list)          # RubricItem[] as dict
    # ---- 超集字段 ----
    answer_key_refs: list = field(default_factory=list)   # 指向所有 reference doc 的 answer_key (隐藏)
    provenance: dict = field(default_factory=dict)
    qc: dict = field(default_factory=dict)                   # QCResult
    scores: list = field(default_factory=list)               # Score[]
    best_idx: Optional[int] = None


# ===========================================================================
# LLM 结构化输出 JSON Schema (供 providers 强制结构化 / 校验)
# 领域特定 prompt 只改"内容", 不改这些"契约"。
# ===========================================================================

PARTITION_SCHEMA = {
    "type": "object",
    "properties": {
        "segments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text_id": {"type": "string"},
                    "label": {"enum": ["data", "analysis", "conclusion"]},
                    "reason": {"type": "string"},
                },
                "required": ["text_id", "label"],
            },
        }
    },
    "required": ["segments"],
}

QUERY_GEN_SCHEMA = {
    "type": "object",
    "properties": {
        "occupation": {"type": "string"},
        "deliverable_type": {"enum": ["prose_md", "prose_docx", "prose_pdf", "data_xlsx"]},
        "prompt": {"type": "string", "description": "完整 GDPval 式 request, 含真实职业情境 + 多子任务 + 格式要求"},
        "subtasks": {"type": "array", "items": {"type": "string"}},
        "format_spec": {"type": "string"},
    },
    "required": ["occupation", "deliverable_type", "prompt", "subtasks", "format_spec"],
}

QC_SCHEMA = {
    "type": "object",
    "properties": {
        "gates": {
            "type": "object",
            "properties": {g: {"enum": [0, 1]} for g in QC_GATES},
            "required": QC_GATES,
        },
        "reasons": {"type": "object"},
    },
    "required": ["gates"],
}

RUBRIC_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "score": {"type": "integer", "minimum": 1},
                    "criterion": {"type": "string"},
                    "kind": {"enum": ["objective", "judgment", "gdpval_dim"]},
                    "gdpval_dim": {"type": ["string", "null"],
                                   "enum": ["accuracy", "instruction_following",
                                            "formatting_aesthetics", "structure_style_relevance", None]},
                    "anchor_ref": {"type": ["string", "null"]},
                    "required": {"type": "boolean"},
                },
                "required": ["score", "criterion", "kind"],
            },
        }
    },
    "required": ["items"],
}

GRADE_SCHEMA = {
    "type": "object",
    "properties": {
        "per_item": {"type": "object", "description": "{rubric_item_id: got_score}"},
        "dim_scores": {"type": "object", "description": "{gdpval_dim: 0..1}"},
        "total": {"type": "number"},
        "justification": {"type": "string"},
    },
    "required": ["per_item", "total"],
}
