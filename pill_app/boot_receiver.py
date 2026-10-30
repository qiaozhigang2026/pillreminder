# -*- coding: utf-8 -*-
"""
开机自启与定时唤醒。
设备重启后，系统闹钟会被清空，需要重新注册。
这里通过 BOOT_COMPLETED 广播接收器，在开机时重新调度所有提醒。
"""
from kivy import platform

try:
    from jnius import autoclass
except Exception:
    autoclass = None

from scheduler import load_schedules, next_fire_time
from storage import list_medicines
from notifications import ensure_channels


def on_boot_completed():
    """开机后调用：重新注册所有闹钟。"""
    if platform != "android":
        return
    ensure_channels()
    _reschedule_all()


def _reschedule_all():
    """遍历所有计划，用 AlarmManager 重新注册。"""
    if autoclass is None:
        return
    try:
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
        AlarmManager = autoclass("android.app.AlarmManager")
        Intent = autoclass("android.content.Intent")
        PendingIntent = autoclass("android.app.PendingIntent")
        Context = autoclass("android.content.Context")

        am = activity.getSystemService(Context.ALARM_SERVICE)
        if am is None:
            return

        meds = {m["id"]: m for m in list_medicines()}
        for s in load_schedules():
            if not s.get("enabled", True):
                continue
            m = meds.get(s.get("medicine_id"))
            if not m:
                continue
            ts = next_fire_time(s)
            if ts is None:
                continue
            intent = Intent(activity, activity.getClass())
            intent.setAction("com.elderlyhealth.pillreminder.ALARM_%s" % s.get("id"))
            pi = PendingIntent.getBroadcast(
                activity, abs(hash(s.get("id"))) % 100000, intent,
                PendingIntent.FLAG_UPDATE_CURRENT
            )
            # 设置精确闹钟（Android 12+ 需要 SCHEDULE_EXACT_ALARM 权限）
            try:
                am.setExactAndAllowWhileIdle(
                    AlarmManager.RTC_WAKEUP, int(ts) * 1000, pi
                )
            except Exception as e:
                print("[Boot] schedule error:", e)
    except Exception as e:
        print("[Boot] reschedule error:", e)
