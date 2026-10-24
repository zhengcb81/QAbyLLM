# QA-RAG-SAFE-REBUILD 交接文档

- 日期：2026-10-24
- 仓库：QAbyLLM（独立 worktree `C:/Users/郑曾波/Projects/QAbyLLM-rag-safe-rebuild`）
- 分支：`codex/qa-rag-safe-rebuild-20261024`
- 冻结起点：`main@ad389f84cd15e54207fc6fcfe4881f86edac63f1`（检查时 origin/main 一致且干净）
- 实现提交：`5d13da5f79b459b62966df6269e37434f4f624ef`
- 最终交付 SHA：`c762e4de96feff3ac0f2b3d3bd3bfe9d72398f99`（实现 + 审查修复）
- 独立审查结论：第二轮复审 **PASS-with-findings**（`docs/plans/qa-rag-safe-rebuild-2026-10-24/review/review-report.md`）；
  第一轮发现 F1(major)/F2(minor) 已在最终 SHA 修复，残留仅 2 条信息级观察（O1 合法为空边界；O2 仅测试钩子可达）。
- 任务卡：company-wiki `docs/plans/du11-source-closure-2026-10-18/harness_lanes/20261024-independent/QA-RAG-SAFE-REBUILD.md`
- PWF：`docs/plans/qa-rag-safe-rebuild-2026-10-24/`（task_plan / findings / progress / testlogs / review）

## 修复的根因

旧 `build_knowledge_base` 先 `collection.delete()` 清空 active 集合再解析/embedding/写入：
任一后续步骤失败旧知识库即永久丢失，调用者只收到 False。同时 chunk ID `doc_{i}_chunk_{j}`
依赖 os.walk 枚举顺序，重排即串档。

## 新机制（rag_system.py）

1. **Generation 布局**：`<persist_root>/generations/gen-<ts>-<uuid8>/` 每代独立 chroma 持久目录
   + `manifest.json`（chunk 数、文档数、input_fingerprint、config_fingerprint、时间戳）。
2. **原子指针**：`<persist_root>/active.json`，发布时 tmp 写入 + fsync + `os.replace`
   （Windows/POSIX 同卷原子）。崩溃只可能留下旧或新指针之一。
3. **安全重建**：构建只写 staging；staging 校验（count / ID 集合 / 来源集合）通过后才切指针；
   切换后重绑客户端，再 best-effort 清理旧代（失败仅留孤儿，下次回收）。
4. **稳定 ID**：`doc-<sha1(relpath)[:10]>-chunk-<N>`，处理顺序按 relpath 排序；
   枚举重排免疫。整代替换：被删文件的旧 chunk 随旧代退役。
5. **失败语义**：`False`=本次失败且旧库完整可查询（指针字节不变）；`True`=新代已发布。
   SystemExit/KeyboardInterrupt 如实上抛；发布后的清理失败不改报 False。
6. **孤儿清理**：`cleanup_orphan_generations(min_age_seconds=0)` 只删非 active 的
   generation 模式目录；指针存在但无效时拒绝清理。构建失败保留 staging 供取证。
7. **Windows 锁管理**：进程内强引用登记 chroma 客户端；清理孤儿前 `client._system.stop()`
   释放 sqlite 锁（stop 会毒化同路径重开，故只停孤儿路径、永不停 active）。

## 兼容性说明

- 公开调用面不变：`RAGSystem(config_path)`、`build_knowledge_base() -> bool`、
  `retrieve_relevant_docs()`（无 active 时返回 []）、metadata 旧键保留并新增 `doc_relpath`。
- **不迁移** legacy 顶层 chroma 布局（任务卡禁 migrate/reset/delete）。既有 `./vector_db`
  顶层文件保持不动；新代码首次成功重建后在同目录新增 `generations/` 与 `active.json`，
  此前（指针缺失期间）检索返回空。源项目 vector_db 前后清单+SHA 一致（见清理证据）。

## 测试（全部离线：合成 TXT/MD、fake embedder、fake/local temp store）

- `python -B -m pytest -q tests/unit/test_rag_safe_rebuild.py tests/integration/test_rag_rebuild_lifecycle.py`
  → 28 passed（单元 21 = 15 实现 + 6 审查员失败注入反例；集成 7 = 真实 chromadb 临时根）。
- 既有 `python -B -m pytest -q tests/` → 97 passed。
- RED 证据（旧实现 3 failed 复现旧库被清空）：`testlogs/red-old-code-*.txt`。
- 第一轮审查反例中 2 条为真实发现（F1/F2），已修复并保留为回归防线；其余 4 条为
  边界回归防线（指针 tmp 残留/目录占位、scan 抛错、staging 创建失败、active 目录被外部删除的降级恢复）。

## 原子性边界（声明）

- `os.replace` 同卷原子；Windows 无目录级 fsync（best-effort，进程级中断不受影响，
  断电目录项持久化不在保证范围）。
- 并发构建：各自 staging 独立，指针最后写入者胜；不变量「active 指向完整一代」始终成立。
- 指针文件损坏（人为/磁盘）：系统以无 active 运行（检索为空），一次成功重建即恢复；
  清理拒绝执行以免误删。

## 交付物清单

| 项 | 位置 |
|---|---|
| 实现 | `rag_system.py`（git diff ad389f8..最终 SHA） |
| 单元测试 | `tests/unit/test_rag_safe_rebuild.py` |
| 集成测试 | `tests/integration/test_rag_rebuild_lifecycle.py` |
| 夹具 | `tests/fixtures/rag_safe_rebuild/`（合成文档） |
| PWF | `docs/plans/qa-rag-safe-rebuild-2026-10-24/` |
| 独立审查 | `docs/plans/qa-rag-safe-rebuild-2026-10-24/review/review-report.md` |
| 测试日志 | `docs/plans/qa-rag-safe-rebuild-2026-10-24/testlogs/` |
| 清理证据 | `testlogs/vector-db-unchanged.txt`（源项目 vector_db 前后清单+SHA 一致） |

未交付：vector_db 数据、真实配置（config.yaml）、公司报告（夹具均为合成内容）。
