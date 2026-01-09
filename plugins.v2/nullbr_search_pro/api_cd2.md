# CloudDrive2 gRPC-Web API Reference

基于官方 gRPC API 文档，使用 gRPC-Web 协议通过 HTTP/JSON 调用。

## 基本说明

- **Base URL**: `http://localhost:19798` (或自定义端口)
- **协议**: gRPC-Web (HTTP/JSON)
- **端点格式**: `/{服务名}/{方法名}`
- **请求方法**: POST
- **Content-Type**: `application/json`
- **认证**: `Authorization: Bearer <token>`

## 认证

### 获取 Token (登录)
- **服务**: `UserSrv`
- **方法**: `GetToken`
- **端点**: `/UserSrv/GetToken`

```json
// 请求
{
  "userName": "admin",
  "password": "password",
  "totpCode": ""
}

// 响应
{
  "token": "eyJh...",
  "expiration": "..."
}
```

---

## 共享链接

### AddSharedLink
将共享链接添加到文件夹。

- **服务**: `CloudDriveFileSrv`
- **方法**: `AddSharedLink`
- **端点**: `/CloudDriveFileSrv/AddSharedLink`

```protobuf
message AddSharedLinkRequest {
  string sharedLinkUrl = 1;
  optional string sharedPassword = 2;
  string toFolder = 3;
}
// 响应: google.protobuf.Empty
```

```json
// 请求示例
{
  "sharedLinkUrl": "https://115.com/s/xxx",
  "sharedPassword": "",
  "toFolder": "/115/Downloads"
}

// 响应: {} (空对象表示成功)
```

---

## 离线下载管理

### AddOfflineFiles
添加离线下载任务(磁力链接、ED2K等)。

- **服务**: `CloudDriveFileSrv`
- **方法**: `AddOfflineFiles`
- **端点**: `/CloudDriveFileSrv/AddOfflineFiles`

```protobuf
message AddOfflineFileRequest {
  string urls = 1;
  string toFolder = 2;
  uint32 checkFolderAfterSecs = 3;
}
// 响应: FileOperationResult
```

```json
// 请求示例
{
  "urls": "magnet:?xt=urn:btih:...",
  "toFolder": "/115/Offline",
  "checkFolderAfterSecs": 0
}
```

### ListOfflineFilesByPath
列出特定路径中的离线文件。

- **服务**: `CloudDriveFileSrv`
- **方法**: `ListOfflineFilesByPath`
- **端点**: `/CloudDriveFileSrv/ListOfflineFilesByPath`

```json
// 请求
{
  "path": "/115/Offline",
  "forceRefresh": true
}

// 响应
{
  "offlineFiles": [...],
  "status": {...}
}
```

### ListAllOfflineFiles
分页列出所有离线文件。

- **服务**: `CloudDriveFileSrv`
- **方法**: `ListAllOfflineFiles`
- **端点**: `/CloudDriveFileSrv/ListAllOfflineFiles`

```protobuf
message OfflineFileListAllRequest {
  string cloudName = 1;
  string cloudAccountId = 2;
  uint32 page = 3;
  optional string path = 4;
}
```

### RemoveOfflineFiles
删除离线下载任务。

- **服务**: `CloudDriveFileSrv`
- **方法**: `RemoveOfflineFiles`
- **端点**: `/CloudDriveFileSrv/RemoveOfflineFiles`

```protobuf
message RemoveOfflineFilesRequest {
  string cloudName = 1;
  string cloudAccountId = 2;
  bool deleteFiles = 3;
  repeated string infoHashes = 4;
  optional string path = 5;
}
```

### GetOfflineQuotaInfo
获取离线下载配额信息。

- **服务**: `CloudDriveFileSrv`
- **方法**: `GetOfflineQuotaInfo`
- **端点**: `/CloudDriveFileSrv/GetOfflineQuotaInfo`

```protobuf
message OfflineQuotaRequest {
  string cloudName = 1;
  string cloudAccountId = 2;
  optional string path = 3;
}

// 响应
message OfflineQuotaInfo {
  int32 total = 1;
  int32 used = 2;
  int32 left = 3;
}
```

### ClearOfflineFiles
按筛选类型清除离线下载。

- **服务**: `CloudDriveFileSrv`
- **方法**: `ClearOfflineFiles`
- **端点**: `/CloudDriveFileSrv/ClearOfflineFiles`

```protobuf
message ClearOfflineFileRequest {
  enum Filter {
    All = 0;
    Finished = 1;
    Error = 2;
    Downloading = 3;
  }
  string cloudName = 1;
  string cloudAccountId = 2;
  Filter filter = 3;
  bool deleteFiles = 4;
  optional string path = 5;
}
```

---

## 系统信息

### GetSystemInfo
获取系统信息。

- **服务**: `CloudDriveSystemSrv`
- **方法**: `GetSystemInfo`
- **端点**: `/CloudDriveSystemSrv/GetSystemInfo`

---

## 其他服务

CloudDrive2 提供以下服务：
- `CloudDriveFileSrv` - 文件操作
- `CloudDriveSystemSrv` - 系统管理
- `CloudDriveMountSrv` - 挂载点管理
- `CloudDriveTransferSrv` - 传输任务
- `CloudDriveCloudAPISrv` - 云API管理
- `UserSrv` - 用户认证

## 注意事项

1. 所有请求使用 POST 方法
2. 空响应 `{}` 表示操作成功 (google.protobuf.Empty)
3. Token 过期后需要重新登录获取
4. 推荐使用 API Token 方式认证
