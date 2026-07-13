"""
providers/base.py — 可插拔 LLM provider (OpenAI-compatible)。

GLM / DeepSeek 均 OpenAI-compatible, 故共用 OpenAICompatProvider, 差异走 models.yaml
的 base_url / model / extra。gemini/gpt 之后同样加一段 config 即可。

用 requests (不硬依赖 openai 包), 便于 offline-first: 无 key 时给清晰报错而非静默。
"""
from __future__ import annotations
import json
import os
import re
import time
from pathlib import Path
from typing import Optional

import requests
import yaml

_ROOT = Path(__file__).resolve().parents[2]      # final/
_MODELS_YAML = _ROOT / "config" / "models.yaml"


# ---------------------------------------------------------------------------
# .env 极简加载 (不引第三方 dotenv)
# ---------------------------------------------------------------------------
def _load_env() -> None:
    env = _ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


_load_env()


def _load_models_cfg() -> dict:
    return yaml.safe_load(_MODELS_YAML.read_text())


# ---------------------------------------------------------------------------
# JSON 容错解析: 剥 ```json fence / 取第一个平衡 {}
# ---------------------------------------------------------------------------
def extract_json(text: str) -> dict:
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    # 逐个 '{' 起点扫平衡块; **跳过字符串内的花括号** (含转义); 每个候选都试解析
    for start in (i for i, c in enumerate(text) if c == "{"):
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(text)):
            c = text[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            else:
                if c == '"':
                    in_str = True
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[start:i + 1])
                        except Exception:
                            break            # 该起点不成, 试下一个 '{'
    raise ValueError(f"无法从模型输出解析 JSON:\n{text[:500]}")


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------
class OpenAICompatProvider:
    def __init__(self, name: str, cfg: dict):
        self.name = name
        self.cfg = cfg
        self.family = cfg.get("family", name)
        self.model = cfg["model"]
        self.base_url = cfg["base_url"].rstrip("/")
        self.max_tokens = cfg.get("max_tokens", 8192)
        self.extra = cfg.get("extra", {}) or {}
        key_env = cfg["api_key_env"]
        self.api_key = os.environ.get(key_env, "")
        self._key_env = key_env

    def _require_key(self):
        if not self.api_key:
            raise RuntimeError(
                f"provider '{self.name}' 缺少 API key (环境变量 {self._key_env})。"
                f" 请在 final/.env 设置后重试。")

    def _apply_think(self, payload: dict, think: Optional[bool]) -> None:
        """think=False -> 关闭深度思考 (简单结构化任务提速); None -> 用 models.yaml 默认。"""
        if think is False:
            payload.pop("thinking", None)
            payload.pop("reasoning_effort", None)
        elif think is True:
            payload["thinking"] = {"type": "enabled"}

    def chat(self, messages: list, temperature: float = 0.7,
             max_tokens: Optional[int] = None, response_json: bool = False,
             retries: int = 3, timeout: int = 300, think: Optional[bool] = None, **kw) -> str:
        """返回最终回答文本 (不含 reasoning_content)。"""
        self._require_key()
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "stream": False,
        }
        payload.update(self.extra)
        payload.update(kw)
        self._apply_think(payload, think)
        if response_json:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self.api_key}",
                   "Content-Type": "application/json"}
        last = None
        for attempt in range(retries):
            try:
                r = requests.post(url, headers=headers, json=payload, timeout=timeout)
                if r.status_code >= 400:
                    last = f"HTTP {r.status_code}: {r.text[:300]}"
                    time.sleep(1.5 * (attempt + 1))
                    continue
                data = r.json()
                msg = data["choices"][0]["message"]
                return msg.get("content") or ""
            except Exception as e:            # noqa
                last = str(e)
                time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"provider '{self.name}' chat 失败 (重试 {retries} 次): {last}")

    def chat_messages(self, messages: list, tools: Optional[list] = None,
                      tool_choice: str = "auto", temperature: float = 0.7,
                      max_tokens: Optional[int] = None, retries: int = 3,
                      timeout: int = 300, think: Optional[bool] = None, **kw) -> dict:
        """返回原始 assistant message dict (可能含 tool_calls)。供 agent 循环用。"""
        self._require_key()
        url = f"{self.base_url}/chat/completions"
        payload = {"model": self.model, "messages": messages,
                   "temperature": temperature, "max_tokens": max_tokens or self.max_tokens,
                   "stream": False}
        payload.update(self.extra)
        payload.update(kw)
        self._apply_think(payload, think)
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        last = None
        for attempt in range(retries):
            try:
                r = requests.post(url, headers=headers, json=payload, timeout=timeout)
                if r.status_code >= 400:
                    last = f"HTTP {r.status_code}: {r.text[:300]}"
                    time.sleep(1.5 * (attempt + 1))
                    continue
                return r.json()["choices"][0]["message"]
            except Exception as e:            # noqa
                last = str(e)
                time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"provider '{self.name}' chat_messages 失败: {last}")

    def chat_json(self, messages: list, schema: Optional[dict] = None,
                  temperature: float = 0.2, retries: int = 3,
                  think: Optional[bool] = None, **kw) -> dict:
        """要求 JSON 输出并容错解析。schema 仅作提示 (放进 system)。"""
        msgs = list(messages)
        if schema is not None:
            msgs = msgs + [{
                "role": "system",
                "content": "只输出一个 JSON 对象, 无多余文字。目标结构:\n"
                           + json.dumps(schema, ensure_ascii=False),
            }]
        last = None
        for attempt in range(retries):
            txt = self.chat(msgs, temperature=temperature, response_json=True, think=think, **kw)
            try:
                return extract_json(txt)
            except Exception as e:            # noqa
                last = e
                msgs = msgs + [{"role": "user", "content": "上次输出不是合法 JSON, 请只输出 JSON。"}]
        raise RuntimeError(f"provider '{self.name}' chat_json 解析失败: {last}")


_REGISTRY: dict = {}


def get_provider(name: str) -> OpenAICompatProvider:
    if name in _REGISTRY:
        return _REGISTRY[name]
    cfg = _load_models_cfg()["providers"]
    if name not in cfg:
        raise KeyError(f"未知 provider: {name} (config/models.yaml 未定义或已注释)")
    pcfg = cfg[name]
    kind = pcfg.get("kind", "openai_compatible")
    if kind != "openai_compatible":
        raise NotImplementedError(f"provider kind 未支持: {kind}")
    # 允许 glm/deepseek 子类做细微覆写
    from . import glm, deepseek           # noqa
    klass = {"glm": glm.GLMProvider, "deepseek": deepseek.DeepSeekProvider}.get(
        name, OpenAICompatProvider)
    prov = klass(name, pcfg)
    _REGISTRY[name] = prov
    return prov


def list_by_role(role: str) -> list:
    return _load_models_cfg().get("roles", {}).get(role, [])


def family_of(name: str) -> str:
    return _load_models_cfg()["providers"][name].get("family", name)
