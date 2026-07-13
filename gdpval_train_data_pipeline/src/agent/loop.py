"""
agent/loop.py — 多轮 agent 循环 (OpenAI-compatible function calling)。
读 reference -> 规划 -> python_exec 计算/建表/生成文件 -> 自检 -> finish。
"""
from __future__ import annotations
import json
from pathlib import Path

import util
from .tools import ToolBox, TOOL_SCHEMAS


def _materialize_reference(query: dict, workdir: Path) -> dict:
    """把 bundle 的 reference 文本写成文件, 返回 {friendly_name: abs_path}。"""
    idx = util.cleaned_index()
    refdir = workdir / "reference"
    refdir.mkdir(parents=True, exist_ok=True)
    mapping = {}
    for fid in query.get("reference_files", []):
        d = idx.get(fid)
        if not d:
            continue
        fname = f"{fid}.md"
        p = refdir / fname
        p.write_text(f"# {d['title']}\n\n{d['reference_text']}")
        mapping[fname] = str(p)
        mapping[fid] = str(p)
    return mapping


def run_agent(provider, query: dict, out_dir: str, max_turns: int = 12,
              temperature: float = 0.9, timeout=120, mem_mb=2048) -> dict:
    workdir = Path(out_dir)
    workdir.mkdir(parents=True, exist_ok=True)
    ref_map = _materialize_reference(query, workdir)
    tb = ToolBox(str(workdir), ref_map, timeout=timeout, mem_mb=mem_mb)

    sys_prompt = util.load_prompt("output_agent", query["domain"])
    ref_list = "\n".join(f"- {k}" for k in ref_map if not k.startswith(query.get("domain", "")))
    user = (
        f"# 任务 ({query['occupation']} / {query['deliverable_type']})\n{query['prompt']}\n\n"
        f"## 子任务\n" + "\n".join(query.get("subtasks", [])) + "\n\n"
        f"## 交付物格式要求\n{query.get('format_spec','')}\n\n"
        f"## 可读 reference 文件 (用 read_file)\n{ref_list}\n\n"
        f"请动手完成并把交付物文件生成到当前工作目录, 最后 finish。"
    )
    messages = [{"role": "system", "content": sys_prompt},
                {"role": "user", "content": user}]

    trace = []
    for turn in range(max_turns):
        msg = provider.chat_messages(messages, tools=TOOL_SCHEMAS,
                                     temperature=temperature, max_tokens=8000)
        # 规范化: 去掉 reasoning_content, 保留 content/tool_calls
        amsg = {"role": "assistant", "content": msg.get("content") or ""}
        tool_calls = msg.get("tool_calls") or []
        if tool_calls:
            amsg["tool_calls"] = tool_calls
        messages.append(amsg)

        if not tool_calls:
            trace.append({"turn": turn, "text": (msg.get("content") or "")[:300]})
            messages.append({"role": "user",
                             "content": "请用工具真正生成交付物文件并调用 finish; 不要只描述。"})
            continue

        for tc in tool_calls:
            fn = tc.get("function", {})
            name = fn.get("name", "")
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except Exception:
                args = {}
            result = tb.call(name, args)
            trace.append({"turn": turn, "tool": name,
                          "args": {k: (str(v)[:120]) for k, v in args.items()},
                          "result": result[:400]})
            messages.append({"role": "tool", "tool_call_id": tc.get("id", ""),
                             "content": result[:16000]})   # 够放 read_file 的长 reference
        if tb.finished:
            break

    return {"deliverable_path": tb.finished, "turns": turn + 1, "trace": trace}
