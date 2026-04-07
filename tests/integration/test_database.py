"""
数据库集成测试

测试MySQL数据库连接和操作
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


@pytest.mark.integration
@pytest.mark.db
class TestDatabaseConnection:
    """数据库连接测试"""

    @pytest.mark.asyncio
    async def test_database_engine_creation(self) -> None:
        """测试数据库引擎创建"""
        from bot.core.database import create_engine

        with patch.dict("os.environ", {
            "MYSQL_HOST": "localhost",
            "MYSQL_PORT": "3306",
            "MYSQL_USER": "test_user",
            "MYSQL_PASSWORD": "test_password",
            "MYSQL_DATABASE": "test_db",
        }):
            engine = create_engine()

            assert engine is not None

    @pytest.mark.asyncio
    async def test_async_session_creation(self) -> None:
        """测试异步会话创建"""
        from bot.core.database import AsyncSessionLocal

        assert AsyncSessionLocal is not None


@pytest.mark.integration
@pytest.mark.db
class TestDatabaseModels:
    """数据库模型测试"""

    def test_user_model(self) -> None:
        """测试用户模型"""
        from models.user import User

        user = User(
            discord_id="123456789",
            username="TestUser",
            preferred_ai_provider="gemini",
        )

        assert user.discord_id == "123456789"
        assert user.username == "TestUser"
        assert user.preferred_ai_provider == "gemini"

    def test_session_model(self) -> None:
        """测试会话模型"""
        from models.session import ChatSession

        session = ChatSession(
            user_id="123456789",
            session_data={"messages": []},
        )

        assert session.user_id == "123456789"
        assert session.session_data == {"messages": []}

    def test_order_model(self) -> None:
        """测试订单模型"""
        from models.order import Order

        order = Order(
            user_id="123456789",
            platform_order_id="ORDER123",
            status="pending",
            total_amount=100.0,
            currency="USD",
        )

        assert order.user_id == "123456789"
        assert order.platform_order_id == "ORDER123"
        assert order.status == "pending"
