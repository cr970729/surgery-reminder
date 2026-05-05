# -*- coding: utf-8 -*-
"""手术间检查自动化提醒 - 每周一通过钉钉机器人发送"""

import os
import sys
import requests
import time
import hmac
import hashlib
import base64
from urllib.parse import quote_plus
from datetime import datetime

# --- 配置 ---
# 从环境变量读取敏感信息（GitHub Secrets 注入）
ACCESS_TOKEN = os.environ.get("DINGTALK_ACCESS_TOKEN", "")
SECRET = os.environ.get("DINGTALK_SECRET", "")

# 第一周的周一（可通过环境变量覆盖，格式 YYYY-MM-DD）
_start_date_str = os.environ.get("START_DATE", "2026-05-11")
START_DATE = datetime.strptime(_start_date_str, "%Y-%m-%d")

# 人员名单（按轮转顺序）
PERSONNEL = [
    "陈柔",
    "王凌之",
    "朱瑜",
    "金建敏",
    "傅雨佳",
    "沈安娜",
]

# 手机号映射（用于钉钉 @ 功能）
PERSON_MOBILE_MAP = {
    "陈柔": "13588356563",
    "王凌之": "15867118967",
    "朱瑜": "15067156369",
    "金建敏": "18806510700",
    "傅雨佳": "13588379795",
    "沈安娜": "15824492369",
}

# 房间段（按轮转顺序）
ROOM_SEGMENTS = [
    "第21-30间",
    "第31-40间",
    "第1-10间",
    "第11-20间",
]


def get_current_week_offset(start_date):
    """计算从 start_date 到现在的周偏移量"""
    today = datetime.now()
    days_diff = (today - start_date).days
    weeks = days_diff // 7
    # 如果当前日期早于起始日期，视为第 0 周（便于测试）
    return max(0, weeks)


def send_dingtalk_message(content, at_mobiles=None):
    """发送钉钉群机器人消息"""
    if not ACCESS_TOKEN:
        print("❌ 未设置 DINGTALK_ACCESS_TOKEN 环境变量")
        return False

    webhook_url = f"https://oapi.dingtalk.com/robot/send?access_token={ACCESS_TOKEN}"
    headers = {"Content-Type": "application/json"}

    # 加签
    if SECRET:
        timestamp = str(round(time.time() * 1000))
        secret_enc = SECRET.encode("utf-8")
        string_to_sign = f"{timestamp}\n{SECRET}"
        string_to_sign_enc = string_to_sign.encode("utf-8")
        hmac_code = hmac.new(
            secret_enc, string_to_sign_enc, digestmod=hashlib.sha256
        ).digest()
        sign = quote_plus(base64.b64encode(hmac_code))
        webhook_url = (
            f"https://oapi.dingtalk.com/robot/send"
            f"?access_token={ACCESS_TOKEN}&timestamp={timestamp}&sign={sign}"
        )

    # 构建消息体
    at_info = {"isAtAll": False}
    final_content = content

    if at_mobiles:
        at_info["atMobiles"] = at_mobiles
        mention_str = " ".join([f"@{mobile}" for mobile in at_mobiles])
        final_content = f"{content}\n{mention_str}"

    payload = {
        "msgtype": "text",
        "text": {"content": final_content},
        "at": at_info,
    }

    try:
        resp = requests.post(webhook_url, json=payload, headers=headers, timeout=10)
        result = resp.json()
        if result.get("errcode") == 0:
            print("✅ 发送成功")
            return True
        else:
            print(f"❌ 发送失败: {result}")
            return False
    except requests.RequestException as e:
        print(f"❌ 网络异常: {e}")
        return False


def main():
    # 验证必要配置
    if not ACCESS_TOKEN:
        print("❌ 错误: 请设置 DINGTALK_ACCESS_TOKEN 环境变量", file=sys.stderr)
        sys.exit(1)

    week_offset = get_current_week_offset(START_DATE)
    person_index = week_offset % len(PERSONNEL)
    responsible = PERSONNEL[person_index]
    segment_index = week_offset % len(ROOM_SEGMENTS)
    room_range = ROOM_SEGMENTS[segment_index]

    message = (
        f"【手术间检查提醒】\n"
        f"本周负责人：{responsible}\n"
        f"检查范围：{room_range}\n"
        f"请按时完成检查。"
    )

    mobiles = [PERSON_MOBILE_MAP[responsible]]
    success = send_dingtalk_message(message, at_mobiles=mobiles)
    print(f"消息: {message}")
    print(f"@手机号: {mobiles}")

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
