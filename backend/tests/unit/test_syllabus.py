"""Syllabus 服务单元测试 —— 拓扑排序"""

import pytest
from app.services.syllabus import SyllabusService, CycleDetectedError


class TestTopologicalSort:
    """拓扑排序测试"""

    def test_simple_chain(self):
        """A → B → C 链式依赖"""
        nodes = [
            {"id": "a", "title": "A", "difficulty": "intro"},
            {"id": "b", "title": "B", "difficulty": "intro"},
            {"id": "c", "title": "C", "difficulty": "intro"},
        ]
        relations = [
            {"from": "a", "to": "b", "type": "PREREQUISITE"},
            {"from": "b", "to": "c", "type": "PREREQUISITE"},
        ]
        result = SyllabusService.topological_sort(nodes, relations)
        assert result == ["a", "b", "c"], f"期望 [a, b, c]，得到 {result}"

    def test_diamond_dependency(self):
        """A → B, A → C, B/C → D"""
        nodes = [
            {"id": "a", "title": "A", "difficulty": "intro"},
            {"id": "b", "title": "B", "difficulty": "intro"},
            {"id": "c", "title": "C", "difficulty": "intro"},
            {"id": "d", "title": "D", "difficulty": "intro"},
        ]
        relations = [
            {"from": "a", "to": "b", "type": "PREREQUISITE"},
            {"from": "a", "to": "c", "type": "PREREQUISITE"},
            {"from": "b", "to": "d", "type": "PREREQUISITE"},
            {"from": "c", "to": "d", "type": "PREREQUISITE"},
        ]
        result = SyllabusService.topological_sort(nodes, relations)
        # A 必须在 B/C 前，B/C 必须在 D 前
        assert result.index("a") < result.index("b")
        assert result.index("a") < result.index("c")
        assert result.index("b") < result.index("d")
        assert result.index("c") < result.index("d")

    def test_no_dependencies(self):
        """无依赖，按难度排序"""
        nodes = [
            {"id": "a", "title": "A", "difficulty": "advanced"},
            {"id": "b", "title": "B", "difficulty": "intro"},
            {"id": "c", "title": "C", "difficulty": "intermediate"},
        ]
        result = SyllabusService.topological_sort(nodes, [])
        # intro 在前
        assert result[0] == "b"

    def test_cycle_detection(self):
        """A → B → C → A 循环依赖"""
        nodes = [
            {"id": "a", "title": "A"},
            {"id": "b", "title": "B"},
            {"id": "c", "title": "C"},
        ]
        relations = [
            {"from": "a", "to": "b", "type": "PREREQUISITE"},
            {"from": "b", "to": "c", "type": "PREREQUISITE"},
            {"from": "c", "to": "a", "type": "PREREQUISITE"},
        ]
        with pytest.raises(CycleDetectedError):
            SyllabusService.topological_sort(nodes, relations)

    def test_single_node(self):
        """单节点"""
        nodes = [{"id": "a", "title": "A"}]
        result = SyllabusService.topological_sort(nodes, [])
        assert result == ["a"]

    def test_empty(self):
        """空列表"""
        result = SyllabusService.topological_sort([], [])
        assert result == []


class TestSyllabusGrouping:
    """模块分组测试"""

    def test_group_by_module(self):
        nodes_map = {
            "id1": {"title": "变量"},
            "id2": {"title": "数据类型"},
            "id3": {"title": "循环"},
        }
        module_configs = [
            {"name": "基础概念", "order": 1, "node_titles": ["变量", "数据类型"]},
            {"name": "流程控制", "order": 2, "node_titles": ["循环"]},
        ]
        result = SyllabusService.group_into_modules(
            ["id1", "id2", "id3"], nodes_map, module_configs
        )
        assert len(result) == 2
        assert result[0]["module_name"] == "基础概念"
        assert result[0]["node_ids"] == ["id1", "id2"]
        assert result[1]["module_name"] == "流程控制"
        assert result[1]["node_ids"] == ["id3"]
