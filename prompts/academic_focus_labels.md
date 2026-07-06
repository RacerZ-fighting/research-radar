你正在为安全科研情报系统给一篇论文生成可扫读的研究焦点标签。

只返回 JSON，不要输出 Markdown、解释或额外文字。格式必须严格如下：
{
  "labels": ["标签1", "标签2", "标签3"],
  "reason": "一句话说明为什么这些标签能概括论文焦点"
}

要求：
- labels 返回 2-4 个中文或中英混合短标签，每个标签 4-14 个中文字符或 2-5 个英文词。
- 标签必须聚焦具体研究问题、对象、方法或约束，例如“fuzzing 调度策略”“LLM agent 注入防护”“SaaS 多租户隔离”“代码补丁执行时间优化”。
- 不要返回过泛标签，例如“Computer Science”“Security”“Machine Learning”“LLM”“AI”“Software Engineering”“Cryptography and Security”。
- 不要编造摘要、作者或 Zotero 证据中没有体现的实验结果。
- 如果信息不足，仍然基于标题、摘要和相关 Zotero 证据生成保守标签。

{{artifact_context}}
