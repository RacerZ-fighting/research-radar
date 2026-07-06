# RUNBOOK

## 1. 目标

这是面向“低管理成本”的操作说明。
默认只保留最少、稳定、可重跑的操作路径。

## 2. 运行前提

### 2.1 环境
- Python 3.10+
- 可用数据库（默认 SQLite）
- 有效的 LLM provider 凭证
- 网络可访问目标 source

### 2.2 首次初始化
```bash
conda activate research-radar
python -m src.cli profile seed-v2
python -m src.cli migrate-tiers
```

## 3. 当前可用命令（基于现有仓库）

### 3.0 Source 配置

Source metadata 统一维护在：

```bash
config/sources.json
```

当前默认 crawl 只会运行满足以下条件的 source：

- `enabled: true`
- `adapter` 属于当前已支持类型：`crawler` / `rss` / `sitemap` / `webpage`
- 对 `adapter: "crawler"`，必须已有对应 crawler class

OpenAI / Anthropic / Brutecat / HackTron / Black Hat / DEF CON / BSidesSF 等已进入集中配置。

当前会实际采集的 source：

- `adapter: "crawler"` 且已有 crawler class
- `adapter: "rss"` 且配置了 `urls.rss` 或 `urls.feed`
- `adapter: "sitemap"` 且配置了 `urls.sitemap`
- `adapter: "webpage"` 且配置了 listing-like URL 与必要 filters

已知 live source 状态：

- 可抓取：OpenAI Blog、Anthropic News、Brutecat、HackTron AI、DEF CON、BSidesSF（AllBSides recording fallback）、PortSwigger
- 官方 parser 已接入：Black Hat Asia 2026、Black Hat USA 2026；crawler 会从官方 schedule shell 发现并抓取 `sessions.json`。当前命令行 requests 可能返回 403，浏览器可见时手动设置 scoped `BLACKHAT_COOKIE` 后再跑；crawler 会用 `curl_cffi` Chrome impersonation fallback。
- 已移除：RSA Conference / RSAC。此前 RainFocus agenda 噪声偏高，当前不再进入集中 source 配置；历史 RSAC artifacts 已归档出展示面。
- browser-use crawler 已接入但需要额外 LLM endpoint：Black Hat Europe 当前仍保留 `BrowserUseConferenceCrawler`；当前本地 `OPENAI_BASE_URL` 指向 `/v1/responses` 时不能直接运行，因为 browser-use `ChatOpenAI` 需要 `/v1/chat/completions` 兼容 endpoint。推荐设置 DashScope `BROWSER_USE_BASE_URL`、独立 `BROWSER_USE_API_KEY` 与 `BROWSER_USE_MODEL=qwen-vl-max` 后再跑。
- 不进入默认 daily refresh：Project Zero。当前环境下官方域名与 Blogspot feed 多个入口会 timeout / SSL / 502，仍可用 `crawl --source project-zero` 手动调试
- 仍被 requests 403 阻断：BSidesSF Sched。当前只用 AllBSides recording fallback。

全量 crawl 遇到单个 source 失败会输出 `Skipped <source>` 并继续处理其他 source。指定 `--source` 时仍会明确失败，便于单源调试。

新增 source 时，先更新 `config/sources.json`；只有需要专用解析逻辑时才新增 crawler class。

RSS source 可直接运行：

```bash
python -m src.cli crawl --source openai-blog
```

Sitemap source 可直接运行：

```bash
python -m src.cli crawl --source anthropic-news
```

Webpage source 可直接运行：

```bash
python -m src.cli crawl --source brutecat
python -m src.cli crawl --source hacktron-ai
```

DEF CON 使用专用 talk parser 抓取公开 speaker/talk 页面，而不是通用 webpage 链接抽取：

```bash
python -m src.cli crawl --source defcon
```

该 crawler 默认先尝试当前年份对应的 DEF CON 届数；如果 speakers 页面未发布或没有 talk 节点，会回退上一届。2026-07-03 实测 DEF CON 34 speakers 页返回 404，因此当前有效抓取目标是 DEF CON 33，Dashboard 会在卡片上显示具体届数。

BSidesSF 当前使用 AllBSides API 作为 talk-recording fallback；官方 Sched 页面仍被 Cloudflare 阻断，暂不引入 browser 依赖：

```bash
python -m src.cli crawl --source bsidessf
```

Black Hat Asia / USA 2026 当前使用官方 schedule parser：

```bash
python -m src.cli crawl --source blackhat-asia
python -m src.cli crawl --source blackhat-usa
```

如果命令行环境返回 HTTP 403，但浏览器可以看到对应 Black Hat schedule 页面，说明浏览器里已有 Cloudflare clearance。不要导出完整浏览器 profile，也不要导出 GA/广告/统计 cookie；通常只需要 `blackhat.com` 作用域下的 `cf_clearance`：

```bash
export BLACKHAT_COOKIE='cf_clearance=...'
python -m src.cli crawl --source blackhat-asia
python -m src.cli crawl --source blackhat-usa
```

Black Hat Europe 2026 schedule 当前未发布，仍使用 browser-use agent 抽取会议 agenda/library 页面：

```bash
# browser-use 需要 chat-completions 兼容 endpoint，不使用 OPENAI_BASE_URL=/v1/responses
export BROWSER_USE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
export BROWSER_USE_API_KEY=...
export BROWSER_USE_MODEL=qwen-vl-max

python -m src.cli crawl --source blackhat-europe
```

如果未设置 `BROWSER_USE_BASE_URL` 且 `OPENAI_BASE_URL` 指向 `/v1/responses`，crawler 会启动前失败并提示配置单独的 browser-use base URL，避免 browser-use 反复请求 `/v1/chat/completions`。
如果 `BROWSER_USE_BASE_URL` 指向 DashScope 这类独立 provider，必须显式设置 `BROWSER_USE_API_KEY`；crawler 不会把主 `OPENAI_API_KEY` 复用到跨 provider 的 browser-use 请求上。

### 3.1 生成日报（不抓取）
```bash
python -m src.cli run --skip-crawl --provider openai --report-type daily
```

推荐的每日刷新入口：

```bash
python -m src.cli daily-refresh --provider openai --request-delay 5
```

默认 crawl scope 是 `daily`：只抓 arXiv 和未标记 `industry-conference` / `daily-disabled` / `unstable-daily` 的 blog-like sources，不跑 NDSS / S&P / CCS / USENIX Security 这类重型会议论文 crawler。需要同步这些会议源时显式使用：

```bash
python -m src.cli daily-refresh --crawl-scope all --provider openai --request-delay 5
```

注意：`--crawl-scope all` 只负责把 T1 conference paper 抓取并 normalize 入库；为了避免一次性对几百到上千篇论文跑 LLM，`daily-refresh` 仍不会自动分析全部 T1 paper。安全四大 paper 的推荐流程是手动抓取/入库后，先跑 `academic-filter`，再对筛出的候选运行 `academic-judge`、`enrich` 和 `academic-labels`。

日报、Dashboard 日期筛选和 `daily-refresh` 默认日期都按配置本地时区解释，默认 `RESEARCH_RADAR_TIMEZONE=Asia/Shanghai`。SQLite 中没有 timezone 的 datetime 会按 UTC 处理后再归入本地日历日。

`daily-refresh` 的 LLM 分析集合包含目标日期条目，也包含本次新抓取/更新的 daily-scope 条目。这样今天才抓到但站点发布日期属于昨天的博客或组织文章，会立即生成中文摘要；Dashboard / 日报候选加载与展示仍按 `published_at` 优先、`created_at` 兜底的日期归属对应日期页。

如果只想重建本地日报，不抓取也不跑 Zotero / CSRankings / LLM academic personalization：

```bash
python -m src.cli daily-refresh --skip-crawl --skip-academic-personalization --request-delay 0
```

### 3.2 生成完整智能分析周报/landscape（不抓取）
```bash
python -m src.cli run --skip-crawl --full --provider anthropic --report-type landscape
```

### 3.3 单独执行关键步骤
```bash
python -m src.cli normalize
python -m src.cli enrich --provider openai
python -m src.cli enrich --provider openai --workers 1 --request-delay 20
python -m src.cli llm-relevance --provider openai --workers 1 --request-delay 20
python -m src.cli academic-filter --zotero-json /path/to/zotero-better-csl.json
python -m src.cli academic-labels --provider openai --request-delay 5
python -m src.cli score
python -m src.cli deep-analyze --provider anthropic
python -m src.cli extract-signals --provider anthropic
python -m src.cli cluster --provider anthropic
python -m src.cli trend --provider anthropic
python -m src.cli detect-gaps
python -m src.cli synthesize --provider anthropic
python -m src.cli report --type daily
python -m src.cli report --type weekly
python -m src.cli report --type landscape
```

当前 enrichment 默认会生成中文 `summary_l1` 和中文详细 `summary_l3`。如果页面或日报仍显示旧英文 excerpt，说明旧 artifact 还没有按 `v2-cn-detailed` 重新 enrichment；重跑 `enrich` 后会补齐 `summary_l3`。

当前 arXiv 从 `config/sources.json` 读取 `params.categories` 与 `params.max_results`；默认 `max_results=30`，并按 category 分开查询、去重，用于每日小批量前沿入口，避免一次组合 OR 查询触发 429 / timeout，也避免一次抓取 2000 条导致运行过重。

Academic 展示过滤可以先运行：

```bash
python -m src.cli academic-filter --zotero-json /path/to/zotero-better-csl.json
```

也可以通过 Zotero API 环境变量运行：

```bash
ZOTERO_USER_ID=123456 ZOTERO_API_KEY=... python -m src.cli academic-filter
```

如果使用本机 Zotero Local API，先在 Zotero Desktop 里开启本地 API，再设置：

```bash
ZOTERO_API_BASE_URL=http://127.0.0.1:23119/api
ZOTERO_USER_ID=0
```

`academic-filter` 会把 `zotero_similarity`、`zotero_matches`、`academic_quality_score` 和 CSRankings 命中证据写入 `Artifact.score_breakdown`。这些字段用于候选召回和提供 LLM 裁判证据；已经运行过 `academic-filter` 但尚未运行 `academic-judge` 的 academic artifact 默认不展示。已评估 arXiv 的 CSRankings 质量分不足仍会隐藏。

Zotero API 默认最多读取 `ZOTERO_MAX_ITEMS=2000` 条，可通过环境变量调大或调小。当前相关度第一步仍会保留 top 5 Zotero evidence，但最终可继续运行 LLM 裁判：

```bash
python -m src.cli academic-judge --provider openai --request-delay 5
```

`academic-judge` 会让 LLM 基于候选论文和 top-k Zotero evidence 判断是否真的相关，并写入 `academic_relevance_judged`、`academic_relevance_relevant`、`academic_relevance_score` 和中文理由。已有 LLM 裁判结果时，Web/Daily 展示过滤以该结果为准，不再用 `zotero_similarity >= 0.18` 作为相关度门槛。

T1 conference paper 的展示更严格：NDSS / IEEE S&P / ACM CCS / USENIX Security 论文必须先完成 `academic-judge` 才会进入 Web/Daily。这样可以先把安全四大 corpus 入库，但只展示经 Zotero evidence + LLM 判断后确实相关的论文。

安全四大手动恢复/更新示例：

```bash
python -m src.cli crawl --source ndss --years 2026
python -m src.cli crawl --source sp --years 2026
python -m src.cli crawl --source ccs --years 2025
python -m src.cli crawl --source usenix-security --years 2026
python -m src.cli normalize --input-dir data/raw --recursive
python -m src.cli academic-filter

# 再对筛出的候选逐篇或小批量运行：
python -m src.cli academic-judge --artifact-id <id> --provider openai
python -m src.cli enrich --artifact-id <id> --provider openai --workers 1
python -m src.cli academic-labels --artifact-id <id> --provider openai
python -m src.cli score
```

2026-07-06 实测：NDSS 2026、IEEE S&P 2026、USENIX Security 2026 可抓；ACM CCS 2026 官方页和 DBLP 均未公开。按当前策略，不使用 ACM CCS 2025 顶替 2026，CCS 2026 未公开时保持为空。

如果希望 paper 卡片展示更具体的研究焦点，而不是原始 arXiv / Zotero 大类标签，继续运行：

```bash
python -m src.cli academic-labels --provider openai --request-delay 5
```

默认只处理当前通过展示过滤的 academic artifact，并把 `academic_focus_labels` 写入 `Artifact.score_breakdown`。Web Console 会优先展示这些 AI 凝练标签，例如“fuzzing 调度策略”“工具调用约束防护”；相关度 chip 来自 `academic-judge` 的 LLM 裁判结果，不再展示无信息量的 `Zotero match`。

### 3.4 本地 Web Console

本地操作台用于查看近期结果、管理集中 source 配置、测试单个 source，并手动触发小范围 pipeline。它复用现有 SQLite、`config/sources.json` 和 CLI pipeline，不是第二套 orchestrator。

```bash
python -m src.cli web
```

默认地址：

```text
http://127.0.0.1:8000
```

可选端口：

```bash
python -m src.cli web --host 127.0.0.1 --port 8010
```

页面能力：

- Dashboard：查看近期 artifacts、academic / industry 分组；支持 `q=<keyword>` 在当前日期范围内搜索卡片，空搜索展示默认视图
- Dashboard `Refresh today`：默认抓取 daily source scope（arXiv + daily-enabled blog-like sources），然后只对目标日期相关 artifacts 重跑摘要、相关度、个性化学术证据、评分和日报；如需禁用 Web 抓取，可设置 `WEB_DAILY_REFRESH_SKIP_CRAWL=true`
- Sources：新增 source、启用/停用、测试抓取；新建 source 默认 `enabled=false`
- Runs：手动触发单 source crawl、normalize、单条 enrich、score、daily report
- Artifacts：从 SQLite artifact 表读取，按时间倒序分页浏览；支持 `track=all|academic|industry&page=N` 和 `q=<keyword>` 搜索，空搜索默认展示当前 track 的全部 displayable artifacts

注意：

- Web Console 默认只适合本机使用；不要直接暴露到公网。
- Source 管理会写回 `config/sources.json`。
- 单条 enrich 依赖 `.env` 中的 LLM provider 配置；限流网关建议在页面中设置 request delay。

## 4. 推荐运行节奏

### Daily
目标：产出日报。
当前最稳妥方式：
```bash
python -m src.cli run --skip-crawl --provider openai --report-type daily
```

### Weekly
目标：产出 full intelligence 输出。
当前最稳妥方式：
```bash
python -m src.cli run --skip-crawl --full --provider anthropic --report-type landscape
```

### Monthly / Quarterly
当前仍是目标能力。
在实现对应 report generator 前，不要伪造“月报/季报”操作路径。

## 5. 安全重跑原则

如果怀疑某一步失败，可优先直接重跑整条链，而不是手改数据库。

原因：
- RawFetch + content_hash
- canonical_id upsert
- append-only feedback
- 报表可重生成

除非明确要做数据修复，不要直接改 SQLite 内容。

## 6. 常见故障与处理

### 6.1 crawl 失败
现象：
- 站点模板变了
- 网络失败
- 只有部分 source 成功

处理：
- 先记录失败 source
- 不要阻塞整个仓库重定位工作
- 若是 parser 漂移，开一个独立 source 修复工单
- 若只是临时网络失败，保留重跑
- 若是 Black Hat 这类稳定 403，不要把它当作 parser bug；改用替代抓取策略后再启用稳定验证

### 6.2 enrich / deep-analyze / llm-relevance 失败
现象：
- LLM provider 失败
- timeout
- 单条内容解析失败

处理：
- 优先利用现有 parallel + isolated failure 机制
- 检查 provider 配置
- 保持单条失败不阻塞全批次
- 不要为单条失败回滚整次 run

OpenAI-compatible streaming gateway:

如果网关只支持 `/v1/responses` 且强制 streaming，可在 `.env` 中配置：

```bash
OPENAI_BASE_URL=http://your-gateway/v1/responses
OPENAI_MODEL_FAST=gpt-5.4
OPENAI_MODEL_STANDARD=gpt-5.4
OPENAI_MODEL_PREMIUM=gpt-5.4
OPENAI_INPUT_AS_LIST=true
OPENAI_STREAM=true
OPENAI_STORE=false
OPENAI_OMIT_GENERATION_PARAMS=true
```

该模式会使用 Responses SSE 事件解析 `response.output_text.delta`，并避免发送网关不支持的 `temperature` / `max_output_tokens` 参数。

如果网关对批量请求限流，使用：

```bash
python -m src.cli enrich --provider openai --workers 1 --request-delay 20
python -m src.cli llm-relevance --provider openai --workers 1 --request-delay 20
```

`--request-delay` 大于 0 时会强制顺序 enrichment / relevance scoring，并在两次 LLM 请求之间等待指定秒数。

### 6.3 report 为空
先检查：
- 该周期是否有新增内容
- 是否被 read 过滤
- 是否时间窗口问题
- 是否 `created_at` 过滤导致 update-only 内容未进报告

如果确认是策略问题，改 `REPORT_POLICY` + generator；不要先手改数据。

### 6.4 feedback 看起来没有“生效”
这是已知现状：
- 当前 feedback 已采集
- 但尚未成为排序/triage 回流的强信号

解决方式：
- 走 `RR-007`，而不是临时 patch 某个报表排序

## 7. 与自动化集成的建议

自动化一定要分层：

- daily automation：只跑日报链
- weekly automation：跑 full intelligence
- monthly / quarterly automation：在对应 report generator 落地后再加

不要让一个超长任务同时负责所有周期输出。

当前可用的轻量 daily scheduler：

```bash
python -m src.cli schedule-daily --time 00:10 --provider openai --request-delay 5
```

语义：
- `--time HH:MM` 使用本机本地时间
- 每天到点运行 `daily-refresh`
- 默认会 crawl daily source scope、normalize、enrich、llm-relevance、score、academic personalization，并生成当天 daily Markdown
- 默认 daily source scope 不包含 NDSS / S&P / CCS / USENIX Security；需要时给 scheduler 加 `--crawl-scope all`
- 如果调试或由外部 supervisor 托管，可先跑一次后退出：

```bash
python -m src.cli schedule-daily --run-now --once --skip-crawl --skip-academic-personalization --request-delay 0
```

如果使用 launchd / cron / systemd，更推荐调度 `daily-refresh` 一次性命令，而不是让多个 `schedule-daily` 进程同时常驻。

## 8. 操作红线

- 不要手工删 report 来“假装刷新状态”
- 不要手工改 artifact score 纠偏
- 不要在生产数据上做试验性 schema 改动
- 不要在未更新 `CURRENT_STATUS.md` 的情况下 merge 行为变化

## 9. 每次变更操作路径后必须同步更新

- `docs/CURRENT_STATUS.md`
- `docs/RUNBOOK.md`
- `README.md`
