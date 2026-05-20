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

# 国家名称到代码的映射（20个指定国家）
COUNTRY_NAME_TO_CODE = {
    # 中文名称
    "巴西": "BR",
    "美国": "US",
    "葡萄牙": "PT",
    "英国": "UK",
    "德国": "DE",
    "加拿大": "CA",
    "中国大陆": "CN",
    "中国": "CN",
    "大陆": "CN",
    "法国": "FR",
    "澳大利亚": "AU",
    "澳洲": "AU",
    "西班牙": "ES",
    "意大利": "IT",
    "爱尔兰": "IE",
    "荷兰": "NL",
    "安哥拉": "AO",
    "墨西哥": "MX",
    "罗马尼亚": "RO",
    "柬埔寨": "KH",
    "奥地利": "AT",
    "阿联酋": "AE",
    "波兰": "PL",

    # 英文名称
    "brazil": "BR",
    "usa": "US",
    "united states": "US",
    "america": "US",
    "portugal": "PT",
    "uk": "UK",
    "united kingdom": "UK",
    "britain": "UK",
    "england": "UK",
    "germany": "DE",
    "canada": "CA",
    "china": "CN",
    "mainland china": "CN",
    "france": "FR",
    "australia": "AU",
    "spain": "ES",
    "italy": "IT",
    "ireland": "IE",
    "netherlands": "NL",
    "angola": "AO",
    "mexico": "MX",
    "romania": "RO",
    "cambodia": "KH",
    "austria": "AT",
    "uae": "AE",
    "united arab emirates": "AE",
    "poland": "PL",
}

# 国家别名映射（用于模糊匹配）
COUNTRY_ALIASES = {
    "BR": ["巴西", "足球王国", "桑巴国"],
    "US": ["米国", "漂亮国", "灯塔国", "美帝", "鹰酱", "阿美莉卡", "美利坚"],
    "PT": ["葡萄牙"],
    "UK": ["腐国", "大不列颠", "日不落", "英伦", "英格兰", "苏格兰", "威尔士", "北爱尔兰"],
    "DE": ["德意志", "汉斯", "德国佬"],
    "CA": ["枫叶国", "加拿大", "加村"],
    "CN": ["中国", "大陆", "中国大陆", "祖国", "国内"],
    "FR": ["法兰西", "高卢鸡", "法国佬"],
    "AU": ["土澳", "袋鼠国", "澳洲"],
    "ES": ["板鸭", "西班牙"],
    "IT": ["意呆", "意呆利", "意大利"],
    "IE": ["爱尔兰"],
    "NL": ["荷兰", "尼德兰"],
    "AO": ["安哥拉"],
    "MX": ["墨西哥"],
    "RO": ["罗马尼亚"],
    "KH": ["柬埔寨", "柬埔"],
    "AT": ["奥地利"],
    "AE": ["阿联酋", "迪拜", "阿布扎比"],
    "PL": ["波兰"],
}

# 国家拼音映射
COUNTRY_PINYIN = {
    "baxi": "BR",
    "meiguo": "US",
    "putaoya": "PT",
    "yingguo": "UK",
    "deguo": "DE",
    "jiana": "CA",
    "zhongguo": "CN",
    "dalu": "CN",
    "faguo": "FR",
    "aozhou": "AU",
    "xibanya": "ES",
    "yidali": "IT",
    "aierlan": "IE",
    "helan": "NL",
    "angela": "AO",
    "moxige": "MX",
    "luomaniya": "RO",
    "jianpuzhai": "KH",
    "aodili": "AT",
    "alianqiu": "AE",
    "bolan": "PL",
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

# 中文数字映射
CHINESE_NUMBERS = {
    '一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5,
    '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
    '半': 0.5, '几': 3,  # 几默认按3计算
}

# 常见物品重量参考（克）
ITEM_WEIGHT_REFERENCES = {
    '手机': 200,
    'iphone': 200,
    '鞋子': 800,
    '鞋': 800,
    '衣服': 300,
    't恤': 200,
    '裤子': 400,
    '包包': 500,
    '包': 500,
    '化妆品': 300,
    '零食': 500,
    '书本': 400,
    '书': 400,
    '耳机': 100,
    '充电器': 150,
    '充电宝': 300,
    '数据线': 50,
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

    def _parse_chinese_number(self, text: str) -> Optional[float]:
        """
        解析中文数字

        Args:
            text: 包含中文数字的文本

        Returns:
            数字值，解析失败返回None
        """
        # 处理"一斤半"、"两公斤"、"三斤"等
        # 先尝试匹配"X斤半"、"X公斤"等模式
        patterns = [
            r'([一二两三四五六七八九十])(斤|公斤|kg|g|克)半',  # 一斤半
            r'([一二两三四五六七八九十])(斤|公斤|kg|g|克)',     # 两公斤
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                chinese_num = match.group(1)
                base_value = CHINESE_NUMBERS.get(chinese_num, 0)
                if '半' in text[match.end()-1:match.end()+1]:
                    base_value += 0.5
                return base_value

        # 处理"十X"的情况（如"十二斤"）
        match = re.search(r'十([一二三四五六七八九]?)(斤|公斤|kg|g|克)', text)
        if match:
            value = 10
            if match.group(1):
                value += CHINESE_NUMBERS.get(match.group(1), 0)
            return value

        return None

    def _extract_item_weight(self, text: str) -> Optional[int]:
        """
        从物品描述中提取参考重量

        Args:
            text: 用户输入文本

        Returns:
            参考重量（克），未找到返回None
        """
        text_lower = text.lower()
        for item, weight in ITEM_WEIGHT_REFERENCES.items():
            if item in text_lower or item in text:
                return weight
        return None

    def _extract_quantity(self, text: str) -> int:
        """
        从文本中提取数量

        Args:
            text: 用户输入文本

        Returns:
            数量，默认为1
        """
        # 匹配阿拉伯数字 + 量词
        quantity_match = re.search(r'(\d+)\s*(部|双|件|个|套|盒|只|条)', text)
        if quantity_match:
            return int(quantity_match.group(1))

        # 匹配中文数字 + 量词
        chinese_quantity_match = re.search(r'([一二两三四五六七八九十])\s*(部|双|件|个|套|盒|只|条)', text)
        if chinese_quantity_match:
            chinese_num = chinese_quantity_match.group(1)
            return int(CHINESE_NUMBERS.get(chinese_num, 1))

        return 1

    def extract_weight(self, text: str) -> Optional[int]:
        """
        从文本中提取重量（克）

        支持格式：
        - 数字格式：100g, 100克, 0.5kg, 1.5公斤, 2斤
        - 中文数字：一斤半, 两公斤, 三斤
        - 模糊表达：500g左右, 大概1kg, 差不多2斤
        - 范围：500-1000g
        - 物品参考：一部手机, 一双鞋

        Args:
            text: 用户输入文本

        Returns:
            重量（克），如果未找到返回None
        """
        # 首先尝试匹配范围格式（如"500-1000g"），取中间值
        range_patterns = [
            r'(\d+)\s*[-~到]\s*(\d+)\s*[gG](?![a-zA-Z])',  # 500-1000g
            r'(\d+)\s*[-~到]\s*(\d+)\s*克',  # 500-1000克
            r'(\d+\.?\d*)\s*[-~到]\s*(\d+\.?\d*)\s*公斤',  # 1-2公斤
            r'(\d+\.?\d*)\s*[-~到]\s*(\d+\.?\d*)\s*[kK][gG]',  # 1-2kg
        ]
        for pattern in range_patterns:
            range_match = re.search(pattern, text)
            if range_match:
                min_val = float(range_match.group(1))
                max_val = float(range_match.group(2))
                # 判断单位
                matched_text = range_match.group(0)
                if '公斤' in matched_text or 'kg' in matched_text.lower():
                    min_val *= 1000
                    max_val *= 1000
                return int((min_val + max_val) / 2)

        # 匹配数字格式（最精确）
        patterns = [
            (r'(\d+\.?\d*)\s*[kK][gG](?![a-zA-Z])', 1000),  # 0.5kg, 1KG -> 克
            (r'(\d+\.?\d*)\s*公斤', 1000),  # 1公斤 -> 克
            (r'(\d+\.?\d*)\s*斤', 500),  # 2斤 -> 克
            (r'(\d+\.?\d*)\s*[gG](?![a-zA-Z])', 1),  # 100g, 100G -> 克
            (r'(\d+\.?\d*)\s*克', 1),  # 100克 -> 克
        ]

        for pattern, multiplier in patterns:
            match = re.search(pattern, text)
            if match:
                value = float(match.group(1))
                return int(value * multiplier)

        # 尝试解析中文数字
        chinese_value = self._parse_chinese_number(text)
        if chinese_value:
            # 判断单位
            if '公斤' in text or 'kg' in text.lower():
                return int(chinese_value * 1000)
            elif '斤' in text:
                return int(chinese_value * 500)
            elif '克' in text or 'g' in text.lower():
                return int(chinese_value)

        # 尝试从物品描述中提取参考重量
        item_weight = self._extract_item_weight(text)
        if item_weight:
            # 检查是否有数量修饰
            quantity = self._extract_quantity(text)
            return item_weight * quantity

        return None

    def _normalize_text(self, text: str) -> str:
        """
        标准化文本，移除多余空格和标点

        Args:
            text: 原始文本

        Returns:
            标准化后的文本
        """
        # 移除多余空格
        text = re.sub(r'\s+', '', text)
        # 转换为小写
        return text.lower()

    def extract_country(self, text: str) -> Optional[str]:
        """
        从文本中提取国家代码

        支持格式：
        - 标准名称：美国、日本、德国
        - 别名：米国、霓虹、枫叶国
        - 拼音：meiguo、riben
        - 英文：usa、japan、germany

        Args:
            text: 用户输入文本

        Returns:
            国家代码，如果未找到返回None
        """
        text_normalized = self._normalize_text(text)
        text_lower = text.lower()

        # 1. 直接匹配标准国家名称（最优先）
        for name, code in COUNTRY_NAME_TO_CODE.items():
            name_normalized = self._normalize_text(name)
            if name_normalized in text_normalized:
                return code

        # 2. 匹配别名
        for code, aliases in COUNTRY_ALIASES.items():
            for alias in aliases:
                alias_normalized = self._normalize_text(alias)
                if alias_normalized in text_normalized:
                    return code

        # 3. 匹配拼音
        for pinyin, code in COUNTRY_PINYIN.items():
            if pinyin in text_normalized:
                return code

        # 4. 模糊匹配（处理可能的拼写错误）
        # 简单的编辑距离匹配，用于处理轻微拼写错误
        best_match = None
        best_score = 0
        min_length = 3  # 最小匹配长度

        for name, code in COUNTRY_NAME_TO_CODE.items():
            if len(name) >= min_length:
                # 检查是否包含主要部分
                name_lower = name.lower()
                if name_lower in text_lower or text_lower in name_lower:
                    score = len(name) / max(len(text), 1)
                    if score > best_score:
                        best_score = score
                        best_match = code

        if best_match and best_score > 0.5:
            return best_match

        return None

    def _build_dynamic_category_keywords(self) -> dict[str, tuple[str, str, list[int]]]:
        """
        动态构建商品类型关键词映射

        从category_type_manager获取最新的商品类型信息

        Returns:
            关键词到(大类代码, 子类代码, 类型ID列表)的映射
        """
        keywords_map = {}
        flattened = category_type_manager.get_flattened_types()

        for type_code, (display_name, cat_name, type_id) in flattened.items():
            # 解析类型代码（格式：大类_子类）
            parts = type_code.split('_')
            if len(parts) >= 2:
                cat_code = parts[0]
                subtype_code = '_'.join(parts[1:])
            else:
                cat_code = type_code
                subtype_code = "general"

            # 添加显示名称作为关键词
            keywords_map[display_name] = (cat_code, subtype_code, [type_id])

            # 添加大类名称作为关键词
            if cat_name:
                keywords_map[cat_name] = (cat_code, "general", [type_id])

        return keywords_map

    def _extract_category_from_description(self, text: str) -> tuple[Optional[str], Optional[str], list[int]]:
        """
        从描述性文本中提取商品类型

        支持描述性输入如"带电池的手机"、"国际品牌运动鞋"

        Args:
            text: 用户输入文本

        Returns:
            (大类代码, 子类代码, 类型ID列表)，未找到返回(None, None, [])
        """
        text_lower = text.lower()

        # 特征词映射到子类型
        feature_keywords = {
            "battery": ["带电池", "含电", "带电", "电池", "充电宝", "锂电池", "电子", "数码", "手机", "电脑", "笔记本", "平板"],
            "brand": ["国际品牌", "大牌", "奢侈品", "名牌", "正品", "专柜", "旗舰店"],
            "sports": ["运动品牌", "运动鞋", "运动服", "nike", "adidas", "耐克", "阿迪", "乔丹"],
            "liquid": ["液体", "水乳", "精华", "香水", "喷雾", "化妆水", "乳液"],
            "snacks": ["零食", "饼干", "巧克力", "糖果", "薯片", "坚果"],
            "health": ["保健品", "维生素", "蛋白粉", "鱼油", "保健", "营养品"],
        }

        # 大类特征词
        category_features = {
            "clothing": ["衣服", "服装", "上衣", "裤子", "裙子", "外套", "t恤", "衬衫", "毛衣", "羽绒服"],
            "shoes": ["鞋子", "鞋", "运动鞋", "皮鞋", "靴子", "凉鞋", "拖鞋", "高跟鞋"],
            "bags": ["包", "包包", "箱包", "背包", "手提包", "钱包", "行李箱", "挎包"],
            "electronics": ["电子", "数码", "电器", "手机", "电脑", "耳机", "充电器", "数据线", "相机"],
            "cosmetics": ["化妆品", "护肤品", "彩妆", "口红", "粉底", "眼影", "面膜", "香水"],
            "food": ["食品", "食物", "零食", "保健品", "营养品", "干货", "特产"],
        }

        # 检测子类型特征
        detected_subtype = "general"
        for subtype, keywords in feature_keywords.items():
            for keyword in keywords:
                if keyword in text_lower or keyword in text:
                    detected_subtype = subtype
                    break
            if detected_subtype != "general":
                break

        # 检测大类特征
        detected_category = None
        for cat_code, keywords in category_features.items():
            for keyword in keywords:
                if keyword in text_lower or keyword in text:
                    detected_category = cat_code
                    break
            if detected_category:
                break

        # 如果检测到大类，获取类型信息
        if detected_category:
            full_code = f"{detected_category}_{detected_subtype}"
            type_ids = category_type_manager.get_category_ids(full_code)

            # 获取显示名称
            flattened = category_type_manager.get_flattened_types()
            if full_code in flattened:
                return detected_category, detected_subtype, type_ids
            else:
                # 尝试使用默认子类
                general_code = f"{detected_category}_general"
                if general_code in flattened:
                    return detected_category, "general", category_type_manager.get_category_ids(general_code)

        return None, None, []

    def extract_category_type(self, text: str) -> tuple[Optional[str], list[int]]:
        """
        从文本中提取商品类型

        支持格式：
        - 标准类型：服饰-普货、电子产品-含电
        - 描述性输入：带电池的手机、国际品牌运动鞋
        - 关键词匹配：衣服、鞋子、化妆品

        Args:
            text: 用户输入文本

        Returns:
            (类型显示名称, 类型ID列表)，如果没有匹配到返回 (None, [])
        """
        text_normalized = self._normalize_text(text)

        # 方法1：尝试从描述性文本中提取（最智能）
        cat_code, subtype_code, type_ids = self._extract_category_from_description(text)
        if cat_code:
            flattened = category_type_manager.get_flattened_types()
            full_code = f"{cat_code}_{subtype_code}"
            if full_code in flattened:
                return flattened[full_code][0], type_ids

        # 方法2：动态关键词匹配
        dynamic_keywords = self._build_dynamic_category_keywords()
        for keyword, (cat_code, subtype_code, type_ids) in sorted(dynamic_keywords.items(), key=lambda x: -len(x[0])):
            # 按长度降序排序，优先匹配更长的关键词
            keyword_normalized = self._normalize_text(keyword)
            if keyword_normalized in text_normalized:
                return keyword, type_ids

        # 方法3：静态关键词匹配（兼容旧逻辑）
        category_code = None
        subtype_code = "general"

        # 查找大类关键词
        for keyword, code in CATEGORY_KEYWORDS.items():
            if keyword in text:
                category_code = code
                break

        if category_code:
            # 查找子类型关键词
            for keyword, code in SUBTYPE_KEYWORDS.items():
                if keyword in text:
                    subtype_code = code
                    break

            # 构建完整的类型代码
            full_code = f"{category_code}_{subtype_code}"
            type_ids = category_type_manager.get_category_ids(full_code)

            # 获取显示名称
            flattened = category_type_manager.get_flattened_types()
            if full_code in flattened:
                return flattened[full_code][0], type_ids
            else:
                # 如果找不到具体类型，使用大类+默认子类
                general_code = f"{category_code}_general"
                if general_code in flattened:
                    return flattened[general_code][0], category_type_manager.get_category_ids(general_code)

        # 方法4：返回默认类型
        return "普货", [189]

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
