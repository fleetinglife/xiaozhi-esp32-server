import requests
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

BASE_URL = "https://flashylife.cn/api"

STOCK_HOT_RANK_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "stock_hot_rank",
        "description": (
            "查询同花顺今日人气股排行榜。"
            "当用户说'今天人气最高的股票'、'热门股'、'人气榜'、'大家都在关注什么股'时调用此工具。"
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}


@register_function("stock_hot_rank", STOCK_HOT_RANK_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def stock_hot_rank(conn: "ConnectionHandler"):
    try:
        resp = requests.get(f"{BASE_URL}/app/index/getHotStock", timeout=5)
        data = resp.json()
        if data.get("code") != "000000" or not data.get("data"):
            return ActionResponse(Action.REQLLM, "获取人气榜失败，请稍后再试", None)

        stocks = data["data"][:10]
        parts = ["以下是今日同花顺人气股TOP10，请用简洁口语播报，重点说涨幅靠前的："]
        for i, item in enumerate(stocks, 1):
            name = item.get("name", "")
            pct_chg = item.get("pctChg", 0)
            price = item.get("close", "")
            tag = item.get("tag") or {}
            concepts = tag.get("conceptTag", [])
            popularity = tag.get("popularityTag", "")
            concept_str = "/".join(concepts[:2]) if concepts else ""
            desc = f"{i}. {name} {price}元 {'涨' if pct_chg >= 0 else '跌'}{abs(pct_chg)}%"
            if popularity:
                desc += f"（{popularity}）"
            if concept_str:
                desc += f" [{concept_str}]"
            parts.append(desc)

        result = "\n".join(parts)
        logger.bind(tag=TAG).info(f"人气榜: {result}")
        return ActionResponse(Action.REQLLM, result, None)

    except Exception as e:
        logger.bind(tag=TAG).error(f"人气榜获取失败: {e}")
        return ActionResponse(Action.REQLLM, "人气榜获取失败，请稍后再试", None)
