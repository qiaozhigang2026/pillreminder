# -*- coding: utf-8 -*-
"""
用药记录与打卡模块。
提供手动打卡（除弹窗「已服用」外，也可在首页直接点「已服药」）、
批量导入导出（备份到文件，方便换手机迁移数据）。
"""
import os
import json
import time
from datetime import datetime, date

from storage import add_log, load_logs, list_medicines, save_medicine, \
    load_schedules, save_schedule


def check_in(medicine_id, dose=""):
    """手动打卡：立即记录一次服药。"""
    return add_log(medicine_id, dose)


def stats(days=30):
    """返回最近 N 天的服药统计：每天服药次数、是否完成当日计划。"""
    from collections import defaultdict
    logs = load_logs()
    meds = {m["id"]: m for m in list_medicines()}
    per_day = defaultdict(list)
    for l in logs:
        d = datetime.fromtimestamp(l.get("ts", 0)).date()
        per_day[d].append(l)
    # 按日期排序
    result = []
    today = date.today()
    for i in range(days - 1, -1, -1):
        d = date(today.year, today.month, today.day)
        from datetime import timedelta
        d = d - timedelta(days=i)
        day_logs = per_day.get(d, [])
        # 当日应服次数 = 有效计划数（简化：以"有提醒计划"计）
        planned = len([s for s in load_schedules() if s.get("enabled", True)])
        result.append({
            "date": d,
            "taken": len(day_logs),
            "planned": planned,
            "done": len(day_logs) > 0 if planned else True,
        })
    return result


def export_data(path=None):
    """导出全部数据到 JSON 文件，用于备份/迁移。"""
    if path is None:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "data", "backup_%s.json" % int(time.time()))
    data = {
        "medicines": list_medicines(),
        "schedules": load_schedules(),
        "logs": load_logs(),
        "exported_at": int(time.time()),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def import_data(path):
    """从 JSON 文件导入数据（合并，不覆盖已有）。"""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for m in data.get("medicines", []):
        save_medicine(m)
    for s in data.get("schedules", []):
        save_schedule(s)
    for l in data.get("logs", []):
        add_log(l.get("medicine_id"), l.get("dose", ""))
    return len(data.get("medicines", [])), len(data.get("schedules", []))
