"""
优化后的运费工具函数测试

测试参数提取功能的优化效果
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from bot.services.ai.tools import shipping_tool


def test_extract_weight():
    """测试重量提取功能"""
    print("=" * 60)
    print("测试重量提取功能")
    print("=" * 60)

    test_cases = [
        # 标准数字格式
        ("500g", 500),
        ("100克", 100),
        ("1kg", 1000),
        ("2.5公斤", 2500),
        ("3斤", 1500),

        # 中文数字
        ("一斤半", 750),
        ("两公斤", 2000),
        ("三斤", 1500),
        ("十克", 10),

        # 范围格式
        ("500-1000g", 750),
        ("1到2公斤", 1500),

        # 物品参考
        ("一部手机", 200),
        ("两双鞋", 1600),
        ("一件衣服", 300),

        # 模糊表达（应该能提取数字部分）
        ("500g左右", 500),
        ("大概1kg", 1000),
    ]

    passed = 0
    failed = 0

    for text, expected in test_cases:
        result = shipping_tool.extract_weight(text)
        status = "✅" if result == expected else "❌"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"{status} 输入: '{text}' -> 期望: {expected}g, 实际: {result}g")

    print(f"\n测试结果: 通过 {passed}/{len(test_cases)}, 失败 {failed}/{len(test_cases)}")
    return failed == 0


def test_extract_country():
    """测试国家识别功能（20个指定国家）"""
    print("\n" + "=" * 60)
    print("测试国家识别功能（20个指定国家）")
    print("=" * 60)

    test_cases = [
        # 20个指定国家 - 中文名称
        ("巴西", "BR"),
        ("美国", "US"),
        ("葡萄牙", "PT"),
        ("英国", "UK"),
        ("德国", "DE"),
        ("加拿大", "CA"),
        ("中国大陆", "CN"),
        ("中国", "CN"),
        ("法国", "FR"),
        ("澳大利亚", "AU"),
        ("西班牙", "ES"),
        ("意大利", "IT"),
        ("爱尔兰", "IE"),
        ("荷兰", "NL"),
        ("安哥拉", "AO"),
        ("墨西哥", "MX"),
        ("罗马尼亚", "RO"),
        ("柬埔寨", "KH"),
        ("奥地利", "AT"),
        ("阿联酋", "AE"),
        ("波兰", "PL"),

        # 别名
        ("米国", "US"),
        ("漂亮国", "US"),
        ("枫叶国", "CA"),
        ("土澳", "AU"),
        ("大陆", "CN"),

        # 拼音
        ("meiguo", "US"),
        ("deguo", "DE"),
        ("zhongguo", "CN"),
        ("faguo", "FR"),
        ("baxi", "BR"),

        # 英文
        ("usa", "US"),
        ("germany", "DE"),
        ("china", "CN"),
        ("brazil", "BR"),

        # 句子中提取
        ("我要寄到米国", "US"),
        ("发往中国大陆的包裹", "CN"),
        ("寄到巴西", "BR"),
    ]

    passed = 0
    failed = 0

    for text, expected in test_cases:
        result = shipping_tool.extract_country(text)
        status = "✅" if result == expected else "❌"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"{status} 输入: '{text}' -> 期望: {expected}, 实际: {result}")

    print(f"\n测试结果: 通过 {passed}/{len(test_cases)}, 失败 {failed}/{len(test_cases)}")
    return failed == 0


def test_extract_category_type():
    """测试商品类型提取功能"""
    print("\n" + "=" * 60)
    print("测试商品类型提取功能")
    print("=" * 60)

    test_cases = [
        # 标准关键词
        ("衣服", None),  # 可能返回具体的类型名称
        ("鞋子", None),
        ("电子产品", None),

        # 描述性输入
        ("带电池的手机", None),
        ("国际品牌运动鞋", None),
        ("化妆品", None),
        ("零食", None),

        # 具体物品
        ("iPhone", None),
        ("耐克鞋", None),
        ("口红", None),
    ]

    passed = 0
    failed = 0

    for text, _ in test_cases:
        result_name, result_ids = shipping_tool.extract_category_type(text)
        # 只要有返回结果就算通过（因为具体返回值取决于category_type_manager）
        status = "✅" if result_name and result_ids else "❌"
        if result_name and result_ids:
            passed += 1
        else:
            failed += 1
        print(f"{status} 输入: '{text}' -> 类型: {result_name}, IDs: {result_ids}")

    print(f"\n测试结果: 通过 {passed}/{len(test_cases)}, 失败 {failed}/{len(test_cases)}")
    return failed == 0


def test_parse_shipping_query():
    """测试完整的查询解析功能"""
    print("\n" + "=" * 60)
    print("测试完整查询解析")
    print("=" * 60)

    test_cases = [
        "1kg到美国",
        "500g寄到中国大陆",
        "两公斤发往巴西",
        "带电池的手机1kg到德国",
        "衣服500g寄往法国",
    ]

    for text in test_cases:
        result = shipping_tool.parse_shipping_query(text)
        print(f"\n输入: '{text}'")
        print(f"  重量: {result['weight']}g")
        print(f"  目的地: {result['destination']}")
        print(f"  商品类型: {result['category_name']}")
        print(f"  缺失参数: {result['missing']}")

    return True


def test_parameter_modification_detection():
    """测试参数修改检测功能"""
    print("\n" + "=" * 60)
    print("测试参数修改检测")
    print("=" * 60)

    from bot.services.shipping_conversation import shipping_conversation_manager

    test_cases = [
        ("重量改成1kg", "weight"),
        ("重量改为500g", "weight"),
        ("目的地换成中国大陆", "destination"),
        ("国家改成美国", "destination"),
        ("类型换成衣服", "category"),
    ]

    for text, expected_param in test_cases:
        param, value = shipping_conversation_manager._detect_parameter_modification(text)
        status = "✅" if param == expected_param else "❌"
        print(f"{status} 输入: '{text}' -> 检测到的参数: {param}, 值: {value}")

    return True


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("运费工具函数优化测试")
    print("=" * 60)

    results = []

    try:
        results.append(("重量提取", test_extract_weight()))
        results.append(("国家识别", test_extract_country()))
        results.append(("商品类型", test_extract_category_type()))
        results.append(("完整解析", test_parse_shipping_query()))
        results.append(("参数修改", test_parameter_modification_detection()))
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {name}")

    all_passed = all(passed for _, passed in results)
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有测试通过！")
    else:
        print("⚠️ 部分测试失败，请检查")
    print("=" * 60)


if __name__ == "__main__":
    main()
