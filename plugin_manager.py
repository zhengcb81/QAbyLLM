#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件管理器
支持动态加载和管理LLM提供商插件
"""

import importlib
import inspect
import pkgutil
from typing import Dict, List, Any, Optional, Type
from pathlib import Path
import logging
from llm_providers import BaseLLMProvider, LLMProviderType

logger = logging.getLogger(__name__)

class Plugin:
    """插件基类"""
    
    def __init__(self, name: str, version: str, description: str = ""):
        self.name = name
        self.version = version
        self.description = description
        self.enabled = True
    
    def enable(self):
        """启用插件"""
        self.enabled = True
    
    def disable(self):
        """禁用插件"""
        self.enabled = False
    
    def get_info(self) -> Dict[str, Any]:
        """获取插件信息"""
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'enabled': self.enabled
        }

class LLMProviderPlugin(Plugin):
    """LLM提供商插件"""
    
    def __init__(self, 
                 name: str, 
                 version: str, 
                 provider_class: Type[BaseLLMProvider],
                 provider_type: LLMProviderType,
                 description: str = ""):
        super().__init__(name, version, description)
        self.provider_class = provider_class
        self.provider_type = provider_type
    
    def create_instance(self, config: Dict[str, Any]) -> BaseLLMProvider:
        """创建提供商实例"""
        return self.provider_class(config)
    
    def get_info(self) -> Dict[str, Any]:
        """获取插件信息"""
        info = super().get_info()
        info.update({
            'provider_type': self.provider_type.value,
            'class_name': self.provider_class.__name__
        })
        return info

class PluginManager:
    """插件管理器"""
    
    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}
        self.llm_providers: Dict[LLMProviderType, LLMProviderPlugin] = {}
    
    def register_plugin(self, plugin: Plugin) -> bool:
        """注册插件"""
        if plugin.name in self.plugins:
            logger.warning(f"插件已存在: {plugin.name}")
            return False
        
        self.plugins[plugin.name] = plugin
        
        # 如果是LLM提供商插件，单独注册
        if isinstance(plugin, LLMProviderPlugin):
            self.llm_providers[plugin.provider_type] = plugin
        
        logger.info(f"注册插件: {plugin.name} v{plugin.version}")
        return True
    
    def unregister_plugin(self, plugin_name: str) -> bool:
        """注销插件"""
        if plugin_name not in self.plugins:
            return False
        
        plugin = self.plugins[plugin_name]
        
        # 如果是LLM提供商插件，从提供商列表中移除
        if isinstance(plugin, LLMProviderPlugin):
            del self.llm_providers[plugin.provider_type]
        
        del self.plugins[plugin_name]
        logger.info(f"注销插件: {plugin_name}")
        return True
    
    def get_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """获取插件"""
        return self.plugins.get(plugin_name)
    
    def get_all_plugins(self) -> List[Dict[str, Any]]:
        """获取所有插件信息"""
        return [plugin.get_info() for plugin in self.plugins.values()]
    
    def get_llm_provider_plugin(self, provider_type: LLMProviderType) -> Optional[LLMProviderPlugin]:
        """获取LLM提供商插件"""
        return self.llm_providers.get(provider_type)
    
    def get_available_llm_providers(self) -> List[str]:
        """获取可用的LLM提供商类型"""
        return [provider_type.value for provider_type in self.llm_providers.keys()]
    
    def create_llm_provider(self, 
                          provider_type: LLMProviderType, 
                          config: Dict[str, Any]) -> Optional[BaseLLMProvider]:
        """创建LLM提供商实例"""
        plugin = self.get_llm_provider_plugin(provider_type)
        if not plugin or not plugin.enabled:
            return None
        
        return plugin.create_instance(config)
    
    def load_plugins_from_module(self, module_name: str) -> int:
        """从模块加载插件"""
        try:
            module = importlib.import_module(module_name)
            return self._discover_plugins_in_module(module)
        except ImportError as e:
            logger.error(f"加载模块失败: {module_name}, 错误: {e}")
            return 0
    
    def load_plugins_from_package(self, package_name: str) -> int:
        """从包加载插件"""
        try:
            package = importlib.import_module(package_name)
            count = 0
            
            # 遍历包中的所有模块
            for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
                if not is_pkg:
                    full_module_name = f"{package_name}.{module_name}"
                    count += self.load_plugins_from_module(full_module_name)
            
            return count
        except ImportError as e:
            logger.error(f"加载包失败: {package_name}, 错误: {e}")
            return 0
    
    def _discover_plugins_in_module(self, module) -> int:
        """在模块中发现插件"""
        count = 0
        
        for name, obj in inspect.getmembers(module):
            # 检查是否是LLM提供商类
            if (inspect.isclass(obj) and 
                issubclass(obj, BaseLLMProvider) and 
                obj != BaseLLMProvider):
                
                # 尝试获取提供商类型
                provider_type = self._get_provider_type_from_class(obj)
                if provider_type:
                    plugin = LLMProviderPlugin(
                        name=obj.__name__,
                        version="1.0.0",
                        provider_class=obj,
                        provider_type=provider_type,
                        description=f"{obj.__name__} LLM提供商插件"
                    )
                    if self.register_plugin(plugin):
                        count += 1
        
        return count
    
    def _get_provider_type_from_class(self, provider_class: Type[BaseLLMProvider]) -> Optional[LLMProviderType]:
        """从提供商类获取类型"""
        try:
            # 创建临时实例来获取提供商类型
            temp_instance = provider_class({})
            return temp_instance.provider_type
        except:
            return None

# 内置插件注册
def register_builtin_plugins(manager: PluginManager) -> None:
    """注册内置插件"""
    from llm_providers import OpenAILMProvider, DeepSeekLMProvider, QwenLMProvider
    
    # 注册OpenAI插件
    openai_plugin = LLMProviderPlugin(
        name="OpenAI Provider",
        version="1.0.0",
        provider_class=OpenAILMProvider,
        provider_type=LLMProviderType.OPENAI,
        description="OpenAI GPT系列模型提供商"
    )
    manager.register_plugin(openai_plugin)
    
    # 注册DeepSeek插件
    deepseek_plugin = LLMProviderPlugin(
        name="DeepSeek Provider",
        version="1.0.0",
        provider_class=DeepSeekLMProvider,
        provider_type=LLMProviderType.DEEPSEEK,
        description="DeepSeek模型提供商"
    )
    manager.register_plugin(deepseek_plugin)
    
    # 注册Qwen插件
    qwen_plugin = LLMProviderPlugin(
        name="Qwen Provider",
        version="1.0.0",
        provider_class=QwenLMProvider,
        provider_type=LLMProviderType.QWEN,
        description="阿里云通义千问模型提供商"
    )
    manager.register_plugin(qwen_plugin)

# 测试代码
if __name__ == "__main__":
    # 创建插件管理器
    manager = PluginManager()
    
    # 注册内置插件
    register_builtin_plugins(manager)
    
    # 显示所有插件
    print("=== 所有插件 ===")
    for plugin_info in manager.get_all_plugins():
        print(f"- {plugin_info['name']} ({plugin_info['provider_type']})")
    
    # 显示可用提供商
    print("\n=== 可用LLM提供商 ===")
    for provider in manager.get_available_llm_providers():
        print(f"- {provider}")
    
    # 测试创建提供商实例
    test_config = {
        'api_key': 'test_key',
        'model': 'gpt-4o',
        'base_url': 'https://api.openai.com'
    }
    
    openai_provider = manager.create_llm_provider(LLMProviderType.OPENAI, test_config)
    if openai_provider:
        print(f"\n✅ 成功创建OpenAI提供商: {openai_provider.get_provider_info()}")
    else:
        print("\n❌ 创建OpenAI提供商失败")