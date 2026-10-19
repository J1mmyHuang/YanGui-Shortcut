# Mac 本地构建「闪念」

选择能够读写仓库并运行终端的 AI 编码 Agent，使用自己的模型配置。
准备 Python 3.10+、Shortcuts Playground 动作资料，以及用于最终签名的 Mac。

## 构建任务

让 Agent 阅读 `ci/BUILD_LOCAL_PROMPT.md`、`spec/闪念_Shortcuts_构建规格.md`，
以及 Shortcuts Playground 的 `SKILL.md`、动作格式、示例和验证脚本，
生成并验证 `dist/ShanNian.xml`，记录六项能力的真实状态及未解决问题。
Shortcuts Playground 可通过 Agent 的插件机制接入，也可获取公开参考源直接使用。

## 签名与导入

在有 Apple 快捷指令环境的 Mac 上归档源 XML，再执行：

```sh
shortcuts sign --mode anyone --input dist/ShanNian.xml --output dist/ShanNian.shortcut
```

确认文件非空，再通过隔空投送或 iCloud Drive 在 iPhone 导入和测试。
签名和静态检查不代表六项动作已通过真机验证。运行时 BYOK 需要使用者单独配置。
不要把真实密钥、Apple 登录凭据或个人应用记录写入仓库或待分享的快捷指令。
