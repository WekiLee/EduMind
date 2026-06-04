"""搜索编排器 —— 多源并行搜索 + 统一结果格式"""

import asyncio
from dataclasses import dataclass, field
from urllib.parse import quote_plus

import httpx

from app.core.config import settings


@dataclass
class SearchResult:
    """统一搜索结果格式"""
    title: str
    snippet: str
    url: str
    source: str  # 来源标识，如 "web" / "duckduckgo" / "searxng"


@dataclass
class SearchResponse:
    """搜索响应"""
    query: str
    results: list[SearchResult] = field(default_factory=list)
    error: str | None = None


class SearchOrchestrator:
    """
    搜索编排器：按配置选择搜索后端，并发查询，返回统一格式结果。

    支持的 Provider：
      - duckduckgo: 无需 API Key，直接调用 DuckDuckGo Lite API（适合 MVP）
      - searxng: 自建 SearXNG 实例（适合生产）
      - none: 关闭搜索（降级为纯 LLM 生成）
    """

    def __init__(self):
        self.provider = settings.search_provider.lower()
        self.api_url = settings.search_api_url

    async def search(self, query: str, max_results: int = 5) -> SearchResponse:
        """
        搜索入口：根据配置的 provider 分发到对应后端。
        """
        if self.provider == "none" or self.provider == "":
            return SearchResponse(query=query, results=[])

        if self.provider == "duckduckgo":
            return await self._search_duckduckgo(query, max_results)
        elif self.provider == "searxng":
            return await self._search_searxng(query, max_results)
        else:
            # 未知 provider，降级返回空
            return SearchResponse(query=query, error=f"不支持的搜索 provider: {self.provider}")

    async def _search_duckduckgo(self, query: str, max_results: int) -> SearchResponse:
        """
        通过 DuckDuckGo Lite API 搜索（免费，无需 Key）。
        API: https://api.duckduckgo.com/?q=...&format=json
        """
        url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1&skip_disambig=1"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

            results = []
            # DuckDuckGo 的 AbstractText 是最佳匹配
            abstract = data.get("AbstractText", "")
            if abstract:
                results.append(SearchResult(
                    title=data.get("Heading", query),
                    snippet=abstract[:500],
                    url=data.get("AbstractURL", ""),
                    source="duckduckgo",
                ))

            # RelatedTopics 作为补充
            for topic in data.get("RelatedTopics", [])[:max_results]:
                if "Text" in topic:
                    results.append(SearchResult(
                        title=topic.get("Text", "")[:100],
                        snippet=topic.get("Text", "")[:500],
                        url=topic.get("FirstURL", ""),
                        source="duckduckgo",
                    ))
                elif "Topics" in topic:
                    for sub in topic["Topics"][:3]:
                        results.append(SearchResult(
                            title=sub.get("Text", "")[:100],
                            snippet=sub.get("Text", "")[:500],
                            url=sub.get("FirstURL", ""),
                            source="duckduckgo",
                        ))

            return SearchResponse(query=query, results=results[:max_results])
        except Exception as e:
            return SearchResponse(query=query, error=f"DuckDuckGo 搜索失败: {e}")

    async def _search_searxng(self, query: str, max_results: int) -> SearchResponse:
        """
        通过自建 SearXNG 实例搜索。
        需在 .env 中配置 SEARCH_API_URL 指向 SearXNG 实例。
        """
        if not self.api_url:
            return SearchResponse(query=query, error="SearXNG 未配置 SEARCH_API_URL")

        params = {
            "q": query,
            "format": "json",
            "language": "zh-CN",
            "categories": "general",
            "pageno": 1,
        }
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(f"{self.api_url}/search", params=params)
                resp.raise_for_status()
                data = resp.json()

            results = []
            for item in data.get("results", [])[:max_results]:
                results.append(SearchResult(
                    title=item.get("title", "")[:200],
                    snippet=item.get("content", item.get("snippet", ""))[:500],
                    url=item.get("url", ""),
                    source="searxng",
                ))
            return SearchResponse(query=query, results=results)
        except Exception as e:
            return SearchResponse(query=query, error=f"SearXNG 搜索失败: {e}")

    async def parallel_search(self, queries: list[str], max_results_per_query: int = 3) -> dict[str, SearchResponse]:
        """
        并发执行多个搜索查询。
        返回 {query: SearchResponse} 映射。
        """
        tasks = [self.search(q, max_results_per_query) for q in queries]
        responses = await asyncio.gather(*tasks)
        return dict(zip(queries, responses, strict=False))
