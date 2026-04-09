"""
Google Gemini AI服务实现

集成Google Gemini API，支持文本对话和流式响应
"""

import json
from typing import Any, AsyncGenerator, List, Optional

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from bot.services.ai.base import BaseAIService, ChatResponse, Message


class GeminiService(BaseAIService):
    """
    Google Gemini AI服务实现类

    支持模型：
    - gemini-1.5-flash: 快速响应模型（推荐）
    - gemini-1.5-flash-8b: 轻量级快速响应模型
    - gemini-1.5-pro: 最新Pro模型
    - gemini-1.5-pro-vision: 多模态模型（支持图片）
    """

    # 支持的模型列表（已弃用gemini-pro和gemini-pro-vision）
    SUPPORTED_MODELS = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-1.5-pro",
        "gemini-1.5-pro-vision",
    ]

    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        generation_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        初始化Gemini服务

        Args:
            api_key: Google API密钥
            model: 模型名称，默认为gemini-pro
            generation_config: 生成配置参数
        """
        super().__init__(api_key, model)
        # 配置Google Generative AI
        genai.configure(api_key=api_key)
        self.generation_config = generation_config or {}

    def _get_default_model(self) -> str:
        """获取默认模型"""
        return "gemini-1.5-flash"

    def _get_provider(self) -> str:
        """获取提供商标识"""
        return "gemini"

    def _convert_messages(self, messages: List[Message]) -> tuple:
        """
        将标准消息格式转换为Gemini格式

        Gemini使用不同的消息格式：
        - system prompt通过model的system_instruction参数设置
        - 对话历史是交替的user/model角色列表

        Args:
            messages: 标准消息列表

        Returns:
            (system_instruction, history) 元组
        """
        system_instruction = None
        history = []

        for msg in messages:
            if msg.role == "system":
                # Gemini使用system_instruction设置系统提示
                system_instruction = msg.content
            elif msg.role == "user":
                history.append({"role": "user", "parts": [msg.content]})
            elif msg.role == "assistant":
                history.append({"role": "model", "parts": [msg.content]})

        return system_instruction, history

    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """
        发送对话请求到Gemini

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
        system_instruction, history = self._convert_messages(messages)

        # 创建生成配置
        generation_config = GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            top_p=kwargs.get("top_p", 0.95),
            top_k=kwargs.get("top_k", 40),
        )

        # 创建模型实例
        model_instance = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config,
            system_instruction=system_instruction,
        )

        # 开始对话
        chat = model_instance.start_chat(history=history[:-1] if history else [])

        # 获取最后一条用户消息
        last_message = history[-1]["parts"][0] if history else ""

        # 发送消息并获取响应
        response = chat.send_message(last_message)

        # 提取token使用情况（Gemini目前不直接提供，使用估算）
        usage = {
            "prompt_tokens": self.estimate_tokens(
                " ".join(m.content for m in messages)
            ),
            "completion_tokens": self.estimate_tokens(response.text),
            "total_tokens": self.estimate_tokens(
                " ".join(m.content for m in messages)
            )
            + self.estimate_tokens(response.text),
        }

        return ChatResponse(
            content=response.text,
            model=model_name,
            provider=self.provider,
            usage=usage,
            finish_reason="stop",
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
        发送流式对话请求到Gemini

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
        system_instruction, history = self._convert_messages(messages)

        # 创建生成配置
        generation_config = GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            top_p=kwargs.get("top_p", 0.95),
            top_k=kwargs.get("top_k", 40),
        )

        # 创建模型实例
        model_instance = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config,
            system_instruction=system_instruction,
        )

        # 开始对话
        chat = model_instance.start_chat(history=history[:-1] if history else [])

        # 获取最后一条用户消息
        last_message = history[-1]["parts"][0] if history else ""

        # 发送消息并获取流式响应
        response = chat.send_message(last_message, stream=True)

        # 流式输出
        for chunk in response:
            if chunk.text:
                yield chunk.text

    async def validate_api_key(self) -> bool:
        """
        验证API密钥是否有效

        Returns:
            API密钥是否有效
        """
        try:
            # 尝试列出模型来验证API密钥
            models = list(genai.list_models())
            return len(models) > 0
        except Exception:
            return False

    async def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """
        计算文本的token数量

        Args:
            text: 输入文本
            model: 模型名称

        Returns:
            token数量
        """
        model_name = model or self.model
        model_instance = genai.GenerativeModel(model_name=model_name)
        return model_instance.count_tokens(text).total_tokens

    def get_model_info(self, model: Optional[str] = None) -> Dict[str, Any]:
        """
        获取模型信息

        Args:
            model: 模型名称

        Returns:
            模型信息字典
        """
        model_name = model or self.model
        try:
            model_info = genai.get_model(f"models/{model_name}")
            return {
                "name": model_info.name,
                "display_name": model_info.display_name,
                "description": model_info.description,
                "input_token_limit": model_info.input_token_limit,
                "output_token_limit": model_info.output_token_limit,
                "supported_generation_methods": model_info.supported_generation_methods,
            }
        except Exception as e:
            return {"error": str(e)}
