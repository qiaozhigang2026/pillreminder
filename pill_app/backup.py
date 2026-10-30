# -*- coding: utf-8 -*-
"""
数据备份：把药品、提醒计划、服药记录打包成一个 zip，
存到手机 Download 目录，方便换手机时迁移。
"""
import os
import zipfile
import time

from storage import DATA_DIR

BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backups")


def make_backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(BACKUP_DIR, "用药提醒备份_%s.zip" % ts)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(DATA_DIR):
            for fn in files:
                full = os.path.join(root, fn)
                zf.write(full, os.path.relpath(full, os.path.dirname(DATA_DIR)))
        # 同时把资源图一起打包
        asset_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
        if os.path.isdir(asset_dir):
            for fn in os.listdir(asset_dir):
                full = os.path.join(asset_dir, fn)
                if os.path.isfile(full):
                    zf.write(full, os.path.join("assets", fn))
    return path


def list_backups():
    if not os.path.isdir(BACKUP_DIR):
        return []
    files = [os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR) if f.endswith(".zip")]
    return sorted(files, key=lambda x: os.path.getmtime(x), reverse=True)
