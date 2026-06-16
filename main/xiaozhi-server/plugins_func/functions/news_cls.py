from levistock.news.news_cls import news_telegraph_cls
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

NEWS_CLS_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "news_cls",
        "description": (
            "获取财联社今日重要电报快讯。支持按关键词匹配标题，如早间新闻、午间新闻、涨停分析等。"
            "当用户说'财联社说什么了'、'最新消息'、'早间新闻'、'午间新闻'、'晚间新闻'、"
            "'涨停分析'、'收评'、'午评'、'最新快讯'、'有什么重要新闻'时调用此工具。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "用户指定的关键词，如'早间'、'午间'、'涨停分析'、'收评'等，没有指定则不传",
                }
            },
            "required": [],
        },
    },
}


@register_function("news_cls", NEWS_CLS_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def news_cls(conn: "ConnectionHandler", keyword: str = None):
    try:
        data = news_telegraph_cls(category="important")
        if not data or len(data) == 0:
            return ActionResponse(Action.REQLLM, "暂无财联社快讯", None)

        # 只保留有title的条目
        titled = [item for item in data if item.get("title", "").strip()]

        if keyword:
            # 用关键词匹配title
            matched = [item for item in titled if keyword in item.get("title", "")]
            if matched:
                item = matched[0]
                result = (
                    f"以下是财联社「{item['title']}」，请用简洁口语播报给用户：\n"
                    f"{item.get('content', '')}"
                )
                logger.bind(tag=TAG).info(f"财联社匹配到: {item['title']}")
                return ActionResponse(Action.REQLLM, result, None)
            else:
                logger.bind(tag=TAG).info(f"财联社未匹配到关键词: {keyword}，返回最新5条")

        # 匹配不到或没有关键词，返回最新5条有title的
        parts = ["以下是财联社今日最新重要快讯，请用简洁口语播报："]
        for item in titled[:5]:
            title = item.get("title", "")
            parts.append(f"· {title}")

        result = "\n".join(parts)
        logger.bind(tag=TAG).info(f"财联社最新5条: {result}")
        return ActionResponse(Action.REQLLM, result, None)

    except Exception as e:
        logger.bind(tag=TAG).error(f"财联社快讯获取失败: {e}")
        return ActionResponse(Action.REQLLM, "获取财联社快讯失败，请稍后再试", None)
