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

        # 初始化商品类型管理器
        try:
            from bot.services.platform.category_types import category_type_manager
            await category_type_manager.initialize()
            self.logger.info("商品类型管理器初始化完成")
        except Exception as e:
            self.logger.warning(f"商品类型管理器初始化失败: {e}")

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

        # 同步斜杠命令（必须在登录后执行）
        await self._sync_commands()

    async def _sync_commands(self) -> None:
        """
        同步斜杠命令

        在Bot就绪后调用，确保命令正确注册
        """
        self.logger.info(f"Guild ID配置: {config.bot.guild_id}")

        if config.bot.guild_id:
            guild = discord.Object(id=config.bot.guild_id)

            # 先清空guild命令（清除Discord缓存）
            try:
                self.tree.clear_commands(guild=guild)
                await self.tree.sync(guild=guild)
                self.logger.info(f"已清空Guild命令缓存")
            except Exception as e:
                self.logger.error(f"清空Guild命令失败: {e}")

            # 全局同步
            try:
                global_commands = await self.tree.sync()
                self.logger.info(f"斜杠命令已全局同步，共 {len(global_commands)} 个命令")
                for cmd in global_commands:
                    self.logger.info(f"  - /{cmd.name}: {cmd.description[:30]}...")
            except Exception as e:
                self.logger.error(f"全局同步失败: {e}")

            # 使用 copy_global_to 将全局命令复制到guild（即时生效）
            try:
                self.tree.copy_global_to(guild=guild)
                guild_commands = await self.tree.sync(guild=guild)
                self.logger.info(f"已将全局命令复制到Guild: {config.bot.guild_id}, Guild命令数: {len(guild_commands)}")
            except Exception as e:
                self.logger.error(f"复制命令到Guild失败: {e}")
        else:
            self.logger.warning("未配置Guild ID，仅进行全局同步（可能需要1小时生效）")
            commands = await self.tree.sync()
            self.logger.info(f"斜杠命令已全局同步，共 {len(commands)} 个命令")

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

    async def on_message(self, message: discord.Message) -> None:
        """
        消息事件处理

        处理用户@Bot的消息或私聊消息，进行AI对话
        所有消息都通过AI处理，AI通过对话收集运费查询参数

        Args:
            message: 消息对象
        """
        # 忽略Bot自己的消息
        if message.author == self.user:
            return

        # 忽略空消息
        if not message.content:
            return

        # 检查是否是私聊消息或@了Bot
        is_private = isinstance(message.channel, discord.DMChannel)
        is_mentioned = self.user.mentioned_in(message)

        if is_private or is_mentioned:
            # 提取消息内容（去除@部分）
            content = message.content.replace(f"<@{self.user.id}>", "").strip()

            if not content:
                return

            msg_type = "私聊" if is_private else "@消息"
            self.logger.info(f"收到{msg_type}: {content} 来自用户: {message.author.id}")

            try:
                # 检查是否是运费查询请求
                shipping_keywords = ["运费", "多少钱", "寄到", "发到", "shipping", "cost", "price"]
                is_shipping_query = any(keyword in content.lower() for keyword in shipping_keywords)
                
                # 导入运费对话管理器
                from bot.services.shipping_conversation import shipping_conversation_manager
                
                # 检查用户是否在运费查询流程中
                is_in_shipping_flow = shipping_conversation_manager.is_in_shipping_flow(message.author.id)
                
                self.logger.info(f"消息处理: is_in_shipping_flow={is_in_shipping_flow}, is_shipping_query={is_shipping_query}")

                # 所有消息都进入AI对话流程
                try:
                    # 发送"正在输入"状态
                    async with message.channel.typing():
                        # 导入必要的模块
                        from bot.services.ai import get_default_ai_service
                        from bot.services.ai.conversation import conversation_manager
                        from bot.services.ai.prompts import get_shopping_system_prompt, get_logistics_system_prompt
                        from bot.services.ai.base import Message

                        # 根据是否是运费查询选择不同的prompt
                        if is_shipping_query or is_in_shipping_flow:
                            system_prompt = get_logistics_system_prompt()
                            session_type = "logistics"
                            self.logger.info("使用物流咨询场景Prompt")
                        else:
                            system_prompt = get_shopping_system_prompt()
                            session_type = "shopping"
                            self.logger.info("使用商品搜索场景Prompt")

                        # 获取或创建会话
                        session = await conversation_manager.get_or_create_session(
                            user_id=message.author.id,
                            session_type=session_type,
                            system_prompt=system_prompt,
                        )

                        # 获取AI服务
                        ai_service = get_default_ai_service()

                        # 获取对话历史
                        messages = await conversation_manager.get_messages(session.session_id)

                        # 如果是运费查询场景，在系统消息中添加当前状态提示
                        if is_shipping_query or is_in_shipping_flow:
                            # 获取或创建运费查询状态
                            state = shipping_conversation_manager.get_or_create_state(message.author.id)
                            
                            # 如果是新的查询且已有完整状态，重置状态
                            if is_shipping_query and state.is_complete():
                                shipping_conversation_manager.clear_state(message.author.id)
                                state = shipping_conversation_manager.get_or_create_state(message.author.id)
                            
                            # 从用户消息中提取参数（无论是首次还是后续）
                            updated = shipping_conversation_manager.update_state_from_input(state, content)
                            if updated:
                                self.logger.info(f"从用户消息中提取到参数: {updated}, 当前状态: {state}")
                            
                            # 获取商品类型列表（从API或静态配置）
                            from bot.services.platform.category_types import category_type_manager
                            category_types = category_type_manager.get_flattened_types()
                            category_options = []
                            for idx, (type_code, (display_name, cat_name, type_id)) in enumerate(category_types.items(), 1):
                                category_options.append(f"{idx}. {display_name}")
                            category_options_text = "\n".join(category_options)  # 显示所有商品类型
                            
                            # 构建状态提示信息
                            status_info = []
                            if state.weight:
                                status_info.append(f"已确认重量: {state.weight}g")
                            if state.destination:
                                status_info.append(f"已确认目的地: {state.destination}")
                            if state.category_name:
                                status_info.append(f"已确认商品类型: {state.category_name}")
                            
                            missing = state.get_missing_params()
                            
                            # 如果必需参数收集完成，检查是否需要询问长宽高
                            if state.is_complete() and state.should_ask_dimensions():
                                # 必需参数齐全，但还没有询问长宽高
                                content_with_context = f"{content}\n\n[系统提示：运费查询参数已收集完成（重量、目的地、商品类型）。请询问用户是否需要提供包裹尺寸（长x宽x高 cm），这是可选的，默认使用10x10x10cm。如果用户不需要提供尺寸，直接执行运费查询。]"
                            elif state.is_complete():
                                self.logger.info(f"参数收集完成，执行运费查询: {state}")
                                result = await shipping_conversation_manager.query_shipping_rate(state)
                                
                                if result["success"]:
                                    # 使用与 /shipping 命令一致的格式
                                    from bot.services.platform.logistics import logistics_service
                                    lines_text = []
                                    for i, line in enumerate(result.get('lines', [])[:5], 1):
                                        label = logistics_service.format_line_label(line.get('label', []))
                                        tags = logistics_service.format_tags(line.get('tags', []))
                                        compute_type = logistics_service.format_compute_type(line.get('compute_type', 1))
                                        
                                        line_text = (
                                            f"**{i}. {line['name']}** {label}\n"
                                            f"💰 **¥{line['price']}** (操作费: ¥{line['operation_fee']})\n"
                                            f"⏱️ **{line['time_required']}天** | 使用次数: {line.get('use_count', 0):,}\n"
                                            f"📊 {compute_type} | {tags}\n"
                                            f"✅ 送达率: {line.get('max_delivery_time', 'N/A')}%"
                                        )
                                        lines_text.append(line_text)
                                    
                                    shipping_result = (
                                        f"📦 **运费估算结果**\n\n"
                                        f"目的地: **{result['destination']}**\n"
                                        f"重量: **{result['weight']}g**\n"
                                        f"商品类型: **{result.get('category_name', '普货')}**\n\n"
                                        f"**可用线路**:\n"
                                        f"{chr(10).join(lines_text)}\n\n"
                                        f"💡 提示: 以上价格为预估价格，实际价格以订单确认时为准。"
                                    )
                                    content_with_context = f"{content}\n\n[系统提示：运费查询已完成。请严格按照以下结果回复用户，不要省略任何线路信息，必须显示所有可用线路（共{len(result.get('lines', []))}条）。\n{shipping_result}]\n\n重要：必须显示所有线路，不要只选择一条。保持格式一致，包含线路名称、价格、操作费、时效、使用次数、计费方式、标签、送达率等所有信息。"
                                    shipping_conversation_manager.clear_state(message.author.id)
                                else:
                                    error_msg = result.get("error", "未知错误")
                                    content_with_context = f"{content}\n\n[系统提示：运费查询失败 - {error_msg}]"
                                    shipping_conversation_manager.clear_state(message.author.id)
                            else:
                                # 参数未收集完成，添加状态提示和商品类型选项
                                if status_info:
                                    content_with_context = f"{content}\n\n[系统提示：当前运费查询进度]\n" + "\n".join(status_info) + f"\n\n仍需收集: {', '.join(missing)}\n\n商品类型选项（输入数字）:\n{category_options_text}\n\n请根据用户已提供的信息，只询问缺失的参数，不要重复询问已确认的信息。"
                                else:
                                    content_with_context = f"{content}\n\n[系统提示：用户想要查询运费。需要从消息中提取或询问以下信息：1.包裹重量 2.目的地国家 3.商品类型。商品类型选项（输入数字）:\n{category_options_text}]"
                        else:
                            content_with_context = content

                        # 添加当前用户消息到列表（用于AI调用）
                        messages.append(Message(role="user", content=content_with_context))

                        # 添加用户消息到会话存储
                        await conversation_manager.add_message(
                            session_id=session.session_id,
                            role="user",
                            content=content_with_context,
                        )

                        # 调用AI生成回复
                        response = await ai_service.chat(messages)
                        self.logger.info(f"AI回复内容: {response.content}")

                        # 添加AI回复到会话
                        await conversation_manager.add_message(
                            session_id=session.session_id,
                            role="assistant",
                            content=response.content,
                        )

                        # 发送回复
                        await message.reply(response.content)
                except Exception as e:
                    # 处理所有AI服务错误，切换到千问作为备选
                    self.logger.warning(f"主AI服务出错: {e}")
                    # 尝试使用千问作为备选
                    try:
                        from bot.services.ai import get_ai_service
                        from bot.services.ai.base import Message

                        # 使用千问AI服务
                        ai_service = get_ai_service(provider="qianwen")
                        self.logger.info("使用千问AI服务作为备选")

                        # 获取对话历史（不包括系统消息，因为千问可能使用不同的系统提示）
                        messages = await conversation_manager.get_messages(
                            session.session_id,
                            include_system=False
                        )

                        # 如果消息列表为空，添加当前用户消息
                        if not messages:
                            messages = [Message(role="user", content=content_with_context if 'content_with_context' in locals() else content)]

                        # 调用千问生成回复
                        response = await ai_service.chat(messages)
                        self.logger.info(f"千问AI回复: {response.content[:100]}...")

                        # 添加AI回复到会话
                        await conversation_manager.add_message(
                            session_id=session.session_id,
                            role="assistant",
                            content=response.content,
                        )

                        # 发送回复
                        await message.reply(response.content)
                    except Exception as e2:
                        self.logger.warning(f"千问AI服务也不可用: {e2}")
                        # 尝试使用OpenAI作为备选
                        try:
                            from bot.services.ai import get_ai_service
                            from bot.services.ai.base import Message

                            # 使用OpenAI服务
                            ai_service = get_ai_service(provider="openai")
                            self.logger.info("使用OpenAI服务作为备选")

                            # 获取对话历史
                            messages = await conversation_manager.get_messages(
                                session_id=session.session_id,
                                include_system=False
                            )

                            # 如果消息列表为空，添加当前用户消息
                            if not messages:
                                messages = [Message(role="user", content=content_with_context if 'content_with_context' in locals() else content)]

                            # 调用OpenAI生成回复
                            response = await ai_service.chat(messages)
                            self.logger.info(f"OpenAI回复: {response.content[:100]}...")

                            # 添加AI回复到会话
                            await conversation_manager.add_message(
                                session_id=session.session_id,
                                role="assistant",
                                content=response.content,
                            )

                            # 发送回复
                            await message.reply(response.content)
                        except Exception as e3:
                            self.logger.error(f"OpenAI服务也不可用: {e3}")
                            # 所有AI服务都不可用，发送错误消息
                            await message.reply("抱歉，所有AI服务暂时不可用，请稍后重试。")

            except Exception as e:
                self.logger.error(f"处理@消息时出错: {e}")
                await message.reply("抱歉，处理您的请求时发生错误，请稍后重试。")


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
