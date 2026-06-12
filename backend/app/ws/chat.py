"""WebSocket 教学对话 —— 实时文字聊天，支持断线重连上下文恢复"""

import asyncio
import base64
import binascii
import json
from datetime import UTC, datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.api.guards import require_owned_node
from app.core.database import async_session_factory, get_redis
from app.core.security import resolve_active_user_id
from app.llm.adapter import LLMAdapter
from app.models.quiz import ChatMessage, ChatSession
from app.models.user import User
from app.services.domain_profile import load_domain_profile
from app.services.knowledge_graph import KnowledgeGraphService
from app.services.learner_profile import DEFAULT_LEARNER_PROFILE
from app.services.learner_profile import normalize as normalize_profile
from app.services.voice import synthesize_speech, transcribe_audio

router = APIRouter()


def decode_ws_payload(raw: str) -> tuple[dict | None, dict | None]:
    """解析 WebSocket JSON 消息，失败时返回错误响应。"""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None, {
            "type": "error",
            "code": "invalid_payload",
            "message": "消息格式不是合法 JSON",
        }
    if not isinstance(data, dict):
        return None, {
            "type": "error",
            "code": "invalid_payload",
            "message": "消息内容必须是 JSON 对象",
        }
    return data, None


def decode_audio_payload(audio_b64: object) -> tuple[bytes | None, dict | None]:
    """解析 base64 音频载荷，失败时返回错误响应。"""
    if not isinstance(audio_b64, str) or not audio_b64:
        return None, {"type": "error", "code": "no_audio", "message": "未收到音频数据"}
    try:
        return base64.b64decode(audio_b64, validate=True), None
    except (binascii.Error, ValueError):
        return None, {
            "type": "error",
            "code": "invalid_audio",
            "message": "音频数据格式不正确",
        }


def _session_matches_context(sess: ChatSession | None, user_id: str, path_id: str, node_id: str) -> bool:
    """确认会话归属与当前教学上下文一致。"""
    return bool(
        sess
        and sess.user_id == user_id
        and sess.path_id == path_id
        and sess.node_id == node_id
    )


async def load_chat_history(session_id: str, user_id: str, path_id: str, node_id: str) -> list[dict] | None:
    """从 PostgreSQL 加载历史消息"""
    if not session_id:
        return []

    async with async_session_factory() as db:
        sess = await db.get(ChatSession, session_id)
        if not _session_matches_context(sess, user_id, path_id, node_id):
            return None
        result = await db.execute(
            select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc())
        )
        msgs = result.scalars().all()
        return [{"role": msg.role, "content": msg.content} for msg in msgs]


async def validate_chat_session(session_id: str, user_id: str, path_id: str, node_id: str) -> bool:
    """恢复会话前先校验会话与当前路径/节点一致，避免跨上下文串话。"""
    if not session_id:
        return False
    async with async_session_factory() as db:
        sess = await db.get(ChatSession, session_id)
        return _session_matches_context(sess, user_id, path_id, node_id)


async def save_message(session_id: str, role: str, content: str):
    """保存单条消息到 PostgreSQL"""
    async with async_session_factory() as db:
        msg = ChatMessage(session_id=session_id, role=role, content=content)
        db.add(msg)
        await db.commit()


async def cache_context_to_redis(user_id: str, session_id: str, messages: list[dict]):
    """将上下文缓存到 Redis（用于断线快速恢复）"""
    try:
        redis = await get_redis()
        await redis.setex(
            f"chat_ctx:{user_id}:{session_id}",
            7200,  # 2h 过期
            json.dumps(messages[-20:]),  # 只缓存最近 20 条
        )
    except Exception:
        pass  # Redis 不可用时降级，不影响主流程


async def load_context_from_redis(user_id: str, session_id: str) -> list[dict] | None:
    """从 Redis 恢复上下文"""
    try:
        redis = await get_redis()
        data = await redis.get(f"chat_ctx:{user_id}:{session_id}")
        if data:
            return json.loads(data)
    except Exception:
        pass
    return None


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    """教学对话 WebSocket"""
    await websocket.accept()

    # ── 认证与用户状态校验 ──
    try:
        auth_raw = await asyncio.wait_for(websocket.receive_text(), timeout=10)
    except WebSocketDisconnect:
        return
    except TimeoutError:
        await websocket.close(code=4001, reason="认证超时")
        return

    auth_data, auth_error = decode_ws_payload(auth_raw)
    if auth_error or auth_data is None:
        await websocket.send_json(
            auth_error
            or {
                "type": "error",
                "code": "invalid_payload",
                "message": "消息内容必须是 JSON 对象",
            }
        )
        await websocket.close(code=4001, reason="认证消息格式错误")
        return

    token = auth_data.get("token") if auth_data.get("type") == "auth" else None
    if not isinstance(token, str) or not token:
        await websocket.send_json(
            {
                "type": "error",
                "code": "auth_required",
                "message": "请先发送认证消息",
            }
        )
        await websocket.close(code=4001, reason="缺少认证令牌")
        return

    try:
        async with async_session_factory() as db:
            user_id = await resolve_active_user_id(token, db)
            if not user_id:
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "invalid_token",
                        "message": "无效、过期或已停用的令牌",
                    }
                )
                await websocket.close(code=4001, reason="无效、过期或已停用的令牌")
                return
            user = await db.get(User, user_id)
            learner_profile = normalize_profile(user.learner_profile) if user else dict(DEFAULT_LEARNER_PROFILE)
    except Exception:
        await websocket.send_json(
            {
                "type": "error",
                "code": "auth_unavailable",
                "message": "认证服务不可用",
            }
        )
        await websocket.close(code=1011, reason="认证服务不可用")
        return

    await websocket.send_json({"type": "connected"})

    session_id = ""
    current_node_id = ""
    chat_history: list[dict] = []
    llm = LLMAdapter()
    profile_override_loaded = False

    try:
        while True:
            raw = await websocket.receive_text()
            data, payload_error = decode_ws_payload(raw)
            if payload_error:
                await websocket.send_json(payload_error)
                continue
            msg_type = data.get("type", "message")

            # ── 语音消息：ASR 识别后转为文字消息处理 ──
            if msg_type == "audio":
                audio_b64 = data.get("audio_data", "")
                audio_bytes, audio_error = decode_audio_payload(audio_b64)
                if audio_error:
                    await websocket.send_json(audio_error)
                    continue
                if audio_bytes:
                    transcribed = await transcribe_audio(audio_bytes)
                    if transcribed:
                        # 将识别结果转为文字消息，走下面的文字处理流程
                        data["type"] = "message"
                        data["content"] = transcribed
                        data["_from_voice"] = True
                        msg_type = "message"
                    else:
                        await websocket.send_json({"type": "error", "code": "asr_failed", "message": "语音识别失败，请重试"})
                        continue

            # ── 消息：开始或继续对话 ──
            if msg_type == "message":
                content = data.get("content", "")
                node_id = data.get("node_id", current_node_id)
                path_id = data.get("path_id", "")

                if not isinstance(content, str):
                    await websocket.send_json(
                        {
                            "type": "error",
                            "code": "invalid_payload",
                            "message": "消息内容必须是文本",
                        }
                    )
                    continue

                if not path_id:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "code": "path_required",
                            "message": "缺少学习路径，无法开始教学会话",
                        }
                    )
                    continue

                if not content.strip():
                    await websocket.send_json(
                        {
                            "type": "error",
                            "code": "empty_message",
                            "message": "消息不能为空",
                        }
                    )
                    continue

                async with async_session_factory() as auth_db:
                    try:
                        await require_owned_node(node_id, user_id, auth_db, path_id)
                    except Exception:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "code": "node_forbidden",
                                "message": "节点不存在或无权访问",
                            }
                        )
                        continue

                # 首次消息 → 创建会话 / 断线重连 → 恢复上下文
                if not session_id:
                    session_id = data.get("session_id", "") or ""
                    current_node_id = node_id

                    if session_id and not await validate_chat_session(session_id, user_id, path_id, node_id):
                        await websocket.send_json(
                            {
                                "type": "error",
                                "code": "invalid_session",
                                "message": "会话不存在或不属于当前学习路径/节点",
                            }
                        )
                        session_id = ""
                        continue

                    # 会话归属校验通过后，才允许从 Redis 快速恢复上下文。
                    chat_history = await load_context_from_redis(user_id, session_id) if session_id else None

                    if chat_history is None and session_id:
                        # Redis 没有 → 从 DB 恢复（慢路径）
                        loaded = await load_chat_history(session_id, user_id, path_id, node_id)
                        if loaded is None:
                            await websocket.send_json(
                                {
                                    "type": "error",
                                    "code": "invalid_session",
                                    "message": "会话不存在或不属于当前学习路径/节点",
                                }
                            )
                            session_id = ""
                            continue
                        chat_history = loaded

                    if not session_id or chat_history is None:
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

                # ── 加载路径级 Learner Profile 覆盖（仅首次） ──
                if path_id and not profile_override_loaded:
                    try:
                        from app.models.path import LearningPath
                        async with async_session_factory() as pdb:
                            p_res = await pdb.execute(
                                select(LearningPath).where(LearningPath.id == path_id, LearningPath.user_id == user_id)
                            )
                            p = p_res.scalar_one_or_none()
                            if p and p.learner_profile_override:
                                merged = dict(learner_profile)
                                for group, fields in p.learner_profile_override.items():
                                    if isinstance(fields, dict):
                                        merged[group] = {**merged.get(group, {}), **fields}
                                learner_profile = merged
                        profile_override_loaded = True
                    except Exception:
                        pass

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
                        "message": "AI 回答失败，请检查 API 配置或稍后重试。",
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
                await cache_context_to_redis(user_id, session_id, chat_history)

                # 更新会话消息计数
                async with async_session_factory() as db:
                    sess = await db.get(ChatSession, session_id)
                    if sess:
                        sess.message_count += 1
                        await db.commit()

            # ── 延伸请求 ──
            elif msg_type == "extend":
                node_id = data.get("node_id", current_node_id)
                path_id = data.get("path_id", "")
                if not path_id:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "code": "path_required",
                            "message": "缺少学习路径，无法生成延伸内容",
                        }
                    )
                    continue
                async with async_session_factory() as auth_db:
                    try:
                        await require_owned_node(node_id, user_id, auth_db, path_id)
                    except Exception:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "code": "node_forbidden",
                                "message": "节点不存在或无权访问",
                            }
                        )
                        continue
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
                    await websocket.send_json(
                        {
                            "type": "error",
                            "code": "llm_error",
                            "message": "延伸请求失败，请稍后重试。",
                        }
                    )
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
