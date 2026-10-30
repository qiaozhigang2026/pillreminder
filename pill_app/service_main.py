# -*- coding: utf-8 -*-
"""
前台服务：保持 App 在后台持续运行，不被系统回收。
用于安卓端保活，桌面端测试时不会被调用。
"""
from kivy import platform

try:
    from jnius import autoclass
except Exception:
    autoclass = None

from notifications import start_foreground, FOREGROUND_CHANNEL


def start_foreground_service():
    if platform != "android" or autoclass is None:
        return
    try:
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        PythonService = autoclass("org.kivy.android.PythonService")
        activity = PythonActivity.mActivity
        service = PythonService()
        # 在 Android 上，通过 Service 类启动
        Intent = autoclass("android.content.Intent")
        ctx = activity.getApplicationContext()
        intent = Intent(ctx, PythonService)
        ctx.startService(intent)
        print("[Service] foreground service started")
    except Exception as e:
        print("[Service] start error:", e)


# 若作为 PythonService 运行（buildozer android.services）
def service_start(service):
    """buildozer android.services 启动入口。"""
    try:
        from notifications import start_foreground
        start_foreground(service, "用药提醒正在运行", "保持提醒在后台正常运行")
    except Exception as e:
        print("[Service] service_start error:", e)


def service_stop(service):
    try:
        service.stopForeground(True)
    except Exception:
        pass
