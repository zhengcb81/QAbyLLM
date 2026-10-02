#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
关键词匹配功能单元测试
"""

import pytest
from answer_verifier import AnswerVerifier


class TestKeywordMatching:
    """关键词匹配功能测试类"""

    def test_extract_significant_keywords_basic(self, sample_verifier):
        """测试基础关键词提取"""
        text = "人工智能是计算机科学的重要分支，机器学习是其核心技术"
        keywords = sample_verifier._extract_significant_keywords(text)
        
        assert len(keywords) > 0, "应该能从文本中提取到关键词"
        assert "人工智能" in keywords, "应该包含人工智能关键词"
        assert "计算机科学" in keywords, "应该包含计算机科学关键词"
        assert "机器学习" in keywords, "应该包含机器学习关键词"
        
        # 应该过滤停用词
        assert "是" not in keywords, "应该过滤停用词"
        assert "的" not in keywords, "应该过滤停用词"

    def test_extract_significant_keywords_empty_input(self, sample_verifier):
        """测试空输入的关键词提取"""
        keywords = sample_verifier._extract_significant_keywords("")
        assert len(keywords) == 0, "空输入应该返回空关键词集合"

    def test_extract_significant_keywords_short_text(self, sample_verifier):
        """测试短文本的关键词提取"""
        keywords = sample_verifier._extract_significant_keywords("测试")
        assert len(keywords) == 0, "过短的文本应该返回空关键词集合"

    def test_extract_significant_keywords_with_punctuation(self, sample_verifier):
        """测试带标点符号的文本关键词提取"""
        text = "人工智能，包括机器学习、深度学习，是计算机科学的重要领域。自然语言处理也很重要！"
        keywords = sample_verifier._extract_significant_keywords(text)
        
        assert "人工智能" in keywords
        assert "机器学习" in keywords
        assert "深度学习" in keywords
        assert "计算机科学" in keywords
        assert "自然语言处理" in keywords

    def test_calculate_keyword_overlap_exact_match(self, sample_verifier):
        """测试精确匹配的关键词重叠计算"""
        keywords1 = {"人工智能", "机器学习", "计算机科学"}
        keywords2 = {"人工智能", "机器学习", "深度学习"}
        
        overlap = sample_verifier._calculate_keyword_overlap(keywords1, keywords2)
        
        assert len(overlap) == 2, "应该找到2个精确匹配的关键词"
        assert "人工智能" in overlap
        assert "机器学习" in overlap
        assert "深度学习" not in overlap

    def test_calculate_keyword_overlap_no_match(self, sample_verifier):
        """测试无匹配的关键词重叠计算"""
        keywords1 = {"人工智能", "机器学习"}
        keywords2 = {"区块链", "物联网"}
        
        overlap = sample_verifier._calculate_keyword_overlap(keywords1, keywords2)
        assert len(overlap) == 0, "没有匹配的关键词应该返回空集合"

    def test_calculate_keyword_overlap_fuzzy_match(self, sample_verifier):
        """测试模糊匹配的关键词重叠计算"""
        keywords1 = {"人工智能技术", "机器学习算法"}
        keywords2 = {"人工智能", "机器学习"}
        
        overlap = sample_verifier._calculate_keyword_overlap(keywords1, keywords2)
        
        # 应该找到模糊匹配的关键词
        assert len(overlap) > 0, "应该找到模糊匹配的关键词"

    def test_are_words_similar_exact(self, sample_verifier):
        """测试精确相似的词判断"""
        assert sample_verifier._are_words_similar("人工智能", "人工智能")

    def test_are_words_similar_substring(self, sample_verifier):
        """测试子串相似的词判断"""
        assert sample_verifier._are_words_similar("人工智能", "人工")
        assert sample_verifier._are_words_similar("机器学习", "学习")

    def test_are_words_similar_different(self, sample_verifier):
        """测试不同词的相似性判断"""
        assert not sample_verifier._are_words_similar("人工智能", "区块链")
        assert not sample_verifier._are_words_similar("机器学习", "物联网")

    def test_check_answer_source_alignment_valid(self, sample_verifier, sample_answer, sample_sources):
        """测试有效的答案-来源一致性检查"""
        alignment = sample_verifier._check_answer_source_alignment(sample_answer, sample_sources)
        assert alignment, "有效的答案和来源应该通过一致性检查"

    def test_check_answer_source_alignment_invalid(self, sample_verifier):
        """测试无效的答案-来源一致性检查"""
        answer = "区块链技术是未来互联网的发展方向"
        sources = [{
            'content': '人工智能是计算机科学的重要分支',
            'title': 'AI概述'
        }]
        
        alignment = sample_verifier._check_answer_source_alignment(answer, sources)
        assert not alignment, "不相关的答案和来源应该不通过一致性检查"

    def test_check_answer_source_alignment_no_sources(self, sample_verifier, sample_answer):
        """测试无来源的一致性检查"""
        alignment = sample_verifier._check_answer_source_alignment(sample_answer, [])
        assert alignment, "没有来源时应该默认通过一致性检查"

    def test_is_answer_consistent_with_context_valid(self, sample_verifier, sample_answer):
        """测试有效的答案-上下文一致性检查"""
        context_info = {
            'keywords': {"人工智能", "计算机科学", "机器学习"}
        }
        
        consistent = sample_verifier._is_answer_consistent_with_context(sample_answer, context_info)
        assert consistent, "相关的答案和上下文应该通过一致性检查"

    def test_is_answer_consistent_with_context_invalid(self, sample_verifier):
        """测试无效的答案-上下文一致性检查"""
        answer = "区块链技术是未来互联网的发展方向"
        context_info = {
            'keywords': {"人工智能", "计算机科学"}
        }
        
        consistent = sample_verifier._is_answer_consistent_with_context(answer, context_info)
        assert not consistent, "不相关的答案和上下文应该不通过一致性检查"

    def test_is_answer_consistent_with_context_no_keywords(self, sample_verifier, sample_answer):
        """测试无关键词的上下文一致性检查"""
        context_info = {'keywords': set()}
        
        consistent = sample_verifier._is_answer_consistent_with_context(sample_answer, context_info)
        assert consistent, "没有上下文关键词时应该默认通过一致性检查"

    def test_contains_contradiction_detection(self, sample_verifier):
        """测试矛盾检测功能"""
        # 包含矛盾指示词
        content = "人工智能不是计算机科学的分支"
        fact = "人工智能是计算机科学的分支"
        
        has_contradiction = sample_verifier._contains_contradiction(content, fact)
        assert has_contradiction, "应该检测到矛盾"
        
        # 不包含矛盾指示词
        content2 = "人工智能是重要的技术领域"
        has_contradiction2 = sample_verifier._contains_contradiction(content2, fact)
        assert not has_contradiction2, "不应该检测到矛盾"

    def test_assess_source_reliability(self, sample_verifier):
        """测试来源可靠性评估"""
        # 学术来源
        academic_source = {
            'type': 'academic',
            'domain': 'edu.example.com'
        }
        reliability = sample_verifier._assess_source_reliability(academic_source)
        assert reliability > 0.8, "学术来源应该有高可靠性"
        
        # 博客来源
        blog_source = {
            'type': 'blog',
            'domain': 'blog.example.com'
        }
        reliability2 = sample_verifier._assess_source_reliability(blog_source)
        assert reliability2 < 0.8, "博客来源应该有较低可靠性"

    def test_extract_context_information(self, sample_verifier, sample_context):
        """测试上下文信息提取"""
        context_info = sample_verifier._extract_context_information(sample_context)
        
        assert 'keywords' in context_info
        assert len(context_info['keywords']) > 0
        assert "人工智能" in context_info['keywords']
        assert "机器人" in context_info['keywords']
        assert "语言识别" in context_info['keywords']