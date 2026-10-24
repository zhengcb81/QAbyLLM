#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QA-RAG-SAFE-REBUILD 单元测试（fake collection / fake embedder，无模型、无 API、无网络）。

覆盖任务卡验收点：
- 首次构建成功发布并绑定；
- 解析 / embedding / 写入 / 空目录失败时旧库完整保留（指针字节不变、旧代可查询）；
- 发布前 / 后模拟进程中断（SystemExit）可恢复，重启仍绑定上一 active generation；
- active generation 不被 orphan cleanup 删除；指针损坏时 cleanup 拒绝执行；
- 输入枚举重排不串档（chunk ID 由相对路径派生，不依赖 os.walk 顺序）；
- 被删文件的旧 chunk 不进入新代（整代替换规则）；
- 校验不一致 / 指针切换失败不得报成功；
- 废弃 doc_{i}_chunk_{j} 枚举序号 ID（反例断言）。

RED 说明：`preserves_old_library` / `empty_folder` 组在冻结起点（ad389f8）的旧实现上运行时，
旧实现先 delete 再构建，失败后旧库被清空，保留性断言失败（证据见 docs/plans/qa-rag-safe-rebuild-2026-10-24/testlogs/）。
"""

import json
import re
import shutil
from pathlib import Path

import numpy as np
import pytest

import rag_system
from langchain.text_splitter import RecursiveCharacterTextSplitter

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "rag_safe_rebuild"
STABLE_ID_PATTERN = re.compile(r"^doc-[0-9a-f]{10}-chunk-\d+$")
LEGACY_ID_PATTERN = re.compile(r"^doc_\d+_chunk_\d+$")


# --------------------------------------------------------------------------
# Fakes
# --------------------------------------------------------------------------

class FakeEmbedder:
    """确定性假 embedder：向量只依赖文本长度，无模型无网络；fail=True 注入失败。"""

    def __init__(self, fail=False):
        self.fail = fail
        self.calls = 0

    def encode(self, texts, show_progress_bar=False):
        self.calls += 1
        if self.fail:
            raise RuntimeError("注入的 embedding 失败")
        return np.array([[float(len(t) % 97 + 1.0), 1.0] for t in texts])


class FakeCollection:
    """chroma Collection 的最小 fake：add/count/get/query/delete，可注入错误。"""

    def __init__(self, name="company_knowledge"):
        self.name = name
        self.ids = []
        self.documents = []
        self.metadatas = []
        self.embeddings = []
        self.fail_on_add_call = None  # 1-based，第 N 次 add 抛错
        self.add_calls = 0
        self.count_override = None

    def add(self, embeddings=None, documents=None, metadatas=None, ids=None):
        self.add_calls += 1
        if self.fail_on_add_call is not None and self.add_calls >= self.fail_on_add_call:
            raise RuntimeError("注入的向量写入失败")
        self.embeddings.extend(embeddings)
        self.documents.extend(documents)
        self.metadatas.extend(metadatas)
        self.ids.extend(ids)

    def count(self):
        if self.count_override is not None:
            return self.count_override
        return len(self.ids)

    def get(self, include=None):
        include = include or []
        return {
            "ids": list(self.ids),
            "embeddings": list(self.embeddings) if "embeddings" in include else None,
            "documents": list(self.documents) if "documents" in include else None,
            "metadatas": list(self.metadatas) if "metadatas" in include else None,
            "uris": None, "data": None,
        }

    def query(self, query_embeddings=None, n_results=5, **kwargs):
        empty = {"ids": [[]], "embeddings": None, "documents": [[]],
                 "uris": None, "included": [], "data": None,
                 "metadatas": [[]], "distances": [[]]}
        if not self.ids:
            return empty
        take = min(n_results, len(self.ids))
        return {
            "ids": [list(self.ids[:take])],
            "documents": [list(self.documents[:take])],
            "metadatas": [list(self.metadatas[:take])],
            "distances": [[0.5] * take],
            "embeddings": None, "uris": None, "data": None, "included": [],
        }

    def delete(self, ids=None, where=None, **kwargs):
        """chroma 语义：无参 delete 清空集合全部条目，集合对象仍可用（旧实现的清空入口）。"""
        self.ids, self.documents, self.metadatas, self.embeddings = [], [], [], []

    def snapshot(self):
        """(id, doc_relpath, content) 排序列表，用于前后一致性比较。"""
        return sorted(zip(
            self.ids,
            [m.get("doc_relpath", m.get("source")) for m in self.metadatas],
            self.documents,
        ))


class FakeChromaClient:
    """fake chroma 客户端：同一路径的客户端共享集合状态，
    模拟持久化目录上"重启后新客户端能看到旧数据"。"""

    _stores = {}  # path -> {collection_name: FakeCollection}

    def __init__(self, path):
        self.path = str(path)
        self.collections = FakeChromaClient._stores.setdefault(self.path, {})

    def create_collection(self, name):
        col = FakeCollection(name)
        self.collections[name] = col
        return col

    def get_collection(self, name):
        if name not in self.collections:
            raise ValueError(f"Collection {name} does not exist")
        return self.collections[name]


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def write_docs(docs_dir: Path, names=("doc_alpha.md", "doc_beta.txt")):
    """把 fixture 文档复制到临时 documents 根；返回实际写入的路径列表。"""
    docs_dir.mkdir(parents=True, exist_ok=True)
    for name in names:
        shutil.copyfile(FIXTURES / name, docs_dir / name)


def make_config(tmp_root: Path, docs_dir: Path):
    return {
        "local_rag": {
            "documents_folder": str(docs_dir),
            "supported_formats": ["txt", "md"],
            "vector_db": {
                "persist_directory": str(tmp_root / "vector_root"),
                "collection_name": "company_knowledge",
            },
            "chunking": {"chunk_size": 200, "chunk_overlap": 50},
        }
    }


def make_system(tmp_root: Path, docs_dir: Path, embedder=None, hooks=None):
    """绕过重量级 __init__（不加载模型），只装配 build_knowledge_base 需要的属性。"""
    system = rag_system.RAGSystem.__new__(rag_system.RAGSystem)
    system.config_path = str(tmp_root / "config.yaml")
    system.config = make_config(tmp_root, docs_dir)
    system.embedding_model = embedder if embedder is not None else FakeEmbedder()
    system.text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=200, chunk_overlap=50, length_function=len,
        separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""],
    )
    system.api_client = None
    system.vector_db = None
    system.collection = None
    system._stage_hooks = dict(hooks or {})
    return system


@pytest.fixture
def fake_store(monkeypatch):
    """把 rag_system.chromadb.PersistentClient 替换为 fake 工厂（新代码的 staging/绑定均走 fake）。"""
    clients = {}

    def factory(path=None, **kwargs):
        client = FakeChromaClient(path)
        clients[str(path)] = client
        return client

    monkeypatch.setattr(rag_system.chromadb, "PersistentClient", factory)
    return clients


def layout_paths(system):
    root = Path(system.config["local_rag"]["vector_db"]["persist_directory"])
    return root, root / "generations", root / "active.json"


def read_pointer(system):
    """读取 active 指针字节；旧实现无指针文件时返回 None（RED 运行兼容）。"""
    pointer_path = layout_paths(system)[2]
    return pointer_path.read_bytes() if pointer_path.exists() else None


def bind_fresh(tmp_root, docs_dir):
    """模拟重启：新实例 setup_vector_db 后应绑定 active generation。"""
    fresh = make_system(tmp_root, docs_dir)
    fresh.setup_vector_db()
    return fresh


def query_texts(system, n=10):
    docs = system.retrieve_relevant_docs("合成查询")
    return [d["content"] for d in docs], [d["metadata"].get("doc_relpath") for d in docs]


def crash_hook(stage):
    return {stage: lambda: (_ for _ in ()).throw(SystemExit(9))}


# --------------------------------------------------------------------------
# RED 组：失败时旧库必须完整保留（旧实现上这些断言失败，即任务卡要求先重现的根因）
# --------------------------------------------------------------------------

def test_embedding_failure_preserves_old_library(tmp_path, monkeypatch):
    docs_dir = tmp_path / "docs"
    write_docs(docs_dir)
    monkeypatch.setattr(rag_system.chromadb, "PersistentClient",
                        lambda path=None, **kw: FakeChromaClient(path))
    system = make_system(tmp_path / "root", docs_dir)
    system.setup_vector_db()
    assert system.build_knowledge_base() is True
    before_texts, before_rels = query_texts(system)
    assert before_texts, "初始构建后应能检索到内容"
    pointer_before = read_pointer(system)

    system.embedding_model = FakeEmbedder(fail=True)
    assert system.build_knowledge_base() is False
    # 恢复可用的 embedder 再查询：证明旧库数据仍在（而不是被查询失败掩盖）
    system.embedding_model = FakeEmbedder()

    after_texts, after_rels = query_texts(system)
    assert after_texts == before_texts, "embedding 失败后旧库必须保持可检索"
    assert after_rels == before_rels
    if pointer_before is not None:
        assert read_pointer(system) == pointer_before, "失败后 active 指针字节必须不变"


def test_write_failure_preserves_old_library(tmp_path, monkeypatch):
    docs_dir = tmp_path / "docs"
    write_docs(docs_dir)
    monkeypatch.setattr(rag_system.chromadb, "PersistentClient",
                        lambda path=None, **kw: FakeChromaClient(path))
    orig_create = FakeChromaClient.create_collection

    system = make_system(tmp_path / "root", docs_dir)
    system.setup_vector_db()
    assert system.build_knowledge_base() is True
    before_texts, _ = query_texts(system)
    pointer_before = read_pointer(system)

    # 重建时注入写入失败：
    # - 新实现：之后新建的 staging collection 第 1 次 add 抛错；
    # - 旧实现：复用当前 collection，让其下一次 add 抛错。
    def create_with_fail(self, name):
        col = orig_create(self, name)
        col.fail_on_add_call = 1
        return col

    monkeypatch.setattr(FakeChromaClient, "create_collection", create_with_fail)
    system.collection.fail_on_add_call = system.collection.add_calls + 1
    assert system.build_knowledge_base() is False
    assert query_texts(system)[0] == before_texts, "写入失败后旧库必须保持可检索"
    if pointer_before is not None:
        assert read_pointer(system) == pointer_before, "失败后 active 指针字节必须不变"


def test_parse_failure_preserves_old_library(tmp_path, monkeypatch):
    docs_dir = tmp_path / "docs"
    write_docs(docs_dir)
    monkeypatch.setattr(rag_system.chromadb, "PersistentClient",
                        lambda path=None, **kw: FakeChromaClient(path))
    system = make_system(tmp_path / "root", docs_dir)
    system.setup_vector_db()
    assert system.build_knowledge_base() is True
    before_texts, _ = query_texts(system)
    pointer_before = read_pointer(system)

    def failing_read(path):
        raise RuntimeError("注入的解析失败：文档读取抛错")

    system._read_document_strict = failing_read
    assert system.build_knowledge_base() is False
    assert query_texts(system)[0] == before_texts, "解析失败后旧库必须保持可检索"
    if pointer_before is not None:
        assert read_pointer(system) == pointer_before, "失败后 active 指针字节必须不变"


def test_empty_folder_returns_false_and_preserves_old_library(tmp_path, fake_store):
    docs_dir = tmp_path / "docs"
    write_docs(docs_dir)
    system = make_system(tmp_path / "root", docs_dir)
    system.setup_vector_db()
    assert system.build_knowledge_base() is True
    before_texts, _ = query_texts(system)
    pointer_before = read_pointer(system)

    empty_dir = tmp_path / "empty_docs"
    empty_dir.mkdir()
    system.config["local_rag"]["documents_folder"] = str(empty_dir)
    assert system.build_knowledge_base() is False
    assert query_texts(system)[0] == before_texts
    if pointer_before is not None:
        assert read_pointer(system) == pointer_before, "空目录失败后 active 指针字节必须不变"


# --------------------------------------------------------------------------
# GREEN 组：新实现的行为细节
# --------------------------------------------------------------------------

def test_first_build_publishes_generation_and_binds(tmp_path, fake_store):
    docs_dir = tmp_path / "docs"
    write_docs(docs_dir)
    system = make_system(tmp_path / "root", docs_dir)
    system.setup_vector_db()

    assert system.build_knowledge_base() is True

    root, generations_dir, pointer_path = layout_paths(system)
    assert pointer_path.exists(), "首次构建成功后必须存在 active 指针"
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    gens = [p.name for p in generations_dir.iterdir() if p.is_dir()]
    assert gens == [pointer["generation"]], "成功后只应有一代（无孤儿）"
    manifest = json.loads(
        (generations_dir / pointer["generation"] / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["chunk_count"] == pointer["chunk_count"] > 0
    assert manifest["input_fingerprint"]

    fresh = bind_fresh(tmp_path / "root", docs_dir)
    texts, rels = query_texts(fresh)
    assert texts, "重启（新实例）后应能检索 active generation"
    assert set(rels) <= {"doc_alpha.md", "doc_beta.txt"}

    # 稳定 ID：相对路径派生，废弃 doc_{i}_chunk_{j}
    ids = fresh.collection.get(include=[])["ids"]
    assert ids
    for chunk_id in ids:
        assert STABLE_ID_PATTERN.match(chunk_id), f"chunk ID 应由相对路径派生: {chunk_id}"
        assert not LEGACY_ID_PATTERN.match(chunk_id), "不得使用枚举序号 ID"


def test_reordered_enumeration_keeps_id_metadata_binding(tmp_path, fake_store):
    docs_dir = tmp_path / "docs"
    write_docs(docs_dir, ("doc_alpha.md", "doc_beta.txt", "sub_doc_gamma.md"))
    sub = docs_dir / "sub"
    sub.mkdir()
    shutil.move(str(docs_dir / "sub_doc_gamma.md"), str(sub / "doc_gamma.md"))

    system = make_system(tmp_path / "root", docs_dir)
    system.setup_vector_db()
    assert system.build_knowledge_base() is True
    got = system.collection.get(include=["metadatas"])
    mapping_v1 = dict(zip(got["ids"], [m["doc_relpath"] for m in got["metadatas"]]))
    assert "sub/doc_gamma.md" in mapping_v1.values()

    # 模拟 os.walk 顺序变化：scan_documents 返回逆序
    reversed_docs = list(reversed(system.scan_documents(str(docs_dir))))
    system.scan_documents = lambda folder: reversed_docs
    assert system.build_knowledge_base() is True
    got = system.collection.get(include=["metadatas"])
    mapping_v2 = dict(zip(got["ids"], [m["doc_relpath"] for m in got["metadatas"]]))
    assert mapping_v2 == mapping_v1, "枚举顺序变化不得改变 chunk ID 与文件 metadata 的绑定"


def test_removed_file_old_chunks_not_in_new_generation(tmp_path, fake_store):
    docs_dir = tmp_path / "docs"
    write_docs(docs_dir, ("doc_alpha.md", "doc_beta.txt"))
    system = make_system(tmp_path / "root", docs_dir)
    system.setup_vector_db()
    assert system.build_knowledge_base() is True
    v1 = system.collection.snapshot()

    (docs_dir / "doc_beta.txt").unlink()
    assert system.build_knowledge_base() is True

    v2 = system.collection.snapshot()
    assert all(rel != "doc_beta.txt" for _, rel, _ in v2), "被删文件的 chunk 不得进入新代"
    v1_alpha = {cid: (rel, content) for cid, rel, content in v1 if rel == "doc_alpha.md"}
    v2_alpha = {cid: (rel, content) for cid, rel, content in v2 if rel == "doc_alpha.md"}
    assert v1_alpha == v2_alpha, "保留文件的 chunk ID 与内容必须稳定"


def test_short_chunk_document_skipped(tmp_path, fake_store):
    docs_dir = tmp_path / "docs"
    write_docs(docs_dir, ("doc_alpha.md", "tiny_doc_delta.md"))
    system = make_system(tmp_path / "root", docs_dir)
    system.setup_vector_db()
    assert system.build_knowledge_base() is True
    rels = {m["doc_relpath"] for m in system.collection.get(include=["metadatas"])["metadatas"]}
    assert "tiny_doc_delta.md" not in rels, "无有效块的文档应被跳过"
    assert "doc_alpha.md" in rels


def test_crash_before_publish_keeps_previous_active(tmp_path, fake_store):
    docs_dir = tmp_path / "docs"
    write_docs(docs_dir)
    tmp_root = tmp_path / "root"
    system = make_system(tmp_root, docs_dir)
    system.setup_vector_db()
    assert system.build_knowledge_base() is True
    pointer_before = read_pointer(system)
    v1_texts, _ = query_texts(system)

    (docs_dir / "doc_alpha.md").write_text(
        (docs_dir / "doc_alpha.md").read_text(encoding="utf-8") + "\n\n新增段落，内容变化触发重建。",
        encoding="utf-8")
    system._stage_hooks.update(crash_hook("before_publish"))
    with pytest.raises(SystemExit):
        system.build_knowledge_base()

    assert read_pointer(system) == pointer_before, "发布前中断，指针必须不变"
    fresh = bind_fresh(tmp_root, docs_dir)
    assert query_texts(fresh)[0] == v1_texts, "重启后仍应绑定上一 active generation"

    _, generations_dir, _ = layout_paths(system)
    assert len([p for p in generations_dir.iterdir() if p.is_dir()]) == 2, "应存在可识别的孤儿 staging"

    removed = system.cleanup_orphan_generations()
    assert len(removed) == 1, "孤儿 staging 应可清除"
    remaining = [p.name for p in generations_dir.iterdir() if p.is_dir()]
    active = json.loads(read_pointer(system))["generation"]
    assert remaining == [active], "清理后只剩 active generation"


def test_crash_after_publish_new_generation_active(tmp_path, fake_store):
    docs_dir = tmp_path / "docs"
    write_docs(docs_dir)
    tmp_root = tmp_path / "root"
    system = make_system(tmp_root, docs_dir)
    system.setup_vector_db()
    assert system.build_knowledge_base() is True
    pointer_v1 = read_pointer(system)

    (docs_dir / "doc_new.md").write_text(
        "新增文档NEW：内容完全不同且足够长，包含独特关键词NEW标记，用于验证发布后中断时新代已生效，"
        "并且此处刻意写成多段落。\n\n第二段落：NEW关键词再次出现，保证多 chunk。\n" * 2,
        encoding="utf-8")
    system._stage_hooks.update(crash_hook("after_publish"))
    with pytest.raises(SystemExit):
        system.build_knowledge_base()

    pointer_v2 = read_pointer(system)
    assert pointer_v2 != pointer_v1, "发布后中断，指针应已切换到新代"
    fresh = bind_fresh(tmp_root, docs_dir)
    texts, rels = query_texts(fresh)
    assert "doc_new.md" in set(rels), "重启后应绑定新 active generation"

    _, generations_dir, _ = layout_paths(system)
    gens = sorted(p.name for p in generations_dir.iterdir() if p.is_dir())
    assert len(gens) == 2, "旧代成为孤儿但仍在磁盘上"

    removed = fresh.cleanup_orphan_generations()
    assert len(removed) == 1
    remaining = sorted(p.name for p in generations_dir.iterdir() if p.is_dir())
    active = json.loads(pointer_v2)["generation"]
    assert remaining == [active], "清理不得删除 active generation"


def test_pointer_switch_failure_keeps_old(tmp_path, fake_store, monkeypatch):
    docs_dir = tmp_path / "docs"
    write_docs(docs_dir)
    system = make_system(tmp_path / "root", docs_dir)
    system.setup_vector_db()
    assert system.build_knowledge_base() is True
    pointer_before = read_pointer(system)
    v1_texts, _ = query_texts(system)

    def boom(src, dst):
        raise OSError("注入的指针切换失败")

    monkeypatch.setattr(rag_system.os, "replace", boom)
    assert system.build_knowledge_base() is False, "指针切换失败必须返回 False"
    assert read_pointer(system) == pointer_before, "指针字节不得被破坏"
    monkeypatch.undo()
    assert query_texts(system)[0] == v1_texts, "旧库仍可查询"


def test_staging_validation_mismatch_returns_false(tmp_path, fake_store, monkeypatch):
    docs_dir = tmp_path / "docs"
    write_docs(docs_dir)
    system = make_system(tmp_path / "root", docs_dir)
    system.setup_vector_db()
    assert system.build_knowledge_base() is True
    pointer_before = read_pointer(system)

    # 注入校验不一致：之后新建的 collection count 返回错误值
    orig_create = FakeChromaClient.create_collection

    def create_with_bad_count(self, name):
        col = orig_create(self, name)
        col.count_override = 99999
        return col

    monkeypatch.setattr(FakeChromaClient, "create_collection", create_with_bad_count)
    assert system.build_knowledge_base() is False, "staging 校验失败不得发布"
    assert read_pointer(system) == pointer_before


def test_cleanup_refuses_when_pointer_corrupt(tmp_path, fake_store):
    docs_dir = tmp_path / "docs"
    write_docs(docs_dir)
    system = make_system(tmp_path / "root", docs_dir)
    system.setup_vector_db()
    assert system.build_knowledge_base() is True

    _, generations_dir, pointer_path = layout_paths(system)
    valid_pointer_bytes = pointer_path.read_bytes()
    active_gen = json.loads(valid_pointer_bytes)["generation"]

    pointer_path.write_text("{ 不是合法 JSON", encoding="utf-8")
    assert system.cleanup_orphan_generations() == [], "指针损坏时必须拒绝清理"
    assert (generations_dir / active_gen).exists(), "拒绝清理时不得误删任何 generation"

    stray = generations_dir / "gen-19990101-000000-000000-deadbeef"
    stray.mkdir()
    pointer_path.write_bytes(valid_pointer_bytes)
    removed = system.cleanup_orphan_generations()
    assert removed == [str(stray)], "仅清除非 active 的孤儿目录"
    assert (generations_dir / active_gen).exists()


def test_cleanup_never_deletes_active_even_if_older(tmp_path, fake_store):
    docs_dir = tmp_path / "docs"
    write_docs(docs_dir)
    system = make_system(tmp_path / "root", docs_dir)
    system.setup_vector_db()
    assert system.build_knowledge_base() is True
    _, generations_dir, pointer_path = layout_paths(system)
    active_gen = json.loads(pointer_path.read_text(encoding="utf-8"))["generation"]

    removed = system.cleanup_orphan_generations(min_age_seconds=0)
    assert removed == []
    assert (generations_dir / active_gen).is_dir(), "active generation 永远不得被清理删除"


def test_false_return_means_old_queryable_by_fresh_instance(tmp_path, fake_store):
    """失败返回 False 时，用全新实例（模拟重启）验证旧库仍完整可用。"""
    docs_dir = tmp_path / "docs"
    write_docs(docs_dir)
    tmp_root = tmp_path / "root"
    system = make_system(tmp_root, docs_dir)
    system.setup_vector_db()
    assert system.build_knowledge_base() is True
    v1_texts, _ = query_texts(system)

    system.embedding_model = FakeEmbedder(fail=True)
    assert system.build_knowledge_base() is False

    fresh = bind_fresh(tmp_root, docs_dir)
    assert query_texts(fresh)[0] == v1_texts, "重启后旧库必须仍可查询"


# ---- 审查员反例 ----
# 以下测试由独立审查员追加（review 2026-10-24）。每条注入一个既有测试未覆盖的故障/边界，
# 断言否定性安全属性：旧库不被破坏 / 不得报成功 / 可恢复。
# 预期结果标注在 docstring：预期通过 = 回归防线；预期失败 = 审查发现（见 review-report.md）。


def test_review_pointer_tmp_write_failure_returns_false_and_recovers(tmp_path, fake_store):
    """【预期通过】发布时指针 tmp 写入失败：不得报成功、指针字节不变、移除阻塞后可恢复。
    注入 1：上次崩溃遗留 active.json.tmp 残留文件（不得阻塞下次发布）；
    注入 2：active.json.tmp 是目录（open 失败 = 发布通道断路）。"""
    docs_dir = tmp_path / "docs"
    write_docs(docs_dir)
    system = make_system(tmp_path / "root", docs_dir)
    system.setup_vector_db()
    assert system.build_knowledge_base() is True

    root, generations_dir, pointer_path = layout_paths(system)

    # 注入 1：tmp 残留文件不阻塞发布
    (root / "active.json.tmp").write_text("上次中断留下的半截 JSON", encoding="utf-8")
    assert system.build_knowledge_base() is True, "残留 tmp 文件不得阻塞下次发布"
    pointer_before = read_pointer(system)
    v2_texts, _ = query_texts(system)

    # 注入 2：tmp 路径被目录占位 → 发布通道断路
    blocker = root / "active.json.tmp"
    if blocker.exists():
        blocker.unlink()
    blocker.mkdir()
    assert system.build_knowledge_base() is False, "指针 tmp 写入失败必须返回 False"
    assert read_pointer(system) == pointer_before, "发布失败后指针字节不得改变"
    assert query_texts(system)[0] == v2_texts, "旧库必须仍可检索"

    # 可恢复：移除注入的阻塞后重建成功
    blocker.rmdir()
    assert system.build_knowledge_base() is True
    fresh = bind_fresh(tmp_path / "root", docs_dir)
    assert query_texts(fresh)[0]


def test_review_scan_documents_crash_returns_false_and_keeps_old(tmp_path, fake_store, monkeypatch):
    """【预期通过】scan_documents 抛出异常（如权限/IO 错误）：必须返回 False、指针不变、旧库可查。"""
    docs_dir = tmp_path / "docs"
    write_docs(docs_dir)
    system = make_system(tmp_path / "root", docs_dir)
    system.setup_vector_db()
    assert system.build_knowledge_base() is True
    pointer_before = read_pointer(system)
    v1_texts, _ = query_texts(system)

    def scan_boom(folder_path):
        raise RuntimeError("注入的扫描失败（如目录权限拒绝）")

    monkeypatch.setattr(system, "scan_documents", scan_boom)
    assert system.build_knowledge_base() is False
    assert read_pointer(system) == pointer_before
    assert query_texts(system)[0] == v1_texts


def test_review_staging_dir_creation_failure_returns_false(tmp_path, fake_store, monkeypatch):
    """【预期通过】staging 目录创建失败（磁盘满/权限拒绝）：必须返回 False、指针不变、不产生新目录。"""
    docs_dir = tmp_path / "docs"
    write_docs(docs_dir)
    system = make_system(tmp_path / "root", docs_dir)
    system.setup_vector_db()
    assert system.build_knowledge_base() is True
    pointer_before = read_pointer(system)
    _, generations_dir, _ = layout_paths(system)
    gens_before = sorted(p.name for p in generations_dir.iterdir())

    def mkdir_boom(generations_dir):
        raise OSError("注入的 staging 目录创建失败（磁盘满）")

    monkeypatch.setattr(system, "_new_generation_dir", mkdir_boom)
    assert system.build_knowledge_base() is False
    assert read_pointer(system) == pointer_before
    assert sorted(p.name for p in generations_dir.iterdir()) == gens_before, \
        "staging 创建失败不得留下任何目录副作用"


def test_review_active_gen_dir_deleted_externally_degrades_and_recovers(tmp_path, fake_store):
    """【预期通过】active 指向的 generation 目录被外部删除：setup 不得崩溃、检索降级为空，
    一次成功重建后恢复。"""
    docs_dir = tmp_path / "docs"
    write_docs(docs_dir)
    tmp_root = tmp_path / "root"
    system = make_system(tmp_root, docs_dir)
    system.setup_vector_db()
    assert system.build_knowledge_base() is True

    _, generations_dir, pointer_path = layout_paths(system)
    active_gen = json.loads(pointer_path.read_text(encoding="utf-8"))["generation"]
    shutil.rmtree(generations_dir / active_gen)  # 注入：外部误删 active generation

    fresh = make_system(tmp_root, docs_dir)
    fresh.setup_vector_db()  # 不得抛异常
    assert fresh.collection is None, "active 目录缺失时不得绑定到任何集合"
    assert fresh.retrieve_relevant_docs("任意查询") == [], "降级检索应返回空而非崩溃"

    # 恢复：一次成功重建即可发布新指针
    assert fresh.build_knowledge_base() is True
    recovered = bind_fresh(tmp_root, docs_dir)
    texts, _ = query_texts(recovered)
    assert texts, "重建后必须恢复可检索"


def test_review_single_file_parse_failure_must_not_report_success(tmp_path, fake_store):
    """【修复后应通过；修复前为审查发现 F1】单文件解析失败（如 Windows 文件被占用导致
    OSError）不得被吞掉后报成功：build 必须返回 False、指针不变，绝不发布悄悄缺少
    该文档的新代（已索引文档静默消失）。
    修复说明（F1）：构建链路改用 _read_document_strict（解析异常上抛），
    本反例的注入点随之从 read_document 迁移到 _read_document_strict。"""
    docs_dir = tmp_path / "docs"
    write_docs(docs_dir)
    system = make_system(tmp_path / "root", docs_dir)
    system.setup_vector_db()
    assert system.build_knowledge_base() is True
    _, v1_rels = query_texts(system)
    assert "doc_beta.txt" in set(v1_rels), "前置：beta 在旧库中已索引"
    pointer_before = read_pointer(system)

    real_read = system._read_document_strict

    def flaky_read(path):
        if str(path).replace("\\", "/").endswith("doc_beta.txt"):
            raise OSError("注入的解析失败：文件被另一进程占用")
        return real_read(path)

    system._read_document_strict = flaky_read
    result = system.build_knowledge_base()
    assert result is False, (
        "单文件解析失败不得被吞掉后报成功：实现不得发布缺少该文档的新代并返回 True"
        "（详见 review-report.md 发现 F1）")
    assert read_pointer(system) == pointer_before, "解析失败后指针不得切换"
    assert query_texts(system)[0], "旧库必须仍可检索"


def test_review_cleanup_spares_non_system_named_dirs(tmp_path, fake_store):
    """【预期失败 = 审查发现】清理只允许删除“本系统命名”的 generation 目录。
    注入 gen-not-a-real-generation（匹配宽松正则 ^gen-[0-9A-Za-z._-]+$ 但并非本系统
    的时间戳+UUID 命名）与 not_a_gen_at_all（不匹配正则）。后者应存活；
    前者按 docstring“只清理本系统命名的目录”也应存活——当前实现会误删
    （详见 review-report.md 发现 F2）。"""
    docs_dir = tmp_path / "docs"
    write_docs(docs_dir)
    system = make_system(tmp_path / "root", docs_dir)
    system.setup_vector_db()
    assert system.build_knowledge_base() is True
    _, generations_dir, pointer_path = layout_paths(system)
    active_gen = json.loads(pointer_path.read_text(encoding="utf-8"))["generation"]

    loose_match_dir = generations_dir / "gen-not-a-real-generation"
    loose_match_dir.mkdir()
    no_match_dir = generations_dir / "not_a_gen_at_all"
    no_match_dir.mkdir()

    system.cleanup_orphan_generations()

    assert no_match_dir.exists(), "不匹配正则的目录必须存活"
    assert loose_match_dir.exists(), (
        "名为 gen-* 但并非本系统命名（时间戳+UUID）的目录不得被清理删除；"
        "docstring 声称只清理本系统命名的 generation 目录（review-report.md 发现 F2）")
    assert (generations_dir / active_gen).exists(), "active 必须存活"
