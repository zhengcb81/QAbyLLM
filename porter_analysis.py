#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
波特五力模型分析 - 直接使用现有向量数据库
"""

import os
import json
import sys
from typing import Dict, List, Any
from datetime import datetime

# 添加当前目录到路径
sys.path.append('.')

from rag_system import RAGSystem

def analyze_porter_five_forces():
    """使用现有RAG系统进行波特五力分析"""
    try:
        # 初始化RAG系统
        rag = RAGSystem()
        
        # 设置嵌入模型（使用较小的模型）
        rag.setup_embedding_model()
        print("[OK] 嵌入模型加载成功")
        
        # 设置向量数据库
        rag.setup_vector_db()
        print("[OK] 向量数据库连接成功")
        
        # 波特五力分析问题
        porter_question = """请用波特五力模型分析{company_name}，包括以下五个方面：
        1. 行业内竞争者现在的竞争能力
        2. 潜在竞争者进入的能力
        3. 替代品的替代能力
        4. 供应商的讨价还价能力
        5. 购买者的讨价还价能力
        
        请给出详细的分析，并对每个方面进行1-10分的评分（1分最弱，10分最强）。
        请以JSON格式回答，包含每个方面的评分和详细理由。"""
        
        # 构建知识库
        print("[INFO] 构建知识库...")
        if not rag.build_knowledge_base():
            raise Exception("知识库构建失败")
        print("[OK] 知识库构建完成")
        
        # 执行查询
        print("🚀 开始波特五力分析...")
        result = rag.ask_question_with_rag(porter_question, "海康威视")
        
        # 保存结果
        output_path = "porter_five_forces_海康威视.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"[OK] 波特五力分析完成，结果已保存到: {output_path}")
        
        # 打印简要结果
        if 'answer' in result:
            print("\n[INFO] 分析结果摘要:")
            print(result['answer'][:500] + "...")
        
        return result
        
    except Exception as e:
        print(f"[ERROR] 分析失败: {e}")
        raise

if __name__ == "__main__":
    analyze_porter_five_forces()