"""
电商数据格式化模块

提供商品数据格式化、价格转换、图片URL处理等功能
"""

import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse, urlencode, urlunparse

from .models import Currency, PlatformType, Product, ProductImage, ProductPrice, SearchResult


class PriceConverter:
    """
    价格转换器

    支持多币种价格转换
    """

    # 汇率缓存（实际应用中应从API获取实时汇率）
    _exchange_rates: Dict[Tuple[Currency, Currency], Decimal] = {
        (Currency.CNY, Currency.USD): Decimal("0.138"),  # 1 CNY = 0.138 USD
        (Currency.CNY, Currency.EUR): Decimal("0.128"),  # 1 CNY = 0.128 EUR
        (Currency.CNY, Currency.GBP): Decimal("0.109"),  # 1 CNY = 0.109 GBP
        (Currency.CNY, Currency.JPY): Decimal("20.8"),   # 1 CNY = 20.8 JPY
        (Currency.USD, Currency.CNY): Decimal("7.25"),   # 1 USD = 7.25 CNY
        (Currency.EUR, Currency.CNY): Decimal("7.82"),   # 1 EUR = 7.82 CNY
        (Currency.GBP, Currency.CNY): Decimal("9.17"),   # 1 GBP = 9.17 CNY
        (Currency.JPY, Currency.CNY): Decimal("0.048"),  # 1 JPY = 0.048 CNY
    }

    @classmethod
    def get_exchange_rate(cls, from_currency: Currency, to_currency: Currency) -> Decimal:
        """
        获取汇率

        Args:
            from_currency: 源货币
            to_currency: 目标货币

        Returns:
            汇率
        """
        if from_currency == to_currency:
            return Decimal("1")

        # 直接汇率
        rate = cls._exchange_rates.get((from_currency, to_currency))
        if rate:
            return rate

        # 通过CNY中转
        cny_rate_from = cls._exchange_rates.get((from_currency, Currency.CNY), Decimal("1"))
        cny_rate_to = cls._exchange_rates.get((Currency.CNY, to_currency), Decimal("1"))

        return cny_rate_from * cny_rate_to

    @classmethod
    def convert(
        cls,
        amount: Decimal,
        from_currency: Currency,
        to_currency: Currency,
    ) -> Decimal:
        """
        转换金额

        Args:
            amount: 金额
            from_currency: 源货币
            to_currency: 目标货币

        Returns:
            转换后的金额
        """
        if from_currency == to_currency:
            return amount

        rate = cls.get_exchange_rate(from_currency, to_currency)
        return (amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    def convert_price(
        cls,
        price: ProductPrice,
        target_currency: Currency,
    ) -> ProductPrice:
        """
        转换价格对象

        Args:
            price: 价格对象
            target_currency: 目标货币

        Returns:
            转换后的价格对象
        """
        if price.currency == target_currency:
            return price

        rate = cls.get_exchange_rate(price.currency, target_currency)
        return price.convert_to(target_currency, rate)


class ImageURLProcessor:
    """
    图片URL处理器

    处理电商平台的图片URL，支持尺寸调整、格式转换等
    """

    # 淘宝图片尺寸映射
    TAOBAO_SIZE_MAP = {
        "small": "40x40",
        "medium": "230x230",
        "large": "430x430",
        "huge": "800x800",
    }

    # 京东图片尺寸映射
    JD_SIZE_MAP = {
        "small": "n5",
        "medium": "n1",
        "large": "n0",
        "huge": "n12",
    }

    @classmethod
    def process_taobao_image(cls, url: str, size: str = "large") -> str:
        """
        处理淘宝图片URL

        Args:
            url: 原始图片URL
            size: 尺寸大小 (small/medium/large/huge)

        Returns:
            处理后的URL
        """
        if not url:
            return url

        # 提取尺寸参数
        size_param = cls.TAOBAO_SIZE_MAP.get(size, "430x430")

        # 处理淘宝图片URL
        # 淘宝图片URL格式: https://img.alicdn.com/.../image.jpg
        if "alicdn.com" in url or "taobaocdn.com" in url:
            # 移除现有的尺寸参数
            url = re.sub(r"_\d+x\d+.*?(?=\.|$)", "", url)
            # 添加新的尺寸参数
            if "." in url:
                base, ext = url.rsplit(".", 1)
                url = f"{base}_{size_param}.{ext}"
            else:
                url = f"{url}_{size_param}"

        return url

    @classmethod
    def process_jd_image(cls, url: str, size: str = "large") -> str:
        """
        处理京东图片URL

        Args:
            url: 原始图片URL
            size: 尺寸大小 (small/medium/large/huge)

        Returns:
            处理后的URL
        """
        if not url:
            return url

        # 提取尺寸参数
        size_param = cls.JD_SIZE_MAP.get(size, "n1")

        # 处理京东图片URL
        # 京东图片URL格式: https://img10.360buyimg.com/.../image.jpg
        if "360buyimg.com" in url or "jd.com" in url:
            # 替换尺寸标识
            url = re.sub(r"/[ns]\d+/", f"/{size_param}/", url)
            # 如果没有尺寸标识，在适当位置添加
            if f"/{size_param}/" not in url:
                url = url.replace("/jfs/", f"/{size_param}/jfs/")

        return url

    @classmethod
    def process_image(cls, url: str, platform: PlatformType, size: str = "large") -> str:
        """
        根据平台处理图片URL

        Args:
            url: 原始图片URL
            platform: 平台类型
            size: 尺寸大小

        Returns:
            处理后的URL
        """
        if platform == PlatformType.TAOBAO or platform == PlatformType.TMALL:
            return cls.process_taobao_image(url, size)
        elif platform == PlatformType.JD:
            return cls.process_jd_image(url, size)
        return url

    @classmethod
    def process_product_images(cls, product: Product, size: str = "large") -> Product:
        """
        处理商品的所有图片

        Args:
            product: 商品对象
            size: 尺寸大小

        Returns:
            处理后的商品对象
        """
        # 处理主图
        if product.main_image:
            product.main_image = cls.process_image(
                product.main_image, product.platform, size
            )

        # 处理图片列表
        for img in product.images:
            img.url = cls.process_image(img.url, product.platform, size)

        return product


class ProductFormatter:
    """
    商品数据格式化器

    提供商品数据的格式化和转换功能
    """

    def __init__(self, target_currency: Optional[Currency] = None):
        """
        初始化格式化器

        Args:
            target_currency: 目标货币，用于价格转换
        """
        self.target_currency = target_currency

    def format_product(self, product: Product) -> Product:
        """
        格式化商品数据

        Args:
            product: 商品对象

        Returns:
            格式化后的商品对象
        """
        # 转换价格
        if self.target_currency and product.price.currency != self.target_currency:
            product.price = PriceConverter.convert_price(
                product.price, self.target_currency
            )

        # 处理图片
        product = ImageURLProcessor.process_product_images(product, "large")

        # 清理标题
        product.title = self._clean_title(product.title)

        # 清理描述
        if product.description:
            product.description = self._clean_description(product.description)

        return product

    def format_search_result(self, result: SearchResult) -> SearchResult:
        """
        格式化搜索结果

        Args:
            result: 搜索结果对象

        Returns:
            格式化后的搜索结果
        """
        result.products = [self.format_product(p) for p in result.products]
        return result

    def _clean_title(self, title: str) -> str:
        """
        清理商品标题

        Args:
            title: 原始标题

        Returns:
            清理后的标题
        """
        if not title:
            return ""

        # 移除HTML标签
        title = re.sub(r"<[^>]+>", "", title)
        # 移除多余空白
        title = re.sub(r"\s+", " ", title)
        # 移除特殊字符
        title = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f]", "", title)

        return title.strip()

    def _clean_description(self, description: str) -> str:
        """
        清理商品描述

        Args:
            description: 原始描述

        Returns:
            清理后的描述
        """
        if not description:
            return ""

        # 移除HTML标签
        description = re.sub(r"<[^>]+>", " ", description)
        # 移除多余空白
        description = re.sub(r"\s+", " ", description)
        # 移除特殊字符
        description = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f]", "", description)

        # 限制长度
        max_length = 500
        if len(description) > max_length:
            description = description[:max_length] + "..."

        return description.strip()


class ProductTranslator:
    """
    商品信息翻译器

    提供商品标题和描述的翻译功能
    """

    def __init__(self, ai_service=None):
        """
        初始化翻译器

        Args:
            ai_service: AI服务实例，用于翻译
        """
        self.ai_service = ai_service

    async def translate_product(
        self,
        product: Product,
        target_language: str = "en",
    ) -> Product:
        """
        翻译商品信息

        Args:
            product: 商品对象
            target_language: 目标语言代码

        Returns:
            翻译后的商品对象
        """
        if not self.ai_service:
            # 如果没有AI服务，返回原商品
            return product

        try:
            # 翻译标题
            if product.title:
                product.title_translated = await self._translate_text(
                    product.title, target_language
                )

            # 翻译描述
            if product.description:
                product.description_translated = await self._translate_text(
                    product.description, target_language
                )

            # 翻译规格
            for spec in product.specs:
                spec.name = await self._translate_text(spec.name, target_language) or spec.name
                spec.value = await self._translate_text(spec.value, target_language) or spec.value

        except Exception as e:
            # 翻译失败不影响商品数据
            pass

        return product

    async def _translate_text(self, text: str, target_language: str) -> Optional[str]:
        """
        翻译文本

        Args:
            text: 原文
            target_language: 目标语言

        Returns:
            译文
        """
        if not text or not self.ai_service:
            return None

        try:
            # 构建翻译Prompt
            prompt = f"请将以下中文翻译成{target_language}:\n{text}"

            # 调用AI服务
            response = await self.ai_service.chat(prompt)
            return response.strip() if response else None

        except Exception as e:
            return None


class URLExtractor:
    """
    URL提取器

    从文本中提取商品链接
    """

    # 平台URL模式
    URL_PATTERNS = {
        PlatformType.TAOBAO: [
            r"https?://item\.taobao\.com/item\.htm\?[^\s\"<>]+",
            r"https?://detail\.tmall\.com/item\.htm\?[^\s\"<>]+",
            r"https?://s\.click\.taobao\.com/[^\s\"<>]+",
        ],
        PlatformType.JD: [
            r"https?://item\.jd\.com/\d+\.html",
            r"https?://item\.jd\.hk/\d+\.html",
        ],
        PlatformType.TMALL: [
            r"https?://detail\.tmall\.com/item\.htm\?[^\s\"<>]+",
        ],
    }

    @classmethod
    def extract_urls(cls, text: str) -> Dict[PlatformType, List[str]]:
        """
        从文本中提取商品链接

        Args:
            text: 文本内容

        Returns:
            按平台分类的URL列表
        """
        results: Dict[PlatformType, List[str]] = {
            platform: [] for platform in PlatformType
        }

        for platform, patterns in cls.URL_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, text)
                results[platform].extend(matches)

        return results

    @classmethod
    def extract_product_id(cls, url: str, platform: PlatformType) -> Optional[str]:
        """
        从URL中提取商品ID

        Args:
            url: 商品链接
            platform: 平台类型

        Returns:
            商品ID
        """
        if platform == PlatformType.TAOBAO or platform == PlatformType.TMALL:
            # 淘宝/天猫: https://item.taobao.com/item.htm?id=123456
            match = re.search(r"[?&]id=(\d+)", url)
            return match.group(1) if match else None

        elif platform == PlatformType.JD:
            # 京东: https://item.jd.com/123456.html
            match = re.search(r"/(\d+)\.html", url)
            return match.group(1) if match else None

        return None


class ProductComparer:
    """
    商品比较器

    提供商品比较功能
    """

    @staticmethod
    def compare_prices(products: List[Product]) -> Dict[str, Any]:
        """
        比较商品价格

        Args:
            products: 商品列表

        Returns:
            价格比较结果
        """
        if not products:
            return {}

        # 统一货币
        target_currency = products[0].price.currency
        prices = []

        for p in products:
            price = p.price
            if price.currency != target_currency:
                price = PriceConverter.convert_price(price, target_currency)
            prices.append({
                "product_id": p.product_id,
                "platform": p.platform.value,
                "title": p.title[:50] + "..." if len(p.title) > 50 else p.title,
                "price": float(price.current_price),
                "currency": price.currency.value,
            })

        # 排序
        prices.sort(key=lambda x: x["price"])

        return {
            "cheapest": prices[0] if prices else None,
            "most_expensive": prices[-1] if prices else None,
            "all_prices": prices,
            "price_range": {
                "min": prices[0]["price"] if prices else 0,
                "max": prices[-1]["price"] if prices else 0,
            },
        }

    @staticmethod
    def compare_ratings(products: List[Product]) -> Dict[str, Any]:
        """
        比较商品评分

        Args:
            products: 商品列表

        Returns:
            评分比较结果
        """
        rated_products = [p for p in products if p.rating is not None]

        if not rated_products:
            return {}

        rated_products.sort(key=lambda x: x.rating or 0, reverse=True)

        return {
            "highest_rated": {
                "product_id": rated_products[0].product_id,
                "platform": rated_products[0].platform.value,
                "title": rated_products[0].title[:50] + "...",
                "rating": rated_products[0].rating,
            },
            "average_rating": sum(p.rating or 0 for p in rated_products) / len(rated_products),
            "rated_count": len(rated_products),
        }

    @staticmethod
    def compare_sales(products: List[Product]) -> Dict[str, Any]:
        """
        比较商品销量

        Args:
            products: 商品列表

        Returns:
            销量比较结果
        """
        products_with_sales = [p for p in products if p.sales_count is not None]

        if not products_with_sales:
            return {}

        products_with_sales.sort(key=lambda x: x.sales_count or 0, reverse=True)

        return {
            "best_selling": {
                "product_id": products_with_sales[0].product_id,
                "platform": products_with_sales[0].platform.value,
                "title": products_with_sales[0].title[:50] + "...",
                "sales": products_with_sales[0].sales_count,
            },
            "total_sales": sum(p.sales_count or 0 for p in products_with_sales),
        }
