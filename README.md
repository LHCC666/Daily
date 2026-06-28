# Daily 🛠️

日常工具集合 — 每日新闻推送、文档等。

## 内容

| 目录 | 说明 |
|---|---|
| `daily-news/` | 每日新闻简报（GitHub Actions + Server酱 → 微信推送） |
| `文档/` | 各类文档 |

## 每日新闻

通过 GitHub Actions 每天自动抓取新闻并通过 Server酱推送到微信。

- 配置文件：`daily-news/config.json`（需自行创建，含 SendKey）
- 工作流：`.github/workflows/daily-news.yml`
- 需在仓库 Settings → Secrets 中配置 `SEND_KEY`
