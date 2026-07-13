"""
cli.py · 管线入口
用法 (在 final/ 下):
  PYTHONPATH=src /opt/conda/envs/py312/bin/python -m cli s1 --limit 3
  PYTHONPATH=src /opt/conda/envs/py312/bin/python -m cli s2
  PYTHONPATH=src /opt/conda/envs/py312/bin/python -m cli s3 --limit-bundles 5
  ... s4 s5 s6 s7 s8 emit
  PYTHONPATH=src /opt/conda/envs/py312/bin/python -m cli all --limit 3
"""
from __future__ import annotations
import argparse


def main():
    ap = argparse.ArgumentParser(prog="gdpval-pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("s1"); p.add_argument("--limit", type=int); p.add_argument("--domain"); p.add_argument("--only")
    sub.add_parser("s2")
    p = sub.add_parser("s3"); p.add_argument("--limit-bundles", type=int)
    p = sub.add_parser("s4"); p.add_argument("--model"); p.add_argument("--limit", type=int)
    p = sub.add_parser("s5"); p.add_argument("--limit", type=int)
    sub.add_parser("s6")
    p = sub.add_parser("s7"); p.add_argument("--limit", type=int)
    p = sub.add_parser("s8"); p.add_argument("--limit", type=int)
    sub.add_parser("emit")
    p = sub.add_parser("all"); p.add_argument("--limit", type=int, default=3)

    a = ap.parse_args()
    if a.cmd == "s1":
        from stages import s1_partition; s1_partition.run(limit=a.limit, domain=a.domain, only=a.only)
    elif a.cmd == "s2":
        from stages import s2_neighbor_grouping; s2_neighbor_grouping.run()
    elif a.cmd == "s3":
        from stages import s3_query_gen; s3_query_gen.run(limit_bundles=a.limit_bundles)
    elif a.cmd == "s4":
        from stages import s4_qc; s4_qc.run(model=a.model, limit=a.limit)
    elif a.cmd == "s5":
        from stages import s5_rubric_gen; s5_rubric_gen.run(limit=a.limit)
    elif a.cmd == "s6":
        from stages import s6_model_select; s6_model_select.run()
    elif a.cmd == "s7":
        from stages import s7_produce; s7_produce.run(limit=a.limit)
    elif a.cmd == "s8":
        from stages import s8_grade; s8_grade.run(limit=a.limit)
    elif a.cmd == "emit":
        import emit; emit.run()
    elif a.cmd == "all":
        from stages import (s1_partition, s2_neighbor_grouping, s3_query_gen,
                            s4_qc, s5_rubric_gen, s7_produce, s8_grade)
        import emit
        s1_partition.run(limit=a.limit)
        s2_neighbor_grouping.run()
        s3_query_gen.run()
        s4_qc.run()
        s5_rubric_gen.run()
        s7_produce.run()
        s8_grade.run()
        emit.run()


if __name__ == "__main__":
    main()
