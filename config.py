# config.py — JFM/JMPS/POF/CMAME 每日文献推送配置

import os

# ====== 邮箱配置 ======
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465  # SSL
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "328161253@qq.com")
SENDER_AUTH_CODE = os.environ.get("SMTP_AUTH_CODE", "poqsytqsltvhcahj")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", "328161253@qq.com")

# ====== 目标期刊及其 ISSN ======
TARGET_JOURNALS = {
    "JFM":   {"name": "Journal of Fluid Mechanics",                      "issns": ["0022-1120", "1469-7645"]},
    "JMPS":  {"name": "Journal of the Mechanics and Physics of Solids",  "issns": ["0022-5096"]},
    "POF":   {"name": "Physics of Fluids",                               "issns": ["1070-6631", "1089-7666"]},
    "CMAME": {"name": "Computer Methods in Applied Mechanics and Engineering", "issns": ["0045-7825"]},
}

# ====== 关键词分组（每组用于 OR 查询） ======
KEYWORD_GROUPS = [
    # 气泡
    ["bubble dynamics", "cavitation bubble", "bubble collapse", "bubble pinch-off", "Taylor bubble"],
    # SPH
    ["smoothed particle hydrodynamics", "SPH method", "incompressible SPH", "weakly compressible SPH"],
    # 物质点法
    ["material point method", "MPM", "material point"],
    # 近场动力学
    ["peridynamics", "peridynamic", "bond-based peridynamics", "state-based peridynamics"],
    # 爆炸冲击
    ["explosion", "blast", "shock wave", "detonation", "impact loading", "high strain rate"],
]

# ====== 每个期刊选取论文数 ======
PER_JOURNAL = 2  # 每个期刊2篇
MAX_RESULTS = PER_JOURNAL * len(TARGET_JOURNALS)  # 共8篇

# ====== CrossRef & OpenAlex API 配置 ======
LOOKBACK_MONTHS = 12  # 放宽到12个月以保证各期刊都有结果
CROSSREF_HEADERS = {"User-Agent": "DailyLitBot/1.0 (mailto:328161253@qq.com)"}
OPENALEX_HEADERS = {"User-Agent": "mailto:328161253@qq.com"}
S2_API_KEY = os.environ.get("S2_API_KEY", "s2k-Byr3HEhZOxk5Sstx9AoAszUNFuEdpB0FcjlneqOg")

# ====== Claude API 翻译配置 ======
TRANSLATION_ENABLED = True
