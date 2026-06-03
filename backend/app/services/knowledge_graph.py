"""知识图谱服务 —— Neo4j 操作封装"""

import uuid

from app.core.database import get_neo4j_driver


class KnowledgeGraphService:
    """知识图谱增删改查，所有 Cypher 查询封装在此"""

    async def __aenter__(self):
        self.driver = await get_neo4j_driver()
        return self

    async def __aexit__(self, *args):
        pass

    async def _run(self, query: str, params: dict = None) -> list:
        """执行 Cypher 查询"""
        driver = await get_neo4j_driver()
        async with driver.session() as session:
            result = await session.run(query, params or {})
            records = []
            async for record in result:
                records.append(record.data())
            return records

    # ── 节点操作 ──

    async def create_node(self, node_data: dict, path_id: str) -> str:
        """创建知识点节点，返回节点 ID"""
        node_id = node_data.get("id", str(uuid.uuid4()))
        query = """
        CREATE (n:KnowledgeNode {
          id: $id,
          title: $title,
          summary: $summary,
          content: $content,
          difficulty: $difficulty,
          domain_id: $domain_id,
          node_type: $node_type,
          examples: $examples,
          code_snippets: $code_snippets,
          ref_links: $ref_links,
          source: $source,
          confidence: $confidence,
          created_at: $created_at
        })
        RETURN n.id AS id
        """
        params = {
            "id": node_id,
            "title": node_data.get("title", ""),
            "summary": node_data.get("summary", ""),
            "content": node_data.get("content", ""),
            "difficulty": node_data.get("difficulty", "intro"),
            "domain_id": node_data.get("domain_id", "general"),
            "node_type": node_data.get("node_type", "concept"),
            "examples": node_data.get("examples", []),
            "code_snippets": node_data.get("code_snippets", []),
            "ref_links": node_data.get("ref_links", []),
            "source": node_data.get("source", "llm_generated"),
            "confidence": node_data.get("confidence", 0.8),
            "created_at": node_data.get("created_at", ""),
        }
        await self._run(query, params)

        # 关联到模块
        module_name = node_data.get("module_name", "默认模块")
        module_order = node_data.get("module_order", 1)
        await self._run(
            """
            MERGE (m:Module {name: $module_name, path_id: $path_id})
            ON CREATE SET m.order = $module_order
            WITH m
            MATCH (n:KnowledgeNode {id: $node_id})
            MERGE (n)-[:PART_OF]->(m)
            """,
            {
                "module_name": module_name,
                "module_order": module_order,
                "path_id": path_id,
                "node_id": node_id,
            },
        )

        return node_id

    async def create_nodes_from_extraction(self, knowledge: dict, path_id: str, domain_id: str) -> dict[str, str]:
        """从 LLM 提取结果批量创建节点，返回 {title: node_id} 映射"""
        title_to_id = {}

        # 1. 创建所有节点
        for _idx, node_data in enumerate(knowledge.get("nodes", [])):
            node_data["domain_id"] = domain_id
            node_data["source"] = "llm_generated"

            # 找出所属模块
            for module in knowledge.get("modules", []):
                if node_data["title"] in module.get("node_titles", []):
                    node_data["module_name"] = module.get("name", "默认模块")
                    node_data["module_order"] = module.get("order", 1)
                    break
            else:
                node_data["module_name"] = "默认模块"
                node_data["module_order"] = "99"

            node_id = await self.create_node(node_data, path_id)
            title_to_id[node_data["title"]] = node_id

        # 2. 创建节点间关系
        for rel in knowledge.get("relations", []):
            from_id = title_to_id.get(rel["from"])
            to_id = title_to_id.get(rel["to"])
            rel_type = rel.get("type", "PREREQUISITE")
            if from_id and to_id:
                await self.create_relation(from_id, to_id, rel_type)

        return title_to_id

    async def create_relation(self, from_node_id: str, to_node_id: str, rel_type: str, strength: int = 1):
        """创建节点间关系"""
        query = f"""
        MATCH (a:KnowledgeNode {{id: $from_id}})
        MATCH (b:KnowledgeNode {{id: $to_id}})
        MERGE (a)-[r:{rel_type}]->(b)
        """
        params = {"from_id": from_node_id, "to_id": to_node_id}
        if rel_type == "RELATED":
            query += " ON CREATE SET r.strength = $strength"
            params["strength"] = strength
        await self._run(query, params)

    # ── 查询操作 ──

    async def get_node(self, node_id: str) -> dict | None:
        """获取单个节点"""
        results = await self._run(
            "MATCH (n:KnowledgeNode {id: $id}) RETURN n",
            {"id": node_id},
        )
        if not results:
            return None
        node = results[0]["n"]
        return self._node_to_dict(node)

    async def get_path_nodes(self, path_id: str) -> list[dict]:
        """获取路径的所有节点"""
        results = await self._run(
            """
            MATCH (n:KnowledgeNode)-[:PART_OF]->(m:Module {path_id: $path_id})
            OPTIONAL MATCH (n)-[:PREREQUISITE]->(pre:KnowledgeNode)
            WITH n, m, collect(pre.id) AS prerequisites
            RETURN n, m, prerequisites
            ORDER BY m.order, n.difficulty
        """,
            {"path_id": path_id},
        )
        return [
            {
                "node": self._node_to_dict(r["n"]),
                "module": {"name": r["m"]["name"], "order": r["m"].get("order", 0)},
                "prerequisites": r["prerequisites"],
            }
            for r in results
        ]

    async def get_subgraph(self, node_id: str, depth: int = 2) -> dict:
        """获取以节点为中心的子图（用于图谱可视化）"""
        results = await self._run(
            """
            MATCH (n:KnowledgeNode {id: $node_id})
            OPTIONAL MATCH (n)-[:PREREQUISITE|RELATED|EXTENDS*1..2]-(related)
            RETURN n, collect(DISTINCT related) AS related_nodes
        """,
            {"node_id": node_id},
        )

        if not results:
            return {"nodes": [], "edges": []}

        data = results[0]
        all_nodes = {data["n"]["id"]: data["n"]}
        for rn in data["related_nodes"]:
            if rn and rn.get("id"):
                all_nodes[rn["id"]] = rn

        # 收集边
        edges = []
        node_ids = list(all_nodes.keys())
        for nid in node_ids:
            edge_results = await self._run(
                """
                MATCH (a:KnowledgeNode {id: $from_id})-[r]->(b:KnowledgeNode)
                WHERE b.id IN $node_ids
                RETURN a.id AS source, b.id AS target, type(r) AS type
            """,
                {"from_id": nid, "node_ids": node_ids},
            )
            edges.extend(edge_results)

        return {
            "nodes": [self._node_to_dict(n) for n in all_nodes.values()],
            "edges": edges,
        }

    async def get_prerequisites(self, node_id: str) -> list[dict]:
        """获取节点的所有前置节点"""
        results = await self._run(
            """
            MATCH (n:KnowledgeNode {id: $node_id})
            MATCH (pre)-[:PREREQUISITE*]->(n)
            RETURN DISTINCT pre
        """,
            {"node_id": node_id},
        )
        return [self._node_to_dict(r["pre"]) for r in results]

    async def get_related_nodes(self, node_id: str) -> list[dict]:
        """获取节点的关联节点"""
        results = await self._run(
            """
            MATCH (n:KnowledgeNode {id: $node_id})
            MATCH (n)-[:RELATED|EXTENDS]-(related)
            RETURN DISTINCT related
        """,
            {"node_id": node_id},
        )
        return [self._node_to_dict(r["related"]) for r in results]

    # ── 删除操作 ──

    async def delete_path_graph(self, path_id: str):
        """删除路径的所有节点和关系"""
        await self._run(
            """
            MATCH (n:KnowledgeNode)-[:PART_OF]->(m:Module {path_id: $path_id})
            DETACH DELETE n, m
        """,
            {"path_id": path_id},
        )

    async def delete_node(self, node_id: str):
        """删除单节点"""
        await self._run(
            "MATCH (n:KnowledgeNode {id: $id}) DETACH DELETE n",
            {"id": node_id},
        )

    # ── 工具方法 ──

    @staticmethod
    def _node_to_dict(n: dict) -> dict:
        """Neo4j Node → Python dict"""
        if n is None:
            return {}
        props = dict(n) if not hasattr(n, "items") else n
        return {
            "id": props.get("id", ""),
            "title": props.get("title", ""),
            "summary": props.get("summary", ""),
            "content": props.get("content", ""),
            "difficulty": props.get("difficulty", "intro"),
            "domain_id": props.get("domain_id", "general"),
            "node_type": props.get("node_type", "concept"),
            "examples": props.get("examples", []),
            "code_snippets": props.get("code_snippets", []),
        }

    async def module_summary(self, path_id: str) -> list[dict]:
        """获取路径的模块摘要"""
        results = await self._run(
            """
            MATCH (n:KnowledgeNode)-[:PART_OF]->(m:Module {path_id: $path_id})
            RETURN m.name AS module_name, m.order AS module_order, count(n) AS node_count
            ORDER BY m.order
        """,
            {"path_id": path_id},
        )
        return results
