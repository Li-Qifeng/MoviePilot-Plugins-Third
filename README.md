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
| 115转存 | ✅ (CMS) | ✅ (CloudDrive2) |
| 磁力离线 | ❌ | ✅ |
| ED2K离线 | ❌ | ✅ |
| API Token认证 | ❌ | ✅ |

### 配置说明

#### Nullbr API配置（必填）
- **APP_ID**: Nullbr API的应用ID
- **API_KEY**: Nullbr API的密钥

#### CloudDrive2配置（可选）
支持两种认证方式：

**方式1: API Token（推荐）**
- **CD2地址**: CloudDrive2服务器地址，如 `http://localhost:19798`
- **API Token**: 在CloudDrive2设置中生成，永久有效

**方式2: 用户名密码**
- **CD2地址**: CloudDrive2服务器地址
- **用户名/密码**: CloudDrive2登录凭证

> 💡 API Token模式推荐：无需续期，配置更简单

#### 路径配置
- **115转存路径**: 默认 `/115/Downloads`
- **离线任务路径**: 默认 `/115/Offline`

### 使用方法

**所有交互必须以问号结尾！**

```
搜索影片？        → 搜索资源
1？              → 选择第1个结果
1.115？          → 获取第1个结果的115资源
```

获取资源后发送编号即可转存/离线：
```
1                → 转存/离线第1个资源
```

## 📝 更新日志

### Pro版 v1.4.1
- 修复Protobuf版本兼容问题，使用protobuf 5.x重新生成gRPC代码

### Pro版 v1.4.0
- 使用原生gRPC协议重写客户端，完全兼容CloudDrive2官方API
- 新增 grpcio 依赖

### Pro版 v1.3.0
- 修复gRPC-Web协议格式，使用正确的端点路径格式 `/服务名/方法名`
- 更新本地API文档

### Pro版 v1.2.0
- 修复API 405错误，添加端点自动回退机制兼容不同版本CloudDrive2

### Pro版 v1.1.0
- 优化CloudDrive2认证，支持API Token（推荐）和用户名密码双重认证方式

### Pro版 v1.0.0
- 初始版本
- 新增CloudDrive2支持（115转存/磁力离线/ED2K离线）

## 📄 许可证

本项目基于GPL-3.0许可证开源。
