"""交叉验证服务 —— 多源内容合并 + 置信评分 + 结构化输出"""

from app.llm.adapter import LLMAdapter


class CrossValidationService:
    """
    交叉验证：将 LLM 生成的知识点与搜索结果进行比对、合并、评分。

    流程：
      1. LLM 提取主题内容 → 生成初步 knowledge
      2. 搜索编排器获取多源结果
      3. LLM 交叉验证 → 合并内容、标记矛盾、分配置信度
      4. 输出 enriched knowledge（含 source / confidence 元数据）
    """

    def __init__(self):
        self.llm = LLMAdapter()

    async def enrich_with_search(
        self,
        topic: str,
        llm_knowledge: dict,
        search_results: list[SearchResult],
        domain_id: str,
    ) -> dict:
        """
        将 LLM 提取的知识点与搜索结果交叉验证，返回增强后的 knowledge。

        Args:
            topic: 原始主题
            llm_knowledge: LLM extract_knowledge 输出的结构
            search_results: 搜索结果列表
            domain_id: 领域 ID

        Returns:
            enriched knowledge dict，结构与 extract_knowledge 相同，
            但每个 node 额外包含 confidence / sources 字段。
        """
        if not search_results:
            # 无搜索结果，直接返回原内容（confidence 默认 0.8）
            return self._add_default_confidence(llm_knowledge)

        # 让 LLM 进行交叉验证
        enriched = await self.llm.cross_validate_knowledge(
            topic=topic,
            llm_knowledge=llm_knowledge,
            search_snippets=[r.snippet for r in search_results],
            search_sources=[r.source for r in search_results],
            domain_id=domain_id,
        )

        # 如果 LLM 交叉验证失败，回退到原内容
        if not enriched or not enriched.get("nodes"):
            return self._add_default_confidence(llm_knowledge)

        return enriched

    @staticmethod
    def _add_default_confidence(knowledge: dict) -> dict:
        """为没有置信度的节点添加默认置信度"""
        for node in knowledge.get("nodes", []):
            if "confidence" not in node:
                node["confidence"] = 0.8
            if "sources" not in node:
                node["sources"] = ["llm_generated"]
        return knowledge
