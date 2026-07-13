"""providers/deepseek.py — deepseek-v4-pro, OpenAI-compatible。

端点/模型/思考参数见 config/models.yaml。也支持 Anthropic-compat (/anthropic), 此处走
OpenAI-compat。deepseek 会返回 reasoning_content, 最终答案在 message.content。
"""
from .base import OpenAICompatProvider


class DeepSeekProvider(OpenAICompatProvider):
    pass
