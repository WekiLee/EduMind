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

    def test_empty_profile_uses_defaults(self):
        """空 profile 应使用默认嵌套结构，不再返回空字符串"""
        result = LLMAdapter._learner_to_instruction({})
        assert "教学风格要求：" in result
        assert "容错率较高" in result  # 默认 tolerance=0.7

    def test_nested_profile(self):
        """嵌套结构也能正确处理"""
        result = LLMAdapter._learner_to_instruction({
            "content": {"abstraction_level": 0.1, "analogy_density": 0.1, "example_style": 0.1},
            "pace": {"teaching_speed": 0.1, "session_duration_min": 15, "repetition_preference": 0.1},
        })
        assert "具体事物" in result
        assert "15 分钟" in result

    def test_example_style_field(self):
        """新字段 example_style 生效"""
        low = LLMAdapter._learner_to_instruction({"content": {"example_style": 0.1}})
        assert "日常生活" in low

        high = LLMAdapter._learner_to_instruction({"content": {"example_style": 0.9}})
        assert "专业领域" in high

    def test_error_handling_field(self):
        """新字段 error_handling 生效"""
        guided = LLMAdapter._learner_to_instruction({"interaction": {"error_handling": 0.1}})
        assert "提示引导" in guided

        direct = LLMAdapter._learner_to_instruction({"interaction": {"error_handling": 0.9}})
        assert "直接指出" in direct

    def test_interrupt_policy_field(self):
        """新字段 interrupt_policy 生效"""
        result = LLMAdapter._learner_to_instruction({"interaction": {"interrupt_policy": "after_segment"}})
        assert "不要中途打断" in result

    def test_enable_tts_field(self):
        """新字段 enable_tts 生效"""
        result = LLMAdapter._learner_to_instruction({"ui": {"enable_tts": True}})
        assert "语音播报" in result


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


# ──────────────────────────────────────────
# 学习者画像归一化
# ──────────────────────────────────────────


class TestLearnerProfileNormalize:
    """learner_profile.normalize 测试"""

    def test_none_returns_default(self):
        from app.services.learner_profile import normalize

        result = normalize(None)
        assert result["content"]["abstraction_level"] == 0.5
        assert result["pace"]["session_duration_min"] == 25
        assert result["ui"]["enable_tts"] is False

    def test_empty_dict_returns_default(self):
        from app.services.learner_profile import normalize

        result = normalize({})
        assert result["content"]["abstraction_level"] == 0.5

    def test_flat_format_migrated(self):
        """旧版扁平格式应正确迁移"""
        from app.services.learner_profile import normalize

        result = normalize({
            "abstraction_level": 0.3,
            "analogy_density": 0.8,
            "teaching_speed": 0.2,
            "feedback_tone": 0.1,
            "quiz_style": 0.9,
        })
        assert result["content"]["abstraction_level"] == 0.3
        assert result["content"]["analogy_density"] == 0.8
        assert result["pace"]["teaching_speed"] == 0.2
        assert result["interaction"]["feedback_tone"] == 0.1
        assert result["assessment"]["quiz_style"] == 0.9
        # 未提供的字段保留默认值
        assert result["content"]["example_style"] == 0.5

    def test_nested_format_preserved(self):
        from app.services.learner_profile import normalize

        result = normalize({
            "content": {"abstraction_level": 0.9, "analogy_density": 0.1},
            "assessment": {"tolerance": 0.9},
        })
        assert result["content"]["abstraction_level"] == 0.9
        assert result["content"]["analogy_density"] == 0.1
        # 未提供的嵌套字段保留默认值
        assert result["content"]["example_style"] == 0.5
        assert result["assessment"]["tolerance"] == 0.9
        assert result["assessment"]["quiz_style"] == 0.5
        # 未提供的组保留默认值
        assert result["ui"]["font_size"] == "medium"

    def test_all_groups_present(self):
        from app.services.learner_profile import normalize

        result = normalize(None)
        assert set(result.keys()) == {"content", "pace", "interaction", "assessment", "ui"}


class TestLearnerProfileRead:
    """learner_profile.read 测试"""

    def test_read_nested_field(self):
        from app.services.learner_profile import read

        val = read({"content": {"abstraction_level": 0.9}}, "content", "abstraction_level")
        assert val == 0.9

    def test_read_flat_field(self):
        """从扁平 profile 也能正确读取"""
        from app.services.learner_profile import read

        val = read({"abstraction_level": 0.3}, "content", "abstraction_level")
        assert val == 0.3

    def test_read_none_profile(self):
        from app.services.learner_profile import read

        val = read(None, "content", "abstraction_level")
        assert val == 0.5

    def test_read_missing_field_returns_default(self):
        from app.services.learner_profile import read

        val = read({}, "ui", "font_size")
        assert val == "medium"
