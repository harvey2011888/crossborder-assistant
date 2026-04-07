"""
会话模型

定义用户AI对话会话的数据表结构
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.core.database import Base

if TYPE_CHECKING:
    from models.user import User


class Session(Base):
    """
    会话模型

    存储用户与AI的对话会话信息
    """

    __tablename__ = "sessions"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 会话ID（对外使用）
    session_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )

    # 外键 - 用户ID
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False, index=True
    )

    # 会话类型
    session_type: Mapped[str] = mapped_column(
        String(50), default="general", nullable=False
    )  # general, shopping, logistics, order

    # AI提供商
    ai_provider: Mapped[str] = mapped_column(String(50), nullable=False)

    # 会话标题（自动生成或用户设置）
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # 会话上下文（JSON格式存储对话历史）
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 会话元数据（JSON格式存储额外信息）
    metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 会话状态
    is_active: Mapped[bool] = mapped_column(default=True)

    # 消息计数
    message_count: Mapped[int] = mapped_column(Integer, default=0)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )  # 会话过期时间
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # 关联关系
    user: Mapped["User"] = relationship("User", back_populates="sessions")

    def __repr__(self) -> str:
        """返回会话对象的字符串表示"""
        return f"<Session(id={self.id}, session_id={self.session_id}, type={self.session_type})>"

    def to_dict(self) -> dict:
        """
        将会话对象转换为字典

        Returns:
            包含会话信息的字典
        """
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "session_type": self.session_type,
            "ai_provider": self.ai_provider,
            "title": self.title,
            "context": self.context,
            "metadata": self.metadata,
            "is_active": self.is_active,
            "message_count": self.message_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_activity_at": (
                self.last_activity_at.isoformat() if self.last_activity_at else None
            ),
        }

    def touch(self) -> None:
        """
        更新最后活动时间

        在每次对话交互时调用
        """
        self.last_activity_at = datetime.utcnow()
        self.message_count += 1
