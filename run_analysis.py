#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
企业竞争力分析系统启动器
支持在线模式和本地RAG模式的交互式选择
"""

import os
import sys
import yaml
from typing import Dict, Any

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """加载配置文件"""
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        else:
            return {}
    except Exception as e:
        print(f"❌ 加载配置文件失败: {e}")
        return {}

def save_config(config: Dict[str, Any], config_path: str = "config.yaml"):
    """保存配置文件"""
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, indent=2)
        print(f"✅ 配置已保存到: {config_path}")
    except Exception as e:
        print(f"❌ 保存配置文件失败: {e}")

def setup_online_mode(config: Dict[str, Any]) -> Dict[str, Any]:
    """设置在线模式"""
    print("\n🌐 配置在线模式")
    print("=" * 40)
    
    # 设置模式
    if 'mode' not in config:
        config['mode'] = {}
    config['mode']['type'] = 'online'
    
    # 配置OpenAI API
    if 'api' not in config:
        config['api'] = {}
    
    current_key = config['api'].get('openai_api_key', 'your_openai_api_key_here')
    if current_key == 'your_openai_api_key_here':
        print("请输入您的OpenAI API密钥:")
        api_key = input("OpenAI API Key: ").strip()
        if api_key:
            config['api']['openai_api_key'] = api_key
        else:
            print("⚠️ 未输入API密钥，将使用环境变量")
    else:
        print(f"✅ 已配置OpenAI API密钥: {current_key[:10]}...")
    
    # 设置模型
    model = input(f"OpenAI模型 (默认: gpt-4o): ").strip()
    config['api']['openai_model'] = model if model else 'gpt-4o'
    
    # 设置分析公司列表
    print("\n请输入要分析的公司列表 (用逗号分隔):")
    companies_input = input("公司列表 (默认: 小米集团,华为,苹果,三星): ").strip()
    if companies_input:
        companies = [c.strip() for c in companies_input.split(',')]
        if 'analysis' not in config:
            config['analysis'] = {}
        config['analysis']['companies'] = companies
    
    print("✅ 在线模式配置完成")
    return config

def setup_local_rag_mode(config: Dict[str, Any]) -> Dict[str, Any]:
    """设置本地RAG模式"""
    print("\n🏠 配置本地RAG模式")
    print("=" * 40)
    
    # 设置模式
    if 'mode' not in config:
        config['mode'] = {}
    config['mode']['type'] = 'local'
    
    # 选择API提供商
    print("选择API提供商:")
    print("1. DeepSeek (推荐，便宜)")
    print("2. Qwen")
    print("3. OpenAI")
    
    provider_choice = input("请选择 (1-3, 默认: 1): ").strip()
    if provider_choice == '2':
        provider = 'qwen'
    elif provider_choice == '3':
        provider = 'openai'
    else:
        provider = 'deepseek'
    
    config['mode']['local_api_provider'] = provider
    
    # 配置API密钥
    if 'api' not in config:
        config['api'] = {}
    
    if provider == 'deepseek':
        current_key = config['api'].get('deepseek_api_key', 'your_deepseek_api_key_here')
        if current_key == 'your_deepseek_api_key_here':
            print("请输入您的DeepSeek API密钥:")
            api_key = input("DeepSeek API Key: ").strip()
            if api_key:
                config['api']['deepseek_api_key'] = api_key
            else:
                print("⚠️ 未输入API密钥")
        else:
            print(f"✅ 已配置DeepSeek API密钥: {current_key[:10]}...")
    
    elif provider == 'qwen':
        current_key = config['api'].get('qwen_api_key', 'your_qwen_api_key_here')
        if current_key == 'your_qwen_api_key_here':
            print("请输入您的Qwen API密钥:")
            api_key = input("Qwen API Key: ").strip()
            if api_key:
                config['api']['qwen_api_key'] = api_key
            else:
                print("⚠️ 未输入API密钥")
        else:
            print(f"✅ 已配置Qwen API密钥: {current_key[:10]}...")
    
    # 配置本地RAG设置
    if 'local_rag' not in config:
        config['local_rag'] = {}
    
    # 公司名称
    current_company = config['local_rag'].get('company_name', '海康威视')
    company_name = input(f"公司名称 (默认: {current_company}): ").strip()
    config['local_rag']['company_name'] = company_name if company_name else current_company
    
    # 文档文件夹
    current_folder = config['local_rag'].get('documents_folder', 'knowledge_base')
    print(f"\n当前文档文件夹: {current_folder}")
    folder_path = input("文档文件夹路径 (回车保持当前): ").strip()
    if folder_path:
        config['local_rag']['documents_folder'] = folder_path
    
    # 检查文件夹是否存在
    final_folder = config['local_rag']['documents_folder']
    if os.path.exists(final_folder):
        print(f"✅ 文档文件夹存在: {final_folder}")
    else:
        print(f"⚠️ 文档文件夹不存在: {final_folder}")
        print("请确保文件夹路径正确")
    
    config['local_rag']['enabled'] = True
    
    print("✅ 本地RAG模式配置完成")
    return config

def show_current_config(config: Dict[str, Any]):
    """显示当前配置"""
    print("\n📋 当前配置:")
    print("=" * 40)
    
    mode = config.get('mode', {}).get('type', '未设置')
    print(f"运行模式: {mode}")
    
    if mode == 'online':
        companies = config.get('analysis', {}).get('companies', [])
        print(f"分析公司: {', '.join(companies)}")
        api_key = config.get('api', {}).get('openai_api_key', '未设置')
        if api_key != '未设置' and api_key != 'your_openai_api_key_here':
            print(f"OpenAI API: {api_key[:10]}...")
        else:
            print("OpenAI API: 未设置")
    
    elif mode == 'local':
        provider = config.get('mode', {}).get('local_api_provider', '未设置')
        company = config.get('local_rag', {}).get('company_name', '未设置')
        folder = config.get('local_rag', {}).get('documents_folder', '未设置')
        print(f"API提供商: {provider}")
        print(f"分析公司: {company}")
        print(f"文档文件夹: {folder}")

def main():
    """主函数"""
    print("🎯 企业竞争力分析系统启动器")
    print("=" * 50)
    
    # 加载现有配置
    config = load_config()
    
    while True:
        print("\n请选择操作:")
        print("1. 配置在线模式 (使用OpenAI API分析多个公司)")
        print("2. 配置本地RAG模式 (基于本地文档分析单个公司)")
        print("3. 查看当前配置")
        print("4. 运行分析")
        print("5. 退出")
        
        choice = input("\n请选择 (1-5): ").strip()
        
        if choice == '1':
            config = setup_online_mode(config)
            save_config(config)
        
        elif choice == '2':
            config = setup_local_rag_mode(config)
            save_config(config)
        
        elif choice == '3':
            show_current_config(config)
        
        elif choice == '4':
            print("\n🚀 开始运行分析...")
            try:
                from qa_system import QASystem
                qa_system = QASystem()
                qa_system.run_analysis()
            except Exception as e:
                print(f"❌ 运行分析失败: {e}")
                print("请确保已安装所有依赖包: pip install -r requirements.txt")
        
        elif choice == '5':
            print("👋 再见！")
            break
        
        else:
            print("❌ 无效选择，请重新输入")

if __name__ == "__main__":
    main() 