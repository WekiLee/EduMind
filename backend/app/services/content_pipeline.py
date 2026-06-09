"""内容管道 —— 混合内容源提取 + 领域识别 + 结构化入库"""

import asyncio
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.adapter import LLMAdapter
from app.models.path import LearningPath
from app.services.cross_validation import CrossValidationService
from app.services.knowledge_graph import KnowledgeGraphService
from app.services.search_orchestrator import SearchOrchestrator
from app.services.semantic_search import SemanticSearchService


class ContentPipelineService:
    """内容管道：接收用户输入 → 提取知识点 → 图谱入库 → 生成大纲"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = LLMAdapter()
        self.kg = KnowledgeGraphService()
        self.searcher = SearchOrchestrator()
        self.cross_validator = CrossValidationService()

    async def process_topic(self, user_id: str, topic: str, domain_id: str) -> LearningPath:
        """模式A：通过主题生成学习路径"""
        # 0. 自动检测领域（如果用户未指定）
        if not domain_id or domain_id == "auto":
            detected = await self.llm.detect_domain(topic)
            domain_id = detected.get("domain", "general")
        # 1. 让 LLM 生成内容（基于主题）
        knowledge = await self.llm.extract_knowledge(f"主题：{topic}", domain_id)

        # 2. 创建学习路径记录
        path = LearningPath(
            user_id=user_id,
            topic=topic,
            domain_id=domain_id,
            status="processing",
            source="topic",
        )
        self.db.add(path)
        await self.db.flush()

        # 3. 写入知识图谱
        node_id_map = await self.kg.create_nodes_from_extraction(knowledge, path.id, domain_id)

        # 4. 生成大纲（直接从 extract_knowledge 的 modules 字段取，避免 LLM 格式不一致）
        modules = knowledge.get("modules", [])
        resolved_syllabus = self._resolve_syllabus_ids(modules, node_id_map)

        path.syllabus = resolved_syllabus
        path.status = "active"
        await self.db.flush()

        # 索引向量嵌入（后台静默执行）
        await self._index_path_embeddings(knowledge, node_id_map, path.id)

        return path

    async def process_topic_with_search(
        self, user_id: str, topic: str, domain_id: str
    ) -> LearningPath:
        """模式C：主题 → 自动搜索 → 交叉验证 → 生成学习路径（增强版）"""
        # 0. 自动检测领域
        if not domain_id or domain_id == "auto":
            detected = await self.llm.detect_domain(topic)
            domain_id = detected.get("domain", "general")

        # 1. 创建路径（初始状态 processing）
        path = LearningPath(
            user_id=user_id,
            topic=topic,
            domain_id=domain_id,
            status="processing",
            source="topic_search",
        )
        self.db.add(path)
        await self.db.flush()

        # 2. LLM 提取基础知识
        llm_knowledge = await self.llm.extract_knowledge(f"主题：{topic}", domain_id)

        # 3. 自动搜索相关主题
        search_topics = [topic]
        # 从 LLM 提取的节点标题中提取搜索关键词（取前 3 个）
        node_titles = [n.get("title", "") for n in llm_knowledge.get("nodes", [])[:3]]
        search_topics.extend(node_titles)

        search_results_map = await self.searcher.parallel_search(search_topics)
        all_results = []
        for resp in search_results_map.values():
            all_results.extend(resp.results)

        # 4. 交叉验证
        if all_results:
            enriched = await self.cross_validator.enrich_with_search(
                topic=topic,
                llm_knowledge=llm_knowledge,
                search_results=all_results,
                domain_id=domain_id,
            )
            # 只保留 LLM 交叉验证产生的 per-node 引用链接，不全局分配
        else:
            enriched = llm_knowledge

        # 5. 写入知识图谱
        node_id_map = await self.kg.create_nodes_from_extraction(enriched, path.id, domain_id)

        # 6. 生成大纲
        modules = enriched.get("modules", [])
        path.syllabus = self._resolve_syllabus_ids(modules, node_id_map)
        path.status = "active"
        await self.db.flush()

        # 索引向量嵌入
        await self._index_path_embeddings(enriched, node_id_map, path.id)

        return path

    async def _index_path_embeddings(self, knowledge: dict, node_id_map: dict[str, str], path_id: str):
        """为路径中所有节点生成向量索引（静默失败不影响主流程）"""
        try:
            searcher = SemanticSearchService()
            for node_data in knowledge.get("nodes", []):
                title = node_data.get("title", "")
                node_id = node_id_map.get(title)
                if not node_id:
                    continue
                text = f"{title}\n\n{node_data.get('summary', '')}\n\n{node_data.get('content', '')}"
                await searcher.index_node(self.db, node_id, path_id, text)
            await self.db.flush()
            print(f"  ✅ 已为 {len(node_id_map)} 个节点生成向量索引")
        except Exception as e:
            print(f"  ⚠️  向量索引生成跳过: {e}")

    async def process_upload(
        self, user_id: str, file_path: str, domain_id: str, topic: str | None = None
    ) -> LearningPath:
        """模式B：通过上传文件生成学习路径"""
        # 1. 提取文本（同步操作放入线程池避免阻塞事件循环）
        text = await asyncio.to_thread(self._extract_text, file_path)
        topic = topic or Path(file_path).stem

        # 2. LLM 提取知识点
        knowledge = await self.llm.extract_knowledge(text, domain_id)

        # 3. 创建路径
        path = LearningPath(
            user_id=user_id,
            topic=topic,
            domain_id=domain_id,
            status="processing",
            source="upload",
        )
        self.db.add(path)
        await self.db.flush()

        # 4. 写入图谱
        node_id_map = await self.kg.create_nodes_from_extraction(knowledge, path.id, domain_id)

        # 5. 生成大纲（直接从 extract_knowledge 的 modules 字段取）
        modules = knowledge.get("modules", [])
        path.syllabus = self._resolve_syllabus_ids(modules, node_id_map)
        path.status = "active"
        await self.db.flush()

        return path

    async def detect_domain(self, topic: str, text: str = "") -> str:
        """检测内容领域"""
        result = await self.llm.detect_domain(topic, text)
        return result.get("domain", "general")

    def _extract_text(self, file_path: str) -> str:
        """从文件提取文本"""
        ext = Path(file_path).suffix.lower()
        if ext == ".txt":
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                return f.read()
        elif ext == ".md":
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                return f.read()
        elif ext == ".pdf":
            return self._extract_pdf(file_path)
        elif ext == ".docx":
            return self._extract_docx(file_path)
        elif ext == ".pptx":
            return self._extract_pptx(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {ext}")

    @staticmethod
    def _extract_pdf(file_path: str) -> str:
        """提取 PDF 文本"""
        try:
            from unstructured.partition.pdf import partition_pdf

            elements = partition_pdf(filename=file_path)
            return "\n".join([str(e) for e in elements])
        except ImportError:
            raise ImportError("需要安装 unstructured[pdf]：pip install unstructured[pdf]") from None

    @staticmethod
    def _extract_docx(file_path: str) -> str:
        """提取 Word 文本"""
        try:
            from unstructured.partition.docx import partition_docx

            elements = partition_docx(filename=file_path)
            return "\n".join([str(e) for e in elements])
        except ImportError:
            raise ImportError("需要安装 unstructured[docx]：pip install unstructured[docx]") from None

    @staticmethod
    def _extract_pptx(file_path: str) -> str:
        """提取 PPT 文本"""
        try:
            from unstructured.partition.pptx import partition_pptx

            elements = partition_pptx(filename=file_path)
            return "\n".join([str(e) for e in elements])
        except ImportError:
            raise ImportError("需要安装 unstructured[pptx]：pip install unstructured[pptx]") from None

    @staticmethod
    def _resolve_syllabus_ids(syllabus: list, node_id_map: dict[str, str]) -> list[dict]:
        """将大纲中的标题替换为 Neo4j 节点 ID

        syllabus 可能来自 LLM，格式可能不统一：
          - [{"name": "...", "node_titles": [...]}, ...]  ← 标准
          - [{"module_name": "...", "node_ids": [...]}]    ← 替代
          - [[模块名, [节点1, 节点2]], ...]                 ← 非标准，需转换
        """
        resolved = []
        for module in syllabus:
            if isinstance(module, str):
                # LLM 返回了纯字符串，跳过
                continue
            if isinstance(module, (list, tuple)):
                # LLM 返回了数组格式 [模块名, [节点列表]]
                mod_name = str(module[0]) if len(module) > 0 else "未命名模块"
                node_titles = module[1] if len(module) > 1 and isinstance(module[1], list) else []
                resolved.append(
                    {
                        "module_name": mod_name,
                        "order": len(resolved) + 1,
                        "node_ids": [node_id_map.get(t, t) for t in node_titles if isinstance(t, str)],
                    }
                )
                continue
            # dict 格式
            mod_name = module.get("name") or module.get("module_name", f"模块{len(resolved) + 1}")
            node_titles = module.get("node_titles") or module.get("nodes") or module.get("node_ids", [])
            resolved.append(
                {
                    "module_name": mod_name,
                    "order": module.get("order", len(resolved) + 1),
                    "node_ids": [node_id_map.get(t, t) for t in node_titles if isinstance(t, str)],
                }
            )
        return resolved
