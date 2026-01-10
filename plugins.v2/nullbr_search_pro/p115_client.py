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
    
    def __init__(self, cookies: str, save_path: str = "/我的接收"):
        """
        初始化客户端
        
        :param cookies: 115 Cookie 字符串，格式如 "UID=...; CID=...; SEID=..."
        :param save_path: 转存的目标文件夹路径（默认 /我的接收）
        """
        if P115Client is None:
            raise ImportError("p115client 未安装，请运行: pip install p115client")
        
        self.cookies = cookies
        self.save_path = save_path
        self._client: Optional[P115Client] = None
        self._save_cid: Optional[str] = None  # 缓存的目标文件夹 CID
        
        # 初始化客户端
        self._init_client()
    
    def _init_client(self):
        """初始化 p115client"""
        try:
            self._client = P115Client(self.cookies)
            logger.info("115 分享转存客户端初始化成功")
            
            # 自动获取保存目录的 CID
            self._save_cid = self._get_or_create_folder_cid(self.save_path)
            logger.info(f"115 转存目标目录: {self.save_path} -> CID: {self._save_cid}")
            
        except Exception as e:
            logger.error(f"115 分享转存客户端初始化失败: {str(e)}")
            raise
    
    def _get_or_create_folder_cid(self, folder_path: str) -> str:
        """
        获取文件夹 CID，如果不存在则创建
        
        :param folder_path: 文件夹路径
        :return: 文件夹 CID
        """
        # 根目录
        if folder_path in ["/", "", "0"]:
            return "0"
        
        try:
            # 尝试获取文件夹信息
            logger.debug(f"尝试获取文件夹 CID: {folder_path}")
            response = self._client.fs_files({"path": folder_path, "limit": 1})
            result = check_response(response)
            
            # 从响应中获取 cid
            if "path" in result and len(result["path"]) > 0:
                cid = str(result["path"][-1].get("cid", "0"))
                logger.debug(f"获取文件夹 CID 成功: {folder_path} -> {cid}")
                return cid
                
        except Exception as e:
            logger.warning(f"获取文件夹失败，尝试创建: {folder_path}, 错误: {str(e)}")
        
        # 文件夹不存在，尝试创建
        try:
            return self._create_folder_path(folder_path)
        except Exception as e:
            logger.error(f"创建文件夹失败: {folder_path}, 错误: {str(e)}")
            return "0"
    
    def _create_folder_path(self, folder_path: str) -> str:
        """
        创建文件夹路径（支持多级）
        
        :param folder_path: 文件夹路径，如 "/我的接收/电影"
        :return: 最终文件夹的 CID
        """
        parts = [p for p in folder_path.split("/") if p]
        current_cid = "0"
        
        for part in parts:
            try:
                logger.debug(f"创建/获取文件夹: {part} in CID: {current_cid}")
                response = self._client.fs_mkdir({"cname": part, "pid": int(current_cid)})
                result = check_response(response)
                current_cid = str(result.get("cid", current_cid))
                logger.debug(f"文件夹 {part} CID: {current_cid}")
            except Exception as e:
                # 如果文件夹已存在，尝试获取其 CID
                error_str = str(e)
                if "已存在" in error_str or "exists" in error_str.lower():
                    # 获取已存在文件夹的 CID
                    try:
                        list_resp = self._client.fs_files({"cid": current_cid, "limit": 1000})
                        list_result = check_response(list_resp)
                        for item in list_result.get("data", []):
                            if item.get("n") == part:
                                current_cid = str(item.get("cid", current_cid))
                                logger.debug(f"已存在文件夹 {part} CID: {current_cid}")
                                break
                    except:
                        pass
                else:
                    logger.warning(f"创建文件夹 {part} 失败: {error_str}")
        
        return current_cid
    
    def parse_share_link(self, share_url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        解析分享链接，提取 share_code 和 password
        
        :param share_url: 分享链接
        :return: (share_code, password) 元组
        """
        # 清理链接（移除 URL 片段和多余字符）
        share_url = share_url.strip()
        if '#' in share_url:
            share_url = share_url.split('#')[0]
        if '&' in share_url:
            # 处理 URL 参数
            pass
        
        logger.debug(f"解析分享链接: {share_url}")
        
        # 使用正则匹配
        match = self.SHARE_PATTERN.search(share_url)
        if match:
            share_code = match.group(1)
            password = match.group(2) or ""
            logger.debug(f"正则匹配成功: share_code={share_code}, password={password}")
            return share_code, password
        
        # 尝试简单的分享码格式 (仅 share_code:password)
        if ':' in share_url and '/' not in share_url:
            parts = share_url.split(':')
            if len(parts) == 2:
                logger.debug(f"简单格式匹配: share_code={parts[0]}, password={parts[1]}")
                return parts[0], parts[1]
        
        logger.warning(f"无法解析分享链接: {share_url}")
        return None, None
    
    def get_share_info(self, share_code: str, password: str = "") -> dict:
        """
        获取分享链接信息
        
        :param share_code: 分享码
        :param password: 分享密码
        :return: 分享信息
        """
        logger.debug(f"获取分享信息: share_code={share_code}, password={'***' if password else '无'}")
        
        try:
            response = self._client.share_snap({
                "share_code": share_code,
                "receive_code": password,
                "offset": 0,
                "limit": 100  # 增加限制以获取更多文件
            })
            result = check_response(response)
            
            # 详细记录返回数据结构
            logger.debug(f"分享信息返回数据 keys: {result.keys() if isinstance(result, dict) else type(result)}")
            if isinstance(result, dict) and "data" in result:
                data = result["data"]
                logger.debug(f"data keys: {data.keys() if isinstance(data, dict) else type(data)}")
                if "list" in data and len(data["list"]) > 0:
                    first_item = data["list"][0]
                    logger.debug(f"第一个文件的字段: {first_item.keys() if isinstance(first_item, dict) else type(first_item)}")
            
            return result
            
        except Exception as e:
            logger.error(f"获取分享信息失败: {str(e)}")
            raise
    
    def save_share_link(self, share_url: str, to_folder_path: str = None) -> dict:
        """
        转存分享链接到指定目录
        
        :param share_url: 分享链接，支持多种格式
        :param to_folder_path: 目标文件夹路径（可选，默认使用初始化时的路径）
        :return: 转存结果
        """
        # 解析分享链接
        share_code, password = self.parse_share_link(share_url)
        
        if not share_code:
            raise ValueError(f"无法解析分享链接: {share_url}")
        
        # 确定目标目录 CID
        if to_folder_path:
            target_cid = self._get_or_create_folder_cid(to_folder_path)
        else:
            target_cid = self._save_cid or "0"
        
        logger.info(f"115 转存分享链接: {share_code[:10]}... -> 路径={to_folder_path or self.save_path}, CID={target_cid}")
        
        try:
            # 1. 获取分享信息
            share_info = self.get_share_info(share_code, password)
            
            # 检查数据结构
            if not isinstance(share_info, dict):
                raise ValueError(f"分享信息返回格式异常: {type(share_info)}")
            
            data = share_info.get("data", {})
            if not isinstance(data, dict):
                raise ValueError(f"分享数据格式异常: {type(data)}")
            
            file_list = data.get("list", [])
            if not file_list:
                raise ValueError("分享链接无效或已过期")
            
            logger.debug(f"分享包含 {len(file_list)} 个文件/文件夹")
            
            # 获取 snap_id
            share_info_data = data.get("shareinfo", {})
            snap_id = share_info_data.get("snap_id")
            if not snap_id:
                logger.error(f"shareinfo 数据: {share_info_data}")
                raise ValueError("无法获取 snap_id")
            
            logger.debug(f"snap_id: {snap_id}")
            
            # 2. 获取所有文件 ID（支持多种可能的字段名）
            file_ids = []
            for f in file_list:
                # 尝试不同的字段名
                fid = f.get("fid") or f.get("file_id") or f.get("id") or f.get("sha1") or f.get("cid")
                if fid:
                    file_ids.append(str(fid))
                else:
                    logger.warning(f"无法获取文件 ID，文件数据: {f}")
            
            if not file_ids:
                logger.error(f"文件列表示例: {file_list[0] if file_list else 'empty'}")
                raise ValueError("分享链接中没有可转存的文件")
            
            logger.debug(f"待转存文件 ID: {file_ids[:5]}{'...' if len(file_ids) > 5 else ''}")
            
            # 3. 执行转存
            logger.debug(f"执行转存: share_code={share_code}, snap_id={snap_id}, cid={target_cid}, file_ids={len(file_ids)}")
            
            response = self._client.share_receive({
                "share_code": share_code,
                "receive_code": password,
                "snap_id": snap_id,
                "cid": target_cid,
                "file_id": ",".join(file_ids)
            })
            
            result = check_response(response)
            logger.debug(f"转存响应: {result}")
            
            logger.info(f"115 转存成功: {len(file_ids)} 个文件")
            
            return {
                "success": True,
                "message": f"成功转存 {len(file_ids)} 个文件到 {to_folder_path or self.save_path}",
                "file_count": len(file_ids),
                "share_code": share_code
            }
            
        except ValueError:
            raise
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
    
    def test_connection(self) -> bool:
        """
        测试连接是否正常
        
        :return: 连接是否成功
        """
        try:
            # 获取用户信息测试连接
            response = self._client.user_my()
            result = check_response(response)
            logger.debug(f"115 连接测试成功: {result}")
            return True
        except Exception as e:
            logger.error(f"115 连接测试失败: {str(e)}")
            return False
    
    @property
    def is_available(self) -> bool:
        """客户端是否可用"""
        return self._client is not None
