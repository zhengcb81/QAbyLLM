#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理器
增强的配置管理和验证系统
"""

import os
import yaml
import json
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import logging
from datetime import datetime
import time
import threading
from enum import Enum
import jsonschema
from jsonschema import validate

# 导入结构化日志系统
try:
    from logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

class ConfigValidationError(Exception):
    """配置验证错误"""
    pass

class ConfigReloadMode(Enum):
    """配置重载模式"""
    MANUAL = "manual"
    AUTO = "auto"
    WATCH = "watch"

# JSON Schema for configuration validation
CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "mode": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["online", "local"]},
                "local_api_provider": {"type": "string", "enum": ["openai", "deepseek", "qwen"]}
            },
            "required": ["type"]
        },
        "api": {
            "type": "object",
            "properties": {
                "openai_api_key": {"type": "string"},
                "openai_model": {"type": "string"},
                "deepseek_api_key": {"type": "string"},
                "deepseek_model": {"type": "string"},
                "deepseek_base_url": {"type": "string"},
                "qwen_api_key": {"type": "string"},
                "qwen_model": {"type": "string"},
                "qwen_base_url": {"type": "string"},
                "use_openai_search": {"type": "boolean"}
            }
        },
        "local_rag": {
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean"},
                "company_name": {"type": "string"},
                "documents_folder": {"type": "string"},
                "supported_formats": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "vector_db": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "persist_directory": {"type": "string"},
                        "collection_name": {"type": "string"}
                    }
                },
                "chunking": {
                    "type": "object",
                    "properties": {
                        "chunk_size": {"type": "integer", "minimum": 100},
                        "chunk_overlap": {"type": "integer", "minimum": 0}
                    }
                },
                "embedding": {
                    "type": "object",
                    "properties": {
                        "model_name": {"type": "string"},
                        "device": {"type": "string"}
                    }
                },
                "retrieval": {
                    "type": "object",
                    "properties": {
                        "top_k": {"type": "integer", "minimum": 1},
                        "similarity_threshold": {"type": "number", "minimum": 0, "maximum": 1}
                    }
                }
            }
        },
        "analysis": {
            "type": "object",
            "properties": {
                "companies": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        },
        "questions": {
            "type": "array",
            "items": {"type": "string"}
        },
        "output": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "include_search_sources": {"type": "boolean"}
            }
        },
        "logging": {
            "type": "object",
            "properties": {
                "level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]},
                "file": {"type": "string"},
                "format": {"type": "string"},
                "max_size": {"type": "integer"},
                "backup_count": {"type": "integer"}
            }
        },
        "monitoring": {
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean"},
                "prometheus_port": {"type": "integer"},
                "metrics_interval": {"type": "integer"}
            }
        },
        "answer_verification": {
            "type": "object",
            "properties": {
                "enabled_methods": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "thresholds": {
                    "type": "object",
                    "properties": {
                        "min_confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "similarity_threshold": {"type": "number", "minimum": 0, "maximum": 1},
                        "keyword_overlap_threshold": {"type": "integer", "minimum": 0}
                    }
                },
                "fact_checking": {
                    "type": "object",
                    "properties": {
                        "stop_words": {"type": "array", "items": {"type": "string"}},
                        "modifiers": {"type": "array", "items": {"type": "string"}},
                        "connectors": {"type": "array", "items": {"type": "string"}},
                        "vague_words": {"type": "array", "items": {"type": "string"}},
                        "factual_indicators": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "expert_knowledge_base": {"type": "object"}
            }
        }
    },
    "required": ["mode"]
}

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, 
                 config_path: str = "config.yaml",
                 reload_mode: ConfigReloadMode = ConfigReloadMode.MANUAL,
                 watch_interval: int = 30):
        self.config_path = config_path
        self.reload_mode = reload_mode
        self.watch_interval = watch_interval
        self.config: Dict[str, Any] = {}
        self.last_modified: float = 0
        self._callbacks: List[callable] = []
        self._watch_thread: Optional[threading.Thread] = None
        self._stop_watching = False
        
        # 初始化配置
        self.load_config()
        
        # 启动文件监视（如果启用）
        if reload_mode == ConfigReloadMode.WATCH:
            self.start_watching()
    
    def load_config(self) -> bool:
        """加载配置文件"""
        try:
            if not os.path.exists(self.config_path):
                logger.warning(f"配置文件不存在: {self.config_path}")
                self.config = self.get_default_config()
                return True
            
            # 检查文件是否修改
            current_modified = os.path.getmtime(self.config_path)
            if current_modified <= self.last_modified:
                return False
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                new_config = yaml.safe_load(f)
            
            # 验证配置
            self.validate_config(new_config)
            
            # 合并默认配置（用于新字段）
            default_config = self.get_default_config()
            merged_config = self._merge_configs(default_config, new_config)
            
            self.config = merged_config
            self.last_modified = current_modified
            
            logger.info(f"配置文件加载成功: {self.config_path}")
            
            # 通知回调
            self._notify_callbacks()
            
            return True
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            # 使用默认配置
            self.config = self.get_default_config()
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置是否符合schema"""
        try:
            validate(instance=config, schema=CONFIG_SCHEMA)
            
            # 额外验证：检查必要的API密钥
            mode = config.get('mode', {}).get('type', 'online')
            
            if mode == 'online':
                api_key = config.get('api', {}).get('openai_api_key', '')
                if not api_key or api_key.endswith('_here'):
                    logger.warning("OpenAI API密钥未配置或无效")
            
            elif mode == 'local':
                provider = config.get('mode', {}).get('local_api_provider', 'deepseek')
                api_key = config.get('api', {}).get(f'{provider}_api_key', '')
                if not api_key or api_key.endswith('_here'):
                    logger.warning(f"{provider} API密钥未配置或无效")
            
            return True
            
        except jsonschema.ValidationError as e:
            raise ConfigValidationError(f"配置验证失败: {e}")
        except Exception as e:
            raise ConfigValidationError(f"配置验证错误: {e}")
    
    def _merge_configs(self, default: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并两个配置"""
        result = default.copy()
        
        for key, value in new.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'mode': {
                'type': 'online',
                'local_api_provider': 'deepseek'
            },
            'api': {
                'openai_api_key': 'your_openai_api_key_here',
                'openai_model': 'gpt-4o',
                'use_openai_search': True,
                'deepseek_api_key': 'your_deepseek_api_key_here',
                'deepseek_model': 'deepseek-chat',
                'deepseek_base_url': 'https://api.deepseek.com',
                'qwen_api_key': 'your_qwen_api_key_here',
                'qwen_model': 'qwen-turbo',
                'qwen_base_url': 'https://dashscope.aliyuncs.com/api/v1'
            },
            'local_rag': {
                'enabled': False,
                'company_name': '海康威视',
                'documents_folder': '',
                'supported_formats': ['txt', 'md', 'json', 'pdf', 'docx', 'xlsx'],
                'vector_db': {
                    'type': 'chromadb',
                    'persist_directory': './vector_db',
                    'collection_name': 'company_knowledge'
                },
                'chunking': {
                    'chunk_size': 1000,
                    'chunk_overlap': 200
                },
                'embedding': {
                    'model_name': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                    'device': 'cpu'
                },
                'retrieval': {
                    'top_k': 5,
                    'similarity_threshold': 0.7
                }
            },
            'analysis': {
                'companies': ['小米集团', '华为', '苹果', '三星']
            },
            'questions': [
                "请分析{company_name}的网络效应强度，并给出1-10分的评分。请以JSON格式回答，包含评分和理由。",
                "请分析{company_name}的规模效应，并给出1-10分的评分。请以JSON格式回答，包含评分和理由。",
                "请分析{company_name}的客户黏性，并给出1-10分的评分。请以JSON格式回答，包含评分和理由。",
                "请分析{company_name}的成本优势，并给出1-10分的评分。请以JSON格式回答，包含评分和理由。",
                "请分析{company_name}所在行业的竞争格局，并给出1-10分的评分。请以JSON格式回答，包含评分和理由。",
                "请分析{company_name}的进入壁垒，并给出1-10分的评分。请以JSON格式回答，包含评分和理由。",
                "请分析{company_name}的价格敏感度，并给出1-10分的评分。请以JSON格式回答，包含评分和理由。"
            ],
            'output': {
                'file_path': 'multi_company_analysis.json',
                'include_search_sources': True
            },
            'logging': {
                'level': 'INFO',
                'file': 'app.log',
                'format': 'json',
                'max_size': 10485760,  # 10MB
                'backup_count': 5
            },
            'monitoring': {
                'enabled': False,
                'prometheus_port': 9090,
                'metrics_interval': 30
            },
            'answer_verification': {
                'enabled_methods': ['fact_check', 'source_validation', 'consistency_check'],
                'thresholds': {
                    'min_confidence': 0.7,
                    'similarity_threshold': 0.15,
                    'keyword_overlap_threshold': 1
                },
                'fact_checking': {
                    'stop_words': ['的', '了', '是', '在', '和', '与', '及', '等', '这个', '那个', '一个', '可以', '能够', '通过', '通常', '作为', '各种', '不同'],
                    'modifiers': ['通常', '一般', '经常', '主要', '基本', '特别', '非常', '十分', '极其', '重要'],
                    'connectors': ['而且', '并且', '另外', '此外', '同时', '然而', '但是', '不过', '因此', '所以'],
                    'vague_words': ['可能', '也许', '大概', '据说', '认为', '觉得', '一些', '各种', '不同', '或许'],
                    'factual_indicators': ['是', '有', '为', '包括', '称为', '技术', '系统', '方法', '分支', '领域', '可以', '能够', '实现', '处理', '支持', '提供', '包含', '属于', '分为', '基于', '使用', '应用', '人工智能', '机器学习', '计算机科学', '自然语言处理', '机器人']
                },
                'expert_knowledge_base': {}
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> bool:
        """设置配置值"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        return True
    
    def save_config(self, path: Optional[str] = None) -> bool:
        """保存配置到文件"""
        save_path = path or self.config_path
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False)
            
            logger.info(f"配置已保存到: {save_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def register_callback(self, callback: callable) -> None:
        """注册配置变更回调"""
        self._callbacks.append(callback)
    
    def unregister_callback(self, callback: callable) -> None:
        """注销配置变更回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _notify_callbacks(self) -> None:
        """通知所有回调函数"""
        for callback in self._callbacks:
            try:
                callback(self.config)
            except Exception as e:
                logger.error(f"配置回调执行失败: {e}")
    
    def start_watching(self) -> None:
        """启动配置文件监视"""
        if self._watch_thread and self._watch_thread.is_alive():
            return
        
        self._stop_watching = False
        self._watch_thread = threading.Thread(target=self._watch_config_file)
        self._watch_thread.daemon = True
        self._watch_thread.start()
        
        logger.info("配置文件监视已启动")
    
    def stop_watching(self) -> None:
        """停止配置文件监视"""
        self._stop_watching = True
        if self._watch_thread:
            self._watch_thread.join(timeout=2.0)
        
        logger.info("配置文件监视已停止")
    
    def _watch_config_file(self) -> None:
        """监视配置文件变化"""
        while not self._stop_watching:
            try:
                self.load_config()  # 这会检查文件修改时间
                time.sleep(self.watch_interval)
            except Exception as e:
                logger.error(f"配置文件监视错误: {e}")
                time.sleep(self.watch_interval)
    
    def __getitem__(self, key: str) -> Any:
        """支持字典式访问"""
        return self.get(key)
    
    def __contains__(self, key: str) -> bool:
        """检查配置项是否存在"""
        return self.get(key) is not None

    # 答案验证系统相关方法
    def get_verification_config(self) -> Dict[str, Any]:
        """获取验证系统配置"""
        return self.get('answer_verification', {})
    
    def get_enabled_verification_methods(self) -> List[str]:
        """获取启用的验证方法"""
        return self.get_verification_config().get('enabled_methods', [])
    
    def get_verification_threshold(self, threshold_name: str, default: float = 0.0) -> float:
        """获取验证阈值"""
        thresholds = self.get_verification_config().get('thresholds', {})
        return thresholds.get(threshold_name, default)
    
    def get_fact_checking_config(self) -> Dict[str, Any]:
        """获取事实检查配置"""
        return self.get_verification_config().get('fact_checking', {})
    
    def get_stop_words(self) -> List[str]:
        """获取停用词列表"""
        return self.get_fact_checking_config().get('stop_words', [])
    
    def get_modifiers(self) -> List[str]:
        """获取修饰词列表"""
        return self.get_fact_checking_config().get('modifiers', [])
    
    def get_connectors(self) -> List[str]:
        """获取连接词列表"""
        return self.get_fact_checking_config().get('connectors', [])
    
    def get_vague_words(self) -> List[str]:
        """获取模糊词列表"""
        return self.get_fact_checking_config().get('vague_words', [])
    
    def get_factual_indicators(self) -> List[str]:
        """获取事实性指示词列表"""
        return self.get_fact_checking_config().get('factual_indicators', [])
    
    def get_expert_knowledge_base(self) -> Dict[str, Any]:
        """获取专家知识库"""
        return self.get_verification_config().get('expert_knowledge_base', {})

# 测试代码
if __name__ == "__main__":
    # 创建配置管理器
    config_manager = ConfigManager("test_config.yaml", ConfigReloadMode.MANUAL)
    
    # 测试配置获取
    print("=== 当前配置 ===")
    print(f"模式: {config_manager.get('mode.type')}")
    print(f"OpenAI模型: {config_manager.get('api.openai_model')}")
    
    # 测试配置设置
    config_manager.set('api.openai_model', 'gpt-4-turbo')
    print(f"修改后的模型: {config_manager.get('api.openai_model')}")
    
    # 测试配置保存
    config_manager.save_config("test_config_saved.yaml")
    print("配置已保存")
    
    # 测试配置验证
    try:
        config_manager.validate_config(config_manager.config)
        print("✅ 配置验证通过")
    except ConfigValidationError as e:
        print(f"❌ 配置验证失败: {e}")