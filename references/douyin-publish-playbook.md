# 抖音发布操作手册

发布前同时阅读 [lessons-and-guardrails.md](lessons-and-guardrails.md)。定时时间调整、草稿重传和叙事一致性以该文件为准。

## 浏览器绑定

使用当前会话的浏览器插件连接内置浏览器：

```js
const { setupBrowserRuntime } = await import("<ACTIVE_BROWSER_PLUGIN>/scripts/browser-client.mjs");
const agent = await setupBrowserRuntime();
const iab = await agent.browsers.get("iab");
await iab.nameSession("📌 抖音金句图自动发布");

const tabs = await iab.tabs.list();
const tab = tabs.length > 0 ? await iab.tabs.get(tabs[0].id) : await iab.tabs.new();
```

- 复用同一个 `iab` 绑定和已保留标签。
- 登录页、发布页或内容管理页需要跨回合时执行 `markHandoff()`；已提交结果页执行 `markDeliverable()`。
- 不关闭登录标签，不清理 Cookies，不退出账号。

## 登录中断协议

打开：

```text
https://creator.douyin.com/creator-micro/home
```

如果页面出现“创作者登录”“扫码登录”“验证码登录”：

1. 状态写为 `login_required`。
2. 执行 `await tab.markHandoff()`。
3. 停止浏览器自动化。
4. 只告诉用户：请在内置浏览器完成登录，完成后回复“登录好了”。
5. 下一回合先读取保留标签；只要 URL 已进入 `/creator-micro/home`，直接继续，不重新登录。

## 上传图文

1. 打开创作者首页。
2. 点击“发布图文”。
3. 等待上传页出现 `input[type="file"]`。
4. 用 file chooser 一次上传按顺序排列的 JPG/PNG：

```js
const chooserPromise = tab.playwright.waitForEvent("filechooser", { timeoutMs: 20000 });
await tab.ax.click(<选择文件按钮序号>);
const chooser = await chooserPromise;
await chooser.setFiles(["/absolute/path/01.jpg", "/absolute/path/02.jpg"]);
```

5. 回读“已添加 N 张图片”，N 必须与状态文件一致。

## 标题和正文

- 标题输入框：`input[placeholder="添加作品标题"]`，通常上限 20 字。
- 正文是第一个 `[contenteditable="true"]`，通常上限 1000 字。

重写正文时必须先全选清空，防止旧文案与新文案拼接：

```js
const editor = tab.playwright.locator('[contenteditable="true"]').first();
await editor.click();
await editor.press("Control+A");
await editor.press("Backspace");
await editor.fill(description);
```

发布前必须回读完整标题、正文和话题标签。

## 背景音乐

1. 点击“选择音乐”。
2. 在搜索框搜索情绪、类型或曲名。
3. 点击具体曲目，确认出现该曲目的标题、作者、时长和试听进度。
4. 点击“使用”。
5. 回读“修改音乐”区域，确认名字与作者正确。

选择原则：

- 社会议题、现实压力、情感讨论：优先低压纯音乐，不抢字幕。
- 不选择口播、强节奏、歌词密集或情绪过满的歌曲。
- 音乐不替代事实核验，也不替代用户对发布时间和内容的确认。

## 定时发布

1. 点击“定时发布”单选项。
1. 当前时间加 2 小时是平台最早可选时间；超过 14 天不可选。
2. 在时间输入框中填写 `YYYY-MM-DD HH:MM`。
3. 立即回读输入框最终值。平台可能自动向前调整，例如请求 20:30、回读为 20:45。
4. 回读值不等于用户请求值时，先取得用户确认，再记录 `requested_at`、`minimum_allowed_at`、`actual_at` 和 `adjustment_reason`。
5. 平台一般要求发布时间在 2 小时后至 14 天内。
6. 确认回读时间与用户最终确认值一致。
5. 状态改为 `awaiting_schedule_confirmation`。

## 最终确认门

点击最终按钮前，向用户展示：

- 平台和账号
- 标题
- 正文首段或全文
- 图片数量
- 背景音乐名称和作者
- 可见范围
- 完整发布时间

只有用户回复明确确认后，才将：

```json
{"schedule":{"confirmed":true}}
```

写入状态文件并点击“发布”。

## 提交后验证

提交成功后通常跳转到：

```text
/creator-micro/content/manage
```

验证：

1. 页面出现“发布成功”。
2. 刷新内容管理页。
3. 列表中能读到正确标题。
4. 能看到用户确认的 `YYYY年MM月DD日 HH:MM`。
5. 状态为“审核中”“待发布”或其他平台中间状态时，按实际状态报告，不声称已经公开可见。

## 个人资料修改

抖音个人主页支持在网页端修改昵称、简介和头像，但编辑图标没有可见文字，AX 树通常不会直接暴露“编辑资料”按钮。

1. 打开 `https://www.douyin.com/user/self`。
2. 找到昵称右侧的铅笔图标。必要时用 DOM 定位 `.REOLM3RC span[role="img"]`。
3. 点击后出现“编辑资料”弹窗。
4. 昵称输入框：`input[placeholder="记得填写昵称"]`。
5. 简介输入框：弹窗内最后一个 `[contenteditable="true"]`，写入前先全选清空。
6. 头像上传：点击头像区域容器 `.vc6pXRJt`，等待 `filechooser` 后上传 PNG/JPG。
7. 头像支持上传后，可能出现“使用原设备扫码”安全验证。必须停止并让用户在内置浏览器完成验证，不得绕过。
8. 用户验证完成后，继续同一标签；先保存头像裁剪框，再保存资料弹窗。
9. 回读主页昵称、简介和头像 URL，确认全部生效。

如果验证页、头像裁剪框或资料弹窗被关闭，重新进入个人主页从头执行；不要调用私有接口。
## 混合原始图文发布

- 图片顺序固定为：封面、完整说明、事件图1、事件图2、事件图3。
- 封面使用原事件画面并叠加短事件名。
- 标题填写短事件名，正文只填标签。
- 不要同时保留多条未发布草稿。每条提交后回内容管理核验，再处理下一条。
- 多条定时发布时，逐条核对日期、时间和作品张数。