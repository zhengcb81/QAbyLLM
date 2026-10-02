#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试结构化日志系统
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

# 初始化日志系统
from setup_logging import initialize_logging
initialize_logging()

# 导入其他模块进行测试
from answer_verifier import AnswerVerifier
from config_manager import ConfigManager

def test_answer_verifier_logging():
    """测试答案验证器的日志功能"""
    print("测试答案验证器日志...")
    
    # 创建验证器
    verifier = AnswerVerifier({
        'enabled_methods': ['fact_check', 'source_validation', 'consistency_check'],
        'min_confidence': 0.7,
        'expert_knowledge_base': {
            "人工智能是计算机科学的一个分支": {
                "is_true": True,
                "confidence": 0.9,
                "evidence": "权威计算机科学教材定义"
            }
        }
    })
    
    # 测试验证
    import asyncio
    
    async def test_verification():
        result = await verifier.verify_answer(
            "人工智能是计算机科学的一个分支",
            "什么是人工智能？",
            context=None,
            sources=None
        )
        print(f"验证结果: {result.is_verified}, 置信度: {result.confidence:.2f}")
        return result
    
    result = asyncio.run(test_verification())
    return result

def test_config_manager_logging():
    """测试配置管理器的日志功能"""
    print("测试配置管理器日志...")
    
    config_manager = ConfigManager("test_config.yaml")
    
    # 测试配置获取
    mode = config_manager.get('mode.type')
    model = config_manager.get('api.openai_model')
    
    print(f"配置模式: {mode}, 模型: {model}")
    
    # 测试配置保存
    config_manager.set('api.openai_model', 'gpt-4-turbo-test')
    config_manager.save_config("test_config_saved.yaml")
    
    return config_manager

def test_edge_cases():
    """测试边界情况的日志"""
    print("测试边界情况日志...")
    
    verifier = AnswerVerifier({
        'enabled_methods': ['fact_check'],
        'min_confidence': 0.7
    })
    
    import asyncio
    
    async def test_empty_answer():
        result = await verifier.verify_answer(
            "",
            "测试问题",
            context=None,
            sources=None
        )
        print(f"空答案验证: {result.confidence:.2f}, 问题: {result.issues_found}")
    
    async def test_short_answer():
        result = await verifier.verify_answer(
            "是的",
            "测试问题", 
            context=None,
            sources=None
        )
        print(f"短答案验证: {result.confidence:.2f}, 问题: {result.issues_found}")
    
    asyncio.run(test_empty_answer())
    asyncio.run(test_short_answer())

if __name__ == "__main__":
    print("=" * 50)
    print("结构化日志系统测试")
    print("=" * 50)
    
    try:
        # 测试配置管理器
        config_mgr = test_config_manager_logging()
        print()
        
        # 测试答案验证器
        result = test_answer_verifier_logging()
        print()
        
        # 测试边界情况
        test_edge_cases()
        print()
        
        print("所有日志测试完成")
        print("检查 app.log 文件查看结构化日志输出")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()