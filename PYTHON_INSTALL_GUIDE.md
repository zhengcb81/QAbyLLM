# Python安装指南

## 🚨 问题诊断
您的系统显示"Python未安装或不在PATH中"，需要先安装Python。

## 🐍 Python安装步骤

### 方法1：从官网下载（推荐）

1. **访问Python官网**：https://www.python.org/downloads/
2. **下载Python 3.8+**：点击"Download Python 3.x.x"
3. **运行安装程序**：
   - ✅ 勾选"Add Python to PATH"（重要！）
   - ✅ 勾选"Install for all users"
   - 点击"Install Now"

### 方法2：使用Microsoft Store

1. 打开Microsoft Store
2. 搜索"Python"
3. 安装"Python 3.11"或更新版本

### 方法3：使用Anaconda（适合数据科学）

1. 访问：https://www.anaconda.com/products/distribution
2. 下载Anaconda Individual Edition
3. 安装时选择"Add Anaconda to PATH"

## 🔧 安装后验证

打开新的命令提示符或PowerShell，运行：
```bash
python --version
pip --version
```

应该显示版本信息，如：
```
Python 3.11.5
pip 23.2.1
```

## 🚀 安装完成后的步骤

1. **重新打开终端**（重要！）
2. **导航到项目目录**：
   ```bash
   cd C:\Users\zheng\Projects\QAbyLLM
   ```
3. **安装项目依赖**：
   ```bash
   pip install -r requirements.txt
   ```
4. **运行快速测试**：
   ```bash
   python quick_test.py
   ```

## 🎯 一键安装脚本

安装Python后，您可以使用以下脚本快速设置环境：

### Windows批处理文件
双击运行：`setup_rag.bat`

### Python安装脚本
```bash
python install_dependencies.py
```

## 🔍 常见问题

### Q: 安装后仍显示"Python未找到"
A: 需要重启终端或重新登录Windows

### Q: pip命令不可用
A: 重新安装Python，确保勾选"Add Python to PATH"

### Q: 权限错误
A: 以管理员身份运行命令提示符

## 📞 获取帮助

如果遇到问题，请：
1. 重启计算机
2. 重新安装Python（记得勾选PATH选项）
3. 使用管理员权限运行命令

---

**⚠️ 重要提醒**：安装Python时必须勾选"Add Python to PATH"选项！ 