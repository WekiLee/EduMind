"""运行时配置安全回归测试。"""

from app.llm.adapter import LLMAdapter


def test_runtime_api_key_can_be_cleared():
    """系统 API Key 显式传空时应清理进程内旧密钥。"""
    old_provider = LLMAdapter._runtime_provider
    old_model = LLMAdapter._runtime_model
    old_api_key = LLMAdapter._runtime_api_key
    old_api_base = LLMAdapter._runtime_api_base
    try:
        LLMAdapter.update_runtime_config(api_key="sk-test")
        assert LLMAdapter._runtime_api_key == "sk-test"

        LLMAdapter.update_runtime_config(api_key=None)
        assert LLMAdapter._runtime_api_key is None
    finally:
        LLMAdapter._runtime_provider = old_provider
        LLMAdapter._runtime_model = old_model
        LLMAdapter._runtime_api_key = old_api_key
        LLMAdapter._runtime_api_base = old_api_base
