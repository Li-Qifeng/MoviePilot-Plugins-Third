import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, Optional
from app.log import logger


class NullbrApiClient:
    """Nullbr API客户端"""
    
    def __init__(self, app_id: str, api_key: str = None):
        self._app_id = app_id
        self._api_key = api_key
        self._base_url = "https://api.nullbr.eu.org"
        
        # 配置请求会话
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'MoviePilot-NullbrSearch/1.0.4',
            'Content-Type': 'application/json'
        })
        
        # 配置重试策略
        try:
            retry_strategy = Retry(
                total=3,
                status_forcelist=[429, 500, 502, 503, 504, 408],
                backoff_factor=1,
                allowed_methods=["HEAD", "GET", "OPTIONS"]
            )
            
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self._session.mount("http://", adapter)
            self._session.mount("https://", adapter)
        except Exception as e:
            logger.warning(f"重试策略配置失败: {str(e)}")
    
    def _make_request(self, url: str, params: dict, headers: dict, use_proxy: bool = True) -> requests.Response:
        """发起HTTP请求，支持代理重试机制"""
        session = self._session
        
        # 如果不使用代理，创建临时session
        if not use_proxy:
            session = requests.Session()
            session.headers.update(self._session.headers)
            session.proxies = {'http': None, 'https': None}
        
        timeout = 5 if use_proxy else (10, 30)
        
        return session.get(url, params=params, headers=headers, timeout=timeout)
    
    def search(self, query: str, page: int = 1) -> Optional[Dict]:
        """搜索媒体资源"""
        try:
            headers = {'X-APP-ID': self._app_id}
            
            if self._api_key:
                headers['X-API-KEY'] = self._api_key
            
            params = {
                'query': query,
                'page': page
            }
            
            logger.info(f"搜索请求: {query}")
            logger.debug(f"请求参数: {params}")
            logger.debug(f"请求头: X-APP-ID={self._app_id}, X-API-KEY={'已设置' if self._api_key else '未设置'}")
            
            url = f"{self._base_url}/search"
            
            # 首先尝试使用系统代理
            try:
                logger.debug("尝试使用系统代理访问Nullbr API")
                response = self._make_request(url, params, headers, use_proxy=True)
                logger.info(f"使用系统代理请求成功，状态码: {response.status_code}")
                
            except (requests.exceptions.Timeout, requests.exceptions.ConnectTimeout, 
                   requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
                logger.warning(f"系统代理访问失败: {str(e)}，尝试直连")
                try:
                    response = self._make_request(url, params, headers, use_proxy=False)
                    logger.info(f"直连请求成功，状态码: {response.status_code}")
                    
                except Exception as direct_error:
                    logger.error(f"直连也失败: {str(direct_error)}")
                    raise direct_error
            
            # 检查响应状态
            response.raise_for_status()
            
            # 解析JSON响应
            result = response.json()
            logger.info(f"搜索完成，找到 {len(result.get('items', []))} 个结果")
            
            return result
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                logger.error("API认证失败，请检查APP_ID和API_KEY")
            elif response.status_code == 403:
                logger.error("API访问被禁止，请检查权限")
            elif response.status_code == 429:
                logger.error("API请求频率超限，请稍后再试")
            else:
                logger.error(f"HTTP错误: {e}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"网络请求失败: {str(e)}")
            return None
            
        except Exception as e:
            logger.error(f"搜索异常: {str(e)}")
            return None
    
    def get_movie_resources(self, tmdbid: int, resource_type: str = "115") -> Optional[Dict]:
        """获取电影资源链接"""
        if not self._api_key:
            logger.warning("获取资源链接需要API_KEY")
            return None
            
        try:
            headers = {'X-APP-ID': self._app_id, 'X-API-KEY': self._api_key}
            url = f"{self._base_url}/movie/{tmdbid}/{resource_type}"
            
            # 首先尝试使用系统代理
            try:
                logger.debug("尝试使用系统代理获取电影资源")
                response = self._make_request(url, {}, headers, use_proxy=True)
                logger.info(f"使用系统代理请求成功，状态码: {response.status_code}")
                
            except (requests.exceptions.Timeout, requests.exceptions.ConnectTimeout, 
                   requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
                logger.warning(f"系统代理访问失败: {str(e)}，尝试直连")
                try:
                    response = self._make_request(url, {}, headers, use_proxy=False)
                    logger.info(f"直连请求成功，状态码: {response.status_code}")
                    
                except Exception as direct_error:
                    logger.error(f"直连也失败: {str(direct_error)}")
                    raise direct_error
            
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"获取电影资源成功: TMDB={tmdbid}, 类型={resource_type}")
            return result
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                logger.warning(f"未找到电影资源: TMDB={tmdbid}, 类型={resource_type}")
            else:
                logger.error(f"获取电影资源失败: {e}")
            return None
            
        except Exception as e:
            logger.error(f"获取电影资源异常: {str(e)}")
            return None
    
    def get_tv_resources(self, tmdbid: int, resource_type: str = "115") -> Optional[Dict]:
        """获取剧集资源链接"""
        if not self._api_key:
            logger.warning("获取资源链接需要API_KEY")
            return None
            
        try:
            headers = {'X-APP-ID': self._app_id, 'X-API-KEY': self._api_key}
            url = f"{self._base_url}/tv/{tmdbid}/{resource_type}"
            
            # 首先尝试使用系统代理
            try:
                logger.debug("尝试使用系统代理获取剧集资源")
                response = self._make_request(url, {}, headers, use_proxy=True)
                logger.info(f"使用系统代理请求成功，状态码: {response.status_code}")
                
            except (requests.exceptions.Timeout, requests.exceptions.ConnectTimeout, 
                   requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
                logger.warning(f"系统代理访问失败: {str(e)}，尝试直连")
                try:
                    response = self._make_request(url, {}, headers, use_proxy=False)
                    logger.info(f"直连请求成功，状态码: {response.status_code}")
                    
                except Exception as direct_error:
                    logger.error(f"直连也失败: {str(direct_error)}")
                    raise direct_error
            
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"获取剧集资源成功: TMDB={tmdbid}, 类型={resource_type}")
            return result
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                logger.warning(f"未找到剧集资源: TMDB={tmdbid}, 类型={resource_type}")
            else:
                logger.error(f"获取剧集资源失败: {e}")
            return None
            
        except Exception as e:
            logger.error(f"获取剧集资源异常: {str(e)}")
            return None