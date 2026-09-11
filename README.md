# douyin-quote-autopublish

一个面向 Codex 的抖音金句图自动发布 Skill：从最新热点发现、视频下载、字幕 OCR、3:4 金句图生成、事实核验，到抖音创作服务平台上传、配乐、发布时间确认和定时发布。

## 特性

- 抖音站内热榜 + 搜索热点优先的 24/72 小时热点发现
- Codex iab 内置浏览器优先与外部浏览器禁止静默回退
- 悬空工具调用、会话失败和浏览器中断恢复
- 事实核验和标题/正文一致性检查
- 视频字幕时间轴 OCR
- 原生字幕 3:4 金句图生成与回读质检
- Codex 内置浏览器登录中断与断点续跑
- 抖音图文上传、背景音乐、定时发布
- 最终发布时间用户确认门
- 抖音个人资料修改流程，包括头像安全验证处理

## 安装

把本目录放到 Codex 用户 Skill 目录：

```text
~/.codex/skills/douyin-quote-autopublish
```

Windows 默认位置：

```text
C:\Users\<user>\.codex\skills\douyin-quote-autopublish
```

安装后可在新任务中调用：

```text
用 $douyin-quote-autopublish 找今天最新的热点，制作金句图并定时发布
```

## 依赖

- Codex 内置浏览器
- `native-subtitle-quote-image` Skill
- Python 3.10+
- `ffmpeg` / `ffprobe`
- `yt-dlp`
- `rapidocr-onnxruntime`
- `opencv-python`
- `Pillow`

## 工作流

1. 先读取抖音官方热榜、创作者中心热度和站内搜索相关词，再用站外平台交叉核验，记录热点年龄、来源和热度证据。
2. 核验事件，淘汰过期、不可核验或高风险题材。
3. 获取视频并 OCR 字幕时间轴。
4. 生成 3:4 金句图并回读质检。
5. 登录缺失时保留浏览器标签并中断，等待用户完成登录或安全验证。
6. 上传图片、填写标题正文、选择背景音乐和定时时间。
7. 展示最终摘要，等待用户明确确认。
8. 提交并回读作品管理页状态。

## 关键文件

- `SKILL.md`: 主流程和硬约束
- `references/latest-hot-topics.md`: 热点发现和筛选规则
- `references/douyin-topic-discovery.md`: 抖音官方热榜与搜索热点发现
- `references/codex-runtime-recovery.md`: Codex 会话、图标读取和浏览器故障恢复
- `references/video-to-assets.md`: 视频到金句图流程
- `references/douyin-publish-playbook.md`: 抖音上传、配乐、定时发布和个人资料修改
- `scripts/workflow_state.py`: 可恢复状态机
- `scripts/ocr_subtitles.py`: 字幕 OCR 时间轴工具

## 安全与授权

- 登录、验证码、扫码和账号安全验证必须由用户完成。
- 不导出或落盘浏览器 Cookie。
- 最终发布前必须由用户确认标题、正文、配图、音乐和发布时间。
- 不绕过平台验证，不调用未公开的私有接口。
- 浏览器优先使用 Codex 内置 `iab`；不得静默回退到外部浏览器。

## License

MIT