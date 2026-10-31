## ROOT 主线发布记录（2026-10-31）

已验收作者提交5e5f22b2d7d652738e54bbfaced1982117616c7a现已快进合入本仓main；ROOT独立稀疏工区重新验证：28 focused+real-temporary-store pytest PASS/78.27s; only existingPyPDF2deprecation。原件/生产配置/作者树未动；MeetingConverter原.coverage保持。正常提交本发布记录后推远端，最终SHA与远端匹配由company-wiki总控PWF记录；本段不虚构CI已绿。

# Progress — qa-rag-safe-rebuild-2026-10-24

## 2026-10-24 会话 1（实现与验收）

| 时间 | 事件 |
|---|---|
| 22:15 | worktree `QAbyLLM-rag-safe-rebuild` 建立于冻结起点 ad389f8，branch codex/qa-rag-safe-rebuild-20261024；源仓 main 与 origin/main 一致且干净 |
| 22:20 | PWF 规划目录建立；研读旧 rag_system.py 确认根因（先 delete 后构建；doc_{i} 枚举 ID） |
| 22:30 | 环境验证：python 3.13.9 / chromadb 1.5.9；rag_system 离线导入可行（约 146s，torch 导入慢）；chroma `client._system.stop()` 可释放 Windows sqlite 锁；同路径二次 PersistentClient 不共享客户端对象但共享 System（停机会毒化同路径重开） |
| 22:40 | RED：旧实现上 `test_embedding_failure_preserves_old_library` 失败，日志显示“清空现有知识库”先于“知识识库构建失败: 注入的 embedding 失败” |
| 22:45 | 修正 fake 语义：chroma `collection.delete()` 无参调用=清空集合条目（对象仍可用），非删除集合 |
| 22:47 | RED 完整证据（3 failed / 1 passed）：embedding/写入/解析失败均清空旧库；空目录场景旧代码本就先返回（两实现一致绿） |
| 22:50 | 新 rag_system.py 实现完成：generations 布局、active.json 原子指针、稳定 ID、staging 校验、发布后清理、阶段钩子、强引用客户端登记表 |
| 22:55 | 单元测试修 fake 持久化（按路径共享集合状态模拟重启）→ 15/15 绿 |
| 23:00 | 集成测试发现 chroma 锁问题：崩溃后 staging 客户端对象被 GC 但后台线程仍持锁 → 登记表改强引用 + build finally 停机未发布 staging |
| 23:02 | 发现停机毒化：发布后中断场景 finally 停掉了已切换为 active 的 staging → `published` 标记移到指针切换之后；修复后 22/22 绿 |
| 23:05 | 验收：卡内命令 22 passed；既有 tests/ 全套 91 passed；源项目 vector_db 前后清单+SHA 不变（53efc2bd…，6 文件） |

### 关键决策记录

1. fake collection 的 delete() 按真实 chroma 语义实现（清空条目），否则 RED 证据失真。
2. 失败 embedder 会同时打断查询路径——测试在断言“旧库可查询”前先恢复可用 embedder，避免混淆证据。
3. `_live_chroma_clients` 必须强引用：chroma System 的后台线程使 GC 后锁不释放；停机后从表移除。
4. `stop()` 会毒化同路径重开（SharedSystemClient 缓存 System）→ 只停孤儿路径的客户端，永不停 active 路径；发布后清理只针对非 active 目录。
5. `published=True` 紧跟 `_publish_pointer` 成功之后：指针已切换即事实发布，其后的中断不再回滚停机 active 客户端。
6. 发布后的旧代清理是 best-effort：失败只产生孤儿（下次清理回收），不得把已成功发布改报为 False。

### 测试结果

- RED（旧实现 ad389f8）：`python -B -m pytest -q tests/unit/test_rag_safe_rebuild.py -k "preserves_old_library or empty_folder"`
  → 3 failed（embedding/写入/解析失败清空旧库）, 1 passed（空目录）。见 testlogs/red-old-code-full.txt。
- 验收命令：`python -B -m pytest -q tests/unit/test_rag_safe_rebuild.py tests/integration/test_rag_rebuild_lifecycle.py`
  → 22 passed。见 testlogs/acceptance-run.txt。
- 既有测试：`python -B -m pytest -q tests/` → 91 passed（含新增 22）。
- 仓库根目录 test_rag.py / test_rag_fix.py 为需要真实模型/API 的运行时脚本，不在离线验收范围（未修改、未运行）。

### 清理证据

- 源项目 C:/Users/郑曾波/Projects/QAbyLLM/vector_db：测试前后 find 清单（6 文件）与聚合 SHA-256（53efc2bdfac5abba237056e20e72ab290eb0ad638a00b982b1b19d96271ed61d）完全一致；见 testlogs/vector-db-unchanged.txt。
- 所有构建/中断/清理测试仅使用 pytest tmp_path（本卡临时根），真实 chroma 目录建在临时根内，会话结束由 pytest 管理。

## 2026-10-24 会话 2（独立审查与修复）

| 时间 | 事件 |
|---|---|
| 23:20 | 提交实现并冻结 SHA `5d13da5`（15 文件，+1695/-136） |
| 23:25 | 第一轮独立审查 agent 启动；审阅 diff、自跑测试、追加 6 个失败注入反例到单元测试文件 |
| 23:47 | 第一轮 agent 因网络故障中断（报告未写出）；发现以反例测试保留：F1（major，单文件解析失败被吞后报 True 发布缺文档新代）、F2（minor，清理正则过松误删外部 gen-* 目录）+ 4 个预期通过的回归防线 |
| 23:55 | 修复 F1：新增 _read_document_strict 与原始提取器 _extract_pdf/_extract_docx/_extract_excel（抛错）；公开 read_document/read_* 保持吞错返回空串的兼容行为；构建链路改用严格读取器；两个解析注入测试迁移到新 seam |
| 23:58 | 修复 F2：GENERATION_NAME_PATTERN 收紧为 ^gen-\d{8}-\d{6}-\d{6}-[0-9a-f]{8}$（cleanup 与 _load_active_pointer 共用） |
| 00:02 | 全套 28 passed（22 实现 + 6 反例）；提交修复 SHA `c762e4d` |
| 00:05 | 第二轮独立复审 agent 启动：验证修复完备性、整体挑战、自跑测试、写正式 review-report.md |

| 00:05 | 第二轮独立复审 agent 启动：验证修复完备性、整体挑战、自跑测试、写正式 review-report.md |
| 00:25 | 第二轮复审完成：F1/F2 修复验证完备（严格读取器无吞错路径、正则 20000/20000 匹配）；定向 28 passed、全套 97 passed；结论 PASS-with-findings（残留 O1/O2 均信息级） |
| 00:30 | handoff.md/handoff.json 回填最终 SHA c762e4d 与审查结论；PWF Phase 6/7 关闭；最终提交 |

## Next

无 —— 交付关闭。
