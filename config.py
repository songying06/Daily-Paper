# config.py — 计算固体力学每日文献推送配置

import os

# ====== 邮箱配置 ======
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465  # SSL
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "328161253@qq.com")
# 授权码优先从环境变量读取（GitHub Secrets），否则使用默认值
SENDER_AUTH_CODE = os.environ.get("SMTP_AUTH_CODE", "poqsytqsltvhcahj")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", "328161253@qq.com")

# ====== arXiv 配置 ======
ARXIV_CATEGORIES = ["cs.CE", "physics.comp-ph"]
ARXIV_MAX_RESULTS = 30

# ====== 期刊 RSS/Atom 源 ======
JOURNAL_FEEDS = {
    "CMAME": "https://rss.sciencedirect.com/publication/science/00457825",
    "IJNME": "https://onlinelibrary.wiley.com/feed/10970207/most-recent",
    "JMPS": "https://rss.sciencedirect.com/publication/science/00225096",
    "Computational Mechanics": "https://link.springer.com/search.rss?facet-content-type=Article&facet-journal-id=466",
    "IJSS": "https://rss.sciencedirect.com/publication/science/00207683",
}

# ====== 期刊权重 (影响因子参考) ======
JOURNAL_WEIGHTS = {
    "CMAME": 6.5,
    "IJNME": 3.5,
    "JMPS": 5.5,
    "Computational Mechanics": 4.0,
    "IJSS": 4.5,
    "arXiv": 3.0,  # 预印本基础分
}

# ====== 关键词过滤（计算固体力学相关） ======
KEYWORDS = [
    "computational mechanics", "finite element", "material point method",
    "peridynamics", "phase field", "cohesive zone", "fracture mechanics",
    "isogeometric analysis", "meshfree", "multiscale", "topology optimization",
    "damage mechanics", "plasticity", "contact mechanics", "solid mechanics",
    "numerical simulation", "constitutive model", "discrete element",
    "boundary element", "extended finite element", "XFEM", "FEM",
    "computational solid mechanics", "nonlinear mechanics", "elastoplasticity",
    "crack propagation", "finite deformation", "homogenization",
]

# ====== 每日推送篇数 ======
TOP_N = 5

# ====== Claude API 翻译配置 ======
# 复用当前会话的 API key
TRANSLATION_ENABLED = True
