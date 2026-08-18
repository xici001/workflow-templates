# 财报分析自动化工作流（v0.1）

把一份财报 PDF（年报 / 季报）自动转化为：结构化财务指标 JSON + 分析报告 Markdown。

## 适用场景

- 个股速读：快速了解一家公司的财务基本面
- 投研初筛：批量对比多家公司（改输入即可复用）
- 个人学习：拆解财报结构的辅助工具

## 输入

见 [schema/input.schema.json](schema/input.schema.json)：公司名、财报 PDF 路径、报告类型（年报/季报）、可选行业与对比期数。

## 处理流水线（DAG）

```
parse(文档解析) → extract(LLM 指标抽取) → analyze(LLM 分析)
      → validate(Schema 校验) → review(人审关卡) → render(生成报告)
```

## 输出

- `output/data.json`：结构化指标（营收、净利润、毛利率、ROE、负债率、经营现金流）+ 摘要 + 趋势 + 风险信号
- `output/report.md`：人类可读的分析报告

## 快速开始

支持两种模型配置方式（二选一，推荐 .env）：

**方式 A：.env 文件（推荐）**

复制 `.env.example` 为 `.env`，填入你的模型配置（本地 Ollama / OpenRouter / 任意 OpenAI 兼容 API 均可）：

```bash
pip install -r scripts/requirements.txt
cp .env.example .env   # 编辑 .env 填入 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL
python scripts/run.py examples/sample-input.json -o output/
```

**方式 B：环境变量**

```bash
pip install -r scripts/requirements.txt
export LLM_BASE_URL=http://localhost:11434/v1   # 默认 Ollama 本地模型
export LLM_MODEL=qwen2.5:7b
python scripts/run.py examples/sample-input.json -o output/
```

OpenRouter 示例（免费模型）：

```bash
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free
LLM_API_KEY=sk-or-v1-你的key
```

无需真实财报时，可用 `examples/sample-report.pdf`（虚构公司"星海智能"）直接跑通全流程验证；把真实财报 PDF 放入 `examples/` 并修改 `sample-input.json` 的 `report_path` 后重跑即可。

## 质量门控

1. LLM 输出必须为合法 JSON，符合 `output.schema.json`
2. 指标抽取后做数值交叉校验（净利润与营收量级一致性）
3. 交付前必经**人工复核关卡**，确认数字与原文一致
4. 提示词强制：禁止编造数字、只抽取文本中出现的值

## 已知限制

- 依赖 PDF 文本层质量（扫描件需先 OCR，v0.1 不支持）
- 长财报会截断到前 20000 字符（可自行调整）
- LLM 可能漏抽字段，缺失值填 `null` 并在摘要中说明
- **本工具仅做客观分析，不构成投资建议**
