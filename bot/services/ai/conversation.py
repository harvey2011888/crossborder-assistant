"""
对话上下文管理模块

实现多轮对话的上下文管理，包括：
- 会话创建、获取、更新、删除
- 对话历史存储和检索
- 会话过期机制
- 上下文长度限制
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.database import get_db_session
from bot.services.ai.base import Message
from models.session import Session

# 配置日志
logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_SESSION_TTL_HOURS = 24  # 会话默认有效期（小时）
MAX_CONTEXT_MESSAGES = 20  # 最大保留消息数
MAX_MESSAGE_LENGTH = 4000  # 单条消息最大长度


class ConversationManager:
    """
    对话上下文管理器

    管理用户与AI的多轮对话会话，支持持久化存储到数据库
    """

    def __init__(
        self,
        session_ttl_hours: int = DEFAULT_SESSION_TTL_HOURS,
        max_context_messages: int = MAX_CONTEXT_MESSAGES,
    ):
        """
        初始化对话管理器

        Args:
            session_ttl_hours: 会话有效期（小时）
            max_context_messages: 最大保留消息数
        """
        self.session_ttl_hours = session_ttl_hours
        self.max_context_messages = max_context_messages

    async def create_session(
        self,
        user_id: int,
        session_type: str = "general",
        ai_provider: str = "gemini",
        title: Optional[str] = None,
        system_prompt: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Session:
        """
        创建新会话

        Args:
            user_id: 用户Discord ID
            session_type: 会话类型 (general/shopping/logistics/order)
            ai_provider: AI提供商
            title: 会话标题
            system_prompt: 系统提示词
            metadata: 会话元数据

        Returns:
            创建的会话对象
        """
        session_id = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(hours=self.session_ttl_hours)

        # 初始化对话上下文
        context = {"messages": []}
        if system_prompt:
            context["messages"].append({
                "role": "system",
                "content": system_prompt,
                "timestamp": datetime.utcnow().isoformat(),
            })

        async with await get_db_session() as db:
            session = Session(
                session_id=session_id,
                user_id=user_id,
                session_type=session_type,
                ai_provider=ai_provider,
                title=title or f"新会话 {datetime.utcnow().strftime('%m-%d %H:%M')}",
                context=json.dumps(context, ensure_ascii=False),
                metadata=json.dumps(metadata or {}, ensure_ascii=False),
                is_active=True,
                message_count=0,
                expires_at=expires_at,
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)

            logger.info(f"创建新会话: {session_id} (用户: {user_id})")
            return session

    async def get_session(
        self,
        session_id: str,
        check_expiry: bool = True,
    ) -> Optional[Session]:
        """
        获取会话

        Args:
            session_id: 会话ID
            check_expiry: 是否检查过期

        Returns:
            会话对象或None
        """
        async with await get_db_session() as db:
            result = await db.execute(
                select(Session).where(Session.session_id == session_id)
            )
            session = result.scalar_one_or_none()

            if not session:
                return None

            # 检查会话是否过期
            if check_expiry and session.expires_at:
                if datetime.utcnow() > session.expires_at:
                    logger.warning(f"会话已过期: {session_id}")
                    session.is_active = False
                    await db.commit()
                    return None

            return session

    async def get_or_create_session(
        self,
        user_id: int,
        session_id: Optional[str] = None,
        session_type: str = "general",
        ai_provider: str = "gemini",
        system_prompt: Optional[str] = None,
    ) -> Session:
        """
        获取或创建会话

        Args:
            user_id: 用户Discord ID
            session_id: 现有会话ID（可选）
            session_type: 会话类型
            ai_provider: AI提供商
            system_prompt: 系统提示词

        Returns:
            会话对象
        """
        # 尝试获取现有会话
        if session_id:
            session = await self.get_session(session_id)
            if session and session.user_id == user_id:
                return session

        # 创建新会话
        return await self.create_session(
            user_id=user_id,
            session_type=session_type,
            ai_provider=ai_provider,
            system_prompt=system_prompt,
        )

    async def get_user_active_sessions(
        self,
        user_id: int,
        session_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Session]:
        """
        获取用户的活跃会话列表

        Args:
            user_id: 用户Discord ID
            session_type: 会话类型过滤
            limit: 返回数量限制

        Returns:
            会话列表
        """
        async with await get_db_session() as db:
            query = select(Session).where(
                Session.user_id == user_id,
                Session.is_active == True,
            )

            if session_type:
                query = query.where(Session.session_type == session_type)

            query = query.order_by(Session.last_activity_at.desc()).limit(limit)

            result = await db.execute(query)
            return list(result.scalars().all())

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        添加消息到会话

        Args:
            session_id: 会话ID
            role: 消息角色 (system/user/assistant)
            content: 消息内容
            metadata: 消息元数据

        Returns:
            是否成功
        """
        session = await self.get_session(session_id)
        if not session:
            logger.error(f"会话不存在: {session_id}")
            return False

        # 截断过长的消息
        if len(content) > MAX_MESSAGE_LENGTH:
            content = content[:MAX_MESSAGE_LENGTH] + "..."

        # 解析现有上下文
        try:
            context = json.loads(session.context or '{"messages": []}')
        except json.JSONDecodeError:
            context = {"messages": []}

        # 添加新消息
        message_data = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if metadata:
            message_data["metadata"] = metadata

        context["messages"].append(message_data)

        # 限制上下文长度（保留系统消息和最近的消息）
        context["messages"] = self._truncate_context(context["messages"])

        # 更新会话
        async with await get_db_session() as db:
            expires_at = datetime.utcnow() + timedelta(hours=self.session_ttl_hours)

            await db.execute(
                update(Session)
                .where(Session.session_id == session_id)
                .values(
                    context=json.dumps(context, ensure_ascii=False),
                    message_count=Session.message_count + 1,
                    last_activity_at=datetime.utcnow(),
                    expires_at=expires_at,
                )
            )
            await db.commit()

        return True

    async def get_messages(
        self,
        session_id: str,
        include_system: bool = True,
        limit: Optional[int] = None,
    ) -> List[Message]:
        """
        获取会话的消息列表

        Args:
            session_id: 会话ID
            include_system: 是否包含系统消息
            limit: 消息数量限制

        Returns:
            消息列表
        """
        session = await self.get_session(session_id)
        if not session:
            return []

        try:
            context = json.loads(session.context or '{"messages": []}')
            messages_data = context.get("messages", [])
        except json.JSONDecodeError:
            return []

        # 过滤系统消息
        if not include_system:
            messages_data = [m for m in messages_data if m.get("role") != "system"]

        # 限制数量
        if limit:
            messages_data = messages_data[-limit:]

        # 转换为Message对象
        messages = []
        for data in messages_data:
            messages.append(
                Message(
                    role=data.get("role", "user"),
                    content=data.get("content", ""),
                )
            )

        return messages

    async def clear_context(
        self,
        session_id: str,
        keep_system: bool = True,
    ) -> bool:
        """
        清空会话上下文

        Args:
            session_id: 会话ID
            keep_system: 是否保留系统消息

        Returns:
            是否成功
        """
        session = await self.get_session(session_id)
        if not session:
            return False

        try:
            context = json.loads(session.context or '{"messages": []}')
            messages = context.get("messages", [])

            if keep_system:
                # 只保留系统消息
                messages = [m for m in messages if m.get("role") == "system"]
            else:
                messages = []

            context["messages"] = messages

            async with await get_db_session() as db:
                await db.execute(
                    update(Session)
                    .where(Session.session_id == session_id)
                    .values(
                        context=json.dumps(context, ensure_ascii=False),
                        message_count=len(messages),
                    )
                )
                await db.commit()

            return True
        except Exception as e:
            logger.error(f"清空上下文失败: {e}")
            return False

    async def update_system_prompt(
        self,
        session_id: str,
        system_prompt: str,
    ) -> bool:
        """
        更新系统提示词

        Args:
            session_id: 会话ID
            system_prompt: 新的系统提示词

        Returns:
            是否成功
        """
        session = await self.get_session(session_id)
        if not session:
            return False

        try:
            context = json.loads(session.context or '{"messages": []}')
            messages = context.get("messages", [])

            # 移除旧的系统消息
            messages = [m for m in messages if m.get("role") != "system"]

            # 添加新的系统消息
            messages.insert(0, {
                "role": "system",
                "content": system_prompt,
                "timestamp": datetime.utcnow().isoformat(),
            })

            context["messages"] = messages

            async with await get_db_session() as db:
                await db.execute(
                    update(Session)
                    .where(Session.session_id == session_id)
                    .values(
                        context=json.dumps(context, ensure_ascii=False),
                    )
                )
                await db.commit()

            logger.info(f"更新会话 {session_id} 的系统提示词")
            return True
        except Exception as e:
            logger.error(f"更新系统提示词失败: {e}")
            return False

    async def close_session(self, session_id: str) -> bool:
        """
        关闭会话

        Args:
            session_id: 会话ID

        Returns:
            是否成功
        """
        async with await get_db_session() as db:
            result = await db.execute(
                update(Session)
                .where(Session.session_id == session_id)
                .values(is_active=False)
            )
            await db.commit()

            if result.rowcount > 0:
                logger.info(f"关闭会话: {session_id}")
                return True
            return False

    async def delete_session(self, session_id: str) -> bool:
        """
        删除会话

        Args:
            session_id: 会话ID

        Returns:
            是否成功
        """
        async with await get_db_session() as db:
            result = await db.execute(
                delete(Session).where(Session.session_id == session_id)
            )
            await db.commit()

            if result.rowcount > 0:
                logger.info(f"删除会话: {session_id}")
                return True
            return False

    async def cleanup_expired_sessions(self) -> int:
        """
        清理过期会话

        Returns:
            清理的会话数量
        """
        async with await get_db_session() as db:
            result = await db.execute(
                update(Session)
                .where(
                    Session.expires_at < datetime.utcnow(),
                    Session.is_active == True,
                )
                .values(is_active=False)
            )
            await db.commit()

            count = result.rowcount
            if count > 0:
                logger.info(f"清理 {count} 个过期会话")
            return count

    def _truncate_context(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        截断上下文，保留系统消息和最近的消息

        Args:
            messages: 消息列表

        Returns:
            截断后的消息列表
        """
        # 分离系统消息和普通消息
        system_messages = [m for m in messages if m.get("role") == "system"]
        other_messages = [m for m in messages if m.get("role") != "system"]

        # 保留最近的N条普通消息
        if len(other_messages) > self.max_context_messages:
            other_messages = other_messages[-self.max_context_messages:]

        return system_messages + other_messages

    async def get_session_stats(self, user_id: int) -> Dict[str, Any]:
        """
        获取用户会话统计

        Args:
            user_id: 用户Discord ID

        Returns:
            统计信息字典
        """
        async with await get_db_session() as db:
            # 活跃会话数
            active_result = await db.execute(
                select(Session).where(
                    Session.user_id == user_id,
                    Session.is_active == True,
                )
            )
            active_sessions = active_result.scalars().all()

            # 总会话数
            total_result = await db.execute(
                select(Session).where(Session.user_id == user_id)
            )
            total_sessions = total_result.scalars().all()

            # 总消息数
            total_messages = sum(s.message_count for s in total_sessions)

            return {
                "active_sessions": len(active_sessions),
                "total_sessions": len(total_sessions),
                "total_messages": total_messages,
                "session_types": {
                    "general": len([s for s in active_sessions if s.session_type == "general"]),
                    "shopping": len([s for s in active_sessions if s.session_type == "shopping"]),
                    "logistics": len([s for s in active_sessions if s.session_type == "logistics"]),
                    "order": len([s for s in active_sessions if s.session_type == "order"]),
                },
            }


# 全局对话管理器实例
conversation_manager = ConversationManager()


# 便捷函数
async def create_conversation_session(
    user_id: int,
    session_type: str = "general",
    ai_provider: str = "gemini",
    system_prompt: Optional[str] = None,
) -> Session:
    """
    创建对话会话的便捷函数

    Args:
        user_id: 用户Discord ID
        session_type: 会话类型
        ai_provider: AI提供商
        system_prompt: 系统提示词

    Returns:
        会话对象
    """
    return await conversation_manager.create_session(
        user_id=user_id,
        session_type=session_type,
        ai_provider=ai_provider,
        system_prompt=system_prompt,
    )


async def get_conversation_messages(
    session_id: str,
    include_system: bool = True,
) -> List[Message]:
    """
    获取对话消息的便捷函数

    Args:
        session_id: 会话ID
        include_system: 是否包含系统消息

    Returns:
        消息列表
    """
    return await conversation_manager.get_messages(
        session_id=session_id,
        include_system=include_system,
    )


async def add_conversation_message(
    session_id: str,
    role: str,
    content: str,
) -> bool:
    """
    添加对话消息的便捷函数

    Args:
        session_id: 会话ID
        role: 消息角色
        content: 消息内容

    Returns:
        是否成功
    """
    return await conversation_manager.add_message(
        session_id=session_id,
        role=role,
        content=content,
    )
