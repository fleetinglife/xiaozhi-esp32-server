import requests
from urllib.parse import quote
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

BASE_URL = "https://flashylife.cn/api"

STOCK_STRATEGY_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "stock_strategy",
        "description": (
            "通过自然语言查询符合条件的股票，支持技术指标和基本面筛选。"
            "当用户说'帮我筛一下XX股票'、'找XX条件的股'、'哪些股票符合XX'、'KDJ金叉的股'、'连板股'时调用此工具。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "筛选条件，如'KDJ金叉'、'连板股'、'放量涨停'等",
                }
            },
            "required": ["query"],
        },
    },
}


@register_function("stock_strategy", STOCK_STRATEGY_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def stock_strategy(conn: "ConnectionHandler", query: str):
    try:
        url = f"{BASE_URL}/strategy?q={quote(query)}"
        resp = requests.get(url, timeout=10)
        data = resp.json()

        if data.get("code") != "000000" or not data.get("data"):
            return ActionResponse(Action.REQLLM, f"未找到符合'{query}'条件的股票", None)

        result_data = data["data"]
        title = result_data.get("title", [])
        results = result_data.get("result", [])

        if not results:
            return ActionResponse(Action.REQLLM, f"今日没有符合'{query}'条件的股票", None)

        # 取前5条，只播报代码、名称、涨跌幅
        parts = [f"以下是符合'{query}'条件的股票，共{len(results)}只，播报前5只："]
        for row in results[:5]:
            code = row[0].split(".")[0] if row[0] else ""
            name = row[1] if len(row) > 1 else ""
            price = row[2] if len(row) > 2 else ""
            pct = row[3] if len(row) > 3 else ""
            pct_val = float(pct or 0)
            parts.append(f"{name}（{code}）：{price}元，{'涨' if pct_val >= 0 else '跌'}{abs(pct_val)}%")

        result = "\n".join(parts)
        logger.bind(tag=TAG).info(f"问财策略: {result}")
        return ActionResponse(Action.REQLLM, result, None)

    except Exception as e:
        logger.bind(tag=TAG).error(f"问财策略查询失败: {e}")
        return ActionResponse(Action.REQLLM, "策略查询失败，请稍后再试", None)
