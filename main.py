# main.py — 计算固体力学每日前沿文献推送
#
# 用法:
#   python main.py           # 抓取 + 翻译 + 推送
#   python main.py --dry-run # 仅抓取 + 显示，不发邮件
#   python main.py --no-translate  # 跳过翻译 (更快)

import sys
from datetime import datetime
from fetcher import fetch_and_rank, mark_as_sent
from mailer import build_html, send_email


def main():
    dry_run = "--dry-run" in sys.argv
    no_translate = "--no-translate" in sys.argv

    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] === 开始抓取文献 ===")

    papers = fetch_and_rank()
    if not papers:
        print("未找到符合条件的文献，退出。")
        return
    print(f"抓取到 {len(papers)} 篇论文")

    if not no_translate:
        print("=== 翻译中 ===")
        from translator import translate_papers

        papers = translate_papers(papers)
    else:
        for p in papers:
            p["title_cn"] = ""
            p["summary_cn"] = ""

    html = build_html(papers)

    if dry_run:
        import tempfile, os, subprocess

        path = os.path.join(tempfile.gettempdir(), "paper_preview.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Dry-run: preview saved to {path}")
        os.startfile(path)
    else:
        print("=== 发送邮件 ===")
        send_email(html)
        # 仅在成功发送后标记为已推送
        mark_as_sent(papers)
        print("Done!")


if __name__ == "__main__":
    main()
