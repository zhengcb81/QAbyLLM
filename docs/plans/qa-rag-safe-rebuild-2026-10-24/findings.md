# Findings — qa-rag-safe-rebuild-2026-10-24

## 根因（冻结起点 ad389f8 的 rag_system.py）

- `build_knowledge_base()` L287-292：处理文档之前先 `self.collection.delete()`（裸 except pass）。
  之后任一步骤失败（解析全空 L326、embedding L332、add L336）时旧知识库已不可恢复，
  调用者只拿到 False。
- L314 `chunk_id = f"doc_{i}_chunk_{j}"`：i 是 os.walk 枚举序号。枚举顺序变化 → 同一 id 绑到
  不同文件的 metadata（串档）。当前靠“每次全清重建”掩盖。
- L336 一次性 `collection.add`：大库可能触发 chroma 批量上限（sqlite ~5k），失败即全损。
- `setup_vector_db` 在启动即 get/create collection 于 `./vector_db` 根目录：旧布局无 generation 概念。

## 新发现（实现与集成测试期间）

1. chroma `collection.delete()` 无参调用 = 清空集合全部条目（集合对象仍可 add），
   不是 client.delete_collection 的“删除集合”。旧实现的破坏点因此可被 fake 精确复现。
2. Windows 上 chroma PersistentClient 持有 sqlite 文件锁；客户端对象被 GC 后，
   其 System 的后台线程仍可能持有锁，目录 rmtree 失败（WinError 32）。
   `client._system.stop()` 可释放；但 SharedSystemClient 按路径缓存 System，
   停机后同路径在同进程内无法重新打开（"Could not connect to tenant default_tenant"）。
   ⇒ 设计结论：强引用登记表 `_live_chroma_clients`（保证总能停机）；只停孤儿路径的
   客户端、永不停 active 路径；`published` 标记在指针切换后立即置位，finally 只停
   未发布的 staging。
3. 失败 embedder 会同时打断查询路径（retrieve_relevant_docs 也调 encode）：
   保留性断言前必须恢复可用 embedder，否则 RED 证据被查询失败混淆。
4. `finally` 在 SystemExit 传播时仍执行：staging 停机放 finally 覆盖优雅失败与
   进程级中断两类路径；真实 SIGKILL 下锁随进程消亡，由下一进程清理孤儿。
5. 集成测试 autouse fixture 在每个测试后停掉全部存活 chroma 客户端，避免
   pytest 临时目录被锁（Windows）。

## 公开调用面（必须兼容）

- `build_knowledge_base() -> bool`：调用方 porter_analysis.py:45、rag_system.py:539（analyze_company_with_rag）。
- `retrieve_relevant_docs(query)` 用 `self.collection.query`。
- `RAGSystem(config_path="config.yaml")` 构造签名不变。
- 既有 metadata 键（source/filename/chunk_index/chunk_size）保留，新增 doc_relpath。

## 环境

- Python 3.13.9，chromadb 1.5.9，sentence_transformers/langchain 已安装；离线导入 rag_system 可行
  （SentenceTransformer 仅导入不加载模型，无网络）。
- 源仓 vector_db/ 为 gitignore 的运行时目录；worktree 内不存在，测试均建在 pytest tmp_path。
- 既有 tests/（conftest + 5 个测试文件）只覆盖 answer_verifier，与 RAG 无交集；
  根目录 test_rag.py/test_rag_fix.py 是需要真实模型/API 的运行时脚本，不在离线验收范围。

## 新布局

```
<persist_root>/                      # 如 ./vector_db
  active.json                        # 唯一 active 指针（原子替换）
  active.json.tmp                    # 发布时临时文件
  generations/
    gen-<YYYYmmdd-HHMMSS-ffffff>-<uuid8>/
      (chroma 持久目录)
      manifest.json                  # generation/collection_name/chunk_count/document_count/
                                      # input_fingerprint/config_fingerprint/created_at/completed_at
```

- input_fingerprint = sha256( sorted("relpath:sha256(content)") )：重排免疫，可检测输入变化。
- 指针校验：generation 目录存在、manifest 可读且与指针一致，否则视为无 active（查询返回空）。

## 原子性边界（声明）

1. active.json 写入：tmp 写入 + fsync + os.replace。同卷 rename 在 Windows (MoveFileEx
   REPLACE_EXISTING) 与 POSIX 均原子；崩溃只会留下旧或新指针之一。replace 前的 .tmp 残留无害，
   下次发布覆盖。
2. Windows 无目录级 fsync；断电极端场景下 rename 已落盘但目录项可能未持久——接受该边界并记录
   （进程级中断/崩溃不受影响，这正是任务卡验收范围）。
3. 指针损坏（人为/磁盘错误）→ 系统以“无 active”运行（查询为空、可重建恢复），
   cleanup_orphan_generations 拒绝执行以免误删。
4. 并发：两个 build 各自 staging 独立目录，指针最后写入者胜；不变量“active 指向完整一代”仍成立。

## 覆盖/删除旧 chunk 规则

- 重建=整代替换：新代仅含本次扫描产生 chunk 的文件；文件夹中已删除文件的 chunk 不进入新代
  （随旧代一并退役）。反例见集成测试 test_removed_file_old_chunks_not_in_new_generation。
- 解析失败/空文档/短块（<50 字符）跳过：与冻结起点行为一致（continue），不计入 document_count。

## 失败语义

- False：本次失败，旧库完整可用（指针字节不变、旧代目录只读未动）。
- True：新代已通过 staging 校验（count、id 集合、来源数）且指针已原子替换；随后旧代清理为
  best-effort（清理失败不影响 True 的真实性，只产生孤儿，下次清理回收）。
