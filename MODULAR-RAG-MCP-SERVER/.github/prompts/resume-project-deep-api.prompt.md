---
name: Resume Project Deep API
description: "Generate deep interview questions from resume project markdown in API(JSON) format."
agent: "Resume Project Deep Interviewer"
argument-hint: "Paste resume markdown or file path + target role + level(Fast/Standard/Deep)"
---

请按以下步骤执行：

1. 读取用户提供的简历 Markdown（文件路径或直接内容）。
2. 仅提取“项目经历”部分，并识别可验证主张与风险点。
3. 生成深挖问题，问题必须绑定原文锚点。
4. 以 JSON 输出结果，键名固定为：
- `session_meta`
- `project_claims`
- `deep_questions`
- `risk_flags`
- `coaching_plan`

补充要求：
- 问题应聚焦：贡献边界、架构取舍、指标口径、工程兜底。
- 若用户要求调用外部 API，先返回 request JSON，再生成可执行 curl。
