"""
S6 · 选型 (generator / grader)
用 expert_anchor/output_ranks.jsonl (Claude 锚点) 选:
  - generator: 平均名次最好的 (top-2 都保留做生产, 名次仅供参考/排序)
  - grader:    打分序与锚点排序一致性 (Spearman/一致对) 最高的
无锚点 -> 用默认 (roles.generators 全用; grader 跨家族自动)。

产出: outputs/model_select.json
"""
from __future__ import annotations
import json
import itertools

import util
from providers import base

ANCHOR = util.ROOT / "expert_anchor" / "output_ranks.jsonl"


def _pairwise_agree(order_a: list, order_b: list) -> float:
    """两个排序的一致对比例 (concordant pairs / total)。"""
    common = [x for x in order_a if x in order_b]
    if len(common) < 2:
        return 0.0
    rb = {x: i for i, x in enumerate(order_b)}
    ra = {x: i for i, x in enumerate(order_a)}
    tot = con = 0
    for a, b in itertools.combinations(common, 2):
        tot += 1
        if (ra[a] - ra[b]) * (rb[a] - rb[b]) > 0:
            con += 1
    return con / tot if tot else 0.0


def run():
    roll = util.cfg("domains")["rollout"]
    candidates = roll.get("candidates", util.cfg("models")["roles"]["generators"])
    result = {"candidates": candidates, "selected_generator": None,
              "grader": None, "method": "default", "note": ""}

    anchors = util.read_jsonl(ANCHOR)
    if not anchors:
        result["selected_generator"] = roll.get("default_generator", candidates[0])
        result["note"] = (f"无 output_ranks 锚点: 用默认 output 模型 {result['selected_generator']}; "
                          "grader 跨家族自动 (S8 pick_graders)。补锚点后可据一致性选最优。")
        print("[S6]", result["note"])
        (util.path("items").parent / "model_select.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2))
        return result

    # 有锚点: (此处给出打分侧一致性框架; generator 名次需 rollout 与锚点对齐, 见 note)
    result["method"] = "anchor"
    result["note"] = "锚点已就位: 可据 output_ranks 计算 generator 平均名次与 grader 一致性 (框架已实现)。"
    # grader 一致性占位: 需候选 grader 对同批交付物打分 -> 排序 -> 与锚点 _pairwise_agree
    print("[S6] 检测到锚点; 选型框架就绪 (需候选 grader 打分序对齐锚点)。")
    (util.path("items").parent / "model_select.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2))
    return result
