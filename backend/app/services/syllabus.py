"""大纲生成器 —— 拓扑排序 + 模块分组"""

from typing import List


class CycleDetectedError(Exception):
    """检测到循环依赖"""
    pass


class SyllabusService:
    """大纲生成：拓扑排序保证依赖顺序 + 模块化分组"""

    @staticmethod
    def topological_sort(nodes: list[dict], relations: list[dict]) -> list[str]:
        """
        拓扑排序，返回排序后的节点 ID 列表。
        nodes: [{"id": "...", "title": "...", ...}]
        relations: [{"from": "idA", "to": "idB", "type": "PREREQUISITE"}]
        """
        # 构建邻接表 + 入度表
        graph = {}
        in_degree = {}

        for node in nodes:
            nid = node["id"]
            graph[nid] = []
            in_degree[nid] = 0

        for rel in relations:
            if rel.get("type") != "PREREQUISITE":
                continue
            from_id = rel["from"]
            to_id = rel["to"]
            if from_id in graph and to_id in graph:
                graph[from_id].append(to_id)
                in_degree[to_id] = in_degree.get(to_id, 0) + 1

        # Kahn 算法
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        sorted_ids = []

        while queue:
            # 按难度排序同级节点（intro 优先）
            node_map = {n["id"]: n for n in nodes}
            queue.sort(key=lambda nid: _difficulty_order(node_map.get(nid, {}).get("difficulty", "intro")))
            current = queue.pop(0)
            sorted_ids.append(current)

            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(sorted_ids) != len(nodes):
            raise CycleDetectedError("检测到循环依赖，请检查知识点前置关系")

        return sorted_ids

    @staticmethod
    def group_into_modules(node_ids: list[str], nodes_map: dict[str, dict], module_configs: list[dict]) -> list[dict]:
        """
        将排序后的节点分组到模块中。
        module_configs: [{"name": "基础", "node_titles": ["变量", "类型"]}]
        映射为 ID 后的大纲格式。
        """
        syllabus = []
        seen = set()

        for cfg in module_configs:
            module_nodes = []
            for title in cfg.get("node_titles", []):
                # 查找标题对应的 ID
                for nid, node in nodes_map.items():
                    if node.get("title") == title and nid not in seen:
                        module_nodes.append(nid)
                        seen.add(nid)
                        break

            if module_nodes or cfg.get("name"):
                syllabus.append({
                    "module_name": cfg.get("name", "默认模块"),
                    "order": cfg.get("order", len(syllabus) + 1),
                    "node_ids": module_nodes,
                })

        # 处理未分组的节点
        remaining = [nid for nid in node_ids if nid not in seen]
        if remaining:
            syllabus.append({
                "module_name": "其他",
                "order": len(syllabus) + 1,
                "node_ids": remaining,
            })

        return syllabus

    @staticmethod
    def reorder_syllabus(syllabus: list[dict], new_order: list[str]) -> list[dict]:
        """
        用户拖拽调整顺序后，重新排列大纲。
        new_order: 用户排序后的节点 ID 列表
        """
        # 保留模块结构，但调整内部节点顺序
        node_to_module = {}
        for module in syllabus:
            for nid in module.get("node_ids", []):
                node_to_module[nid] = module["module_name"]

        # 重新分配节点到模块
        module_map = {m["module_name"]: {**m, "node_ids": []} for m in syllabus}
        for nid in new_order:
            mod_name = node_to_module.get(nid, list(module_map.keys())[0] if module_map else "其他")
            if mod_name in module_map:
                module_map[mod_name]["node_ids"].append(nid)

        return [v for v in module_map.values() if v["node_ids"]]


def _difficulty_order(difficulty: str) -> int:
    """难度排序权重"""
    return {"intro": 0, "intermediate": 1, "advanced": 2}.get(difficulty, 0)
