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

### 使用方法

#### 1. 搜索资源

- **方式一（推荐）**: 使用命令 `/nullbr 关键词`
  ```bash
  /nullbr 流浪地球
  ```
- **方式二**: 使用 `#` 前缀（适用于不支持斜杠命令的平台）
  ```bash
  #流浪地球
  ```

#### 2. 选择资源/交互

- **点击按钮**: 在 Telegram/Slack 等支持按钮的平台直接点击
- **使用指令**:
  ```bash
  #1                     → 选择第1个结果
  #1.115                 → 获取第1个结果的115资源
  #1.magnet              → 获取第1个结果的磁力链接
  ```

#### 3. 其他命令

- `/nullbr_offline` - 查询离线任务状态
- `/nullbr_help` - 查看帮助信息

## 📝 更新日志

### Pro版 v2.0.0 ✨
- **全平台交互优化**: 
  - 支持 `#关键词` 直接搜索
  - 修复 115 转存功能
  - 帮助命令根据平台自适应显示
- **命令增强**: 新增 `/nullbr_offline` 和 `/nullbr_help`

### Pro版 v1.8.0
- 重新设计交互：使用 `/nullbr` 命令启动搜索

### Pro版 v1.7.0
- 新增按钮交互消息系统

### Pro版 v1.6.0
- 精简配置：CD2只保留API Token，115转存只用CID

### Pro版 v1.5.0
- 新增 p115client 支持，通过 Cookie 直接调用 115 API
- 解决 CloudDrive2 的 115open 不支持分享转存的问题

## 📄 许可证

本项目基于GPL-3.0许可证开源。
