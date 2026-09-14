# 视频到事件图文资产

先读 [lessons-and-guardrails.md](lessons-and-guardrails.md)。默认使用“独立封面 + 白底经过卡 + 三张代表性原视频截图”。只有用户明确要求原生字幕金句拼图时，才执行本文件后面的原生字幕流程；此时把 `assets.mode` 设为 `native-subtitle-quote`，并把最终拼图路径按顺序写入 `images`。

## 1. 来源与权限

先记录以下字段到 `workflow-state.json`：

- 平台、原始链接、作品 ID、作者、标题
- 本地视频绝对路径
- 是否含烧录字幕
- 用户是否有权处理和发布
- 事实核验来源，谣言类必须至少一个权威来源

优先复用已经下载的视频，避免重复下载。

## 2. 获取视频

热点事件先区分素材角色：

- `exposure`：原始曝光或传播最广的事件视频，自媒体叙事优先使用。
- `commentary`：后发评论、解读或律师分析。
- `official`：官方通报和新闻播报，默认用于事实核验，不替代曝光视频。

在线视频优先使用 `yt-dlp`，已有 Cookies 时复用本地 Cookie 文件；没有时优先 `--cookies-from-browser`。如果平台要求登录：

1. 停止下载。
2. 让用户在内置浏览器中登录。
3. 保留浏览器标签。
4. 登录后继续，不导出或落盘浏览器 Cookie。

示例：

```bash
yt-dlp --cookies-from-browser edge --skip-download \
  --print "%(title)s|%(uploader)s|%(duration)s|%(description)s" "<VIDEO_URL>"

yt-dlp --cookies-from-browser edge \
  -o "<WORK_DIR>/downloads/%(id)s.mp4" "<VIDEO_URL>"
```

## 3. 找字幕带

先抽帧和 OCR，确认字幕在画面里的纵向位置。两行烧录字幕常见于 `0.72–0.92`，单行常见于 `0.75–0.90`。

```bash
python <SKILL_DIR>/scripts/ocr_subtitles.py \
  --video "<VIDEO_PATH>" \
  --out "<WORK_DIR>/subtitle-lines.json" \
  --band-top 0.72 --band-bottom 0.92 --fps 2
```

原生字幕模式再次强调：

- 主画面优先选无底部字幕的帧。
- 同一个字幕段只选一个时间点。
- 相邻时间点至少间隔一个完整切换，通常 `>= 0.8 秒`。
- 主画面和字幕条不能出现同句。
- 不重复的检查必须做在成品 JPG 上，而不是只检查候选帧。

选择时间点必须满足：

- OCR 置信度通常不低于 0.85。
- 同一句在连续采样中持续至少 0.4 秒。
- 文本完整，不是切换瞬间、残影、重复行或广告贴片。
- 五个时间点顺序递增，并组成可读的论证链。
- 热点事件先核验事实，再决定标题。标题不能只写“一个消息/一条海报”，必须说明具体对象。

## 4. 生成 manifest

原生字幕模式示例：

```json
{
  "images": [
    {
      "title": "具体事件短标题",
      "times": [12.0, 15.5, 18.0, 22.5, 28.0]
    }
  ]
}
```

- `times[0]` 是主画面，`times[1:]` 是字幕条。
- 原生字幕模式不得把 OCR 文本重绘到画面上。
- 两行字幕在多图布局中容易被压小。优先采用“1 主图 + 2 字幕条”，或将 `--hero-fraction` 降到约 `0.55`。
- 默认单行字幕可使用 4 个字幕条和 `--hero-fraction 0.70`。

## 5. 渲染

使用已安装的 `native-subtitle-quote-image`：

```bash
python "<CODEX_HOME>/skills/native-subtitle-quote-image/scripts/native_subtitle_stitch.py" render \
  "<VIDEO_PATH>" \
  --manifest "<WORK_DIR>/manifest.json" \
  --out-dir "<OUTPUTS_DIR>" \
  --aspect 3:4 --width 1080 \
  --band-top 0.72 --band-bottom 0.92 \
  --hero-fraction 0.55 --overwrite
```

渲染前先运行该 Skill 的版本检查；发现更新只提醒，不自动覆盖。

## 6. 质检

对每张 JPG 做 OCR 回读，至少检查：

- 输出尺寸和比例正确。
- 图片数量与 manifest 一致。
- 主画面和字幕条完整，没有只有半句。
- 同一条字幕不重复。
- 文本顺序与原视频一致。
- 标题与正文所指事件一致，正文明确写出“发生了什么”。
- 发现半句时，优先调整 `band-top`、`band-bottom`、`hero-fraction` 或时间点，不进入发布阶段。

质检结果和最终图片绝对路径写回 `workflow-state.json`。
## 事件封面图文模式 `event-cover-carousel`

默认使用该模式，固定产出“1 张独立封面 + 4 张正文图片”。封面与正文资产必须分开保存，不能把封面当作正文第一张。

### 1. 独立封面

1. 从主曝光视频抽出能识别事件主体或冲突的代表性原始画面。
2. 在画面中部加入背景层和文本排版，写入准确、简短的事件名称；不要只做纯文字封面，也不要伪造原画面没有的事实。
3. 默认输出 3:4 JPG，保存为 `assets.cover_path`，并把实际封面文字写入 `assets.cover_text`。
4. 封面只用于抖音作品封面设置，禁止放进 `assets.content_images`。

### 2. 正文四图

`assets.content_images` 必须严格按以下顺序保存 4 个绝对路径：

1. 事件经过卡：白底黑字，完整写清时间、人物、地点、事件经过、争议点和必要回应。文字必须在单张图和手机缩略图中可读。
2. 原视频截图 1：事件起因、初始经过或最早曝光画面。
3. 原视频截图 2：关键动作、直接冲突或最能说明事件的核心画面。
4. 原视频截图 3：关键证据、当事方回应、处理进展或结果转折。

三张截图的选择硬门：

- 必须来自已经核验的视频时间点，并记录 `source_url`、`source_time` 和选择理由。
- 必须是三个不同的时间或信息节点，不能是同一画面的连续截图或近似重复。
- 画面要能代表事件本身，不能因为画面清晰却与事件核心无关就选用。
- 没有三张合格截图时停止并向用户说明，不得随机截图凑数。
- 优先使用主曝光视频；有其他公开来源可用于补充关键证据时再跨来源，不为了凑来源数量牺牲代表性。

如果使用 `native-subtitle-quote-image` 辅助定位：

- 只用它核对字幕、稳定帧和时间点。
- 必须把三个时间点分别导出为独立截图，不能把该 Skill 默认生成的单张纵向字幕拼图直接放进正文。
- 不得 OCR 后重绘、伪造或改变原始截图中的事件内容。

### 3. 状态与质检

状态文件示例：

```json
{
  "assets": {
    "mode": "event-cover-carousel",
    "cover_path": "<WORK_DIR>/outputs/cover.jpg",
    "cover_text": "准确的事件名称",
    "content_images": [
      "<WORK_DIR>/outputs/01-event-summary.jpg",
      "<WORK_DIR>/outputs/02-frame-cause.jpg",
      "<WORK_DIR>/outputs/03-frame-conflict.jpg",
      "<WORK_DIR>/outputs/04-frame-evidence.jpg"
    ]
  }
}
```

发布前逐张打开检查：

- `cover_path` 存在、事件名称准确，且不等于 `content_images` 中任意一张。
- `content_images` 恰好 4 张，顺序与角色一致。
- 白底经过卡无截断、乱码、事实错误。
- 三张原视频截图场景不同，分别支持同一条叙事主线。
- 标题、经过卡、三张截图和正文指向同一事件。
