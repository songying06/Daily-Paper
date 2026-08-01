# fetcher.py — 文献抓取：CrossRef API + OpenAlex 摘要补充

import requests
import json
import os
import hashlib
import time
from datetime import datetime, timedelta, timezone
from config import (
    TARGET_JOURNALS,
    KEYWORD_GROUPS,
    PER_JOURNAL,
    MAX_RESULTS,
    LOOKBACK_MONTHS,
    CROSSREF_HEADERS,
    OPENALEX_HEADERS,
    S2_API_KEY,
)

# ====== 已推送论文追踪 ======
SENT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sent_papers.json")


def _load_sent_papers():
    """加载历史已推送论文记录"""
    if not os.path.exists(SENT_FILE):
        return {}
    try:
        with open(SENT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        return {h: d for h, d in data.items() if d >= cutoff}
    except Exception:
        return {}


def _save_sent_papers(papers):
    """保存本次推送的论文"""
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


def get_journal_key(journal_name):
    """Map journal name to short key (JFM/JMPS/POF/CMAME)."""
    if not journal_name:
        return None
    j = journal_name.lower().strip()
    for key, info in TARGET_JOURNALS.items():
        if info["name"].lower() in j:
            return key
    return None


def compute_relevance(title, abstract=""):
    """
    Compute relevance score for a paper against keyword groups.
    Returns (score, matched_keywords).
    """
    text = (title + " " + abstract).lower()
    score = 0
    matched = []

    for group in KEYWORD_GROUPS:
        group_weight = 15
        best = 0
        best_kw = None
        for kw in group:
            if kw.lower() in text:
                if kw.lower() in title.lower():
                    s = group_weight
                else:
                    s = group_weight * 0.6
                if s > best:
                    best = s
                    best_kw = kw
        if best > 0:
            score += best
            matched.append(best_kw)

    return min(score, 100), matched


def fetch_from_crossref(issn_filter):
    """Search CrossRef for recent journal articles by ISSN."""
    query_terms = [g[0] for g in KEYWORD_GROUPS]
    query = " OR ".join(query_terms)

    lookback = datetime.now() - timedelta(days=LOOKBACK_MONTHS * 30)
    filter_date = lookback.strftime("%Y-%m-%d")

    filters = f"from-pub-date:{filter_date},type:journal-article,issn:{issn_filter}"

    params = {
        "query": query,
        "filter": filters,
        "rows": 25,
        "sort": "published",
        "order": "desc",
    }

    print(f"  CrossRef [issn={issn_filter}] (since {filter_date})...")
    try:
        resp = requests.get(
            "https://api.crossref.org/works",
            params=params,
            headers=CROSSREF_HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
    except Exception as e:
        print(f"    Error: {e}")
        return []

    data = resp.json()
    items = data.get("message", {}).get("items", [])
    total = data.get("message", {}).get("total-results", "?")
    print(f"    → {total} total, {len(items)} returned")

    papers = []
    for item in items:
        title = (item.get("title") or ["Untitled"])[0].replace("\n", " ").strip()

        authors = []
        for a in item.get("author", [])[:8]:
            given = a.get("given", "")
            family = a.get("family", "")
            if given or family:
                authors.append(f"{given} {family}".strip())

        journal = (item.get("container-title") or [""])[0]
        doi = item.get("DOI", "")
        url = item.get("URL", f"https://doi.org/{doi}" if doi else "")

        published = item.get("published", {})
        date_parts = published.get("date-parts", [[0, 0, 0]])[0]
        try:
            y, m, d = (int(x) if x else 0 for x in date_parts)
            pub_dt = datetime(y or 1970, m or 1, d or 1, tzinfo=timezone.utc)
            pub_str = f"{y}-{m:02d}-{d:02d}"
        except (ValueError, TypeError):
            pub_str = "-".join(str(x) for x in date_parts)
            pub_dt = datetime(1970, 1, 1, tzinfo=timezone.utc)

        relevance, matched_kws = compute_relevance(title, "")
        if relevance == 0:
            continue

        papers.append(
            {
                "title": title,
                "authors": authors,
                "journal": journal,
                "journal_key": get_journal_key(journal),
                "doi": doi,
                "url": url,
                "pub_date_str": pub_str,
                "pub_date_obj": pub_dt,
                "relevance": relevance,
                "matched_keywords": matched_kws,
                "abstract": "",
                "abstract_source": "",
                "source": get_journal_key(journal) or journal,
                "published": pub_str,
            }
        )

    return papers


def enrich_abstracts(papers):
    """Fetch abstracts from OpenAlex, with fallbacks."""
    print(f"  Fetching abstracts...")
    enriched = 0
    for p in papers:
        if not p["doi"]:
            continue
        if p.get("abstract"):
            enriched += 1
            continue

        time.sleep(1.2)

        # Source 1: OpenAlex
        try:
            url = f"https://api.openalex.org/works/doi:{p['doi']}"
            resp = requests.get(url, headers=OPENALEX_HEADERS, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                inv = data.get("abstract_inverted_index", None)
                if inv and isinstance(inv, dict) and len(inv) > 0:
                    words = sorted(
                        inv.items(),
                        key=lambda x: x[1][0] if isinstance(x[1], list) else x[1],
                    )
                    abstract = " ".join(w[0] for w in words)
                    if len(abstract) > 50:
                        p["abstract"] = abstract
                        p["abstract_source"] = "OpenAlex"
                        enriched += 1
                        rel, matched = compute_relevance(p["title"], abstract)
                        p["relevance"] = rel
                        p["matched_keywords"] = matched
                        continue
        except Exception:
            pass

        # Source 2: CrossRef single-work API
        try:
            time.sleep(1.5)
            url = f"https://api.crossref.org/works/{p['doi']}"
            resp = requests.get(url, headers=CROSSREF_HEADERS, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                abstract = data.get("message", {}).get("abstract", "")
                if abstract and len(abstract) > 50:
                    import re

                    abstract = re.sub(r"<[^>]+>", "", abstract).strip()
                    p["abstract"] = abstract
                    p["abstract_source"] = "CrossRef"
                    enriched += 1
                    rel, matched = compute_relevance(p["title"], abstract)
                    p["relevance"] = rel
                    p["matched_keywords"] = matched
                    continue
        except Exception:
            pass

        # Source 3: Semantic Scholar
        try:
            time.sleep(1.5)
            s2_headers = {**OPENALEX_HEADERS, "x-api-key": S2_API_KEY}
            url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{p['doi']}?fields=abstract"
            resp = requests.get(url, headers=s2_headers, timeout=15)
            if resp.status_code == 200:
                abstract = resp.json().get("abstract", "")
                if abstract and len(abstract) > 50:
                    p["abstract"] = abstract
                    p["abstract_source"] = "SemanticScholar"
                    enriched += 1
                    rel, matched = compute_relevance(p["title"], abstract)
                    p["relevance"] = rel
                    p["matched_keywords"] = matched
                    continue
        except Exception:
            pass

    print(f"    Abstracts found: {enriched}/{len(papers)}")
    return papers


def select_diverse(papers, per_journal=2):
    """
    Select papers ensuring journal diversity.
    Pick top per_journal from each journal by relevance.
    """
    by_journal = {}
    for p in papers:
        k = p.get("journal_key", "OTHER")
        by_journal.setdefault(k, []).append(p)

    selected = []
    seen_dois = set()

    # Phase 1: pick per_journal best from each journal
    for j_key in TARGET_JOURNALS.keys():
        candidates = sorted(
            by_journal.get(j_key, []),
            key=lambda x: (-x["relevance"], -x["pub_date_obj"].timestamp()),
        )
        count = 0
        for p in candidates:
            if count >= per_journal:
                break
            if p["doi"] and p["doi"] in seen_dois:
                continue
            if p["doi"]:
                seen_dois.add(p["doi"])
            selected.append(p)
            count += 1

    # Phase 2: fill remaining with next best from any journal
    remaining = sorted(
        [p for p in papers if p["doi"] not in seen_dois],
        key=lambda x: (-x["relevance"], -x["pub_date_obj"].timestamp()),
    )
    while len(selected) < MAX_RESULTS and remaining:
        p = remaining.pop(0)
        if p["doi"]:
            seen_dois.add(p["doi"])
        selected.append(p)

    return selected


def fetch_and_rank():
    """Main fetcher: search all journals, enrich, rank, select."""
    all_papers = []
    seen_dois = set()

    for j_key, j_info in TARGET_JOURNALS.items():
        for issn in j_info["issns"]:
            try:
                results = fetch_from_crossref(issn)
                for p in results:
                    if p["doi"] and p["doi"] in seen_dois:
                        continue
                    if p["doi"]:
                        seen_dois.add(p["doi"])
                    all_papers.append(p)
            except Exception as e:
                print(f"    {j_key}({issn}) search failed: {e}")
                continue

    if not all_papers:
        print("  No papers found.")
        return []

    print(f"\n  Total candidate papers (relevant): {len(all_papers)}")

    # Enrich with abstracts
    all_papers = enrich_abstracts(all_papers)

    # Filter already sent papers
    already_sent = _load_sent_papers()
    fresh = [p for p in all_papers if not _is_already_sent(p)]
    if not fresh:
        print(f"所有 {len(all_papers)} 篇候选论文均已推送过，跳过本次推送")
        return []

    print(f"过滤掉 {len(all_papers) - len(fresh)} 篇已推送论文，剩余 {len(fresh)} 篇新论文")

    # Diversified selection
    papers = select_diverse(fresh, per_journal=PER_JOURNAL)

    # Report
    print(f"\n  Selected {len(papers)} papers:")
    for i, p in enumerate(papers, 1):
        rel = p.get("relevance", 0)
        abs_tag = " [ABS]" if p.get("abstract") else ""
        kws = ",".join(p.get("matched_keywords", [])[:3])
        print(f"    {i}. [{p.get('journal_key','?')}]{abs_tag} rel={rel} ({kws})")
        print(f"       {p['title'][:90]}")
        print(f"       {p['journal']} | {p['pub_date_str']}")

    return papers


def mark_as_sent(papers):
    """标记论文为已推送（仅在成功发送后调用）"""
    _save_sent_papers(papers)


if __name__ == "__main__":
    top = fetch_and_rank()
    print(f"\nTotal: {len(top)} papers")
