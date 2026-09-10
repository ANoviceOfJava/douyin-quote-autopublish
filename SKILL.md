---
name: douyin-quote-autopublish
description: "自动化完成最新热点发现、抖音金句图选材、视频下载、字幕定位、3:4 出图、事实核验、浏览器登录中断恢复、图文上传、背景音乐、发布时间确认到定时发布的完整流程。适用于用户要求追最新热点、批量制作并发布视频金句图、断点续跑或托管发布时。"
---

# 抖音金句图自动发布

## 目标

把“最新热点发现 → 视频来源 → 字幕金句筛选 → 3:4 金句图 → 发布文案 → 抖音创作服务平台上传 → 配乐 → 用户确认发布时间 → 定时发布 → 验证状态”做成可断点续跑的工作流。

用户只负责两类必要输入：

1. 在登录失效时，在浏览器里完成登录。
2. 在最终提交前，确认发布时间。

## 不可违反的规则

- 内容默认追最新热点，不从旧素材池里挑过时话题冒充热点。热点新鲜度和事实核验与画面质量同等重要。
- 最终发布前必须让用户明确确认标题、正文、配图、背景音乐和发布时间。未得到用户确认，不得点击最终“发布”按钮。
- 登录缺失、验证码、短信验证码、扫码确认或账号安全验证必须中断，让用户处理。不得绕过验证，不得代替用户完成 CAPTCHA，不得索取密码或验证码。
- 复用同一个内置浏览器会话，不关闭登录页或发布页，不清理 Cookies，不导出或落盘 Cookie。优先使用 `markHandoff` 保留等待登录的页面，使用 `markDeliverable` 保留已提交结果页。
- 热点、谣言、截图和网络传言必须核验“具体事件是什么、谁发布、何时发生、何时辟谣、如何定性”。标题不得只有情绪，不能出现“一个消息/一件事情”却不说明事件对象的悬空表达。
- 原生字幕模式不得 OCR 后重绘、翻译或改写画面文字。脚本字幕只能使用已核对台词。
- 用户明确承担版权责任不解除热点时效、事实核验、平台规则和发布前确认义务。
- 抖音个人主页可以通过昵称右侧的隐藏编辑图标修改头像、昵称和简介；头像变更可能触发原设备扫码验证。出现验证时停止并交给用户，不得绕过。

## 最新热点硬门

默认只选满足以下条件的热点：

- `0–24 小时`：优先使用。
- `24–72 小时`：可使用，但必须有持续发酵或新进展。
- `超过 72 小时`：默认淘汰。只有出现新的权威进展，或用户明确要求做回顾时，才可继续。
- 必须在抖音热点、百度热搜、微博热搜、头条热榜或同等平台看到明确热度信号。
- 必须由至少两个独立来源交叉确认；谣言、爆料、截图类必须有权威媒体、官方账号或当事机构回应。
- 必须能找到带烧录字幕或完整口播的视频素材，适合拆成金句图。
- 优先“高热度 + 强共鸣 + 可核验 + 可视觉化”，不追灾难、血腥、隐私、未成年人受害、未经证实的刑事指控和金融荐股。
- 状态文件必须记录：事件日期、首次发现时间、发现时间、当前年龄、来源 URL、热度证据和核验结论。

详细来源、评分和淘汰规则见 [references/latest-hot-topics.md](references/latest-hot-topics.md)。

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
  --json '{"topic":{"title":"...","event_date":"2026-09-10","discovered_at":"2026-09-10T14:00:00+08:00","age_hours":4,"source_urls":["..."],"heat_evidence":"抖音热点榜第3","fact_status":"confirmed"}}'
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
- 保存作品 ID、原始链接、作者、标题、下载路径和字幕来源。
- 使用 `yt-dlp` 时优先复用浏览器登录态；若读取失败，停在登录要求，不导出 Cookie。

### `assets_ready`

- OCR 定位烧录字幕，建立稳定时间轴。
- 选择有完整语义链的句子，生成 3:4 JPG。
- 对成品做 OCR 回读、尺寸、张数、主图比例和字幕完整性质检。
- 两行字幕优先使用“1 主图 + 2 字幕条”或降低 `hero-fraction`；不要为了固定 4 条把整句裁掉。
- 保存最终图片列表到状态文件。

### `content_ready`

- 先核验事件，再写标题和正文。
- 标题建议格式：`最新事件 + 冲突/问题`。
- 正文顺序：事件事实 → 最新进展或权威结论 → 为什么会共鸣 → 价值判断 → 互动问题。
- 正文不得省略事件对象。热点截图、海报或传言必须写清“谁、何时、宣称了什么、后来如何回应”。
- 话题标签 4–6 个，包含事件词、议题词和账号名。
- 对谣言类内容必须记录至少一个权威来源。
- 发布前重新计算热点年龄；超过 72 小时且无新进展时退回 `hot_topic_selected`。

### `browser_ready` / `login_required`

- 选择内置浏览器 `iab`。
- 打开抖音创作者中心或作品发布页。
- 若出现登录、扫码或安全验证：
  1. 更新状态为 `login_required`。
  2. 对当前标签执行 `markHandoff()`。
  3. 停止工作并请用户完成登录。
  4. 用户回复登录完成后，重新取得同一个浏览器绑定和已保留标签，继续执行，不要要求重复登录。
- 若浏览器会话确实丢失，才停在 `login_required` 并要求重新登录。

### `upload_ready`

- 按 [references/douyin-publish-playbook.md](references/douyin-publish-playbook.md) 上传图片并填写内容。
- 标题、正文、图片顺序、封面、音乐、公开范围、保存权限必须逐项回读。
- 富文本正文重写前先全选清空，防止旧文案与新文案拼接。
- 更新状态为 `awaiting_schedule_confirmation`，等待用户确认发布时间。

### `awaiting_schedule_confirmation`

- 向用户展示最终发布摘要：热点及新鲜度、来源、标题、正文首段、图片数量、音乐、时间、可见范围。
- 只有用户明确确认后，才运行：

```bash
python <SKILL_DIR>/scripts/workflow_state.py confirm-schedule \
  --state <WORK_DIR>/workflow-state.json
```

- 未确认时保留页面，不得提交。

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

## 资源

- 最新热点发现与筛选：`references/latest-hot-topics.md`
- 视频到金句图：`references/video-to-assets.md`
- 抖音上传发布：`references/douyin-publish-playbook.md`
- 断点状态机：`scripts/workflow_state.py`
- 字幕时间轴 OCR：`scripts/ocr_subtitles.py`