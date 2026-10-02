#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一LLM提供商接口
支持多种LLM服务提供商的标准接口
"""

import abc
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class LLMProviderType(Enum):
    """LLM提供商类型枚举"""
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"

class LLMResponse:
    """LLM响应统一格式"""
    
    def __init__(self, 
                 content: str,
                 provider: str,
                 model: str,
                 token_usage: Optional[Dict[str, int]] = None,
                 latency_ms: Optional[int] = None,
                 error: Optional[str] = None):
        self.content = content
        self.provider = provider
        self.model = model
        self.token_usage = token_usage or {}
        self.latency_ms = latency_ms
        self.error = error
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'content': self.content,
            'provider': self.provider,
            'model': self.model,
            'token_usage': self.token_usage,
            'latency_ms': self.latency_ms,
            'error': self.error,
            'timestamp': self.timestamp
        }
    
    def is_success(self) -> bool:
        """检查是否成功"""
        return self.error is None

class BaseLLMProvider(abc.ABC):
    """LLM提供商基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.provider_type = LLMProviderType.CUSTOM
        self.model = config.get('model', '')
        self.base_url = config.get('base_url', '')
        self.api_key = config.get('api_key', '')
        self.timeout = config.get('timeout', 60)
        self.max_retries = config.get('max_retries', 3)
    
    @abc.abstractmethod
    async def chat_completion(self, 
                            messages: List[Dict[str, str]],
                            temperature: float = 0.7,
                            max_tokens: int = 2000) -> LLMResponse:
        """聊天补全接口"""
        pass
    
    @abc.abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """生成文本嵌入"""
        pass
    
    def validate_config(self) -> bool:
        """验证配置是否有效"""
        if not self.api_key or self.api_key.endswith('_here'):
            logger.warning(f"无效的API密钥配置: {self.provider_type.value}")
            return False
        if not self.model:
            logger.warning(f"未配置模型: {self.provider_type.value}")
            return False
        return True
    
    def get_provider_info(self) -> Dict[str, Any]:
        """获取提供商信息"""
        return {
            'type': self.provider_type.value,
            'model': self.model,
            'base_url': self.base_url,
            'timeout': self.timeout,
            'max_retries': self.max_retries
        }

class OpenAILMProvider(BaseLLMProvider):
    """OpenAI提供商实现"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider_type = LLMProviderType.OPENAI
        
    async def chat_completion(self, 
                            messages: List[Dict[str, str]],
                            temperature: float = 0.7,
                            max_tokens: int = 2000) -> LLMResponse:
        """OpenAI聊天补全"""
        import openai
        from openai import OpenAI
        
        start_time = datetime.now()
        
        try:
            client = OpenAI(api_key=self.api_key)
            
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            return LLMResponse(
                content=response.choices[0].message.content,
                provider='openai',
                model=self.model,
                token_usage={
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                },
                latency_ms=latency_ms
            )
            
        except Exception as e:
            logger.error(f"OpenAI API调用失败: {e}")
            return LLMResponse(
                content="",
                provider='openai',
                model=self.model,
                error=str(e)
            )
    
    async def generate_embedding(self, text: str) -> List[float]:
        """OpenAI嵌入生成"""
        import openai
        from openai import OpenAI
        
        try:
            client = OpenAI(api_key=self.api_key)
            
            response = client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"OpenAI嵌入生成失败: {e}")
            raise

class DeepSeekLMProvider(BaseLLMProvider):
    """DeepSeek提供商实现"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider_type = LLMProviderType.DEEPSEEK
        
    async def chat_completion(self, 
                            messages: List[Dict[str, str]],
                            temperature: float = 0.7,
                            max_tokens: int = 2000) -> LLMResponse:
        """DeepSeek聊天补全"""
        import requests
        import time
        
        start_time = datetime.now()
        
        for attempt in range(self.max_retries):
            try:
                url = f"{self.base_url}/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                
                response = requests.post(url, headers=headers, json=data, timeout=self.timeout)
                response.raise_for_status()
                
                result = response.json()
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                return LLMResponse(
                    content=result['choices'][0]['message']['content'],
                    provider='deepseek',
                    model=self.model,
                    latency_ms=latency_ms
                )
                
            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    wait_time = (attempt + 1) * 10
                    logger.warning(f"DeepSeek API超时，等待 {wait_time}秒后重试...")
                    time.sleep(wait_time)
                    continue
                else:
                    error_msg = f"DeepSeek API调用超时 ({self.timeout}秒)"
                    logger.error(error_msg)
                    return LLMResponse(
                        content="",
                        provider='deepseek',
                        model=self.model,
                        error=error_msg
                    )
                    
            except Exception as e:
                logger.error(f"DeepSeek API调用失败: {e}")
                return LLMResponse(
                    content="",
                    provider='deepseek',
                    model=self.model,
                    error=str(e)
                )
    
    async def generate_embedding(self, text: str) -> List[float]:
        """DeepSeek暂不支持嵌入，使用本地模型"""
        from sentence_transformers import SentenceTransformer
        
        try:
            model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
            embedding = model.encode(text)
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"本地嵌入生成失败: {e}")
            raise

class QwenLMProvider(BaseLLMProvider):
    """Qwen提供商实现"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider_type = LLMProviderType.QWEN
        
    async def chat_completion(self, 
                            messages: List[Dict[str, str]],
                            temperature: float = 0.7,
                            max_tokens: int = 2000) -> LLMResponse:
        """Qwen聊天补全"""
        import requests
        
        start_time = datetime.now()
        
        try:
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            return LLMResponse(
                content=result['choices'][0]['message']['content'],
                provider='qwen',
                model=self.model,
                latency_ms=latency_ms
            )
            
        except Exception as e:
            logger.error(f"Qwen API调用失败: {e}")
            return LLMResponse(
                content="",
                provider='qwen',
                model=self.model,
                error=str(e)
            )
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Qwen暂不支持嵌入，使用本地模型"""
        from sentence_transformers import SentenceTransformer
        
        try:
            model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
            embedding = model.encode(text)
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"本地嵌入生成失败: {e}")
            raise

class LLMProviderFactory:
    """LLM提供商工厂"""
    
    @staticmethod
    def create_provider(provider_type: Union[str, LLMProviderType], 
                      config: Dict[str, Any]) -> BaseLLMProvider:
        """创建LLM提供商实例"""
        
        if isinstance(provider_type, str):
            provider_type = LLMProviderType(provider_type.lower())
        
        provider_config = config.get('api', {}).get(provider_type.value, {})
        
        if provider_type == LLMProviderType.OPENAI:
            return OpenAILMProvider(provider_config)
        elif provider_type == LLMProviderType.DEEPSEEK:
            return DeepSeekLMProvider(provider_config)
        elif provider_type == LLMProviderType.QWEN:
            return QwenLMProvider(provider_config)
        else:
            raise ValueError(f"不支持的LLM提供商类型: {provider_type}")
    
    @staticmethod
    def get_available_providers() -> List[str]:
        """获取所有可用的提供商类型"""
        return [provider.value for provider in LLMProviderType]

# 测试代码
if __name__ == "__main__":
    # 测试配置
    test_config = {
        'api': {
            'openai': {
                'api_key': 'test_key',
                'model': 'gpt-4o',
                'base_url': 'https://api.openai.com',
                'timeout': 60,
                'max_retries': 3
            },
            'deepseek': {
                'api_key': 'test_key',
                'model': 'deepseek-chat',
                'base_url': 'https://api.deepseek.com',
                'timeout': 120,
                'max_retries': 3
            }
        }
    }
    
    # 测试工厂
    factory = LLMProviderFactory()
    
    # 创建OpenAI提供商
    openai_provider = factory.create_provider('openai', test_config)
    print(f"OpenAI提供商信息: {openai_provider.get_provider_info()}")
    
    # 创建DeepSeek提供商
    deepseek_provider = factory.create_provider('deepseek', test_config)
    print(f"DeepSeek提供商信息: {deepseek_provider.get_provider_info()}")
    
    # 获取所有可用提供商
    print(f"可用提供商: {factory.get_available_providers()}")