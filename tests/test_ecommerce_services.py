"""
电商服务单元测试

测试淘宝、京东等电商平台API服务
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.services.ecommerce.models import ProductInfo, ProductSearchResult


@pytest.mark.unit
class TestProductModels:
    """商品数据模型测试"""

    def test_product_info_creation(self) -> None:
        """测试创建商品信息对象"""
        product = ProductInfo(
            title="测试商品",
            price=99.99,
            currency="CNY",
            platform="淘宝",
            product_url="https://example.com/product/123",
            product_id="123",
        )

        assert product.title == "测试商品"
        assert product.price == 99.99
        assert product.platform == "淘宝"

    def test_product_info_formatted_price(self) -> None:
        """测试格式化价格"""
        product = ProductInfo(
            title="测试商品",
            price=99.99,
            currency="CNY",
            platform="淘宝",
            product_url="https://example.com/product/123",
            product_id="123",
        )

        formatted = product.get_formatted_price()
        assert "99.99" in formatted
        assert "CNY" in formatted or "¥" in formatted

    def test_product_search_result(self) -> None:
        """测试商品搜索结果"""
        products = [
            ProductInfo(
                title="商品1",
                price=100.0,
                currency="CNY",
                platform="淘宝",
                product_url="https://example.com/1",
                product_id="1",
            ),
            ProductInfo(
                title="商品2",
                price=200.0,
                currency="CNY",
                platform="京东",
                product_url="https://example.com/2",
                product_id="2",
            ),
        ]

        result = ProductSearchResult(
            products=products,
            total=2,
            page=1,
            page_size=10,
            query="测试",
        )

        assert len(result.products) == 2
        assert result.total == 2
        assert result.query == "测试"


@pytest.mark.unit
@pytest.mark.asyncio
class TestTaobaoService:
    """淘宝服务测试"""

    async def test_search_products(self) -> None:
        """测试搜索商品"""
        from bot.services.ecommerce.taobao import TaobaoService

        mock_response = {
            "items": {
                "item": [
                    {
                        "title": "测试商品",
                        "price": "99.99",
                        "pic_url": "https://example.com/image.jpg",
                        "detail_url": "https://example.com/product/123",
                        "num_iid": "123",
                        "seller_nick": "测试店铺",
                    }
                ]
            }
        }

        with patch.object(TaobaoService, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            service = TaobaoService(app_key="test_key", app_secret="test_secret")
            result = await service.search("手机", page=1, page_size=10)

            assert result is not None
            mock_request.assert_called_once()

    async def test_get_product_detail(self) -> None:
        """测试获取商品详情"""
        from bot.services.ecommerce.taobao import TaobaoService

        mock_response = {
            "item": {
                "title": "测试商品详情",
                "price": "199.99",
                "pic_url": "https://example.com/detail.jpg",
                "num_iid": "456",
                "seller_nick": "测试店铺",
            }
        }

        with patch.object(TaobaoService, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            service = TaobaoService(app_key="test_key", app_secret="test_secret")
            product = await service.get_product_detail("456")

            assert product is not None
            mock_request.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
class TestJDService:
    """京东服务测试"""

    async def test_search_products(self) -> None:
        """测试搜索商品"""
        from bot.services.ecommerce.jd import JDService

        mock_response = {
            "data": [
                {
                    "skuName": "京东测试商品",
                    "price": "299.99",
                    "imageUrl": "https://example.com/jd_image.jpg",
                    "skuId": "789",
                }
            ]
        }

        with patch.object(JDService, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            service = JDService(app_key="test_key", app_secret="test_secret")
            result = await service.search("电脑", page=1, page_size=10)

            assert result is not None
            mock_request.assert_called_once()


@pytest.mark.unit
class TestEcommerceFormatter:
    """电商数据格式化测试"""

    def test_format_price_cny_to_usd(self) -> None:
        """测试人民币转美元"""
        from bot.services.ecommerce.formatter import format_price

        result = format_price(100.0, "CNY", "USD")
        assert result is not None
        assert "USD" in result or "$" in result

    def test_format_product_for_discord(self) -> None:
        """测试格式化商品为Discord展示"""
        from bot.services.ecommerce.formatter import format_product_for_discord

        product = ProductInfo(
            title="测试商品",
            price=99.99,
            currency="CNY",
            platform="淘宝",
            product_url="https://example.com/product/123",
            product_id="123",
            shop_name="测试店铺",
            sales="1000+",
        )

        embed_data = format_product_for_discord(product, index=1)

        assert embed_data is not None
        assert "title" in embed_data or "description" in embed_data


@pytest.mark.unit
class TestEcommerceFactory:
    """电商服务工厂测试"""

    def test_factory_get_service(self) -> None:
        """测试工厂获取服务"""
        from bot.services.ecommerce.factory import EcommerceFactory, PlatformType

        factory = EcommerceFactory()

        # 测试获取淘宝服务
        taobao_service = factory.get_service(PlatformType.TAOBAO)
        assert taobao_service is not None

        # 测试获取京东服务
        jd_service = factory.get_service(PlatformType.JD)
        assert jd_service is not None

    def test_factory_get_all_services(self) -> None:
        """测试获取所有服务"""
        from bot.services.ecommerce.factory import EcommerceFactory

        factory = EcommerceFactory()
        services = factory.get_all_services()

        assert len(services) >= 2
