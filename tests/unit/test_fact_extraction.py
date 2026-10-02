#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事实提取功能单元测试
"""

import pytest
from answer_verifier import AnswerVerifier


class TestFactExtraction:
    """事实提取功能测试类"""

    def test_extract_facts_from_valid_answer(self, sample_verifier, sample_answer):
        """测试从有效答案中提取事实"""
        facts = sample_verifier._extract_facts(sample_answer)
        
        assert len(facts) > 0, "应该能从有效答案中提取到事实"
        assert any("人工智能" in fact for fact in facts), "应该包含人工智能相关事实"
        assert any("计算机科学" in fact for fact in facts), "应该包含计算机科学相关事实"

    def test_extract_facts_from_wrong_answer(self, sample_verifier, sample_wrong_answer):
        """测试从错误答案中提取事实"""
        facts = sample_verifier._extract_facts(sample_wrong_answer)
        
        # 错误答案也应该能提取到事实，但内容不同
        assert len(facts) > 0, "应该能从错误答案中提取到事实"
        assert any("人工智能" in fact for fact in facts), "应该包含人工智能相关事实"

    def test_extract_facts_empty_input(self, sample_verifier):
        """测试空输入的情况"""
        facts = sample_verifier._extract_facts("")
        assert len(facts) == 0, "空输入应该返回空事实列表"

    def test_extract_facts_short_text(self, sample_verifier):
        """测试短文本输入"""
        facts = sample_verifier._extract_facts("这是测试")
        assert len(facts) == 0, "过短的文本应该返回空事实列表"

    def test_is_potential_fact_method(self, sample_verifier):
        """测试潜在事实判断方法"""
        # 有效事实陈述
        assert sample_verifier._is_potential_fact("人工智能是计算机科学的分支")
        assert sample_verifier._is_potential_fact("机器学习可以处理数据")
        
        # 无效事实陈述（疑问句）
        assert not sample_verifier._is_potential_fact("什么是人工智能？")
        assert not sample_verifier._is_potential_fact("人工智能是什么？")
        
        # 无效事实陈述（模糊词）
        assert not sample_verifier._is_potential_fact("可能人工智能很重要")
        assert not sample_verifier._is_potential_fact("据说机器学习很强大")

    def test_extract_core_fact_method(self, sample_verifier):
        """测试核心事实提取方法"""
        sentence = "通常人工智能是计算机科学的一个重要分支"
        core_fact = sample_verifier._extract_core_fact(sentence)
        
        assert "通常" not in core_fact, "应该去除修饰词"
        assert "重要" not in core_fact, "应该去除修饰词"
        assert "人工智能" in core_fact, "应该保留核心内容"
        assert "计算机科学" in core_fact, "应该保留核心内容"

    def test_is_complete_fact_method(self, sample_verifier):
        """测试完整事实判断方法"""
        # 完整事实
        assert sample_verifier._is_complete_fact("人工智能是计算机科学分支")
        assert sample_verifier._is_complete_fact("机器学习处理数据分析")
        
        # 不完整事实
        assert not sample_verifier._is_complete_fact("人工智能")
        assert not sample_verifier._is_complete_fact("可能很重要")