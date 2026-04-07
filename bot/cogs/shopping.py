"""
购物相关命令Cog

包含商品搜索、推荐、对比、翻译等购物相关命令
"""

import logging
from typing import List, Optional

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from bot.core.config import config
from bot.core.database import get_db_session
from bot.services.ecommerce.models import Currency, PlatformType, Product, SearchResult
from models.user import User

logger = logging.getLogger(__name__)


class ShoppingCog(commands.Cog):
    """
    购物命令Cog

    提供商品搜索、智能推荐、商品对比、翻译等购物相关功能
    """

    def __init__(self, bot: commands.Bot) -> None:
        """
        初始化Cog

        Args:
            bot: Bot实例
        """
        self.bot = bot
        self.logger = logging.getLogger(self.__class__.__name__)

    async def _get_or_create_user(
        self,
        discord_user: discord.User | discord.Member,
    ) -> User:
        """
        获取或创建用户

        Args:
            discord_user: Discord用户对象

        Returns:
            用户模型实例
        """
        async with get_db_session() as session:
            result = await session.execute(
                select(User).where(User.id == discord_user.id)
            )
            user = result.scalar_one_or_none()

            if not user:
                user = User(
                    id=discord_user.id,
                    username=discord_user.name,
                    discriminator=str(discord_user.discriminator)
                    if hasattr(discord_user, "discriminator")
                    else None,
                    avatar_url=str(discord_user.display_avatar.url)
                    if discord_user.display_avatar
                    else None,
                    preferred_ai_provider=config.ai.default_provider,
                )
                session.add(user)
                await session.commit()

            return user

    @app_commands.command(name="search", description="搜索商品")
    @app_commands.describe(
        keyword="搜索关键词",
        platform="选择电商平台",
        max_price="最高价格（人民币）",
        min_price="最低价格（人民币）",
    )
    @app_commands.choices(
        platform=[
            app_commands.Choice(name="淘宝", value="taobao"),
            app_commands.Choice(name="京东", value="jd"),
            app_commands.Choice(name="全部平台", value="all"),
        ]
    )
    async def search_command(
        self,
        interaction: discord.Interaction,
        keyword: str,
        platform: Optional[app_commands.Choice[str]] = None,
        max_price: Optional[int] = None,
        min_price: Optional[int] = None,
    ) -> None:
        """
        商品搜索命令

        搜索淘宝、京东等电商平台的商品

        Args:
            interaction: Discord交互对象
            keyword: 搜索关键词
            platform: 电商平台选择
            max_price: 最高价格限制
            min_price: 最低价格限制
        """
        # 先发送"正在搜索"提示
        await interaction.response.defer(thinking=True)

        # 获取或创建用户
        user = await self._get_or_create_user(interaction.user)

        # 确定搜索平台
        search_platform = platform.value if platform else "all"
        platform_name = {
            "taobao": "淘宝",
            "jd": "京东",
            "all": "全部平台",
        }.get(search_platform, "全部平台")

        # 构建搜索条件描述
        filters = []
        if min_price is not None:
            filters.append(f"最低价格: ¥{min_price}")
        if max_price is not None:
            filters.append(f"最高价格: ¥{max_price}")

        filter_text = f" | 筛选: {', '.join(filters)}" if filters else ""

        try:
            # TODO: 接入实际的电商API
            # 目前使用模拟数据演示
            mock_products = self._get_mock_products(keyword, search_platform)

            # 应用价格筛选
            if min_price is not None:
                mock_products = [
                    p for p in mock_products
                    if p.price.current_price >= min_price
                ]
            if max_price is not None:
                mock_products = [
                    p for p in mock_products
                    if p.price.current_price <= max_price
                ]

            if not mock_products:
                embed = discord.Embed(
                    title="搜索结果",
                    description=f"未找到与 **{keyword}** 相关的商品{filter_text}",
                    color=discord.Color.orange(),
                )
                embed.add_field(
                    name="建议",
                    value="• 尝试使用不同的关键词\n• 放宽价格筛选条件\n• 尝试其他平台",
                    inline=False,
                )
                await interaction.followup.send(embed=embed)
                return

            # 创建搜索结果展示
            embed = discord.Embed(
                title=f"搜索结果 - {keyword}",
                description=f"平台: {platform_name}{filter_text}\n找到 {len(mock_products)} 个商品",
                color=discord.Color.blue(),
            )

            # 显示前5个商品
            for i, product in enumerate(mock_products[:5], 1):
                price_text = product.get_formatted_price()
                shop_text = f" | {product.shop.shop_name}" if product.shop else ""
                sales_text = f" | 销量: {product.sales_count}" if product.sales_count else ""

                embed.add_field(
                    name=f"{i}. {product.title[:50]}{'...' if len(product.title) > 50 else ''}",
                    value=f"💰 {price_text}{shop_text}{sales_text}\n[查看详情]({product.product_url})",
                    inline=False,
                )

            if len(mock_products) > 5:
                embed.set_footer(text=f"还有 {len(mock_products) - 5} 个结果，使用更精确的关键词查看")

            # 添加使用提示
            embed.add_field(
                name="下一步",
                value="• 使用 `/compare <商品1> <商品2>` 对比商品\n• 直接@我询问商品详情",
                inline=False,
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.error(f"搜索商品时出错: {e}")
            await interaction.followup.send(
                "搜索商品时发生错误，请稍后重试。",
                ephemeral=True,
            )

    def _get_mock_products(
        self,
        keyword: str,
        platform: str,
    ) -> List[Product]:
        """
        获取模拟商品数据（用于演示）

        Args:
            keyword: 搜索关键词
            platform: 平台

        Returns:
            商品列表
        """
        from decimal import Decimal

        # 模拟商品数据
        mock_data = [
            {
                "product_id": "123456",
                "platform": PlatformType.TAOBAO,
                "title": f"高品质{keyword} - 官方正品保证",
                "product_url": "https://item.taobao.com/item.htm?id=123456",
                "price": {
                    "original_price": Decimal("299.00"),
                    "current_price": Decimal("199.00"),
                    "currency": Currency.CNY,
                    "discount": "6.7折",
                },
                "main_image": "https://via.placeholder.com/400x400",
                "sales_count": 1500,
                "rating": 4.8,
                "shop": {
                    "shop_name": "官方旗舰店",
                    "shop_rating": 4.9,
                },
                "location": "浙江杭州",
            },
            {
                "product_id": "123457",
                "platform": PlatformType.JD,
                "title": f"{keyword} - 京东自营 次日达",
                "product_url": "https://item.jd.com/123457.html",
                "price": {
                    "original_price": Decimal("399.00"),
                    "current_price": Decimal("299.00"),
                    "currency": Currency.CNY,
                    "discount": "7.5折",
                },
                "main_image": "https://via.placeholder.com/400x400",
                "sales_count": 3200,
                "rating": 4.9,
                "shop": {
                    "shop_name": "京东自营",
                    "shop_rating": 5.0,
                },
                "location": "北京",
            },
            {
                "product_id": "123458",
                "platform": PlatformType.TAOBAO,
                "title": f"{keyword} - 海外直邮 包税",
                "product_url": "https://item.taobao.com/item.htm?id=123458",
                "price": {
                    "original_price": Decimal("259.00"),
                    "current_price": Decimal("159.00"),
                    "currency": Currency.CNY,
                    "discount": "6.1折",
                },
                "main_image": "https://via.placeholder.com/400x400",
                "sales_count": 800,
                "rating": 4.6,
                "shop": {
                    "shop_name": "海外购专营店",
                    "shop_rating": 4.7,
                },
                "location": "上海",
            },
        ]

        # 过滤平台
        if platform != "all":
            platform_type = PlatformType(platform)
            mock_data = [d for d in mock_data if d["platform"] == platform_type]

        products = []
        for data in mock_data:
            from bot.services.ecommerce.models import ProductPrice, ShopInfo

            price_data = data.pop("price")
            shop_data = data.pop("shop")

            product = Product(
                **data,
                price=ProductPrice(**price_data),
                shop=ShopInfo(**shop_data),
            )
            products.append(product)

        return products

    @app_commands.command(name="recommend", description="获取智能商品推荐")
    @app_commands.describe(
        category="商品类别",
        budget="预算范围（人民币）",
    )
    @app_commands.choices(
        category=[
            app_commands.Choice(name="电子产品", value="electronics"),
            app_commands.Choice(name="服装", value="clothing"),
            app_commands.Choice(name="家居用品", value="home"),
            app_commands.Choice(name="美妆护肤", value="beauty"),
            app_commands.Choice(name="运动户外", value="sports"),
            app_commands.Choice(name="图书文具", value="books"),
        ],
        budget=[
            app_commands.Choice(name="100元以下", value="0-100"),
            app_commands.Choice(name="100-500元", value="100-500"),
            app_commands.Choice(name="500-1000元", value="500-1000"),
            app_commands.Choice(name="1000-3000元", value="1000-3000"),
            app_commands.Choice(name="3000元以上", value="3000+"),
        ]
    )
    async def recommend_command(
        self,
        interaction: discord.Interaction,
        category: Optional[app_commands.Choice[str]] = None,
        budget: Optional[app_commands.Choice[str]] = None,
    ) -> None:
        """
        智能推荐命令

        根据用户偏好和历史记录推荐商品

        Args:
            interaction: Discord交互对象
            category: 商品类别
            budget: 预算范围
        """
        await interaction.response.defer(thinking=True)

        # 获取用户
        user = await self._get_or_create_user(interaction.user)

        # 构建推荐描述
        category_name = category.name if category else "综合"
        budget_name = budget.name if budget else "不限"

        embed = discord.Embed(
            title="智能商品推荐",
            description=f"类别: {category_name} | 预算: {budget_name}",
            color=discord.Color.green(),
        )

        # TODO: 接入AI推荐逻辑和实际商品数据
        # 目前使用模拟推荐
        recommendations = [
            {
                "name": "热门推荐",
                "items": [
                    "小米手环8 Pro - ¥399",
                    "Anker 65W氮化镓充电器 - ¥149",
                    "倍思蓝牙耳机 - ¥199",
                ],
            },
            {
                "name": "性价比之选",
                "items": [
                    "Redmi Buds 4 - ¥199",
                    "罗马仕20000mAh充电宝 - ¥89",
                    "绿联Type-C扩展坞 - ¥129",
                ],
            },
        ]

        for rec in recommendations:
            items_text = "\n".join([f"• {item}" for item in rec["items"]])
            embed.add_field(
                name=rec["name"],
                value=items_text,
                inline=False,
            )

        embed.add_field(
            name="个性化推荐",
            value="💡 使用 `/search <关键词>` 搜索特定商品\n💡 直接@我描述需求获取精准推荐",
            inline=False,
        )

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="compare", description="对比两个商品")
    @app_commands.describe(
        product1="第一个商品链接或ID",
        product2="第二个商品链接或ID",
    )
    async def compare_command(
        self,
        interaction: discord.Interaction,
        product1: str,
        product2: str,
    ) -> None:
        """
        商品对比命令

        对比两个商品的价格、评分、销量等信息

        Args:
            interaction: Discord交互对象
            product1: 第一个商品链接或ID
            product2: 第二个商品链接或ID
        """
        await interaction.response.defer(thinking=True)

        try:
            # TODO: 接入实际商品API获取商品详情
            # 目前使用模拟数据

            embed = discord.Embed(
                title="商品对比",
                description=f"对比: {product1[:30]}... vs {product2[:30]}...",
                color=discord.Color.blue(),
            )

            # 模拟对比数据
            comparison_data = {
                "价格": ["¥199", "¥299", "✅ 更便宜"],
                "评分": ["4.8⭐", "4.9⭐", "✅ 更高"],
                "销量": ["1500+", "3200+", "✅ 更畅销"],
                "店铺": ["官方旗舰店", "京东自营", "-"],
                "发货地": ["浙江杭州", "北京", "-"],
            }

            for field, values in comparison_data.items():
                embed.add_field(
                    name=field,
                    value=f"商品1: {values[0]}\n商品2: {values[1]}\n{values[2]}",
                    inline=True,
                )

            embed.add_field(
                name="建议",
                value="根据对比，商品1价格更优惠，商品2评分和销量更高。建议根据您的 priorities 选择。",
                inline=False,
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.error(f"对比商品时出错: {e}")
            await interaction.followup.send(
                "对比商品时发生错误，请检查商品链接或ID是否正确。",
                ephemeral=True,
            )

    @app_commands.command(name="translate", description="翻译商品信息")
    @app_commands.describe(
        content="要翻译的商品信息（标题、描述等）",
        target_language="目标语言",
    )
    @app_commands.choices(
        target_language=[
            app_commands.Choice(name="English", value="en"),
            app_commands.Choice(name="日本語", value="ja"),
            app_commands.Choice(name="한국어", value="ko"),
            app_commands.Choice(name="Français", value="fr"),
            app_commands.Choice(name="Deutsch", value="de"),
            app_commands.Choice(name="Español", value="es"),
        ]
    )
    async def translate_command(
        self,
        interaction: discord.Interaction,
        content: str,
        target_language: app_commands.Choice[str],
    ) -> None:
        """
        商品信息翻译命令

        将商品标题、描述等信息翻译成目标语言

        Args:
            interaction: Discord交互对象
            content: 要翻译的内容
            target_language: 目标语言
        """
        await interaction.response.defer(thinking=True)

        # 语言名称映射
        lang_names = {
            "en": "English",
            "ja": "日本語",
            "ko": "한국어",
            "fr": "Français",
            "de": "Deutsch",
            "es": "Español",
        }

        try:
            # TODO: 接入AI翻译服务
            # 目前返回模拟翻译结果

            # 模拟翻译结果
            mock_translations = {
                "en": f"[EN] {content}",
                "ja": f"[JP] {content}",
                "ko": f"[KO] {content}",
                "fr": f"[FR] {content}",
                "de": f"[DE] {content}",
                "es": f"[ES] {content}",
            }

            translated = mock_translations.get(
                target_language.value,
                f"[Translated] {content}",
            )

            embed = discord.Embed(
                title="商品信息翻译",
                color=discord.Color.purple(),
            )

            embed.add_field(
                name="原文（中文）",
                value=content[:1024] if len(content) <= 1024 else content[:1021] + "...",
                inline=False,
            )

            embed.add_field(
                name=f"翻译结果（{lang_names.get(target_language.value, target_language.value)}）",
                value=translated[:1024] if len(translated) <= 1024 else translated[:1021] + "...",
                inline=False,
            )

            embed.set_footer(text="翻译由AI提供，仅供参考")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.error(f"翻译商品信息时出错: {e}")
            await interaction.followup.send(
                "翻译时发生错误，请稍后重试。",
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    """
    Cog设置函数

    Args:
        bot: Bot实例
    """
    await bot.add_cog(ShoppingCog(bot))
    logger.info("ShoppingCog 已加载")
