# 闪念 · ShanNian Shortcut

一个基于 iPhone Action Button 的中文语音助手，使用 Apple 原生的**备忘录、日历和提醒事项**。AI 理解自然语言，真正的创建和查询由设备上的快捷指令动作完成。

**官方版本免费提供，采用 [AGPL-3.0-or-later](LICENSE) 许可证。** 官方仓库：[J1mmyHuang/ShanNian-Shortcut](https://github.com/J1mmyHuang/ShanNian-Shortcut)。

> **当前为实验性测试版。** 已生成 Apple 签名文件，26项离线测试通过；尚未完成 iPhone 实测，Notes 动作仍未通过插件校验，可能阻止流程运行。仅日期、没有具体时刻的提醒尚未实现。请先阅读[功能与限制](preview/FEATURES.md)。

## 选择使用方式

| 你想做什么 | 入口 | 需要什么 |
| --- | --- | --- |
| 下载后直接试用 | [下载已签名的 ShanNian.shortcut](preview/ShanNian.shortcut?raw=true) | iPhone，以及自己选择的模型服务的 API 配置；无需 AI Agent 或重新构建 |
| 审阅或重建现有测试版 | [本地构建指南](LOCAL_BUILD.md) | Python 3.10+；重新签名需要 Mac |
| 让 AI Agent 修改或继续完善 | [通用构建任务](ci/BUILD_LOCAL_PROMPT.md) | 能读写仓库、运行终端的代码 Agent；动作资料与验证工具；签名需要 Mac |
| 在 GitHub 上自动生成 | [Actions 构建页面](https://github.com/J1mmyHuang/ShanNian-Shortcut/actions/workflows/build-shortcut.yml) | 当前附带的流程使用 AI Agent Action，需要单独的构建用 API Key |

## 免构建试用

1. 下载[已签名测试版](preview/ShanNian.shortcut?raw=true)，通过隔空投送或 iCloud Drive 在 iPhone 打开，审查动作后添加到「快捷指令」。私有仓库的下载需要相应访问权限。
2. 首次先从快捷指令 App 运行并选择文字输入，检查恢复备忘录动作是否可用，再逐项测试创建和查询。
3. 每次运行填写自己的 **API Base URL、Model、API Key**。支持 OpenAI-compatible Chat Completions API；使用提供方支持的模型与密钥。构建阶段的 AI 登录不会自动提供运行时 API 额度。
4. 按系统提示授予所需权限。验证后到「设置 → 操作按钮 → 快捷指令 → 闪念」绑定。

这个入口省去本地构建与签名，但仍需 API 配置、设备授权和实测；当前不是已经验证可靠的开箱即用正式版。

下载版顶部含一条「注释」，标明软件免费开源和官方仓库。它供打开编辑器时查看，运行时不弹窗，也不发送给模型。

## 功能范围

| 原生 App | 创建 | 查询 |
| --- | --- | --- |
| Apple Notes | `note.create` | `note.search` |
| Apple Calendar | `calendar.create` | `calendar.search` |
| Apple Reminders | `reminder.create` | `reminder.search` |

支持中文听写和文字输入。模型只能选择这六项操作或请求澄清；缺少时间、范围等信息时应先提问。当前版本一次处理一个操作，复合请求会明确要求拆分。查询最多10条，无结果时直接说明。没有删除、修改现有记录或标记完成的功能。

详细实现状态、仅日期提醒限制和 iPhone 测试清单见 [FEATURES.md](preview/FEATURES.md)。

## 使用你习惯的 AI Agent

能够读取文件、编辑代码、执行 Python/终端命令并使用 Shortcuts 动作资料的 AI 编码 Agent，都可以参与构建和维护；具体完成质量取决于模型能力、工具权限和验证结果。只有聊天能力的工具无法独立完成本机签名。

将仓库交给 Agent，并发送：

```text
读取并执行 ci/BUILD_LOCAL_PROMPT.md，结合 spec/闪念_Shortcuts_构建规格.md
和 Shortcuts Playground 的动作资料与验证工具，构建、验证并签名「闪念」。
优先复用 preview/ 中已有实现，保留已知限制的记录。
不要写入真实 API Key，不要宣称已经通过未执行的 iPhone 测试。
```

[本地构建指南](LOCAL_BUILD.md) 提供无需 Agent 的重建步骤，以及通用 Agent 的准备方式。Shortcuts Playground 可通过适合该 Agent 的插件方式使用，也可读取其公开参考文件并直接运行 Python/签名脚本。最终签名依赖 **macOS 的 Apple `shortcuts` 工具**，与选择哪家 Agent 无关。

## 自动检查与构建

GitHub Actions 负责检查仓库内容。手动触发时，有生成器快照就重建未签名 XML；
尚无生成器的版本会提供构建任务说明。使用自己选择的 AI Agent 读取 `ci/BUILD_PROMPT.md` 完成构建。
最终 Apple 签名在有登录环境的 Mac 上完成，不向 GitHub 上传 Apple 账户凭据。

## 密钥、隐私与签名

- **运行时 API Key**：在 iPhone 每次运行时输入，输入可见，未预填真实密钥。不要将 Key 改成快捷指令固定文本或默认值，否则可能随文件同步和分享。
- **发送给模型的数据**：原话、澄清内容、设备当地时间和时区；认证 Key 发送到同一自选 API 提供方。当前测试版查得的本机笔记、日历和提醒记录仅在本机展示。
- **原话恢复**：当前版本联网前先显示原话，经明确同意后保存一条恢复备忘录，以应对后续网络或权限动作直接中断。恢复笔记按备忘录/iCloud 设置同步；取消则结束。Notes 动作失败时可能无法保存。
- **Apple 签名**：本机发起 `anyone` 签名，Apple 会收到快捷指令副本验证。公开证书中有不透明标识，不应将签名视为匿名发布或功能安全认证。详见[签名说明](preview/SIGNING.md)。
- **构建产物**：源码、签名文件及摘要在 `preview/`；临时输出放在被 Git 忽略的 `dist/`。不要提交真实密钥、Apple 登录凭据或个人应用数据。

## 许可证

Copyright (C) 2026 J1mmyHuang.

本项目采用 **GNU Affero General Public License 第3版或任何后续版本**，SPDX 标识为 **`AGPL-3.0-or-later`**。完整条款见 [LICENSE](LICENSE)。

官方版本免费提供；AGPL 仍允许遵守许可证的商业使用与收费分发。快捷指令中的提示用于标明官方来源，不增加禁止商业使用的许可条件。源码提供、修改和分发义务以许可证为准。第三方工具和资料保留各自的许可证与署名。

## 相关文件

- [功能规格](spec/闪念_Shortcuts_构建规格.md)
- [本地构建指南](LOCAL_BUILD.md)与[通用 Agent 构建任务](ci/BUILD_LOCAL_PROMPT.md)
- [源 XML](preview/ShanNian.xml)、[生成器](preview/build_shannian.py)、[构建摘要](preview/build-manifest.json)
- [Shortcuts Playground](https://github.com/viticci/shortcuts-playground-plugin)
