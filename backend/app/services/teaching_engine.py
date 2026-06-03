"""教学引擎 —— 教学对话 + 领域适配 + 学习者适配"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.adapter import LLMAdapter
from app.services.knowledge_graph import KnowledgeGraphService


class TeachingEngineService:
    """教学引擎核心：合并 Domain Profile × Learner Profile，输出教学内容"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = LLMAdapter()
        self.kg = KnowledgeGraphService()

    async def teach_node(
        self,
        node: dict,
        domain_profile: dict,
        learner_profile: dict,
        chat_history: list[dict] = None,
    ) -> str:
        """讲解一个知识点"""
        return await self.llm.teach_concept(node, domain_profile, learner_profile, chat_history)

    async def answer_question(
        self,
        question: str,
        node: dict,
        domain_profile: dict,
        learner_profile: dict,
        chat_history: list[dict],
    ) -> str:
        """回答学生提问"""
        return await self.llm.answer_question(question, node, domain_profile, learner_profile, chat_history)

    async def request_extension(
        self,
        node_id: str,
        node: dict,
        domain_profile: dict,
        learner_profile: dict,
    ) -> dict:
        """请求延伸学习"""
        # 获取关联节点
        related = await self.kg.get_related_nodes(node_id)
        prerequisites = await self.kg.get_prerequisites(node_id)

        all_related = related + [
            {"title": f"前置：{n.get('title', '')}", **n} for n in prerequisites if n.get("id") != node_id
        ]

        if not all_related:
            return {
                "content": "当前知识点没有其他关联内容。你可以尝试搜索更多资料。",
                "related_nodes": [],
            }

        # 让 LLM 推荐延伸方向
        suggestion = await self.llm.suggest_extension(node, all_related, learner_profile)

        return {
            "content": suggestion,
            "related_nodes": [
                {
                    "id": n.get("id"),
                    "title": n.get("title", ""),
                    "relation": "延伸",
                }
                for n in all_related[:5]
            ],
        }

    @staticmethod
    def get_domain_profile_path(domain_id: str) -> str:
        """获取领域配置文件的路径"""
        return f"app/domain_profiles/{domain_id}.yaml"

    @staticmethod
    def check_prerequisites_met(
        node_id: str,
        prerequisites: list[str],
        node_progress_map: dict[str, dict],
    ) -> tuple[bool, list[str]]:
        """检查前置节点是否已完成"""
        unmet = []
        for pre_id in prerequisites:
            progress = node_progress_map.get(pre_id, {})
            if progress.get("status") != "completed" or (progress.get("mastery", 0) or 0) < 0.6:
                unmet.append(pre_id)
        return len(unmet) == 0, unmet
