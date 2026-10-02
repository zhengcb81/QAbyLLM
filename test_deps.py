#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的依赖测试脚本
"""

print("🔍 测试RAG系统依赖...")
print("=" * 40)

# 测试基础依赖
try:
    import yaml
    print("✅ yaml")
except ImportError as e:
    print(f"❌ yaml: {e}")

try:
    import requests
    print("✅ requests")
except ImportError as e:
    print(f"❌ requests: {e}")

# 测试RAG核心依赖
try:
    import chromadb
    print("✅ chromadb")
except ImportError as e:
    print(f"❌ chromadb: {e}")

try:
    import sentence_transformers
    print("✅ sentence_transformers")
except ImportError as e:
    print(f"❌ sentence_transformers: {e}")

try:
    import langchain
    print("✅ langchain")
except ImportError as e:
    print(f"❌ langchain: {e}")

try:
    import langchain_community
    print("✅ langchain_community")
except ImportError as e:
    print(f"❌ langchain_community: {e}")

# 测试文档处理依赖
try:
    import PyPDF2
    print("✅ PyPDF2")
except ImportError as e:
    print(f"❌ PyPDF2: {e}")

try:
    import docx
    print("✅ python-docx")
except ImportError as e:
    print(f"❌ python-docx: {e}")

try:
    import openpyxl
    print("✅ openpyxl")
except ImportError as e:
    print(f"❌ openpyxl: {e}")

try:
    import tiktoken
    print("✅ tiktoken")
except ImportError as e:
    print(f"❌ tiktoken: {e}")

print("\n" + "=" * 40)
print("依赖测试完成！") 