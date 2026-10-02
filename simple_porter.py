#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单波特五力分析 - 直接调用API
"""

import os
import json
import requests
from datetime import datetime
from typing import Dict, List, Any

def call_deepseek_api_directly(question: str, company_name: str) -> str:
    """直接调用DeepSeek API"""
    try:
        api_key = os.environ["SIMPLE_PORTER_API_KEY"]
        model = "deepseek-reasoner"
        base_url = "https://api.deepseek.com"
        
        # 构建提示词
        system_prompt = """你是一个专业的企业战略分析师，擅长使用波特五力模型分析公司竞争力。
请基于你的专业知识和行业经验进行分析，提供详细、准确的分析。"""
        
        user_prompt = question.format(company_name=company_name)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": 0.6,
            "max_tokens": 4000
        }
        
        print("正在调用DeepSeek API进行波特五力分析...")
        response = requests.post(url, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        
        result = response.json()
        return result['choices'][0]['message']['content']
        
    except Exception as e:
        print(f"API调用失败: {e}")
        raise

def analyze_porter_five_forces():
    """进行波特五力分析"""
    try:
        # 波特五力分析问题
        porter_question = """请用波特五力模型分析{company_name}，包括以下五个方面：
        1. 行业内竞争者现在的竞争能力
        2. 潜在竞争者进入的能力
        3. 替代品的替代能力
        4. 供应商的讨价还价能力
        5. 购买者的讨价还价能力
        
        请给出详细的分析，并对每个方面进行1-10分的评分（1分最弱，10分最强）。
        请以JSON格式回答，包含每个方面的评分和详细理由。"""
        
        # 调用API
        answer = call_deepseek_api_directly(porter_question, "海康威视")
        
        # 构建结果
        result = {
            'company': '海康威视',
            'analysis_time': datetime.now().isoformat(),
            'analysis_type': 'porter_five_forces',
            'question': porter_question.format(company_name='海康威视'),
            'answer': answer,
            'api_provider': 'deepseek',
            'model': 'deepseek-reasoner'
        }
        
        # 保存结果
        output_path = "porter_five_forces_海康威视.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"波特五力分析完成，结果已保存到: {output_path}")
        
        # 打印简要结果
        print("\n分析结果摘要:")
        if 'answer' in result:
            print(result['answer'][:500] + "...")
        
        return result
        
    except Exception as e:
        print(f"分析失败: {e}")
        raise

if __name__ == "__main__":
    analyze_porter_five_forces()