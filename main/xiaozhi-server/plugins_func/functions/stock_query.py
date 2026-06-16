import requests
from levistock.stock.stock_em import stocks_em
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

STOCK_QUERY_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "stock_query",
        "description": (
            "查询指定股票的实时价格和涨跌幅。"
            "当用户说'XX股票多少钱'、'帮我看一下XX'、'XX现在怎么样'、'XX涨了多少'时调用此工具。"
            "需要从用户话语中提取股票代码或名称。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "stock_codes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "股票代码列表，如['600519','000001']，不带交易所前缀",
                }
            },
            "required": ["stock_codes"],
        },
    },
}


@register_function("stock_query", STOCK_QUERY_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def stock_query(conn: "ConnectionHandler", stock_codes: list):
    try:
        data = stocks_em(stock_codes)
        if not data or len(data) == 0:
            return ActionResponse(Action.REQLLM, "未找到该股票数据，请确认股票代码是否正确", None)

        parts = ["以下是股票实时行情，请用简洁口语播报："]
        for item in data:
            name = item.get("stock_name", "")
            price = item.get("price", "")
            change_pct = item.get("change_pct", "")
            change_amt = item.get("change_amt", "")
            parts.append(
                f"{name}：现价{price}元，"
                f"{'涨' if float(change_pct or 0) >= 0 else '跌'}{abs(float(change_pct or 0))}%，"
                f"{'涨' if float(change_amt or 0) >= 0 else '跌'}{abs(float(change_amt or 0))}元"
            )

        result = "\n".join(parts)
        logger.bind(tag=TAG).info(f"股票查询: {result}")
        return ActionResponse(Action.REQLLM, result, None)

    except Exception as e:
        logger.bind(tag=TAG).error(f"股票查询失败: {e}")
        return ActionResponse(Action.REQLLM, "股票查询失败，请稍后再试", None)
