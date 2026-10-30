# -*- coding: utf-8 -*-
"""
打包脚本：把 Python 源码 + 资源组织成 buildozer 需要的目录结构，
并生成一份「一键打包」说明，让有安卓环境的电脑能直接产出 apk。
"""
import os
import shutil
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "packaged")
PKG_NAME = "pillreminder"

if os.path.exists(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)

# 1. 复制源码
shutil.copytree(os.path.join(ROOT, "pill_app"),
                os.path.join(OUT, "pill_app"))
# 2. 复制资源
shutil.copytree(os.path.join(ROOT, "assets"),
                os.path.join(OUT, "assets"))
# 3. 复制构建配置
shutil.copy(os.path.join(ROOT, "buildozer.spec"),
            os.path.join(OUT, "buildozer.spec"))
# 4. 复制打包脚本自身
shutil.copy(os.path.join(ROOT, "tools", "pack_android.py"),
            os.path.join(OUT, "pack_android.py"))

# 5. 写入一键打包脚本（Windows/Mac/Linux 通用）
with open(os.path.join(OUT, "打包.bat" if os.name == "nt" else "打包.sh"), "w") as f:
    if os.name == "nt":
        f.write("@echo off\nbuildozer android debug\npause\n")
    else:
        f.write("#!/bin/bash\ncd \"$(dirname \"$0\")\"\nbuildozer android debug\n")

# 6. 生成图标到 res 目录（兼容安卓 mipmap）
res_dir = os.path.join(OUT, "res", "mipmap")
os.makedirs(res_dir, exist_ok=True)
for s in (48, 72, 96, 144, 192):
    src = os.path.join(ROOT, "assets", "icon_%d.png" % s)
    if os.path.exists(src):
        shutil.copy(src, os.path.join(res_dir, "ic_launcher.png"))

# 7. README
readme = os.path.join(OUT, "打包说明.txt")
with open(readme, "w", encoding="utf-8") as f:
    f.write("""用药提醒 App —— 安卓打包说明
================================

【本目录内容】
- pill_app/        : 全部 Python 源码
- assets/         : 图标、药品默认图、闹铃音、语音提示音
- buildozer.spec  : 安卓构建配置（已配好，一般不用改）
- res/mipmap/     : 应用图标（5 种尺寸）
- 打包.sh / 打包.bat : 一键打包脚本

【打包步骤（只需要做一次）】

第一步：安装环境
  - 安装 Python 3.8 以上
  - 安装 Java JDK 17（必须 17，不能用 11）
    下载：https://adoptium.net/temurin/releases/
  - 安装 Buildozer（它会自动下载 Android SDK/NDK）
    pip install buildozer

第二步：连接手机
  - 手机打开「开发者选项」→「USB 调试」
  - 用数据线连到电脑，弹窗选「允许」
  - 命令行执行：adb devices
    能看到设备号就说明连好了

第三步：开始打包
  - 双击「打包.sh」（Mac/Linux）或「打包.bat」（Windows）
  - 第一次会下载 Android SDK/NDK，可能需要 20-40 分钟
  - 之后每次约 5-10 分钟
  - 完成后会在 .buildozer/bin/ 目录下生成：
    用药提醒-1.0.0-debug.apk

第四步：装到手机
  - 把 apk 文件传到手机，点击安装
  - 第一次安装会提示「未知来源应用」，允许即可
  - 华为手机：安装后去「手机管家」→「应用启动管理」→ 找到「用药提醒」
    → 关闭自动管理 → 打开「允许自启动 / 允许后台活动 / 允许锁屏显示」

【常见问题】
Q: 闹钟到点不响？
A: 检查电池优化是否关闭、是否允许自启动、是否允许后台活动。
   这是安卓系统的通病，不是 App 的问题。

Q: 能不能用 Android Studio 打开？
A: 可以。buildozer 会生成 .buildozer/android/platform/ 下的 gradle 项目，
   用 Android Studio 打开即可。

Q: 想要更简单的办法？
A: 用「一键打包网站」：GitHub 上搜 buildozer cloud build，
   上传整个文件夹，在线编译，下载 apk。

【技术支持】
源码采用 Python + Kivy 框架，全部开源可改。
老年人专用设计：大字体、大按钮、高对比配色。
""")

# 8. 打包成 zip
zip_path = os.path.join(ROOT, "用药提醒App_完整源码.zip")
if os.path.exists(zip_path):
    os.remove(zip_path)
# 排除缓存目录
EXCLUDE = {"__pycache__", ".pytest_cache", ".git", ".buildozer"}

def _zip_dir(zf, src, arcroot):
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in EXCLUDE]
        for fn in files:
            full = os.path.join(root, fn)
            arc = os.path.join(arcroot, os.path.relpath(full, src))
            zf.write(full, arc)

with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    _zip_dir(zf, OUT, PKG_NAME)

print("打包完成：", zip_path)
print("大小：%.1f KB" % (os.path.getsize(zip_path) / 1024))
print("\n目录结构：")
for root, dirs, files in os.walk(OUT):
    d = os.path.relpath(root, OUT)
    if d == ".":
        d = "(根)"
    print("  " + d + "/")
    for fn in files:
        print("    " + fn)
