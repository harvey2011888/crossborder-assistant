"""
Discord Bot 入口文件

跨境电商智能助手的主入口
"""

import asyncio
import logging
import sys
from typing import List, Optional

import discord
from discord.ext import commands

# 添加项目根目录到路径
sys.path.insert(0, "d:\\buy\\hobi\\crossborder-assistant")

from bot.core.config import config
from bot.core.database import init_database

# 配置日志
logging.basicConfig(
    level=getattr(logging, config.bot.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class CrossborderBot(commands.Bot):
    """
    跨境电商智能助手Bot类

    继承自discord.ext.commands.Bot，提供自定义功能
    """

    def __init__(self) -> None:
        """初始化Bot实例"""
        # 配置intents
        intents = discord.Intents.all()
        intents.message_content = True
        intents.members = True

        super().__init__(
            command_prefix=config.bot.prefix,
            intents=intents,
            help_command=None,  # 禁用默认help命令，使用自定义
        )

        self.logger = logging.getLogger(self.__class__.__name__)

    async def setup_hook(self) -> None:
        """
        Bot启动前的初始化钩子

        加载所有Cog扩展
        """
        self.logger.info("开始加载Cog扩展...")

        # 加载Cog列表
        cogs = [
            "bot.cogs.general",
            "bot.cogs.shopping",
            "bot.cogs.logistics",
            "bot.cogs.orders",
        ]

        for cog in cogs:
            try:
                await self.load_extension(cog)
                self.logger.info(f"成功加载Cog: {cog}")
            except Exception as e:
                self.logger.error(f"加载Cog失败 {cog}: {e}")

        # 同步斜杠命令
        if config.bot.guild_id:
            guild = discord.Object(id=config.bot.guild_id)
            
            await self.tree.sync()
            self.logger.info("斜杠命令已全局同步（支持私聊）")
            
            guild = discord.Object(id=config.bot.guild_id)
            await self.tree.sync(guild=guild)
            self.logger.info(f"斜杠命令已同步到Guild: {config.bot.guild_id}")
        else:
            await self.tree.sync()
            self.logger.info("斜杠命令已全局同步")

    async def on_ready(self) -> None:
        """
        Bot就绪事件处理

        当Bot成功连接到Discord时触发
        """
        self.logger.info(f"{self.user} 已成功登录!")
        self.logger.info(f"Bot ID: {self.user.id}")
        self.logger.info(f"已连接到 {len(self.guilds)} 个服务器")

        # 设置Bot状态
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="跨境电商助手 | /help",
        )
        await self.change_presence(activity=activity)

    async def on_command_error(
        self,
        ctx: commands.Context,
        error: commands.CommandError,
    ) -> None:
        """
        命令错误处理

        Args:
            ctx: 命令上下文
            error: 错误对象
        """
        if isinstance(error, commands.CommandNotFound):
            return  # 忽略命令未找到错误

        if isinstance(error, commands.MissingPermissions):
            await ctx.send("您没有执行此命令的权限。")
            return

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"缺少必要参数: {error.param.name}")
            return

        self.logger.error(f"命令执行错误: {error}")
        await ctx.send(f"执行命令时发生错误: {str(error)}")

    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: discord.app_commands.AppCommandError,
    ) -> None:
        """
        斜杠命令错误处理

        Args:
            interaction: 交互对象
            error: 错误对象
        """
        self.logger.error(f"斜杠命令错误: {error}")

        if interaction.response.is_done():
            await interaction.followup.send(f"执行命令时发生错误: {str(error)}")
        else:
            await interaction.response.send_message(
                f"执行命令时发生错误: {str(error)}",
                ephemeral=True,
            )


async def main() -> None:
    """
    主入口函数

    初始化数据库并启动Bot
    """
    # 初始化数据库
    try:
        await init_database()
        logger.info("数据库初始化成功")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise

    # 创建并启动Bot
    bot = CrossborderBot()

    try:
        await bot.start(config.bot.token)
    except KeyboardInterrupt:
        logger.info("接收到停止信号，正在关闭Bot...")
        await bot.close()
    except Exception as e:
        logger.error(f"Bot运行错误: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("程序已终止")
    except Exception as e:
        logger.error(f"程序异常: {e}")
        sys.exit(1)
