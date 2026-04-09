"""
测试脚本：列出 Google Gemini 所有可用模型
"""
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, "d:\\buy\\hobi\\crossborder-assistant")

import google.generativeai as genai
from bot.core.config import config

# 配置 API Key
genai.configure(api_key=config.ai.gemini_api_key)

print("正在获取可用模型列表...\n")

try:
    models = list(genai.list_models())
    print(f"找到 {len(models)} 个模型:\n")

    for model in models:
        print(f"模型名称: {model.name}")
        print(f"显示名称: {model.display_name}")
        print(f"描述: {model.description}")
        print(f"支持的方法: {model.supported_generation_methods}")
        print(f"输入限制: {model.input_token_limit} tokens")
        print(f"输出限制: {model.output_token_limit} tokens")
        print("-" * 50)
except Exception as e:
    print(f"获取模型列表失败: {e}")
