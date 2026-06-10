"""管理员节点删除辅助逻辑测试。"""

from app.api.admin import remove_node_from_mastery_snapshot, remove_node_from_syllabus


def test_remove_node_from_syllabus_removes_references():
    """删除节点时应从所有模块大纲中移除引用。"""
    syllabus = [
        {"module_name": "基础", "node_ids": ["n1", "n2"]},
        {"module_name": "进阶", "node_ids": ["n2", "n3"]},
    ]

    cleaned, changed = remove_node_from_syllabus(syllabus, "n2")

    assert changed is True
    assert cleaned == [
        {"module_name": "基础", "node_ids": ["n1"]},
        {"module_name": "进阶", "node_ids": ["n3"]},
    ]


def test_remove_node_from_syllabus_keeps_unchanged_content():
    """不存在目标节点时应保持原大纲语义不变。"""
    syllabus = [{"module_name": "基础", "node_ids": ["n1"]}]

    cleaned, changed = remove_node_from_syllabus(syllabus, "missing")

    assert changed is False
    assert cleaned == syllabus


def test_remove_node_from_mastery_snapshot_recalculates_summary():
    """删除节点时应同步修正掌握度快照聚合字段。"""
    snapshot = {
        "overall_mastery": 0.5,
        "completed_nodes": 1,
        "total_nodes": 2,
        "nodes": [
            {"node_id": "n1", "mastery": 0.8, "status": "completed"},
            {"node_id": "n2", "mastery": 0.2, "status": "learning"},
        ],
    }

    cleaned, changed = remove_node_from_mastery_snapshot(snapshot, "n2")

    assert changed is True
    assert cleaned["total_nodes"] == 1
    assert cleaned["completed_nodes"] == 1
    assert cleaned["overall_mastery"] == 0.8
    assert cleaned["nodes"] == [{"node_id": "n1", "mastery": 0.8, "status": "completed"}]
