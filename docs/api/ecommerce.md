# 电商平台API文档

本文档描述跨境电商智能助手中的电商平台API集成。

## 概述

电商平台模块提供统一的接口来集成多个中国电商平台（淘宝、京东等），支持商品搜索、详情获取、价格监控等功能。

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                 Ecommerce Factory                           │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │    Taobao    │  │      JD      │  │   Future...  │      │
│  │   Service    │  │   Service    │  │   Service    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## 数据模型

### ProductInfo

```python
class ProductInfo(BaseModel):
    """商品信息数据模型"""
    # 基础信息
    title: str                      # 商品标题
    product_id: str                 # 商品ID
    product_url: str                # 商品链接
    platform: str                   # 所属平台

    # 价格信息
    price: float                    # 当前价格
    original_price: Optional[float] = None  # 原价
    currency: str = "CNY"          # 货币

    # 媒体信息
    image_url: Optional[str] = None       # 主图URL
    images: list[str] = []               # 图片列表

    # 店铺信息
    shop_name: Optional[str] = None      # 店铺名称
    shop_url: Optional[str] = None       # 店铺链接

    # 销售信息
    sales: Optional[str] = None          # 销量
    rating: Optional[str] = None         # 评分
    reviews_count: Optional[int] = None  # 评价数

    # 其他信息
    description: Optional[str] = None    # 商品描述
    category: Optional[str] = None       # 分类
    brand: Optional[str] = None          # 品牌
    specifications: dict = {}           # 规格参数

    def get_formatted_price(self, target_currency: Optional[str] = None) -> str
    """获取格式化价格"""
```

### ProductSearchResult

```python
class ProductSearchResult(BaseModel):
    """商品搜索结果"""
    products: list[ProductInfo]     # 商品列表
    total: int                      # 总数
    page: int                       # 当前页
    page_size: int                  # 每页数量
    query: str                      # 搜索关键词
    platform: Optional[str] = None  # 平台筛选
```

## 服务接口

### BaseEcommerceService

所有电商服务的基类。

```python
class BaseEcommerceService(ABC):
    """电商服务基类"""

    @abstractmethod
    async def search(
        self,
        query: str,
        page: int = 1,
        page_size: int = 10,
        **kwargs: Any
    ) -> ProductSearchResult:
        """搜索商品"""
        pass

    @abstractmethod
    async def get_product_detail(
        self,
        product_id: str,
        **kwargs: Any
    ) -> Optional[ProductInfo]:
        """获取商品详情"""
        pass

    @abstractmethod
    def get_platform_name(self) -> str:
        """获取平台名称"""
        pass
```

### TaobaoService

淘宝API服务封装。

```python
class TaobaoService(BaseEcommerceService):
    """淘宝服务"""

    def __init__(
        self,
        app_key: str,
        app_secret: str,
        api_url: Optional[str] = None,
    ) -> None

    async def search(
        self,
        query: str,
        page: int = 1,
        page_size: int = 10,
        sort: str = "default",      # default/price/sales
        price_range: Optional[tuple[float, float]] = None,
    ) -> ProductSearchResult

    async def get_product_detail(
        self,
        product_id: str,
    ) -> Optional[ProductInfo]

    async def get_product_description(
        self,
        product_id: str,
    ) -> Optional[str]

    def get_platform_name(self) -> str
    """返回'淘宝'"""
```

### JDService

京东API服务封装。

```python
class JDService(BaseEcommerceService):
    """京东服务"""

    def __init__(
        self,
        app_key: str,
        app_secret: str,
        api_url: Optional[str] = None,
    ) -> None

    async def search(
        self,
        query: str,
        page: int = 1,
        page_size: int = 10,
        sort: str = "default",
        price_range: Optional[tuple[float, float]] = None,
    ) -> ProductSearchResult

    async def get_product_detail(
        self,
        product_id: str,
    ) -> Optional[ProductInfo]

    def get_platform_name(self) -> str
    """返回'京东'"""
```

## 工厂类

### EcommerceFactory

```python
class EcommerceFactory:
    """电商服务工厂"""

    def get_service(
        self,
        platform: PlatformType,
    ) -> BaseEcommerceService
    """获取指定平台的服务实例"""

    def get_all_services(self) -> list[BaseEcommerceService]
    """获取所有平台的服务实例"""

    def search_all(
        self,
        query: str,
        page: int = 1,
        page_size: int = 10,
    ) -> dict[str, ProductSearchResult]
    """在所有平台搜索"""
```

### PlatformType 枚举

```python
class PlatformType(str, Enum):
    """平台类型枚举"""
    TAOBAO = "taobao"
    JD = "jd"
    TMALL = "tmall"
    PDD = "pdd"
```

## 使用示例

### 搜索商品

```python
from bot.services.ecommerce.factory import EcommerceFactory, PlatformType

factory = EcommerceFactory()

# 搜索淘宝商品
taobao = factory.get_service(PlatformType.TAOBAO)
result = await taobao.search("手机", page=1, page_size=10)

for product in result.products:
    print(f"{product.title}: {product.get_formatted_price()}")
```

### 获取商品详情

```python
# 获取淘宝商品详情
product = await taobao.get_product_detail("123456789")

if product:
    print(f"标题: {product.title}")
    print(f"价格: {product.get_formatted_price()}")
    print(f"店铺: {product.shop_name}")
    print(f"销量: {product.sales}")
```

### 多平台搜索

```python
# 在所有平台搜索
results = await factory.search_all("Nike跑鞋", page=1, page_size=5)

for platform, result in results.items():
    print(f"\n=== {platform} ===")
    for product in result.products:
        print(f"- {product.title}: {product.price}")
```

### 价格筛选

```python
# 按价格范围搜索
result = await taobao.search(
    "手机",
    page=1,
    page_size=10,
    price_range=(1000, 3000),  # 1000-3000元
    sort="price"               # 按价格排序
)
```

## 数据格式化

### ProductFormatter

```python
class ProductFormatter:
    """商品数据格式化器"""

    @staticmethod
    def format_price(
        price: float,
        from_currency: str,
        to_currency: str,
        exchange_rate: Optional[float] = None,
    ) -> str
    """格式化价格（含货币转换）"""

    @staticmethod
    def format_product_for_discord(
        product: ProductInfo,
        index: Optional[int] = None,
    ) -> dict[str, Any]
    """格式化为Discord Embed数据"""

    @staticmethod
    def format_product_comparison(
        products: list[ProductInfo],
    ) -> dict[str, Any]
    """格式化商品对比数据"""
```

### 使用示例

```python
from bot.services.ecommerce.formatter import ProductFormatter

# 价格转换
usd_price = ProductFormatter.format_price(
    price=1999.99,
    from_currency="CNY",
    to_currency="USD"
)
print(usd_price)  # "$280.00 USD"

# 格式化为Discord Embed
embed_data = ProductFormatter.format_product_for_discord(
    product,
    index=1
)
```

## 价格监控

### PriceMonitor

```python
class PriceMonitor:
    """价格监控器"""

    async def track_product(
        self,
        product: ProductInfo,
        user_id: str,
        target_price: Optional[float] = None,
    ) -> str
    """添加商品到价格监控"""

    async def check_price_changes(self) -> list[PriceChangeEvent]
    """检查价格变动"""

    async def get_tracked_products(
        self,
        user_id: str,
    ) -> list[TrackedProduct]
    """获取用户监控的商品列表"""

    async def remove_tracking(
        self,
        tracking_id: str,
    ) -> bool
    """移除价格监控"""
```

## 配置参数

### 环境变量

```env
# 淘宝API配置
TAOBAO_APP_KEY=your_taobao_app_key
TAOBAO_APP_SECRET=your_taobao_app_secret
TAOBAO_API_URL=https://api.onebound.cn/taobao

# 京东API配置
JD_APP_KEY=your_jd_app_key
JD_APP_SECRET=your_jd_app_secret
JD_API_URL=https://api.onebound.cn/jd
```

### 默认参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| page_size | 10 | 每页商品数量 |
| timeout | 30 | 请求超时时间（秒） |
| max_retries | 3 | 最大重试次数 |
| cache_ttl | 300 | 缓存时间（秒） |

## 错误处理

```python
from bot.services.ecommerce.base import EcommerceError

try:
    result = await taobao.search("手机")
except EcommerceError as e:
    print(f"电商API错误: {e}")
except Exception as e:
    print(f"未知错误: {e}")
```

## 最佳实践

1. **API限流**: 遵守各平台的API调用频率限制
2. **缓存策略**: 对搜索结果进行合理缓存，减少API调用
3. **错误重试**: 对网络错误实现指数退避重试
4. **数据验证**: 对API返回数据进行验证和清理
5. **图片处理**: 使用CDN或缩略图服务优化图片加载

## 扩展新平台

### 实现新的电商服务

```python
from bot.services.ecommerce.base import BaseEcommerceService
from bot.services.ecommerce.models import ProductInfo, ProductSearchResult

class NewPlatformService(BaseEcommerceService):
    """新平台服务"""

    def __init__(self, api_key: str, **kwargs):
        self.api_key = api_key
        self.base_url = "https://api.newplatform.com"

    async def search(
        self,
        query: str,
        page: int = 1,
        page_size: int = 10,
        **kwargs
    ) -> ProductSearchResult:
        # 实现搜索逻辑
        pass

    async def get_product_detail(
        self,
        product_id: str,
        **kwargs
    ) -> Optional[ProductInfo]:
        # 实现详情获取逻辑
        pass

    def get_platform_name(self) -> str:
        return "新平台"
```

### 注册到工厂

```python
from bot.services.ecommerce.factory import EcommerceFactory, PlatformType

factory = EcommerceFactory()
factory.register_service(PlatformType.NEW, NewPlatformService)
```
