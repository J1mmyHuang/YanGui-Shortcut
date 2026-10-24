# 测试版签名与隐私

`YanGui.shortcut` 由开发者本机 Mac 上的 Apple `shortcuts sign` 生成，使用 Shortcuts Playground 1.2.1 的归档/签名脚本，模式为 `anyone`。它是用于分发的真实签名文件，不是把 XML 改名得到的文件。文件大小、SHA-256 和源 XML 摘要见 `build-manifest.json`。

## 本机发起、Apple 验证

Apple 官方文档说明：签名时 Apple 会收到快捷指令副本以进行验证；`anyone` 允许任何人导入。`people-who-know-me` 则只允许联系人导入，并把签名者联系人信息包含在文件中。本次使用 `anyone`，不是联系人限制模式。

来源：[Apple — 从命令行运行及签名快捷指令](https://support.apple.com/en-au/guide/shortcuts-mac/apd455c82f02/mac)。

这次操作没有读取或传递 1Password Git SSH 私钥、GitHub Token 或 Passkey。快捷指令签名与 Git 登录/提交签名是两套独立机制。本项目没有导出 Apple Account 凭据或签名私钥。

## 文件检查

- XML 不含真实 API Key。Base URL、API Key、模型 ID 三个文本动作为空，API 协议默认 openai，均在用户添加快捷指令时通过导入问题填写。
- 源 XML 不含个人笔记、日历事件、提醒或联系人。
- 签名文件为 `AEA1` 封装；其公开认证元数据只含 `SigningCertificateChain`。
- 已检查该证书链：没有邮箱地址，签名者证书主题使用不透明标识，颁发者是 Apple System Integration CA 4。证书本身是公开验证材料；这不等于保证完全匿名或无法关联签名者。
- 签名不会把作者 Mac 的 Notes/Calendar/Reminders 权限转授给接收者；导入后仍由接收者在自己的设备授权。

签名表示可验证的分发封装，**不表示 Apple 已确认业务逻辑、安全性或所有动作兼容性**。本测试版仍有 Notes 插件校验失败，且未进行 iPhone 测试，详见 `FEATURES.md`。

## 修改后的重新签名

修改 XML 后，原来的签名文件不会自动更新。先重新检查，再在已配置 Apple Account 的 Mac 上重新签名，例如：

```sh
cp preview/YanGui.xml dist/YanGui-sign-input.shortcut
shortcuts sign --mode anyone --input dist/YanGui-sign-input.shortcut --output dist/YanGui.shortcut
```

输入文件需要 `.shortcut` 扩展名和同名文件名，并在沙箱外执行。重新核对文件非空、更新摘要并测试 iPhone 导入。含真实 Key 的快捷指令先清空配置，再上传至仓库或提交给 Apple 的签名服务。
