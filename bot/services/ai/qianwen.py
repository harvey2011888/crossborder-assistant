"""
阿里千问 AI服务实现

集成阿里云DashScope API，支持千问系列模型
"""

from typing import Any, AsyncGenerator, Dict, List, Optional

import dashscope
from dashscope import Generation
from dashscope.api_entities.dashscope_response import GenerationResponse

from bot.services.ai.base import BaseAIService, ChatResponse, Message


class QianwenService(BaseAIService):
    """
    阿里千问 AI服务实现类

    支持模型：
    - qwen-turbo: 快速响应模型，适合简单任务
    - qwen-plus: 增强版模型，综合能力更强
    - qwen-max: 最强模型，复杂任务首选
    """

    # 支持的模型列表
    SUPPORTED_MODELS = [
        "qwen-turbo",
        "qwen-plus",
        "qwen-max",
        "qwen-max-1201",
        "qwen-max-longcontext",
    ]

    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
    ) -> None:
        """
        初始化千问服务

        Args:
            api_key: 阿里云DashScope API密钥
            model: 模型名称，默认为qwen-turbo
        """
        super().__init__(api_key, model)
        # 配置DashScope API密钥
        dashscope.api_key = api_key

    def _get_default_model(self) -> str:
        """获取默认模型"""
        return "qwen-turbo"

    def _get_provider(self) -> str:
        """获取提供商标识"""
        return "qianwen"

    def _convert_messages(self, messages: List[Message]) -> List[Dict[str, str]]:
        """
        将标准消息格式转换为千问格式

        千问使用OpenAI兼容的消息格式

        Args:
            messages: 标准消息列表

        Returns:
            千问格式的消息列表
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
        发送对话请求到千问

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
            "result_format": "message",
        }

        # 添加可选参数
        if max_tokens:
            request_params["max_tokens"] = max_tokens
        if "top_p" in kwargs:
            request_params["top_p"] = kwargs["top_p"]
        if "top_k" in kwargs:
            request_params["top_k"] = kwargs["top_k"]
        if "enable_search" in kwargs:
            request_params["enable_search"] = kwargs["enable_search"]

        # 发送请求
        response = Generation.call(**request_params)

        # 检查响应状态
        if response.status_code != 200:
            raise RuntimeError(
                f"千问API调用失败: {response.status_code} - {response.message}"
            )

        # 解析响应
        output = response.output
        usage = response.usage

        # 提取生成的内容
        content = ""
        if output and output.choices:
            choice = output.choices[0]
            if choice.message:
                content = choice.message.content

        # 构建token使用信息
        usage_info = None
        if usage:
            usage_info = {
                "prompt_tokens": usage.input_tokens,
                "completion_tokens": usage.output_tokens,
                "total_tokens": usage.input_tokens + usage.output_tokens,
            }

        # 获取finish_reason
        finish_reason = None
        if output and output.choices:
            finish_reason = output.choices[0].finish_reason

        return ChatResponse(
            content=content,
            model=model_name,
            provider=self.provider,
            usage=usage_info,
            finish_reason=finish_reason,
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
        发送流式对话请求到千问

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
            "result_format": "message",
            "stream": True,
        }

        # 添加可选参数
        if max_tokens:
            request_params["max_tokens"] = max_tokens
        if "top_p" in kwargs:
            request_params["top_p"] = kwargs["top_p"]

        # 发送流式请求
        responses = Generation.call(**request_params)

        # 处理流式响应
        for response in responses:
            if response.status_code == 200:
                output = response.output
                if output and output.choices:
                    choice = output.choices[0]
                    if choice.message and choice.message.content:
                        yield choice.message.content
            else:
                raise RuntimeError(
                    f"千问API流式调用失败: {response.status_code} - {response.message}"
                )

    async def validate_api_key(self) -> bool:
        """
        验证API密钥是否有效

        Returns:
            API密钥是否有效
        """
        try:
            # 发送一个简单的测试请求
            response = Generation.call(
                model=self.model,
                messages=[{"role": "user", "content": "你好"}],
                max_tokens=5,
            )
            return response.status_code == 200
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

        # 千问模型信息（基于官方文档）
        model_info_map = {
            "qwen-turbo": {
                "name": "qwen-turbo",
                "display_name": "通义千问 Turbo",
                "description": "快速响应模型，适合简单任务和对话",
                "context_length": 8192,
                "max_output_tokens": 1500,
                "supports_streaming": True,
                "supports_function_calling": False,
            },
            "qwen-plus": {
                "name": "qwen-plus",
                "display_name": "通义千问 Plus",
                "description": "增强版模型，综合能力更强",
                "context_length": 32768,
                "max_output_tokens": 2000,
                "supports_streaming": True,
                "supports_function_calling": True,
            },
            "qwen-max": {
                "name": "qwen-max",
                "display_name": "通义千问 Max",
                "description": "最强模型，复杂任务首选",
                "context_length": 32768,
                "max_output_tokens": 2000,
                "supports_streaming": True,
                "supports_function_calling": True,
            },
            "qwen-max-1201": {
                "name": "qwen-max-1201",
                "display_name": "通义千问 Max 1201",
                "description": "Max模型特定版本",
                "context_length": 32768,
                "max_output_tokens": 2000,
                "supports_streaming": True,
                "supports_function_calling": True,
            },
            "qwen-max-longcontext": {
                "name": "qwen-max-longcontext",
                "display_name": "通义千问 Max 长上下文",
                "description": "支持超长上下文的Max模型",
                "context_length": 131072,
                "max_output_tokens": 2000,
                "supports_streaming": True,
                "supports_function_calling": True,
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
        调用支持工具/函数调用的千问模型

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
            "result_format": "message",
            "tools": tools,
        }

        # 发送请求
        response = Generation.call(**request_params)

        # 检查响应状态
        if response.status_code != 200:
            raise RuntimeError(
                f"千问API调用失败: {response.status_code} - {response.message}"
            )

        # 解析响应
        output = response.output
        usage = response.usage

        # 提取生成的内容
        content = ""
        tool_calls = None
        if output and output.choices:
            choice = output.choices[0]
            if choice.message:
                content = choice.message.content
                # 检查是否有工具调用
                if hasattr(choice.message, "tool_calls"):
                    tool_calls = choice.message.tool_calls

        # 构建token使用信息
        usage_info = None
        if usage:
            usage_info = {
                "prompt_tokens": usage.input_tokens,
                "completion_tokens": usage.output_tokens,
                "total_tokens": usage.input_tokens + usage.output_tokens,
            }

        return ChatResponse(
            content=content,
            model=model_name,
            provider=self.provider,
            usage=usage_info,
            finish_reason=output.choices[0].finish_reason if output and output.choices else None,
            raw_response=response,
        )
