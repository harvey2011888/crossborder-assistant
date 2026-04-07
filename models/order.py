"""
订单模型

定义订单相关的数据表结构
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.core.database import Base

if TYPE_CHECKING:
    from models.user import User


class OrderStatus(str, PyEnum):
    """订单状态枚举"""

    PENDING = "pending"  # 待处理
    CONFIRMED = "confirmed"  # 已确认
    PAID = "paid"  # 已支付
    PURCHASING = "purchasing"  # 采购中
    PURCHASED = "purchased"  # 已采购
    SHIPPING = "shipping"  # 运输中
    DELIVERED = "delivered"  # 已送达
    COMPLETED = "completed"  # 已完成
    CANCELLED = "cancelled"  # 已取消
    REFUNDED = "refunded"  # 已退款


class Order(Base):
    """
    订单模型

    存储用户的代购订单信息
    """

    __tablename__ = "orders"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 订单号（对外显示）
    order_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )

    # 外键 - 用户ID
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False, index=True
    )

    # 商品信息
    product_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    product_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    product_image: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    product_price_cny: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    product_quantity: Mapped[int] = mapped_column(Integer, default=1)

    # 规格信息
    product_specs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 订单金额
    product_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 商品费用
    domestic_shipping: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 国内运费
    service_fee: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 服务费
    international_shipping: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )  # 国际运费
    total_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 总金额

    # 订单状态
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False
    )

    # 物流信息
    tracking_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    shipping_carrier: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    shipping_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 平台订单ID（对接自建平台）
    platform_order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # 备注
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    shipped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 关联关系
    user: Mapped["User"] = relationship("User", back_populates="orders")

    def __repr__(self) -> str:
        """返回订单对象的字符串表示"""
        return f"<Order(id={self.id}, order_number={self.order_number}, status={self.status})>"

    def to_dict(self) -> dict:
        """
        将订单对象转换为字典

        Returns:
            包含订单信息的字典
        """
        return {
            "id": self.id,
            "order_number": self.order_number,
            "user_id": self.user_id,
            "product_url": self.product_url,
            "product_title": self.product_title,
            "product_image": self.product_image,
            "product_price_cny": self.product_price_cny,
            "product_quantity": self.product_quantity,
            "product_specs": self.product_specs,
            "product_cost": self.product_cost,
            "domestic_shipping": self.domestic_shipping,
            "service_fee": self.service_fee,
            "international_shipping": self.international_shipping,
            "total_amount": self.total_amount,
            "status": self.status.value if self.status else None,
            "tracking_number": self.tracking_number,
            "shipping_carrier": self.shipping_carrier,
            "shipping_address": self.shipping_address,
            "platform_order_id": self.platform_order_id,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "shipped_at": self.shipped_at.isoformat() if self.shipped_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
