#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
相似度计算功能单元测试
"""

import pytest
from answer_verifier import AnswerVerifier


class TestSimilarityCalculation:
    """相似度计算功能测试类"""

    def test_jaccard_similarity_exact_match(self, sample_verifier):
        """测试精确匹配的Jaccard相似度"""
        similarity = sample_verifier._jaccard_similarity("人工智能", "人工智能")
        assert similarity == 1.0, "完全相同的文本应该有1.0的相似度"

    def test_jaccard_similarity_partial_match(self, sample_verifier):
        """测试部分匹配的Jaccard相似度"""
        similarity = sample_verifier._jaccard_similarity("人工智能", "人工")
        assert similarity > 0.0, "部分匹配的文本应该有大于0的相似度"
        assert similarity < 1.0, "部分匹配的文本应该小于1.0的相似度"

    def test_jaccard_similarity_no_match(self, sample_verifier):
        """测试无匹配的Jaccard相似度"""
        similarity = sample_verifier._jaccard_similarity("人工智能", "区块链")
        assert similarity == 0.0, "完全不同的文本应该有0.0的相似度"

    def test_jaccard_similarity_empty_input(self, sample_verifier):
        """测试空输入的Jaccard相似度"""
        similarity = sample_verifier._jaccard_similarity("", "人工智能")
        assert similarity == 0.0, "空输入应该有0.0的相似度"
        
        similarity2 = sample_verifier._jaccard_similarity("人工智能", "")
        assert similarity2 == 0.0, "空输入应该有0.0的相似度"

    def test_word_based_similarity_exact_match(self, sample_verifier):
        """测试精确匹配的词级相似度"""
        similarity = sample_verifier._word_based_similarity("人工智能 机器学习", "人工智能 机器学习")
        assert similarity == 1.0, "完全相同的文本应该有1.0的相似度"

    def test_word_based_similarity_partial_match(self, sample_verifier):
        """测试部分匹配的词级相似度"""
        similarity = sample_verifier._word_based_similarity("人工智能 机器学习", "人工智能")
        assert similarity > 0.0, "部分匹配的文本应该有大于0的相似度"
        assert similarity < 1.0, "部分匹配的文本应该小于1.0的相似度"

    def test_word_based_similarity_no_match(self, sample_verifier):
        """测试无匹配的词级相似度"""
        similarity = sample_verifier._word_based_similarity("人工智能", "区块链")
        assert similarity == 0.0, "完全不同的文本应该有0.0的相似度"

    def test_calculate_similarity_short_texts(self, sample_verifier):
        """测试短文本的相似度计算"""
        similarity = sample_verifier._calculate_similarity("人工智能", "人工")
        assert similarity > 0.0, "短文本应该有大于0的相似度"

    def test_calculate_similarity_long_texts(self, sample_verifier):
        """测试长文本的相似度计算"""
        text1 = "人工智能是计算机科学的重要分支，专注于创建智能系统"
        text2 = "机器学习是人工智能的核心技术，使计算机能够从数据中学习"
        
        similarity = sample_verifier._calculate_similarity(text1, text2)
        assert similarity > 0.0, "相关文本应该有大于0的相似度"
        assert similarity < 1.0, "不同文本应该小于1.0的相似度"

    def test_calculate_similarity_identical_texts(self, sample_verifier):
        """测试相同文本的相似度计算"""
        text = "人工智能是计算机科学的重要分支"
        similarity = sample_verifier._calculate_similarity(text, text)
        assert similarity == 1.0, "完全相同的文本应该有1.0的相似度"

    def test_calculate_similarity_unrelated_texts(self, sample_verifier):
        """测试不相关文本的相似度计算"""
        text1 = "人工智能是计算机科学的重要分支"
        text2 = "区块链是分布式账本技术的创新应用"
        
        similarity = sample_verifier._calculate_similarity(text1, text2)
        assert similarity < 0.3, "不相关文本应该有很低的相似度"

    def test_calculate_similarity_with_key_terms(self, sample_verifier):
        """测试包含关键术语的文本相似度"""
        text1 = "人工智能技术"
        text2 = "机器学习技术"
        
        similarity = sample_verifier._calculate_similarity(text1, text2)
        # 由于都包含AI相关术语和技术，应该有中等相似度
        assert similarity > 0.1, "包含相关关键术语的文本应该有中等相似度"

    def test_calculate_similarity_edge_cases(self, sample_verifier):
        """测试边界情况的相似度计算"""
        # 单字符文本
        similarity = sample_verifier._calculate_similarity("a", "b")
        assert similarity == 0.0, "单字符不同文本应该有0.0相似度"
        
        # 空文本
        similarity = sample_verifier._calculate_similarity("", "人工智能")
        assert similarity == 0.0, "空文本应该有0.0相似度"

    def test_similarity_consistency(self, sample_verifier):
        """测试相似度计算的一致性"""
        text1 = "人工智能技术"
        text2 = "人工技术"
        
        similarity1 = sample_verifier._calculate_similarity(text1, text2)
        similarity2 = sample_verifier._calculate_similarity(text2, text1)
        
        assert similarity1 == similarity2, "相似度计算应该是对称的"

    def test_similarity_with_special_characters(self, sample_verifier):
        """测试包含特殊字符的相似度计算"""
        text1 = "人工智能-机器学习"
        text2 = "人工智能 机器学习"
        
        similarity = sample_verifier._calculate_similarity(text1, text2)
        assert similarity > 0.5, "相同内容不同格式应该有高相似度"

    def test_are_words_similar_various_cases(self, sample_verifier):
        """测试各种情况的词相似性判断"""
        # 完全相同
        assert sample_verifier._are_words_similar("人工智能", "人工智能")
        
        # 子串关系
        assert sample_verifier._are_words_similar("人工智能", "人工")
        assert sample_verifier._are_words_similar("机器学习", "学习")
        
        # 完全不同
        assert not sample_verifier._are_words_similar("人工智能", "区块链")
        
        # 短词相似性
        assert sample_verifier._are_words_similar("AI", "AI技术")
        
        # 空词
        assert not sample_verifier._are_words_similar("", "人工智能")
        assert not sample_verifier._are_words_similar("人工智能", "")