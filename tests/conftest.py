#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试配置文件
为答案验证系统测试提供共享的fixture和配置
"""

import pytest
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from answer_verifier import AnswerVerifier


@pytest.fixture
def sample_verifier():
    """创建示例验证器实例"""
    return AnswerVerifier({
        'enabled_methods': ['fact_check', 'source_validation', 'consistency_check'],
        'min_confidence': 0.7,
        'expert_knowledge_base': {
            "人工智能是计算机科学的一个分支": {
                "is_true": True,
                "confidence": 0.9,
                "evidence": "权威计算机科学教材定义"
            },
            "机器学习是人工智能的核心技术": {
                "is_true": True,
                "confidence": 0.95,
                "evidence": "广泛接受的学术共识"
            }
        }
    })


@pytest.fixture
def sample_question():
    """示例问题"""
    return "什么是人工智能？"


@pytest.fixture
def sample_answer():
    """示例正确答案"""
    return "人工智能是计算机科学的一个分支，它致力于创建能够执行通常需要人类智能的任务的系统。"


@pytest.fixture
def sample_wrong_answer():
    """示例错误答案"""
    return "人工智能是一种魔法技术，可以让计算机拥有超能力。"


@pytest.fixture
def sample_context():
    """示例上下文信息"""
    return [
        {
            'content': '人工智能研究包括机器人、语言识别、图像识别、自然语言处理等领域',
            'title': '人工智能概述'
        }
    ]


@pytest.fixture
def sample_sources():
    """示例来源信息"""
    return [
        {
            'content': '人工智能是计算机科学中研究如何制造智能机器的分支学科',
            'title': '人工智能导论',
            'reliability': 'high'
        }
    ]