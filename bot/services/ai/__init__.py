"""
AI服务模块

提供统一的AI服务接口，支持多种AI提供商：
- Google Gemini
- 阿里千问 (Qwen)
- OpenAI GPT

使用示例:
    >>> from bot.services.ai import get_ai_service, Message
    >>> service = get_ai_service(provider="gemini")
    >>> response = await service.chat([
    ...     Message(role="system", content="你是一个助手"),
    ...     Message(role="user", content="你好")
    ... ])
"""

from bot.services.ai.base import (
    AIProvider,
    AIModel,
    BaseAIService,
    ChatRequest,
    ChatResponse,
    Message,
)
from bot.services.ai.conversation import (
    ConversationManager,
    conversation_manager,
    create_conversation_session,
    get_conversation_messages,
    add_conversation_message,
)
from bot.services.ai.factory import (
    AIServiceFactory,
    get_ai_service,
    get_default_ai_service,
    get_available_services,
    validate_ai_provider,
)
from bot.services.ai.gemini import GeminiService
from bot.services.ai.openai import OpenAIService
from bot.services.ai.prompts import (
    PromptManager,
    PromptType,
    PromptTemplate,
    prompt_manager,
    get_system_prompt,
    get_shopping_system_prompt,
    get_logistics_system_prompt,
    get_order_system_prompt,
)
from bot.services.ai.qianwen import QianwenService

__all__ = [
    # 基类和数据类
    "BaseAIService",
    "Message",
    "ChatResponse",
    "ChatRequest",
    "AIProvider",
    "AIModel",
    # 工厂类
    "AIServiceFactory",
    "get_ai_service",
    "get_default_ai_service",
    "get_available_services",
    "validate_ai_provider",
    # 具体服务实现
    "GeminiService",
    "QianwenService",
    "OpenAIService",
    # 对话管理
    "ConversationManager",
    "conversation_manager",
    "create_conversation_session",
    "get_conversation_messages",
    "add_conversation_message",
    # Prompt管理
    "PromptManager",
    "PromptType",
    "PromptTemplate",
    "prompt_manager",
    "get_system_prompt",
    "get_shopping_system_prompt",
    "get_logistics_system_prompt",
    "get_order_system_prompt",
]
