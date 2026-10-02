@echo off
chcp 65001 >nul
echo 🎯 QAbyLLM RAG环境设置
echo ========================

echo 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python未安装或不在PATH中
    echo 请先安装Python 3.7+
    pause
    exit /b 1
)

python --version
echo ✅ Python环境正常

echo.
echo 升级pip...
python -m pip install --upgrade pip --quiet

echo.
echo 安装RAG核心依赖包...
echo [1/8] 安装ChromaDB...
python -m pip install chromadb --quiet
if errorlevel 1 (
    echo ❌ ChromaDB安装失败
) else (
    echo ✅ ChromaDB安装成功
)

echo [2/8] 安装Sentence Transformers...
python -m pip install sentence-transformers --quiet
if errorlevel 1 (
    echo ❌ Sentence Transformers安装失败
) else (
    echo ✅ Sentence Transformers安装成功
)

echo [3/8] 安装LangChain...
python -m pip install langchain --quiet
if errorlevel 1 (
    echo ❌ LangChain安装失败
) else (
    echo ✅ LangChain安装成功
)

echo [4/8] 安装LangChain Community...
python -m pip install langchain-community --quiet
if errorlevel 1 (
    echo ❌ LangChain Community安装失败
) else (
    echo ✅ LangChain Community安装成功
)

echo [5/8] 安装PyPDF2...
python -m pip install PyPDF2 --quiet
if errorlevel 1 (
    echo ❌ PyPDF2安装失败
) else (
    echo ✅ PyPDF2安装成功
)

echo [6/8] 安装python-docx...
python -m pip install python-docx --quiet
if errorlevel 1 (
    echo ❌ python-docx安装失败
) else (
    echo ✅ python-docx安装成功
)

echo [7/8] 安装openpyxl...
python -m pip install openpyxl --quiet
if errorlevel 1 (
    echo ❌ openpyxl安装失败
) else (
    echo ✅ openpyxl安装成功
)

echo [8/8] 安装tiktoken...
python -m pip install tiktoken --quiet
if errorlevel 1 (
    echo ❌ tiktoken安装失败
) else (
    echo ✅ tiktoken安装成功
)

echo.
echo 测试依赖包导入...
python -c "import chromadb; print('✅ ChromaDB导入成功')" 2>nul || echo "❌ ChromaDB导入失败"
python -c "import sentence_transformers; print('✅ Sentence Transformers导入成功')" 2>nul || echo "❌ Sentence Transformers导入失败"
python -c "import langchain; print('✅ LangChain导入成功')" 2>nul || echo "❌ LangChain导入失败"

echo.
echo 运行完整测试...
python quick_test.py

echo.
echo 🎉 设置完成！
echo.
echo 接下来可以运行:
echo   python qa_system.py        (直接运行分析)
echo   python run_analysis.py     (交互式配置)
echo   run_rag_analysis.bat       (批处理运行)
echo.
pause 