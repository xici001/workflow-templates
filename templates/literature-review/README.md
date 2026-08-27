# 文献综述初稿工作流（v0.1）

输入文献摘要列表，自动生成结构化文献综述初稿：研究背景 + 主题聚类分节 + 关键文献 + 研究缺口 + 参考文献。

## 适用场景

- 开题/论文第一章的综述初稿（先用 AI 搭骨架，再人工精修）
- 调研一个陌生领域：5-10 篇摘要 → 10 分钟拿到综述框架
- 组会周报：把本周读的文献整理成结构化笔记

## 输入

见 [schema/input.schema.json](schema/input.schema.json)：综述主题 + 文献列表（标题/摘要/年份/出处）+ 可选风格与分节数。

## 处理流水线（DAG）

```
summarize(逐篇提炼) → cluster(主题聚类) → draft(生成综述初稿)
      → validate(Schema 校验) → review(人审关卡) → render(生成报告)
```

## 输出

- `output/data.json`：结构化综述（overview / sections / key_papers / research_gaps / references）
- `output/report.md`：Markdown 综述初稿（可直接作为论文综述章节的草稿）

## 示例

```bash
python scripts/run.py examples/sample-input.json -o output/
# 或自动化复核（跳过人工确认，调用方负责核验）
python scripts/run.py examples/sample-input.json -o output/ --auto-review
```
