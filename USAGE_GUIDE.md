# QAbyLLM 使用指南

## 🚀 快速开始

### 1. 安装依赖
```bash
# 方法1：自动安装（推荐）
python install_dependencies.py

# 方法2：手动安装
pip install -r requirements.txt

# 方法3：测试RAG功能
python test_rag.py
```

### 2. 启动系统
```bash
# 交互式启动（推荐）
python run_analysis.py

# 或直接运行
python qa_system.py
```

## 🔄 运行模式选择

### 在线模式 🌐
**适用场景**: 快速对比多个公司
- 使用OpenAI API
- 分析多个公司
- 基于公开信息

**配置步骤**:
1. 运行 `python run_analysis.py`
2. 选择 "1. 配置在线模式"
3. 输入OpenAI API密钥
4. 设置要分析的公司列表
5. 选择 "4. 运行分析"

### 本地RAG模式 🏠
**适用场景**: 基于本地文档深度分析单个公司
- 使用便宜的API（DeepSeek/Qwen）
- 分析单个公司
- 基于本地文档

**配置步骤**:
1. 运行 `python run_analysis.py`
2. 选择 "2. 配置本地RAG模式"
3. 选择API提供商（推荐DeepSeek）
4. 输入API密钥
5. 设置公司名称和文档文件夹路径
6. 选择 "4. 运行分析"

## 💰 API提供商对比

| 提供商 | 成本 | 性能 | 获取方式 | 推荐度 |
|--------|------|------|----------|--------|
| **DeepSeek** | 💰 极低 | ⭐⭐⭐⭐ | [deepseek.com](https://deepseek.com) | ⭐⭐⭐⭐⭐ |
| **Qwen** | 💰💰 低 | ⭐⭐⭐⭐⭐ | [阿里云](https://dashscope.aliyuncs.com) | ⭐⭐⭐⭐ |
| **OpenAI** | 💰💰💰 高 | ⭐⭐⭐⭐⭐ | [openai.com](https://openai.com) | ⭐⭐⭐ |

### DeepSeek API 获取（推荐）
1. 访问 [deepseek.com](https://deepseek.com)
2. 注册账号
3. 获取API密钥
4. 成本约为OpenAI的1/10

### Qwen API 获取
1. 访问 [阿里云DashScope](https://dashscope.aliyuncs.com)
2. 注册阿里云账号
3. 开通通义千问服务
4. 获取API密钥

## 📁 本地文档准备

### 支持的文件格式
- **PDF**: 财务报告、研究报告
- **Word**: 公司介绍、战略规划
- **Excel**: 财务数据、市场数据
- **TXT**: 文本资料
- **Markdown**: 技术文档
- **JSON**: 结构化数据

### 文档组织建议
```
公司文档文件夹/
├── 财务报告/
│   ├── 2023年年报.pdf
│   ├── 2023Q3季报.pdf
│   └── 财务数据.xlsx
├── 研究报告/
│   ├── 行业分析报告.pdf
│   ├── 竞争对手分析.docx
│   └── 市场调研.txt
├── 公司资料/
│   ├── 公司介绍.md
│   ├── 产品手册.pdf
│   └── 战略规划.docx
└── 其他资料/
    ├── 新闻报道.txt
    └── 专利信息.json
```

## 🔧 配置文件说明

### config.yaml 结构
```yaml
# 运行模式
mode:
  type: "local"  # "online" 或 "local"
  local_api_provider: "deepseek"  # "deepseek", "qwen", "openai"

# API配置
api:
  deepseek_api_key: "your_key_here"
  deepseek_model: "deepseek-chat"
  
# 本地RAG配置
local_rag:
  company_name: "海康威视"
  documents_folder: "C:\\path\\to\\documents"
  supported_formats: ["txt", "md", "json", "pdf", "docx", "xlsx"]
```

## 📊 结果查看

### 1. JSON结果文件
分析完成后会生成JSON文件：
- 在线模式: `multi_company_analysis.json`
- 本地RAG模式: `rag_analysis_公司名.json`

### 2. 交互式仪表板
```bash
# 启动仪表板
python start_dashboard.py

# 或直接打开HTML文件
open enhanced_dashboard.html
```

### 3. 结果文件结构
```json
{
  "company": "海康威视",
  "analysis_mode": "local_rag",
  "api_provider": "deepseek",
  "documents_folder": "knowledge_base",
  "网络效应": {
    "评分": 8,
    "理由": "基于本地文档的详细分析..."
  },
  "规模效应": {
    "评分": 9,
    "理由": "..."
  }
}
```

## 🔍 RAG工作原理

### 1. 文档处理流程
```
文档扫描 → 内容提取 → 文本分块 → 向量化 → 存储到数据库
```

### 2. 问答流程
```
用户问题 → 向量检索 → 相关文档 → 上下文构建 → LLM生成答案
```

### 3. 向量数据库
- 使用ChromaDB存储向量
- 支持持久化存储
- 增量更新文档

## 🛠️ 高级配置

### 文本分块参数
```yaml
chunking:
  chunk_size: 1000      # 文本块大小
  chunk_overlap: 200    # 重叠字符数
```

### 检索参数
```yaml
retrieval:
  top_k: 5              # 检索文档数量
  similarity_threshold: 0.7  # 相似度阈值
```

### 嵌入模型
```yaml
embedding:
  model_name: "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
  device: "cpu"         # 或 "cuda"
```

## 🐛 常见问题

### Q1: 依赖包安装失败
**解决方案**:
```bash
# 升级pip
pip install --upgrade pip

# 使用国内镜像
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 分步安装
python install_dependencies.py
```

### Q2: 文档文件夹不存在
**解决方案**:
- 检查文件夹路径是否正确
- 确保路径中包含支持的文件格式
- 使用绝对路径

### Q3: API密钥无效
**解决方案**:
- 检查API密钥是否正确
- 确认API服务商账户状态
- 检查网络连接

### Q4: 向量数据库错误
**解决方案**:
```bash
# 删除向量数据库重新构建
rm -rf ./vector_db

# 重新运行分析
python run_analysis.py
```

### Q5: 内存不足
**解决方案**:
- 减少chunk_size参数
- 减少top_k检索数量
- 使用更小的嵌入模型

## 📈 性能优化

### 1. 硬件优化
- **CPU**: 多核处理器提升文档处理速度
- **内存**: 8GB+推荐，处理大量文档
- **存储**: SSD提升向量数据库性能

### 2. 参数优化
```yaml
# 快速模式（适合测试）
chunking:
  chunk_size: 500
  chunk_overlap: 100
retrieval:
  top_k: 3

# 精确模式（适合生产）
chunking:
  chunk_size: 1000
  chunk_overlap: 200
retrieval:
  top_k: 5
```

### 3. 文档优化
- 清理无关文档
- 使用高质量的文档
- 合理组织文档结构

## 🔄 工作流程示例

### 完整分析流程
```bash
# 1. 安装依赖
python install_dependencies.py

# 2. 测试系统
python test_rag.py

# 3. 配置系统
python run_analysis.py
# 选择本地RAG模式
# 配置API和文档路径

# 4. 运行分析
# 系统自动扫描文档、构建知识库、生成分析

# 5. 查看结果
python start_dashboard.py
# 在浏览器中查看交互式图表
```

## 📞 获取帮助

- **GitHub Issues**: 报告问题和建议
- **文档**: README.md 和 PROJECT_SUMMARY.md
- **测试**: 运行 test_rag.py 验证功能
- **配置**: 参考 config_example.yaml

---

**🎉 开始使用QAbyLLM的本地RAG模式，深度分析您的企业数据！** 