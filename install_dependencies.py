#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依赖包安装脚本
自动安装QAbyLLM项目所需的所有依赖包
"""

import subprocess
import sys
import os

def run_command(command, description):
    """运行命令并显示结果"""
    print(f"\n🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description}成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description}失败: {e}")
        if e.stdout:
            print(f"输出: {e.stdout}")
        if e.stderr:
            print(f"错误: {e.stderr}")
        return False

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    print(f"🐍 Python版本: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 6):
        print("❌ 需要Python 3.6或更高版本")
        return False
    else:
        print("✅ Python版本符合要求")
        return True

def install_basic_packages():
    """安装基础包"""
    basic_packages = [
        "pip>=21.0",
        "setuptools>=50.0",
        "wheel"
    ]
    
    for package in basic_packages:
        if not run_command(f"pip install --upgrade {package}", f"安装/升级 {package}"):
            return False
    return True

def install_rag_packages():
    """安装RAG相关包"""
    rag_packages = [
        "chromadb>=0.4.0",
        "sentence-transformers>=2.2.0",
        "langchain>=0.1.0",
        "langchain-community>=0.0.10",
    ]
    
    print("\n📦 安装RAG核心包...")
    for package in rag_packages:
        if not run_command(f"pip install {package}", f"安装 {package}"):
            return False
    return True

def install_document_packages():
    """安装文档处理包"""
    doc_packages = [
        "PyPDF2>=3.0.0",
        "python-docx>=0.8.11",
        "openpyxl>=3.1.0",
    ]
    
    print("\n📄 安装文档处理包...")
    for package in doc_packages:
        if not run_command(f"pip install {package}", f"安装 {package}"):
            return False
    return True

def install_other_packages():
    """安装其他依赖包"""
    other_packages = [
        "tiktoken>=0.5.0",
        "requests>=2.25.0",
        "pyyaml>=6.0",
        "python-dotenv>=0.19.0",
        "beautifulsoup4>=4.10.0",
        "matplotlib>=3.5.0",
        "numpy>=1.21.0",
        "seaborn>=0.11.0",
        "openai>=1.0.0"
    ]
    
    print("\n🔧 安装其他依赖包...")
    for package in other_packages:
        if not run_command(f"pip install {package}", f"安装 {package}"):
            return False
    return True

def install_from_requirements():
    """从requirements.txt安装"""
    if os.path.exists("requirements.txt"):
        print("\n📋 从requirements.txt安装依赖...")
        return run_command("pip install -r requirements.txt", "安装requirements.txt中的依赖")
    else:
        print("⚠️ 未找到requirements.txt文件")
        return False

def test_installation():
    """测试安装结果"""
    print("\n🧪 测试安装结果...")
    
    test_packages = [
        'chromadb',
        'sentence_transformers',
        'langchain',
        'PyPDF2',
        'docx',
        'openpyxl',
        'tiktoken',
        'yaml',
        'requests',
        'openai'
    ]
    
    failed_packages = []
    
    for package in test_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package}")
            failed_packages.append(package)
    
    if failed_packages:
        print(f"\n⚠️ 以下包导入失败: {', '.join(failed_packages)}")
        return False
    else:
        print("\n✅ 所有包导入成功")
        return True

def main():
    """主函数"""
    print("🎯 QAbyLLM 依赖包安装工具")
    print("=" * 50)
    
    # 检查Python版本
    if not check_python_version():
        return
    
    print("\n选择安装方式:")
    print("1. 从requirements.txt安装 (推荐)")
    print("2. 分步安装各类依赖包")
    print("3. 仅测试当前安装状态")
    
    choice = input("\n请选择 (1-3): ").strip()
    
    if choice == '1':
        # 从requirements.txt安装
        success = install_from_requirements()
        
    elif choice == '2':
        # 分步安装
        print("\n🚀 开始分步安装依赖包...")
        
        steps = [
            (install_basic_packages, "安装基础包"),
            (install_rag_packages, "安装RAG包"),
            (install_document_packages, "安装文档处理包"),
            (install_other_packages, "安装其他依赖包")
        ]
        
        success = True
        for step_func, step_name in steps:
            print(f"\n📦 {step_name}...")
            if not step_func():
                print(f"❌ {step_name}失败")
                success = False
                break
    
    elif choice == '3':
        # 仅测试
        success = test_installation()
    
    else:
        print("❌ 无效选择")
        return
    
    # 测试安装结果
    if choice in ['1', '2']:
        print("\n" + "=" * 50)
        test_success = test_installation()
        success = success and test_success
    
    # 显示结果
    print("\n" + "=" * 50)
    if success:
        print("🎉 安装完成！")
        print("\n接下来可以:")
        print("1. 运行测试: python test_rag.py")
        print("2. 启动系统: python run_analysis.py")
        print("3. 查看文档: README.md")
    else:
        print("❌ 安装过程中出现问题")
        print("\n建议:")
        print("1. 检查网络连接")
        print("2. 升级pip: pip install --upgrade pip")
        print("3. 使用国内镜像: pip install -i https://pypi.tuna.tsinghua.edu.cn/simple")

if __name__ == "__main__":
    main() 