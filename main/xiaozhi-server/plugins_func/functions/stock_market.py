import requests
from datetime import datetime
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

BASE_URL = "https://flashylife.cn/api"
CACHE_KEY = "market_brief_today"

STOCK_MORNING_BRIEF_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "stock_market",
        "description": (
            "获取A股市场今日行情数据，包括是否是交易日、市场情绪、涨停梯队、最高连板、空间龙头、今日主线方向、热点板块，"
            "15:40后只返回AI情绪周期分析和仓位建议。"
            "当用户说'今天市场怎么样'、'大盘情绪'、'今天主线是什么'、'今天热点'、"
            "'大A怎么样'、'大A咋样'、'股票咋样'、'今天行情'、'市场行情'、'今天涨停多少'时调用此工具。"
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}


def fetch_is_trade_day():
    try:
        resp = requests.get(f"{BASE_URL}/isTradeDay", timeout=5)
        data = resp.json()
        return data.get("code") == "000000"
    except Exception as e:
        logger.bind(tag=TAG).error(f"isTradeDay请求失败: {e}")
        return False


def fetch_json(path):
    try:
        resp = requests.get(f"{BASE_URL}{path}", timeout=5)
        data = resp.json()
        if data.get("code") == "000000":
            return data.get("data")
    except Exception as e:
        logger.bind(tag=TAG).error(f"请求{path}失败: {e}")
    return None


def is_after_close():
    """15:00后"""
    now = datetime.now()
    return now.hour >= 15


def is_after_analysis():
    """15:40后"""
    now = datetime.now()
    return now.hour > 15 or (now.hour == 15 and now.minute >= 40)


def build_realtime_brief():
    """查实时接口，用于15:40前"""
    parts = [
        "以下是今日A股市场数据，请你用简洁自然的口语播报给用户，重点突出关键信息，控制在30秒内能说完：",
    ]

    if not fetch_is_trade_day():
        return "今天不是交易日，市场休市。"
    parts.append("【交易日状态】今天是交易日")

    emotion = fetch_json("/app/index/getStockEmotion")
    if emotion:
        market_degree = emotion.get("marketDegree", "")
        performance = emotion.get("performance", "")
        up_down = emotion.get("upDownDis", {})
        rise_num = up_down.get("riseNum", "")
        fall_num = up_down.get("fallNum", "")
        limit_up_board = emotion.get("limitUpBoard", {})
        row1 = limit_up_board.get("row1", [])
        row2 = limit_up_board.get("row2", [])
        parts.append(
            f"【市场情绪】市场活跃度评分{market_degree}分（满分100，越高越活跃）；"
            f"全市场上涨{rise_num}家，下跌{fall_num}家；平均赚钱效应{performance}"
        )
        if row1 and row2 and len(row2) >= 3:
            board_items = [f"{row1[i]}{row2[i]}个" for i in range(min(4, len(row1), len(row2)))]
            parts.append(f"【涨停梯队】{'、'.join(board_items)}")

    zt_pool = fetch_json("/stock/dingpan/getZtPool")
    if zt_pool and len(zt_pool) > 0:
        try:
            max_lbc = max(s.get("continuous", 1) for s in zt_pool)
            top_stocks = [s.get("stockName", "") for s in zt_pool if s.get("continuous") == max_lbc]
            parts.append(
                f"【高度板】今日最高连板数{max_lbc}板，"
                f"空间龙头：{'、'.join(top_stocks)}（连板数越高说明市场赚钱效应越强）"
            )
        except Exception as e:
            logger.bind(tag=TAG).error(f"计算高度板失败: {e}")

    mainline = fetch_json("/stock/dingpan/getMainline")
    if mainline and len(mainline) > 0:
        for item in mainline[:2]:
            name = item.get("name", "")
            reason = item.get("reason", "")[:60]
            rise_count = item.get("riseCount", "")
            faucets = item.get("faucets", [])
            faucet_desc = "、".join([
                f"{f.get('stockName')}（{f.get('reason', '')}）"
                for f in faucets[:2]
            ])
            parts.append(
                f"【主线方向】{name}：{reason}；板块内{rise_count}只股上涨；代表龙头：{faucet_desc}"
            )

    hot_plates = fetch_json("/stock/dingpan/getHotPlates")
    if hot_plates and len(hot_plates) > 0:
        plate_descs = []
        for item in hot_plates[:3]:
            name = item.get("secuName", "")
            change = item.get("change", 0)
            up_reason = item.get("upReason", "")[:50]
            up_num = item.get("plateStockUpNum", "")
            stock_list = item.get("stockList", [])
            leader = stock_list[0].get("secuName", "") if stock_list else ""
            leader_change = stock_list[0].get("change", "") if stock_list else ""
            plate_descs.append(
                f"{name}（整体涨幅{round(change * 100, 1)}%，{up_num}只股涨停，龙头{leader}{leader_change}）：{up_reason}"
            )
        parts.append("【热点板块】" + "；".join(plate_descs))

    return "\n".join(parts)


def build_analysis_brief():
    """只查AI情绪周期分析，用于15:40后"""
    parts = [
        "以下是今日A股收盘后AI情绪周期分析，请你用简洁自然的口语播报给用户：",
    ]

    if not fetch_is_trade_day():
        return "今天不是交易日，市场休市。"

    daily_emotion = fetch_json("/stock/dailyEmotion")
    if not daily_emotion or len(daily_emotion) == 0:
        return "今日AI情绪周期分析暂未生成，请稍后再问。"

    item = daily_emotion[0]
    phase = item.get("phase", "")
    sub_phase = item.get("subPhase", "")
    confidence = item.get("confidence", "")
    cycle_reason = item.get("cycleReason", "")
    position_ratio = item.get("positionRatio", "")
    position_direction = item.get("positionDirection", "")
    position_advice = item.get("positionAdvice", "")
    emotion_forecast = item.get("emotionForecast", "")
    tomorrow_reason = item.get("tomorrowReason", "")

    parts.append(
        f"【AI情绪周期分析】当前处于{phase}阶段（{sub_phase}），置信度{confidence}%；"
        f"判断依据：{cycle_reason}"
    )
    parts.append(
        f"【仓位建议】建议仓位{position_ratio}%，方向{position_direction}；{position_advice}"
    )
    parts.append(
        f"【明日预判】情绪预判{emotion_forecast}；{tomorrow_reason}"
    )

    return "\n".join(parts)


@register_function("stock_market", STOCK_MORNING_BRIEF_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def stock_market(conn: "ConnectionHandler"):
    from core.utils.cache.manager import cache_manager, CacheType

    # 15:00后读缓存
    if is_after_close():
        cached = cache_manager.get(CacheType.WEATHER, CACHE_KEY)
        if cached:
            logger.bind(tag=TAG).info("使用缓存的市场数据")
            return ActionResponse(Action.REQLLM, cached, None)

    # 15:40后只查AI分析，否则查实时接口
    if is_after_analysis():
        result = build_analysis_brief()
    else:
        result = build_realtime_brief()

    logger.bind(tag=TAG).info(f"市场数据: {result}")

    # 15:00后写缓存
    if is_after_close():
        cache_manager.set(CacheType.WEATHER, CACHE_KEY, result)
        logger.bind(tag=TAG).info("市场数据已缓存")

    return ActionResponse(Action.REQLLM, result, None)
