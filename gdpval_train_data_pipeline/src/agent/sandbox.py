"""
agent/sandbox.py — pilot 沙箱: subprocess + 超时 + 工作目录隔离 + 危险调用 denylist。

诚实边界: 这**不是**强安全沙箱(无 namespace/cgroup 隔离, 无法真断网)。适用于可信机器上
生成良性金融分析代码的 pilot。加固路径见 pipeline.yaml agent.sandbox (Docker)。
"""
from __future__ import annotations
import os
import re
import subprocess
import sys
from pathlib import Path

# 明显危险/越权调用的 denylist (软防护, 非完全隔离)
_DENY = [
    r"\bos\.system\b", r"\bos\.popen\b", r"\bsubprocess\b", r"\bsocket\b",
    r"\bshutil\.rmtree\b", r"\brequests\b", r"\burllib\b", r"\bhttpx\b", r"\bftplib\b",
    r"__import__\(\s*['\"]os['\"]",
    r"open\(\s*['\"]/(etc|root|proc|sys)\b",
    # 注: 不封 eval/exec —— 会误杀 pandas.eval / DataFrame.eval; 主要越权(system/net)已封
]
_DENY_RE = [re.compile(p) for p in _DENY]

PY = sys.executable        # /opt/conda/envs/py312/bin/python


def scan(code: str) -> list:
    return [p.pattern for p, r in zip(_DENY, _DENY_RE) if r.search(code)]


def run_python(code: str, workdir: str, timeout: int = 120, mem_mb: int = 2048) -> dict:
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    bad = scan(code)
    if bad:
        return {"ok": False, "stdout": "", "stderr": f"[sandbox] 命中 denylist: {bad}",
                "returncode": -1, "files": []}

    before = set(p.name for p in workdir.iterdir())
    script = workdir / "_run.py"
    script.write_text(code)

    def _limit():
        try:
            import resource
            b = mem_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (b, b))
        except Exception:
            pass

    try:
        proc = subprocess.run(
            [PY, "_run.py"], cwd=str(workdir), timeout=timeout,
            capture_output=True, text=True, preexec_fn=_limit,
            env={**os.environ, "MPLBACKEND": "Agg", "OPENBLAS_NUM_THREADS": "4"})
        after = set(p.name for p in workdir.iterdir())
        new_files = sorted(after - before - {"_run.py"})
        return {"ok": proc.returncode == 0, "stdout": proc.stdout[-6000:],
                "stderr": proc.stderr[-4000:], "returncode": proc.returncode,
                "files": new_files}
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": f"[sandbox] 超时 {timeout}s",
                "returncode": -9, "files": []}
    except Exception as e:                       # noqa
        return {"ok": False, "stdout": "", "stderr": f"[sandbox] {e}",
                "returncode": -1, "files": []}
