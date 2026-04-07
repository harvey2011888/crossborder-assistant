"""
交互优化模块

提供Discord Bot的交互优化功能，包括加载状态提示、错误处理、确认对话框、快捷操作按钮等
"""

import functools
import logging
from typing import Any, Callable, Coroutine, Optional, TypeVar

import discord
from discord.ext import commands

from utils.embeds import EmbedTemplates

# 配置日志
logger = logging.getLogger(__name__)

# 类型变量
T = TypeVar("T")
ContextType = TypeVar("ContextType", discord.Interaction, commands.Context)


class LoadingContext:
    """加载状态上下文管理器"""

    def __init__(
        self,
        ctx: ContextType,
        message: str = "处理中...",
        ephemeral: bool = False,
    ) -> None:
        """
        初始化加载上下文

        Args:
            ctx: Discord上下文（Interaction或Context）
            message: 加载提示消息
            ephemeral: 是否仅对用户可见
        """
        self.ctx = ctx
        self.message = message
        self.ephemeral = ephemeral
        self._original_message: Optional[discord.Message] = None
        self._is_interaction = isinstance(ctx, discord.Interaction)

    async def __aenter__(self) -> "LoadingContext":
        """进入上下文，显示加载状态"""
        try:
            if self._is_interaction:
                # 对于Interaction，使用typing指示器
                interaction = self.ctx
                if not interaction.response.is_done():
                    await interaction.response.defer(ephemeral=self.ephemeral, thinking=True)
            else:
                # 对于传统Context，发送加载消息
                embed = EmbedTemplates.loading(description=self.message)
                self._original_message = await self.ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"显示加载状态失败: {e}")
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """退出上下文，清理加载状态"""
        # 清理工作由调用方处理（更新消息或删除）
        pass

    async def send_success(
        self,
        title: str = "完成",
        description: str = "操作已完成",
        **kwargs: Any,
    ) -> Optional[discord.Message]:
        """
        发送成功消息

        Args:
            title: 标题
            description: 描述
            **kwargs: 其他参数

        Returns:
            发送的消息对象
        """
        embed = EmbedTemplates.success(title=title, description=description, **kwargs)
        return await self._send_response(embed=embed)

    async def send_error(
        self,
        title: str = "错误",
        description: str = "操作失败",
        **kwargs: Any,
    ) -> Optional[discord.Message]:
        """
        发送错误消息

        Args:
            title: 标题
            description: 描述
            **kwargs: 其他参数

        Returns:
            发送的消息对象
        """
        embed = EmbedTemplates.error(title=title, description=description, **kwargs)
        return await self._send_response(embed=embed)

    async def send_warning(
        self,
        title: str = "警告",
        description: str = "请注意",
        **kwargs: Any,
    ) -> Optional[discord.Message]:
        """
        发送警告消息

        Args:
            title: 标题
            description: 描述
            **kwargs: 其他参数

        Returns:
            发送的消息对象
        """
        embed = EmbedTemplates.warning(title=title, description=description, **kwargs)
        return await self._send_response(embed=embed)

    async def _send_response(self, embed: discord.Embed) -> Optional[discord.Message]:
        """
        发送响应消息

        Args:
            embed: 要发送的Embed

        Returns:
            发送的消息对象
        """
        try:
            if self._is_interaction:
                interaction = self.ctx
                if interaction.response.is_done():
                    # 如果已经defer，使用followup
                    return await interaction.followup.send(embed=embed, ephemeral=self.ephemeral)
                else:
                    # 否则直接响应
                    await interaction.response.send_message(embed=embed, ephemeral=self.ephemeral)
                    return None
            else:
                # 传统Context，编辑或发送新消息
                if self._original_message:
                    return await self._original_message.edit(embed=embed)
                else:
                    return await self.ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"发送响应消息失败: {e}")
            return None


def with_typing_indicator(
    message: str = "处理中，请稍候...",
) -> Callable[[Callable[..., Coroutine[Any, Any, T]]], Callable[..., Coroutine[Any, Any, T]]]:
    """
    装饰器：为命令添加typing指示器

    Args:
        message: 加载提示消息

    Returns:
        装饰器函数
    """
    def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            # 找到上下文参数
            ctx = None
            for arg in args:
                if isinstance(arg, (commands.Context, discord.Interaction)):
                    ctx = arg
                    break

            if ctx is None:
                # 没有找到上下文，直接执行
                return await func(*args, **kwargs)

            async with LoadingContext(ctx, message=message):
                return await func(*args, **kwargs)

        return wrapper
    return decorator


class ConfirmView(discord.ui.View):
    """确认对话框视图"""

    def __init__(
        self,
        confirm_label: str = "确认",
        cancel_label: str = "取消",
        confirm_style: discord.ButtonStyle = discord.ButtonStyle.danger,
        cancel_style: discord.ButtonStyle = discord.ButtonStyle.secondary,
        timeout: float = 60.0,
    ) -> None:
        """
        初始化确认对话框

        Args:
            confirm_label: 确认按钮文本
            cancel_label: 取消按钮文本
            confirm_style: 确认按钮样式
            cancel_style: 取消按钮样式
            timeout: 超时时间（秒）
        """
        super().__init__(timeout=timeout)
        self.confirm_label = confirm_label
        self.cancel_label = cancel_label
        self.confirm_style = confirm_style
        self.cancel_style = cancel_style
        self.value: Optional[bool] = None
        self.interaction: Optional[discord.Interaction] = None

        # 添加按钮
        self._add_buttons()

    def _add_buttons(self) -> None:
        """添加确认和取消按钮"""
        # 确认按钮
        confirm_btn = discord.ui.Button(
            label=self.confirm_label,
            style=self.confirm_style,
            custom_id="confirm",
        )
        confirm_btn.callback = self._on_confirm
        self.add_item(confirm_btn)

        # 取消按钮
        cancel_btn = discord.ui.Button(
            label=self.cancel_label,
            style=self.cancel_style,
            custom_id="cancel",
        )
        cancel_btn.callback = self._on_cancel
        self.add_item(cancel_btn)

    async def _on_confirm(self, interaction: discord.Interaction) -> None:
        """确认按钮回调"""
        self.value = True
        self.interaction = interaction
        self.stop()

    async def _on_cancel(self, interaction: discord.Interaction) -> None:
        """取消按钮回调"""
        self.value = False
        self.interaction = interaction
        self.stop()

    async def on_timeout(self) -> None:
        """超时处理"""
        self.value = None
        # 禁用所有按钮
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True


async def confirm_dialog(
    ctx: ContextType,
    title: str = "确认操作",
    description: str = "您确定要执行此操作吗？",
    confirm_label: str = "确认",
    cancel_label: str = "取消",
    ephemeral: bool = True,
    timeout: float = 60.0,
) -> tuple[bool, Optional[discord.Interaction]]:
    """
    显示确认对话框

    Args:
        ctx: Discord上下文
        title: 对话框标题
        description: 对话框描述
        confirm_label: 确认按钮文本
        cancel_label: 取消按钮文本
        ephemeral: 是否仅对用户可见
        timeout: 超时时间（秒）

    Returns:
        (是否确认, 交互对象) 元组，超时返回 (None, None)
    """
    embed = EmbedTemplates.warning(title=title, description=description)
    view = ConfirmView(
        confirm_label=confirm_label,
        cancel_label=cancel_label,
        timeout=timeout,
    )

    # 发送确认对话框
    if isinstance(ctx, discord.Interaction):
        if ctx.response.is_done():
            message = await ctx.followup.send(embed=embed, view=view, ephemeral=ephemeral)
        else:
            await ctx.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
            message = None
    else:
        message = await ctx.send(embed=embed, view=view)

    # 等待用户响应
    await view.wait()

    # 更新消息，禁用按钮
    if view.interaction:
        for child in view.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        await view.interaction.response.edit_message(view=view)
    elif message:
        for child in view.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        await message.edit(view=view)

    return view.value, view.interaction


class ProductActionView(discord.ui.View):
    """商品操作按钮视图"""

    def __init__(
        self,
        product_url: str,
        product_data: dict[str, Any],
        timeout: float = 180.0,
    ) -> None:
        """
        初始化商品操作视图

        Args:
            product_url: 商品链接
            product_data: 商品数据
            timeout: 超时时间（秒）
        """
        super().__init__(timeout=timeout)
        self.product_url = product_url
        self.product_data = product_data

        # 添加按钮
        self._add_buttons()

    def _add_buttons(self) -> None:
        """添加操作按钮"""
        # 查看详情按钮
        details_btn = discord.ui.Button(
            label="查看详情",
            style=discord.ButtonStyle.link,
            url=self.product_url,
            emoji="🔗",
        )
        self.add_item(details_btn)

        # 创建订单按钮
        order_btn = discord.ui.Button(
            label="创建订单",
            style=discord.ButtonStyle.primary,
            custom_id="create_order",
            emoji="🛒",
        )
        order_btn.callback = self._on_create_order
        self.add_item(order_btn)

        # 添加到收藏按钮
        favorite_btn = discord.ui.Button(
            label="收藏",
            style=discord.ButtonStyle.secondary,
            custom_id="add_favorite",
            emoji="⭐",
        )
        favorite_btn.callback = self._on_add_favorite
        self.add_item(favorite_btn)

        # 分享按钮
        share_btn = discord.ui.Button(
            label="分享",
            style=discord.ButtonStyle.secondary,
            custom_id="share",
            emoji="📤",
        )
        share_btn.callback = self._on_share
        self.add_item(share_btn)

    async def _on_create_order(self, interaction: discord.Interaction) -> None:
        """创建订单按钮回调"""
        # TODO: 实现创建订单逻辑
        embed = EmbedTemplates.info(
            title="创建订单",
            description="订单功能即将上线，敬请期待！",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _on_add_favorite(self, interaction: discord.Interaction) -> None:
        """添加到收藏按钮回调"""
        # TODO: 实现收藏逻辑
        embed = EmbedTemplates.success(
            title="已收藏",
            description="商品已添加到您的收藏列表！",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _on_share(self, interaction: discord.Interaction) -> None:
        """分享按钮回调"""
        product_title = self.product_data.get("title", "商品")
        share_text = f"发现好物：{product_title}\n{self.product_url}"

        embed = EmbedTemplates.info(
            title="分享商品",
            description=f"```\n{share_text}\n```",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class OrderActionView(discord.ui.View):
    """订单操作按钮视图"""

    def __init__(
        self,
        order_id: str,
        order_status: str,
        timeout: float = 180.0,
    ) -> None:
        """
        初始化订单操作视图

        Args:
            order_id: 订单号
            order_status: 订单状态
            timeout: 超时时间（秒）
        """
        super().__init__(timeout=timeout)
        self.order_id = order_id
        self.order_status = order_status

        # 根据状态添加可用按钮
        self._add_buttons()

    def _add_buttons(self) -> None:
        """根据订单状态添加操作按钮"""
        # 查看详情按钮
        details_btn = discord.ui.Button(
            label="查看详情",
            style=discord.ButtonStyle.primary,
            custom_id="view_details",
            emoji="📋",
        )
        details_btn.callback = self._on_view_details
        self.add_item(details_btn)

        # 追踪物流按钮（如果已发货）
        if self.order_status in ["shipped", "delivered"]:
            track_btn = discord.ui.Button(
                label="追踪物流",
                style=discord.ButtonStyle.secondary,
                custom_id="track",
                emoji="🚚",
            )
            track_btn.callback = self._on_track
            self.add_item(track_btn)

        # 取消订单按钮（如果待支付）
        if self.order_status == "pending":
            cancel_btn = discord.ui.Button(
                label="取消订单",
                style=discord.ButtonStyle.danger,
                custom_id="cancel",
                emoji="❌",
            )
            cancel_btn.callback = self._on_cancel
            self.add_item(cancel_btn)

        # 支付按钮（如果待支付）
        if self.order_status == "pending":
            pay_btn = discord.ui.Button(
                label="立即支付",
                style=discord.ButtonStyle.success,
                custom_id="pay",
                emoji="💳",
            )
            pay_btn.callback = self._on_pay
            self.add_item(pay_btn)

    async def _on_view_details(self, interaction: discord.Interaction) -> None:
        """查看详情按钮回调"""
        embed = EmbedTemplates.info(
            title="订单详情",
            description=f"订单号: {self.order_id}",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _on_track(self, interaction: discord.Interaction) -> None:
        """追踪物流按钮回调"""
        embed = EmbedTemplates.info(
            title="物流追踪",
            description=f"订单号: {self.order_id}\n\n物流追踪功能即将上线！",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _on_cancel(self, interaction: discord.Interaction) -> None:
        """取消订单按钮回调"""
        # 显示确认对话框
        confirmed, _ = await confirm_dialog(
            interaction,
            title="确认取消订单",
            description=f"您确定要取消订单 **{self.order_id}** 吗？",
            confirm_label="确认取消",
            cancel_label="保留订单",
        )

        if confirmed:
            # TODO: 实现取消订单逻辑
            embed = EmbedTemplates.success(
                title="订单已取消",
                description=f"订单 **{self.order_id}** 已成功取消。",
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    async def _on_pay(self, interaction: discord.Interaction) -> None:
        """支付按钮回调"""
        embed = EmbedTemplates.info(
            title="订单支付",
            description=f"订单号: {self.order_id}\n\n支付功能即将上线！",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def handle_command_error(
    ctx: ContextType,
    error: Exception,
    log_error: bool = True,
) -> None:
    """
    统一处理命令错误

    Args:
        ctx: Discord上下文
        error: 异常对象
        log_error: 是否记录错误日志
    """
    if log_error:
        logger.error(f"命令执行错误: {error}", exc_info=True)

    # 根据错误类型返回不同提示
    if isinstance(error, commands.MissingRequiredArgument):
        embed = EmbedTemplates.error(
            title="参数错误",
            description=f"缺少必需参数: `{error.param.name}`",
        )
    elif isinstance(error, commands.BadArgument):
        embed = EmbedTemplates.error(
            title="参数格式错误",
            description=str(error),
        )
    elif isinstance(error, commands.CommandNotFound):
        # 不响应未知命令
        return
    elif isinstance(error, commands.MissingPermissions):
        embed = EmbedTemplates.error(
            title="权限不足",
            description="您没有执行此命令的权限。",
        )
    elif isinstance(error, commands.BotMissingPermissions):
        embed = EmbedTemplates.error(
            title="Bot权限不足",
            description=f"Bot缺少以下权限: {', '.join(error.missing_permissions)}",
        )
    elif isinstance(error, commands.CommandOnCooldown):
        embed = EmbedTemplates.warning(
            title="冷却中",
            description=f"请等待 {error.retry_after:.1f} 秒后重试。",
        )
    else:
        # 未知错误
        embed = EmbedTemplates.error(
            title="执行错误",
            description="执行命令时发生错误，请稍后重试。",
            error_details=str(error)[:500],
        )

    # 发送错误消息
    try:
        if isinstance(ctx, discord.Interaction):
            if ctx.response.is_done():
                await ctx.followup.send(embed=embed, ephemeral=True)
            else:
                await ctx.response.send_message(embed=embed, ephemeral=True)
        else:
            await ctx.send(embed=embed)
    except Exception as e:
        logger.error(f"发送错误消息失败: {e}")


class InteractionHelper:
    """交互辅助类"""

    @staticmethod
    async def defer_if_needed(
        interaction: discord.Interaction,
        ephemeral: bool = False,
    ) -> None:
        """
        如果需要，延迟响应

        Args:
            interaction: Discord交互对象
            ephemeral: 是否仅对用户可见
        """
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=ephemeral)

    @staticmethod
    async def safe_send(
        ctx: ContextType,
        content: Optional[str] = None,
        embed: Optional[discord.Embed] = None,
        view: Optional[discord.ui.View] = None,
        ephemeral: bool = False,
    ) -> Optional[discord.Message]:
        """
        安全发送消息

        Args:
            ctx: Discord上下文
            content: 消息内容
            embed: Embed对象
            view: 视图对象
            ephemeral: 是否仅对用户可见

        Returns:
            发送的消息对象
        """
        try:
            if isinstance(ctx, discord.Interaction):
                if ctx.response.is_done():
                    return await ctx.followup.send(
                        content=content,
                        embed=embed,
                        view=view,
                        ephemeral=ephemeral,
                    )
                else:
                    await ctx.response.send_message(
                        content=content,
                        embed=embed,
                        view=view,
                        ephemeral=ephemeral,
                    )
                    return None
            else:
                return await ctx.send(
                    content=content,
                    embed=embed,
                    view=view,
                )
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return None

    @staticmethod
    async def safe_edit(
        message: discord.Message,
        content: Optional[str] = None,
        embed: Optional[discord.Embed] = None,
        view: Optional[discord.ui.View] = None,
    ) -> Optional[discord.Message]:
        """
        安全编辑消息

        Args:
            message: 要编辑的消息
            content: 新内容
            embed: 新Embed
            view: 新视图

        Returns:
            编辑后的消息对象
        """
        try:
            return await message.edit(
                content=content,
                embed=embed,
                view=view,
            )
        except Exception as e:
            logger.error(f"编辑消息失败: {e}")
            return None
