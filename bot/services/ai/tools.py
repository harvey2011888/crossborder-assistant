"""
AI工具函数模块

提供AI对话中可以调用的工具函数，如运费查询等
"""

import logging
import re
from typing import Any, Optional

from bot.services.platform.logistics import (
    LogisticsService,
    ShippingRateRequest,
    logistics_service,
)
from bot.services.platform.shipping_api import ShippingAPIError
from bot.services.platform.category_types import category_type_manager

logger = logging.getLogger(__name__)

# 国家名称到代码的映射
COUNTRY_NAME_TO_CODE = {
    # 中文名称
    "巴西": "BR",
    "美国": "US",
    "加拿大": "CA",
    "英国": "UK",
    "德国": "DE",
    "法国": "FR",
    "澳大利亚": "AU",
    "澳洲": "AU",
    "日本": "JP",
    "韩国": "KR",
    "新加坡": "SG",
    "马来西亚": "MY",
    "新西兰": "NZ",
    "意大利": "IT",
    "西班牙": "ES",
    "荷兰": "NL",
    "比利时": "BE",
    "奥地利": "AT",
    "瑞士": "CH",
    "瑞典": "SE",
    "挪威": "NO",
    "丹麦": "DK",
    "芬兰": "FI",
    "爱尔兰": "IE",
    "葡萄牙": "PT",
    "希腊": "GR",
    "波兰": "PL",
    "捷克": "CZ",
    "匈牙利": "HU",
    "罗马尼亚": "RO",
    "保加利亚": "BG",
    
    # 英文名称
    "brazil": "BR",
    "usa": "US",
    "united states": "US",
    "america": "US",
    "canada": "CA",
    "uk": "UK",
    "united kingdom": "UK",
    "britain": "UK",
    "england": "UK",
    "germany": "DE",
    "france": "FR",
    "australia": "AU",
    "japan": "JP",
    "korea": "KR",
    "south korea": "KR",
    "singapore": "SG",
    "malaysia": "MY",
    "new zealand": "NZ",
    "italy": "IT",
    "spain": "ES",
    "netherlands": "NL",
    "belgium": "BE",
    "austria": "AT",
    "switzerland": "CH",
    "sweden": "SE",
    "norway": "NO",
    "denmark": "DK",
    "finland": "FI",
    "ireland": "IE",
    "portugal": "PT",
    "greece": "GR",
    "poland": "PL",
    "czech": "CZ",
    "czech republic": "CZ",
    "hungary": "HU",
    "romania": "RO",
    "bulgaria": "BG",
}

# 商品类型关键词映射到类型代码
CATEGORY_KEYWORDS = {
    "服饰": "clothing",
    "衣服": "clothing",
    "服装": "clothing",
    "鞋子": "shoes",
    "鞋": "shoes",
    "箱包": "bags",
    "包": "bags",
    "电子产品": "electronics",
    "电子": "electronics",
    "带电": "electronics",
    "化妆品": "cosmetics",
    "化妆": "cosmetics",
    "食品": "food",
    "食物": "food",
}

# 子类型关键词映射
SUBTYPE_KEYWORDS = {
    "普货": "general",
    "普通": "general",
    "一般": "general",
    "国际品牌": "brand",
    "品牌": "brand",
    "运动品牌": "sports",
    "运动": "sports",
    "含电": "battery",
    "带电": "battery",
    "电池": "battery",
    "液体": "liquid",
    "粉末": "liquid",
    "零食": "snacks",
    "保健品": "health",
}


class ShippingTool:
    """
    运费查询工具

    用于AI对话中处理运费查询请求
    """

    def __init__(self, logistics_service: Optional[LogisticsService] = None):
        """
        初始化运费查询工具

        Args:
            logistics_service: 物流服务实例
        """
        self.logistics_service = logistics_service or LogisticsService()

    def extract_weight(self, text: str) -> Optional[int]:
        """
        从文本中提取重量（克）

        Args:
            text: 用户输入文本

        Returns:
            重量（克），如果未找到返回None
        """
        # 匹配模式：100g, 100克, 0.5kg, 1.5公斤, 2斤
        patterns = [
            (r'(\d+\.?\d*)\s*[kK][gG](?![a-zA-Z])', 1000),  # 0.5kg, 1KG -> 克
            (r'(\d+\.?\d*)\s*公斤', 1000),  # 1公斤 -> 克
            (r'(\d+\.?\d*)\s*斤', 500),  # 2斤 -> 克
            (r'(\d+\.?\d*)\s*[gG](?![a-zA-Z])', 1),  # 100g, 100G -> 克 (负向断言确保后面不是英文字母)
            (r'(\d+\.?\d*)\s*克', 1),  # 100克 -> 克
        ]

        for pattern, multiplier in patterns:
            match = re.search(pattern, text)
            if match:
                value = float(match.group(1))
                return int(value * multiplier)

        return None

    def extract_country(self, text: str) -> Optional[str]:
        """
        从文本中提取国家代码

        Args:
            text: 用户输入文本

        Returns:
            国家代码，如果未找到返回None
        """
        text_lower = text.lower()

        # 直接匹配国家名称
        for name, code in COUNTRY_NAME_TO_CODE.items():
            if name.lower() in text_lower:
                return code

        return None

    def extract_category_type(self, text: str) -> tuple[str, list[int]]:
        """
        从文本中提取商品类型

        Args:
            text: 用户输入文本

        Returns:
            (类型显示名称, 类型ID列表)，如果没有匹配到返回 (None, [])
        """
        # 尝试匹配大类和子类
        category_code = None
        subtype_code = "general"  # 默认子类型

        # 查找大类关键词
        for keyword, code in CATEGORY_KEYWORDS.items():
            if keyword in text:
                category_code = code
                break

        # 如果没有匹配到大类，返回None（不要默认值）
        if not category_code:
            return None, []

        # 查找子类型关键词
        for keyword, code in SUBTYPE_KEYWORDS.items():
            if keyword in text:
                subtype_code = code
                break

        # 构建完整的类型代码
        full_code = f"{category_code}_{subtype_code}"

        # 获取类型ID
        type_ids = category_type_manager.get_category_ids(full_code)

        # 获取显示名称
        flattened = category_type_manager.get_flattened_types()
        if full_code in flattened:
            display_name = flattened[full_code][0]
        else:
            # 如果找不到具体类型，使用大类+默认子类
            full_code = f"{category_code}_general"
            if full_code in flattened:
                display_name = flattened[full_code][0]
            else:
                display_name = "普货"
                type_ids = [189]

        return display_name, type_ids

    def extract_dimensions(self, text: str) -> tuple[Optional[int], Optional[int], Optional[int]]:
        """
        从文本中提取尺寸

        Args:
            text: 用户输入文本

        Returns:
            (长度, 宽度, 高度)，如果未找到返回None
        """
        # 匹配模式：10x20x30, 10*20*30, 10×20×30
        pattern = r'(\d+)\s*[xX*×]\s*(\d+)\s*[xX*×]\s*(\d+)'
        match = re.search(pattern, text)

        if match:
            return int(match.group(1)), int(match.group(2)), int(match.group(3))

        return None, None, None

    async def query_shipping_rate(
        self,
        weight: int,
        destination: str,
        category_type: str = "general",
        length: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        查询运费

        Args:
            weight: 重量（克）
            destination: 目的地国家代码
            category_type: 商品类型（已废弃，使用category_ids）
            length: 长度（厘米）
            width: 宽度（厘米）
            height: 高度（厘米）

        Returns:
            运费查询结果
        """
        # 提取商品类型信息
        category_name, category_ids = self.extract_category_type(category_type)
        logger.info(f"查询运费: 重量={weight}g, 目的地={destination}, 类型={category_name}, IDs={category_ids}")

        request = ShippingRateRequest(
            destination_country=destination,
            weight_g=weight,
            length_cm=length or 10,
            width_cm=width or 10,
            height_cm=height or 10,
            category_types=category_ids,
        )

        try:
            response = await self.logistics_service.estimate_shipping_rate(request)

            # 格式化结果
            available_lines = [line for line in response.lines if line.state == "available"]

            result = {
                "success": True,
                "destination": destination,
                "weight": weight,
                "category_name": category_name,
                "lines": [],
            }

            for line in available_lines[:5]:
                result["lines"].append({
                    "name": line.name,
                    "price": line.price,
                    "operation_fee": line.operation_fee,
                    "time_required": line.time_required,
                    "use_count": line.use_count,
                    "max_delivery_time": line.max_delivery_time,
                })

            return result

        except ShippingAPIError as e:
            logger.error(f"运费API错误: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def parse_shipping_query(self, text: str) -> dict[str, Any]:
        """
        解析运费查询请求

        Args:
            text: 用户输入文本

        Returns:
            解析结果，包含提取的参数和缺失的参数
        """
        weight = self.extract_weight(text)
        destination = self.extract_country(text)
        category_name, category_ids = self.extract_category_type(text)
        dimensions = self.extract_dimensions(text)

        result = {
            "weight": weight,
            "destination": destination,
            "category_name": category_name,
            "category_ids": category_ids,
            "dimensions": dimensions,
            "missing": [],
        }

        # 检查缺失的参数
        if weight is None:
            result["missing"].append("weight")
        if destination is None:
            result["missing"].append("destination")
        
        # 检查商品类型是否明确指定（如果没有指定大类，询问用户）
        has_category = False
        for keyword in CATEGORY_KEYWORDS.keys():
            if keyword in text:
                has_category = True
                break
        if not has_category:
            result["missing"].append("category")

        return result


# 全局运费工具实例
shipping_tool = ShippingTool()
