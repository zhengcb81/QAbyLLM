#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地RAG知识库系统
支持文档扫描、向量化存储和基于知识库的问答

安全重建（QA-RAG-SAFE-REBUILD，2026-10-24）：
知识库按 generation 管理：<persist_root>/generations/gen-* 每代是独立的 chroma 持久目录，
<persist_root>/active.json 是唯一 active 指针（临时文件 + fsync + os.replace 原子替换）。
build_knowledge_base 只写 staging generation，完整校验通过并原子切换指针后才清理旧代；
任何失败/中断都不会影响当前 active generation 的可查询性。
"""

import os
import re
import json
import gc
import time
import uuid
import shutil
import hashlib
import yaml
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
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

# 磁盘布局常量
GENERATIONS_DIRNAME = "generations"
ACTIVE_POINTER_FILENAME = "active.json"
STAGING_ADD_BATCH_SIZE = 4096
GENERATION_NAME_PATTERN = re.compile(r"^gen-[0-9A-Za-z._-]+$")

# 进程内仍存活的 chroma 客户端（强引用登记表）。chroma 的后台线程会在客户端对象
# 被 GC 后仍持有 sqlite 文件锁（Windows 上会锁死目录删除），因此用强引用确保
# 清理孤儿 generation 前总能定位并停掉对应客户端；停机后从表中移除。
_live_chroma_clients: List[Any] = []


def _open_chroma_client(path) -> Any:
    """打开（并登记）一个 chroma 持久客户端。"""
    client = chromadb.PersistentClient(path=str(path))
    try:
        client._rag_generation_path = str(path)  # 登记目录，供孤儿清理时定位停机
        _live_chroma_clients.append(client)
    except Exception:  # 登记失败不影响功能
        pass
    return client


def _stop_chroma_client(client: Any) -> None:
    """停掉 chroma 客户端底层 system（释放 sqlite 文件锁），并移出登记表。"""
    try:
        _live_chroma_clients.remove(client)
    except ValueError:
        pass
    system = getattr(client, "_system", None)
    if system is None:
        return
    try:
        system.stop()
    except Exception as e:
        logger.debug(f"chroma system 停止失败（忽略）: {e}")


def _stop_live_clients_for_path(path) -> None:
    target = str(path)
    for client in list(_live_chroma_clients):
        if getattr(client, "_rag_generation_path", None) == target:
            _stop_chroma_client(client)


def _remove_directory(path) -> bool:
    """删除目录：先 gc 释放隐式句柄，OSError 时短暂重试；失败返回 False（留待下次进程清理）。"""
    last_error: Optional[Exception] = None
    for attempt in range(3):
        gc.collect()
        try:
            shutil.rmtree(path)
            return True
        except OSError as e:
            last_error = e
            time.sleep(0.2 * (attempt + 1))
    logger.warning(f"清理目录失败（可能被占用，留待下次清理）: {path}: {last_error}")
    return False


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
        # 进程中断/崩溃注入钩子（默认空，仅测试使用）：staging_created / chunks_built /
        # embedded / staged_validated / before_publish / after_publish / after_cleanup
        self._stage_hooks: Dict[str, Any] = {}

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

    # ------------------------------------------------------------------
    # generation 布局与 active 指针
    # ------------------------------------------------------------------

    def _vector_layout(self) -> Tuple[Path, Path, Path]:
        """返回 (persist 根目录, generations 目录, active 指针文件) 三个路径。"""
        persist_dir = self.config.get('local_rag', {}).get('vector_db', {}).get(
            'persist_directory', './vector_db')
        root = Path(persist_dir)
        return root, root / GENERATIONS_DIRNAME, root / ACTIVE_POINTER_FILENAME

    def _collection_name(self) -> str:
        return self.config.get('local_rag', {}).get('vector_db', {}).get(
            'collection_name', 'company_knowledge')

    def _load_active_pointer(self) -> Tuple[str, Optional[Dict[str, Any]]]:
        """读取并校验 active 指针。

        返回 (state, pointer)：state 为 "absent"（无指针文件）、"ok"（有效）
        或 "invalid"（存在但不可用——JSON 损坏、generation 缺失或 manifest 不一致）。
        """
        _, generations_dir, pointer_path = self._vector_layout()
        if not pointer_path.exists():
            return "absent", None
        try:
            pointer = json.loads(pointer_path.read_text(encoding='utf-8'))
        except Exception as e:
            logger.error(f"active 指针文件无法解析: {e}")
            return "invalid", None
        generation = pointer.get("generation")
        if not isinstance(generation, str) or not GENERATION_NAME_PATTERN.match(generation):
            logger.error(f"active 指针包含非法 generation 名: {generation!r}")
            return "invalid", None
        generation_dir = generations_dir / generation
        if not generation_dir.is_dir():
            logger.error(f"active 指针指向不存在的 generation: {generation}")
            return "invalid", None
        try:
            manifest = json.loads((generation_dir / "manifest.json").read_text(encoding='utf-8'))
            if manifest.get("generation") != generation:
                logger.error("active 指针与 generation manifest 的 generation 不一致")
                return "invalid", None
            if manifest.get("chunk_count") != pointer.get("chunk_count"):
                logger.error("active 指针与 generation manifest 的 chunk_count 不一致")
                return "invalid", None
        except Exception as e:
            logger.error(f"active generation manifest 不可读: {e}")
            return "invalid", None
        return "ok", pointer

    def setup_vector_db(self):
        """设置向量数据库：绑定当前 active generation（若无则不创建任何集合）。"""
        try:
            root, generations_dir, _ = self._vector_layout()
            os.makedirs(generations_dir, exist_ok=True)
            state, pointer = self._load_active_pointer()
            if state == "ok":
                self._bind_active_collection(generations_dir / pointer["generation"])
                logger.info(f"✅ 绑定现有知识库 generation: {pointer['generation']}")
            else:
                if state == "invalid":
                    logger.error("active 指针存在但无效；检索不可用，需一次成功重建恢复")
                else:
                    logger.info("尚无 active generation（等待首次构建）")
                self.vector_db = None
                self.collection = None
        except Exception as e:
            logger.error(f"❌ 向量数据库设置失败: {e}")
            raise

    def _bind_active_collection(self, generation_dir: Path) -> None:
        """把 self.vector_db / self.collection 绑定到指定 generation 目录。"""
        collection_name = self._collection_name()
        client = _open_chroma_client(generation_dir)
        try:
            collection = client.get_collection(name=collection_name)
        except Exception:
            collection = client.create_collection(name=collection_name)
        self.vector_db = client
        self.collection = collection

    @staticmethod
    def _normalize_relpath(file_path: str, folder_path: str) -> str:
        """文档相对 documents 根的归一化路径（posix 分隔符），作为稳定身份。"""
        return os.path.relpath(file_path, folder_path).replace("\\", "/")

    @staticmethod
    def _stable_doc_key(doc_relpath: str) -> str:
        """由相对路径派生的稳定文档 key：枚举顺序无关。"""
        return hashlib.sha1(doc_relpath.encode("utf-8")).hexdigest()[:10]

    def _new_generation_dir(self, generations_dir: Path) -> Path:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        path = generations_dir / f"gen-{stamp}-{uuid.uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=False)
        return path

    def _fire_stage_hook(self, stage: str) -> None:
        hooks = getattr(self, "_stage_hooks", None) or {}
        hook = hooks.get(stage)
        if hook is not None:
            logger.info(f"触发构建阶段钩子: {stage}")
            hook()

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

    # ------------------------------------------------------------------
    # 安全重建：staging -> 校验 -> 原子发布 -> 清理旧代
    # ------------------------------------------------------------------

    def _validate_staging(self, collection, expected_ids: List[str],
                          per_doc_chunks: Dict[str, int]) -> None:
        """发布前对 staging generation 做完整性校验；不一致即抛错（不得发布）。"""
        expected_count = len(expected_ids)
        actual_count = collection.count()
        if actual_count != expected_count:
            raise RuntimeError(
                f"staging 校验失败: chunk 数不一致（期望 {expected_count}，实际 {actual_count}）")
        stored = collection.get(include=["metadatas"])
        if sorted(stored["ids"]) != sorted(expected_ids):
            missing = set(expected_ids) - set(stored["ids"])
            extra = set(stored["ids"]) - set(expected_ids)
            raise RuntimeError(
                f"staging 校验失败: chunk ID 集合不一致（缺失 {len(missing)}，多出 {len(extra)}）")
        stored_sources = {m.get("doc_relpath") for m in stored["metadatas"]}
        expected_sources = set(per_doc_chunks)
        if stored_sources != expected_sources:
            raise RuntimeError(
                f"staging 校验失败: 文档来源不一致"
                f"（缺失 {sorted(expected_sources - stored_sources)}，"
                f"多出 {sorted(stored_sources - expected_sources)}）")

    def _write_manifest(self, generation_dir: Path, manifest: Dict[str, Any]) -> None:
        path = generation_dir / "manifest.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())

    def _publish_pointer(self, pointer_path: Path, payload: Dict[str, Any]) -> None:
        """原子切换 active 指针：写临时文件 + fsync + os.replace。

        原子性边界：os.replace 在 Windows/POSIX 同卷内原子；崩溃只会留下旧指针或
        新指针之一。Windows 不支持目录级 fsync（以 best-effort try/except 处理），
        进程级中断不受影响；断电场景的目录项持久化不在本卡保证范围内。
        """
        tmp_path = pointer_path.with_name(pointer_path.name + ".tmp")
        data = json.dumps(payload, ensure_ascii=False, indent=2)
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, pointer_path)
        try:
            dir_fd = os.open(str(pointer_path.parent), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass  # Windows 无目录 fsync

    def cleanup_orphan_generations(self, min_age_seconds: float = 0.0) -> List[str]:
        """清除非 active 的孤儿 generation 目录，返回已删除路径列表。

        安全规则：active 指针有效时绝不删除其 generation；指针文件存在但无效时
        拒绝清理（无法判定 active）；无指针文件（尚未发布过）时全部视为孤儿。
        """
        _, generations_dir, pointer_path = self._vector_layout()
        if not generations_dir.exists():
            return []
        state, pointer = self._load_active_pointer()
        if pointer_path.exists() and state != "ok":
            logger.error("active 指针无效，拒绝清理 generation（避免误删 active）")
            return []
        active_generation = pointer["generation"] if state == "ok" else None

        removed: List[str] = []
        now = time.time()
        for entry in sorted(generations_dir.iterdir()):
            if not entry.is_dir() or entry.name == active_generation:
                continue
            if not GENERATION_NAME_PATTERN.match(entry.name):
                continue  # 只清理本系统命名的 generation 目录
            try:
                if now - entry.stat().st_mtime < min_age_seconds:
                    continue
            except OSError:
                continue
            _stop_live_clients_for_path(entry)
            if _remove_directory(entry):
                removed.append(str(entry))
                logger.info(f"清除孤儿 generation: {entry.name}")
        return removed

    def build_knowledge_base(self) -> bool:
        """构建知识库（安全重建）。

        返回 True：新 generation 已完整构建、校验通过并原子发布（active 指针已切换）。
        返回 False：本次构建失败，此前的 active generation 完全未受影响、仍可查询。
        进程级中断（SystemExit/KeyboardInterrupt）向上传播，同样不会破坏 active。
        """
        staging_client = None
        published = False
        try:
            started_at = datetime.now().isoformat()
            folder_path = self.config.get('local_rag', {}).get('documents_folder', '')
            if not folder_path:
                logger.error("未配置文档文件夹路径")
                return False

            documents = self.scan_documents(folder_path)
            if not documents:
                logger.error("未找到任何文档文件")
                return False
            # 处理顺序与 chunk ID 一律由归一化相对路径决定，不依赖 os.walk 枚举顺序
            documents = sorted(
                documents, key=lambda p: self._normalize_relpath(p, folder_path))

            root, generations_dir, pointer_path = self._vector_layout()
            os.makedirs(generations_dir, exist_ok=True)
            pointer_state, _previous_pointer = self._load_active_pointer()
            if pointer_state == "invalid":
                logger.warning("active 指针无效；本次重建成功后将发布新的有效指针")

            # ---- staging：新代写入独立目录，绝不触碰当前 active ----
            staging_dir = self._new_generation_dir(generations_dir)
            client = _open_chroma_client(staging_dir)
            staging_client = client
            staging_collection = client.create_collection(name=self._collection_name())
            self._fire_stage_hook("staging_created")

            all_chunks: List[str] = []
            all_metadatas: List[Dict[str, Any]] = []
            all_ids: List[str] = []
            per_doc_chunks: Dict[str, int] = {}
            input_fingerprint = hashlib.sha256()

            for i, doc_path in enumerate(documents):
                logger.info(f"处理文档 {i+1}/{len(documents)}: {os.path.basename(doc_path)}")
                content = self.read_document(doc_path)
                if not content or not content.strip():
                    continue
                doc_relpath = self._normalize_relpath(doc_path, folder_path)
                content_sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
                input_fingerprint.update(f"{doc_relpath}:{content_sha}\n".encode("utf-8"))
                doc_key = self._stable_doc_key(doc_relpath)

                chunks = self.text_splitter.split_text(content)
                accepted = 0
                for chunk in chunks:
                    if len(chunk.strip()) < 50:  # 跳过太短的块
                        continue
                    chunk_id = f"doc-{doc_key}-chunk-{accepted}"
                    metadata = {
                        'source': doc_path,
                        'filename': os.path.basename(doc_path),
                        'doc_relpath': doc_relpath,
                        'chunk_index': accepted,
                        'chunk_size': len(chunk)
                    }
                    all_chunks.append(chunk)
                    all_metadatas.append(metadata)
                    all_ids.append(chunk_id)
                    accepted += 1
                if accepted:
                    per_doc_chunks[doc_relpath] = accepted
            self._fire_stage_hook("chunks_built")

            if not all_chunks:
                logger.error(f"没有有效的文本块；未发布任何变更（staging 保留于 {staging_dir}）")
                return False

            # 生成嵌入向量
            logger.info(f"正在生成 {len(all_chunks)} 个文本块的嵌入向量...")
            embeddings = self.embedding_model.encode(all_chunks, show_progress_bar=True)
            self._fire_stage_hook("embedded")
            embedding_list = embeddings.tolist()

            # 分批写入 staging
            logger.info("正在写入 staging generation...")
            for start in range(0, len(all_ids), STAGING_ADD_BATCH_SIZE):
                end = start + STAGING_ADD_BATCH_SIZE
                staging_collection.add(
                    embeddings=embedding_list[start:end],
                    documents=all_chunks[start:end],
                    metadatas=all_metadatas[start:end],
                    ids=all_ids[start:end]
                )

            # ---- 校验 staging 完整性，通过前绝不发布 ----
            self._validate_staging(staging_collection, all_ids, per_doc_chunks)
            self._fire_stage_hook("staged_validated")

            chunking = self.config.get('local_rag', {}).get('chunking', {})
            manifest = {
                'version': 1,
                'generation': staging_dir.name,
                'collection_name': self._collection_name(),
                'chunk_count': len(all_ids),
                'document_count': len(per_doc_chunks),
                'input_fingerprint': input_fingerprint.hexdigest(),
                'config_fingerprint': {
                    'chunk_size': chunking.get('chunk_size', 1000),
                    'chunk_overlap': chunking.get('chunk_overlap', 200),
                    'embedding_model': self.config.get('local_rag', {}).get(
                        'embedding', {}).get(
                        'model_name',
                        'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'),
                },
                'documents': per_doc_chunks,
                'created_at': started_at,
                'completed_at': datetime.now().isoformat(),
            }
            self._write_manifest(staging_dir, manifest)

            # ---- 原子发布：切换 active 指针 ----
            pointer_payload = {
                'version': 1,
                'generation': staging_dir.name,
                'collection_name': manifest['collection_name'],
                'chunk_count': manifest['chunk_count'],
                'document_count': manifest['document_count'],
                'input_fingerprint': manifest['input_fingerprint'],
                'published_at': datetime.now().isoformat(),
            }
            self._fire_stage_hook("before_publish")
            self._publish_pointer(pointer_path, pointer_payload)
            published = True  # 指针已原子切换 = 新代已发布（此后任何中断都不影响发布事实）
            self._fire_stage_hook("after_publish")

            # ---- 发布成功：重绑到新代（复用 staging 客户端），然后（尽力）清理旧代 ----
            self.vector_db = client
            self.collection = staging_collection
            try:
                removed = self.cleanup_orphan_generations()
            except Exception as cleanup_error:
                removed = []
                logger.warning(f"发布后清理旧代失败（不影响发布结果，留待下次清理）: {cleanup_error}")
            self._fire_stage_hook("after_cleanup")
            logger.info(
                f"✅ 知识库构建完成，已发布 generation {staging_dir.name}"
                f"（{len(all_ids)} 个文本块 / {len(per_doc_chunks)} 个文档），"
                f"清理旧代 {len(removed)} 个")
            return True

        except (SystemExit, KeyboardInterrupt):
            # 进程级中断：如实上抛（不吞、不报成功）；active 未被触碰
            raise
        except Exception as e:
            logger.error(f"❌ 知识库构建失败（旧知识库未受影响，仍可查询）: {e}")
            return False
        finally:
            # 未发布的 staging 客户端在此停机（含 SystemExit 传播路径：finally 仍执行），
            # 释放 sqlite 文件锁，使 staging 目录可被孤儿清理移除；数据保留供取证。
            if staging_client is not None and not published:
                _stop_chroma_client(staging_client)

    def retrieve_relevant_docs(self, query: str) -> List[Dict[str, Any]]:
        """检索相关文档"""
        try:
            if self.collection is None:
                logger.warning("当前没有 active 知识库（未构建或指针无效），无法检索")
                return []

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
