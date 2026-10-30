# -*- coding: utf-8 -*-
"""
提醒调度引擎：负责"下一次该什么时候响"。
不依赖 Android 系统 API，用纯 Python 计算下一次触发时间，
因此桌面端（测试/预览）和安卓端都能用同一套逻辑。
"""
import time
from datetime import datetime, timedelta

from storage import list_medicines, load_schedules


def _next_weekday(now, target_wd):
    """返回下一个等于 target_wd（0=周一）的日期，若今天就是则返回今天。"""
    for i in range(8):
        d = now + timedelta(days=i)
        if d.weekday() == target_wd:
            return d
    return now


def next_fire_time(schedule, after=None):
    """
    返回该计划下一次触发时间的 unix 时间戳，无下一次则返回 None。
    """
    if not schedule.get("enabled", True):
        return None
    now = datetime.fromtimestamp(after or time.time())
    hh, mm = [int(x) for x in schedule.get("time", "08:00").split(":")][:2]
    period = schedule.get("period", "everyday")

    if period == "everyday":
        cand = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if cand <= now:
            cand += timedelta(days=1)
        return int(cand.timestamp())

    if period == "every2days":
        # 以 1970-01-01 为锚点，取大于等于 now 且 (days 差 % 2 == 0) 的那一天
        base = datetime(1970, 1, 1)
        days = (now.date() - base.date()).days
        cand_date = base.date() + timedelta(days=days)
        # 找到第一个 >= now 且 parity 对齐的
        for i in range(4):
            d = base.date() + timedelta(days=days + i)
            if (d - base.date()).days % 2 == days % 2:
                dt = datetime(d.year, d.month, d.day, hh, mm)
                if dt > now:
                    return int(dt.timestamp())
        return None

    if period == "weekly":
        wds = schedule.get("weekdays") or []
        if not wds:
            return None
        for i in range(8):
            d = (now.date() + timedelta(days=i))
            dt = datetime(d.year, d.month, d.day, hh, mm)
            if d.weekday() in wds and dt > now:
                return int(dt.timestamp())
        return None

    if period == "monthly":
        mds = sorted([int(x) for x in (schedule.get("monthdays") or [])])
        if not mds:
            return None
        year, month = now.year, now.month
        for _ in range(24):
            for md in mds:
                try:
                    dt = datetime(year, month, md, hh, mm)
                except ValueError:
                    continue
                if dt > now:
                    return int(dt.timestamp())
            month += 1
            if month > 12:
                month = 1
                year += 1
        return None

    return None


def upcoming(limit=20, after=None):
    """
    返回即将到来的提醒列表，按时间升序。
    每条：{schedule, medicine, fire_ts}
    """
    meds = {m["id"]: m for m in list_medicines()}
    items = []
    for s in load_schedules():
        if not s.get("enabled", True):
            continue
        m = meds.get(s.get("medicine_id"))
        if not m:
            continue
        ts = next_fire_time(s, after)
        if ts:
            items.append({"schedule": s, "medicine": m, "fire_ts": ts})
    items.sort(key=lambda x: x["fire_ts"])
    return items[:limit]


def today_schedules(now=None):
    """返回今天需要服药的项目（含已过和未过），用于首页列表。"""
    now = now or datetime.now()
    today_ts = int(datetime(now.year, now.month, now.day).timestamp())
    meds = {m["id"]: m for m in list_medicines()}
    out = []
    for s in load_schedules():
        if not s.get("enabled", True):
            continue
        m = meds.get(s.get("medicine_id"))
        if not m:
            continue
        ts = next_fire_time(s, today_ts)
        if ts is None:
            continue
        fire = datetime.fromtimestamp(ts)
        if fire.date() == now.date():
            out.append({"schedule": s, "medicine": m, "fire_ts": ts})
    out.sort(key=lambda x: x["fire_ts"])
    return out


def format_time(ts):
    return datetime.fromtimestamp(ts).strftime("%H:%M")


def format_datetime(ts):
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def period_label(schedule):
    p = schedule.get("period", "everyday")
    labels = {
        "everyday": "每天",
        "every2days": "隔天",
        "weekly": "每周",
        "monthly": "每月",
    }
    base = labels.get(p, "每天")
    if p == "weekday":
        pass
    return base
