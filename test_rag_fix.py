#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试RAG系统修复
"""

import os
import sys
sys.path.append('.')

from rag_system import RAGSystem

def test_rag_build():
    """测试RAG知识库构建"""
    try:
        rag = RAGSystem()
        
        # 设置组件
        rag.setup_embedding_model()
        print("[OK] 嵌入模型加载成功")
        
        rag.setup_vector_db()
        print("[OK] 向量数据库连接成功")
        
        # 构建知识库
        print("[INFO] 构建知识库...")
        success = rag.build_knowledge_base()
        
        if success:
            print("[OK] 知识库构建成功")
            
            # 检查向量数据库内容
            coll = rag.collection
            count = coll.count()
            print(f"[INFO] 向量数据库中的文档块数量: {count}")
            
            # 检查文档来源
            results = coll.get(include=['metadatas'])
            sources = set()
            for meta in results['metadatas']:
                if meta and 'source' in meta:
                    sources.add(meta['source'])
            
            print(f"[INFO] 唯一文档来源数量: {len(sources)}")
            print("[INFO] 前5个文档来源:")
            for source in list(sources)[:5]:
                print(f"  {source}")
                
        else:
            print("[ERROR] 知识库构建失败")
            
        return success
        
    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_rag_build()