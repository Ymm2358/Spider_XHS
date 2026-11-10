# 数据与接口契约

`brief.json` 是稳定契约，CLI 是稳定接口。换 agent 时只换适配层，不重写指标、存储和报告。

## 数据流

```text
采集 CLI -> data/xhs.db -> brief CLI -> reports/日期/brief.json -> agent 适配层 -> 选题建议
```

后续加 MCP 时，MCP 也只是适配层：

```text
agent -> MCP server -> 同一套 CLI / 核心逻辑 -> 同一份 brief.json
```

`brief.md` 给人看，不作为机器契约。agent 只读 `brief.json`。

## 顶层字段

| 字段 | 类型 | 含义 |
|---|---|---|
| `schema_version` | string | 契约版本，当前为 `1.0`。 |
| `generated_at` | string | 生成时间，本地时间，格式 `YYYY-MM-DDTHH:MM:SS`，无时区。 |
| `window_days` | integer | 请求的统计窗口天数，默认 7。 |
| `viral_z` | number | 爆款判定阈值，默认 2.0。 |
| `novice_fans` | integer | 素人粉丝上限，默认 10000；低于该值算素人。 |
| `total_notes` | integer | 库内全部笔记数，不受 `window_days` 限制。 |
| `dated_notes` | integer | 库内有发布时间的笔记数。 |
| `fans_known` | integer | 库内已知作者粉丝数的笔记数。 |
| `directions[]` | array | 方向汇总，结构见下表。 |
| `keywords[]` | array | 关键词汇总，结构见下表。 |

## `directions[]` 每项

| 字段 | 类型 | 含义 |
|---|---|---|
| `direction` | string | 方向名，来自 `config/keywords.yml`；未匹配为“未分组”。 |
| `keywords` | string[] | 该方向下的关键词。 |
| `notes` | integer | 该方向各关键词 `notes` 之和。 |
| `supply_per_day` | number | 该方向各关键词 `supply_per_day` 之和。 |
| `median_engagement` | number | 各关键词 `median_engagement` 的中位数。 |
| `median_velocity` | number | 各关键词 `median_velocity` 的中位数。 |
| `viral_rate` | number | 各关键词 `viral_rate` 的中位数。 |
| `novice_viral_rate` | number \| null | 各关键词非 null `novice_viral_rate` 的中位数；全为 null 时为 null。 |
| `video_share` | number | 各关键词 `video_share` 的中位数。 |
| `median_images` | number | 各关键词 `median_images` 的中位数。 |
| `blue_ocean` | number | 各关键词 `blue_ocean` 的中位数；全为 null 时为 0。 |
| `top_notes[]` | array | 按关键词顺序拼接各关键词 `top_notes`，取前 5 条；不是方向内全局按 z 重排。 |

方向指标不是把方向内所有笔记重新汇总。`notes`、`supply_per_day` 是求和，其余中位数、比率和蓝海指标取关键词级结果的中位数。

## `keywords[]` 每项

| 字段 | 类型 | 含义 |
|---|---|---|
| `keyword` | string | 关键词。 |
| `direction` | string | 所属方向；未匹配为“未分组”。 |
| `notes` | integer | 本行实际使用的样本数。 |
| `dated` | integer | 样本中有发布时间的笔记数。 |
| `median_engagement` | number | 样本 `engagement` 的中位数。 |
| `p90_engagement` | number | 样本 `engagement` 的 90 分位。 |
| `median_velocity` | number | 有发布时间样本的每小时加权互动中位数；分母最小按 6 小时算。 |
| `viral_count` | integer | 有发布时间且 `z >= viral_z` 的笔记数。 |
| `viral_rate` | number | `viral_count / dated`；`dated` 为 0 时为 0。 |
| `viral_with_fans` | integer | 爆款中已知作者粉丝数的笔记数，也是素人爆款率的分母。 |
| `novice_viral_rate` | number \| null | 爆款中作者粉丝数低于 `novice_fans` 的占比；分母为 0 时为 null。 |
| `video_share` | number | 视频笔记占样本的比例。 |
| `median_images` | number | 非视频笔记图片数的中位数；没有非视频笔记时为 0。 |
| `supply_per_day` | number | 近 7 天发布的笔记数除以 7；固定 7 天，不受 `window_days` 影响。 |
| `blue_ocean` | number | 需求分位减供给分位，范围 -1 到 1；需求用 `median_velocity` 排名，供给用 `supply_per_day` 排名。 |
| `window_days` | integer | 本行实际窗口标记；样本少于 30 时回退全量并记为 30。 |
| `top_notes[]` | array | 有发布时间的笔记按 `z` 降序取前 5 条。 |

样本少于 30 时，`window_days` 可能显示 30，但样本并不一定严格截在 30 天内。引用时要说明“样本不足，已回退”。

## `top_notes[]` 每项

| 字段 | 类型 | 含义 |
|---|---|---|
| `note_id` | string | 小红书笔记 ID。 |
| `title` | string | 笔记标题，可能为空。 |
| `url` | string | 笔记链接，原样引用。 |
| `author` | string | 作者昵称。 |
| `author_fans` | integer \| null | 作者粉丝数；未补全时为 null。 |
| `publish_text` | string | 平台展示的发布时间，如“3天前”；不是精确时间。 |
| `liked` | integer | 展示点赞数，可能有取整。 |
| `collected` | integer | 展示收藏数，可能有取整。 |
| `comment` | integer | 展示评论数，可能有取整。 |
| `engagement` | number | 加权互动：点赞 × 1 + 收藏 × 3 + 评论 × 4 + 分享 × 2，权重可配。 |
| `z` | number | 优先按（关键词、笔记类型、发布时长段）分组，在 `log1p(velocity)` 空间算稳健 z；组内样本不足时回退到关键词级，仍不足为 0。 |
| `images` | integer | 图片数，来自 `image_count`。 |
| `type` | string | 笔记类型，`normal` 或 `video`。 |

`engagement` 计算包含分享，但 `top_notes` 不回传 `share`。不要从 `engagement` 反推分享数。

## 兼容规则

1. **新增字段只能追加，不能改名。** 已有字段的名称、类型、含义保持不变。
2. 删除字段、改字段名、改字段类型、改指标口径都算破坏性变更。必须提升 `schema_version` 主版本，并提供适配或迁移，不能静默改变输出。
3. `1.x` 版本内只做向后兼容的追加。新字段必须可缺省，老 agent 忽略未知字段后仍能工作。
4. `null` 表示未知，不是 0。消费方必须处理 null，不能把 null 当数值参与排序。
5. 消费方不依赖字段顺序，也不依赖数组顺序，除非字段说明里明确写了排序规则。
6. CLI 命令名和已有参数保持不变。新增能力只加可选参数，不复用旧参数表达新含义。
7. `brief --json` 输出 `brief.json` 本体；其他命令的 JSON 至少保留已有字段，新增字段同样只追加。
8. 新 agent 需要新指标时，先追加到 `brief.json`，不要在 agent 里另建一套平行报告格式。

## 换 agent 的边界

- 当前链路：agent 调 CLI，读 `reports/日期/brief.json`。
- 换模型、换提示词、换工具调用格式，只改适配层。
- 采集、指标、SQLite 表结构、日报字段不跟着 agent 改。
- 适配层不能自己算一套“互动分”或“爆款率”，必须用 `brief.json` 的值。

## MCP 计划

目前还没有 MCP server。不要在当前流程里假设它存在，也不要写不存在的工具调用。

后续会加，工具名固定为：

| 工具名 | 用途 |
|---|---|
| `search_notes` | 按关键词检索或采集笔记。 |
| `get_brief` | 读取或生成 `brief.json`。 |
| `list_candidates` | 列出候选选题。 |
| `write_draft` | 写入选题草稿。 |

工具的参数和返回结构在实现时另定。MCP 只做适配，底层仍走同一套 CLI 和核心逻辑，`brief.json` 仍是数据契约。
