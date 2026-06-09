"""MCP 客户端 —— 管理外部 MCP Server 连接 + 内置工具"""

import json
import subprocess
from typing import Any

from app.core.config import settings


# ── 内置工具（直接调用本地服务，无需外部进程）──


async def _builtin_search(query: str, max_results: int = 5) -> str:
    """内置搜索工具：通过 SearchOrchestrator 搜索网络"""
    from app.services.search_orchestrator import SearchOrchestrator

    orch = SearchOrchestrator()
    resp = await orch.search(query, max_results)
    if not resp.results:
        return "未找到相关结果"
    parts = []
    for r in resp.results[:max_results]:
        parts.append(f"- [{r.title}]({r.url}): {r.snippet[:200]}")
    return "\n".join(parts)


async def _builtin_knowledge(node_id: str, action: str = "get") -> str:
    """内置知识图谱工具：查询节点信息"""
    from app.services.knowledge_graph import KnowledgeGraphService

    kg = KnowledgeGraphService()
    if action == "get":
        node = await kg.get_node(node_id)
        if not node:
            return f"节点 {node_id} 不存在"
        return f"**{node.get('title', '')}**\n\n{node.get('content', '')[:500]}"
    elif action == "related":
        related = await kg.get_related_nodes(node_id)
        if not related:
            return "无关联节点"
        return "\n".join(f"- {n.get('title', n.get('id', ''))}" for n in related[:5])
    elif action == "prerequisites":
        prereqs = await kg.get_prerequisites(node_id)
        if not prereqs:
            return "无前置节点"
        return "\n".join(f"- {n.get('title', n.get('id', ''))}" for n in prereqs[:5])
    return f"不支持的操作: {action}"


_BUILTIN_TOOLS: dict[str, dict] = {
    "core-search": {
        "name": "core-search",
        "description": "搜索网络获取最新信息。参数: query(搜索关键词), max_results(返回条数,默认5)",
        "handler": _builtin_search,
    },
    "core-knowledge": {
        "name": "core-knowledge",
        "description": "查询知识图谱节点信息。参数: node_id(节点ID), action(get|related|prerequisites)",
        "handler": _builtin_knowledge,
    },
}


# ── 外部 MCP Server 管理（stdio 协议）──


class MCPClientManager:
    """MCP 客户端管理器：启动/停止外部 MCP Server 进程，调用工具"""

    def __init__(self):
        self._servers: dict[str, Any] = {}  # name -> subprocess / state
        self._parsed_config: list[dict] = []
        self._parse_config()

    def _parse_config(self):
        """从 settings 解析 MCP Server 配置"""
        if not settings.mcp_enabled or not settings.mcp_servers:
            self._parsed_config = []
            return
        try:
            self._parsed_config = json.loads(settings.mcp_servers)
        except (json.JSONDecodeError, TypeError):
            self._parsed_config = []

    def get_all_tools(self) -> list[dict]:
        """获取所有可用工具列表（内置 + 外部）"""
        tools = list(_BUILTIN_TOOLS.values())
        for cfg in self._parsed_config:
            tools.append({
                "name": cfg.get("name", "unknown"),
                "description": f"MCP 服务器: {cfg.get('name', 'unknown')}。命令: {' '.join(cfg.get('args', []))}",
                "handler": None,  # 外部工具调用时临时连接
            })
        return tools

    def get_tool_descriptions(self) -> str:
        """获取工具描述文本（嵌入 LLM 系统提示用）"""
        tools = self.get_all_tools()
        if not tools:
            return ""
        parts = ["可用工具："]
        for t in tools:
            parts.append(f"- **{t['name']}**: {t['description']}")
        parts.append("\n如需使用工具，在回答中单独一行写 TOOL_CALL: {{'tool': '工具名', 'args': {{...}}}}")
        parts.append("执行结果会追加到下一轮对话中。")
        return "\n".join(parts)

    async def call_tool(self, tool_name: str, args: dict) -> str:
        """调用工具（内置或外部），返回结果文本"""
        # 1. 先查内置工具
        if tool_name in _BUILTIN_TOOLS:
            tool = _BUILTIN_TOOLS[tool_name]
            return await tool["handler"](**args)

        # 2. 外部 MCP Server
        cfg = next((c for c in self._parsed_config if c.get("name") == tool_name), None)
        if not cfg:
            return f"⚠️ 工具 {tool_name} 未找到"

        return await self._call_external_tool(cfg, args)

    async def _call_external_tool(self, cfg: dict, args: dict) -> str:
        """通过 stdio 协议调用外部 MCP Server（暂未实现完整的 MCP 协议握手）"""
        command = cfg.get("command", "")
        cmd_args = cfg.get("args", [])

        # 简单模式：将参数作为环境变量传递给命令
        env = {f"MCP_ARG_{k.upper()}": str(v) for k, v in args.items()}
        try:
            result = subprocess.run(
                [command, *cmd_args],
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
            )
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            if stdout:
                return stdout[:1000]
            if stderr:
                return f"⚠️ 工具返回: {stderr[:300]}"
            return "⚠️ 工具无输出"
        except subprocess.TimeoutExpired:
            return "⚠️ 工具调用超时(30s)"
        except FileNotFoundError:
            return f"⚠️ 命令不存在: {command}"
        except Exception as e:
            return f"⚠️ 工具调用失败: {e}"


# 全局单例
_mcp_manager: MCPClientManager | None = None


def get_mcp_manager() -> MCPClientManager:
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPClientManager()
    return _mcp_manager
