---
name: douyin-quote-autopublish
description: "自动化完成最新热点发现、事件封面与正文图文制作、事实核验、浏览器登录中断恢复、图文上传、背景音乐、发布时间确认到定时发布的完整流程。默认输出独立封面和正文四图：白底事件经过卡加三张代表性原视频截图；也支持用户明确要求的原生字幕金句拼图。适用于抖音热点事件追更、图文制作发布、断点续跑或托管发布。"
---

# 抖音热点事件图文自动发布

## 目标

把“最新热点发现 → 视频来源 → 独立事件封面与正文四图制作 → 事实核验 → 发布文案 → 抖音创作服务平台上传 → 配乐 → 用户确认发布时间 → 定时发布 → 验证状态”做成可断点续跑的工作流。

默认图文结构为 `event-cover-carousel`：

- 独立封面 `cover_path`：使用处理后的原事件画面，在中部加入背景层和事件名称；只用于作品封面，不进入正文图片。
- 正文 `content_images`：固定 4 张，顺序为白底黑字事件经过卡、原视频截图 1、原视频截图 2、原视频截图 3。

只有用户明确要求原生字幕金句拼图时，才使用 `native-subtitle-quote-image` 的拼图成品流程。

用户只负责两类必要输入：

1. 在登录失效时，在浏览器里完成登录。
2. 在最终提交前，确认发布时间。

## 运行环境自举

每个新任务开始、读取热点之前先运行：

```bash
python <SKILL_DIR>/scripts/run.py check
```

- 首次运行会自动在 `%CODEX_HOME%\cache\douyin-quote-autopublish\venv`（非 Windows 为 `$CODEX_HOME/cache/...`）创建私有 Python 虚拟环境，并按 `requirements.txt` 自动安装依赖。
- 不需要手工执行 `pip install`，不需要系统安装 FFmpeg；OCR 和取帧使用 `imageio-ffmpeg` 提供的 FFmpeg 二进制。
- 后续统一使用 `<SKILL_DIR>/scripts/run.py` 运行 `ocr`、`yt-dlp` 和 `ffmpeg` 命令。
- 默认 `event-cover-carousel` 模式不依赖 `native-subtitle-quote-image`。只有用户明确要求原生字幕金句拼图时才检查并调用该 Skill。
- 如果系统没有 Python 3.10+，先调用 Codex 的 `load_workspace_dependencies` 获取内置 Python，再用它执行 `run.py`。
- 首次准备环境需要联网下载依赖；安装失败时停止任务并报告原始错误，不要求用户逐项手工安装。

## 不可违反的规则

- 内容默认追最新热点，不从旧素材池里挑过时话题冒充热点。热点新鲜度和事实核验与画面质量同等重要。
- 发布前必须先确定 `content.angle`，并确保标题、正文图片内容、正文首段和结尾问题都围绕同一叙事主线。
- 默认使用 `event-cover-carousel`。`cover_path` 禁止出现在 `content_images`，也禁止作为正文第 1 张上传。
- `content_images` 必须恰好 4 张且顺序固定：白底事件经过卡、原视频截图 1、原视频截图 2、原视频截图 3。
- 三张原视频截图必须分别对应事件起因或经过、关键动作或冲突、关键证据或结果/转折，必须是不同时间或信息节点；无法找到三张有代表性的截图时停止并说明，不得随机截图凑数。
- 一旦用户明确要求使用 `native-subtitle-quote-image` 的原生字幕拼图模式，不得为了去重或排版擅自改成脚本字幕、自制信息卡或其他替代方案。无法解决时必须停下让用户决定。
- 自媒体热点叙事优先使用事件发生时的最热曝光视频；官方通报和新闻播报默认只用于事实核验，不替代曝光素材。
- 默认模式必须在最终发布前让用户确认标题、正文、配图、背景音乐和发布时间。未得到用户确认，不得点击最终“发布”按钮。
- 用户明确指定 `publish_policy=autonomous` 时，跳过人工确认并按自动发布门直接发布；高风险内容直接跳过，见 [references/autonomous-publish-policy.md](references/autonomous-publish-policy.md)。
- 登录缺失、验证码、短信验证码、扫码确认或账号安全验证必须中断，让用户处理。不得绕过验证，不得代替用户完成 CAPTCHA，不得索取密码或验证码。
- 复用同一个内置浏览器会话，不关闭登录页或发布页，不清理 Cookies，不导出或落盘 Cookie。优先使用 `markHandoff` 保留等待登录的页面，使用 `markDeliverable` 保留已提交结果页。
- 浏览器默认且优先使用 Codex 内置浏览器 `iab`。`iab` 不可用时先诊断并说明阻塞，不得静默回退到外部 Chrome、Edge 或系统浏览器。
- 当前线程出现 `No tool output found for tool call ...` 时，视为会话历史已损坏；不要反复回复“继续”。按 [references/codex-runtime-recovery.md](references/codex-runtime-recovery.md) 从磁盘状态恢复，并 fork 或新开干净线程继续。
- 批量查看成品图片时逐张读取并等待每次工具结果返回；不要在一次工具批次里并发提交多张 `view_image`。
- 热点、谣言、截图和网络传言必须核验“具体事件是什么、谁发布、何时发生、何时辟谣、如何定性”。标题不得只有情绪，不能出现“一个消息/一件事情”却不说明事件对象的悬空表达。
- 原生字幕模式不得 OCR 后重绘、翻译或改写画面文字。脚本字幕只能使用已核对台词。
- 用户明确承担版权责任不解除热点时效、事实核验、平台规则和发布前确认义务。
- 抖音个人主页可以通过昵称右侧的隐藏编辑图标修改头像、昵称和简介；头像变更可能触发原设备扫码验证。出现验证时停止并交给用户，不得绕过。

## 最新热点硬门

默认只选满足以下条件的热点：

- `0–24 小时`：优先使用。
- `24–72 小时`：可使用，但必须有持续发酵或新进展。
- `超过 72 小时`：默认淘汰。只有出现新的权威进展，或用户明确要求做回顾时，才可继续。
- 必须包含抖音站内热度证据：优先检查抖音官方热点榜、抖音热榜、创作者中心热点或站内搜索结果及相关搜索。不得只依赖微博、今日头条、B站、知乎等站外来源。
- 抖音官方热榜不是全部。品牌、产品、功能和服务类事件必须再查站内搜索及相关搜索；未做这一步不得声称“已覆盖抖音热点”。某些品牌、产品、功能或服务事件可能尚未进入当刻 Top 榜，但站内搜索和相关搜索已经形成当前事件。
- 站外平台用于交叉核验和扩展，不可替代抖音站内热度发现。
- 必须由至少两个独立来源交叉确认；谣言、爆料、截图类必须有权威媒体、官方账号或当事机构回应。
- 必须能找到可用于事件图文的视频素材；若要制作白底经过卡，至少能定位完整经过、关键动作和关键证据。
- 优先“高热度 + 强共鸣 + 可核验 + 可视觉化”，不追灾难、血腥、隐私、未成年人受害、未经证实的刑事指控和金融荐股。
- 状态文件必须记录：事件日期、首次发现时间、发现时间、当前年龄、来源 URL、抖音站内热度证据或搜索相关词、站外交叉证据和核验结论。

详细来源、评分和淘汰规则见 [references/latest-hot-topics.md](references/latest-hot-topics.md)。真实执行中的事件图文、原生字幕、草稿恢复、定时时间与删除坑位见 [references/lessons-and-guardrails.md](references/lessons-and-guardrails.md)。

## 叙事与模式硬门

- 在 `content` 中记录 `angle`、`must_include` 和 `excluded_outcomes`。如果用户要求只讲事件，后续通报、退款、校方承担、专项核查不得出现在标题、正文图片文字或正文中。
- 标题的主语和冲突、正文四图的内容推进顺序、正文第一段必须指向同一个事件和同一个矛盾点。三者不一致时禁止进入上传阶段。
- `source.role` 只能是 `exposure`、`commentary`、`official` 或 `user_supplied`。热点事件默认优先 `exposure`。
- 使用曝光视频时记录 `published_at` 和 `heat_evidence`，避免拿后发的官方通报冒充原始曝光素材。
- 原生字幕拼图成品必须通过 OCR 回读查重。主画面与字幕条不能出现同句；同一字幕段只选一个时间点；相邻时间点不得落在切换残影上。
- 自定义信息卡、脚本字幕或其他替代方案只有在用户明确同意后才能替换原生字幕拼图模式。
- `event-cover-carousel` 是默认模式：独立封面只用于作品封面，正文严格使用“白底说明 + 三张代表性原视频截图”。
- `event-cover-carousel` 的抖音标题使用短事件名，正文只放话题标签，不重复事件说明。
- 同一天发布多条时，需要逐条上传、逐条定时、逐条提交；不要同时保留多个未发布草稿。每条提交后刷新作品管理，确认标题、张数、时间和状态。

## 开始任务

1. 选择一个任务目录，例如 `work/<task-name>` 和 `outputs/<task-name>`，全程使用绝对路径。
2. 初始化状态：

```bash
python <SKILL_DIR>/scripts/workflow_state.py init \
  --state <WORK_DIR>/workflow-state.json \
  --workdir <WORK_DIR> \
  --outputs-dir <OUTPUTS_DIR> \
  --platform douyin
```

3. 展示状态后从 `intake` 阶段开始。若存在状态文件，先运行：

```bash
python <SKILL_DIR>/scripts/workflow_state.py show --state <WORK_DIR>/workflow-state.json
python <SKILL_DIR>/scripts/workflow_state.py validate --state <WORK_DIR>/workflow-state.json
```

4. 每完成一个阶段，立即更新状态。示例：

```bash
python <SKILL_DIR>/scripts/workflow_state.py set-stage \
  --state <WORK_DIR>/workflow-state.json --stage hot_topic_selected

python <SKILL_DIR>/scripts/workflow_state.py set \
  --state <WORK_DIR>/workflow-state.json \
  --json '{"topic":{"title":"...","event_date":"2026-09-10","discovered_at":"2026-09-10T14:00:00+08:00","age_hours":4,"source_urls":["..."],"heat_evidence":"抖音热点榜第3","fact_status":"confirmed"},"source":{"role":"exposure","published_at":"2026-09-10T15:00:00+08:00","heat_evidence":"1018 热度"},"content":{"angle":"学校让班级平摊滤芯费","must_include":["31个滤芯","8680元","每班98元"],"excluded_outcomes":["全额清退","校方承担"]}}'
```

## 阶段状态机

### `intake`

- 确认平台，默认抖音。
- 明确内容领域、目标条数、发布时间偏好和需要规避的题材。
- 记录账号、内容风格、版权确认和状态文件路径。

### `hot_topic_selected`

- 按 [references/latest-hot-topics.md](references/latest-hot-topics.md) 获取当前热榜。
- 生成至少 5 个候选，再按“时效、热度、共鸣、可核验、可出图”排序。
- 记录候选淘汰原因和最终选择。
- 若最终热点超过 72 小时且没有新进展，不得进入下一阶段；向用户说明并重新选择。
- 只有完成核验后，才进入视频获取。

### `source_ready`

- 按 [references/video-to-assets.md](references/video-to-assets.md) 获取本地视频。
- 保存作品 ID、原始链接、作者、标题、发布时间、热度证据、下载路径、字幕来源和 `source.role`。
- 使用 `yt-dlp` 时优先复用浏览器登录态；若读取失败，停在登录要求，不导出 Cookie。

### `assets_ready`

- 默认按 [references/video-to-assets.md](references/video-to-assets.md) 制作 `event-cover-carousel` 资产：
  - 生成独立封面：从原事件视频选择可识别的代表性画面，在中部加入背景层和事件名称，保存为 `assets.cover_path`。
  - 正文第 1 张生成白底黑字事件经过卡；第 2–4 张分别从原视频导出三张独立代表性截图。
  - 三张截图分别覆盖事件起因或经过、关键动作或冲突、关键证据或结果/转折，禁止重复画面和随机截图。
  - 状态文件必须保存 `assets.mode`、`assets.cover_path`、`assets.cover_text` 和按顺序排列的 `assets.content_images` 四个绝对路径。
  - 逐张质检尺寸、清晰度、事件对应关系和正文顺序；确认 `cover_path` 不在 `content_images` 中。
- 只有用户明确要求原生字幕金句拼图时，才 OCR 定位烧录字幕并生成拼图：
  - 将 `assets.mode` 改为 `native-subtitle-quote`，把最终拼图绝对路径按顺序写回 `images`。
  - 选择有完整语义链的句子，生成 3:4 JPG。
  - 对成品做 OCR 回读、尺寸、张数、主图比例和字幕完整性质检。
  - 两行字幕优先使用“1 主图 + 2 字幕条”或降低 `hero-fraction`；不要为了固定 4 条把整句裁掉。
  - 主画面优先使用无底部字幕的帧；如果主画面带字幕，主画面与字幕条不得选到同一句。
  - 同一字幕段只选一个时间点，相邻点至少间隔一个完整切换，通常 `>= 0.8 秒`；成品必须 OCR 回读确认无重复。
- 保存最终图片列表到状态文件。

### `content_ready`

- 先核验事件，再写标题和正文。
- 标题建议格式：`最新事件 + 冲突/问题`。
- 正文顺序必须服从 `content.angle`。如果用户只要事件，正文只写事件事实、费用拆解和追问，不写处理结果。
- 正文不得省略事件对象。热点截图、海报或传言必须写清“谁、何时、宣称了什么、后来如何回应”。
- 话题标签 4–6 个，包含事件词、议题词和账号名。
- 对谣言类内容必须记录至少一个权威来源。
- 发布前重新计算热点年龄；超过 72 小时且无新进展时退回 `hot_topic_selected`。

### `browser_ready` / `login_required`

- 必须优先且默认选择 Codex 内置浏览器 `iab`；不得静默回退到外部 Chrome、Edge 或系统浏览器。
- `iab` 不可用时按 [references/codex-runtime-recovery.md](references/codex-runtime-recovery.md) 诊断；仍不可用时停止并说明阻塞。
- 打开抖音创作者中心或作品发布页。
- 若出现登录、扫码或安全验证：
  1. 更新状态为 `login_required`。
  2. 对当前标签执行 `markHandoff()`。
  3. 停止工作并请用户完成登录。
  4. 用户回复登录完成后，重新取得同一个浏览器绑定和已保留标签，继续执行，不要要求重复登录。
- 若浏览器会话确实丢失，才停在 `login_required` 并要求重新登录。

### `upload_ready`

- 按 [references/douyin-publish-playbook.md](references/douyin-publish-playbook.md) 上传图片并填写内容。
- `event-cover-carousel` 模式：正文只上传 `assets.content_images` 的 4 张图，不得把 `assets.cover_path` 放进正文上传列表；上传后必须单独把 `cover_path` 设置为作品封面。
- 标题、正文、正文图片数量与顺序、独立封面、音乐、公开范围、保存权限必须逐项回读。
- 富文本正文重写前先全选清空，防止旧文案与新文案拼接。
- `event-cover-carousel` 模式：标题填短事件名，正文只填标签。不要重复写入事件说明或长文案。
- 更新状态为 `awaiting_schedule_confirmation`，等待用户确认发布时间。

### `awaiting_schedule_confirmation`

- 向用户展示最终发布摘要：热点及新鲜度、`source.role`、叙事角度、排除的结果事实、独立封面路径与封面事件名、正文四图角色顺序、标题、正文首段、音乐、可见范围，以及用户请求时间、平台最早允许时间和实际回读时间。
- 抖音定时要求至少晚于当前时间 2 小时、最多 14 天。用户时间不满足时，不得默默使用平台调整值；必须先让用户确认调整后的时间。
- 多条内容需要同一天发布时，每提交一条后都回到内容管理页核验，再开始下一条。不要把“发布成功”提示当作最终成功，以内容管理列表中的时间、张数和状态为准。
- 平台回读时间写入状态文件后再确认：

```bash
python <SKILL_DIR>/scripts/workflow_state.py set \
  --state <WORK_DIR>/workflow-state.json \
  --json '{"schedule":{"requested_at":"2026-09-10 20:30","minimum_allowed_at":"2026-09-10 20:45","actual_at":"2026-09-10 20:45","adjustment_reason":"平台要求至少提前2小时"}}'
```
- 只有用户明确确认后，才运行：

```bash
python <SKILL_DIR>/scripts/workflow_state.py confirm-schedule \
  --state <WORK_DIR>/workflow-state.json
```

- 未确认时保留页面，不得提交。
- `autonomous` 模式下不等待人工确认；先检查 `auto_publish.eligible` 和高风险类别，再直接发布。发布后记录 `published_at`、作品管理状态和去重指纹。

### `submitted` / `verified`

- 点击最终发布按钮。
- 进入内容管理，验证标题、时间、状态。
- 只有作品管理页显示正确标题和用户确认的发布时间，才更新为 `verified`，向用户报告完成。
- 如果平台显示“审核中”，这是正常中间状态，不等于已公开。

## 恢复协议

1. 读取状态文件和已存在产物，以文件系统为准，不凭聊天记忆猜测进度。
2. 检查热点年龄和事实来源是否仍有效；过期则退回 `hot_topic_selected`。
3. 检查浏览器是否还有已保留标签。
4. 从第一个未完成阶段继续。
5. 若登录状态已存在，直接复用，不重新登录。
6. 若正文、时间或图片任一缺失，退回对应阶段补齐后再请求确认。
7. 每次登录中断和最终确认前都要更新状态文件。
8. 若当前线程出现悬空工具调用错误，按 [references/codex-runtime-recovery.md](references/codex-runtime-recovery.md) 换到干净线程恢复；不要继续向故障线程发送“继续”。

## 资源

- 运行环境自举与命令入口：`scripts/run.py`
- Python 依赖清单：`requirements.txt`
- 最新热点发现与筛选：`references/latest-hot-topics.md`
- 抖音站内热点与搜索热点发现：`references/douyin-topic-discovery.md`
- Codex 运行故障与恢复：`references/codex-runtime-recovery.md`
- 视频到事件封面与正文四图：`references/video-to-assets.md`
- 抖音上传发布：`references/douyin-publish-playbook.md`
- 断点状态机：`scripts/workflow_state.py`
- 字幕时间轴 OCR：`scripts/ocr_subtitles.py`
- 实战经验与硬门：`references/lessons-and-guardrails.md`
- 自动发布策略：`references/autonomous-publish-policy.md`