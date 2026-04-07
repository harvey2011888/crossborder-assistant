"""
京东API集成模块

实现京东开放平台API的调用，支持商品搜索、详情获取和价格监控

注意：京东API需要申请权限，本实现提供了：
1. 基于京东宙斯API/京东联盟API的标准实现
2. 基于第三方API服务的备选实现
3. 模拟数据模式（用于开发和测试）
"""

import hashlib
import json
import os
import re
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

import aiohttp

from .base import (
    APIAuthenticationError,
    APIRateLimitError,
    APITimeoutError,
    BaseEcommerceClient,
    EcommerceAPIError,
)
from .models import (
    Currency,
    PlatformType,
    PriceHistory,
    Product,
    ProductImage,
    ProductPrice,
    ProductSpec,
    ProductStatus,
    SearchResult,
    ShopInfo,
)


class JDClient(BaseEcommerceClient):
    """
    京东API客户端

    支持多种API接入方式：
    1. 京东宙斯开放平台API（需申请权限）
    2. 京东联盟API（需申请权限）
    3. 第三方API服务
    4. 模拟模式（开发和测试使用）
    """

    # API类型
    API_TYPE_OFFICIAL = "official"  # 官方宙斯API
    API_TYPE_UNION = "union"  # 京东联盟API
    API_TYPE_THIRDPARTY = "thirdparty"  # 第三方API
    API_TYPE_MOCK = "mock"  # 模拟模式

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        api_type: str = API_TYPE_MOCK,
        thirdparty_base_url: Optional[str] = None,
    ):
        """
        初始化京东客户端

        Args:
            api_key: API密钥（App Key）
            api_secret: API密钥（App Secret）
            api_type: API类型
            thirdparty_base_url: 第三方API基础URL
        """
        super().__init__(api_key, api_secret)
        self.api_type = api_type
        self.thirdparty_base_url = thirdparty_base_url

        # 从环境变量加载配置
        if not self.api_key:
            self.api_key = os.getenv("JD_APP_KEY", "")
        if not self.api_secret:
            self.api_secret = os.getenv("JD_APP_SECRET", "")
        if not self.thirdparty_base_url:
            self.thirdparty_base_url = os.getenv("JD_API_URL", "")

        # 价格监控缓存
        self._price_cache: Dict[str, PriceHistory] = {}
        self._cache_ttl = timedelta(hours=1)

    @property
    def platform(self) -> PlatformType:
        """返回平台类型"""
        return PlatformType.JD

    @property
    def base_url(self) -> str:
        """返回API基础URL"""
        if self.api_type == self.API_TYPE_OFFICIAL:
            return "https://api.jd.com/routerjson"
        elif self.api_type == self.API_TYPE_UNION:
            return "https://api.jd.com/routerjson"
        elif self.api_type == self.API_TYPE_THIRDPARTY:
            return self.thirdparty_base_url or "https://api.onebound.cn/jd"
        else:
            return ""

    def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建HTTP会话"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"Content-Type": "application/json"},
            )
        return self._session

    def _generate_sign(self, params: Dict[str, Any]) -> str:
        """
        生成京东API签名

        Args:
            params: 请求参数

        Returns:
            签名字符串
        """
        # 按参数名排序
        sorted_params = sorted(params.items())
        # 拼接字符串
        sign_str = self.api_secret + "".join(f"{k}{v}" for k, v in sorted_params if v is not None) + self.api_secret
        # MD5加密
        return hashlib.md5(sign_str.encode("utf-8")).hexdigest().upper()

    def _build_official_params(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        构建官方API请求参数

        Args:
            method: API方法名
            params: 业务参数

        Returns:
            完整请求参数
        """
        common_params = {
            "app_key": self.api_key,
            "method": method,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "format": "json",
            "v": "1.0",
            "sign_method": "md5",
        }

        if params:
            for key, value in params.items():
                if isinstance(value, (dict, list)):
                    common_params[key] = json.dumps(value, ensure_ascii=False)
                else:
                    common_params[key] = value

        # 生成签名
        common_params["sign"] = self._generate_sign(common_params)
        return common_params

    async def _make_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        http_method: str = "GET",
    ) -> Dict[str, Any]:
        """
        发送API请求

        Args:
            method: API方法名
            params: 请求参数
            http_method: HTTP方法

        Returns:
            API响应数据

        Raises:
            EcommerceAPIError: API调用失败
        """
        if self.api_type == self.API_TYPE_MOCK:
            return self._get_mock_response(method, params)

        session = self._get_session()

        try:
            if self.api_type in (self.API_TYPE_OFFICIAL, self.API_TYPE_UNION):
                request_params = self._build_official_params(method, params)
                url = self.base_url
            else:
                request_params = params or {}
                request_params["api_key"] = self.api_key
                url = f"{self.base_url}/{method}"

            if http_method.upper() == "GET":
                async with session.get(url, params=request_params) as response:
                    data = await response.json()
            else:
                async with session.post(url, json=request_params) as response:
                    data = await response.json()

            # 检查错误
            if self.api_type in (self.API_TYPE_OFFICIAL, self.API_TYPE_UNION):
                if data.get("error_response"):
                    error = data["error_response"]
                    error_code = error.get("code", "")
                    error_msg = error.get("zh_desc", error.get("en_desc", "Unknown error"))

                    if error_code in ("201", "202"):
                        raise APIAuthenticationError(f"认证失败: {error_msg}", error_code)
                    elif error_code == "203":
                        raise APIRateLimitError(f"请求过于频繁: {error_msg}", error_code)
                    else:
                        raise EcommerceAPIError(error_msg, error_code, data)

                return data
            else:
                # 第三方API错误处理
                if data.get("code") != 200 and data.get("error"):
                    raise EcommerceAPIError(data.get("error", "Unknown error"))
                return data

        except aiohttp.ClientError as e:
            raise EcommerceAPIError(f"网络请求失败: {str(e)}")
        except asyncio.TimeoutError:
            raise APITimeoutError("请求超时")
        except Exception as e:
            if isinstance(e, EcommerceAPIError):
                raise
            raise EcommerceAPIError(f"请求失败: {str(e)}")

    def _get_mock_response(self, method: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取模拟响应数据（用于开发和测试）

        Args:
            method: API方法名
            params: 请求参数

        Returns:
            模拟响应数据
        """
        if "search" in method.lower() or method == "item_search":
            query = params.get("q", "商品") if params else "商品"
            return {
                "items": {
                    "item": [
                        {
                            "num_iid": f"1000{i}234567",
                            "title": f"【京东自营】{query} 优质商品 {i+1}",
                            "pic_url": f"https://example.com/jd_image{i}.jpg",
                            "price": f"{149 + i * 20}.00",
                            "sales": f"{2000 + i * 1000}",
                            "seller_nick": "京东自营",
                            "item_loc": "北京",
                            "detail_url": f"https://item.jd.com/1000{i}234567.html",
                            "shop_type": "自营",
                        }
                        for i in range(5)
                    ],
                    "total_results": 100,
                }
            }
        elif "detail" in method.lower() or method == "item_get":
            item_id = params.get("num_iid", "10001234567") if params else "10001234567"
            return {
                "item": {
                    "num_iid": item_id,
                    "title": "【京东自营】优质商品示例 - 京东配送",
                    "desc": "京东自营商品，品质保证，极速配送。",
                    "pic_url": "https://example.com/jd_main.jpg",
                    "item_imgs": {
                        "item_img": [
                            {"url": "https://example.com/jd_img1.jpg"},
                            {"url": "https://example.com/jd_img2.jpg"},
                            {"url": "https://example.com/jd_img3.jpg"},
                        ]
                    },
                    "price": "199.00",
                    "orginal_price": "299.00",
                    "sales": "10000",
                    "seller": {
                        "nick": "京东自营",
                        "shop_name": "京东自营旗舰店",
                        "level": "京东好店",
                    },
                    "props_list": {
                        "1": "品牌:示例品牌",
                        "2": "型号:示例型号",
                    },
                    "skus": {
                        "sku": [
                            {
                                "sku_id": "1000123456801",
                                "price": "199.00",
                                "properties": "1",
                                "properties_name": "1:品牌:示例品牌",
                                "quantity": "500",
                            }
                        ]
                    },
                    "good_rate": "98%",
                    "comment_count": "5000+",
                }
            }
        elif "price" in method.lower():
            # 价格监控模拟数据
            item_id = params.get("skuIds", "10001234567") if params else "10001234567"
            return {
                "jingdong_ware_price_get_responce": {
                    "price_changes": [
                        {
                            "skuId": item_id,
                            "price": "189.00",
                            "original_price": "199.00",
                            "timestamp": datetime.now().isoformat(),
                        }
                    ]
                }
            }
        return {}

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
        搜索京东商品

        Args:
            query: 搜索关键词
            page: 页码
            page_size: 每页数量
            sort_by: 排序方式 (default/price_asc/price_desc/sales/new)
            min_price: 最低价格
            max_price: 最高价格
            **kwargs: 其他参数

        Returns:
            搜索结果
        """
        # 排序映射
        sort_map = {
            "default": "",
            "price_asc": "price_asc",
            "price_desc": "price_desc",
            "sales": "sale_desc",
            "new": "new_desc",
            "score": "score_desc",
        }

        params = {
            "q": query,
            "page": page,
            "page_size": min(page_size, 100),
            "sort": sort_map.get(sort_by, ""),
        }

        if min_price:
            params["start_price"] = min_price
        if max_price:
            params["end_price"] = max_price

        # API方法名映射
        method_map = {
            self.API_TYPE_OFFICIAL: "jd.union.open.goods.query",
            self.API_TYPE_UNION: "jd.union.open.goods.query",
            self.API_TYPE_THIRDPARTY: "item_search",
            self.API_TYPE_MOCK: "item_search",
        }

        try:
            data = await self._make_request(method_map[self.api_type], params)

            # 解析商品列表
            products = []
            items = []

            if self.api_type in (self.API_TYPE_OFFICIAL, self.API_TYPE_UNION):
                # 京东联盟API响应格式
                result = data.get("jd_union_open_goods_query_response", {}).get("data", [])
                if isinstance(result, list):
                    items = result
                elif isinstance(result, dict):
                    items = result.get("list", [])
            else:
                items = data.get("items", {}).get("item", [])

            for item in items:
                product = self._parse_product(item)
                if product:
                    products.append(product)

            # 获取总数
            total = len(products)
            if self.api_type in (self.API_TYPE_OFFICIAL, self.API_TYPE_UNION):
                total = data.get("jd_union_open_goods_query_response", {}).get("totalCount", len(products))
            else:
                total = data.get("items", {}).get("total_results", len(products))

            return SearchResult(
                products=products,
                total=total,
                page=page,
                page_size=page_size,
                has_more=total > page * page_size,
                query=query,
                platform=self.platform,
            )

        except EcommerceAPIError:
            raise
        except Exception as e:
            raise EcommerceAPIError(f"搜索商品失败: {str(e)}")

    async def get_product_detail(self, product_id: str, **kwargs: Any) -> Optional[Product]:
        """
        获取京东商品详情

        Args:
            product_id: 商品ID（skuId）
            **kwargs: 其他参数

        Returns:
            商品详情
        """
        params = {"skuIds": [product_id]}

        # API方法名映射
        method_map = {
            self.API_TYPE_OFFICIAL: "jd.ware.product.detail.search.list.get",
            self.API_TYPE_UNION: "jd.union.open.goods.promotiongoodsinfo.query",
            self.API_TYPE_THIRDPARTY: "item_get",
            self.API_TYPE_MOCK: "item_get",
        }

        try:
            data = await self._make_request(method_map[self.api_type], params)

            item = None
            if self.api_type in (self.API_TYPE_OFFICIAL, self.API_TYPE_UNION):
                items = data.get("jd_union_open_goods_promotiongoodsinfo_query_response", {}).get("data", [])
                if items:
                    item = items[0]
            else:
                item = data.get("item", {})

            if not item:
                return None

            return self._parse_product_detail(item)

        except EcommerceAPIError:
            raise
        except Exception as e:
            raise EcommerceAPIError(f"获取商品详情失败: {str(e)}")

    async def get_product_by_url(self, url: str, **kwargs: Any) -> Optional[Product]:
        """
        通过URL获取京东商品信息

        Args:
            url: 商品链接
            **kwargs: 其他参数

        Returns:
            商品详情
        """
        # 从URL中提取商品ID
        product_id = self._extract_item_id(url)
        if not product_id:
            raise EcommerceAPIError(f"无法从URL中提取商品ID: {url}")

        return await self.get_product_detail(product_id)

    def _extract_item_id(self, url: str) -> Optional[str]:
        """
        从京东商品URL中提取商品ID

        Args:
            url: 商品链接

        Returns:
            商品ID
        """
        patterns = [
            r"item\.jd\.com/(\d+)",
            r"item\.jd\.hk/(\d+)",
            r"/(\d+)\.html",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    def _parse_product(self, item: Dict[str, Any]) -> Optional[Product]:
        """
        解析商品基础信息

        Args:
            item: API返回的商品数据

        Returns:
            商品对象
        """
        try:
            # 提取商品ID
            product_id = str(item.get("skuId", item.get("num_iid", item.get("goods_id", ""))))

            # 提取价格
            price_str = str(item.get("unitPrice", item.get("price", item.get("wlUnitPrice", "0"))))
            price = Decimal(price_str)

            # 提取原价
            original_price_str = item.get("wlUnitPrice", item.get("unitPrice", price_str))
            original_price = Decimal(str(original_price_str)) if original_price_str else price

            # 提取销量
            sales_count = None
            if "inOrderCount30Days" in item:
                sales_count = int(item["inOrderCount30Days"])
            elif "sales" in item:
                sales_count = self._parse_sales_count(str(item["sales"]))

            # 店铺信息
            shop_name = item.get("shopName", item.get("seller_nick", "京东"))
            is_self = item.get("owner", "") == "g" or "自营" in shop_name

            # 构建商品对象
            product = Product(
                product_id=product_id,
                platform=self.platform,
                title=item.get("skuName", item.get("title", "")),
                product_url=item.get("materialUrl", item.get("detail_url", f"https://item.jd.com/{product_id}.html")),
                price=ProductPrice(
                    original_price=original_price,
                    current_price=price,
                    currency=Currency.CNY,
                    discount=item.get("couponInfo"),
                ),
                images=[ProductImage(url=item.get("imageUrl", item.get("pic_url", "")), is_main=True)],
                main_image=item.get("imageUrl", item.get("pic_url")),
                sales_count=sales_count,
                shop=ShopInfo(
                    shop_name=shop_name,
                    shop_level="京东自营" if is_self else "第三方",
                ),
                location=item.get("item_loc", "北京"),
                raw_data=item if os.getenv("DEBUG") else None,
            )

            return product

        except Exception as e:
            return None

    def _parse_product_detail(self, item: Dict[str, Any]) -> Optional[Product]:
        """
        解析商品详情

        Args:
            item: API返回的商品详情数据

        Returns:
            商品对象
        """
        try:
            # 基础信息
            product_id = str(item.get("skuId", item.get("num_iid", "")))
            title = item.get("skuName", item.get("title", ""))
            description = item.get("desc", "")

            # 价格信息
            price = Decimal(str(item.get("unitPrice", item.get("price", "0"))))
            original_price = Decimal(str(item.get("wlUnitPrice", price)))

            # 图片列表
            images = []
            main_image = item.get("imageUrl", item.get("pic_url", ""))

            item_imgs = item.get("item_imgs", {}).get("item_img", [])
            if not isinstance(item_imgs, list):
                item_imgs = [item_imgs]

            for idx, img in enumerate(item_imgs):
                img_url = img.get("url", "") if isinstance(img, dict) else img
                if img_url:
                    images.append(ProductImage(url=img_url, is_main=(idx == 0)))

            if not images and main_image:
                images.append(ProductImage(url=main_image, is_main=True))

            # 规格信息
            specs = []
            props_list = item.get("props_list", {})
            if isinstance(props_list, dict):
                for key, value in props_list.items():
                    if ":" in value:
                        parts = value.split(":", 1)
                        specs.append(ProductSpec(name=parts[0], value=parts[1]))

            # 店铺信息
            seller = item.get("seller", {})
            shop_name = seller.get("shop_name", seller.get("nick", item.get("shopName", "京东")))
            is_self = "自营" in shop_name or item.get("owner") == "g"

            shop = ShopInfo(
                shop_name=shop_name,
                shop_level="京东自营" if is_self else "第三方",
                shop_rating=float(seller.get("score", 0)) if seller.get("score") else None,
            )

            # 销量和评价
            sales_count = None
            if "inOrderCount30Days" in item:
                sales_count = int(item["inOrderCount30Days"])
            elif "sales" in item:
                sales_count = self._parse_sales_count(str(item["sales"]))

            rating = None
            if "goodRate" in item:
                try:
                    rating = float(item["goodRate"].replace("%", "")) / 20  # 转换为5分制
                except:
                    pass

            review_count = None
            if "commentCount" in item:
                try:
                    review_count = int(item["commentCount"].replace("+", "").replace(",", ""))
                except:
                    pass

            # 构建商品对象
            product = Product(
                product_id=product_id,
                platform=self.platform,
                title=title or "未知商品",
                product_url=f"https://item.jd.com/{product_id}.html",
                price=ProductPrice(
                    original_price=original_price,
                    current_price=price,
                    currency=Currency.CNY,
                ),
                images=images,
                main_image=main_image,
                description=description,
                specs=specs,
                shop=shop,
                sales_count=sales_count,
                rating=rating,
                review_count=review_count,
                location=item.get("item_loc", "北京"),
                raw_data=item if os.getenv("DEBUG") else None,
            )

            return product

        except Exception as e:
            return None

    async def get_price_history(self, product_id: str) -> Optional[PriceHistory]:
        """
        获取商品价格历史

        Args:
            product_id: 商品ID

        Returns:
            价格历史记录
        """
        # 检查缓存
        cache_key = f"{self.platform.value}_{product_id}"
        if cache_key in self._price_cache:
            history = self._price_cache[cache_key]
            # 检查缓存是否过期
            if history.prices:
                last_update = datetime.fromisoformat(history.prices[-1]["timestamp"])
                if datetime.now() - last_update < self._cache_ttl:
                    return history

        # 创建新的价格历史记录
        history = PriceHistory(
            product_id=product_id,
            platform=self.platform,
            prices=[],
        )

        try:
            # 获取当前价格
            product = await self.get_product_detail(product_id)
            if product:
                history.add_price(product.price)
                self._price_cache[cache_key] = history

            return history

        except Exception as e:
            # 如果获取失败，返回空的历史记录
            return history

    async def check_price_change(self, product_id: str) -> Optional[Dict[str, Any]]:
        """
        检查商品价格变化

        Args:
            product_id: 商品ID

        Returns:
            价格变化信息
        """
        history = await self.get_price_history(product_id)
        if not history or len(history.prices) < 2:
            return None

        current_price = Decimal(str(history.prices[-1]["price"]))
        previous_price = Decimal(str(history.prices[-2]["price"]))

        if current_price != previous_price:
            change_percent = ((current_price - previous_price) / previous_price) * 100
            return {
                "product_id": product_id,
                "previous_price": float(previous_price),
                "current_price": float(current_price),
                "change_amount": float(current_price - previous_price),
                "change_percent": float(change_percent),
                "is_discount": current_price < previous_price,
                "timestamp": history.prices[-1]["timestamp"],
            }

        return None

    async def monitor_prices(self, product_ids: List[str]) -> List[Dict[str, Any]]:
        """
        批量监控商品价格

        Args:
            product_ids: 商品ID列表

        Returns:
            价格变化列表
        """
        changes = []

        for product_id in product_ids:
            try:
                change = await self.check_price_change(product_id)
                if change:
                    changes.append(change)
            except Exception as e:
                # 继续监控其他商品
                continue

        return changes


# 导入asyncio用于类型检查
import asyncio
