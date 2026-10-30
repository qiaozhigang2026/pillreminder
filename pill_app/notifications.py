# -*- coding: utf-8 -*-
"""
通知管理：Android 状态栏通知 + 前台服务。
前台服务用于保证 App 退到后台甚至锁屏后，提醒进程不被系统回收。
"""
from kivy import platform

try:
    from jnius import autoclass
except Exception:
    autoclass = None

CHANNEL_ID = "pill_reminder_alarm"
FOREGROUND_CHANNEL = "pill_reminder_foreground"


def ensure_channels():
    if platform != "android" or autoclass is None:
        return
    try:
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
        Context = autoclass("android.content.Context")
        NotificationManager = autoclass("android.app.NotificationManager")
        NotificationChannel = autoclass("android.app.NotificationChannel")
        nm = activity.getSystemService(Context.NOTIFICATION_SERVICE)
        if nm is None:
            return
        for cid, name, desc, importance in (
            (CHANNEL_ID, "用药提醒", "服药时间到时的闹钟提醒", NotificationManager.IMPORTANCE_HIGH),
            (FOREGROUND_CHANNEL, "后台运行", "保持提醒在后台正常运行", NotificationManager.IMPORTANCE_LOW),
        ):
            chan = NotificationManager.NotificationChannel(cid, name, importance)
            chan.setDescription(desc)
            chan.enableVibration(True)
            if cid == CHANNEL_ID:
                chan.setBypassDollyMode(True)
                chan.setLockscreenVisibility(autoclass("android.app.Notification").VISIBILITY_PUBLIC)
            nm.createNotificationChannel(chan)
    except Exception as e:
        print("[Notify] channel error:", e)


def show_reminder_notification(title, text, fire_ts):
    """状态栏通知：点击进入 App 的提醒弹窗。"""
    if platform != "android" or autoclass is None:
        print("[Notify] desktop mode -> %s | %s" % (title, text))
        return
    try:
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
        Context = autoclass("android.content.Context")
        Intent = autoclass("android.content.Intent")
        PendingIntent = autoclass("android.app.PendingIntent")
        NotificationBuilder = autoclass("android.app.Notification$Builder")
        nm = activity.getSystemService(Context.NOTIFICATION_SERVICE)

        intent = Intent(activity, activity.getClass())
        intent.setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP)
        pi = PendingIntent.getActivity(activity, int(fire_ts) % 100000, intent, PendingIntent.FLAG_UPDATE_CURRENT)

        builder = NotificationBuilder(activity, CHANNEL_ID)
        builder.setContentTitle(title)
        builder.setContentText(text)
        builder.setSmallIcon(activity.getResources().getIdentifier("icon", "mipmap", activity.getPackageName()))
        builder.setAutoCancel(True)
        builder.setContentIntent(pi)
        builder.setPriority(NotificationBuilder.PRIORITY_MAX)
        builder.setCategory(autoclass("android.app.Notification").CATEGORY_ALARM)
        nm.notify(int(fire_ts) % 100000, builder.build())
    except Exception as e:
        print("[Notify] show error:", e)


def start_foreground(service, title, text):
    if platform != "android" or autoclass is None:
        return
    try:
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
        Context = autoclass("android.content.Context")
        Intent = autoclass("android.content.Intent")
        PendingIntent = autoclass("android.app.PendingIntent")
        NotificationBuilder = autoclass("android.app.Notification$Builder")

        intent = Intent(activity, service.getClass() if hasattr(service, "getClass") else activity.getClass())
        pi = PendingIntent.getActivity(activity, 1, intent, PendingIntent.FLAG_UPDATE_CURRENT)
        builder = NotificationBuilder(activity, FOREGROUND_CHANNEL)
        builder.setContentTitle(title)
        builder.setContentText(text)
        builder.setSmallIcon(activity.getResources().getIdentifier("icon", "mipmap", activity.getPackageName()))
        builder.setContentIntent(pi)
        service.startForeground(1, builder.build())
    except Exception as e:
        print("[Notify] foreground error:", e)
