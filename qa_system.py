#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
企业竞争力分析问答系统
支持多公司分析和交互式可视化
支持在线模式和本地RAG模式
"""

import os
import json
import yaml
import openai
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
import re

# 导入RAG系统
try:
    from rag_system import RAGSystem
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    print("⚠️ RAG系统不可用，请安装相关依赖包")

class QASystem:
    """智能问答系统主类"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """初始化系统"""
        self.config_path = config_path
        self.config = self.load_config()
        self.openai_client = None
        self.rag_system = None
        
        # 根据配置选择模式
        self.mode = self.config.get('mode', {}).get('type', 'online')
        
        if self.mode == 'online':
            self.setup_openai()
        elif self.mode == 'local' and RAG_AVAILABLE:
            self.setup_rag_system()
        else:
            print(f"❌ 不支持的模式: {self.mode}")
        
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            else:
                print(f"⚠️ 配置文件 {self.config_path} 不存在，使用默认配置")
                return self.get_default_config()
        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")
            return self.get_default_config()
    
    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'mode': {
                'type': 'online',
                'local_api_provider': 'deepseek'
            },
            'api': {
                'openai_api_key': 'your_openai_api_key_here',
                'openai_model': 'gpt-4o',
                'use_openai_search': True,
                'deepseek_api_key': 'your_deepseek_api_key_here',
                'deepseek_model': 'deepseek-chat',
                'deepseek_base_url': 'https://api.deepseek.com'
            },
            'local_rag': {
                'enabled': False,
                'company_name': '海康威视',
                'documents_folder': 'knowledge_base'
            },
            'analysis': {
                'companies': ['小米集团', '华为', '苹果', '三星']
            },
            'questions': [
                "请分析{company_name}的网络效应强度，并给出1-10分的评分。请以JSON格式回答，包含评分和理由。",
                "请分析{company_name}的规模效应，并给出1-10分的评分。请以JSON格式回答，包含评分和理由。",
                "请分析{company_name}的客户黏性，并给出1-10分的评分。请以JSON格式回答，包含评分和理由。",
                "请分析{company_name}的成本优势，并给出1-10分的评分。请以JSON格式回答，包含评分和理由。",
                "请分析{company_name}所在行业的竞争格局，并给出1-10分的评分。请以JSON格式回答，包含评分和理由。",
                "请分析{company_name}的进入壁垒，并给出1-10分的评分。请以JSON格式回答，包含评分和理由。",
                "请分析{company_name}的价格敏感度，并给出1-10分的评分。请以JSON格式回答，包含评分和理由。"
            ],
            'output': {
                'file_path': 'multi_company_analysis.json',
                'include_search_sources': True
            }
        }
    
    def setup_openai(self):
        """设置OpenAI客户端"""
        try:
            api_key = os.getenv('OPENAI_API_KEY') or self.config.get('api', {}).get('openai_api_key')
            if api_key and api_key != "your_openai_api_key_here":
                self.openai_client = openai.OpenAI(api_key=api_key)
                print("✅ OpenAI客户端初始化成功")
            else:
                print("⚠️ 未找到有效的OpenAI API密钥")
                print("请设置环境变量 OPENAI_API_KEY 或在config.yaml中配置")
        except Exception as e:
            print(f"❌ OpenAI客户端初始化失败: {e}")
    
    def setup_rag_system(self):
        """设置RAG系统"""
        try:
            self.rag_system = RAGSystem(self.config_path)
            print("✅ RAG系统初始化成功")
        except Exception as e:
            print(f"❌ RAG系统初始化失败: {e}")
    
    def ask_question(self, question: str, use_search: bool = True) -> Dict[str, Any]:
        """提问并获取答案（在线模式）"""
        if not self.openai_client:
            return {
                'question': question,
                'answer': '错误：OpenAI客户端未初始化',
                'error': 'OpenAI客户端未初始化，请检查API密钥配置',
                'timestamp': datetime.now().isoformat(),
                'search_model': 'none'
            }
        
        try:
            # 使用GPT-4o进行分析
            response = self.openai_client.chat.completions.create(
                model=self.config.get('api', {}).get('openai_model', 'gpt-4o'),
                messages=[
                    {"role": "system", "content": "你是一个专业的企业分析师，擅长分析公司的竞争优势和商业模式。请提供详细、准确的分析，并按要求的JSON格式回答。"},
                    {"role": "user", "content": question}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            answer = response.choices[0].message.content
            
            return {
                'question': question,
                'answer': answer,
                'timestamp': datetime.now().isoformat(),
                'search_model': self.config.get('api', {}).get('openai_model', 'gpt-4o'),
                'token_usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
            
        except Exception as e:
            print(f"❌ 提问失败: {e}")
            return {
                'question': question,
                'answer': f'错误：{str(e)}',
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'search_model': 'error'
            }
    
    def extract_json_from_answer(self, answer: str) -> Optional[Dict[str, Any]]:
        """从答案中提取JSON数据"""
        try:
            # 尝试直接解析JSON
            if answer.strip().startswith('{') and answer.strip().endswith('}'):
                return json.loads(answer.strip())
            
            # 查找JSON代码块
            json_pattern = r'```json\s*(.*?)\s*```'
            matches = re.findall(json_pattern, answer, re.DOTALL)
            if matches:
                return json.loads(matches[0].strip())
            
            # 查找花括号内容
            brace_pattern = r'\{[^{}]*\}'
            matches = re.findall(brace_pattern, answer)
            for match in matches:
                try:
                    return json.loads(match)
                except:
                    continue
            
            return None
        except Exception as e:
            print(f"⚠️ JSON提取失败: {e}")
            return None
    
    def analyze_companies(self) -> List[Dict[str, Any]]:
        """分析多个公司（在线模式）"""
        companies = self.config.get('analysis', {}).get('companies', [])
        questions = self.config.get('questions', [])
        results = []
        
        print(f"🚀 开始分析 {len(companies)} 家公司...")
        
        for company in companies:
            print(f"\n📊 正在分析: {company}")
            company_result = {
                'company': company,
                'analysis_time': datetime.now().isoformat(),
                'analysis_mode': 'online',
                'dimensions': {}
            }
            
            for i, question_template in enumerate(questions, 1):
                question = question_template.format(company_name=company)
                print(f"  {i}/{len(questions)}: {self.get_dimension_name(question)}")
                
                result = self.ask_question(question)
                
                # 提取JSON数据
                json_data = self.extract_json_from_answer(result['answer'])
                if json_data:
                    # 尝试提取评分和理由
                    dimension_name = self.get_dimension_name(question)
                    company_result['dimensions'][dimension_name] = {
                        'raw_answer': result['answer'],
                        'extracted_data': json_data,
                        'timestamp': result['timestamp']
                    }
                else:
                    dimension_name = self.get_dimension_name(question)
                    company_result['dimensions'][dimension_name] = {
                        'raw_answer': result['answer'],
                        'extracted_data': None,
                        'timestamp': result['timestamp']
                    }
            
            results.append(company_result)
        
        return results
    
    def analyze_company_with_rag(self) -> Dict[str, Any]:
        """使用RAG分析单个公司（本地模式）"""
        if not self.rag_system:
            raise Exception("RAG系统未初始化")
        
        return self.rag_system.analyze_company_with_rag()
    
    def get_dimension_name(self, question: str) -> str:
        """从问题中提取维度名称"""
        if "网络效应" in question:
            return "网络效应"
        elif "规模效应" in question:
            return "规模效应"
        elif "客户黏性" in question:
            return "客户黏性"
        elif "成本优势" in question:
            return "成本优势"
        elif "竞争格局" in question:
            return "竞争格局"
        elif "进入壁垒" in question:
            return "进入壁垒"
        elif "价格敏感度" in question:
            return "价格敏感度"
        else:
            return "未知维度"
    
    def save_results(self, results: Any, filename: str = None):
        """保存分析结果"""
        if filename is None:
            if self.mode == 'local':
                company_name = self.config.get('local_rag', {}).get('company_name', '未知公司')
                filename = f"rag_analysis_{company_name}.json"
            else:
                filename = self.config.get('output', {}).get('file_path', 'multi_company_analysis.json')
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"✅ 结果已保存到: {filename}")
        except Exception as e:
            print(f"❌ 保存结果失败: {e}")
    
    def run_analysis(self):
        """运行完整分析"""
        print("🎯 企业竞争力分析系统启动")
        print("=" * 50)
        print(f"📋 运行模式: {self.mode}")
        
        # 检查配置
        if not os.path.exists(self.config_path):
            print(f"⚠️ 配置文件不存在，请先复制 config_example.yaml 为 {self.config_path}")
            return
        
        try:
            if self.mode == 'online':
                # 在线模式：分析多个公司
                results = self.analyze_companies()
                self.save_results(results)
                print(f"\n🎉 在线分析完成！共分析了 {len(results)} 家公司")
                
            elif self.mode == 'local':
                # 本地RAG模式：分析单个公司
                if not RAG_AVAILABLE:
                    print("❌ RAG系统不可用，请安装相关依赖包")
                    return
                
                company_name = self.config.get('local_rag', {}).get('company_name', '海康威视')
                print(f"📊 本地RAG模式：分析公司 {company_name}")
                
                result = self.analyze_company_with_rag()
                self.save_results(result)
                print(f"\n🎉 本地RAG分析完成！")
                
            else:
                print(f"❌ 不支持的运行模式: {self.mode}")
                return
            
            print("💡 可以使用交互式仪表板查看结果：python start_dashboard.py")
            
        except Exception as e:
            print(f"❌ 分析过程中出现错误: {e}")

def main():
    """主函数"""
    qa_system = QASystem()
    qa_system.run_analysis()

if __name__ == "__main__":
    main() 