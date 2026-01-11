# MoviePilot 消息处理与模块重载机制分析

## 一、核心架构

MoviePilot 采用 **Chain + Module** 的架构：

- **Chain（处理链）**：业务逻辑层，位于 `app/chain/`
- **Module（模块）**：功能实现层，位于 `app/modules/`
- **Plugin（插件）**：扩展层，可重载 Module 方法

## 二、消息处理流程

### 2.1 入口

消息从通知渠道（企业微信、Telegram 等）进入后：

1. 请求到达 `app/api/endpoints/message.py`
2. 调用 `MessageChain().process()`
3. 解析消息内容，调用 `handle_message()`

### 2.2 handle_message 核心逻辑

位置：`app/chain/message.py` 第 134-558 行

```python
def handle_message(self, channel, source, userid, username, text, ...):
    # 1. CALLBACK: 开头 -> 处理按钮回调
    if text.startswith('CALLBACK:'):
        self._handle_callback(...)
    
    # 2. / 开头（非 /ai）-> 执行命令
    elif text.startswith('/') and not text.lower().startswith('/ai'):
        self.eventmanager.send_event(EventType.CommandExcute, {...})
    
    # 3. /ai 开头 -> AI 智能体
    elif text.lower().startswith('/ai'):
        self._handle_ai_message(...)
    
    # 4. 全局 AI 模式 -> AI 响应
    elif settings.AI_AGENT_ENABLE and settings.AI_AGENT_GLOBAL:
        self._handle_ai_message(...)
    
    # 5. 普通消息
    else:
        if text.isdigit():
            # 5.1 数字 -> 选择缓存条目
            ...
        elif text.lower() == "p":
            # 5.2 上一页
            ...
        elif text.lower() == "n":
            # 5.3 下一页
            ...
        else:
            # 5.4 文本处理
            if text.startswith("订阅"):
                action = "Subscribe"
            elif text.startswith("洗版"):
                action = "ReSubscribe"
            elif text.startswith("搜索") or text.startswith("下载"):
                action = "ReSearch"
            elif text.startswith("#") or is_question(text) or is_long_text(text):
                action = "Chat"  # 触发 UserMessage 事件
            elif is_link(text):
                action = "Link"
            else:
                action = "Search"  # 默认搜索！
            
            # 搜索/订阅操作
            if action in ["Search", "ReSearch", "Subscribe", "ReSubscribe"]:
                meta, medias = MediaChain().search(content)  # 关键调用！
                ...
            else:
                # 广播 UserMessage 事件
                self.eventmanager.send_event(EventType.UserMessage, {...})
```

### 2.3 关键发现

1. **普通文本默认触发搜索**：用户发送影片名会直接调用 `MediaChain().search()`
2. **`#` 开头消息触发 Chat**：会广播 `UserMessage` 事件，插件可监听
3. **搜索调用链**：`handle_message` → `MediaChain().search()` → `run_module("search_medias")`

## 三、模块重载机制

### 3.1 run_module 执行顺序

位置：`app/chain/__init__.py` 第 298-313 行

```python
def run_module(self, method: str, *args, **kwargs) -> Any:
    result = None

    # 1. 先执行插件模块
    result = self.__execute_plugin_modules(method, result, *args, **kwargs)

    # 2. 如果插件返回非空且非列表，直接返回（不执行系统模块）
    if not self.__is_valid_empty(result) and not isinstance(result, list):
        return result

    # 3. 执行系统模块
    return self.__execute_system_modules(method, result, *args, **kwargs)
```

### 3.2 插件模块注册

位置：`app/chain/__init__.py` 第 167-190 行

```python
def __execute_plugin_modules(self, method: str, result: Any, *args, **kwargs):
    for plugin, module_dict in self.pluginmanager.get_plugin_modules().items():
        plugin_id, plugin_name = plugin
        if method in module_dict:
            func = module_dict[method]
            if func:
                if self.__is_valid_empty(result):
                    # 返回 None 时执行
                    result = func(*args, **kwargs)
                elif isinstance(result, list):
                    # 列表结果合并
                    temp = func(*args, **kwargs)
                    if isinstance(temp, list):
                        result.extend(temp)
                else:
                    # 非空非列表，跳出
                    break
    return result
```

### 3.3 插件声明方法

插件通过 `get_module()` 方法声明要重载的模块方法：

```python
def get_module(self) -> Dict[str, Any]:
    """
    获取插件模块声明
    返回格式: {"方法名": 方法实现}
    """
    return {
        "search_medias": self.my_search_medias,
    }
```

## 四、可重载的关键方法

### 4.1 search_medias（媒体搜索）

```python
def search_medias(self, meta: MetaBase) -> Optional[List[MediaInfo]]:
    """
    搜索媒体信息
    :param meta: 识别的元数据（包含 name, year, type 等）
    :return: MediaInfo 列表
    """
```

**调用场景**：用户搜索、订阅搜索、API 搜索

### 4.2 message_parser（消息解析）

```python
def message_parser(self, source: str, body: Any, form: Any,
                   args: Any) -> Optional[CommingMessage]:
    """
    解析消息内容
    """
```

**调用场景**：所有外部消息进入时

### 4.3 recognize_media（媒体识别）

```python
def recognize_media(self, meta: MetaBase, mtype, tmdbid, ...) -> Optional[MediaInfo]:
    """
    识别媒体信息
    """
```

**调用场景**：需要识别媒体详细信息时

## 五、MediaInfo 数据结构

位置：`app/core/context.py`

关键字段：
```python
class MediaInfo:
    title: str               # 标题
    original_title: str      # 原标题
    year: str               # 年份
    type: MediaType         # 类型（电影/电视剧）
    tmdb_id: int            # TMDB ID
    douban_id: str          # 豆瓣 ID
    poster_path: str        # 海报路径
    backdrop_path: str      # 背景图路径
    vote_average: float     # 评分
    overview: str           # 简介
    seasons: dict           # 季集信息（电视剧）
    ...
```

## 六、结论

1. **无法直接劫持 `handle_message`**：它是类方法，不经过 `run_module`
2. **可以劫持 `search_medias`**：拦截搜索请求，使用自定义搜索源
3. **需要返回标准格式**：若劫持搜索，需返回 `MediaInfo` 格式
4. **`#` 前缀是安全区**：以 `#` 开头的消息会触发 `UserMessage` 事件，不走系统搜索
