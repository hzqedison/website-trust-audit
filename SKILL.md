---
name: website-trust-audit
description: 在明确范围内整理或复测软件官网的信任、下载、安装与付费证据，区分直接观察、官网自述、第三方资料、评审推断和用户需求。
metadata:
  short-description: 官网信任、下载与付费证据评审
---

# 官网信任评审

按用户请求选择一种模式：整理信息基线、按指定范围复测/对比，或澄清需求并形成五章 SPEC。仅整理基线不代表决定改版、排序或打分。

项目证据和客户资料留在项目目录，不放入此通用技能。每项证据记录唯一 ID、表述、证据类型、状态、来源、观察时间、站点/语言/页面/设备范围、方法和附件。`current` 只表示本次在指定上下文中复核，不代表官网宣传已被证实。

按需阅读：[基线整理](references/baseline.md)、[复测与对比](references/retest.md)或[需求与 SPEC](references/spec.md)。证据包格式见[证据结构](references/evidence-schema.md)；可用 `python scripts/validate_audit.py <evidence.json>` 做离线结构检查，并参考 `assets/` 模板。

验证器不联网、不抓取网页、不运行下载或安装程序、不支付。验证通过不等于审计完成；复核者需人工确认引用证据的方法确实覆盖相应检查层级。协作和发布遵循[团队协作](docs/collaboration.md)与[分发说明](docs/publishing.md)。Planner/reviewer 与 executor 模型可配置；不得声称自动路由成功，只有宿主支持且用户授权代理时才实际委派。
