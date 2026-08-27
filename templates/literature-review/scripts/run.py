#!/usr/bin/env python3
"""文献综述初稿工作流 v0.1 — 轻量 Python 实现（数字管道第二个模板）

用法：
    export LLM_BASE_URL=http://localhost:11434/v1   # 默认 Ollama 本地模型
    export LLM_MODEL=qwen2.5:7b
    python scripts/run.py examples/sample-input.json -o output/

也支持 .env 文件（模板根目录），格式见 .env.example：
    LLM_BASE_URL=https://openrouter.ai/api/v1
    LLM_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free
    LLM_API_KEY=sk-or-v1-xxx

流水线（DAG）：summarize -> cluster -> draft -> validate -> review -> render
"""
import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


def call_llm(system: str, user: str, base_url: str, api_key: str, model: str) -> str:
    """调用任意 OpenAI 兼容接口（Ollama / OpenRouter / DeepSeek ...）"""
    import time

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.3,
    }
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    last_err = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            last_err = e
            wait = 3 * (attempt + 1)
            print(f"[retry] 第 {attempt + 1} 次失败（{type(e).__name__}），{wait}s 后重试")
            time.sleep(wait)
    raise last_err


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
    """质量门控 review：人审关卡"""
    print("\n=== 人工复核 ===")
    print(f"标题：{data.get('title')}")
    print(f"分节：{[s['heading'] for s in data.get('sections', [])]}")
    answer = input("综述结构符合预期吗？(y/n) ").strip().lower()
    data["human_review_required"] = answer != "y"
    if data["human_review_required"]:
        print("[!] 已标记待人工修正，输出仍会落盘")
    return data


def render(spec: dict, result: dict) -> str:
    """阶段 render：结构化数据 -> Markdown 综述初稿"""
    lines = [
        f"# {result['title']}",
        "",
        f"> 主题：{spec['topic']} | 文献数：{len(spec['papers'])} | 风格：{spec.get('style', 'academic')}",
        "",
        "## 一、研究背景",
        result["overview"],
        "",
    ]
    for i, sec in enumerate(result["sections"], 1):
        num = ["一", "二", "三", "四", "五", "六"][i - 1] if i <= 6 else str(i)
        lines += [f"## {num}、{sec['heading']}", "", sec["content"], ""]
    lines += ["## 关键文献", ""]
    for kp in result["key_papers"]:
        lines += [f"- **{kp['title']}**：{kp['contribution']}"]
    lines += ["", "## 研究缺口", ""]
    lines += [f"- {g}" for g in result["research_gaps"]] or ["- 未识别到明显研究缺口"]
    lines += ["", "## 参考文献", ""]
    lines += [f"{i}. {r}" for i, r in enumerate(result["references"], 1)]
    lines += ["", "> 本综述初稿由自动化工作流生成，请对照原始文献核验引用与结论。"]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="文献综述初稿工作流 v0.1")
    ap.add_argument("input", help="输入 JSON 路径（见 schema/input.schema.json）")
    ap.add_argument("-o", "--output", default="output", help="输出目录")
    ap.add_argument("--auto-review", action="store_true",
                    help="自动化复核：跳过人工确认，human_review_required=false（调用方负责核验）")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent  # 模板根目录
    if load_dotenv is not None:
        load_dotenv(root / ".env")

    base_url = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
    api_key = os.environ.get("LLM_API_KEY", "ollama")
    model = os.environ.get("LLM_MODEL", "qwen2.5:7b")

    spec = json.loads(Path(args.input).read_text(encoding="utf-8"))
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    system_prompt = (root / "prompts" / "system.md").read_text(encoding="utf-8")

    # 1/3 summarize：逐篇提炼要点（一次调用，输出标注结构的要点 JSON）
    papers_text = "\n\n".join(
        f"[文献{i + 1}] {p['title']}"
        + (f"（{p.get('year')}，{p.get('venue')}）" if p.get('year') or p.get('venue') else "")
        + f"\n摘要：{p['abstract']}"
        for i, p in enumerate(spec["papers"])
    )
    raw1 = call_llm(
        system_prompt,
        f"请为以下 {len(spec['papers'])} 篇文献分别提炼 3-5 个核心要点，输出 JSON："
        f"{{notes: [{{title, points: [string]}}]}}\n\n{papers_text}",
        base_url, api_key, model,
    )
    notes = extract_json(raw1)
    print(f"[1/3] 文献要点提炼完成：{len(notes.get('notes', []))} 篇")

    # 2/3 draft：聚类 + 生成综述初稿（第二次 LLM 调用）
    raw2 = call_llm(
        system_prompt,
        f"主题：{spec['topic']}\n风格：{spec.get('style', 'academic')}\n分节数：{spec.get('section_count', 3)}\n\n"
        f"基于以下文献要点生成综述初稿 JSON（严格按 output.schema.json 结构）：\n"
        f"{json.dumps(notes, ensure_ascii=False)}",
        base_url, api_key, model,
    )
    result = extract_json(raw2)
    print(f"[2/3] 综述初稿生成完成：{len(result.get('sections', []))} 节 / {len(result.get('references', []))} 条参考文献")

    # 3/3 review + validate + render
    if args.auto_review:
        result["human_review_required"] = False
        result["review_note"] = "自动化复核（调用方负责核验）"
    else:
        result = human_review(result)
    validate_output(result, root / "schema" / "output.schema.json")

    (out_dir / "data.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "report.md").write_text(render(spec, result), encoding="utf-8")
    print(f"[完成] 交付物：{out_dir / 'data.json'} / {out_dir / 'report.md'}")


if __name__ == "__main__":
    main()
