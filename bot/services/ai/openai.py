"""
OpenAI GPT AI服务实现

集成OpenAI API，支持GPT-4和GPT-3.5-Turbo模型
"""

from typing import Any, AsyncGenerator, Dict, List, Optional

import openai
from openai import AsyncOpenAI

from bot.services.ai.base import BaseAIService, ChatResponse, Message


class OpenAIService(BaseAIService):
    """
    OpenAI GPT AI服务实现类

    支持模型：
    - gpt-4: GPT-4基础模型
    - gpt-4-turbo-preview: GPT-4 Turbo最新版本
    - gpt-3.5-turbo: GPT-3.5 Turbo模型
    """

    # 支持的模型列表
    SUPPORTED_MODELS = [
        "gpt-4",
        "gpt-4-0613",
        "gpt-4-32k",
        "gpt-4-32k-0613",
        "gpt-4-turbo-preview",
        "gpt-4-1106-preview",
        "gpt-4-0125-preview",
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-0613",
        "gpt-3.5-turbo-16k",
        "gpt-3.5-turbo-1106",
        "gpt-3.5-turbo-0125",
    ]

    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        organization: Optional[str] = None,
    ) -> None:
        """
        初始化OpenAI服务

        Args:
            api_key: OpenAI API密钥
            model: 模型名称，默认为gpt-3.5-turbo
            base_url: 自定义API基础URL（用于代理或兼容API）
            organization: OpenAI组织ID
        """
        super().__init__(api_key, model)
        # 创建异步客户端
        client_kwargs: Dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        if organization:
            client_kwargs["organization"] = organization

        self.client = AsyncOpenAI(**client_kwargs)

    def _get_default_model(self) -> str:
        """获取默认模型"""
        return "gpt-3.5-turbo"

    def _get_provider(self) -> str:
        """获取提供商标识"""
        return "openai"

    def _convert_messages(self, messages: List[Message]) -> List[Dict[str, str]]:
        """
        将标准消息格式转换为OpenAI格式

        Args:
            messages: 标准消息列表

        Returns:
            OpenAI格式的消息列表
        """
        formatted = []
        for msg in messages:
            message_dict: Dict[str, str] = {"role": msg.role, "content": msg.content}
            if msg.name:
                message_dict["name"] = msg.name
            formatted.append(message_dict)
        return formatted

    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """
        发送对话请求到OpenAI

        Args:
            messages: 对话消息列表
            model: 使用的模型
            temperature: 温度参数
            max_tokens: 最大生成token数
            **kwargs: 其他参数

        Returns:
            AI响应对象
        """
        model_name = model or self.model

        # 验证模型名称
        if model_name not in self.SUPPORTED_MODELS:
            raise ValueError(f"不支持的模型: {model_name}")

        # 转换消息格式
        formatted_messages = self._convert_messages(messages)

        # 构建请求参数
        request_params: Dict[str, Any] = {
            "model": model_name,
            "messages": formatted_messages,
            "temperature": temperature,
        }

        # 添加可选参数
        if max_tokens:
            request_params["max_tokens"] = max_tokens
        if "top_p" in kwargs:
            request_params["top_p"] = kwargs["top_p"]
        if "frequency_penalty" in kwargs:
            request_params["frequency_penalty"] = kwargs["frequency_penalty"]
        if "presence_penalty" in kwargs:
            request_params["presence_penalty"] = kwargs["presence_penalty"]
        if "stop" in kwargs:
            request_params["stop"] = kwargs["stop"]
        if "seed" in kwargs:
            request_params["seed"] = kwargs["seed"]

        # 发送请求
        response = await self.client.chat.completions.create(**request_params)

        # 解析响应
        choice = response.choices[0]
        message = choice.message

        # 构建token使用信息
        usage_info = None
        if response.usage:
            usage_info = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return ChatResponse(
            content=message.content or "",
            model=response.model,
            provider=self.provider,
            usage=usage_info,
            finish_reason=choice.finish_reason,
            raw_response=response,
        )

    async def chat_stream(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """
        发送流式对话请求到OpenAI

        Args:
            messages: 对话消息列表
            model: 使用的模型
            temperature: 温度参数
            max_tokens: 最大生成token数
            **kwargs: 其他参数

        Yields:
            生成的文本片段
        """
        model_name = model or self.model

        # 验证模型名称
        if model_name not in self.SUPPORTED_MODELS:
            raise ValueError(f"不支持的模型: {model_name}")

        # 转换消息格式
        formatted_messages = self._convert_messages(messages)

        # 构建请求参数
        request_params: Dict[str, Any] = {
            "model": model_name,
            "messages": formatted_messages,
            "temperature": temperature,
            "stream": True,
        }

        # 添加可选参数
        if max_tokens:
            request_params["max_tokens"] = max_tokens
        if "top_p" in kwargs:
            request_params["top_p"] = kwargs["top_p"]

        # 发送流式请求
        stream = await self.client.chat.completions.create(**request_params)

        # 处理流式响应
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def validate_api_key(self) -> bool:
        """
        验证API密钥是否有效

        Returns:
            API密钥是否有效
        """
        try:
            # 发送一个简单的测试请求
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5,
            )
            return response.choices[0].message.content is not None
        except Exception:
            return False

    def get_model_info(self, model: Optional[str] = None) -> Dict[str, Any]:
        """
        获取模型信息

        Args:
            model: 模型名称

        Returns:
            模型信息字典
        """
        model_name = model or self.model

        # OpenAI模型信息
        model_info_map = {
            "gpt-4": {
                "name": "gpt-4",
                "display_name": "GPT-4",
                "description": "强大的多模态模型，适合复杂任务",
                "context_length": 8192,
                "max_output_tokens": 4096,
                "supports_streaming": True,
                "supports_function_calling": True,
                "supports_vision": False,
            },
            "gpt-4-32k": {
                "name": "gpt-4-32k",
                "display_name": "GPT-4 32K",
                "description": "GPT-4长上下文版本",
                "context_length": 32768,
                "max_output_tokens": 4096,
                "supports_streaming": True,
                "supports_function_calling": True,
                "supports_vision": False,
            },
            "gpt-4-turbo-preview": {
                "name": "gpt-4-turbo-preview",
                "display_name": "GPT-4 Turbo",
                "description": "最新的GPT-4 Turbo模型",
                "context_length": 128000,
                "max_output_tokens": 4096,
                "supports_streaming": True,
                "supports_function_calling": True,
                "supports_vision": True,
            },
            "gpt-4-1106-preview": {
                "name": "gpt-4-1106-preview",
                "display_name": "GPT-4 Turbo 1106",
                "description": "GPT-4 Turbo 2023年11月版本",
                "context_length": 128000,
                "max_output_tokens": 4096,
                "supports_streaming": True,
                "supports_function_calling": True,
                "supports_vision": False,
            },
            "gpt-4-0125-preview": {
                "name": "gpt-4-0125-preview",
                "display_name": "GPT-4 Turbo 0125",
                "description": "GPT-4 Turbo 2024年1月版本",
                "context_length": 128000,
                "max_output_tokens": 4096,
                "supports_streaming": True,
                "supports_function_calling": True,
                "supports_vision": False,
            },
            "gpt-3.5-turbo": {
                "name": "gpt-3.5-turbo",
                "display_name": "GPT-3.5 Turbo",
                "description": "快速且经济的模型，适合大多数任务",
                "context_length": 4096,
                "max_output_tokens": 4096,
                "supports_streaming": True,
                "supports_function_calling": True,
                "supports_vision": False,
            },
            "gpt-3.5-turbo-16k": {
                "name": "gpt-3.5-turbo-16k",
                "display_name": "GPT-3.5 Turbo 16K",
                "description": "GPT-3.5 Turbo长上下文版本",
                "context_length": 16384,
                "max_output_tokens": 4096,
                "supports_streaming": True,
                "supports_function_calling": True,
                "supports_vision": False,
            },
            "gpt-3.5-turbo-1106": {
                "name": "gpt-3.5-turbo-1106",
                "display_name": "GPT-3.5 Turbo 1106",
                "description": "GPT-3.5 Turbo 2023年11月版本",
                "context_length": 16384,
                "max_output_tokens": 4096,
                "supports_streaming": True,
                "supports_function_calling": True,
                "supports_vision": False,
            },
            "gpt-3.5-turbo-0125": {
                "name": "gpt-3.5-turbo-0125",
                "display_name": "GPT-3.5 Turbo 0125",
                "description": "最新的GPT-3.5 Turbo模型",
                "context_length": 16384,
                "max_output_tokens": 4096,
                "supports_streaming": True,
                "supports_function_calling": True,
                "supports_vision": False,
            },
        }

        return model_info_map.get(
            model_name, {"error": f"未知的模型: {model_name}"}
        )

    async def call_with_tools(
        self,
        messages: List[Message],
        tools: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> ChatResponse:
        """
        调用支持工具/函数调用的OpenAI模型

        Args:
            messages: 对话消息列表
            tools: 工具定义列表
            model: 使用的模型
            temperature: 温度参数
            **kwargs: 其他参数

        Returns:
            AI响应对象
        """
        model_name = model or self.model

        # 验证模型是否支持函数调用
        model_info = self.get_model_info(model_name)
        if not model_info.get("supports_function_calling", False):
            raise ValueError(f"模型 {model_name} 不支持函数调用")

        # 转换消息格式
        formatted_messages = self._convert_messages(messages)

        # 构建请求参数
        request_params: Dict[str, Any] = {
            "model": model_name,
            "messages": formatted_messages,
            "temperature": temperature,
            "tools": tools,
        }

        # 添加可选参数
        if "tool_choice" in kwargs:
            request_params["tool_choice"] = kwargs["tool_choice"]

        # 发送请求
        response = await self.client.chat.completions.create(**request_params)

        # 解析响应
        choice = response.choices[0]
        message = choice.message

        # 构建token使用信息
        usage_info = None
        if response.usage:
            usage_info = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        # 如果有工具调用，将信息添加到内容中
        content = message.content or ""
        if message.tool_calls:
            tool_calls_info = []
            for tc in message.tool_calls:
                tool_calls_info.append({
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                })
            # 将工具调用信息存储在raw_response中

        return ChatResponse(
            content=content,
            model=response.model,
            provider=self.provider,
            usage=usage_info,
            finish_reason=choice.finish_reason,
            raw_response=response,
        )

    async def create_embeddings(
        self,
        texts: List[str],
        model: str = "text-embedding-3-small",
    ) -> List[List[float]]:
        """
        创建文本嵌入向量

        Args:
            texts: 文本列表
            model: 嵌入模型名称

        Returns:
            嵌入向量列表
        """
        response = await self.client.embeddings.create(
            model=model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    async def create_image(
        self,
        prompt: str,
        model: str = "dall-e-3",
        size: str = "1024x1024",
        quality: str = "standard",
        n: int = 1,
    ) -> List[str]:
        """
        使用DALL-E生成图片

        Args:
            prompt: 图片描述
            model: 图片生成模型
            size: 图片尺寸
            quality: 图片质量
            n: 生成数量

        Returns:
            图片URL列表
        """
        response = await self.client.images.generate(
            model=model,
            prompt=prompt,
            size=size,
            quality=quality,
            n=n,
        )
        return [item.url for item in response.data]
