#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混合检索器
结合本地文档检索和网络搜索的混合检索策略
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
import time
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class RetrievalSource(Enum):
    """检索来源枚举"""
    LOCAL = "local"
    NETWORK = "network"
    HYBRID = "hybrid"

@dataclass
class RetrievalResult:
    """检索结果"""
    content: str
    source: RetrievalSource
    relevance_score: float
    metadata: Dict[str, Any]
    retrieved_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'content': self.content,
            'source': self.source.value,
            'relevance_score': self.relevance_score,
            'metadata': self.metadata,
            'retrieved_at': self.retrieved_at
        }

class HybridRetriever:
    """混合检索器"""
    
    def __init__(self, 
                 config: Optional[Dict[str, Any]] = None,
                 local_retriever: Any = None,
                 network_searcher: Any = None):
        self.config = config or {}
        self.local_retriever = local_retriever
        self.network_searcher = network_searcher
        self.strategy = self.config.get('strategy', 'balanced')
        self.max_results = self.config.get('max_results', 10)
        self.min_relevance = self.config.get('min_relevance', 0.3)
    
    async def retrieve(self, query: str, **kwargs) -> List[RetrievalResult]:
        """执行混合检索"""
        start_time = time.time()
        
        # 根据策略决定检索方式
        if self.strategy == 'local_first':
            results = await self._local_first_strategy(query, **kwargs)
        elif self.strategy == 'network_first':
            results = await self._network_first_strategy(query, **kwargs)
        elif self.strategy == 'parallel':
            results = await self._parallel_strategy(query, **kwargs)
        else:  # balanced
            results = await self._balanced_strategy(query, **kwargs)
        
        # 过滤和排序结果
        filtered_results = self._filter_results(results)
        sorted_results = self._sort_results(filtered_results, query)
        
        # 限制结果数量
        final_results = sorted_results[:self.max_results]
        
        processing_time = time.time() - start_time
        logger.info(f"混合检索完成: {len(final_results)} 个结果, 耗时: {processing_time:.2f}秒")
        
        return final_results
    
    async def _local_first_strategy(self, query: str, **kwargs) -> List[RetrievalResult]:
        """本地优先策略"""
        results = []
        
        # 首先尝试本地检索
        if self.local_retriever:
            try:
                local_results = await self._retrieve_local(query, **kwargs)
                results.extend(local_results)
                
                # 如果本地结果足够，直接返回
                if len(local_results) >= self.max_results:
                    return results
                    
            except Exception as e:
                logger.warning(f"本地检索失败: {e}")
        
        # 本地结果不足，补充网络检索
        if self.network_searcher and len(results) < self.max_results:
            try:
                network_results = await self._retrieve_network(query, **kwargs)
                results.extend(network_results)
            except Exception as e:
                logger.warning(f"网络检索失败: {e}")
        
        return results
    
    async def _network_first_strategy(self, query: str, **kwargs) -> List[RetrievalResult]:
        """网络优先策略"""
        results = []
        
        # 首先尝试网络检索
        if self.network_searcher:
            try:
                network_results = await self._retrieve_network(query, **kwargs)
                results.extend(network_results)
            except Exception as e:
                logger.warning(f"网络检索失败: {e}")
        
        # 网络结果不足或需要补充，添加本地检索
        if self.local_retriever and (len(results) < self.max_results or self.strategy == 'balanced'):
            try:
                local_results = await self._retrieve_local(query, **kwargs)
                results.extend(local_results)
            except Exception as e:
                logger.warning(f"本地检索失败: {e}")
        
        return results
    
    async def _parallel_strategy(self, query: str, **kwargs) -> List[RetrievalResult]:
        """并行检索策略"""
        import asyncio
        
        results = []
        tasks = []
        
        # 创建并行任务
        if self.local_retriever:
            tasks.append(self._retrieve_local(query, **kwargs))
        
        if self.network_searcher:
            tasks.append(self._retrieve_network(query, **kwargs))
        
        # 并行执行
        if tasks:
            try:
                gathered_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in gathered_results:
                    if isinstance(result, Exception):
                        logger.warning(f"并行检索任务失败: {result}")
                    elif isinstance(result, list):
                        results.extend(result)
                        
            except Exception as e:
                logger.error(f"并行检索失败: {e}")
        
        return results
    
    async def _balanced_strategy(self, query: str, **kwargs) -> List[RetrievalResult]:
        """平衡策略"""
        # 根据查询类型决定策略
        query_type = self._analyze_query_type(query)
        
        if query_type == 'factual':
            # 事实性问题优先网络
            return await self._network_first_strategy(query, **kwargs)
        elif query_type == 'internal':
            # 内部文档问题优先本地
            return await self._local_first_strategy(query, **kwargs)
        else:
            # 默认并行
            return await self._parallel_strategy(query, **kwargs)
    
    async def _retrieve_local(self, query: str, **kwargs) -> List[RetrievalResult]:
        """执行本地检索"""
        if not self.local_retriever:
            return []
        
        try:
            # 假设local_retriever有retrieve_relevant_docs方法
            if hasattr(self.local_retriever, 'retrieve_relevant_docs'):
                local_docs = self.local_retriever.retrieve_relevant_docs(query)
            else:
                # 回退到其他可能的方法名
                local_docs = []
                
            results = []
            for doc in local_docs:
                results.append(RetrievalResult(
                    content=doc.get('content', ''),
                    source=RetrievalSource.LOCAL,
                    relevance_score=doc.get('distance', 0.8),  # 假设距离越小越相关
                    metadata=doc.get('metadata', {}),
                    retrieved_at=datetime.now().isoformat()
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"本地检索执行失败: {e}")
            return []
    
    async def _retrieve_network(self, query: str, **kwargs) -> List[RetrievalResult]:
        """执行网络检索"""
        if not self.network_searcher:
            return []
        
        try:
            # 假设network_searcher有search方法
            if hasattr(self.network_searcher, 'search'):
                search_results = self.network_searcher.search(query, **kwargs)
            else:
                search_results = {'success': False, 'results': []}
            
            if not search_results.get('success', False):
                return []
            
            results = []
            for item in search_results.get('results', []):
                # 构建内容片段
                content = f"{item.get('title', '')}\n{item.get('snippet', '')}"
                
                results.append(RetrievalResult(
                    content=content,
                    source=RetrievalSource.NETWORK,
                    relevance_score=item.get('relevance_score', 0.7),
                    metadata={
                        'url': item.get('url', ''),
                        'source': item.get('source', ''),
                        'search_engine': item.get('search_engine', '')
                    },
                    retrieved_at=datetime.now().isoformat()
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"网络检索执行失败: {e}")
            return []
    
    def _analyze_query_type(self, query: str) -> str:
        """分析查询类型"""
        query_lower = query.lower()
        
        # 事实性问题模式
        factual_patterns = [
            r'什么时候',
            r'哪里',
            r'谁',
            r'什么是',
            r'如何',
            r'为什么',
            r'多少',
            r'最新',
            r'新闻',
            r'趋势'
        ]
        
        # 内部文档问题模式
        internal_patterns = [
            r'我们公司',
            r'内部',
            r'文档',
            r'报告',
            r'会议',
            r'项目',
            r'客户',
            r'产品',
            r'战略',
            r'规划'
        ]
        
        # 检查模式
        for pattern in factual_patterns:
            if re.search(pattern, query_lower):
                return 'factual'
        
        for pattern in internal_patterns:
            if re.search(pattern, query_lower):
                return 'internal'
        
        return 'general'
    
    def _filter_results(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """过滤结果"""
        filtered = []
        
        for result in results:
            # 检查相关性分数
            if result.relevance_score >= self.min_relevance:
                # 检查内容长度
                if len(result.content.strip()) >= 10:  # 至少10个字符
                    filtered.append(result)
        
        return filtered
    
    def _sort_results(self, results: List[RetrievalResult], query: str) -> List[RetrievalResult]:
        """排序结果"""
        if not results:
            return []
        
        query_terms = query.lower().split()
        
        def custom_sort_key(result: RetrievalResult) -> Tuple[float, float]:
            # 主要按相关性分数排序
            base_score = result.relevance_score
            
            # 根据来源调整分数
            source_bonus = 0.0
            if result.source == RetrievalSource.LOCAL:
                source_bonus = 0.1  # 本地结果稍微优先
            
            # 根据内容质量调整分数
            content_quality = self._assess_content_quality(result.content, query_terms)
            
            # 最终分数
            final_score = base_score + source_bonus + content_quality
            
            # 返回元组用于排序（分数，时间戳用于打破平局）
            try:
                timestamp = datetime.fromisoformat(result.retrieved_at).timestamp()
            except:
                timestamp = 0
            
            return (-final_score, -timestamp)  # 负号用于降序排序
        
        return sorted(results, key=custom_sort_key)
    
    def _assess_content_quality(self, content: str, query_terms: List[str]) -> float:
        """评估内容质量"""
        quality_score = 0.0
        content_lower = content.lower()
        
        # 长度奖励（适中的长度更好）
        length = len(content)
        if 100 <= length <= 1000:
            quality_score += 0.05
        elif length > 1000:
            quality_score += 0.02
        
        # 查询术语匹配
        matched_terms = 0
        for term in query_terms:
            if term in content_lower:
                matched_terms += 1
        
        if matched_terms > 0:
            quality_score += (matched_terms / len(query_terms)) * 0.1
        
        # 结构奖励（包含标题、列表等）
        if any(marker in content for marker in [':', '- ', '•', '*']):
            quality_score += 0.03
        
        return min(quality_score, 0.2)  # 限制最大质量分数
    
    def set_strategy(self, strategy: str) -> None:
        """设置检索策略"""
        valid_strategies = ['local_first', 'network_first', 'parallel', 'balanced']
        if strategy in valid_strategies:
            self.strategy = strategy
            logger.info(f"检索策略已设置为: {strategy}")
        else:
            logger.warning(f"无效的检索策略: {strategy}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'strategy': self.strategy,
            'max_results': self.max_results,
            'min_relevance': self.min_relevance,
            'local_retriever_available': self.local_retriever is not None,
            'network_searcher_available': self.network_searcher is not None
        }

# 测试代码
if __name__ == "__main__":
    # 创建混合检索器
    retriever = HybridRetriever({
        'strategy': 'balanced',
        'max_results': 8,
        'min_relevance': 0.4
    })
    
    # 测试查询分析
    test_queries = [
        "我们公司2024年的战略规划是什么？",
        "人工智能的最新发展趋势",
        "如何配置Python开发环境"
    ]
    
    print("=== 查询类型分析测试 ===")
    for query in test_queries:
        query_type = retriever._analyze_query_type(query)
        print(f"'{query}' -> {query_type}")
    
    # 测试策略设置
    print("\n=== 策略设置测试 ===")
    retriever.set_strategy('local_first')
    retriever.set_strategy('invalid_strategy')  # 应该警告
    
    # 显示统计信息
    stats = retriever.get_stats()
    print(f"\n=== 检索器统计 ===")
    print(f"当前策略: {stats['strategy']}")
    print(f"最大结果数: {stats['max_results']}")
    print(f"最小相关性: {stats['min_relevance']}")
    print(f"本地检索器可用: {stats['local_retriever_available']}")
    print(f"网络搜索器可用: {stats['network_searcher_available']}")