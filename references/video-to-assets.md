# 视频到金句图

先读 [lessons-and-guardrails.md](lessons-and-guardrails.md)。其中“曝光视频优先”“原生模式锁定”“字幕不得重复”是硬约束。

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
## 混合原始图文模式

用户明确要求“封面用原事件截图 + 白底说明 + 原始图片”时，使用混合原始图文模式：

1. 封面：从主曝光视频抽取最具冲突感的原始帧，叠加事件名称。
2. 事件说明：白底黑字，完整写清时间、人物、经过、争议和必要回应。
3. 事件图 1：主来源的原始画面。
4. 事件图 2：主来源的另一个原始画面。
5. 事件图 3：另一个公开来源的原始画面。

禁止：

- 用纯白底说明卡做封面。
- 所有事件图都来自同一条视频。
- 在原始事件图上重绘、伪造证据。
- 让标题、说明卡和原始图片指向不同事件。