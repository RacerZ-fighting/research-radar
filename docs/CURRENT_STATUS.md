# CURRENT_STATUS

> 这是后续所有 agent / Codex 会话的唯一主入口。
> 如果 README、iteration_plan、旧 handoff 与本文件冲突，以本文件为准，并在当前 PR 中补齐漂移。

## 1. 当前定位

本仓库已经从“安全博士研究方向发现系统”重定位为：

> 面向安全科研的前沿情报收集、分层消费与周期总结系统。

“研究方向发现”保留为上层输出，而不是底层唯一目标。

## 2. 现状总览

### 2.1 已经可用
- crawl / normalize / enrich / llm-relevance / score / report / run CLI 已存在
- academic / industry 双轨概念已在模型、设计文档和若干 pipeline 中落地
- daily / weekly / landscape 报告生成已存在
- gap detection / direction synthesis 已存在
- feedback event 已存在，并支持 append-only 记录
- RawFetch + canonical_id + upsert 已经提供可重跑基础
- source metadata 已集中到 `config/sources.json`
- enabled RSS source 已支持通过通用 `RSSFeedCrawler` 进入 raw JSON 链路
- curated research blog RSS 源已扩展：Trail of Bits、Google Online Security Blog、GitHub Blog Security、Assetnote Research、Bishop Fox Blog 均进入集中配置并复用通用 RSS crawler；GitHub Security Lab feed 当前返回 0 entries，暂不接入默认配置
- enabled sitemap source 已支持通过通用 `SitemapCrawler` 进入 raw JSON 链路；Anthropic News 当前走 sitemap
- enabled webpage source 已支持通过通用 `WebpageCrawler` 进入 raw JSON 链路；Brutecat / HackTron 已通过 live smoke
- DEF CON 已使用专用 talk crawler 抓取公开 speaker/talk 页面，输出进入 Industry conferences lane；crawler 会优先探测当前年份对应届数，当前 DEF CON 34 speakers 页在 2026-07-03 实测 404，因此回退展示 DEF CON 33，并在卡片上显式标记届数
- BSidesSF 已使用 AllBSides-backed fallback crawler 抓取 2026 talk recordings；官方 Sched 页面当前 requests 仍被 Cloudflare 403 阻断
- Black Hat Asia / USA 已切到官方 schedule parser：先读取 Black Hat schedule shell 中的 `sessions.json` 数据源，再解析 talk/time/speaker/track/format/location/description，并保留 `official-schedule` 标记；requests 403 时会用 `curl_cffi` Chrome impersonation + scoped `BLACKHAT_COOKIE` fallback。2026-07-03 Black Hat Asia live smoke 抓取 53 条有效议题并完成 normalize / 中文摘要 / LLM relevance / score；2026-07-04 Black Hat USA live smoke 抓取 104 条有效议题并完成 normalize / 中文摘要 / LLM relevance / score。Black Hat Europe 2026 schedule 当前未发布
- RSAC 已从集中 source 配置中移除：此前官方 RainFocus agenda 可抓取，但 session 噪声偏高，不再作为默认工业会议信号源维护；历史 RSAC artifacts 已归档出展示面
- 本地 Web Console 已可通过 `python -m src.cli web` 启动，用于查看近期结果、管理 source 配置、测试单源抓取和手动触发小范围 pipeline
- enrichment 现在默认生成中文概览摘要与中文详细内容总结，Web Console 和日报优先展示 `summary_l3`
- Web Console 的 Industry Dashboard 已拆成工业界会议、研究博客、组织发布三个子板块
- Anthropic News 的 sitemap crawler 现在会抓取详情页正文，避免仅凭标题生成摘要
- Academic 展示过滤已支持先用 Zotero 个人文献库计算相关度，再用 CSRankings faculty 数据给 arXiv 候选补充质量信号；证据写入 `score_breakdown`，不做 schema 迁移
- Academic 相关度已支持 LLM 基于 top-k Zotero evidence 做二次裁判；已有裁判结果时，展示过滤以 LLM 相关度为准，不再使用 `zotero_similarity >= 0.18` 作为相关度门槛
- Web Console 的 paper 卡片会优先展示中文详细摘要，并以 AI 凝练的研究焦点标签、LLM 相关度裁判与 CSRankings faculty / group 证据辅助判断
- Dashboard 顶部已提供 `Refresh today` 手动刷新按钮，默认抓取 daily source scope（arXiv + daily-enabled blog-like sources），并只分析目标日期相关 artifacts 后回到当天日期视图
- Web Console sidebar 已支持宽屏折叠成窄 rail，并用 localStorage 记住折叠状态；移动端保持完整导航
- Dashboard 日期控件已支持 Today / 7 days / Custom 三种视图；该范围筛选只作用于日常博客、组织更新和 arXiv，工业会议与 T1 顶会仍保持近期视图
- `daily-refresh` / `schedule-daily` 的默认 crawl scope 已收敛为 arXiv + daily-enabled blog-like sources，不再默认同步 NDSS / S&P / CCS / USENIX Security 等重型会议论文 crawler；需要时使用 `--crawl-scope all`
- Dashboard refresh 已有内存态实时进度条，显示 queued / crawl / normalize / enrich / relevance / score / report 等阶段；crawl 阶段会显示当前 source，并在交互式刷新中对单源 fail-fast
- arXiv daily fetch 已改为按 `cs.CR` / `cs.SE` / `cs.PL` 分 category 小批量抓取并去重，默认最多 30 条，避免组合 OR 查询触发 429 / timeout
- Project Zero 在当前网络环境下多个入口不稳定，保留 enabled/manual crawl，但通过 `daily-disabled` 标签排除出默认 daily refresh
- Daily report、Dashboard 和 `daily-refresh` 的日期归属现在按配置本地时区判断，默认 `Asia/Shanghai`；SQLite 中 naive datetime 视为 UTC 后再转本地日期，避免 UTC 晚间 arXiv 被归到前一天
- `daily-refresh` 会分析目标日期条目以及本次新抓取/更新的 daily-scope 条目；因此今天抓到但站点发布日期属于昨天的博客/组织文章，也会立即补齐中文摘要与相关度，Dashboard / 日报展示时仍按发布日期归属对应日期页

### 2.2 真正还缺的
- 报告层还没有完成“亲读 / 详细摘要 / 一句话 / delegate / 归档”的稳定分层
- 月报、季报尚未成为正式一等输出
- 反馈还没有真正回流成排序/triage偏好
- advisories 仍未接入
- weekly 与 landscape 的语义和命名仍有漂移
- 文档存在明显时间差与实现差异
- BSidesSF Sched 当前直接 requests 抓取返回 403；BSidesSF 已有 AllBSides recording fallback
- Black Hat Asia / USA 官方 schedule parser 依赖 scoped `BLACKHAT_COOKIE` 才能在当前命令行环境稳定越过 Cloudflare；后续需要确认 cookie 更新/轮换的运维方式是否可接受。Black Hat Europe 2026 schedule 当前未发布

## 3. 文档优先级（冲突解决顺序）

1. `docs/CURRENT_STATUS.md`
2. `AGENTS.md`
3. `docs/TARGET_SYSTEM.md`
4. `docs/TRIAGE_POLICY.md`
5. `docs/REPORT_POLICY.md`
6. 代码实现
7. `README.md`
8. `docs/iteration_plan.md`
9. 旧 handoff / 历史设计文档

说明：
- 历史设计文档仍然重要，但不再自动等于“当前行为”
- 如果代码与文档冲突，优先写清楚“当前真实行为”再决定是否改代码

## 4. 当前代码骨架（保持不动的默认基础）

### 4.1 编排层
- 顶层 Click CLI 保持不动
- `run` 仍然是默认 orchestrator
- 不新增第二套平行流程

### 4.2 数据层
- `Artifact` 保留 `summary_l1 / summary_l2 / summary_l3`
- `summary_l2` 目前视为 L2 结构化深度分析承载位
- `score_breakdown` 继续承载衍生评分/轨道元信息
- `FeedbackEvent` 继续 append-only

### 4.3 报告层
- `BaseReportGenerator` 保持
- `daily.py / weekly.py / landscape.py` 在现有基础上演进
- 新周期报告优先沿用同一 reporting 体系

## 5. 当前已确认的“文档-实现漂移”

这些问题不是 bug backlog 的边缘问题，而是当前最高优先级文档债：

### Drift A: 入口与状态数字曾分散在 README / handoff / iteration_plan
- 2026-04-09 已收敛：README 现在只承载定位、入口和稳定使用说明
- 2026-04-09 已收敛：`iteration_plan.md` 现在只承载历史/工程记录
- `handoff_2026-03-12.md` 保留为 dated snapshot，不再作为 current status

处理原则：
- 以后不要在多个地方重复维护“唯一状态”
- 把最新状态集中写到本文件

### Drift B: weekly 与 landscape 的语义不一致
- 部分文档说 landscape 取代了 original weekly
- 代码里 weekly 和 landscape 仍同时存在

处理原则：
- 保留兼容命名
- 先收敛行为，再决定是否废弃某个名字

### Drift C: 评分文档与实现存在历史版本并存
- 2026-04-09 已收敛：`iteration_plan.md` 的旧单一权重表述已降级为历史记录
- 当前实现继续按 track 切权重，并写入 `score_breakdown`

处理原则：
- 不新增 `academic_score` / `industry_score` 列
- 继续沿用 `final_score + score_breakdown.track/weights`

## 6. 当前开发原则

未来连续开发时，默认按以下顺序推进：

1. source 配置集中管理（已完成）
2. 日报展示 AI 摘要与关键词（当前收窄优先级）
3. triage 分层（暂缓）
4. 日/周报重构
5. 月/季报
6. feedback 回流
7. advisories
8. 自动化调度
9. 额外 sources

## 7. 当前明确不建议做的事

- 不要先接大量新源
- 不要把 Web Console 扩展成第二套平行 orchestrator
- 不要重写 scoring engine
- 不要把 academic / industry 合并成一个队列
- 不要先做复杂 agent orchestration
- 不要先做 schema-heavy 重构

## 8. 下一阶段推荐起手工单

当前有两条可并行但应保持顺序清晰的推进线：

### 8.1 分层消费主线

用户已明确：短期不需要 `read_original / one_line / delegate` 分层 bucket。先做最小有效日报：

1. `RR-017` 日报展示 AI 摘要与关键词（已完成）

完成后再回到以下长期分层路线：

优先连续做这 4 张票：

1. `RR-002` 多层摘要与 delegate briefing 语义落位
2. `RR-003` triage 引擎
3. `RR-004` 日报重构
4. `RR-005` 周报与 landscape 收敛

`RR-001` 已完成。只有上面这 4 张票继续收敛，后面的月/季报与 feedback 回流才会真正稳。

### 8.2 个性化相关度主线

用户已确认：
- Zotero 导出格式先用 Better CSL JSON
- arXiv 采用宁缺毋滥策略
- 不要求用户先手工划分 core / background / low-priority
- Zotero 作为个人文献语料库：外部候选先检索 top-k 相似 Zotero 条目，再由 agent 结合 Zotero 证据和作者/课题组质量信号做判断

推荐先新增并执行：

1. `RR-011` Zotero 相似检索与 agent 相关度裁判
2. `RR-012` arXiv 质量证据与宁缺毋滥筛选
3. `RR-024` Web/日报的 academic 论文详细呈现（将 arXiv 小批量摘要从 Dashboard 扩展到 Daily/Weekly）

这条主线可在 `RR-002/RR-003` 前后推进，但第一阶段仍应避免 schema-heavy 重构，优先把结果写入 `score_breakdown`。

## 9. Assumptions

默认假设：
- 单用户
- 本地 SQLite 持久化继续保留
- CLI 是主入口
- source metadata 以 `config/sources.json` 为集中入口；旧 crawler class 可保留但不一定注册为当前 source
- 默认全量 crawl 会跳过单个失败 source 并继续处理其他 source；指定单 source crawl 仍会明确失败
- monthly / quarterly 先走 markdown 文件，不做数据库大重构
- T4 个人源只有在用户提供 URL 后才接入
- advisories 在接入前始终作为独立 industry 子类，不与 academic 混排

## 10. Work Log

> 每做完一个工单都更新这里。不要只更新代码。

- 2026-06-16: 准备处理 RR-013 Source 配置集中管理；假设本次不删除旧 crawler class、不新增 schema、不新增外部依赖，只把 source metadata / enabled / tier 收敛到集中 JSON 配置。
- 2026-06-16: 完成 RR-013 Source 配置集中管理；新增 `config/sources.json` 和 source config loader，registry 默认只加载 enabled crawler source，normalization 从集中配置推断 tier；测试通过。
- 2026-06-16: 调整集中 source 清单：启用 OpenAI / Anthropic，移除 Cloudflare / Trail of Bits 配置项，新增 Brutecat / HackTron / Black Hat USA/Asia/Europe / DEF CON / RSAC / BSidesSF；非 crawler adapter 目前只作为配置入口，不参与默认 crawl。
- 2026-06-16: 完成 RR-014 配置驱动 RSS ingest；集成 feedparser，新增通用 RSSFeedCrawler，enabled RSS source 可进入 crawl registry，webpage adapter 留待后续。
- 2026-06-16: 完成 RR-015 配置驱动 sitemap ingest；Anthropic News 从 RSS 改为 sitemap，使用官方 sitemap + `/news/` 过滤，live smoke 可返回 5 条 news item。
- 2026-07-01: 准备处理 RR-016 配置驱动 webpage ingest 与 live smoke；涉及新 source 接入和 crawler 行为变化，不涉及 schema 变更、scoring/triage 阈值变化或报告命名兼容策略变化。
- 2026-07-01: 完成 RR-016；新增通用 WebpageCrawler，webpage adapter 进入默认 blog registry，全量 crawl 对单源失败改为 skip-and-continue；live smoke 确认 OpenAI / Anthropic / Brutecat / HackTron / DEF CON / BSidesSF 可返回资讯，Black Hat 与 RSAC 当前 403；使用真实抓取数据 + deterministic LLM stub 验证 normalize → enrich → signal extraction → score → daily report 链路通过。
- 2026-07-01: 准备处理 RR-017 日报展示 AI 摘要与关键词；用户确认短期不做分层 bucket，本次不涉及 schema、scoring/triage 阈值、新 source 或报告文件命名变化。
- 2026-07-01: 完成 RR-017；日报推荐条目现在优先展示 AI 生成的 `summary_l1`，并显示 `tags` 作为关键词；没有 AI 摘要时回退 raw abstract，没有 tags 时显示占位。
- 2026-07-01: 完成 OpenAI-compatible streaming gateway 配置验证；本地 `.env` 已配置 OpenAI provider 指向内网 `/v1/responses` 网关和 `gpt-5.4`，新增 provider 兼容开关以支持 input list、SSE stream、store=false、禁用 unsupported generation params；LLMClient 与单条 EnrichmentPipeline live smoke 均通过；批量 enrichment 触发网关 rate limit，已新增 `enrich --request-delay` 用于顺序慢速处理。
- 2026-07-01: 准备处理 RR-019 Local Web Console；假设采用 FastAPI + Jinja + 原生 CSS，默认本地绑定，复用现有 SQLite / `config/sources.json` / pipeline，不新增 schema、不新增平行 orchestrator。
- 2026-07-01: 完成 RR-019；新增 FastAPI + Jinja 本地 Web Console，支持 Dashboard / Sources / Runs / Artifacts，source 管理写回集中配置且新 source 默认 disabled，后台任务复用现有 pipeline；路由测试和截图检查通过。
- 2026-07-01: 准备处理 RR-020 中文详细内容总结；假设复用 `summary_l3` 承载详细中文总结，不新增 schema、不改 scoring、不改 source 配置，但会改变 enrichment 和日报/Web 展示语义。
- 2026-07-01: 完成 RR-020；摘要 prompt 改为中文详细总结，EnrichmentPipeline 默认版本升级为 `v2-cn-detailed` 并写回 `summary_l3`，日报与 Web 优先展示详细内容总结。
- 2026-07-01: 准备处理 RR-021 Industry Dashboard 子板块拆分；假设仅改 Web Console 展示分类，复用 `config/sources.json` 的 tags/slug/source name，不新增 schema、不改 pipeline。
- 2026-07-01: 完成 RR-021；Dashboard 的 Industry 区域拆成工业界会议、研究博客、组织发布三个子板块，并用测试覆盖分类展示。
- 2026-07-01: 准备处理 RR-022 Anthropic sitemap 详情页正文可见性修复；用户发现 Anthropic 摘要仍像标题推测，本次不新增 source、不改 schema、不改 scoring，只修复 sitemap crawler 的正文可见性和 enrichment 缓存键。
- 2026-07-01: 完成 RR-022；确认 Anthropic 详情页可访问且 `<article>` 有正文，修复 SitemapCrawler 抓取详情页 excerpt，并让 enrichment cache key 纳入正文指纹；已重新抓取 Anthropic News 20 条并重跑摘要。
- 2026-07-01: 准备处理 RR-023 低相关展示过滤与 arXiv 小批量呈现；本次涉及 report/Web 展示语义、scoring fallback、arXiv source 参数和 live source 验证，不做 schema 迁移。
- 2026-07-01: 完成 RR-023；日报和 Web 统一隐藏 `llm_relevance_score < 0.4` 的最低相关 artifact，`score` 在无 Profile 时仍使用 LLM relevance；arXiv 默认从集中配置读取 `max_results=100`，live crawl 入库 100 条，并对 5 条最新 arXiv 生成中文摘要和 relevance，Dashboard 已显示相关 prompt injection 论文。
- 2026-07-01: 准备处理 RR-025 Artifact 浏览按时间分页；假设继续使用 SQLite，不新增存储或 schema，仅改 Web 查询、分页控件和文档说明。
- 2026-07-01: 完成 RR-025；`/artifacts` 继续使用 SQLite artifact 表，按 `published_at`/`created_at`/`id` 倒序展示，默认每页 20 条，支持 `track=all|academic|industry&page=N`，并保持低相关隐藏不计入页数。
- 2026-07-02: 准备处理 RR-026 Dashboard 双列比例与时间排序修正；依据用户截图，假设仅改 Web 展示 CSS 和 Dashboard 查询排序，不改 schema、不改 source、不改 scoring 阈值。
- 2026-07-02: 完成 RR-026；Dashboard 候选排序改为 `published_at desc nulls last, created_at desc, id desc`，宽屏布局从固定 360px 右栏改为明确的 1:1 双列，并给 CSS 链接加版本参数避免浏览器继续使用旧样式。
- 2026-07-02: 准备处理 RR-027 Academic Zotero/CSRankings 首轮过滤；本次涉及 academic 展示过滤语义和 Zotero/CSRankings 外部数据读取，不做 schema 迁移、不改 source 配置、不改基础 scoring engine。
- 2026-07-02: 完成 RR-027；新增 Zotero Better CSL JSON / Zotero API 语料加载、top-k 相似检索、CSRankings faculty 质量信号和 `academic-filter` CLI，展示层会隐藏已评估但 Zotero 低相关的论文，以及已评估但质量信号不足的 arXiv 论文。
- 2026-07-02: 准备处理 RR-028 Academic evidence chips 展示；本次仅改 Web 展示和已存在 `score_breakdown` 证据的 presenter，不改 schema、不改 source、不改 scoring/triage 阈值。
- 2026-07-02: 完成 RR-028；paper 卡片现在以 chip 展示 artifact topic、Zotero 相似度、Zotero 命中 topic 或相关论文标题，以及 CSRankings faculty/group 命中证据；Zotero match evidence 新增 `topics` 字段并提升 academic filter version 以支持重算。
- 2026-07-02: 准备处理 RR-029 Academic AI focus labels；用户指出 `Zotero 0.18` 和原始 Zotero topic 太难读/太泛，本次新增可重跑的 LLM 标签派生步骤，不改 schema、不改过滤阈值、不接新 source。
- 2026-07-02: 完成 RR-029；新增 `academic-labels` CLI 和 `AcademicLabelPipeline`，将 AI 凝练的具体研究焦点写入 `score_breakdown.academic_focus_labels`；Web paper 卡片优先展示这些 focus chips，Zotero 分数降级为 tooltip 中的 raw similarity，页面只显示 `Zotero match`。
- 2026-07-02: 准备处理 RR-030 Paper 卡片摘要与 Zotero keyword 收敛；本次只改 Web 展示和 Zotero evidence 数量上限，不改 schema、不改过滤阈值、不接新 source。
- 2026-07-02: 完成 RR-030；paper 卡片摘要改为优先展示较短中文 `summary_l1`，缺少中文摘要时用 `academic_focus_labels` 合成中文研究焦点句，博客仍保留详细 `summary_l3`；Zotero match evidence 的 `topics` 从最多 5 个收敛到最多 3 个，并已重跑 `academic-filter` 更新现有 100 条 paper。
- 2026-07-02: 准备处理 RR-031 Paper 摘要展示回调与 Zotero top-k 诊断；用户反馈 paper 卡片不应把研究焦点当摘要，本次仅修正 Web 展示和文档说明，不改 schema、不改过滤阈值、不接新 source。
- 2026-07-02: 完成 RR-031；paper 卡片恢复为中文详细摘要优先，只有缺少中文摘要时才用 `academic_focus_labels` 兜底；已对当前 18 篇 displayable arXiv paper 补跑中文 enrichment，页面 smoke 确认 JETO-Bench 等条目显示完整中文摘要；当前 Zotero 检索为 top-k=5，展示过滤只看 top1 token cosine similarity，0.18 阈值下 100 篇 arXiv 有 29 篇通过 Zotero，相比 0.25 阈值只剩 1 篇。
- 2026-07-02: 准备处理 RR-032 Zotero 全量读取与 LLM 相关度裁判；用户确认“没内容没关系”，Academic 相关度应由 LLM 基于 top-k Zotero evidence 判断，而不是只靠 0.18 词面相似度；本次不做 schema 迁移、不接新 source，但会新增更严格的已裁判 paper 展示过滤。
- 2026-07-02: 完成 RR-032；Zotero API 默认读取上限从 500 提升到 2000 并支持 `ZOTERO_MAX_ITEMS`，live check 确认配置的 Zotero corpus 可读取；新增 `academic-judge` LLM 裁判 pipeline/CLI，已对一批 arXiv 候选写入裁判结果，相关候选叠加 arXiv 质量门槛后进入 Web 展示，且展示项均有中文 `summary_l3`。
- 2026-07-02: 准备并完成 RR-033 Academic evidence chip 语义收敛；用户指出 `Zotero match` 无信息量且 chip 颜色语义不清，本次仅改 Web presenter/CSS/文档，不改 schema、不改过滤规则；paper 卡片移除 `Zotero match`，改显示 LLM 裁判 `相关度 0.xx`，橙色保留为研究焦点，绿色保留为质量证据。
- 2026-07-02: 准备处理 RR-034 Web Console Kami 视觉主题化；用户希望前端换成 tw93/Kami 风格，本次仅改 Web Console 的 CSS/轻量模板文案与静态资源版本，不涉及 schema、scoring/triage 阈值、新 source 或报告语义变化。
- 2026-07-02: 完成 RR-034；Web Console 全局样式切换为 Kami 风格的 parchment / ivory / ink-blue / warm neutral，sidebar、metric、artifact card、chip、button、form、pagination 已统一纸张层级；CSS cache version 更新为 `20260702-kami-theme`，Web route smoke 通过。当前环境未安装 Playwright，未能做桌面/手机截图验证。
- 2026-07-02: 准备处理 RR-035 Dashboard 博客日期筛选；用户希望 dashboard 加日期按钮并默认展示当天最新博客，本次仅改 Web Console 展示筛选与测试，不涉及 schema、scoring/triage 阈值、新 source 或报告语义变化；Academic papers 和 Industry conferences 不受日期筛选影响。
- 2026-07-02: 完成 RR-035；Dashboard 增加 `date=YYYY-MM-DD` 日期控件，默认当天；Research blogs 与 Organizations 板块只显示所选日期条目，Academic paper lane 与 Industry conferences lane 继续显示近期排序结果；Web 测试与 route smoke 通过。
- 2026-07-02: 准备处理 RR-036 Dashboard arXiv 日期筛选；用户希望 arXiv 也按 dashboard 日期筛选，本次仅扩展现有日期筛选到 T2 arXiv，不涉及 schema、scoring/triage 阈值、新 source 或报告语义变化；安全四大顶会论文仍不受日期筛选影响。
- 2026-07-02: 完成 RR-036；Dashboard 日期控件文案改为 `Daily date`，T2 arXiv paper 现在按所选日期筛选，T1 安全四大顶会论文继续按近期排序展示；博客和组织更新的日期筛选保持不变，Web 测试与 route smoke 通过。
- 2026-07-02: 准备并完成 RR-037 Daily Markdown 日期视图与每日自动刷新；Daily Markdown 现在按目标日期展示普通博客、组织更新和 arXiv，保留近期工业会议 topic 与顶会论文动态；新增 `daily-refresh` 一次性刷新命令和 `schedule-daily` 每日定时刷新命令，不涉及 schema、scoring/triage 阈值或新 source。
- 2026-07-02: 准备并完成 RR-038 Dashboard 当天手动刷新入口；Dashboard header 移除跳转 Runs/Sources 的两个按钮，改为 `Refresh today` 后台触发轻量 daily refresh 并回到当天日期视图；默认不做全量 crawl，避免一次点击同步大量会议详情页，本次不涉及 schema、scoring/triage 阈值、新 source 或报告命名变化。
- 2026-07-02: 准备并完成 RR-039 日常 crawl scope 与 Dashboard refresh 进度；`daily-refresh` / `schedule-daily` 默认 crawl scope 改为 daily，只抓 arXiv 与 blog/webpage 源，安全四大会议 crawler 需显式 `--crawl-scope all`；Dashboard 新增 `/dashboard/refresh-status` 与进度条轮询展示。本次不涉及 schema、scoring/triage 阈值或新 source。
- 2026-07-02: 准备并完成 RR-040 Dashboard refresh 语义修正；Dashboard `Refresh today` 现在会 crawl daily source scope，并将 enrichment / LLM relevance / academic personalization 限制到目标日期相关 artifacts，避免一次刷新补全历史缺摘要队列。本次不涉及 schema、scoring/triage 阈值或新 source。
- 2026-07-02: 准备并完成 RR-041 Dashboard crawl 进度与 fail-fast；用户发现 refresh 卡在 10%，定位为 arXiv 429/timeout 与 Project Zero retry 导致 crawl 阶段长时间无细分进度。Dashboard daily crawl 现在排除 industry-conference webpage 源，逐 source 更新进度，并使用短 timeout / 0 retry 快速跳过单源失败。本次不涉及 schema、scoring/triage 阈值或新 source。
- 2026-07-02: 准备并完成 RR-042 Daily source fetch 稳定性修复；用户指出应先修数据源 fetch 不稳定。arXiv 改为逐 category 小批量查询并去重，默认 daily 上限从 100 收敛到 30；Project Zero 因当前环境下官方域名和 Blogspot feed 均不稳定，保留手动抓取但通过 `daily-disabled` 排除出默认 daily refresh。本次不涉及 schema、scoring/triage 阈值或新 source。
- 2026-07-03: 准备并完成 RR-043 Daily/Dashboard 本地日期边界修复；用户发现 refresh 完成并生成 `2026-07-02.md` 但 Dashboard 没有条目。根因是 arXiv 的 UTC 晚间发布时间在 Asia/Shanghai 已属于 7 月 2 日，但旧逻辑直接用 UTC/naive `.date()` 比较。新增本地时区 helper，Dashboard / Daily / daily-refresh target selection 统一按 `Asia/Shanghai` 本地日判断；重新生成 2026-07-02 日报后今日 arXiv 显示 8 篇。本次不涉及 schema、scoring/triage 阈值或新 source。
- 2026-07-03: 准备并完成 RR-044 Daily refresh 新抓取旧发布日期分析修复；用户发现 Anthropic 文章正文已抓到但没有中文 summary。根因是 `daily-refresh` 只分析目标日期 artifact，导致今天抓到但发布日期为昨天的 Anthropic 条目被 normalize/score 后跳过 enrichment。现在目标集合包含目标日期条目和本次新 normalize/update 的 daily-scope 条目，日报候选加载也按 `published_at || created_at` 的展示时间取数，展示日期仍按发布日期归属。本次不涉及 schema、scoring/triage 阈值或新 source。
- 2026-07-03: 准备并完成 RR-045 Web Console sidebar 折叠；依据用户截图，左侧固定 sidebar 在窄窗口中过宽，压缩阅读区。本次仅改 Web 模板/CSS/轻量 JS，新增宽屏折叠 rail、状态持久化和 CSS cache version，移动端保持完整导航；不涉及 schema、scoring/triage 阈值、新 source 或报告语义变化。
- 2026-07-03: 准备并完成 RR-046 Dashboard 日期范围切换；用户只需要“只看当天 / 最近 7 天 / 自定义日期”，不需要已读/隐藏等反馈功能。本次仅改 Web Dashboard 查询参数、筛选逻辑、模板控件和 CSS；`range=today|7d|custom` 只影响日常博客、组织更新和 arXiv，工业会议与 T1 顶会继续近期展示。不涉及 schema、scoring/triage 阈值、新 source 或 Markdown 报告增强。
- 2026-07-03: 准备处理 RR-047 Industry conference agenda ingest 第一阶段；用户同意先做 DEF CON 专用 talk parser 打通工业会议议题链路。假设本次不引入 browser 依赖、不处理 Black Hat/RSAC/BSidesSF 403 源、不改 schema；新抓取内容继续走 blog-like artifact、`industry-conference` tag、现有 LLM relevance 和 Dashboard conference lane。
- 2026-07-03: 完成 RR-047；新增 `DefconTalkCrawler` 解析 DEF CON 公开 speaker/talk 页面，`defcon` source 从 generic webpage 切到 crawler-backed，live crawl 抓到 20 条 DEF CON 33 talks；已对 20 条 talk 入库、补中文摘要和 LLM relevance，Dashboard Industry conferences lane 现在按 final_score 展示相关议题。本次不涉及 schema 或 browser 依赖；Black Hat/RSAC/BSidesSF Sched 仍作为后续 browser-backed/官方导出策略处理。
- 2026-07-03: 准备处理 RR-047 后续修正；用户指出 DEF CON 会议届数应显式标记，并要求确认 DEF CON 34 是否已发布。本次只修正 DEF CON crawler 的 current-year fallback 与 Web 展示标记，不新增 source、不改 schema、不改 scoring/triage 阈值、不扩大 daily refresh 默认范围。
- 2026-07-03: 完成 RR-047 后续修正；live check 确认 `dc-34-speakers.html` 当前返回 404，`dc-33-speakers.html` 返回 200 且包含 talk 节点。`DefconTalkCrawler` 现在默认先尝试当前年会 DEF CON 34，失败或无 talk 节点时回退 DEF CON 33；raw item 增加 `defcon-33` 这类届数 tag，Web artifact 卡片会用 `external_ids.conference` 显示 `DEF CON 33`。
- 2026-07-03: 准备处理 RR-048 BSidesSF conference fallback ingest；live check 显示 Black Hat、RSAC 与 BSidesSF Sched 仍被 Cloudflare/403 阻断，BSidesSF 主站可访问但只跳转 Sched。假设本次不引入 browser 依赖、不新增 schema、不改 scoring/triage 阈值；先将 BSidesSF 切到 AllBSides API 的 2026 talk-recording fallback，并明确标注 fallback 来源。
- 2026-07-03: 完成 RR-048；新增 `AllBsidesTalkCrawler` 并将 `bsidessf` 切到 crawler-backed fallback，使用 `api.allbsides.com/v1/talks?organizer=bsidessf&year=2026` 抓取 2026 talk recordings。Live crawl 返回 12 条，normalize 创建 12 条 artifact；已对 12 条跑 LLM relevance 和 score，仅 AI coding agent talk 通过展示过滤，并已补中文摘要。顺手修复 enrichment 覆盖结构标签的问题，并让 Dashboard conference lane 保留多会议源可见性；页面 smoke 已显示 `BSidesSF 2026`。Black Hat / RSAC 仍等待 browser-backed 或官方导出策略。
- 2026-07-03: 准备处理 RR-049 Browser-use conference crawler；用户明确要求先做 browser-use，不走普通 Playwright fallback。本次会新增可选 browser-use 依赖和专用会议 crawler，把 Black Hat / RSAC 从 generic webpage 切到 browser-use-backed crawler；不涉及 schema、scoring/triage 阈值或 daily refresh 默认范围变化。
- 2026-07-03: 完成 RR-049；新增 `BrowserUseConferenceCrawler`，将 Black Hat USA/Asia/Europe 与 RSAC 改为 `adapter=crawler`、`crawler=browser-use-conference`，agent 输出固定 JSON 后复用现有 blog-like raw/normalize 链路。已安装 `browser-use` 与 `socksio` 到 venv，并补充 `.env.example`；live smoke 确认 browser-use 成功启动浏览器并打开 Black Hat Asia，但当前 `OPENAI_BASE_URL=/v1/responses` 网关不支持 browser-use 所需 `/v1/chat/completions`，因此 crawler 现在会 fail-fast 提示配置 `BROWSER_USE_BASE_URL`。相关测试通过。
- 2026-07-03: 完成 RR-050；按用户决策将 browser-use 会议 crawler 的推荐模型收敛为 DashScope `qwen-vl-max`，`.env.example` / runbook 改为 DashScope 示例；crawler 在 DashScope endpoint 下未显式配置模型时默认 `qwen-vl-max`，且跨 provider 时要求独立 `BROWSER_USE_API_KEY`，避免误用主 Responses API key。
- 2026-07-03: 准备处理 RR-051 Black Hat Asia 官方 schedule parser；用户确认浏览器可直接看到 `blackhat.com/asia-26/briefings/schedule/index.html`，不希望依赖第三方镜像。本次涉及 source 获取策略变化，不涉及 schema、scoring/triage 阈值或 report 文件命名变化；假设只将 Black Hat Asia 从 browser-use 切到官方 HTML parser，USA/Europe/RSAC 暂不扩张。
- 2026-07-03: 完成 RR-051；新增 `BlackHatScheduleCrawler`，解析官方 Black Hat Asia 2026 schedule 的 title/speaker/track/format/location/time，并过滤茶歇、overflow、注册等非议题条目；`blackhat-asia` source 改为 `crawler=blackhat-schedule`，输出继续走 blog-like raw artifact 与 `industry-conference` lane。单元测试通过；live smoke 当前返回 HTTP 403，crawler 会 fail-fast 提示提供 scoped `BLACKHAT_COOKIE`，不自动读取浏览器 cookie。
- 2026-07-03: 完成 RR-051 后续验证与实现收敛；确认官方 schedule shell 内含 `var dataUrl = 'sessions.json'`，`sessions.json` 是稳定官方议题数据源。新增 `curl_cffi` Chrome impersonation fallback，使用 scoped `cf_clearance` 即可抓取 JSON，不需要 GA/广告/统计 cookie；live crawl 抓到 53 条有效 Black Hat Asia 2026 议题，已 normalize 入库、补中文摘要、跑 LLM relevance 和 score。旧误入库的 `Briefings Refreshment Break` 已标记 `rejected`，parser 增加 refreshment break 过滤。
- 2026-07-04: 准备处理 RR-052 Black Hat USA 官方 schedule 接入与 RSAC 官方 agenda 探测；本次涉及 source 获取策略变化，不做 schema 迁移、不改 scoring/triage 阈值、不改报告命名。假设 Black Hat USA 可复用 Black Hat 官方 `sessions.json` parser，Black Hat Europe 2026 schedule 未发布前保持 browser-use，RSAC 继续调研官方 RainFocus agenda 接口。
- 2026-07-04: RR-052 阶段性完成 Black Hat USA 官方 schedule 接入；`blackhat-usa` 已从 browser-use 切到 `blackhat-schedule`，live crawl 从官方 `sessions.json` 抓到 104 条有效议题，已 normalize 入库并补齐中文摘要、LLM relevance 和 final score。OpenAI gateway 短暂 502 后恢复，摘要与相关度已重试完成；RSAC 官方 RainFocus agenda crawler 仍作为后续工作。
- 2026-07-04: RR-052 继续完成 RSAC 官方 RainFocus agenda crawler；抓包确认 `events.rsaconference.com/api/sessions` 可用，新增 `RSACAgendaCrawler`，`rsac` source 从 browser-use 切到 `rsac-agenda`，live crawl 抓取 160 条有效议题并 normalize 入库、重跑 score。当前 OpenAI gateway 再次返回 502，因此 RSAC 中文摘要和 LLM relevance 暂未补齐。
- 2026-07-06: 完成 RR-053 RSAC source 移除；用户确认 RSAC 噪声过高，已从 `config/sources.json` 和默认 registry 移除，Dashboard / daily 不再把 RSAC 作为会议源，历史 `RSA Conference` artifacts 已归档出展示面；保留 `RSACAgendaCrawler` 代码与 fixture 测试，便于未来明确需要时恢复。
- 2026-07-06: 完成 RR-054 未分析会议条目展示过滤；修复 BSidesSF 重复 raw artifact 绕过低相关判断的问题。工业会议条目现在必须已有 AI 摘要或 LLM relevance 判断才进入 Dashboard / Daily，避免展示“暂无中文摘要”的 raw agenda/talk 卡片。
- 2026-07-06: 准备处理 RR-055 安全四大 Paper 恢复与展示；当前本地 SQLite 只有 arXiv paper，没有 NDSS / IEEE S&P / ACM CCS / USENIX Security active artifact。假设本次不新增 schema、不改 scoring/triage 阈值、不新增 source，先复用现有 T1 crawler、normalization、Zotero/CSRankings/LLM academic personalization 链路恢复小范围 corpus 并验证 Dashboard 展示。
- 2026-07-06: 完成 RR-055；live crawl 入库 IEEE S&P 2026 254 篇、NDSS 2026 265 篇、USENIX Security 2026 376 篇、ACM CCS 2025 353 篇（CCS 2026 官方页/DBLP 均未公开）。已对每个会议 Zotero top 6 候选运行 `academic-judge`、中文 enrichment 和 `academic-labels`，共 24 篇 T1 paper 进入展示候选；T1 paper 现在必须有 LLM academic judgment 才能显示，Dashboard Academic lane 使用更宽 paper 候选池和来源多样性，7-day 页面已显示 USENIX / S&P / NDSS / CCS 且无“暂无中文摘要”。
- 2026-07-06: 准备处理 RR-056 安全四大年份收敛与 Artifact 搜索；用户确认 CCS 不用 2025，没有 2026 就先为空。本次不新增 source、不改 schema、不改 scoring/triage 阈值，只归档本地 CCS 2025 artifacts，并给 Artifact 浏览页增加搜索框，默认空搜索展示全部。
- 2026-07-06: 完成 RR-056；本地 353 条 ACM CCS 2025 T1 paper 已归档，Dashboard / Artifacts 不再用 2025 顶替 CCS 2026。Artifact 浏览页新增 `q` 搜索框，默认空搜索展示当前 track 下全部 displayable artifacts，搜索命中 title / source / summary / tags / academic focus labels，并保留分页参数。
- 2026-07-06: 准备处理 RR-057 Dashboard 搜索框；用户澄清搜索框应加在 Dashboard 首页。本次不新增 schema、不改 source、不改 scoring/triage 阈值，只把现有 artifact 搜索能力接入 Dashboard 卡片过滤，并保留日期范围语义。
- 2026-07-06: 完成 RR-057；Dashboard 现在支持 `q` 搜索框，空搜索保持默认视图，非空搜索会过滤当前日期范围下的 academic / industry 卡片；Today / 7 days / Custom 日期控件会保留搜索词，Clear 会回到当前范围的未搜索视图。
- 2026-07-06: 准备并完成 RR-058 Curated research blog RSS expansion；用户指出博客系统数据源偏少。本次新增 Trail of Bits、Google Online Security Blog、GitHub Blog Security、Assetnote Research、Bishop Fox Blog 五个 enabled RSS source，全部复用现有 RSS crawler，不新增 schema、不改 scoring/triage 阈值；GitHub Security Lab feed 当前返回 0 entries，暂不纳入默认配置。
- 2026-06-16: 准备处理 Zotero 个性化相关度路线的文档落位；假设本次只新增设计文档和 backlog，不涉及 schema 变更、scoring 阈值变更、新 source 接入或 report 文件兼容策略调整。
- 2026-06-16: 完成 Zotero relevance 简化方案落位：Better CSL JSON 作为输入，Zotero 作为检索语料，agent 结合 top-k Zotero 证据与作者/课题组质量信号做判断；新增 RR-011/RR-012。
- 2026-04-09: 准备处理 RR-001 的 iteration_plan 收敛与旧文档清理；假设只删除明确的草稿/垃圾文件，不删除仍有历史参考价值的 dated 文档。
- 2026-04-09: 完成 iteration_plan 历史化改写、PR template 建立、rewrite notes 清理与 `.DS_Store` 删除；RR-001 进入完成状态。
- 2026-04-09: 准备处理 RR-001 的 README 重写；假设 `docs/CURRENT_STATUS.md` 为唯一真值入口，本次不涉及 schema 变更、scoring / triage 阈值变化、新 source 接入或 report 文件兼容策略调整。
- 2026-04-09: 完成 README 重写，使外部入口改为“前沿情报收集 + 分层消费 + 周期总结”，并明确 `CURRENT_STATUS` 为唯一入口；本次仅做文档收敛，不改代码行为。
- 2026-04-09: 建立新的仓库定位、文档入口、triage/report/source/backlog/rules 基线。
