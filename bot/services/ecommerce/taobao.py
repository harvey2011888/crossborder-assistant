"""
淘宝API集成模块

实现淘宝开放平台API的调用，支持商品搜索和详情获取

注意：由于淘宝开放平台API需要申请权限，本实现提供了：
1. 基于淘宝客API的标准实现
2. 基于第三方API服务的备选实现（如万邦、折淘客等）
3. 模拟数据模式（用于开发和测试）
"""

import hashlib
import json
import os
import re
import time
import urllib.parse
from decimal import Decimal
from typing import Any, Dict, List, Optional

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
    Product,
    ProductImage,
    ProductPrice,
    ProductSpec,
    ProductStatus,
    SearchResult,
    ShopInfo,
)


class TaobaoClient(BaseEcommerceClient):
    """
    淘宝API客户端

    支持多种API接入方式：
    1. 淘宝开放平台官方API（需申请权限）
    2. 第三方API服务（万邦、折淘客等）
    3. 模拟模式（开发和测试使用）
"""

    # API类型
    API_TYPE_OFFICIAL = "official"  # 官方API
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
        初始化淘宝客户端

        Args:
            api_key: API密钥（App Key）
            api_secret: API密钥（App Secret）
            api_type: API类型，可选 official/thirdparty/mock
            thirdparty_base_url: 第三方API基础URL
        """
        super().__init__(api_key, api_secret)
        self.api_type = api_type
        self.thirdparty_base_url = thirdparty_base_url

        # 从环境变量加载配置
        if not self.api_key:
            self.api_key = os.getenv("TAOBAO_APP_KEY", "")
        if not self.api_secret:
            self.api_secret = os.getenv("TAOBAO_APP_SECRET", "")
        if not self.thirdparty_base_url:
            self.thirdparty_base_url = os.getenv("TAOBAO_API_URL", "")

    @property
    def platform(self) -> PlatformType:
        """返回平台类型"""
        return PlatformType.TAOBAO

    @property
    def base_url(self) -> str:
        """返回API基础URL"""
        if self.api_type == self.API_TYPE_OFFICIAL:
            return "https://eco.taobao.com/router/rest"
        elif self.api_type == self.API_TYPE_THIRDPARTY:
            return self.thirdparty_base_url or "https://api.onebound.cn/taobao"
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
        生成淘宝API签名

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
            "v": "2.0",
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
            if self.api_type == self.API_TYPE_OFFICIAL:
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
            if self.api_type == self.API_TYPE_OFFICIAL:
                if "error_response" in data:
                    error = data["error_response"]
                    error_code = error.get("code", "")
                    error_msg = error.get("msg", "Unknown error")

                    if error_code in ("7", "27"):
                        raise APIAuthenticationError(f"认证失败: {error_msg}", error_code)
                    elif error_code == "29":
                        raise APIRateLimitError(f"请求过于频繁: {error_msg}", error_code)
                    else:
                        raise EcommerceAPIError(error_msg, error_code, data)

                # 提取业务数据
                return data.get(f"{method}_response", data)
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
                            "num_iid": f"{i}23456789{i}",
                            "title": f"【{query}】优质商品示例 {i+1} - 淘宝热销款",
                            "pic_url": f"https://example.com/image{i}.jpg",
                            "price": f"{99 + i * 10}.00",
                            "sales": f"{1000 + i * 500}+",
                            "seller_nick": f"示例店铺{i+1}",
                            "item_loc": "浙江杭州",
                            "detail_url": f"https://item.taobao.com/item.htm?id={i}23456789{i}",
                        }
                        for i in range(5)
                    ],
                    "total_results": 100,
                }
            }
        elif "detail" in method.lower() or method == "item_get":
            item_id = params.get("num_iid", "123456789") if params else "123456789"
            return {
                "item": {
                    "num_iid": item_id,
                    "title": "【淘宝热销】优质商品示例 - 详细描述",
                    "desc": "这是商品的详细描述，包含各种特性和规格信息。",
                    "pic_url": "https://example.com/main.jpg",
                    "item_imgs": {
                        "item_img": [
                            {"url": "https://example.com/img1.jpg"},
                            {"url": "https://example.com/img2.jpg"},
                        ]
                    },
                    "price": "129.00",
                    "orginal_price": "199.00",
                    "sales": "5000+",
                    "seller": {
                        "nick": "示例旗舰店",
                        "shop_name": "示例旗舰店",
                        "level": "5",
                    },
                    "props_list": {
                        "1627207:28320": "颜色分类:黑色",
                        "1627207:28321": "颜色分类:白色",
                    },
                    "skus": {
                        "sku": [
                            {
                                "sku_id": "12345678901",
                                "price": "129.00",
                                "properties": "1627207:28320",
                                "properties_name": "1627207:28320:颜色分类:黑色",
                                "quantity": "100",
                            }
                        ]
                    },
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
        搜索淘宝商品

        Args:
            query: 搜索关键词
            page: 页码
            page_size: 每页数量
            sort_by: 排序方式 (default/price_asc/price_desc/sales)
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
        }

        params = {
            "q": query,
            "page": page,
            "page_size": min(page_size, 100),  # 淘宝限制最大100
            "sort": sort_map.get(sort_by, ""),
        }

        if min_price:
            params["start_price"] = min_price
        if max_price:
            params["end_price"] = max_price

        # API方法名映射
        method_map = {
            self.API_TYPE_OFFICIAL: "taobao.tbk.item.get",
            self.API_TYPE_THIRDPARTY: "item_search",
            self.API_TYPE_MOCK: "item_search",
        }

        try:
            data = await self._make_request(method_map[self.api_type], params)

            # 解析商品列表
            products = []
            items = []

            if self.api_type == self.API_TYPE_OFFICIAL:
                items = data.get("results", {}).get("n_tbk_item", [])
            elif self.api_type == self.API_TYPE_THIRDPARTY:
                items = data.get("items", {}).get("item", [])
            else:
                items = data.get("items", {}).get("item", [])

            for item in items:
                product = self._parse_product(item)
                if product:
                    products.append(product)

            # 获取总数
            total = 0
            if self.api_type == self.API_TYPE_OFFICIAL:
                total = data.get("total_results", len(products))
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
        获取淘宝商品详情

        Args:
            product_id: 商品ID（num_iid）
            **kwargs: 其他参数

        Returns:
            商品详情
        """
        params = {"num_iid": product_id}

        # API方法名映射
        method_map = {
            self.API_TYPE_OFFICIAL: "taobao.item.get",
            self.API_TYPE_THIRDPARTY: "item_get",
            self.API_TYPE_MOCK: "item_get",
        }

        try:
            data = await self._make_request(method_map[self.api_type], params)

            if self.api_type == self.API_TYPE_OFFICIAL:
                item = data.get("item", {})
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
        通过URL获取淘宝商品信息

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
        从淘宝商品URL中提取商品ID

        Args:
            url: 商品链接

        Returns:
            商品ID
        """
        patterns = [
            r"[?&]id=(\d+)",
            r"item/(\d+)",
            r"item\.htm\?.*?id=(\d+)",
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
            # 提取价格
            price_str = str(item.get("price", item.get("zk_final_price", "0")))
            price = Decimal(price_str)

            # 提取原价
            original_price_str = item.get("reserve_price", item.get("price", "0"))
            original_price = Decimal(str(original_price_str)) if original_price_str else price

            # 提取销量
            sales_count = self._parse_sales_count(item.get("sales", item.get("volume", "")))

            # 构建商品对象
            product = Product(
                product_id=str(item.get("num_iid", item.get("item_id", ""))),
                platform=self.platform,
                title=item.get("title", ""),
                product_url=item.get("detail_url", item.get("item_url", "")),
                short_url=item.get("click_url"),
                price=ProductPrice(
                    original_price=original_price,
                    current_price=price,
                    currency=Currency.CNY,
                    discount=None,
                ),
                images=[ProductImage(url=item.get("pic_url", ""), is_main=True)],
                main_image=item.get("pic_url"),
                sales_count=sales_count,
                shop=ShopInfo(
                    shop_name=item.get("seller_nick", item.get("nick", "")),
                ),
                location=item.get("item_loc"),
                raw_data=item if os.getenv("DEBUG") else None,
            )

            return product

        except Exception as e:
            # 记录错误但继续处理其他商品
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
            product_id = str(item.get("num_iid", ""))
            title = self._clean_html(item.get("title", ""))
            description = self._clean_html(item.get("desc", ""))

            # 价格信息
            price = Decimal(str(item.get("price", "0")))
            original_price = Decimal(str(item.get("orginal_price", item.get("price", "0"))))

            # 图片列表
            images = []
            main_image = item.get("pic_url", "")

            item_imgs = item.get("item_imgs", {}).get("item_img", [])
            if not isinstance(item_imgs, list):
                item_imgs = [item_imgs]

            for idx, img in enumerate(item_imgs):
                img_url = img.get("url", "")
                if img_url:
                    images.append(ProductImage(url=img_url, is_main=(idx == 0)))

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
            shop = ShopInfo(
                shop_name=seller.get("shop_name", seller.get("nick", "")),
                shop_rating=float(seller.get("score", 0)) if seller.get("score") else None,
                shop_level=seller.get("level"),
            )

            # 销量
            sales_count = self._parse_sales_count(item.get("sales", ""))

            # 构建商品对象
            product = Product(
                product_id=product_id,
                platform=self.platform,
                title=title or "未知商品",
                product_url=f"https://item.taobao.com/item.htm?id={product_id}",
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
                location=item.get("item_loc"),
                raw_data=item if os.getenv("DEBUG") else None,
            )

            return product

        except Exception as e:
            return None

    async def convert_tkl(self, tkl: str) -> Optional[str]:
        """
        解析淘口令获取商品链接

        Args:
            tkl: 淘口令（如"￥ABC123￥"）

        Returns:
            商品链接
        """
        # 淘口令解析需要特殊API，这里提供接口占位
        # 实际实现需要调用淘宝的淘口令解析API
        raise NotImplementedError("淘口令解析功能需要额外的API权限")


# 导入asyncio用于类型检查
import asyncio
