"""服务端插件工具执行器"""

from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler
from ..base import ToolType, ToolDefinition, ToolExecutor
from plugins_func.register import all_function_registry, Action, ActionResponse


class ServerPluginExecutor(ToolExecutor):
    """服务端插件工具执行器"""

    def __init__(self, conn: "ConnectionHandler"):
        self.conn = conn
        self.config = conn.config

    async def execute(
        self, conn: "ConnectionHandler", tool_name: str, arguments: Dict[str, Any]
    ) -> ActionResponse:
        """执行服务端插件工具"""
        func_item = all_function_registry.get(tool_name)
        if not func_item:
            return ActionResponse(
                action=Action.NOTFOUND, response=f"插件函数 {tool_name} 不存在"
            )
        try:
            # 根据工具类型决定如何调用
            if hasattr(func_item, "type"):
                func_type = func_item.type
                if func_type.code in [4, 5]:
                    result = func_item.func(conn, **arguments)
                elif func_type.code == 2:
                    result = func_item.func(**arguments)
                elif func_type.code == 3:
                    result = func_item.func(conn, **arguments)
                else:
                    result = func_item.func(**arguments)
            else:
                result = func_item.func(**arguments)
            return result
        except Exception as e:
            return ActionResponse(action=Action.ERROR, response=str(e))

    def get_tools(self) -> Dict[str, ToolDefinition]:
        """获取所有注册的服务端插件工具"""
        tools = {}
        necessary_functions = ["handle_exit_intent", "get_lunar"]
        config_functions = list(all_function_registry.keys())
        all_required_functions = list(set(necessary_functions + config_functions))
        for func_name in all_required_functions:
            func_item = all_function_registry.get(func_name)
            if func_item:
                plugin_conf = self.config.get("plugins", {}).get(func_name, {})
                if isinstance(plugin_conf, str):
                    import json
                    try:
                        plugin_conf = json.loads(plugin_conf)
                    except Exception:
                        plugin_conf = {}
                fun_description = plugin_conf.get("description", "")
                if fun_description:
                    if "function" in func_item.description and isinstance(
                        func_item.description["function"], dict
                    ):
                        func_item.description["function"]["description"] = fun_description
                if func_name == "get_news_from_newsnow":
                    self._init_news_source_description(func_item, func_name)
                tools[func_name] = ToolDefinition(
                    name=func_name,
                    description=func_item.description,
                    tool_type=ToolType.SERVER_PLUGIN,
                )
        return tools

    def has_tool(self, tool_name: str) -> bool:
        return tool_name in all_function_registry

    def _init_news_source_description(self, func_item, func_name):
        news_sources = self.config.get("plugins", {}).get(func_name, {})
        if isinstance(news_sources, str):
            import json
            try:
                news_sources = json.loads(news_sources).get("news_sources", "")
            except Exception:
                news_sources = ""
        else:
            news_sources = news_sources.get("news_sources", "")
        if not news_sources:
            news_sources = "澎湃新闻;百度热搜;财联社"
        sources_str = news_sources.replace(";", "、")
        try:
            func_item.description["function"]["parameters"]["properties"]["source"][
                "description"
            ] = f"新闻源的标准中文名称，例如{sources_str}等。可选参数，如果不提供则使用默认新闻源"
        except (KeyError, TypeError):
            pass
