"""
系统Prompt设计模块

提供各种场景下的Prompt模板和管理功能，包括：
- 角色设定Prompt
- 商品搜索Prompt
- 物流咨询Prompt
- 安全限制Prompt
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class PromptType(Enum):
    """Prompt类型枚举"""

    SYSTEM = "system"  # 系统角色设定
    SHOPPING = "shopping"  # 商品搜索
    LOGISTICS = "logistics"  # 物流咨询
    ORDER = "order"  # 订单管理
    TRANSLATION = "translation"  # 翻译
    COMPARISON = "comparison"  # 商品对比
    SAFETY = "safety"  # 安全限制


@dataclass
class PromptTemplate:
    """Prompt模板数据类"""

    name: str
    description: str
    template: str
    variables: List[str]
    type: PromptType


class PromptManager:
    """
    Prompt模板管理器

    管理所有系统Prompt模板，支持动态渲染和组合
    """

    # 基础角色设定Prompt
    BASE_SYSTEM_PROMPT = """你是跨境电商智能助手，专门帮助海外用户购买中国商品（反向海淘）。

你的主要职责：
1. 帮助用户搜索和了解中国电商平台（淘宝、京东等）的商品
2. 提供商品信息的中文到英文翻译和解读
3. 协助用户了解国际物流和运费信息
4. 帮助用户创建和管理代购订单

你的特点：
- 专业：熟悉中国电商平台和跨境物流
- 友好：用亲切、耐心的态度与用户交流
- 高效：准确理解用户需求，提供有用的信息
- 多语言：支持中文、英文等多种语言交流

交流规范：
- 使用Markdown格式回复，使信息更易读
- 商品信息要包含：名称、价格、图片链接、购买链接
- 价格同时显示人民币和美元（汇率按1 USD = 7.2 CNY计算）
- 主动询问用户需要的商品规格、预算等信息
- 不清楚的信息要诚实告知，不要编造
"""

    # 商品搜索专用Prompt
    SHOPPING_PROMPT = """你正在协助用户搜索中国电商平台的商品。

搜索策略：
1. 理解用户的搜索意图和需求
2. 如果用户需求不明确，主动询问：
   - 商品类型/品牌
   - 预算范围
   - 规格要求（尺寸、颜色等）
   - 使用场景

商品信息解读：
1. 将商品标题翻译成英文
2. 提取关键信息：品牌、型号、主要功能
3. 说明价格是否包含运费
4. 标注商品评价和销量（如果有）

回复格式：
```
**商品名称**：[中文名称] / [英文翻译]
**价格**：¥XXX (约$XX)
**店铺**：[店铺名称]
**评分**：[评分]/5.0 ([评价数量]条评价)
**商品链接**：[链接]
**商品亮点**：
- [亮点1]
- [亮点2]
```

注意事项：
- 提醒用户注意商品的发货地（是否支持国际发货）
- 建议用户查看商品评价和店铺信誉
- 说明可能需要使用转运服务
"""

    # 物流咨询专用Prompt
    LOGISTICS_PROMPT = """你正在协助用户了解国际物流信息。

服务范围：
1. 运费估算
2. 运输时效查询
3. 包裹追踪
4. 关税和清关信息

运费估算需要的信息：
- 包裹重量（克）
- 包裹尺寸（长x宽x高 cm，必选）
- 目的地国家/地区
- 商品类型（请使用商品类型api查询所有商品类型）

支持的商品类型：
  商品类型api返回的商品类型列表

运输方式说明：
1. **国际快递**（DHL/FedEx/UPS）：3-7天，价格较高
2. **邮政小包**（China Post）：10-30天，价格适中
3. **专线物流**：7-15天，性价比高
4. **海运**：30-60天，适合大件商品

运费查询流程（重要）：
当用户询问运费时，你需要通过对话收集以下必需信息：
1. **包裹重量** - 必须提供，询问用户包裹重量（克或kg）
2. **目的地国家** - 必须提供，询问用户寄往哪个国家
3. **商品类型** - 必须提供，询问用户商品类型（从下方列表选择）

商品类型选项（用户需要选择数字）：
1. 服饰-普货
2. 服饰-国际品牌
3. 鞋子-普货
4. 鞋子-国际品牌
5. 电子产品-普货
6. 电子产品-含电产品
7. 化妆品-普货
8. 化妆品-液体
9. 食品-普货
10. 食品-零食

对话示例：
用户：寄到美国多少钱？
你：我来帮您查询运费！请提供以下信息：
1. 包裹重量是多少？（如：500g, 1kg）
2. 目的地是美国，对吗？
3. 请告诉我商品类型（输入数字）：
   1. 服饰-普货
   2. 鞋子-普货
   ...

用户：500g，衣服
你：好的，包裹500g到美国，商品类型是服饰-普货。让我为您查询运费...
[调用运费查询工具]

工具调用说明：
当你收集到所有必需信息（重量、目的地、商品类型）后，系统会自动调用运费查询工具获取实时价格。你只需要：
1. 通过对话收集完整信息
2. 确认信息无误
3. 告诉用户正在查询

回复格式：
```
**运输方式**：[方式名称]
**预计时效**：[天数] 天
**预估运费**：¥XXX (约$XX)
**特点**：
- [特点1]
- [特点2]
**注意事项**：[重要提示]
```

关税提示：
- 提醒用户目的地国家可能收取进口关税
- 关税通常由收件人承担
- 建议用户了解当地免税额度
"""

    # 订单管理专用Prompt
    ORDER_PROMPT = """你正在协助用户管理代购订单。

订单流程：
1. 用户提交商品链接/信息
2. 确认商品详情和价格
3. 创建订单并生成订单号
4. 用户支付
5. 采购商品
6. 国际运输
7. 送达确认

订单状态说明：
- **待支付**：订单已创建，等待用户付款
- **已支付**：付款完成，准备采购
- **采购中**：正在购买商品
- **已到货**：商品已到达仓库
- **已发货**：已发出国际快递
- **运输中**：国际运输途中
- **已送达**：商品已送达
- **已完成**：订单完成
- **已取消**：订单已取消

回复格式：
```
**订单号**：[ORDER-XXXXXX]
**商品**：[商品名称]
**状态**：[当前状态]
**金额**：¥XXX (约$XX)
**更新时间**：[时间]
**下一步**：[操作提示]
```

注意事项：
- 提醒用户保存订单号以便查询
- 说明退款和售后政策
- 告知预计的处理时间
"""

    # 商品翻译专用Prompt
    TRANSLATION_PROMPT = """你正在帮助用户翻译和解读商品信息。

翻译原则：
1. 准确翻译商品名称和描述
2. 保留关键参数和规格
3. 解释中国特色的商品术语
4. 标注单位换算（如尺码）

商品信息结构：
- 商品名称（品牌+型号+核心功能）
- 规格参数（尺寸、重量、材质等）
- 功能特点
- 适用场景
- 注意事项

尺码对照（服装）：
- 中国S ≈ US XS
- 中国M ≈ US S
- 中国L ≈ US M
- 中国XL ≈ US L
- 中国XXL ≈ US XL

回复格式：
```
**商品名称**：
中文：[原文]
英文：[翻译]

**规格参数**：
- [参数1]：[值]
- [参数2]：[值]

**功能特点**：
- [特点1]
- [特点2]

**购买建议**：
[建议内容]
```
"""

    # 商品对比专用Prompt
    COMPARISON_PROMPT = """你正在帮助用户对比不同商品。

对比维度：
1. 价格（包含运费估算）
2. 品牌和质量
3. 功能和规格
4. 用户评价
5. 店铺信誉
6. 发货速度

对比方法：
1. 创建对比表格
2. 标注各商品的优势和劣势
3. 根据用户需求给出推荐
4. 说明推荐理由

回复格式：
```
**商品对比**：[商品A] vs [商品B]

| 维度 | 商品A | 商品B |
|------|-------|-------|
| 价格 | ¥XXX | ¥XXX |
| 品牌 | [品牌A] | [品牌B] |
| 评分 | X.X/5 | X.X/5 |
| 销量 | XXX | XXX |

**优势分析**：
- **商品A**：[优势]
- **商品B**：[优势]

**推荐**：
根据你的需求，推荐 [商品X]，理由是：
1. [理由1]
2. [理由2]
```
"""

    # 安全限制Prompt
    SAFETY_PROMPT = """安全准则（必须遵守）：

禁止内容：
1. 不要提供购买违禁品的信息或建议
2. 不要协助进行欺诈或非法交易
3. 不要泄露用户的个人信息
4. 不要提供虚假的商品信息
5. 不要推荐假冒伪劣商品

敏感商品处理：
1. **电子产品**：提醒用户注意电压和插头标准差异
2. **食品/化妆品**：提醒用户注意保质期和成分
3. **仿冒品**：明确告知用户风险，不推荐购买
4. **管制物品**：说明海关限制，建议不要购买

免责声明：
- 价格信息仅供参考，以实际购买时为准
- 物流时效为预估，实际可能因各种因素变化
- 关税政策以目的地国家海关为准
- 商品质量问题请联系卖家或平台处理

用户隐私：
- 保护用户的个人信息和订单信息
- 不将用户信息用于任何商业目的
"""

    def __init__(self):
        """初始化Prompt管理器"""
        self._templates: Dict[str, PromptTemplate] = {}
        self._register_default_templates()

    def _register_default_templates(self) -> None:
        """注册默认Prompt模板"""
        templates = [
            PromptTemplate(
                name="base_system",
                description="基础系统角色设定",
                template=self.BASE_SYSTEM_PROMPT,
                variables=[],
                type=PromptType.SYSTEM,
            ),
            PromptTemplate(
                name="shopping",
                description="商品搜索场景",
                template=self.SHOPPING_PROMPT,
                variables=[],
                type=PromptType.SHOPPING,
            ),
            PromptTemplate(
                name="logistics",
                description="物流咨询场景",
                template=self.LOGISTICS_PROMPT,
                variables=[],
                type=PromptType.LOGISTICS,
            ),
            PromptTemplate(
                name="order",
                description="订单管理场景",
                template=self.ORDER_PROMPT,
                variables=[],
                type=PromptType.ORDER,
            ),
            PromptTemplate(
                name="translation",
                description="商品翻译场景",
                template=self.TRANSLATION_PROMPT,
                variables=[],
                type=PromptType.TRANSLATION,
            ),
            PromptTemplate(
                name="comparison",
                description="商品对比场景",
                template=self.COMPARISON_PROMPT,
                variables=[],
                type=PromptType.COMPARISON,
            ),
            PromptTemplate(
                name="safety",
                description="安全限制",
                template=self.SAFETY_PROMPT,
                variables=[],
                type=PromptType.SAFETY,
            ),
        ]

        for template in templates:
            self._templates[template.name] = template

    def get_prompt(
        self,
        name: str,
        variables: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        获取Prompt模板

        Args:
            name: 模板名称
            variables: 模板变量

        Returns:
            渲染后的Prompt
        """
        template = self._templates.get(name)
        if not template:
            raise ValueError(f"未知的Prompt模板: {name}")

        prompt = template.template
        if variables:
            for key, value in variables.items():
                prompt = prompt.replace(f"{{{key}}}", value)

        return prompt

    def get_system_prompt(
        self,
        include_safety: bool = True,
        scenario: Optional[str] = None,
    ) -> str:
        """
        获取完整的系统Prompt

        Args:
            include_safety: 是否包含安全限制
            scenario: 场景类型（shopping/logistics/order等）

        Returns:
            完整的系统Prompt
        """
        prompts = [self.BASE_SYSTEM_PROMPT]

        # 添加场景特定Prompt
        if scenario and scenario in self._templates:
            prompts.append(self._templates[scenario].template)

        # 添加安全限制
        if include_safety:
            prompts.append(self.SAFETY_PROMPT)

        return "\n\n---\n\n".join(prompts)

    def get_shopping_prompt(self) -> str:
        """获取商品搜索场景Prompt"""
        return self.get_system_prompt(scenario="shopping")

    def get_logistics_prompt(self) -> str:
        """获取物流咨询场景Prompt"""
        return self.get_system_prompt(scenario="logistics")

    def get_order_prompt(self) -> str:
        """获取订单管理场景Prompt"""
        return self.get_system_prompt(scenario="order")

    def get_translation_prompt(self) -> str:
        """获取商品翻译场景Prompt"""
        return self.get_system_prompt(scenario="translation")

    def get_comparison_prompt(self) -> str:
        """获取商品对比场景Prompt"""
        return self.get_system_prompt(scenario="comparison")

    def register_template(
        self,
        name: str,
        description: str,
        template: str,
        variables: List[str],
        prompt_type: PromptType = PromptType.SYSTEM,
    ) -> None:
        """
        注册新的Prompt模板

        Args:
            name: 模板名称
            description: 模板描述
            template: 模板内容
            variables: 模板变量列表
            prompt_type: Prompt类型
        """
        self._templates[name] = PromptTemplate(
            name=name,
            description=description,
            template=template,
            variables=variables,
            type=prompt_type,
        )

    def list_templates(self, prompt_type: Optional[PromptType] = None) -> List[str]:
        """
        列出所有模板

        Args:
            prompt_type: 按类型过滤

        Returns:
            模板名称列表
        """
        if prompt_type:
            return [
                name
                for name, template in self._templates.items()
                if template.type == prompt_type
            ]
        return list(self._templates.keys())

    def get_template_info(self, name: str) -> Optional[Dict]:
        """
        获取模板信息

        Args:
            name: 模板名称

        Returns:
            模板信息字典
        """
        template = self._templates.get(name)
        if not template:
            return None

        return {
            "name": template.name,
            "description": template.description,
            "type": template.type.value,
            "variables": template.variables,
        }


# 全局Prompt管理器实例
prompt_manager = PromptManager()


# 便捷函数
def get_system_prompt(
    scenario: Optional[str] = None,
    include_safety: bool = True,
) -> str:
    """
    获取系统Prompt的便捷函数

    Args:
        scenario: 场景类型
        include_safety: 是否包含安全限制

    Returns:
        系统Prompt
    """
    return prompt_manager.get_system_prompt(
        scenario=scenario,
        include_safety=include_safety,
    )


def get_shopping_system_prompt() -> str:
    """获取商品搜索系统Prompt"""
    return prompt_manager.get_shopping_prompt()


def get_logistics_system_prompt() -> str:
    """获取物流咨询系统Prompt"""
    return prompt_manager.get_logistics_prompt()


def get_order_system_prompt() -> str:
    """获取订单管理系统Prompt"""
    return prompt_manager.get_order_prompt()
