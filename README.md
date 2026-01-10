# MoviePilot 第三方插件库

## 📦 插件列表

### Nullbr资源搜索
支持Nullbr API搜索影视资源，支持115网盘、磁力、ed2k、m3u8等多种资源类型。

### Nullbr资源搜索Pro ✨
基于Nullbr资源搜索升级版，集成CloudDrive2实现：
- ✅ 115分享链接转存
- ✅ 磁力链接离线下载
- ✅ ED2K链接离线下载

## 🛠️ 安装方法

复制仓库地址到MoviePilot插件源配置：

```
https://github.com/Li-Qifeng/MoviePilot-Plugins-Third
```

## 📖 Nullbr资源搜索Pro 使用指南

### 功能特性

| 功能 | Nullbr资源搜索 | Pro版 |
|------|:-------------:|:-----:|
| 115转存(p115client) | ❌ | ✅ |
| 磁力/ED2K离线(CD2) | ❌ | ✅ |
| 按钮交互 | ❌ | ✅ |

### 配置说明

#### Nullbr API配置（必填）
- **APP_ID**: Nullbr API的应用ID
- **API_KEY**: Nullbr API的密钥

#### 115 转存配置（推荐）
使用 p115client 直接调用 115 API，支持分享链接转存：

- **启用115转存**: 开启后支持115分享链接转存
- **转存目录CID**: 在浏览器 URL 中获取，如 `https://115.com/?cid=123456` 中的 `123456`
- **115 Cookie**: 必须包含 `UID`, `CID`, `SEID`, `KID`
  - 获取方式: 浏览器登录 115.com → F12 → Application → Cookies

#### CloudDrive2配置（可选）
仅用于磁力/ED2K离线任务：

- **CD2地址**: CloudDrive2服务器地址，如 `http://localhost:19798`
- **API Token**: 在CloudDrive2设置中生成
- **离线任务路径**: 默认 `/115/Offline`

### 使用方法

> ⚠️ **重要**: 为避免与 MoviePilot 原生搜索冲突，本插件使用 **问号结尾** 触发搜索

#### 文本交互（所有渠道）

```
搜索影片？        → 搜索资源（必须以？结尾）
1               → 选择第1个结果
1.115           → 获取第1个结果的115资源
```

获取资源后发送编号即可转存/离线：
```
1               → 转存/离线第1个资源
```

#### 按钮交互（Telegram/Slack）

搜索结果会显示交互按钮，**点击按钮即可选择**，无需输入数字：

- `📥 1. 影片名` - 点击选择第1个结果
- `📥 2. 影片名` - 点击选择第2个结果

> 💡 按钮交互仅支持 Telegram、Slack 等支持按钮回调的通道

## 📝 更新日志

### Pro版 v1.7.0 ✨
- **新增按钮交互消息系统**，支持 Telegram/Slack 按钮回调
- 搜索结果显示交互按钮，点击即可选择
- 保留文本输入方式作为兼容方案

### Pro版 v1.6.0
- 精简配置：CD2只保留API Token，115转存只用CID

### Pro版 v1.5.0
- 新增 p115client 支持，通过 Cookie 直接调用 115 API
- 解决 CloudDrive2 的 115open 不支持分享转存的问题

## 📄 许可证

本项目基于GPL-3.0许可证开源。
