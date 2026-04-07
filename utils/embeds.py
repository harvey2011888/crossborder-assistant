"""
Discord Embed模板模块

提供统一的Discord消息Embed模板，用于商品展示、订单信息、物流追踪等
"""

from datetime import datetime
from typing import Any, Optional

import discord


class EmbedColors:
    """Embed颜色常量"""

    PRIMARY = 0x3498DB  # 蓝色 - 主要信息
    SUCCESS = 0x2ECC71  # 绿色 - 成功
    WARNING = 0xF39C12  # 橙色 - 警告
    ERROR = 0xE74C3C  # 红色 - 错误
    INFO = 0x9B59B6  # 紫色 - 信息
    GOLD = 0xF1C40F  # 金色 - 特殊
    DARK = 0x2C3E50  # 深色 - 中性


class EmbedTemplates:
    """Discord Embed模板类"""

    @staticmethod
    def create_base_embed(
        title: Optional[str] = None,
        description: Optional[str] = None,
        color: int = EmbedColors.PRIMARY,
        url: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> discord.Embed:
        """
        创建基础Embed

        Args:
            title: 标题
            description: 描述
            color: 颜色
            url: 链接URL
            timestamp: 时间戳

        Returns:
            discord.Embed实例
        """
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            url=url,
            timestamp=timestamp or datetime.now(),
        )
        return embed

    @staticmethod
    def success(
        title: str = "成功",
        description: str = "操作已成功完成",
        **kwargs: Any,
    ) -> discord.Embed:
        """
        成功提示Embed

        Args:
            title: 标题
            description: 描述
            **kwargs: 其他参数

        Returns:
            成功样式的Embed
        """
        embed = EmbedTemplates.create_base_embed(
            title=f"✅ {title}",
            description=description,
            color=EmbedColors.SUCCESS,
            **kwargs,
        )
        return embed

    @staticmethod
    def error(
        title: str = "错误",
        description: str = "操作失败",
        error_details: Optional[str] = None,
        **kwargs: Any,
    ) -> discord.Embed:
        """
        错误提示Embed

        Args:
            title: 标题
            description: 描述
            error_details: 错误详情
            **kwargs: 其他参数

        Returns:
            错误样式的Embed
        """
        embed = EmbedTemplates.create_base_embed(
            title=f"❌ {title}",
            description=description,
            color=EmbedColors.ERROR,
            **kwargs,
        )
        if error_details:
            embed.add_field(
                name="错误详情",
                value=f"```\n{error_details[:1000]}\n```",
                inline=False,
            )
        return embed

    @staticmethod
    def warning(
        title: str = "警告",
        description: str = "请注意",
        **kwargs: Any,
    ) -> discord.Embed:
        """
        警告提示Embed

        Args:
            title: 标题
            description: 描述
            **kwargs: 其他参数

        Returns:
            警告样式的Embed
        """
        embed = EmbedTemplates.create_base_embed(
            title=f"⚠️ {title}",
            description=description,
            color=EmbedColors.WARNING,
            **kwargs,
        )
        return embed

    @staticmethod
    def info(
        title: str = "信息",
        description: str = "",
        **kwargs: Any,
    ) -> discord.Embed:
        """
        信息提示Embed

        Args:
            title: 标题
            description: 描述
            **kwargs: 其他参数

        Returns:
            信息样式的Embed
        """
        embed = EmbedTemplates.create_base_embed(
            title=f"ℹ️ {title}",
            description=description,
            color=EmbedColors.INFO,
            **kwargs,
        )
        return embed

    @staticmethod
    def loading(
        title: str = "处理中",
        description: str = "请稍候...",
        **kwargs: Any,
    ) -> discord.Embed:
        """
        加载中提示Embed

        Args:
            title: 标题
            description: 描述
            **kwargs: 其他参数

        Returns:
            加载中样式的Embed
        """
        embed = EmbedTemplates.create_base_embed(
            title=f"⏳ {title}",
            description=description,
            color=EmbedColors.PRIMARY,
            **kwargs,
        )
        return embed


class ProductEmbeds:
    """商品相关Embed模板"""

    @staticmethod
    def product_card(
        title: str,
        price: str,
        platform: str,
        product_url: str,
        image_url: Optional[str] = None,
        description: Optional[str] = None,
        original_price: Optional[str] = None,
        rating: Optional[str] = None,
        sales: Optional[str] = None,
        shop_name: Optional[str] = None,
        index: Optional[int] = None,
    ) -> discord.Embed:
        """
        创建商品卡片Embed

        Args:
            title: 商品标题
            price: 当前价格
            platform: 电商平台（淘宝/京东等）
            product_url: 商品链接
            image_url: 商品图片URL
            description: 商品描述
            original_price: 原价
            rating: 评分
            sales: 销量
            shop_name: 店铺名称
            index: 序号（用于列表展示）

        Returns:
            商品卡片Embed
        """
        # 构建标题
        display_title = title
        if index is not None:
            display_title = f"{index}. {title}"

        # 构建价格显示
        price_display = f"**{price}**"
        if original_price:
            price_display += f" ~~{original_price}~~"

        # 构建描述
        description_parts = [f"💰 {price_display}"]

        if rating:
            description_parts.append(f"⭐ {rating}")
        if sales:
            description_parts.append(f"📊 {sales}")
        if shop_name:
            description_parts.append(f"🏪 {shop_name}")

        embed_description = " | ".join(description_parts)

        if description:
            embed_description += f"\n\n{description[:200]}..."

        embed = discord.Embed(
            title=display_title[:256],  # Discord标题限制256字符
            description=embed_description,
            color=EmbedColors.GOLD,
            url=product_url,
            timestamp=datetime.now(),
        )

        # 添加平台标识
        platform_emoji = {"淘宝": "🛒", "京东": "📦", "天猫": "🏬"}.get(platform, "🛍️")
        embed.set_author(name=f"{platform_emoji} {platform}")

        # 设置图片
        if image_url:
            embed.set_thumbnail(url=image_url)

        # 添加页脚
        embed.set_footer(text="点击标题查看商品详情")

        return embed

    @staticmethod
    def product_list(
        products: list[dict[str, Any]],
        query: str,
        page: int = 1,
        total_pages: int = 1,
    ) -> discord.Embed:
        """
        创建商品列表Embed

        Args:
            products: 商品列表数据
            query: 搜索关键词
            page: 当前页码
            total_pages: 总页数

        Returns:
            商品列表Embed
        """
        embed = discord.Embed(
            title=f"🔍 搜索结果: {query}",
            description=f"找到 {len(products)} 件商品",
            color=EmbedColors.PRIMARY,
            timestamp=datetime.now(),
        )

        for i, product in enumerate(products[:10], 1):  # 最多显示10个
            index = (page - 1) * 10 + i
            title = product.get("title", "未知商品")
            price = product.get("price", "价格未知")
            platform = product.get("platform", "未知平台")

            field_value = f"💰 {price} | 🛒 {platform}"
            if product.get("sales"):
                field_value += f" | 📊 {product['sales']}"

            embed.add_field(
                name=f"{index}. {title[:50]}{'...' if len(title) > 50 else ''}",
                value=field_value,
                inline=False,
            )

        embed.set_footer(text=f"第 {page}/{total_pages} 页")
        return embed

    @staticmethod
    def product_comparison(
        products: list[dict[str, Any]],
    ) -> discord.Embed:
        """
        创建商品对比Embed

        Args:
            products: 要对比的商品列表（2-3个）

        Returns:
            商品对比Embed
        """
        embed = discord.Embed(
            title="📊 商品对比",
            description="对比以下商品",
            color=EmbedColors.INFO,
            timestamp=datetime.now(),
        )

        for i, product in enumerate(products[:3], 1):
            title = product.get("title", "未知商品")
            price = product.get("price", "价格未知")
            platform = product.get("platform", "未知平台")
            rating = product.get("rating", "无评分")
            sales = product.get("sales", "销量未知")

            value = (
                f"💰 **价格**: {price}\n"
                f"🛒 **平台**: {platform}\n"
                f"⭐ **评分**: {rating}\n"
                f"📊 **销量**: {sales}"
            )

            embed.add_field(
                name=f"商品 {i}: {title[:40]}{'...' if len(title) > 40 else ''}",
                value=value,
                inline=True,
            )

        return embed


class OrderEmbeds:
    """订单相关Embed模板"""

    @staticmethod
    def order_created(order_info: dict[str, Any]) -> discord.Embed:
        """
        订单创建成功Embed

        Args:
            order_info: 订单信息字典

        Returns:
            订单创建成功Embed
        """
        embed = discord.Embed(
            title="✅ 订单创建成功",
            description=f"订单号: **{order_info.get('order_id', 'N/A')}**",
            color=EmbedColors.SUCCESS,
            timestamp=datetime.now(),
        )

        # 添加商品信息
        items = order_info.get("items", [])
        if items:
            items_text = "\n".join([
                f"• {item.get('product_name', '未知商品')} x{item.get('quantity', 1)}"
                for item in items[:5]  # 最多显示5个商品
            ])
            embed.add_field(name="🛍️ 商品", value=items_text, inline=False)

        # 添加金额信息
        total = order_info.get("total_amount", "N/A")
        currency = order_info.get("currency", "USD")
        embed.add_field(name="💰 订单金额", value=f"{total} {currency}", inline=True)

        # 添加状态
        status = order_info.get("status", "pending")
        status_emoji = {"pending": "⏳", "paid": "✅", "cancelled": "❌"}.get(status, "📋")
        embed.add_field(name="📋 状态", value=f"{status_emoji} {status}", inline=True)

        # 添加支付链接
        payment_url = order_info.get("payment_url")
        if payment_url:
            embed.add_field(
                name="💳 支付",
                value=f"[点击支付]({payment_url})",
                inline=False,
            )

        return embed

    @staticmethod
    def order_status(order_info: dict[str, Any]) -> discord.Embed:
        """
        订单状态Embed

        Args:
            order_info: 订单信息字典

        Returns:
            订单状态Embed
        """
        status = order_info.get("status", "unknown")
        status_colors = {
            "pending": EmbedColors.WARNING,
            "paid": EmbedColors.INFO,
            "shipped": EmbedColors.PRIMARY,
            "delivered": EmbedColors.SUCCESS,
            "cancelled": EmbedColors.ERROR,
        }

        embed = discord.Embed(
            title=f"📦 订单状态: {order_info.get('order_id', 'N/A')}",
            color=status_colors.get(status, EmbedColors.DARK),
            timestamp=datetime.now(),
        )

        # 状态进度条
        progress = order_info.get("progress", 0)
        progress_bar = "▓" * (progress // 10) + "░" * (10 - progress // 10)
        embed.description = f"{progress_bar} {progress}%"

        # 添加追踪信息
        tracking_number = order_info.get("tracking_number")
        if tracking_number:
            carrier = order_info.get("carrier", "未知物流")
            embed.add_field(
                name="🚚 物流信息",
                value=f"承运商: {carrier}\n单号: `{tracking_number}`",
                inline=False,
            )

        # 添加最新更新
        latest_update = order_info.get("latest_update")
        if latest_update:
            embed.add_field(name="📝 最新动态", value=latest_update, inline=False)

        return embed

    @staticmethod
    def order_list(
        orders: list[dict[str, Any]],
        page: int = 1,
        total: int = 0,
    ) -> discord.Embed:
        """
        订单列表Embed

        Args:
            orders: 订单列表
            page: 当前页码
            total: 总订单数

        Returns:
            订单列表Embed
        """
        embed = discord.Embed(
            title="📋 我的订单",
            description=f"共 {total} 个订单",
            color=EmbedColors.PRIMARY,
            timestamp=datetime.now(),
        )

        status_emoji = {
            "pending": "⏳",
            "paid": "💰",
            "shipped": "🚚",
            "delivered": "✅",
            "cancelled": "❌",
        }

        for order in orders[:5]:  # 每页最多5个
            order_id = order.get("order_id", "N/A")
            status = order.get("status", "unknown")
            total_amount = order.get("total_amount", "N/A")
            currency = order.get("currency", "USD")
            created_at = order.get("created_at", "未知时间")

            emoji = status_emoji.get(status, "📦")
            value = f"{emoji} {status} | 💰 {total_amount} {currency} | 📅 {created_at}"

            embed.add_field(
                name=f"订单: {order_id}",
                value=value,
                inline=False,
            )

        embed.set_footer(text=f"第 {page} 页")
        return embed


class LogisticsEmbeds:
    """物流相关Embed模板"""

    @staticmethod
    def shipping_estimate(rates: list[dict[str, Any]], destination: str) -> discord.Embed:
        """
        运费估算Embed

        Args:
            rates: 运费选项列表
            destination: 目的地

        Returns:
            运费估算Embed
        """
        embed = discord.Embed(
            title="💰 运费估算",
            description=f"目的地: **{destination}**",
            color=EmbedColors.INFO,
            timestamp=datetime.now(),
        )

        for rate in rates[:5]:  # 最多显示5个选项
            method = rate.get("method_name", "未知方式")
            cost = rate.get("estimated_cost", "N/A")
            currency = rate.get("currency", "USD")
            days_min = rate.get("estimated_days_min", "?")
            days_max = rate.get("estimated_days_max", "?")

            value = f"💵 {cost} {currency}\n⏱️ {days_min}-{days_max} 天"

            if rate.get("tracking_available"):
                value += "\n📍 支持追踪"

            embed.add_field(
                name=f"🚚 {method}",
                value=value,
                inline=True,
            )

        return embed

    @staticmethod
    def tracking_info(tracking_data: dict[str, Any]) -> discord.Embed:
        """
        包裹追踪Embed

        Args:
            tracking_data: 追踪数据

        Returns:
            包裹追踪Embed
        """
        status = tracking_data.get("status", "unknown")
        status_colors = {
            "pending": EmbedColors.WARNING,
            "in_transit": EmbedColors.PRIMARY,
            "delivered": EmbedColors.SUCCESS,
            "exception": EmbedColors.ERROR,
        }

        embed = discord.Embed(
            title=f"📦 包裹追踪: {tracking_data.get('tracking_number', 'N/A')}",
            color=status_colors.get(status, EmbedColors.DARK),
            timestamp=datetime.now(),
        )

        # 当前状态
        status_text = tracking_data.get("status_text", "未知状态")
        embed.add_field(name="📋 当前状态", value=status_text, inline=True)

        # 承运商
        carrier = tracking_data.get("carrier", "未知")
        embed.add_field(name="🚚 承运商", value=carrier, inline=True)

        # 预计送达
        estimated = tracking_data.get("estimated_delivery")
        if estimated:
            embed.add_field(name="📅 预计送达", value=str(estimated), inline=True)

        # 最近事件
        events = tracking_data.get("events", [])
        if events:
            recent_events = events[:3]  # 最近3个事件
            events_text = "\n".join([
                f"• {event.get('timestamp', '')}: {event.get('description', '')}"
                for event in recent_events
            ])
            embed.add_field(
                name="📝 最近动态",
                value=events_text[:1024],  # Discord字段限制
                inline=False,
            )

        # 承运商链接
        carrier_url = tracking_data.get("carrier_url")
        if carrier_url:
            embed.add_field(
                name="🔗 追踪链接",
                value=f"[在官网追踪]({carrier_url})",
                inline=False,
            )

        return embed


class HelpEmbeds:
    """帮助相关Embed模板"""

    @staticmethod
    def command_help(
        command_name: str,
        description: str,
        usage: str,
        examples: Optional[list[str]] = None,
        aliases: Optional[list[str]] = None,
    ) -> discord.Embed:
        """
        命令帮助Embed

        Args:
            command_name: 命令名称
            description: 命令描述
            usage: 使用方法
            examples: 使用示例列表
            aliases: 命令别名列表

        Returns:
            命令帮助Embed
        """
        embed = discord.Embed(
            title=f"📖 命令帮助: /{command_name}",
            description=description,
            color=EmbedColors.INFO,
            timestamp=datetime.now(),
        )

        embed.add_field(name="📝 用法", value=f"`/{usage}`", inline=False)

        if aliases:
            embed.add_field(
                name="🏷️ 别名",
                value=", ".join([f"`{alias}`" for alias in aliases]),
                inline=True,
            )

        if examples:
            examples_text = "\n".join([f"• `{ex}`" for ex in examples])
            embed.add_field(name="💡 示例", value=examples_text, inline=False)

        return embed

    @staticmethod
    def general_help(commands: dict[str, str]) -> discord.Embed:
        """
        通用帮助Embed

        Args:
            commands: 命令名称和描述的字典

        Returns:
            通用帮助Embed
        """
        embed = discord.Embed(
            title="🤖 跨境电商智能助手",
            description="欢迎使用跨境电商智能助手！我可以帮你搜索商品、查询物流、管理订单。",
            color=EmbedColors.PRIMARY,
            timestamp=datetime.now(),
        )

        # 基础命令
        general_cmds = [
            ("/help", "显示帮助信息"),
            ("/start", "开始使用引导"),
            ("/settings", "用户设置"),
        ]
        general_text = "\n".join([f"`{cmd}` - {desc}" for cmd, desc in general_cmds])
        embed.add_field(name="📋 基础命令", value=general_text, inline=False)

        # 购物命令
        shopping_cmds = [
            ("/search <关键词>", "搜索商品"),
            ("/recommend", "智能推荐"),
            ("/compare <商品1> <商品2>", "商品对比"),
        ]
        shopping_text = "\n".join([f"`{cmd}` - {desc}" for cmd, desc in shopping_cmds])
        embed.add_field(name="🛍️ 购物命令", value=shopping_text, inline=False)

        # 物流和订单命令
        other_cmds = [
            ("/shipping <重量> <目的地>", "运费估算"),
            ("/track <运单号>", "包裹追踪"),
            ("/order list", "查看订单"),
        ]
        other_text = "\n".join([f"`{cmd}` - {desc}" for cmd, desc in other_cmds])
        embed.add_field(name="📦 物流与订单", value=other_text, inline=False)

        embed.set_footer(text="使用 /help <命令> 查看详细帮助")
        return embed


class PaginationView(discord.ui.View):
    """分页视图组件"""

    def __init__(
        self,
        embeds: list[discord.Embed],
        timeout: float = 180.0,
    ) -> None:
        """
        初始化分页视图

        Args:
            embeds: Embed列表
            timeout: 超时时间（秒）
        """
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.current_page = 0
        self.total_pages = len(embeds)

        # 更新按钮状态
        self._update_buttons()

    def _update_buttons(self) -> None:
        """更新按钮状态"""
        # 更新页码显示
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.label:
                if "页" in child.label:
                    child.label = f"第 {self.current_page + 1}/{self.total_pages} 页"
                    child.disabled = True

        # 禁用/启用导航按钮
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.custom_id == "first":
                    child.disabled = self.current_page == 0
                elif child.custom_id == "prev":
                    child.disabled = self.current_page == 0
                elif child.custom_id == "next":
                    child.disabled = self.current_page >= self.total_pages - 1
                elif child.custom_id == "last":
                    child.disabled = self.current_page >= self.total_pages - 1

    @discord.ui.button(label="⏮️ 首页", style=discord.ButtonStyle.secondary, custom_id="first")
    async def first_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """跳转到第一页"""
        self.current_page = 0
        self._update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="◀️ 上一页", style=discord.ButtonStyle.primary, custom_id="prev")
    async def previous_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """上一页"""
        if self.current_page > 0:
            self.current_page -= 1
            self._update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="第 1/X 页", style=discord.ButtonStyle.gray, disabled=True)
    async def page_indicator(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """页码指示器（禁用按钮）"""
        pass

    @discord.ui.button(label="下一页 ▶️", style=discord.ButtonStyle.primary, custom_id="next")
    async def next_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """下一页"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="末页 ⏭️", style=discord.ButtonStyle.secondary, custom_id="last")
    async def last_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """跳转到最后一页"""
        self.current_page = self.total_pages - 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
