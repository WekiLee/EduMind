"""用户模型安全输出测试。"""

from app.models.user import User


def test_public_model_config_masks_api_key():
    """用户模型配置输出时应隐藏原始 API Key。"""
    result = User._public_model_config(
        {
            "provider": "openai-compatible",
            "model": "demo-model",
            "api_key": "sk-1234567890abcdef",
            "api_base": "https://example.com/v1",
        }
    )

    assert result["provider"] == "openai-compatible"
    assert result["model"] == "demo-model"
    assert result["api_base"] == "https://example.com/v1"
    assert "api_key" not in result
    assert result["api_key_masked"].startswith("sk-123")


def test_public_model_config_empty_returns_none():
    """空模型配置应保持为空，避免前端误判存在密钥。"""
    assert User._public_model_config(None) is None
    assert User._public_model_config({}) is None
