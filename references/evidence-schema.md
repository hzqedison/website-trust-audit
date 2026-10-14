# 证据包结构（版本 1）

JSON 顶层字段：`schema_version`（整数 `1`）、`run_id`（非空字符串）、`as_of`（带时区 ISO-8601 时间）、`evidence`（数组）及 `coverage`（数组）。合成示例见 `assets/example-audit.json`。

每条 evidence 必须包含 `id`、`claim`、`kind`、`status`、`source`、`observed_at`、`method`、`scope`、`artifact` 和 `derived_from`。类型限定为 `observation`、`official_claim`、`third_party`、`reviewer_inference`、`user_requirement`；状态限定为 `historical`、`current`、`unverified`。`scope` 是包含非空 `site`、`locale`、`page`、`device` 的对象，可附加 `check` 等字段。`source` 是非空 URL 或相对于输入 JSON 所在目录的项目路径；`artifact` 是相对于输入 JSON 所在目录的项目文件路径或 null；`observed_at` 可为带时区 ISO 时间、精确日期 `YYYY-MM-DD`（仅 historical/unverified）或 null；`derived_from` 是证据 ID 数组。historical 时间未知时允许 `observed_at: null`，但须附非空 `time_note` 说明缺失；不得把只有日期精度的记录补造为午夜或添加时区。日期精度的记录按日历日期与 `as_of` 日期比较。

历史证据必须含来源和时间；若时间未知，按上述 `time_note` 规则记录，可以没有附件。当前证据必须含带时区且不晚于包内 `as_of` 的观察时间，以及输入 JSON 所在目录内存在的附件文件。相对附件路径不得逃出该目录。未验证证据可不含观察时间或使用日期精度。`current` 只表示在指定运行上下文重新核对，不证明官网自述属实。

评审推断必须引用已存在的证据；不允许自引用或循环依赖。每条 coverage 必须含 scope（非空 `site`、`locale`、`page`、`device`、`check`）、状态（`verified`、`partial`、`blocked`、`not_tested`）、`evidence_ids` 数组和非空说明。完全相同的五字段 scope 不可重复。`verified` 中每条引用均须是 `current`，并与该行站点、语言、页面和设备匹配；用户需求或评审推断本身不能单独证明做过页面检查。可引用 observation、official_claim 或 third_party，但保留原证据类型，不升级为真实性已证实。复核者仍须人工确认方法确实覆盖该行的检查项。

验证器离线运行：不请求网页、不运行下载或安装程序、不支付。它检查结构、引用、时间和附件路径，不判断来源主张是否真实、附件是否可信、视觉检查是否实际发生，也不判定 evidence 的 `method` 是否匹配 coverage 的 `check`。缺少覆盖是允许的，因此成功通过结构校验不表示审计完成。证据材料保存在项目目录，不放入此通用技能。
