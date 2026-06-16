import json
import os
import asyncio
import uuid
from datetime import datetime
from config.logger import setup_logging

TAG = "alarm_checker"
logger = setup_logging()
ALARM_FILE = "/opt/xiaozhi-esp32-server/alarms.json"

active_connections = {}

def register_connection(client_ip, conn):
    active_connections[client_ip] = conn

def unregister_connection(client_ip):
    active_connections.pop(client_ip, None)

def load_alarms():
    if not os.path.exists(ALARM_FILE):
        return []
    try:
        with open(ALARM_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_alarms(alarms):
    try:
        with open(ALARM_FILE, "w", encoding="utf-8") as f:
            json.dump(alarms, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.bind(tag=TAG).error(f"保存闹钟失败: {e}")

async def check_alarms(ws_server=None):
    while True:
        try:
            now = datetime.now()
            current_time = now.strftime("%H:%M")
            current_weekday = now.weekday()
            alarms = load_alarms()
            changed = False
            for alarm in alarms:
                if alarm.get("triggered") and alarm.get("repeat") == "once":
                    continue
                if alarm.get("time") != current_time:
                    continue
                repeat = alarm.get("repeat", "once")
                if repeat == "workday" and current_weekday >= 5:
                    continue
                client_ip = alarm.get("client_ip")
                message = alarm.get("message", "提醒时间到了")
                tts_text = f"叮！叮！叮！{message}"
                conn = active_connections.get(client_ip)
                if conn:
                    try:
                        from core.handle.intentHandler import speak_txt
                        # 刷新sentence_id确保TTS线程不过滤
                        conn.sentence_id = str(uuid.uuid4().hex)
                        conn.client_abort = False
                        conn.executor.submit(speak_txt, conn, tts_text)
                        logger.bind(tag=TAG).info(f"闹钟推送成功: {client_ip} - {tts_text}")
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"闹钟推送失败: {e}")
                else:
                    logger.bind(tag=TAG).warning(f"设备不在线，闹钟未推送: {client_ip}")
                if repeat == "once":
                    alarm["triggered"] = True
                    changed = True
            if changed:
                save_alarms(alarms)
        except Exception as e:
            logger.bind(tag=TAG).error(f"闹钟检查异常: {e}")
        await asyncio.sleep(60)
