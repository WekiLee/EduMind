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
