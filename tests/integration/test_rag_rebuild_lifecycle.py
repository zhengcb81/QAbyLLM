#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QA-RAG-SAFE-REBUILD 集成生命周期测试。

使用真实 chromadb（仅建在 pytest 临时根 = 本卡临时根）+ fake embedder + 合成 TXT/MD，
无模型、无 API、无网络。覆盖：
- 首次构建、旧→新成功切换（发布后旧代被清理）；
- 发布前 / 发布后模拟进程中断（SystemExit）后的重启恢复；
- active generation 不被孤儿清理删除；
- 被删文件旧 chunk 不再被检索（整代替换规则）；
- 输入枚举重排下 chunk ID 与 metadata 绑定稳定（真实存储）；
- 失败注入后旧库在真实存储上仍可查询；
- 测试根（documents 树 + sentinel）在构建/中断/清理前后清单与 hash 不变。
"""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

import rag_system
from langchain.text_splitter import RecursiveCharacterTextSplitter

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "rag_safe_rebuild"


class FakeEmbedder:
    """确定性假 embedder（无模型无网络）；fail=True 注入失败。"""

    def __init__(self, fail=False):
        self.fail = fail

    def encode(self, texts, show_progress_bar=False):
        if self.fail:
            raise RuntimeError("注入的 embedding 失败")
        import numpy as np
        return np.array([[float(len(t) % 97 + 1.0), 1.0] for t in texts])


@pytest.fixture(autouse=True)
def release_chroma_clients():
    """测试结束后停掉本进程内所有存活 chroma 客户端，释放 Windows sqlite 锁。"""
    yield
    for client in list(rag_system._live_chroma_clients):
        rag_system._stop_chroma_client(client)


def write_docs(docs_dir: Path, names=("doc_alpha.md", "doc_beta.txt")):
    docs_dir.mkdir(parents=True, exist_ok=True)
    for name in names:
        shutil.copyfile(FIXTURES / name, docs_dir / name)


def make_real_system(tmp_root: Path, docs_dir: Path, embedder=None, hooks=None):
    """真实 chromadb 的 RAGSystem（绕过加载模型的 __init__）。"""
    system = rag_system.RAGSystem.__new__(rag_system.RAGSystem)
    system.config_path = str(tmp_root / "config.yaml")
    system.config = {
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


def fresh_bound(tmp_root: Path, docs_dir: Path):
    """模拟重启：新实例 setup_vector_db 后绑定 active generation。"""
    fresh = make_real_system(tmp_root, docs_dir)
    fresh.setup_vector_db()
    assert fresh.collection is not None, "重启后必须能绑定 active generation"
    return fresh


def layout(tmp_root: Path):
    root = tmp_root / "vector_root"
    return root, root / "generations", root / "active.json"


def gen_names(tmp_root: Path):
    _, generations_dir, _ = layout(tmp_root)
    return sorted(p.name for p in generations_dir.iterdir() if p.is_dir())


def active_generation(tmp_root: Path) -> str:
    _, _, pointer_path = layout(tmp_root)
    return json.loads(pointer_path.read_text(encoding="utf-8"))["generation"]


def all_stored_chunks(system):
    """(id, doc_relpath, content) 全量快照。"""
    got = system.collection.get(include=["metadatas", "documents"])
    return sorted(zip(got["ids"],
                      [m["doc_relpath"] for m in got["metadatas"]],
                      got["documents"]))


def tree_digest(root: Path) -> str:
    """目录递归清单 + 内容 hash 的摘要（sentinel/不变性断言用）。"""
    items = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_file():
            items.append(f"{rel}:{hashlib.sha256(path.read_bytes()).hexdigest()}")
        else:
            items.append(f"{rel}/")
    return hashlib.sha256("\n".join(items).encode("utf-8")).hexdigest()


def crash_hook(stage):
    return {stage: lambda: (_ for _ in ()).throw(SystemExit(9))}


NEW_DOC = ("新增文档NEW：内容完全不同且足够长，包含独特关键词NEW标记，用于验证发布与中断场景，"
           "并且此处刻意写成多段落。\n\n第二段落：NEW关键词再次出现，保证产生多个文本块。\n" * 2)


def test_full_lifecycle_build_query_and_switch(tmp_path):
    docs_dir = tmp_path / "docs"
    write_docs(docs_dir)
    tmp_root = tmp_path / "root"
    system = make_real_system(tmp_root, docs_dir)
    system.setup_vector_db()
    assert system.collection is None  # 尚无 active

    # 首次构建成功：指针存在、可查询
    assert system.build_knowledge_base() is True
    _, _, pointer_path = layout(tmp_root)
    assert pointer_path.exists()
    v1_chunks = all_stored_chunks(fresh_bound(tmp_root, docs_dir))
    assert v1_chunks, "首次构建后应能通过重启实例检索"

    # 旧 -> 新成功切换：内容变化 + 新文件
    (docs_dir / "doc_alpha.md").write_text(
        (docs_dir / "doc_alpha.md").read_text(encoding="utf-8") + "\n\n追加段落：修改后的Alpha内容。",
        encoding="utf-8")
    (docs_dir / "doc_new.md").write_text(NEW_DOC, encoding="utf-8")
    assert system.build_knowledge_base() is True

    v2_chunks = all_stored_chunks(fresh_bound(tmp_root, docs_dir))
    assert any("doc_new.md" == rel for _, rel, _ in v2_chunks)
    assert any("修改后的Alpha内容" in content for _, _, content in v2_chunks)

    # 发布成功后旧代被清理：只剩 active 一代
    assert gen_names(tmp_root) == [active_generation(tmp_root)]

    # 指针与 manifest 一致
    _, generations_dir, pointer_path = layout(tmp_root)
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    manifest = json.loads(
        (generations_dir / pointer["generation"] / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["generation"] == pointer["generation"]
    assert manifest["chunk_count"] == pointer["chunk_count"] == len(v2_chunks)
    assert manifest["input_fingerprint"] == pointer["input_fingerprint"]


def test_interrupt_before_publish_recovery(tmp_path):
    docs_dir = tmp_path / "docs"
    write_docs(docs_dir)
    tmp_root = tmp_path / "root"
    system = make_real_system(tmp_root, docs_dir)
    system.setup_vector_db()
    assert system.build_knowledge_base() is True
    pointer_v1 = (layout(tmp_root)[2]).read_bytes()
    v1_chunks = all_stored_chunks(system)

    (docs_dir / "doc_new.md").write_text(NEW_DOC, encoding="utf-8")
    system._stage_hooks.update(crash_hook("before_publish"))
    with pytest.raises(SystemExit):
        system.build_knowledge_base()

    # 发布前中断：指针不变，重启仍绑定旧 active
    assert (layout(tmp_root)[2]).read_bytes() == pointer_v1
    assert all_stored_chunks(fresh_bound(tmp_root, docs_dir)) == v1_chunks
    assert len(gen_names(tmp_root)) == 2, "staging 成为可识别孤儿"

    # 孤儿清理：staging 被清除，active 保留
    recover = fresh_bound(tmp_root, docs_dir)
    removed = recover.cleanup_orphan_generations()
    assert len(removed) == 1
    assert gen_names(tmp_root) == [active_generation(tmp_root)]

    # 恢复后可正常重建发布
    recover2 = make_real_system(tmp_root, docs_dir)
    recover2.setup_vector_db()
    assert recover2.build_knowledge_base() is True
    chunks = all_stored_chunks(fresh_bound(tmp_root, docs_dir))
    assert any("doc_new.md" == rel for _, rel, _ in chunks)


def test_interrupt_after_publish_recovery(tmp_path):
    docs_dir = tmp_path / "docs"
    write_docs(docs_dir)
    tmp_root = tmp_path / "root"
    system = make_real_system(tmp_root, docs_dir)
    system.setup_vector_db()
    assert system.build_knowledge_base() is True
    pointer_v1 = (layout(tmp_root)[2]).read_bytes()

    (docs_dir / "doc_new.md").write_text(NEW_DOC, encoding="utf-8")
    system._stage_hooks.update(crash_hook("after_publish"))
    with pytest.raises(SystemExit):
        system.build_knowledge_base()

    # 发布后中断：指针已切换，重启绑定新代；旧代成为孤儿但未被误删
    pointer_v2 = (layout(tmp_root)[2]).read_bytes()
    assert pointer_v2 != pointer_v1
    assert active_generation(tmp_root) in gen_names(tmp_root)
    fresh = fresh_bound(tmp_root, docs_dir)
    assert any("doc_new.md" == rel for _, rel, _ in all_stored_chunks(fresh))
    assert len(gen_names(tmp_root)) == 2

    removed = fresh.cleanup_orphan_generations()
    assert len(removed) == 1
    assert gen_names(tmp_root) == [active_generation(tmp_root)], "清理不得删除 active"
    assert any("doc_new.md" == rel for _, rel, _ in all_stored_chunks(
        fresh_bound(tmp_root, docs_dir)))


def test_removed_file_old_chunks_not_served(tmp_path):
    docs_dir = tmp_path / "docs"
    write_docs(docs_dir, ("doc_alpha.md", "doc_beta.txt"))
    tmp_root = tmp_path / "root"
    system = make_real_system(tmp_root, docs_dir)
    system.setup_vector_db()
    assert system.build_knowledge_base() is True
    assert any("doc_beta.txt" == rel for _, rel, _ in all_stored_chunks(system))

    (docs_dir / "doc_beta.txt").unlink()
    assert system.build_knowledge_base() is True

    chunks = all_stored_chunks(fresh_bound(tmp_root, docs_dir))
    assert all(rel != "doc_beta.txt" for _, rel, _ in chunks), \
        "被删文件的旧 chunk 不得残留于新 active generation"


def test_enumeration_reorder_id_stability_real_store(tmp_path):
    docs_dir = tmp_path / "docs"
    write_docs(docs_dir, ("doc_alpha.md", "doc_beta.txt", "sub_doc_gamma.md"))
    sub = docs_dir / "sub"
    sub.mkdir()
    shutil.move(str(docs_dir / "sub_doc_gamma.md"), str(sub / "doc_gamma.md"))
    tmp_root = tmp_path / "root"
    system = make_real_system(tmp_root, docs_dir)
    system.setup_vector_db()
    assert system.build_knowledge_base() is True
    v1 = all_stored_chunks(system)

    reversed_docs = list(reversed(system.scan_documents(str(docs_dir))))
    system.scan_documents = lambda folder: reversed_docs
    assert system.build_knowledge_base() is True
    v2 = all_stored_chunks(fresh_bound(tmp_root, docs_dir))

    assert v2 == v1, "枚举顺序变化不得改变 chunk ID 与 metadata/内容的绑定"


def test_embedding_failure_keeps_active_queryable_real_store(tmp_path):
    """失败注入反例（真实存储）：embedding 失败后旧库通过全新客户端仍完整可查。"""
    docs_dir = tmp_path / "docs"
    write_docs(docs_dir)
    tmp_root = tmp_path / "root"
    system = make_real_system(tmp_root, docs_dir)
    system.setup_vector_db()
    assert system.build_knowledge_base() is True
    pointer_before = (layout(tmp_root)[2]).read_bytes()
    v1_chunks = all_stored_chunks(system)

    system.embedding_model = FakeEmbedder(fail=True)
    assert system.build_knowledge_base() is False
    assert (layout(tmp_root)[2]).read_bytes() == pointer_before

    system.embedding_model = FakeEmbedder()
    assert all_stored_chunks(fresh_bound(tmp_root, docs_dir)) == v1_chunks, \
        "失败后 active generation 必须仍可被新进程完整读取"


def test_documents_tree_and_sentinel_unchanged(tmp_path):
    """测试根 sentinel：构建、中断、清理全流程后 documents 树与 sentinel 清单/hash 不变。"""
    docs_dir = tmp_path / "docs"
    write_docs(docs_dir)
    sentinel = tmp_path / "SENTINEL.bin"
    sentinel.write_bytes(b"qa-rag-safe-rebuild sentinel \x00\x01\x02")
    docs_before = tree_digest(docs_dir)
    sentinel_before = hashlib.sha256(sentinel.read_bytes()).hexdigest()

    tmp_root = tmp_path / "root"
    system = make_real_system(tmp_root, docs_dir)
    system.setup_vector_db()
    assert system.build_knowledge_base() is True

    system._stage_hooks.update(crash_hook("before_publish"))
    (docs_dir / "doc_new.md").write_text(NEW_DOC, encoding="utf-8")
    docs_before_disrupt = tree_digest(docs_dir)
    with pytest.raises(SystemExit):
        system.build_knowledge_base()

    recover = fresh_bound(tmp_root, docs_dir)
    recover.cleanup_orphan_generations()
    assert recover.build_knowledge_base() is True

    # 构建只读 documents：树内容除测试自己写入的 doc_new 外不发生变化
    tree_after = tree_digest(docs_dir)
    assert tree_after == docs_before_disrupt, "构建/中断/清理不得修改 documents 树"
    assert hashlib.sha256(sentinel.read_bytes()).hexdigest() == sentinel_before
    # 未受测试写入影响的部分与最初一致：移除 doc_new 后应回到初始摘要
    (docs_dir / "doc_new.md").unlink()
    assert tree_digest(docs_dir) == docs_before
