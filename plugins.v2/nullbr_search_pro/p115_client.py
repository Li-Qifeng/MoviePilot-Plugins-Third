"""
115 分享链接转存客户端

使用 p115client 库通过 Cookie 认证调用 115 Web API
实现分享链接转存功能

依赖: pip install p115client
"""
import re
from typing import Optional, Tuple
from app.log import logger

try:
    from p115client import P115Client, check_response
except ImportError:
    P115Client = None
    check_response = None
    logger.warning("p115client 未安装，115分享链接转存功能不可用")


class P115ShareClient:
    """115 分享链接转存客户端
    
    通过 Cookie 认证使用 115 Web API 进行分享链接转存
    
    使用方法:
        client = P115ShareClient(cookies="UID=...; CID=...; SEID=...")
        result = client.save_share_link("https://115.com/s/xxx?password=1234", "/我的接收")
    """
    
    # 支持的 115 分享链接域名
    SHARE_DOMAINS = [
        '115.com',
        '115cdn.com', 
        'anxia.com',
        '115.tv'
    ]
    
    # 分享链接正则模式
    SHARE_PATTERN = re.compile(
        r'(?:https?://)?(?:www\.)?(?:' + 
        '|'.join(d.replace('.', r'\.') for d in SHARE_DOMAINS) + 
        r')/s/([a-zA-Z0-9]+)(?:\?password=([a-zA-Z0-9]+))?'
    )
    
    def __init__(self, cookies: str):
        """
        初始化客户端
        
        :param cookies: 115 Cookie 字符串，格式如 "UID=...; CID=...; SEID=..."
        """
        if P115Client is None:
            raise ImportError("p115client 未安装，请运行: pip install p115client")
        
        self.cookies = cookies
        self._client: Optional[P115Client] = None
        
        # 初始化客户端
        self._init_client()
    
    def _init_client(self):
        """初始化 p115client"""
        try:
            self._client = P115Client(self.cookies)
            logger.info("115 分享转存客户端初始化成功")
        except Exception as e:
            logger.error(f"115 分享转存客户端初始化失败: {str(e)}")
            raise
    
    def parse_share_link(self, share_url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        解析分享链接，提取 share_code 和 password
        
        :param share_url: 分享链接
        :return: (share_code, password) 元组
        """
        # 清理链接
        share_url = share_url.strip()
        
        # 使用正则匹配
        match = self.SHARE_PATTERN.search(share_url)
        if match:
            share_code = match.group(1)
            password = match.group(2) or ""
            return share_code, password
        
        # 尝试简单的分享码格式 (仅 share_code:password)
        if ':' in share_url and '/' not in share_url:
            parts = share_url.split(':')
            if len(parts) == 2:
                return parts[0], parts[1]
        
        return None, None
    
    def get_share_info(self, share_code: str, password: str = "") -> dict:
        """
        获取分享链接信息
        
        :param share_code: 分享码
        :param password: 分享密码
        :return: 分享信息
        """
        try:
            response = self._client.share_snap({
                "share_code": share_code,
                "receive_code": password,
                "offset": 0,
                "limit": 1
            })
            return check_response(response)
        except Exception as e:
            logger.error(f"获取分享信息失败: {str(e)}")
            raise
    
    def save_share_link(self, share_url: str, to_folder_cid: str = "0") -> dict:
        """
        转存分享链接到指定目录
        
        :param share_url: 分享链接，支持多种格式:
            - https://115.com/s/xxx?password=1234
            - https://115cdn.com/s/xxx?password=1234
            - xxx:1234 (share_code:password)
        :param to_folder_cid: 目标文件夹 CID，默认 "0" 表示根目录
        :return: 转存结果
        """
        # 解析分享链接
        share_code, password = self.parse_share_link(share_url)
        
        if not share_code:
            raise ValueError(f"无法解析分享链接: {share_url}")
        
        logger.info(f"115 转存分享链接: {share_code[:10]}... -> cid:{to_folder_cid}")
        
        try:
            # 1. 获取分享信息
            share_info = self.get_share_info(share_code, password)
            
            if not share_info.get("data", {}).get("list"):
                raise ValueError("分享链接无效或已过期")
            
            # 获取 snap_id 和文件列表
            snap_id = share_info["data"]["shareinfo"]["snap_id"]
            file_list = share_info["data"]["list"]
            
            # 2. 获取所有文件 ID
            file_ids = [str(f["fid"]) for f in file_list]
            
            if not file_ids:
                raise ValueError("分享链接中没有可转存的文件")
            
            # 3. 执行转存
            response = self._client.share_receive({
                "share_code": share_code,
                "receive_code": password,
                "snap_id": snap_id,
                "cid": to_folder_cid,
                "file_id": ",".join(file_ids)
            })
            
            result = check_response(response)
            
            logger.info(f"115 转存成功: {len(file_ids)} 个文件")
            
            return {
                "success": True,
                "message": f"成功转存 {len(file_ids)} 个文件",
                "file_count": len(file_ids),
                "share_code": share_code
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"115 转存失败: {error_msg}")
            
            # 解析常见错误
            if "expired" in error_msg.lower() or "过期" in error_msg:
                raise ValueError("分享链接已过期")
            elif "password" in error_msg.lower() or "密码" in error_msg:
                raise ValueError("分享密码错误")
            elif "limit" in error_msg.lower() or "上限" in error_msg:
                raise ValueError("接收人次已达上限")
            else:
                raise ValueError(f"转存失败: {error_msg}")
    
    def get_folder_cid(self, folder_path: str) -> Optional[str]:
        """
        根据文件夹路径获取 CID
        
        :param folder_path: 文件夹路径，如 "/我的接收/电影"
        :return: 文件夹 CID
        """
        try:
            # 根目录
            if folder_path in ["/", "", "0"]:
                return "0"
            
            # 按路径查找
            response = self._client.fs_dir_getid({
                "path": folder_path
            })
            
            result = check_response(response)
            return str(result.get("id", "0"))
            
        except Exception as e:
            logger.warning(f"获取文件夹 CID 失败，使用根目录: {str(e)}")
            return "0"
    
    def create_folder(self, parent_cid: str, folder_name: str) -> Optional[str]:
        """
        创建文件夹
        
        :param parent_cid: 父文件夹 CID
        :param folder_name: 新文件夹名称
        :return: 新文件夹 CID
        """
        try:
            response = self._client.fs_mkdir({
                "cname": folder_name,
                "pid": int(parent_cid)
            })
            
            result = check_response(response)
            return str(result.get("cid", ""))
            
        except Exception as e:
            logger.error(f"创建文件夹失败: {str(e)}")
            return None
    
    def test_connection(self) -> bool:
        """
        测试连接是否正常
        
        :return: 连接是否成功
        """
        try:
            # 获取用户信息测试连接
            response = self._client.user_my()
            check_response(response)
            return True
        except Exception as e:
            logger.error(f"115 连接测试失败: {str(e)}")
            return False
    
    @property
    def is_available(self) -> bool:
        """客户端是否可用"""
        return self._client is not None
