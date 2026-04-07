"""
电商平台服务模块

包含淘宝、京东等电商平台API集成

使用示例:
    # 搜索商品
    from bot.services.ecommerce import search_products, PlatformType

    results = await search_products(
        query="手机",
        platforms=[PlatformType.TAOBAO, PlatformType.JD],
        page=1,
        page_size=20
    )

    # 获取商品详情
    from bot.services.ecommerce import get_product_by_url

    product = await get_product_by_url("https://item.taobao.com/item.htm?id=123456")

    # 使用工厂创建客户端
    from bot.services.ecommerce import EcommerceClientFactory

    client = EcommerceClientFactory.create_client(PlatformType.TAOBAO)
    result = await client.search_products("手机")
"""

from .base import (
    APIAuthenticationError,
    APIRateLimitError,
    APITimeoutError,
    BaseEcommerceClient,
    EcommerceAPIError,
)
from .factory import (
    EcommerceClientFactory,
    MultiPlatformSearcher,
    get_product_by_url,
    search_products,
)
from .formatter import (
    ImageURLProcessor,
    PriceConverter,
    ProductComparer,
    ProductFormatter,
    ProductTranslator,
    URLExtractor,
)
from .jd import JDClient
from .models import (
    Currency,
    PlatformType,
    PriceHistory,
    Product,
    ProductImage,
    ProductPrice,
    ProductSKU,
    ProductSpec,
    ProductStatus,
    SearchResult,
    ShopInfo,
)
from .taobao import TaobaoClient

__all__ = [
    # 模型类
    "Product",
    "ProductPrice",
    "ProductImage",
    "ProductSpec",
    "ProductSKU",
    "ShopInfo",
    "SearchResult",
    "PriceHistory",
    "PlatformType",
    "Currency",
    "ProductStatus",
    # 客户端类
    "BaseEcommerceClient",
    "TaobaoClient",
    "JDClient",
    # 工厂类
    "EcommerceClientFactory",
    "MultiPlatformSearcher",
    # 格式化工具
    "PriceConverter",
    "ImageURLProcessor",
    "ProductFormatter",
    "ProductTranslator",
    "URLExtractor",
    "ProductComparer",
    # 便捷函数
    "search_products",
    "get_product_by_url",
    # 异常类
    "EcommerceAPIError",
    "APIAuthenticationError",
    "APIRateLimitError",
    "APITimeoutError",
]
