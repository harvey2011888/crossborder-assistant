"""
Pytest配置和共享fixture

提供测试所需的共享资源和配置
"""

import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio


# ============================================================================
# 事件循环配置
# ============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    创建会话级别的事件循环

    Yields:
        asyncio.AbstractEventLoop: 事件循环实例
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_discord_user() -> MagicMock:
    """
    创建模拟Discord用户

    Returns:
        MagicMock: 模拟用户对象
    """
    user = MagicMock()
    user.id = 123456789
    user.name = "TestUser"
    user.display_name = "Test User"
    user.mention = "<@123456789>"
    user.avatar = MagicMock()
    user.avatar.url = "https://cdn.discordapp.com/avatars/123456789/abc.png"
    return user


@pytest.fixture
def mock_discord_guild() -> MagicMock:
    """
    创建模拟Discord服务器

    Returns:
        MagicMock: 模拟服务器对象
    """
    guild = MagicMock()
    guild.id = 987654321
    guild.name = "Test Guild"
    guild.icon = MagicMock()
    guild.icon.url = "https://cdn.discordapp.com/icons/987654321/abc.png"
    return guild


@pytest.fixture
def mock_discord_channel() -> MagicMock:
    """
    创建模拟Discord频道

    Returns:
        MagicMock: 模拟频道对象
    """
    channel = MagicMock()
    channel.id = 111222333
    channel.name = "test-channel"
    channel.send = AsyncMock()
    return channel


@pytest.fixture
def mock_discord_message() -> MagicMock:
    """
    创建模拟Discord消息

    Returns:
        MagicMock: 模拟消息对象
    """
    message = MagicMock()
    message.id = 444555666
    message.content = "Test message"
    message.author = MagicMock()
    message.author.id = 123456789
    message.channel = MagicMock()
    message.guild = MagicMock()
    message.reply = AsyncMock()
    message.edit = AsyncMock()
    return message


@pytest.fixture
def mock_discord_interaction(mock_discord_user: MagicMock) -> MagicMock:
    """
    创建模拟Discord交互

    Args:
        mock_discord_user: 模拟用户fixture

    Returns:
        MagicMock: 模拟交互对象
    """
    interaction = MagicMock()
    interaction.id = 777888999
    interaction.user = mock_discord_user
    interaction.guild = MagicMock()
    interaction.guild.id = 987654321
    interaction.channel = MagicMock()
    interaction.channel.id = 111222333

    # 响应方法
    interaction.response = MagicMock()
    interaction.response.is_done = MagicMock(return_value=False)
    interaction.response.defer = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.response.edit_message = AsyncMock()

    # Followup方法
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()

    return interaction


@pytest.fixture
def mock_bot() -> MagicMock:
    """
    创建模拟Discord Bot

    Returns:
        MagicMock: 模拟Bot对象
    """
    bot = MagicMock()
    bot.user = MagicMock()
    bot.user.id = 999888777
    bot.user.name = "TestBot"
    bot.user.display_name = "Test Bot"
    bot.user.avatar = MagicMock()
    bot.user.avatar.url = "https://cdn.discordapp.com/avatars/999888777/bot.png"
    bot.guilds = []
    bot.get_guild = MagicMock(return_value=None)
    bot.get_channel = MagicMock(return_value=None)
    bot.get_user = MagicMock(return_value=None)
    return bot


# ============================================================================
# 环境变量Fixture
# ============================================================================

@pytest.fixture
def mock_env_vars() -> Generator[dict[str, str], None, None]:
    """
    提供模拟环境变量

    Yields:
        dict[str, str]: 环境变量字典
    """
    env_vars = {
        "DISCORD_TOKEN": "test_discord_token_12345",
        "MYSQL_HOST": "localhost",
        "MYSQL_PORT": "3306",
        "MYSQL_USER": "test_user",
        "MYSQL_PASSWORD": "test_password",
        "MYSQL_DATABASE": "test_db",
        "GEMINI_API_KEY": "test_gemini_api_key",
        "DASHSCOPE_API_KEY": "test_dashscope_api_key",
        "OPENAI_API_KEY": "test_openai_api_key",
        "DEFAULT_AI_PROVIDER": "gemini",
        "PLATFORM_API_URL": "https://test-platform.example.com/api",
        "PLATFORM_API_KEY": "test_platform_api_key",
    }

    with patch.dict("os.environ", env_vars, clear=False):
        yield env_vars


# ============================================================================
# 数据库Fixture
# ============================================================================

@pytest_asyncio.fixture
async def mock_db_session() -> AsyncGenerator[AsyncMock, None]:
    """
    创建模拟数据库会话

    Yields:
        AsyncMock: 模拟数据库会话
    """
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock()
    session.scalars = AsyncMock()
    yield session


@pytest.fixture
def mock_db_engine() -> MagicMock:
    """
    创建模拟数据库引擎

    Returns:
        MagicMock: 模拟数据库引擎
    """
    engine = MagicMock()
    engine.connect = MagicMock()
    engine.dispose = MagicMock()
    return engine


# ============================================================================
# AI服务Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_gemini_response() -> MagicMock:
    """
    创建模拟Gemini API响应

    Returns:
        MagicMock: 模拟响应对象
    """
    response = MagicMock()
    response.text = "这是Gemini的测试回复"
    response.candidates = [MagicMock()]
    response.candidates[0].content = MagicMock()
    response.candidates[0].content.parts = [MagicMock()]
    response.candidates[0].content.parts[0].text = "这是Gemini的测试回复"
    return response


@pytest.fixture
def mock_openai_response() -> MagicMock:
    """
    创建模拟OpenAI API响应

    Returns:
        MagicMock: 模拟响应对象
    """
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message = MagicMock()
    response.choices[0].message.content = "这是OpenAI的测试回复"
    response.usage = MagicMock()
    response.usage.total_tokens = 100
    return response


@pytest.fixture
def mock_qianwen_response() -> MagicMock:
    """
    创建模拟阿里千问API响应

    Returns:
        MagicMock: 模拟响应对象
    """
    response = MagicMock()
    response.status_code = 200
    response.output = MagicMock()
    response.output.choices = [MagicMock()]
    response.output.choices[0].message = MagicMock()
    response.output.choices[0].message.content = "这是阿里千问的测试回复"
    return response


# ============================================================================
# HTTP客户端Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_aiohttp_session() -> MagicMock:
    """
    创建模拟aiohttp会话

    Returns:
        MagicMock: 模拟会话对象
    """
    session = MagicMock()
    session.get = AsyncMock()
    session.post = AsyncMock()
    session.put = AsyncMock()
    session.delete = AsyncMock()
    session.close = AsyncMock()
    session.closed = False
    return session


@pytest.fixture
def mock_http_response() -> MagicMock:
    """
    创建模拟HTTP响应

    Returns:
        MagicMock: 模拟HTTP响应对象
    """
    response = MagicMock()
    response.status = 200
    response.json = AsyncMock(return_value={"success": True, "data": {}})
    response.text = AsyncMock(return_value="OK")
    response.headers = {"Content-Type": "application/json"}
    return response
