# 闪念：原生 Apple 三件套语音助手

**目标设备**：iPhone（iOS 27 或兼容系统），由 Action Button 启动 Apple Shortcuts。  
**语言**：中文优先，兼容中英混合口述。  
**唯一数据源**：Apple Notes（备忘录）、Apple Calendar（日历）、Apple Reminders（提醒事项）。  
**模型**：支持自定义 OpenAI-compatible Chat Completions API 的 Base URL / Model / API Key（BYOK）。  
**交付**：可读、可编辑的源 XML/plist + 经 Apple `shortcuts sign` 签名的 `.shortcut` 文件；在真实 iPhone 上仍需最终测试和授权。

---

## 交给具备文件和终端能力的 AI Agent 的构建任务

你是 Apple Shortcuts 资深工程师。请使用已经安装的 **Shortcuts Playground** 插件、其 action schema / golden examples / validator，构建一个适用于 **iOS 27 iPhone** 的原生快捷指令，名称「闪念」。不要只写说明文档。请生成实际的 Shortcuts XML/plist，执行可用的静态验证，在这台 Mac 上用 Apple 自带 `shortcuts sign` 生成 `.shortcut`，并报告可能需要在 iPhone 上手动配置的动作。

### 1. 唯一允许的能力（六个）

- `note.create`：在 Apple 备忘录创建新笔记；保留用户原话的关键信息，必要时整理标题。
- `note.search`：从 Apple 备忘录查找匹配的现有笔记，读取必要正文并回答。若只支持关键词搜索，明确告知不能保证语义召回。
- `calendar.create`：在 Apple 日历创建事件（标题、起止时间、全天、备注、可选地点）。
- `calendar.search`：查找指定时间段内的日历事件并用简短中文回复。
- `reminder.create`：在 Apple 提醒事项添加待办（标题、截止日期、时间、可选备注/列表）。
- `reminder.search`：查询指定范围的提醒事项，包括是否完成。默认只查询未完成，用户明确要求才显示已完成。

禁止删除、批量修改、标记完成、读写其他 App、浏览器操作、后台数据同步、第三方笔记库。

### 2. 用户体验

- 从 iPhone Action Button **长按触发**快捷指令；Shortcut 运行后用系统“听写文本”（Dictate Text）进行中文语音输入。不能声称支持原生“按住讲话松手发送”；实际结束方式使用系统听写支持的停止方式。
- 同时允许从快捷指令 App 运行并输入文字，以便在 Mac 上有限测试。
- 模型自动识别操作，不要求用户先选择 Note / Calendar / Reminders。
- 写入成功：给出简短通知，如「已存入备忘录：xxx」。查询：展示结果或可选朗读。
- 无网、API 失败或解析错误：**不要丢失原始口述内容**；显示错误，并让用户选择将原话保存为 Apple 备忘录（必须明确确认）。
- 遇到有歧义的日期/时间（如「周末有个会」）先询问；不允许编造准确时刻。
- 查询没结果时直接说「没有找到」，不能脑补行程或笔记。
- 一个口述可能包含多个操作，优先支持返回 `operations[]` 列表，且逐个执行；若 Shortcuts 受限，可在 v1 限定一次一个操作，并提示分开说，不可悄悄丢弃后续任务。

### 3. BYOK 配置与 API

- 首次使用时提供配置变量（或导入提问）：`API_BASE_URL`（示例 `https://api.openai.com/v1`）、`API_MODEL`（由用户填写）、`API_KEY`（由用户在自己设备填写）。不要假定用户使用特定厂商的密钥，也不要将真实密钥写入源码、日志或提示词。
- 请求 OpenAI-compatible `POST <base_url>/chat/completions`，鉴权 `Authorization: Bearer <key>`，JSON 中使用 `model`, `messages`。若提供方不支持 JSON schema response format，则采用严格 JSON-only 提示词并校验结果。
- 用系统动作「获取 URL 内容」访问 API。要正确处理 HTTP 失败、非法 JSON 和空字段；不要把用户内容发送到任何其他域名。
- 模型仅负责**意图分类、日期解析、生成查询词、对本地查询结果作语言整理**；真正增删查由本地 Apple Shortcuts 系统动作执行。禁止采用模型输出任意 Shortcuts action 名称/URL 执行不在白名单内的操作。

### 4. 意图解析响应契约

第一轮给模型的系统提示词应限定输出：

```json
{
  "operations": [
    {
      "action": "note.create | note.search | calendar.create | calendar.search | reminder.create | reminder.search | clarify",
      "title": "string",
      "body": "string",
      "query": "string",
      "start": "ISO8601 or empty",
      "end": "ISO8601 or empty",
      "due": "ISO8601 or YYYY-MM-DD or empty",
      "all_day": false,
      "include_completed": false,
      "question": "string"
    }
  ]
}
```

- 日期解释必须基于快捷指令传入的 `Current Date` 和当前时区，绝不能使用模型内部的假定日期。
- 标题和用户原话应保留中文，避免为了整洁篡改原意。
- Calendar 创建若只有开始时间而无结束时间，可询问持续时间；不得擅自虚构。若用户明确只指定日期则创建全天事件（经确认）。
- Reminder 只有日期而无时间时用全天截止日期，不得自作主张设为 9:00。
- 生成的动作名必须严格映射到这七种（六种+clarify）；不支持的动作走失败分支。
- 重要：真实模型响应中的 JSON 字段只有在类型验证通过后才能用来写入系统数据。

### 5. 本机数据查询方案

- `note.search`：先用关键词过滤 Apple Notes 的名称/正文（以 Shortcuts 实际可用的过滤条件为准）。设置合理候选上限，例如 10～20 条，避免把全部笔记发送给模型；如果无关键词匹配，可以询问更具体的线索。
- `calendar.search`：用用户请求范围过滤 Apple Calendar 事件，结构化提取标题、开始、结束等字段，送模型生成答案。默认时间范围尽量小，不能无范围批量读取全部历史。
- `reminder.search`：用日期、是否完成、标题等条件过滤 Apple Reminders；默认未完成，不发送无关提醒内容。
- 查询先**真实读取本机系统数据**，再回答；严禁只让模型自行预测「我明天有什么安排」。

### 6. 安全与体验保障

- 写入前尽量展示简短确认，或提供可关闭的确认选项；首次测试保持确认开启。
- 明确说明输入文字、必要查询片段会发给自选 API 提供方；系统原始数据保留在 Apple App/iCloud。
- 不要写入 第三方聊天记录库、Notion、Todoist、Drafts、Google Calendar 等第三方数据库。
- 首次执行时提示允许 Shortcuts 访问备忘录、日历、提醒事项、麦克风和网络（实际以系统弹窗为准）。
- 每个主要分支有可读 Comment；变量必须正确连接。不要留下任何 Unknown Action/空必填字段/占位符。
- 输出一个测试清单、一个快捷指令源文件和签名后的 `.shortcut` 文件。能在 Mac 测的内容先测；**真实 iOS 动作必须注明等待用户在 iPhone 上验证**。

### 7. 测试样例

1. 「记一下，我想把手机操作按钮做成灵感入口」→ `note.create`。
2. 「我之前记的那个手机快捷按钮设计是什么」→ `note.search`，只根据实际查到的笔记回答。
3. 「明天下午三点到四点见导师」→ `calendar.create`。
4. 「明天有什么日程」→ `calendar.search`，读取真实事件。
5. 「周五之前提醒我买洗衣液」→ `reminder.create`，必要时明确截止日。
6. 「我还剩什么没有完成的事」→ `reminder.search`，筛选未完成。
7. 「帮我删除全部提醒事项」→ 拒绝执行，不执行任何删除。
8. API 返回 401、超时、非 JSON → 错误反馈，原话仍可人工保存。
9. 「明天提醒我买书，再记一下这本书推荐给朋友」→ 两个操作或主动要求拆分，不得漏掉一个。

### 8. 交付检查

- 目标平台设为 **iOS**，不要误用 macOS-only AppleScript/JXA 或仅 macOS 可用的 AppIntent。
- 在 Mac 上签名之后，输出具体文件路径；不要声称已经实机测试。
- 如插件或 Shortcuts 当前实现不能支持某个功能，明确标记「未实现」，不要假装六个功能全部可用。
- 提醒用户最后在 iPhone：「设置 → 操作按钮 → 快捷指令 → 闪念」绑定。用户需要自己完成一次授权和实际导入。

---

## 获取构建参考资料

使用具备仓库读写和终端能力的 AI Agent，按 Shortcuts Playground 的插件机制或公开参考源获取动作资料。
查找包含 `SKILL.md` 与 `scripts/` 的技能目录，阅读格式和示例后构建、验证并在 Mac 签名。
构建时记录每项能力的真实验证结果，不能用静态检查代替 iPhone 实测。

来源：
- https://github.com/viticci/shortcuts-playground-plugin
- https://github.com/runnerr0/OpenShortcuts
- https://github.com/Wuvomi/shortcut-cli