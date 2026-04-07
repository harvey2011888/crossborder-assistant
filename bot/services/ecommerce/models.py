"""
电商平台商品数据模型

定义统一的商品数据结构，使用Pydantic模型进行验证和序列化
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class PlatformType(str, Enum):
    """电商平台类型枚举"""

    TAOBAO = "taobao"
    JD = "jd"
    TMALL = "tmall"
    PDD = "pdd"


class Currency(str, Enum):
    """货币类型枚举"""

    CNY = "CNY"  # 人民币
    USD = "USD"  # 美元
    EUR = "EUR"  # 欧元
    GBP = "GBP"  # 英镑
    JPY = "JPY"  # 日元


class ProductStatus(str, Enum):
    """商品状态枚举"""

    ON_SALE = "on_sale"  # 在售
    OUT_OF_STOCK = "out_of_stock"  # 缺货
    OFF_SHELF = "off_shelf"  # 下架
    UNKNOWN = "unknown"  # 未知


class ProductImage(BaseModel):
    """商品图片模型"""

    url: str = Field(..., description="图片URL")
    width: Optional[int] = Field(None, description="图片宽度")
    height: Optional[int] = Field(None, description="图片高度")
    is_main: bool = Field(False, description="是否主图")


class ProductPrice(BaseModel):
    """商品价格模型"""

    original_price: Decimal = Field(..., description="原价")
    current_price: Decimal = Field(..., description="现价")
    currency: Currency = Field(default=Currency.CNY, description="货币类型")
    discount: Optional[str] = Field(None, description="折扣信息")

    @field_validator("original_price", "current_price", mode="before")
    @classmethod
    def validate_price(cls, value: Any) -> Decimal:
        """验证价格字段"""
        if isinstance(value, (int, float, str)):
            return Decimal(str(value))
        return value

    def convert_to(self, target_currency: Currency, rate: Decimal) -> "ProductPrice":
        """
        转换价格到目标货币

        Args:
            target_currency: 目标货币
            rate: 汇率

        Returns:
            转换后的价格对象
        """
        return ProductPrice(
            original_price=self.original_price * rate,
            current_price=self.current_price * rate,
            currency=target_currency,
            discount=self.discount,
        )


class ProductSpec(BaseModel):
    """商品规格模型"""

    name: str = Field(..., description="规格名称")
    value: str = Field(..., description="规格值")


class ProductSKU(BaseModel):
    """商品SKU模型"""

    sku_id: str = Field(..., description="SKU ID")
    specs: List[ProductSpec] = Field(default_factory=list, description="规格列表")
    price: ProductPrice = Field(..., description="SKU价格")
    stock: Optional[int] = Field(None, description="库存数量")
    image_url: Optional[str] = Field(None, description="SKU图片")


class ShopInfo(BaseModel):
    """店铺信息模型"""

    shop_id: Optional[str] = Field(None, description="店铺ID")
    shop_name: str = Field(..., description="店铺名称")
    shop_url: Optional[str] = Field(None, description="店铺链接")
    shop_rating: Optional[float] = Field(None, description="店铺评分")
    shop_level: Optional[str] = Field(None, description="店铺等级")


class Product(BaseModel):
    """
    统一商品数据模型

    用于标准化不同电商平台的商品数据
    """

    # 基础信息
    product_id: str = Field(..., description="商品ID")
    platform: PlatformType = Field(..., description="所属平台")
    title: str = Field(..., description="商品标题")
    title_translated: Optional[str] = Field(None, description="翻译后的标题")

    # 链接
    product_url: str = Field(..., description="商品链接")
    short_url: Optional[str] = Field(None, description="短链接")

    # 价格
    price: ProductPrice = Field(..., description="价格信息")

    # 图片
    images: List[ProductImage] = Field(default_factory=list, description="图片列表")
    main_image: Optional[str] = Field(None, description="主图URL")

    # 描述
    description: Optional[str] = Field(None, description="商品描述")
    description_translated: Optional[str] = Field(None, description="翻译后的描述")

    # 规格
    specs: List[ProductSpec] = Field(default_factory=list, description="商品规格")
    skus: List[ProductSKU] = Field(default_factory=list, description="SKU列表")

    # 店铺信息
    shop: Optional[ShopInfo] = Field(None, description="店铺信息")

    # 销量和评价
    sales_count: Optional[int] = Field(None, description="销量")
    rating: Optional[float] = Field(None, description="评分")
    review_count: Optional[int] = Field(None, description="评价数量")

    # 状态
    status: ProductStatus = Field(default=ProductStatus.UNKNOWN, description="商品状态")

    # 物流
    location: Optional[str] = Field(None, description="发货地")
    shipping_fee: Optional[Decimal] = Field(None, description="运费")

    # 元数据
    category: Optional[str] = Field(None, description="商品分类")
    brand: Optional[str] = Field(None, description="品牌")
    keywords: List[str] = Field(default_factory=list, description="关键词")

    # 时间戳
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

    # 原始数据（用于调试和扩展）
    raw_data: Optional[Dict[str, Any]] = Field(None, description="原始API数据")

    class Config:
        """Pydantic配置"""

        json_encoders = {Decimal: str, datetime: lambda v: v.isoformat()}

    def get_main_image_url(self) -> Optional[str]:
        """获取主图URL"""
        if self.main_image:
            return self.main_image
        for img in self.images:
            if img.is_main:
                return img.url
        return self.images[0].url if self.images else None

    def get_formatted_price(self, locale: str = "zh-CN") -> str:
        """
        获取格式化价格字符串

        Args:
            locale: 地区设置

        Returns:
            格式化后的价格字符串
        """
        currency_symbols = {
            Currency.CNY: "¥",
            Currency.USD: "$",
            Currency.EUR: "€",
            Currency.GBP: "£",
            Currency.JPY: "¥",
        }
        symbol = currency_symbols.get(self.price.currency, "")

        if self.price.original_price > self.price.current_price:
            return f"~~{symbol}{self.price.original_price}~~ {symbol}{self.price.current_price}"
        return f"{symbol}{self.price.current_price}"

    def to_embed_dict(self) -> Dict[str, Any]:
        """
        转换为Discord Embed格式字典

        Returns:
            Embed格式字典
        """
        title = self.title_translated or self.title
        if len(title) > 256:
            title = title[:253] + "..."

        description = self.description_translated or self.description or ""
        if len(description) > 4096:
            description = description[:4093] + "..."

        fields = [
            {"name": "价格", "value": self.get_formatted_price(), "inline": True},
            {"name": "平台", "value": self.platform.value.upper(), "inline": True},
        ]

        if self.sales_count:
            fields.append({"name": "销量", "value": f"{self.sales_count}", "inline": True})

        if self.rating:
            fields.append({"name": "评分", "value": f"⭐ {self.rating}", "inline": True})

        if self.shop:
            fields.append({"name": "店铺", "value": self.shop.shop_name, "inline": True})

        if self.location:
            fields.append({"name": "发货地", "value": self.location, "inline": True})

        embed_dict = {
            "title": title,
            "description": description,
            "url": self.product_url,
            "fields": fields,
            "image": {"url": self.get_main_image_url()},
        }

        return embed_dict


class SearchResult(BaseModel):
    """搜索结果模型"""

    products: List[Product] = Field(default_factory=list, description="商品列表")
    total: int = Field(0, description="总数量")
    page: int = Field(1, description="当前页码")
    page_size: int = Field(20, description="每页数量")
    has_more: bool = Field(False, description="是否有更多结果")
    query: str = Field("", description="搜索关键词")
    platform: Optional[PlatformType] = Field(None, description="搜索平台")

    def get_best_match(self) -> Optional[Product]:
        """获取最佳匹配商品（根据销量和评分）"""
        if not self.products:
            return None

        def score_product(product: Product) -> float:
            """计算商品得分"""
            score = 0.0
            if product.sales_count:
                score += min(product.sales_count / 1000, 100)
            if product.rating:
                score += product.rating * 10
            return score

        return max(self.products, key=score_product)


class PriceHistory(BaseModel):
    """价格历史记录模型"""

    product_id: str = Field(..., description="商品ID")
    platform: PlatformType = Field(..., description="平台")
    prices: List[Dict[str, Any]] = Field(default_factory=list, description="价格记录列表")

    def add_price(self, price: ProductPrice) -> None:
        """添加价格记录"""
        self.prices.append(
            {
                "price": float(price.current_price),
                "currency": price.currency.value,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def get_lowest_price(self) -> Optional[Decimal]:
        """获取历史最低价"""
        if not self.prices:
            return None
        return Decimal(str(min(p["price"] for p in self.prices)))

    def get_highest_price(self) -> Optional[Decimal]:
        """获取历史最高价"""
        if not self.prices:
            return None
        return Decimal(str(max(p["price"] for p in self.prices)))
