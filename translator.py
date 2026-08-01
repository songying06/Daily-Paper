# translator.py — 使用 Claude-compatible API 翻译论文标题和摘要

import requests
import json
import os

# API 配置：优先从环境变量读取（GitHub Secrets）
API_URL = os.environ.get("TRANSLATE_API_URL", "https://api.deepseek.com/anthropic/v1/messages")
API_KEY = os.environ.get("TRANSLATE_API_KEY", "sk-d9781e71a93e410690d5a8f5acce2026")
MODEL = os.environ.get("TRANSLATE_MODEL", "deepseek-v4-pro")


def _log_error(msg):
    from datetime import datetime
    import os
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "error.log")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n")


def translate_paper(paper):
    title = paper.get("title", "")
    abstract = paper.get("abstract", "")

    if not title:
        return paper

    # Skip abstract translation if no meaningful abstract
    has_abstract = abstract and len(abstract.strip()) > 30
    abstract_line = f"\nAbstract: {abstract[:800]}" if has_abstract else ""

    prompt = f"""Translate the following academic paper title{" and abstract" if has_abstract else ""} into Chinese.
Keep technical terms accurate (e.g., "Bubble Dynamics" → "气泡动力学", "Cavitation" → "空化", "SPH" → "光滑粒子流体动力学", "Material Point Method" → "物质点法", "Peridynamics" → "近场动力学", "Explosion" → "爆炸", "Blast Wave" → "爆炸波", "Shock Wave" → "激波", "Impact" → "冲击", "High Strain Rate" → "高应变率").

Return ONLY a JSON object with fields "title_cn" and "abstract_cn". No markdown, no extra text.

Title: {title}
{abstract_line}
"""

    try:
        resp = requests.post(
            API_URL,
            headers={
                "Content-Type": "application/json",
                "x-api-key": API_KEY,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": MODEL,
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
                "thinking": {"type": "disabled"},
            },
            timeout=90,
        )
        if resp.status_code == 200:
            data = resp.json()
            text = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    text = block.get("text", "")
                    break
            # Extract JSON from response
            json_start = text.find("{")
            json_end = text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(text[json_start:json_end])
                paper["title_cn"] = result.get("title_cn", "")
                paper["abstract_cn"] = result.get("abstract_cn", "")
                # Keep summary_cn for backward compatibility
                if not paper.get("abstract_cn"):
                    paper["abstract_cn"] = result.get("summary_cn", "")
        else:
            paper["title_cn"] = ""
            paper["abstract_cn"] = ""
            _log_error(f"API status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        paper["title_cn"] = ""
        paper["abstract_cn"] = ""
        print(f"[translate] error: {e}")
        _log_error(str(e))

    return paper


def translate_papers(papers):
    translated = []
    for i, p in enumerate(papers):
        print(f"  translating {i+1}/{len(papers)}: {p['title'][:60]}...")
        translated.append(translate_paper(p))
    return translated
