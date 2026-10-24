# 本地构建「言归」

只想试用时，可直接下载仓库中的[已签名测试版](preview/YanGui.shortcut)，无需安装 AI Agent 或准备 Mac。当前 Notes 兼容性等限制仍然存在，详见 [FEATURES.md](preview/FEATURES.md)。

本指南提供两条本地路线：使用现有 Python 生成器重建快照，或让你选择的 AI 编码 Agent 继续完善。选择具备文件和终端能力的 AI Agent 即可；最终 Apple 签名需要 Mac。

## 准备环境

1. 准备 Python 3.10+。重新签名需在有 Apple「快捷指令」和适当 Apple Account 登录环境的 Mac 上完成。
2. 在终端检查：

   ```sh
   python3 --version
   shortcuts --help
   ```

3. 克隆仓库并进入目录；私有仓库需要先取得 GitHub 访问权限：

   ```sh
   git clone https://github.com/J1mmyHuang/YanGui-Shortcut.git
   cd YanGui-Shortcut
   ```

构建现有快照和离线测试不调用模型，不需要 API Key。使用 AI Agent 改造时，其模型登录、订阅或 API 费用由你选择的工具决定。iPhone 上运行的 BYOK 模型服务在添加快捷指令时填写 API 协议、Base URL、API Key、模型 ID（可留空，运行时选择）。

## 重建现有测试版（无需 AI Agent）

在仓库根目录执行：

```sh
python3 preview/build_yangui.py
python3 -m unittest discover -s preview -p 'test_*.py' -v
python3 ci/validate_plist.py preview/YanGui.xml
plutil -lint preview/YanGui.xml
```

这会更新 `preview/YanGui.xml`，保留当前实现及其已知限制。89 项测试是离线模拟，不是 Apple 的实际动作引擎；Mac 引擎实测用 `python3 preview/build_yangui.py --test` 生成的测试版（加 `--real-notes` 时备忘录真实写入），步骤见 `handoff.md`，结果见 `preview/validation-mac-engine.log`。完整 Shortcuts Playground 检查仍有 Notes 错误，见 `preview/validation-ios27.log`；重建不会自动修复这些问题，也不会更新旧签名。

如需为重建后的 XML 生成新的**测试版**签名，在 Mac 上执行：

```sh
mkdir -p dist
cp preview/YanGui.xml dist/YanGui.xml
cp dist/YanGui.xml dist/YanGui-unsigned-backup.xml
cp dist/YanGui.xml dist/YanGui-sign-input.shortcut
shortcuts sign --mode anyone --input dist/YanGui-sign-input.shortcut --output dist/YanGui.shortcut
test -s dist/YanGui.shortcut
```

输入文件使用 `.shortcut` 扩展名和与快捷指令同名的文件名；`.xml` 扩展名或无关文件名会得到“isn’t in the correct format”。带沙箱的 Agent 需在沙箱外执行 `shortcuts sign`，沙箱内该进程会以 133 退出。签名失败时保留 XML 和错误日志；有 Shortcuts Playground 时可使用其 `scripts/sign_shortcut.sh`，该脚本会归档源文件并处理部分 plist 格式重试。签名成功不表示 Notes 兼容性已解决。

## 使用任意具备工具能力的 AI Agent

选择能读取仓库、编辑文件并执行终端命令的 AI 编码 Agent，在仓库目录打开它，使用该工具已有的模型配置。

Agent 需要 Shortcuts Playground 的动作格式、示例和验证脚本。可使用该 Agent 支持的插件安装方式；也可直接获取公开参考源：

```sh
git clone https://github.com/viticci/shortcuts-playground-plugin.git .ci-tools/shortcuts-playground
```

在参考仓库中查找 Shortcuts Playground 的 `SKILL.md`，其同目录下包含动作资料、示例和 `scripts/`。这里获取的是上游当前版本，未承诺与已发布快照使用的1.2.1完全一致。请记录实际使用的版本，并按其文档执行验证。

给 Agent 发送：

```text
读取并执行 ci/BUILD_LOCAL_PROMPT.md，依据 spec/言归_Shortcuts_构建规格.md
以及 Shortcuts Playground 的资料，构建、验证并签名「言归」。
优先复用 preview/ 中的生成器和测试，核对已有未解决问题。
请报告实际运行的检查、每项能力的状态和所有未验证内容。
不要把真实 API Key 写入仓库或快捷指令，不要读取个人应用数据库来猜动作格式。
```

本地通用任务见 [ci/BUILD_LOCAL_PROMPT.md](ci/BUILD_LOCAL_PROMPT.md)。Agent 应按其宿主工具的方式读取动作资料并执行脚本；签名命令需在 Mac 执行。

读取已签名文件（例如用户导出的样本）：

```sh
python3 ci/read_signed_shortcut.py 某个.shortcut 输出.xml
```

仅限 macOS，依赖系统的 `aea`、`aa`、`openssl`。

## 在 Mac 上用真实引擎测试

`python3 preview/build_yangui.py --test` 生成测试版 `dist/YanGui-Test.xml`：原话来自「快捷指令输入」，结果作为输出返回，备忘录动作只生成文本，其余动作与正式版相同。按上面的步骤签名成 `dist/YanGui-Test.shortcut`，在 Mac 上双击导入并填写 API 协议、Base URL、API Key、模型 ID（不要留空），然后：

```sh
python3 ci/run_mac_test.py YanGui-Test "测试：今天下午两点有个会"
```

该命令需在沙箱外运行，会真实写入日历和提醒事项，测试原话建议带「测试」二字。首次运行时系统会弹出日历、提醒事项权限，需要在 Mac 上点允许。

## 交付检查

新的构建输出放在 `dist/`：

- `YanGui.xml`：可审阅的 XML/plist。
- `YanGui.shortcut`：仅当 Apple 签名成功且文件非空时存在。
- `FEATURES.md`：六项能力的实现、验证状态、限制与实机测试清单。

公开下载版快照位于 `preview/`。更新它时应同步源 XML、生成器、签名文件、相关日志及 `build-manifest.json` 摘要，并保留顶部免费开源和官方仓库的注释。项目许可证为 [AGPL-3.0-or-later](LICENSE)。

`dist/` 被 Git 忽略，但仍不应向其中写入待分享的真实密钥或个人应用记录。签名时 Apple 会收到快捷指令副本；详见 [SIGNING.md](preview/SIGNING.md)。

## 导入和测试

通过隔空投送或 iCloud Drive 在 iPhone 打开已签名 `.shortcut`，依次填写 API 协议、Base URL、API Key、模型 ID，审查动作后导入。先在快捷指令 App 里运行，测试 Notes、Calendar、Reminders 的创建和查询，核对权限与日期。确认后在「设置 → 操作按钮 → 快捷指令 → 言归」绑定，按一下说话，说完点按完成。

遇到未知动作或导入错误时，将具体错误反馈给维护者或你的 Agent。静态结构检查、离线测试和签名都不能代替 iPhone 实测。
