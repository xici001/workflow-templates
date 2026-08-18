#!/usr/bin/env python3
"""财报分析工作流 v0.1 — 轻量 Python 实现（数字管道的第一个样板）

用法：
    export LLM_BASE_URL=http://localhost:11434/v1   # 默认 Ollama 本地模型
    export LLM_MODEL=qwen2.5:7b
    python scripts/run.py examples/sample-input.json -o output/

流水线（DAG）：parse -> extract -> analyze -> validate -> review -> render
"""
import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path


def parse_pdf(path: str) -> str:
    """阶段 parse：PDF -> 文本"""
    try:
        from pypdf import PdfReader
    except ImportError:
        sys.exit("缺少依赖：pip install -r scripts/requirements.txt")
    reader = PdfReader(path)
    parts = []
    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        parts.append(f"--- 第 {i} 页 ---\n{text}")
    return "\n".join(parts)


def call_llm(system: str, user: str, base_url: str, api_key: str, model: str) -> str:
    """调用任意 OpenAI 兼容接口（Ollama / Dify / DeepSeek / 本地 vLLM...）"""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def extract_json(text: str):
    """质量门控：从 LLM 输出中稳健提取 JSON（容忍代码块包裹）"""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("LLM 输出中未找到 JSON 对象，请检查提示词或模型")
    return json.loads(text[start : end + 1])


def validate_output(data: dict, schema_path: Path) -> None:
    """质量门控 validate：输出契约校验（jsonschema）"""
    try:
        import jsonschema
    except ImportError:
        print("[warn] 未安装 jsonschema，跳过 Schema 校验")
        return
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(data, schema)
    print("[ok] 输出契约校验通过")


def human_review(data: dict) -> dict:
    """质量门控 review：人审关卡，财务数字必须人工确认"""
    print("\n=== 人工复核 ===")
    print(json.dumps(data.get("metrics", {}), ensure_ascii=False, indent=2))
    answer = input("以上指标与原始财报一致吗？(y/n) ").strip().lower()
    data["human_review_required"] = answer != "y"
    if data["human_review_required"]:
        print("[!] 已标记待人工修正，输出仍会落盘")
    return data


def render(spec: dict, result: dict) -> str:
    """阶段 render：结构化数据 -> Markdown 报告"""
    lines = [
        f"# {spec['company_name']} 财报分析",
        "",
        f"> 类型：{spec.get('report_type', 'unknown')} | 生成时间：自动",
        "",
        "## 摘要",
        result["summary"],
        "",
        "## 趋势",
        result["trend"],
        "",
        "## 风险信号",
    ]
    lines += [f"- {s}" for s in result["risk_signals"]] or ["- 未识别到明显风险信号"]
    lines += [
        "",
        "## 指标",
        "```json",
        json.dumps(result["metrics"], ensure_ascii=False, indent=2),
        "```",
        "",
        "> 本报告由自动化工作流生成，仅做客观分析，不构成投资建议。",
    ]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="财报分析工作流 v0.1")
    ap.add_argument("input", help="输入 JSON 路径（见 schema/input.schema.json）")
    ap.add_argument("-o", "--output", default="output", help="输出目录")
    args = ap.parse_args()

    base_url = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
    api_key = os.environ.get("LLM_API_KEY", "ollama")
    model = os.environ.get("LLM_MODEL", "qwen2.5:7b")

    root = Path(__file__).resolve().parent.parent  # 模板根目录
    spec = json.loads(Path(args.input).read_text(encoding="utf-8"))
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1/4 parse
    report_path = Path(spec["report_path"])
    if not report_path.is_absolute():
        report_path = root / report_path
    if not report_path.exists():
        sys.exit(f"未找到财报 PDF：{report_path}（把真实财报放入 examples/ 并修改 sample-input.json）")
    text = parse_pdf(str(report_path))
    print(f"[1/4] 解析完成：{len(text)} 字符")

    # 2/4 extract（LLM）
    system_prompt = (root / "prompts" / "system.md").read_text(encoding="utf-8")
    raw = call_llm(system_prompt, f"请从以下财报文本中抽取指标并输出 JSON：\n{text[:20000]}",
                   base_url, api_key, model)
    extracted = extract_json(raw)
    print(f"[2/4] 指标抽取完成：{len(extracted.get('metrics', {}))} 项")

    # 3/4 analyze（LLM）
    analyze_prompt = (
        "你是财报分析师。基于以下结构化指标输出 JSON："
        "summary(300字内), trend(注明同比/环比口径), risk_signals(字符串数组)。"
        "只做客观分析，不做投资建议。"
    )
    raw2 = call_llm(analyze_prompt, json.dumps(extracted, ensure_ascii=False),
                    base_url, api_key, model)
    analysis = extract_json(raw2)

    # 4/4 validate + review + render
    result = {**extracted, **analysis}
    validate_output(result, root / "schema" / "output.schema.json")
    result = human_review(result)

    (out_dir / "data.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "report.md").write_text(render(spec, result), encoding="utf-8")
    print(f"[完成] 交付物：{out_dir / 'data.json'} / {out_dir / 'report.md'}")


if __name__ == "__main__":
    main()
