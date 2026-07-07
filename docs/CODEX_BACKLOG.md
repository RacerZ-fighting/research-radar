# CODEX_BACKLOG

> 这是面向 Codex 的连续开发队列。
> 默认一次只做一张票；做完必须更新 `docs/CURRENT_STATUS.md` 和本文件。
> 如果任务与本文件冲突，以本文件的任务定义为准，再回写其它文档。

## 使用规则

- 状态只允许：`todo` / `in_progress` / `blocked` / `done`
- 每张票必须写明依赖、涉及模块、验收标准
- 一次只做一张票
- 若需要人工 review，PR 标题加 `[Needs human review]`
- 先做文档与 triage，再做 source expansion
- 每完成一张票，必须同步更新：
  - `docs/CURRENT_STATUS.md`
  - `docs/CODEX_BACKLOG.md`
  - 以及被行为变化影响到的 policy / runbook / README

## 票据总览

| ID | 标题 | 状态 | 依赖 | Review |
|---|---|---|---|---|
| RR-001 | 仓库重定位与单一文档入口 | done | - | Codex can do directly |
| RR-002 | 多层摘要与 delegate briefing 落位 | todo | RR-001 | Needs human review before merge |
| RR-003 | Triage 引擎与 bucket 分类 | todo | RR-001, RR-002 | Needs human review before merge |
| RR-004 | 日报重构为分层消费视图 | todo | RR-003 | Needs human review before merge |
| RR-005 | 周报与 landscape 收敛 | todo | RR-003 | Needs human review before merge |
| RR-006 | 月报与季报生成器 | todo | RR-005 | Needs human review before merge |
| RR-007 | Feedback 回流与 delegate usefulness 记录 | todo | RR-003 | Needs human review before merge |
| RR-008 | Advisory 作为独立 industry feed 接入 | todo | RR-003 | Needs human review before merge |
| RR-009 | 自动化调度脚本与健康检查 | todo | RR-004, RR-005 | Needs human review before merge |
| RR-010 | Source expansion phase 2（额外博客 / T4 / 可选 SE 轨） | todo | RR-008 | Needs human review before merge |
| RR-011 | Zotero 相似检索与 agent 相关度裁判 | todo | RR-001 | Needs human review before merge |
| RR-012 | arXiv 质量证据与宁缺毋滥筛选 | todo | RR-011 | Needs human review before merge |
| RR-013 | Source 配置集中管理 | done | RR-001 | Needs human review before merge |
| RR-014 | 配置驱动 RSS ingest | done | RR-013 | Needs human review before merge |
| RR-015 | 配置驱动 sitemap ingest | done | RR-013 | Needs human review before merge |
| RR-016 | 配置驱动 webpage ingest 与 live source smoke | done | RR-013 | Needs human review before merge |
| RR-017 | 日报展示 AI 摘要与关键词 | done | RR-014, RR-015, RR-016 | Codex can do directly |
| RR-018 | OpenAI-compatible streaming gateway 配置 | done | RR-017 | Codex can do directly |
| RR-019 | Local Web Console | done | RR-013, RR-017 | Needs human review before merge |
| RR-020 | 中文详细内容总结 | done | RR-017, RR-019 | Needs human review before merge |
| RR-021 | Industry Dashboard 子板块拆分 | done | RR-019 | Codex can do directly |
| RR-022 | Anthropic sitemap 详情页正文可见性修复 | done | RR-015, RR-020 | Codex can do directly |
| RR-023 | 低相关展示过滤与 arXiv 小批量呈现 | done | RR-012, RR-019, RR-022 | Needs human review before merge |
| RR-024 | Academic 论文详细呈现到 Daily/Weekly | todo | RR-023 | Needs human review before merge |
| RR-025 | Artifact 浏览按时间分页 | done | RR-019, RR-023 | Codex can do directly |
| RR-026 | Dashboard 双列比例与时间排序修正 | done | RR-019, RR-025 | Codex can do directly |
| RR-027 | Academic Zotero/CSRankings 首轮过滤 | done | RR-011, RR-012, RR-023 | Needs human review before merge |
| RR-028 | Academic evidence chips 展示 | done | RR-027 | Needs human review before merge |
| RR-029 | Academic AI focus labels | done | RR-028 | Needs human review before merge |
| RR-030 | Paper 卡片摘要与 Zotero keyword 收敛 | done | RR-029 | Codex can do directly |
| RR-031 | Paper 摘要展示回调与 Zotero top-k 诊断 | done | RR-030 | Codex can do directly |
| RR-032 | Zotero 全量读取与 LLM 相关度裁判 | done | RR-031 | Needs human review before merge |
| RR-033 | Academic evidence chip 语义收敛 | done | RR-032 | Codex can do directly |
| RR-034 | Web Console Kami 视觉主题化 | done | RR-019, RR-033 | Codex can do directly |
| RR-035 | Dashboard 博客日期筛选 | done | RR-019, RR-034 | Codex can do directly |
| RR-036 | Dashboard arXiv 日期筛选 | done | RR-035 | Codex can do directly |
| RR-037 | Daily Markdown 日期视图与每日自动刷新 | done | RR-036 | Codex can do directly |
| RR-038 | Dashboard 当天手动刷新入口 | done | RR-037 | Codex can do directly |
| RR-039 | 日常 crawl scope 与 Dashboard refresh 进度 | done | RR-038 | Codex can do directly |
| RR-040 | Dashboard refresh 当天抓取与目标分析 | done | RR-039 | Codex can do directly |
| RR-041 | Dashboard crawl 进度与 fail-fast | done | RR-040 | Codex can do directly |
| RR-042 | Daily source fetch 稳定性修复 | done | RR-041 | Codex can do directly |
| RR-043 | Daily/Dashboard 本地日期边界修复 | done | RR-042 | Codex can do directly |
| RR-044 | Daily refresh 新抓取旧发布日期分析修复 | done | RR-043 | Codex can do directly |
| RR-045 | Web Console sidebar 折叠 | done | RR-034 | Codex can do directly |
| RR-046 | Dashboard 日期范围切换 | done | RR-036 | Codex can do directly |
| RR-047 | Industry conference agenda ingest 第一阶段 | done | RR-021 | Needs human review before merge |
| RR-048 | BSidesSF talk-recording fallback ingest | done | RR-047 | Needs human review before merge |
| RR-049 | Browser-use conference crawler for Black Hat / RSAC | done | RR-047 | Needs human review before merge |
| RR-050 | Browser-use DashScope qwen-vl-max 配置收敛 | done | RR-049 | Codex can do directly |
| RR-051 | Black Hat Asia 官方 schedule parser | done | RR-049 | Needs human review before merge |
| RR-052 | Black Hat USA 官方 schedule parser 与 RSAC agenda 探测 | done | RR-051 | Needs human review before merge |
| RR-053 | RSAC source 移除与历史数据归档 | done | RR-052 | Codex can do directly |
| RR-054 | 未分析会议条目展示过滤 | done | RR-048 | Codex can do directly |
| RR-055 | 安全四大 Paper 恢复与展示 | done | RR-032, RR-036 | Needs human review before merge |
| RR-056 | 安全四大年份收敛与 Artifact 搜索 | done | RR-055 | Codex can do directly |
| RR-057 | Dashboard 搜索框 | done | RR-056 | Codex can do directly |
| RR-058 | Curated research blog RSS expansion | done | RR-057 | Needs human review before merge |
| RR-059 | Dashboard refresh backfill cap and progress | done | RR-058 | Codex can do directly |
| RR-060 | Synacktiv Publications RSS source | done | RR-058 | Needs human review before merge |

---

## RR-060 Synacktiv Publications RSS source
**Why now**  
用户指定 Synacktiv 的 Argo CD / CodeQL RCE 研究文章，希望将 Synacktiv Publications 纳入日常工业界研究博客源。该站点内容偏漏洞研究、利用链分析、云原生安全与逆向，适合进入 curated research blog lane。

**Involved files**
- `config/sources.json`
- `tests/test_source_config.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`
- `docs/RUNBOOK.md`
- `docs/SOURCE_EXPANSION_PLAN.md`

**Do**
1. 确认 Synacktiv Publications 的官方 RSS 入口
2. 复用现有 `RSSFeedCrawler`
3. 不新增 crawler class
4. live smoke 确认 feed 可返回用户指定文章
5. 更新 source config 测试和运行文档

**Done when**
- `synacktiv-publications` 在 `config/sources.json` 中 enabled
- `BLOG_CRAWLER_REGISTRY` 能注册该 RSS source
- `crawl --source synacktiv-publications` 能返回 raw items

**Completed (2026-07-07)**  
- 新增 enabled RSS source `synacktiv-publications`，RSS URL 为 `https://www.synacktiv.com/en/feed/lastblog.xml`。
- live feed smoke 返回 30 条 entries，包含 `Caught in the Octopus Trap: Unauthenticated RCE in Argo CD with CodeQL`。
- 该 RSS 的 `pubDate` 当前为空；Dashboard/date refresh 首次抓取会按 `created_at` 兜底，后续去重依赖 canonical URL。

**Review**  
Needs human review before merge

---

## RR-059 Dashboard refresh backfill cap and progress
**Why now**  
新增多组 RSS blog source 后，用户点击 `Refresh today` 发现进度卡在 45%。实际原因是 daily refresh 会把本次新 normalize 的历史 RSS 条目也纳入 LLM processing，新增源首次抓取会形成较大的 backfill；Dashboard 又只在 enrichment 阶段入口更新一次进度，看起来像卡死。

**Involved files**
- `src/cli/process.py`
- `src/web/app.py`
- `src/pipelines/enrichment.py`
- `src/pipelines/llm_relevance.py`
- `tests/cli/test_commands.py`
- `tests/web/test_web_app.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`

**Do**
1. Dashboard refresh 默认限制一次 LLM target 数量
2. CLI daily-refresh 默认行为保持不变
3. Enrichment / LLM relevance 阶段向进度条报告 item-level progress
4. 新 source backfill 优先处理目标日期和较新的条目

**Done when**
- `/dashboard/refresh-today` 传入 `max_llm_items=30`
- Progress message 能显示当前处理进度和 artifact title
- 测试覆盖 backfill cap 和 Web 参数

**Completed (2026-07-06)**  
- `_run_daily_refresh` 新增可选 `max_llm_items`，Dashboard 默认 30，CLI 默认不限制。
- `_daily_refresh_target_ids` 会按目标日期、新/更新状态、时间戳和 id 排序后再 cap。
- `EnrichmentPipeline` 和 `LLMRelevancePipeline` 支持 `progress_callback`，Dashboard 可显示 `n/total - title`。
- Regression tests 覆盖 Dashboard 参数和 backfill cap。

**Review**  
Codex can do directly

---

## RR-058 Curated research blog RSS expansion
**Why now**  
用户指出博客系统的数据源偏少。当前 daily-safe 日常博客源只有少数几个，Industry 的研究博客 lane 容易缺少足够信号；应优先补高信噪比、结构稳定、可长期维护的 RSS/Atom 源，而不是接泛安全新闻站。

**Involved files**
- `config/sources.json`
- `tests/test_source_config.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`
- `docs/RUNBOOK.md`
- `docs/SOURCE_EXPANSION_PLAN.md`

**Do**
1. 新增 Trail of Bits、Google Online Security Blog、GitHub Blog Security、Assetnote Research、Bishop Fox Blog
2. 全部复用现有 `RSSFeedCrawler`
3. 不新增 crawler class
4. live smoke 确认 feed 可返回有效 entries
5. GitHub Security Lab feed 当前返回 0 entries，先不纳入默认 source
6. 更新 source config 测试和运行文档

**Done when**
- 新 RSS source 在 `config/sources.json` 中 enabled
- `BLOG_CRAWLER_REGISTRY` 能注册新增 RSS source
- 单源 crawl 能返回 raw items
- 测试覆盖新增 RSS source

**Completed (2026-07-06)**  
- 新增 5 个 curated research blog RSS sources：Trail of Bits、Google Online Security Blog、GitHub Blog Security、Assetnote Research、Bishop Fox Blog。
- 这些 source 均走现有 `RSSFeedCrawler`，会进入默认 daily-safe blog-like crawl scope。
- GitHub Security Lab feed 当前可访问但返回 0 entries，暂不接入默认配置。

**Review**  
Needs human review before merge

---

## RR-055 安全四大 Paper 恢复与展示
**Why now**  
Industry conference lane 已经基本可用，Academic lane 目前只剩 arXiv；用户希望开始处理安全四大 paper。当前本地 SQLite 没有 NDSS / IEEE S&P / ACM CCS / USENIX Security active artifacts，因此需要先恢复 T1 corpus 的抓取、入库、个性化分析和 Dashboard 展示闭环。

**Involved files**
- `config/sources.json`
- `src/crawlers/*_crawler.py`
- `src/cli/process.py`
- `src/web/app.py`
- `src/reporting/relevance_filter.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`
- `docs/RUNBOOK.md`

**Do**
1. 确认四大 source 配置、registry 和 crawler 是否仍可用
2. 小范围 live crawl 当前年度四大 paper，避免直接全量多年跑爆
3. normalize 入库并确认 source tier 为 `t1-conference`
4. 对 T1 candidates 运行 Zotero/CSRankings/LLM academic personalization
5. Dashboard Academic lane 展示安全四大近期 paper，并保留 arXiv 日期筛选语义
6. 如果 live source 不稳定，记录具体失败点，不盲目引入第三方镜像

**Done when**
- SQLite 中出现 active `t1-conference` paper artifacts
- Dashboard Academic lane 能展示经过过滤的安全四大 paper
- Paper 卡片有中文摘要、相关度/研究焦点/质量证据 chips
- 文档说明 T1 paper 不属于每日默认 refresh，需显式全量/手动命令

**Completed (2026-07-06)**  
- Live crawl 入库 IEEE S&P 2026 254 篇、NDSS 2026 265 篇、USENIX Security 2026 376 篇、ACM CCS 2025 353 篇；ACM CCS 2026 官方页和 DBLP 当前均返回 404，未使用第三方镜像。
- 运行 `normalize` 后 SQLite 新增 1248 条 `t1-conference` paper artifacts。
- 运行 `academic-filter` 后，对每个会议 Zotero top 6 候选运行 `academic-judge`、`enrich` 和 `academic-labels`，共 24 篇进入展示候选。
- T1 conference paper 必须有 LLM academic judgment 才会进入 Web/Daily；已经 `academic-filter` 但未 judge 的 academic artifact 默认不展示。
- Dashboard Academic lane 使用更宽 paper 候选池，并按来源多样性先覆盖 arXiv / USENIX / S&P / NDSS / CCS，再按分数补满。
- Web smoke 确认 7-day Dashboard 展示 USENIX Security 2026、IEEE S&P 2026、NDSS 2026、ACM CCS 2025，且没有“暂无中文摘要”。

**Review**  
Needs human review before merge

---

## RR-056 安全四大年份收敛与 Artifact 搜索
**Why now**  
用户确认 CCS 不应使用 2025 作为替代，四大 paper 先统一按 2026 处理，没有 2026 公开数据就留空。同时当前 Artifact 浏览缺少关键词搜索，不方便在默认全部展示中按 topic / title / source 快速筛选。

**Involved files**
- `src/web/app.py`
- `src/web/templates/artifacts.html`
- `src/web/static/app.css`
- `tests/web/test_web_app.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`

**Do**
1. 归档当前本地 ACM CCS 2025 T1 paper artifacts
2. 保持 CCS 2026 没有官方/DBLP 数据时不展示 CCS 替代年份
3. Artifact 浏览页增加搜索框
4. 空搜索默认展示全部当前 track 下的 displayable artifacts
5. 搜索命中 title / source / summary / tags / academic focus labels，并保留分页

**Done when**
- Dashboard / Artifacts 不再展示 ACM CCS 2025
- `/artifacts?track=academic` 默认展示全部 displayable academic artifacts
- `/artifacts?track=academic&q=<keyword>` 只展示命中结果
- 测试覆盖搜索过滤和空搜索默认行为

**Completed (2026-07-06)**  
- 本地 353 条 ACM CCS 2025 T1 paper artifacts 已标记为 `archived`，不再进入 Dashboard / Artifacts 展示。
- 保持 CCS 2026 为空：官方页和 DBLP 未公开时不使用旧年份替代。
- Artifact 浏览页新增搜索框，默认空搜索显示当前 track 下全部 displayable artifacts。
- 搜索命中 title / source / summary / tags / academic focus labels，并保留分页参数。
- CSS cache key 更新为 `20260706-artifact-search`。

**Review**  
Codex can do directly

---

## RR-057 Dashboard 搜索框
**Why now**  
用户澄清搜索框应放在 Dashboard 首页，而不是只在 Artifact browser。Dashboard 是每日主入口，需要能在当前日期范围视图中直接按 topic / title / source 快速筛选卡片。

**Involved files**
- `src/web/app.py`
- `src/web/templates/dashboard.html`
- `tests/web/test_web_app.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`
- `docs/RUNBOOK.md`

**Do**
1. Dashboard 支持 `q=<keyword>` 查询参数
2. 空搜索保持当前默认 Dashboard
3. 非空搜索过滤 Dashboard academic / industry 卡片
4. 日期范围控件保留当前搜索词
5. Clear 操作回到当前日期范围的未搜索视图

**Done when**
- `/dashboard?q=fuzzing` 只显示匹配卡片
- `/dashboard?range=7d&q=fuzzing` 同时保留 7-day 与搜索语义
- Dashboard 页面有搜索框
- Web 测试覆盖搜索过滤和默认空搜索

**Completed (2026-07-06)**  
- Dashboard route 新增 `q` 查询参数，并复用 artifact 搜索匹配逻辑。
- Header 增加 Dashboard search form，空搜索保持默认卡片视图。
- Today / 7 days / Custom 日期控件会保留当前搜索词。
- Clear 链接回到当前日期范围的未搜索视图。
- Web 测试覆盖 Dashboard 搜索过滤、空搜索默认视图和范围链接保留 `q`。

**Review**  
Codex can do directly

---

## RR-001 仓库重定位与单一文档入口
**Why now**  
当前最大问题不是缺模块，而是文档入口不统一、定位仍偏旧、README / iteration_plan / handoff 存在漂移。

**Involved files**
- `README.md`
- `AGENTS.md`
- `docs/CURRENT_STATUS.md`
- `docs/PRODUCT_BRIEF.md`
- `docs/TARGET_SYSTEM.md`
- `docs/TRIAGE_POLICY.md`
- `docs/REPORT_POLICY.md`
- `docs/RUNBOOK.md`
- `docs/SOURCE_EXPANSION_PLAN.md`
- `.github/pull_request_template.md`

**Do**
1. 建立 `CURRENT_STATUS.md` 作为唯一入口
2. 明确新定位
3. 保留“研究方向发现”但上移层级
4. 给出后续 backlog 基线
5. 让 README 指向 CURRENT_STATUS

**Done when**
- 新文档落库
- README 定位改写
- iteration_plan 被标记为历史/工程记录而非唯一入口
- PR template 强制要求更新文档

**Completed (2026-04-09)**  
- `README.md` 已改写为新定位，并明确 `CURRENT_STATUS` 为唯一入口。
- `docs/iteration_plan.md` 已改成历史/工程记录，不再作为当前优先级入口。
- `.github/pull_request_template.md` 已新增，强制按统一模板填写目标、测试、回滚和文档更新。
- rewrite notes 与明显无用文件已清理，文档集合进一步收敛。

**Review**  
Codex can do directly

---

## RR-034 Web Console Kami 视觉主题化
**Why now**  
用户已经开始实际试用 Web Console，并明确希望前端换成 tw93/Kami 的纸张、墨蓝、serif 层级风格。当前冷灰 SaaS 风格和研究日报阅读场景不够贴合。

**Involved files**
- `src/web/static/app.css`
- `src/web/templates/base.html`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`

**Do**
1. 保留现有 FastAPI / Jinja / 原生 CSS 架构
2. 将全局 token 收敛为 Kami 风格的 parchment / ivory / ink-blue / warm neutral
3. 调整 sidebar、metric、artifact card、chip、button、form、pagination 的视觉层级
4. 保持 dashboard / artifacts / sources / runs 的现有行为不变
5. 更新 CSS cache version，并做 Web smoke / 单测验证

**Done when**
- Dashboard 与 artifact 列表呈现 Kami 风格
- academic / industry 仍分轨展示
- source 管理和 run 控件仍可访问
- Web 测试通过

**Completed (2026-07-02)**  
- Web Console 全局 token 已切换为 Kami 风格的 parchment、ivory、ink-blue 和 warm neutral。
- Sidebar、metric、artifact card、chip、button、form、pagination 已统一为纸张式层级和轻阴影。
- CSS cache version 更新为 `20260702-kami-theme`，测试断言同步。
- `dashboard` / `artifacts` / `sources` / `runs` route smoke 通过；当前环境未安装 Playwright，未做截图验证。

**Review**  
Codex can do directly

---

## RR-035 Dashboard 博客日期筛选
**Why now**  
用户希望 dashboard 可以通过日期按钮查看当天最新博客，但安全四大论文与业界会议 topic 不应被当天日期卡住。

**Involved files**
- `src/web/app.py`
- `src/web/templates/dashboard.html`
- `src/web/static/app.css`
- `tests/web/test_web_app.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`

**Do**
1. Dashboard 支持 `date=YYYY-MM-DD` 查询参数
2. 默认日期为当天
3. 只对 Research blogs 与 Organizations 两个博客类板块应用日期筛选
4. Academic paper lane 与 Industry conferences lane 保持近期排序，不受日期筛选影响
5. 增加测试覆盖日期筛选与保留会议项

**Done when**
- Dashboard header 有日期控件
- 选择日期后博客板块只显示该日条目
- 安全四大/academic 与业界会议不被该日期过滤
- Web 测试通过

**Completed (2026-07-02)**  
- Dashboard 支持 `date=YYYY-MM-DD` 查询参数，缺省为当天。
- Header 增加日期输入、`Show day` 和 `Today` 控件。
- Research blogs 与 Organizations 按所选日期筛选。
- Academic paper lane 与 Industry conferences lane 保持近期排序，不受日期筛选影响。
- Web 测试和 route smoke 通过。

**Review**  
Codex can do directly

---

## RR-036 Dashboard arXiv 日期筛选
**Why now**  
用户确认 arXiv 也应该跟 dashboard 日期控件联动，但安全四大顶会论文仍需要保留近期视图，避免因为当天没有顶会更新而空掉。

**Involved files**
- `src/web/app.py`
- `src/web/templates/dashboard.html`
- `tests/web/test_web_app.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`

**Do**
1. 复用 `date=YYYY-MM-DD` 查询参数
2. 对 T2 arXiv paper 应用日期筛选
3. 对 T1 conference paper 不应用日期筛选
4. 日期控件文案从 `Blog date` 改为更通用的 `Daily date`
5. 增加测试覆盖 arXiv 被筛选、USENIX 等顶会论文保留

**Done when**
- 选择日期后 arXiv lane 只显示该日 arXiv 条目
- 安全四大顶会论文仍按近期排序展示
- 博客和组织更新继续按日期筛选
- Web 测试通过

**Completed (2026-07-02)**  
- Dashboard academic lane 现在会对 T2 arXiv paper 应用所选日期筛选。
- T1 conference paper 不应用日期筛选，继续保留近期排序结果。
- 日期控件文案从 `Blog date` 改为 `Daily date`。
- 博客和组织更新继续按日期筛选，业界会议不受影响。
- Web 测试和 route smoke 通过。

**Review**  
Codex can do directly

---

## RR-037 Daily Markdown 日期视图与每日自动刷新
**Why now**  
Web Dashboard 已经按日期展示 blogs / organizations / arXiv，并保留顶会与工业会议近期视图。Markdown 日报和自动化入口还没有对齐，无法做到每天自动刷新当天消息。

**Involved files**
- `src/reporting/daily.py`
- `src/cli/process.py`
- `src/cli/main.py`
- `tests/reporting/test_daily.py`
- `tests/cli/test_commands.py`
- `README.md`
- `docs/RUNBOOK.md`
- `docs/REPORT_POLICY.md`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`

**Do**
1. Daily Markdown 按目标日期展示普通博客、组织更新、arXiv
2. Daily Markdown 保留近期工业会议 topic 与顶会论文动态提示
3. 新增一次性 `daily-refresh` 命令
4. 新增长期运行的 `schedule-daily` 命令
5. 自动刷新命令支持 request delay、skip crawl、跳过 academic personalization

**Done when**
- Markdown 日报与 Dashboard 的日期视图语义一致
- `daily-refresh` 可以手动刷新当天日报
- `schedule-daily --time HH:MM` 可以每天自动运行
- 空 raw 目录不会让自动日报失败
- 相关测试通过

**Completed (2026-07-02)**  
- Daily Markdown 新增 `今日组织更新`、`今日 arXiv`、`近期工业会议 topic` 分区。
- `今日博客推荐` 现在只取目标日期当天普通研究博客，组织和工业会议不混入该列表。
- `daily-refresh` 跑 crawl / normalize / enrich / llm-relevance / score / academic personalization / daily report。
- `schedule-daily` 支持 `--time HH:MM`、`--run-now`、`--once`，可作为轻量长期进程。
- 自动日报在没有 raw JSON 时会跳过 normalize 并继续生成报告。
- Reporting 与 CLI 测试通过。

**Review**  
Codex can do directly

---

## RR-038 Dashboard 当天手动刷新入口
**Why now**  
用户已经有按日期查看当天内容的 Dashboard，也有 CLI 级别的 `daily-refresh`。Dashboard 顶部仍显示 `Run pipeline` 和 `Manage sources`，既占空间又不能直接完成“刷新今天”的任务。

**Involved files**
- `src/web/app.py`
- `src/web/templates/dashboard.html`
- `src/web/static/app.css`
- `tests/web/test_web_app.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`

**Do**
1. 将 Dashboard header 的 `Run pipeline` 替换为 `Refresh today`
2. 从 Dashboard header 移除 `Manage sources`
3. `Refresh today` 默认触发轻量 daily refresh，并返回当天日期视图
4. 修正 header action 和日期表单的对齐，避免按钮被撑高
5. 增加 Web route 测试

**Done when**
- Dashboard 顶部只保留日期控件和 `Refresh today`
- 点击刷新后会启动当天轻量 daily refresh
- 页面重定向回 `/dashboard?date=今天`
- Web 测试通过

**Completed (2026-07-02)**  
- Dashboard header 已移除 `Run pipeline` 和 `Manage sources`。
- 新增 `Refresh today` POST 按钮，后台调用轻量 `daily-refresh` 链路，默认不做全量 crawl。
- 刷新动作完成提交后会回到当天日期视图并显示 notice。
- Header action 底部对齐，避免按钮被日期控件高度撑大。
- Web 测试通过。

**Review**  
Codex can do directly

---

## RR-039 日常 crawl scope 与 Dashboard refresh 进度
**Why now**  
用户点击 Dashboard refresh 后发现后台进入 NDSS accepted papers 大量详情页抓取。日常刷新应面向当天博客、组织更新和 arXiv，而不是默认同步安全四大会议全量论文页；同时 Dashboard 需要展示真实运行进度，而不是只显示静态 notice。

**Involved files**
- `src/cli/crawl.py`
- `src/cli/process.py`
- `src/web/app.py`
- `src/web/templates/base.html`
- `src/web/templates/dashboard.html`
- `src/web/static/app.css`
- `tests/cli/test_commands.py`
- `tests/web/test_web_app.py`
- `README.md`
- `docs/RUNBOOK.md`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`

**Do**
1. 新增 daily crawl scope，只抓 arXiv 与 blog/webpage 类日常源
2. `daily-refresh` / `schedule-daily` 默认使用 daily crawl scope
3. 保留 `--crawl-scope all` 以显式同步 NDSS / S&P / CCS / USENIX Security
4. Dashboard refresh 暴露轻量状态 API
5. Dashboard 展示 refresh 阶段、百分比和最后消息，并在运行中禁用按钮

**Done when**
- 默认 `daily-refresh` 不会跑 NDSS 等重型会议 paper crawler
- 需要全量会议同步时仍可显式开启
- Dashboard refresh 页面能看到实时阶段进度
- CLI 与 Web 测试通过

**Completed (2026-07-02)**  
- 新增 `_crawl_daily_sources()`，默认只跑 arXiv paper crawler 和 blog registry。
- `daily-refresh` / `schedule-daily` 新增 `--crawl-scope daily|all`，默认 `daily`。
- Dashboard 新增内存态 refresh status store 与 `/dashboard/refresh-status`。
- Dashboard 增加 Kami 风格进度条，轮询显示 queued / crawl / normalize / enrich / relevance / score / report / complete。
- 测试覆盖 daily scope 排除 NDSS、Dashboard 状态 API 和进度条标记。

**Review**  
Codex can do directly

---

## RR-040 Dashboard refresh 当天抓取与目标分析
**Why now**  
用户指出 Dashboard refresh 不能只处理已有 raw，它应该抓取并分析当天数据。但它也不能重新进入 NDSS 等重型会议 crawler，或顺手补全历史缺摘要队列。

**Involved files**
- `src/cli/process.py`
- `src/web/app.py`
- `tests/cli/test_commands.py`
- `tests/web/test_web_app.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`
- `docs/RUNBOOK.md`

**Do**
1. Dashboard refresh 默认执行 daily source crawl
2. 保持 daily crawl scope，不跑安全四大会议 crawler
3. enrichment / LLM relevance / academic personalization 只处理目标日期相关 artifacts
4. 避免 refresh 顺手补全历史缺摘要队列
5. 增加测试覆盖目标日期过滤

**Done when**
- 点击 Dashboard refresh 会抓取 arXiv + daily-enabled blog-like sources
- 不会抓 NDSS / S&P / CCS / USENIX Security
- LLM 分析只面向目标日期相关 artifacts
- Web 与 CLI 测试通过

**Completed (2026-07-02)**  
- Dashboard `_run_daily_refresh` 调用默认 `skip_crawl=false`、`crawl_scope=daily`、`artifact_scope=daily`。
- `_run_daily_refresh` 新增 daily target selection，只把目标日期相关 arXiv/blog artifacts 送入 LLM enrichment、LLM relevance 和 academic personalization。
- 旧日期 raw 可以 normalize 入库，但不会在当天 refresh 中触发 LLM 分析。
- 测试覆盖 Dashboard 参数、daily target selection 和历史 raw 不触发 LLM。

**Review**  
Codex can do directly

---

## RR-041 Dashboard crawl 进度与 fail-fast
**Why now**  
用户点击 Dashboard refresh 后进度停在 10%。日志显示 arXiv 被 429 / timeout，Project Zero 也出现 read timeout retry。问题不是任务没跑，而是 crawl 阶段没有逐 source 进度，并且交互式刷新对单个慢源等待过久。

**Involved files**
- `src/cli/crawl.py`
- `src/cli/process.py`
- `tests/cli/test_commands.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`

**Do**
1. daily crawl 排除 `industry-conference` webpage 源
2. Dashboard refresh crawl 阶段逐 source 更新进度消息
3. Dashboard refresh 对单源使用更短 timeout 和 0 retry
4. CLI 普通 daily refresh 保持原有较耐心的 retry 行为
5. 增加测试覆盖具体 source 进度消息

**Done when**
- Dashboard 不再长期显示模糊的 10%
- 单个源超时或 429 会快速跳过并继续
- daily scope 仍包含 arXiv 和普通研究博客/组织博客
- 测试通过

**Completed (2026-07-02)**  
- `_crawl_daily_sources()` 支持 `progress` 和 `fail_fast` 参数。
- Dashboard refresh 传入 progress callback，因此 crawl 阶段会显示 `Crawling <source> (i/n)`。
- fail-fast 模式将 crawler timeout 限到 5 秒，并设置 `max_retries=0`。
- daily blog source scope 排除 `industry-conference` 标签源，避免 Black Hat / DEF CON / RSAC / BSidesSF 进入日常按钮。
- 测试覆盖 arXiv + OpenAI daily source 顺序与进度消息。

**Review**  
Codex can do directly

---

## RR-042 Daily source fetch 稳定性修复
**Why now**  
用户指出 refresh 卡住的根因仍是数据源 fetch 不稳定，而不是单纯缺进度条。live 排查显示 arXiv 组合 OR 查询容易触发 429 / timeout，Project Zero 在当前网络环境下官方域名与 Blogspot feed 多个入口均不稳定。

**Involved files**
- `src/crawlers/arxiv_crawler.py`
- `src/cli/crawl.py`
- `config/sources.json`
- `tests/crawlers/test_arxiv_crawler.py`
- `tests/cli/test_commands.py`
- `tests/test_source_config.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`
- `docs/RUNBOOK.md`
- `docs/SOURCE_EXPANSION_PLAN.md`
- `docs/design/05_source_plan.md`

**Do**
1. arXiv 不再使用 `(cat:a OR cat:b OR cat:c)` 单次大查询
2. arXiv 按配置 category 分开小批量抓取并按 arXiv ID 去重
3. arXiv 默认 daily 抓取上限从 100 收敛到 30
4. Project Zero 保留 enabled/manual crawl，但通过 `daily-disabled` 从默认 daily refresh 移出
5. daily source scope 支持排除 `daily-disabled` / `unstable-daily` 标签
6. 更新测试和文档说明当前稳定性策略

**Done when**
- arXiv 多 category fetch 不再生成 OR 查询
- 跨 category 重复论文不会重复返回
- Dashboard / daily refresh 默认不再调用 Project Zero
- source config 测试锁定 arXiv=30 与 Project Zero daily 排除标记
- 相关测试通过

**Completed (2026-07-02)**  
- `ArxivCrawler` 改为逐 category 查询，单 category 结果按 `arxiv_id` / URL / title 去重。
- `config/sources.json` 将 arXiv `params.max_results` 改为 30，降低 daily 请求量。
- Project Zero 增加 `daily-disabled` tag，仍可通过显式 `crawl --source project-zero` 手动抓取。
- `_daily_blog_source_slugs()` 排除 `industry-conference`、`daily-disabled` 和 `unstable-daily` 标签。
- 新增 arXiv crawler 单测，覆盖分 category 查询和跨列表去重。

**Review**  
Codex can do directly

---

## RR-043 Daily/Dashboard 本地日期边界修复
**Why now**  
用户看到 Dashboard refresh 完成并生成 `2026-07-02.md`，但 Dashboard 与日报都没有展示条目。排查发现 2026-07-02 入库了 24 篇 arXiv，其中多篇发布时间为 2026-07-01 16:00 UTC 之后，在 Asia/Shanghai 已经属于 2026-07-02；旧代码直接用 UTC/naive `.date()` 比较，导致本地 7 月 2 日凌晨发布的 arXiv 被归到 7 月 1 日。

**Involved files**
- `src/timezone.py`
- `src/reporting/base.py`
- `src/reporting/daily.py`
- `src/web/app.py`
- `src/cli/main.py`
- `src/cli/process.py`
- `src/cli/crawl.py`
- `src/web/source_admin.py`
- `tests/reporting/test_daily.py`
- `tests/web/test_web_app.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`

**Do**
1. 新增统一的 configured local timezone helper，默认 `Asia/Shanghai`
2. 将 naive SQLite datetime 视为 UTC，再转成本地日期比较
3. Daily report 的 day range 使用本地日历日对应的 UTC 窗口
4. Dashboard / Daily report / daily-refresh target selection 共享本地日期判断
5. CLI 默认日期和 Web 默认日期改成本地日期
6. 增加 UTC evening arXiv 归入下一本地日的回归测试

**Done when**
- UTC 2026-07-01 17:xx 发布的 arXiv 能出现在 2026-07-02 Dashboard / Daily
- Dashboard 与 Daily report 的日期语义一致
- `daily-refresh` 不传 `--date` 时使用配置本地日期
- 相关测试通过

**Completed (2026-07-03)**  
- 新增 `src/timezone.py`，默认 `RESEARCH_RADAR_TIMEZONE=Asia/Shanghai`。
- Dashboard、Daily report、daily-refresh target selection 改为用 `local_date()` 判断目标日期。
- Daily report `_day_range()` 改成本地日历日对应 UTC 窗口。
- 重新生成 `data/reports/daily/2026-07-02.md` 后，今日 arXiv 从 0 篇变为 8 篇。
- Web smoke 确认 `/dashboard?date=2026-07-02` 显示 Theoria、All-out Attack、Antaeus 等 arXiv 条目。

**Review**  
Codex can do directly

---

## RR-044 Daily refresh 新抓取旧发布日期分析修复
**Why now**  
用户发现 Anthropic News 详情正文已经抓到，但页面仍显示英文原文片段且没有中文 summary。排查发现该条目在 2026-07-03 抓取入库，但站点发布日期是 2026-07-02；旧 `daily-refresh` 只对目标日期条目做 enrichment / relevance，导致本次新抓到的旧发布日期文章被跳过分析。

**Involved files**
- `src/cli/process.py`
- `src/repositories/artifact_repository.py`
- `src/reporting/base.py`
- `tests/cli/test_commands.py`
- `tests/reporting/test_daily.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`
- `docs/RUNBOOK.md`

**Do**
1. 保持 Dashboard / Daily report 仍按发布日期归属日期页
2. `daily-refresh` 的 LLM 目标集合包含目标日期条目
3. `daily-refresh` 的 LLM 目标集合也包含本次新 normalize/update 的 daily-scope 条目
4. 报告候选加载按 `published_at` 优先、`created_at` 兜底的展示时间取数
5. 增加回归测试覆盖“今天刷新抓到昨天发布的博客会补摘要”，以及延迟抓取博客仍进入发布日期日报

**Done when**
- Anthropic 这类新抓取旧发布日期文章会被立即 enrichment
- 目标日期日报不会混入非目标日期条目
- 相关 CLI 测试通过

**Completed (2026-07-03)**  
- `_daily_refresh_target_ids()` 改为选择 `target_date` 命中项以及本次 `normalized` 命中的 daily-scope 项。
- CLI 回归测试确认旧发布日期的新抓取博客会参与 enrichment / relevance。
- `ArtifactRepository.list_by_date_range()` 和报告缺失评分计数改为使用 `coalesce(published_at, created_at)`。
- Daily report 回归测试确认延迟抓取的博客仍会出现在发布日期对应日报。
- 目标日期日报仍按发布日期归属展示内容。

**Review**  
Codex can do directly

---

## RR-045 Web Console sidebar 折叠
**Why now**  
用户截图显示左侧固定 sidebar 在窄窗口中过宽，压缩 Dashboard 阅读区。当前页面需要保留 Kami 纸张风格，同时让用户在阅读日报时快速收起导航。

**Involved files**
- `src/web/templates/base.html`
- `src/web/static/app.css`
- `tests/web/test_web_app.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`

**Do**
1. 在 sidebar 顶部加入折叠/展开按钮
2. 宽屏折叠后从完整 sidebar 变成窄 rail
3. 折叠态只保留 RR、单字母导航和状态线
4. 使用 `localStorage` 记住折叠状态
5. 移动端保持完整导航，避免小屏布局被半折叠状态破坏

**Done when**
- Dashboard 可以收起 sidebar，主内容区域自动变宽
- 刷新页面后保持用户选择的折叠状态
- Web 测试通过

**Completed (2026-07-03)**  
- Base template 增加 sidebar toggle、折叠状态预加载脚本和持久化脚本。
- CSS 增加 `--sidebar-expanded` / `--sidebar-collapsed` token，宽屏折叠为 76px rail。
- nav 在折叠态显示 `D/S/A/R` 单字母标记，移动端恢复完整文本导航。
- CSS cache version 更新为 `20260703-sidebar-collapse`，Web 测试同步覆盖。

**Review**  
Codex can do directly

---

## RR-046 Dashboard 日期范围切换
**Why now**  
用户明确只需要 Dashboard 支持“只看当天 / 最近 7 天 / 自定义日期”的视图切换，不需要已读、隐藏、稍后看等反馈操作。当前 Dashboard 已有单日 `date` 筛选，扩展为轻量范围选择能提升日常浏览效率。

**Involved files**
- `src/web/app.py`
- `src/web/templates/dashboard.html`
- `src/web/static/app.css`
- `tests/web/test_web_app.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`

**Do**
1. Dashboard 支持 `range=today|7d|custom`
2. 默认 `today`，旧 `?date=YYYY-MM-DD` 兼容为 custom
3. `7d` 只影响日常博客、组织更新和 arXiv
4. 工业会议与 T1 顶会保持近期视图，不被范围筛掉
5. 顶部控件改为 Today / 7 days / Custom 分段切换

**Done when**
- `/dashboard` 展示当天
- `/dashboard?range=7d` 展示近 7 天日常源
- `/dashboard?range=custom&date=YYYY-MM-DD` 展示指定日期
- Web 测试通过

**Completed (2026-07-03)**  
- 新增 `DashboardDateRange`，统一解析 Dashboard 日期范围。
- Dashboard academic / industry daily lanes 改为使用 range 匹配。
- 顶部日期控件改为 Today / 7 days / Custom，并保留旧 `date` URL 兼容。
- CSS cache version 更新为 `20260703-range-selector`。
- Web 测试覆盖 custom 与 7 days 行为。

**Review**  
Codex can do directly

---

## RR-047 Industry conference agenda ingest 第一阶段
**Why now**  
用户希望工业界会议板块不只是空 lane，而是能获取 Black Hat / DEF CON / RSAC / BSidesSF 等会议的相关议题，并像 arXiv 一样做相关度过滤。Live 调研确认 DEF CON 公开 speaker/talk 页面可用 requests 稳定解析；Black Hat、RSAC、BSidesSF Sched 当前 requests 访问存在 403/Cloudflare，先不引入 browser 依赖。

**Involved files**
- `config/sources.json`
- `src/crawlers/defcon_talk_crawler.py`
- `src/crawlers/registry.py`
- `src/crawlers/__init__.py`
- `src/web/app.py`
- `tests/crawlers/test_defcon_talk_crawler.py`
- `tests/test_source_config.py`
- `tests/web/test_web_app.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`
- `docs/RUNBOOK.md`
- `docs/SOURCE_EXPANSION_PLAN.md`
- `docs/design/05_source_plan.md`

**Do**
1. 新增 DEF CON 专用 talk parser，解析 `article.talk` / `.talk-title` / `.abstract` 等结构
2. 将 `defcon` source 从 generic webpage 切到 crawler-backed
3. raw item 继续使用 blog-like artifact 语义，保留 `industry-conference` tag
4. Dashboard conference lane 使用现有 `should_display_artifact()` 过滤低相关内容
5. conference lane 按 `final_score` 优先展示相关议题
6. 修复 Dashboard candidate pool，使没有 `published_at` 但刚抓取的会议 talk 不会被排到候选池外

**Done when**
- `python -m src.cli crawl --source defcon` 可抓到 talk 级条目
- normalize 后 DEF CON talk 能进入 Artifact 表
- enrichment / llm-relevance / score 后 Dashboard 的 Industry conferences lane 显示相关 talk
- daily refresh 仍不默认抓 `industry-conference` 源
- 相关测试通过

**Completed (2026-07-03)**  
- 新增 `DefconTalkCrawler`，默认先尝试当前年份对应的 DEF CON speakers 页面，失败或无 talk 节点时回退上一届；2026-07-03 live check 确认 DEF CON 34 speakers 页为 404，当前有效抓取 DEF CON 33 前 20 条 talk。
- `defcon` source 已改为 `adapter=crawler`、`crawler=defcon`。
- 已对 20 条 DEF CON talk 入库，并补跑中文摘要、LLM relevance 和 scoring。
- Dashboard conference lane 现在能显示 DEF CON 相关议题，卡片会显式标记 `DEF CON 33` 这类届数，并按 `final_score` 优先排序。
- Black Hat / RSAC / BSidesSF Sched 暂不处理，后续需要 browser-backed fetch、官方导出或可信 mirror。

**Review**  
Needs human review before merge

---

## RR-048 BSidesSF talk-recording fallback ingest
**Why now**  
用户要求继续适配 DEF CON 之外的工业界会议。Live check 显示 BSidesSF 官方主站可访问，但 talk 级 schedule 跳转到 `bsidessf2026.sched.com`，当前 requests 抓取被 Cloudflare 403；AllBSides API 可稳定返回 BSidesSF 2026 talk recording 列表，可作为不引入 browser 依赖的 fallback。

**Involved files**
- `config/sources.json`
- `src/crawlers/allbsides_talk_crawler.py`
- `src/crawlers/registry.py`
- `src/crawlers/__init__.py`
- `tests/crawlers/test_allbsides_talk_crawler.py`
- `tests/test_source_config.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`
- `docs/RUNBOOK.md`
- `docs/SOURCE_EXPANSION_PLAN.md`
- `docs/design/05_source_plan.md`

**Do**
1. 新增 AllBSides-backed talk crawler，输出现有 blog-like conference artifact
2. 将 `bsidessf` source 从 generic webpage 切到 crawler-backed fallback
3. 使用 `organizer=bsidessf&year=2026`，避免 `by-event` 端点混入历史热门 talk
4. 保留 `industry-conference` / `security-conference` / `talks` 标签，并增加 `bsidessf-2026`
5. 不引入 browser 依赖，不扩大 daily refresh 默认范围

**Done when**
- `python -m src.cli crawl --source bsidessf` 可抓到 BSidesSF 2026 talk recording 条目
- normalize 后 BSidesSF talk 能进入 Artifact 表
- LLM relevance 可隐藏低相关 career/community 条目
- 相关测试通过

**Completed (2026-07-03)**  
- 新增 `AllBsidesTalkCrawler`，使用 AllBSides API 抓取 BSidesSF 2026 talk recordings。
- `bsidessf` source 已改为 `adapter=crawler`、`crawler=allbsides`，并保留官方 homepage/schedule URL 作为来源说明。
- Live crawl 返回 12 条 BSidesSF 2026 recordings；normalize 创建 12 条 artifact。
- 已对 12 条跑 LLM relevance 和 scoring，其中 1 条 AI coding agent 相关 talk 通过展示过滤，并已补中文摘要。
- Enrichment 现在保留既有 source / conference 结构标签，避免补摘要时把 `industry-conference` 覆盖掉。
- Dashboard conference lane 现在先保留每个会议源的最高分条目，再用剩余高分补齐，避免 DEF CON 把 BSidesSF 完全挤出首页。
- Black Hat、RSAC 与 BSidesSF Sched 仍需 browser-backed、官方导出或其他稳定 API 策略。

**Review**  
Needs human review before merge

---

## RR-049 Browser-use conference crawler for Black Hat / RSAC
**Why now**  
Black Hat USA/Asia/Europe 与 RSAC 的 requests 抓取稳定 403，用户明确要求先做 browser-use，而不是普通 Playwright fallback。需要先把 browser-use 作为会议源 crawler 接进现有 pipeline，再单独处理 LLM endpoint 兼容。

**Involved files**
- `config/sources.json`
- `requirements.txt`
- `.env.example`
- `src/crawlers/browser_use_conference_crawler.py`
- `src/crawlers/registry.py`
- `src/crawlers/__init__.py`
- `tests/crawlers/test_browser_use_conference_crawler.py`
- `tests/test_source_config.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`
- `docs/RUNBOOK.md`
- `docs/SOURCE_EXPANSION_PLAN.md`
- `docs/design/05_source_plan.md`

**Do**
1. 新增 browser-use-backed conference crawler
2. 让 agent 输出固定 JSON，并映射成 blog-like raw items
3. 将 Black Hat USA/Asia/Europe 与 RSAC 从 `webpage` 切到 `crawler=browser-use-conference`
4. 保留 `industry-conference` 标签，避免进入默认 daily refresh
5. 补 browser-use / SOCKS proxy 依赖与配置说明
6. 如果当前 OpenAI endpoint 不支持 browser-use 所需 API，启动前 fail-fast

**Done when**
- Black Hat / RSAC 在 registry 中使用 `BrowserUseConferenceCrawler`
- crawler 能解析 browser-use JSON 输出并保留会议标签
- 当前 Responses-only 网关不会触发长时间 browser-use 重试
- 相关测试通过

**Completed (2026-07-03)**  
- 新增 `BrowserUseConferenceCrawler`，lazy import browser-use，并支持 runner 注入测试。
- Black Hat USA/Asia/Europe 与 RSAC 已切到 `adapter=crawler`、`crawler=browser-use-conference`，配置了 2026 agenda/library target URLs 和 event label。
- `requirements.txt` 增加 `browser-use` 与 `socksio`；当前 venv 已安装 browser-use 0.13.3。
- `.env.example` 增加 `BROWSER_USE_BASE_URL` / `BROWSER_USE_MODEL` / `BROWSER_USE_HEADLESS` / `BROWSER_USE_MAX_FAILURES`。
- Live smoke 确认 browser-use 可启动浏览器并打开 Black Hat Asia 页面；失败点是当前内网 OpenAI gateway 只支持 `/v1/responses`，而 browser-use `ChatOpenAI` 调用 `/v1/chat/completions`。
- crawler 现在会在 `OPENAI_BASE_URL` 指向 `/v1/responses` 且未设置 `BROWSER_USE_BASE_URL` 时 fail-fast，避免 6 轮 agent 重试。

**Review**  
Needs human review before merge

---

## RR-050 Browser-use DashScope qwen-vl-max 配置收敛
**Why now**  
用户决定 browser-use 会议 crawler 先用 `qwen-vl-max`。需要把示例、运行说明和 crawler 默认行为收敛到同一条路径，避免继续误用内网 Responses-only OpenAI 网关或把主 OpenAI key 打到 DashScope。

**Involved files**
- `.env.example`
- `src/crawlers/browser_use_conference_crawler.py`
- `tests/crawlers/test_browser_use_conference_crawler.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`
- `docs/RUNBOOK.md`
- `docs/SOURCE_EXPANSION_PLAN.md`
- `docs/design/05_source_plan.md`

**Do**
1. 将 browser-use 示例配置改为 DashScope compatible endpoint
2. 将推荐模型改为 `qwen-vl-max`
3. DashScope endpoint 下未显式配置 `BROWSER_USE_MODEL` 时默认 `qwen-vl-max`
4. 跨 provider 时不复用主 `OPENAI_API_KEY`，要求独立 `BROWSER_USE_API_KEY`
5. 补充测试和文档说明

**Done when**
- browser-use conference crawler 在 DashScope endpoint 下默认模型为 `qwen-vl-max`
- 跨 provider key 误用有测试覆盖
- runbook 示例可直接指导 Black Hat / RSAC smoke

**Completed (2026-07-03)**  
- `.env.example` 与 `docs/RUNBOOK.md` 已切到 DashScope + `qwen-vl-max` 示例。
- `BrowserUseConferenceCrawler` 现在会在 DashScope endpoint 下默认 `qwen-vl-max`。
- 当 `BROWSER_USE_BASE_URL` 与主 `OPENAI_BASE_URL` host 不一致时，crawler 要求显式 `BROWSER_USE_API_KEY`，不复用主 OpenAI key。
- 单元测试覆盖 DashScope 默认模型和跨 provider key 隔离。

**Review**  
Codex can do directly

---

## RR-051 Black Hat Asia 官方 schedule parser
**Why now**  
用户确认普通浏览器可以直接打开 Black Hat Asia 2026 schedule 页面并看到议题列表。继续依赖 browser-use 或第三方镜像都会降低稳定性；更合理的是优先解析官方 HTML，并在命令行被 Cloudflare 拦截时提供明确的 scoped cookie fallback。

**Involved files**
- `config/sources.json`
- `requirements.txt`
- `.env.example`
- `src/crawlers/blackhat_schedule_crawler.py`
- `src/crawlers/registry.py`
- `src/crawlers/__init__.py`
- `tests/crawlers/test_blackhat_schedule_crawler.py`
- `tests/test_source_config.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`
- `docs/RUNBOOK.md`
- `docs/SOURCE_EXPANSION_PLAN.md`
- `docs/design/05_source_plan.md`

**Do**
1. 新增 Black Hat 官方 schedule parser，优先读取 schedule shell 中的 `sessions.json`
2. 将 `blackhat-asia` 从 `browser-use-conference` 切到 `blackhat-schedule`
3. 解析 title / speaker / contributor / track / format / location / schedule day
4. 过滤茶歇、overflow、注册、expo 等非议题条目
5. 保留 `industry-conference` 与 `official-schedule` 标签
6. requests 被 Cloudflare / 403 拦截时使用 `curl_cffi` Chrome impersonation + scoped `BLACKHAT_COOKIE` fallback

**Done when**
- Black Hat Asia registry 使用 `BlackHatScheduleCrawler`
- parser 单测覆盖官方 schedule JSON、非议题过滤、403 fallback 和 cookie 注入
- live smoke 能从官方 `sessions.json` 抓到议题，或在 cookie 失效时输出明确的 `BLACKHAT_COOKIE` 操作提示

**Completed (2026-07-03)**  
- 新增 `BlackHatScheduleCrawler`，从官方 Black Hat Asia 2026 schedule shell 发现 `sessions.json`，解析 JSON 为 blog-like conference artifact。
- `blackhat-asia` source 配置改为 `crawler=blackhat-schedule`，目标 URL 为 `https://blackhat.com/asia-26/briefings/schedule/index.html`，并配置 Thursday/Friday 日期映射和 `max_results=80`。
- crawler 会跳过 Coffee/Tea Break、Refreshment Break、Overflow Room、Registration、Expo Hall 等非 session 条目，保留 speaker/track/format/location/description 到 excerpt/tags。
- `requirements.txt` 增加 `curl_cffi`；当 requests 返回 403 时，crawler 使用 Chrome impersonation fallback。
- live smoke：只使用 scoped `cf_clearance` 即可抓取官方 `sessions.json`，不需要 GA/广告/统计 cookie；已抓到 53 条有效 Black Hat Asia 2026 议题。
- 已 normalize 入库 53 条 active artifact，补齐中文摘要、LLM relevance 和 final score；旧误入库的 `Briefings Refreshment Break` 已标记为 `rejected`。
- 不自动读取 Chrome profile/cookies，避免扩大本地隐私面；如果要长期自动化，需人工确认 scoped cookie 更新/轮换方式。

**Review**  
Needs human review before merge

---

## RR-052 Black Hat USA 官方 schedule parser 与 RSAC agenda 探测
**Why now**  
Black Hat Asia 已验证官方 schedule shell + `sessions.json` 路线比 browser-use 更稳定。Black Hat USA 2026 页面也已发布同结构 schedule；应优先复用官方 parser。Black Hat Europe 2026 schedule 当前未发布，RSAC 2026 使用 RainFocus 官方 agenda，需要单独确认稳定接口。

**Involved files**
- `config/sources.json`
- `tests/test_source_config.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`
- `docs/RUNBOOK.md`
- `docs/SOURCE_EXPANSION_PLAN.md`
- `docs/design/05_source_plan.md`

**Do**
1. 将 `blackhat-usa` 从 browser-use 切到 `blackhat-schedule`
2. 使用官方 `https://www.blackhat.com/us-26/briefings/schedule/index.html` 与 `sessions.json`
3. 继续使用 scoped `BLACKHAT_COOKIE` + `curl_cffi` fallback
4. 保持 Black Hat Europe 2026 在官方 schedule 发布前不强行切换
5. 探测 RSAC 2026 官方 RainFocus agenda 的稳定抓取入口

**Done when**
- Black Hat USA registry 使用 `BlackHatScheduleCrawler`
- live smoke 能从官方 Black Hat USA `sessions.json` 抓到议题
- docs 明确 USA / Europe / RSAC 三者当前状态差异

**Progress (2026-07-04)**  
- `blackhat-usa` 已从 `browser-use-conference` 切到 `blackhat-schedule`，目标 URL 为官方 `https://www.blackhat.com/us-26/briefings/schedule/index.html`。
- live crawl 从官方 `sessions.json` 抓到 104 条有效 Black Hat USA 2026 议题，并 normalize 入库。
- OpenAI gateway 短暂 502 后恢复；已补齐 104 条 Black Hat USA 中文摘要、LLM relevance 和 final score。
- Black Hat Europe 2026 schedule 当前未发布，保持 browser-use crawler，后续发布后优先复用 `blackhat-schedule`。
- RSAC 2026 官方 Full Agenda 已确认使用 RainFocus widget API；新增 `RSACAgendaCrawler` 并将 `rsac` 切到 `crawler=rsac-agenda`。
- live crawl 从 `events.rsaconference.com/api/sessions` 抓到 160 条有效 RSAC 2026 议题，并 normalize 入库、重跑 score。
- 当前 OpenAI gateway 再次返回 502，RSAC 160 条的中文摘要与 LLM relevance 仍待 gateway 恢复后补跑。

**Completed (2026-07-04)**  
- Source 接入目标已完成：Black Hat USA 和 RSAC 均改为官方数据源，不再依赖 browser-use。
- 剩余工作不是 crawler 阻塞，而是 LLM provider 恢复后补跑 RSAC enrichment / relevance。

**Review**  
Needs human review before merge

---

## RR-053 RSAC source 移除与历史数据归档
**Why now**  
RSAC RainFocus agenda 虽然可抓取，但 session 噪声偏高，进入 Dashboard 后会稀释工业会议技术 topic lane。用户已明确先移除 RSAC 数据源。

**Involved files**
- `config/sources.json`
- `src/web/app.py`
- `src/reporting/daily.py`
- `src/reporting/relevance_filter.py`
- `tests/test_source_config.py`
- `tests/crawlers/test_rsac_agenda_crawler.py`
- `tests/web/test_web_app.py`
- `tests/personalization/test_academic_filter.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`
- `docs/RUNBOOK.md`
- `docs/SOURCE_EXPANSION_PLAN.md`
- `docs/design/05_source_plan.md`
- `README.md`

**Do**
1. 从集中 source 配置删除 `rsac`
2. 从 Dashboard / daily 的会议源提示和 marker 中去掉 RSAC
3. 保留 `RSACAgendaCrawler` 代码与 fixture 测试，但不再由 registry 暴露
4. 归档当前 SQLite 中已有 `RSA Conference` artifacts
5. 更新当前状态与 source 文档，避免后续误判为“待补摘要”工作

**Done when**
- `source_configs_by_slug()` 不再包含 `rsac`
- `BLOG_CRAWLER_REGISTRY` 不再包含 `rsac`
- Dashboard HTML 不再出现 `RSA Conference` / RSAC 条目
- 相关测试通过

**Completed (2026-07-06)**  
- `rsac` 已从 `config/sources.json` 删除，默认 registry 不再注册该 source。
- Dashboard / daily 会议源 marker 与空状态文案已移除 RSAC。
- 共享展示过滤器会隐藏历史 `RSA Conference` artifacts。
- 本地 SQLite 中 160 条 `RSA Conference` artifact 已归档。
- 文档已更新为“RSAC 因噪声过高移除”，不再作为待维护 source。

**Review**  
Codex can do directly

---

## RR-054 未分析会议条目展示过滤
**Why now**  
Dashboard 显示了 `BSidesSF 2026 - More Role Models in AppSec...`，但卡片只有“暂无中文摘要”。排查发现同一 talk 有重复 artifact：已分析版本因 LLM relevance 低被隐藏，未分析 raw 版本缺少摘要和 LLM relevance，却因有 abstract 被会议 lane 放行。

**Involved files**
- `src/reporting/relevance_filter.py`
- `tests/personalization/test_academic_filter.py`
- `tests/web/test_web_app.py`
- `tests/reporting/test_daily.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`

**Do**
1. 工业会议 artifact 只有 raw abstract 时，不进入 Dashboard / Daily 展示
2. 已有中文摘要的会议 artifact 可以展示
3. 已有 LLM relevance 且低于阈值的会议 artifact 继续隐藏
4. 更新 Web / reporting / relevance tests

**Done when**
- 只含 raw abstract 的 BSidesSF 重复条目不再显示
- Dashboard 不再出现未分析会议条目的“暂无中文摘要”卡片
- 相关测试通过

**Completed (2026-07-06)**  
- `should_display_artifact` 现在要求工业会议条目至少有 AI 摘要或 LLM relevance 判断，否则隐藏。
- `id=235` 低相关 BSidesSF talk 与 `id=423` 未分析重复条目均不再展示。
- Dashboard 和 industry artifacts 页面 smoke 确认不再出现该标题。

**Review**  
Codex can do directly

---

## RR-002 多层摘要与 delegate briefing 落位
**Why now**  
没有稳定的多层摘要，就无法做 triage，也无法支持 detailed / delegate 两个消费层。

**Involved files**
- `prompts/summarize_artifact.md`
- `src/pipelines/enrichment.py`
- `src/pipelines/deep_analysis.py`（若需要明确与 `summary_l2` 的职责边界）
- `tests/` 相关 enrichment / pipeline tests
- `docs/TARGET_SYSTEM.md`
- `docs/TRIAGE_POLICY.md`

**Do**
1. 明确 `summary_l1 / summary_l2 / summary_l3` 各自职责
2. 让 `summary_l3` 开始承载 detailed brief / delegate brief
3. 保持 `summary_l2` 继续作为结构化 deep analysis
4. 增加解析与测试覆盖
5. 记录 versioning / fallback 规则

**Done when**
- 生成链路不会覆盖 `summary_l2` 的现有语义
- `summary_l3` 有可测试的生成行为
- triage 所需摘要层级可以直接被 report 使用

**Review**  
Needs human review before merge

**Status note (2026-07-01)**  
用户已确认短期不需要 triage bucket 或 delegate 分层。先用 `RR-017` 做最小有效日报：每条内容展示 AI 生成的 `summary_l1` 和 `tags`。

---

## RR-003 Triage 引擎与 bucket 分类
**Why now**  
没有 triage，引擎只能“算分”，还不能“减少用户注意力成本”。

**Involved files**
- `src/reporting/`（新增 `triage.py` 或等效模块）
- `src/repositories/` 查询辅助（如需要）
- `tests/` triage / report tests
- `docs/TRIAGE_POLICY.md`
- `docs/CURRENT_STATUS.md`

**Do**
1. 先按 track 分流
2. 再派生五类 bucket
3. 接入 read / dislike 等反馈
4. 让同一 artifact 在一个周期只进一个 bucket
5. 把规则写死在 policy + tests 里，而不是口头约定

**Done when**
- `read_original / detailed_summary / one_line / delegate / archive` 可稳定复现
- academic / industry 不混排
- 报表层能直接调用 triage 结果

**Review**  
Needs human review before merge

---

## RR-004 日报重构为分层消费视图
**Why now**  
当前日报主要还是博客推荐，不足以承接“低管理成本”的真实日常使用场景。

**Involved files**
- `src/reporting/daily.py`
- `src/reporting/renderer.py`（如需要）
- `tests/` daily report tests
- `docs/REPORT_POLICY.md`
- `docs/RUNBOOK.md`

**Do**
1. 改成 academic / industry 分区
2. 每个分区内做 triage buckets
3. 保留 advisories 占位
4. 增加 delegate section
5. 保持空 section 可读

**Done when**
- 日报不再只是博客列表
- academic / industry / advisories 结构明确
- 用户可以直接知道“今天该做什么”

**Review**  
Needs human review before merge

---

## RR-005 周报与 landscape 收敛
**Why now**  
weekly 与 landscape 的语义漂移会持续制造维护成本。

**Involved files**
- `src/reporting/weekly.py`
- `src/reporting/landscape.py`
- `src/cli/report.py`
- `src/cli/process.py`
- `tests/` weekly / landscape / cli tests
- `docs/REPORT_POLICY.md`
- `README.md`

**Do**
1. 定义 weekly 为主周报
2. 给 landscape 一个兼容期定位
3. 共享 triage / section policy
4. 明确 CLI 行为
5. 保持向后兼容

**Done when**
- weekly / landscape 不再各自漂移
- 文档、CLI、输出文件命名至少在语义上统一
- 有清晰兼容说明

**Review**  
Needs human review before merge

---

## RR-006 月报与季报生成器
**Why now**  
用户需求已经明确包含月报与季度总结；没有正式 generator，就只能临时拼接。

**Involved files**
- `src/reporting/` 新 generator
- `src/cli/report.py`
- `src/cli/process.py`（若需要）
- `tests/` report / cli tests
- `docs/REPORT_POLICY.md`
- `docs/RUNBOOK.md`

**Do**
1. 增加 monthly generator
2. 增加 quarterly generator
3. 定义输出路径
4. 接入 feedback / source performance / direction changes
5. 补测试与 runbook

**Done when**
- 月报和季报都有稳定 markdown 输出
- 能从 CLI 调起
- 空数据时仍有可读报告

**Review**  
Needs human review before merge

---

## RR-007 Feedback 回流与 delegate usefulness 记录
**Why now**  
feedback 已存在，但还没有真正改变 triage / 阅读推荐。

**Involved files**
- `src/cli/feedback.py`
- `src/feedback/collector.py`
- `src/models/feedback.py`（若只改结构化 content 约定则无需 schema 变更）
- `tests/` feedback tests
- `docs/TRIAGE_POLICY.md`
- `docs/CURRENT_STATUS.md`

**Do**
1. 扩展 feedback 的 target / outcome 语义
2. 增加 delegate useful / useless 的记录约定
3. 让 monthly / quarterly 能消费这些信号
4. 明确哪些反馈只影响 report、哪些将来影响排序

**Done when**
- 已读/喜欢/不喜欢/代读结果都可结构化记录
- 报表里能看到 feedback snapshot
- triage 可以消费最低限度的反馈信号

**Review**  
Needs human review before merge

---

## RR-008 Advisory 作为独立 industry feed 接入
**Why now**  
当前日报已经留了“漏洞速报”占位，下一步最自然的 industry 扩展就是 advisories。

**Involved files**
- `src/crawlers/`
- `src/pipelines/normalization.py`（如需 tier/source 映射）
- `src/scoring/authority.py`
- `src/reporting/daily.py`
- `tests/`
- `docs/SOURCE_EXPANSION_PLAN.md`

**Do**
1. 接入 1 个 advisory source baseline
2. 单独定义 industry 子分区
3. 定义 authority / urgency / dedupe 规则
4. 接入日报 / 周报
5. 保持与 academic 分离

**Done when**
- daily “漏洞速报”不再为空占位
- advisories 不与 academic 混排
- source policy 文档同步

**Review**  
Needs human review before merge

---

## RR-009 自动化调度脚本与健康检查
**Why now**  
用户明确要低维护和自动化；光有 CLI 还不够，需要最小可操作自动化脚手架。

**Involved files**
- `scripts/` 或 `.github/workflows/`
- `docs/RUNBOOK.md`
- `README.md`
- `tests/`（如有脚本层测试）

**Do**
1. 固化 daily / weekly 操作路径
2. 增加最小健康检查
3. 明确失败后的处理方式
4. 保留手动 rerun 路径

**Done when**
- 至少存在稳定的 daily / weekly automation 模板
- runbook 能支持非交互操作
- 失败时知道如何恢复

**Review**  
Needs human review before merge

---

## RR-010 Source expansion phase 2
**Why now**  
只有在 triage 与报表已经稳定后，额外 source 才不会带来纯噪音。

**Involved files**
- `src/crawlers/`
- `docs/SOURCE_EXPANSION_PLAN.md`
- `README.md`
- `docs/CURRENT_STATUS.md`

**Do**
1. 评估额外 curated blogs
2. 在用户提供 URL 后接入 T4 personal sources
3. 评估是否纳入 SE 安全相关会议轨
4. 做 source performance review

**Done when**
- 每个新 source 都通过准入规则
- 没有破坏 no-mix 原则
- 文档同步记录保留/淘汰理由

**Review**  
Needs human review before merge

---

## RR-011 Zotero 相似检索与 agent 相关度裁判
**Why now**  
用户明确希望相关度基于已有 Zotero 数据，而不是手工维护 core / background / low-priority profile。Zotero 应作为个人文献语料库：对每条外部候选检索最相近的 Zotero 条目，再由 agent 基于证据判断是否值得读。

**Involved files**
- `src/` 新增 Zotero JSON 读取与相似检索模块
- `prompts/` 新增候选条目 vs Zotero 证据裁判 prompt
- `src/scoring/` 或 report 派生逻辑（优先写入 `score_breakdown`）
- `tests/` Zotero import / retrieval / judge tests
- `docs/design/10_zotero_relevance.md`
- `docs/CURRENT_STATUS.md`

**Do**
1. 支持 Better CSL JSON 作为 Zotero 导入格式
2. 不要求用户预先标注 core / background / low-priority
3. 为每条外部候选检索 top-k 相似 Zotero 条目
4. 让 agent 输出结构化判断：相关度、关联 Zotero 条目、推荐理由、消费 bucket hint
5. 第一阶段不新增 schema，优先写入 `score_breakdown`
6. 控制成本：不把全量 Zotero 直接塞进 prompt，只提供检索后的 top-k 证据

**Done when**
- 本地 Better CSL JSON 可以被导入或加载
- 候选 artifact 可以拿到 Zotero top-k 相似证据
- agent judgment 可重跑、可测试、可缓存
- `score_breakdown` 中能看到个人相关度和 Zotero 证据
- 不破坏现有 academic / industry 分轨

**Review**  
Needs human review before merge

---

## RR-012 arXiv 质量证据与宁缺毋滥筛选
**Why now**  
用户明确偏好 arXiv 宁缺毋滥。arXiv 只按主题相关会噪声过高，必须结合作者、课题组、机构、历史发表和外部学术图谱信号，才能进入 must-read 或 detailed-summary。

**Involved files**
- `src/` 新增 external scholarly metadata adapter（Semantic Scholar / OpenAlex / DBLP，可分步）
- `src/scoring/` 质量证据计算
- `prompts/` arXiv candidate quality judge prompt（如需要）
- `tests/` metadata fallback / scoring tests
- `docs/design/10_zotero_relevance.md`
- `docs/SOURCE_EXPANSION_PLAN.md`（如 source 策略变化）

**Do**
1. 为 arXiv candidate 补作者 / 机构 / 历史发表 / 引用等质量证据
2. 将质量证据与 Zotero 相似度结合
3. 采用宁缺毋滥策略：质量证据不足时不能仅凭相关度进入高优先级
4. 外部 API 不可用时降级为低置信度，而不是阻断日报
5. 输出可解释理由：为什么值得读，或为什么只进入 one-line / archive

**Done when**
- arXiv candidate 有 `quality_score` 或等价 `score_breakdown` 字段
- 高优先级 arXiv 必须同时具备个人相关度和质量证据
- 外部 metadata 失败时系统可继续运行
- 测试覆盖质量信号缺失、弱质量强相关、强质量弱相关等情况

**Review**  
Needs human review before merge

---

## RR-013 Source 配置集中管理
**Why now**  
当前 source URL、启用状态、tier 映射分散在 crawler class、`registry.py` 和 `normalization.py` 中。后续要接 OpenAI / Anthropic / 安全机构博客、会议页面、Zotero/arXiv 质量信号时，需要一个集中入口；不相关或暂不维护的 source 应能通过配置下线，而不是删除代码破坏兼容。

**Involved files**
- `config/sources.json`
- `src/config/sources.py`
- `src/crawlers/registry.py`
- `src/pipelines/normalization.py`
- `tests/`
- `docs/CURRENT_STATUS.md`

**Do**
1. 新增集中 source metadata 配置
2. registry 从配置读取默认启用 crawler
3. normalization 从配置推断 source tier
4. 不删除旧 crawler class，先用 `enabled` 控制默认运行范围
5. 不新增 YAML 依赖，优先使用 JSON

**Done when**
- source tier 映射不再只维护在 `normalization.py`
- 默认 crawler registry 由集中配置过滤
- 未启用 source 不参与默认 crawl
- 现有测试通过

**Completed (2026-06-16)**  
- 新增 `config/sources.json` 作为 source metadata 集中入口。
- 新增 `src/config/sources.py`，统一加载 source slug/name/type/tier/track/adapter/enabled/aliases/urls/tags。
- `registry.py` 现在只默认注册配置中 `enabled=true` 且 `adapter=crawler` 的 source。
- `normalization.py` 现在通过集中配置推断 `source_tier`，不再维护独立 `SOURCE_TIER_BY_NAME`。
- OpenAI / Anthropic 已设为 enabled RSS source；Brutecat / HackTron / Black Hat / DEF CON / RSAC / BSidesSF 已进入配置。
- Cloudflare Security Blog / Trail of Bits 已从集中配置移除；旧 crawler class 未删除，以保留兼容空间。
- 未删除旧 crawler class，保留兼容与测试覆盖。

**Review**  
Needs human review before merge

---

## RR-014 配置驱动 RSS ingest
**Why now**  
OpenAI / Anthropic 等 source 已进入集中配置并启用，但当前默认 crawl 只支持专用 crawler class。需要一个轻量 RSS adapter，让 `adapter=rss` 的 source 可以真正进入 raw JSON -> normalization 链路。

**Involved files**
- `requirements.txt`
- `config/sources.json`
- `src/crawlers/rss_crawler.py`
- `src/crawlers/registry.py`
- `tests/`
- `docs/RUNBOOK.md`
- `docs/CURRENT_STATUS.md`

**Do**
1. 集成 `feedparser`
2. 新增通用 RSS/Atom crawler
3. 从 `config/sources.json` 读取 `urls.rss` / `urls.feed`
4. 输出与现有 blog crawler 一致的 raw item shape
5. 将 enabled RSS sources 注册到 crawl registry
6. 保持 webpage source 只作为配置入口，不在本票实现

**Done when**
- `crawl --source openai-blog` / `crawl --source anthropic-news` 可以走 RSS adapter
- RSS item 解析出 title / link / date / excerpt / authors / tags
- malformed feed 有明确失败路径
- 相关测试通过

**Completed (2026-06-16)**  
- 新增 `feedparser>=6.0.11` 依赖。
- 新增 `RSSFeedCrawler`，支持 RSS/Atom 解析、bozo 检测、日期/作者/tag/excerpt 提取。
- `BLOG_CRAWLER_REGISTRY` 现在会注册 enabled RSS source。
- OpenAI 配置补充 `urls.rss`；Anthropic 后续已改走 sitemap。

**Review**  
Needs human review before merge

---

## RR-015 配置驱动 sitemap ingest
**Why now**  
Anthropic News 当前没有可用官方 RSS，`/news/rss.xml` 返回 404；但 `robots.txt` 指向官方 sitemap，`sitemap.xml` 包含 `/news/` URL 和 `lastmod`。需要通用 sitemap adapter 来覆盖没有 RSS 但 sitemap 稳定的网站。

**Involved files**
- `config/sources.json`
- `src/crawlers/sitemap_crawler.py`
- `src/crawlers/registry.py`
- `src/config/sources.py`
- `tests/`
- `docs/CURRENT_STATUS.md`

**Do**
1. 支持 `adapter=sitemap`
2. 从 `urls.sitemap` 读取 sitemap XML
3. 支持 `filters.include_url_prefixes`
4. 对 listing/homepage 做可选 metadata 补充
5. 输出与 blog raw item 一致的 shape
6. 将 Anthropic 从 RSS 改为 sitemap

**Done when**
- `anthropic-news` 可以返回有效 raw items
- sitemap URL 过滤、lastmod 日期、listing metadata 有测试覆盖
- registry 能注册 enabled sitemap source
- 不影响 RSS / crawler source

**Completed (2026-06-16)**  
- 新增 `SitemapCrawler`。
- Anthropic News 改为 `adapter=sitemap`，使用 `https://www.anthropic.com/sitemap.xml` 并过滤 `/news/` URL。
- listing page 可补充标题、日期和 subject；listing 不覆盖时退回 URL slug title。
- live smoke 成功抓取 Anthropic News 5 条。

**Review**  
Needs human review before merge

---

## RR-016 配置驱动 webpage ingest 与 live source smoke
**Why now**  
Brutecat / HackTron / Black Hat / DEF CON / RSAC / BSidesSF 已进入集中 source 配置，但 `webpage` adapter 尚未参与真实 crawl，无法验证这些源是否能提供每日资讯。

**Involved files**
- `config/sources.json`
- `src/crawlers/webpage_crawler.py`
- `src/crawlers/registry.py`
- `src/cli/crawl.py`
- `tests/crawlers/test_webpage_crawler.py`
- `tests/test_source_config.py`
- `docs/CURRENT_STATUS.md`
- `docs/RUNBOOK.md`
- `docs/SOURCE_EXPANSION_PLAN.md`
- `docs/design/05_source_plan.md`

**Do**
1. 新增通用 HTML listing-page crawler
2. 让 `adapter: "webpage"` 的 enabled blog source 进入 registry
3. 为当前网页源补最小 URL/text filters
4. 全量 crawl 遇到单 source 失败时跳过并继续
5. 用真实网络 smoke 验证可用源和失败源
6. 用真实抓取数据验证 normalize/enrich/signal/report 链路

**Done when**
- Webpage parser 有单元测试覆盖
- Webpage source 可通过 `python -m src.cli crawl --source <slug>` 单独运行
- live smoke 明确记录哪些源可用、哪些源 blocked
- 分析归纳链路能消费网页源 raw JSON

**Completed (2026-07-01)**  
- 新增 `WebpageCrawler` 并注册 `webpage` adapter。
- Brutecat、HackTron、DEF CON、BSidesSF 已能返回条目；OpenAI RSS 与 Anthropic sitemap 仍可返回 2026-06-30 最新条目。
- Black Hat USA/Asia/Europe 与 RSAC 当前 requests 访问返回 403，后续需要替代抓取策略。
- 使用真实抓取数据和 deterministic LLM stub 验证 `normalize → enrich → signal extraction → score → daily report` 通过。

**Review**  
Needs human review before merge

---

## RR-017 日报展示 AI 摘要与关键词
**Why now**  
用户明确短期不需要“亲读 / 一句话 / delegate”分层。当前更直接的价值是：每条进入日报的内容都有 AI 生成的一句话摘要和关键词，便于每日扫读。

**Involved files**
- `src/reporting/daily.py`
- `tests/reporting/test_daily.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`
- `docs/REPORT_POLICY.md`

**Do**
1. 日报推荐条目优先展示 `summary_l1`
2. 当 `summary_l1` 缺失时再 fallback 到原始 `abstract`
3. 每条推荐展示 `tags` 作为关键词
4. 不新增 triage bucket
5. 不改 schema / scoring / source 配置

**Done when**
- 日报每条推荐都有摘要行
- 有 tags 时显示关键词
- 没有 tags 时输出清晰占位
- 测试覆盖 summary 优先级和关键词展示

**Completed (2026-07-01)**  
- 日报推荐条目优先展示 `summary_l1`，缺失时回退 `abstract`。
- 日报推荐条目新增 `关键词` 行，来自 artifact `tags`。
- 缺少 tags 时显示 `暂无关键词。`。
- 不新增 bucket、不改 schema、不改 scoring。

**Review**  
Codex can do directly

---

## RR-018 OpenAI-compatible streaming gateway 配置
**Why now**  
用户提供了 OpenAI-compatible 内网网关、API key 和 `gpt-5.4` 模型，希望先验证项目 LLM 摘要链路能否工作。

**Involved files**
- `.env`（gitignored，本地配置）
- `.env.example`
- `src/llm/providers.py`
- `tests/llm/test_providers.py`
- `docs/CURRENT_STATUS.md`
- `docs/RUNBOOK.md`

**Do**
1. 配置 OpenAI provider 指向 `/v1/responses` 网关
2. 配置 fast / standard / premium 都使用 `gpt-5.4`
3. 支持 input list payload
4. 支持 Responses SSE stream 解析
5. 支持 `store=false`
6. 支持省略网关不接受的 generation params
7. 为限流网关提供 enrichment 请求间隔参数

**Done when**
- `LLMClient(provider="openai")` 最小 prompt live smoke 通过
- `EnrichmentPipeline` 对临时 artifact live smoke 通过
- provider stream parser 有单元测试
- 不影响默认 OpenAI Responses API 行为

**Completed (2026-07-01)**  
- 本地 `.env` 已配置内网 OpenAI-compatible gateway 和 `gpt-5.4`。
- `OpenAIProvider` 新增可配置兼容开关：`OPENAI_INPUT_AS_LIST`、`OPENAI_STREAM`、`OPENAI_STORE`、`OPENAI_OMIT_GENERATION_PARAMS`。
- live smoke 返回 JSON pong。
- live EnrichmentPipeline 成功生成 `summary_l1` 和 5 个 tags。
- `enrich` CLI 新增 `--request-delay`，用于限流网关下的顺序慢速 enrichment。

**Review**  
Codex can do directly

---

## RR-019 Local Web Console
**Why now**  
用户希望不止有静态前端，而是有一个本地 Web 应用，可以按 academic / industry 查看结果，并在后台管理 source 配置、测试数据源、触发基础 pipeline。

**Involved files**
- `requirements.txt`
- `src/cli/main.py`
- `src/cli/web.py`
- `src/web/`
- `templates/static assets`
- `tests/web/`
- `docs/CURRENT_STATUS.md`
- `docs/RUNBOOK.md`

**Do**
1. 新增 FastAPI + Jinja 本地 Web Console
2. Dashboard 展示最近 artifacts、academic / industry 分组、source / LLM 状态
3. Sources 页面支持 list / create / enable toggle / test fetch
4. Runs 页面支持手动触发小范围 pipeline 命令
5. Artifacts 页面支持浏览最近条目
6. 默认只绑定 `127.0.0.1`
7. 不新增并行 orchestrator，不改 DB schema

**Done when**
- `python -m src.cli web` 可以启动本地服务
- Dashboard / Sources / Runs / Artifacts 页面可打开
- 新 source 默认 `enabled=false`
- Source test fetch 能返回成功/失败和样例条目
- 有基础路由/配置写入测试

**Completed (2026-07-01)**  
- 新增 FastAPI + Jinja 本地 Web Console，默认绑定 `127.0.0.1`。
- Dashboard 按 industry / academic 查看近期 artifact，并展示 source 与 LLM 配置状态。
- Sources 页面支持集中配置的 list / create / enable toggle / test fetch；新建 source 默认 disabled。
- Runs 页面支持手动触发单 source crawl、normalize、单条 enrich、score 和 daily report。
- Artifacts 页面支持按 all / academic / industry 浏览近期条目。
- Web 后台复用现有 SQLite、`config/sources.json` 和 pipeline，不新增 schema，也不新增平行 orchestrator。

**Review**  
Needs human review before merge

---

## RR-020 中文详细内容总结
**Why now**  
用户测试 Web Console 后反馈摘要太短，且希望摘要使用中文，核心需求是“总结每个收集到的文章的内容”，而不是只给一句短提示。

**Involved files**
- `prompts/summarize_artifact.md`
- `src/pipelines/enrichment.py`
- `src/reporting/daily.py`
- `src/web/templates/partials/artifact_item.html`
- `src/web/static/app.css`
- `tests/pipelines/test_enrichment_pipeline.py`
- `tests/reporting/test_daily.py`
- `tests/web/test_web_app.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`
- `docs/REPORT_POLICY.md`

**Do**
1. 摘要生成默认要求中文输出
2. `summary_l1` 从极短一句话改为中文概览摘要
3. `summary_l3` 承载 250-500 字中文详细内容总结
4. enrichment 默认版本升级，避免复用旧短摘要缓存
5. 缺少 `summary_l3` 的旧 artifact 允许重新 enrichment
6. 日报和 Web 卡片优先展示 `summary_l3`
7. 不新增 schema、不改 scoring、不改 source 配置

**Done when**
- 新 enrichment response 可写入 `summary_l1 / summary_l3 / tags`
- 旧条目只有 `summary_l1` 时会补齐详细总结
- 日报推荐条目展示 `内容总结`
- Web Console artifact 卡片优先展示详细总结
- 测试覆盖 fallback 和展示优先级

**Completed (2026-07-01)**  
- `prompts/summarize_artifact.md` 改为中文详细摘要 prompt。
- `EnrichmentPipeline` 默认版本升级到 `v2-cn-detailed`，请求 token 上限提升到 900，并写回 `summary_l3`。
- 缺少 `summary_l3` 的 active artifact 会重新进入 enrichment，以补齐详细总结。
- 日报 `今日博客推荐` 将 `摘要` 改为 `内容总结`，优先展示 `summary_l3`，再回退 `summary_l1` / `abstract`。
- Web Console artifact 卡片优先展示 `summary_l3`，并保留换行。

**Review**  
Needs human review before merge

---

## RR-021 Industry Dashboard 子板块拆分
**Why now**  
用户希望 Web Console 里的 Industry 不再是单一列表，而是进一步拆成工业界会议、博客文章、组织发布三个板块，方便每天扫读时按信息类型消费。

**Involved files**
- `src/web/app.py`
- `src/web/templates/dashboard.html`
- `src/web/static/app.css`
- `tests/web/test_web_app.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`

**Do**
1. Industry Dashboard 按 source metadata 分类
2. `industry-conference` tag 进入工业界会议板块
3. OpenAI / Anthropic 进入组织发布板块
4. 其余 T3 research blog 进入博客文章板块
5. 保持 academic / industry 仍然分轨
6. 不新增 schema、不改 source 配置、不改 scoring

**Done when**
- Dashboard 展示三个 Industry 子板块
- 每个子板块有独立空态和数量
- 分类逻辑有测试覆盖
- 移动端仍保持单列可读

**Completed (2026-07-01)**  
- Dashboard 的 Industry 区域拆成 `Industry conferences`、`Research blogs`、`Organizations` 三个子板块。
- 分类优先使用 `config/sources.json` 中的 tags / slug，source name 仅做兜底。
- Web 路由测试覆盖会议、博客、组织三类 artifact 展示。

**Review**  
Codex can do directly

---

## RR-022 Anthropic sitemap 详情页正文可见性修复
**Why now**  
用户发现 Anthropic News 的摘要仍然像“只看标题推测”，说明抓取层没有拿到文章正文，导致中文详细摘要缺乏真实可见内容。

**Involved files**
- `src/crawlers/sitemap_crawler.py`
- `tests/crawlers/test_sitemap_crawler.py`
- `src/pipelines/enrichment.py`
- `tests/pipelines/test_enrichment_pipeline.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`

**Do**
1. 确认 Anthropic raw item 是否包含详情正文
2. 确认详情页是否可直接访问
3. sitemap crawler 对 limited entries 抓取详情页正文
4. 将详情页正文写入 raw `excerpt`
5. enrichment cache key 纳入正文指纹，避免正文更新后复用旧摘要
6. 重新抓取、normalize、enrich Anthropic News

**Done when**
- Anthropic raw item `excerpt` 不再为空
- `Introducing Claude Sonnet 5` 的 artifact abstract 来自详情页正文
- 重新生成的 `summary_l3` 不再是标题推测
- crawler 与 cache key 都有回归测试

**Completed (2026-07-01)**  
- `SitemapCrawler` 现在会在 `limit` 截断后抓取详情页，并从 `article/main` 抽取最多 6000 字正文作为 `excerpt`。
- `EnrichmentPipeline` cache key 增加标题、abstract、source_url 的内容指纹，避免 source 可见性改善后命中旧缓存。
- 已重新抓取 Anthropic News 20 条，normalize 后更新 artifact abstract，并重跑 Anthropic 摘要。
- `Introducing Claude Sonnet 5` 现在有 6002 字 abstract 和 421 字中文 `summary_l3`。

**Review**  
Codex can do directly

---

## RR-023 低相关展示过滤与 arXiv 小批量呈现
**Why now**  
用户希望分析后“完全和网络安全没啥关系”的内容不要展示，同时 arXiv 已接入但还没有稳定呈现在每日阅读界面。

**Involved files**
- `src/reporting/relevance_filter.py`
- `src/scoring/relevance.py`
- `src/pipelines/llm_relevance.py`
- `src/crawlers/registry.py`
- `src/config/sources.py`
- `config/sources.json`
- `src/web/app.py`
- `src/reporting/daily.py`
- `tests/`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`

**Do**
1. 统一展示过滤逻辑：仅隐藏已分析且 `llm_relevance_score < 0.4` 的 artifact
2. 修复无 active Profile 时 `score` 忽略 LLM relevance 的问题
3. 让 arXiv crawler 从集中配置读取 `categories` 和 `max_results`
4. 将 arXiv 默认抓取上限收敛为 100 条，避免每日运行过重
5. 扩大 Dashboard 候选池，避免 arXiv 批量入库挤空 industry lane
6. 用真实 arXiv 小批量验证中文摘要、相关性评分和页面展示

**Done when**
- 低相关 generic AI/product 内容不出现在日报和 Dashboard
- `score` 阶段能把 `llm_relevance_score` 写入最终 relevance/final score
- `crawl --source arxiv` 当前返回 100 条以内最新论文
- Web Dashboard 能同时显示 arXiv 相关论文和 industry 信号
- 测试覆盖展示过滤、评分 fallback、arXiv params 和 Dashboard 候选池

**Completed (2026-07-01)**  
- 新增共享 `should_display_artifact`，日报和 Web 统一隐藏最低相关档 artifact。
- `RelevanceStrategy` 在没有 Profile 时仍使用预计算 LLM relevance；没有 LLM 分时才回退 0.5。
- arXiv source 配置新增 `params.categories` / `params.max_results=100`，registry 实例化时传入 crawler。
- Dashboard 候选池扩大到 160，避免 arXiv 批量入库挤掉 industry sections。
- live run：arXiv API 返回 100 条最新论文；对 5 条最新 arXiv 生成中文摘要和 LLM relevance；Prompt Injection 相关论文显示，最低相关 arXiv 条目隐藏。

**Review**  
Needs human review before merge

---

## RR-024 Academic 论文详细呈现到 Daily/Weekly
**Why now**  
arXiv 已能小批量抓取、摘要和相关性过滤，但 Daily 目前只输出论文新增数量，用户仍需要在日报/周报中看到高相关 academic item 的中文摘要和关键词。

**Involved files**
- `src/reporting/daily.py`
- `src/reporting/weekly.py`
- `src/reporting/relevance_filter.py`
- `tests/reporting/`
- `docs/REPORT_POLICY.md`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`

**Do**
1. 在 Daily 中增加 Academic 论文摘要区，先只展示已分析且通过 relevance filter 的少量高分论文
2. 保持 academic / industry 分轨，不和博客混排
3. 优先展示 `summary_l3`、关键词和 source URL
4. 明确 arXiv 日报上限，避免 100 条全量刷屏
5. 与 Weekly/landscape 的后续收敛保持兼容

**Done when**
- Daily 能看到高相关 arXiv / T1 paper 的中文详细摘要
- 低相关 arXiv 不进入 Daily
- 报告测试覆盖 Academic 区和上限
- `REPORT_POLICY` 更新实际结构

**Review**  
Needs human review before merge

---

## RR-025 Artifact 浏览按时间分页
**Why now**  
arXiv 和 RSS/webpage source 接入后，artifact 数量会快速增加；浏览页固定只取最近 80 条会漏掉数据，也无法稳定按时间翻阅。

**Involved files**
- `src/web/app.py`
- `src/web/templates/artifacts.html`
- `src/web/static/app.css`
- `tests/web/test_web_app.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`

**Do**
1. `/artifacts` 使用 SQLite 中的 artifact 表作为展示数据源
2. 按时间倒序展示：`published_at` 优先，缺失时回退 `created_at/id`
3. 增加分页参数 `page`，默认每页 20 条
4. 保持 `track=all/academic/industry` 过滤
5. 保持低相关展示过滤，不把隐藏项计入页数

**Done when**
- Artifact browser 显示当前范围和总数
- Previous / Next 可翻页
- 第 1 页和第 2 页内容不重复
- 低相关 artifact 不出现在分页结果里

**Completed (2026-07-01)**  
- `/artifacts` 增加分页查询与分页上下文，默认每页 20 条。
- 模板新增顶部/底部分页控件，保留 track tab。
- Web 测试覆盖时间倒序、分页范围、下一页内容和低相关隐藏。

**Review**  
Codex can do directly

---

## RR-026 Dashboard 双列比例与时间排序修正
**Why now**  
用户截图反馈 Dashboard 左侧 Industry 过宽、右侧 Academic 过窄，并指出首页排序也应按时间顺序。

**Involved files**
- `src/web/app.py`
- `src/web/static/app.css`
- `tests/web/test_web_app.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`

**Do**
1. Dashboard 候选 artifact 排序与 Artifacts 页一致，优先按 `published_at` 倒序
2. 宽屏 Dashboard 从固定 360px 右栏改成明确的 1:1 双列
3. 保留 960px 以下单列响应式布局
4. 增加回归测试防止 Dashboard 回退到按插入时间排序

**Done when**
- Dashboard 左右两列在宽屏下不再明显失衡
- Academic lane 至少有可读宽度
- 首页 item 顺序按发布时间倒序
- Web 测试通过

**Completed (2026-07-02)**  
- `_recent_artifacts` 现在按 `published_at desc nulls last, created_at desc, id desc` 排序。
- `.dashboard-grid` 从 `1fr 360px` 改为 `minmax(0, 1fr) minmax(0, 1fr)`。
- `base.html` 给 `app.css` 增加版本参数，避免浏览器缓存旧布局。
- 新增 Dashboard 发布时间排序回归测试。

**Review**  
Codex can do directly

---

## RR-027 Academic Zotero/CSRankings 首轮过滤
**Why now**  
用户明确指出 Academic 还缺少质量和相关度限制：相关度应基于个人 Zotero 文献库，不相关的候选直接不展示；arXiv 质量应优先考虑 CSRankings 上有知名度的组/作者。

**Involved files**
- `src/personalization/zotero.py`
- `src/personalization/academic_quality.py`
- `src/pipelines/academic_filter.py`
- `src/reporting/relevance_filter.py`
- `src/cli/process.py`
- `src/cli/main.py`
- `.env.example`
- `tests/personalization/`
- `tests/cli/test_commands.py`
- `docs/RUNBOOK.md`
- `docs/design/10_zotero_relevance.md`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`

**Do**
1. 支持 Better CSL JSON 作为 Zotero 首个稳定输入格式
2. 支持 Zotero Web API / Local API 作为后续自动同步入口
3. 对 academic artifact 检索 top-k 相似 Zotero 条目，并写入 `score_breakdown`
4. 用 CSRankings faculty CSV 给 arXiv 候选写入质量信号
5. 展示层隐藏已评估但 Zotero 低相关的论文，以及已评估但质量信号不足的 arXiv 论文

**Done when**
- `academic-filter` CLI 可对已有 SQLite artifact 写入 Zotero / CSRankings 证据
- 未配置 Zotero 时不会破坏默认 `run` 链路
- Daily/Web 共享 relevance filter 会消费新证据
- 相关单元测试和 CLI 测试通过

**Completed (2026-07-02)**  
- 新增 `src/personalization/`，支持 Better CSL JSON、Zotero API、token cosine top-k 检索。
- 新增 CSRankings CSV 质量索引，命中候选作者时写入 faculty / affiliation / scholar id 证据。
- 新增 `academic-filter` CLI，将 `zotero_similarity`、`zotero_matches`、`academic_quality_score` 等字段写入 `score_breakdown`。
- `relevance_filter` 对已评估 academic artifact 应用 Zotero 相关度门槛；对已评估 arXiv 应用 CSRankings 质量门槛。
- 补充 personalization、CLI 和展示过滤测试。

**Review**  
Needs human review before merge

---

## RR-028 Academic evidence chips 展示
**Why now**  
用户希望每篇 paper 不只显示摘要，还要显示 topic、命中的知名度证据，以及与 Zotero 相关论文的 topic，方便快速判断为什么这篇论文被保留。

**Involved files**
- `src/web/presentation.py`
- `src/web/templates/partials/artifact_item.html`
- `src/web/static/app.css`
- `src/web/templates/base.html`
- `src/personalization/zotero.py`
- `src/pipelines/academic_filter.py`
- `tests/web/test_web_app.py`
- `tests/personalization/test_zotero.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`
- `docs/REPORT_POLICY.md`
- `docs/design/10_zotero_relevance.md`

**Do**
1. 从 artifact `tags` 生成普通 topic chips
2. 从 `score_breakdown.zotero_similarity` 和 `zotero_matches` 生成 Zotero relevance chips
3. 从 `academic_quality_signals.matched_faculty` 生成 CSRankings faculty / group chips
4. 让 Dashboard 和 Artifacts 共用同一 partial，避免两处展示漂移
5. 保持 chip 数量有限，避免 paper card 噪声过高

**Done when**
- Academic card 能展示原始 topic、Zotero topic、Zotero 相似度和 CSRankings evidence
- 没有 evidence 的旧 artifact 仍能正常显示
- CSS 缓存版本更新
- Web 测试覆盖 chip 渲染

**Completed (2026-07-02)**  
- 新增 `src/web/presentation.py`，将 artifact 和 academic evidence 转成 UI chips。
- `artifact_item.html` 改为渲染 presenter 输出，Dashboard 和 Artifacts 同步受益。
- CSS 区分 topic / relevance / quality chips，控制长标签换行和密度。
- Zotero match evidence 新增 `topics` 字段，academic filter version 升级为 `v2-zotero-csrankings-topics`。
- 测试覆盖 Zotero topics 和 Web evidence chips。

**Review**  
Needs human review before merge

---

## RR-029 Academic AI focus labels
**Why now**  
用户指出 `Zotero 0.18` 这种裸相似度数字难以理解，Zotero/arXiv 原始 topic 也太泛，需要用 AI 凝练成更具体的研究焦点，例如“fuzzing 调度策略”。

**Involved files**
- `prompts/academic_focus_labels.md`
- `src/pipelines/academic_labels.py`
- `src/cli/process.py`
- `src/cli/main.py`
- `src/web/presentation.py`
- `src/web/static/app.css`
- `src/web/templates/base.html`
- `tests/personalization/test_academic_labels.py`
- `tests/web/test_web_app.py`
- `tests/cli/test_commands.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`
- `docs/RUNBOOK.md`
- `docs/REPORT_POLICY.md`
- `docs/design/10_zotero_relevance.md`

**Do**
1. 新增 LLM prompt，将 paper title/abstract、Zotero match 和 CSRankings evidence 凝练成 2-4 个具体研究焦点标签
2. 新增 `academic-labels` CLI，默认只处理当前通过展示过滤的 academic artifact
3. 将结果写入 `score_breakdown.academic_focus_labels`，不新增 schema
4. Web paper 卡片优先展示 focus labels
5. 页面不再展示裸 `Zotero 0.xx` 分数；原始相似度仅放在 `Zotero match` tooltip
6. 有 AI focus labels 时，不再展示泛化 Zotero topic 或相关论文长标题

**Done when**
- `academic-labels` 可独立运行且可重跑
- 当前 displayable papers 都能生成 focus labels
- Web chips 聚焦具体研究问题/方法/对象
- 测试覆盖 pipeline、CLI 和 Web 展示

**Completed (2026-07-02)**  
- 新增 `AcademicLabelPipeline` 和 `academic-labels` 命令。
- 新增 `prompts/academic_focus_labels.md`，要求 LLM 输出具体研究焦点标签并避免泛标签。
- Web presenter 优先展示 `academic_focus_labels`，将 raw similarity 改为 `Zotero match` tooltip。
- 已实际运行 `python -m src.cli academic-labels --provider openai --request-delay 5`，当前 18 条 displayable paper 均已生成 focus labels。
- 测试覆盖新增 pipeline、CLI 和 Web 行为。

**Review**  
Needs human review before merge

---

## RR-030 Paper 卡片摘要与 Zotero keyword 收敛
**Why now**  
用户反馈 Zotero keyword 数量应更少，paper 卡片摘要也应更简洁且优先中文。当前 Web 卡片直接展示长 `summary_l3` 会占用太多阅读空间。

**Involved files**
- `src/web/presentation.py`
- `src/web/templates/partials/artifact_item.html`
- `src/web/templates/base.html`
- `src/web/app.py`
- `src/personalization/zotero.py`
- `src/pipelines/academic_filter.py`
- `tests/web/test_web_app.py`
- `tests/personalization/test_zotero.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`
- `docs/REPORT_POLICY.md`
- `docs/design/10_zotero_relevance.md`

**Do**
1. Paper card 摘要优先展示中文 `summary_l1`
2. Blog / industry card 保持优先展示 `summary_l3`
3. 缺少中文摘要时，用 `academic_focus_labels` 合成中文研究焦点句
4. Zotero match evidence 中每条 match 的 `topics` 最多保留 3 个
5. 更新 CSS cache 版本
6. 增加测试覆盖 paper 摘要优先级和 Zotero topic 数量

**Done when**
- paper 卡片不再默认展示长 `summary_l3`
- paper 有中文 `summary_l1` 或 focus labels 时不展示英文 abstract
- Zotero match topic 每条最多 3 个
- 相关 Web / personalization 测试通过

**Completed (2026-07-02)**  
- 新增 `artifact_summary()` presenter，paper 卡片优先展示较短中文 `summary_l1`。
- 对缺少中文摘要的 paper，卡片用 `academic_focus_labels` 合成中文研究焦点句，不直接展示英文 abstract。
- `artifact_item.html` 改为使用 presenter 控制摘要选择。
- Zotero matcher 输出的 `topics` 从 5 个收敛为 3 个。
- Academic filter version 升级为 `v3-zotero-csrankings-topics3`，已重跑 `academic-filter` 更新现有 paper。
- 测试覆盖 paper concise summary 和 Zotero topics 上限。

**Review**  
Codex can do directly

---

## RR-031 Paper 摘要展示回调与 Zotero top-k 诊断
**Why now**  
用户反馈 paper 卡片被过度压缩成“研究焦点”句子，应该仍以中文内容摘要为主；同时当前 Zotero 相关度结果偏宽，需要明确 top-k 的真实作用后再决定是否收紧阈值。

**Involved files**
- `src/web/presentation.py`
- `src/web/templates/base.html`
- `tests/web/test_web_app.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`
- `docs/REPORT_POLICY.md`
- `docs/design/10_zotero_relevance.md`

**Do**
1. Paper 卡片摘要优先展示中文 `summary_l3`
2. 缺少中文详细摘要时回退中文 `summary_l1`
3. 只有没有中文摘要时才用 `academic_focus_labels` 合成研究焦点句
4. 保留 focus labels 作为 chips，不把它们当主摘要
5. 说明当前 top-k 只是 Zotero evidence retrieval，过滤只看 top1 cosine similarity

**Done when**
- 有中文 `summary_l3` 的 paper 卡片展示详细中文摘要
- 英文 abstract 仍不会在卡片上直接暴露
- 测试覆盖 paper 摘要优先级
- 文档不再要求 paper 卡片优先短摘要

**Completed (2026-07-02)**  
- `artifact_summary()` 对 paper 改为 `summary_l3 -> summary_l1 -> academic_focus_labels`。
- Paper 卡片中文摘要上限从 220 字符放宽到 520 字符。
- Web 测试改为断言 paper 优先展示中文详细摘要。
- 已对当前 18 篇 displayable arXiv paper 补跑中文 enrichment。
- 更新 report policy 和 Zotero relevance 设计文档，避免后续按旧策略回退。

**Review**  
Codex can do directly

---

## RR-032 Zotero 全量读取与 LLM 相关度裁判
**Why now**  
用户确认 arXiv 结果宁缺毋滥，没内容也可以；Academic 相关度应该由 LLM 基于 top-k Zotero evidence 判断，而不是只靠 `zotero_similarity >= 0.18` 的词面相似度。

**Involved files**
- `src/personalization/zotero.py`
- `src/pipelines/academic_judge.py`
- `src/reporting/relevance_filter.py`
- `src/cli/process.py`
- `src/cli/main.py`
- `prompts/academic_relevance_judge.md`
- `tests/personalization/test_academic_judge.py`
- `tests/personalization/test_zotero.py`
- `tests/cli/test_commands.py`
- `.env.example`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`
- `docs/RUNBOOK.md`
- `docs/REPORT_POLICY.md`
- `docs/design/10_zotero_relevance.md`

**Do**
1. Zotero API 读取上限不要卡在 500，支持覆盖较大的个人 Zotero 语料库
2. 新增 LLM 相关度裁判 prompt 和 pipeline
3. LLM 只接收候选论文和 top-k Zotero evidence，不发送完整 Zotero 库
4. 将裁判结果写入 `score_breakdown`
5. 已有裁判结果时，展示过滤以 LLM 相关度为准，不再用 0.18 词面阈值作为相关度门槛
6. 保留 arXiv 质量门槛作为独立质量过滤

**Done when**
- 当前配置的 Zotero corpus 可读取
- `academic-judge` 可独立运行且可重跑
- Web/Daily 对已裁判 paper 使用 LLM 相关度过滤
- 测试覆盖 Zotero max items、judge pipeline、CLI 和展示过滤

**Completed (2026-07-02)**  
- `DEFAULT_ZOTERO_MAX_ITEMS` 从 500 调整为 2000，并新增 `ZOTERO_MAX_ITEMS` 环境变量。
- 新增 `AcademicJudgePipeline` 和 `academic-judge` CLI。
- 新增 `prompts/academic_relevance_judge.md`，要求 LLM 严格判断研究问题/方法/攻击面/系统对象是否与 Zotero evidence 明确重叠。
- `relevance_filter` 在已有 LLM 裁判结果时跳过原始 Zotero 0.18 词面阈值，改用 `academic_relevance_relevant` 和 `academic_relevance_score`。
- 已重跑 `academic-filter` 和 `academic-judge`：100 篇 arXiv 完成裁判，15 篇被判相关，9 篇通过相关度与质量门槛进入 Web 展示。

**Review**  
Needs human review before merge

---

## RR-033 Academic evidence chip 语义收敛
**Why now**  
用户指出 `Zotero match` chip 没有信息量，同时灰色和橙色 tag 的区别不清晰。当前已有 LLM 相关度裁判后，页面不应再用 Zotero 检索存在性作为可见证据。

**Involved files**
- `src/web/presentation.py`
- `src/web/static/app.css`
- `src/web/templates/base.html`
- `tests/web/test_web_app.py`
- `docs/CURRENT_STATUS.md`
- `docs/CODEX_BACKLOG.md`
- `docs/RUNBOOK.md`
- `docs/REPORT_POLICY.md`
- `docs/design/10_zotero_relevance.md`

**Do**
1. 移除 `Zotero match` chip
2. 有 LLM 裁判结果时显示 `相关度 0.xx` chip
3. `相关度` tooltip 使用中文裁判理由
4. 保持橙色 focus chips 表示研究焦点
5. 保持绿色 quality chips 表示 CSRankings/课题组质量证据
6. 更新 CSS cache 版本和测试

**Done when**
- Web paper card 不再显示 `Zotero match`
- 相关度 chip 有实际分数和理由
- chip 颜色语义在文档中明确
- Web 测试通过

**Completed (2026-07-02)**  
- `artifact_chips()` 改为从 `academic_relevance_score` 生成 `相关度 0.xx`，并把 `academic_relevance_reason` 放到 tooltip。
- 移除了无信息量的 `Zotero match` chip。
- 加强蓝色 relevance chip 的视觉区分，并更新 CSS cache version。
- 测试和文档同步更新。

**Review**  
Codex can do directly
