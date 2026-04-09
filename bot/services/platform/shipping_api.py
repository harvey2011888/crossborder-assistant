"""
运费测算API客户端

封装运费测算API的调用，提供运费计算、物流线路查询等功能
API文档: docs/outapi/运费测算接口文档.md
"""

import logging
import secrets
from typing import Any, Optional

import aiohttp

from bot.core.config import config

# 配置日志
logger = logging.getLogger(__name__)


class ShippingAPIError(Exception):
    """运费API错误基类"""

    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class ShippingAPIClient:
    """
    运费测算API客户端

    封装运费测算API的HTTP请求，包括:
    - 运费计算
    - 物流线路查询
    - 商品类型查询
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30,
    ) -> None:
        """
        初始化运费API客户端

        Args:
            base_url: API基础URL，默认从配置读取
            api_key: API密钥，默认从配置读取
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url or config.shipping.api_url or ""
        self.api_key = api_key or config.shipping.api_key or ""
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None

        if not self.base_url:
            logger.warning("运费API基础URL未配置，运费测算功能将不可用")

    def _generate_nonce(self) -> str:
        """
        生成随机nonce字符串

        Returns:
            16位随机十六进制字符串
        """
        return secrets.token_hex(8)

    def _get_default_headers(self) -> dict[str, str]:
        """
        获取默认请求头

        Returns:
            包含Content-Type和nonce的请求头字典
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "nonce": self._generate_nonce(),
        }

        # 添加API密钥认证（如果有）
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        return headers

    async def _get_session(self) -> aiohttp.ClientSession:
        """
        获取或创建HTTP会话

        Returns:
            aiohttp.ClientSession实例
        """
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            )
        return self._session

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
            method: HTTP方法
            endpoint: API端点路径
            params: URL查询参数
            data: 请求体数据
            headers: 额外请求头

        Returns:
            API响应数据

        Raises:
            ShippingAPIError: API调用失败
        """
        if not self.base_url:
            raise ShippingAPIError("运费API基础URL未配置")

        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        session = await self._get_session()

        # 合并请求头
        request_headers = self._get_default_headers()
        if headers:
            request_headers.update(headers)

        logger.debug(f"运费API请求: {method} {url}")

        try:
            async with session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=request_headers,
            ) as response:
                try:
                    response_data = await response.json()
                except aiohttp.ContentTypeError:
                    response_text = await response.text()
                    response_data = {"raw_response": response_text}

                # 检查API返回的业务错误码
                if response_data.get("code") != 0 and response_data.get("code") != 200:
                    msg = response_data.get("msg", "未知错误")
                    raise ShippingAPIError(
                        f"API返回错误: {msg}",
                        status_code=response.status,
                        response_data=response_data,
                    )

                return response_data

        except aiohttp.ClientError as e:
            logger.error(f"运费API网络错误: {e}")
            raise ShippingAPIError(f"网络请求失败: {e}") from e
        except Exception as e:
            logger.error(f"运费API请求异常: {e}")
            raise ShippingAPIError(f"请求异常: {e}") from e

    async def calculate_postage(
        self,
        country: str,
        weight: int,
        length: int = 10,
        width: int = 10,
        height: int = 10,
        count: int = 1,
        category_types: Optional[list[int]] = None,
        request_type: int = 1,
    ) -> dict[str, Any]:
        """
        计算运费

        Args:
            country: 目的国家代码（如 "US"）
            weight: 包裹重量（克）
            length: 包裹长度（厘米），默认10
            width: 包裹宽度（厘米），默认10
            height: 包裹高度（厘米），默认10
            count: 包裹数量，默认1
            category_types: 商品类型ID列表，默认[189]（普货）
            request_type: 请求类型，默认1

        Returns:
            API响应数据，包含运费线路列表

        Raises:
            ShippingAPIError: API调用失败
        """
        if category_types is None:
            category_types = [189]  # 默认普货

        endpoint = "/express/pub/postage"
        data = {
            "country": country,
            "categoryTypes": category_types,
            "requestType": request_type,
            "arr": [
                {
                    "weight": weight,
                    "long": length,
                    "width": width,
                    "height": height,
                    "count": count,
                    "coefficient": 1,
                }
            ],
        }

        logger.info(f"计算运费: 国家={country}, 重量={weight}g, 尺寸={length}x{width}x{height}cm")
        return await self.request("POST", endpoint, data=data)

    async def get_express_types(self) -> dict[str, Any]:
        """
        获取快递类型列表

        Returns:
            API响应数据，包含快递类型列表

        Raises:
            ShippingAPIError: API调用失败
        """
        endpoint = "/express/pub/types"
        logger.info("获取快递类型列表")
        return await self.request("GET", endpoint)

    async def close(self) -> None:
        """
        关闭HTTP会话
        """
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("运费API客户端会话已关闭")

    def is_configured(self) -> bool:
        """
        检查客户端是否已配置

        Returns:
            如果基础URL已配置则返回True
        """
        return bool(self.base_url)


# 全局运费API客户端实例
shipping_api_client = ShippingAPIClient()
