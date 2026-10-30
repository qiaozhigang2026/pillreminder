# -*- coding: utf-8 -*-
"""
安卓端：闹钟接收器 + 闹钟注册。
使用 p4a/builder 的 AndroidManifest.xml.tmpl 方式嵌入，此处提供
供 buildozer 构建时合并到 AndroidManifest.xml。
"""
import os

MANIFEST_TEMPLATE = r"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.elderlyhealth.pillreminder"
    android:versionCode="1000"
    android:versionName="1.0.0">

    <!-- 权限 -->
    <uses-permission android:name="android.permission.WAKE_LOCK" />
    <uses-permission android:name="android.permission.VIBRATE" />
    <uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.SCHEDULE_EXACT_ALARM" />
    <uses-permission android:name="android.permission.USE_EXACT_ALARM" />
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
    <uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />
    <uses-permission android:name="android.permission.INTERNET" />

    <uses-sdk android:minSdkVersion="21" android:targetSdkVersion="33" />

    <application
        android:label="@string/app_name"
        android:icon="@mipmap/icon"
        android:allowBackup="true"
        android:supportsRtl="true"
        android:theme="@android:style/Theme.NoTitleBar.Fullscreen">

        <activity
            android:name="org.kivy.android.PythonActivity"
            android:label="@string/app_name"
            android:configChanges="orientation|screenSize|smallestScreenSize|keyboardHidden|keyboard"
            android:launchMode="singleTop"
            android:screenOrientation="portrait"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>

        <service
            android:name="org.kivy.android.PythonService"
            android:exported="false" />

        <!-- 开机自启：重新注册所有闹钟 -->
        <receiver
            android:name=".BootReceiver"
            android:enabled="true"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.BOOT_COMPLETED" />
                <action android:name="android.intent.action.QUICKBOOT_POWERON" />
                <action android:name="android.intent.action.LOCKED_BOOT_COMPLETED" />
            </intent-filter>
        </receiver>

        <!-- 闹钟触发接收器 -->
        <receiver
            android:name=".AlarmReceiver"
            android:enabled="true"
            android:exported="true" />

    </application>
</manifest>
"""


def write_manifest(out_dir):
    """写出 AndroidManifest.xml 到指定目录（供 buildozer 使用）。"""
    path = os.path.join(out_dir, "AndroidManifest.xml")
    os.makedirs(out_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(MANIFEST_TEMPLATE)
    return path


# Java 接收器源码（buildozer 可编译进 apk）
BOOT_RECEIVER_JAVA = r"""
package com.elderlyhealth.pillreminder;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.util.Log;

public class BootReceiver extends BroadcastReceiver {
    private static final String TAG = "PillReminder";

    @Override
    public void onReceive(Context context, Intent intent) {
        Log.d(TAG, "Boot completed, rescheduling alarms");
        // 通知 Python 端重新注册所有闹钟
        Intent serviceIntent = new Intent(context, org.kivy.android.PythonService.class);
        context.startService(serviceIntent);
    }
}
"""

ALARM_RECEIVER_JAVA = r"""
package com.elderlyhealth.pillreminder;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.util.Log;

public class AlarmReceiver extends BroadcastReceiver {
    private static final String TAG = "PillReminder";

    @Override
    public void onReceive(Context context, Intent intent) {
        Log.d(TAG, "Alarm fired");
        // 启动主 Activity 弹出提醒
        Intent activityIntent = new Intent(context, org.kivy.android.PythonActivity.class);
        activityIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        context.startActivity(activityIntent);
    }
}
"""


def write_java_receivers(out_dir):
    jd = os.path.join(out_dir, "src", "com", "elderlyhealth", "pillreminder")
    os.makedirs(jd, exist_ok=True)
    with open(os.path.join(jd, "BootReceiver.java"), "w") as f:
        f.write(BOOT_RECEIVER_JAVA)
    with open(os.path.join(jd, "AlarmReceiver.java"), "w") as f:
        f.write(ALARM_RECEIVER_JAVA)
    return jd


if __name__ == "__main__":
    import sys
    d = sys.argv[1] if len(sys.argv) > 1 else "/tmp/manifest_out"
    print("manifest:", write_manifest(d))
    print("java:", write_java_receivers(d))
