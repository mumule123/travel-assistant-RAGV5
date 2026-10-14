# Web 前端页面 Spec（参考 MODULAR-RAG-MCP-SERVER Dashboard）

> 目标：对齐 `MODULAR-RAG-MCP-SERVER/src/observability/dashboard` 的布局与信息密度，形成 **左侧主流程 + 右侧监控信息** 的分析型界面风格，同时保留对话与记忆展示。

## 1. 信息架构
**顶栏（Header）**
- 标题：Aligo 商旅助手
- 用户输入区：User ID
- 连接状态指示：LLM/服务状态（可选）

**主栏（Main）**
- **对话流**：按时间顺序展示用户与助手消息
- **执行明细**（折叠）：展示本次调用的 agent 列表 + 原始 JSON

**侧栏（Sidebar）**
- 记忆统计（短期消息数/长期行程数/已加载智能体）
- 历史行程列表（最近 10 条）
- 用户偏好（结构化展示）

## 2. 关键页面/组件
- `ChatPanel`：对话消息、输入框、发送按钮、loading 状态
- `MemoryPanel`：记忆统计卡片
- `HistoryPanel`：历史行程表格或列表
- `PreferencePanel`：偏好列表（支持多值显示）
- `ResultDetails`：可折叠 JSON 结果展示

## 3. 数据流与接口
- `POST /api/query`：请求体 `{ user_id, message }`
  - 返回：`{ reply_text, result }`
- `GET /api/status?user_id=`：记忆统计
- `GET /api/history?user_id=`：历史行程
- `GET /api/preferences?user_id=`：用户偏好

## 4. 交互细节
- 发送后立即回显用户气泡，助手气泡进入“处理中”
- 请求完成后替换为 `reply_text`，并保留 `result` 折叠详情
- 侧栏信息在每次对话完成后刷新

## 5. 视觉风格（对标 Dashboard）
- 卡片式布局、圆角、轻阴影
- 表格/列表清晰分区
- 强调可读性（字体层级、间距充足）

## 6. 技术约束
- **不新增依赖**：使用内置 HTTP Server + 单页 HTML
- 前端以原生 HTML/CSS/JS 实现
- 保留 CLI 与 Web 双入口
