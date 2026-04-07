"""
订单服务单元测试

测试自建平台订单管理服务
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from bot.services.platform.orders import (
    OrderCancelRequest,
    OrderCancelResponse,
    OrderCreateRequest,
    OrderCreateResponse,
    OrderInfo,
    OrderItem,
    OrderListRequest,
    OrderListResponse,
    OrderService,
    OrderStatus,
    OrderStatusResponse,
    ShippingAddress,
)
from bot.services.platform.client import PlatformAPIError


@pytest.mark.unit
class TestOrderModels:
    """订单数据模型测试"""

    def test_order_item_creation(self) -> None:
        """测试创建订单商品项"""
        item = OrderItem(
            product_name="测试商品",
            product_url="https://example.com/product/123",
            platform="淘宝",
            price_cny=99.99,
            quantity=2,
        )

        assert item.product_name == "测试商品"
        assert item.price_cny == 99.99
        assert item.quantity == 2

    def test_shipping_address_creation(self) -> None:
        """测试创建收货地址"""
        address = ShippingAddress(
            recipient_name="张三",
            phone="13800138000",
            country="美国",
            city="洛杉矶",
            street_address="123 Main St",
            postal_code="90001",
        )

        assert address.recipient_name == "张三"
        assert address.country == "美国"
        assert address.postal_code == "90001"

    def test_order_create_request(self) -> None:
        """测试创建订单请求"""
        item = OrderItem(
            product_name="测试商品",
            product_url="https://example.com/product/123",
            platform="淘宝",
            price_cny=99.99,
            quantity=1,
        )

        address = ShippingAddress(
            recipient_name="张三",
            phone="13800138000",
            country="美国",
            city="洛杉矶",
            street_address="123 Main St",
            postal_code="90001",
        )

        request = OrderCreateRequest(
            user_id="123456789",
            items=[item],
            shipping_address=address,
            notes="请尽快发货",
        )

        assert request.user_id == "123456789"
        assert len(request.items) == 1
        assert request.notes == "请尽快发货"

    def test_order_status_enum(self) -> None:
        """测试订单状态枚举"""
        assert OrderStatus.PENDING == "pending"
        assert OrderStatus.PAID == "paid"
        assert OrderStatus.SHIPPED == "shipped"
        assert OrderStatus.DELIVERED == "delivered"
        assert OrderStatus.CANCELLED == "cancelled"


@pytest.mark.unit
class TestOrderService:
    """订单服务测试"""

    def test_service_initialization(self) -> None:
        """测试服务初始化"""
        mock_client = MagicMock()
        service = OrderService(client=mock_client)

        assert service.client is mock_client

    def test_is_available_configured(self) -> None:
        """测试服务可用性检查（已配置）"""
        mock_client = MagicMock()
        mock_client.is_configured.return_value = True

        service = OrderService(client=mock_client)

        assert service.is_available() is True

    def test_is_available_not_configured(self) -> None:
        """测试服务可用性检查（未配置）"""
        mock_client = MagicMock()
        mock_client.is_configured.return_value = False

        service = OrderService(client=mock_client)

        assert service.is_available() is False


@pytest.mark.unit
@pytest.mark.asyncio
class TestOrderServiceAsync:
    """订单服务异步方法测试"""

    async def test_create_order_not_implemented(self) -> None:
        """测试创建订单（未实现）"""
        mock_client = MagicMock()
        mock_client.is_configured.return_value = True

        service = OrderService(client=mock_client)

        item = OrderItem(
            product_name="测试商品",
            product_url="https://example.com/product/123",
            platform="淘宝",
            price_cny=99.99,
            quantity=1,
        )

        address = ShippingAddress(
            recipient_name="张三",
            phone="13800138000",
            country="美国",
            city="洛杉矶",
            street_address="123 Main St",
            postal_code="90001",
        )

        request = OrderCreateRequest(
            user_id="123456789",
            items=[item],
            shipping_address=address,
        )

        with pytest.raises(NotImplementedError):
            await service.create_order(request)

    async def test_get_order_list_not_implemented(self) -> None:
        """测试查询订单列表（未实现）"""
        mock_client = MagicMock()
        mock_client.is_configured.return_value = True

        service = OrderService(client=mock_client)

        request = OrderListRequest(
            user_id="123456789",
            page=1,
            page_size=10,
        )

        with pytest.raises(NotImplementedError):
            await service.get_order_list(request)

    async def test_get_order_status_not_implemented(self) -> None:
        """测试查询订单状态（未实现）"""
        mock_client = MagicMock()
        mock_client.is_configured.return_value = True

        service = OrderService(client=mock_client)

        with pytest.raises(NotImplementedError):
            await service.get_order_status("ORDER123", "123456789")

    async def test_cancel_order_not_implemented(self) -> None:
        """测试取消订单（未实现）"""
        mock_client = MagicMock()
        mock_client.is_configured.return_value = True

        service = OrderService(client=mock_client)

        request = OrderCancelRequest(
            order_id="ORDER123",
            user_id="123456789",
            reason="不想要了",
        )

        with pytest.raises(NotImplementedError):
            await service.cancel_order(request)

    async def test_get_order_detail_not_implemented(self) -> None:
        """测试获取订单详情（未实现）"""
        mock_client = MagicMock()
        mock_client.is_configured.return_value = True

        service = OrderService(client=mock_client)

        with pytest.raises(NotImplementedError):
            await service.get_order_detail("ORDER123", "123456789")
