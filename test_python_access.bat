@echo off
chcp 65001 >nul
echo.
echo 🐍 Python访问测试工具
echo ================================
echo.

echo 📋 测试1: 直接调用python命令
python --version 2>nul
if %errorlevel% == 0 (
    echo ✅ python命令可用
    python --version
) else (
    echo ❌ python命令不可用
)

echo.
echo 📋 测试2: 使用完整路径调用
C:\Users\zheng\anaconda3\python.exe --version 2>nul
if %errorlevel% == 0 (
    echo ✅ 完整路径Python可用
    C:\Users\zheng\anaconda3\python.exe --version
) else (
    echo ❌ 完整路径Python不可用
)

echo.
echo 📋 测试3: 检查PATH环境变量
echo PATH中的Anaconda相关路径:
echo %PATH% | findstr /i anaconda

echo.
echo 💡 解决方案:
echo 1. 如果python命令不可用，请尝试以下方法:
echo    - 重新启动命令提示符/PowerShell
echo    - 重新启动计算机
echo    - 或者使用完整路径: C:\Users\zheng\anaconda3\python.exe
echo.
echo 2. 创建python命令别名:
echo    doskey python=C:\Users\zheng\anaconda3\python.exe $*
echo    doskey pip=C:\Users\zheng\anaconda3\Scripts\pip.exe $*
echo.

echo 🚀 快速启动Python:
echo 输入以下命令之一:
echo   python          (如果PATH正常)
echo   C:\Users\zheng\anaconda3\python.exe  (完整路径)
echo.

pause 