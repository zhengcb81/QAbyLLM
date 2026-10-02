@echo off
echo 🎯 QAbyLLM 本地RAG分析启动器
echo ================================

echo 检查Python环境...
python --version
if errorlevel 1 (
    echo ❌ Python未安装或不在PATH中
    pause
    exit /b 1
)

echo.
echo 检查配置文件...
if not exist config.yaml (
    echo ❌ 配置文件config.yaml不存在
    pause
    exit /b 1
)

echo.
echo 检查文档文件夹...
if not exist "knowledge_base" (
    echo ⚠️ 文档文件夹不存在，但继续运行...
)

echo.
echo 🚀 开始运行RAG分析...
python qa_system.py

echo.
echo 分析完成！按任意键退出...
pause 