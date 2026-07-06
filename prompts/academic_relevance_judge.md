你正在为安全科研情报系统判断一篇候选论文是否真的和用户已有 Zotero 文献库相关。

只返回 JSON：
{
  "relevant": true,
  "relevance_score": 0.0,
  "reason": "中文一句话说明",
  "matched_zotero_titles": ["Zotero 论文标题"]
}

判断标准：
- relevant 只在候选论文与 Zotero evidence 存在明确研究问题、方法、攻击面、系统对象或实验任务重叠时为 true。
- 只共享 AI、LLM、security、software engineering、benchmark、survey 这类泛主题，不算相关。
- CSRankings 或作者质量证据只能说明质量，不能替代相关度。
- 如果 Zotero evidence 很弱、只是词面碰巧重合，返回 relevant=false。
- relevance_score 使用 0 到 1；0.75 以上表示强相关，0.6-0.75 表示可保留，低于 0.6 表示不展示。
- reason 使用中文，直接说明为什么相关或为什么不相关。
- matched_zotero_titles 只放真正支撑判断的 Zotero 标题，最多 3 个；没有则返回空数组。

{{artifact_context}}
