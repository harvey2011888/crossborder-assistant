# 跨境电商智能助手 (CrossBorder E-commerce Assistant)

一个基于Discord Bot的跨境电商智能助手，为海外用户提供中国电商平台（淘宝、京东等）的商品搜索、智能导购、物流查询等服务。

## 功能特性

### 核心功能
- **AI智能导购**: 支持自然语言商品搜索，智能推荐与比价
- **多平台集成**: 支持淘宝、京东等主流电商平台
- **多AI支持**: 集成Google Gemini、阿里千问、OpenAI GPT-4
- **订单管理**: 对接自建跨境电商平台，支持订单创建与追踪（预留接口）
- **物流服务**: 运费估算、包裹追踪、时效查询（预留接口）

### 技术特性
- **Discord Bot**: 基于 discord.py v2.3+
- **异步架构**: 使用 asyncio 和 aiohttp
- **数据库**: MySQL 8.0+ 配合 SQLAlchemy ORM
- **类型安全**: 完整的类型注解支持
- **容器化**: Docker + Docker Compose 部署

## 项目结构

```
crossborder-assistant/
├── bot/                          # Discord Bot核心
│   ├── main.py                  # 入口文件
│   ├── cogs/                    # 命令模块
│   │   ├── general.py          # 基础命令
│   │   ├── shopping.py         # 购物相关命令
│   │   ├── logistics.py        # 物流相关命令
│   │   └── orders.py           # 订单管理命令
│   ├── core/                    # 核心功能
│   │   ├── config.py           # 配置管理
│   │   ├── database.py         # 数据库连接
│   │   └── session.py          # 会话管理
│   └── services/                # 外部服务集成
│       ├── ai/                  # AI服务
│       │   ├── base.py         # AI服务基类
│       │   ├── gemini.py       # Google Gemini
│       │   ├── qianwen.py      # 阿里千问
│       │   ├── openai.py       # OpenAI GPT-4
│       │   └── factory.py      # AI服务工厂
│       ├── ecommerce/           # 电商平台API
│       │   ├── taobao.py       # 淘宝API
│       │   └── jd.py           # 京东API
│       └── platform/            # 自建平台API
│           ├── client.py       # 平台API客户端
│           ├── orders.py       # 订单API
│           └── logistics.py    # 物流API
├── models/                      # 数据模型
│   ├── user.py                 # 用户模型
│   ├── order.py                # 订单模型
│   └── session.py              # 会话模型
├── utils/                       # 工具函数
│   ├── embeds.py               # Discord Embed模板
│   └── interactions.py         # 交互优化
├── tests/                       # 测试目录
│   ├── unit/                   # 单元测试
│   └── integration/            # 集成测试
├── alembic/                     # 数据库迁移
├── Dockerfile                   # Docker镜像构建
├── docker-compose.yml          # Docker Compose配置
├── requirements.txt            # Python依赖
└── .env.example                # 环境变量示例
```

## 快速开始

### 环境要求
- Python 3.11+
- MySQL 8.0+
- Discord Bot Token
- AI API Key (Gemini / 阿里千问 / OpenAI)

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd crossborder-assistant
```

2. **创建虚拟环境**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，填写必要的配置
```

5. **初始化数据库**
```bash
# 创建数据库
mysql -u root -p -e "CREATE DATABASE crossborder_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 运行迁移
alembic upgrade head
```

6. **启动Bot**
```bash
python -m bot.main
```

## Docker部署

### 使用Docker Compose（推荐）

1. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件
```

2. **启动服务**
```bash
docker-compose up -d
```

这将启动：
- MySQL数据库服务
- Discord Bot服务

3. **查看日志**
```bash
docker-compose logs -f bot
```

4. **停止服务**
```bash
docker-compose down
```

### 使用Docker Compose with Redis（可选）
```bash
docker-compose --profile with-redis up -d
```

## 命令列表

### 基础命令
- `/help` - 显示帮助信息
- `/start` - 开始使用引导
- `/settings` - 用户设置
- `/ai_switch` - 切换AI提供商

### 购物命令
- `/search <关键词>` - 搜索商品
- `/recommend` - 智能推荐
- `/compare <商品1> <商品2>` - 商品对比
- `/translate <商品信息>` - 商品信息翻译

### 物流命令（预留）
- `/shipping <重量> <目的地>` - 运费估算
- `/track <运单号>` - 包裹追踪
- `/estimate <商品信息>` - 物流时效预估

### 订单命令（预留）
- `/order create <链接>` - 创建订单
- `/order list` - 订单列表
- `/order status <订单号>` - 查询状态
- `/order cancel <订单号>` - 取消订单

## 环境变量配置

### 必需配置
```env
# Discord Bot
DISCORD_TOKEN=your_discord_bot_token

# MySQL Database
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=bot_user
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=crossborder_bot

# AI API Keys (至少配置一个)
GEMINI_API_KEY=your_gemini_api_key
DASHSCOPE_API_KEY=your_qianwen_api_key
OPENAI_API_KEY=your_openai_api_key
```

### 可选配置
```env
# 默认AI提供商 (gemini/qianwen/openai)
DEFAULT_AI_PROVIDER=gemini

# 平台API（待接口文档）
PLATFORM_API_URL=https://your-platform.com/api
PLATFORM_API_KEY=your_platform_api_key

# 淘宝/京东API
TAOBAO_APP_KEY=your_taobao_app_key
TAOBAO_APP_SECRET=your_taobao_app_secret
JD_APP_KEY=your_jd_app_key
JD_APP_SECRET=your_jd_app_secret

# Bot配置
BOT_PREFIX=/
BOT_LANGUAGE=zh-CN
LOG_LEVEL=INFO
```

## 测试

### 运行单元测试
```bash
pytest -m unit
```

### 运行集成测试
```bash
pytest -m integration
```

### 运行所有测试
```bash
pytest
```

### 生成测试覆盖率报告
```bash
pytest --cov=bot --cov=models --cov=utils --cov-report=html
```

## 开发指南

### 代码规范
- 使用 black 进行代码格式化
- 使用 isort 进行导入排序
- 使用 flake8 进行代码检查
- 所有函数必须添加类型注解
- 使用中文注释和docstring

### 格式化代码
```bash
# 格式化Python代码
black bot/ models/ utils/ tests/

# 排序导入
isort bot/ models/ utils/ tests/

# 代码检查
flake8 bot/ models/ utils/ tests/
```

### 添加新命令

1. 在 `bot/cogs/` 目录下创建或编辑Cog文件
2. 继承 `commands.Cog` 类
3. 使用 `@commands.command()` 或 `@app_commands.command()` 装饰器
4. 在 `bot/main.py` 中加载Cog

示例：
```python
from discord.ext import commands
import discord

class MyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="mycommand", description="命令描述")
    async def my_command(self, interaction: discord.Interaction):
        await interaction.response.send_message("Hello!")

async def setup(bot: commands.Bot):
    await bot.add_cog(MyCog(bot))
```

## API文档

### AI服务API

详见 [docs/api/ai-services.md](docs/api/ai-services.md)

### 电商平台API

详见 [docs/api/ecommerce.md](docs/api/ecommerce.md)

### 自建平台API

详见 [docs/api/platform.md](docs/api/platform.md)

## 常见问题

### Q: 如何获取Discord Bot Token？
A: 访问 [Discord Developer Portal](https://discord.com/developers/applications)，创建应用并添加Bot，复制Token。

### Q: 如何获取AI API Key？
A:
- **Google Gemini**: 访问 [Google AI Studio](https://makersuite.google.com/app/apikey)
- **阿里千问**: 访问 [阿里云DashScope](https://dashscope.console.aliyun.com/apiKey)
- **OpenAI**: 访问 [OpenAI Platform](https://platform.openai.com/api-keys)

### Q: 如何邀请Bot到服务器？
A: 在Discord Developer Portal中，选择你的应用 -> OAuth2 -> URL Generator，选择 `bot` 和 `applications.commands` 权限，生成URL并访问。

### Q: 数据库连接失败怎么办？
A: 检查以下几点：
1. MySQL服务是否运行
2. 环境变量配置是否正确
3. 数据库和用户是否已创建
4. 防火墙是否允许连接

## 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 联系方式

- 项目主页: [GitHub Repository](https://github.com/yourusername/crossborder-assistant)
- 问题反馈: [Issues](https://github.com/yourusername/crossborder-assistant/issues)
- 邮件: your.email@example.com

## 致谢

- [discord.py](https://github.com/Rapptz/discord.py) - Discord Bot框架
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM框架
- [Google Gemini](https://ai.google.dev/) - AI服务
- [阿里千问](https://dashscope.aliyun.com/) - AI服务
- [OpenAI](https://openai.com/) - AI服务

---

**注意**: 本项目仅供学习和研究使用，请遵守相关平台的服务条款和API使用规范。
