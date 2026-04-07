"""
平台API客户端单元测试

测试PlatformClient的各种功能
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.services.platform.client import (
    PlatformAPIError,
    PlatformAuthError,
    PlatformClient,
    PlatformRequestError,
)


@pytest.mark.unit
class TestPlatformClient:
    """PlatformClient测试类"""

    def test_init_with_params(self) -> None:
        """测试使用参数初始化客户端"""
        client = PlatformClient(
            base_url="https://custom.api.com",
            api_key="custom_key",
            timeout=60,
        )

        assert client.base_url == "https://custom.api.com"
        assert client.api_key == "custom_key"
        assert client.timeout == 60

    def test_init_without_config(self) -> None:
        """测试未配置时的初始化"""
        with patch.dict("os.environ", {}, clear=True):
            client = PlatformClient()

            assert client.base_url == ""
            assert client.api_key == ""

    def test_is_configured_true(self) -> None:
        """测试is_configured返回True"""
        client = PlatformClient(
            base_url="https://api.example.com",
            api_key="test_key",
        )

        assert client.is_configured() is True

    def test_is_configured_false(self) -> None:
        """测试is_configured返回False"""
        client = PlatformClient(base_url="", api_key="")

        assert client.is_configured() is False

    def test_get_default_headers(self) -> None:
        """测试获取默认请求头"""
        client = PlatformClient(
            base_url="https://api.example.com",
            api_key="test_key",
        )

        headers = client._get_default_headers()

        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"
        assert headers["User-Agent"] == "CrossBorderBot/1.0"
        assert headers["X-API-Key"] == "test_key"
        assert headers["Authorization"] == "Bearer test_key"

    def test_build_url(self) -> None:
        """测试构建URL"""
        client = PlatformClient(base_url="https://api.example.com")

        url = client._build_url("/orders")
        assert url == "https://api.example.com/orders"

    def test_build_url_without_base_url(self) -> None:
        """测试没有基础URL时构建URL应抛出异常"""
        client = PlatformClient()

        with pytest.raises(PlatformAPIError, match="平台API基础URL未配置"):
            client._build_url("/orders")

    def test_sanitize_log_data(self) -> None:
        """测试日志数据脱敏"""
        client = PlatformClient()

        data = {
            "username": "test_user",
            "password": "secret123",
            "api_key": "key123",
        }

        sanitized = client._sanitize_log_data(data)

        assert sanitized["username"] == "test_user"
        assert sanitized["password"] == "***"
        assert sanitized["api_key"] == "***"


@pytest.mark.unit
@pytest.mark.asyncio
class TestPlatformClientAsync:
    """PlatformClient异步方法测试类"""

    async def test_close(self) -> None:
        """测试关闭会话"""
        client = PlatformClient()

        mock_session = AsyncMock()
        mock_session.closed = False
        client._session = mock_session

        await client.close()

        mock_session.close.assert_called_once()

    async def test_health_check_not_configured(self) -> None:
        """测试未配置时的健康检查"""
        client = PlatformClient()

        result = await client.health_check()

        assert result["status"] == "not_configured"
