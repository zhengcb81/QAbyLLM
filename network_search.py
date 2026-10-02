#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络搜索集成模块
支持多种搜索引擎的集成搜索
"""

import os
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from enum import Enum
import time
import json
import re
from urllib.parse import quote, urlencode

logger = logging.getLogger(__name__)

class SearchEngine(Enum):
    """搜索引擎枚举"""
    GOOGLE = "google"
    BING = "bing"
    DUCKDUCKGO = "duckduckgo"
    SERPER = "serper"  # 付费API
    SERPAPI = "serpapi"  # 付费API

class SearchResult:
    """搜索结果"""
    
    def __init__(self, 
                 title: str,
                 url: str,
                 snippet: str,
                 source: str,
                 search_engine: str,
                 relevance_score: float = 0.0,
                 published_date: Optional[str] = None):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.source = source
        self.search_engine = search_engine
        self.relevance_score = relevance_score
        self.published_date = published_date
        self.retrieved_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'title': self.title,
            'url': self.url,
            'snippet': self.snippet,
            'source': self.source,
            'search_engine': self.search_engine,
            'relevance_score': self.relevance_score,
            'published_date': self.published_date,
            'retrieved_at': self.retrieved_at
        }
    
    def __str__(self) -> str:
        return f"{self.title} ({self.url}) - {self.snippet[:100]}..."

class NetworkSearch:
    """网络搜索集成"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.search_engines = self._initialize_engines()
        self.cache_enabled = self.config.get('cache', {}).get('enabled', True)
        self.cache_duration = self.config.get('cache', {}).get('duration_minutes', 60)
        self._search_cache: Dict[str, Dict[str, Any]] = {}
        self._last_search_time: Dict[str, float] = {}
    
    def _initialize_engines(self) -> Dict[SearchEngine, bool]:
        """初始化搜索引擎"""
        engines = {}
        
        # 检查配置中启用的引擎
        enabled_engines = self.config.get('search_engines', [])
        
        for engine in SearchEngine:
            # 检查API密钥（对于付费引擎）
            if engine in [SearchEngine.SERPER, SearchEngine.SERPAPI]:
                api_key = self.config.get('api_keys', {}).get(engine.value)
                engines[engine] = bool(api_key and not api_key.endswith('_here'))
            else:
                engines[engine] = engine.value in enabled_engines if enabled_engines else True
        
        return engines
    
    def search(self, 
               query: str, 
               engines: Optional[List[SearchEngine]] = None,
               num_results: int = 10,
               **kwargs) -> Dict[str, Any]:
        """执行搜索"""
        start_time = time.time()
        
        # 检查缓存
        cache_key = self._generate_cache_key(query, engines, num_results, kwargs)
        if self.cache_enabled and cache_key in self._search_cache:
            cached_result = self._search_cache[cache_key]
            if self._is_cache_valid(cached_result):
                logger.info(f"使用缓存搜索结果: {query}")
                return cached_result
        
        # 确定要使用的引擎
        search_engines = engines or [engine for engine, enabled in self.search_engines.items() if enabled]
        
        if not search_engines:
            return self._create_error_result("没有可用的搜索引擎")
        
        # 执行搜索
        all_results: List[SearchResult] = []
        errors = []
        
        for engine in search_engines:
            try:
                if not self.search_engines.get(engine, False):
                    continue
                
                # 检查速率限制
                self._check_rate_limit(engine)
                
                engine_results = self._search_with_engine(engine, query, num_results, **kwargs)
                all_results.extend(engine_results)
                
                logger.info(f"{engine.value}搜索完成: {len(engine_results)} 个结果")
                
            except Exception as e:
                error_msg = f"{engine.value}搜索失败: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # 去重和排序
        unique_results = self._deduplicate_results(all_results)
        sorted_results = self._sort_results(unique_results, query)
        
        # 限制结果数量
        final_results = sorted_results[:num_results]
        
        processing_time = time.time() - start_time
        
        result = {
            'success': True,
            'query': query,
            'results': [r.to_dict() for r in final_results],
            'total_results': len(final_results),
            'engines_used': [e.value for e in search_engines],
            'processing_time_seconds': processing_time,
            'errors': errors,
            'cached': False
        }
        
        # 缓存结果
        if self.cache_enabled:
            result['cached_until'] = (datetime.now() + timedelta(minutes=self.cache_duration)).isoformat()
            self._search_cache[cache_key] = result
        
        return result
    
    def _search_with_engine(self, 
                          engine: SearchEngine, 
                          query: str, 
                          num_results: int,
                          **kwargs) -> List[SearchResult]:
        """使用特定引擎搜索"""
        
        if engine == SearchEngine.GOOGLE:
            return self._google_search(query, num_results, **kwargs)
        elif engine == SearchEngine.BING:
            return self._bing_search(query, num_results, **kwargs)
        elif engine == SearchEngine.DUCKDUCKGO:
            return self._duckduckgo_search(query, num_results, **kwargs)
        elif engine == SearchEngine.SERPER:
            return self._serper_search(query, num_results, **kwargs)
        elif engine == SearchEngine.SERPAPI:
            return self._serpapi_search(query, num_results, **kwargs)
        else:
            return []
    
    def _google_search(self, query: str, num_results: int, **kwargs) -> List[SearchResult]:
        """Google搜索"""
        # 这里使用简单的请求模拟，实际使用时需要更复杂的处理
        # 或者使用Google Custom Search JSON API
        
        try:
            # 模拟结果 - 实际实现需要使用API
            return [
                SearchResult(
                    title=f"Google结果 {i} - {query}",
                    url=f"https://example.com/result{i}",
                    snippet=f"这是关于 {query} 的Google搜索结果摘要 {i}",
                    source="google.com",
                    search_engine="google",
                    relevance_score=0.9 - (i * 0.1)
                ) for i in range(min(num_results, 5))
            ]
            
        except Exception as e:
            logger.error(f"Google搜索失败: {e}")
            return []
    
    def _bing_search(self, query: str, num_results: int, **kwargs) -> List[SearchResult]:
        """Bing搜索"""
        try:
            # 模拟结果
            return [
                SearchResult(
                    title=f"Bing结果 {i} - {query}",
                    url=f"https://example.com/bing-result{i}",
                    snippet=f"这是关于 {query} 的Bing搜索结果摘要 {i}",
                    source="bing.com",
                    search_engine="bing",
                    relevance_score=0.85 - (i * 0.1)
                ) for i in range(min(num_results, 5))
            ]
            
        except Exception as e:
            logger.error(f"Bing搜索失败: {e}")
            return []
    
    def _duckduckgo_search(self, query: str, num_results: int, **kwargs) -> List[SearchResult]:
        """DuckDuckGo搜索"""
        try:
            # 使用DuckDuckGo API
            import requests
            
            params = {
                'q': query,
                'format': 'json',
                'no_html': '1',
                'skip_disambig': '1'
            }
            
            response = requests.get('https://api.duckduckgo.com/', params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            # 提取抽象文本
            if data.get('AbstractText'):
                results.append(SearchResult(
                    title=data.get('Heading', query),
                    url=data.get('AbstractURL', ''),
                    snippet=data['AbstractText'],
                    source='duckduckgo.com',
                    search_engine='duckduckgo',
                    relevance_score=0.9
                ))
            
            # 提取相关主题
            for i, topic in enumerate(data.get('RelatedTopics', [])[:num_results-1]):
                if 'Text' in topic and 'FirstURL' in topic:
                    results.append(SearchResult(
                        title=topic['Text'].split(' - ')[0] if ' - ' in topic['Text'] else topic['Text'],
                        url=topic['FirstURL'],
                        snippet=topic['Text'],
                        source='duckduckgo.com',
                        search_engine='duckduckgo',
                        relevance_score=0.8 - (i * 0.1)
                    ))
            
            return results
            
        except Exception as e:
            logger.error(f"DuckDuckGo搜索失败: {e}")
            return []
    
    def _serper_search(self, query: str, num_results: int, **kwargs) -> List[SearchResult]:
        """Serper API搜索"""
        api_key = self.config.get('api_keys', {}).get('serper')
        if not api_key or api_key.endswith('_here'):
            logger.warning("Serper API密钥未配置")
            return []
        
        try:
            import requests
            
            url = "https://google.serper.dev/search"
            headers = {
                'X-API-KEY': api_key,
                'Content-Type': 'application/json'
            }
            data = {
                'q': query,
                'num': num_results
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            search_data = response.json()
            results = []
            
            # 处理有机搜索结果
            for i, item in enumerate(search_data.get('organic', [])):
                results.append(SearchResult(
                    title=item.get('title', ''),
                    url=item.get('link', ''),
                    snippet=item.get('snippet', ''),
                    source=item.get('source', ''),
                    search_engine='serper',
                    relevance_score=0.95 - (i * 0.05)
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Serper搜索失败: {e}")
            return []
    
    def _serpapi_search(self, query: str, num_results: int, **kwargs) -> List[SearchResult]:
        """SERPAPI搜索"""
        api_key = self.config.get('api_keys', {}).get('serpapi')
        if not api_key or api_key.endswith('_here'):
            logger.warning("SERPAPI密钥未配置")
            return []
        
        try:
            import requests
            
            params = {
                'q': query,
                'api_key': api_key,
                'num': num_results,
                'engine': 'google'
            }
            
            response = requests.get('https://serpapi.com/search', params=params, timeout=30)
            response.raise_for_status()
            
            search_data = response.json()
            results = []
            
            # 处理有机搜索结果
            for i, item in enumerate(search_data.get('organic_results', [])):
                results.append(SearchResult(
                    title=item.get('title', ''),
                    url=item.get('link', ''),
                    snippet=item.get('snippet', ''),
                    source=item.get('source', ''),
                    search_engine='serpapi',
                    relevance_score=0.95 - (i * 0.05)
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"SERPAPI搜索失败: {e}")
            return []
    
    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """去重搜索结果"""
        seen_urls = set()
        unique_results = []
        
        for result in results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                unique_results.append(result)
        
        return unique_results
    
    def _sort_results(self, results: List[SearchResult], query: str) -> List[SearchResult]:
        """排序搜索结果"""
        # 简单的相关性排序（实际应该使用更复杂的算法）
        query_terms = query.lower().split()
        
        def relevance_score(result: SearchResult) -> float:
            # 基础分数
            score = result.relevance_score
            
            # 标题匹配加分
            title_lower = result.title.lower()
            for term in query_terms:
                if term in title_lower:
                    score += 0.1
            
            # 摘要匹配加分
            snippet_lower = result.snippet.lower()
            for term in query_terms:
                if term in snippet_lower:
                    score += 0.05
            
            return score
        
        return sorted(results, key=relevance_score, reverse=True)
    
    def _generate_cache_key(self, 
                          query: str, 
                          engines: Optional[List[SearchEngine]], 
                          num_results: int,
                          kwargs: Dict[str, Any]) -> str:
        """生成缓存键"""
        engine_names = [e.value for e in (engines or [])]
        key_data = {
            'query': query,
            'engines': sorted(engine_names),
            'num_results': num_results,
            'kwargs': kwargs
        }
        return json.dumps(key_data, sort_keys=True)
    
    def _is_cache_valid(self, cached_result: Dict[str, Any]) -> bool:
        """检查缓存是否有效"""
        if 'cached_until' not in cached_result:
            return False
        
        try:
            cached_until = datetime.fromisoformat(cached_result['cached_until'])
            return datetime.now() < cached_until
        except:
            return False
    
    def _check_rate_limit(self, engine: SearchEngine) -> None:
        """检查速率限制"""
        current_time = time.time()
        last_time = self._last_search_time.get(engine.value, 0)
        
        # 简单的速率限制：每秒最多1次请求
        if current_time - last_time < 1.0:
            time.sleep(1.0 - (current_time - last_time))
        
        self._last_search_time[engine.value] = time.time()
    
    def _create_error_result(self, error_msg: str) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            'success': False,
            'error': error_msg,
            'results': [],
            'total_results': 0,
            'processing_time_seconds': 0,
            'cached': False
        }
    
    def clear_cache(self) -> None:
        """清空缓存"""
        self._search_cache.clear()
        logger.info("搜索缓存已清空")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            'cache_size': len(self._search_cache),
            'cache_enabled': self.cache_enabled,
            'cache_duration_minutes': self.cache_duration
        }

# 测试代码
if __name__ == "__main__":
    # 创建搜索实例
    search = NetworkSearch({
        'search_engines': ['google', 'bing', 'duckduckgo'],
        'cache': {'enabled': True, 'duration_minutes': 30},
        'api_keys': {
            'serper': 'your_serper_key_here',
            'serpapi': 'your_serpapi_key_here'
        }
    })
    
    # 测试搜索
    print("=== 网络搜索测试 ===")
    result = search.search("人工智能发展趋势", num_results=5)
    
    print(f"搜索成功: {result['success']}")
    print(f"结果数量: {result['total_results']}")
    print(f"使用的引擎: {result['engines_used']}")
    print(f"处理时间: {result['processing_time_seconds']:.2f}秒")
    
    if result['success'] and result['results']:
        print("\n=== 前3个结果 ===")
        for i, res in enumerate(result['results'][:3], 1):
            print(f"{i}. {res['title']}")
            print(f"   链接: {res['url']}")
            print(f"   摘要: {res['snippet'][:100]}...")
            print()
    
    # 测试缓存
    print("=== 缓存测试 ===")
    cache_stats = search.get_cache_stats()
    print(f"缓存大小: {cache_stats['cache_size']}")
    print(f"缓存启用: {cache_stats['cache_enabled']}")