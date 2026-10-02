#!/usr/bin/env python3
# -*- coding: utf-8 -*-

print("🔍 检查RAG依赖包...")

# 检查基础包
try:
    import yaml
    print("✅ yaml - 已安装")
except ImportError:
    print("❌ yaml - 未安装")

try:
    import requests
    print("✅ requests - 已安装")
except ImportError:
    print("❌ requests - 未安装")

# 检查RAG核心包
rag_packages = {
    'chromadb': 'ChromaDB向量数据库',
    'sentence_transformers': 'Sentence Transformers嵌入模型',
    'langchain': 'LangChain文档处理',
    'langchain_community': 'LangChain社区组件'
}

print("\n🧠 RAG核心包检查:")
missing_rag = []

for package, desc in rag_packages.items():
    try:
        __import__(package)
        print(f"✅ {package} - {desc}")
    except ImportError:
        print(f"❌ {package} - {desc} (未安装)")
        missing_rag.append(package)

# 检查文档处理包
doc_packages = {
    'PyPDF2': 'PDF文档处理',
    'docx': 'Word文档处理',
    'openpyxl': 'Excel文档处理',
    'tiktoken': 'Token计算'
}

print("\n📄 文档处理包检查:")
missing_doc = []

for package, desc in doc_packages.items():
    try:
        __import__(package)
        print(f"✅ {package} - {desc}")
    except ImportError:
        print(f"❌ {package} - {desc} (未安装)")
        missing_doc.append(package)

# 总结
total_missing = len(missing_rag) + len(missing_doc)
print(f"\n📊 检查结果:")
print(f"缺失的RAG包: {len(missing_rag)}个")
print(f"缺失的文档处理包: {len(missing_doc)}个")
print(f"总计缺失: {total_missing}个")

if total_missing == 0:
    print("\n🎉 所有依赖包都已安装！可以运行RAG系统")
    print("运行命令: python qa_system.py")
else:
    print(f"\n⚠️ 需要安装 {total_missing} 个依赖包")
    print("安装命令: pip install -r requirements.txt")
    print("或双击运行: setup_rag.bat")

print("\n" + "="*50) 