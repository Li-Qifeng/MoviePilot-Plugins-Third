"""
CloudDrive2 API 客户端

支持功能：
- 115分享链接转存
- 磁力/ED2K离线任务
- 任务状态查询

认证方式：
- API Token (推荐): 直接使用配置的 API Token
- 用户名密码: 通过登录获取临时 Token
"""
import requests
import time
from typing import Optional, Dict
from app.log import logger


class CloudDrive2Client:
    """CloudDrive2 API 客户端
    
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
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.api_token = api_token
        self._login_token = None
        self._token_expiry = 0
        
        # 认证模式
        self._use_api_token = bool(api_token)
        
        # 配置请求会话
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # CloudDrive2 通常为本地服务，禁用代理
        self.session.proxies = {
            'http': None,
            'https': None
        }
        
        # 初始化认证
        self._init_auth()
    
    def _init_auth(self):
        """初始化认证"""
        if self._use_api_token:
            # API Token 模式：直接设置 Authorization header
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_token}'
            })
            logger.info("CloudDrive2 使用 API Token 认证模式")
        else:
            # 用户名密码模式：登录获取 Token
            if not self.username or not self.password:
                raise ValueError("CloudDrive2 认证失败: 需要提供用户名密码或 API Token")
            self._ensure_valid_token()
            logger.info("CloudDrive2 使用用户名密码认证模式")
    
    def _login(self) -> dict:
        """
        登录 CloudDrive2 获取 token（用户名密码模式）
        
        :return: 登录响应数据
        :raises: ValueError 如果登录失败
        """
        try:
            response = self.session.post(
                f'{self.base_url}/api/GetToken',
                json={
                    'userName': self.username,
                    'password': self.password,
                    'totpCode': ''  # TOTP 验证码，可选
                },
                timeout=(10, 30)
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get('success'):
                raise ValueError(f"CloudDrive2登录失败: {data.get('message', '未知错误')}")
            
            logger.info("CloudDrive2 登录成功")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"CloudDrive2 登录请求失败: {str(e)}")
            raise
    
    def _ensure_valid_token(self):
        """确保 token 有效（仅用户名密码模式）"""
        if self._use_api_token:
            # API Token 模式不需要刷新
            return
            
        current_time = time.time()
        
        # 如果 token 不存在或距离过期不到1小时，重新获取
        if not self._login_token or current_time >= (self._token_expiry - 3600):
            login_data = self._login()
            self._login_token = login_data['token']
            
            # 设置 token 过期时间为24小时后
            self._token_expiry = current_time + 86400
            
            # 更新 session 的 Authorization header
            self.session.headers.update({
                'Authorization': f'Bearer {self._login_token}'
            })
            
            logger.debug("CloudDrive2 登录 token 已更新")
    
    def _request(self, endpoint: str, payload: dict = None, 
                 timeout: tuple = (10, 60)) -> dict:
        """
        发送请求到 CloudDrive2 API
        
        :param endpoint: API 端点
        :param payload: 请求负载
        :param timeout: 超时设置
        :return: 响应数据
        """
        if not self._use_api_token:
            self._ensure_valid_token()
        
        if payload is None:
            payload = {}
        
        try:
            response = self.session.post(
                f'{self.base_url}{endpoint}',
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                if self._use_api_token:
                    # API Token 无效
                    logger.error("CloudDrive2 API Token 无效或已过期，请检查配置")
                    raise ValueError("API Token 无效或已过期")
                else:
                    # 登录 token 过期，刷新后重试
                    logger.warning("CloudDrive2 token 过期，正在刷新...")
                    self._login_token = None
                    self._ensure_valid_token()
                    
                    # 重试请求
                    response = self.session.post(
                        f'{self.base_url}{endpoint}',
                        json=payload,
                        timeout=timeout
                    )
                    response.raise_for_status()
                    return response.json()
            raise
        except Exception as e:
            logger.error(f"CloudDrive2 API 请求失败: {str(e)}")
            raise
    
    def add_shared_link(self, share_url: str, password: str = "", 
                        to_folder: str = "/115/Downloads") -> dict:
        """
        添加 115 分享链接进行转存
        
        :param share_url: 115 分享链接，如 https://115.com/s/xxx
        :param password: 分享密码（可选）
        :param to_folder: 转存目标路径
        :return: API 响应
        """
        if not share_url:
            raise ValueError("分享链接不能为空")
        
        logger.info(f"CloudDrive2 添加分享链接转存: {share_url[:50]}... -> {to_folder}")
        
        # CloudDrive2 使用 gRPC-Web 风格端点
        # 尝试多个可能的端点路径
        endpoints = [
            '/api/fs/115/AddSharedLink',
            '/api/FileOperation/AddSharedLink',
            '/api/AddSharedLink'
        ]
        
        payload = {
            'sharedLinkUrl': share_url,
            'sharedPassword': password,
            'toFolder': to_folder
        }
        
        last_error = None
        for endpoint in endpoints:
            try:
                result = self._request(endpoint, payload)
                logger.info(f"CloudDrive2 分享链接转存请求已发送 (端点: {endpoint})")
                return result
            except Exception as e:
                last_error = e
                if '405' in str(e) or '404' in str(e):
                    logger.debug(f"端点 {endpoint} 不可用，尝试下一个...")
                    continue
                raise
        
        # 所有端点都失败
        raise last_error
    
    def add_offline_files(self, urls: str, 
                          to_folder: str = "/115/Offline") -> dict:
        """
        添加离线任务（支持磁力链接、ED2K 等）
        
        :param urls: 资源链接（磁力/ED2K/HTTP等）
        :param to_folder: 下载保存路径
        :return: API 响应
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
        
        # CloudDrive2 使用 gRPC-Web 风格端点
        endpoints = [
            '/api/fs/115/AddOfflineFiles',
            '/api/FileOperation/AddOfflineFiles', 
            '/api/AddOfflineFiles'
        ]
        
        payload = {
            'urls': urls,
            'toFolder': to_folder,
            'checkFolderAfterSecs': 0
        }
        
        last_error = None
        for endpoint in endpoints:
            try:
                result = self._request(endpoint, payload)
                logger.info(f"CloudDrive2 离线任务请求已发送 (端点: {endpoint})")
                return result
            except Exception as e:
                last_error = e
                if '405' in str(e) or '404' in str(e):
                    logger.debug(f"端点 {endpoint} 不可用，尝试下一个...")
                    continue
                raise
        
        raise last_error
    
    def get_offline_status(self, path: str = "/115/Offline", 
                           force_refresh: bool = True) -> dict:
        """
        获取离线任务状态
        
        :param path: 离线任务路径
        :param force_refresh: 是否强制刷新
        :return: 任务状态列表
        """
        logger.debug(f"CloudDrive2 查询离线任务状态: {path}")
        
        result = self._request('/api/ListOfflineFilesByPath', {
            'path': path,
            'forceRefresh': force_refresh
        }, timeout=(10, 30))
        
        return result
    
    def get_upload_status(self) -> dict:
        """
        获取上传/转存任务状态
        
        :return: 任务状态列表
        """
        logger.debug("CloudDrive2 查询上传任务状态")
        
        result = self._request('/api/GetUploadFileList', {}, timeout=(10, 30))
        
        return result
    
    def test_connection(self) -> bool:
        """
        测试连接是否正常
        
        :return: 连接是否成功
        """
        try:
            if self._use_api_token:
                # API Token 模式：尝试一个简单的 API 调用
                self._request('/api/GetSystemInfo', {}, timeout=(5, 10))
            else:
                self._ensure_valid_token()
            return True
        except Exception as e:
            logger.error(f"CloudDrive2 连接测试失败: {str(e)}")
            return False
    
    @property
    def auth_mode(self) -> str:
        """返回当前认证模式"""
        return "API Token" if self._use_api_token else "用户名密码"
