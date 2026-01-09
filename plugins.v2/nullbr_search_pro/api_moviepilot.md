# MoviePilot Plugin API Reference

Based on `MoviePilot-Plugins/README.md`.

## Core Concepts

### Directory Structure
*   `plugins/`: Plugin code. Each plugin in a subdirectory named lowercase of the plugin class name.
*   `__init__.py`: Plugin main class.
*   `package.json`: Manifest for all plugins.

### Events
Plugins can interact with the system via events.

#### Asynchronous Broadcast Events (`EventType`)
*   `PluginReload`: Plugin reload.
*   `PluginAction`: Trigger plugin action.
*   `PluginTriggered`: Plugin triggered event.
*   `CommandExcute`: Execute command.
*   `SiteDeleted`, `SiteUpdated`, `SiteRefreshed`: Site changes.
*   `TransferComplete`: Transfer complete.
*   `DownloadAdded`, `DownloadDeleted`, `DownloadFileDeleted`: Download tasks.
*   `HistoryDeleted`: History deleted.
*   `UserMessage`: User message received.
*   `WebhookMessage`: Webhook message received.
*   `NoticeMessage`: Send notification message.
*   `SubscribeAdded`, `SubscribeModified`, `SubscribeDeleted`, `SubscribeComplete`: Subscriptions.
*   `SystemError`: System error.
*   `MetadataScrape`: Metadata scrape.
*   `ModuleReload`: Module reload.

#### Synchronous Chain Events (`ChainEventType`)
*   `NameRecognize`: Name recognition.
*   `AuthVerification`, `AuthIntercept`: Authentication.
*   `CommandRegister`: Command registration.
*   `TransferRename`, `TransferIntercept`: Transfer handling.
*   `ResourceSelection`, `ResourceDownload`: Resource handling.
*   `DiscoverSource`: Discover media source.
*   `MediaRecognizeConvert`: Media identify convert.
*   `RecommendSource`: Recommend media source.
*   `WorkflowExecution`: Workflow execution.
*   `StorageOperSelection`: Storage operation selection.

## Interfaces

### 1. Remote Command (`get_command`)
Register commands for chat bots.
```python
def get_command(self) -> List[Dict[str, Any]]:
    return [{
        "cmd": "/my_cmd",
        "event": EventType.PluginAction,
        "desc": "Description",
        "category": "Category",
        "data": {"action": "my_action"}
    }]
```

### 2. API Endpoints (`get_api`)
Expose internal API.
```python
def get_api(self) -> List[Dict[str, Any]]:
    return [{
        "path": "/my_endpoint",
        "endpoint": self.handler_func,
        "methods": ["GET", "POST"],
        "summary": "Summary",
        "description": "Description"
    }]
```

### 3. Background Service (`get_service`)
Register scheduled tasks.
```python
def get_service(self) -> List[Dict[str, Any]]:
    return [{
        "id": "service_id",
        "name": "Service Name",
        "trigger": "cron/interval/date",
        "func": self.task_func,
        "kwargs": {}
    }]
```

### 4. Interactive Messages
Use `MessageAction` event for button callbacks.
*   **Callback Data Format**: `[PLUGIN]PluginClassName|action_data`
*   **Handle**: `@eventmanager.register(EventType.MessageAction)`

### 5. Notification (`NoticeMessage`)
Send notifications via `eventmanager.send_event(EventType.NoticeMessage, data)`.
```json
{
     "channel": "MessageChannel|None",
     "type": "NotificationType|None",
     "title": "Title",
     "text": "Body",
     "image": "Image URL",
     "userid": "User ID"
}
```

### 6. Storage Extension (`StorageOperSelection` & `get_module`)
Extend storage types and file operations.
*   Register custom storage in UI.
*   Implement file operations (list, download, upload, etc.).
*   Intercept `StorageOperSelection` to provide the operation instance.
*   Use `get_module` to hijack system file manager methods.

### 7. Workflow Actions (`get_actions`)
Integrate with the workflow system.
```python
def get_actions(self) -> List[Dict[str, Any]]:
    return [{
        "id": "action_id",
        "name": "Action Name",
        "func": self.action_func,
        "kwargs": {}
    }]
```

### 8. System Cache
Use `app.core.cache` decorators or helpers.
*   `@cached(region="plugin_name", ttl=3600)`
*   `TTLCache`
*   `FileCache`

### 9. Agent Tools (`get_agent_tools`)
Register tools for AI agents.
*   Return list of classes inheriting `MoviePilotTool`.
*   Implement `run` (async), `get_tool_message`.
