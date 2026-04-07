"""
AI服务基类模块

定义所有AI服务提供商的统一接口和抽象基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional, Union


class AIProvider(Enum):
    """AI服务提供商枚举"""

    GEMINI = "gemini"
    QIANWEN = "qianwen"
    OPENAI = "openai"


class AIModel(Enum):
    """AI模型枚举"""

    # Google Gemini 模型
    GEMINI_PRO = "gemini-pro"
    GEMINI_PRO_VISION = "gemini-pro-vision"
    GEMINI_1_5_PRO = "gemini-1.5-pro"
    GEMINI_1_5_FLASH = "gemini-1.5-flash"

    # 阿里千问模型
    QWEN_TURBO = "qwen-turbo"
    QWEN_PLUS = "qwen-plus"
    QWEN_MAX = "qwen-max"

    # OpenAI 模型
    GPT_4 = "gpt-4"
    GPT_4_TURBO = "gpt-4-turbo-preview"
    GPT_3_5_TURBO = "gpt-3.5-turbo"


@dataclass
class Message:
    """对话消息数据类"""

    role: str  # system, user, assistant
    content: str
    name: Optional[str] = None  # 用于区分不同用户（可选）


@dataclass
class ChatResponse:
    """AI对话响应数据类"""

    content: str
    model: str
    provider: str
    usage: Optional[Dict[str, int]] = None  # token使用情况
    finish_reason: Optional[str] = None
    raw_response: Optional[Any] = None  # 原始响应对象


@dataclass
class ChatRequest:
    """AI对话请求数据类"""

    messages: List[Message]
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    stream: bool = False


class BaseAIService(ABC):
    """
    AI服务抽象基类

    所有AI服务提供商必须实现此基类定义的方法
    """

    def __init__(self, api_key: str, model: Optional[str] = None) -> None:
        """
        初始化AI服务

        Args:
            api_key: API密钥
            model: 默认使用的模型名称
        """
        self.api_key = api_key
        self.model = model or self._get_default_model()
        self.provider = self._get_provider()

    @abstractmethod
    def _get_default_model(self) -> str:
        """获取默认模型名称"""
        pass

    @abstractmethod
    def _get_provider(self) -> str:
        """获取提供商标识"""
        pass

    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """
        发送对话请求

        Args:
            messages: 对话消息列表
            model: 使用的模型（覆盖默认模型）
            temperature: 温度参数（创造性程度）
            max_tokens: 最大生成token数
            **kwargs: 其他参数

        Returns:
            AI响应对象
        """
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """
        发送流式对话请求

        Args:
            messages: 对话消息列表
            model: 使用的模型（覆盖默认模型）
            temperature: 温度参数
            max_tokens: 最大生成token数
            **kwargs: 其他参数

        Yields:
            生成的文本片段
        """
        pass

    @abstractmethod
    async def validate_api_key(self) -> bool:
        """
        验证API密钥是否有效

        Returns:
            API密钥是否有效
        """
        pass

    def format_messages(
        self, messages: List[Message]
    ) -> Union[List[Dict[str, str]], Any]:
        """
        将消息列表格式化为提供商特定的格式

        Args:
            messages: 消息列表

        Returns:
            格式化后的消息
        """
        # 默认实现：转换为OpenAI格式
        formatted = []
        for msg in messages:
            message_dict: Dict[str, str] = {"role": msg.role, "content": msg.content}
            if msg.name:
                message_dict["name"] = msg.name
            formatted.append(message_dict)
        return formatted

    def estimate_tokens(self, text: str) -> int:
        """
        估算文本的token数量（粗略估计）

        Args:
            text: 输入文本

        Returns:
            估算的token数
        """
        # 粗略估计：中文约1.5个字符/token，英文约4个字符/token
        # 这里使用简单的启发式方法
        chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 0.7 + other_chars * 0.25) + 1

    def truncate_messages(
        self,
        messages: List[Message],
        max_tokens: int = 4000,
        reserve_tokens: int = 1000,
    ) -> List[Message]:
        """
        截断消息列表以适应token限制

        Args:
            messages: 原始消息列表
            max_tokens: 最大token限制
            reserve_tokens: 为响应预留的token数

        Returns:
            截断后的消息列表
        """
        available_tokens = max_tokens - reserve_tokens
        total_tokens = 0
        truncated_messages = []

        # 从最新的消息开始计算，保留系统消息
        system_messages = [m for m in messages if m.role == "system"]
        other_messages = [m for m in messages if m.role != "system"]

        # 计算系统消息的token
        for msg in system_messages:
            total_tokens += self.estimate_tokens(msg.content)

        # 从后往前添加消息
        for msg in reversed(other_messages):
            msg_tokens = self.estimate_tokens(msg.content)
            if total_tokens + msg_tokens > available_tokens:
                break
            total_tokens += msg_tokens
            truncated_messages.insert(0, msg)

        # 添加系统消息到开头
        return system_messages + truncated_messages
