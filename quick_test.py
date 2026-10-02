#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试脚本 - 验证RAG系统基本功能
"""

import os
import sys

def test_imports():
    """测试关键模块导入"""
    print("🔍 测试模块导入...")
    
    try:
        import yaml
        print("  ✅ yaml")
    except ImportError as e:
        print(f"  ❌ yaml: {e}")
        return False
    
    try:
        import requests
        print("  ✅ requests")
    except ImportError as e:
        print(f"  ❌ requests: {e}")
        return False
    
    try:
        import chromadb
        print("  ✅ chromadb")
    except ImportError as e:
        print(f"  ❌ chromadb: {e}")
        return False
    
    try:
        import sentence_transformers
        print("  ✅ sentence_transformers")
    except ImportError as e:
        print(f"  ❌ sentence_transformers: {e}")
        return False
    
    try:
        import langchain
        print("  ✅ langchain")
    except ImportError as e:
        print(f"  ❌ langchain: {e}")
        return False
    
    return True

def test_config():
    """测试配置文件"""
    print("\n📋 测试配置文件...")
    
    if not os.path.exists('config.yaml'):
        print("  ❌ config.yaml 不存在")
        return False
    
    try:
        import yaml
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 检查关键配置
        if config.get('mode', {}).get('type') == 'local':
            print("  ✅ 本地RAG模式已配置")
        else:
            print("  ⚠️ 未配置为本地RAG模式")
        
        api_provider = config.get('mode', {}).get('local_api_provider', '')
        if api_provider:
            print(f"  ✅ API提供商: {api_provider}")
        else:
            print("  ❌ 未配置API提供商")
        
        company_name = config.get('local_rag', {}).get('company_name', '')
        if company_name:
            print(f"  ✅ 公司名称: {company_name}")
        else:
            print("  ❌ 未配置公司名称")
        
        docs_folder = config.get('local_rag', {}).get('documents_folder', '')
        if docs_folder:
            print(f"  ✅ 文档文件夹: {docs_folder}")
            if os.path.exists(docs_folder):
                print("  ✅ 文档文件夹存在")
            else:
                print("  ⚠️ 文档文件夹不存在")
        else:
            print("  ❌ 未配置文档文件夹")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 配置文件解析失败: {e}")
        return False

def test_rag_system():
    """测试RAG系统初始化"""
    print("\n🔧 测试RAG系统...")
    
    try:
        from rag_system import RAGSystem
        print("  ✅ RAG系统模块导入成功")
        
        # 尝试初始化
        rag = RAGSystem()
        print("  ✅ RAG系统初始化成功")
        
        return True
        
    except Exception as e:
        print(f"  ❌ RAG系统测试失败: {e}")
        return False

def test_qa_system():
    """测试QA系统"""
    print("\n🎯 测试QA系统...")
    
    try:
        from qa_system import QASystem
        print("  ✅ QA系统模块导入成功")
        
        # 尝试初始化
        qa = QASystem()
        print("  ✅ QA系统初始化成功")
        print(f"  ✅ 运行模式: {qa.mode}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ QA系统测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🎯 QAbyLLM 快速测试工具")
    print("=" * 50)
    
    tests = [
        ("模块导入", test_imports),
        ("配置文件", test_config),
        ("RAG系统", test_rag_system),
        ("QA系统", test_qa_system)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 测试: {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} 测试通过")
            else:
                print(f"❌ {test_name} 测试失败")
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！系统可以正常运行")
        print("\n💡 接下来可以运行:")
        print("   python qa_system.py")
        print("   或")
        print("   python run_analysis.py")
    else:
        print("⚠️ 部分测试失败，请检查错误信息")
        print("\n💡 建议:")
        print("   1. 安装缺失的依赖: pip install -r requirements.txt")
        print("   2. 检查配置文件: config.yaml")
        print("   3. 运行安装脚本: python install_dependencies.py")

if __name__ == "__main__":
    main() 