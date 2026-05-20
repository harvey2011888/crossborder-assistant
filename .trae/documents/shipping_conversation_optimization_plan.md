# 运费测算对话逻辑优化计划

## 1. 当前系统分析

### 1.1 运费测算完整调用链路

```
用户对话 → bot/main.py 
    → shipping_conversation_manager.update_state_from_input() [收集参数]
    → shipping_conversation_manager.query_shipping_rate() [第311行]
        → logistics_service.estimate_shipping_rate() [shipping_conversation.py:197]
            → shipping_client.calculate_postage() [logistics.py:208]
                → POST /express/pub/postage [shipping_api.py:222]
```

### 1.2 商品类型获取链路

```
category_type_manager.initialize() [category_types.py:88]
    → _fetch_from_api() [category_types.py:123]
        → POST /express/pub/types [category_types.py:144]
```

### 1.3 /shipping 命令参数

* **必需参数**: `weight` (重量), `destination` (目的地国家)

* **可选参数**: `category_type` (商品类型), `length/width/height` (尺寸，默认10cm)

* **实现位置**: `bot/cogs/logistics.py` 第92-301行

### 1.4 当前对话式运费测算问题

**实现位置**: `bot/services/shipping_conversation.py` 和 `bot/main.py` 第280-351行

**当前流程**:

1. 用户表达运费查询意图 → AI识别并设置 `in_shipping_flow=true`
2. 从消息中提取参数 → `update_state_from_input()`
3. 检查缺失参数 → `get_missing_params()`
4. 参数齐全后调用 → `query_shipping_rate()`

**存在的问题**:

1. **参数提取不够智能**: 重量、国家、商品类型的提取依赖简单正则/关键词匹配
2. **对话流程不够流畅**: 用户无法方便地修改已提供的参数
3. **缺少参数确认环节**: 直接执行查询，没有给用户确认的机会
4. **尺寸信息引导不够友好**: 用户不知道该如何提供尺寸
5. **商品类型匹配过于简单**: 仅依赖静态关键词映射

## 2. 优化目标

### 2.1 提升参数提取准确率

* 重量提取：支持更多表达方式（如"一斤半"、"两公斤左右"）

* 国家识别：支持模糊匹配和常见错误纠正（如"米国"->"美国"）

* 商品类型：智能匹配，支持描述性输入

### 2.2 优化对话流程体验

* 支持用户随时修改已提供的参数

* 添加参数确认机制

* 提供更友好的提示和引导

### 2.3 增强尺寸信息引导

* 提供常见尺寸参考

* 支持跳过尺寸（使用默认值）

## 3. 具体优化方案

### 3.1 优化重量提取逻辑

**文件**: `bot/services/ai/tools.py` 第149-174行

**当前实现**:

```python
def extract_weight(self, text: str) -> Optional[int]:
    patterns = [
        (r'(\d+\.?\d*)\s*[kK][gG](?![a-zA-Z])', 1000),
        (r'(\d+\.?\d*)\s*公斤', 1000),
        (r'(\d+\.?\d*)\s*斤', 500),
        (r'(\d+\.?\d*)\s*[gG](?![a-zA-Z])', 1),
        (r'(\d+\.?\d*)\s*克', 1),
    ]
```

**改进内容**:

1. 添加中文数字支持（"一斤半"、"两公斤"）
2. 添加模糊表达支持（"左右"、"大概"、"差不多"）
3. 添加范围提取（"500-1000g"）

### 3.2 优化国家识别逻辑

**文件**: `bot/services/ai/tools.py` 第176-193行

**当前实现**:

```python
def extract_country(self, text: str) -> Optional[str]:
    text_lower = text.lower()
    for name, code in COUNTRY_NAME_TO_CODE.items():
        if name.lower() in text_lower:
            return code
```

**改进内容**:

1. 扩展 `COUNTRY_NAME_TO_CODE` 映射表，添加别名（"米国"、"漂亮国"、"灯塔国"->"美国"）
2. 添加拼音匹配（"meiguo"->"美国"）
3. 添加模糊匹配评分

### 3.3 优化商品类型匹配

**文件**: `bot/services/ai/tools.py` 第195-244行

**当前实现**: 使用静态 `CATEGORY_KEYWORDS` 和 `SUBTYPE_KEYWORDS` 映射

**改进内容**:

1. 从 `category_type_manager` 动态获取类型信息构建关键词映射
2. 添加描述性匹配（"带电池的手机"->"电子产品-含电"）
3. 支持多级匹配（先匹配大类，再匹配子类）

### 3.4 优化对话状态管理

**文件**: `bot/services/shipping_conversation.py` 和 `bot/main.py`

**当前实现**:

* `update_state_from_input()`: 只更新缺失的参数

* 没有参数修改支持

**改进内容**:

1. 添加参数修改检测（用户可以说"重量改成1kg"）
2. 添加参数确认步骤（收集完所有参数后让用户确认）
3. 优化 `get_prompt_message()` 显示已收集参数的摘要

### 3.5 添加尺寸信息引导

**文件**: `bot/services/shipping_conversation.py`

**改进内容**:

1. 在 `should_ask_dimensions()` 后添加友好的尺寸询问
2. 提供常见尺寸参考（"手机大小"、"鞋盒大小"）
3. 支持跳过尺寸（使用默认值）

## 4. 实施步骤

### 步骤1: 优化重量提取 (优先级: P0)

* 修改 `bot/services/ai/tools.py` 中的 `extract_weight` 方法

* 添加中文数字转换函数

* 添加模糊匹配支持

### 步骤2: 优化国家识别 (优先级: P0)

* 修改 `bot/services/ai/tools.py` 中的 `extract_country` 方法

* 扩展 `COUNTRY_NAME_TO_CODE` 映射表

* 添加模糊匹配逻辑

### 步骤3: 优化商品类型匹配 (优先级: P0)

* 修改 `bot/services/ai/tools.py` 中的 `extract_category_type` 方法

* 从 `category_type_manager` 动态获取类型信息

* 添加智能匹配算法

### 步骤4: 优化对话状态管理 (优先级: P1)

* 修改 `bot/services/shipping_conversation.py`

* 添加参数修改检测逻辑

* 添加参数确认步骤

* 优化提示消息生成

### 步骤5: 添加尺寸引导 (优先级: P1)

* 修改 `bot/services/shipping_conversation.py`

* 添加尺寸询问逻辑

* 添加常见尺寸参考

## 5. 关键代码验证点

### 5.1 商品类型API调用验证

* **位置**: `category_types.py` 第144行

* **接口**: `POST /express/pub/types`

* **验证**: 确保API返回的数据正确解析并缓存

### 5.2 运费测算API调用验证

* **位置**: `shipping_api.py` 第222行

* **接口**: `POST /express/pub/postage`

* **参数**: country, weight, length, width, height, categoryTypes

* **验证**: 确保所有参数正确传递，特别是 `categoryTypes` 从商品类型API获取的ID

## 6. 测试计划

### 6.1 单元测试

* 测试各种重量表达方式

* 测试国家名称变体

* 测试商品类型描述

### 6.2 集成测试

* 测试完整对话流程

* 测试参数修改场景

* 测试错误处理

### 6.3 用户场景测试

* 场景1: 用户一次性提供所有信息

* 场景2: 用户逐步提供信息

* 场景3: 用户修改已提供的信息

* 场景4: 用户提供模糊/错误信息

## 7. 相关文件

* `bot/services/ai/tools.py` - AI工具函数（参数提取）

* `bot/services/shipping_conversation.py` - 对话管理

* `bot/services/platform/category_types.py` - 商品类型API

* `bot/services/platform/shipping_api.py` - 运费测算API

* `bot/services/platform/logistics.py` - 物流服务封装

* `bot/cogs/logistics.py` - /shipping命令

* `bot/main.py` - 对话处理主逻辑（第280-351行）

