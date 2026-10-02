# QAbyLLM 项目总结

## 🎯 项目概述

QAbyLLM 是一个基于大语言模型的企业竞争力分析系统，现已成功实现**双模式运行**：
- **在线模式**：多公司对比分析和交互式数据可视化
- **本地RAG模式**：基于本地文档的单公司深度分析 🆕

## ✅ 已完成功能

### 1. 核心分析系统
- ✅ 智能问答系统 (`qa_system.py`)
- ✅ **本地RAG系统** (`rag_system.py`) 🆕
- ✅ **交互式启动器** (`run_analysis.py`) 🆕
- ✅ 多公司批量分析（在线模式）
- ✅ 单公司深度分析（本地RAG模式）
- ✅ JSON格式数据输出
- ✅ 多API提供商支持（OpenAI、DeepSeek、Qwen）
- ✅ 配置文件管理

### 2. 本地RAG知识库系统 🆕
- ✅ **文档自动扫描**：支持文件夹递归扫描
- ✅ **多格式支持**：PDF、Word、Excel、TXT、Markdown、JSON
- ✅ **智能文本分块**：使用LangChain的RecursiveCharacterTextSplitter
- ✅ **向量数据库**：ChromaDB持久化存储
- ✅ **语义检索**：基于Sentence Transformers的相似度搜索
- ✅ **上下文增强**：检索相关文档片段作为问答上下文
- ✅ **多语言嵌入模型**：支持中文文档处理

### 3. 便宜的API提供商支持 🆕
- ✅ **DeepSeek API**：成本极低，推荐使用
- ✅ **Qwen API**：阿里云通义千问，成本较低
- ✅ **OpenAI API**：保持原有支持
- ✅ **统一接口**：无缝切换不同API提供商

### 4. 交互式可视化仪表板
- ✅ 独立HTML文件 (`enhanced_dashboard.html`)
- ✅ 多种图表类型：
  - 📊 雷达图：多维度竞争力对比
  - 📈 柱状图：各维度评分详细对比
  - 🔥 热力图：评分分布可视化
  - 📋 汇总表：总分和统计信息
- ✅ **核心交互功能**：鼠标悬停显示详细评分理由
- ✅ 文件上传功能（拖拽和点击）
- ✅ 现代化UI设计
- ✅ 响应式布局

### 5. 数据分析维度
- ✅ 网络效应分析
- ✅ 规模效应评估
- ✅ 客户黏性测量
- ✅ 成本优势分析
- ✅ 竞争格局评估
- ✅ 进入壁垒分析
- ✅ 价格敏感度评估

### 6. 示例数据
- ✅ 4家公司分析结果（小米、华为、苹果、三星）
- ✅ 7个维度完整评分和理由
- ✅ 标准JSON数据格式
- ✅ **海康威视RAG分析示例** 🆕

### 7. 部署和使用
- ✅ 零依赖部署（直接打开HTML文件）
- ✅ 本地服务器支持 (`start_dashboard.py`)
- ✅ **交互式配置界面** (`run_analysis.py`) 🆕
- ✅ 完整的项目文档
- ✅ 配置文件模板

## 📁 项目文件结构

```
QAbyLLM/
├── enhanced_dashboard.html      # 🌟 主要交互式仪表板
├── qa_system.py                # 核心分析系统
├── rag_system.py               # 🆕 本地RAG知识库系统
├── run_analysis.py             # 🆕 交互式启动器
├── start_dashboard.py          # 启动器脚本
├── multi_company_analysis.json # 示例分析数据
├── config_example.yaml         # 配置文件模板
├── config.yaml                 # 🆕 实际配置文件
├── requirements.txt            # Python依赖（已更新）
├── vector_db/                  # 🆕 向量数据库存储目录
├── README.md                   # 项目说明（已更新）
├── .gitignore                  # Git忽略文件
└── PROJECT_SUMMARY.md          # 项目总结
```

## 🚀 快速开始

### 方法1：交互式启动（推荐）🆕
```bash
# 安装依赖
pip install -r requirements.txt

# 交互式配置和运行
python run_analysis.py
```

### 方法2：直接使用仪表板
```bash
# 直接在浏览器中打开
open enhanced_dashboard.html
```

### 方法3：本地服务器
```bash
# 启动本地服务器
python start_dashboard.py

# 或手动启动
python -m http.server 8000
# 然后访问 http://localhost:8000/enhanced_dashboard.html
```

### 方法4：命令行运行
```bash
# 1. 配置API密钥
cp config_example.yaml config.yaml
# 编辑 config.yaml 添加 API 密钥

# 2. 运行分析
python qa_system.py

# 3. 查看结果
python start_dashboard.py
```

## 🎨 核心特性

### 双模式运行 🆕
- **在线模式**：使用OpenAI API分析多个公司，适合快速对比
- **本地RAG模式**：基于本地文档深度分析单个公司，适合详细研究

### 本地RAG功能 🆕
- **智能文档处理**：自动识别和处理多种文件格式
- **语义检索**：基于向量相似度的智能文档检索
- **上下文增强**：将相关文档片段作为问答上下文
- **持久化存储**：向量数据库支持增量更新

### 成本优化 🆕
- **DeepSeek API**：成本比OpenAI低90%以上
- **Qwen API**：阿里云服务，成本较低
- **本地嵌入模型**：无需额外API调用费用

### 交互式功能
- **鼠标悬停交互**：在任何图表数据点上悬停，右侧面板实时显示该公司在该维度的详细评分理由
- **文件上传**：支持拖拽和点击上传自定义JSON分析文件
- **多图表联动**：雷达图、柱状图、热力图同步显示数据
- **响应式设计**：适配桌面和移动设备

### 数据格式支持
```json
{
  "company": "海康威视",
  "analysis_mode": "local_rag",
  "api_provider": "deepseek",
  "documents_folder": "knowledge_base",
  "网络效应": {
    "评分": 8,
    "理由": "详细分析理由..."
  },
  "规模效应": {
    "评分": 9,
    "理由": "详细分析理由..."
  }
}
```

## 🛠️ 技术栈

### 后端技术
- **Python 3.6+**: 主要编程语言
- **OpenAI API**: 在线模式LLM服务
- **DeepSeek API**: 低成本LLM服务 🆕
- **Qwen API**: 阿里云LLM服务 🆕

### RAG技术栈 🆕
- **ChromaDB**: 向量数据库
- **Sentence Transformers**: 多语言嵌入模型
- **LangChain**: 文档处理和分块
- **PyPDF2**: PDF文档处理
- **python-docx**: Word文档处理
- **openpyxl**: Excel文档处理

### 前端技术
- **HTML5, CSS3, JavaScript ES6+**: 前端基础
- **Chart.js**: 图表可视化
- **响应式设计**: 移动端适配

### 数据和部署
- **JSON格式**: 数据交换格式
- **YAML配置**: 配置文件管理
- **零依赖部署**: 可直接运行

## 📊 使用示例

### 在线模式示例
```bash
python run_analysis.py
# 选择 1 -> 配置在线模式
# 输入公司: 小米集团,华为,苹果,三星
# 选择 4 -> 运行分析
```

### 本地RAG模式示例
```bash
python run_analysis.py
# 选择 2 -> 配置本地RAG模式
# 选择API: 1 (DeepSeek)
# 输入公司: 海康威视
# 输入路径: knowledge_base
# 选择 4 -> 运行分析
```

## 🎯 应用场景

### 在线模式适用场景
- **投资分析**: 多公司竞争力对比
- **市场研究**: 行业竞争格局分析
- **快速评估**: 基于公开信息的初步分析

### 本地RAG模式适用场景 🆕
- **尽职调查**: 基于内部文档的深度分析
- **战略规划**: 基于详细资料的战略制定
- **学术研究**: 基于大量文献的研究分析
- **投资决策**: 基于财报和研报的深度评估

## 🔧 扩展功能

系统设计具有良好的扩展性：
- ✅ 支持自定义分析维度
- ✅ 支持不同行业的公司分析
- ✅ 可集成更多图表类型
- ✅ 支持数据导出功能
- ✅ **支持多种文档格式** 🆕
- ✅ **支持多种API提供商** 🆕
- ✅ **支持向量数据库扩展** 🆕

## 📝 版本信息

- **当前版本**: v2.0.0 🆕
- **主要更新**: 添加本地RAG模式和多API支持
- **最后更新**: 2025年1月
- **兼容性**: Python 3.6+, 现代浏览器

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📞 联系方式

如有问题，请通过GitHub Issues联系。

---

**🎉 项目v2.0已成功完成，新增本地RAG模式和多API支持，所有核心功能均已实现并测试通过！** 