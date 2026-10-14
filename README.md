# 差旅出行助手与模块化 RAG MCP 服务项目 (Travel Agent & RAG MCP Server)

本项目包含两个核心子项目，分别专注于**多智能体协作应用（Agent）**与**底层检索增强生成（RAG）能力封装**。两者结合展示了现代 AI 应用开发中的先进架构：基于大模型的多智能体调度系统与标准化的外部工具/知识接入协议（MCP）。

## 📂 仓库结构

- [**travel_agent (Aligo 智能旅行助手)**](./travel_agent/)
  基于 AgentScope 框架的多智能体旅行规划系统。采用了 Plan-and-Execute 架构，通过大模型进行智能意图识别，调度多类子智能体（如偏好管理、知识查询、信息搜索、行程规划）并行执行任务，同时包含完整的短期/长期记忆管理架构。

- [**MODULAR-RAG-MCP-SERVER (模块化 RAG MCP Server)**](./MODULAR-RAG-MCP-SERVER/)
  一个可插拔、可观测的模块化 RAG 服务框架。它将复杂的检索（混合检索 + 重排）、多模态视觉处理、RAG 评估与 LLM 响应封装起来，通过当下热门的 **MCP (Model Context Protocol)** 协议对外暴露工具接口，使得各路 Copilot / Agent 能够无缝接入内部知识库。

## ✨ 核心亮点

### 🤖 Aligo 智能旅行助手 (Agent 侧)
- **智能意图识别**：无需关键词匹配的自然语言意图分发，自动生成执行计划和调度优先级。
- **两层记忆架构**：Redis 短期滑动窗口会话缓存 + PostgreSQL 长期持久化总结。
- **并发与性能优化**：对同优先级子智能体采用异步并发调度，大幅降低系统响应时间。
- **插件化架构**：通过 Lazy 机制动态发现和加载 Skill，实现模块解耦。

### 📚 Modular RAG MCP Server (RAG & 工具侧)
- **🔌 接口标准化**：通过 MCP 协议暴露数据检索工具，实现与主流大模型客户端无缝集成。
- **🔍 混合检索重排**：结合 Dense (向量) 与 Sparse (BM25) 的双路召回，通过 RRF 融合并进行精确重排。
- **🖼️ 多模态支持**：利用 Vision LLM 进行图像语义抽取并融合，支持图文多模态检索。
- **📊 评估与观测**：内置 Ragas 等评估体系，配套可视化 Dashboard 进行大模型链路全流程观测。

## 🚀 快速开始

两个项目均可作为独立服务运行。请分别进入对应子目录查看详细的部署说明：

1. **配置并运行 RAG MCP Server**
   - 见 [`MODULAR-RAG-MCP-SERVER/README.md`](./MODULAR-RAG-MCP-SERVER/README.md)
2. **配置并启动 Travel Agent**
   - 见 [`travel_agent/README.md`](./travel_agent/README.md)

## 🤝 贡献与说明
本项目除了作为可运行的工程实现外，也非常适合用于 **大模型相关技术学习与面试求职参考**，项目中蕴含了系统架构设计、自动化测试、技能驱动全流程开发等丰富的工程化思路。
