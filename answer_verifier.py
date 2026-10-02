#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
答案验证系统
验证LLM生成答案的准确性和可信度
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime
from enum import Enum
import re
import json
from dataclasses import dataclass

# 导入结构化日志系统
try:
    from logging_config import get_logger, log_verification_result
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

class VerificationLevel(Enum):
    """验证级别枚举"""
    HIGH = "high"      # 高度可信
    MEDIUM = "medium"  # 中等可信
    LOW = "low"        # 低可信度
    UNVERIFIED = "unverified"  # 未验证

class VerificationMethod(Enum):
    """验证方法枚举"""
    FACT_CHECK = "fact_check"      # 事实检查
    SOURCE_VALIDATION = "source_validation"  # 来源验证
    CONSISTENCY_CHECK = "consistency_check"  # 一致性检查
    EXPERT_ASSESSMENT = "expert_assessment"  # 专家评估
    CROSS_REFERENCE = "cross_reference"      # 交叉参考

@dataclass
class VerificationResult:
    """验证结果"""
    is_verified: bool
    confidence: float  # 0.0 - 1.0
    verification_level: VerificationLevel
    methods_used: List[VerificationMethod]
    issues_found: List[str]
    supporting_evidence: List[Dict[str, Any]]
    contradictory_evidence: List[Dict[str, Any]]
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'is_verified': self.is_verified,
            'confidence': self.confidence,
            'verification_level': self.verification_level.value,
            'methods_used': [method.value for method in self.methods_used],
            'issues_found': self.issues_found,
            'supporting_evidence': self.supporting_evidence,
            'contradictory_evidence': self.contradictory_evidence,
            'timestamp': self.timestamp
        }

class AnswerVerifier:
    """答案验证器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 使用配置管理器获取配置值
        from config_manager import ConfigManager
        self.config_manager = ConfigManager()
        
        self.enabled_methods = self.config.get('enabled_methods', 
            self.config_manager.get_enabled_verification_methods())
        self.min_confidence = self.config.get('min_confidence', 
            self.config_manager.get_verification_threshold('min_confidence', 0.7))
        self.fact_check_api = self.config.get('fact_check_api')
        self.expert_knowledge_base = self.config.get('expert_knowledge_base', 
            self.config_manager.get_expert_knowledge_base())
    
    async def verify_answer(self, 
                          answer: str, 
                          question: str, 
                          context: Optional[List[Dict[str, Any]]] = None,
                          sources: Optional[List[Dict[str, Any]]] = None) -> VerificationResult:
        """验证答案"""
        start_time = datetime.now()
        
        methods_used = []
        issues_found = []
        supporting_evidence = []
        contradictory_evidence = []
        
        # 执行各种验证方法
        confidence_scores = []
        
        # 事实检查
        if 'fact_check' in self.enabled_methods:
            fact_result = await self._fact_check(answer, question, context)
            confidence_scores.append(fact_result['confidence'])
            methods_used.append(VerificationMethod.FACT_CHECK)
            issues_found.extend(fact_result['issues'])
            supporting_evidence.extend(fact_result['supporting_evidence'])
            contradictory_evidence.extend(fact_result['contradictory_evidence'])
            
            # 调试信息：显示提取的事实
            facts = self._extract_facts(answer)
            print(f"DEBUG: Extracted {len(facts)} facts: {facts}")
        
        # 来源验证
        if 'source_validation' in self.enabled_methods and sources:
            source_result = self._validate_sources(answer, sources)
            confidence_scores.append(source_result['confidence'])
            methods_used.append(VerificationMethod.SOURCE_VALIDATION)
            issues_found.extend(source_result['issues'])
            supporting_evidence.extend(source_result['supporting_evidence'])
            contradictory_evidence.extend(source_result['contradictory_evidence'])
        else:
            # 没有来源时给予中等置信度
            confidence_scores.append(0.7)
        
        # 一致性检查
        if 'consistency_check' in self.enabled_methods and context:
            consistency_result = self._check_consistency(answer, context)
            confidence_scores.append(consistency_result['confidence'])
            methods_used.append(VerificationMethod.CONSISTENCY_CHECK)
            issues_found.extend(consistency_result['issues'])
        else:
            # 没有上下文时给予中等置信度
            confidence_scores.append(0.7)
        
        # 专家评估
        if 'expert_assessment' in self.enabled_methods:
            expert_result = self._expert_assessment(answer, question)
            confidence_scores.append(expert_result['confidence'])
            methods_used.append(VerificationMethod.EXPERT_ASSESSMENT)
            issues_found.extend(expert_result['issues'])
        
        # 交叉参考验证
        if 'cross_reference' in self.enabled_methods:
            cross_ref_result = await self._cross_reference_check(answer, question, context, sources)
            confidence_scores.append(cross_ref_result['confidence'])
            methods_used.append(VerificationMethod.CROSS_REFERENCE)
            issues_found.extend(cross_ref_result['issues'])
            supporting_evidence.extend(cross_ref_result['supporting_evidence'])
            contradictory_evidence.extend(cross_ref_result['contradictory_evidence'])
        else:
            # 没有交叉参考时给予中等置信度
            confidence_scores.append(0.7)
        
        # 计算总体置信度
        if confidence_scores:
            overall_confidence = sum(confidence_scores) / len(confidence_scores)
        else:
            overall_confidence = 0.5  # 默认中等置信度
        
        # 确定验证级别
        verification_level = self._determine_verification_level(overall_confidence, issues_found)
        
        # 检查是否通过验证
        is_verified = (overall_confidence >= self.min_confidence and 
                      verification_level != VerificationLevel.LOW)
        
        result = VerificationResult(
            is_verified=is_verified,
            confidence=overall_confidence,
            verification_level=verification_level,
            methods_used=methods_used,
            issues_found=issues_found,
            supporting_evidence=supporting_evidence,
            contradictory_evidence=contradictory_evidence,
            timestamp=datetime.now().isoformat()
        )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # 添加处理时间到结果对象以便日志记录
        result.processing_time = processing_time
        
        # 使用结构化日志记录验证结果
        try:
            log_verification_result(logger, result, question, answer)
        except:
            # 回退到简单日志
            logger.info(f"答案验证完成: 置信度 {overall_confidence:.2f}, 耗时: {processing_time:.2f}秒")
        
        return result
    
    async def _fact_check(self, answer: str, question: str, context: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """事实检查"""
        # 提取可验证的事实陈述
        facts = self._extract_facts(answer)
        
        issues = []
        supporting_evidence = []
        contradictory_evidence = []
        confidence = 1.0  # 初始置信度
        
        if not facts:
            # 对于空答案或非常短的答案，给予较低置信度并添加问题
            if len(answer.strip()) <= 2:  # 空或非常短的答案
                confidence = 0.4
                if not answer.strip():  # 完全空的答案
                    issues.append("答案为空，无法验证具体内容")
                else:
                    issues.append("答案过短，缺乏具体事实内容")
            else:
                confidence = 0.8  # 没有具体事实但答案有一定长度，相对安全
            
            return {
                'confidence': confidence,
                'issues': issues,
                'supporting_evidence': supporting_evidence,
                'contradictory_evidence': contradictory_evidence
            }
        
        # 检查每个事实
        for fact in facts:
            # 这里可以集成事实检查API或本地知识库
            fact_result = await self._check_single_fact(fact, context)
            print(f"DEBUG: Fact check result - Fact: {fact}")
            print(f"DEBUG:  Supported: {fact_result['is_supported']}, Contradictory: {fact_result['is_contradictory']}, Confidence: {fact_result['confidence']}")
            print(f"DEBUG:  Evidence: {fact_result['evidence']}")
            
            if fact_result['is_contradictory']:
                issues.append(f"事实矛盾: {fact}")
                contradictory_evidence.append({
                    'fact': fact,
                    'contradiction': fact_result['evidence']
                })
                confidence *= 0.7  # 每个矛盾事实降低置信度
            elif fact_result['is_supported']:
                supporting_evidence.append({
                    'fact': fact,
                    'support': fact_result['evidence']
                })
            else:
                # 无法验证的事实
                issues.append(f"无法验证的事实: {fact}")
                confidence *= 0.9  # 轻微降低置信度
        
        return {
            'confidence': confidence,
            'issues': issues,
            'supporting_evidence': supporting_evidence,
            'contradictory_evidence': contradictory_evidence
        }
    
    def _validate_sources(self, answer: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """验证来源"""
        issues = []
        supporting_evidence = []
        contradictory_evidence = []
        confidence = 1.0
        
        # 检查来源可靠性
        reliable_sources = 0
        total_sources = len(sources)
        
        for source in sources:
            source_reliability = self._assess_source_reliability(source)
            
            if source_reliability >= 0.7:
                reliable_sources += 1
                supporting_evidence.append({
                    'source': source,
                    'reliability_score': source_reliability
                })
            else:
                issues.append(f"来源可靠性低: {source.get('url', '未知来源')}")
                confidence *= 0.8
        
        # 计算来源可靠性分数
        if total_sources > 0:
            source_confidence = reliable_sources / total_sources
            confidence *= source_confidence
        
        # 检查答案是否与来源一致
        source_alignment = self._check_answer_source_alignment(answer, sources)
        if not source_alignment:
            issues.append("答案与来源内容不一致")
            confidence *= 0.6
        print(f"DEBUG: Answer-source alignment: {source_alignment}")
        
        return {
            'confidence': confidence,
            'issues': issues,
            'supporting_evidence': supporting_evidence,
            'contradictory_evidence': contradictory_evidence
        }
    
    def _check_consistency(self, answer: str, context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """检查一致性"""
        issues = []
        confidence = 1.0
        
        # 提取上下文中的关键信息
        context_info = self._extract_context_information(context)
        
        # 检查答案是否与上下文一致
        context_consistency = self._is_answer_consistent_with_context(answer, context_info)
        if not context_consistency:
            issues.append("答案与上下文信息不一致")
            confidence = 0.8  # 更宽松的惩罚，因为上下文可能包含具体应用而答案是通用概念
        print(f"DEBUG: Answer-context consistency: {context_consistency}")
        
        # 检查答案内部一致性
        if not self._is_answer_internally_consistent(answer):
            issues.append("答案内部存在矛盾")
            confidence *= 0.7
        
        return {
            'confidence': confidence,
            'issues': issues,
            'supporting_evidence': [],
            'contradictory_evidence': []
        }
    
    def _expert_assessment(self, answer: str, question: str) -> Dict[str, Any]:
        """专家评估"""
        issues = []
        confidence = 0.8  # 默认中等置信度
        
        # 检查答案质量
        quality_issues = self._assess_answer_quality(answer, question)
        issues.extend(quality_issues)
        
        # 每个质量问题降低置信度
        for _ in quality_issues:
            confidence *= 0.9
        
        # 检查专业知识匹配
        if not self._check_expertise_match(answer, question):
            issues.append("答案可能缺乏专业深度")
            confidence *= 0.8
        
        return {
            'confidence': confidence,
            'issues': issues,
            'supporting_evidence': [],
            'contradictory_evidence': []
        }
    
    async def _cross_reference_check(self, answer: str, question: str, 
                                   context: Optional[List[Dict[str, Any]]], 
                                   sources: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """交叉参考验证"""
        issues = []
        supporting_evidence = []
        contradictory_evidence = []
        confidence = 1.0
        
        # 提取答案中的关键主张
        claims = self._extract_claims(answer)
        
        if not claims:
            return {
                'confidence': 0.8,
                'issues': issues,
                'supporting_evidence': supporting_evidence,
                'contradictory_evidence': contradictory_evidence
            }
        
        # 验证每个主张
        verified_claims = 0
        total_claims = len(claims)
        
        for claim in claims:
            # 检查多个来源的一致性
            verification_results = []
            
            # 检查上下文
            if context:
                context_result = self._verify_claim_in_context(claim, context)
                verification_results.append(context_result)
            
            # 检查来源
            if sources:
                source_result = self._verify_claim_in_sources(claim, sources)
                verification_results.append(source_result)
            
            # 检查知识库
            if self.expert_knowledge_base:
                kb_result = self._verify_claim_in_knowledge_base(claim)
                verification_results.append(kb_result)
            
            # 评估验证结果
            if verification_results:
                claim_verified = sum(r['confidence'] for r in verification_results) / len(verification_results) >= 0.6
                if claim_verified:
                    verified_claims += 1
                    supporting_evidence.append({
                        'claim': claim,
                        'sources': [r['evidence'] for r in verification_results if r['confidence'] > 0.6]
                    })
                else:
                    issues.append(f"主张无法验证: {claim}")
                    confidence *= 0.8
            else:
                issues.append(f"主张无验证来源: {claim}")
                confidence *= 0.7
        
        # 计算交叉验证置信度
        if total_claims > 0:
            cross_ref_confidence = verified_claims / total_claims
            confidence *= cross_ref_confidence
        
        return {
            'confidence': confidence,
            'issues': issues,
            'supporting_evidence': supporting_evidence,
            'contradictory_evidence': contradictory_evidence
        }
    
    def _extract_claims(self, answer: str) -> List[str]:
        """提取答案中的关键主张"""
        # 更精细的主张提取模式
        claim_patterns = [
            r'([^。！？]+(?:应该|必须|需要|建议|推荐)[^。！？]+)',
            r'([^。！？]+(?:导致|造成|引起|影响)[^。！？]+)',
            r'([^。！？]+(?:证明|表明|显示|说明)[^。！？]+)',
            r'([^。！？]+(?:优于|胜过|好于|比.*更好)[^。！？]+)',
            r'([^。！？]+(?:解决方案|方法|策略|措施)[^。！？]+)'
        ]
        
        claims = []
        for pattern in claim_patterns:
            matches = re.findall(pattern, answer)
            claims.extend(matches)
        
        # 去重和过滤
        claims = list(set(claims))
        claims = [claim.strip() for claim in claims if len(claim) > 5 and len(claim) < 200]
        
        return claims
    
    def _verify_claim_in_context(self, claim: str, context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """在上下文中验证主张"""
        claim_keywords = set(re.findall(r'\w+', claim.lower()))
        
        for item in context:
            if 'content' in item:
                content = item['content'].lower()
                content_keywords = set(re.findall(r'\w+', content))
                
                # 检查关键词重叠
                overlap = claim_keywords.intersection(content_keywords)
                if len(overlap) >= len(claim_keywords) * 0.4:  # 40%关键词匹配
                    return {
                        'confidence': 0.7,
                        'evidence': f"上下文支持: {content[:100]}..."
                    }
        
        return {
            'confidence': 0.3,
            'evidence': '上下文中未找到相关支持'
        }
    
    def _verify_claim_in_sources(self, claim: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """在来源中验证主张"""
        claim_keywords = set(re.findall(r'\w+', claim.lower()))
        
        for source in sources:
            source_content = source.get('content', '').lower()
            source_keywords = set(re.findall(r'\w+', source_content))
            
            # 检查关键词重叠
            overlap = claim_keywords.intersection(source_keywords)
            if len(overlap) >= len(claim_keywords) * 0.4:  # 40%关键词匹配
                source_reliability = self._assess_source_reliability(source)
                confidence = 0.5 + (source_reliability * 0.5)  # 基于来源可靠性调整置信度
                
                return {
                    'confidence': min(confidence, 0.9),
                    'evidence': f"来源支持: {source.get('title', '未知来源')}"
                }
        
        return {
            'confidence': 0.3,
            'evidence': '来源中未找到相关支持'
        }
    
    def _verify_claim_in_knowledge_base(self, claim: str) -> Dict[str, Any]:
        """在知识库中验证主张"""
        claim_lower = claim.lower()
        
        for kb_claim, kb_info in self.expert_knowledge_base.items():
            if (kb_claim.lower() in claim_lower or 
                claim_lower in kb_claim.lower() or 
                self._calculate_similarity(claim_lower, kb_claim.lower()) > 0.6):
                
                return {
                    'confidence': kb_info.get('confidence', 0.8),
                    'evidence': f"知识库匹配: {kb_info.get('evidence', kb_claim[:50])}"
                }
        
        return {
            'confidence': 0.3,
            'evidence': '知识库中未找到相关信息'
        }
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        # 改进的相似度计算，针对中文优化
        if not text1 or not text2:
            return 0.0
        
        # 对于短文本，使用Jaccard相似度
        if len(text1) < 10 or len(text2) < 10:
            return self._jaccard_similarity(text1, text2)
        
        # 对于长文本，使用词级相似度
        return self._word_based_similarity(text1, text2)
    
    def _jaccard_similarity(self, text1: str, text2: str) -> float:
        """Jaccard相似度"""
        # 使用字符级别的2-gram
        def get_ngrams(text, n=2):
            return set(text[i:i+n] for i in range(len(text) - n + 1))
        
        ngrams1 = get_ngrams(text1, 2)
        ngrams2 = get_ngrams(text2, 2)
        
        if not ngrams1 or not ngrams2:
            return 0.0
        
        intersection = ngrams1.intersection(ngrams2)
        union = ngrams1.union(ngrams2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _word_based_similarity(self, text1: str, text2: str) -> float:
        """基于词的相似度计算"""
        # 中文分词（简单实现）
        def chinese_segment(text):
            # 简单的基于规则的中文分词
            # 实际应用中应该使用jieba等分词库
            words = []
            i = 0
            while i < len(text):
                # 尝试匹配2-4字符的词
                found = False
                for length in range(4, 1, -1):
                    if i + length <= len(text):
                        word = text[i:i+length]
                        # 检查是否是常见的中文词（简单判断）
                        if len(word) >= 2 and any(c in word for c in ['是', '有', '为', '的', '了', '在', '和']):
                            words.append(word)
                            i += length
                            found = True
                            break
                if not found:
                    words.append(text[i])
                    i += 1
            return words
        
        words1 = chinese_segment(text1)
        words2 = chinese_segment(text2)
        
        if not words1 or not words2:
            return 0.0
        
        # 计算词级Jaccard相似度
        set1 = set(words1)
        set2 = set(words2)
        
        intersection = set1.intersection(set2)
        union = set1.union(set2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _extract_facts(self, answer: str) -> List[str]:
        """提取可验证的事实陈述"""
        # 首先按句子分割
        sentences = re.split(r'[。！？,.!?]+', answer)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]
        
        facts = []
        
        # 从每个句子中提取核心事实
        for sentence in sentences:
            # 更智能的事实提取条件
            if self._is_potential_fact(sentence):
                # 提取核心事实陈述（去除修饰语）
                core_fact = self._extract_core_fact(sentence)
                if core_fact and self._is_complete_fact(core_fact):
                    facts.append(core_fact)
        
        # 去重
        facts = list(set(facts))
        
        return facts
    
    def _is_potential_fact(self, text: str) -> bool:
        """检查是否是潜在的事实陈述"""
        # 排除疑问句、感叹句等
        if any(marker in text for marker in ['?', '？', '!', '！', '吗', '呢', '啊', '什么', '为什么', '如何']):
            return False
        
        # 排除包含模糊词的陈述
        vague_words = self.config_manager.get_vague_words()
        if any(word in text for word in vague_words):
            return False
        
        # 检查长度
        if len(text) < 6 or len(text) > 150:
            return False
            
        # 检查是否包含事实性内容
        factual_indicators = self.config_manager.get_factual_indicators()
        return any(indicator in text for indicator in factual_indicators)
    
    def _extract_core_fact(self, sentence: str) -> str:
        """提取句子的核心事实部分"""
        # 从配置管理器获取修饰词和连接词
        modifiers = self.config_manager.get_modifiers()
        connectors = self.config_manager.get_connectors()
        
        # 中文文本处理：逐个字符检查而不是按空格分割
        result = sentence
        for modifier in modifiers + connectors:
            result = result.replace(modifier, '')
        
        # 清理多余的空格
        result = re.sub(r'\s+', ' ', result).strip()
        
        return result
    
    def _is_complete_fact(self, text: str) -> bool:
        """检查是否是完整的事实陈述"""
        # 排除疑问句、感叹句等
        if any(marker in text for marker in ['?', '？', '!', '！', '吗', '呢', '啊']):
            return False
        
        # 排除包含模糊词的陈述
        vague_words = self.config_manager.get_vague_words()
        if any(word in text for word in vague_words):
            return False
        
        # 检查句子结构完整性
        if len(text) < 6 or len(text) > 120:  # 放宽长度限制
            return False
            
        # 检查是否包含核心事实要素
        factual_indicators = self.config_manager.get_factual_indicators()
        has_subject = any(keyword in text for keyword in factual_indicators)
        has_content = len(text) >= 4  # 中文文本：至少4个字符视为有内容
        
        return has_subject or has_content  # 放宽条件：有主语或有内容即可
    
    async def _check_single_fact(self, fact: str, context: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """检查单个事实"""
        try:
            # 首先尝试使用外部事实检查API
            if self.fact_check_api:
                api_result = await self._check_with_fact_check_api(fact)
                if api_result:
                    return api_result
            
            # 如果没有API或API失败，使用本地知识库和上下文验证
            return await self._check_with_local_knowledge(fact, context)
            
        except Exception as e:
            logger.warning(f"事实检查失败: {e}")
            # 失败时返回中性结果
            return {
                'is_supported': False,
                'is_contradictory': False,
                'evidence': f'验证失败: {e}',
                'confidence': 0.5
            }
    
    async def _check_with_fact_check_api(self, fact: str) -> Optional[Dict[str, Any]]:
        """使用外部事实检查API"""
        try:
            # 这里可以集成Google Fact Check Tools API或其他事实检查服务
            # 示例实现
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                # 模拟API调用
                # 实际使用时需要替换为真实API端点
                async with session.get(
                    f"https://factchecktools.googleapis.com/v1alpha1/claims:search",
                    params={'query': fact, 'key': self.fact_check_api},
                    timeout=10
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_fact_check_api_response(data, fact)
            
        except Exception as e:
            logger.warning(f"事实检查API调用失败: {e}")
            return None
    
    def _parse_fact_check_api_response(self, data: Dict[str, Any], fact: str) -> Dict[str, Any]:
        """解析事实检查API响应"""
        # 解析API响应，提取验证结果
        if data.get('claims') and len(data['claims']) > 0:
            claim = data['claims'][0]
            claim_review = claim.get('claimReview', [{}])[0]
            
            # 根据评分判断事实真伪
            rating = claim_review.get('textualRating', '').lower()
            
            if any(word in rating for word in ['false', 'incorrect', 'misleading']):
                return {
                    'is_supported': False,
                    'is_contradictory': True,
                    'evidence': f"事实检查API标记为: {rating}",
                    'confidence': 0.9
                }
            elif any(word in rating for word in ['true', 'correct', 'accurate']):
                return {
                    'is_supported': True,
                    'is_contradictory': False,
                    'evidence': f"事实检查API标记为: {rating}",
                    'confidence': 0.9
                }
        
        return {
            'is_supported': False,
            'is_contradictory': False,
            'evidence': '事实检查API无明确结论',
            'confidence': 0.6
        }
    
    async def _check_with_local_knowledge(self, fact: str, context: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """使用本地知识库和上下文验证事实"""
        # 检查专家知识库
        if self.expert_knowledge_base:
            kb_result = self._check_with_knowledge_base(fact)
            if kb_result['confidence'] > 0.7:
                return kb_result
        
        # 检查上下文一致性
        if context:
            context_result = self._check_with_context(fact, context)
            if context_result['confidence'] > 0.7:
                return context_result
        
        # 默认返回无法验证
        return {
            'is_supported': False,
            'is_contradictory': False,
            'evidence': '无法验证的事实陈述',
            'confidence': 0.5
        }
    
    def _check_with_knowledge_base(self, fact: str) -> Dict[str, Any]:
        """使用本地知识库验证"""
        fact_lower = fact.lower()
        
        # 首先尝试精确匹配
        for kb_fact, kb_info in self.expert_knowledge_base.items():
            kb_fact_lower = kb_fact.lower()
            
            # 精确匹配
            if fact_lower == kb_fact_lower:
                return {
                    'is_supported': kb_info.get('is_true', True),
                    'is_contradictory': not kb_info.get('is_true', True),
                    'evidence': f"知识库精确匹配: {kb_info.get('evidence', kb_fact)}",
                    'confidence': kb_info.get('confidence', 0.9)
                }
            
            # 包含匹配 - 更宽松的条件
            if (kb_fact_lower in fact_lower or 
                fact_lower in kb_fact_lower):
                
                return {
                    'is_supported': kb_info.get('is_true', True),
                    'is_contradictory': not kb_info.get('is_true', True),
                    'evidence': f"知识库包含匹配: {kb_info.get('evidence', kb_fact)}",
                    'confidence': kb_info.get('confidence', 0.8) * 0.8  # 相似度调整
                }
            
            # 相似度匹配 - 改进的相似度计算
            similarity = self._calculate_similarity(fact_lower, kb_fact_lower)
            print(f"DEBUG: Fact '{fact}' similarity with KB '{kb_fact}': {similarity:.2f}")
            
            # 使用改进的相似度阈值：对于包含关键术语的句子，降低阈值
            key_terms = ['机器学习', '人工智能', '计算机', '数据', '学习', '系统']
            has_key_terms = any(term in fact_lower for term in key_terms)
            
            similarity_threshold = 0.15 if has_key_terms else 0.2
            
            if similarity > similarity_threshold:
                return {
                    'is_supported': kb_info.get('is_true', True),
                    'is_contradictory': not kb_info.get('is_true', True),
                    'evidence': f"Knowledge base similarity match ({similarity:.2f}): {kb_info.get('evidence', kb_fact)}",
                    'confidence': kb_info.get('confidence', 0.7) * min(1.0, similarity * 2)  # 增强相似度权重
                }
        
        return {
            'is_supported': False,
            'is_contradictory': False,
            'evidence': '知识库中未找到相关信息',
            'confidence': 0.5
        }
    
    def _check_with_context(self, fact: str, context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """使用上下文验证事实"""
        # 改进的关键词提取，针对中文优化
        fact_keywords = self._extract_significant_keywords(fact)
        
        supporting_evidence = []
        contradictory_evidence = []
        
        for item in context:
            if 'content' in item:
                content = item['content']
                content_keywords = self._extract_significant_keywords(content)
                
                # 检查关键词重叠
                overlap = fact_keywords.intersection(content_keywords)
                if len(overlap) >= max(2, len(fact_keywords) * 0.3):  # 至少2个关键词或30%匹配
                    # 检查内容是否支持或矛盾
                    if self._contains_contradiction(content, fact):
                        contradictory_evidence.append(content[:200] + '...')
                    else:
                        supporting_evidence.append(content[:200] + '...')
        
        if contradictory_evidence:
            return {
                'is_supported': False,
                'is_contradictory': True,
                'evidence': f"Context contradiction: {contradictory_evidence[0]}",
                'confidence': 0.7
            }
        elif supporting_evidence:
            return {
                'is_supported': True,
                'is_contradictory': False,
                'evidence': f"Context support: {supporting_evidence[0]}",
                'confidence': 0.7
            }
        
        return {
            'is_supported': False,
            'is_contradictory': False,
            'evidence': 'No relevant evidence found in context',
            'confidence': 0.5
        }
    
    def _extract_significant_keywords(self, text: str) -> Set[str]:
        """提取有意义的关键词"""
        if not text:
            return set()
        
        # 从配置管理器获取停用词
        stop_words = set(self.config_manager.get_stop_words())
        
        # 改进的关键词提取：先按标点分割，再提取有意义的部分
        # 首先分割成短语
        phrases = re.split(r'[，,。！？!?；;\s]+', text)
        
        keywords = set()
        for phrase in phrases:
            phrase = phrase.strip()
            if len(phrase) < 2:
                continue
                
            # 提取名词性短语和关键术语
            # 使用更智能的提取：提取包含特定模式的部分
            key_terms = self.config_manager.get_factual_indicators()
            if any(keyword in phrase for keyword in key_terms):
                # 进一步清理短语
                clean_phrase = re.sub(r'[的地得着了过]', '', phrase)
                if len(clean_phrase) >= 2:
                    keywords.add(clean_phrase)
            
            # 也添加单个有意义的词
            words = re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{2,}', phrase)
            for word in words:
                if (word not in stop_words and 
                    len(word) >= 2 and 
                    not any(marker in word for marker in ['什么', '如何', '为什么', '哪个'])):
                    keywords.add(word)
        
        # 确保提取的是有意义的单个词或短语，而不是整个句子
        filtered_keywords = set()
        for keyword in keywords:
            # 如果关键词太长（可能是整个句子），尝试分割
            if len(keyword) > 10:
                # 尝试提取其中的关键术语
                for term in key_terms:
                    if term in keyword:
                        filtered_keywords.add(term)
                # 也添加单个有意义的词
                words_in_keyword = re.findall(r'[\u4e00-\u9fff]{2,}', keyword)
                for word in words_in_keyword:
                    if len(word) <= 8 and word not in stop_words and len(word) >= 2:  # 限制单个词长度
                        filtered_keywords.add(word)
            else:
                filtered_keywords.add(keyword)
        
        # 添加额外的关键术语提取
        for term in key_terms:
            if term in text and term not in filtered_keywords:
                filtered_keywords.add(term)
        
        # 确保关键术语被正确提取
        key_terms = self.config_manager.get_factual_indicators()
        for term in key_terms:
            if term in text and term not in filtered_keywords:
                filtered_keywords.add(term)
        
        # 过滤掉单个无意义的短词
        final_keywords = set()
        for keyword in filtered_keywords:
            # 检查是否是真正有意义的词（不是单个字符或过于通用的词）
            if (len(keyword) >= 2 and 
                keyword not in stop_words and
                not any(marker in keyword for marker in ['测试', '这个', '那个', '什么'])):
                final_keywords.add(keyword)
        
        return final_keywords
    
    def _calculate_keyword_overlap(self, keywords1: Set[str], keywords2: Set[str]) -> Set[str]:
        """计算关键词重叠，使用模糊匹配"""
        if not keywords1 or not keywords2:
            return set()
        
        # 精确匹配
        exact_matches = keywords1.intersection(keywords2)
        if exact_matches:
            return exact_matches
        
        # 模糊匹配：检查子串关系和相似性
        fuzzy_matches = set()
        
        for word1 in keywords1:
            for word2 in keywords2:
                # 子串关系
                if word1 in word2 or word2 in word1:
                    fuzzy_matches.add(word1)
                    fuzzy_matches.add(word2)
                # 相似词匹配（针对中文）
                elif self._are_words_similar(word1, word2):
                    fuzzy_matches.add(word1)
                    fuzzy_matches.add(word2)
        
        return fuzzy_matches
    
    def _are_words_similar(self, word1: str, word2: str) -> bool:
        """检查两个中文词是否相似"""
        if not word1 or not word2:
            return False
        
        # 对于短词，使用字符重叠
        if len(word1) <= 3 or len(word2) <= 3:
            overlap = set(word1).intersection(set(word2))
            return len(overlap) >= min(2, len(word1), len(word2))
        
        # 对于长词，使用改进的相似度计算
        similarity = self._calculate_similarity(word1, word2)
        return similarity > 0.4
    
    def _contains_contradiction(self, content: str, fact: str) -> bool:
        """检查内容是否包含矛盾"""
        contradiction_indicators = ['不是', '没有', '错误', '不', '否认', '反驳', '矛盾', '相反']
        return any(indicator in content for indicator in contradiction_indicators)
    
    def _assess_source_reliability(self, source: Dict[str, Any]) -> float:
        """评估来源可靠性"""
        # 简单的可靠性评估
        reliability = 0.7  # 基础分数
        
        # 根据来源类型调整
        source_type = source.get('type', '')
        if source_type in ['academic', 'government', 'official']:
            reliability += 0.2
        elif source_type in ['blog', 'forum', 'social']:
            reliability -= 0.2
        
        # 根据域名信誉调整
        domain = source.get('domain', '')
        if any(d in domain for d in ['.edu', '.gov', '.org']):
            reliability += 0.1
        
        return min(max(reliability, 0.1), 1.0)  # 限制在0.1-1.0之间
    
    def _check_answer_source_alignment(self, answer: str, sources: List[Dict[str, Any]]) -> bool:
        """检查答案与来源的一致性"""
        if not sources:
            return True  # 没有来源时默认一致
            
        # 使用改进的关键词提取
        answer_keywords = self._extract_significant_keywords(answer)
        
        if not answer_keywords:
            return True  # 没有关键词时默认一致
        
        # 检查至少一个来源有足够的关键词匹配
        for source in sources:
            source_content = source.get('content', '')
            if not source_content:
                continue
                
            source_keywords = self._extract_significant_keywords(source_content)
            
            # 检查重叠程度（使用模糊匹配）
            overlap = self._calculate_keyword_overlap(answer_keywords, source_keywords)
            print(f"DEBUG: Source keywords: {source_keywords}")
            print(f"DEBUG: Answer keywords: {answer_keywords}")
            print(f"DEBUG: Overlapping keywords: {overlap}")
            
            # 更宽松的匹配条件
            if len(overlap) >= 1:  # 至少1个关键词匹配
                return True
        
        return False
    
    def _extract_context_information(self, context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """提取上下文信息"""
        # 改进的信息提取
        info = {'keywords': set(), 'entities': set()}
        
        for item in context:
            if 'content' in item:
                content = item['content']
                # 使用改进的关键词提取
                keywords = self._extract_significant_keywords(content)
                info['keywords'].update(keywords)
                
                # 提取更具体的上下文信息
                if 'title' in item:
                    title_keywords = self._extract_significant_keywords(item['title'])
                    info['keywords'].update(title_keywords)
        
        # 确保关键词是有意义的
        info['keywords'] = {kw for kw in info['keywords'] if len(kw) >= 2 and not any(char in kw for char in '的了吗呢啊')}
        
        return info
    
    def _is_answer_consistent_with_context(self, answer: str, context_info: Dict[str, Any]) -> bool:
        """检查答案与上下文是否一致"""
        if not context_info['keywords']:
            return True  # 没有上下文信息时默认一致
            
        # 使用改进的关键词提取
        answer_keywords = self._extract_significant_keywords(answer)
        context_keywords = context_info['keywords']
        
        if not answer_keywords:
            return True  # 没有关键词时默认一致
        
        # 检查关键词重叠（使用模糊匹配）
        overlap = self._calculate_keyword_overlap(answer_keywords, context_keywords)
        print(f"DEBUG: Context keywords: {context_keywords}")
        print(f"DEBUG: Answer keywords: {answer_keywords}")
        print(f"DEBUG: Context overlapping keywords: {overlap}")
        
        # 更宽松的匹配条件：检查语义相似性
        if len(overlap) >= 1:
            return True
        
        # 如果没有直接的关键词匹配，检查语义相似性
        # 将关键词集合转换为字符串进行相似度计算
        answer_text = ' '.join(answer_keywords)
        context_text = ' '.join(context_keywords)
        
        if answer_text and context_text:
            similarity = self._calculate_similarity(answer_text, context_text)
            print(f"DEBUG: Semantic similarity with context: {similarity:.2f}")
            
            # 更宽松的相似度阈值，因为上下文可能包含具体应用而答案是通用概念
            key_terms = self.config_manager.get_factual_indicators()
            key_terms_in_answer = any(term in answer_text for term in key_terms)
            key_terms_in_context = any(term in context_text for term in key_terms)
            
            # 如果双方都包含关键术语，降低相似度要求
            if key_terms_in_answer and key_terms_in_context:
                return similarity > 0.15
            
            return similarity > 0.3  # 默认语义相似度阈值
        
        # 最后检查：如果答案和上下文都包含关键术语，认为一致
        key_terms = self.config_manager.get_factual_indicators()
        key_terms_in_answer = any(term in answer_text for term in key_terms)
        key_terms_in_context = any(term in context_text for term in key_terms)
        
        if key_terms_in_answer and key_terms_in_context:
            return True
        
        return False  # 没有匹配
    
    def _is_answer_internally_consistent(self, answer: str) -> bool:
        """检查答案内部一致性"""
        # 检查明显的矛盾
        contradictions = [
            (r'是.*不是', r'不是.*是'),
            (r'有.*没有', r'没有.*有'),
            (r'会.*不会', r'不会.*会')
        ]
        
        for pattern1, pattern2 in contradictions:
            if re.search(pattern1, answer) and re.search(pattern2, answer):
                return False
        
        return True
    
    def _assess_answer_quality(self, answer: str, question: str) -> List[str]:
        """评估答案质量"""
        issues = []
        
        # 检查答案长度
        if len(answer) < 10:
            issues.append("答案过短")
        elif len(answer) > 2000:
            issues.append("答案过长")
        
        # 检查是否直接回答问题
        is_direct = self._is_direct_answer(answer, question)
        if not is_direct:
            issues.append("答案可能没有直接回答问题")
        print(f"DEBUG: Direct answer check: {is_direct}")
        
        # 检查模糊语言
        vague_phrases = ['可能', '也许', '大概', '据说', '有人认为']
        if any(phrase in answer for phrase in vague_phrases):
            issues.append("答案包含模糊语言")
        
        return issues
    
    def _check_expertise_match(self, answer: str, question: str) -> bool:
        """检查专业知识匹配"""
        # 简单的专业术语检查
        technical_terms = self._extract_technical_terms(question)
        
        if not technical_terms:
            return True  # 没有专业术语，不需要深度检查
        
        # 检查答案中是否包含这些术语
        answer_lower = answer.lower()
        for term in technical_terms:
            if term not in answer_lower:
                return False
        
        return True
    
    def _extract_technical_terms(self, text: str) -> List[str]:
        """提取专业术语"""
        # 这里可以集成专业术语词典
        # 简单实现：返回长单词作为潜在术语
        words = re.findall(r'\w+', text)
        return [word for word in words if len(word) >= 8]  # 假设长单词可能是术语
    
    def _is_direct_answer(self, answer: str, question: str) -> bool:
        """检查是否直接回答问题"""
        # 对于"什么是X"这类问题，检查答案是否包含X
        if question.startswith('什么是') or '是什么' in question:
            # 提取问题中的核心概念
            core_concept = question.replace('什么是', '').replace('是什么', '').replace('？', '').replace('?', '').strip()
            if core_concept and core_concept in answer:
                return True
        
        # 对于一般问题，检查关键词重叠
        common_words = {'什么', '为什么', '如何', '怎样', '哪个', '哪里', '谁', '的', '了', '是', '在', '吗', '呢', '啊', '请', '问'}
        
        # 提取问题关键词
        question_words = set(re.findall(r'[\w\u4e00-\u9fff]+', question.lower()))  # 支持中文字符
        question_keywords = [word for word in question_words if word not in common_words and len(word) > 1]
        
        # 提取答案关键词
        answer_words = set(re.findall(r'[\w\u4e00-\u9fff]+', answer.lower()))
        answer_keywords = [word for word in answer_words if len(word) > 1]
        
        if not question_keywords:
            return True  # 没有问题关键词时默认直接回答
        
        # 检查关键词重叠
        overlap = set(question_keywords).intersection(answer_keywords)
        return len(overlap) >= min(1, len(question_keywords) * 0.3)  # 至少1个或30%的关键词重叠
    
    def _determine_verification_level(self, confidence: float, issues: List[str]) -> VerificationLevel:
        """确定验证级别"""
        if confidence >= 0.8 and not issues:
            return VerificationLevel.HIGH
        elif confidence >= 0.6:
            return VerificationLevel.MEDIUM
        elif confidence >= 0.4:
            return VerificationLevel.LOW
        else:
            return VerificationLevel.UNVERIFIED

# 测试代码
if __name__ == "__main__":
    # 设置控制台编码
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    # 创建验证器（启用所有验证方法）
    verifier = AnswerVerifier({
        'enabled_methods': ['fact_check', 'source_validation', 'consistency_check', 
                          'expert_assessment', 'cross_reference'],
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
            },
            "人工智能致力于创建智能系统": {
                "is_true": True,
                "confidence": 0.9,
                "evidence": "AI研究领域共识"
            },
            "机器学习使计算机能够从数据中学习": {
                "is_true": True,
                "confidence": 0.95,
                "evidence": "机器学习基本定义"
            },
            "人工智能可以执行需要人类智能的任务": {
                "is_true": True,
                "confidence": 0.85,
                "evidence": "AI能力描述"
            }
        }
    })
    
    # 测试答案和上下文
    test_question = "什么是人工智能？"
    test_answer = "人工智能是计算机科学的一个分支，它致力于创建能够执行通常需要人类智能的任务的系统。机器学习作为AI的核心技术，使计算机能够从数据中学习并做出预测。"
    
    test_context = [
        {"content": "人工智能研究包括机器人、语言识别、图像识别、自然语言处理等领域。"},
        {"content": "机器学习算法可以分为监督学习、无监督学习和强化学习。"}
    ]
    
    test_sources = [
        {
            "title": "人工智能导论",
            "url": "https://example.com/ai-intro",
            "content": "人工智能是计算机科学中研究如何制造智能机器的分支学科。",
            "type": "academic",
            "domain": "edu.example.com"
        },
        {
            "title": "机器学习基础", 
            "url": "https://example.com/ml-basics",
            "content": "机器学习使计算机系统能够从经验中改进性能，是AI的重要组成部分。",
            "type": "academic", 
            "domain": "org.ml-research"
        }
    ]
    
    # 综合验证测试
    import asyncio
    
    async def comprehensive_test():
        print("=== 综合答案验证测试 ===")
        print(f"问题: {test_question}")
        print(f"答案: {test_answer}")
        print()
        
        # 执行验证
        result = await verifier.verify_answer(
            test_answer, 
            test_question, 
            context=test_context,
            sources=test_sources
        )
        
        print("=== 验证结果详情 ===")
        print(f"验证通过: {result.is_verified}")
        print(f"总体置信度: {result.confidence:.2f}")
        print(f"验证级别: {result.verification_level.value}")
        print(f"使用的方法: {[m.value for m in result.methods_used]}")
        print()
        
        if result.issues_found:
            print("=== 发现的问题 ===")
            for i, issue in enumerate(result.issues_found, 1):
                print(f"{i}. {issue}")
        else:
            print("✓ 未发现问题")
        print()
        
        if result.supporting_evidence:
            print("=== 支持证据 ===")
            for i, evidence in enumerate(result.supporting_evidence[:3], 1):
                if 'fact' in evidence:
                    print(f"{i}. 事实支持: {evidence.get('fact')}")
                elif 'source' in evidence:
                    print(f"{i}. 来源支持: {evidence.get('source', {}).get('title', '未知来源')}")
        
        if result.contradictory_evidence:
            print("\n=== 矛盾证据 ===")
            for i, evidence in enumerate(result.contradictory_evidence[:3], 1):
                print(f"{i}. {evidence.get('contradiction', '未知矛盾')}")
    
    # 运行测试
    asyncio.run(comprehensive_test())
    
    # 额外测试：错误答案验证
    async def test_false_answer():
        print("\n" + "="*50)
        print("=== 错误答案验证测试 ===")
        
        false_answer = "人工智能是一种魔法技术，可以让计算机拥有超能力。机器学习是骗人的把戏。"
        
        result = await verifier.verify_answer(
            false_answer,
            "什么是人工智能？",
            context=test_context,
            sources=test_sources
        )
        
        print(f"错误答案验证通过: {result.is_verified}")
        print(f"置信度: {result.confidence:.2f}")
        print(f"问题数量: {len(result.issues_found)}")
        
        if result.issues_found:
            print("发现的问题:")
            for issue in result.issues_found[:3]:
                print(f"  - {issue}")
    
    asyncio.run(test_false_answer())