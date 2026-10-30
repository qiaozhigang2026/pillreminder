[app]

# 应用基本信息
title = 用药提醒
package.name = pillreminder
package.domain = com.elderlyhealth
version = 1.0.0
numeric_version = 1000

# 源码：main.py 与 pill_app 目录
source.dir = .
source.include_exts = py,png,jpg,kv,wav,json,ttf
source.exclude_exts = spec,pyc
source.exclude_dirs = tests, bin, .buildozer
source.include_patterns = pill_app/*,assets/*,data/*
main.source = pill_app/main.py

# 应用资源
presplash.filename = assets/icon.png
icon.filename = assets/icon.png
orientation = portrait
fullscreen = 0
android.arch = arm64-v8a

# 依赖：python3 与这些纯 python 包
requirements = python3,kivy,sqlite3,jnius

# 安卓 SDK 配置
android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25b
android.private_storage = True
android.accept_sdk_license = True

# 权限
android.permissions = WAKE_LOCK,VIBRATE,RECEIVE_BOOT_COMPLETED,POST_NOTIFICATIONS,FOREGROUND_SERVICE,SCHEDULE_EXACT_ALARM,USE_EXACT_ALARM,READ_EXTERNAL_STORAGE,READ_MEDIA_IMAGES,INTERNET
android.features =
android.manifest.intent_filters =

# 服务：前台保活服务
android.services = reminder:service_main.py

# 开机自启
android.broadcast_receivers = BootReceiver

# 主题
android.theme = @android:style/Theme.NoTitleBar.Fullscreen
android.windowSoftInputMode = adjustResize
android.launchMode = singleTop

[buildozer]

log_level = 2
warn_on_root = 1
log_dir = .buildozer/logs
bin_dir = .buildozer/bin

# 本地构建（无 SDK 时启用此模式，仅生成中间产物）
android.skip_update = False
