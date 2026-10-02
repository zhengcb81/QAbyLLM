#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志系统初始化脚本
在应用程序启动时调用此脚本来配置结构化日志
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    from logging_config import setup_logging, DEFAULT_CONFIG
    from config_manager import ConfigManager
    
    def initialize_logging() -> None:
        """初始化应用程序日志系统"""
        try:
            # 尝试从配置管理器获取日志配置
            config_manager = ConfigManager()
            logging_config = config_manager.get('logging', DEFAULT_CONFIG)
            
            # 设置日志系统
            setup_logging(logging_config)
            
            # 获取日志器来记录初始化成功
            from logging_config import get_logger
            logger = get_logger(__name__)
            
            logger.info("日志系统初始化成功", extra={
                'config_file': config_manager.config_path,
                'log_level': logging_config.get('level', 'INFO'),
                'log_file': logging_config.get('file', 'app.log'),
                'log_format': logging_config.get('format', 'json')
            })
            
        except Exception as e:
            # 如果配置管理器不可用，使用默认配置
            setup_logging(DEFAULT_CONFIG)
            
            from logging_config import get_logger
            logger = get_logger(__name__)
            logger.warning(f"使用默认日志配置: {e}")
    
    # 导出初始化函数
    __all__ = ['initialize_logging']
    
except ImportError as e:
    # 如果日志配置模块不可用，提供回退
    import logging
    
    def initialize_logging() -> None:
        """简单的日志初始化回退"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        logger = logging.getLogger(__name__)
        logger.warning(f"使用基本日志配置: {e}")
    
    __all__ = ['initialize_logging']


if __name__ == "__main__":
    # 测试日志初始化
    initialize_logging()
    
    # 测试日志记录
    try:
        from logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("日志初始化测试成功")
        logger.debug("调试信息", extra={'test_value': 123, 'feature': 'logging'})
        
        print("✅ 日志系统测试成功")
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"日志测试失败: {e}")
        print(f"❌ 日志测试失败: {e}")