"""嵌入向量生成服务 —— 支持本地(sentence-transformers)和远程(LiteLLM)模式"""

import asyncio

from app.core.config import settings


class EmbeddingService:
    """文本嵌入向量生成

    支持两种 Provider:
      - local: sentence-transformers 本地模型
      - litellm: 通过 LiteLLM 调用远程嵌入 API (OpenAI/Ollama 等)
    """

    def __init__(self):
        self.provider = settings.embedding_provider
        self.model_name = settings.embedding_model
        self.dimensions = settings.embedding_dim
        self._local_model = None
        self._local_lock = asyncio.Lock()

    async def embed(self, text: str) -> list[float] | None:
        """将单段文本转为向量，失败返回 None"""
        if not text or not text.strip():
            return None
        if self.provider == "local":
            return await self._embed_local(text)
        elif self.provider == "litellm":
            return await self._embed_litellm(text)
        return None

    async def embed_batch(self, texts: list[str]) -> list[list[float] | None]:
        """批量嵌入"""
        results = []
        for t in texts:
            v = await self.embed(t)
            results.append(v)
        return results

    async def _embed_local(self, text: str) -> list[float] | None:
        """使用本地 sentence-transformers 生成向量"""
        model = await self._get_local_model()
        if model is None:
            return None
        try:
            vec = await asyncio.to_thread(lambda: model.encode(text, normalize_embeddings=True).tolist())
            return vec
        except Exception as e:
            print(f"  ❌ 本地嵌入失败: {e}")
            return None

    async def _get_local_model(self):
        """延迟加载本地模型（首次调用时加载）"""
        if self._local_model is not None:
            return self._local_model
        async with self._local_lock:
            if self._local_model is not None:
                return self._local_model
            try:
                from sentence_transformers import SentenceTransformer

                model = await asyncio.to_thread(
                    lambda: SentenceTransformer(self.model_name, device="cpu")
                )
                self._local_model = model
                print(f"  ✅ 本地嵌入模型已加载: {self.model_name} ({self.dimensions}维)")
            except Exception as e:
                print(f"  ⚠️  本地嵌入模型加载失败: {e}")
                return None
        return self._local_model

    async def _embed_litellm(self, text: str) -> list[float] | None:
        """通过 LiteLLM 调用远程嵌入 API"""
        try:
            from litellm import aembedding

            resp = await aembedding(
                model=self.model_name,
                input=[text],
            )
            return resp.data[0]["embedding"]
        except Exception as e:
            print(f"  ❌ LiteLLM 嵌入失败: {e}")
            return None
