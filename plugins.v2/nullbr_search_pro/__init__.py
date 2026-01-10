import re
import time
from typing import Any, List, Dict, Tuple

from app.core.event import eventmanager, Event
from app.log import logger
from app.plugins import _PluginBase
from app.schemas.types import EventType
from app.db.systemconfig_oper import SystemConfigOper


class nullbr_search_pro(_PluginBase):
    # 插件基本信息
    plugin_name = "Nullbr资源搜索Pro"
    plugin_desc = "支持Nullbr API搜索影视资源，集成CloudDrive2实现115转存和磁力/ED2K离线下载"
    plugin_icon = "https://raw.githubusercontent.com/Li-Qifeng/MoviePilot-Plugins-Third/main/icons/nullbr_pro.png"
    plugin_version = "1.5.0"
    plugin_author = "Li-Qifeng"
    author_url = "https://github.com/Li-Qifeng"
    plugin_config_prefix = "nullbr_search_pro_"
    plugin_order = 1
    auth_level = 1

    def __init__(self):
        super().__init__()
        # 基本配置
        self._enabled = False
        self._app_id = None
        self._api_key = None
        self._resource_priority = ["115", "magnet", "ed2k", "video"]  # 默认优先级
        self._enable_115 = True
        self._enable_magnet = True
        self._enable_video = True
        self._enable_ed2k = True
        self._search_timeout = 30
        
        # CloudDrive2配置 (用于磁力/ED2K离线)
        self._cd2_enabled = False
        self._cd2_url = ""
        self._cd2_api_token = ""                  # API Token（推荐）
        self._cd2_username = ""                   # 用户名（备用）
        self._cd2_password = ""                   # 密码（备用）
        self._cd2_save_path = "/115/Downloads"    # 115转存路径
        self._cd2_offline_path = "/115/Offline"   # 离线任务路径
        
        # 115转存配置 (用于分享链接转存)
        self._p115_enabled = False
        self._p115_cookies = ""                   # 115 Cookie
        self._p115_save_cid = "0"                 # 转存目标目录 CID
        
        # 客户端实例
        self._client = None
        self._cd2_client = None
        self._p115_client = None                  # 115分享转存客户端
        
        # 用户搜索结果缓存和资源缓存
        self._user_search_cache = {}  # {userid: {'results': [...], 'timestamp': time.time()}}
        self._user_resource_cache = {}  # {userid: {'resources': [...], 'title': str, 'timestamp': time.time()}}
        
        # 统计数据
        self._stats = {
            'total_searches': 0,           # 总搜索次数
            'successful_searches': 0,      # 成功搜索次数  
            'failed_searches': 0,          # 失败搜索次数
            'total_resources': 0,          # 获取的总资源数
            'cd2_transfers': 0,            # CloudDrive2转存次数
            'cd2_offline': 0,              # 离线任务次数
            'successful_transfers': 0,     # 成功转存次数
            'failed_transfers': 0,         # 失败转存次数
            'last_search_time': None,      # 最后搜索时间
            'last_transfer_time': None,    # 最后转存时间
            'api_status': 'unknown',       # API状态
            'cd2_status': 'unknown',       # CloudDrive2状态
            'popular_resources': {}        # 热门搜索统计 {keyword: count}
        }

    def _format_message_for_wechat(self, text: str) -> str:
        """格式化消息以兼容微信企业应用显示"""
        # 微信企业应用需要特殊处理换行符和格式
        # 将连续的换行符合并，并在关键位置添加分隔符
        lines = text.split('\n')
        formatted_lines = []
        
        for i, line in enumerate(lines):
            stripped_line = line.strip()
            
            # 空行处理：连续空行只保留一个
            if not stripped_line:
                if formatted_lines and formatted_lines[-1] != '':
                    formatted_lines.append('')
                continue
            
            # 对于标题行（包含emoji和中文冒号），前后加空行
            if ('🎬' in stripped_line or '🎯' in stripped_line or '✅' in stripped_line or '❌' in stripped_line) and '：' in stripped_line:
                if formatted_lines and formatted_lines[-1] != '':
                    formatted_lines.append('')
                formatted_lines.append(stripped_line)
                formatted_lines.append('')
            # 对于编号列表项
            elif re.match(r'^\d+\.', stripped_line) or re.match(r'^【\d+】', stripped_line):
                if formatted_lines and formatted_lines[-1] != '':
                    formatted_lines.append('')
                formatted_lines.append(stripped_line)
            # 对于缩进的详情行
            elif stripped_line.startswith(' ') or stripped_line.startswith('   '):
                formatted_lines.append(stripped_line)
            # 对于分隔符和提示信息
            elif stripped_line.startswith('---') or stripped_line.startswith('💡') or stripped_line.startswith('📋'):
                if formatted_lines and formatted_lines[-1] != '':
                    formatted_lines.append('')
                formatted_lines.append(stripped_line)
            else:
                formatted_lines.append(stripped_line)
        
        return '\n'.join(formatted_lines)

    def post_message(self, channel, title: str, text: str, userid: str = None):
        """发送消息，自动处理微信格式兼容"""
        # 检测是否为微信通知渠道
        try:
            # channel可能是字符串或MessageChannel对象
            if hasattr(channel, 'name'):
                channel_name = str(channel.name).lower()
            elif hasattr(channel, 'type'):
                channel_name = str(channel.type).lower()
            else:
                channel_name = str(channel).lower()
            
            # 检测微信相关渠道
            if 'wechat' in channel_name or 'wecom' in channel_name or 'wework' in channel_name:
                formatted_text = self._format_message_for_wechat(text)
            else:
                formatted_text = text
        except Exception:
            # 如果检测失败，使用原文本
            formatted_text = text
        
        # 调用父类的post_message方法
        super().post_message(channel=channel, title=title, text=formatted_text, userid=userid)

    def init_plugin(self, config: dict = None):
        """初始化插件"""
        logger.info(f"正在初始化 {self.plugin_name} v{self.plugin_version}")
        config_oper = SystemConfigOper()
        if config:
            self._enabled = config.get("enabled", False)
            self._app_id = config.get("app_id")
            self._api_key = config.get("api_key")
            
            # 构建资源优先级列表
            priority_list = []
            for i in range(1, 5):
                priority = config.get(f"priority_{i}")
                if priority and priority not in priority_list:
                    priority_list.append(priority)
            
            # 如果配置不完整，使用默认优先级
            if len(priority_list) < 4:
                self._resource_priority = ["115", "magnet", "ed2k", "video"]
            else:
                self._resource_priority = priority_list
            
            self._enable_115 = config.get("enable_115", True)
            self._enable_magnet = config.get("enable_magnet", True)
            self._enable_video = config.get("enable_video", True)
            self._enable_ed2k = config.get("enable_ed2k", True)
            self._search_timeout = config.get("search_timeout", 30)
            
            # CloudDrive2配置
            self._cd2_enabled = config.get("cd2_enabled", False)
            self._cd2_url = config.get("cd2_url", "")
            self._cd2_api_token = config.get("cd2_api_token", "")
            self._cd2_username = config.get("cd2_username", "")
            self._cd2_password = config.get("cd2_password", "")
            self._cd2_save_path = config.get("cd2_save_path", "/115/Downloads")
            self._cd2_offline_path = config.get("cd2_offline_path", "/115/Offline")
            
            logger.info(f"Nullbr资源优先级设置: {' > '.join(self._resource_priority)}")
            if self._cd2_enabled:
                auth_mode = "API Token" if self._cd2_api_token else "用户名密码"
                logger.info(f"CloudDrive2已启用: {self._cd2_url} (认证模式: {auth_mode})")
        
        # 初始化API客户端
        if self._enabled and self._app_id:
            try:
                from .nullbr_client import NullbrApiClient
                self._client = NullbrApiClient(self._app_id, self._api_key)
                logger.info("Nullbr API客户端初始化成功")
            except Exception as e:
                logger.error(f"Nullbr API客户端初始化失败: {str(e)}")
                self._enabled = False
        else:
            if not self._app_id:
                logger.warning("Nullbr插件配置错误: 缺少APP_ID")
            self._client = None
        
        # 初始化CloudDrive2客户端
        # 支持两种认证方式: API Token (优先) 或 用户名密码
        if self._cd2_enabled and self._cd2_url:
            has_api_token = bool(self._cd2_api_token)
            has_password_auth = bool(self._cd2_username and self._cd2_password)
            
            if has_api_token or has_password_auth:
                try:
                    from .clouddrive_client import CloudDrive2Client
                    self._cd2_client = CloudDrive2Client(
                        base_url=self._cd2_url,
                        username=self._cd2_username if not has_api_token else None,
                        password=self._cd2_password if not has_api_token else None,
                        api_token=self._cd2_api_token if has_api_token else None
                    )
                    logger.info(f"CloudDrive2客户端已初始化 (认证模式: {self._cd2_client.auth_mode})")
                except Exception as e:
                    logger.error(f"CloudDrive2初始化失败: {str(e)}")
                    self._cd2_enabled = False
                    self._cd2_client = None
            else:
                logger.warning("CloudDrive2配置不完整: 需要 API Token 或 用户名密码")
                self._cd2_client = None
        else:
            self._cd2_client = None
        
        # 初始化 115 分享转存客户端
        self._p115_enabled = config.get("p115_enabled", False) if config else False
        self._p115_cookies = config.get("p115_cookies", "") if config else ""
        self._p115_save_cid = config.get("p115_save_cid", "0") if config else "0"
        
        if self._p115_enabled and self._p115_cookies:
            try:
                from .p115_client import P115ShareClient
                self._p115_client = P115ShareClient(cookies=self._p115_cookies)
                logger.info("115 分享转存客户端已初始化")
            except ImportError:
                logger.warning("p115client 未安装，115分享转存功能不可用。请安装: pip install p115client")
                self._p115_client = None
            except Exception as e:
                logger.error(f"115 分享转存客户端初始化失败: {str(e)}")
                self._p115_client = None
        else:
            self._p115_client = None
            if self._p115_enabled and not self._p115_cookies:
                logger.warning("115 分享转存已启用但未配置 Cookie")

    def get_state(self) -> bool:
        """获取插件状态"""
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        """获取插件命令"""
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        """获取插件API"""
        pass

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """
        return [
            {
                'component': 'VForm',
                'content': [
                {
                    'component': 'VRow',
                    'content': [
                    {
                        'component': 'VCol',
                        'props': {'cols': 12},
                        'content': [
                        {
                            'component': 'VAlert',
                            'props': {
                            'type': 'info',
                            'variant': 'tonal',
                            'text': '🌟 Nullbr资源搜索插件将优先使用Nullbr API查找资源。支持115网盘、磁力、ed2k、m3u8等多种资源类型。'
                            }
                        }
                        ]
                    }
                    ]
                },
                {
                    'component': 'VRow',
                    'content': [
                    {
                        'component': 'VCol',
                        'props': {'cols': 12, 'md': 6},
                        'content': [
                        {
                            'component': 'VSwitch',
                            'props': {
                            'model': 'enabled',
                            'label': '启用插件',
                            'hint': '开启后插件将开始工作，优先搜索Nullbr资源',
                            'persistent-hint': True
                            }
                        }
                        ]
                    }
                    ]
                },
                {
                    'component': 'VRow',
                    'content': [
                    {
                        'component': 'VCol',
                        'props': {'cols': 12, 'md': 6},
                        'content': [
                        {
                            'component': 'VTextField',
                            'props': {
                            'model': 'app_id',
                            'label': 'APP_ID *',
                            'placeholder': '请输入Nullbr API的APP_ID',
                            'hint': '必填：用于API认证的应用ID',
                            'persistent-hint': True,
                            'clearable': True
                            }
                        }
                        ]
                    },
                    {
                        'component': 'VCol',
                        'props': {'cols': 12, 'md': 6},
                        'content': [
                        {
                            'component': 'VTextField',
                            'props': {
                            'model': 'api_key',
                            'label': 'API_KEY',
                            'placeholder': '请输入Nullbr API的API_KEY',
                            'hint': '可选：用于获取资源链接，没有则只能搜索不能获取下载链接',
                            'persistent-hint': True,
                            'clearable': True,
                            'type': 'password'
                            }
                        }
                        ]
                    }
                    ]
                },
                {
                    'component': 'VRow',
                    'content': [
                    {
                        'component': 'VCol',
                        'props': {'cols': 12},
                        'content': [
                        {
                            'component': 'VExpansionPanels',
                            'content': [
                            {
                                'component': 'VExpansionPanel',
                                'props': {'title': '⚙️ 高级设置'},
                                'content': [
                                {
                                    'component': 'VExpansionPanelText',
                                    'content': [
                                    {
                                        'component': 'VRow',
                                        'content': [
                                        {
                                            'component': 'VCol',
                                            'props': {'cols': 12, 'md': 3},
                                            'content': [
                                            {
                                                'component': 'VSwitch',
                                                'props': {
                                                'model': 'enable_115',
                                                'label': '115网盘',
                                                'hint': '搜索115网盘分享资源',
                                                'persistent-hint': True
                                                }
                                            }
                                            ]
                                        },
                                        {
                                            'component': 'VCol',
                                            'props': {'cols': 12, 'md': 3},
                                            'content': [
                                            {
                                                'component': 'VSwitch',
                                                'props': {
                                                'model': 'enable_magnet',
                                                'label': '磁力链接',
                                                'hint': '搜索磁力链接资源',
                                                'persistent-hint': True
                                                }
                                            }
                                            ]
                                        },
                                        {
                                            'component': 'VCol',
                                            'props': {'cols': 12, 'md': 3},
                                            'content': [
                                            {
                                                'component': 'VSwitch',
                                                'props': {
                                                'model': 'enable_video',
                                                'label': 'M3U8视频',
                                                'hint': '搜索在线观看资源',
                                                'persistent-hint': True
                                                }
                                            }
                                            ]
                                        },
                                        {
                                            'component': 'VCol',
                                            'props': {'cols': 12, 'md': 3},
                                            'content': [
                                            {
                                                'component': 'VSwitch',
                                                'props': {
                                                'model': 'enable_ed2k',
                                                'label': 'ED2K链接',
                                                'hint': '搜索ED2K链接资源',
                                                'persistent-hint': True
                                                }
                                            }
                                            ]
                                        }
                                        ]
                                    },
                                    {
                                        'component': 'VRow',
                                        'content': [
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12},
                                                'content': [
                                                    {
                                                        'component': 'VAlert',
                                                        'props': {
                                                            'type': 'info',
                                                            'variant': 'tonal'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'span',
                                                                'text': '🎯 资源优先级设置 - 自动按优先级获取资源（可拖拽排序）'
                                                            }
                                                        ]
                                                    }
                                                ]
                                            }
                                        ]
                                    },
                                    {
                                        'component': 'VRow',
                                        'content': [
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'md': 6},
                                                'content': [
                                                    {
                                                        'component': 'VSelect',
                                                        'props': {
                                                            'model': 'priority_1',
                                                            'label': '第一优先级',
                                                            'items': [
                                                                {'title': '115网盘', 'value': '115'},
                                                                {'title': '磁力链接', 'value': 'magnet'},
                                                                {'title': 'ED2K链接', 'value': 'ed2k'},
                                                                {'title': 'M3U8视频', 'value': 'video'}
                                                            ],
                                                            'hint': '优先获取的资源类型',
                                                            'persistent-hint': True
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'md': 6},
                                                'content': [
                                                    {
                                                        'component': 'VSelect',
                                                        'props': {
                                                            'model': 'priority_2',
                                                            'label': '第二优先级',
                                                            'items': [
                                                                {'title': '115网盘', 'value': '115'},
                                                                {'title': '磁力链接', 'value': 'magnet'},
                                                                {'title': 'ED2K链接', 'value': 'ed2k'},
                                                                {'title': 'M3U8视频', 'value': 'video'}
                                                            ],
                                                            'hint': '第二选择的资源类型',
                                                            'persistent-hint': True
                                                        }
                                                    }
                                                ]
                                            }
                                        ]
                                    },
                                    {
                                        'component': 'VRow',
                                        'content': [
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'md': 6},
                                                'content': [
                                                    {
                                                        'component': 'VSelect',
                                                        'props': {
                                                            'model': 'priority_3',
                                                            'label': '第三优先级',
                                                            'items': [
                                                                {'title': '115网盘', 'value': '115'},
                                                                {'title': '磁力链接', 'value': 'magnet'},
                                                                {'title': 'ED2K链接', 'value': 'ed2k'},
                                                                {'title': 'M3U8视频', 'value': 'video'}
                                                            ],
                                                            'hint': '第三选择的资源类型',
                                                            'persistent-hint': True
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'md': 6},
                                                'content': [
                                                    {
                                                        'component': 'VSelect',
                                                        'props': {
                                                            'model': 'priority_4',
                                                            'label': '第四优先级',
                                                            'items': [
                                                                {'title': '115网盘', 'value': '115'},
                                                                {'title': '磁力链接', 'value': 'magnet'},
                                                                {'title': 'ED2K链接', 'value': 'ed2k'},
                                                                {'title': 'M3U8视频', 'value': 'video'}
                                                            ],
                                                            'hint': '最后选择的资源类型',
                                                            'persistent-hint': True
                                                        }
                                                    }
                                                ]
                                            }
                                        ]
                                    },
                                    {
                                        'component': 'VRow',
                                        'content': [
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12},
                                                'content': [
                                                    {
                                                        'component': 'VAlert',
                                                        'props': {
                                                            'type': 'info',
                                                            'variant': 'tonal'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'span',
                                                                'text': '🚀 CloudDrive2配置 - 支持115转存和磁力/ED2K离线下载'
                                                            }
                                                        ]
                                                    }
                                                ]
                                            }
                                        ]
                                    },
                                    {
                                        'component': 'VRow',
                                        'content': [
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'md': 6},
                                                'content': [
                                                    {
                                                        'component': 'VSwitch',
                                                        'props': {
                                                            'model': 'cd2_enabled',
                                                            'label': '启用CloudDrive2',
                                                            'hint': '开启后支持115转存和磁力/ED2K离线下载',
                                                            'persistent-hint': True
                                                        }
                                                    }
                                                ]
                                            }
                                        ]
                                    },
                                    {
                                        'component': 'VRow',
                                        'content': [
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'md': 6},
                                                'content': [
                                                    {
                                                        'component': 'VTextField',
                                                        'props': {
                                                            'model': 'cd2_url',
                                                            'label': 'CloudDrive2地址',
                                                            'placeholder': 'http://localhost:19798',
                                                            'hint': 'CloudDrive2服务器地址',
                                                            'persistent-hint': True
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'md': 6},
                                                'content': [
                                                    {
                                                        'component': 'VTextField',
                                                        'props': {
                                                            'model': 'cd2_api_token',
                                                            'label': 'API Token（推荐）',
                                                            'placeholder': '在CD2设置中生成的API Token',
                                                            'hint': '推荐: 永久有效，无需续期',
                                                            'persistent-hint': True,
                                                            'type': 'password'
                                                        }
                                                    }
                                                ]
                                            }
                                        ]
                                    },
                                    {
                                        'component': 'VRow',
                                        'content': [
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'md': 6},
                                                'content': [
                                                    {
                                                        'component': 'VTextField',
                                                        'props': {
                                                            'model': 'cd2_username',
                                                            'label': 'CD2用户名（备选）',
                                                            'placeholder': 'API Token为空时使用',
                                                            'hint': '备选: 无API Token时填写',
                                                            'persistent-hint': True
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'md': 6},
                                                'content': [
                                                    {
                                                        'component': 'VTextField',
                                                        'props': {
                                                            'model': 'cd2_password',
                                                            'label': 'CD2密码（备选）',
                                                            'placeholder': 'API Token为空时使用',
                                                            'hint': '备选: 无API Token时填写',
                                                            'persistent-hint': True,
                                                            'type': 'password'
                                                        }
                                                    }
                                                ]
                                            }
                                        ]
                                    },
                                    {
                                        'component': 'VRow',
                                        'content': [
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'md': 6},
                                                'content': [
                                                    {
                                                        'component': 'VTextField',
                                                        'props': {
                                                            'model': 'search_timeout',
                                                            'label': '搜索超时时间(秒)',
                                                            'placeholder': '30',
                                                            'hint': '单次API请求的超时时间',
                                                            'persistent-hint': True,
                                                            'type': 'number',
                                                            'min': 10,
                                                            'max': 120
                                                        }
                                                    }
                                                ]
                                            }
                                        ]
                                    },
                                    {
                                        'component': 'VRow',
                                        'content': [
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'md': 6},
                                                'content': [
                                                    {
                                                        'component': 'VTextField',
                                                        'props': {
                                                            'model': 'cd2_save_path',
                                                            'label': '115转存路径',
                                                            'placeholder': '/115/Downloads',
                                                            'hint': '115分享链接转存的目标路径',
                                                            'persistent-hint': True
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'md': 6},
                                                'content': [
                                                    {
                                                        'component': 'VTextField',
                                                        'props': {
                                                            'model': 'cd2_offline_path',
                                                            'label': '离线任务路径',
                                                            'placeholder': '/115/Offline',
                                                            'hint': '磁力/ED2K离线任务的保存路径',
                                                            'persistent-hint': True
                                                        }
                                                    }
                                                ]
                                            }
                                        ]
                                    },
                                    {
                                        'component': 'VRow',
                                        'content': [
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12},
                                                'content': [
                                                    {
                                                        'component': 'VAlert',
                                                        'props': {
                                                            'type': 'warning',
                                                            'variant': 'tonal'
                                                        },
                                                        'content': [
                                                            {
                                                                'component': 'span',
                                                                'text': '🔄 115分享链接转存配置 - 使用Cookie直接调用115 API（推荐）'
                                                            }
                                                        ]
                                                    }
                                                ]
                                            }
                                        ]
                                    },
                                    {
                                        'component': 'VRow',
                                        'content': [
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'md': 4},
                                                'content': [
                                                    {
                                                        'component': 'VSwitch',
                                                        'props': {
                                                            'model': 'p115_enabled',
                                                            'label': '启用115转存',
                                                            'hint': '开启后支持115分享链接转存',
                                                            'persistent-hint': True
                                                        }
                                                    }
                                                ]
                                            },
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12, 'md': 4},
                                                'content': [
                                                    {
                                                        'component': 'VTextField',
                                                        'props': {
                                                            'model': 'p115_save_cid',
                                                            'label': '转存目录CID',
                                                            'placeholder': '0',
                                                            'hint': '0表示根目录，可在浏览器URL中获取',
                                                            'persistent-hint': True
                                                        }
                                                    }
                                                ]
                                            }
                                        ]
                                    },
                                    {
                                        'component': 'VRow',
                                        'content': [
                                            {
                                                'component': 'VCol',
                                                'props': {'cols': 12},
                                                'content': [
                                                    {
                                                        'component': 'VTextarea',
                                                        'props': {
                                                            'model': 'p115_cookies',
                                                            'label': '115 Cookie',
                                                            'placeholder': 'UID=xxx; CID=xxx; SEID=xxx; KID=xxx',
                                                            'hint': '从浏览器开发者工具获取，格式: UID=xxx; CID=xxx; SEID=xxx',
                                                            'persistent-hint': True,
                                                            'rows': 2
                                                        }
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                    ]
                                }
                                ]
                            }
                            ]
                        }
                        ]
                    }
                    ]
                }
            ]
        }
        ], {
        "enabled": False,
        "app_id": "",
        "api_key": "",
        "enable_115": True,
        "enable_magnet": True,
        "enable_video": True,
        "enable_ed2k": True,
        "priority_1": "115",
        "priority_2": "magnet",
        "priority_3": "ed2k",
        "priority_4": "video",
        "cd2_enabled": False,
        "cd2_url": "",
        "cd2_api_token": "",
        "cd2_username": "",
        "cd2_password": "",
        "cd2_save_path": "/115/Downloads",
        "cd2_offline_path": "/115/Offline",
        "search_timeout": 30,
        "p115_enabled": False,
        "p115_cookies": "",
        "p115_save_cid": "0"
        }

    def get_page(self) -> List[dict]:
        """
        拼装插件详情页面，需要返回页面配置，同时附带数据
        插件详情页面使用Vuetify组件拼装，参考：https://vuetifyjs.com/

        :return: 页面配置（vuetify模式）或 None（vue模式）
        """
        pass

    @eventmanager.register(EventType.UserMessage)
    def talk(self, event: Event):
        """
        监听用户消息，识别搜索请求和编号选择
        """
        if not self._enabled:
            return
        
        # 第3步测试阶段：即使没有client也要响应，用于测试交互逻辑
        if not self._client:
            logger.info("API客户端未初始化，但继续处理用户消息进行测试")
            
        text = event.event_data.get("text")
        userid = event.event_data.get("userid")
        channel = event.event_data.get("channel")
        
        if not text:
            return
            
        logger.info(f"收到用户消息: {text}")
        
        # 检查是否为回退搜索触发的消息，避免无限循环
        if event.event_data.get('source') == 'nullbr_fallback':
            logger.info("检测到回退搜索消息，跳过处理避免循环")
            return
        
        # 先检查是否为获取资源的请求（包含问号的情况，如 "1.115?" "2.magnet?"）
        clean_text = text.rstrip('？?').strip()
        if re.match(r'^\d+\.(115|magnet|video|ed2k)$', clean_text):
            parts = clean_text.split('.')
            number = int(parts[0])
            resource_type = parts[1]
            logger.info(f"检测到资源获取请求: {number}.{resource_type}")
            self.handle_get_resources(number, resource_type, channel, userid)
        
        # 检查是否为编号选择（纯数字，包含问号的情况）
        elif clean_text.isdigit():
            number = int(clean_text)
            
            # 先检查是否有资源缓存（直接进行转存）
            if userid in self._user_resource_cache:
                cache = self._user_resource_cache[userid]
                if time.time() - cache['timestamp'] < 3600:  # 1小时内有效
                    if 1 <= number <= len(cache['resources']):
                        if self._cd2_enabled and self._cd2_client:
                            logger.info(f"检测到资源转存请求: {number}")
                            self.handle_resource_transfer(number, channel, userid)
                        else:
                            # 有资源缓存但CD2未启用，显示资源详情和提示
                            selected_resource = cache['resources'][number - 1]
                            resource_detail = f"🎯 选择的资源:\n\n"
                            resource_detail += f"🎬 影片: 「{cache['title']}」\n"
                            resource_detail += f"📂 名称: {selected_resource['title']}\n"
                            resource_detail += f"💾 大小: {selected_resource['size']}\n"
                            resource_detail += f"🔗 链接: {selected_resource['url']}\n"
                            resource_detail += f"{'─' * 15}\n"
                            resource_detail += f"💡 CloudDrive2转存功能未启用\n"
                            resource_detail += f"⚙️ 如需转存功能，请在插件设置中配置CloudDrive2"
                            
                            self.post_message(
                                channel=channel,
                                title="资源详情",
                                text=resource_detail,
                                userid=userid
                            )
                        return
                    else:
                        # 数字超出资源范围，提示用户
                        self.post_message(
                            channel=channel,
                            title="编号错误",
                            text=f"请输入有效的资源编号 (1-{len(cache['resources'])})。",
                            userid=userid
                        )
                        return
            
            # 如果没有资源缓存，检查是否有搜索结果缓存
            logger.info(f"检测到编号选择: {number}")
            self.handle_resource_selection(number, channel, userid)
        
        # 检查是否为搜索请求（以？结尾，但不是数字或资源请求）
        elif text.endswith('？') or text.endswith('?'):
            # 提取搜索关键词（去掉问号）
            keyword = clean_text
            
            if keyword:
                logger.info(f"检测到搜索请求: {keyword}")
                self.search_and_reply(keyword, channel, userid)

    def search_and_reply(self, keyword: str, channel: str, userid: str):
        """执行搜索并回复结果"""
        try:
            # 更新搜索统计
            self._stats['total_searches'] += 1
            self._stats['last_search_time'] = time.time()
            
            # 更新热门搜索统计
            if keyword in self._stats['popular_resources']:
                self._stats['popular_resources'][keyword] += 1
            else:
                self._stats['popular_resources'][keyword] = 1
            
            # 检查API客户端是否可用
            if not self._client:
                logger.warning("API客户端未初始化，无法搜索")
                self._stats['failed_searches'] += 1
                self.post_message(
                    channel=channel,
                    title="配置错误",
                    text="❌ API客户端未初始化\n\n请检查插件配置中的APP_ID设置",
                    userid=userid
                )
                return
            
            # 调用Nullbr API搜索
            result = self._client.search(keyword)
            
            if not result or not result.get('items'):
                # Nullbr没有搜索结果，回退到MoviePilot原始搜索
                logger.info(f"Nullbr未找到「{keyword}」的搜索结果，回退到MoviePilot搜索")
                self._stats['failed_searches'] += 1
                self.post_message(
                    channel=channel,
                    title="切换搜索",
                    text=f"Nullbr没有找到「{keyword}」的资源，正在使用MoviePilot原始搜索...",
                    userid=userid
                )
                
                self.fallback_to_moviepilot_search(keyword, channel, userid)
                return
            
            # 搜索成功，更新统计
            self._stats['successful_searches'] += 1
            
            # 清理之前的缓存（重要：避免缓存混乱）
            if userid in self._user_resource_cache:
                logger.info(f"清理用户 {userid} 的旧资源缓存")
                del self._user_resource_cache[userid]
            
            # 缓存搜索结果
            self._user_search_cache[userid] = {
                'results': result.get('items', []),
                'timestamp': time.time()
            }
            
            # 构建回复消息
            reply_text = f"🎬 找到 {len(result.get('items', []))} 个「{keyword}」相关资源:\n\n"
            
            # 显示前10个结果
            for i, item in enumerate(result.get('items', [])[:10], 1):
                title = item.get('title', '未知标题')
                year = item.get('release_date', item.get('first_air_date', ''))[:4] if item.get('release_date') or item.get('first_air_date') else ''
                media_type = '电影' if item.get('media_type') == 'movie' else '剧集' if item.get('media_type') == 'tv' else item.get('media_type', '未知')
                
                reply_text += f"【{i}】{title}"
                if year:
                    reply_text += f" ({year})"
                reply_text += f"\n🎭 类型: {media_type}\n"
                
                # 显示可用的资源类型标记
                resource_flags = []
                if item.get('115-flg') and self._enable_115:
                    resource_flags.append('💾115')
                if item.get('magnet-flg') and self._enable_magnet:
                    resource_flags.append('🧲磁力')
                if item.get('video-flg') and self._enable_video:
                    resource_flags.append('🎬在线')
                if item.get('ed2k-flg') and self._enable_ed2k:
                    resource_flags.append('📎ed2k')
                
                if resource_flags:
                    reply_text += f"📂 资源: {' | '.join(resource_flags)}\n"
                reply_text += f"{'─' * 15}\n"
            
            # 如果结果超过10个，显示提示
            if len(result.get('items', [])) > 10:
                reply_text += f"... 还有 {len(result.get('items', [])) - 10} 个结果\n\n"
            
            if self._api_key:
                reply_text += "📋 使用方法:\n"
                reply_text += f"• 发送数字自动获取资源: 如 \"1\" (优先级: {' > '.join(self._resource_priority)})\n" 
                reply_text += "• 手动指定资源类型: 如 \"1.115\" \"2.magnet\" (可选)"
            else:
                reply_text += "💡 提示: 请配置API_KEY以获取下载链接"
            
            self.post_message(
                channel=channel,
                title="Nullbr搜索结果",
                text=reply_text,
                userid=userid
            )
            
            
        except Exception as e:
            logger.error(f"搜索处理异常: {str(e)}")
            self.post_message(
                channel=channel,
                title="搜索错误",
                text=f"搜索「{keyword}」时出现错误: {str(e)}",
                userid=userid
            )

    def handle_resource_selection(self, number: int, channel: str, userid: str):
        """处理用户的编号选择"""
        try:
            # 检查缓存
            cache = self._user_search_cache.get(userid)
            if not cache or time.time() - cache['timestamp'] > 3600:  # 缓存1小时
                self.post_message(
                    channel=channel,
                    title="提示",
                    text="搜索结果已过期，请重新搜索。",
                    userid=userid
                )
                return
            
            results = cache['results']
            if number < 1 or number > len(results):
                self.post_message(
                    channel=channel,
                    title="提示",
                    text=f"请输入有效的编号 (1-{len(results)})。",
                    userid=userid
                )
                return
            
            # 获取选中的项目
            selected = results[number - 1]
            title = selected.get('title', '未知标题')
            media_type = selected.get('media_type', 'unknown')
            year = selected.get('release_date', selected.get('first_air_date', ''))[:4] if selected.get('release_date') or selected.get('first_air_date') else ''
            tmdbid = selected.get('tmdbid')
            
            if not self._api_key:
                # 如果没有API_KEY，显示详细信息
                reply_text = f"📺 选择的资源: {title}"
                if year:
                    reply_text += f" ({year})"
                reply_text += f"\n类型: {'电影' if media_type == 'movie' else '剧集' if media_type == 'tv' else media_type}"
                reply_text += f"\nTMDB ID: {tmdbid}"
                
                if selected.get('overview'):
                    reply_text += f"\n简介: {selected.get('overview')[:100]}..."
                
                # 显示可用的资源类型
                reply_text += f"\n\n🔗 可用资源类型:"
                resource_options = []
                
                if selected.get('115-flg') and self._enable_115:
                    resource_options.append(f"• 115网盘")
                if selected.get('magnet-flg') and self._enable_magnet:
                    resource_options.append(f"• 磁力链接")
                if selected.get('video-flg') and self._enable_video:
                    resource_options.append(f"• 在线观看")
                if selected.get('ed2k-flg') and self._enable_ed2k:
                    resource_options.append(f"• ED2K链接")
                
                if resource_options:
                    reply_text += f"\n" + "\n".join(resource_options)
                    reply_text += "\n\n⚠️ 注意: 需要配置API_KEY才能获取具体下载链接"
                else:
                    reply_text += f"\n暂无可用资源类型"
                
                self.post_message(
                    channel=channel,
                    title="资源详情",
                    text=reply_text,
                    userid=userid
                )
            else:
                # 清理之前的资源缓存（重要：避免缓存混乱）
                if userid in self._user_resource_cache:
                    logger.info(f"清理用户 {userid} 的旧资源缓存")
                    del self._user_resource_cache[userid]
                
                # 如果有API_KEY，直接按优先级获取资源
                self.post_message(
                    channel=channel,
                    title="获取中",
                    text=f"正在按优先级获取「{title}」的资源...",
                    userid=userid
                )
                
                self.get_resources_by_priority(selected, channel, userid)
            
        except Exception as e:
            logger.error(f"处理资源选择异常: {str(e)}")
            self.post_message(
                channel=channel,
                title="错误",
                text=f"处理选择时出现错误: {str(e)}",
                userid=userid
            )

    def handle_get_resources(self, number: int, resource_type: str, channel: str, userid: str):
        """处理获取具体资源链接的请求"""
        try:
            # 检查API_KEY
            if not self._api_key:
                self.post_message(
                    channel=channel,
                    title="配置错误",
                    text="获取下载链接需要配置API_KEY，请在插件设置中添加。",
                    userid=userid
                )
                return
            
            # 检查缓存
            cache = self._user_search_cache.get(userid)
            if not cache or time.time() - cache['timestamp'] > 3600:
                self.post_message(
                    channel=channel,
                    title="提示",
                    text="搜索结果已过期，请重新搜索。",
                    userid=userid
                )
                return
            
            results = cache['results']
            if number < 1 or number > len(results):
                self.post_message(
                    channel=channel,
                    title="提示", 
                    text=f"请输入有效的编号 (1-{len(results)})。",
                    userid=userid
                )
                return
            
            # 获取选中的项目
            selected = results[number - 1]
            title = selected.get('title', '未知标题')
            media_type = selected.get('media_type', 'unknown')
            tmdbid = selected.get('tmdbid')
            
            if not tmdbid:
                self.post_message(
                    channel=channel,
                    title="错误",
                    text="该资源缺少TMDB ID，无法获取下载链接。",
                    userid=userid
                )
                return
            
            # 清理之前的资源缓存（重要：避免缓存混乱）
            if userid in self._user_resource_cache:
                logger.info(f"清理用户 {userid} 的旧资源缓存")
                del self._user_resource_cache[userid]
            
            # 发送获取中的提示
            self.post_message(
                channel=channel,
                title="获取中",
                text=f"正在获取「{title}」的{resource_type}资源...",
                userid=userid
            )
            
            # 调用相应的API获取资源
            resources = None
            if media_type == 'movie':
                resources = self._client.get_movie_resources(tmdbid, resource_type)
            elif media_type == 'tv':
                resources = self._client.get_tv_resources(tmdbid, resource_type)
            
            if not resources:
                # Nullbr没有找到资源，回退到MoviePilot原始搜索
                logger.info(f"Nullbr未找到「{title}」的{resource_type}资源，回退到MoviePilot搜索")
                self.post_message(
                    channel=channel,
                    title="切换搜索",
                    text=f"Nullbr没有找到「{title}」的{resource_type}资源，正在使用MoviePilot原始搜索...",
                    userid=userid
                )
                
                # 调用MoviePilot的原始搜索功能
                self.fallback_to_moviepilot_search(title, channel, userid)
                return
            
            # 格式化资源链接（第4步完善）
            self.format_and_send_resources(resources, resource_type, title, channel, userid)
            
        except Exception as e:
            logger.error(f"获取资源链接异常: {str(e)}")
            self.post_message(
                channel=channel,
                title="错误",
                text=f"获取资源链接时出现错误: {str(e)}",
                userid=userid
            )

    def get_resources_by_priority(self, selected: dict, channel: str, userid: str):
        """按优先级获取资源"""
        try:
            title = selected.get('title', '未知标题')
            media_type = selected.get('media_type', 'unknown')
            tmdbid = selected.get('tmdbid')
            
            if not tmdbid:
                self.post_message(
                    channel=channel,
                    title="错误",
                    text="该资源缺少TMDB ID，无法获取下载链接。",
                    userid=userid
                )
                return
            
            # 清理之前的资源缓存（重要：避免缓存混乱）
            if userid in self._user_resource_cache:
                logger.info(f"清理用户 {userid} 的旧资源缓存")
                del self._user_resource_cache[userid]
            
            logger.info(f"按优先级获取资源: {title} (TMDB: {tmdbid})")
            logger.info(f"优先级顺序: {' > '.join(self._resource_priority)}")
            
            # 按优先级尝试获取资源
            for priority_type in self._resource_priority:
                # 检查该资源类型是否可用
                flag_key = f"{priority_type}-flg"
                if not selected.get(flag_key):
                    logger.info(f"跳过 {priority_type}: 资源不可用")
                    continue
                
                # 检查该资源类型是否启用
                enable_key = f"_enable_{priority_type}"
                if not getattr(self, enable_key, True):
                    logger.info(f"跳过 {priority_type}: 已在配置中禁用")
                    continue
                
                logger.info(f"尝试获取 {priority_type} 资源...")
                
                # 调用相应的API获取资源
                resources = None
                if media_type == 'movie':
                    resources = self._client.get_movie_resources(tmdbid, priority_type)
                elif media_type == 'tv':
                    resources = self._client.get_tv_resources(tmdbid, priority_type)
                
                if resources and resources.get(priority_type):
                    # 找到资源，发送结果并结束
                    resource_name = {
                        '115': '115网盘',
                        'magnet': '磁力链接', 
                        'ed2k': 'ED2K链接',
                        'video': 'M3U8视频'
                    }.get(priority_type, priority_type)
                    
                    logger.info(f"成功获取 {priority_type} 资源，共 {len(resources[priority_type])} 个")
                    
                    self.post_message(
                        channel=channel,
                        title="获取成功",
                        text=f"✅ 已获取「{title}」的{resource_name}资源",
                        userid=userid
                    )
                    
                    # 格式化并发送资源链接
                    self.format_and_send_resources(resources, priority_type, title, channel, userid)
                    return
                else:
                    logger.info(f"{priority_type} 资源不可用，尝试下一优先级")
            
            # 所有优先级都没有找到资源，回退到MoviePilot搜索
            logger.info(f"所有优先级资源都不可用，回退到MoviePilot搜索")
            self.post_message(
                channel=channel,
                title="切换搜索",
                text=f"Nullbr没有找到「{title}」的任何资源，正在使用MoviePilot原始搜索...",
                userid=userid
            )
            
            self.fallback_to_moviepilot_search(title, channel, userid)
            
        except Exception as e:
            logger.error(f"按优先级获取资源异常: {str(e)}")
            self.post_message(
                channel=channel,
                title="错误",
                text=f"获取资源时出现错误: {str(e)}",
                userid=userid
            )

    def handle_resource_transfer(self, resource_id: int, channel: str, userid: str):
        """处理资源转存/离线请求
        
        资源处理策略：
        - 115分享链接: 优先使用 p115client (Cookie认证)
        - 磁力/ED2K: 使用 CloudDrive2 (gRPC)
        """
        try:
            # 获取用户资源缓存
            cache = self._user_resource_cache.get(userid)
            if not cache or time.time() - cache['timestamp'] > 3600:
                self.post_message(
                    channel=channel,
                    title="缓存过期",
                    text="资源缓存已过期，请重新获取资源后再试。",
                    userid=userid
                )
                return
            
            resources = cache['resources']
            title = cache['title']
            resource_type = cache['resource_type']
            
            if resource_id < 1 or resource_id > len(resources):
                self.post_message(
                    channel=channel,
                    title="编号错误",
                    text=f"请输入有效的资源编号 (1-{len(resources)})。",
                    userid=userid
                )
                return
            
            # 获取要处理的资源
            selected_resource = resources[resource_id - 1]
            resource_url = selected_resource['url']
            resource_title = selected_resource['title']
            resource_size = selected_resource['size']
            
            # 根据资源类型选择处理方式
            if resource_type == "115":
                # 115分享链接转存 - 使用 p115client
                self._handle_115_transfer(
                    resource_url, resource_title, resource_size, 
                    title, channel, userid
                )
                
            elif resource_type in ["magnet", "ed2k"]:
                # 磁力/ED2K离线任务 - 使用 CloudDrive2
                self._handle_offline_task(
                    resource_url, resource_title, resource_size,
                    resource_type, title, channel, userid
                )
                
            else:
                # 不支持的资源类型
                self.post_message(
                    channel=channel,
                    title="不支持的操作",
                    text=f"❌ 暂不支持{resource_type}类型资源的转存/离线操作\n\n"
                         f"💡 支持的类型: 115网盘、磁力链接、ED2K链接",
                    userid=userid
                )
            
        except Exception as e:
            logger.error(f"资源处理异常: {str(e)}")
            self.post_message(
                channel=channel,
                title="处理错误",
                text=f"❌ 处理过程中发生错误:\n\n{str(e)}\n\n💡 请检查配置和网络连接",
                userid=userid
            )
    
    def _handle_115_transfer(self, resource_url: str, resource_title: str, 
                             resource_size: str, title: str, channel: str, userid: str):
        """处理 115 分享链接转存 - 使用 p115client"""
        
        # 检查 p115client 是否可用
        if not self._p115_client:
            # 如果 p115client 不可用，尝试回退到 CloudDrive2
            if self._cd2_enabled and self._cd2_client:
                logger.warning("p115client 不可用，尝试使用 CloudDrive2")
                try:
                    self.post_message(
                        channel=channel,
                        title="转存中",
                        text=f"🚀 正在转存「{title}」中的资源:\n\n"
                             f"📁 {resource_title}\n"
                             f"📊 大小: {resource_size}\n\n"
                             f"⏳ 使用 CloudDrive2 处理中...",
                        userid=userid
                    )
                    
                    result = self._cd2_client.add_shared_link(
                        share_url=resource_url,
                        to_folder=self._cd2_save_path
                    )
                    self._handle_cd2_result(result, title, resource_title, resource_size, "转存", channel, userid)
                    return
                except Exception as e:
                    error_msg = str(e)
                    if "not supported" in error_msg.lower() or "115open" in error_msg.lower():
                        self.post_message(
                            channel=channel,
                            title="功能不支持",
                            text="❌ CloudDrive2 的 115open 不支持分享链接转存\n\n"
                                 "💡 请在插件设置中配置 **115 Cookie** 以启用分享链接转存功能",
                            userid=userid
                        )
                    else:
                        raise
                    return
            
            # 都不可用
            self.post_message(
                channel=channel,
                title="功能未启用",
                text="❌ 115 分享链接转存功能未启用\n\n"
                     "💡 请在插件设置中配置 **115 Cookie** 以启用此功能",
                userid=userid
            )
            return
        
        # 使用 p115client 转存
        logger.info(f"开始115转存: 用户={userid}, 资源={resource_title}, URL={resource_url}")
        
        self._stats['cd2_transfers'] += 1
        self._stats['last_transfer_time'] = time.time()
        
        self.post_message(
            channel=channel,
            title="转存中",
            text=f"🚀 正在转存「{title}」中的资源:\n\n"
                 f"📁 {resource_title}\n"
                 f"📊 大小: {resource_size}\n\n"
                 f"⏳ 使用 p115client 处理中...",
            userid=userid
        )
        
        try:
            result = self._p115_client.save_share_link(
                share_url=resource_url,
                to_folder_cid=self._p115_save_cid
            )
            
            # 转存成功
            self.post_message(
                channel=channel,
                title="✅ 转存成功",
                text=f"🎉 「{title}」资源转存成功!\n\n"
                     f"📁 {resource_title}\n"
                     f"📊 大小: {resource_size}\n"
                     f"📂 保存位置: 115网盘 (CID: {self._p115_save_cid})\n\n"
                     f"💡 {result.get('message', '')}",
                userid=userid
            )
            
        except ValueError as e:
            # 业务错误（链接过期、密码错误等）
            self.post_message(
                channel=channel,
                title="转存失败",
                text=f"❌ 转存失败: {str(e)}\n\n"
                     f"📁 {resource_title}",
                userid=userid
            )
        except Exception as e:
            logger.error(f"115 转存异常: {str(e)}")
            raise
    
    def _handle_offline_task(self, resource_url: str, resource_title: str,
                             resource_size: str, resource_type: str, 
                             title: str, channel: str, userid: str):
        """处理磁力/ED2K 离线任务 - 使用 CloudDrive2"""
        
        # 检查 CloudDrive2 是否可用
        if not self._cd2_enabled or not self._cd2_client:
            self.post_message(
                channel=channel,
                title="功能未启用",
                text="❌ CloudDrive2 离线功能未启用\n\n"
                     "💡 请在插件设置中配置 CloudDrive2 以使用磁力/ED2K离线功能",
                userid=userid
            )
            return
        
        task_type = "磁力" if resource_type == "magnet" else "ED2K"
        logger.info(f"开始离线: 用户={userid}, 资源={resource_title}, 类型={resource_type}")
        
        self._stats['cd2_offline'] += 1
        self._stats['last_transfer_time'] = time.time()
        
        self.post_message(
            channel=channel,
            title="添加离线任务",
            text=f"🚀 正在添加「{title}」的{task_type}离线任务:\n\n"
                 f"📁 {resource_title}\n"
                 f"📊 大小: {resource_size}\n\n"
                 f"⏳ 请稍等，正在处理中...",
            userid=userid
        )
        
        # 调用 CloudDrive2 API 添加离线任务
        result = self._cd2_client.add_offline_files(
            urls=resource_url,
            to_folder=self._cd2_offline_path
        )
        
        # 处理离线结果
        self._handle_cd2_result(result, title, resource_title, resource_size, f"{task_type}离线", channel, userid)
    
    def _handle_cd2_result(self, result: dict, title: str, resource_title: str, 
                           resource_size: str, action_type: str, channel: str, userid: str):
        """处理CloudDrive2 API返回结果"""
        try:
            # CloudDrive2 API 成功通常直接返回结果，失败会抛出异常
            # 这里简化处理，如果没有异常就认为成功
            self._stats['successful_transfers'] += 1
            
            success_msg = f"✅ {action_type}任务已添加!\n"
            success_msg += f"{'─' * 15}\n"
            success_msg += f"🎬 影片: 「{title}」\n"
            success_msg += f"📁 资源: {resource_title}\n"
            success_msg += f"📊 大小: {resource_size}\n"
            success_msg += f"{'─' * 15}\n"
            success_msg += "💡 可在CloudDrive2管理界面查看任务进度"
            
            self.post_message(
                channel=channel,
                title=f"{action_type}成功",
                text=success_msg,
                userid=userid
            )
            
            logger.info(f"CD2 {action_type}成功: {resource_title}")
            
        except Exception as e:
            # 处理失败
            self._stats['failed_transfers'] += 1
            
            failure_msg = f"❌ {action_type}失败\n"
            failure_msg += f"{'─' * 15}\n"
            failure_msg += f"📁 资源: {resource_title}\n"
            failure_msg += f"🚨 错误: {str(e)}\n"
            failure_msg += f"{'─' * 15}\n"
            failure_msg += "💡 请检查CloudDrive2服务状态"
            
            self.post_message(
                channel=channel,
                title=f"{action_type}失败",
                text=failure_msg,
                userid=userid
            )
            
            logger.warning(f"CD2 {action_type}失败: {resource_title} -> {str(e)}")

    def format_and_send_resources(self, resources: dict, resource_type: str, title: str, channel: str, userid: str):
        """格式化并发送资源链接"""
        try:
            resource_list = resources.get(resource_type, [])
            if not resource_list:
                self.post_message(
                    channel=channel,
                    title="无资源",
                    text=f"没有找到「{title}」的{resource_type}资源。",
                    userid=userid
                )
                return
            
            # 更新资源统计
            self._stats['total_resources'] += len(resource_list)
            
            # 缓存资源到用户缓存中，用于CMS转存
            resource_cache = []
            for res in resource_list[:10]:  # 最多缓存10个
                if resource_type == "115":
                    url = res.get('share_link', '')
                elif resource_type == "magnet":
                    url = res.get('magnet', '')
                elif resource_type in ["video", "ed2k"]:
                    url = res.get('url', res.get('link', ''))
                else:
                    url = ''
                
                if url:
                    resource_cache.append({
                        'url': url,
                        'title': res.get('title', res.get('name', '未知')),
                        'size': res.get('size', '未知'),
                        'type': resource_type
                    })
            
            # 保存到用户资源缓存
            self._user_resource_cache[userid] = {
                'resources': resource_cache,
                'title': title,
                'resource_type': resource_type,
                'timestamp': time.time()
            }
            
            # 格式化显示文本
            reply_text = f"🎯 「{title}」的{resource_type}资源:\n\n"
            
            if resource_type == "115":
                for i, res in enumerate(resource_list[:10], 1):
                    reply_text += f"【{i}】{res.get('title', '未知')}\n"
                    reply_text += f"💾 大小: {res.get('size', '未知')}\n"
                    reply_text += f"🔗 链接: {res.get('share_link', '无')}\n"
                    reply_text += f"{'─' * 15}\n"
                    
            elif resource_type == "magnet":
                for i, res in enumerate(resource_list[:10], 1):
                    reply_text += f"【{i}】{res.get('name', '未知')}\n"
                    reply_text += f"💾 大小: {res.get('size', '未知')}\n"
                    reply_text += f"📺 分辨率: {res.get('resolution', '未知')}\n"
                    reply_text += f"🈴 中文字幕: {'✅' if res.get('zh_sub') else '❌'}\n"
                    reply_text += f"🧲 磁力: {res.get('magnet', '无')}\n"
                    reply_text += f"{'─' * 15}\n"
                    
            elif resource_type in ["video", "ed2k"]:
                for i, res in enumerate(resource_list[:10], 1):
                    reply_text += f"【{i}】{res.get('name', res.get('title', '未知'))}\n"
                    if res.get('size'):
                        reply_text += f"💾 大小: {res.get('size')}\n"
                    reply_text += f"🔗 链接: {res.get('url', res.get('link', '无'))}\n"
                    reply_text += f"{'─' * 15}\n"
            
            if len(reply_text) > 3500:  # 留出空间给CMS提示
                reply_text = reply_text[:3400] + "...\n\n(内容过长已截断)\n\n"
            
            reply_text += f"📊 共找到 {len(resource_list)} 个资源\n\n"
            
            # 如果启用了CloudDrive2，添加转存提示
            if self._cd2_enabled and self._cd2_client and resource_type in ["115", "magnet", "ed2k"]:
                if resource_type == "115":
                    reply_text += "🚀 CloudDrive2转存:\n"
                    reply_text += "发送资源编号进行转存，如: 1、2、3...\n"
                else:
                    reply_text += "🚀 CloudDrive2离线下载:\n"
                    reply_text += "发送资源编号添加离线任务，如: 1、2、3..."
            
            self.post_message(
                channel=channel,
                title=f"{resource_type.upper()}资源",
                text=reply_text,
                userid=userid
            )
            
        except Exception as e:
            logger.error(f"格式化资源异常: {str(e)}")
            self.post_message(
                channel=channel,
                title="错误",
                text=f"处理资源信息时出现错误: {str(e)}",
                userid=userid
            )

    def fallback_to_moviepilot_search(self, title: str, channel: str, userid: str):
        """回退到MoviePilot原始搜索功能"""
        logger.info(f"启动MoviePilot原始搜索: {title}")
        
        # 尝试其他搜索方式
        self.try_alternative_search(title, channel, userid)

    def try_alternative_search(self, title: str, channel: str, userid: str):
        """尝试其他搜索方式"""
        try:
            logger.info(f"尝试MoviePilot原始搜索: {title}")
            
            # 简化策略：直接发送搜索建议和提示
            # 避免复杂的模块调用导致的错误
            
            success = False
            
            # 方法1: 尝试调用站点助手的简单方法
            try:
                from app.helper.sites import SitesHelper
                sites_helper = SitesHelper()
                
                # 只是检查是否有配置的站点
                if hasattr(sites_helper, 'get_indexers'):
                    indexers = sites_helper.get_indexers()
                    if indexers:
                        logger.info(f"检测到 {len(indexers)} 个配置的站点")
                        
                        self.post_message(
                            channel=channel,
                            title="搜索提示",
                            text=f"🔍 Nullbr未找到「{title}」的资源\n\n" +
                                 f"💡 系统检测到您已配置 {len(indexers)} 个搜索站点\n" +
                                 f"建议通过以下方式继续搜索:\n\n" +
                                 f"🌐 MoviePilot Web界面搜索\n" +
                                 f"📱 其他搜索渠道\n" +
                                 f"⚙️ 检查站点配置状态",
                            userid=userid
                        )
                        success = True
                
            except Exception as e:
                logger.warning(f"站点检测失败: {str(e)}")
            
            # 如果上面的方法也失败，发送通用建议
            if not success:
                self.send_manual_search_suggestion(title, channel, userid)
            
        except Exception as e:
            logger.error(f"备用搜索失败: {str(e)}")
            self.send_manual_search_suggestion(title, channel, userid)

    def send_manual_search_suggestion(self, title: str, channel: str, userid: str):
        """发送手动搜索建议"""
        self.post_message(
            channel=channel,
            title="搜索建议",
            text=f"📋 「{title}」未找到资源，建议:\n\n" +
                 f"🔍 在MoviePilot Web界面搜索\n" +
                 f"⚙️ 检查资源站点配置\n" +
                 f"🔄 尝试其他关键词\n" +
                 f"📱 使用其他搜索渠道",
            userid=userid
        )

    def stop_service(self):
        """停止插件服务"""
        try:
            # 清理客户端连接
            if self._client:
                logger.info("清理Nullbr客户端")
                self._client = None
            
            if self._cd2_client:
                logger.info("清理CloudDrive2客户端连接")
                if hasattr(self._cd2_client, 'session'):
                    self._cd2_client.session.close()
                self._cd2_client = None
            
            # 清理缓存
            self._user_search_cache.clear()
            self._user_resource_cache.clear()
            
            self._enabled = False
            logger.info("Nullbr资源搜索Pro插件已停止")
        except Exception as e:
            logger.error(f"插件停止异常: {str(e)}")


# 导出插件类
__all__ = ['nullbr_search_pro']