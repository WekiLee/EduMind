"""LLM 适配器 —— 统一接口 + Token 感知上下文裁剪 + 响应缓存 + MCP 工具"""

import hashlib
import json
import time
from collections.abc import AsyncGenerator

import litellm
from litellm import acompletion

litellm.request_timeout = 30  # LLM 调用超时 30 秒

from app.core.config import settings
from app.services.learner_profile import normalize as normalize_profile


class LLMAdapter:
    """
    LLM 适配器，支持 Ollama / OpenAI-compatible 等 Provider。

    配置优先级（由高到低）：
      1. 管理员在 Web UI 中设置的运行时配置（SystemConfig）
      2. .env 文件中的配置（仅当运行时配置为空时）
    """

    # 类级缓存（进程内，所有实例共享）
    _response_cache: dict[str, tuple[str, float]] = {}
    _domain_profile_cache: dict[str, dict] = {}
    # 运行时配置（管理员通过 Web UI 设置，重启后从 DB 加载）
    _runtime_provider: str | None = None
    _runtime_model: str | None = None
    _runtime_api_key: str | None = None
    _runtime_api_base: str | None = None

    def __init__(self):
        # 优先使用运行时配置（管理员 Web 设置），其次 .env
        self.provider = self._runtime_provider or settings.llm_provider
        self.model = self._runtime_model or settings.llm_model
        self._setup_provider()

    @classmethod
    def update_runtime_config(cls, provider: str = None, model: str = None, api_key: str = None, api_base: str = None):
        """由管理员 API 调用，动态更新 LLM 配置"""
        if provider:
            cls._runtime_provider = provider
        if model:
            cls._runtime_model = model
        if api_key:
            cls._runtime_api_key = api_key
        if api_base:
            cls._runtime_api_base = api_base

    def with_user_config(self, model_config: dict | None) -> "LLMAdapter":
        """返回一个使用用户级模型配置的 LLMAdapter 副本"""
        if not model_config:
            return self
        import copy
        clone = copy.copy(self)
        if model_config.get("provider"):
            clone.provider = model_config["provider"]
        if model_config.get("model"):
            clone.model = model_config["model"]
        if model_config.get("api_base"):
            clone.api_base = model_config["api_base"]
        if model_config.get("api_key"):
            clone.api_key = model_config["api_key"]
        clone._setup_provider()
        return clone

    def _setup_provider(self):
        if self.provider == "ollama":
            self.api_base = self._runtime_api_base or settings.ollama_base_url
            self.model_name = f"ollama/{self.model}"
        elif self.provider == "openai-compatible":
            self.api_base = self._runtime_api_base or settings.openai_base_url
            self.model_name = f"openai/{self.model}"
        else:
            raise ValueError(f"不支持的 Provider: {self.provider}")
        self.api_key = self._runtime_api_key or settings.openai_api_key

    # ──────────────────────────────────────────
    # 核心 Chat 接口（带缓存）
    # ──────────────────────────────────────────

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        use_cache: bool = False,
    ) -> str | AsyncGenerator[str, None]:
        """
        统一的 chat 接口。

        use_cache=True 时，相同 messages + temperature 组合命中缓存直接返回。
        适用于出题、知识提取等确定性高的调用。
        教学对话中建议 use_cache=False（每次回答应不同）。
        """
        if use_cache:
            cache_key = self._cache_key(messages, temperature)
            cached = self._get_cached(cache_key)
            if cached:
                return cached

        kwargs = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if self.api_base:
            kwargs["api_base"] = self.api_base
        if self.api_key:
            kwargs["api_key"] = self.api_key

        response = await acompletion(**kwargs)

        if stream:
            return self._stream_response(response)

        result = response.choices[0].message.content or ""

        if not result.strip():
            print("  ⚠️  LLM 返回空内容，可检查 API Key 额度或网络")
            result = ""

        if use_cache:
            self._set_cache(cache_key, result)

        return result

    async def stream_chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """流式 chat 的便捷方法"""
        stream_gen = await self.chat(messages, temperature=temperature, stream=True)
        full = ""
        async for chunk in stream_gen:
            full += chunk
            yield chunk

    # ──────────────────────────────────────────
    # 上下文裁剪（Token 感知）
    # ──────────────────────────────────────────

    @staticmethod
    def trim_context(
        messages: list[dict],
        max_tokens: int = settings.context_max_tokens,
        reserve_recent: int = settings.context_recent_messages,
    ) -> list[dict]:
        """
        裁剪对话历史，保证总 token 不超过 max_tokens。

        策略：
        1. System prompt 始终保留
        2. 最近 reserve_recent 条消息始终保留
        3. 从最早的非 system 消息开始丢弃，直到 token 数达标
        """
        if not messages:
            return messages

        # 分离 system 和 对话消息
        system_msgs = [m for m in messages if m.get("role") == "system"]
        conversation = [m for m in messages if m.get("role") != "system"]

        # 粗略估算 token 数（中英文混合按 1.5 字/token）
        def estimate_tokens(text: str) -> int:
            return int(len(text) / 1.5) + 1

        def total_tokens(msg_list: list[dict]) -> int:
            return sum(estimate_tokens(m.get("content", "")) for m in msg_list)

        # 如果全部消息也不超限，直接返回
        if total_tokens(system_msgs + conversation) <= max_tokens:
            return messages

        # 保留最近的 reserve_recent 条
        if len(conversation) <= reserve_recent:
            return system_msgs + conversation  # 太少就不裁了

        recent = conversation[-reserve_recent:]
        early = conversation[:-reserve_recent]

        # 从最早的开始丢弃，直到 token 达标
        while early and total_tokens(system_msgs + early + recent) > max_tokens:
            early.pop(0)

        return system_msgs + early + recent

    @staticmethod
    def need_summary(messages: list[dict], threshold: int = settings.context_summary_threshold) -> bool:
        """判断是否需要触发上下文摘要"""
        conversation = [m for m in messages if m.get("role") != "system"]
        return len(conversation) >= threshold

    @staticmethod
    def build_summary_prompt(messages: list[dict]) -> str:
        """构建上下文摘要的 prompt"""
        return (
            "以下是当前教学对话的历史记录，请用 100 字以内概括已讨论的内容、"
            "学生的掌握情况以及仍有疑问的知识点：\n\n"
            + "\n".join(f"{'学生' if m['role'] == 'user' else '老师'}：{m['content'][:200]}" for m in messages[-10:])
        )

    # ──────────────────────────────────────────
    # 业务方法（内置上下文管理）
    # ──────────────────────────────────────────

    async def teach_concept(
        self,
        node: dict,
        domain_profile: dict,
        learner_profile: dict,
        chat_history: list[dict] = None,
    ) -> str:
        """教学讲解（带上下文裁剪）"""
        prompt_template = domain_profile.get("prompt_overrides", {}).get("teach_concept", "请讲解以下知识点。")
        learner_style = self._learner_to_instruction(learner_profile)

        messages = [
            {"role": "system", "content": f"{prompt_template}\n\n{learner_style}"},
        ]
        if chat_history:
            trimmed = self.trim_context(chat_history)
            messages.extend(trimmed)

        messages.append(
            {
                "role": "user",
                "content": f"知识点：{node.get('title')}\n\n{node.get('content', '')}",
            }
        )

        return await self.chat(messages, temperature=0.7, max_tokens=4096)

    async def answer_question(
        self,
        question: str,
        node: dict,
        domain_profile: dict,
        learner_profile: dict,
        chat_history: list[dict],
    ) -> str:
        """回答学生提问（带上下文裁剪）"""
        learner_style = self._learner_to_instruction(learner_profile)
        profile_prompt = domain_profile.get("prompt_overrides", {}).get("handle_question", "")

        system_content = f"你是一位耐心的老师。当前讲解的知识点是：{node.get('title')}\n\n{learner_style}"
        if profile_prompt:
            system_content += f"\n\n{profile_prompt}"

        messages = [{"role": "system", "content": system_content}]

        if chat_history:
            trimmed = self.trim_context(chat_history)
            messages.extend(trimmed)

        # 如果上下文已包含该问题（重复发送），不重复追加
        if not chat_history or chat_history[-1].get("content") != question:
            messages.append({"role": "user", "content": question})

        return await self.chat(messages, temperature=0.7, max_tokens=4096)

    async def answer_with_tools(
        self,
        question: str,
        node: dict,
        domain_profile: dict,
        learner_profile: dict,
        chat_history: list[dict],
        max_tool_rounds: int = 3,
    ) -> str:
        """回答学生提问（带 MCP 工具调用），支持多轮工具交互"""
        learner_style = self._learner_to_instruction(learner_profile)
        profile_prompt = domain_profile.get("prompt_overrides", {}).get("handle_question", "")
        system_content = f"你是一位耐心的老师。当前讲解的知识点是：{node.get('title')}\n\n{learner_style}"
        if profile_prompt:
            system_content += f"\n\n{profile_prompt}"

        # 添加工具描述
        from app.services.mcp_client import get_mcp_manager

        tool_desc = get_mcp_manager().get_tool_descriptions()
        if tool_desc:
            system_content += f"\n\n{tool_desc}"

        messages = [{"role": "system", "content": system_content}]
        if chat_history:
            trimmed = self.trim_context(chat_history)
            messages.extend(trimmed)
        if not chat_history or chat_history[-1].get("content") != question:
            messages.append({"role": "user", "content": question})

        for _round in range(max_tool_rounds):
            answer = await self.chat(messages, temperature=0.7, max_tokens=4096)
            tool_call = self._extract_tool_call(answer)
            if not tool_call:
                return answer

            # 执行工具调用
            tool_result = await get_mcp_manager().call_tool(tool_call["tool"], tool_call["args"])
            messages.append({"role": "assistant", "content": f"[调用工具 {tool_call['tool']}]"})
            messages.append({"role": "user", "content": f"工具 {tool_call['tool']} 返回结果：\n{tool_result}\n\n请基于此结果回答学生的问题。"})

        # 超过最大轮次，返回最后一次生成的文本
        return await self.chat(messages, temperature=0.7, max_tokens=4096)

    @staticmethod
    def _extract_tool_call(text: str) -> dict | None:
        """从 LLM 回答中提取 TOOL_CALL 指令"""
        import re

        m = re.search(r"TOOL_CALL:\s*(\{.*\})", text, re.DOTALL)
        if not m:
            return None
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            return None

    async def generate_quiz(self, node: dict, domain_profile: dict) -> dict:
        """生成测验题目（带缓存，相同节点不出两次题）"""
        prompt_template = domain_profile.get("prompt_overrides", {}).get("generate_quiz", "请生成 3 道选择题。")
        prompt = f"""{prompt_template}

知识点内容：
{node.get("content", "")}

返回 JSON 格式（不要 markdown 包裹）：
{{
  "questions": [
    {{"id": "q1", "type": "multiple_choice", "question": "...",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."], "answer": "A"}}
  ]
}}"""

        result = await self.chat(
            [{"role": "user", "content": prompt}], temperature=0.7, max_tokens=4096, use_cache=False
        )
        # 如果返回为空或明显截断，用本地规则兜底
        if not result or len(result.strip()) < 20 or result.strip().endswith('"options":'):
            # API 返回空 → 用本地规则生成一个简单问题兜底
            return {
                "questions": [
                    {
                        "id": "q1",
                        "type": "multiple_choice",
                        "question": f"关于「{node.get('title', '本知识点')}」的理解，以下哪项是正确的？",
                        "options": [
                            "A. 以上描述全部正确",
                            "B. 以上描述部分正确",
                            "C. 以上描述不正确",
                            "D. 无法判断",
                        ],
                        "answer": "A",
                    }
                ]
            }
        return self._parse_json(result)

    async def extract_knowledge(self, text: str, domain_id: str = "general") -> dict:
        """从文本中提取结构化知识点（带缓存）"""
        prompt = f"""你是一位知识工程师。请从以下内容中提取知识点，返回严格的 JSON 格式。

内容：
{text[:8000]}

要求：
1. 提取所有独立的知识点，每个包含 title、summary、content、difficulty、node_type
2. 识别知识点之间的前置依赖关系（PREREQUISITE）
3. 将它们分组为 2-5 个模块，由浅入深
4. difficulty 取值：intro / intermediate / advanced
5. node_type 取值：concept / skill / fact / procedure

返回格式（严格 JSON，不要 markdown 包裹）：
{{
  "nodes": [
    {{"title": "...", "summary": "...", "content": "...# Markdown",
      "difficulty": "intro", "node_type": "concept", "examples": []}}
  ],
  "relations": [
    {{"from": "节点A标题", "to": "节点B标题", "type": "PREREQUISITE"}}
  ],
  "modules": [
    {{"name": "模块名", "order": 1, "node_titles": ["节点A标题", "节点B标题"]}}
  ]
}}"""

        result = await self.chat(
            [{"role": "user", "content": prompt}], temperature=0.3, max_tokens=8192, use_cache=True
        )

        if len(result) < 50:
            print(f"  ⚠️ extract_knowledge 返回过短（{len(result)} 字符），使用空结构兜底")
            return {"nodes": [], "relations": [], "modules": []}

        try:
            return self._parse_json(result)
        except json.JSONDecodeError:
            print(f"  ⚠️ extract_knowledge JSON 解析失败，使用空结构兜底")
            return {"nodes": [], "relations": [], "modules": []}

    async def generate_syllabus(self, nodes: list[dict], domain_profile: dict) -> list[dict]:
        """生成大纲（模块分组）"""
        titles = [n["title"] for n in nodes]
        prompt = f"""以下是知识点列表：{json.dumps(titles, ensure_ascii=False)}

请将这些知识点按教学逻辑排序并分组，返回 JSON 格式的模块列表。
每个模块包含名称和该模块包含的知识点标题列表。
知识点必须按教学顺序排列（由浅入深）。"""

        result = await self.chat(
            [{"role": "user", "content": prompt}], temperature=0.3, max_tokens=4096, use_cache=True
        )
        return self._parse_json(result)

    async def detect_domain(self, topic: str, text: str = "") -> dict:
        """检测内容所属领域（带缓存）"""
        content = topic + "\n" + (text[:2000] if text else "")
        prompt = f"""分析以下内容最可能属于哪个学习领域。

内容：{content[:3000]}

可选领域：general（通用）, math（数学）, programming（编程）,\
  language（语言）, history（历史）, physics（物理）, music（音乐）

返回 JSON：{{"domain": "领域ID", "confidence": 0.0~1.0, "reason": "简短理由"}}"""

        result = await self.chat([{"role": "user", "content": prompt}], temperature=0.2, use_cache=True)
        return self._parse_json(result)

    async def cross_validate_knowledge(
        self,
        topic: str,
        llm_knowledge: dict,
        search_snippets: list[str],
        search_sources: list[str],
        domain_id: str,
    ) -> dict:
        """交叉验证：将 LLM 生成的知识点与搜索结果比对，返回增强后的结构化知识"""
        snippets_text = "\n\n".join(
            f"[来源 {i+1}] {s[:600]}" for i, s in enumerate(search_snippets[:8])
        )
        prompt = f"""你是一位知识验证专家。以下是关于「{topic}」的初步知识结构和网络搜索结果。

=== LLM 初步生成的知识点 ===
{json.dumps(llm_knowledge, ensure_ascii=False, indent=2)[:4000]}

=== 网络搜索结果（多源）===
{snippets_text}

请执行以下验证并返回 JSON：

1. **事实核查**：对比多个来源，标记可能存在的矛盾或已过时的信息
2. **内容补充**：如果搜索结果包含 LLM 生成中缺少的重要知识点，请补充
3. **置信评分**：对每个知识点给出 confidence (0.0~1.0)，依据多个来源一致性评估
4. **来源标记**：在每个节点中记录 sources 字段，列出支持该节点的来源索引
5. **引用链接**：如果搜索结果提供了可引用的信息，在 ref_links 中记录

返回格式（严格 JSON，不要 markdown 包裹）：
{{
  "nodes": [
    {{"title": "...", "summary": "...", "content": "...",
      "difficulty": "intro/intermediate/advanced",
      "node_type": "concept/skill/fact/procedure",
      "confidence": 0.0~1.0,
      "sources": ["llm_generated", "search_1"],
      "examples": [],
      "ref_links": [{{"title": "...", "url": "..."}}]}}
  ],
  "relations": [
    {{"from": "节点标题", "to": "节点标题", "type": "PREREQUISITE"}}
  ],
  "modules": [
    {{"name": "模块名", "order": 1, "node_titles": ["节点A", "节点B"]}}
  ]
}}

注意：如果没有矛盾或补充，保持原结构不变，只增加 confidence 和 sources 字段。"""

        result = await self.chat(
            [{"role": "user", "content": prompt}], temperature=0.3, max_tokens=8192, use_cache=False
        )

        if not result or len(result.strip()) < 50:
            return {}

        try:
            parsed = self._parse_json(result)
            if isinstance(parsed, dict) and "nodes" in parsed:
                return parsed
            return {}
        except Exception:
            return {}

    async def suggest_extension(self, node: dict, related_nodes: list[dict], learner_profile: dict) -> str:
        """生成延伸内容"""
        learner_style = self._learner_to_instruction(learner_profile)
        prompt = f"""{learner_style}

当前知识点：{node.get("title")}
学生已掌握该内容，想要延伸学习以下关联话题：
{json.dumps([n.get("title") for n in related_nodes], ensure_ascii=False)}

请推荐一个最值得延伸的方向，并简要说明理由和学习路径建议（100字以内）。"""

        return await self.chat([{"role": "user", "content": prompt}], temperature=0.7)

    async def summarize_context(self, messages: list[dict]) -> str:
        """对长时间对话进行摘要压缩"""
        prompt = self.build_summary_prompt(messages)
        return await self.chat([{"role": "user", "content": prompt}], temperature=0.3, max_tokens=300)

    # ──────────────────────────────────────────
    # 缓存管理
    # ──────────────────────────────────────────

    @staticmethod
    def _cache_key(messages: list[dict], temperature: float) -> str:
        """生成缓存键（messages JSON + temperature 的哈希）"""
        raw = json.dumps(messages, sort_keys=True) + str(temperature)
        return hashlib.md5(raw.encode()).hexdigest()

    @classmethod
    def _get_cached(cls, key: str) -> str | None:
        """从进程缓存获取"""
        entry = cls._response_cache.get(key)
        if entry:
            response, ts = entry
            if time.time() - ts < settings.cache_ttl_seconds:
                return response
            del cls._response_cache[key]
        return None

    @classmethod
    def _set_cache(cls, key: str, response: str):
        """写入进程缓存"""
        cls._response_cache[key] = (response, time.time())

    @classmethod
    def clear_cache(cls):
        """清空缓存（调试用）"""
        cls._response_cache.clear()
        cls._domain_profile_cache.clear()

    # ──────────────────────────────────────────
    # 工具方法
    # ──────────────────────────────────────────

    @staticmethod
    async def _stream_response(response) -> AsyncGenerator[str, None]:
        """处理流式响应"""
        async for chunk in response:
            delta = chunk.choices[0].delta.content if chunk.choices else ""
            if delta:
                yield delta

    @staticmethod
    def _parse_json(text: str) -> dict | list:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0] if "```" in text else text
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError as e:
            # 解析失败时打印前 200 和后 200 字符帮助调试
            print(f"  ❌ JSON 解析失败: {e}")
            print(f"  前200字: {text[:200]}")
            print(f"  后200字: {text[-200:]}")
            raise

    @staticmethod
    def _learner_to_instruction(profile: dict) -> str:
        """将 Learner Profile 转为自然语言教学指令（支持嵌套/扁平格式）"""
        norm = normalize_profile(profile)
        parts = []

        def _val(group: str, field: str, default=None):
            """从已归一化的 norm 中安全读取字段"""
            return norm.get(group, {}).get(field, default)

        # ── content ──
        abstraction = _val("content", "abstraction_level", 0.5)
        analogy = _val("content", "analogy_density", 0.5)
        example_style = _val("content", "example_style", 0.5)

        if abstraction < 0.3:
            parts.append("尽量用具体事物举例，避免抽象概念")
        elif abstraction > 0.7:
            parts.append("可以直接使用专业术语和抽象概念")

        if analogy > 0.7:
            parts.append("多用比喻和类比来解释")
        elif analogy < 0.3:
            parts.append("少用比喻，直接讲本质")

        if example_style < 0.3:
            parts.append("举例尽量贴近日常生活")
        elif example_style > 0.7:
            parts.append("举例可以偏向专业领域")

        # ── pace ──
        speed = _val("pace", "teaching_speed", 0.5)
        session_duration = _val("pace", "session_duration_min")
        repetition = _val("pace", "repetition_preference", 0.5)

        if speed < 0.3:
            parts.append("请放慢语速，每讲完一个点确认是否理解")
        elif speed > 0.7:
            parts.append("保持简洁高效，快速推进")

        if session_duration:
            parts.append(f"建议单次学习时长控制在 {int(session_duration)} 分钟左右")

        if repetition > 0.7:
            parts.append("重要概念请适度重复加深印象")
        elif repetition < 0.3:
            parts.append("不需要重复，讲一遍即可")

        # ── interaction ──
        feedback = _val("interaction", "feedback_tone", 0.5)
        error_handling = _val("interaction", "error_handling", 0.5)
        interrupt = _val("interaction", "interrupt_policy")

        if feedback < 0.3:
            parts.append("反馈以鼓励为主，错误时先引导学生自己思考")
        else:
            parts.append("反馈直接明确，错误时直接指出")

        if error_handling < 0.3:
            parts.append("学生答错时先给出提示引导，不直接公布答案")
        else:
            parts.append("学生答错时直接指出正确答案并解释原因")

        if interrupt and interrupt != "anytime":
            parts.append("请等学生把一段话说完再回应，不要中途打断")

        # ── assessment ──
        quiz_style = _val("assessment", "quiz_style", 0.5)
        tolerance = _val("assessment", "tolerance", 0.7)

        if quiz_style < 0.3:
            parts.append("出题尽量有趣，可以加入闯关或游戏化元素")
        elif quiz_style > 0.7:
            parts.append("出题风格按传统考试方式进行")

        if tolerance > 0.6:
            parts.append("容错率较高，答对 60% 即可通过")
        else:
            parts.append("要求较高，需要答对 80% 以上才算通过")

        # ── ui.tts ──
        enable_tts = _val("ui", "enable_tts")
        if enable_tts:
            parts.append("学生开启了语音播报模式，回答内容请保持口语化和适合朗读")

        if not parts:
            return ""
        return "教学风格要求：" + "；".join(parts) + "。"

