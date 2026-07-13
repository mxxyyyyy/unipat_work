"""providers/embedding.py — 本地 Qwen3-Embedding-0.6B (S2 近邻成组用)。

用 sentence-transformers 加载。无权重则**清晰报错**, 不静默降级 (config/models.yaml
embedding.fallback: null)。
"""
from __future__ import annotations
from pathlib import Path
from typing import List
import yaml

_ROOT = Path(__file__).resolve().parents[2]
_MODELS_YAML = _ROOT / "config" / "models.yaml"

_MODEL = None
_CFG = None


def _cfg() -> dict:
    global _CFG
    if _CFG is None:
        _CFG = yaml.safe_load(_MODELS_YAML.read_text())["embedding"]
    return _CFG


def _resolve_device(device: str) -> str:
    if device != "auto":
        return device
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def _load():
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    cfg = _cfg()
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        raise RuntimeError(
            "缺少 sentence-transformers。请 `pip install sentence-transformers`。") from e
    try:
        _MODEL = SentenceTransformer(cfg["model"], device=_resolve_device(cfg.get("device", "auto")))
    except Exception as e:
        raise RuntimeError(
            f"无法加载 embedding 模型 {cfg['model']}: {e}\n"
            f"请确认本机可访问该权重 (HF 缓存或本地路径)。fallback=null, 不静默降级。") from e
    return _MODEL


def embed(texts: List[str]):
    """返回 (n, d) numpy 数组, 已按 config 归一化。"""
    cfg = _cfg()
    model = _load()
    return model.encode(
        texts,
        batch_size=cfg.get("batch_size", 16),
        normalize_embeddings=cfg.get("normalize", True),
        show_progress_bar=False,
        convert_to_numpy=True,
    )
