# Agent 化增强流程执行规范（EXEC SPEC）

> 版本：v0.2  
> 状态：Draft（可直接进入实现）  
> 适用范围：Ingestion Pipeline Stage 4（Transform）

---

## 目录

- 1. 背景与目标
- 2. 方案总览
- 3. 架构设计
- 4. 分阶段执行计划
- 5. 代码改造清单（按执行顺序）
- 6. 配置与Prompt治理
- 7. 观测与评估
- 8. 风险、回退与边界
- 9. 验收标准（DoD）
- 10. 排期建议
- 11. 阶段任务看板模板

---

## 1. 背景与目标

当前 Ingestion 的增强流程已经具备三类能力：
- Chunk 增强（ChunkRefiner）
- 元数据增强（MetadataEnricher）
- 图片增强（ImageCaptioner）

并且已有三份可用 Prompt：
- config/prompts/chunk_refinement.txt
- config/prompts/metadata_enrichment.txt
- config/prompts/image_captioning.txt

目标是在不破坏现有 Pipeline 稳定性的前提下，引入 主 Agent 编排 + 子 Agent 执行 的可扩展模式，实现：
1. 动态流程控制（按文档特征决定执行顺序与跳过策略）
2. 一致的增强质量门控（输出结构化、可观测、可回退）
3. 可扩展能力位（后续可加 OCR Agent、表格 Agent、术语抽取 Agent）

---

## 2. 方案总览

### 2.1 目标形态

- 主 Agent（Orchestrator）
  - 负责计划、调度、失败隔离、回退策略、阶段汇总
- 子 Agent（Workers）
  - ChunkEnhanceAgent
  - MetadataEnhanceAgent
  - ImageEnhanceAgent

### 2.2 落地原则

1. 接口稳定优先：保留现有 transform(chunks, trace) 入口
2. 增量改造优先：先编排层，再子能力内核 Agent 化
3. 可回退优先：任一子 Agent 失败不阻断主流程
4. 可观测优先：每步都有 trace、耗时、输入输出摘要

---

## 3. 架构设计

### 3.1 模块分层

- 编排层：src/ingestion/transform/enhancement_orchestrator.py
- 能力层：复用现有
  - src/ingestion/transform/chunk_refiner.py
  - src/ingestion/transform/metadata_enricher.py
  - src/ingestion/transform/image_captioner.py
- 配置层：config/settings.yaml（新增 orchestration 段）
- 提示词层：config/prompts/*.txt

### 3.2 执行时序（默认）

1. Chunk 增强
2. 元数据增强
3. 图片增强（仅检测到图片占位符时执行）

### 3.3 可选动态策略

- 文档无图片：自动跳过 ImageEnhanceAgent
- 文本过短：跳过 ChunkEnhanceAgent
- 元数据已完整：降低 MetadataEnhanceAgent 强度

---

## 4. 分阶段执行计划

### 4.0 执行状态机（必须遵循）

每个 Phase 必须按以下状态流转，不可跳步：

1. `todo`：任务已定义，未开始执行
2. `in_progress`：任务执行中
3. `ready_for_review`：实现完成，等待评审
4. `review_failed`：评审不通过，返回整改
5. `review_passed`：评审通过，可进入下一阶段
6. `done`：阶段收尾完成（文档、测试、状态都已更新）

状态流转规则：
1. 仅允许 `todo -> in_progress -> ready_for_review`
2. 评审后只能 `ready_for_review -> review_failed` 或 `ready_for_review -> review_passed`
3. 评审失败后必须 `review_failed -> in_progress` 修复后再次提交评审
4. 只有 `review_passed` 才允许改为 `done`
5. 只有上一个 Phase 为 `done`，下一个 Phase 才能从 `todo` 进入 `in_progress`

Review Gate 通用检查项（每个 Phase 必查）：
1. 功能：是否满足本阶段目标与产出定义
2. 测试：相关 unit/integration 是否通过
3. 观测：trace/日志是否可定位关键步骤
4. 回退：失败场景是否可降级或回滚
5. 文档：本规范中的阶段状态与结果是否已同步

### Phase 0：基线冻结与评测准备

目标：建立改造前基线，避免改造后无法归因。

执行项：
1. 固定一组测试文档与评测问题（含图片与无图片样本）
2. 保存当前设置快照（settings + prompts）
3. 记录基线指标：
   - ingest 总耗时
   - transform 耗时占比
   - query hit_rate / mrr
   - 关键问答样本质量

产出：
- 基线报告（可放 logs 或 docs）

任务拆解与状态：
1. T0-1 固定样本集与评测问题（状态：`todo`）
2. T0-2 保存 settings/prompts 快照（状态：`todo`）
3. T0-3 采集并记录基线指标（状态：`todo`）

Phase 0 Review Gate：
1. 基线报告可复现，包含输入样本和命令
2. 指标口径明确且可对比（至少质量/性能/稳定性三类）
3. 三项任务都达到 `ready_for_review` 后才能触发评审

### Phase 1：引入主 Agent 编排器（不改子模块接口）

目标：先把调度逻辑集中，不改变已有能力实现。

执行项：
1. 新建 EnhancementOrchestrator
2. 支持固定顺序执行 + 条件跳过
3. 汇总每一步结果（成功/失败/耗时/降级）
4. Pipeline Stage 4 改为调用 orchestrator

产出：
- 主流程可用，功能等价于当前实现

任务拆解与状态：
1. T1-1 新增 `enhancement_orchestrator.py` 骨架（状态：`todo`）
2. T1-2 实现固定顺序 + 条件跳过（状态：`todo`）
3. T1-3 Pipeline Stage 4 接入编排器（状态：`todo`）
4. T1-4 补最小回归测试（状态：`todo`）

Phase 1 Review Gate：
1. 默认配置下输出与现有流程功能等价
2. 子步骤失败不会中断主 ingest（满足 fail policy）
3. T1-1 ~ T1-4 全部 `ready_for_review` 后统一评审

### Phase 2：子 Agent 协议统一（标准输入输出）

目标：为三类子 Agent 定义统一 contract，便于扩展与观测。

执行项：
1. 定义 AgentTask / AgentResult 数据结构
2. 三个子能力统一返回：
   - updated_chunks
   - stats
   - warnings
   - fallback_used
3. 将现有 transform 适配到该协议

产出：
- 统一 contract，降低后续维护成本

任务拆解与状态：
1. T2-1 新增 `agent_contracts.py`（状态：`todo`）
2. T2-2 三子模块适配统一返回结构（状态：`todo`）
3. T2-3 补协议层单测（状态：`todo`）

Phase 2 Review Gate：
1. 三子模块输出字段一致（updated_chunks/stats/warnings/fallback_used）
2. 旧调用方无需大范围改动（兼容性通过）
3. 协议单测与关键回归测试通过

### Phase 3：策略化执行（Rule + LLM Planner）

目标：让主 Agent 可根据文档特征动态决策。

执行项：
1. 先上规则版 Planner（不引入额外 LLM）
2. 可选接入 LLM Planner（开关控制）
3. 支持配置化顺序与跳过策略

产出：
- 对不同文档类型有差异化增强路径

任务拆解与状态：
1. T3-1 实现规则版 Planner（状态：`todo`）
2. T3-2 增加配置化顺序与跳过策略（状态：`todo`）
3. T3-3 可选接入 LLM Planner 开关（状态：`todo`）

Phase 3 Review Gate：
1. 规则策略命中行为可解释（有日志或 trace 证据）
2. 同一输入在相同配置下行为确定
3. 关闭 LLM Planner 时不影响主流程稳定性

### Phase 4：质量门控与安全防护

目标：防止增强污染文本，保证幂等性和稳定性。

执行项：
1. 增加输出校验（长度、重复率、非法字段）
2. 幂等保护（避免重复追加 caption/summary）
3. 单步失败自动回退（保留原 chunk）
4. 超时、重试、并发上限配置化

产出：
- 生产可用级别可靠性

任务拆解与状态：
1. T4-1 增强输出校验器（状态：`todo`）
2. T4-2 幂等保护实现（状态：`todo`）
3. T4-3 超时/重试/并发上限配置化（状态：`todo`）
4. T4-4 降级与回退路径测试（状态：`todo`）

Phase 4 Review Gate：
1. 失败场景能自动降级且不污染文本
2. 重复执行结果稳定（幂等）
3. 超时与重试策略在测试中被覆盖

### Phase 5：评估闭环与上线策略

目标：量化收益并可灰度上线。

执行项：
1. 对比基线与新流程指标
2. 引入开关灰度（agent_orchestration.enabled）
3. 达标后默认开启，否则回退

产出：
- 可审计的上线决策依据

任务拆解与状态：
1. T5-1 对比基线与新流程指标（状态：`todo`）
2. T5-2 灰度开关与回滚预案演练（状态：`todo`）
3. T5-3 上线评审记录归档（状态：`todo`）

Phase 5 Review Gate：
1. 关键指标达到门槛（或给出明确不上线结论）
2. 灰度与回滚路径已演练并可执行
3. 评审结论和证据（数据/日志/命令）已归档

---

## 5. 代码改造清单（按执行顺序）

### 5.1 新增文件

1. src/ingestion/transform/enhancement_orchestrator.py
   - 主 Agent 编排器
   - 执行计划生成、步骤调度、错误隔离、回退

2. src/ingestion/transform/agent_contracts.py
   - AgentTask / AgentResult / OrchestrationReport 等协议对象

3. tests/unit/test_enhancement_orchestrator.py
   - 正常路径、跳过路径、失败回退、统计汇总测试

### 5.2 修改文件

1. src/ingestion/pipeline.py
   - Stage 4 改造为 orchestrator 调用
   - trace 记录迁移到编排结果

2. src/ingestion/transform/chunk_refiner.py
   - 适配统一 AgentResult 输出
   - 增加幂等与校验钩子

3. src/ingestion/transform/metadata_enricher.py
   - 适配统一 AgentResult 输出
   - 增加字段白名单/去重策略

4. src/ingestion/transform/image_captioner.py
   - 适配统一 AgentResult 输出
   - 增加重复 caption 防护与失败回退

5. src/core/settings.py
   - 新增 agent_orchestration 配置结构（可选）

6. config/settings.yaml
   - 新增 orchestration 配置段（enabled/order/max_workers/fallback）

### 5.3 可选改造

1. src/observability/dashboard/pages/ingestion_traces.py
   - 展示每个子 Agent 的耗时与回退情况

2. tests/integration/test_ingestion_pipeline.py
   - 增加编排模式下端到端测试

---

## 6. 配置与 Prompt 治理

### 6.1 推荐新增配置

在 settings.yaml 新增（示例语义）：
- agent_orchestration.enabled: true/false
- agent_orchestration.mode: rule | llm
- agent_orchestration.order: [chunk, metadata, image]
- agent_orchestration.fail_policy: continue | abort
- agent_orchestration.max_workers: 1..N
- agent_orchestration.step_timeout_sec: number

### 6.2 Prompt 治理原则

1. Prompt 版本化（文件注释含版本号）
2. 输出格式约束（JSON 或严格段落模板）
3. 不同 Agent 的提示词职责不重叠
4. 每次 Prompt 调整要配套评测记录

---

## 7. 观测与评估

### 7.1 Trace 维度

每个子 Agent 必须记录：
- step_name
- latency_ms
- input_chunk_count
- output_chunk_count
- fallback_used
- warning_count
- cache_hit（适用时）

### 7.2 评估指标

1. 质量类：hit_rate、mrr、faithfulness
2. 性能类：ingest P50/P95、transform 占比
3. 成本类：token 与 Vision 调用次数
4. 稳定性：失败率、回退率

---

## 8. 风险、回退与边界

### 8.1 主要风险

1. 成本上升：多 Agent 增加 LLM 调用
2. 延迟变长：串行步骤过多
3. 输出漂移：子 Agent 风格不一致
4. 复杂度提升：调试链路变长

### 8.2 回退策略

1. 全局开关：一键关闭编排回到原流程
2. 单步开关：独立关闭 image/metadata/chunk 子 Agent
3. 失败降级：使用原始 chunk 或 rule-based 结果

### 8.3 非目标（当前版本不做）

1. 不在本期引入跨文档记忆
2. 不在本期引入多 Agent 自反思长链路
3. 不改动 query 端检索协议

---

## 9. 验收标准（DoD）

必须同时满足：
1. 功能等价：在默认配置下结果不劣于现网基线
2. 稳定性：单步失败不影响整体 ingest 成功率
3. 可观测：每个子 Agent 可在 trace 中定位
4. 可回退：配置开关生效且回退路径测试通过
5. 测试通过：新增 unit/integration 用例全部通过

---

## 10. 排期建议

- Week 1：Phase 0 + Phase 1（主编排器落地）
- Week 2：Phase 2 + Phase 3（协议统一 + 规则 Planner）
- Week 3：Phase 4（质量门控与容错）
- Week 4：Phase 5（评估对比与灰度上线）

并行建议：
1. 一人负责 orchestrator + pipeline 集成
2. 一人负责三子模块 contract 适配
3. 一人负责测试与评测基线

---

## 11. 阶段任务看板模板

建议将每个 Phase 的任务放入统一看板，字段如下：

| Task ID | Phase | 任务描述 | Owner | 状态 | 开始时间 | 完成时间 | Reviewer | Review结论 | 备注 |
|---|---|---|---|---|---|---|---|---|---|
| T1-1 | Phase 1 | 新增 orchestrator 骨架 |  | todo |  |  |  |  |  |

状态更新规范：
1. 开发者仅可更新到 `ready_for_review`
2. Reviewer 负责更新 `review_failed/review_passed`
3. Phase Owner 在收尾时更新 `done`

建议在每次评审后同步两处：
1. 本文档对应 Phase 的任务状态
2. 代码仓库中的变更记录（PR 描述或 changelog）

---

## 附录 A：最小上线路径（MVP）

如果希望最快落地，先做以下最小集：
1. 主编排器（固定顺序）
2. 三子模块统一返回结构
3. 全局开关 + 单步失败 continue
4. 基础 trace 字段

这样可以在较低风险下完成 Agent 化第一步，再逐步引入动态 Planner 与质量门控。
