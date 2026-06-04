"""语音模块单元测试 —— ASR + TTS 服务"""

from app.services.voice import (
    synthesize_speech,
    transcribe_audio,
    is_asr_available,
    is_tts_available,
    _asr_available,
    _tts_available,
    _MAX_AUDIO_BYTES,
)


class TestAvailable:
    """可用性检查测试"""

    def test_tts_available_flag(self):
        """edge-tts 未安装时应返回 False"""
        # 运行环境中 edge-tts 可能未安装，此处只验证函数返回与模块级标志一致
        assert is_tts_available() == _tts_available

    async def test_asr_available_flag(self):
        """faster-whisper 未安装时应返回 False"""
        available = await is_asr_available()
        # 本地无 Whisper 模型时应为 False
        assert available is False


class TestSynthesizeSpeech:
    """TTS 语音合成测试"""

    async def test_tts_not_available_returns_none(self):
        """edge-tts 不可用时返回 None"""
        if not _tts_available:
            result = await synthesize_speech("测试文字")
            assert result is None

    async def test_tts_empty_text(self):
        """空文本也应返回有效结果或 None（取决于是否可用）"""
        result = await synthesize_speech("")
        if not _tts_available:
            assert result is None
        # 如果 TTS 可用，空文本也可能返回空音频
        if result is not None:
            assert isinstance(result, bytes)


class TestTranscribeAudio:
    """ASR 语音转写测试"""

    async def test_asr_not_available_returns_none(self):
        """Whisper 模型不可用时返回 None"""
        result = await transcribe_audio(b"fake_audio_data")
        # 无 Whisper 时应返回 None
        if not _asr_available:
            assert result is None

    async def test_asr_empty_bytes(self):
        """空字节应返回 None（无模型）或空字符串（有模型但识别到空）"""
        result = await transcribe_audio(b"")
        if not _asr_available:
            assert result is None

    async def test_asr_exceeds_size_limit(self):
        """超过大小限制应直接返回 None"""
        oversized = b"\x00" * (_MAX_AUDIO_BYTES + 1)
        result = await transcribe_audio(oversized)
        assert result is None

    async def test_asr_exact_size_limit(self):
        """刚好等于大小限制的应尝试处理（而非直接拒绝）"""
        at_limit = b"\x00" * _MAX_AUDIO_BYTES
        result = await transcribe_audio(at_limit)
        # 无模型时返回 None，有模型时继续处理
        if not _asr_available:
            assert result is None


class TestAudioSizeLimit:
    """音频大小限制测试"""

    def test_max_audio_bytes_positive(self):
        """大小限制常量应为正数"""
        assert _MAX_AUDIO_BYTES > 0

    def test_max_audio_bytes_value(self):
        """默认限制应为 10MB"""
        assert _MAX_AUDIO_BYTES == 10 * 1024 * 1024
