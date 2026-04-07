"""
Alembic 迁移环境配置

配置SQLAlchemy和Alembic以支持异步数据库操作
"""

import asyncio
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import AsyncEngine

from alembic import context

# 添加项目根目录到路径
sys.path.insert(0, "d:\\buy\\hobi\\crossborder-assistant")

from bot.core.config import config as app_config  # noqa: E402
from bot.core.database import Base  # noqa: E402
from models.order import Order  # noqa: E402, F401
from models.session import Session  # noqa: E402, F401
from models.user import User  # noqa: E402, F401

# this is the Alembic Config object
config = context.config

# 从应用配置读取数据库URL
db_url = app_config.database.url
config.set_main_option("sqlalchemy.url", db_url)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    离线模式运行迁移

    使用URL而不是Engine执行迁移
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """
    执行迁移操作

    Args:
        connection: 数据库连接
    """
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    在线模式运行迁移

    创建Engine并关联连接，然后执行迁移
    """
    # 创建同步引擎用于迁移
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
