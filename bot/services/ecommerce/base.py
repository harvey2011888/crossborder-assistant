"""
电商平台API基类

定义统一的电商平台接口规范
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .models import PlatformType, Product, SearchResult


class EcommerceAPIError(Exception):
    """电商平台API错误基类"""

    def __init__(self, message: str, code: Optional[str] = None, raw_response: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.raw_response = raw_response


class APIRateLimitError(EcommerceAPIError):
    """API速率限制错误"""

    pass


class APITimeoutError(EcommerceAPIError):
    """API超时错误"""

    pass


class APIAuthenticationError(EcommerceAPIError):
    """API认证错误"""

    pass


class BaseEcommerceClient(ABC):
    """
    电商平台API客户端基类

    定义所有电商平台客户端必须实现的接口
    """

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """
        初始化客户端

        Args:
            api_key: API密钥
            api_secret: API密钥
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self._session = None

    @property
    @abstractmethod
    def platform(self) -> PlatformType:
        """返回平台类型"""
        pass

    @property
    @abstractmethod
    def base_url(self) -> str:
        """返回API基础URL"""
        pass

    @abstractmethod
    async def search_products(
        self,
        query: str,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "default",
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        **kwargs: Any,
    ) -> SearchResult:
        """
        搜索商品

        Args:
            query: 搜索关键词
            page: 页码
            page_size: 每页数量
            sort_by: 排序方式
            min_price: 最低价格
            max_price: 最高价格
            **kwargs: 其他参数

        Returns:
            搜索结果
        """
        pass

    @abstractmethod
    async def get_product_detail(self, product_id: str, **kwargs: Any) -> Optional[Product]:
        """
        获取商品详情

        Args:
            product_id: 商品ID
            **kwargs: 其他参数

        Returns:
            商品详情，不存在则返回None
        """
        pass

    @abstractmethod
    async def get_product_by_url(self, url: str, **kwargs: Any) -> Optional[Product]:
        """
        通过URL获取商品信息

        Args:
            url: 商品链接
            **kwargs: 其他参数

        Returns:
            商品详情，不存在则返回None
        """
        pass

    async def close(self) -> None:
        """关闭客户端连接"""
        if self._session:
            await self._session.close()
            self._session = None

    def _build_search_params(
        self,
        query: str,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "default",
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        构建搜索参数

        Args:
            query: 搜索关键词
            page: 页码
            page_size: 每页数量
            sort_by: 排序方式
            min_price: 最低价格
            max_price: 最高价格

        Returns:
            参数字典
        """
        params: Dict[str, Any] = {
            "q": query,
            "page": page,
            "page_size": page_size,
            "sort": sort_by,
        }

        if min_price is not None:
            params["min_price"] = min_price
        if max_price is not None:
            params["max_price"] = max_price

        return params

    def _parse_sales_count(self, sales_text: Optional[str]) -> Optional[int]:
        """
        解析销量文本

        Args:
            sales_text: 销量文本，如"已售1.2万+"

        Returns:
            销量数字
        """
        if not sales_text:
            return None

        import re

        # 移除常见前缀
        sales_text = sales_text.replace("已售", "").replace("月销", "").replace("+", "").strip()

        # 匹配数字
        match = re.search(r"(\d+\.?\d*)", sales_text)
        if not match:
            return None

        number = float(match.group(1))

        # 处理单位
        if "万" in sales_text:
            number *= 10000
        elif "千" in sales_text:
            number *= 1000
        elif "百" in sales_text:
            number *= 100

        return int(number)

    def _clean_html(self, text: Optional[str]) -> Optional[str]:
        """
        清理HTML标签

        Args:
            text: 包含HTML的文本

        Returns:
            清理后的文本
        """
        if not text:
            return None

        import re

        # 移除HTML标签
        clean = re.sub(r"<[^>]+>", "", text)
        # 移除多余空白
        clean = re.sub(r"\s+", " ", clean)
        return clean.strip()
