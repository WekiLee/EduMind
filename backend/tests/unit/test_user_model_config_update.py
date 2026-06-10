"""用户级模型配置清洗测试。"""

from app.api.users import build_model_config_update


def test_model_config_preserves_existing_api_key_when_omitted():
    """未提交 api_key 字段时保留旧密钥。"""
    result = build_model_config_update(
        {"provider": "openai-compatible", "api_key_masked": "****"},
        {"api_key": "sk-old"},
    )

    assert result["provider"] == "openai-compatible"
    assert result["api_key"] == "sk-old"
    assert "api_key_masked" not in result


def test_model_config_clears_api_key_when_empty():
    """显式提交空 api_key 时清空旧密钥。"""
    result = build_model_config_update(
        {"provider": "openai-compatible", "api_key": ""},
        {"api_key": "sk-old"},
    )

    assert result == {"provider": "openai-compatible"}


def test_model_config_trims_new_api_key():
    """新密钥应去除首尾空白后保存。"""
    result = build_model_config_update({"api_key": "  sk-new  "})

    assert result["api_key"] == "sk-new"
