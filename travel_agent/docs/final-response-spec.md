# Final Response Spec（压缩表达 + 待确认清单 + 结构化结果）

> 目标：让 Web/CLI 在“所有任务执行完成后”输出同一份高可读、可执行、可机读的标准结果，避免碎片化拼接和信息过载。

## 1. 背景与问题

当前输出问题：
- 文本过长：关键信息被淹没，用户难以快速执行。
- 缺少待确认项：模型自动规划后，用户下一步动作不明确。
- 缺少结构化产物：后续无法稳定用于导出、二次处理、自动下单。
- 渲染口径不一致：Web/CLI 可能出现不同展示逻辑。

## 2. 目标与非目标

### 2.1 目标
- 压缩表达：默认返回 3 段以内可读摘要。
- 待确认清单：明确列出需用户补充或确认的信息。
- 结构化结果：返回统一 JSON，用于前端渲染和后续自动化。
- 端侧一致性：CLI 与 Web 复用同一格式化器。

### 2.2 非目标
- 不改意图识别与编排策略本身。
- 不引入新模型或新外部服务。
- 不改变现有 agent 的核心业务能力。

## 3. 统一输出契约

`orchestration_result` 解析后，统一生成 `final_response`：

```json
{
  "summary": "...压缩后的最终答复...",
  "confirmation_checklist": [
    {"id": "C1", "item": "是否锁定南方航空去程CZ3593", "required": true, "status": "pending"}
  ],
  "structured_result": {
    "trip": {
      "title": "广州-南京3日出差行程",
      "origin": "广州市",
      "destination": "南京市",
      "start_date": "2026-03-25",
      "end_date": "2026-03-27",
      "duration_days": 3,
      "budget_total": 2750,
      "budget_limit": 3000,
      "currency": "CNY"
    },
    "daily_plans": [],
    "weather": {},
    "preferences_applied": {},
    "sources": []
  },
  "warnings": ["天气为历史参考，非实时预报"],
  "errors": []
}
```

## 4. 压缩表达策略（Summary）

### 4.1 输出模板（三段式）
- 段 1（结论）：是否完成、行程标题、时长、预算是否达标。
- 段 2（关键安排）：每日 1-2 个关键节点（不展开全量细节）。
- 段 3（风险与下一步）：待确认项数量 + 关键风险提示。

### 4.2 长度约束
- 默认不超过 8 行。
- 单行不超过 60 汉字（超出截断并保留结构化详情）。
- 避免 Markdown 花式格式（删除线、复杂嵌套列表）。

### 4.3 文本清洗
- 去除 Markdown 删除线标记 `~~`。
- 温度区间统一为 `x-y°C`。
- 非关键来源链接不进入 summary（进入 `sources`）。

## 5. 待确认清单策略（Confirmation Checklist）

### 5.1 生成规则
当下列信息缺失或高风险时，生成待确认项：
- 交通：航班/高铁偏好、舱位、时段。
- 住宿：酒店区域、可接受品牌、房型。
- 费用：预算上限、报销规则、是否需要含税发票。
- 会议：具体地址、联系人、开始结束时间。
- 风险：天气非实时、政策数据过期、来源可信度不足。

### 5.2 字段定义
- `id`: 稳定标识（如 C1/C2）。
- `item`: 需确认内容。
- `required`: 是否阻断后续执行。
- `status`: `pending | confirmed | skipped`。
- `reason`: 可选，说明为何需要确认。

## 6. 结构化结果策略（Structured Result）

### 6.1 顶层对象
- `trip`: 行程主信息（起终点、日期、预算）。
- `daily_plans`: 每日安排数组（时间段、地点、动作、交通）。
- `weather`: 实时/历史来源标记 + 未来天气。
- `preferences_applied`: 本次应用到的偏好项。
- `sources`: 可追溯来源链接。

### 6.2 缺省行为
- 无数据字段返回空对象/空数组，不返回 `null`。
- 任何 agent 失败写入 `errors`，不影响已有结果返回。

## 7. Web/CLI 同步策略

### 7.1 单一格式化入口
统一新增格式化模块（建议）：
- `utils/response_formatter.py`

导出函数：
- `build_final_response(result_data) -> dict`
- `build_summary_text(final_response) -> str`

### 7.2 复用规则
- CLI：使用 `build_summary_text` 输出终态文本。
- Web：显示 `summary`，并用卡片展示 `confirmation_checklist` 与 `structured_result`。
- 禁止在 CLI/Web 各自维护分叉的文本拼装逻辑。

## 8. 实施任务拆解

### Phase A：格式化核心
- 新增 `utils/response_formatter.py`。
- 把现有摘要拼装迁移到统一函数。
- 增加清洗器（去 `~~`、区间格式化）。

### Phase B：待确认清单
- 从 `results` 聚合缺失信息。
- 建立规则表（交通/住宿/预算/会议/风险）。
- 输出 `confirmation_checklist`。

### Phase C：结构化结果
- 从 `itinerary_planning`、`information_query`、`preference` 结果提取字段。
- 标准化为 `structured_result`。

### Phase D：前端呈现
- Web 改三块展示：Summary、待确认清单、结构化结果（可折叠 JSON）。
- CLI 保持简洁文本输出，并支持查看结构化详情（可选命令）。

## 9. 验收标准（DoD）

- 功能：
  - 所有任务完成后只生成 1 份最终答复对象。
  - 必须包含 `summary`、`confirmation_checklist`、`structured_result`。
- 一致性：
  - 同一输入下 CLI/Web 的 `summary` 内容一致。
- 可读性：
  - summary 不超过 8 行，关键信息（路线、日期、预算、下一步）齐全。
- 鲁棒性：
  - 部分 agent 失败时仍返回可用结果，并在 `errors/warnings` 中体现。

## 10. 测试用例（最小集）

1. 行程规划完整输入：输出应包含完整 summary + 0~2 条确认项。
2. 缺少返程日期：应生成必填确认项。
3. 天气查询失败：summary 有提示，`warnings/errors` 有记录。
4. 仅偏好更新：summary 简洁反馈，`structured_result.preferences_applied` 完整。
5. 含特殊符号文本：不出现 Markdown 误渲染效果。

## 11. 里程碑建议

- M1（0.5 天）：完成统一 formatter 与 summary 收敛。
- M2（0.5 天）：完成确认清单规则和输出。
- M3（0.5 天）：完成结构化结果提取与 Web 展示。
- M4（0.5 天）：补齐测试与回归，完成文档更新。

---

该 Spec 优先解决“能看懂、能确认、能落地、能复用”四个问题；后续可在此基础上扩展导出日历、自动下单、审批流对接等能力。
