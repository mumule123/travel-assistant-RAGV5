# API Contract - Resume Project Deep Interview

用于“项目深挖”模式的统一 JSON 输入/输出协议。

## Request JSON

```json
{
  "target_role": "LLM Application Engineer",
  "interview_level": "Standard",
  "resume_markdown": "# ...完整简历Markdown...",
  "focus_project_names": ["TravelOps Agent Hub", "基于 GRPO 的数学推理增强实验"],
  "question_count": 8,
  "language": "zh-CN"
}
```

字段说明：
- `target_role`: 目标岗位
- `interview_level`: `Fast | Standard | Deep`
- `resume_markdown`: 简历 md 原文
- `focus_project_names`: 可选，指定优先深挖的项目
- `question_count`: 可选，默认按强度自动推导
- `language`: 输出语言

## Response JSON

```json
{
  "session_meta": {
    "target_role": "LLM Application Engineer",
    "interview_level": "Standard",
    "total_questions": 8
  },
  "project_claims": [
    {
      "project": "TravelOps Agent Hub",
      "claim": "意图识别准确率从65%提升至90%+",
      "anchor_quote": "...简历原文片段...",
      "risk_level": "medium"
    }
  ],
  "deep_questions": [
    {
      "id": "Q1",
      "module": "metrics",
      "question": "你写准确率从65%到90%+，评测口径和样本规模分别是什么？",
      "anchor_quote": "意图识别准确率从65%提升至90%+",
      "intent": "验证指标可复现性",
      "expected_depth": "需要回答数据集、标签口径、评估脚本"
    }
  ],
  "risk_flags": [
    {
      "type": "metric_reproducibility",
      "severity": "high",
      "evidence": "只写了提升幅度，未说明口径"
    }
  ],
  "coaching_plan": {
    "quick_fixes": ["补齐指标定义与评测口径"],
    "one_week_plan": ["整理每个项目的贡献边界与关键代码点"],
    "long_term_plan": ["构建固定面试题库并做2轮模拟复盘"]
  }
}
```

## Optional HTTP Calling Example

```bash
curl -X POST "${API_ENDPOINT}" \
  -H "Content-Type: application/json" \
  -d @request.json
```
