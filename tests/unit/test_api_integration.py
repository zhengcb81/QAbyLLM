#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API集成功能单元测试
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from answer_verifier import AnswerVerifier
import aiohttp


class TestAPIIntegration:
    """API集成功能测试类"""

    @pytest.mark.asyncio
    async def test_fact_check_api_successful_call(self, sample_verifier):
        """测试成功的事实检查API调用"""
        # 配置API密钥
        sample_verifier.fact_check_api = "test_api_key"
        
        # 模拟成功的API响应
        mock_response = {
            'claims': [{
                'claimReview': [{
                    'textualRating': 'true'
                }]
            }]
        }
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value.status = 200
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            
            result = await sample_verifier._check_with_fact_check_api("测试事实")
            
            assert result is not None
            assert result['is_supported'] is True
            assert result['confidence'] > 0.8

    @pytest.mark.asyncio
    async def test_fact_check_api_false_rating(self, sample_verifier):
        """测试API返回false评分"""
        sample_verifier.fact_check_api = "test_api_key"
        
        mock_response = {
            'claims': [{
                'claimReview': [{
                    'textualRating': 'false'
                }]
            }]
        }
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value.status = 200
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            
            result = await sample_verifier._check_with_fact_check_api("测试事实")
            
            assert result is not None
            assert result['is_contradictory'] is True

    @pytest.mark.asyncio
    async def test_fact_check_api_no_claims(self, sample_verifier):
        """测试API无返回claims"""
        sample_verifier.fact_check_api = "test_api_key"
        
        mock_response = {'claims': []}
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value.status = 200
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            
            result = await sample_verifier._check_with_fact_check_api("测试事实")
            
            assert result is not None
            assert result['confidence'] == 0.6

    @pytest.mark.asyncio
    async def test_fact_check_api_http_error(self, sample_verifier):
        """测试API HTTP错误"""
        sample_verifier.fact_check_api = "test_api_key"
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value.status = 500
            
            result = await sample_verifier._check_with_fact_check_api("测试事实")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_fact_check_api_timeout(self, sample_verifier):
        """测试API超时"""
        sample_verifier.fact_check_api = "test_api_key"
        
        with patch('aiohttp.ClientSession.get', side_effect=aiohttp.ClientTimeout()):
            result = await sample_verifier._check_with_fact_check_api("测试事实")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_fact_check_api_no_api_key(self, sample_verifier):
        """测试无API密钥的情况"""
        sample_verifier.fact_check_api = None
        
        result = await sample_verifier._check_with_fact_check_api("测试事实")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_check_single_fact_with_api_success(self, sample_verifier):
        """测试使用API的单事实检查"""
        sample_verifier.fact_check_api = "test_api_key"
        
        mock_response = {
            'claims': [{
                'claimReview': [{
                    'textualRating': 'true'
                }]
            }]
        }
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value.status = 200
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            
            result = await sample_verifier._check_single_fact("测试事实", None)
            
            assert result['is_supported'] is True

    @pytest.mark.asyncio
    async def test_check_single_fact_api_fallback(self, sample_verifier):
        """测试API失败时的回退机制"""
        sample_verifier.fact_check_api = "test_api_key"
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value.status = 500
            
            # 模拟本地知识库验证
            with patch.object(sample_verifier, '_check_with_local_knowledge', 
                            AsyncMock(return_value={
                                'is_supported': True,
                                'is_contradictory': False,
                                'evidence': '本地验证',
                                'confidence': 0.8
                            })):
                
                result = await sample_verifier._check_single_fact("测试事实", None)
                
                assert result['is_supported'] is True

    @pytest.mark.asyncio
    async def test_check_single_fact_exception_handling(self, sample_verifier):
        """测试异常处理"""
        sample_verifier.fact_check_api = "test_api_key"
        
        with patch('aiohttp.ClientSession.get', side_effect=Exception("测试异常")):
            result = await sample_verifier._check_single_fact("测试事实", None)
            
            assert result['confidence'] == 0.5
            assert '验证失败' in result['evidence'] or '无法验证' in result['evidence']

    def test_parse_fact_check_api_response_true_rating(self, sample_verifier):
        """测试解析true评分"""
        response_data = {
            'claims': [{
                'claimReview': [{
                    'textualRating': 'true'
                }]
            }]
        }
        
        result = sample_verifier._parse_fact_check_api_response(response_data, "测试事实")
        
        assert result['is_supported'] is True
        assert result['is_contradictory'] is False

    def test_parse_fact_check_api_response_false_rating(self, sample_verifier):
        """测试解析false评分"""
        response_data = {
            'claims': [{
                'claimReview': [{
                    'textualRating': 'false'
                }]
            }]
        }
        
        result = sample_verifier._parse_fact_check_api_response(response_data, "测试事实")
        
        assert result['is_supported'] is False
        assert result['is_contradictory'] is True

    def test_parse_fact_check_api_response_misleading_rating(self, sample_verifier):
        """测试解析misleading评分"""
        response_data = {
            'claims': [{
                'claimReview': [{
                    'textualRating': 'misleading'
                }]
            }]
        }
        
        result = sample_verifier._parse_fact_check_api_response(response_data, "测试事实")
        
        assert result['is_supported'] is False
        assert result['is_contradictory'] is True

    def test_parse_fact_check_api_response_no_clear_conclusion(self, sample_verifier):
        """测试解析无明确结论"""
        response_data = {
            'claims': [{
                'claimReview': [{
                    'textualRating': 'unverified'
                }]
            }]
        }
        
        result = sample_verifier._parse_fact_check_api_response(response_data, "测试事实")
        
        assert result['confidence'] == 0.6

    def test_parse_fact_check_api_response_empty_claims(self, sample_verifier):
        """测试解析空claims"""
        response_data = {'claims': []}
        
        result = sample_verifier._parse_fact_check_api_response(response_data, "测试事实")
        
        assert result['confidence'] == 0.6

    def test_parse_fact_check_api_response_missing_claim_review(self, sample_verifier):
        """测试解析缺失claimReview"""
        response_data = {
            'claims': [{}]
        }
        
        result = sample_verifier._parse_fact_check_api_response(response_data, "测试事实")
        
        assert result['confidence'] == 0.6