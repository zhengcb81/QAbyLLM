# QA-RAG-SAFE-REBUILD 第二轮独立审查报告

- 审查人：第二轮独立审查 agent（未参与实现与第一轮审查）
- 日期：2026-10-24
- 仓库：`C:/Users/郑曾波/Projects/QAbyLLM-rag-safe-rebuild`
- 分支：`codex/qa-rag-safe-rebuild-20261024`
- 审查对象（SHA 链）：
  - 冻结基线：`ad389f8`（旧的破坏性实现：`build_knowledge_base` 先 `self.collection.delete()` 清空 active collection 再构建，见 ad389f8:rag_system.py:289，且清空动作用裸 `except: pass` 包裹）
  - 实现提交：`5d13da5`（generation staging + active.json 原子指针安全重建）
  - 修复提交（最终 SHA）：`c762e4d`（第一轮发现 F1/F2 的修复 + 6 个失败注入反例测试）

## 1. 第一轮审查发现记录（历史）

第一轮审查员（独立 agent）审阅 `5d13da5`，追加 6 个 `test_review_` 前缀反例测试到
`tests/unit/test_rag_safe_rebuild.py`，在写出报告前因网络故障中断，发现以反例测试形式保留：

| 编号 | 级别 | 内容 | 反例测试 |
|---|---|---|---|
| F1 | major | 单文件解析失败被 `read_document` 吞掉（返回空串）后 build 仍报 True 并发布缺少该文档的新代（已索引文档静默消失，违反"关键阶段不能吞异常后报成功"） | `test_review_single_file_parse_failure_must_not_report_success` |
| F2 | minor | cleanup 的 `GENERATION_NAME_PATTERN` 过松（`^gen-[0-9A-Za-z._-]+$`，5d13da5:rag_system.py:49），会误删 `gen-not-a-real-generation` 这类外部目录，与"只清理本系统命名目录"的声明不符 | `test_review_cleanup_spares_non_system_named_dirs` |

实现方在 `c762e4d` 中修复：F1 → 新增 `_read_document_strict` 与原始提取器
`_extract_pdf/_extract_docx/_extract_excel`（抛错），公开 `read_document/read_pdf/read_docx/read_excel`
保持吞错返回空串的兼容行为，构建链路改用严格读取器，解析异常 → `RuntimeError` → 顶层捕获返回 False；
两个解析注入点同步迁移到 `_read_document_strict`。F2 → 正则收紧为
`^gen-\d{8}-\d{6}-\d{6}-[0-9a-f]{8}$`（cleanup 与 `_load_active_pointer` 共用）。

## 2. F1 修复验证（结论：完备）

以下引用均为最终 SHA `c762e4d` 工作树中的 `rag_system.py` 行号。

### 2.1 `_read_document_strict` 所有分支确实抛错

`_read_document_strict`（rag_system.py:345-366）函数体内**没有任何 try/except**：

- `.txt`/`.md`（:351-353）：裸 `open(...).read()`——`FileNotFoundError`、`PermissionError`（Windows 文件被占用）、`UnicodeDecodeError` 均上抛；
- `.json`（:354-357）：`json.load` 的 `JSONDecodeError` 上抛；
- `.pdf`（:358-359）→ `_extract_pdf`（:368-374）：裸 `PyPDF2.PdfReader` 循环提取，任何解析异常上抛；
- `.docx`（:360-361）→ `_extract_docx`（:376-381）：裸 `Document(file_path)`，异常上抛；
- `.xlsx/.xls`（:362-363）→ `_extract_excel`（:383-393）：裸 `openpyxl.load_workbook`，异常上抛；
- 其他扩展名（:364-366）：警告后返回空串——这是 docstring（:348）明示的"合法为空"边界（空文件/纯空白/不支持的扩展名），与旧实现语义一致，不属于 F1 的"解析失败被吞"。

三个 `_extract_*` 的提取逻辑与基线 `ad389f8` 的 `read_pdf/read_docx/read_excel` 函数体逐行一致（已对照 `git show ad389f8:rag_system.py`），即"原始提取器 = 旧逻辑去掉外层吞错 try"，没有引入新的解析行为差异。

### 2.2 公开兼容方法行为与旧实现一致（吞错返回空串）

- `read_document`（:337-343）：整体 try/except → log → 返回 `""`。旧实现是单一大 try 包住全部分支 → log → `""`；新实现委托 strict 再整体捕获，外部可观察行为（返回值、日志类别）等价。
- `read_pdf`（:395-401）/ `read_docx`（:403-409）/ `read_excel`（:411-417）：各自 try 包住 `_extract_*` → log → `""`，与基线逐一等价。
- 仓库内调用方核查（grep 全仓）：生产代码中无任何模块调用 `read_document/read_pdf/read_docx/read_excel` 做知识构建（`ocr_table_processor.py` 的 `tabula/camelot.read_pdf` 是无关的表格 OCR 库函数）；根目录 `test_rag.py:149` 使用 `read_document`（真实模型根测试，不在离线范围）——兼容行为保持，不受影响。

### 2.3 build 内包装不会把错误吞成 True

- 构建循环（rag_system.py:574-579）：`except Exception as e: raise RuntimeError(...) from e`——**重抛而非吞掉**，且消息注明"本次构建中止，旧知识库不受影响"；
- 顶层（:685-690）：`except (SystemExit, KeyboardInterrupt): raise`（进程级中断如实上抛，不报成功）；`except Exception` → log → `return False`。因此解析失败 → False，绝不发布；
- `finally`（:691-695）：未发布（`published=False`）时停掉 staging 客户端释放 sqlite 锁，staging 目录保留供取证（显式清理策略，属已接受边界）；
- 发布动作在解析之后（:666），失败路径根本走不到发布——"缺少该文档的新代"不可能被发布。

### 2.4 调用方影响

- `analyze_company_with_rag`（:881-924）：build 返回 False → `raise Exception("知识库构建失败")` → 外层 `except ... raise`（:922-924）。与基线契约一致（基线 build 对空目录也返回 False 并同样抛出），只是现在解析失败也会走该路径——**更严格、更安全**，无兼容性回归。
- `qa_system.py:242/306`（`analyze_company_with_rag`）、`porter_analysis.py:45`（`build_knowledge_base` 返回 bool 分支）、`test_rag_fix.py:27`：契约均为"bool / 异常"，无需改动，行为正确。

### 2.5 测试证据

- `test_review_single_file_parse_failure_must_not_report_success`（tests/unit/test_rag_safe_rebuild.py:671-699）：对 `doc_beta.txt` 注入 `OSError`，断言 build False、指针字节不变、旧库仍可检索——F1 的直接复现，现在通过。
- `test_parse_failure_preserves_old_library`（:280-298）：注入点已随 seam 迁移到 `_read_document_strict`（:294），并改为真实抛错（旧版注入是 `read_document = lambda path: ""` 的"合法为空"路径，测不到严格分支）——迁移正确。

## 3. F2 修复验证（结论：完备）

### 3.1 正则与本系统实际命名一致

- 命名生成（rag_system.py:283-287）：`gen-` + `strftime("%Y%m%d-%H%M%S-%f")` + `-` + `uuid4().hex[:8]`。
  - `%Y%m%d` 恒 8 位数字；`%H%M%S` 恒 6 位；`%f`（微秒）在 CPython 恒补零到 6 位；`uuid4().hex` 恒小写 hex 取前 8 位——与本系统命名结构逐段对应。
- 正则（rag_system.py:50）：`^gen-\d{8}-\d{6}-\d{6}-[0-9a-f]{8}$`。
- 实测（本审查独立运行，20,000 次模拟 `_new_generation_dir` 命名）：**20,000/20,000 全部匹配**。
- 边界用例实测：`gen-20261024-225417-828677-e98306ba` 匹配；`gen-not-a-real-generation`、`not_a_gen_at_all`、大写 hex、微秒少一位、`active.json`、`generations` 均不匹配——方向正确（宁可不删，绝不误删）。

### 3.2 指针校验不会误判合法 generation

`_load_active_pointer`（rag_system.py:207-240）用同一正则校验指针内 `generation` 名（:222）。
指针 payload（:656-664）的 `generation` 与 `chunk_count` 直接取自同一 build 刚写好的 manifest（:634-653），且
manifest 先于指针落盘（:653 → :666），指针校验又回读 manifest 比对 `generation`/`chunk_count`（:230-236）——
本系统写出的指针必然通过自身校验，不存在合法代被误判 invalid 的路径。唯一理论上被拒的是手工改名的目录
（如大写 hex），拒绝/不删均为保守安全方向。

### 3.3 清理侧

`cleanup_orphan_generations`（:496-527）：非 active（:514）、匹配严格正则（:516，注释明示"只清理本系统命名的
generation 目录"）才进入删除；指针存在但无效时整体拒绝清理（:506-508）。`test_review_cleanup_spares_non_system_named_dirs`
（tests/unit/test_rag_safe_rebuild.py:702-727）断言 `gen-not-a-real-generation` 与 `not_a_gen_at_all` 均存活、
active 存活——F2 复现测试现在通过。同时 `gen-19990101-000000-000000-deadbeef`（严格命名的真孤儿）仍被清除
（:526-530），收紧没有过度。

## 4. 整体设计挑战（逐维度）

### 4.1 staging → 校验 → 发布 → 清理顺序：正确

build（rag_system.py:529-695）顺序为：新开 staging 目录（:560，`mkdir(exist_ok=False)` 防撞名）→
写 staging collection（:620-627，4096/批）→ `_validate_staging` 完整性校验（:630；count + chunk ID 集合 +
doc_relpath 来源集合三方比对，:444-464）→ 写 manifest 并 fsync（:653，:466-471）→ tmp+fsync+`os.replace`
原子切换指针（:666，:473-494）→ 重绑到新代（:671-672）→ 尽力清理旧代（:673-678，cleanup 自身异常被捕获，
不影响已发布结果）。关键不变量成立：**指针永远只指向"已通过校验且 manifest 已落盘"的 generation**——
manifest 先于指针写入，校验先于 manifest 写入。staging 构建全程不触碰当前 active collection（对比基线
:289 的 `self.collection.delete()` 先清空——根因确实消除）。

### 4.2 异常注入路径：全部收敛到"False + 旧库完整"或"如实崩溃"

逐注入点核对（均有测试覆盖）：

| 注入点 | 结果 | 证据测试 |
|---|---|---|
| scan_documents 抛错 | False，指针不变 | test_review_scan_documents_crash… |
| staging 目录创建失败 | False，无目录副作用 | test_review_staging_dir_creation_failure… |
| 单文件解析失败（F1） | False，指针不变 | test_review_single_file_parse_failure… |
| embedding 失败 | False，指针不变，重启后旧库可查（真实存储） | 单元 :227 + 集成 :274 |
| 向量写入失败 | False，指针不变 | 单元 :251 |
| staging 校验不一致 | False，不发布 | 单元 :490 |
| 指针 tmp 写入失败（含 tmp 被目录占位、崩溃残留 tmp） | False，指针字节不变；残留 tmp 不阻塞下次发布 | test_review_pointer_tmp_write_failure… |
| 指针 os.replace 失败 | False，指针字节不破坏 | 单元 :471 |
| 发布前 SystemExit | 上抛，指针不变，重启绑旧代，staging 成为可清孤儿 | 单元 :406 + 集成 :174 |
| 发布后 SystemExit | 上抛，指针已切换，重启绑新代，旧代待清理 | 单元 :437 + 集成 :208 |
| active 代目录被外部误删 | setup 不崩溃，检索降级为空，一次重建恢复 | test_review_active_gen_dir_deleted… |
| 空文档目录 / 无有效块 | False，不发布 | 单元 :301 |

进程级中断（SystemExit/KeyboardInterrupt）显式 `raise`（:685-687），既不吞也不报成功，符合任务要求。

### 4.3 崩溃恢复边界：闭环

- 发布前崩溃：staging 留在 generations/ 下，匹配命名 → 下次 `cleanup_orphan_generations` 可清（单元 :427-434）；
- 发布瞬间崩溃：`os.replace` 同卷原子（:486），指针只会是旧或新之一；残留 `active.json.tmp` 不会被读取，
  下次发布以 `"w"` 截断重写，自愈（test_review_pointer_tmp_write_failure 注入 1）；
- 发布后、清理前崩溃：新代已生效，旧代成为孤儿，下次清理移除（集成 :222-234）；
- 清理中崩溃：cleanup 逐目录独立进行，永不触碰 active（:514 跳过 + :506 指针无效即拒绝）；
- 指针文件损坏（JSON 坏 / 指向缺失代 / manifest 不一致）：`_load_active_pointer` 判 invalid → setup 降级为
  不绑定（检索返回空而非崩溃）→ 一次成功重建即恢复（test_review_active_gen_dir_deleted… + 单元 :511）。

Windows 无目录 fsync、断电持久化不在保证范围——已接受边界（:477-479 docstring 亦有如实声明）。

### 4.4 输入重排：ID 与绑定稳定

- 文档列表按归一化相对路径排序后才处理（:550-551），`input_fingerprint` 按同一顺序累计（:584），与 `os.walk` 枚举顺序解耦；
- chunk ID = `doc-{sha1(relpath)[:10]}-chunk-{accepted}`（:585, :592），每代新建 collection，无跨代 ID 复用问题；
- 单元（:354-374）与集成（:254-271）均有"枚举逆序后 ID↔metadata↔内容 快照逐项相等"断言；另有废弃
  `doc_{i}_chunk_{j}` 枚举序号 ID 的反例断言（:32-33, :346-351）。
- 被删文件的旧 chunk 不进入新代（整代替换，:560 每代全新），单元 :377 与集成 :237 覆盖。

### 4.5 范围隔离：通过

`git diff --stat ad389f8..c762e4d` 共 15 个文件：`rag_system.py`、`tests/unit/test_rag_safe_rebuild.py`、
`tests/integration/test_rag_rebuild_lifecycle.py`、`tests/fixtures/rag_safe_rebuild/**`（5 个 fixture 文档 + README）、
`docs/plans/qa-rag-safe-rebuild-2026-10-24/**`（task_plan/findings/progress + 4 份 testlogs）。**不含任何其他
生产模块**，与声明范围完全一致。qa_system.py / porter_analysis.py / quick_test.py 等调用方零改动且契约不变。

### 4.6 次要观察（信息级，不阻塞，无需本卡处理）

- **O1（informational）**：若用户在 config `supported_formats` 中加入 strict reader 不支持的扩展名（如 `csv`），
  该类文件会被 scan 收录、在 `_read_document_strict` 走"不支持的扩展名 → 空串"分支（:364-366）并被 build 静默
  跳过（:580-581）。这是 docstring（:348）明示的"合法为空"边界且与 legacy 行为一致；默认配置的
  txt/md/json/pdf/docx/xlsx 全部被 strict reader 覆盖，触发需要非默认配置。属记录性边界，非缺陷。
- **O2（informational）**：`published = True`（:667）之后的残余语句中，若 `after_publish`/`after_cleanup` 阶段钩子
  抛出普通 Exception（仅测试注入可达；生产路径此处只剩空钩子调用、属性赋值、已 try/except 包裹的 cleanup 与
  日志），会落入顶层 `except Exception` 返回 False——而指针实际已发布、进程内绑定仍指向旧代。状态在重启后
  收敛（重启按指针绑新代），生产不可达，故不阻塞；若日后加固，可把发布后的钩子视为"已成功"或将
  after_publish 语义并入崩溃路径处理。

## 5. 测试运行结果（本审查自行运行，Windows git bash）

命令 1（指定范围）：

```
$ python -B -m pytest -q tests/unit/test_rag_safe_rebuild.py tests/integration/test_rag_rebuild_lifecycle.py -p no:cacheprovider
28 passed, 1 warning in 95.74s (0:01:35)
```

（28 = 单元 21〔15 实现 + 6 反例〕+ 集成 7；唯一 warning 为 PyPDF2 弃用提示，既有、与本卡无关。）

命令 2（全套）：

```
$ python -B -m pytest -q tests/ -p no:cacheprovider
97 passed, 1 warning in 59.84s
```

收集计数复核：`28 tests collected`（指定范围）。工作树除本报告与协调方会话日志（progress.md，非本审查
修改）外无其他变更；未修改任何代码/测试，未 commit。

## 6. 最终结论

**PASS-with-findings**（以最终 SHA `c762e4d` 为准）。

- F1（major）修复完备：strict 读取器全分支抛错、公开方法兼容行为逐行等价、build 包装重抛不吞、顶层
  False 不发布、调用方契约不变（§2，rag_system.py:345-366, 574-579, 685-695）；
- F2（minor）修复完备：正则与生成器 20,000/20,000 自洽，指针校验不可能误拒本系统代，清理只删严格命名的
  非 active 目录（§3，rag_system.py:50, 222, 516）；
- 整体设计六维度挑战全部通过（§4）；范围隔离干净；28 项定向测试与 97 项全套测试全绿（§5）；
- 仅存两条信息级观察（O1 配置依赖的"合法为空"边界、O2 仅测试钩子可达的发布后返回值语义），均为已声明
  边界或生产不可达，不阻塞验收，无需本卡返工。
