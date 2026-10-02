#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG系统测试脚本
用于验证本地RAG功能是否正常工作
"""

import os
import sys
import tempfile
import json
from pathlib import Path

def create_test_documents():
    """创建测试文档"""
    # 创建临时目录
    test_dir = tempfile.mkdtemp(prefix="rag_test_")
    print(f"创建测试文档目录: {test_dir}")
    
    # 创建测试文档
    documents = {
        "company_overview.txt": """
海康威视数字技术股份有限公司成立于2001年，是全球领先的以视频为核心的智能物联网解决方案和大数据服务提供商。

公司主要业务包括：
1. 视频监控产品：摄像机、录像机、显示器等
2. 智能家居产品：智能门锁、智能摄像头等
3. 机器视觉产品：工业相机、智能读码器等
4. 汽车电子产品：车载摄像头、行车记录仪等

公司在全球拥有超过4万名员工，在中国、美国、英国等地设有研发中心。
        """,
        
        "financial_data.txt": """
海康威视2023年财务数据：

营业收入：841.84亿元，同比增长7.37%
净利润：133.86亿元，同比增长8.06%
研发投入：65.73亿元，占营收比重7.81%
毛利率：45.2%

主要财务指标：
- 总资产：1,156.23亿元
- 净资产：756.45亿元
- 资产负债率：34.6%
- ROE：18.3%

公司现金流充裕，财务状况稳健。
        """,
        
        "market_position.md": """
# 海康威视市场地位

## 全球市场份额
- 视频监控市场：全球第一，市场份额约22%
- 在中国市场份额超过40%
- 产品销往全球180多个国家和地区

## 竞争优势
1. **技术领先**：在AI、云计算、大数据等领域持续投入
2. **产品丰富**：覆盖前端、后端、显示、存储等全产业链
3. **渠道完善**：全球化销售网络
4. **品牌影响力**：连续多年位居全球视频监控市场第一

## 主要竞争对手
- 大华股份
- 宇视科技
- 安讯士（Axis）
- 博世安防
        """
    }
    
    # 写入文档
    for filename, content in documents.items():
        file_path = os.path.join(test_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content.strip())
    
    return test_dir

def test_rag_system():
    """测试RAG系统"""
    try:
        # 导入RAG系统
        from rag_system import RAGSystem
        
        # 创建测试文档
        test_dir = create_test_documents()
        
        # 创建测试配置
        test_config = {
            'mode': {
                'type': 'local',
                'local_api_provider': 'deepseek'
            },
            'api': {
                'deepseek_api_key': 'test_key_here',
                'deepseek_model': 'deepseek-chat',
                'deepseek_base_url': 'https://api.deepseek.com'
            },
            'local_rag': {
                'enabled': True,
                'company_name': '海康威视',
                'documents_folder': test_dir,
                'supported_formats': ['txt', 'md', 'json'],
                'vector_db': {
                    'type': 'chromadb',
                    'persist_directory': './test_vector_db',
                    'collection_name': 'test_knowledge'
                },
                'chunking': {
                    'chunk_size': 500,
                    'chunk_overlap': 100
                },
                'embedding': {
                    'model_name': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                    'device': 'cpu'
                },
                'retrieval': {
                    'top_k': 3,
                    'similarity_threshold': 0.7
                }
            },
            'questions': [
                "请分析{company_name}的网络效应强度，并给出1-10分的评分。请以JSON格式回答，包含评分和理由。"
            ]
        }
        
        # 保存测试配置
        with open('test_config.yaml', 'w', encoding='utf-8') as f:
            import yaml
            yaml.dump(test_config, f, default_flow_style=False, allow_unicode=True)
        
        print("🚀 开始测试RAG系统...")
        
        # 初始化RAG系统
        rag_system = RAGSystem('test_config.yaml')
        
        # 测试文档扫描
        print("\n📁 测试文档扫描...")
        documents = rag_system.scan_documents(test_dir)
        print(f"找到 {len(documents)} 个文档文件")
        for doc in documents:
            print(f"  - {os.path.basename(doc)}")
        
        # 测试文档读取
        print("\n📖 测试文档读取...")
        for doc_path in documents[:2]:  # 只测试前两个文档
            content = rag_system.read_document(doc_path)
            print(f"  - {os.path.basename(doc_path)}: {len(content)} 字符")
        
        # 测试知识库构建
        print("\n🔧 测试知识库构建...")
        success = rag_system.build_knowledge_base()
        if success:
            print("✅ 知识库构建成功")
        else:
            print("❌ 知识库构建失败")
            return False
        
        # 测试文档检索
        print("\n🔍 测试文档检索...")
        test_queries = [
            "海康威视的主要业务是什么？",
            "公司的财务状况如何？",
            "市场地位和竞争优势"
        ]
        
        for query in test_queries:
            print(f"\n查询: {query}")
            relevant_docs = rag_system.retrieve_relevant_docs(query)
            print(f"检索到 {len(relevant_docs)} 个相关文档片段")
            for i, doc in enumerate(relevant_docs[:2]):  # 只显示前两个
                print(f"  {i+1}. 来源: {doc['metadata']['filename']}")
                print(f"     内容: {doc['content'][:100]}...")
        
        print("\n✅ RAG系统基础功能测试完成")
        
        # 清理测试文件
        import shutil
        shutil.rmtree(test_dir)
        if os.path.exists('test_config.yaml'):
            os.remove('test_config.yaml')
        if os.path.exists('./test_vector_db'):
            shutil.rmtree('./test_vector_db')
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入RAG系统失败: {e}")
        print("请确保已安装所有依赖包: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        return False

def test_dependencies():
    """测试依赖包是否正确安装"""
    print("🔍 检查依赖包...")
    
    required_packages = [
        ('chromadb', 'ChromaDB向量数据库'),
        ('sentence_transformers', 'Sentence Transformers嵌入模型'),
        ('langchain', 'LangChain文档处理'),
        ('PyPDF2', 'PDF文档处理'),
        ('docx', 'Word文档处理'),
        ('openpyxl', 'Excel文档处理'),
        ('tiktoken', 'Token计算'),
        ('yaml', 'YAML配置文件'),
        ('requests', 'HTTP请求')
    ]
    
    missing_packages = []
    
    for package, description in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package} - {description}")
        except ImportError:
            print(f"  ❌ {package} - {description} (未安装)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️ 缺少以下依赖包: {', '.join(missing_packages)}")
        print("请运行: pip install -r requirements.txt")
        return False
    else:
        print("\n✅ 所有依赖包已正确安装")
        return True

def main():
    """主函数"""
    print("🎯 RAG系统测试工具")
    print("=" * 50)
    
    # 检查依赖
    if not test_dependencies():
        return
    
    print("\n" + "=" * 50)
    
    # 测试RAG系统
    if test_rag_system():
        print("\n🎉 RAG系统测试通过！")
        print("现在可以使用本地RAG模式进行企业分析了。")
    else:
        print("\n❌ RAG系统测试失败")
        print("请检查错误信息并修复问题。")

if __name__ == "__main__":
    main() 