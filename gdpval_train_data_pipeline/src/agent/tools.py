"""
agent/tools.py — agent 可用工具 (OpenAI function-calling schema + 执行器)。
工具执行绑定到一个 workdir 与该题的 reference 文件。
"""
from __future__ import annotations
import json
from pathlib import Path

from . import sandbox

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "read_file", "description": "读取一个 reference 文件或 workdir 内文件的文本内容。",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}},
                       "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "python_exec",
        "description": "在沙箱执行 Python 代码 (cwd=workdir, 已装 pandas/numpy/openpyxl/matplotlib/reportlab/python-docx/weasyprint/jinja2)。打印你要回看的中间结果。生成的文件留在 workdir。",
        "parameters": {"type": "object", "properties": {"code": {"type": "string"}},
                       "required": ["code"]}}},
    {"type": "function", "function": {
        "name": "write_file", "description": "把文本写入 workdir 下的文件 (如 .md/.html)。",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"]}}},
    {"type": "function", "function": {
        "name": "finish", "description": "声明最终交付物文件(在 workdir 内)的相对路径, 结束任务。",
        "parameters": {"type": "object", "properties": {"deliverable_path": {"type": "string"}},
                       "required": ["deliverable_path"]}}},
]


class ToolBox:
    def __init__(self, workdir: str, reference_paths: dict, timeout=120, mem_mb=2048):
        self.workdir = Path(workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.reference_paths = reference_paths      # {name_or_id: abs_path}
        self.timeout = timeout
        self.mem_mb = mem_mb
        self.finished = None

    def _resolve(self, path: str) -> Path:
        # reference 名直达
        if path in self.reference_paths:
            return Path(self.reference_paths[path])
        p = Path(path)
        if not p.is_absolute():
            p = self.workdir / p
        return p

    def call(self, name: str, args: dict) -> str:
        try:
            if name == "read_file":
                p = self._resolve(args["path"])
                if not p.exists():
                    avail = list(self.reference_paths) + [x.name for x in self.workdir.iterdir()]
                    return f"[read_file] 不存在: {args['path']}。可用: {avail}"
                return p.read_text(errors="ignore")[:15000]
            if name == "python_exec":
                r = sandbox.run_python(args["code"], str(self.workdir),
                                       timeout=self.timeout, mem_mb=self.mem_mb)
                return json.dumps({"ok": r["ok"], "stdout": r["stdout"],
                                   "stderr": r["stderr"], "new_files": r["files"]},
                                  ensure_ascii=False)
            if name == "write_file":
                p = self._resolve(args["path"])
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(args["content"])
                return f"[write_file] 写入 {p.name} ({len(args['content'])} chars)"
            if name == "finish":
                dp = self._resolve(args["deliverable_path"])
                if not dp.exists():
                    return f"[finish] 交付物不存在: {args['deliverable_path']}, 请先生成再 finish。"
                if dp.stat().st_size == 0:
                    return f"[finish] 交付物为空, 请检查。"
                self.finished = str(dp)
                return f"[finish] OK -> {dp.name}"
            return f"[未知工具] {name}"
        except Exception as e:                       # noqa
            return f"[{name}] 执行异常: {e}"
