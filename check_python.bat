@echo off
chcp 65001 >nul
echo.
echo 🐍 Python环境检测工具
echo ================================
echo.

REM 检查python命令
python --version >nul 2>&1
if %errorlevel% == 0 (
    echo ✅ Python已安装
    python --version
    echo.
    
    REM 检查pip
    pip --version >nul 2>&1
    if %errorlevel% == 0 (
        echo ✅ pip已安装
        pip --version
        echo.
        
        echo 🎯 开始安装RAG依赖包...
        echo.
        pip install -r requirements.txt
        echo.
        
        echo 🧪 运行快速测试...
        python quick_test.py
        
    ) else (
        echo ❌ pip未安装，请重新安装Python
    )
    
) else (
    echo ❌ Python未安装或不在PATH中
    echo.
    echo 📋 解决方案：
    echo 1. 访问 https://www.python.org/downloads/
    echo 2. 下载并安装Python 3.8+
    echo 3. 安装时务必勾选 "Add Python to PATH"
    echo 4. 安装完成后重新运行此脚本
    echo.
    echo 💡 或者打开Microsoft Store搜索"Python"安装
)

echo.
echo 按任意键退出...
pause >nul 