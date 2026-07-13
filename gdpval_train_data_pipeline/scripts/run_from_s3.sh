#!/usr/bin/env bash
# 从 S3 续跑到落盘 (S1 切分 + S2 近邻成组已完成, 产物在 data/cleaned, outputs/bundles.jsonl)。
# 前提: config/models.yaml 里的模型 key 有余额 (2026-07-13 GLM/DeepSeek 均耗尽, 充值任一即可)。
# 用法: bash scripts/run_from_s3.sh [S7_LIMIT]
set -e
cd "$(dirname "$0")/.."
PY=/opt/conda/envs/py312/bin/python
export PYTHONPATH=src PYTHONUNBUFFERED=1
S7_LIMIT="${1:-20}"          # S7 只对前 N 条通过质检的 query 产交付物 (控成本), 不传默认 20

echo "==== S3 query 生成 ===="   ; $PY -m cli s3
echo "==== S4 质检(8 硬门槛) ===="; $PY -m cli s4
echo "==== S5 rubric 生成 ===="   ; $PY -m cli s5
echo "==== S7 交付物生成(limit=$S7_LIMIT) ===="; $PY -m cli s7 --limit "$S7_LIMIT"
echo "==== S8 打分 ===="          ; $PY -m cli s8
echo "==== emit 落盘 ===="        ; $PY -m cli emit
echo "==== 完成: outputs/items.jsonl ===="
