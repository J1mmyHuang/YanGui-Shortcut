# 闪念 · ShanNian Shortcut

**本地构建：Mac + 具备文件和终端能力的 AI Agent。**



一个基于 iPhone Action Button 的轻量语音助手。只访问三款 Apple 原生 App：**备忘录、日历、提醒事项**。AI 只负责理解自然语言，实际读写由 Shortcuts 的本机动作执行。

> **当前状态：已生成本机 Apple 签名测试版，26项离线测试通过；尚未经过 iPhone 实测，Notes 动作仍未通过插件校验。** 仅日期的全天提醒未实现，遇到这种请求会明确停止。当前不宜作为已验证的日常助手。

## 本机签名测试版

- [下载 ShanNian.shortcut](preview/ShanNian.shortcut?raw=true)；[审阅源 XML](preview/ShanNian.xml)。
- [六项能力、限制与 iPhone 测试清单](preview/FEATURES.md)。
- [签名方式与隐私说明](preview/SIGNING.md)：本机发起 `anyone` 签名，Apple 会收到快捷指令副本以进行验证。
- [构建与签名摘要](preview/build-manifest.json)，以及 [iOS27 插件校验失败日志](preview/validation-ios27.log)。

通过隔空投送或 iCloud Drive 在 iPhone 打开文件，审查并导入。先用文字输入检查恢复备忘录动作，再逐项测试。验证后可在「设置 → 操作按钮 → 快捷指令 → 闪念」绑定。

此版本每次先经用户明确同意保存一条原话恢复笔记，以应对后续网络或权限动作直接中断；如果该 Notes 动作不兼容，流程可能在 API 请求前停止。API Base URL、Model 和 Key 在每次运行时输入，构建文件没有真实 Key。Key 输入可见。

可重建的生成器、UUID 池及离线测试也在 `preview/`，无需 API Key：

```sh
python3 -m unittest discover -s preview -p 'test_*.py' -v
python3 ci/validate_plist.py preview/ShanNian.xml
# 如需重新生成源 XML（之后须重新签名）：
python3 preview/build_shannian.py
```

`preview/` 保存这次测试版快照；`dist/` 继续作为被 Git 忽略的临时构建目录。推送只触发原有的免费基础源文件检查；26项行为测试请按上方命令在本机运行。AI 云构建仍需手动启动。

## 功能范围

| 原生 App | 创建 | 查询 |
| --- | --- | --- |
| Apple Notes | note.create | note.search |
| Apple Calendar | calendar.create | calendar.search |
| Apple Reminders | reminder.create | reminder.search |

支持中文语音、Action Button 快捷启动、BYOK 的 OpenAI-compatible Chat Completions API。禁止删除、修改现有数据或接入其他个人资料。

## 自动检查与构建

GitHub Actions 负责检查仓库内容。手动触发时，有生成器快照就重建未签名 XML；
尚无生成器的版本会提供构建任务说明。使用自己选择的 AI Agent 读取 `ci/BUILD_PROMPT.md` 完成构建。
最终 Apple 签名在有登录环境的 Mac 上完成，不向 GitHub 上传 Apple 账户凭据。

## 云端签名失败时

如果 GitHub runner 无法使用 iCloud 签名，最后一步需要在已登录 Apple Account 的 Mac 上执行（**不需要 Apple 开发者账号**）：

    shortcuts sign --mode anyone --input ShanNian.xml --output ShanNian.shortcut

不要把 Apple ID、iCloud 密码、Apple 登录 Cookie 或私人 API Key 上传到 GitHub。尽管本仓库为 private，Actions Artifact 也不应包含任何个人备忘录、日历事件或待办数据。

## 密钥和隐私

- **Runtime API Key**：当前测试版每次在 iPhone 运行时输入，供语音意图解析使用。绝不可提交到此仓库；不要写成快捷指令固定文本或默认值，否则可能随快捷指令同步、分享。
- 当前测试版向自选模型服务商发送原话、澄清内容、设备时间和时区；查询到的 Apple Notes/Calendar/Reminders 记录仅在本机展示。恢复笔记和系统记录按 Apple App/iCloud 设置正常同步。
- 建议先测试写入虚构数据，并在保存前确认目标操作。

仓库目前未设置开源许可证。公开仓库与授予他人使用、修改和再分发权限是不同的事；正式开源前应由所有者选择许可证，并保留相关第三方署名。当前测试版依赖的构建参考工具为 [Shortcuts Playground](https://github.com/viticci/shortcuts-playground-plugin)，仓库没有打包其插件代码或任何 Apple 系统二进制文件。

## 参考资料

- 需求：[spec/闪念_Shortcuts_构建规格.md](spec/闪念_Shortcuts_构建规格.md)
- 构建提示：[ci/BUILD_PROMPT.md](ci/BUILD_PROMPT.md)
- [Shortcuts Playground](https://github.com/viticci/shortcuts-playground-plugin)

