# SOURCE_EXPANSION_PLAN

## 1. 原则

source expansion 不是当前第一优先级。
只有当 triage、daily/weekly 报告、feedback 回流已经稳定后，才继续扩 source。

顺序必须是：

```text
source stability -> triage stability -> report usefulness -> source expansion
```

## 2. 当前基线 source

### Academic
- T1 conferences
- T2 arXiv（当前通过 `config/sources.json` 控制 categories/max_results，默认每日最多 30 条，并按 category 分开查询）

### Industry
- T3 curated research blogs
- T3 industry conference topic sources

### 未完成
- advisories
- T4 personal sources
- Black Hat Asia / USA scoped cookie 更新/轮换方式确认；Black Hat Europe 2026 schedule 发布监控
- BSidesSF Sched 的稳定替代抓取策略

## 3. source 准入规则

任何新增 source 在接入前都必须满足以下问题的回答：

1. 它更偏 academic 还是 industry？
2. 它的更新频率是否适合长期自动化？
3. 页面结构是否稳定？
4. 是否有明确发布时间和 URL？
5. 噪声是否可控？
6. 是否会明显增加维护成本？
7. 是否会破坏现有 no-mix 规则？

如果回答不清楚，就先不要接。

## 4. 推荐扩展顺序

### Phase 1：Advisories
目的：
- 填补 daily 报告里的“漏洞速报”空白
- 强化 industry track 的现实紧迫性信号

要求：
- 作为独立 industry 子分区
- 单独定义 authority / urgency 规则
- 不与 paper 共排
- 默认不进入 academic 排序

推荐候选：
- GitHub Advisory
- NVD
- AVD

### Phase 2：额外 curated research blogs
目的：
- 扩大高质量 industry signal 覆盖
- 但仍保持“研究导向”，不接营销内容

候选顺序建议：
1. Trail of Bits
2. 其他能稳定提供研究型安全博客的 source
3. 慎重评估 Daily Swig / 类似媒体型来源

不建议优先接：
- 泛安全新闻站
- 高频营销博客
- 没有稳定结构的个人站

当前已进入集中配置并验证的 T3 source：

- 可抓取：PortSwigger、OpenAI Blog、Anthropic News、Brutecat、HackTron AI、Trail of Bits、Google Online Security Blog、GitHub Blog Security、Assetnote Research、Bishop Fox Blog、BSidesSF（AllBSides recording fallback）
- 暂不接入：GitHub Security Lab feed 当前可访问但返回 0 entries，先不进入默认 source
- 专用 parser 可抓取：DEF CON speaker/talk 页面，默认先探测当前年份对应届数；2026-07-03 实测 DEF CON 34 speakers 页为 404，因此当前回退抓取并展示 DEF CON 33 talks
- 官方 parser 已接入：Black Hat Asia 2026、Black Hat USA 2026；crawler 读取官方 `sessions.json`，requests 403 时使用 scoped `BLACKHAT_COOKIE` + `curl_cffi` Chrome impersonation fallback。Black Hat Asia 2026 live smoke 抓到 53 条有效议题，Black Hat USA 2026 live smoke 抓到 104 条有效议题，均已完成摘要/相关度/评分
- 已移除：RSA Conference / RSAC。此前官方 RainFocus agenda 可抓取，但 session 噪声偏高，当前不再作为默认 source 维护；历史 artifacts 已归档出展示面
- browser-use crawler 已接入：Black Hat Europe。Black Hat Europe 2026 schedule 当前未发布
- 保留手动调试：Project Zero。当前环境下官方域名和 Blogspot feed 多个入口不稳定，已通过 `daily-disabled` 排除出默认 daily refresh
- requests 直接抓取仍被 403 阻断：Black Hat Asia / USA 官方 schedule 在无 scoped cookie 时可能返回 403，但 scoped `cf_clearance` + `curl_cffi` 已验证可用；Black Hat Europe 2026 schedule 尚未发布；BSidesSF Sched 仍需 browser-use、官方导出或其它稳定策略

Black Hat Asia / USA 后续需要确认 scoped cookie 更新/轮换方式是否可长期维护；Black Hat Europe 等官方 schedule 发布后应优先复用 `blackhat-schedule`，不要回到第三方镜像。BSidesSF 当前 fallback 只能覆盖已发布录制 talk，不等同于完整 Sched agenda。

### Phase 3：T4 personal sources
目的：
- 纳入用户真正关心的个人博客 / 公众号

前置条件：
- 用户明确给出 URL 列表
- 明确其属于 industry track
- 有最小去重和人工审查规则

### Phase 4：可选 academic 扩展
目标：
- 只在用户需要时补充 SE 安全相关会议轨

候选：
- ICSE security-related papers
- FSE security-related papers
- ASE security-related papers

注意：
- 必须明确它们仍属于 academic track
- 不要在 triage 稳定前就接入

## 5. source 淘汰规则

新增 source 之后，如果满足以下情况之一，应考虑下线：

- 模板频繁漂移
- 噪声极高
- 维护成本明显高于信号价值
- 长期几乎不进入 must-read / detailed / delegate bucket
- 与其他 source 高度重复

## 6. 每次 source 变更后必须同步更新

- `docs/CURRENT_STATUS.md`
- `docs/SOURCE_EXPANSION_PLAN.md`
- `docs/RUNBOOK.md`
- `README.md`
- 如有排序影响，更新 `docs/TRIAGE_POLICY.md`

## 7. 人工决策保留项

以下问题不要由 Codex 直接拍板：

- 用户要不要追踪某个 T4 个人 source
- 某个 source 是否值得长期维护
- advisories 的 authority / urgency 具体阈值
- 是否要扩到更广泛的软件工程会议轨
