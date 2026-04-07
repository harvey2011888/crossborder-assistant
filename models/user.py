"""
用户模型

定义用户相关的数据表结构
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.core.database import Base

if TYPE_CHECKING:
    from models.order import Order
    from models.session import Session


class User(Base):
    """
    用户模型

    存储Discord用户的基本信息和偏好设置
    """

    __tablename__ = "users"

    # 主键 - Discord用户ID
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)

    # Discord用户信息
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    discriminator: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # 用户偏好设置
    preferred_language: Mapped[str] = mapped_column(String(10), default="zh-CN")
    preferred_currency: Mapped[str] = mapped_column(String(10), default="CNY")
    default_shipping_country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # AI设置
    preferred_ai_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 关联关系
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="user")
    sessions: Mapped[List["Session"]] = relationship("Session", back_populates="user")

    def __repr__(self) -> str:
        """返回用户对象的字符串表示"""
        return f"<User(id={self.id}, username={self.username})>"

    def to_dict(self) -> dict:
        """
        将用户对象转换为字典

        Returns:
            包含用户信息的字典
        """
        return {
            "id": self.id,
            "username": self.username,
            "discriminator": self.discriminator,
            "avatar_url": self.avatar_url,
            "preferred_language": self.preferred_language,
            "preferred_currency": self.preferred_currency,
            "default_shipping_country": self.default_shipping_country,
            "preferred_ai_provider": self.preferred_ai_provider,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
        }
