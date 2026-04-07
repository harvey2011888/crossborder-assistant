# 跨境电商智能助手 - Dockerfile
# 使用Python 3.11+作为基础镜像

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY bot/ ./bot/
COPY models/ ./models/
COPY utils/ ./utils/
COPY alembic/ ./alembic/
COPY alembic.ini .

# 创建非root用户
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import discord; print('Discord imported successfully')" || exit 1

# 启动命令
CMD ["python", "-m", "bot.main"]
