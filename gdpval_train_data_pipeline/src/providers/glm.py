"""providers/glm.py — GLM-5.2 (智谱 bigmodel), OpenAI-compatible。

端点/模型/思考参数见 config/models.yaml。thinking + reasoning_effort 通过 extra 透传。
如需 GLM 特有的 reasoning_content 处理可在此覆写, 目前默认取 message.content 即可。
"""
from .base import OpenAICompatProvider


class GLMProvider(OpenAICompatProvider):
    pass
