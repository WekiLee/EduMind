"""WebSocket 教学对话 —— 实时文字聊天，支持断线重连上下文恢复"""

import base64
import json
import time
from datetime import UTC, datetime

import yaml
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.database import async_session_factory, get_redis
from app.core.security import decode_access_token
from app.llm.adapter import LLMAdapter
from app.models.quiz import ChatMessage, ChatSession
from app.services.knowledge_graph import KnowledgeGraphService
from app.services.voice import synthesize_speech, transcribe_audio

router = APIRouter()


# ── 领域配置缓存（类级，避免重复读盘）──
_domain_profile_cache: dict[str, dict] = {}
_last_loaded: dict[str, float] = {}


def load_domain_profile(domain_id: str) -> dict:
    """加载领域配置（带缓存，最多 5 分钟重新读盘一次）"""
    now = time.time()
    cached = _domain_profile_cache.get(domain_id)
    last = _last_loaded.get(domain_id, 0)

    if cached and (now - last) < 300:
        return cached

    import os

    path = os.path.join("app", "domain_profiles", f"{domain_id}.yaml")
    if not os.path.exists(path):
        path = os.path.join("app", "domain_profiles", "general.yaml")
        domain_id = "general"

    with open(path, encoding="utf-8") as f:
        profile = yaml.safe_load(f)

    _domain_profile_cache[domain_id] = profile
    _last_loaded[domain_id] = now
    return profile


async def load_chat_history(session_id: str) -> list[dict]:
    """从 PostgreSQL 加载历史消息"""
    if not session_id:
        return []

    async with async_session_factory() as db:
        result = await db.execute(
            select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc())
        )
        msgs = result.scalars().all()
        return [{"role": msg.role, "content": msg.content} for msg in msgs]


async def save_message(session_id: str, role: str, content: str):
    """保存单条消息到 PostgreSQL"""
    async with async_session_factory() as db:
        msg = ChatMessage(session_id=session_id, role=role, content=content)
        db.add(msg)
        await db.commit()


async def cache_context_to_redis(session_id: str, messages: list[dict]):
    """将上下文缓存到 Redis（用于断线快速恢复）"""
    try:
        redis = await get_redis()
        await redis.setex(
            f"chat_ctx:{session_id}",
            7200,  # 2h 过期
            json.dumps(messages[-20:]),  # 只缓存最近 20 条
        )
    except Exception:
        pass  # Redis 不可用时降级，不影响主流程


async def load_context_from_redis(session_id: str) -> list[dict] | None:
    """从 Redis 恢复上下文"""
    try:
        redis = await get_redis()
        data = await redis.get(f"chat_ctx:{session_id}")
        if data:
            return json.loads(data)
    except Exception:
        pass
    return None


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket, token: str):
    """教学对话 WebSocket"""
    # ── 认证 ──
    user_id = decode_access_token(token)
    if not user_id:
        await websocket.close(code=4001, reason="无效令牌")
        return

    await websocket.accept()

    # ── 从数据库加载用户的学习风格配置 ──
    learner_profile = None
    try:
        from app.models.user import User
        async with async_session_factory() as db:
            user_result = await db.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            if user and user.learner_profile:
                lp = user.learner_profile
                if isinstance(lp, dict) and any(k in lp for k in ("abstraction_level", "analogy_density")):
                    learner_profile = lp
    except Exception:
        pass
    if learner_profile is None:
        learner_profile = {
            "abstraction_level": 0.5,
            "analogy_density": 0.5,
            "teaching_speed": 0.5,
            "feedback_tone": 0.5,
        }

    session_id = ""
    current_node_id = ""
    chat_history: list[dict] = []
    llm = LLMAdapter()

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type", "message")

            # ── 语音消息：ASR 识别后转为文字消息处理 ──
            if msg_type == "audio":
                audio_b64 = data.get("audio_data", "")
                if audio_b64:
                    audio_bytes = base64.b64decode(audio_b64)
                    transcribed = await transcribe_audio(audio_bytes)
                    if transcribed:
                        # 将识别结果转为文字消息，走下面的文字处理流程
                        data["type"] = "message"
                        data["content"] = transcribed
                        data["_from_voice"] = True
                    else:
                        await websocket.send_json({"type": "error", "code": "asr_failed", "message": "语音识别失败，请重试"})
                        continue
                else:
                    await websocket.send_json({"type": "error", "code": "no_audio", "message": "未收到音频数据"})
                    continue

            # ── 消息：开始或继续对话 ──
            if msg_type == "message":
                content = data.get("content", "")
                node_id = data.get("node_id", current_node_id)
                path_id = data.get("path_id", "")

                if not content.strip():
                    await websocket.send_json(
                        {
                            "type": "error",
                            "code": "empty_message",
                            "message": "消息不能为空",
                        }
                    )
                    continue

                # 首次消息 → 创建会话 / 断线重连 → 恢复上下文
                if not session_id:
                    session_id = data.get("session_id", "") or ""
                    current_node_id = node_id

                    # 尝试从 Redis 恢复上下文（快速路径）
                    chat_history = await load_context_from_redis(session_id)

                    if chat_history is None and session_id:
                        # Redis 没有 → 从 DB 恢复（慢路径）
                        loaded = await load_chat_history(session_id)
                        if loaded is not None:
                            chat_history = loaded

                    if not session_id or chat_history is None or len(chat_history) == 0:
                        # 全新会话
                        async with async_session_factory() as db:
                            sess = ChatSession(
                                user_id=user_id,
                                path_id=path_id,
                                node_id=node_id,
                            )
                            db.add(sess)
                            await db.commit()
                            session_id = sess.id
                        chat_history = []

                    await websocket.send_json(
                        {
                            "type": "session_ready",
                            "session_id": session_id,
                            "restored": len(chat_history) > 0,
                        }
                    )

                current_node_id = node_id

                # ── 获取节点信息 ──
                kg = KnowledgeGraphService()
                node = await kg.get_node(node_id)
                if not node:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "code": "node_not_found",
                            "message": "节点不存在",
                        }
                    )
                    continue

                domain_id = node.get("domain_id", "general")
                profile = load_domain_profile(domain_id)

                # 保存用户消息
                await save_message(session_id, "user", content)
                chat_history.append({"role": "user", "content": content})

                # ── 判断是否需要摘要压缩 ──
                if LLMAdapter.need_summary(chat_history):
                    summary = await llm.summarize_context(chat_history)
                    chat_history = [
                        {
                            "role": "system",
                            "content": f"以下是对之前对话的摘要，请基于此继续教学：{summary}",
                        },
                    ] + chat_history[-4:]  # 保留最近 4 条

                # ── LLM 回答（带超时和错误处理）──
                try:
                    answer = await llm.answer_question(
                        question=content,
                        node=node,
                        domain_profile=profile.get("domain", {}),
                        learner_profile=learner_profile,
                        chat_history=chat_history,
                    )
                except Exception as e:
                    print(f"  ❌ LLM 教学回答失败: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "code": "llm_error",
                        "message": f"AI 回答失败: {str(e)[:100]}。请检查 API 配置或稍后重试。",
                    })
                    continue

                # 流式发送
                for i in range(0, len(answer), 20):
                    await websocket.send_json(
                        {
                            "type": "teaching_chunk",
                            "session_id": session_id,
                            "content": answer[i : i + 20],
                        }
                    )
                await websocket.send_json(
                    {
                        "type": "teaching_done",
                        "session_id": session_id,
                    }
                )

                # 如果来自语音输入，将回答转为语音返回
                if data.get("_from_voice"):
                    try:
                        audio_reply = await synthesize_speech(answer)
                        if audio_reply:
                            audio_b64 = base64.b64encode(audio_reply).decode()
                            await websocket.send_json({
                                "type": "audio_reply",
                                "session_id": session_id,
                                "audio_data": audio_b64,
                            })
                    except Exception as e:
                        print(f"  ⚠️ TTS 合成失败（不影响文字回复）: {e}")

                # 保存 AI 回答
                await save_message(session_id, "assistant", answer)
                chat_history.append({"role": "assistant", "content": answer})

                # 缓存到 Redis（断线重连用）
                await cache_context_to_redis(session_id, chat_history)

                # 更新会话消息计数
                async with async_session_factory() as db:
                    sess = await db.get(ChatSession, session_id)
                    if sess:
                        sess.message_count += 1
                        await db.commit()

            # ── 延伸请求 ──
            elif msg_type == "extend":
                node_id = data.get("node_id", current_node_id)
                kg = KnowledgeGraphService()
                node = await kg.get_node(node_id)
                if not node:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "code": "node_not_found",
                            "message": "节点不存在",
                        }
                    )
                    continue

                related = await kg.get_related_nodes(node_id)
                prereqs = await kg.get_prerequisites(node_id)
                all_related = related + [
                    {"title": f"前置：{n.get('title', '')}", **n} for n in prereqs if n.get("id") != node_id
                ]

                try:
                    suggestion = await llm.suggest_extension(node, all_related, learner_profile)
                except Exception as e:
                    print(f"  ❌ LLM 延伸请求失败: {e}")
                    await websocket.send_json({"type": "error", "code": "llm_error", "message": f"延伸请求失败: {str(e)[:80]}"})
                    continue

                await websocket.send_json(
                    {
                        "type": "extension",
                        "session_id": session_id,
                        "content": suggestion,
                        "related_nodes": [
                            {"id": n.get("id"), "title": n.get("title", ""), "relation": "延伸"}
                            for n in all_related[:5]
                        ],
                    }
                )

            # ── 请求测验 ──
            elif msg_type == "request_quiz":
                await websocket.send_json(
                    {
                        "type": "quiz_requested",
                        "session_id": session_id,
                        "node_id": current_node_id,
                    }
                )

    except WebSocketDisconnect:
        pass
    finally:
        # 关闭时标记会话结束
        if session_id:
            async with async_session_factory() as db:
                sess = await db.get(ChatSession, session_id)
                if sess:
                    sess.ended_at = datetime.now(UTC)
                    await db.commit()
