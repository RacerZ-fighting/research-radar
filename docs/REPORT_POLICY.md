# REPORT_POLICY

## 1. 总原则

报告是主产品，而不是附属物。所有 pipeline 最终都要服务报告输出。

报告必须做到：
- 低维护
- 可重跑
- 结构稳定
- 学术 / 工业分开
- 一眼能看出“我该做什么”

## 2. 报告类型

### 2.1 Daily
目标：5–10 分钟。
回答问题：
- 今天有什么值得注意？
- 短期：每条值得注意内容的 AI 摘要和关键词是什么？
- 长期：哪些要亲读？
- 长期：哪些只看一句话？
- 长期：哪些应该 delegate？

### 2.2 Weekly
目标：30–60 分钟。
回答问题：
- 这周 academic frontier 是什么？
- 这周 industry signal 是什么？
- 哪些是跨轨道 gap？
- 下一周读什么？

### 2.3 Monthly
目标：60–90 分钟。
回答问题：
- 哪些趋势稳定存在？
- 哪些 sources 真有用？
- 哪些 delegate 真的节省了时间？
- 哪些候选方向应升级为研究池？

### 2.4 Quarterly
目标：1–2 小时。
回答问题：
- 哪些方向值得进入季度研究路线图？
- 哪些 source 应保留、扩展、淘汰？
- 哪些主题是阶段性噪音，哪些是真正可持续方向？

## 3. 每种报告都必须遵守的结构规则

1. 先 academic，再 industry，最后 cross-track synthesis
2. 每个 track 内再按 triage bucket 分组
3. 不做 academic + industry 混排 Top-N
4. 每个 bucket 都有数量上限
5. 空 section 也要明确输出“暂无”
6. 所有生成文件都是 Markdown
7. 报告优先输出可执行下一步，而不是堆信息

## 4. Daily 报告结构

当前短期结构：

1. Header / meta
2. 今日博客推荐（目标日期当天普通研究博客）
   - 来源
   - 发布日期
   - 相关度
   - URL
   - 内容总结（优先 `summary_l3`，再回退 `summary_l1` / raw abstract）
   - 关键词（来自 `tags`）
3. 今日组织更新（目标日期当天 OpenAI / Anthropic 等组织发布）
   - 来源
   - 发布日期
   - 相关度
   - URL
   - 内容总结
   - 关键词
4. 今日 arXiv（目标日期当天通过展示过滤的 T2 arXiv paper）
   - 来源
   - 发布日期
   - 相关度
   - URL
   - 内容总结（优先中文 `summary_l3` / `summary_l1`）
   - 关键词 / focus labels
5. 近期工业会议 topic（不按目标日期硬过滤）
6. Advisories 占位
7. 论文动态（T1 顶会新增提示，不列完整标题）
8. Today stats

Daily 与 Web Dashboard 的日期语义保持一致：
- blogs / organizations / arXiv 按 `target_date` 展示
- T1 conference paper 与 industry conference topic 作为低频更新提示，保留近期视图，不因当天无新增而完全空掉

当前 Daily/Web 展示会应用共享 relevance filter：
- 已有 `llm_relevance_score` 且 `< 0.4` 的 artifact 默认不展示
- 没有 LLM relevance 的旧 artifact 暂不隐藏，避免未分析内容被误删
- 对已经运行过 `academic-judge` 的 academic artifact，LLM 判定不相关或 `academic_relevance_score` 低于当前门槛的论文默认不展示
- 对尚未运行 `academic-judge` 但已经运行过 `academic-filter` 的 academic artifact，默认不展示；相关度最终由 LLM 基于 top-k Zotero evidence 判断
- T1 conference paper 必须有 `academic_relevance_judged=true` 才进入 Daily/Web 展示，避免安全四大 raw corpus 直接刷屏
- 对已经运行过 `academic-filter` 的 arXiv artifact，`academic_quality_score` 低于当前阈值的论文默认不展示
- `0.4` 视为弱相关/边缘信号，先保留给用户判断

Academic 个性化过滤的派生证据存放在 `Artifact.score_breakdown`，包括：
- `zotero_similarity`
- `zotero_matches`
- `academic_relevance_judged`
- `academic_relevance_score`
- `academic_relevance_reason`
- `academic_quality_score`
- `academic_quality_signals`
- `academic_focus_labels`

Web Console 的 paper 卡片会把这些证据压缩成可扫读 chips：
- AI focus：来自 `academic_focus_labels`，优先展示具体研究问题/对象/方法
- LLM relevance：页面显示 `相关度 0.xx`，tooltip 放中文裁判理由
- 知名度/课题组证据：来自 `academic_quality_signals.matched_faculty`

如果尚未运行 `academic-labels`，paper 卡片可退回到少量非泛化 `Artifact.tags` 或 Zotero 证据；一旦有 AI focus labels，就不再展示 `Computer Science - ...` 这类泛 topic。

Paper 卡片摘要优先使用中文 `summary_l3`，让卡片仍以内容摘要为主；如果缺少中文详细摘要，则回退中文 `summary_l1`。如果 paper 暂无中文 summary，则用 `academic_focus_labels` 合成一句中文研究焦点摘要，而不是直接展示英文 abstract。Industry/blog 卡片同样优先使用 `summary_l3` 作为详细内容总结。Zotero match evidence 中每条相关 Zotero item 的 `topics` 最多保留 3 个。

未评估的旧 T2 arXiv artifact 暂不按 Zotero / CSRankings 隐藏，避免在缺少 Zotero 配置时误删展示结果；T1 conference paper 例外，必须先完成 LLM academic judgment。

建议固定结构：

1. Header / meta
2. Academic
   - Must read original
   - Detailed summary
   - One-line watchlist
   - Delegate to agent
3. Industry
   - Must read original
   - Detailed summary
   - One-line watchlist
   - Delegate to agent
4. Advisories（如果未接入则明确占位）
5. Today stats
6. Carry-over notes（可选）

Daily 中不输出完整 candidate directions，只允许：
- “本条已进入本周 gap shortlist”
- “本条已放入 delegate queue”

## 5. Weekly 报告结构

建议固定结构：

1. Header / week meta
2. Academic frontier
3. Industry signals
4. Cross-track gaps
5. Candidate directions shortlist
6. Must-read queue for next week
7. Delegate queue for next week
8. Feedback snapshot
9. Stats

Weekly 是用户主周报。

## 6. Landscape 的兼容策略

在兼容期内：

- `landscape` 仍保留
- 它可以作为：
  - `weekly` 的战略版
  - 或 `weekly` 的兼容别名
- 但不能继续和 `weekly` 各说各话

兼容期建议：
- `weekly`：主周报
- `landscape`：可选的战略附录/兼容输出
- 如果两个文件都生成，必须共享同一 triage / report policy

## 7. Monthly 报告结构

建议固定结构：

1. 本月最重要的 academic themes
2. 本月最重要的 industry pain signals
3. 重复出现的 gaps
4. 候选方向变化（新增 / 上升 / 下降 / 移除）
5. 阅读 ROI
6. delegate ROI
7. source performance
8. 下月建议关注项

## 8. Quarterly 报告结构

建议固定结构：

1. 季度综述
2. 稳定 academic frontiers
3. 稳定 industry demands
4. 持续 gaps
5. 值得进入研究路线图的方向
6. source expansion / pruning proposal
7. profile / triage 调整建议
8. 下一季度执行建议

## 9. 文件命名策略

### 现有兼容
- daily: `data/reports/daily/YYYY-MM-DD.md`
- weekly: `data/reports/weekly/YYYY-WXX.md`
- landscape: 兼容期内不要硬删旧路径

### 目标扩展
- monthly: `data/reports/monthly/YYYY-MM.md`
- quarterly: `data/reports/quarterly/YYYY-QX.md`

如果 landscape 需要与 weekly 共存，建议：
- weekly: `YYYY-WXX.md`
- landscape: `YYYY-WXX-landscape.md`

但在真正改路径之前，必须先做兼容迁移并更新 runbook。

## 10. 数量上限建议

### Daily
- academic must-read: <= 2
- industry must-read: <= 2
- detailed summary total: <= 8
- delegate total: <= 4
- one-line total: <= 12

### Weekly
- must-read total: <= 10
- delegate total: <= 8
- candidate directions shortlist: <= 5

### Monthly
- 核心主题: <= 10
- 候选方向: <= 8

### Quarterly
- 进入路线图的方向: <= 5

## 11. 何时允许空缺

如果没有足够高价值条目，不要为了“看起来完整”硬塞内容。

允许：
- must-read 为空
- delegate 为空
- candidate direction 为空

不允许：
- academic / industry 结构消失
- 没有说明为什么为空
