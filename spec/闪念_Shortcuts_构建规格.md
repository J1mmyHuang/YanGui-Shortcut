# 闪念：原生 Apple 三件套语音助手

**目标设备**：iPhone（iOS 27 或兼容系统），由 Action Button 启动 Apple Shortcuts。  
**语言**：中文优先，兼容中英混合口述。  
**唯一数据源**：Apple Notes（备忘录）、Apple Calendar（日历）、Apple Reminders（提醒事项）。  
**模型**：支持自定义 OpenAI-compatible Chat Completions API 的 Base URL / Model / API Key（BYOK）。  
**交付**：可读、可编辑的源 XML/plist + 经 Apple `shortcuts sign` 签名的 `.shortcut` 文件；在真实 iPhone 上仍需最终测试和授权。

**交互**：按一下 Action Button 直接开始听写，说完点按完成，自动分段、分类并写入。

---

## 交给具备文件和终端能力的 AI Agent 的构建任务

你是 Apple Shortcuts 资深工程师。请使用 **Shortcuts Playground** 的 action schema / golden examples / validator（可通过插件或直接读取参考源文件），构建一个适用于 **iOS 27 iPhone** 的原生快捷指令，名称「闪念」。Agent 必须具备所需文件和终端能力。不要只写说明文档。请生成实际的 Shortcuts XML/plist，执行可用的静态验证，在 Mac 上用 Apple 自带 `shortcuts sign` 生成 `.shortcut`，并报告可能需要在 iPhone 上手动配置的动作。

### 1. 唯一允许的能力（六个）

- `note.create`：在 Apple 备忘录创建新笔记；保留用户原话的关键信息，必要时整理标题。
- `note.search`：从 Apple 备忘录查找匹配的现有笔记，读取必要正文并回答。若只支持关键词搜索，明确告知不能保证语义召回。
- `calendar.create`：在 Apple 日历创建事件（标题、起止时间、全天、备注、可选地点）。
- `calendar.search`：查找指定时间段内的日历事件并用简短中文回复。
- `reminder.create`：在 Apple 提醒事项添加待办（标题、截止日期、时间、可选备注/列表）。
- `reminder.search`：查询指定范围的提醒事项，包括是否完成。默认只查询未完成，用户明确要求才显示已完成。

禁止删除、批量修改、标记完成、读写其他 App、浏览器操作、后台数据同步、第三方笔记库。

### 2. 用户体验

- 按一下 iPhone Action Button，快捷指令先检查配置，通过后立即开始系统「听写文本」（Dictate Text，中文）。没有菜单、没有输入框。
- 听写结束方式：「停止聆听」设为点按完成。不能声称支持原生“按住讲话松手发送”；操作按钮第二次按下能否结束听写需在 iPhone 实测，记录结果。
- 听写结束后全程自动：模型把口述拆成多个独立事项，每项自动归入备忘录、提醒事项或日历，逐项写入。
- **智能分类**：有明确日期（可带时间）的会议、约会、活动、行程 → 日历；要自己去做的待办、提醒、截止事项 → 提醒事项；想法、灵感、信息、清单和拿不准的内容 → 备忘录；明确要查找已有记录 → 对应 App 的真实查询。
- 全部写入成功：一条通知汇总每一项的去向，如「已处理 3 项」。有查询结果、改存或未执行的事项时，用弹窗展示完整内容。
- 无网、API 失败或解析错误：**不要丢失原始口述内容**。能读取到的失败自动把原话存成备忘录并显示；配置里提供「原话备份」开关，打开后每次联网前先存一份。
- 遇到有歧义的日期/时间（如「周末有个会」）不猜：改存为备忘录或无日期待办，并保留原话说法；不允许编造准确时刻。只给开始时间没说时长的日历事件，按 1 小时记录并在备注注明。
- 任一事项校验失败时，该项改存为备忘录并说明原因，其余事项照常写入。
- 查询没结果时直接说「没有找到」，不能脑补行程或笔记。
- 一个口述可能包含多个操作：`operations[]` 全部逐个执行，不得丢弃任何一项。

### 3. BYOK 配置与 API

- 首次安装（导入快捷指令）时，通过**导入问题**明确要求用户填写 `API_PROTOCOL`（`openai` 或 `anthropic`）、`API_BASE_URL`（示例 `https://api.openai.com/v1`）、`API_KEY`、`API_MODEL`。四项对应快捷指令最前面的四个文本动作，用户之后可以直接点开修改。XML 中 Base URL、Key、模型为空；不要假定用户使用特定厂商的密钥，也不要将真实密钥写入源码、日志或提示词。
- 模型 ID 可手填；留空时每次运行先请求服务的 `/models`（openai 协议 `<Base URL>/models`，anthropic 协议 `<根地址>/v1/models`），列出模型让用户选择，并提示把选中的 ID 填入配置以跳过选择。
- API Key 保存在用户自己的快捷指令里，可能随 iCloud 同步；文档提示分享或导出前先清空。
- 接入方式为 API Key。OAuth 登录未接入：Anthropic 要求第三方产品使用 API Key；OpenAI 的 Sign in with ChatGPT 需要本地回环监听，快捷指令无法提供。
- openai 协议：`POST <base_url>/chat/completions`，鉴权 `Authorization: Bearer <key>`，JSON 中使用 `model`, `messages`。anthropic 协议：`POST <根地址>/v1/messages`，`x-api-key` 与 `anthropic-version` 头，JSON 中使用 `model`, `max_tokens`, `system`, `messages`，返回读第一个 `text` 内容块。若提供方不支持 JSON schema response format，则采用严格 JSON-only 提示词并校验结果。
- API 失败时，向用户显示服务返回的错误原文、协议、请求地址和模型（不含密钥）。请求体中的字典、数组、数字条目必须使用真实导出的 `WFItemType` 编码（0 文本、1 字典、2 数组、3 数字、4 布尔）。
- 用系统动作「获取 URL 内容」访问 API。要正确处理 HTTP 失败、非法 JSON 和空字段；不要把用户内容发送到任何其他域名。
- 模型仅负责**意图分类、拆分事项、日期解析、生成查询词**；真正创建和查询由本地 Apple Shortcuts 系统动作执行。禁止采用模型输出任意 Shortcuts action 名称/URL 执行不在白名单内的操作。

### 4. 意图解析响应契约

第一轮给模型的系统提示词应限定输出：

```json
{
  "operations": [
    {
      "action": "note.create | note.search | calendar.create | calendar.search | reminder.create | reminder.search",
      "title": "string",
      "body": "string",
      "query": "string",
      "start": "ISO8601 or empty",
      "end": "ISO8601 or empty",
      "due": "ISO8601 or YYYY-MM-DD or empty",
      "all_day": false,
      "include_completed": false,
      "checklist": false
    }
  ]
}
```

- 日期解释必须基于快捷指令传入的 `Current Date` 和当前时区，绝不能使用模型内部的假定日期。
- 标题和用户原话应保留中文，避免为了整洁篡改原意。
- 一段口述含多个事项时，每项一个操作，按口述顺序排列，不得合并或遗漏。
- 时间写成设备当地时间 `YYYY-MM-DDTHH:mm:ss`，不带时区偏移，由快捷指令按设备时区解释；仍接受带 `Z` 或 `±hh:mm` 的值。只说了钟点没说日期时，日期按今天。
- 归类：在某个日期或钟点发生、需要到场的事（会议、约会、活动）归日历，即使口述说成“提醒我下午3点有会议”；要自己去做的动作类待办归提醒事项。
- 清单类内容（购物清单、物品清单等并列条目）归备忘录，`checklist=true`，`body` 每行一个条目、不加符号。快捷指令先创建只有标题的备忘录，再对每个条目执行 Notes 的“追加待办项”，生成可勾选的清单。
- Calendar 创建：start 和 end 必填；只有开始时间时 end 为开始后 1 小时并在 body 注明；只有日期时 `all_day=true`，end 为最后一天的次日（排他边界）。
- Reminder 只说了日期没说钟点时（“今天”“周五之前”），由 AI 给出默认到期时间并在备注注明：日期是今天取当前时间之后的下一个整点，其他日期取当天 09:00。AI 仍只给日期时，快捷指令创建无提醒时间的待办，日期写在备注。
- Reminder 的时间说得模糊（“一会儿”“待会儿”“稍后”）或无法识别时，`due` 留空：创建没有提醒时间的待办，把原说法写进备注，不能因此创建失败。
- 日期说不准时不猜：改用 `note.create` 或 `due` 为空的 `reminder.create`，原话说法写入 body。
- 生成的动作名必须严格映射到这六种；契约之外的动作整体拒绝。
- 重要：真实模型响应中的 JSON 字段只有在类型验证通过后才能用来写入系统数据。

### 5. 本机数据查询方案

- `note.search`：先用关键词过滤 Apple Notes 的名称/正文（以 Shortcuts 实际可用的过滤条件为准）。设置合理候选上限，例如 10～20 条，避免把全部笔记发送给模型；如果无关键词匹配，可以询问更具体的线索。
- `calendar.search`：用用户请求范围过滤 Apple Calendar 事件，结构化提取标题、开始、结束等字段，送模型生成答案。默认时间范围尽量小，不能无范围批量读取全部历史。
- `reminder.search`：用日期、是否完成、标题等条件过滤 Apple Reminders；默认未完成，不发送无关提醒内容。
- 查询先**真实读取本机系统数据**，再回答；严禁只让模型自行预测「我明天有什么安排」。

### 6. 安全与体验保障

- 写入自动完成，完成后用通知汇总每一项的去向，便于核对；校验失败的事项改存为备忘录并说明原因。
- 明确说明输入文字、必要查询片段会发给自选 API 提供方；系统原始数据保留在 Apple App/iCloud。
- 不要写入 第三方聊天记录库、Notion、Todoist、Drafts、Google Calendar 等数据库。
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
9. 「明天提醒我买书，再记一下这本书推荐给朋友」→ 一次听写拆成两个操作（提醒 + 备忘录），全部写入。
10. 「明天下午三点到四点见导师，周五之前提醒我买洗衣液，还有我想把操作按钮做成灵感入口」→ 日历、提醒、备忘录各一条。
11. 「周末有个会」→ 不猜日期，改存为备忘录并保留原说法。

### 8. 交付检查

- 目标平台设为 **iOS**，不要误用 macOS-only AppleScript/JXA 或仅 macOS 可用的 AppIntent。
- 在 Mac 上签名之后，输出具体文件路径；不要声称已经实机测试。
- 如插件或 Shortcuts 当前实现不能支持某个功能，明确标记「未实现」，不要假装六个功能全部可用。
- 提醒用户最后在 iPhone：「设置 → 操作按钮 → 快捷指令 → 闪念」绑定。用户需要自己完成一次授权和实际导入，并在导入时填写 Base URL、模型 ID、API Key。

---

## 获取构建参考资料

使用任意具备仓库读写和终端能力的 AI Agent，读取[本地构建指南](../LOCAL_BUILD.md)和[通用构建任务](../ci/BUILD_LOCAL_PROMPT.md)。可按该 Agent 的插件机制接入 Shortcuts Playground，或获取其公开参考源，查找 `SKILL.md`、动作格式和验证脚本后直接使用。

最终 `.shortcut` 文件需要在 Mac 上用 Apple 原生工具签名。构建过程应记录实际执行的验证、未实现功能和需要 iPhone 复核的动作；规格本身不代表已完成构建或签名。

来源：
- https://github.com/viticci/shortcuts-playground-plugin
- https://github.com/runnerr0/OpenShortcuts
- https://github.com/Wuvomi/shortcut-cli
