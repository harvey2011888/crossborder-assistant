"""
运费查询对话管理模块

管理用户通过对话形式查询运费的状态和流程
"""

import logging
import re
from typing import Any, Optional
from dataclasses import dataclass, field

from bot.services.ai.tools import shipping_tool
from bot.services.platform.logistics import (
    LogisticsService,
    ShippingRateRequest,
    logistics_service,
)
from bot.services.platform.shipping_api import ShippingAPIError
from bot.services.platform.category_types import category_type_manager

logger = logging.getLogger(__name__)


@dataclass
class ShippingQueryState:
    """运费查询状态"""
    user_id: int
    weight: Optional[int] = None
    destination: Optional[str] = None
    category_type: Optional[str] = None
    category_name: Optional[str] = None
    category_ids: list[int] = field(default_factory=lambda: [189])
    length: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    step: str = "init"  # init, weight, destination, category, dimensions, confirm, done
    awaiting_confirmation: bool = False  # 是否等待用户确认参数
    dimensions_asked: bool = False  # 是否已经询问过尺寸

    def is_complete(self) -> bool:
        """检查是否所有必需参数都已收集（不包括长宽高，长宽高是可选的）"""
        return self.weight is not None and self.destination is not None and self.category_type is not None

    def get_missing_params(self) -> list[str]:
        """获取缺失的参数列表"""
        missing = []
        if self.weight is None:
            missing.append("weight")
        if self.destination is None:
            missing.append("destination")
        if self.category_type is None:
            missing.append("category")
        return missing

    def should_ask_dimensions(self) -> bool:
        """检查是否应该询问长宽高（当必需参数都齐全但长宽高未设置且未询问过时）"""
        return self.is_complete() and not self.dimensions_asked and self.length is None and self.width is None and self.height is None

    def get_summary(self) -> str:
        """获取当前参数摘要"""
        lines = []
        if self.weight:
            lines.append(f"📦 重量: {self.weight}g")
        if self.destination:
            lines.append(f"🌍 目的地: {self.destination}")
        if self.category_name:
            lines.append(f"🏷️ 商品类型: {self.category_name}")
        if self.length and self.width and self.height:
            lines.append(f"📐 尺寸: {self.length}×{self.width}×{self.height}cm")
        else:
            lines.append(f"📐 尺寸: 10×10×10cm（默认）")
        return "\n".join(lines)


class ShippingConversationManager:
    """
    运费查询对话管理器
    
    管理用户通过对话形式查询运费的状态机
    """
    
    def __init__(self):
        self._states: dict[int, ShippingQueryState] = {}
        self.logistics_service = logistics_service
        self._category_options = None
    
    @property
    def CATEGORY_OPTIONS(self) -> dict[str, tuple[str, str, list[int]]]:
        """动态获取商品类型选项"""
        if self._category_options is None:
            self._category_options = {}
            flattened = category_type_manager.get_flattened_types()
            for idx, (type_code, (display_name, cat_name, type_id)) in enumerate(flattened.items(), 1):
                self._category_options[str(idx)] = (display_name, type_code, [type_id])
        return self._category_options
    
    def get_or_create_state(self, user_id: int) -> ShippingQueryState:
        """获取或创建用户状态"""
        if user_id not in self._states:
            self._states[user_id] = ShippingQueryState(user_id=user_id)
        return self._states[user_id]
    
    def clear_state(self, user_id: int):
        """清除用户状态"""
        if user_id in self._states:
            del self._states[user_id]
    
    def is_in_shipping_flow(self, user_id: int) -> bool:
        """检查用户是否在运费查询流程中"""
        return user_id in self._states and self._states[user_id].step != "done"
    
    def parse_input(self, text: str) -> dict[str, Any]:
        """解析用户输入，提取运费相关参数"""
        return shipping_tool.parse_shipping_query(text)

    def _detect_parameter_modification(self, text: str) -> tuple[Optional[str], Any]:
        """
        检测用户是否想要修改某个参数

        支持格式：
        - "重量改成1kg"、"重量改为500g"
        - "目的地换成日本"、"国家改成美国"
        - "类型换成衣服"

        Args:
            text: 用户输入文本

        Returns:
            (参数名, 新值)，如果没有检测到修改返回 (None, None)
        """
        text_lower = text.lower()

        # 重量修改检测
        weight_patterns = [
            r'(?:重量|重|weight).*?(?:改|换|变|调整|修改).*?(\d+\.?\d*)\s*(g|克|kg|公斤|斤)',
            r'(?:改|换|变|调整|修改).*?(?:重量|重|weight).*?(\d+\.?\d*)\s*(g|克|kg|公斤|斤)',
        ]
        for pattern in weight_patterns:
            match = re.search(pattern, text_lower)
            if match:
                value = float(match.group(1))
                unit = match.group(2)
                if unit in ['kg', '公斤']:
                    value *= 1000
                elif unit == '斤':
                    value *= 500
                return 'weight', int(value)

        # 目的地修改检测
        destination_patterns = [
            r'(?:目的地|国家|地址|destination).*?(?:改|换|变|调整|修改).*?([\u4e00-\u9fa5]+|[a-zA-Z]+)',
            r'(?:改|换|变|调整|修改).*?(?:目的地|国家|地址|destination).*?([\u4e00-\u9fa5]+|[a-zA-Z]+)',
        ]
        for pattern in destination_patterns:
            match = re.search(pattern, text_lower)
            if match:
                country_text = match.group(1)
                country_code = shipping_tool.extract_country(country_text)
                if country_code:
                    return 'destination', country_code

        # 商品类型修改检测
        category_patterns = [
            r'(?:类型|种类|商品|category).*?(?:改|换|变|调整|修改).*?([\u4e00-\u9fa5]+)',
            r'(?:改|换|变|调整|修改).*?(?:类型|种类|商品|category).*?([\u4e00-\u9fa5]+)',
        ]
        for pattern in category_patterns:
            match = re.search(pattern, text_lower)
            if match:
                category_text = match.group(1)
                category_name, category_ids = shipping_tool.extract_category_type(category_text)
                if category_name:
                    return 'category', (category_name, category_ids)

        return None, None

    def update_state_from_input(self, state: ShippingQueryState, text: str) -> dict[str, Any]:
        """
        根据用户输入更新状态

        Returns:
            更新结果字典，包含：
            - updated: 新收集到的参数列表
            - modified: 被修改的参数列表
            - is_confirmation: 是否是确认操作
            - is_skip_dimensions: 是否跳过尺寸输入
        """
        result = {
            'updated': [],
            'modified': [],
            'is_confirmation': False,
            'is_skip_dimensions': False,
        }

        text_stripped = text.strip().lower()

        # 1. 检测是否是确认操作
        confirmation_keywords = ['确认', '是的', '没错', '对', '正确', 'ok', 'yes', '确定', '可以', '好']
        if any(kw in text_stripped for kw in confirmation_keywords):
            result['is_confirmation'] = True
            return result

        # 2. 检测是否是跳过尺寸
        skip_keywords = ['跳过', '不用', '不需要', '默认', '没有', 'no', 'skip']
        if any(kw in text_stripped for kw in skip_keywords):
            result['is_skip_dimensions'] = True
            state.dimensions_asked = True
            return result

        # 3. 检测参数修改
        param_to_modify, new_value = self._detect_parameter_modification(text)
        if param_to_modify:
            if param_to_modify == 'weight':
                state.weight = new_value
                result['modified'].append('weight')
            elif param_to_modify == 'destination':
                state.destination = new_value
                result['modified'].append('destination')
            elif param_to_modify == 'category':
                state.category_name, state.category_ids = new_value
                state.category_type = str(state.category_ids[0]) if state.category_ids else '189'
                result['modified'].append('category')
            return result

        # 4. 正常参数提取
        parsed = self.parse_input(text)

        # 更新重量
        if state.weight is None and parsed["weight"] is not None:
            state.weight = parsed["weight"]
            result['updated'].append("weight")

        # 更新目的地
        if state.destination is None and parsed["destination"] is not None:
            state.destination = parsed["destination"]
            result['updated'].append("destination")

        # 更新商品类型（从文本中提取或从选项中选择）
        if state.category_type is None:
            # 检查是否是数字选项
            if text_stripped in self.CATEGORY_OPTIONS:
                state.category_name, state.category_type, state.category_ids = self.CATEGORY_OPTIONS[text_stripped]
                result['updated'].append("category")
            elif parsed["category_name"] is not None:
                state.category_name = parsed["category_name"]
                state.category_ids = parsed["category_ids"]
                state.category_type = parsed["category_ids"][0] if parsed["category_ids"] else "189"
                result['updated'].append("category")

        # 更新尺寸（可选）
        if parsed["dimensions"]:
            state.length, state.width, state.height = parsed["dimensions"]
            state.dimensions_asked = True

        return result
    
    def get_prompt_message(self, state: ShippingQueryState) -> str:
        """根据当前状态生成提示消息"""
        missing = state.get_missing_params()

        # 如果所有必需参数都已收集，显示确认信息
        if not missing:
            if state.awaiting_confirmation:
                return (
                    f"📋 请确认以下运费查询信息:\n\n"
                    f"{state.get_summary()}\n\n"
                    f'✅ 信息正确，请回复"确认"开始查询\n'
                    f'📝 如需修改，请说"重量改成..."或"目的地换成..."等'
                )
            elif state.should_ask_dimensions():
                state.dimensions_asked = True
                return (
                    f"📋 运费查询信息已收集完成！\n\n"
                    f"{state.get_summary()}\n\n"
                    f"📐 是否需要提供包裹尺寸（长x宽x高 cm）？\n"
                    f"💡 常见参考：手机(15x8x2)、鞋盒(30x20x12)、衣服(25x20x5)\n"
                    f'📝 直接输入尺寸如"20x15x10"，或回复"跳过"使用默认尺寸'
                )
            else:
                return "所有信息已收集完成！正在查询运费..."

        messages = ["📦 我来帮您查询运费！\n"]

        # 显示已收集的信息
        collected = []
        if state.weight:
            collected.append(f"✅ 重量: {state.weight}g")
        if state.destination:
            collected.append(f"✅ 目的地: {state.destination}")
        if state.category_name:
            collected.append(f"✅ 商品类型: {state.category_name}")

        if collected:
            messages.append("已收集信息:")
            messages.extend(collected)
            messages.append("")

        # 询问缺失的信息
        if "weight" in missing:
            messages.append("⏳ 请提供包裹重量\n")
            messages.append("💡 支持格式：")
            messages.append("   • 数字：500g, 1kg, 2.5公斤")
            messages.append("   • 中文：一斤半, 两公斤")
            messages.append("   • 物品：一部手机, 一双鞋")
        elif "destination" in missing:
            messages.append("⏳ 请提供目的地国家\n")
            messages.append("💡 支持格式：")
            messages.append("   • 标准：美国、日本、德国")
            messages.append("   • 别名：米国、霓虹、枫叶国")
            messages.append("   • 拼音：meiguo、riben")
        elif "category" in missing:
            messages.append("⏳ 请选择商品类型（输入数字）:\n")
            for num, (name, code, ids) in list(self.CATEGORY_OPTIONS.items())[:10]:  # 只显示前10个
                messages.append(f"   {num}. {name}")
            if len(self.CATEGORY_OPTIONS) > 10:
                messages.append(f"   ... 还有 {len(self.CATEGORY_OPTIONS) - 10} 个选项")
            messages.append('\n💡 也可以直接描述：如"带电池的手机"、"国际品牌运动鞋"')

        return "\n".join(messages)
    
    async def query_shipping_rate(self, state: ShippingQueryState) -> dict[str, Any]:
        """
        执行运费查询
        
        Returns:
            查询结果字典
        """
        if not state.is_complete():
            return {
                "success": False,
                "error": "参数不完整",
                "missing": state.get_missing_params(),
            }
        
        request = ShippingRateRequest(
            destination_country=state.destination,
            weight_g=state.weight,
            length_cm=state.length or 10,
            width_cm=state.width or 10,
            height_cm=state.height or 10,
            category_types=state.category_ids,
        )
        
        try:
            logger.info(f"开始查询运费: 目的地={state.destination}, 重量={state.weight}g")
            response = await self.logistics_service.estimate_shipping_rate(request)
            logger.info(f"运费查询成功, 返回 {len(response.lines)} 条线路")
            
            # 格式化结果
            available_lines = [line for line in response.lines if line.state == "available"]
            logger.info(f"可用线路: {len(available_lines)} 条")
            
            result = {
                "success": True,
                "destination": state.destination,
                "weight": state.weight,
                "category_name": state.category_name or "普货",
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
    
    def format_result(self, result: dict[str, Any]) -> str:
        """格式化运费查询结果"""
        if not result["success"]:
            return f"❌ 运费查询失败: {result.get('error', '未知错误')}"
        
        lines_text = []
        for i, line in enumerate(result["lines"][:3], 1):
            lines_text.append(
                f"{i}. **{line['name']}**\n"
                f"   💰 ¥{line['price']} (操作费: ¥{line['operation_fee']})\n"
                f"   ⏱️ {line['time_required']}天 | 使用次数: {line['use_count']:,}\n"
                f"   ✅ 送达率: {line['max_delivery_time']}%"
            )
        
        return (
            f"📦 **运费估算结果**\n\n"
            f"目的地: **{result['destination']}**\n"
            f"重量: **{result['weight']}g**\n"
            f"商品类型: **{result['category_name']}**\n\n"
            f"**可用线路**:\n"
            f"{chr(10).join(lines_text)}\n\n"
            f"💡 提示: 以上价格为预估价格，实际价格以订单确认时为准。"
        )


# 全局运费对话管理器实例
shipping_conversation_manager = ShippingConversationManager()
