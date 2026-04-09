"""
AI服务工厂模块

实现AI服务提供商的工厂模式，支持通过配置动态切换AI服务
"""

import logging
from typing import Dict, Optional, Type

from bot.core.config import config
from bot.services.ai.base import AIProvider, BaseAIService

# 延迟导入具体服务实现
def _import_gemini():
    from bot.services.ai.gemini import GeminiService
    return GeminiService

def _import_qianwen():
    from bot.services.ai.qianwen import QianwenService
    return QianwenService

def _import_openai():
    from bot.services.ai.openai import OpenAIService
    return OpenAIService

# 配置日志
logger = logging.getLogger(__name__)


class AIServiceFactory:
    """
    AI服务工厂类

    负责创建和管理AI服务实例，支持多种AI提供商的动态切换
    """

    # 服务注册表（使用延迟导入函数）
    _services: Dict[str, callable] = {
        AIProvider.GEMINI.value: _import_gemini,
        AIProvider.QIANWEN.value: _import_qianwen,
        AIProvider.OPENAI.value: _import_openai,
    }

    # 服务实例缓存
    _instances: Dict[str, BaseAIService] = {}

    @classmethod
    def create_service(
        cls,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs,
    ) -> BaseAIService:
        """
        创建AI服务实例

        Args:
            provider: AI提供商名称 (gemini/qianwen/openai)
            api_key: API密钥（如果为None则从配置读取）
            model: 模型名称
            **kwargs: 其他参数

        Returns:
            AI服务实例

        Raises:
            ValueError: 当提供商不支持时
            RuntimeError: 当API密钥未配置时
        """
        # 使用默认提供商
        provider = provider or config.ai.default_provider
        provider = provider.lower()

        # 验证提供商
        if provider not in cls._services:
            raise ValueError(
                f"不支持的AI提供商: {provider}. "
                f"支持的提供商: {list(cls._services.keys())}"
            )

        # 获取API密钥
        if api_key is None:
            api_key = cls._get_api_key(provider)

        if not api_key:
            raise RuntimeError(
                f"未配置 {provider} 的API密钥，请在环境变量中设置相应的API密钥"
            )

        # 创建服务实例
        import_func = cls._services[provider]

        try:
            # 延迟导入服务类
            service_class = import_func()
            service = service_class(api_key=api_key, model=model, **kwargs)
            logger.info(f"成功创建 {provider} 服务实例，使用模型: {service.model}")
            return service
        except Exception as e:
            logger.error(f"创建 {provider} 服务实例失败: {e}")
            raise RuntimeError(f"创建AI服务失败: {e}")

    @classmethod
    def get_service(
        cls,
        provider: Optional[str] = None,
        cache: bool = True,
        **kwargs,
    ) -> BaseAIService:
        """
        获取AI服务实例（带缓存）

        Args:
            provider: AI提供商名称
            cache: 是否使用缓存
            **kwargs: 创建服务时的其他参数

        Returns:
            AI服务实例
        """
        provider = provider or config.ai.default_provider
        provider = provider.lower()

        # 检查缓存
        cache_key = f"{provider}:{kwargs.get('model', 'default')}"
        if cache and cache_key in cls._instances:
            logger.debug(f"从缓存获取 {provider} 服务实例")
            return cls._instances[cache_key]

        # 创建新实例
        service = cls.create_service(provider=provider, **kwargs)

        # 缓存实例
        if cache:
            cls._instances[cache_key] = service

        return service

    @classmethod
    def _get_api_key(cls, provider: str) -> Optional[str]:
        """
        根据提供商获取对应的API密钥

        Args:
            provider: AI提供商名称

        Returns:
            API密钥或None
        """
        key_map = {
            AIProvider.GEMINI.value: config.ai.gemini_api_key,
            AIProvider.QIANWEN.value: config.ai.dashscope_api_key,
            AIProvider.OPENAI.value: config.ai.openai_api_key,
        }
        return key_map.get(provider)

    @classmethod
    def register_service(
        cls,
        provider: str,
        service_class: Type[BaseAIService],
    ) -> None:
        """
        注册新的AI服务

        Args:
            provider: 提供商名称
            service_class: 服务类
        """
        cls._services[provider.lower()] = service_class
        logger.info(f"注册新的AI服务: {provider}")

    @classmethod
    def unregister_service(cls, provider: str) -> None:
        """
        注销AI服务

        Args:
            provider: 提供商名称
        """
        provider = provider.lower()
        if provider in cls._services:
            del cls._services[provider]
            # 清除缓存
            keys_to_remove = [
                k for k in cls._instances.keys() if k.startswith(f"{provider}:")
            ]
            for key in keys_to_remove:
                del cls._instances[key]
            logger.info(f"注销AI服务: {provider}")

    @classmethod
    def get_available_providers(cls) -> list:
        """
        获取所有可用的AI提供商

        Returns:
            提供商名称列表
        """
        available = []
        for provider in cls._services.keys():
            if cls._get_api_key(provider):
                available.append(provider)
        return available

    @classmethod
    def get_provider_status(cls) -> Dict[str, Dict]:
        """
        获取所有提供商的状态

        Returns:
            提供商状态字典
        """
        status = {}
        for provider in cls._services.keys():
            api_key = cls._get_api_key(provider)
            status[provider] = {
                "configured": bool(api_key),
                "cached": any(
                    k.startswith(f"{provider}:") for k in cls._instances.keys()
                ),
            }
        return status

    @classmethod
    def clear_cache(cls, provider: Optional[str] = None) -> None:
        """
        清除服务实例缓存

        Args:
            provider: 指定提供商（为None则清除所有）
        """
        if provider:
            keys_to_remove = [
                k for k in cls._instances.keys() if k.startswith(f"{provider}:")
            ]
            for key in keys_to_remove:
                del cls._instances[key]
            logger.info(f"清除 {provider} 服务缓存")
        else:
            cls._instances.clear()
            logger.info("清除所有AI服务缓存")

    @classmethod
    def get_default_service(cls, **kwargs) -> BaseAIService:
        """
        获取默认的AI服务实例

        Args:
            **kwargs: 创建服务时的其他参数

        Returns:
            AI服务实例
        """
        return cls.get_service(provider=config.ai.default_provider, **kwargs)


# 便捷函数
def get_ai_service(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs,
) -> BaseAIService:
    """
    获取AI服务的便捷函数

    Args:
        provider: AI提供商名称
        model: 模型名称
        **kwargs: 其他参数

    Returns:
        AI服务实例

    Example:
        >>> service = get_ai_service(provider="gemini", model="gemini-pro")
        >>> response = await service.chat(messages=[...])
    """
    return AIServiceFactory.get_service(provider=provider, model=model, **kwargs)


def get_default_ai_service(**kwargs) -> BaseAIService:
    """
    获取默认AI服务的便捷函数

    Returns:
        默认AI服务实例
    """
    return AIServiceFactory.get_default_service(**kwargs)


async def validate_ai_provider(provider: str) -> bool:
    """
    验证AI提供商配置是否有效

    Args:
        provider: 提供商名称

    Returns:
        配置是否有效
    """
    try:
        service = AIServiceFactory.create_service(provider=provider, cache=False)
        return await service.validate_api_key()
    except Exception as e:
        logger.error(f"验证 {provider} 配置失败: {e}")
        return False


async def get_available_services() -> Dict[str, bool]:
    """
    获取所有可用服务的状态

    Returns:
        服务名称到可用状态的映射
    """
    results = {}
    for provider in AIServiceFactory._services.keys():
        results[provider] = await validate_ai_provider(provider)
    return results
