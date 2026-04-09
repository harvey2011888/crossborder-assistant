"""
商品类型管理模块

提供商品类型的动态获取和缓存功能
支持从API获取商品类型列表，按照网页版形式展示
"""

import logging
from typing import Any, Optional

from bot.services.platform.shipping_api import ShippingAPIClient, ShippingAPIError

# 配置日志
logger = logging.getLogger(__name__)

# 静态商品类型配置（API获取失败时的备选）
STATIC_CATEGORY_TYPES = {
    "clothing": {
        "name": "服饰",
        "types": [
            {"code": "clothing_general", "name": "普货", "id": 189},
            {"code": "clothing_brand", "name": "国际品牌", "id": 190},
            {"code": "clothing_sports", "name": "运动品牌", "id": 191},
        ]
    },
    "shoes": {
        "name": "鞋子",
        "types": [
            {"code": "shoes_general", "name": "普货", "id": 192},
            {"code": "shoes_brand", "name": "国际品牌", "id": 193},
            {"code": "shoes_sports", "name": "运动品牌", "id": 194},
        ]
    },
    "bags": {
        "name": "箱包",
        "types": [
            {"code": "bags_general", "name": "普货", "id": 195},
            {"code": "bags_brand", "name": "国际品牌", "id": 196},
        ]
    },
    "electronics": {
        "name": "电子产品",
        "types": [
            {"code": "electronics_general", "name": "普货", "id": 197},
            {"code": "electronics_battery", "name": "含电产品", "id": 198},
            {"code": "electronics_brand", "name": "国际品牌", "id": 199},
        ]
    },
    "cosmetics": {
        "name": "化妆品",
        "types": [
            {"code": "cosmetics_general", "name": "普货", "id": 200},
            {"code": "cosmetics_liquid", "name": "液体", "id": 201},
            {"code": "cosmetics_brand", "name": "国际品牌", "id": 202},
        ]
    },
    "food": {
        "name": "食品",
        "types": [
            {"code": "food_general", "name": "普货", "id": 203},
            {"code": "food_snacks", "name": "零食", "id": 204},
            {"code": "food_health", "name": "保健品", "id": 205},
        ]
    },
}


class CategoryTypeManager:
    """
    商品类型管理器

    管理商品类型的获取、缓存和查询
    从API获取商品类型，按照网页版形式（大类+子类）展示
    """

    def __init__(self, api_client: Optional[ShippingAPIClient] = None) -> None:
        """
        初始化商品类型管理器

        Args:
            api_client: 运费API客户端实例
        """
        self.api_client = api_client or ShippingAPIClient()
        self._categories: dict[str, dict] = {}  # 大类数据
        self._initialized = False
        logger.info("CategoryTypeManager 实例已创建")

    async def initialize(self) -> bool:
        """
        初始化商品类型

        从API获取商品类型列表，失败则使用静态配置

        Returns:
            是否成功获取商品类型
        """
        if self._initialized:
            logger.info("CategoryTypeManager 已经初始化，跳过")
            return True

        logger.info("开始初始化 CategoryTypeManager...")

        # 尝试从API获取
        if self.api_client.is_configured():
            try:
                logger.info("尝试从API获取商品类型...")
                categories = await self._fetch_from_api()
                if categories:
                    self._categories = categories
                    self._initialized = True
                    total_types = sum(len(cat.get("types", [])) for cat in categories.values())
                    logger.info(f"从API获取商品类型成功，共{len(categories)}个大类，{total_types}个子类")
                    return True
            except Exception as e:
                logger.warning(f"从API获取商品类型失败: {e}")
        else:
            logger.warning("API未配置，跳过API获取")

        # API获取失败，使用静态配置
        self._categories = STATIC_CATEGORY_TYPES.copy()
        self._initialized = True
        total_types = sum(len(cat.get("types", [])) for cat in self._categories.values())
        logger.info(f"使用静态商品类型配置，共{len(self._categories)}个大类，{total_types}个子类")
        logger.info(f"商品类型内容: {list(self._categories.keys())}")
        return True

    async def _fetch_from_api(self) -> Optional[dict[str, dict]]:
        """
        从API获取商品类型列表

        按照网页版形式获取大类和子类

        Returns:
            商品类型字典，结构：{大类code: {name: 大类名称, types: [{code, name, id}]}}
        """
        try:
            # 尝试调用商品类型接口
            logger.info("调用商品类型API: GET /express/pub/categories")
            response = await self.api_client.request("GET", "/express/pub/categories")
            logger.debug(f"商品类型API响应: {response}")
            
            data = response.get("data", {})

            if data:
                categories = {}
                # 解析API返回的数据
                for category in data.get("categories", []):
                    cat_code = category.get("code", "").lower()
                    cat_name = category.get("name", "")
                    cat_types = category.get("types", [])

                    if cat_code and cat_name:
                        categories[cat_code] = {
                            "name": cat_name,
                            "types": [
                                {
                                    "code": t.get("code", "").lower(),
                                    "name": t.get("name", ""),
                                    "id": t.get("id", 0)
                                }
                                for t in cat_types if t.get("code") and t.get("name")
                            ]
                        }

                return categories if categories else None

        except ShippingAPIError as e:
            logger.warning(f"商品类型API接口不可用: {e}")

        return None

    def get_categories(self) -> dict[str, dict]:
        """
        获取所有商品类型（大类+子类）

        Returns:
            商品类型字典
        """
        return self._categories.copy()

    def get_flattened_types(self) -> dict[str, tuple[str, str, int]]:
        """
        获取扁平化的商品类型列表

        用于Discord命令选项，格式：{code: (显示名称, 大类名称, type_id)}

        Returns:
            扁平化的商品类型字典
        """
        # logger.info(f"get_flattened_types 被调用，_initialized={self._initialized}, _categories={self._categories}")
        
        flattened = {}
        for cat_code, cat_data in self._categories.items():
            cat_name = cat_data.get("name", "")
            types_list = cat_data.get("types", [])
            logger.debug(f"处理大类 {cat_code}: {cat_name}, 有 {len(types_list)} 个子类")
            for type_info in types_list:
                type_code = type_info.get("code", "")
                type_name = type_info.get("name", "")
                type_id = type_info.get("id", 0)
                if type_code and type_name:
                    # 组合显示名称：大类-子类
                    display_name = f"{cat_name}-{type_name}"
                    flattened[type_code] = (display_name, cat_name, type_id)
                    logger.debug(f"  添加子类: {type_code} -> {display_name}")
        
        logger.info(f"get_flattened_types 返回 {len(flattened)} 个类型")
        return flattened

    def get_category_ids(self, type_code: str) -> list[int]:
        """
        获取商品类型ID列表

        Args:
            type_code: 商品类型代码

        Returns:
            商品类型ID列表
        """
        for cat_data in self._categories.values():
            for type_info in cat_data.get("types", []):
                if type_info.get("code", "").lower() == type_code.lower():
                    return [type_info.get("id", 0)]
        return [189]  # 默认普货

    def is_initialized(self) -> bool:
        """
        检查是否已初始化

        Returns:
            是否已初始化
        """
        return self._initialized

    async def refresh(self) -> bool:
        """
        刷新商品类型缓存

        重新从API获取商品类型列表

        Returns:
            是否刷新成功
        """
        self._initialized = False
        self._categories.clear()
        return await self.initialize()


# 全局商品类型管理器实例
category_type_manager = CategoryTypeManager()
