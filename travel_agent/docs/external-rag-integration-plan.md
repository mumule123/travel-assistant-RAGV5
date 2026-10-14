# 模块化 RAG 对接方案（不执行代码变更版）

## 目标

- 在尽量不改变现有调用链与 UI 的前提下，让“差旅助手”项目的 `RAGKnowledgeAgent` 可选择使用外部“可插拔 RAG（MODULAR-RAG-MCP-SERVER）”进行检索与重排。
- 通过配置开关一键切换：本地 Milvus+BGE 或 外部 HybridSearch+Rerank。

## 总体设计

- 保留现有架构：`IntentionAgent → OrchestrationAgent → rag_knowledge`；CLI 渲染逻辑保持不变。
- 在 `RAGKnowledgeAgent` 内增加“外部 RAG 适配器”：启用时动态加载外部项目组件，执行 Hybrid 检索与可选重排；关闭时继续走本地 Milvus。
- 提供配置项 `EXTERNAL_RAG_CONFIG` 控制启用与指向路径。

## 拟变更清单（文件与行号）

- `居丽叶简历项目6：差旅出行助手/config.py:38`
  - 添加 `EXTERNAL_RAG_CONFIG`：
    - `enabled`: 是否启用外部 RAG（默认 False）
    - `repo_root`: 外部项目根目录（默认 `../MODULAR-RAG-MCP-SERVER`）
    - `settings_path`: 外部项目配置文件（默认 `config/settings.yaml`）
    - `collection`: 检索集合（默认 `default`）
    - `use_rerank`: 是否进行重排（默认 True）

- `.claude/skills/ask-question/script/agent.py`
  - `self.using_external_rag` 标志位：`agent.py:66`
  - `_init_external_rag(self, ext_cfg: Dict)`: 初始化外部 RAG 组件，`agent.py:147`
    - 加载设置：`src/core/settings.load_settings`
    - 向量存储与嵌入：`VectorStoreFactory.create`、`EmbeddingFactory.create`
    - 检索器：`create_dense_retriever`、`BM25Indexer`+`create_sparse_retriever`
    - 混合检索与融合：`create_hybrid_search`
    - 重排器（可选）：`create_core_reranker`
  - `search_knowledge(self, query, top_k)`: 外部模式分支，`agent.py:284`
    - 调用 HybridSearch 搜索，必要时调用重排器
    - 将外部 `RetrievalResult` 统一映射为内部文档结构：`id`、`content`、`metadata`、`score`、`distance=1-score`
  - `get_stats(self)`: 外部模式返回简要统计，`agent.py:508`

## 集成流程（外部模式）

- 初始化阶段
  - 判断 `EXTERNAL_RAG_CONFIG["enabled"]`，启用则进入 `_init_external_rag`。
  - 动态导入外部项目模块（只读，不改外部代码）：`src/core/settings.py`、`src/core/query_engine/*`、`src/libs/*`、`src/ingestion/storage/bm25_indexer.py`。
- 检索阶段
  - 混合检索：Dense（向量）+ Sparse（BM25）并行或顺序执行 → RRF 融合（`HybridSearch.search`）。
  - 可选重排：根据配置调用 `CoreReranker.rerank`，失败时优雅回退到原顺序。
- 生成阶段
  - 沿用当前 LLM 生成逻辑（`agent.py:333-423`），严格基于检索上下文生成答案；无 LLM 时返回检索片段聚合文本。

## 启用步骤（拟定）

- 在差旅助手项目修改配置（执行前评审）：
  - `config.py` 中将 `EXTERNAL_RAG_CONFIG["enabled"]` 设为 `True`
  - 设定 `repo_root` 指向外部项目路径，`settings_path` 指向配置，`collection` 指向集合，`use_rerank` 根据需要开关
- 外部项目准备：
  - 按其 `config/settings.yaml` 配置好 `embedding`、`vector_store`、`retrieval`、`rerank`
  - 运行摄取脚本生成向量库与 BM25 索引（例如：`scripts/ingest.py`）
- 运行差旅助手 `python cli.py`，直接自然语言提问（如“北京的住宿标准是多少”），验证 RAG 触发与展示。

## 兼容与回退

- 兼容：未启用外部模式时保留 Milvus Lite + BGE 本地知识库流程（初始化脚本见 `init_knowledge_base.py`）。
- 回退：外部模式任一组件失败（如重排器）时记录警告并使用可用结果；严重错误时回退到本地 RAG 或提示“未检索到相关信息”。

## 依赖与风险

- 外部项目依赖需安装（`pyproject.toml`），数据需提前摄取；否则外部检索返回空。
- 路径与版本风险：`repo_root` 与 Python 版本、依赖冲突需在虚拟环境中隔离。
- 性能：开启重排会增加时延，可通过 `use_rerank=False` 关闭。

## 测试计划

- 端到端交互：在 CLI 里提问典型知识问题；观察 `rag_knowledge` 输出与文档片段来源。
- 外部检索对比：在外部项目运行 `scripts/query.py --query "RAG pipeline architecture" --verbose` 对比检索与融合结果。
- 回归用例：使用现有 `tests/test_rag_agent.py` 增加外部模式参数化场景（不改生产代码时，可先在文档中记录测试点）。

## 影响评估

- 对现有编排与 UI 无感：仅更换 `RAGKnowledgeAgent` 的后端。
- 配置即插即用：开发与测试环境可切换不同集合与是否重排。

## 变更申请（可逐条审阅）

- 新增配置项：`config.py:38` 引入 `EXTERNAL_RAG_CONFIG` 开关。
- 在 `RAGKnowledgeAgent` 增加外部适配器与分支逻辑：`agent.py:66`、`agent.py:147`、`agent.py:284`、`agent.py:508`。
- 保持现有文件与接口契约不变；不改 `IntentionAgent`、`OrchestrationAgent`、`cli.py` 的交互结构。

## 备注

- 本文档为“先沉淀方案，不执行代码”的设计说明；待你确认后，可按上述清单逐条实施与验证。 
