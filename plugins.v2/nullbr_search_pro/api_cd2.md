# CloudDrive2 gRPC API Reference

基于官方 gRPC API 文档。

## 基本说明

- **协议**: gRPC (HTTP/2 + Protocol Buffers)
- **默认端口**: 19798
- **认证**: Bearer Token (JWT)

## 依赖

```bash
pip install grpcio
```

## Proto 文件

下载地址: https://www.clouddrive2.com/api/clouddrive.proto

生成 Python 代码:
```bash
pip install grpcio-tools
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. clouddrive.proto
```

---

## 认证

### GetToken (登录)
- **服务**: `CloudDriveFileSrv`
- **方法**: `GetToken`

```protobuf
message GetTokenRequest {
  string userName = 1;
  string password = 2;
  optional string totpCode = 3;
}

message TokenResult {
  bool success = 1;
  string token = 2;
  string expiration = 3;
  string errorMessage = 4;
}
```

---

## 共享链接

### AddSharedLink
将共享链接添加到文件夹。

- **服务**: `CloudDriveFileSrv`
- **方法**: `AddSharedLink`

```protobuf
message AddSharedLinkRequest {
  string sharedLinkUrl = 1;
  optional string sharedPassword = 2;
  string toFolder = 3;
}
// 响应: google.protobuf.Empty
```

---

## 离线下载

### AddOfflineFiles
添加离线下载任务(磁力链接、ED2K等)。

- **服务**: `CloudDriveFileSrv`
- **方法**: `AddOfflineFiles`

```protobuf
message AddOfflineFileRequest {
  string urls = 1;
  string toFolder = 2;
  uint32 checkFolderAfterSecs = 3;
}
// 响应: FileOperationResult
```

### ListOfflineFilesByPath
列出特定路径中的离线文件。

- **服务**: `CloudDriveFileSrv`
- **方法**: `ListOfflineFilesByPath`

```protobuf
message FileRequest {
  string path = 1;
}

message OfflineFileListResult {
  repeated OfflineFile offlineFiles = 1;
  OfflineStatus status = 2;
}
```

---

## 系统信息

### GetSystemInfo
获取系统信息（无需认证）。

- **服务**: `CloudDriveSystemSrv`
- **方法**: `GetSystemInfo`

```protobuf
// 请求: google.protobuf.Empty

message CloudDriveSystemInfo {
  bool SystemReady = 1;
  string UserName = 2;
  string Version = 3;
  // ...
}
```

---

## Python 示例

```python
import grpc
import clouddrive_pb2
import clouddrive_pb2_grpc

# 连接
channel = grpc.insecure_channel('localhost:19798')
stub = clouddrive_pb2_grpc.CloudDriveFileSrvStub(channel)

# 登录
request = clouddrive_pb2.GetTokenRequest(
    userName='admin',
    password='password'
)
response = stub.GetToken(request)
token = response.token

# 创建认证元数据
metadata = [('authorization', f'Bearer {token}')]

# 添加分享链接
request = clouddrive_pb2.AddSharedLinkRequest(
    sharedLinkUrl='https://115.com/s/xxx',
    toFolder='/115/Downloads'
)
stub.AddSharedLink(request, metadata=metadata)

# 添加离线任务
request = clouddrive_pb2.AddOfflineFileRequest(
    urls='magnet:?xt=urn:btih:...',
    toFolder='/115/Offline'
)
stub.AddOfflineFiles(request, metadata=metadata)

# 关闭
channel.close()
```

## 服务列表

| 服务名 | 说明 |
|--------|------|
| CloudDriveFileSrv | 文件操作（100+ 方法） |
| CloudDriveSystemSrv | 系统管理 |
| CloudDriveMountSrv | 挂载点管理 |
| CloudDriveTransferSrv | 传输任务 |
| CloudDriveCloudAPISrv | 云API管理 |

## 注意事项

1. gRPC 使用 HTTP/2 协议
2. 需要使用 `grpc.insecure_channel()` 连接（如需 TLS 使用 `grpc.secure_channel()`）
3. 所有需要授权的方法需要传递 `metadata=[('authorization', f'Bearer {token}')]`
4. 空响应表示操作成功 (google.protobuf.Empty)
