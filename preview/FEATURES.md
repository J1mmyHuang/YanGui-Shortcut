# 闪念：签名测试版交付说明

此构建是供 iPhone 导入审查与实测的测试版，**不是六项能力均已验证的正式版**。源文件为 `ShanNian.xml`，目标名称为「闪念」。Apple 签名只证明文件成功封装签名，不证明动作能运行。

## 六项能力

| 操作 | 已实现及静态检查覆盖 | 已实现、仍未验证 | 缺失或限制 |
| --- | --- | --- | --- |
| `note.create` | 固定原生 Create Note 分支；标题与正文组合为一个输入；写入前确认；正文保留原话 | legacy `com.apple.mobilenotes.SharingExtension` + `WFCreateNoteInput` 在当前 iPhone 的识别及创建结果；插件整体校验未通过 | 现代 iOS Notes 动作迁移尚未验证；恢复笔记也依赖这个动作 |
| `note.search` | 名称 OR 正文关键词过滤；最多10条；正文最多1200字符；空结果明确显示未找到 | iPhone Notes 权限、过滤属性与正文读取；插件把此动作标成 macOS 专用 | 不做语义搜索，不把查得笔记交给模型；短关键词可能漏召回 |
| `calendar.create` | 原生创建；标题、起止时间、全天、备注；明确确认；正向区间和日期格式保护 | 真实 iPhone 的时区、夏令时、全天排他结束日期及目标日历选择 | 无自动指定日历；地点保留在备注；缺少结束时间时先澄清 |
| `calendar.search` | 原生结束日期下界、可选标题关键词、开始时间排序；最多10候选；上界排他检查；保留跨界重叠事件 | 系统过滤与权限行为 | 一次范围最多31天（秒数上限容许一次夏令时切换）；结果为本机结构化中文展示 |
| `reminder.create` | 原生无截止待办，或明确时刻及偏移的截止提醒；标题、备注、确认 | iPhone 默认列表、具体时刻和通知行为 | **仅日期的全天提醒未实现，会明确停止，不补设午夜或9点**；不指定自定义列表 |
| `reminder.search` | 默认未完成；明确要求并确认才包含已完成；可选范围/标题词；最多10条；上界排他 | iPhone 完成状态、截止日期属性、列表名称和权限 | 无日期范围时返回最多10条；不自动分页 |

“静态覆盖”仅指源结构、离线契约与模拟动作流检查，不代表完整 Shortcuts Playground 校验通过或 Apple 真机测试通过。

## 校验结果与遗留问题

- `plistlib` 能读取实际交付 XML；`plutil -lint` 通过。
- 图标与颜色已使用插件 resolver 选择；UUID 由本机 `uuidgen` 生成。
- 离线测试覆盖 JSON 类型/转义/白名单、多操作拒绝、原生 JSON 请求数组、日期与偏移、epoch 操作数、关键词筛选、密钥输入，以及模拟路由。运行结果见 `offline-tests.log`。解释器是自建模拟器，不是 Apple Shortcuts 引擎。
- **未修改的 Shortcuts Playground 1.2.1 validator 整体失败**。iOS27 最终完整日志见 `validation-ios27.log`：两个 Create Note 动作分别缺少其要求的 `AppIntentDescriptor` 和独立 title/name 参数，并被目录标为 macOS-only；Find Notes 也被标为 macOS-only。没有添加虚构描述符、别名或修改验证器来让它通过。
- macOS26 交叉校验见 `validation-macos26.log`，剩余相同的 Create Note 描述符和标题检查错误。最初 iOS26 检查见 `validation-ios26.log`；该插件仅有 iOS27 快照，连 Comment 等基础动作都被目标版本规则拒绝，不能据此宣称 iOS26 兼容。
- 已进行针对性修复并停止重复校验，未超过5轮修复限制。插件 `SKILL.md` 的退出条件为 “Same errors repeating … stop”。这些失败没有被当作已获准豁免的误报。
- Notes 的本机静态元数据和插件的现代 macOS 参数，不能证明 iPhone 旧动作的完整导出格式。保留具有公开 iOS 工具映射依据的 legacy 输入键：标题、空行、正文组成 `WFCreateNoteInput`。**若 iPhone 无法识别恢复笔记动作，整个流程会在调用 API 前停止。**
- 签名方式和隐私说明见 `SIGNING.md`；文件大小和 SHA-256 见 `build-manifest.json`。

## 本次运行流程与故障恢复

1. 选择中文听写或文字。听写使用系统点按停止；不支持按住讲话松手发送。
2. 先展示完整原话供核对/复制。明确同意后创建一条「闪念原话 · 当地时间」恢复笔记；取消则结束。
3. 本次运行分别输入 HTTPS API Base URL、Model、API Key，确认向该地址发送原话。
4. 最多三轮模型解析/澄清。完整 JSON 必须符合固定字段顺序、实际类型和六项操作白名单。多操作整体停止并要求拆开说。
5. 所有目标创建再次确认；查询真实本机候选后在本机展示。不会删除、修改、标记完成。

原生网络/权限动作可能直接中断 Shortcuts，无法用普通条件分支捕获全部错误。因此采用联网前确认保存原话的恢复笔记，**每次运行都会额外创建一条恢复笔记**，不是仅失败时保存。没有默认同意或后台保存。

API 返回可读取的错误、空字段或非法模型 JSON 时，会显示错误及原话。网络或后续权限动作直接中断时，从已保存的恢复笔记找回；若 Notes 本身被拒绝授权或动作不兼容，则无法保证磁盘备份，使用先前原话展示界面复制文本。麦克风被拒绝可能直接中止，需重新运行选择文字输入。

## 密钥与隐私

- 构建没有使用真实 API Key，没有读取个人笔记、日历、提醒事项或云备份，没有调用付费模型 API。
- Key 每次在 iPhone 的「询问输入」中填写，输入可见；动作没有默认 Key，流程不将 Key 写入备忘录、文件、通知、模型提示词或剪贴板。不要在编辑器中把 Key 改成固定文本或默认值，否则可能随快捷指令/iCloud 同步和分享。
- 发送给自选 API 的是原话、澄清对话、设备当地时间和时区。认证 Key 通过请求 Authorization 头发送到同一提供方。数据保留、费用由该提供方决定。
- 本机查询到的笔记、日历和提醒记录不再发给模型。恢复笔记及目标记录按 Apple App 的账户/iCloud 设置正常同步。
- 不要在原话中口述密码或密钥；原话是用户明确确认的备份内容及 API 输入。

## iPhone 导入与验收

通过隔空投送或 iCloud Drive 在 iPhone 打开 `ShanNian.shortcut`，审查动作后添加到「快捷指令」。优先在快捷指令 App 内用文字输入实测；系统权限按需授权。验证后到「设置 → 操作按钮 → 快捷指令 → 闪念」绑定。

建议使用无敏感信息的测试数据，并逐项检查：

- [ ] **首先检查两处创建备忘录和一处查找备忘录有无未知动作**；测试「同意保存原话并继续」确实生成恢复笔记，取消时不联网。
- [ ] note.create：「记一下，测试操作按钮灵感入口」；核对标题/正文/原话。
- [ ] note.search：用该测试笔记的独特关键词检索；另一随机词应明确没有找到。
- [ ] calendar.create：明确起止时刻；跨时区瞬间；跨午夜；夏令时日；全天单日与多日；倒序/非法日期应停止。
- [ ] calendar.search：跨范围下界的事件保留；等于结束上界的事件排除；标题词在10条上限之前筛选。
- [ ] reminder.create：无日期待办与明确时刻；仅日期输入应停止并说明未实现，不能生成午夜通知。
- [ ] reminder.search：默认不含已完成；明确要求时确认并包含；测试无截止项目、边界、关键词与空结果。
- [ ] 模型返回缺字段、错误类型、未知 action、重复字段、空 operations、多个操作时，没有目标创建动作。
- [ ] 401/额度不足、HTML响应、离线/超时、拒绝 Calendar/Reminders 权限：核对恢复笔记仍可找回原话。
- [ ] 中文听写为空时文字补充；拒绝麦克风后重新运行文字入口；连续澄清最多三轮。

本机只完成构建、静态/离线检查和签名；**没有执行这些 iPhone 验收测试，也没有验证真实 API 响应或系统写入。**

## 依据与重建

- 本仓库构建要求：`../ci/BUILD_LOCAL_PROMPT.md`、`../spec/闪念_Shortcuts_构建规格.md`。
- 安装的 Shortcuts Playground 1.2.1：在已有插件或参考源中查找包含 `SKILL.md` 和 `scripts/` 的技能目录。
- legacy iOS Create Note 输入键：[作者 Shortcut Source Tool 动作映射](https://github.com/extratone/jellycuts/blob/main/ShortcutsBatchSource.jelly#L539-L543)。这是工具映射依据，不是当前 iPhone 导出实例。
- 经用户授权读取的本机 Notes 静态 AppIntents 元数据：`/System/Applications/Notes.app/Contents/Resources/Metadata.appintents/extract.actionsdata`，SHA-256 `943fa568d0801beb18a064e6c917511ef483cb170209b4058d5ed6bcb115e67e`；仅查看动作定义，未查看用户数据。
- HTTP 请求参照 [Chat Completions 官方文档](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)。

生成器：`python3 preview/build_shannian.py`；离线检查：`python3 -m unittest discover -s preview -p 'test_*.py' -v`。重新生成 XML 后须重新静态校验并签名，旧签名不会自动更新。仓库跟踪 `preview/` 中的测试版快照与可重建源文件。本机临时构建目录 `dist/` 继续被 Git 忽略。未包含本机凭据或个人数据库。
