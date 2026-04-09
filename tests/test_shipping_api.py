"""
运费测算API测试

测试运费测算API客户端的功能
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from bot.services.platform.shipping_api import ShippingAPIClient, ShippingAPIError
from bot.services.platform.logistics import (
    LogisticsService,
    ShippingRateRequest,
    logistics_service,
)


async def test_shipping_api_client():
    """测试运费API客户端"""
    print("=" * 50)
    print("测试运费API客户端")
    print("=" * 50)

    client = ShippingAPIClient()

    # 测试配置
    print(f"\n1. API配置检查:")
    print(f"   基础URL: {client.base_url}")
    print(f"   是否配置: {client.is_configured()}")

    if not client.is_configured():
        print("\n   ⚠️ 运费API未配置，跳过API调用测试")
        return

    # 测试运费计算
    print(f"\n2. 测试运费计算 (美国, 100g):")
    try:
        response = await client.calculate_postage(
            country="US",
            weight=100,
            length=10,
            width=10,
            height=10,
        )
        print(f"   ✅ 请求成功")
        print(f"   响应码: {response.get('code')}")
        print(f"   消息: {response.get('msg')}")

        data = response.get("data", {})
        lines = data.get("lines", [])
        print(f"   可用线路数: {len(lines)}")

        if lines:
            print(f"\n   线路示例:")
            for i, line in enumerate(lines[:3], 1):
                print(f"   {i}. {line.get('lineName')} - ¥{line.get('price')} - {line.get('timeRequired')}天")

    except ShippingAPIError as e:
        print(f"   ❌ API错误: {e}")
    except Exception as e:
        print(f"   ❌ 错误: {e}")

    # 测试快递类型查询
    print(f"\n3. 测试快递类型查询:")
    try:
        response = await client.get_express_types()
        print(f"   ✅ 请求成功")
        print(f"   响应码: {response.get('code')}")

        data = response.get("data", [])
        print(f"   快递类型数: {len(data)}")

        if data:
            print(f"\n   类型示例:")
            for item in data[:3]:
                print(f"   - {item.get('name')} ({item.get('code')})")

    except ShippingAPIError as e:
        print(f"   ❌ API错误: {e}")
    except Exception as e:
        print(f"   ❌ 错误: {e}")

    await client.close()


async def test_logistics_service():
    """测试物流服务"""
    print("\n" + "=" * 50)
    print("测试物流服务")
    print("=" * 50)

    service = LogisticsService()

    # 测试配置
    print(f"\n1. 服务配置检查:")
    print(f"   是否可用: {service.is_available()}")

    if not service.is_available():
        print("\n   ⚠️ 物流服务不可用，跳过服务测试")
        return

    # 测试运费估算
    print(f"\n2. 测试运费估算 (美国, 500g):")
    try:
        request = ShippingRateRequest(
            destination_country="US",
            weight_g=500,
            length_cm=15,
            width_cm=10,
            height_cm=8,
        )

        response = await service.estimate_shipping_rate(request)
        print(f"   ✅ 请求成功")
        print(f"   目的地: {response.destination_country}")
        print(f"   包裹重量: {response.package_weight_g}g")
        print(f"   包裹尺寸: {response.package_dimensions}")
        print(f"   线路数量: {len(response.lines)}")

        if response.lines:
            print(f"\n   线路详情:")
            available_lines = [line for line in response.lines if line.state == "available"]
            print(f"   - 可用线路: {len(available_lines)}")

            for i, line in enumerate(available_lines[:3], 1):
                label = service.format_line_label(line.label)
                tags = service.format_tags(line.tags)
                print(f"   {i}. {line.name} {label}")
                print(f"      价格: ¥{line.price} | 时效: {line.time_required}天")
                print(f"      标签: {tags}")

    except Exception as e:
        print(f"   ❌ 错误: {e}")

    # 测试格式化功能
    print(f"\n3. 测试格式化功能:")
    print(f"   计费类型1: {service.format_compute_type(1)}")
    print(f"   计费类型2: {service.format_compute_type(2)}")
    print(f"   标签格式化: {service.format_line_label([{'name': 'standard', 'type': 1}])}")


async def main():
    """主测试函数"""
    print("\n" + "=" * 50)
    print("运费测算API测试开始")
    print("=" * 50)

    try:
        await test_shipping_api_client()
        await test_logistics_service()
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 关闭客户端
        from bot.services.platform.shipping_api import shipping_api_client
        await shipping_api_client.close()

    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
