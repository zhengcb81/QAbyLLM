#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合验证系统集成测试
"""

import pytest
import asyncio
from answer_verifier import AnswerVerifier, VerificationLevel


class TestComprehensiveVerification:
    """综合验证系统测试类"""

    @pytest.mark.asyncio
    async def test_comprehensive_verification_valid_answer(self, sample_verifier, sample_answer, sample_question, sample_context, sample_sources):
        """测试有效的综合验证"""
        result = await sample_verifier.verify_answer(
            sample_answer, 
            sample_question, 
            context=sample_context,
            sources=sample_sources
        )
        
        assert result.is_verified is True
        assert result.confidence >= 0.7
        assert result.verification_level in [VerificationLevel.HIGH, VerificationLevel.MEDIUM]
        assert len(result.methods_used) >= 3  # 至少使用3种验证方法

    @pytest.mark.asyncio
    async def test_comprehensive_verification_false_answer(self, sample_verifier, sample_question, sample_context, sample_sources):
        """测试错误的综合验证"""
        false_answer = "人工智能是一种魔法技术，可以让计算机拥有超能力。机器学习是骗人的把戏。"
        
        result = await sample_verifier.verify_answer(
            false_answer,
            sample_question,
            context=sample_context,
            sources=sample_sources
        )
        
        # 错误答案应该有问题或置信度较低
        assert len(result.issues_found) > 0 or result.confidence < 0.7

    @pytest.mark.asyncio
    async def test_verification_without_context_and_sources(self, sample_verifier, sample_answer, sample_question):
        """测试无上下文和来源的验证"""
        result = await sample_verifier.verify_answer(
            sample_answer,
            sample_question,
            context=None,
            sources=None
        )
        
        # 即使没有上下文和来源，基于知识库的验证也应该工作
        assert result.confidence >= 0.5
        # 可能只使用事实检查一种方法
        assert len(result.methods_used) >= 1

    @pytest.mark.asyncio
    async def test_verification_with_only_context(self, sample_verifier, sample_answer, sample_question, sample_context):
        """测试只有上下文的验证"""
        result = await sample_verifier.verify_answer(
            sample_answer,
            sample_question,
            context=sample_context,
            sources=None
        )
        
        assert result.confidence >= 0.6
        assert 'consistency_check' in [m.value for m in result.methods_used]

    @pytest.mark.asyncio
    async def test_verification_with_only_sources(self, sample_verifier, sample_answer, sample_question, sample_sources):
        """测试只有来源的验证"""
        result = await sample_verifier.verify_answer(
            sample_answer,
            sample_question,
            context=None,
            sources=sample_sources
        )
        
        assert result.confidence >= 0.6
        assert 'source_validation' in [m.value for m in result.methods_used]

    @pytest.mark.asyncio
    async def test_verification_level_determination(self, sample_verifier):
        """测试验证级别确定"""
        # 测试高置信度无问题
        high_level = sample_verifier._determine_verification_level(0.85, [])
        assert high_level == VerificationLevel.HIGH
        
        # 测试中等置信度
        medium_level = sample_verifier._determine_verification_level(0.75, [])
        assert medium_level == VerificationLevel.MEDIUM
        
        # 测试低置信度
        low_level = sample_verifier._determine_verification_level(0.45, [])
        assert low_level == VerificationLevel.LOW
        
        # 测试未验证
        unverified_level = sample_verifier._determine_verification_level(0.3, [])
        assert unverified_level == VerificationLevel.UNVERIFIED
        
        # 测试有问题的高置信度
        high_with_issues = sample_verifier._determine_verification_level(0.85, ["问题1"])
        assert high_with_issues == VerificationLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_verification_result_serialization(self, sample_verifier, sample_answer, sample_question):
        """测试验证结果序列化"""
        result = await sample_verifier.verify_answer(
            sample_answer,
            sample_question,
            context=None,
            sources=None
        )
        
        # 转换为字典
        result_dict = result.to_dict()
        
        # 检查所有必要字段
        assert 'is_verified' in result_dict
        assert 'confidence' in result_dict
        assert 'verification_level' in result_dict
        assert 'methods_used' in result_dict
        assert 'issues_found' in result_dict
        assert 'supporting_evidence' in result_dict
        assert 'contradictory_evidence' in result_dict
        assert 'timestamp' in result_dict
        
        # 检查类型正确性
        assert isinstance(result_dict['is_verified'], bool)
        assert isinstance(result_dict['confidence'], float)
        assert isinstance(result_dict['methods_used'], list)
        assert isinstance(result_dict['issues_found'], list)

    @pytest.mark.asyncio
    async def test_performance_benchmark(self, sample_verifier, sample_answer, sample_question, sample_context, sample_sources):
        """测试性能基准"""
        import time
        
        start_time = time.time()
        
        result = await sample_verifier.verify_answer(
            sample_answer,
            sample_question,
            context=sample_context,
            sources=sample_sources
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # 验证应该在合理时间内完成（小于5秒）
        assert processing_time < 5.0, f"验证耗时过长: {processing_time:.2f}秒"
        
        # 记录性能数据
        print(f"综合验证耗时: {processing_time:.2f}秒")
        print(f"置信度: {result.confidence:.2f}")
        print(f"使用的方法: {[m.value for m in result.methods_used]}")

    @pytest.mark.asyncio
    async def test_edge_case_empty_answer(self, sample_verifier, sample_question):
        """测试空答案边界情况"""
        result = await sample_verifier.verify_answer(
            "",
            sample_question,
            context=None,
            sources=None
        )
        
        # 空答案应该置信度较低或有问题
        assert result.confidence < 0.6 or len(result.issues_found) > 0

    @pytest.mark.asyncio
    async def test_edge_case_very_short_answer(self, sample_verifier, sample_question):
        """测试非常短的答案"""
        result = await sample_verifier.verify_answer(
            "是的",
            sample_question,
            context=None,
            sources=None
        )
        
        # 短答案应该置信度较低或有问题
        assert result.confidence < 0.7 or len(result.issues_found) > 0

    @pytest.mark.asyncio
    async def test_edge_case_very_long_answer(self, sample_verifier, sample_question):
        """测试非常长的答案"""
        long_answer = "人工智能" * 500  # 创建很长的答案
        
        result = await sample_verifier.verify_answer(
            long_answer,
            sample_question,
            context=None,
            sources=None
        )
        
        # 长答案应该能够处理，但可能置信度较低
        assert result.confidence >= 0.4

    @pytest.mark.asyncio
    async def test_different_question_types(self, sample_verifier, sample_answer):
        """测试不同类型的问题"""
        question_types = [
            "什么是人工智能？",
            "人工智能有哪些应用？", 
            "机器学习与人工智能的关系是什么？",
            "请解释深度学习的原理",
            "计算机科学包含哪些分支？"
        ]
        
        for question in question_types:
            result = await sample_verifier.verify_answer(
                sample_answer,
                question,
                context=None,
                sources=None
            )
            
            # 所有问题类型都应该能够处理
            assert result.confidence >= 0.5
            # 对于某些问题类型，可能只使用一种验证方法
            assert len(result.methods_used) >= 1