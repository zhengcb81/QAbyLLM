# QAbyLLM - 企业竞争力分析系统

一个基于大语言模型的智能问答和企业竞争力分析系统，支持**在线模式**和**本地RAG模式**，提供多公司对比分析和交互式数据可视化。

## 🌟 主要功能

### 1. 双模式智能问答系统
- **在线模式**: 使用OpenAI API分析多个公司
- **本地RAG模式**: 基于本地文档构建知识库，分析单个公司
- 支持多种便宜的API提供商（DeepSeek、Qwen等）
- 向量数据库存储和语义检索

### 2. 本地RAG知识库 🆕
- 自动扫描本地文档文件夹
- 支持多种文件格式：PDF、Word、Excel、TXT、Markdown、JSON
- 智能文本分块和向量化存储
- 基于相似度的文档检索
- 上下文增强的问答生成

### 3. 交互式数据可视化
- **雷达图**: 多维度竞争力对比
- **柱状图**: 各维度评分详细对比  
- **热力图**: 评分分布可视化
- **汇总表**: 总分和统计信息
- **鼠标悬停交互**: 显示详细评分理由

### 4. 企业竞争力分析
- 网络效应分析
- 规模效应评估
- 客户黏性测量
- 成本优势分析
- 竞争格局评估
- 进入壁垒分析
- 价格敏感度评估

## 🚀 快速开始

### 1. 环境准备
```bash
# 克隆项目
git clone https://github.com/zhengcb81/QAbyLLM.git
cd QAbyLLM

# 安装依赖
pip install -r requirements.txt
```

### 2. 交互式配置（推荐）
```bash
# 使用交互式启动器
python run_analysis.py
```

### 3. 手动配置
```bash
# 复制配置文件模板
cp config_example.yaml config.yaml

# 编辑配置文件
```

## 🔄 运行模式

### 在线模式
分析多个公司，使用OpenAI API：
```yaml
mode:
  type: "online"
api:
  openai_api_key: "your_api_key_here"
analysis:
  companies: ["小米集团", "华为", "苹果", "三星"]
```

### 本地RAG模式 🆕
基于本地文档分析单个公司：
```yaml
mode:
  type: "local"
  local_api_provider: "deepseek"  # 或 "qwen", "openai"
local_rag:
  company_name: "海康威视"
  documents_folder: "C:\\path\\to\\documents"
api:
  deepseek_api_key: "your_deepseek_api_key_here"
```

## 💰 支持的API提供商

| 提供商 | 成本 | 模型 | 推荐度 |
|--------|------|------|--------|
| **DeepSeek** | 💰 极低 | deepseek-chat | ⭐⭐⭐⭐⭐ |
| **Qwen** | 💰💰 低 | qwen-turbo | ⭐⭐⭐⭐ |
| **OpenAI** | 💰💰💰 高 | gpt-4o | ⭐⭐⭐ |

## 📊 交互式仪表板

### 独立版本（推荐）
直接打开 `enhanced_dashboard.html` 文件，无需服务器：
- 支持JSON文件上传
- 完整的图表展示
- 鼠标悬停显示详细理由
- 现代化界面设计

### 服务器版本
```bash
# 启动本地服务器
python start_dashboard.py
# 访问 http://localhost:8000/enhanced_dashboard.html
```

## 📁 项目结构

```
QAbyLLM/
├── qa_system.py              # 主分析系统
├── rag_system.py             # 🆕 RAG知识库系统
├── run_analysis.py           # 🆕 交互式启动器
├── enhanced_dashboard.html   # 独立交互式仪表板
├── start_dashboard.py        # 仪表板启动器
├── config_example.yaml       # 配置文件模板
├── config.yaml               # 🆕 实际配置文件
├── multi_company_analysis.json # 示例分析结果
├── requirements.txt          # 依赖包列表
├── vector_db/                # 🆕 向量数据库存储
└── README.md                # 项目说明
```

## 🔧 详细配置

### 本地RAG配置
```yaml
local_rag:
  enabled: true
  company_name: "海康威视"
  documents_folder: "knowledge_base"
  supported_formats: ["txt", "md", "json", "pdf", "docx", "xlsx"]
  
  # 向量数据库配置
  vector_db:
    type: "chromadb"
    persist_directory: "./vector_db"
    collection_name: "company_knowledge"
  
  # 文本分块配置
  chunking:
    chunk_size: 1000
    chunk_overlap: 200
  
  # 嵌入模型配置
  embedding:
    model_name: "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    device: "cpu"
  
  # 检索配置
  retrieval:
    top_k: 5
    similarity_threshold: 0.7
```

## 📈 数据格式

系统支持以下JSON数据格式：
```json
{
  "company": "海康威视",
  "analysis_mode": "local_rag",
  "api_provider": "deepseek",
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

## 🎯 使用场景

- **投资分析**: 基于公司文档的深度分析
- **战略规划**: 行业竞争格局分析
- **市场研究**: 企业优势劣势评估
- **学术研究**: 商业模式分析
- **尽职调查**: 基于内部文档的全面评估

## 🛠️ 技术栈

- **后端**: Python, OpenAI/DeepSeek/Qwen API
- **RAG**: ChromaDB, Sentence Transformers, LangChain
- **前端**: HTML5, CSS3, JavaScript
- **图表**: Chart.js
- **数据**: JSON格式
- **部署**: 零依赖，可直接运行

## 📋 使用示例

### 1. 在线模式示例
```bash
python run_analysis.py
# 选择 1 -> 配置在线模式
# 选择 4 -> 运行分析
```

### 2. 本地RAG模式示例
```bash
python run_analysis.py
# 选择 2 -> 配置本地RAG模式
# 输入公司名: 海康威视
# 输入文档路径: knowledge_base
# 选择 4 -> 运行分析
```

## 🔍 RAG工作流程

1. **文档扫描**: 自动扫描指定文件夹中的所有支持格式文档
2. **内容提取**: 从PDF、Word、Excel等文件中提取文本内容
3. **文本分块**: 将长文档分割成适合处理的文本块
4. **向量化**: 使用嵌入模型将文本转换为向量
5. **存储**: 将向量存储到ChromaDB数据库
6. **检索**: 根据问题检索最相关的文档片段
7. **生成**: 基于检索到的上下文生成答案

## 📝 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📞 联系方式

如有问题，请通过GitHub Issues联系。 