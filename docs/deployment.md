# 部署指南

本文档描述跨境电商智能助手的部署流程。

## 部署方式

支持以下部署方式：
1. [Docker Compose部署](#docker-compose部署)（推荐）
2. [Docker部署](#docker部署)
3. [手动部署](#手动部署)

## Docker Compose部署（推荐）

### 环境要求

- Docker 20.10+
- Docker Compose 2.0+
- 2GB+ 可用内存
- 10GB+ 可用磁盘空间

### 部署步骤

1. **下载项目代码**
```bash
git clone <repository-url>
cd crossborder-assistant
```

2. **配置环境变量**
```bash
cp .env.example .env
nano .env  # 或使用其他编辑器
```

必需配置项：
```env
# Discord Bot
DISCORD_TOKEN=your_discord_bot_token

# MySQL
MYSQL_ROOT_PASSWORD=secure_root_password
MYSQL_PASSWORD=secure_bot_password

# AI API (至少配置一个)
GEMINI_API_KEY=your_gemini_api_key
```

3. **启动服务**
```bash
docker-compose up -d
```

4. **检查服务状态**
```bash
docker-compose ps
```

5. **查看日志**
```bash
# 查看Bot日志
docker-compose logs -f bot

# 查看数据库日志
docker-compose logs -f mysql
```

6. **停止服务**
```bash
docker-compose down
```

### 数据持久化

Docker Compose配置中已包含数据卷：
- `mysql_data`: MySQL数据持久化
- `./logs`: Bot日志持久化

### 更新部署

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose up -d --build

# 运行数据库迁移（如有需要）
docker-compose exec bot alembic upgrade head
```

## Docker部署

### 构建镜像

```bash
docker build -t crossborder-bot .
```

### 运行容器

```bash
# 创建网络
docker network create crossborder_network

# 运行MySQL
docker run -d \
  --name crossborder_mysql \
  --network crossborder_network \
  -e MYSQL_ROOT_PASSWORD=rootpassword \
  -e MYSQL_DATABASE=crossborder_bot \
  -e MYSQL_USER=bot_user \
  -e MYSQL_PASSWORD=bot_password \
  -v mysql_data:/var/lib/mysql \
  mysql:8.0

# 运行Bot
docker run -d \
  --name crossborder_bot \
  --network crossborder_network \
  -e DISCORD_TOKEN=your_token \
  -e MYSQL_HOST=crossborder_mysql \
  -e MYSQL_USER=bot_user \
  -e MYSQL_PASSWORD=bot_password \
  -e GEMINI_API_KEY=your_key \
  crossborder-bot
```

## 手动部署

### 环境要求

- Python 3.11+
- MySQL 8.0+
- pip
- git

### 部署步骤

1. **安装Python依赖**
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

2. **配置MySQL数据库**
```bash
# 登录MySQL
mysql -u root -p

# 创建数据库
CREATE DATABASE crossborder_bot
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

# 创建用户
CREATE USER 'bot_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON crossborder_bot.* TO 'bot_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

3. **配置环境变量**
```bash
cp .env.example .env
nano .env
```

4. **运行数据库迁移**
```bash
alembic upgrade head
```

5. **启动Bot**
```bash
python -m bot.main
```

### 使用Systemd服务（Linux）

创建服务文件 `/etc/systemd/system/crossborder-bot.service`：

```ini
[Unit]
Description=CrossBorder E-commerce Bot
After=network.target mysql.service

[Service]
Type=simple
User=botuser
WorkingDirectory=/opt/crossborder-assistant
Environment=PATH=/opt/crossborder-assistant/venv/bin
ExecStart=/opt/crossborder-assistant/venv/bin/python -m bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用并启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable crossborder-bot
sudo systemctl start crossborder-bot

# 查看状态
sudo systemctl status crossborder-bot

# 查看日志
sudo journalctl -u crossborder-bot -f
```

### 使用PM2（Node.js风格管理）

```bash
# 安装PM2
npm install -g pm2

# 创建PM2配置文件 ecosystem.config.js
module.exports = {
  apps: [{
    name: 'crossborder-bot',
    script: 'python',
    args: '-m bot.main',
    cwd: '/opt/crossborder-assistant',
    interpreter: '/opt/crossborder-assistant/venv/bin/python',
    autorestart: true,
    max_restarts: 5,
    min_uptime: '10s',
    env: {
      PYTHONUNBUFFERED: '1'
    },
    log_file: './logs/combined.log',
    out_file: './logs/out.log',
    error_file: './logs/error.log',
    time: true
  }]
};

# 启动
pm2 start ecosystem.config.js

# 保存配置
pm2 save
pm2 startup
```

## 生产环境配置

### 环境变量

```env
# Discord
DISCORD_TOKEN=your_production_token
DISCORD_GUILD_ID=your_guild_id

# MySQL（使用强密码）
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=bot_user
MYSQL_PASSWORD=strong_random_password
MYSQL_DATABASE=crossborder_bot

# AI（生产环境建议使用付费API）
GEMINI_API_KEY=your_gemini_key
DASHSCOPE_API_KEY=your_qianwen_key
OPENAI_API_KEY=your_openai_key
DEFAULT_AI_PROVIDER=gemini

# Bot配置
BOT_PREFIX=/
BOT_LANGUAGE=zh-CN
LOG_LEVEL=WARNING

# 平台API（生产环境）
PLATFORM_API_URL=https://api.your-platform.com
PLATFORM_API_KEY=your_platform_key
```

### 安全配置

1. **防火墙配置**
```bash
# 仅允许必要端口
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 3306/tcp  # MySQL（如需要远程访问）
sudo ufw enable
```

2. **MySQL安全**
```bash
# 运行安全脚本
sudo mysql_secure_installation

# 禁用远程root登录
# 在my.cnf中添加：
bind-address = 127.0.0.1
```

3. **文件权限**
```bash
# 设置正确的权限
chmod 600 .env
chmod 755 logs/
chown -R botuser:botuser /opt/crossborder-assistant
```

### 备份策略

1. **数据库备份**
```bash
# 创建备份脚本 /opt/backup/backup.sh
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
mysqldump -u root -p'your_password' crossborder_bot > \
  /opt/backup/crossborder_bot_$DATE.sql

# 保留最近7天备份
find /opt/backup -name "crossborder_bot_*.sql" -mtime +7 -delete
```

2. **定时任务**
```bash
# 编辑crontab
crontab -e

# 每天凌晨2点备份
0 2 * * * /opt/backup/backup.sh
```

### 监控

1. **日志监控**
```bash
# 使用logrotate管理日志
# /etc/logrotate.d/crossborder-bot
/opt/crossborder-assistant/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 botuser botuser
}
```

2. **健康检查**
```bash
# 创建健康检查脚本
#!/bin/bash
if ! pgrep -f "python -m bot.main" > /dev/null; then
    echo "Bot is not running!" | mail -s "Bot Alert" admin@example.com
    systemctl restart crossborder-bot
fi
```

## 云平台部署

### 部署到Railway

1. 在Railway创建新项目
2. 连接GitHub仓库
3. 添加环境变量
4. 部署

### 部署到Heroku

```bash
# 登录Heroku
heroku login

# 创建应用
heroku create your-bot-name

# 添加MySQL插件
heroku addons:create jawsdb:kitefin

# 设置环境变量
heroku config:set DISCORD_TOKEN=your_token
heroku config:set GEMINI_API_KEY=your_key

# 部署
git push heroku main
```

### 部署到AWS ECS

```bash
# 构建镜像
docker build -t crossborder-bot .

# 推送到ECR
aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
docker tag crossborder-bot:latest <account>.dkr.ecr.<region>.amazonaws.com/crossborder-bot:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/crossborder-bot:latest

# 使用ECS控制台或CLI创建服务和任务
```

## 故障排查

### 常见问题

1. **Bot无法启动**
   - 检查DISCORD_TOKEN是否正确
   - 检查日志文件
   - 确认Python版本>=3.11

2. **数据库连接失败**
   - 检查MySQL服务是否运行
   - 验证数据库凭据
   - 检查防火墙设置

3. **AI服务无响应**
   - 验证API Key有效性
   - 检查网络连接
   - 查看API配额

4. **内存不足**
   - 增加交换空间
   - 优化代码
   - 升级服务器配置

### 调试模式

```bash
# 启用调试日志
LOG_LEVEL=DEBUG python -m bot.main
```

## 更新维护

### 版本更新

1. 备份数据
2. 拉取最新代码
3. 更新依赖
4. 运行迁移
5. 重启服务

### 数据库迁移

```bash
# 创建迁移
alembic revision --autogenerate -m "description"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

## 性能优化

1. **数据库优化**
   - 添加适当索引
   - 定期清理旧数据
   - 使用连接池

2. **Bot优化**
   - 启用缓存
   - 异步处理
   - 限制并发请求

3. **系统优化**
   - 使用SSD
   - 增加内存
   - 优化内核参数
