"""
电商平台客户端工厂

提供统一的电商平台客户端创建和管理
"""

import os
from typing import Dict, List, Optional, Type

from .base import BaseEcommerceClient
from .jd import JDClient
from .models import Currency, PlatformType, Product, SearchResult
from .taobao import TaobaoClient


class EcommerceClientFactory:
    """
    电商平台客户端工厂

    统一管理所有电商平台客户端的创建和配置
    """

    # 客户端注册表
    _clients: Dict[PlatformType, Type[BaseEcommerceClient]] = {
        PlatformType.TAOBAO: TaobaoClient,
        PlatformType.JD: JDClient,
    }

    # 客户端实例缓存
    _instances: Dict[PlatformType, BaseEcommerceClient] = {}

    @classmethod
    def create_client(
        cls,
        platform: PlatformType,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        **kwargs,
    ) -> BaseEcommerceClient:
        """
        创建电商平台客户端

        Args:
            platform: 平台类型
            api_key: API密钥
            api_secret: API密钥
            **kwargs: 其他参数

        Returns:
            客户端实例

        Raises:
            ValueError: 不支持的电商平台
        """
        client_class = cls._clients.get(platform)
        if not client_class:
            raise ValueError(f"不支持的电商平台: {platform}")

        # 从环境变量加载配置
        if not api_key:
            if platform == PlatformType.TAOBAO:
                api_key = os.getenv("TAOBAO_APP_KEY")
            elif platform == PlatformType.JD:
                api_key = os.getenv("JD_APP_KEY")

        if not api_secret:
            if platform == PlatformType.TAOBAO:
                api_secret = os.getenv("TAOBAO_APP_SECRET")
            elif platform == PlatformType.JD:
                api_secret = os.getenv("JD_APP_SECRET")

        return client_class(api_key=api_key, api_secret=api_secret, **kwargs)

    @classmethod
    def get_client(
        cls,
        platform: PlatformType,
        use_cache: bool = True,
        **kwargs,
    ) -> BaseEcommerceClient:
        """
        获取电商平台客户端（带缓存）

        Args:
            platform: 平台类型
            use_cache: 是否使用缓存
            **kwargs: 其他参数

        Returns:
            客户端实例
        """
        if use_cache and platform in cls._instances:
            return cls._instances[platform]

        client = cls.create_client(platform, **kwargs)

        if use_cache:
            cls._instances[platform] = client

        return client

    @classmethod
    def register_client(
        cls,
        platform: PlatformType,
        client_class: Type[BaseEcommerceClient],
    ) -> None:
        """
        注册新的电商平台客户端

        Args:
            platform: 平台类型
            client_class: 客户端类
        """
        cls._clients[platform] = client_class

    @classmethod
    def get_supported_platforms(cls) -> List[PlatformType]:
        """
        获取支持的电商平台列表

        Returns:
            平台类型列表
        """
        return list(cls._clients.keys())

    @classmethod
    async def close_all(cls) -> None:
        """关闭所有客户端连接"""
        for client in cls._instances.values():
            await client.close()
        cls._instances.clear()


class MultiPlatformSearcher:
    """
    多平台商品搜索器

    支持同时在多个电商平台搜索商品
    """

    def __init__(
        self,
        platforms: Optional[List[PlatformType]] = None,
        target_currency: Optional[Currency] = None,
    ):
        """
        初始化多平台搜索器

        Args:
            platforms: 要搜索的平台列表，默认为所有支持的平台
            target_currency: 目标货币
        """
        self.platforms = platforms or EcommerceClientFactory.get_supported_platforms()
        self.target_currency = target_currency
        self._clients: Dict[PlatformType, BaseEcommerceClient] = {}

    async def __aenter__(self):
        """异步上下文管理器入口"""
        for platform in self.platforms:
            try:
                self._clients[platform] = EcommerceClientFactory.get_client(platform)
            except Exception as e:
                # 如果某个平台客户端创建失败，跳过
                continue
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        for client in self._clients.values():
            await client.close()
        self._clients.clear()

    async def search(
        self,
        query: str,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "default",
        max_results_per_platform: int = 10,
    ) -> Dict[PlatformType, SearchResult]:
        """
        在多个平台搜索商品

        Args:
            query: 搜索关键词
            page: 页码
            page_size: 每页数量
            sort_by: 排序方式
            max_results_per_platform: 每个平台最大结果数

        Returns:
            按平台分类的搜索结果
        """
        results: Dict[PlatformType, SearchResult] = {}

        for platform, client in self._clients.items():
            try:
                result = await client.search_products(
                    query=query,
                    page=page,
                    page_size=min(page_size, max_results_per_platform),
                    sort_by=sort_by,
                )

                # 转换价格
                if self.target_currency:
                    for product in result.products:
                        if product.price.currency != self.target_currency:
                            from .formatter import PriceConverter

                            product.price = PriceConverter.convert_price(
                                product.price, self.target_currency
                            )

                results[platform] = result

            except Exception as e:
                # 某个平台搜索失败，继续搜索其他平台
                results[platform] = SearchResult(
                    query=query,
                    platform=platform,
                )

        return results

    async def search_all(
        self,
        query: str,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "default",
        max_results_per_platform: int = 10,
    ) -> SearchResult:
        """
        在多个平台搜索并合并结果

        Args:
            query: 搜索关键词
            page: 页码
            page_size: 每页数量
            sort_by: 排序方式
            max_results_per_platform: 每个平台最大结果数

        Returns:
            合并后的搜索结果
        """
        platform_results = await self.search(
            query=query,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            max_results_per_platform=max_results_per_platform,
        )

        # 合并所有结果
        all_products = []
        total = 0

        for result in platform_results.values():
            all_products.extend(result.products)
            total += result.total

        # 根据排序方式重新排序
        if sort_by == "price_asc":
            all_products.sort(key=lambda p: p.price.current_price)
        elif sort_by == "price_desc":
            all_products.sort(key=lambda p: p.price.current_price, reverse=True)
        elif sort_by == "sales":
            all_products.sort(
                key=lambda p: p.sales_count or 0,
                reverse=True,
            )

        return SearchResult(
            products=all_products,
            total=total,
            page=page,
            page_size=page_size,
            has_more=total > page * page_size,
            query=query,
            platform=None,  # 多平台搜索
        )

    async def get_product(
        self,
        product_url: str,
    ) -> Optional[Product]:
        """
        通过URL获取商品信息

        Args:
            product_url: 商品链接

        Returns:
            商品信息
        """
        from .formatter import URLExtractor

        # 识别平台
        urls_by_platform = URLExtractor.extract_urls(product_url)

        for platform, urls in urls_by_platform.items():
            if urls and platform in self._clients:
                try:
                    client = self._clients[platform]
                    return await client.get_product_by_url(urls[0])
                except Exception as e:
                    continue

        return None


# 便捷的搜索函数
async def search_products(
    query: str,
    platforms: Optional[List[PlatformType]] = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "default",
    target_currency: Optional[Currency] = None,
) -> Dict[PlatformType, SearchResult]:
    """
    搜索商品（便捷函数）

    Args:
        query: 搜索关键词
        platforms: 要搜索的平台列表
        page: 页码
        page_size: 每页数量
        sort_by: 排序方式
        target_currency: 目标货币

    Returns:
        搜索结果
    """
    async with MultiPlatformSearcher(platforms, target_currency) as searcher:
        return await searcher.search(query, page, page_size, sort_by)


async def get_product_by_url(url: str) -> Optional[Product]:
    """
    通过URL获取商品信息（便捷函数）

    Args:
        url: 商品链接

    Returns:
        商品信息
    """
    async with MultiPlatformSearcher() as searcher:
        return await searcher.get_product(url)
