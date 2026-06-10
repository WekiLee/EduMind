"""WebSocket 输入解析回归测试。"""

import base64

from app.ws.chat import decode_audio_payload, decode_ws_payload


def test_decode_ws_payload_rejects_invalid_json():
    """非法 JSON 应返回稳定错误码。"""
    data, error = decode_ws_payload("{bad json")

    assert data is None
    assert error["code"] == "invalid_payload"


def test_decode_ws_payload_rejects_non_object():
    """数组等非对象 JSON 不应进入业务处理。"""
    data, error = decode_ws_payload("[1, 2, 3]")

    assert data is None
    assert error["code"] == "invalid_payload"


def test_decode_audio_payload_rejects_invalid_base64():
    """非法 base64 音频应返回 invalid_audio。"""
    audio, error = decode_audio_payload("not-base64!")

    assert audio is None
    assert error["code"] == "invalid_audio"


def test_decode_audio_payload_accepts_valid_base64():
    """合法 base64 音频应解码为 bytes。"""
    payload = base64.b64encode(b"audio").decode()

    audio, error = decode_audio_payload(payload)

    assert audio == b"audio"
    assert error is None
