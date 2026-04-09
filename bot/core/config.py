"""
配置管理模块

负责加载和管理所有环境变量及配置项
"""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


@dataclass
class DatabaseConfig:
    """数据库配置类"""

    host: str
    port: int
    user: str
    password: str
    database: str

    @property
    def url(self) -> str:
        """生成SQLAlchemy数据库URL"""
        return (
            f"mysql+pymysql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )


@dataclass
class AIConfig:
    """AI服务配置类"""

    gemini_api_key: Optional[str]
    dashscope_api_key: Optional[str]
    openai_api_key: Optional[str]
    default_provider: str = "gemini"


@dataclass
class PlatformConfig:
    """自建平台API配置类"""

    api_url: Optional[str]
    api_key: Optional[str]


@dataclass
class ShippingConfig:
    """运费测算API配置类"""

    api_url: Optional[str]
    api_key: Optional[str]


@dataclass
class TaobaoConfig:
    """淘宝API配置类"""

    app_key: Optional[str]
    app_secret: Optional[str]
    api_url: Optional[str]


@dataclass
class JDConfig:
    """京东API配置类"""

    app_key: Optional[str]
    app_secret: Optional[str]
    api_url: Optional[str]


@dataclass
class BotConfig:
    """Bot配置类"""

    token: str
    guild_id: Optional[int]
    prefix: str = "/"
    language: str = "zh-CN"
    log_level: str = "INFO"


class Config:
    """全局配置管理类"""

    def __init__(self) -> None:
        """初始化所有配置"""
        self.bot = self._load_bot_config()
        self.database = self._load_database_config()
        self.ai = self._load_ai_config()
        self.platform = self._load_platform_config()
        self.shipping = self._load_shipping_config()
        self.taobao = self._load_taobao_config()
        self.jd = self._load_jd_config()

    def _load_bot_config(self) -> BotConfig:
        """加载Discord Bot配置"""
        token = os.getenv("DISCORD_TOKEN", "")
        if not token:
            raise ValueError("DISCORD_TOKEN 环境变量未设置")

        guild_id_str = os.getenv("DISCORD_GUILD_ID", "")
        guild_id = int(guild_id_str) if guild_id_str else None

        return BotConfig(
            token=token,
            guild_id=guild_id,
            prefix=os.getenv("BOT_PREFIX", "/"),
            language=os.getenv("BOT_LANGUAGE", "zh-CN"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )

    def _load_database_config(self) -> DatabaseConfig:
        """加载数据库配置"""
        return DatabaseConfig(
            host=os.getenv("MYSQL_HOST", "localhost"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", "bot_user"),
            password=os.getenv("MYSQL_PASSWORD", ""),
            database=os.getenv("MYSQL_DATABASE", "crossborder_bot"),
        )

    def _load_ai_config(self) -> AIConfig:
        """加载AI服务配置"""
        return AIConfig(
            gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY") or None,
            openai_api_key=os.getenv("OPENAI_API_KEY") or None,
            default_provider=os.getenv("DEFAULT_AI_PROVIDER", "gemini"),
        )

    def _load_platform_config(self) -> PlatformConfig:
        """加载自建平台配置"""
        return PlatformConfig(
            api_url=os.getenv("PLATFORM_API_URL") or None,
            api_key=os.getenv("PLATFORM_API_KEY") or None,
        )

    def _load_shipping_config(self) -> ShippingConfig:
        """加载运费测算API配置"""
        return ShippingConfig(
            api_url=os.getenv("SHIPPING_API_URL") or "https://express-api-727446398583.us-central1.run.app",
            api_key=os.getenv("SHIPPING_API_KEY") or None,
        )

    def _load_taobao_config(self) -> TaobaoConfig:
        """加载淘宝API配置"""
        return TaobaoConfig(
            app_key=os.getenv("TAOBAO_APP_KEY") or None,
            app_secret=os.getenv("TAOBAO_APP_SECRET") or None,
            api_url=os.getenv("TAOBAO_API_URL") or None,
        )

    def _load_jd_config(self) -> JDConfig:
        """加载京东API配置"""
        return JDConfig(
            app_key=os.getenv("JD_APP_KEY") or None,
            app_secret=os.getenv("JD_APP_SECRET") or None,
            api_url=os.getenv("JD_API_URL") or None,
        )


# 全局配置实例
config = Config()
