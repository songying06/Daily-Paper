# mailer.py — HTML 邮件生成 + QQ SMTP 发送

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config import SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_AUTH_CODE, RECIPIENT_EMAIL


CSS = """
body { font-family: 'Microsoft YaHei', 'Segoe UI', Arial, sans-serif; max-width: 720px; margin: 20px auto; color: #1a1a1a; }
.header { background: linear-gradient(135deg, #1a5276, #2980b9); color: white; padding: 28px 24px; border-radius: 10px 10px 0 0; }
.header h1 { margin: 0; font-size: 20px; }
.header .date { font-size: 13px; opacity: 0.85; margin-top: 6px; }
.paper { padding: 20px 24px; border-bottom: 1px solid #e8e8e8; }
.paper:last-child { border-bottom: none; }
.paper .index { display: inline-block; background: #2980b9; color: white; width: 26px; height: 26px; line-height: 26px; text-align: center; border-radius: 50%; font-size: 13px; font-weight: bold; margin-right: 8px; }
.paper .title { font-size: 16px; font-weight: bold; color: #1a5276; margin: 6px 0; }
.paper .title-cn { font-size: 15px; color: #2c3e50; margin: 2px 0 8px 0; }
.paper .meta { font-size: 12px; color: #888; margin: 4px 0; }
.paper .meta .source { color: #2980b9; font-weight: bold; }
.paper .abstract { font-size: 13px; color: #555; line-height: 1.7; margin: 8px 0; }
.paper .abstract-cn { font-size: 13px; color: #7d3c98; line-height: 1.7; margin: 4px 0 8px 0; padding-left: 12px; border-left: 3px solid #d2b4de; }
.paper .link { font-size: 12px; }
.paper .link a { color: #2980b9; text-decoration: none; }
.paper .link a:hover { text-decoration: underline; }
.footer { background: #f5f5f5; padding: 16px 24px; border-radius: 0 0 10px 10px; font-size: 11px; color: #999; text-align: center; }
"""


def build_html(papers):
    date_str = datetime.now().strftime("%Y年%m月%d日")
    rows = ""
    for i, p in enumerate(papers, 1):
        title = p.get("title", "")
        title_cn = p.get("title_cn", "")
        summary = p.get("summary", "")
        summary_cn = p.get("summary_cn", "")
        authors = ", ".join(p.get("authors", [])[:5])
        source = p.get("source", "")
        link = p.get("link", "#")
        published = p.get("published", "")

        rows += f"""
<div class="paper">
    <div><span class="index">{i}</span><span class="meta"><span class="source">{source}</span> &nbsp;|&nbsp; {published}</span></div>
    <div class="title">{title}</div>
    <div class="title-cn">{"中文：" + title_cn if title_cn else ""}</div>
    <div class="meta">{authors}</div>
    {(f'<div class="abstract"><b>Abstract:</b> {summary[:400]}</div>') if summary and len(summary) > 20 else ""}
    {f'<div class="abstract-cn">{"摘要：" + summary_cn}</div>' if summary_cn and len(summary_cn) > 20 else ""}
    <div class="link"><a href="{link}">{'arXiv' if 'arxiv' in link else 'Read on Publisher'}</a></div>
</div>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{CSS}</style></head>
<body>
<div class="header">
    <h1>计算固体力学 · 每日前沿文献</h1>
    <div class="date">{date_str} | 共 {len(papers)} 篇 | 来源: arXiv · CMAME · IJNME · JMPS · Comp Mech · IJSS</div>
</div>
{rows}
<div class="footer">
    此邮件由 daily-paper-push 自动生成 · 每日 7:00 AM 推送<br>
    如需调整关键词或期刊来源，请联系修改配置
</div>
</body></html>"""


def send_email(html_body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"计算固体力学前沿文献 — {datetime.now().strftime('%Y.%m.%d')}"
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
