"""
数据库连接管理模块

负责SQLAlchemy引擎、会话和连接池的管理
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from bot.core.config import config

logger = logging.getLogger(__name__)

# 创建声明式基类
Base = declarative_base()

# 全局引擎和会话工厂
_engine = None
_async_session_maker = None


def get_engine():
    """
    获取或创建SQLAlchemy异步引擎

    Returns:
        异步引擎实例
    """
    global _engine
    if _engine is None:
        # 将pymysql URL转换为aiomysql URL
        db_url = config.database.url.replace(
            "mysql+pymysql://", "mysql+aiomysql://"
        )

        _engine = create_async_engine(
            db_url,
            echo=config.bot.log_level == "DEBUG",
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        logger.info("数据库引擎已创建")
    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """
    获取异步会话工厂

    Returns:
        异步会话工厂
    """
    global _async_session_maker
    if _async_session_maker is None:
        engine = get_engine()
        _async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _async_session_maker


async def init_database() -> None:
    """
    初始化数据库

    创建所有定义的表结构
    """
    engine = get_engine()

    try:
        # 导入所有模型以确保它们被注册到Base
        from models.user import User  # noqa: F401
        from models.order import Order  # noqa: F401
        from models.session import Session  # noqa: F401
        from models.user import User  # noqa: F401

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("数据库表结构初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


async def close_database() -> None:
    """
    关闭数据库连接

    清理所有连接池资源
    """
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None
        logger.info("数据库连接已关闭")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话的异步生成器

    用于依赖注入，确保会话正确关闭

    Yields:
        AsyncSession: 异步数据库会话
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_session() -> AsyncSession:
    """
    直接获取数据库会话

    Returns:
        AsyncSession: 异步数据库会话
    """
    session_maker = get_session_maker()
    return session_maker()
