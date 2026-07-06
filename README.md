# daily-paper-push — 计算固体力学每日前沿文献推送

每天早上 7:00 (北京时间) 自动抓取 arXiv + CMAME + IJNME + JMPS + Computational Mechanics + IJSS 的最新文献，翻译标题和摘要后通过 QQ 邮箱推送。

## 工作原理

- **arXiv API**: 按关键词搜索最新预印本
- **CrossRef API**: 抓取 Elsevier/Springer 期刊最新论文
- **RSS/Atom**: 补充 Wiley (IJNME) 等平台的论文摘要
- **去重**: 自动记录已推送论文，每天推送的都是新论文
- **翻译**: 使用 AI API 翻译标题和摘要为中文
- **云端运行**: 通过 GitHub Actions 定时执行，电脑关机也不影响

## 部署到 GitHub

### 1. 创建 GitHub 仓库并推送代码

**方法 A — 使用 gh CLI（推荐）:**
```bash
# 先安装 gh: https://cli.github.com/
gh auth login
gh repo create daily-paper-push --private --source . --remote origin --push
```

**方法 B — 手动创建:**
1. 打开 https://github.com/new 创建新仓库（建议设为 **Private**）
2. 创建后，在本地执行:
```bash
git remote add origin https://github.com/YOUR_USERNAME/daily-paper-push.git
git push -u origin master
```

### 2. 设置 GitHub Secrets

在仓库的 **Settings → Secrets and variables → Actions** 中添加以下 Secrets:

| Secret 名称 | 说明 | 示例值 |
|------------|------|--------|
| `SMTP_AUTH_CODE` | QQ邮箱授权码 | `poqsytqsltvhcahj` |
| `SENDER_EMAIL` | 发送邮箱 | `328161253@qq.com` |
| `RECIPIENT_EMAIL` | 接收邮箱 | `328161253@qq.com` |
| `TRANSLATE_API_KEY` | (可选) 翻译 API Key | `sk-xxxx` |

### 3. 手动测试

在仓库的 **Actions** 标签页，选择 **Daily Paper Push** workflow，点击 **Run workflow** 手动触发一次测试。

## 禁用本地 Windows 定时任务（重要）

如果之前设置了 Windows Task Scheduler，请禁用以避免重复推送:

```powershell
Unregister-ScheduledTask -TaskName "DailyPaperPush" -Confirm:$false
```

或在 `taskschd.msc` 中找到 "DailyPaperPush" 任务并禁用。

## 本地运行

```bash
pip install feedparser requests
python main.py              # 完整运行（抓取 + 翻译 + 发送）
python main.py --dry-run    # 仅抓取，在浏览器预览（不发送邮件）
python main.py --no-translate  # 跳过翻译（更快）
```
