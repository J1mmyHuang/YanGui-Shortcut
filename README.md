# 闪念 · ShanNian Shortcut

一个基于 iPhone Action Button 的轻量语音助手。只访问三款 Apple 原生 App：**备忘录、日历、提醒事项**。AI 只负责理解自然语言，实际读写由 Shortcuts 的本机动作执行。

> **当前状态：CI 构建工程已提交，完整 iPhone 快捷指令尚未生成或经过实机验证。** GitHub runner 上的苹果公开签名可能因无 iCloud 会话失败。

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

- **Runtime API Key**：最终在个人 iPhone 快捷指令中配置，供实际语音意图解析使用。绝不可提交到此仓库。
- 查询 Apple Notes/Calendar/Reminders 时，必要的匹配内容会发送到你选择的模型服务商。系统原始数据仍保留在原生 App 和 iCloud。
- 建议先测试写入虚构数据，并在保存前确认目标操作。

## 参考资料

- 需求：[spec/闪念_Shortcuts_构建规格.md](spec/闪念_Shortcuts_构建规格.md)
- 构建提示：[ci/BUILD_PROMPT.md](ci/BUILD_PROMPT.md)
- [Shortcuts Playground](https://github.com/viticci/shortcuts-playground-plugin)

