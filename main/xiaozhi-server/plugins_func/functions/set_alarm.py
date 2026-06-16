import json
import os
from datetime import datetime
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from alarm_checker import register_connection, unregister_connection
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

ALARM_FILE = "/opt/xiaozhi-esp32-server/alarms.json"


def load_alarms():
    if not os.path.exists(ALARM_FILE):
        return []
    try:
        with open(ALARM_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_alarms(alarms):
    with open(ALARM_FILE, "w", encoding="utf-8") as f:
        json.dump(alarms, f, ensure_ascii=False, indent=2)


SET_ALARM_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "set_alarm",
        "description": (
            "设置闹钟或定时提醒。当用户说'明天早上7点叫我'、'提醒我xx'、'定个闹钟'、'x点提醒我'时调用此工具。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "time": {
                    "type": "string",
                    "description": "提醒时间，格式 HH:MM，如 07:00、08:30",
                },
                "message": {
                    "type": "string",
                    "description": "提醒内容，如'该起床了'、'吃药时间'",
                },
                "repeat": {
                    "type": "string",
                    "description": "重复类型：once=仅一次，daily=每天，workday=工作日，默认once",
                },
            },
            "required": ["time", "message"],
        },
    },
}


@register_function("set_alarm", SET_ALARM_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def set_alarm(conn: "ConnectionHandler", time: str, message: str, repeat: str = "once"):
    try:
        # 验证时间格式
        datetime.strptime(time, "%H:%M")

        alarms = load_alarms()

        # 生成唯一ID，绑定设备client_ip
        alarm = {
            "id": f"{conn.client_ip}_{time}_{len(alarms)}",
            "client_ip": conn.client_ip,
            "time": time,
            "message": message,
            "repeat": repeat,
            "triggered": False,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        register_connection(conn.client_ip, conn)
        alarms.append(alarm)
        save_alarms(alarms)

        repeat_desc = {"once": "仅今天一次", "daily": "每天", "workday": "每个工作日"}.get(repeat, "仅一次")
        result = f"好的，已为你设置{time}的提醒：{message}（{repeat_desc}）"
        logger.bind(tag=TAG).info(f"设置闹钟: {alarm}")
        return ActionResponse(Action.REQLLM, result, None)

    except ValueError:
        return ActionResponse(Action.REQLLM, "时间格式不正确，请说类似'早上7点'或'下午3点半'", None)
    except Exception as e:
        logger.bind(tag=TAG).error(f"设置闹钟失败: {e}")
        return ActionResponse(Action.REQLLM, "设置闹钟失败，请稍后再试", None)
