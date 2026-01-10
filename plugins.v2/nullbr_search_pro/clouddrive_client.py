"""
CloudDrive2 gRPC 客户端

支持功能：
- 115分享链接转存
- 磁力/ED2K离线任务
- 任务状态查询

使用 gRPC 协议与 CloudDrive2 通信
"""
import grpc
from typing import Optional
from app.log import logger

# 导入生成的 gRPC 代码
try:
    from . import clouddrive_pb2
    from . import clouddrive_pb2_grpc
except ImportError:
    import clouddrive_pb2
    import clouddrive_pb2_grpc


class CloudDrive2Client:
    """CloudDrive2 gRPC 客户端
    
    支持两种认证方式：
    1. API Token（推荐）: 在 CloudDrive2 设置中生成的永久 Token
    2. 用户名密码: 通过登录接口获取临时 Token
    """
    
    def __init__(self, base_url: str, username: str = None, password: str = None, 
                 api_token: str = None):
        """
        初始化客户端
        
        :param base_url: CloudDrive2 服务器地址，如 http://localhost:19798
        :param username: 用户名（密码认证时必填）
        :param password: 密码（密码认证时必填）
        :param api_token: API Token（优先使用，推荐）
        """
        # 解析地址，移除 http:// 前缀
        self.address = base_url.replace('http://', '').replace('https://', '').rstrip('/')
        self.username = username
        self.password = password
        self.api_token = api_token
        self._jwt_token = None
        
        # 认证模式
        self._use_api_token = bool(api_token)
        
        # 创建 gRPC channel
        self.channel = grpc.insecure_channel(self.address)
        
        # 创建服务 stub (所有方法都在 CloudDriveFileSrv 中)
        self.file_stub = clouddrive_pb2_grpc.CloudDriveFileSrvStub(self.channel)
        
        # 初始化认证
        self._init_auth()
    
    def _init_auth(self):
        """初始化认证"""
        if self._use_api_token:
            # API Token 直接使用
            self._jwt_token = self.api_token
            logger.info("CloudDrive2 使用 API Token 认证模式")
        else:
            # 用户名密码模式：登录获取 Token
            if not self.username or not self.password:
                raise ValueError("CloudDrive2 认证失败: 需要提供用户名密码或 API Token")
            self._login()
            logger.info("CloudDrive2 使用用户名密码认证模式")
    
    def _login(self):
        """登录获取 JWT Token"""
        try:
            request = clouddrive_pb2.GetTokenRequest(
                userName=self.username,
                password=self.password
            )
            
            response = self.file_stub.GetToken(request)
            
            if response.success:
                self._jwt_token = response.token
                logger.info(f"CloudDrive2 登录成功，过期时间: {response.expiration}")
            else:
                raise ValueError(f"CloudDrive2 登录失败: {response.errorMessage}")
                
        except grpc.RpcError as e:
            logger.error(f"CloudDrive2 登录请求失败: {e.details()}")
            raise
    
    def _create_metadata(self):
        """创建带授权的元数据"""
        if not self._jwt_token:
            return []
        return [('authorization', f'Bearer {self._jwt_token}')]
    
    def close(self):
        """关闭 gRPC channel"""
        if self.channel:
            self.channel.close()
            logger.info("CloudDrive2 客户端已关闭")
    
    def add_shared_link(self, share_url: str, password: str = "", 
                        to_folder: str = "/115/Downloads") -> dict:
        """
        添加 115 分享链接进行转存
        
        :param share_url: 115 分享链接
        :param password: 分享密码（可选）
        :param to_folder: 转存目标路径
        :return: 操作结果
        """
        if not share_url:
            raise ValueError("分享链接不能为空")
        
        logger.info(f"CloudDrive2 添加分享链接转存: {share_url[:50]}... -> {to_folder}")
        
        try:
            request = clouddrive_pb2.AddSharedLinkRequest(
                sharedLinkUrl=share_url,
                sharedPassword=password,
                toFolder=to_folder
            )
            
            metadata = self._create_metadata()
            self.file_stub.AddSharedLink(request, metadata=metadata)
            
            logger.info("CloudDrive2 分享链接转存请求已发送")
            return {'success': True}
            
        except grpc.RpcError as e:
            logger.error(f"CloudDrive2 分享链接转存失败: {e.details()}")
            raise ValueError(f"转存失败: {e.details()}")
    
    def add_offline_files(self, urls: str, 
                          to_folder: str = "/115/Offline") -> dict:
        """
        添加离线任务（支持磁力链接、ED2K 等）
        
        :param urls: 资源链接（磁力/ED2K/HTTP等）
        :param to_folder: 下载保存路径
        :return: 操作结果
        """
        if not urls:
            raise ValueError("资源链接不能为空")
        
        # 判断链接类型
        link_type = "未知"
        if urls.startswith("magnet:"):
            link_type = "磁力"
        elif urls.lower().startswith("ed2k://"):
            link_type = "ED2K"
        elif urls.startswith("http"):
            link_type = "HTTP"
        
        logger.info(f"CloudDrive2 添加{link_type}离线任务: {urls[:50]}... -> {to_folder}")
        
        try:
            request = clouddrive_pb2.AddOfflineFileRequest(
                urls=urls,
                toFolder=to_folder,
                checkFolderAfterSecs=0
            )
            
            metadata = self._create_metadata()
            result = self.file_stub.AddOfflineFiles(request, metadata=metadata)
            
            logger.info("CloudDrive2 离线任务请求已发送")
            return {
                'success': result.result.success if hasattr(result, 'result') else True,
                'message': result.result.errorMessage if hasattr(result, 'result') else ''
            }
            
        except grpc.RpcError as e:
            logger.error(f"CloudDrive2 离线任务添加失败: {e.details()}")
            raise ValueError(f"离线任务添加失败: {e.details()}")
    
    def get_offline_status(self, path: str = "/115/Offline") -> dict:
        """
        获取离线任务状态
        
        :param path: 离线任务路径
        :return: 任务状态列表
        """
        logger.debug(f"CloudDrive2 查询离线任务状态: {path}")
        
        try:
            request = clouddrive_pb2.FileRequest(path=path)
            
            metadata = self._create_metadata()
            result = self.file_stub.ListOfflineFilesByPath(request, metadata=metadata)
            
            return {
                'offlineFiles': list(result.offlineFiles) if hasattr(result, 'offlineFiles') else [],
                'status': result.status if hasattr(result, 'status') else None
            }
            
        except grpc.RpcError as e:
            logger.error(f"CloudDrive2 查询离线状态失败: {e.details()}")
            raise ValueError(f"查询失败: {e.details()}")
    
    def get_system_info(self) -> dict:
        """
        获取系统信息（无需认证）
        
        :return: 系统信息
        """
        try:
            from google.protobuf import empty_pb2
            # GetSystemInfo 在 CloudDriveFileSrv 中
            result = self.file_stub.GetSystemInfo(empty_pb2.Empty())
            
            return {
                'systemReady': result.SystemReady,
                'userName': result.UserName if hasattr(result, 'UserName') else '',
                'version': result.Version if hasattr(result, 'Version') else ''
            }
            
        except grpc.RpcError as e:
            logger.error(f"CloudDrive2 获取系统信息失败: {e.details()}")
            raise ValueError(f"获取系统信息失败: {e.details()}")
    
    def test_connection(self) -> bool:
        """
        测试连接是否正常
        
        :return: 连接是否成功
        """
        try:
            self.get_system_info()
            return True
        except Exception as e:
            logger.error(f"CloudDrive2 连接测试失败: {str(e)}")
            return False
    
    @property
    def auth_mode(self) -> str:
        """返回当前认证模式"""
        return "API Token" if self._use_api_token else "用户名密码"
    
    @property  
    def session(self):
        """兼容旧代码的属性"""
        return self.channel
