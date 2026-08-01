# mailer.py — HTML 邮件生成 + QQ SMTP 发送

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config import SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_AUTH_CODE, RECIPIENT_EMAIL


CSS = """
body { font-family: 'Microsoft YaHei', 'Segoe UI', Arial, sans-serif; max-width: 780px; margin: 20px auto; color: #1a1a1a; background: #f0f2f5; }
.header { background: linear-gradient(135deg, #1a3c5e, #2471a3); color: white; padding: 28px 24px; border-radius: 10px 10px 0 0; }
.header h1 { margin: 0; font-size: 20px; }
.header .date { font-size: 13px; opacity: 0.85; margin-top: 6px; }
.container { background: white; padding: 6px 18px; border-radius: 0 0 10px 10px; }
.paper { padding: 18px 24px; border-left: 4px solid #2471a3; background: #f8fafc; border-radius: 4px; margin: 16px 0; }
.paper .meta-line { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.paper .badge { background: #2471a3; color: white; font-size: 11px; font-weight: bold; padding: 3px 10px; border-radius: 3px; }
.paper .date { color: #888; font-size: 12px; }
.paper .title { font-size: 15px; font-weight: bold; color: #1a3c5e; margin: 6px 0; line-height: 1.4; }
.paper .title-cn { font-size: 14px; color: #2c3e50; margin: 2px 0 8px 0; line-height: 1.4; }
.paper .authors { color: #666; margin: 4px 0; font-size: 12px; }
.paper .kw-tags { margin: 6px 0; }
.paper .kw-tag { display: inline-block; background: #e8f0f8; color: #2471a3; font-size: 11px; padding: 2px 8px; margin: 2px 4px 2px 0; border-radius: 10px; }
.paper .abstract { font-size: 12px; color: #444; line-height: 1.5; margin: 8px 0; padding: 10px; background: #f0f4f8; border-radius: 4px; }
.paper .abstract-cn { font-size: 12px; color: #7d3c98; line-height: 1.6; margin: 4px 0 8px 0; padding: 10px 10px 10px 14px; background: #faf5ff; border-left: 3px solid #d2b4de; border-radius: 4px; }
.paper .link { margin-top: 8px; }
.paper .link a { color: #2471a3; text-decoration: none; font-size: 12px; font-weight: 500; }
.paper .link a:hover { text-decoration: underline; }
.paper .doi { color: #aaa; font-size: 11px; margin-left: 6px; }
.footer { background: #f5f5f5; padding: 16px 24px; border-radius: 0 0 10px 10px; font-size: 11px; color: #999; text-align: center; }
"""


def build_html(papers):
    date_str = datetime.now().strftime("%Y年%m月%d日")

    # Count by journal
    journal_counts = {}
    for p in papers:
        k = p.get("journal_key", "?")
        journal_counts[k] = journal_counts.get(k, 0) + 1
    journal_summary = " | ".join(f"{k} {n}" for k, n in sorted(journal_counts.items()))

    rows = ""
    for i, p in enumerate(papers, 1):
        title = p.get("title", "")
        title_cn = p.get("title_cn", "")
        abstract = p.get("abstract", "")
        abstract_cn = p.get("abstract_cn", "")
        authors = ", ".join(p.get("authors", [])[:5])
        if len(p.get("authors", [])) > 5:
            authors += " et al."
        journal_key = p.get("journal_key", "")
        journal = p.get("journal", "")
        doi = p.get("doi", "")
        url = p.get("url", f"https://doi.org/{doi}" if doi else "#")
        pub_str = p.get("pub_date_str", "")
        matched = p.get("matched_keywords", [])

        # Badge color by journal
        badge_colors = {"JFM": "#d4a017", "JMPS": "#c0392b", "POF": "#1e6f5c", "CMAME": "#8e44ad"}
        badge_color = badge_colors.get(journal_key, "#2471a3")

        # Keyword tags
        kw_tags = "".join(
            f'<span class="kw-tag">{kw}</span>' for kw in matched[:4]
        )

        rows += f"""
<div class="paper" style="border-left-color: {badge_color};">
    <div class="meta-line">
        <span class="badge" style="background: {badge_color};">{journal_key}</span>
        <span class="date">{pub_str}</span>
    </div>
    <div class="title">{i}. {title}</div>
    {'<div class="title-cn">中文：' + title_cn + '</div>' if title_cn else ''}
    <div class="authors"><b>Authors:</b> {authors}</div>
    {'<div class="kw-tags">' + kw_tags + '</div>' if kw_tags else ''}
    {'<div class="abstract"><b>Abstract:</b> ' + abstract[:500] + ('...' if len(abstract) > 500 else '') + '</div>' if abstract and len(abstract) > 20 else ''}
    {'<div class="abstract-cn"><b>摘要：</b>' + abstract_cn + '</div>' if abstract_cn and len(abstract_cn) > 20 else ''}
    <div class="link">
        <a href="{url}">View Paper →</a>
        {'<span class="doi">DOI: ' + doi + '</span>' if doi else ''}
    </div>
</div>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><style>{CSS}</style></head>
<body>
<div class="header">
    <h1>JFM · JMPS · PoF · CMAME 文献推送</h1>
    <div class="date">气泡 · SPH · 物质点法 · 近场动力学 · 爆炸冲击  |  {date_str}  |  {journal_summary}</div>
</div>
<div class="container">
{rows}
</div>
<div class="footer">
    Claude Code 自动生成 · 数据源: CrossRef + OpenAlex<br>
    Keywords: 气泡 / SPH / 物质点法 / 近场动力学 / 爆炸冲击<br>
    每天 07:00 推送 · 收件人: {RECIPIENT_EMAIL}
</div>
</body>
</html>"""

    return html


def send_email(html_body):
    msg = MIMEMultipart("alternative")
    today = datetime.now().strftime("%Y.%m.%d")
    msg["Subject"] = f"JFM·JMPS·PoF·CMAME 文献推送 — {today}"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SENDER_EMAIL, SENDER_AUTH_CODE)
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        print("Mail sent successfully!")
    except Exception as e:
        import os
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "error.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] SMTP failed: {e}\n")
        raise
