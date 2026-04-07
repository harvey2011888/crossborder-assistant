# AI服务API文档

本文档描述跨境电商智能助手中的AI服务API接口。

## 概述

AI服务模块提供统一的接口来集成多个AI提供商（Google Gemini、阿里千问、OpenAI GPT-4），支持智能对话、商品推荐、翻译等功能。

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Service Factory                       │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │    Gemini    │  │   Qianwen    │  │    OpenAI    │      │
│  │   Service    │  │   Service    │  │   Service    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## 基础接口

### AIProvider 枚举

```python
class AIProvider(str, Enum):
    """AI服务提供商枚举"""
    GEMINI = "gemini"      # Google Gemini
    QIANWEN = "qianwen"    # 阿里千问
    OPENAI = "openai"      # OpenAI GPT-4
```

### AIResponse 数据模型

```python
class AIResponse(BaseModel):
    """AI响应数据模型"""
    content: str                    # 响应内容
    role: MessageRole              # 消息角色
    model: Optional[str] = None    # 使用的模型
    usage: Optional[dict] = None   # Token使用统计
    raw_response: Optional[Any] = None  # 原始响应
```

## 服务类接口

### BaseAIService

所有AI服务的基类，定义统一接口。

```python
class BaseAIService(ABC):
    """AI服务基类"""

    @abstractmethod
    async def generate_response(
        self,
        prompt: str,
        **kwargs: Any
    ) -> AIResponse:
        """生成单次回复"""
        pass

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any
    ) -> AIResponse:
        """多轮对话"""
        pass
```

### GeminiService

Google Gemini API封装。

```python
class GeminiService(BaseAIService):
    """Gemini AI服务"""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-pro",
        **kwargs: Any
    ) -> None

    async def generate_response(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AIResponse

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AIResponse
```

**支持模型**:
- `gemini-pro`: 文本生成模型
- `gemini-pro-vision`: 多模态模型（支持图片）

### QianwenService

阿里千问 API封装。

```python
class QianwenService(BaseAIService):
    """阿里千问AI服务"""

    def __init__(
        self,
        api_key: str,
        model: str = "qwen-turbo",
        **kwargs: Any
    ) -> None

    async def generate_response(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AIResponse

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AIResponse
```

**支持模型**:
- `qwen-turbo`: 快速响应模型
- `qwen-plus`: 增强版模型
- `qwen-max`: 最强能力模型

### OpenAIService

OpenAI GPT-4 API封装。

```python
class OpenAIService(BaseAIService):
    """OpenAI GPT服务"""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4",
        base_url: Optional[str] = None,
        **kwargs: Any
    ) -> None

    async def generate_response(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AIResponse

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AIResponse
```

**支持模型**:
- `gpt-4`: GPT-4模型
- `gpt-4-turbo`: GPT-4 Turbo模型
- `gpt-3.5-turbo`: GPT-3.5模型

## 工厂类

### AIServiceFactory

```python
class AIServiceFactory:
    """AI服务工厂"""

    def register_service(
        self,
        provider: AIProvider,
        service_class: type[BaseAIService]
    ) -> None
    """注册AI服务"""

    def create_service(
        self,
        provider: AIProvider,
        **kwargs: Any
    ) -> BaseAIService
    """创建AI服务实例"""

    def get_available_providers(self) -> list[AIProvider]
    """获取可用提供商列表"""
```

## 使用示例

### 基础使用

```python
from bot.services.ai.factory import AIProvider, ai_service_factory

# 创建Gemini服务
service = ai_service_factory.create_service(
    AIProvider.GEMINI,
    api_key="your_api_key"
)

# 生成回复
response = await service.generate_response("你好，请介绍一下自己")
print(response.content)
```

### 多轮对话

```python
messages = [
    {"role": "user", "content": "我想买一双跑鞋"},
    {"role": "assistant", "content": "好的，请问您的预算是多少？"},
    {"role": "user", "content": "500元以内"},
]

response = await service.chat(messages)
print(response.content)
```

### 切换AI提供商

```python
# 使用阿里千问
qianwen = ai_service_factory.create_service(
    AIProvider.QIANWEN,
    api_key="your_qianwen_key",
    model="qwen-plus"
)

response = await qianwen.generate_response("你好")
```

## 对话管理

### ConversationManager

```python
class ConversationManager:
    """对话管理器"""

    def create_session(
        self,
        user_id: str,
        ttl: Optional[int] = None
    ) -> str
    """创建新会话，返回session_id"""

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str
    ) -> None
    """添加消息到会话"""

    def get_history(
        self,
        session_id: str
    ) -> list[dict[str, str]]
    """获取会话历史"""

    def clear_history(self, session_id: str) -> None
    """清空会话历史"""

    def delete_session(self, session_id: str) -> None
    """删除会话"""
```

### 使用示例

```python
from bot.services.ai.conversation import ConversationManager

manager = ConversationManager()

# 创建会话
session_id = manager.create_session("user123")

# 添加消息
manager.add_message(session_id, "user", "我想买一部手机")
manager.add_message(session_id, "assistant", "好的，请问您的预算是多少？")

# 获取历史
history = manager.get_history(session_id)

# 使用历史进行对话
response = await service.chat(history)
```

## 系统Prompt

### 预定义Prompt

```python
from bot.services.ai.prompts import SYSTEM_PROMPTS

# 获取商品搜索Prompt
product_search_prompt = SYSTEM_PROMPTS["product_search"]

# 获取物流咨询Prompt
logistics_prompt = SYSTEM_PROMPTS["logistics_assistant"]
```

### 自定义Prompt

```python
from bot.services.ai.prompts import PromptTemplate

# 创建Prompt模板
template = PromptTemplate(
    name="custom_assistant",
    template="""你是一个专业的{role}。
    用户需求：{user_input}
    请提供专业的建议。""",
    variables=["role", "user_input"]
)

# 渲染Prompt
prompt = template.render(role="购物顾问", user_input="我想买手机")
```

## 错误处理

```python
from bot.services.ai.base import AIServiceError

try:
    response = await service.generate_response("你好")
except AIServiceError as e:
    print(f"AI服务错误: {e}")
except Exception as e:
    print(f"未知错误: {e}")
```

## 配置参数

### 环境变量

```env
# AI API Keys
GEMINI_API_KEY=your_gemini_api_key
DASHSCOPE_API_KEY=your_qianwen_api_key
OPENAI_API_KEY=your_openai_api_key

# 默认AI提供商
DEFAULT_AI_PROVIDER=gemini

# 可选：自定义OpenAI基础URL（用于代理）
OPENAI_BASE_URL=https://api.openai.com/v1
```

### 默认参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| temperature | 0.7 | 创造性程度（0-2） |
| max_tokens | 2048 | 最大生成token数 |
| top_p | 0.95 | 核采样概率 |
| top_k | 40 | 最高概率采样 |

## 性能优化

### 连接池

```python
# 使用连接池管理多个AI服务
services = {
    provider: ai_service_factory.create_service(provider)
    for provider in AIProvider
}
```

### 缓存

```python
from functools import lru_cache

@lru_cache(maxsize=100)
async def cached_generate(prompt: str) -> str:
    response = await service.generate_response(prompt)
    return response.content
```

## 监控指标

### Token使用统计

```python
response = await service.generate_response("你好")
print(f"输入Token: {response.usage['prompt_tokens']}")
print(f"输出Token: {response.usage['completion_tokens']}")
print(f"总Token: {response.usage['total_tokens']}")
```

### 响应时间监控

```python
import time

start = time.time()
response = await service.generate_response("你好")
latency = time.time() - start
print(f"响应时间: {latency:.2f}s")
```

## 最佳实践

1. **错误处理**: 始终使用try-except捕获AI服务异常
2. **超时设置**: 设置合理的请求超时时间（建议30-60秒）
3. **重试机制**: 对网络错误实现指数退避重试
4. **Token限制**: 监控Token使用量，避免超出配额
5. **上下文管理**: 合理控制对话历史长度，避免超出模型限制
