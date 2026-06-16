from levistock.stock.stock_zt_cls import stock_zt_pool_cls
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

STOCK_ZT_REASON_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "stock_zt_reason",
        "description": (
            "查询今日涨停股票及涨停原因。"
            "当用户说'XX为什么涨停'、'今天哪些股涨停了'、'涨停原因'时调用此工具。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "stock_name": {
                    "type": "string",
                    "description": "要查询的股票名称，如果用户没有指定则不传，返回全部涨停股前5条",
                }
            },
            "required": [],
        },
    },
}


@register_function("stock_zt_reason", STOCK_ZT_REASON_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def stock_zt_reason(conn: "ConnectionHandler", stock_name: str = None):
    try:
        data = stock_zt_pool_cls()
        if not data or len(data) == 0:
            return ActionResponse(Action.REQLLM, "今日暂无涨停数据", None)

        parts = ["以下是今日涨停股票及原因，请用简洁口语播报："]

        if stock_name:
            # 查指定股票
            matched = [item for item in data if stock_name in item.get("secu_name", "")]
            if not matched:
                return ActionResponse(Action.REQLLM, f"今日涨停池中未找到{stock_name}", None)
            for item in matched[:2]:
                name = item.get("secu_name", "")
                reason = item.get("up_reason", "暂无原因")
                parts.append(f"{name}涨停原因：{reason}")
        else:
            # 返回前5条
            for item in data[:5]:
                name = item.get("secu_name", "")
                reason = item.get("up_reason", "暂无原因")
                parts.append(f"{name}：{reason}")

        result = "\n".join(parts)
        logger.bind(tag=TAG).info(f"涨停原因: {result}")
        return ActionResponse(Action.REQLLM, result, None)

    except Exception as e:
        logger.bind(tag=TAG).error(f"涨停原因查询失败: {e}")
        return ActionResponse(Action.REQLLM, "涨停原因查询失败，请稍后再试", None)
