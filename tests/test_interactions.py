"""
交互优化模块单元测试

测试Discord交互优化功能
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import discord
from discord.ext import commands

from utils.interactions import (
    ConfirmView,
    InteractionHelper,
    LoadingContext,
    OrderActionView,
    ProductActionView,
    confirm_dialog,
    handle_command_error,
    with_typing_indicator,
)
from utils.embeds import EmbedTemplates


@pytest.mark.unit
class TestLoadingContext:
    """加载上下文测试"""

    @pytest.mark.asyncio
    async def test_loading_context_with_interaction(self, mock_discord_interaction: MagicMock) -> None:
        """测试使用Interaction的加载上下文"""
        mock_discord_interaction.response.is_done.return_value = False

        async with LoadingContext(mock_discord_interaction, message="处理中...") as ctx:
            pass

        mock_discord_interaction.response.defer.assert_called_once()

    @pytest.mark.asyncio
    async def test_loading_context_send_success(self, mock_discord_interaction: MagicMock) -> None:
        """测试发送成功消息"""
        mock_discord_interaction.response.is_done.return_value = True

        async with LoadingContext(mock_discord_interaction) as ctx:
            await ctx.send_success(title="完成", description="操作成功")

        mock_discord_interaction.followup.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_loading_context_send_error(self, mock_discord_interaction: MagicMock) -> None:
        """测试发送错误消息"""
        mock_discord_interaction.response.is_done.return_value = True

        async with LoadingContext(mock_discord_interaction) as ctx:
            await ctx.send_error(title="错误", description="操作失败")

        mock_discord_interaction.followup.send.assert_called_once()


@pytest.mark.unit
class TestConfirmView:
    """确认对话框视图测试"""

    def test_confirm_view_creation(self) -> None:
        """测试创建确认视图"""
        view = ConfirmView(
            confirm_label="确认删除",
            cancel_label="取消",
            timeout=60.0,
        )

        assert view.value is None
        assert len(view.children) == 2  # 确认和取消按钮

    def test_confirm_view_buttons(self) -> None:
        """测试确认视图按钮"""
        view = ConfirmView()

        buttons = [child for child in view.children if isinstance(child, discord.ui.Button)]
        assert len(buttons) == 2

        # 检查按钮标签
        labels = [btn.label for btn in buttons]
        assert "确认" in labels or "取消" in labels


@pytest.mark.unit
class TestProductActionView:
    """商品操作视图测试"""

    def test_product_action_view_creation(self) -> None:
        """测试创建商品操作视图"""
        product_data = {"title": "测试商品", "price": "¥99.99"}

        view = ProductActionView(
            product_url="https://example.com/product/123",
            product_data=product_data,
        )

        assert view.product_url == "https://example.com/product/123"
        assert len(view.children) >= 3  # 查看详情、创建订单、收藏、分享


@pytest.mark.unit
class TestOrderActionView:
    """订单操作视图测试"""

    def test_order_action_view_pending(self) -> None:
        """测试待支付订单的操作视图"""
        view = OrderActionView(
            order_id="ORD123",
            order_status="pending",
        )

        # 待支付订单应该有：查看详情、取消订单、支付按钮
        assert len(view.children) >= 3

    def test_order_action_view_shipped(self) -> None:
        """测试已发货订单的操作视图"""
        view = OrderActionView(
            order_id="ORD123",
            order_status="shipped",
        )

        # 已发货订单应该有：查看详情、追踪物流按钮
        assert len(view.children) >= 2

    def test_order_action_view_delivered(self) -> None:
        """测试已送达订单的操作视图"""
        view = OrderActionView(
            order_id="ORD123",
            order_status="delivered",
        )

        # 已送达订单应该只有：查看详情按钮
        buttons = [child for child in view.children if isinstance(child, discord.ui.Button)]
        assert len(buttons) >= 1


@pytest.mark.unit
@pytest.mark.asyncio
class TestInteractionHelper:
    """交互辅助类测试"""

    async def test_defer_if_needed(self, mock_discord_interaction: MagicMock) -> None:
        """测试延迟响应"""
        mock_discord_interaction.response.is_done.return_value = False

        await InteractionHelper.defer_if_needed(mock_discord_interaction)

        mock_discord_interaction.response.defer.assert_called_once()

    async def test_defer_if_already_done(self, mock_discord_interaction: MagicMock) -> None:
        """测试已响应时不延迟"""
        mock_discord_interaction.response.is_done.return_value = True

        await InteractionHelper.defer_if_needed(mock_discord_interaction)

        mock_discord_interaction.response.defer.assert_not_called()

    async def test_safe_send_with_interaction(self, mock_discord_interaction: MagicMock) -> None:
        """测试安全发送消息（Interaction）"""
        mock_discord_interaction.response.is_done.return_value = False

        embed = EmbedTemplates.success(title="测试")
        await InteractionHelper.safe_send(
            mock_discord_interaction,
            embed=embed,
        )

        mock_discord_interaction.response.send_message.assert_called_once()

    async def test_safe_send_with_context(self) -> None:
        """测试安全发送消息（Context）"""
        mock_ctx = MagicMock()
        mock_ctx.send = AsyncMock()

        embed = EmbedTemplates.success(title="测试")
        await InteractionHelper.safe_send(mock_ctx, embed=embed)

        mock_ctx.send.assert_called_once()


@pytest.mark.unit
class TestHandleCommandError:
    """命令错误处理测试"""

    @pytest.mark.asyncio
    async def test_missing_required_argument(self, mock_discord_interaction: MagicMock) -> None:
        """测试缺少必需参数错误"""
        error = commands.MissingRequiredArgument(
            param=MagicMock(name="keyword")
        )

        await handle_command_error(mock_discord_interaction, error, log_error=False)

        mock_discord_interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_bad_argument(self, mock_discord_interaction: MagicMock) -> None:
        """测试参数格式错误"""
        error = commands.BadArgument("参数格式不正确")

        await handle_command_error(mock_discord_interaction, error, log_error=False)

        mock_discord_interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_missing_permissions(self, mock_discord_interaction: MagicMock) -> None:
        """测试权限不足错误"""
        error = commands.MissingPermissions(["administrator"])

        await handle_command_error(mock_discord_interaction, error, log_error=False)

        mock_discord_interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_command_on_cooldown(self, mock_discord_interaction: MagicMock) -> None:
        """测试命令冷却中错误"""
        error = commands.CommandOnCooldown(MagicMock(), retry_after=30.0)

        await handle_command_error(mock_discord_interaction, error, log_error=False)

        mock_discord_interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_command_not_found(self, mock_discord_message: MagicMock) -> None:
        """测试命令不存在错误（应静默处理）"""
        error = commands.CommandNotFound("未知命令")

        # 创建mock context
        mock_ctx = MagicMock()
        mock_ctx.send = AsyncMock()

        await handle_command_error(mock_ctx, error, log_error=False)

        # 命令不存在时不应发送任何消息
        mock_ctx.send.assert_not_called()


@pytest.mark.unit
class TestWithTypingIndicator:
    """Typing指示器装饰器测试"""

    def test_decorator_creation(self) -> None:
        """测试装饰器创建"""
        decorator = with_typing_indicator(message="处理中...")

        assert callable(decorator)

    def test_decorator_with_function(self) -> None:
        """测试装饰器应用于函数"""
        decorator = with_typing_indicator(message="处理中...")

        async def test_func(ctx):
            return "result"

        decorated = decorator(test_func)

        assert decorated.__name__ == "test_func"
