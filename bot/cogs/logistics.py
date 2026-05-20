"""
国际物流服务命令Cog

包含运费估算、包裹追踪、物流时效预估等物流相关命令
"""

import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from bot.core.config import config
from bot.services.platform.logistics import (
    LogisticsService,
    ShippingRateRequest,
    logistics_service,
)
from bot.services.platform.shipping_api import ShippingAPIError
from bot.services.platform.category_types import category_type_manager

logger = logging.getLogger(__name__)

# 支持的目的地国家代码映射（20个指定国家）
SUPPORTED_COUNTRIES = {
    "BR": "巴西",
    "US": "美国",
    "PT": "葡萄牙",
    "UK": "英国",
    "DE": "德国",
    "CA": "加拿大",
    "CN": "中国大陆",
    "FR": "法国",
    "AU": "澳大利亚",
    "ES": "西班牙",
    "IT": "意大利",
    "IE": "爱尔兰",
    "NL": "荷兰",
    "AO": "安哥拉",
    "MX": "墨西哥",
    "RO": "罗马尼亚",
    "KH": "柬埔寨",
    "AT": "奥地利",
    "AE": "阿联酋",
    "PL": "波兰",
}

# 完整的国家映射（用于显示和API调用）
ALL_COUNTRIES = SUPPORTED_COUNTRIES


class LogisticsCog(commands.Cog):
    """
    物流服务命令Cog

    提供运费估算、包裹追踪、物流时效预估等功能
    """

    def __init__(self, bot: commands.Bot) -> None:
        """
        初始化Cog

        Args:
            bot: Bot实例
        """
        self.bot = bot
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logistics_service = logistics_service

    @app_commands.command(name="shipping", description="估算运费")
    @app_commands.describe(
        weight="包裹重量（克）",
        destination="目的地国家",
        category_type="商品类型（大类-子类）",
        length="包裹长度（厘米，默认10）",
        width="包裹宽度（厘米，默认10）",
        height="包裹高度（厘米，默认10）",
    )
    @app_commands.choices(
        destination=[
            app_commands.Choice(name=f"{name} ({code})", value=code)
            for code, name in SUPPORTED_COUNTRIES.items()
        ],
    )
    async def shipping_command(
        self,
        interaction: discord.Interaction,
        weight: int,
        destination: app_commands.Choice[str],
        category_type: Optional[str] = None,
        length: Optional[int] = 10,
        width: Optional[int] = 10,
        height: Optional[int] = 10,
    ) -> None:
        """
        运费估算命令

        根据包裹重量、尺寸和目的地估算运费

        Args:
            interaction: Discord交互对象
            weight: 包裹重量（克）
            destination: 目的地国家代码
            category_type: 商品类型代码
            length: 包裹长度（厘米）
            width: 包裹宽度（厘米）
            height: 包裹高度（厘米）
        """
        # 检查交互是否已过期，如果过期则不执行
        try:
            await interaction.response.defer(thinking=True)
        except discord.errors.NotFound:
            # 交互已过期，忽略
            return
        except Exception as e:
            logger.warning(f"defer失败: {e}")
            return

        # 检查运费API是否配置
        if not self.logistics_service.is_available():
            embed = discord.Embed(
                title="⚠️ 服务不可用",
                description="运费测算服务未配置，请联系管理员。",
                color=discord.Color.orange(),
            )
            await interaction.followup.send(embed=embed)
            return

        # 验证输入参数
        if weight <= 0:
            await interaction.followup.send(
                "❌ 包裹重量必须大于0克",
                ephemeral=True,
            )
            return

        if weight > 30000:  # 30kg限制
            await interaction.followup.send(
                "❌ 包裹重量不能超过30000克（30公斤）",
                ephemeral=True,
            )
            return

        if length <= 0 or width <= 0 or height <= 0:
            await interaction.followup.send(
                "❌ 包裹尺寸必须大于0",
                ephemeral=True,
            )
            return

        try:
            # 获取商品类型信息
            if category_type:
                # 从扁平化列表中获取显示名称
                flattened = category_type_manager.get_flattened_types()
                type_info = flattened.get(category_type.lower())
                if type_info:
                    category_name = type_info[0]  # 显示名称
                    category_ids = [type_info[2]]  # ID
                else:
                    category_name = category_type
                    category_ids = [189]
            else:
                category_name = "普货"
                category_ids = [189]

            # 创建运费估算请求
            request = ShippingRateRequest(
                destination_country=destination.value,
                weight_g=weight,
                length_cm=length,
                width_cm=width,
                height_cm=height,
                category_types=category_ids,
            )

            # 调用运费测算服务
            response = await self.logistics_service.estimate_shipping_rate(request)

            # 构建响应Embed
            country_name = ALL_COUNTRIES.get(destination.value, destination.value)
            embed = discord.Embed(
                title="📦 运费估算结果",
                description=f"目的地: **{country_name}** ({destination.value})",
                color=discord.Color.blue(),
            )

            # 添加包裹信息
            embed.add_field(
                name="📋 包裹信息",
                value=(
                    f"重量: **{weight}g**\n"
                    f"尺寸: **{length} × {width} × {height} cm**\n"
                    f"体积: **{length * width * height} cm³**\n"
                    f"商品类型: **{category_name}**"
                ),
                inline=False,
            )

            # 分离可用和不可用线路
            available_lines = [line for line in response.lines if line.state == "available"]
            unavailable_lines = [line for line in response.lines if line.state != "available"]

            # 添加可用线路（最多显示5条）
            if available_lines:
                lines_text = []
                for i, line in enumerate(available_lines[:5], 1):
                    label = self.logistics_service.format_line_label(line.label)
                    tags = self.logistics_service.format_tags(line.tags)
                    compute_type = self.logistics_service.format_compute_type(line.compute_type)

                    line_text = (
                        f"**{i}. {line.name}** {label}\n"
                        f"💰 **¥{line.price}** (操作费: ¥{line.operation_fee})\n"
                        f"⏱️ **{line.time_required}天** | 使用次数: {line.use_count:,}\n"
                        f"📊 {compute_type} | {tags}\n"
                        f"✅ 送达率: {line.max_delivery_time}%\n"
                    )
                    lines_text.append(line_text)

                embed.add_field(
                    name=f"🚚 可用线路 ({len(available_lines)}条)",
                    value="\n".join(lines_text) if lines_text else "暂无可用线路",
                    inline=False,
                )

            # 如果有不可用线路，简要显示
            if unavailable_lines:
                unavailable_text = []
                for line in unavailable_lines[:3]:
                    reason = line.unavailable_reason[0] if line.unavailable_reason else "暂不可用"
                    unavailable_text.append(f"• {line.name}: {reason}")

                embed.add_field(
                    name=f"⚠️ 不可用线路 ({len(unavailable_lines)}条)",
                    value="\n".join(unavailable_text) if unavailable_text else "暂无不可用线路",
                    inline=False,
                )

            # 添加说明
            embed.add_field(
                name="💡 说明",
                value=(
                    "• 以上价格为预估价格，实际价格以订单确认时为准\n"
                    "• 计费方式: 实重计费按实际重量计算，体积重计费按长×宽×高/6000计算\n"
                    "• 送达率表示历史包裹在预计时间内送达的百分比\n"
                    "• 可投保线路支持购买运输保险"
                ),
                inline=False,
            )

            embed.set_footer(text="数据来源于Hubbuy物流平台")
            embed.timestamp = discord.utils.utcnow()

            await interaction.followup.send(embed=embed)

        except ShippingAPIError as e:
            self.logger.error(f"运费API错误: {e}")
            error_msg = str(e)
            if "missing nonce header" in error_msg.lower():
                error_msg = "API认证失败，请检查配置"
            elif "参数错误" in error_msg:
                error_msg = "请求参数错误，请检查输入"

            embed = discord.Embed(
                title="❌ 运费测算失败",
                description=f"调用运费API时出错: {error_msg}",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.error(f"估算运费时出错: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ 系统错误",
                description="估算运费时发生系统错误，请稍后重试。",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed)

    @shipping_command.autocomplete("category_type")
    async def category_type_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """
        商品类型自动完成

        根据用户输入提供商品类型建议
        """
        try:
            # 检查管理器是否已初始化
            if not category_type_manager.is_initialized():
                logger.warning("商品类型管理器未初始化，尝试初始化...")
                await category_type_manager.initialize()
            
            flattened = category_type_manager.get_flattened_types()
            logger.debug(f"自动完成获取到 {len(flattened)} 个商品类型")
            
            # 如果没有获取到商品类型，返回空列表
            if not flattened:
                logger.warning("商品类型为空，自动完成无法提供选项")
                return []
            
            choices = []
            current_lower = current.lower() if current else ""
            
            for code, (display_name, _, _) in flattened.items():
                # 如果用户有输入，进行过滤
                if not current_lower or current_lower in display_name.lower() or current_lower in code.lower():
                    choices.append(app_commands.Choice(name=display_name[:100], value=code[:100]))  # Discord限制名称长度
            
            logger.debug(f"自动完成返回 {len(choices)} 个选项")
            # 限制返回25个选项（Discord限制）
            return choices[:25]
        except Exception as e:
            logger.error(f"商品类型自动完成出错: {e}", exc_info=True)
            return []

    @app_commands.command(name="track", description="追踪包裹（预留功能）")
    @app_commands.describe(
        tracking_number="运单号",
        carrier="物流公司（可选）",
    )
    @app_commands.choices(
        carrier=[
            app_commands.Choice(name="顺丰速运", value="sf"),
            app_commands.Choice(name="DHL", value="dhl"),
            app_commands.Choice(name="UPS", value="ups"),
            app_commands.Choice(name="FedEx", value="fedex"),
            app_commands.Choice(name="EMS", value="ems"),
        ]
    )
    async def track_command(
        self,
        interaction: discord.Interaction,
        tracking_number: str,
        carrier: Optional[app_commands.Choice[str]] = None,
    ) -> None:
        """
        包裹追踪命令（预留框架）

        根据运单号查询包裹物流状态
        待自建平台API接口文档提供后实现

        Args:
            interaction: Discord交互对象
            tracking_number: 运单号
            carrier: 物流公司
        """
        await interaction.response.defer(thinking=True)

        # 检查平台API是否配置
        if not config.platform.api_url:
            embed = discord.Embed(
                title="功能预留",
                description="包裹追踪功能正在开发中，敬请期待！",
                color=discord.Color.orange(),
            )
            embed.add_field(
                name="您输入的信息",
                value=(
                    f"运单号: {tracking_number}\n"
                    f"物流公司: {carrier.name if carrier else '自动识别'}"
                ),
                inline=False,
            )
            embed.add_field(
                name="预计上线时间",
                value="待自建平台API接口文档提供后实现",
                inline=False,
            )
            await interaction.followup.send(embed=embed)
            return

        # TODO: 接入自建平台物流追踪API
        # 实现包裹追踪逻辑
        try:
            # 模拟物流追踪数据
            embed = discord.Embed(
                title="包裹追踪",
                description=f"运单号: {tracking_number}",
                color=discord.Color.blue(),
            )

            carrier_name = carrier.name if carrier else "自动识别"
            embed.add_field(
                name="物流公司",
                value=carrier_name,
                inline=True,
            )

            embed.add_field(
                name="当前状态",
                value="运输中",
                inline=True,
            )

            # 模拟物流轨迹
            tracking_history = [
                ("2024-01-15 14:30", "包裹已到达目的地国家", "✅"),
                ("2024-01-14 08:00", "包裹已离开始发国", "🛫"),
                ("2024-01-13 16:45", "包裹已到达集运中心", "📦"),
                ("2024-01-13 09:20", "包裹已揽收", "📋"),
            ]

            history_text = "\n".join(
                [f"{time} {icon} {status}" for time, status, icon in tracking_history]
            )

            embed.add_field(
                name="物流轨迹",
                value=history_text,
                inline=False,
            )

            embed.set_footer(text="物流信息每小时更新一次")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.error(f"追踪包裹时出错: {e}")
            await interaction.followup.send(
                "追踪包裹时发生错误，请检查运单号是否正确。",
                ephemeral=True,
            )

    @app_commands.command(name="estimate", description="物流时效预估（预留功能）")
    @app_commands.describe(
        destination="目的地国家",
        method="物流方式",
        origin_city="发货城市（可选，默认为上海）",
    )
    @app_commands.choices(
        destination=[
            app_commands.Choice(name=name, value=code)
            for code, name in list(SUPPORTED_COUNTRIES.items())[:10]
        ],
        method=[
            app_commands.Choice(name="标准快递", value="standard"),
            app_commands.Choice(name="特快专递", value="express"),
            app_commands.Choice(name="经济物流", value="economy"),
            app_commands.Choice(name="海运", value="sea"),
        ],
    )
    async def estimate_command(
        self,
        interaction: discord.Interaction,
        destination: app_commands.Choice[str],
        method: app_commands.Choice[str],
        origin_city: Optional[str] = "上海",
    ) -> None:
        """
        物流时效预估命令（预留框架）

        预估从发货地到目的地的物流时效
        待自建平台API接口文档提供后实现

        Args:
            interaction: Discord交互对象
            destination: 目的地国家
            method: 物流方式
            origin_city: 发货城市
        """
        await interaction.response.defer(thinking=True)

        # 检查平台API是否配置
        if not config.platform.api_url:
            embed = discord.Embed(
                title="功能预留",
                description="物流时效预估功能正在开发中，敬请期待！",
                color=discord.Color.orange(),
            )
            embed.add_field(
                name="您输入的信息",
                value=(
                    f"发货地: {origin_city}\n"
                    f"目的地: {destination.name}\n"
                    f"物流方式: {method.name}"
                ),
                inline=False,
            )
            embed.add_field(
                name="预计上线时间",
                value="待自建平台API接口文档提供后实现",
                inline=False,
            )
            await interaction.followup.send(embed=embed)
            return

        # TODO: 接入自建平台时效预估API
        # 实现时效预估逻辑
        try:
            # 模拟时效数据
            estimated_days = {
                "standard": (7, 15),
                "express": (3, 7),
                "economy": (15, 30),
                "sea": (30, 60),
            }.get(method.value, (7, 15))

            embed = discord.Embed(
                title="物流时效预估",
                description=f"从 {origin_city} 到 {destination.name}",
                color=discord.Color.green(),
            )

            embed.add_field(
                name="物流方式",
                value=method.name,
                inline=True,
            )

            embed.add_field(
                name="预计时效",
                value=f"{estimated_days[0]}-{estimated_days[1]} 个工作日",
                inline=True,
            )

            embed.add_field(
                name="说明",
                value=(
                    "• 以上时效仅供参考\n"
                    "• 实际时效可能受海关清关、天气等因素影响\n"
                    "• 节假日期间可能会有延迟"
                ),
                inline=False,
            )

            embed.set_footer(text="具体时效以实际发货为准")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.error(f"预估物流时效时出错: {e}")
            await interaction.followup.send(
                "预估物流时效时发生错误，请稍后重试。",
                ephemeral=True,
            )

    @app_commands.command(name="logistics_help", description="查看物流服务帮助")
    async def logistics_help_command(self, interaction: discord.Interaction) -> None:
        """
        物流帮助命令

        显示物流相关命令的使用说明

        Args:
            interaction: Discord交互对象
        """
        embed = discord.Embed(
            title="📦 国际物流服务帮助",
            description="了解如何使用物流相关功能",
            color=discord.Color.blue(),
        )

        embed.add_field(
            name="🚀 可用命令",
            value=(
                "`/shipping` - 估算运费\n"
                "`/track` - 追踪包裹\n"
                "`/estimate` - 物流时效预估\n"
                "`/logistics_help` - 查看此帮助"
            ),
            inline=False,
        )

        embed.add_field(
            name="💰 运费估算",
            value=(
                "使用 `/shipping` 命令估算运费，需要提供:\n"
                "• 包裹重量（克）\n"
                "• 目的地国家\n"
                "• 商品类型（可选，输入时会自动提示）\n"
                "• 包裹尺寸（可选，默认10×10×10cm）\n\n"
                "**示例**: `/shipping weight:500 destination:美国`"
            ),
            inline=False,
        )

        embed.add_field(
            name="📋 商品类型",
            value=(
                "输入商品类型时会自动提示，格式为：大类-子类\n"
                "例如：服饰-普货、鞋子-国际品牌、化妆品等"
            ),
            inline=False,
        )

        embed.add_field(
            name="📋 包裹追踪",
            value=(
                "使用 `/track` 命令追踪包裹，需要提供:\n"
                "• 运单号\n"
                "• 物流公司（可选）\n\n"
                "**注意**: 此功能正在开发中"
            ),
            inline=False,
        )

        embed.add_field(
            name="🌍 支持的国家",
            value=(
                "巴西、美国、葡萄牙、英国、德国、加拿大、中国大陆、\n"
                "法国、澳大利亚、西班牙、意大利、爱尔兰、荷兰、\n"
                "安哥拉、墨西哥、罗马尼亚、柬埔寨、奥地利、阿联酋、波兰"
            ),
            inline=False,
        )

        embed.add_field(
            name="💡 计费说明",
            value=(
                "• **实重计费**: 按包裹实际重量计算\n"
                "• **体积重计费**: 按长×宽×高/6000计算，取较大值\n"
                "• 价格包含运费和操作费\n"
                "• 部分线路支持购买运输保险"
            ),
            inline=False,
        )

        embed.set_footer(text="数据来源于Hubbuy物流平台")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    """
    Cog设置函数

    Args:
        bot: Bot实例
    """
    await bot.add_cog(LogisticsCog(bot))
    logger.info("LogisticsCog 已加载")
