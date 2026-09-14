# douyin-quote-autopublish

一个面向 Codex 的抖音热点事件图文自动发布 Skill：从最新热点发现、视频下载、独立封面制作、白底经过卡与代表性截图生成、事实核验，到抖音创作服务平台上传、配乐、发布时间确认和定时发布。

## 特性

- 抖音站内热榜 + 搜索热点优先的 24/72 小时热点发现
- Codex iab 内置浏览器优先与外部浏览器禁止静默回退
- 悬空工具调用、会话失败和浏览器中断恢复
- 事实核验和标题/正文一致性检查
- 视频字幕时间轴 OCR
- 默认生成独立封面和正文四图：白底事件经过卡加三张代表性原视频截图
- 支持用户明确要求的原生字幕 3:4 金句拼图
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

不需要手工安装 Python 包。首次调用 skill 时，`SKILL.md` 会要求 Codex 先运行：

```bash
python scripts/run.py check
```

该命令会自动创建私有虚拟环境并安装依赖，不需要手工执行 `pip install`，也不需要系统安装 FFmpeg。环境默认放在 `%CODEX_HOME%\cache\douyin-quote-autopublish\venv`，非 Windows 对应 `$CODEX_HOME/cache/douyin-quote-autopublish/venv`。

之后可在新任务中调用：

```text
用 $douyin-quote-autopublish 找今天最新的热点，制作独立事件封面和正文四图，并定时发布
```

## 依赖

自动安装：

- `opencv-python`
- `rapidocr-onnxruntime`
- `Pillow`
- `yt-dlp`
- `imageio-ffmpeg`：自带 FFmpeg 二进制

外部能力：

- Codex 内置浏览器 `iab`
- Python 3.10+；若系统没有 Python，可使用 Codex 内置 Python 运行 `run.py`
- `native-subtitle-quote-image` Skill：仅原生字幕金句拼图模式需要，默认图文模式不需要

首次安装依赖需要网络。

## 工作流

1. 先读取抖音官方热榜、创作者中心热度和站内搜索相关词，再用站外平台交叉核验，记录热点年龄、来源和热度证据。
2. 核验事件，淘汰过期、不可核验或高风险题材。
3. 获取视频并 OCR 字幕时间轴。
4. 生成独立事件封面、白底经过卡和三张代表性原视频截图，并逐张回读质检。
5. 登录缺失时保留浏览器标签并中断，等待用户完成登录或安全验证。
6. 正文上传四图，单独设置作品封面，填写标题正文、选择背景音乐和定时时间。
7. 展示最终摘要，等待用户明确确认。
8. 提交并回读作品管理页状态。

## 关键文件

- `SKILL.md`: 主流程和硬约束
- `references/latest-hot-topics.md`: 热点发现和筛选规则
- `references/douyin-topic-discovery.md`: 抖音官方热榜与搜索热点发现
- `references/codex-runtime-recovery.md`: Codex 会话、图标读取和浏览器故障恢复
- `references/video-to-assets.md`: 视频到独立封面和正文四图流程
- `references/douyin-publish-playbook.md`: 抖音上传、配乐、定时发布和个人资料修改
- `requirements.txt`: 可移植 Python 依赖清单
- `scripts/run.py`: 自动自举环境并提供 OCR、yt-dlp、FFmpeg 统一入口
- `scripts/runtime_env.py`: 私有虚拟环境创建和校验
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