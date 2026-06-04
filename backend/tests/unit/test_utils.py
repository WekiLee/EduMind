"""知识图谱工具 + 内容管道 + 领域配置 + LLM 工具方法单元测试"""

import pytest

from app.services.content_pipeline import ContentPipelineService
from app.services.domain_profile import load_domain_profile
from app.services.knowledge_graph import KnowledgeGraphService
from app.llm.adapter import LLMAdapter


# ──────────────────────────────────────────
# 知识图谱工具方法
# ──────────────────────────────────────────


class TestNodeToDict:
    """KnowledgeGraphService._node_to_dict 测试"""

    def test_standard_node(self):
        node = {"id": "n1", "title": "变量", "content": "变量是...", "difficulty": "intro"}
        result = KnowledgeGraphService._node_to_dict(node)
        assert result["id"] == "n1"
        assert result["title"] == "变量"
        assert result["difficulty"] == "intro"
        assert result["examples"] == []
        assert result["confidence"] == 0.8
        assert result["sources"] == ["llm_generated"]
        assert result["ref_links"] == []

    def test_none_node(self):
        result = KnowledgeGraphService._node_to_dict(None)
        assert result == {}

    def test_empty_node(self):
        result = KnowledgeGraphService._node_to_dict({})
        assert result["id"] == ""
        assert result["examples"] == []


# ──────────────────────────────────────────
# 内容管道工具方法
# ──────────────────────────────────────────


class TestResolveSyllabusIds:
    """ContentPipelineService._resolve_syllabus_ids 测试"""

    def test_standard_dict_format(self):
        syllabus = [
            {"name": "模块1", "node_titles": ["变量", "类型"]},
            {"name": "模块2", "node_titles": ["循环"]},
        ]
        node_id_map = {"变量": "id1", "类型": "id2", "循环": "id3"}
        result = ContentPipelineService._resolve_syllabus_ids(syllabus, node_id_map)
        assert len(result) == 2
        assert result[0]["module_name"] == "模块1"
        assert result[0]["node_ids"] == ["id1", "id2"]
        assert result[1]["module_name"] == "模块2"
        assert result[1]["node_ids"] == ["id3"]

    def test_alternative_module_name_key(self):
        syllabus = [{"module_name": "模块1", "node_ids": ["id_a"]}]
        result = ContentPipelineService._resolve_syllabus_ids(syllabus, {})
        assert result[0]["module_name"] == "模块1"

    def test_list_tuple_format(self):
        syllabus = [("模块1", ["变量", "类型"])]
        node_id_map = {"变量": "id1", "类型": "id2"}
        result = ContentPipelineService._resolve_syllabus_ids(syllabus, node_id_map)
        assert result[0]["module_name"] == "模块1"
        assert result[0]["node_ids"] == ["id1", "id2"]

    def test_string_entry_skipped(self):
        syllabus = ["纯字符串（LLM 格式错误）", {"name": "模块1", "node_titles": ["变量"]}]
        node_id_map = {"变量": "id1"}
        result = ContentPipelineService._resolve_syllabus_ids(syllabus, node_id_map)
        assert len(result) == 1

    def test_none_title_filtered(self):
        """node_titles 中包含 None 应被过滤"""
        syllabus = [{"name": "模块1", "node_titles": ["变量", None]}]
        node_id_map = {"变量": "id1"}
        result = ContentPipelineService._resolve_syllabus_ids(syllabus, node_id_map)
        assert result[0]["node_ids"] == ["id1"]

    def test_missing_map_title_preserved(self):
        syllabus = [{"name": "模块1", "node_titles": ["变量", "不存在的节点"]}]
        node_id_map = {"变量": "id1"}
        result = ContentPipelineService._resolve_syllabus_ids(syllabus, node_id_map)
        assert "不存在的节点" in result[0]["node_ids"]

    def test_empty_syllabus(self):
        result = ContentPipelineService._resolve_syllabus_ids([], {})
        assert result == []


# ──────────────────────────────────────────
# 领域配置加载
# ──────────────────────────────────────────


class TestLoadDomainProfile:
    """load_domain_profile 测试"""

    def test_general_profile_exists(self):
        profile = load_domain_profile("general")
        assert profile is not None
        assert "domain" in profile
        assert profile["domain"]["id"] == "general"

    def test_unknown_domain_falls_back_to_general(self):
        profile = load_domain_profile("non_existent_domain_xyz")
        assert profile is not None
        assert profile["domain"]["id"] == "general"

    def test_math_profile(self):
        profile = load_domain_profile("math")
        assert profile["domain"]["id"] == "math"
        assert profile["domain"]["graph_structure"]["type"] == "strict_dag"


# ──────────────────────────────────────────
# LLM 适配器工具方法
# ──────────────────────────────────────────


class TestTrimContext:
    """LLMAdapter.trim_context 测试"""

    def test_empty_messages(self):
        result = LLMAdapter.trim_context([])
        assert result == []

    def test_below_max_tokens(self):
        messages = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！有什么可以帮助你的？"},
        ]
        result = LLMAdapter.trim_context(messages, max_tokens=5000)
        assert len(result) == 2

    def test_system_message_preserved(self):
        messages = [
            {"role": "system", "content": "你是老师"},
            {"role": "user", "content": "你好" * 2000},  # 超长
            {"role": "assistant", "content": "你好" * 2000},  # 超长
        ]
        result = LLMAdapter.trim_context(messages, max_tokens=100)
        assert any(m["role"] == "system" for m in result)


class TestNeedSummary:
    """LLMAdapter.need_summary 测试"""

    def test_below_threshold(self):
        messages = [{"role": "user", "content": "hi"}] * 5
        assert LLMAdapter.need_summary(messages) is False

    def test_above_threshold(self):
        messages = [{"role": "user", "content": "hi"}] * 15
        assert LLMAdapter.need_summary(messages) is True

    def test_system_not_counted(self):
        messages = [{"role": "system", "content": "sys"}] + [{"role": "user", "content": "hi"}] * 10
        assert LLMAdapter.need_summary(messages) is False  # 只有 10 条对话消息


class TestLearnerToInstruction:
    """LLMAdapter._learner_to_instruction 测试"""

    def test_default_profile(self):
        result = LLMAdapter._learner_to_instruction({"abstraction_level": 0.5, "analogy_density": 0.5, "teaching_speed": 0.5, "feedback_tone": 0.5})
        assert "教学风格要求：" in result

    def test_high_abstraction(self):
        result = LLMAdapter._learner_to_instruction({"abstraction_level": 0.9, "analogy_density": 0.5, "teaching_speed": 0.5, "feedback_tone": 0.5})
        assert "专业术语" in result

    def test_low_abstraction(self):
        result = LLMAdapter._learner_to_instruction({"abstraction_level": 0.1, "analogy_density": 0.5, "teaching_speed": 0.5, "feedback_tone": 0.5})
        assert "具体事物" in result

    def test_empty_profile(self):
        result = LLMAdapter._learner_to_instruction({})
        assert result == ""


class TestParseJson:
    """LLMAdapter._parse_json 测试"""

    def test_plain_json(self):
        result = LLMAdapter._parse_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_with_markdown_fence(self):
        result = LLMAdapter._parse_json('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_json_without_lang_tag(self):
        result = LLMAdapter._parse_json('```\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_invalid_json_raises(self):
        with pytest.raises(Exception):
            LLMAdapter._parse_json("这不是 JSON")


# ──────────────────────────────────────────
# 搜索编排器
# ──────────────────────────────────────────


class TestSearchOrchestrator:
    """SearchOrchestrator 单元测试"""

    async def test_search_disabled(self):
        """search_provider=none 时返回空结果"""
        from app.services.search_orchestrator import SearchOrchestrator

        # 临时修改配置
        import app.core.config as config_mod
        original = config_mod.settings.search_provider
        config_mod.settings.search_provider = "none"

        try:
            orch = SearchOrchestrator()
            resp = await orch.search("test")
            assert resp.results == []
        finally:
            config_mod.settings.search_provider = original

    async def test_search_unknown_provider(self):
        """未知 provider 降级返回空"""
        from app.services.search_orchestrator import SearchOrchestrator

        import app.core.config as config_mod
        original = config_mod.settings.search_provider
        config_mod.settings.search_provider = "unknown_provider"

        try:
            orch = SearchOrchestrator()
            resp = await orch.search("test")
            assert resp.results == []
            assert resp.error is not None
        finally:
            config_mod.settings.search_provider = original

    def test_search_result_dataclass(self):
        """SearchResult 数据结构正确"""
        from app.services.search_orchestrator import SearchResult

        r = SearchResult(title="标题", snippet="摘要", url="https://example.com", source="web")
        assert r.title == "标题"
        assert r.snippet == "摘要"
        assert r.url == "https://example.com"
        assert r.source == "web"

    async def test_parallel_search_with_empty(self):
        """并发搜索空列表返回空字典"""
        from app.services.search_orchestrator import SearchOrchestrator

        import app.core.config as config_mod
        original = config_mod.settings.search_provider
        config_mod.settings.search_provider = "none"

        try:
            orch = SearchOrchestrator()
            results = await orch.parallel_search([])
            assert results == {}
        finally:
            config_mod.settings.search_provider = original

    async def test_search_empty_query(self):
        """空查询直接返回空结果，不请求外部 API"""
        from app.services.search_orchestrator import SearchOrchestrator

        import app.core.config as config_mod
        original = config_mod.settings.search_provider
        config_mod.settings.search_provider = "duckduckgo"

        try:
            orch = SearchOrchestrator()
            resp = await orch.search("")
            assert resp.results == []
            assert resp.query == ""
        finally:
            config_mod.settings.search_provider = original


class TestCrossValidation:
    """CrossValidationService 单元测试"""

    def test_add_default_confidence(self):
        from app.services.cross_validation import CrossValidationService

        knowledge = {
            "nodes": [
                {"title": "变量", "content": "变量是..."},
                {"title": "循环", "content": "循环是..."},
            ],
            "relations": [],
            "modules": [],
        }
        result = CrossValidationService._add_default_confidence(knowledge)
        for node in result["nodes"]:
            assert node["confidence"] == 0.8
            assert node["sources"] == ["llm_generated"]

    def test_add_default_confidence_empty(self):
        from app.services.cross_validation import CrossValidationService

        result = CrossValidationService._add_default_confidence({"nodes": []})
        assert result["nodes"] == []

    async def test_enrich_without_search_results(self):
        """无搜索结果时原样返回"""
        from app.services.cross_validation import CrossValidationService

        svc = CrossValidationService()
        knowledge = {
            "nodes": [{"title": "A", "content": "A的内容"}],
            "relations": [],
            "modules": [{"name": "模块1", "order": 1, "node_titles": ["A"]}],
        }
        result = await svc.enrich_with_search("测试", knowledge, [], "general")
        # 内容应保留
        assert result["nodes"][0]["title"] == "A"
        assert result["nodes"][0]["confidence"] == 0.8
        assert result["nodes"][0]["sources"] == ["llm_generated"]
