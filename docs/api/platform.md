# 自建平台API文档

本文档描述跨境电商智能助手与自建跨境电商平台的API集成。

## 概述

自建平台API模块提供与自建跨境电商网站（订单管理、物流服务）的接口封装。当前为预留框架，待平台API接口文档提供后实现具体逻辑。

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    Platform Client                          │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐                        │
│  │    Order     │  │   Logistics  │                        │
│  │   Service    │  │   Service    │                        │
│  └──────────────┘  └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Platform API    │
                    │ (自建电商平台)   │
                    └──────────────────┘
```

## 客户端基类

### PlatformClient

```python
class PlatformClient:
    """自建平台API客户端"""

    def __init__(
        self,
        base_url: Optional[str] = None,    # API基础URL
        api_key: Optional[str] = None,     # API密钥
        timeout: int = 30,                 # 超时时间（秒）
    ) -> None

    # HTTP方法
    async def get(endpoint, params=None, headers=None) -> dict
    async def post(endpoint, data=None, params=None, headers=None) -> dict
    async def put(endpoint, data=None, params=None, headers=None) -> dict
    async def delete(endpoint, params=None, headers=None) -> dict

    # 工具方法
    async def health_check() -> dict      # 健康检查
    def is_configured() -> bool           # 检查是否已配置
    async def close() -> None             # 关闭连接
```

### 异常类

```python
class PlatformAPIError(Exception):
    """平台API错误基类"""
    status_code: Optional[int]
    response_data: Optional[dict]

class PlatformAuthError(PlatformAPIError):
    """认证错误（401/403）"""

class PlatformRequestError(PlatformAPIError):
    """请求错误（400/404）"""
```

## 订单服务

### OrderService

```python
class OrderService:
    """订单管理服务"""

    def __init__(self, client: Optional[PlatformClient] = None)

    # 订单操作
    async def create_order(request: OrderCreateRequest) -> OrderCreateResponse
    async def get_order_list(request: OrderListRequest) -> OrderListResponse
    async def get_order_status(order_id: str, user_id: str) -> OrderStatusResponse
    async def get_order_detail(order_id: str, user_id: str) -> OrderInfo
    async def cancel_order(request: OrderCancelRequest) -> OrderCancelResponse

    # 状态检查
    def is_available() -> bool
```

### 数据模型

#### OrderStatus 枚举

```python
class OrderStatus(str, Enum):
    PENDING = "pending"           # 待支付
    PAID = "paid"                 # 已支付
    CONFIRMED = "confirmed"       # 已确认
    PURCHASING = "purchasing"     # 采购中
    PURCHASED = "purchased"       # 已采购
    WAREHOUSE = "warehouse"       # 已入库
    SHIPPING = "shipping"         # 运输中
    CUSTOMS = "customs"           # 清关中
    DELIVERED = "delivered"       # 已送达
    COMPLETED = "completed"       # 已完成
    CANCELLED = "cancelled"       # 已取消
    REFUNDED = "refunded"         # 已退款
```

#### OrderItem

```python
class OrderItem(BaseModel):
    """订单商品项"""
    product_name: str             # 商品名称
    product_url: str              # 商品链接
    platform: str                 # 电商平台
    price_cny: float              # 单价（人民币）
    quantity: int                 # 数量
    specifications: Optional[str] = None  # 规格
    image_url: Optional[str] = None       # 图片URL
```

#### ShippingAddress

```python
class ShippingAddress(BaseModel):
    """收货地址"""
    recipient_name: str           # 收件人姓名
    phone: str                    # 联系电话
    country: str                  # 国家
    province: Optional[str] = None        # 省/州
    city: str                     # 城市
    district: Optional[str] = None        # 区/县
    street_address: str           # 街道地址
    postal_code: str              # 邮政编码
```

#### OrderCreateRequest / OrderCreateResponse

```python
class OrderCreateRequest(BaseModel):
    """创建订单请求"""
    user_id: str                  # 用户ID
    items: list[OrderItem]        # 商品列表
    shipping_address: ShippingAddress     # 收货地址
    notes: Optional[str] = None           # 备注
    currency: str = "USD"         # 结算货币

class OrderCreateResponse(BaseModel):
    """创建订单响应"""
    order_id: str                 # 订单号
    status: OrderStatus           # 订单状态
    total_amount_cny: float       # 商品总金额（人民币）
    service_fee: float            # 服务费
    shipping_fee: Optional[float] = None  # 运费
    total_amount: float           # 订单总金额
    currency: str                 # 结算货币
    created_at: datetime          # 创建时间
    payment_url: Optional[str] = None     # 支付链接
```

#### OrderInfo

```python
class OrderInfo(BaseModel):
    """订单信息"""
    order_id: str                 # 订单号
    user_id: str                  # 用户ID
    status: OrderStatus           # 状态
    items: list[OrderItem]        # 商品列表
    shipping_address: ShippingAddress     # 收货地址
    total_amount_cny: float       # 商品总金额
    service_fee: float            # 服务费
    shipping_fee: Optional[float] = None  # 运费
    total_amount: float           # 订单总金额
    currency: str                 # 货币
    tracking_number: Optional[str] = None # 物流单号
    carrier: Optional[str] = None         # 物流公司
    notes: Optional[str] = None           # 备注
    created_at: datetime          # 创建时间
    updated_at: datetime          # 更新时间
    paid_at: Optional[datetime] = None    # 支付时间
    shipped_at: Optional[datetime] = None # 发货时间
    delivered_at: Optional[datetime] = None   # 送达时间
```

### 使用示例

```python
from bot.services.platform.orders import (
    OrderService, OrderCreateRequest, OrderItem, ShippingAddress
)

# 创建订单服务
order_service = OrderService()

# 检查服务是否可用
if not order_service.is_available():
    print("订单服务未配置")
    return

# 构建订单请求
item = OrderItem(
    product_name="iPhone 15 Pro",
    product_url="https://item.taobao.com/item.htm?id=123",
    platform="淘宝",
    price_cny=7999.0,
    quantity=1,
    specifications="256GB 黑色"
)

address = ShippingAddress(
    recipient_name="张三",
    phone="13800138000",
    country="美国",
    province="加利福尼亚",
    city="洛杉矶",
    street_address="123 Main St, Apt 4B",
    postal_code="90001"
)

request = OrderCreateRequest(
    user_id="123456789",
    items=[item],
    shipping_address=address,
    notes="请包装严实",
    currency="USD"
)

# 创建订单（当前会抛出NotImplementedError）
try:
    response = await order_service.create_order(request)
    print(f"订单创建成功: {response.order_id}")
except NotImplementedError:
    print("订单功能待平台API接口文档提供后实现")
```

## 物流服务

### LogisticsService

```python
class LogisticsService:
    """物流服务"""

    def __init__(self, client: Optional[PlatformClient] = None)

    # 运费和时效
    async def estimate_shipping_rate(request: ShippingRateRequest) -> ShippingRateResponse
    async def estimate_delivery_time(request: DeliveryTimeEstimateRequest) -> DeliveryTimeResponse

    # 包裹追踪
    async def track_package(request: PackageTrackingRequest) -> PackageTrackingResponse

    # 辅助信息
    async def get_supported_countries() -> list[dict]
    async def get_supported_carriers() -> list[dict]
    async def calculate_vat_and_duties(
        destination_country: str,
        package_value: float,
        category: Optional[str] = None,
    ) -> dict

    # 工具方法
    def format_tracking_status(status: TrackingStatus) -> str
    def format_shipping_method(method: ShippingMethod) -> str
    def is_available() -> bool
```

### 数据模型

#### ShippingMethod 枚举

```python
class ShippingMethod(str, Enum):
    STANDARD = "standard"         # 标准快递
    EXPRESS = "express"           # 特快专递
    ECONOMY = "economy"           # 经济快递
    SEA = "sea"                   # 海运
    AIR = "air"                   # 空运
    RAIL = "rail"                 # 铁路运输
```

#### TrackingStatus 枚举

```python
class TrackingStatus(str, Enum):
    PENDING = "pending"           # 待发货
    PICKED_UP = "picked_up"       # 已揽收
    IN_TRANSIT = "in_transit"     # 运输中
    ARRIVED_AT_FACILITY = "arrived_at_facility"   # 到达处理中心
    CUSTOMS_CLEARANCE = "customs_clearance"       # 清关中
    OUT_FOR_DELIVERY = "out_for_delivery"         # 派送中
    DELIVERED = "delivered"       # 已送达
    EXCEPTION = "exception"       # 异常
    RETURNED = "returned"         # 已退回
```

#### ShippingRateRequest / ShippingRateResponse

```python
class ShippingRateRequest(BaseModel):
    """运费估算请求"""
    destination_country: str              # 目的地国家
    destination_postal_code: Optional[str] = None  # 邮政编码
    weight_kg: float                      # 重量（千克）
    length_cm: Optional[float] = None     # 长度
    width_cm: Optional[float] = None      # 宽度
    height_cm: Optional[float] = None     # 高度
    package_value: Optional[float] = None # 包裹价值
    currency: str = "USD"                 # 货币
    shipping_methods: Optional[list[ShippingMethod]] = None  # 指定物流方式

class ShippingRate(BaseModel):
    """运费选项"""
    method: ShippingMethod                # 物流方式
    method_name: str                      # 方式名称
    carrier: str                          # 承运商
    estimated_cost: float                 # 预估运费
    currency: str                         # 货币
    estimated_days_min: int               # 预计最小天数
    estimated_days_max: int               # 预计最大天数
    tracking_available: bool              # 是否支持追踪
    insurance_included: bool              # 是否含保险

class ShippingRateResponse(BaseModel):
    """运费估算响应"""
    destination_country: str
    package_weight_kg: float
    rates: list[ShippingRate]
    valid_until: Optional[datetime] = None
```

#### PackageTrackingRequest / PackageTrackingResponse

```python
class PackageTrackingRequest(BaseModel):
    """包裹追踪请求"""
    tracking_number: str                  # 物流单号
    carrier: Optional[str] = None         # 承运商

class TrackingEvent(BaseModel):
    """追踪事件"""
    timestamp: datetime                   # 事件时间
    status: TrackingStatus                # 状态
    status_text: str                      # 状态描述
    location: Optional[str] = None        # 地点
    description: str                      # 详细描述

class PackageTrackingResponse(BaseModel):
    """包裹追踪响应"""
    tracking_number: str                  # 物流单号
    carrier: str                          # 承运商
    carrier_url: Optional[str] = None     # 承运商官网
    status: TrackingStatus                # 当前状态
    status_text: str                      # 状态描述
    origin_country: Optional[str] = None  # 发货国家
    destination_country: Optional[str] = None     # 目的地
    shipped_at: Optional[datetime] = None         # 发货时间
    estimated_delivery: Optional[datetime] = None # 预计送达
    delivered_at: Optional[datetime] = None       # 实际送达
    events: list[TrackingEvent]           # 追踪事件列表
    last_updated: datetime                # 最后更新时间
```

### 使用示例

```python
from bot.services.platform.logistics import (
    LogisticsService, ShippingRateRequest, PackageTrackingRequest
)

# 创建物流服务
logistics_service = LogisticsService()

# 检查服务是否可用
if not logistics_service.is_available():
    print("物流服务未配置")
    return

# 估算运费
rate_request = ShippingRateRequest(
    destination_country="美国",
    weight_kg=2.5,
    length_cm=30,
    width_cm=20,
    height_cm=15,
    package_value=100.0,
    currency="USD"
)

try:
    rate_response = await logistics_service.estimate_shipping_rate(rate_request)
    for rate in rate_response.rates:
        print(f"{rate.method_name}: {rate.estimated_cost} {rate.currency}")
        print(f"  预计时效: {rate.estimated_days_min}-{rate.estimated_days_max}天")
except NotImplementedError:
    print("运费估算功能待平台API接口文档提供后实现")

# 追踪包裹
track_request = PackageTrackingRequest(
    tracking_number="1Z999AA10123456784",
    carrier="UPS"
)

try:
    track_response = await logistics_service.track_package(track_request)
    print(f"当前状态: {track_response.status_text}")
    for event in track_response.events[:3]:
        print(f"  {event.timestamp}: {event.description}")
except NotImplementedError:
    print("包裹追踪功能待平台API接口文档提供后实现")
```

## 预期API端点

### 订单API

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | /api/v1/orders | 创建订单 |
| GET | /api/v1/orders | 查询订单列表 |
| GET | /api/v1/orders/{order_id} | 获取订单详情 |
| GET | /api/v1/orders/{order_id}/status | 查询订单状态 |
| POST | /api/v1/orders/{order_id}/cancel | 取消订单 |

### 物流API

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | /api/v1/logistics/rates | 估算运费 |
| GET | /api/v1/logistics/tracking/{tracking_number} | 追踪包裹 |
| GET | /api/v1/logistics/delivery-time | 查询时效 |
| GET | /api/v1/logistics/countries | 支持国家列表 |
| GET | /api/v1/logistics/carriers | 承运商列表 |
| POST | /api/v1/logistics/taxes | 计算税费 |

## 认证方式

### API Key认证

```python
# 请求头
headers = {
    "X-API-Key": "your_api_key",
    "Authorization": "Bearer your_api_key"
}
```

### 环境变量配置

```env
# 平台API配置
PLATFORM_API_URL=https://your-platform.com/api
PLATFORM_API_KEY=your_platform_api_key
```

## 待办事项

- [ ] 提供自建平台订单管理API接口文档
- [ ] 提供自建平台物流服务API接口文档
- [ ] 确认平台API认证方式
- [ ] 确认平台API基础URL和环境配置
- [ ] 实现具体API调用逻辑
- [ ] 添加Webhook支持（订单状态变更通知）

## 扩展开发

当平台API文档提供后，按以下步骤实现：

1. **更新数据模型**: 根据实际API响应调整Pydantic模型
2. **实现API调用**: 在OrderService和LogisticsService中实现具体方法
3. **添加错误处理**: 处理各种API错误情况
4. **编写测试**: 添加单元测试和集成测试
5. **更新文档**: 更新API文档和使用说明
