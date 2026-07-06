# fetcher.py — 文献抓取：arXiv API + CrossRef API + IJNME RSS

import feedparser
import requests
import xml.etree.ElementTree as ET
import re
import json
import os
import hashlib
from datetime import datetime, timedelta, timezone
from config import ARXIV_MAX_RESULTS, KEYWORDS, TOP_N, JOURNAL_FEEDS

# ====== 已推送论文追踪（防止重复推送）======
SENT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sent_papers.json")


def _load_sent_papers():
    """加载历史已推送论文记录，返回 title_hash -> date 的字典"""
    if not os.path.exists(SENT_FILE):
        return {}
    try:
        with open(SENT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 只保留最近 30 天的记录，防止文件膨胀
        cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        return {h: d for h, d in data.items() if d >= cutoff}
    except Exception:
        return {}


def _save_sent_papers(papers):
    """保存本次推送的论文到 sent_papers.json"""
    existing = _load_sent_papers()
    today = datetime.now().strftime("%Y-%m-%d")
    for p in papers:
        title_hash = hashlib.md5(p["title"].lower().strip().encode()).hexdigest()
        existing[title_hash] = today
    with open(SENT_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


def _is_already_sent(paper):
    """检查该论文是否已被推送过"""
    sent = _load_sent_papers()
    title_hash = hashlib.md5(paper["title"].lower().strip().encode()).hexdigest()
    return title_hash in sent

# Journal ISSN → name + weight
JOURNALS = {
    "0045-7825": ("CMAME", 6.5),
    "0022-5096": ("JMPS", 5.5),
    "0020-7683": ("IJSS", 4.5),
    "0178-7675": ("Computational Mechanics", 4.0),
    "1097-0207": ("IJNME", 3.5),
}


def _strip_html(text):
    return re.sub(r"<[^>]+>", "", text).strip()


def _sanitize(text):
    """Fix encoding glitches: replace common broken chars, strip non-printable."""
    if not text:
        return ""
    # Replace common encoding artifacts
    text = text.replace("\x96", "–")  # en-dash in Windows-1252
    text = text.replace("\x97", "—")  # em-dash
    text = text.replace("\x8e", "é")
    text = text.replace("\x92", "'")
    text = text.replace("\x93", "\"")
    text = text.replace("\x94", "\"")
    # Remove other non-printable characters (keep newlines, tabs)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)
    return text.strip()


def _score_paper(paper):
    score = paper.get("source_weight", 3.0)
    days = paper.get("days_ago", 0)
    score += max(0, 7 - days) * 1.2
    text = (paper.get("title", "") + " " + paper.get("summary", "")).lower()
    matched = sum(1 for kw in KEYWORDS if kw.lower() in text)
    score += matched * 3.0
    return score


def _paper_within_days(paper, max_days=7):
    return paper.get("days_ago", 999) <= max_days


# ========== arXiv ==========

def fetch_arxiv():
    # Use keyword-enhanced search for more relevant results
    keywords = "+OR+".join(
        [
            "computational+mechanics",
            "finite+element+method",
            "material+point+method",
            "phase+field+fracture",
            "cohesive+zone",
            "peridynamics",
            "isogeometric+analysis",
            "topology+optimization",
            "damage+mechanics",
            "fracture+mechanics",
            "nonlinear+mechanics",
            "constitutive+model",
            "contact+mechanics",
            "numerical+simulation+solid",
            "multiscale+modeling",
        ]
    )
    url = (
        f"http://export.arxiv.org/api/query?"
        f"search_query=all:{keywords}&sortBy=submittedDate&"
        f"start=0&max_results={ARXIV_MAX_RESULTS}"
    )
    papers = []
    try:
        resp = requests.get(url, timeout=30)
        root = ET.fromstring(resp.content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", ns):
            title = _strip_html(entry.find("atom:title", ns).text or "")
            summary = _strip_html(entry.find("atom:summary", ns).text or "")
            published = entry.find("atom:published", ns).text or ""
            link = entry.find("atom:id", ns).text or ""
            authors = [
                a.find("atom:name", ns).text
                for a in entry.findall("atom:author", ns)
            ]
            try:
                pub_dt = datetime.strptime(published[:10], "%Y-%m-%d")
                days_ago = (
                    datetime.now(timezone.utc) - pub_dt.replace(tzinfo=timezone.utc)
                ).days
            except Exception:
                days_ago = 99
            papers.append(
                {
                    "title": _sanitize(title),
                    "summary": _sanitize(summary[:600]),
                    "authors": authors,
                    "source": "arXiv",
                    "source_weight": 3.0,
                    "link": link,
                    "published": published[:10],
                    "days_ago": days_ago,
                }
            )
    except Exception as e:
        print(f"[arXiv] fetch error: {e}")
    return papers


# ========== CrossRef (Elsevier + Springer journals) ==========

def fetch_crossref(issn, journal_name, weight):
    papers = []
    since = (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%Y-%m-%d")
    url = "https://api.crossref.org/works"
    params = {
        "filter": f"issn:{issn},from-pub-date:{since}",
        "rows": 10,
        "sort": "published",
        "order": "desc",
    }
    try:
        resp = requests.get(url, params=params, timeout=30)
        data = resp.json()
        items = data.get("message", {}).get("items", [])
        for item in items:
            title = item.get("title", [""])[0] if item.get("title") else ""
            title = _strip_html(title)
            summary = item.get("abstract", "")
            if summary:
                summary = _strip_html(summary)[:600]
            link = item.get("URL", "")
            authors = [
                a.get("given", "") + " " + a.get("family", "")
                for a in item.get("author", [])
            ]
            created = item.get("created", {}).get("date-time", "")
            try:
                pub_dt = datetime.strptime(created[:10], "%Y-%m-%d")
                days_ago = (
                    datetime.now(timezone.utc) - pub_dt.replace(tzinfo=timezone.utc)
                ).days
            except Exception:
                days_ago = 14
            papers.append(
                {
                    "title": _sanitize(title),
                    "summary": _sanitize(summary),
                    "authors": authors,
                    "source": journal_name,
                    "source_weight": weight,
                    "link": link,
                    "published": created[:10],
                    "days_ago": days_ago,
                }
            )
    except Exception as e:
        print(f"[{journal_name}] CrossRef error: {e}")
    return papers


# ========== IJNME (Wiley RSS — works reliably) ==========

def fetch_ijnme():
    papers = []
    try:
        feed = feedparser.parse(
            "https://onlinelibrary.wiley.com/feed/10970207/most-recent"
        )
        for entry in feed.entries[:10]:
            title = _strip_html(entry.get("title", ""))
            # Try multiple fields for real abstract content
            summary = entry.get("summary", entry.get("description", ""))
            summary = _strip_html(summary)
            # Try content:encoded for richer description
            if len(summary) < 200 and "content" in entry:
                for c in entry["content"]:
                    if c.get("type") == "text/html":
                        content_text = _strip_html(c.get("value", ""))
                        if len(content_text) > len(summary):
                            summary = content_text
            # Try description separately
            if len(summary) < 200 and "description" in entry:
                desc = _strip_html(entry["description"])
                if len(desc) > len(summary):
                    summary = desc
            # Wiley feed often has "Abstract" prefix in the description
            if summary.startswith(title):
                summary = summary[len(title) :].strip()
            link = entry.get("link", "")
            if isinstance(link, list):
                link = link[0].get("href", "") if link else ""
            authors = []
            if "authors" in entry:
                authors = [a.get("name", "") for a in entry["authors"]]
            pub = entry.get("published", entry.get("updated", ""))
            days_ago = 7
            try:
                for fmt in [
                    "%a, %d %b %Y %H:%M:%S %z",
                    "%a, %d %b %Y %H:%M:%S %Z",
                ]:
                    try:
                        dt = datetime.strptime(pub.strip(), fmt)
                        days_ago = (
                            datetime.now(timezone.utc)
                            - dt.astimezone(timezone.utc)
                        ).days
                        break
                    except Exception:
                        continue
            except Exception:
                pass
            papers.append(
                {
                    "title": _sanitize(title),
                    "summary": _sanitize(summary[:600]),
                    "authors": authors,
                    "source": "IJNME",
                    "source_weight": 3.5,
                    "link": link,
                    "published": pub,
                    "days_ago": days_ago,
                }
            )
    except Exception as e:
        print(f"[IJNME] fetch error: {e}")
    return papers


# ========== 通用 RSS/Atom 抓取（作为 CrossRef 摘要补充） ==========

def fetch_generic_rss(url, journal_name):
    """Fetch papers from a generic RSS/Atom feed. Returns list of papers."""
    papers = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:10]:
            title = _strip_html(entry.get("title", ""))
            if not title:
                continue
            # Try multiple fields for abstract
            summary = entry.get("summary", entry.get("description", ""))
            summary = _strip_html(summary)
            # Try content:encoded for richer description
            if "content" in entry:
                for c in entry["content"]:
                    if c.get("type") == "text/html" and c.get("value", ""):
                        ct = _strip_html(c["value"])
                        if len(ct) > len(summary):
                            summary = ct
            # Try dc:description, content:description, etc.
            if len(summary) < 50:
                for key in ["dc_description", "description", "dc:description"]:
                    val = entry.get(key, "")
                    if val and len(_strip_html(val)) > len(summary):
                        summary = _strip_html(val)
            # RSSHub (elsevier) often puts abstract in a specific field
            if len(summary) < 50:
                for key in entry.keys():
                    val = entry.get(key, "")
                    if isinstance(val, str) and len(_strip_html(val)) > len(summary):
                        summary = _strip_html(val)
            # Filter out non-paper entries
            if any(bad in title.lower() for bad in ["issue information", "editorial board", "table of contents"]):
                continue
            link = entry.get("link", "")
            if isinstance(link, list):
                link = link[0].get("href", "") if link else ""
            papers.append({
                "title": _sanitize(title),
                "summary": _sanitize(summary[:800]),
                "source": journal_name,
                "link": link,
            })
    except Exception as e:
        print(f"[{journal_name}] RSS error: {e}")
    return papers


# ========== 聚合 + 排序 ==========

def fetch_and_rank():
    all_papers = fetch_arxiv()

    # CrossRef first (better metadata), then RSS
    for issn, (name, weight) in JOURNALS.items():
        all_papers.extend(fetch_crossref(issn, name, weight))
    all_papers.extend(fetch_ijnme())

    # Supplement: fetch RSS feeds for journals and merge abstracts
    rss_papers = []
    for journal_name, url in JOURNAL_FEEDS.items():
        # IJNME already handled by its dedicated RSS fetcher
        if journal_name == "IJNME":
            continue
        rss_papers.extend(fetch_generic_rss(url, journal_name))

    # Merge RSS abstracts into papers with empty summaries (match by title prefix)
    if rss_papers:
        for p in all_papers:
            if len(p.get("summary", "")) < 50:
                p_key = p["title"].lower()[:50]
                for rp in rss_papers:
                    r_key = rp["title"].lower()[:50]
                    if p_key == r_key and len(rp.get("summary", "")) > len(p.get("summary", "")):
                        p["summary"] = rp["summary"]

    # Score & filter
    for p in all_papers:
        p["_score"] = _score_paper(p)

    all_papers = [p for p in all_papers if _paper_within_days(p, max_days=14)]
    all_papers.sort(key=lambda p: p["_score"], reverse=True)

    # Deduplicate, preferring entries with abstracts
    seen = {}
    for p in all_papers:
        key = p["title"].lower()[:60]
        if any(
            bad in p["title"].lower()
            for bad in [
                "hypersonic",
                "plasma",
                "turbulence",
                "battery",
                "membrane",
                "droplet",
                "biological",
                "protein",
                "dna",
                "gene",
                "drug",
                "chemistry",
                "chemical",
                "corrosion",
                "fokker-planck",
                "quantum",
                "electromagnetic",
                "antenna",
                "issue information",
                "editorial board",
                "table of contents",
            ]
        ):
            continue
        if key not in seen or len(p.get("summary", "")) > len(seen[key].get("summary", "")):
            seen[key] = p
    unique = list(seen.values())

    # 过滤已推送过的论文
    already_sent = _load_sent_papers()
    fresh = [p for p in unique if not _is_already_sent(p)]
    if not fresh:
        # 如果没有新论文，记录但不推送（避免重复发同一批文章）
        print(f"所有 {len(unique)} 篇候选论文均已推送过，跳过本次推送")
        return []

    print(f"过滤掉 {len(unique) - len(fresh)} 篇已推送论文，剩余 {len(fresh)} 篇新论文")

    result = fresh[:TOP_N]

    return result


def mark_as_sent(papers):
    """标记论文为已推送（仅在成功发送后调用）"""
    _save_sent_papers(papers)


if __name__ == "__main__":
    top = fetch_and_rank()
    for i, p in enumerate(top, 1):
        print(f"[{i}] [{p['source']}] {p['title'][:80]}")
