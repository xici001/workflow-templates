# 小红书爆款文案工作流（v0.1）

输入主题/卖点，自动生成小红书爆款文案：3 个备选标题 + 正文 + 话题标签 + 发布建议。

## 适用场景

- 个人博主日更：一个主题 2 分钟产出初稿，再人工微调
- 产品种草/技术科普：把"数字孪生、MCP、AI 工具"讲成小红书能懂的话
- 内容矩阵批量生产：改输入即可换主题，保持风格统一

## 输入

见 [schema/input.schema.json](schema/input.schema.json)：主题（必填）+ 卖点/受众/风格/字数上限（可选）。

## 处理流水线（DAG）

```
extract(卖点提炼) → draft(文案初稿) → enhance(爆款要素润色)
      → validate(Schema 校验) → review(人审关卡) → render(生成文案稿)
```

## 输出

- `output/data.json`：结构化文案（titles / body / tags / publish_tips）
- `output/report.md`：Markdown 文案稿（标题候选 + 正文 + 标签 + 发布建议）

## 示例

```bash
python scripts/run.py examples/sample-input.json -o output/
python scripts/run.py examples/sample-input.json -o output/ --auto-review   # 自动化复核
```
