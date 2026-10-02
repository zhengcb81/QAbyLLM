#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地RAG知识库系统
支持文档扫描、向量化存储和基于知识库的问答
"""

import os
import json
import yaml
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import re
import logging
from pathlib import Path

# 文档处理
import PyPDF2
from docx import Document
import openpyxl
import tiktoken

# 向量数据库和嵌入
import chromadb
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document as LangchainDocument

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGSystem:
    """本地RAG知识库系统"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """初始化RAG系统"""
        self.config_path = config_path
        self.config = self.load_config()
        self.embedding_model = None
        self.vector_db = None
        self.collection = None
        self.text_splitter = None
        self.api_client = None
        
        # 初始化组件
        self.setup_embedding_model()
        self.setup_vector_db()
        self.setup_text_splitter()
        self.setup_api_client()
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            else:
                logger.warning(f"配置文件 {self.config_path} 不存在，使用默认配置")
                return self.get_default_config()
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return self.get_default_config()
    
    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'mode': {
                'type': 'local',
                'local_api_provider': 'deepseek'
            },
            'api': {
                'deepseek_api_key': 'your_deepseek_api_key_here',
                'deepseek_model': 'deepseek-chat',
                'deepseek_base_url': 'https://api.deepseek.com'
            },
            'local_rag': {
                'enabled': True,
                'company_name': '海康威视',
                'documents_folder': 'knowledge_base',
                'supported_formats': ['txt', 'md', 'json', 'pdf', 'docx', 'xlsx'],
                'vector_db': {
                    'type': 'chromadb',
                    'persist_directory': './vector_db',
                    'collection_name': 'company_knowledge'
                },
                'chunking': {
                    'chunk_size': 1000,
                    'chunk_overlap': 200
                },
                'embedding': {
                    'model_name': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                    'device': 'cpu'
                },
                'retrieval': {
                    'top_k': 5,
                    'similarity_threshold': 0.7
                }
            }
        }
    
    def setup_embedding_model(self):
        """设置嵌入模型"""
        try:
            model_name = self.config.get('local_rag', {}).get('embedding', {}).get('model_name', 
                'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
            device = self.config.get('local_rag', {}).get('embedding', {}).get('device', 'cpu')
            
            logger.info(f"正在加载嵌入模型: {model_name}")
            self.embedding_model = SentenceTransformer(model_name, device=device)
            logger.info("✅ 嵌入模型加载成功")
        except Exception as e:
            logger.error(f"❌ 嵌入模型加载失败: {e}")
            raise
    
    def setup_vector_db(self):
        """设置向量数据库"""
        try:
            persist_dir = self.config.get('local_rag', {}).get('vector_db', {}).get('persist_directory', './vector_db')
            collection_name = self.config.get('local_rag', {}).get('vector_db', {}).get('collection_name', 'company_knowledge')
            
            # 创建持久化目录
            os.makedirs(persist_dir, exist_ok=True)
            
            # 初始化ChromaDB客户端
            self.vector_db = chromadb.PersistentClient(path=persist_dir)
            
            # 获取或创建集合
            try:
                self.collection = self.vector_db.get_collection(name=collection_name)
                logger.info(f"✅ 找到现有集合: {collection_name}")
            except:
                self.collection = self.vector_db.create_collection(name=collection_name)
                logger.info(f"✅ 创建新集合: {collection_name}")
                
        except Exception as e:
            logger.error(f"❌ 向量数据库设置失败: {e}")
            raise
    
    def setup_text_splitter(self):
        """设置文本分割器"""
        try:
            chunk_size = self.config.get('local_rag', {}).get('chunking', {}).get('chunk_size', 1000)
            chunk_overlap = self.config.get('local_rag', {}).get('chunking', {}).get('chunk_overlap', 200)
            
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""]
            )
            logger.info("✅ 文本分割器设置成功")
        except Exception as e:
            logger.error(f"❌ 文本分割器设置失败: {e}")
            raise
    
    def setup_api_client(self):
        """设置API客户端"""
        try:
            provider = self.config.get('mode', {}).get('local_api_provider', 'deepseek')
            
            if provider == 'deepseek':
                self.api_key = self.config.get('api', {}).get('deepseek_api_key')
                self.api_model = self.config.get('api', {}).get('deepseek_model', 'deepseek-chat')
                self.api_base_url = self.config.get('api', {}).get('deepseek_base_url', 'https://api.deepseek.com')
            elif provider == 'qwen':
                self.api_key = self.config.get('api', {}).get('qwen_api_key')
                self.api_model = self.config.get('api', {}).get('qwen_model', 'qwen-turbo')
                self.api_base_url = self.config.get('api', {}).get('qwen_base_url', 'https://dashscope.aliyuncs.com/api/v1')
            else:
                raise ValueError(f"不支持的API提供商: {provider}")
            
            if not self.api_key or self.api_key.endswith('_here'):
                logger.warning(f"⚠️ 未找到有效的{provider} API密钥")
            else:
                logger.info(f"✅ {provider} API客户端设置成功")
                
        except Exception as e:
            logger.error(f"❌ API客户端设置失败: {e}")
    
    def read_document(self, file_path: str) -> str:
        """读取文档内容"""
        try:
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            elif file_ext == '.md':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            elif file_ext == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return json.dumps(data, ensure_ascii=False, indent=2)
            elif file_ext == '.pdf':
                return self.read_pdf(file_path)
            elif file_ext == '.docx':
                return self.read_docx(file_path)
            elif file_ext in ['.xlsx', '.xls']:
                return self.read_excel(file_path)
            else:
                logger.warning(f"不支持的文件格式: {file_ext}")
                return ""
        except Exception as e:
            logger.error(f"读取文档失败 {file_path}: {e}")
            return ""
    
    def read_pdf(self, file_path: str) -> str:
        """读取PDF文件"""
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            logger.error(f"读取PDF失败 {file_path}: {e}")
            return ""
    
    def read_docx(self, file_path: str) -> str:
        """读取Word文档"""
        try:
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            logger.error(f"读取Word文档失败 {file_path}: {e}")
            return ""
    
    def read_excel(self, file_path: str) -> str:
        """读取Excel文件"""
        try:
            workbook = openpyxl.load_workbook(file_path)
            text = ""
            for sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]
                text += f"工作表: {sheet_name}\n"
                for row in sheet.iter_rows(values_only=True):
                    row_text = "\t".join([str(cell) if cell is not None else "" for cell in row])
                    text += row_text + "\n"
                text += "\n"
            return text
        except Exception as e:
            logger.error(f"读取Excel文件失败 {file_path}: {e}")
            return ""
    
    def scan_documents(self, folder_path: str) -> List[str]:
        """扫描文档文件夹"""
        supported_formats = self.config.get('local_rag', {}).get('supported_formats', ['txt', 'md', 'json', 'pdf', 'docx', 'xlsx'])
        documents = []
        
        if not os.path.exists(folder_path):
            logger.error(f"文档文件夹不存在: {folder_path}")
            return documents
        
        logger.info(f"正在扫描文档文件夹: {folder_path}")
        
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_ext = Path(file).suffix.lower().lstrip('.')
                if file_ext in supported_formats:
                    file_path = os.path.join(root, file)
                    documents.append(file_path)
        
        logger.info(f"找到 {len(documents)} 个文档文件")
        return documents
    
    def build_knowledge_base(self) -> bool:
        """构建知识库"""
        try:
            folder_path = self.config.get('local_rag', {}).get('documents_folder', '')
            if not folder_path:
                logger.error("未配置文档文件夹路径")
                return False
            
            # 扫描文档
            documents = self.scan_documents(folder_path)
            if not documents:
                logger.error("未找到任何文档文件")
                return False
            
            # 清空现有集合
            try:
                self.collection.delete()
                logger.info("清空现有知识库")
            except:
                pass
            
            # 处理文档
            all_chunks = []
            all_metadatas = []
            all_ids = []
            
            for i, doc_path in enumerate(documents):
                logger.info(f"处理文档 {i+1}/{len(documents)}: {os.path.basename(doc_path)}")
                
                # 读取文档内容
                content = self.read_document(doc_path)
                if not content.strip():
                    continue
                
                # 分割文本
                chunks = self.text_splitter.split_text(content)
                
                for j, chunk in enumerate(chunks):
                    if len(chunk.strip()) < 50:  # 跳过太短的块
                        continue
                    
                    chunk_id = f"doc_{i}_chunk_{j}"
                    metadata = {
                        'source': doc_path,
                        'filename': os.path.basename(doc_path),
                        'chunk_index': j,
                        'chunk_size': len(chunk)
                    }
                    
                    all_chunks.append(chunk)
                    all_metadatas.append(metadata)
                    all_ids.append(chunk_id)
            
            if not all_chunks:
                logger.error("没有有效的文本块")
                return False
            
            # 生成嵌入向量
            logger.info(f"正在生成 {len(all_chunks)} 个文本块的嵌入向量...")
            embeddings = self.embedding_model.encode(all_chunks, show_progress_bar=True)
            
            # 存储到向量数据库
            logger.info("正在存储到向量数据库...")
            self.collection.add(
                embeddings=embeddings.tolist(),
                documents=all_chunks,
                metadatas=all_metadatas,
                ids=all_ids
            )
            
            logger.info(f"✅ 知识库构建完成，共处理 {len(all_chunks)} 个文本块")
            return True
            
        except Exception as e:
            logger.error(f"❌ 知识库构建失败: {e}")
            return False
    
    def retrieve_relevant_docs(self, query: str) -> List[Dict[str, Any]]:
        """检索相关文档"""
        try:
            top_k = self.config.get('local_rag', {}).get('retrieval', {}).get('top_k', 5)
            
            # 生成查询向量
            query_embedding = self.embedding_model.encode([query])
            
            # 检索相似文档
            results = self.collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=top_k
            )
            
            relevant_docs = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    relevant_docs.append({
                        'content': doc,
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i] if 'distances' in results else 0
                    })
            
            return relevant_docs
            
        except Exception as e:
            logger.error(f"文档检索失败: {e}")
            return []
    
    def call_api(self, messages: List[Dict[str, str]]) -> str:
        """调用API"""
        try:
            provider = self.config.get('mode', {}).get('local_api_provider', 'deepseek')
            
            if provider == 'deepseek':
                return self.call_deepseek_api(messages)
            elif provider == 'qwen':
                return self.call_qwen_api(messages)
            else:
                raise ValueError(f"不支持的API提供商: {provider}")
                
        except Exception as e:
            logger.error(f"API调用失败: {e}")
            return f"错误：{str(e)}"
    
    def call_deepseek_api(self, messages: List[Dict[str, str]]) -> str:
        """调用DeepSeek API"""
        import time
        
        # DeepSeek R1推理模型需要更长的超时时间
        timeout = 120 if self.api_model == 'deepseek-reasoner' else 60
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                url = f"{self.api_base_url}/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": self.api_model,
                    "messages": messages,
                    "temperature": 0.6,  # R1推荐温度0.5-0.7
                    "max_tokens": 4000   # 增加最大token数
                }
                
                logger.info(f"正在调用DeepSeek API (尝试 {attempt + 1}/{max_retries})，超时设置: {timeout}秒")
                response = requests.post(url, headers=headers, json=data, timeout=timeout)
                response.raise_for_status()
                
                result = response.json()
                return result['choices'][0]['message']['content']
                
            except requests.exceptions.Timeout as e:
                logger.warning(f"API调用超时 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 10  # 递增等待时间
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"DeepSeek API调用失败: 超时 ({timeout}秒)")
                    raise
            except Exception as e:
                logger.error(f"DeepSeek API调用失败: {e}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    raise
    
    def call_qwen_api(self, messages: List[Dict[str, str]]) -> str:
        """调用Qwen API"""
        try:
            url = f"{self.api_base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.api_model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            # DeepSeek R1推理模型需要更长的超时时间
            timeout = 120 if self.api_model == 'deepseek-reasoner' else 60
            response = requests.post(url, headers=headers, json=data, timeout=timeout)
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content']
            
        except Exception as e:
            logger.error(f"Qwen API调用失败: {e}")
            raise
    
    def ask_question_with_rag(self, question: str, company_name: str) -> Dict[str, Any]:
        """基于RAG的问答"""
        try:
            # 检索相关文档
            relevant_docs = self.retrieve_relevant_docs(question)
            
            if not relevant_docs:
                logger.warning("未找到相关文档")
                context = "未找到相关的背景信息。"
            else:
                # 构建上下文
                context_parts = []
                for doc in relevant_docs:
                    context_parts.append(f"文档来源: {doc['metadata']['filename']}")
                    context_parts.append(f"内容: {doc['content']}")
                    context_parts.append("---")
                
                context = "\n".join(context_parts)
            
            # 构建提示词
            system_prompt = f"""你是一个专业的企业分析师，擅长分析公司的竞争优势和商业模式。
你需要基于提供的背景资料来分析{company_name}公司。

请根据以下背景资料回答问题：

{context}

请提供详细、准确的分析，并按要求的JSON格式回答。如果背景资料不足，请明确说明并基于你的专业知识进行合理推测。"""

            user_prompt = question.format(company_name=company_name)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # 调用API
            answer = self.call_api(messages)
            
            return {
                'question': user_prompt,
                'answer': answer,
                'context_sources': [doc['metadata']['filename'] for doc in relevant_docs],
                'context_chunks': len(relevant_docs),
                'timestamp': datetime.now().isoformat(),
                'api_provider': self.config.get('mode', {}).get('local_api_provider', 'deepseek'),
                'company_name': company_name
            }
            
        except Exception as e:
            logger.error(f"RAG问答失败: {e}")
            return {
                'question': question,
                'answer': f'错误：{str(e)}',
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'api_provider': 'error'
            }
    
    def analyze_company_with_rag(self) -> Dict[str, Any]:
        """使用RAG分析公司"""
        try:
            company_name = self.config.get('local_rag', {}).get('company_name', '海康威视')
            questions = self.config.get('questions', [])
            
            logger.info(f"🚀 开始基于RAG分析公司: {company_name}")
            
            # 构建知识库
            if not self.build_knowledge_base():
                raise Exception("知识库构建失败")
            
            # 分析各个维度
            company_result = {
                'company': company_name,
                'analysis_time': datetime.now().isoformat(),
                'analysis_mode': 'local_rag',
                'api_provider': self.config.get('mode', {}).get('local_api_provider', 'deepseek'),
                'documents_folder': self.config.get('local_rag', {}).get('documents_folder', ''),
                'dimensions': {}
            }
            
            for i, question_template in enumerate(questions, 1):
                dimension_name = self.get_dimension_name(question_template)
                logger.info(f"  {i}/{len(questions)}: {dimension_name}")
                
                result = self.ask_question_with_rag(question_template, company_name)
                
                # 提取JSON数据
                json_data = self.extract_json_from_answer(result['answer'])
                
                company_result['dimensions'][dimension_name] = {
                    'raw_answer': result['answer'],
                    'extracted_data': json_data,
                    'context_sources': result.get('context_sources', []),
                    'context_chunks': result.get('context_chunks', 0),
                    'timestamp': result['timestamp']
                }
            
            return company_result
            
        except Exception as e:
            logger.error(f"❌ RAG分析失败: {e}")
            raise
    
    def get_dimension_name(self, question: str) -> str:
        """从问题中提取维度名称"""
        if "网络效应" in question:
            return "网络效应"
        elif "规模效应" in question:
            return "规模效应"
        elif "客户黏性" in question:
            return "客户黏性"
        elif "成本优势" in question:
            return "成本优势"
        elif "竞争格局" in question:
            return "竞争格局"
        elif "进入壁垒" in question:
            return "进入壁垒"
        elif "价格敏感度" in question:
            return "价格敏感度"
        else:
            return "未知维度"
    
    def extract_json_from_answer(self, answer: str) -> Optional[Dict[str, Any]]:
        """从答案中提取JSON数据"""
        try:
            # 尝试直接解析JSON
            if answer.strip().startswith('{') and answer.strip().endswith('}'):
                return json.loads(answer.strip())
            
            # 查找JSON代码块
            json_pattern = r'```json\s*(.*?)\s*```'
            matches = re.findall(json_pattern, answer, re.DOTALL)
            if matches:
                return json.loads(matches[0].strip())
            
            # 查找花括号内容
            brace_pattern = r'\{[^{}]*\}'
            matches = re.findall(brace_pattern, answer)
            for match in matches:
                try:
                    return json.loads(match)
                except:
                    continue
            
            return None
        except Exception as e:
            logger.warning(f"JSON提取失败: {e}")
            return None

def main():
    """主函数 - 测试RAG系统"""
    rag_system = RAGSystem()
    
    try:
        # 分析公司
        result = rag_system.analyze_company_with_rag()
        
        # 保存结果
        output_path = f"rag_analysis_{result['company']}.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ RAG分析完成，结果已保存到: {output_path}")
        
    except Exception as e:
        logger.error(f"❌ RAG分析失败: {e}")

if __name__ == "__main__":
    main() 