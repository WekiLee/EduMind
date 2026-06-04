"""语音服务 —— ASR 语音识别 + TTS 语音合成"""

import asyncio
import tempfile
from pathlib import Path

from app.core.config import settings

# ── TTS ──

_tts_available = False
try:
    import edge_tts

    _tts_available = True
except ImportError:
    pass

# ── ASR ──

_asr_model = None
_asr_available = False
_asr_init_lock = asyncio.Lock()
_MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10MB


async def _get_asr_model():
    """异步延迟加载 Whisper 模型（首次调用时加载，避免阻塞事件循环）"""
    global _asr_model, _asr_available
    if _asr_model is not None:
        return _asr_model
    async with _asr_init_lock:
        # 双检锁
        if _asr_model is not None:
            return _asr_model
        try:
            from faster_whisper import WhisperModel

            model_size = settings.whisper_model_size
            # 模型加载可能耗时，放到线程池避免阻塞事件循环
            model = await asyncio.to_thread(
                lambda: WhisperModel(model_size, device="cpu", compute_type="int8")
            )
            _asr_model = model
            _asr_available = True
            print(f"  ✅ Whisper 模型已加载: {model_size}")
        except Exception as e:
            print(f"  ⚠️ Whisper 加载失败（语音识别不可用）: {e}")
            _asr_available = False
    return _asr_model


async def transcribe_audio(audio_data: bytes, sample_rate: int = 16000) -> str | None:
    """
    ASR：将音频数据转为文字。

    Args:
        audio_data: 音频二进制数据（支持 WAV / WebM / MP3 等常见格式）
        sample_rate: 采样率（Hz）

    Returns:
        识别出的文字，失败返回 None
    """
    # 大小校验
    if len(audio_data) > _MAX_AUDIO_BYTES:
        print(f"  ❌ ASR 音频过大: {len(audio_data)} bytes（上限 {_MAX_AUDIO_BYTES}）")
        return None

    model = await _get_asr_model()
    if model is None:
        return None

    # 写入临时文件（Whisper 需要文件路径）
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_data)
        tmp_path = tmp.name

    try:
        segments, _ = await asyncio.to_thread(
            model.transcribe, tmp_path, language="zh", beam_size=5
        )
        text = "".join(seg.text for seg in segments)
        return text.strip()
    except Exception as e:
        print(f"  ❌ ASR 识别失败: {e}")
        return None
    finally:
        Path(tmp_path).unlink(missing_ok=True)


async def synthesize_speech(text: str, voice: str = "zh-CN-XiaoxiaoNeural") -> bytes | None:
    """
    TTS：将文字转为语音（MP3 格式，edge-tts 输出）。

    Args:
        text: 要朗读的文字
        voice: 语音角色，默认中文女声

    Returns:
        MP3 音频二进制数据，失败返回 None
    """
    if not _tts_available:
        print("  ⚠️ edge-tts 未安装，TTS 不可用")
        return None

    try:
        communicate = edge_tts.Communicate(text, voice)
        audio_bytes = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes += chunk["data"]
        return audio_bytes
    except Exception as e:
        print(f"  ❌ TTS 合成失败: {e}")
        return None


async def is_asr_available() -> bool:
    """检查 ASR 是否可用"""
    await _get_asr_model()
    return _asr_available


def is_tts_available() -> bool:
    """检查 TTS 是否可用"""
    return _tts_available
