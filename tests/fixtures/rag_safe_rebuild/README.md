# rag_safe_rebuild 测试夹具

本目录存放 QA-RAG-SAFE-REBUILD 任务卡的合成测试文档（TXT/MD），全部为虚构内容，
与任何真实公司、真实报告无关。测试将其复制到 pytest tmp_path 的临时 documents 文件夹，
构建只在临时根内进行；不涉及模型、API 或网络。

- `doc_alpha.md` — 主文档 A（多 chunk，中文合成内容）
- `doc_beta.txt` — 主文档 B（多 chunk，中文合成内容）
- `sub_doc_gamma.md` — 子目录文档 C（验证相对路径派生的稳定 chunk ID）
- `tiny_doc_delta.md` — 小于 50 字符有效块的文档（验证跳过规则）
