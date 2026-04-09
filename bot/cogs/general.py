"""
基础命令Cog

包含/help、/start、/settings等基础命令
"""

import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from bot.core.config import config
from bot.core.database import get_db_session
from models.user import User

logger = logging.getLogger(__name__)

# AI提供商选项
AI_PROVIDERS = {
    "gemini": "Google Gemini (默认)",
    "qianwen": "阿里千问",
    "openai": "OpenAI GPT-4",
}


class GeneralCog(commands.Cog):
    """
    基础命令Cog

    提供Bot的基础交互命令
    """

    def __init__(self, bot: commands.Bot) -> None:
        """
        初始化Cog

        Args:
            bot: Bot实例
        """
        self.bot = bot
        self.logger = logging.getLogger(self.__class__.__name__)

    @app_commands.command(name="help", description="显示帮助信息")
    async def help_command(self, interaction: discord.Interaction) -> None:
        """
        帮助命令

        显示Bot的所有可用命令和说明

        Args:
            interaction: Discord交互对象
        """
        embed = discord.Embed(
            title="跨境电商智能助手 - 帮助",
            description="欢迎使用跨境电商智能助手！我是您的专属反向海淘购物助手。",
            color=discord.Color.blue(),
        )

        # 基础命令
        embed.add_field(
            name="基础命令",
            value=(
                "`/help` - 显示此帮助信息\n"
                "`/start` - 开始使用引导"
            ),
            inline=False,
        )

        # 购物命令
        embed.add_field(
            name="购物相关 (即将推出)",
            value=(
                "`/search <关键词>` - 搜索商品\n"
                "`/recommend` - 获取智能推荐\n"
                "`/compare <商品1> <商品2>` - 商品对比"
            ),
            inline=False,
        )

        # 订单和物流命令
        embed.add_field(
            name="订单与物流 (即将推出)",
            value=(
                "`/order create <链接>` - 创建代购订单\n"
                "`/order list` - 查看订单列表\n"
                "`/track <运单号>` - 追踪包裹"
            ),
            inline=False,
        )

        embed.set_footer(text="提示: 您也可以直接@我进行对话")

        # 尝试发送响应，处理可能的交互错误
        try:
            # 检查交互是否已经被确认
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=False)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=False)
        except (discord.errors.NotFound, discord.errors.HTTPException) as e:
            # 处理交互超时或无效的情况
            self.logger.warning(f"发送响应时出错: {e}")

    @app_commands.command(name="start", description="开始使用跨境电商助手")
    async def start_command(self, interaction: discord.Interaction) -> None:
        """
        开始命令

        向新用户介绍Bot的功能和使用方法

        Args:
            interaction: Discord交互对象
        """
        # 先发送响应，避免长时间显示 typing
        embed = discord.Embed(
            title="欢迎使用跨境电商智能助手",
            description=f"您好，{interaction.user.display_name}！",
            color=discord.Color.green(),
        )

        embed.add_field(
            name="关于我",
            value=(
                "我是您的跨境电商智能助手，专门帮助海外用户从中国电商平台"
                "（淘宝、京东等）购买商品。我可以帮您搜索商品、比较价格、"
                "翻译商品信息，以及跟踪订单物流。"
            ),
            inline=False,
        )

        embed.add_field(
            name="如何开始",
            value=(
                "1. 使用 `/search <关键词>` 搜索您想要的商品\n"
                "2. 直接@我并描述您的购物需求\n"
                "3. 使用 `/help` 查看所有可用命令"
            ),
            inline=False,
        )

        embed.add_field(
            name="示例对话",
            value=(
                "• @助手 我想买一双Nike跑鞋，预算500元以内\n"
                "• @助手 帮我找一款适合学生的笔记本电脑\n"
                "• @助手 这个商品寄到美国运费多少？"
            ),
            inline=False,
        )

        # 尝试发送响应，处理可能的交互错误
        try:
            # 检查交互是否已经被确认
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=False)
            else:
                # 使用 defer 提前响应，然后发送实际消息
                await interaction.response.defer(ephemeral=False, thinking=False)
                await interaction.followup.send(embed=embed, ephemeral=False)
        except (discord.errors.NotFound, discord.errors.HTTPException) as e:
            # 处理交互超时或无效的情况
            self.logger.warning(f"发送响应时出错: {e}")

    # @app_commands.command(name="settings", description="查看和修改用户设置")
    # async def settings_command(self, interaction: discord.Interaction) -> None:
    #     """
    #     设置命令

    #     显示当前用户的设置信息，包括AI提供商偏好等

    #     Args:
    #         interaction: Discord交互对象
    #     """
    #     # 从数据库获取用户设置
    #     async with get_db_session() as session:
    #         result = await session.execute(
    #             select(User).where(User.id == interaction.user.id)
    #         )
    #         user = result.scalar_one_or_none()

    #         # 如果用户不存在，创建新用户
    #         if not user:
    #             user = User(
    #                 id=interaction.user.id,
    #                 username=interaction.user.name,
    #                 discriminator=str(interaction.user.discriminator)
    #                 if hasattr(interaction.user, "discriminator")
    #                 else None,
    #                 avatar_url=str(interaction.user.display_avatar.url)
    #                 if interaction.user.display_avatar
    #                 else None,
    #                 preferred_ai_provider=config.ai.default_provider,
    #             )
    #             session.add(user)
    #             await session.commit()

    #         ai_provider = user.preferred_ai_provider or config.ai.default_provider
    #         ai_provider_name = AI_PROVIDERS.get(ai_provider, ai_provider)

    #     embed = discord.Embed(
    #         title="用户设置",
    #         description="您的个人设置信息",
    #         color=discord.Color.gold(),
    #     )

    #     embed.add_field(
    #         name="用户信息",
    #         value=(
    #             f"用户名: {interaction.user.display_name}\n"
    #             f"用户ID: {interaction.user.id}\n"
    #             f"语言: {user.preferred_language if user else config.bot.language}\n"
    #             f"货币: {user.preferred_currency if user else 'CNY'}"
    #         ),
    #         inline=False,
    #     )

    #     embed.add_field(
    #         name="AI设置",
    #         value=(
    #             f"当前AI提供商: {ai_provider_name}\n"
    #             f"使用 `/ai_switch` 切换AI提供商"
    #         ),
    #         inline=False,
    #     )

    #     if user and user.default_shipping_country:
    #         embed.add_field(
    #             name="物流设置",
    #             value=f"默认收货国家: {user.default_shipping_country}",
    #             inline=False,
    #         )

    #     embed.add_field(
    #         name="快捷操作",
    #         value=(
    #             "`/ai_switch` - 切换AI提供商\n"
    #             "`/help` - 查看所有命令"
    #         ),
    #         inline=False,
    #     )

    #     # 尝试发送响应，处理可能的交互错误
    #     try:
    #         # 检查交互是否已经被确认
    #         if interaction.response.is_done():
    #             await interaction.followup.send(embed=embed, ephemeral=False)
    #         else:
    #             await interaction.response.send_message(embed=embed, ephemeral=False)
    #     except (discord.errors.NotFound, discord.errors.HTTPException) as e:
    #         # 处理交互超时或无效的情况
    #         self.logger.warning(f"发送响应时出错: {e}")

    @app_commands.command(name="ai_switch", description="切换AI服务提供商")
    @app_commands.describe(provider="选择AI提供商")
    @app_commands.choices(
        provider=[
            app_commands.Choice(name="Google Gemini (默认)", value="gemini"),
            app_commands.Choice(name="阿里千问", value="qianwen"),
            app_commands.Choice(name="OpenAI GPT-4", value="openai"),
        ]
    )
    async def ai_switch_command(
        self,
        interaction: discord.Interaction,
        provider: app_commands.Choice[str],
    ) -> None:
        """
        切换AI提供商命令

        允许用户选择使用哪个AI服务提供商进行对话

        Args:
            interaction: Discord交互对象
            provider: AI提供商选择
        """
        # 检查所选提供商的API Key是否配置
        provider_key_map = {
            "gemini": config.ai.gemini_api_key,
            "qianwen": config.ai.dashscope_api_key,
            "openai": config.ai.openai_api_key,
        }

        if not provider_key_map.get(provider.value):
            embed = discord.Embed(
                title="切换失败",
                description=f"抱歉，{provider.name} 当前未配置API Key，无法使用。",
                color=discord.Color.red(),
            )
            embed.add_field(
                name="可用选项",
                value="请联系管理员配置所需的AI服务API Key",
                inline=False,
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)
            return

        # 更新用户偏好
        async with get_db_session() as session:
            result = await session.execute(
                select(User).where(User.id == interaction.user.id)
            )
            user = result.scalar_one_or_none()

            if not user:
                # 创建新用户
                user = User(
                    id=interaction.user.id,
                    username=interaction.user.name,
                    discriminator=str(interaction.user.discriminator)
                    if hasattr(interaction.user, "discriminator")
                    else None,
                    avatar_url=str(interaction.user.display_avatar.url)
                    if interaction.user.display_avatar
                    else None,
                    preferred_ai_provider=provider.value,
                )
                session.add(user)
            else:
                user.preferred_ai_provider = provider.value

            await session.commit()

        embed = discord.Embed(
            title="AI提供商已切换",
            description=f"您的AI服务提供商已切换为: **{provider.name}**",
            color=discord.Color.green(),
        )

        embed.add_field(
            name="提示",
            value="新的AI设置将在下次对话时生效",
            inline=False,
        )

        # 尝试发送响应，处理可能的交互错误
        try:
            # 检查交互是否已经被确认
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=False)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=False)
        except (discord.errors.NotFound, discord.errors.HTTPException) as e:
            # 处理交互超时或无效的情况
            self.logger.warning(f"发送响应时出错: {e}")

    @app_commands.command(name="ping", description="测试Bot响应")
    async def ping_command(self, interaction: discord.Interaction) -> None:
        """
        Ping命令

        测试Bot的响应速度和在线状态

        Args:
            interaction: Discord交互对象
        """
        latency = round(self.bot.latency * 1000)

        embed = discord.Embed(
            title="Pong!",
            description=f"Bot延迟: {latency}ms",
            color=discord.Color.green() if latency < 200 else discord.Color.orange(),
        )

        # 尝试发送响应，处理可能的交互错误
        try:
            # 检查交互是否已经被确认
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=False)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=False)
        except (discord.errors.NotFound, discord.errors.HTTPException) as e:
            # 处理交互超时或无效的情况
            self.logger.warning(f"发送响应时出错: {e}")

    # @commands.Cog.listener()
    # async def on_member_join(self, member: discord.Member) -> None:
    #     """
    #     新成员加入事件监听

    #     当有新用户加入服务器时发送欢迎消息

    #     Args:
    #         member: 新加入的成员
    #     """
    #     # 只在有系统消息频道时发送欢迎
    #     if member.guild.system_channel:
    #         try:
    #             embed = discord.Embed(
    #                 title="欢迎新用户！",
    #                 description=f"欢迎 {member.mention} 加入服务器！\n使用 `/start` 了解跨境电商助手。",
    #                 color=discord.Color.green(),
    #             )
    #             await member.guild.system_channel.send(embed=embed)
    #         except discord.Forbidden:
    #             self.logger.warning(f"无法在新用户加入时发送消息到 {member.guild.name}")


async def setup(bot: commands.Bot) -> None:
    """
    Cog设置函数

    Args:
        bot: Bot实例
    """
    await bot.add_cog(GeneralCog(bot))
    logger.info("GeneralCog 已加载")
