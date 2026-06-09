"""语音服务 —— ASR 语音识别 + TTS 语音合成（支持 edge-tts / Kokoro）"""

import asyncio
import io
import tempfile
import wave
from pathlib import Path

from app.core.config import settings

# ── TTS: edge-tts ──

_edge_tts_available = False
try:
    import edge_tts

    _edge_tts_available = True
except ImportError:
    pass

# ── TTS: Kokoro ──

_kokoro_available = False
_kokoro_pipeline = None
_kokoro_init_lock = asyncio.Lock()


async def _get_kokoro_pipeline():
    """延迟加载 Kokoro 模型"""
    global _kokoro_pipeline, _kokoro_available
    if _kokoro_pipeline is not None:
        return _kokoro_pipeline
    async with _kokoro_init_lock:
        if _kokoro_pipeline is not None:
            return _kokoro_pipeline
        try:
            from kokoro import KPipeline

            pipeline = await asyncio.to_thread(lambda: KPipeline(lang_code="z"))
            _kokoro_pipeline = pipeline
            _kokoro_available = True
            print("  ✅ Kokoro TTS 模型已加载")
        except Exception as e:
            print(f"  ⚠️ Kokoro 加载失败: {e}")
            _kokoro_available = False
    return _kokoro_pipeline


# ── ASR ──

_asr_model = None
_asr_available = False
_asr_init_lock = asyncio.Lock()
_MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10MB


async def _get_asr_model():
    """异步延迟加载 Whisper 模型"""
    global _asr_model, _asr_available
    if _asr_model is not None:
        return _asr_model
    async with _asr_init_lock:
        if _asr_model is not None:
            return _asr_model
        try:
            from faster_whisper import WhisperModel

            model_size = settings.whisper_model_size
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
    if len(audio_data) > _MAX_AUDIO_BYTES:
        print(f"  ❌ ASR 音频过大: {len(audio_data)} bytes（上限 {_MAX_AUDIO_BYTES}）")
        return None

    model = await _get_asr_model()
    if model is None:
        return None

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


# ── TTS 统一接口 ──


async def synthesize_speech(text: str, voice: str = "zh-CN-XiaoxiaoNeural") -> bytes | None:
    """
    TTS：将文字转为语音。

    根据 settings.tts_provider 选择引擎：
      - edge-tts: 输出 MP3 格式
      - kokoro:   输出 WAV 格式（PCM 16-bit 24kHz 单声道）

    Args:
        text: 要朗读的文字
        voice: 语音角色（仅 edge-tts 使用）

    Returns:
        音频二进制数据（MP3 或 WAV），失败返回 None
    """
    provider = settings.tts_provider.lower()

    if provider == "kokoro":
        return await _synthesize_kokoro(text)
    else:
        return await _synthesize_edge_tts(text, voice)


async def _synthesize_edge_tts(text: str, voice: str) -> bytes | None:
    """使用 edge-tts 合成（MP3 输出）"""
    if not _edge_tts_available:
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
        print(f"  ❌ edge-tts 合成失败: {e}")
        return None


async def _synthesize_kokoro(text: str) -> bytes | None:
    """使用 Kokoro 合成（WAV/PCM 输出）"""
    pipeline = await _get_kokoro_pipeline()
    if pipeline is None:
        # 回退到 edge-tts
        print("  ⚠️ Kokoro 不可用，回退到 edge-tts")
        return await _synthesize_edge_tts(text, "zh-CN-XiaoxiaoNeural")

    try:
        audio_chunks = []
        for result in pipeline(text, voice="zf_001", speed=1.0):
            audio_chunks.append(result.audio)

        if not audio_chunks:
            return None

        # 拼接所有音频块为 WAV
        import numpy as np

        full_audio = np.concatenate(audio_chunks)
        sample_rate = 24000

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(full_audio.astype(np.int16).tobytes())

        return buf.getvalue()
    except Exception as e:
        print(f"  ❌ Kokoro 合成失败: {e}")
        return None


async def is_asr_available() -> bool:
    """检查 ASR 是否可用"""
    await _get_asr_model()
    return _asr_available


def is_tts_available() -> bool:
    """检查 TTS 是否可用"""
    return _edge_tts_available or _kokoro_available
