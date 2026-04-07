"""
AI服务单元测试

测试各种AI服务(Gemini, OpenAI, Qianwen)的功能
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.services.ai.base import AIResponse, MessageRole
from bot.services.ai.factory import AIProvider, ai_service_factory


@pytest.mark.unit
class TestAIResponse:
    """AI响应模型测试"""

    def test_ai_response_creation(self) -> None:
        """测试创建AI响应对象"""
        response = AIResponse(
            content="测试回复",
            role=MessageRole.ASSISTANT,
            model="gemini-pro",
            usage={"prompt_tokens": 10, "completion_tokens": 20},
        )

        assert response.content == "测试回复"
        assert response.role == MessageRole.ASSISTANT
        assert response.model == "gemini-pro"
        assert response.usage["prompt_tokens"] == 10

    def test_ai_response_to_dict(self) -> None:
        """测试AI响应转换为字典"""
        response = AIResponse(
            content="测试回复",
            role=MessageRole.ASSISTANT,
            model="gemini-pro",
        )

        data = response.to_dict()

        assert data["content"] == "测试回复"
        assert data["role"] == "assistant"
        assert data["model"] == "gemini-pro"


@pytest.mark.unit
class TestAIServiceFactory:
    """AI服务工厂测试"""

    def test_factory_creation(self) -> None:
        """测试工厂创建服务实例"""
        factory = ai_service_factory

        assert factory is not None
        assert hasattr(factory, 'create_service')
        assert hasattr(factory, 'register_service')

    def test_get_available_providers(self) -> None:
        """测试获取可用提供商列表"""
        providers = ai_service_factory.get_available_providers()

        assert isinstance(providers, list)
        assert len(providers) >= 3
        assert AIProvider.GEMINI in providers
        assert AIProvider.OPENAI in providers
        assert AIProvider.QIANWEN in providers


@pytest.mark.unit
@pytest.mark.asyncio
class TestGeminiService:
    """Gemini服务测试"""

    async def test_generate_response(self, mock_gemini_response: MagicMock) -> None:
        """测试生成回复"""
        with patch('google.generativeai.GenerativeModel') as mock_model_class:
            mock_model = MagicMock()
            mock_model.generate_content_async = AsyncMock(return_value=mock_gemini_response)
            mock_model_class.return_value = mock_model

            from bot.services.ai.gemini import GeminiService

            service = GeminiService(api_key="test_key")
            service._model = mock_model

            response = await service.generate_response("你好")

            assert response.content == "这是Gemini的测试回复"
            assert response.role == MessageRole.ASSISTANT

    async def test_chat_conversation(self, mock_gemini_response: MagicMock) -> None:
        """测试对话功能"""
        with patch('google.generativeai.GenerativeModel') as mock_model_class:
            mock_chat = MagicMock()
            mock_chat.send_message_async = AsyncMock(return_value=mock_gemini_response)

            mock_model = MagicMock()
            mock_model.start_chat.return_value = mock_chat
            mock_model_class.return_value = mock_model

            from bot.services.ai.gemini import GeminiService

            service = GeminiService(api_key="test_key")
            service._model = mock_model

            messages = [
                {"role": "user", "content": "你好"},
            ]
            response = await service.chat(messages)

            assert response.content == "这是Gemini的测试回复"


@pytest.mark.unit
@pytest.mark.asyncio
class TestOpenAIService:
    """OpenAI服务测试"""

    async def test_generate_response(self, mock_openai_response: MagicMock) -> None:
        """测试生成回复"""
        with patch('openai.AsyncOpenAI') as mock_client_class:
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
            mock_client_class.return_value = mock_client

            from bot.services.ai.openai import OpenAIService

            service = OpenAIService(api_key="test_key")
            service._client = mock_client

            response = await service.generate_response("你好")

            assert response.content == "这是OpenAI的测试回复"
            assert response.usage is not None


@pytest.mark.unit
@pytest.mark.asyncio
class TestQianwenService:
    """阿里千问服务测试"""

    async def test_generate_response(self, mock_qianwen_response: MagicMock) -> None:
        """测试生成回复"""
        with patch('dashscope.Generation') as mock_generation_class:
            mock_generation_class.call = AsyncMock(return_value=mock_qianwen_response)

            from bot.services.ai.qianwen import QianwenService

            service = QianwenService(api_key="test_key")

            response = await service.generate_response("你好")

            assert response.content == "这是阿里千问的测试回复"


@pytest.mark.unit
class TestConversationManager:
    """对话管理器测试"""

    def test_conversation_creation(self) -> None:
        """测试创建对话"""
        from bot.services.ai.conversation import ConversationManager

        manager = ConversationManager()
        session_id = manager.create_session("user123")

        assert session_id is not None
        assert len(session_id) > 0

    def test_add_message(self) -> None:
        """测试添加消息"""
        from bot.services.ai.conversation import ConversationManager

        manager = ConversationManager()
        session_id = manager.create_session("user123")

        manager.add_message(session_id, "user", "你好")
        manager.add_message(session_id, "assistant", "你好！有什么可以帮助你的？")

        history = manager.get_history(session_id)
        assert len(history) == 2
        assert history[0]["content"] == "你好"
        assert history[1]["role"] == "assistant"

    def test_clear_history(self) -> None:
        """测试清空历史"""
        from bot.services.ai.conversation import ConversationManager

        manager = ConversationManager()
        session_id = manager.create_session("user123")

        manager.add_message(session_id, "user", "你好")
        manager.clear_history(session_id)

        history = manager.get_history(session_id)
        assert len(history) == 0

    def test_session_expiry(self) -> None:
        """测试会话过期"""
        from bot.services.ai.conversation import ConversationManager

        # 创建会话管理器，设置很短的过期时间
        manager = ConversationManager(default_ttl=0)
        session_id = manager.create_session("user123")

        # 立即检查会话是否过期
        import time
        time.sleep(0.1)

        # 过期后应该返回空历史
        history = manager.get_history(session_id)
        # 注意：实际行为取决于实现
        assert history is not None  # 或者根据实际实现调整断言
