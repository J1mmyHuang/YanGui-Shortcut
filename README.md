# 言归 · YanGui Shortcut

一个基于 iPhone Action Button 的中文语音记事助手：按一下，直接说话，说完停一下就自动结束。AI 自动把你说的话分成多个事项，并归入 Apple 原生的**备忘录、提醒事项和日历**。真正的创建和查询由设备上的快捷指令动作完成。

**官方版本免费提供。** 官方仓库：[J1mmyHuang/YanGui-Shortcut](https://github.com/J1mmyHuang/YanGui-Shortcut)。

> **当前为实验性测试版。** 已生成 Apple 签名文件，89 项离线测试通过；在 Mac 的 Shortcuts 引擎上实测了备忘录与可勾选的清单（真实写入备忘录 App）、备忘录查询、日历（有时间、全天）、提醒（带时刻、仅日期、模糊时间），以及经真实 API 把一句话里的三件事分别写入日历、提醒事项和备忘录，不再出现「请为此操作中的每个参数选取值」（[实测记录](preview/validation-mac-engine.log)）。作者已在 iPhone 上跑通整条流程（操作按钮听写、一句话多件事分别写入三个 App、购物清单）；Notes 动作在插件校验中仍有已知误报。请先阅读[功能与限制](preview/FEATURES.md)。

## 选择使用方式

| 你想做什么 | 入口 | 需要什么 |
| --- | --- | --- |
| 下载后直接试用 | [Releases 中的已签名 YanGui.shortcut](https://github.com/J1mmyHuang/YanGui-Shortcut/releases/latest) | iPhone，以及自己选择的模型服务的 API 协议、Base URL、API Key、模型 ID；无需 AI Agent 或重新构建 |
| 审阅或重建现有测试版 | [本地构建指南](LOCAL_BUILD.md) | Python 3.10+；重新签名需要 Mac |
| 让 AI Agent 修改或继续完善 | [通用构建任务](ci/BUILD_LOCAL_PROMPT.md) | 能读写仓库、运行终端的代码 Agent；动作资料与验证工具；签名需要 Mac |
| 在 GitHub 上检查和重建 | [Actions 构建页面](https://github.com/J1mmyHuang/YanGui-Shortcut/actions/workflows/build-shortcut.yml) | 使用已有生成器输出源 XML，无需模型构建密钥；签名在 Mac 完成 |

## 免构建试用

从 [GitHub Releases](https://github.com/J1mmyHuang/YanGui-Shortcut/releases/latest) 下载 `YanGui.shortcut`（与仓库中的 [preview/YanGui.shortcut](preview/YanGui.shortcut) 相同），通过隔空投送或 iCloud Drive 在 iPhone 打开。私有仓库的下载需要相应访问权限。

1. 打开文件后，快捷指令 App 依次询问 **API 协议、Base URL、API Key、模型 ID**。协议填 `openai`（OpenAI compatible）或 `anthropic`（Anthropic compatible）；模型 ID 可以留空，运行时从服务的 `/models` 列表里选。这四项也是快捷指令最前面的四个文本动作，之后点开即可修改。
2. 审查动作后添加，先在快捷指令 App 里运行一次，按系统提示授予麦克风、备忘录、日历、提醒事项等权限。
3. 到「设置 → 操作按钮 → 快捷指令」选这条快捷指令绑定。导入后的名称取自文件名，显示为「YanGui」，可在快捷指令 App 里改名为「言归」。
4. 按一下操作按钮，直接说话；说完停顿一下，听写自动结束。通知会汇总每一项记到了哪里。

这个入口省去本地构建与签名，仍需自己的 API 配置和设备授权。当前是实验性测试版，已知限制见 [FEATURES.md](preview/FEATURES.md)。

下载版顶部含一条「注释」，标明软件免费开源和官方仓库。它供打开编辑器时查看，运行时不弹窗，也不发送给模型。

## 功能范围

| 原生 App | 创建 | 查询 |
| --- | --- | --- |
| Apple Notes | `note.create` | `note.search` |
| Apple Calendar | `calendar.create` | `calendar.search` |
| Apple Reminders | `reminder.create` | `reminder.search` |

**智能分类**：AI 判断每个事项的去向。有明确日期或时间的会议、活动进日历（「提醒我下午3点有会议」也进日历，只说钟点时日期按今天）；要去做的单件待办进提醒事项；想法、信息和拿不准的内容进备忘录；要买或要带的东西有两样及以上时，写成备忘录里可以点按勾选的待办项清单。**自动分段**：一次听写里的多件事各自归类，按顺序全部写入。日期说不准时不猜，改记为备忘录并保留原话。

查询最多10条，无结果时直接说明。没有删除、修改现有记录或标记完成的功能。详细实现状态和 iPhone 测试清单见 [FEATURES.md](preview/FEATURES.md)。

**接入方式**：API Key，协议可选 OpenAI compatible 或 Anthropic compatible，请求格式见 [FEATURES.md](preview/FEATURES.md#接入方式api-key两种协议)。Anthropic 要求第三方产品使用 API Key，OpenAI 的「Sign in with ChatGPT」需要本地回环监听，快捷指令无法提供，所以 OAuth 登录未接入。API 出错时，弹窗会显示服务返回的错误原文。

## 使用你习惯的 AI Agent

选择能够读取文件、编辑代码、执行 Python/终端命令并使用 Shortcuts 动作资料的 AI 编码 Agent，即可参与构建和维护。具体完成质量取决于模型能力、工具权限和验证结果；本机签名需要终端执行能力。

将仓库交给 Agent，并发送：

```text
读取并执行 ci/BUILD_LOCAL_PROMPT.md，结合 spec/言归_Shortcuts_构建规格.md
和 Shortcuts Playground 的动作资料与验证工具，构建、验证并签名「言归」。
优先复用 preview/ 中已有实现，保留已知限制的记录。
不要写入真实 API Key，不要宣称已经通过未执行的 iPhone 测试。
```

[本地构建指南](LOCAL_BUILD.md) 提供无需 Agent 的重建步骤，以及通用 Agent 的准备方式。Shortcuts Playground 可通过适合该 Agent 的插件方式使用，也可读取其公开参考文件并直接运行 Python/签名脚本。最终签名依赖 **macOS 的 Apple `shortcuts` 工具**，与选择哪家 Agent 无关。

## 自动检查与重建

普通 push 会运行源文件检查和已有的离线行为测试，不调用模型，也不需要模型构建密钥。

可在 [Actions 构建页面](https://github.com/J1mmyHuang/YanGui-Shortcut/actions/workflows/build-shortcut.yml) 手动选择 **Run workflow**，使用仓库中已有的 Python 生成器重建 XML，并下载 `YanGui-build-source` Artifact。这个产物是未签名源文件，最终签名需在自己的 Mac 上完成，步骤见[本地构建指南](LOCAL_BUILD.md)。

需要改变功能时，将[通用构建任务](ci/BUILD_LOCAL_PROMPT.md)交给自己选择的 AI Agent。模型服务的登录和使用方式由该 Agent 的配置决定；仓库的自动流程负责检查和重建现有实现。

## 密钥、隐私与签名

- **API Key**：在添加快捷指令时填写，保存在你自己的这条快捷指令里，可能随 iCloud 同步。仓库里的文件三项配置为空；分享、导出或上传自己的快捷指令之前先清空这三项。
- **发送给模型的数据**：原话、设备当地时间和时区；认证 Key 发送到同一自选 API 提供方。查得的本机笔记、日历和提醒记录仅在本机展示。
- **原话保护**：API 返回错误或内容不合格式时，原话自动存成备忘录「言归原话（未处理）」。配置里的「原话备份」改为 `是` 后，每次联网前先存一份，网络直接中断时也能找回。
- **Apple 签名**：本机发起 `anyone` 签名，Apple 会收到快捷指令副本验证。公开证书中有不透明标识，不应将签名视为匿名发布或功能安全认证。详见[签名说明](preview/SIGNING.md)。
- **构建产物**：源码、签名快照及摘要在 `preview/`；面向使用者的发布文件在 GitHub Releases；临时输出放在被 Git 忽略的 `dist/`。不要提交真实密钥、Apple 登录凭据或个人应用数据。

## 相关文件

- [功能规格](spec/言归_Shortcuts_构建规格.md)
- [本地构建指南](LOCAL_BUILD.md)与[通用 Agent 构建任务](ci/BUILD_LOCAL_PROMPT.md)
- [源 XML](preview/YanGui.xml)、[生成器](preview/build_yangui.py)、[构建摘要](preview/build-manifest.json)、[Mac 引擎实测记录](preview/validation-mac-engine.log)
- [Shortcuts Playground](https://github.com/viticci/shortcuts-playground-plugin)

## 许可证

Copyright (C) 2026 J1mmyHuang.

本项目采用 **GNU Affero General Public License 第3版或任何后续版本**，SPDX 标识为 **`AGPL-3.0-or-later`**。完整条款见 [LICENSE](LICENSE)。

官方版本免费提供；AGPL 仍允许遵守许可证的商业使用与收费分发。快捷指令中的提示用于标明官方来源，不增加禁止商业使用的许可条件。源码提供、修改和分发义务以许可证为准。第三方工具和资料保留各自的许可证与署名。
