"""
测试脚本：测试阿里千问 API
"""
import sys
sys.path.insert(0, "d:\\buy\\hobi\\crossborder-assistant")

import dashscope
from bot.core.config import config

# 配置 API Key
dashscope.api_key = config.ai.dashscope_api_key

print(f"API Key: {config.ai.dashscope_api_key[:10]}...")
print("正在测试千问 API...\n")

try:
    from dashscope import Generation

    response = Generation.call(
        model="qwen-turbo",
        messages=[{"role": "user", "content": "你好，请介绍一下自己"}],
        temperature=0.7,
        result_format="message",
    )

    print(f"状态码: {response.status_code}")
    print(f"响应消息: {response.message}")

    if response.status_code == 200:
        print(f"\nAI回复: {response.output.choices[0].message.content}")
    else:
        print(f"\n请求失败: {response}")

except Exception as e:
    print(f"测试失败: {e}")
    import traceback
    traceback.print_exc()
