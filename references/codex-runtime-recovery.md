# Codex 运行故障与恢复

## 悬空工具调用

### 症状

- 任务突然失败，错误中包含：

  `No tool output found for tool call call_...`
- 上游通常表现为 `/responses` 返回 HTTP 400，可能经过 CC Switch 或其他代理转发。
- 在同一线程继续发送“继续”后，即使切换供应商，仍会报同一批旧 `call_id`。

### 根因

这不是素材文件损坏，也不是单纯的上游模型故障。失败的会话历史中保留了“已发起但没有对应 tool output”的工具调用；后续请求携带了不完整消息链，上游因此拒绝整个请求。

### 恢复规则

1. 停止在故障线程继续发送消息，不要把“继续”当作修复动作。
2. 以磁盘文件和已保存标签页为准，读取 `workflow-state.json`、发布计划、产物目录和最近核验结果。
3. 从故障线程 fork 一个干净线程，或新开线程并附上简短交接信息：工作目录、当前阶段、已验证产物、下一条待执行动作、内置浏览器标签状态。
4. fork 只会复制已完成历史，不会复制失败中的未完成轮次，适合恢复此类悬空调用。
5. 恢复后重新取得 Codex 内置浏览器和标签页句柄，不要假设上一线程的对象仍可复用。

### 批量读图

一次同时发起多张 `view_image` 可能增加工具结果未完整回写的风险。成品 QA 默认逐张读取并确认结果返回后再看下一张，不要在一次工具批次里并发提交多张成品图。

## iab 浏览器不可用

- 先检查当前任务是否已启用 Codex browser 插件，并确认 `nodeRepl.rpc` 是可调用的函数。
- 使用浏览器插件提供的 `setupBrowserRuntime`，再执行 `agent.browsers.list()`。
- 只选择 `type === "iab"` 的 Codex 内置浏览器。Edge/Chrome extension 或外部浏览器不能作为静默替代。
- 若 `nodeRepl.rpc` 未定义、列表中没有 `iab`，或标签页操作持续报浏览器服务错误，停止并说明阻塞；需要外部浏览器时先取得用户明确同意。
- 登录页、发布页和结果页跨回合时分别使用 `markHandoff()` 和 `markDeliverable()`。

## 点击后页面不变

当“使用”“发布”等语义点击没有产生状态变化时：

1. 先确认按钮可见且可用，检查当前 URL、页面截图、必填项错误和弹窗遮挡。
2. 同名文本可能有多个节点，其中只有一个是可见按钮；使用 `filter({ visible: true })` 缩小范围。
3. 确认没有缺失字段或异步阻塞后，再使用一次带超时的 `force: true` 点击。
4. 点击“发布”后等待进入内容管理页；必须刷新并回读标题、图片数、时间和状态，不能把“发布成功”提示当作最终成功。

## Windows 状态脚本

在 Windows 上运行 `workflow_state.py` 时优先设置 `PYTHONUTF8=1`：

```powershell
$env:PYTHONUTF8='1'
python <SKILL_DIR>/scripts/workflow_state.py show --state <WORK_DIR>/workflow-state.json
```

控制台显示乱码不等于 JSON 文件已损坏；可用 Node `JSON.parse(fs.readFileSync(path, "utf8"))` 或读取原始字节复核。确认文件已损坏时停止，不要继续覆盖状态。
