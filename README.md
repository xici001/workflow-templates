# workflow-templates

> 把重复性脑力劳动，打包成"输入-处理-输出"的自动化工作流。
> 做数字管道的建筑师。

开源 AI 自动化工作流模板集合。每个模板都是一条可复用的"数字管道"：
从触发源（输入）→ 处理流水线（编排 / 模型 / 质量门控）→ 交付物（输出）。

## 演示 / Demo

完整故事见博客《四天四个开源项目》（含 3D 可视化截图与踩坑实录）：<https://github.com/xici001/factory-twin-viz/blob/main/docs/screenshot.png>（看 3D 工厂效果）；也可以直接看本仓库跑出来的[首份财报分析报告](templates/financial-report-analysis/output/report.md)。

## 为什么做这个项目

AI 不缺模型，缺的是"把模型用起来的管道"。
这个仓库把高频、重复、有明确交付物的脑力劳动（财报分析、文献综述、文案生成……）
沉淀为契约化模板：**一个模板，无限复用；一次构建，多方受益。**

## 模板列表

| 模板 | 场景 | 输入 | 输出 | 状态 |
|------|------|------|------|------|
| [财报分析](templates/financial-report-analysis/README.md) | 个股 / 公司财报速读 | PDF / 公告 | 结构化指标 + Markdown 报告 | ✅ v0.1 |
| [文献综述初稿](templates/literature-review/README.md) | 学术写作 | 文献摘要列表 | 综述初稿（分节/缺口/参考文献） | ✅ v0.1 |
| [小红书爆款文案](templates/xiaohongshu-copy/README.md) | 内容创作 | 选题 + 卖点 | 3 标题 + 正文 + 标签 + 发布建议 | ✅ v0.1 |

每个模板都可独立运行：`cd templates/<模板名> && python scripts/run.py examples/sample-input.json -o output/`。

## 核心设计：输入-处理-输出契约

每个模板必须满足 [docs/workflow-standard.md](docs/workflow-standard.md) 定义的标准：

1. **输入契约**：明确的触发源与输入 Schema（JSON Schema 校验）
2. **处理契约**：DAG 编排（解析 → 抽取 → 分析 → 校验 → 人审 → 报告），含质量门控与失败降级
3. **输出契约**：结构化交付物，Schema 校验 + 人审关卡

## 快速开始（任一模板）

```bash
cd templates/literature-review        # 或 financial-report-analysis / xiaohongshu-copy
pip install -r requirements.txt
# 默认走本地模型（Ollama），也可换成任意 OpenAI 兼容 API（模板根目录 .env 配置）
export LLM_BASE_URL=http://localhost:11434/v1
export LLM_MODEL=qwen2.5:7b
python scripts/run.py examples/sample-input.json -o output/
# 自动化复核（跳过人工确认，调用方负责核验）
python scripts/run.py examples/sample-input.json -o output/ --auto-review
```

## 技术栈

- **编排**：Python（轻量 v0，可直接跑）/ n8n（v0.2 提供可导入的 JSON）
- **应用层**：Dify（Agent / 知识库，v0.2 接入）
- **模型**：本地小模型（Ollama + Qwen 等）或任意 OpenAI 兼容 API
- **契约**：JSON Schema 校验 + 人审关卡 + 失败重试 / 降级

## 路线图

- v0.1：3 个种子模板 + 契约标准 v1（财报分析先行）
- v0.2：n8n / Dify 可导入版本 + 每模板演示视频
- v0.3：模板生成器 + 社区贡献指南

## 许可

MIT License
