"""
自建平台API客户端基类

提供HTTP客户端封装、认证机制、请求/响应日志等功能
用于对接自建跨境电商平台的API服务
"""

import logging
from typing import Any, Optional
from urllib.parse import urljoin

import aiohttp

from bot.core.config import config

# 配置日志
logger = logging.getLogger(__name__)


class PlatformAPIError(Exception):
    """平台API错误基类"""

    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class PlatformAuthError(PlatformAPIError):
    """平台认证错误"""
    pass


class PlatformRequestError(PlatformAPIError):
    """平台请求错误"""
    pass


class PlatformClient:
    """
    自建平台API客户端基类

    封装HTTP请求、认证、日志等功能，为订单管理、物流服务等提供基础支持
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30,
    ) -> None:
        """
        初始化平台API客户端

        Args:
            base_url: API基础URL，默认从环境变量读取
            api_key: API密钥，默认从环境变量读取
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url or config.platform.api_url or ""
        self.api_key = api_key or config.platform.api_key or ""
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None

        # 验证配置
        if not self.base_url:
            logger.warning("平台API基础URL未配置，平台功能将不可用")
        if not self.api_key:
            logger.warning("平台API密钥未配置，认证功能将不可用")

    async def _get_session(self) -> aiohttp.ClientSession:
        """
        获取或创建HTTP会话

        Returns:
            aiohttp.ClientSession实例
        """
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers=self._get_default_headers(),
            )
        return self._session

    def _get_default_headers(self) -> dict[str, str]:
        """
        获取默认请求头

        Returns:
            包含认证信息的请求头字典
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "CrossBorderBot/1.0",
        }

        # 添加API密钥认证
        if self.api_key:
            headers["X-API-Key"] = self.api_key
            # 也支持Authorization头部（Bearer Token格式）
            headers["Authorization"] = f"Bearer {self.api_key}"

        return headers

    def _build_url(self, endpoint: str) -> str:
        """
        构建完整API URL

        Args:
            endpoint: API端点路径

        Returns:
            完整的API URL
        """
        if not self.base_url:
            raise PlatformAPIError("平台API基础URL未配置")
        return urljoin(self.base_url.rstrip("/") + "/", endpoint.lstrip("/"))

    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """
        发送HTTP请求

        Args:
            method: HTTP方法 (GET, POST, PUT, DELETE等)
            endpoint: API端点路径
            params: URL查询参数
            data: 请求体数据
            headers: 额外请求头

        Returns:
            API响应数据（JSON格式）

        Raises:
            PlatformAuthError: 认证失败
            PlatformRequestError: 请求失败
            PlatformAPIError: 其他API错误
        """
        if not self.base_url:
            raise PlatformAPIError("平台API基础URL未配置，无法发送请求")

        url = self._build_url(endpoint)
        session = await self._get_session()

        # 合并请求头
        request_headers = self._get_default_headers()
        if headers:
            request_headers.update(headers)

        # 记录请求日志
        logger.debug(f"平台API请求: {method} {url}")
        if params:
            logger.debug(f"请求参数: {params}")
        if data:
            # 隐藏敏感信息
            safe_data = self._sanitize_log_data(data)
            logger.debug(f"请求数据: {safe_data}")

        try:
            async with session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=request_headers,
            ) as response:
                # 读取响应内容
                try:
                    response_data = await response.json()
                except aiohttp.ContentTypeError:
                    response_text = await response.text()
                    response_data = {"raw_response": response_text}

                # 记录响应日志
                logger.debug(f"平台API响应: {response.status}")

                # 处理HTTP错误状态码
                if response.status == 401:
                    raise PlatformAuthError(
                        "平台API认证失败，请检查API密钥配置",
                        status_code=response.status,
                        response_data=response_data,
                    )
                elif response.status == 403:
                    raise PlatformAuthError(
                        "平台API访问被拒绝，请检查权限配置",
                        status_code=response.status,
                        response_data=response_data,
                    )
                elif response.status == 404:
                    raise PlatformRequestError(
                        f"平台API端点不存在: {endpoint}",
                        status_code=response.status,
                        response_data=response_data,
                    )
                elif response.status >= 500:
                    raise PlatformAPIError(
                        f"平台服务器错误: {response.status}",
                        status_code=response.status,
                        response_data=response_data,
                    )
                elif response.status >= 400:
                    raise PlatformRequestError(
                        f"平台API请求错误: {response.status}",
                        status_code=response.status,
                        response_data=response_data,
                    )

                return response_data

        except aiohttp.ClientError as e:
            logger.error(f"平台API网络错误: {e}")
            raise PlatformAPIError(f"网络请求失败: {e}") from e
        except Exception as e:
            logger.error(f"平台API请求异常: {e}")
            raise PlatformAPIError(f"请求异常: {e}") from e

    async def get(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """
        发送GET请求

        Args:
            endpoint: API端点路径
            params: URL查询参数
            headers: 额外请求头

        Returns:
            API响应数据
        """
        return await self.request("GET", endpoint, params=params, headers=headers)

    async def post(
        self,
        endpoint: str,
        data: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """
        发送POST请求

        Args:
            endpoint: API端点路径
            data: 请求体数据
            params: URL查询参数
            headers: 额外请求头

        Returns:
            API响应数据
        """
        return await self.request("POST", endpoint, params=params, data=data, headers=headers)

    async def put(
        self,
        endpoint: str,
        data: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """
        发送PUT请求

        Args:
            endpoint: API端点路径
            data: 请求体数据
            params: URL查询参数
            headers: 额外请求头

        Returns:
            API响应数据
        """
        return await self.request("PUT", endpoint, params=params, data=data, headers=headers)

    async def delete(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """
        发送DELETE请求

        Args:
            endpoint: API端点路径
            params: URL查询参数
            headers: 额外请求头

        Returns:
            API响应数据
        """
        return await self.request("DELETE", endpoint, params=params, headers=headers)

    def _sanitize_log_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        清理日志数据中的敏感信息

        Args:
            data: 原始数据

        Returns:
            清理后的数据副本
        """
        sensitive_fields = {"password", "token", "api_key", "secret", "credit_card"}
        safe_data = {}
        for key, value in data.items():
            if any(field in key.lower() for field in sensitive_fields):
                safe_data[key] = "***"
            elif isinstance(value, dict):
                safe_data[key] = self._sanitize_log_data(value)
            else:
                safe_data[key] = value
        return safe_data

    async def close(self) -> None:
        """
        关闭HTTP会话

        应在程序结束时调用，释放资源
        """
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("平台API客户端会话已关闭")

    async def health_check(self) -> dict[str, Any]:
        """
        健康检查

        检查平台API服务是否可用

        Returns:
            健康状态信息

        Raises:
            PlatformAPIError: 健康检查失败
        """
        if not self.base_url:
            return {
                "status": "not_configured",
                "message": "平台API基础URL未配置",
            }

        try:
            # 尝试调用健康检查端点（常见端点：/health, /api/health, /status）
            for endpoint in ["/health", "/api/health", "/status"]:
                try:
                    response = await self.get(endpoint)
                    return {
                        "status": "healthy",
                        "endpoint": endpoint,
                        "response": response,
                    }
                except PlatformRequestError:
                    continue

            # 如果健康检查端点都不存在，尝试调用根路径
            response = await self.get("/")
            return {
                "status": "available",
                "endpoint": "/",
                "response": response,
            }

        except PlatformAuthError as e:
            return {
                "status": "auth_required",
                "message": "API需要认证，但配置可能正确",
                "error": str(e),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"健康检查失败: {e}",
            }

    def is_configured(self) -> bool:
        """
        检查客户端是否已配置

        Returns:
            如果基础URL和API密钥都已配置则返回True
        """
        return bool(self.base_url and self.api_key)
