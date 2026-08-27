#!/usr/bin/env python3
"""小红书爆款文案工作流 v0.1 — 轻量 Python 实现（数字管道第三个模板）

用法：
    export LLM_BASE_URL=http://localhost:11434/v1   # 默认 Ollama 本地模型
    export LLM_MODEL=qwen2.5:7b
    python scripts/run.py examples/sample-input.json -o output/

也支持 .env 文件（模板根目录），格式见 .env.example。

流水线（DAG）：extract -> draft -> enhance -> validate -> review -> render
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
        "temperature": 0.7,  # 文案需要一点创造性
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
    """质量门控 review：人审关卡（品牌口径 / 合规性）"""
    print("\n=== 人工复核 ===")
    print(f"标题候选：{data.get('titles')}")
    answer = input("文案内容符合品牌口径与合规要求吗？(y/n) ").strip().lower()
    data["human_review_required"] = answer != "y"
    if data["human_review_required"]:
        print("[!] 已标记待人工修正，输出仍会落盘")
    return data


def render(spec: dict, result: dict) -> str:
    """阶段 render：结构化数据 -> Markdown 文案稿"""
    lines = [
        f"# 小红书文案：{spec['topic']}",
        "",
        f"> 受众：{spec.get('audience', '泛科技人群')} | 风格：{spec.get('tone', '种草')} | 字数上限：{spec.get('word_limit', 500)}",
        "",
        "## 备选标题",
        "",
    ]
    lines += [f"{i}. {t}" for i, t in enumerate(result["titles"], 1)]
    lines += ["", "## 正文", "", result["body"], "", "## 话题标签", ""]
    lines += [f"#{t}" for t in result["tags"]]
    lines += ["", "## 发布建议", ""]
    lines += [f"- {p}" for p in result["publish_tips"]]
    lines += ["", "> 本文案由自动化工作流生成，发布前请人工核对合规与品牌口径。"]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="小红书爆款文案工作流 v0.1")
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

    # 1/3 extract：卖点提炼（若用户已提供则直接用）
    selling_points = spec.get("selling_points")
    if not selling_points:
        raw0 = call_llm(
            system_prompt,
            f"主题：{spec['topic']}\n目标人群：{spec.get('audience', '泛科技人群')}\n"
            f"请提炼 3-5 个最值得讲的卖点/切入角度，输出 JSON：{{selling_points: [string]}}",
            base_url, api_key, model,
        )
        selling_points = extract_json(raw0).get("selling_points", [])
    print(f"[1/3] 卖点：{selling_points}")

    # 2/3 draft：生成文案初稿
    raw1 = call_llm(
        system_prompt,
        f"主题：{spec['topic']}\n受众：{spec.get('audience', '泛科技人群')}\n风格：{spec.get('tone', '种草')}\n"
        f"字数上限：{spec.get('word_limit', 500)}\n卖点：{json.dumps(selling_points, ensure_ascii=False)}\n\n"
        "生成文案（严格按 output.schema.json 结构输出 JSON）",
        base_url, api_key, model,
    )
    draft = extract_json(raw1)
    print(f"[2/3] 文案初稿完成：{len(draft.get('titles', []))} 标题 / {len(draft.get('body', ''))} 字正文")

    # 3/3 enhance：爆款要素自检润色（第二次 LLM 调用）
    raw2 = call_llm(
        system_prompt,
        f"这是初稿：\n{json.dumps(draft, ensure_ascii=False)}\n\n"
        "请按爆款要素检查并润色：标题更抓人、正文增强情绪与互动钩子、标签更精准。"
        "输出与原结构一致的 JSON（titles 3 个 / body / tags / publish_tips）。",
        base_url, api_key, model,
    )
    result = extract_json(raw2)
    print(f"[3/3] 润色完成：{len(result.get('titles', []))} 标题 / {len(result.get('body', ''))} 字正文")

    # 收尾 review + validate + render
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
