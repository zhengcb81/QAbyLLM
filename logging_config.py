#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结构化日志配置系统
提供统一的日志配置和管理
"""

import logging
import logging.config
import json
from typing import Dict, Any, Optional
from pathlib import Path
import os


class StructuredLogger:
    """结构化日志管理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._configured = False
    
    def configure(self, config: Optional[Dict[str, Any]] = None) -> None:
        """配置日志系统"""
        if config:
            self.config = config
        
        logging_config = self._create_logging_config()
        logging.config.dictConfig(logging_config)
        self._configured = True
        
        # 设置根日志器级别
        root_level = self.config.get('level', 'INFO')
        logging.getLogger().setLevel(getattr(logging, root_level))
    
    def _create_logging_config(self) -> Dict[str, Any]:
        """创建日志配置字典"""
        log_file = self.config.get('file', 'app.log')
        log_level = self.config.get('level', 'INFO')
        log_format = self.config.get('format', 'json')
        max_size = self.config.get('max_size', 10485760)  # 10MB
        backup_count = self.config.get('backup_count', 5)
        
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        if log_format == 'json':
            formatter_config = {
                '()': 'logging_config.JsonFormatter',
                'fmt': {
                    'timestamp': '%(asctime)s',
                    'level': '%(levelname)s',
                    'module': '%(module)s',
                    'function': '%(funcName)s',
                    'line': '%(lineno)d',
                    'message': '%(message)s',
                    'process': '%(process)d',
                    'thread': '%(thread)d'
                }
            }
        else:
            formatter_config = {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        
        return {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'standard': formatter_config,
                'simple': {
                    'format': '%(asctime)s - %(levelname)s - %(message)s'
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'level': log_level,
                    'formatter': 'simple',
                    'stream': 'ext://sys.stdout'
                },
                'file': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'level': log_level,
                    'formatter': 'standard',
                    'filename': log_file,
                    'maxBytes': max_size,
                    'backupCount': backup_count,
                    'encoding': 'utf-8'
                }
            },
            'root': {
                'level': log_level,
                'handlers': ['console', 'file']
            },
            'loggers': {
                'answer_verifier': {
                    'level': 'DEBUG',
                    'handlers': ['console', 'file'],
                    'propagate': False
                },
                'config_manager': {
                    'level': 'INFO',
                    'handlers': ['console', 'file'],
                    'propagate': False
                },
                'rag_system': {
                    'level': 'INFO',
                    'handlers': ['console', 'file'],
                    'propagate': False
                }
            }
        }
    
    def get_logger(self, name: str) -> logging.Logger:
        """获取配置好的日志器"""
        if not self._configured:
            self.configure()
        return logging.getLogger(name)


class JsonFormatter(logging.Formatter):
    """JSON格式日志格式化器"""
    
    def __init__(self, fmt: Optional[Dict[str, str]] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fmt = fmt or {
            'timestamp': '%(asctime)s',
            'level': '%(levelname)s',
            'module': '%(module)s',
            'function': '%(funcName)s',
            'line': '%(lineno)d',
            'message': '%(message)s'
        }
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为JSON"""
        log_data = {}
        
        for key, format_spec in self.fmt.items():
            try:
                value = format_spec % record.__dict__
                log_data[key] = value
            except:
                log_data[key] = format_spec
        
        # 添加额外字段
        if hasattr(record, 'extra') and record.extra:
            log_data.update(record.extra)
        
        return json.dumps(log_data, ensure_ascii=False)


# 全局日志管理器实例
_logger_manager = StructuredLogger()


def setup_logging(config: Optional[Dict[str, Any]] = None) -> None:
    """设置全局日志配置"""
    _logger_manager.configure(config)


def get_logger(name: str) -> logging.Logger:
    """获取配置好的日志器"""
    return _logger_manager.get_logger(name)


def log_verification_result(logger: logging.Logger, result: Any, question: str, answer: str) -> None:
    """记录验证结果的结构化日志"""
    extra_data = {
        'question': question[:200],  # 限制长度
        'answer_length': len(answer),
        'verified': getattr(result, 'is_verified', False),
        'confidence': getattr(result, 'confidence', 0.0),
        'verification_level': getattr(result, 'verification_level', 'unknown'),
        'methods_used': [m.value for m in getattr(result, 'methods_used', [])],
        'issues_count': len(getattr(result, 'issues_found', [])),
        'processing_time': getattr(result, 'processing_time', 0) if hasattr(result, 'processing_time') else 0
    }
    
    if extra_data['verified']:
        logger.info("答案验证成功", extra=extra_data)
    else:
        logger.warning("答案验证失败", extra=extra_data)


# 默认配置
DEFAULT_CONFIG = {
    'level': 'INFO',
    'file': 'app.log',
    'format': 'json',
    'max_size': 10485760,  # 10MB
    'backup_count': 5
}


if __name__ == "__main__":
    # 测试代码
    setup_logging(DEFAULT_CONFIG)
    logger = get_logger(__name__)
    
    logger.info("日志系统初始化成功")
    logger.debug("调试信息", extra={'test': 'value', 'number': 42})
    logger.warning("警告信息")
    logger.error("错误信息")
    
    print("日志配置测试完成")