# 工作流模板标准 v1

所有模板必须遵守本标准的统一结构，保证：可读、可复用、可被 n8n / Dify 自动导入。

## 1. 目录结构（每个模板）

```
templates/<template-id>/
├── README.md               # 场景说明 + 快速开始 + 已知限制
├── workflow.json           # 机器可读的 DAG 流程定义（可导入 n8n / Dify）
├── prompts/                # 提示词资产（system / 各步骤）
│   ├── system.md
│   └── ...
├── schema/
│   ├── input.schema.json   # 输入契约（JSON Schema）
│   └── output.schema.json  # 输出契约（JSON Schema）
├── examples/
│   └── sample-input.json   # 示例输入（含脱敏数据）
└── scripts/
    ├── run.py              # 轻量可运行实现（v0）
    └── requirements.txt
```

## 2. 输入契约

- 明确声明**触发源**：文件（PDF/CSV/URL）、关键词、定时任务。
- `input.schema.json` 强制校验，必填字段缺失即拒绝启动。
- 示例输入必须脱敏，且附带一行说明来源与预期输出。

## 3. 处理契约（DAG）

- 所有步骤定义在 `workflow.json` 的 `dag.nodes` 中，字段：`id / type / input / output / depends_on`。
- 步骤必须包含：
  - **解析类**：`doc-parse`（PDF/网页 → 文本）
  - **抽取类**：`llm-extract`（文本 → 结构化 JSON）
  - **分析类**：`llm-analyze`（结构化数据 → 洞察）
  - **渲染类**：`render`（数据 → 交付文档）
- 运筹学应用点（本项目护城河）：
  - **优先级**：`depends_on` 表达 DAG 依赖，无依赖步骤可并行。
  - **约束**：每步定义超时、token 预算、输入大小上限。
  - **容错**：失败重试 N 次 → 降级（本地模型兜底 API）→ 转人工。
  - **成本路由**：简单任务走本地小模型，复杂任务才调 API。

## 4. 输出契约

- `output.schema.json` 强制校验，未通过不得交付。
- 交付物清单：结构化 JSON（`data.json`）+ 人类可读文档（`report.md`）+ 必要附件。
- 人审关卡：高风险字段（财务数字、法律结论）必须经人工确认后才标记可交付。

## 5. 质量门控规则

| 门控 | 触发点 | 规则 |
|------|--------|------|
| Schema 校验 | 每个 LLM 步骤后 | 输出必须是合法 JSON 且符合契约 |
| 数值交叉校验 | 抽取后 | 净利润 ≈ 营收 × 净利率；现金流与利润背离需标记 |
| 幻觉防护 | 提示词 + 校验 | 禁止编造数字；只允许输出文本中出现的值；要求引用页码 |
| 人审关卡 | 交付前 | 高风险字段人工确认，未确认时 `human_review_required=true` |
| 失败降级 | 任意步骤 | 重试 → 降级模型 → 转人工处理 |

## 6. 文档要求

README.md 必含：适用场景、输入说明、输出说明、快速开始、已知限制（LLM 幻觉风险、性能边界）。
