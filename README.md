# QAbyLLM - 企业竞争力分析系统

一个基于大语言模型的智能问答和企业竞争力分析系统，支持多公司对比分析和交互式数据可视化。

## 🌟 主要功能

### 1. 智能问答系统
- 支持网络搜索增强的问答
- 集成OpenAI GPT模型
- 本地知识库支持
- 多公司批量分析

### 2. 交互式数据可视化
- **雷达图**: 多维度竞争力对比
- **柱状图**: 各维度评分详细对比  
- **热力图**: 评分分布可视化
- **汇总表**: 总分和统计信息
- **鼠标悬停交互**: 显示详细评分理由

### 3. 企业竞争力分析
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

### 2. 配置设置
```bash
# 复制配置文件模板
cp config_example.yaml config.yaml

# 编辑配置文件，添加您的OpenAI API密钥
# config.yaml 中设置：
# api:
#   openai_api_key: "your_actual_api_key_here"
```

### 3. 运行分析
```bash
# 运行企业分析
python qa_system.py

# 启动交互式仪表板
python start_dashboard.py
```

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
# 访问 http://localhost:8000/interactive_dashboard.html
```

## 📁 项目结构

```
QAbyLLM/
├── qa_system.py              # 主程序
├── enhanced_dashboard.html   # 独立交互式仪表板
├── interactive_dashboard.html # 服务器版仪表板
├── start_dashboard.py        # 仪表板启动器
├── config_example.yaml       # 配置文件模板
├── multi_company_analysis.json # 示例分析结果
├── requirements.txt          # 依赖包列表
└── README.md                # 项目说明
```

## 🔧 配置说明

### API配置
```yaml
api:
  openai_api_key: "your_api_key_here"
  openai_model: "gpt-4o"
  use_openai_search: true
```

### 分析配置
```yaml
analysis:
  companies:
    - "小米集团"
    - "华为" 
    - "苹果"
    - "三星"
```

## 📈 数据格式

系统支持以下JSON数据格式：
```json
{
  "公司名": "公司名称",
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

- **投资分析**: 多公司竞争力对比
- **战略规划**: 行业竞争格局分析
- **市场研究**: 企业优势劣势评估
- **学术研究**: 商业模式分析

## 🛠️ 技术栈

- **后端**: Python, OpenAI API
- **前端**: HTML5, CSS3, JavaScript
- **图表**: Chart.js
- **数据**: JSON格式
- **部署**: 零依赖，可直接运行

## 📝 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📞 联系方式

如有问题，请通过GitHub Issues联系。 