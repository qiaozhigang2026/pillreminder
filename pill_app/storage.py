# -*- coding: utf-8 -*-
"""
数据存储层：用药与服药记录的本地持久化。
使用 JSON 文件存储，路径位于应用私有目录，对老年人来说无需账号、无云同步，
拔出手机也不会丢数据。
"""
import os
import json
import time
import uuid
import threading

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
MED_FILE = os.path.join(DATA_DIR, "medicines.json")
SCHEDULE_FILE = os.path.join(DATA_DIR, "schedules.json")
LOG_FILE = os.path.join(DATA_DIR, "logs.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

_lock = threading.Lock()


def _ensure():
    os.makedirs(DATA_DIR, exist_ok=True)
    for p in (MED_FILE, SCHEDULE_FILE, LOG_FILE, SETTINGS_FILE):
        if not os.path.exists(p):
            with open(p, "w", encoding="utf-8") as f:
                json.dump([], f)


def _load(path):
    _ensure()
    with _lock:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)


def _save(path, data):
    _ensure()
    with _lock:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)


# ==================== 药品 ====================
def list_medicines():
    return _load(MED_FILE)


def get_medicine(mid):
    for m in list_medicines():
        if m.get("id") == mid:
            return m
    return None


def save_medicine(med):
    """med: {name, image, note, color}"""
    data = list_medicines()
    med_id = med.get("id")
    if not med_id:
        med["id"] = uuid.uuid4().hex[:10]
    for i, m in enumerate(data):
        if m.get("id") == med["id"]:
            data[i] = med
            _save(MED_FILE, data)
            return med
    data.append(med)
    _save(MED_FILE, data)
    return med


def delete_medicine(mid):
    data = [m for m in list_medicines() if m.get("id") != mid]
    _save(MED_FILE, data)
    # 级联删除计划与记录
    _save(SCHEDULE_FILE, [s for s in load_schedules() if s.get("medicine_id") != mid])
    _save(LOG_FILE, [l for l in load_logs() if l.get("medicine_id") != mid])


# ==================== 服药计划 ====================
def load_schedules():
    return _load(SCHEDULE_FILE)


def save_schedule(sch):
    """
    sch: {
      medicine_id, time(HH:MM),
      period: 'everyday'|'every2days'|'weekly'|'monthly',
      weekdays: [0-6] (周一是0),  # 仅 weekly
      monthdays: [1-31],          # 仅 monthly
      dose: '1粒',
      enabled: True
    }
    """
    data = load_schedules()
    if not sch.get("id"):
        sch["id"] = uuid.uuid4().hex[:10]
    for i, s in enumerate(data):
        if s.get("id") == sch["id"]:
            data[i] = sch
            _save(SCHEDULE_FILE, data)
            return sch
    data.append(sch)
    _save(SCHEDULE_FILE, data)
    return sch


def delete_schedule(sid):
    data = [s for s in load_schedules() if s.get("id") != sid]
    _save(SCHEDULE_FILE, data)


# ==================== 服药记录 ====================
def load_logs():
    return _load(LOG_FILE)


def add_log(medicine_id, dose, ts=None):
    data = load_logs()
    rec = {
        "id": uuid.uuid4().hex[:10],
        "medicine_id": medicine_id,
        "dose": dose,
        "ts": ts or int(time.time()),
    }
    data.append(rec)
    _save(LOG_FILE, data)
    return rec


def delete_log(lid):
    _save(LOG_FILE, [l for l in load_logs() if l.get("id") != lid])
