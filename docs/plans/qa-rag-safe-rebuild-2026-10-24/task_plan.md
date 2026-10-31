## ROOT 主线发布记录（2026-10-31）

已验收作者提交5e5f22b2d7d652738e54bbfaced1982117616c7a现已快进合入本仓main；ROOT独立稀疏工区重新验证：28 focused+real-temporary-store pytest PASS/78.27s; only existingPyPDF2deprecation。原件/生产配置/作者树未动；MeetingConverter原.coverage保持。正常提交本发布记录后推远端，最终SHA与远端匹配由company-wiki总控PWF记录；本段不虚构CI已绿。

# QA-RAG-SAFE-REBUILD：安全重建本地知识库

PLAN_ID: qa-rag-safe-rebuild-2026-10-24
PWF_PLAN_ROOT: docs/plans
任务卡：docs/plans/du11-source-closure-2026-10-18/harness_lanes/20261024-independent/QA-RAG-SAFE-REBUILD.md（company-wiki 仓）
仓库：QAbyLLM-rag-safe-rebuild worktree，branch codex/qa-rag-safe-rebuild-20261024，冻结起点 main@ad389f84cd15e54207fc6fcfe4881f86edac63f1

## Goal

修复 rag_system.build_knowledge_base「先清空 active collection、后构建」的破坏性根因：
新库在独立 generation 目录完整构造并校验通过之前，旧库必须可查询且记录不变；
失败或中断不得错误发布新库；成功发布后才清理旧代。

## 唯一写入范围

允许：rag_system.py；tests/unit/test_rag_safe_rebuild.py；tests/integration/test_rag_rebuild_lifecycle.py；
tests/fixtures/rag_safe_rebuild/**；本 PWF 目录；docs/handoff/QA-RAG-2026-10-24/**。
禁止：config.yaml、config_example.yaml、vector_db/**、test_vector_db/**、output/**、真实 JSON 报告、
UI/启动脚本、document_processor.py、hybrid_retriever.py、providers/keys、其他仓库与全局安装；
不得对原有 vector_db 或真实 collection 调 delete/reset/migrate。

## 设计决策（详见 findings.md）

1. Generation 布局：`<persist_root>/generations/gen-<ts>-<uuid4hex>/` 每代是独立 chroma 持久目录，
   内含 manifest.json；`<persist_root>/active.json` 是唯一 active 指针。
2. 原子切换：指针写入 active.json.tmp → fsync → os.replace（Windows/POSIX 同卷原子）。
   原子性边界：replace 前崩溃=旧指针保留；replace 后=新指针生效。目录 fsync 在 Windows 上不可用，
   以 best-effort 处理并记录。
3. 稳定 chunk ID：`doc-<sha1(relpath)[:10]>-chunk-<j>`，j 为该文档内 chunk 序号；处理顺序按
   relpath 排序，枚举重排不影响 id↔metadata 绑定；废弃 doc_{i}_chunk_{j} 枚举序号 id。
4. 覆盖/删除规则：重建=整代替换。新代只含本次扫描到的文件；被删文件的旧 chunk 随旧代退役，
   不做原位删除。短块（<50 字符）与解析失败文件跳过（沿既有行为）。
5. 失败语义：build_knowledge_base 返回 False = 本次失败、旧库完整可用；True = 新代已验证并发布。
   内部关键阶段异常上抛到顶层统一处理，不吞异常报成功。
6. 孤儿清理：cleanup_orphan_generations 只删 active 指针之外的 generation 目录；
   指针文件存在但不可读时拒绝清理（无法判定 active）。优雅失败保留 staging 供取证，
   清理显式进行。
7. 中断注入：实例级 _stage_hooks（staging_created/chunks_built/embedded/staged_validated/
   before_publish/after_publish/after_cleanup），默认空，不改变行为；测试注入 SystemExit 模拟进程死亡。

## Phases

### Phase 1: PWF 规划与基线确认
- **Status:** complete
- worktree/branch 创建于冻结起点 ad389f8；源仓 main 与 origin/main 一致且干净。

### Phase 2: RED — 重现“失败时旧库被清空”
- **Status:** complete
- 旧实现上 3 个保留性测试失败（embedding/写入/解析失败→旧库清空）；空目录场景两实现一致。
- 证据：testlogs/red-old-code-first-failure.txt、red-old-code-full.txt。

### Phase 3: GREEN — 实现 staging/publish 安全重建
- **Status:** complete
- rag_system.py：generation 布局、active.json 原子指针（tmp+fsync+os.replace）、relpath 派生稳定 ID、
  staging 完整性校验（count/ID 集合/来源集合）、发布后 best-effort 清理、阶段钩子、
  强引用 chroma 客户端登记表（Windows 锁释放）。公开调用兼容保持。

### Phase 4: 集成生命周期测试（真实 chromadb，本卡临时根）
- **Status:** complete
- 7 个生命周期测试全绿（首次构建、旧→新切换、发布前/后中断恢复、孤儿清理不删 active、
  删除文件不串档、枚举重排稳定、失败注入真实存储、sentinel 不变）。

### Phase 5: 验收运行与证据
- **Status:** complete
- 卡内命令 22 passed；既有 tests/ 全套 91 passed；源项目 vector_db 清单+SHA 前后一致。
- 证据：testlogs/acceptance-run.txt、vector-db-unchanged.txt。

### Phase 6: 提交冻结 + 独立审查
- **Status:** complete
- 实现 SHA `5d13da5`；第一轮审查（agent 网络中断，发现以 6 个反例测试保留）F1 major/F2 minor；
  修复 SHA `c762e4d`；第二轮独立复审 PASS-with-findings（review/review-report.md），
  残留仅 2 条信息级观察（O1 合法为空边界 / O2 测试钩子路径），无需返工。

### Phase 7: 交接交付
- **Status:** complete
- docs/handoff/QA-RAG-2026-10-24/handoff.md + handoff.json（最终 SHA、审查结论、测试与清理证据）；
  未交付 vector_db、真实配置或公司报告。

## Decisions Made

| 日期 | 决定 | 原因 |
|---|---|---|
| 2026-10-24 | 独立 generation 目录 + active.json 原子指针，而非 collection rename | chroma 不支持集合原子 rename；os.replace 指针切换在 Windows/POSIX 同卷原子 |
| 2026-10-24 | chunk ID 由 documents_folder 相对路径哈希派生 | 消除枚举顺序依赖（doc_0 反例） |
| 2026-10-24 | 优雅失败保留 staging 目录 | 孤儿可识别可清除，取证优先；清理显式触发 |
| 2026-10-24 | 不迁移 legacy 顶层 chroma 布局 | 任务卡禁止对原有 vector_db migrate/reset/delete |

## Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|
| (none yet) | | |

## Next Step

无 —— 全部 Phase 完成；卡 QA-RAG-SAFE-REBUILD 交付关闭（最终 SHA c762e4d）。
