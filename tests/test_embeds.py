"""
Embed模板单元测试

测试Discord Embed模板和UI组件
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

import discord

from utils.embeds import (
    EmbedColors,
    EmbedTemplates,
    HelpEmbeds,
    LogisticsEmbeds,
    OrderEmbeds,
    PaginationView,
    ProductEmbeds,
)


@pytest.mark.unit
class TestEmbedColors:
    """Embed颜色常量测试"""

    def test_color_values(self) -> None:
        """测试颜色值"""
        assert EmbedColors.PRIMARY == 0x3498DB
        assert EmbedColors.SUCCESS == 0x2ECC71
        assert EmbedColors.WARNING == 0xF39C12
        assert EmbedColors.ERROR == 0xE74C3C
        assert EmbedColors.INFO == 0x9B59B6


@pytest.mark.unit
class TestEmbedTemplates:
    """Embed模板测试"""

    def test_create_base_embed(self) -> None:
        """测试创建基础Embed"""
        embed = EmbedTemplates.create_base_embed(
            title="测试标题",
            description="测试描述",
            color=EmbedColors.PRIMARY,
        )

        assert isinstance(embed, discord.Embed)
        assert embed.title == "测试标题"
        assert embed.description == "测试描述"
        assert embed.color.value == EmbedColors.PRIMARY

    def test_success_embed(self) -> None:
        """测试成功Embed"""
        embed = EmbedTemplates.success(
            title="操作成功",
            description="任务已完成",
        )

        assert "✅" in embed.title
        assert "操作成功" in embed.title
        assert embed.color.value == EmbedColors.SUCCESS

    def test_error_embed(self) -> None:
        """测试错误Embed"""
        embed = EmbedTemplates.error(
            title="发生错误",
            description="操作失败",
            error_details="详细错误信息",
        )

        assert "❌" in embed.title
        assert embed.color.value == EmbedColors.ERROR

    def test_warning_embed(self) -> None:
        """测试警告Embed"""
        embed = EmbedTemplates.warning(
            title="注意",
            description="请谨慎操作",
        )

        assert "⚠️" in embed.title
        assert embed.color.value == EmbedColors.WARNING

    def test_loading_embed(self) -> None:
        """测试加载中Embed"""
        embed = EmbedTemplates.loading(
            title="处理中",
            description="请稍候...",
        )

        assert "⏳" in embed.title
        assert embed.color.value == EmbedColors.PRIMARY


@pytest.mark.unit
class TestProductEmbeds:
    """商品Embed测试"""

    def test_product_card(self) -> None:
        """测试商品卡片Embed"""
        embed = ProductEmbeds.product_card(
            title="测试商品",
            price="¥99.99",
            platform="淘宝",
            product_url="https://example.com/product/123",
            image_url="https://example.com/image.jpg",
            description="这是一个测试商品",
            shop_name="测试店铺",
            index=1,
        )

        assert isinstance(embed, discord.Embed)
        assert "测试商品" in embed.title
        assert "¥99.99" in embed.description
        assert embed.url == "https://example.com/product/123"

    def test_product_list(self) -> None:
        """测试商品列表Embed"""
        products = [
            {"title": "商品1", "price": "¥100", "platform": "淘宝", "sales": "1000+"},
            {"title": "商品2", "price": "¥200", "platform": "京东", "sales": "500+"},
        ]

        embed = ProductEmbeds.product_list(
            products=products,
            query="手机",
            page=1,
            total_pages=2,
        )

        assert isinstance(embed, discord.Embed)
        assert "手机" in embed.title
        assert len(embed.fields) == 2

    def test_product_comparison(self) -> None:
        """测试商品对比Embed"""
        products = [
            {"title": "商品A", "price": "¥100", "platform": "淘宝", "rating": "4.5", "sales": "1000"},
            {"title": "商品B", "price": "¥150", "platform": "京东", "rating": "4.8", "sales": "500"},
        ]

        embed = ProductEmbeds.product_comparison(products=products)

        assert isinstance(embed, discord.Embed)
        assert "对比" in embed.title
        assert len(embed.fields) == 2


@pytest.mark.unit
class TestOrderEmbeds:
    """订单Embed测试"""

    def test_order_created(self) -> None:
        """测试订单创建成功Embed"""
        order_info = {
            "order_id": "ORD123456",
            "items": [
                {"product_name": "商品1", "quantity": 2},
                {"product_name": "商品2", "quantity": 1},
            ],
            "total_amount": 299.99,
            "currency": "USD",
            "status": "pending",
            "payment_url": "https://payment.example.com/pay/123",
        }

        embed = OrderEmbeds.order_created(order_info)

        assert isinstance(embed, discord.Embed)
        assert "ORD123456" in embed.description
        assert len(embed.fields) >= 3

    def test_order_status(self) -> None:
        """测试订单状态Embed"""
        order_info = {
            "order_id": "ORD123456",
            "status": "shipped",
            "progress": 60,
            "tracking_number": "TRACK789",
            "carrier": "DHL",
            "latest_update": "包裹已到达洛杉矶",
        }

        embed = OrderEmbeds.order_status(order_info)

        assert isinstance(embed, discord.Embed)
        assert "ORD123456" in embed.title
        assert "60%" in embed.description

    def test_order_list(self) -> None:
        """测试订单列表Embed"""
        orders = [
            {"order_id": "ORD001", "status": "pending", "total_amount": 100, "currency": "USD", "created_at": "2024-01-01"},
            {"order_id": "ORD002", "status": "shipped", "total_amount": 200, "currency": "USD", "created_at": "2024-01-02"},
        ]

        embed = OrderEmbeds.order_list(orders=orders, page=1, total=2)

        assert isinstance(embed, discord.Embed)
        assert len(embed.fields) == 2


@pytest.mark.unit
class TestLogisticsEmbeds:
    """物流Embed测试"""

    def test_shipping_estimate(self) -> None:
        """测试运费估算Embed"""
        rates = [
            {"method_name": "标准快递", "estimated_cost": 50, "currency": "USD", "estimated_days_min": 7, "estimated_days_max": 14, "tracking_available": True},
            {"method_name": "特快专递", "estimated_cost": 100, "currency": "USD", "estimated_days_min": 3, "estimated_days_max": 5, "tracking_available": True},
        ]

        embed = LogisticsEmbeds.shipping_estimate(rates=rates, destination="美国")

        assert isinstance(embed, discord.Embed)
        assert "美国" in embed.description
        assert len(embed.fields) == 2

    def test_tracking_info(self) -> None:
        """测试包裹追踪Embed"""
        tracking_data = {
            "tracking_number": "TRACK123",
            "status": "in_transit",
            "status_text": "运输中",
            "carrier": "DHL",
            "estimated_delivery": "2024-01-15",
            "events": [
                {"timestamp": "2024-01-10", "description": "包裹已发货"},
                {"timestamp": "2024-01-11", "description": "到达上海"},
            ],
        }

        embed = LogisticsEmbeds.tracking_info(tracking_data)

        assert isinstance(embed, discord.Embed)
        assert "TRACK123" in embed.title


@pytest.mark.unit
class TestHelpEmbeds:
    """帮助Embed测试"""

    def test_command_help(self) -> None:
        """测试命令帮助Embed"""
        embed = HelpEmbeds.command_help(
            command_name="search",
            description="搜索商品",
            usage="search <关键词>",
            examples=["/search 手机", "/search Nike鞋子"],
            aliases=["find", "s"],
        )

        assert isinstance(embed, discord.Embed)
        assert "search" in embed.title
        assert len(embed.fields) >= 2

    def test_general_help(self) -> None:
        """测试通用帮助Embed"""
        embed = HelpEmbeds.general_help({})

        assert isinstance(embed, discord.Embed)
        assert len(embed.fields) >= 3  # 基础命令、购物命令、物流订单


@pytest.mark.unit
class TestPaginationView:
    """分页视图测试"""

    def test_pagination_view_creation(self) -> None:
        """测试创建分页视图"""
        embeds = [
            discord.Embed(title="页面1"),
            discord.Embed(title="页面2"),
            discord.Embed(title="页面3"),
        ]

        view = PaginationView(embeds=embeds)

        assert view.current_page == 0
        assert view.total_pages == 3
        assert len(view.children) == 5  # 5个按钮

    def test_pagination_view_single_page(self) -> None:
        """测试单页分页视图"""
        embeds = [discord.Embed(title="唯一页面")]

        view = PaginationView(embeds=embeds)

        assert view.total_pages == 1
