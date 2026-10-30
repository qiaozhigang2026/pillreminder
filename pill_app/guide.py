# -*- coding: utf-8 -*-
"""
老年人使用引导（第一次启动时显示）。
三步引导，字号大、配图、步骤清晰。
"""
GUIDE_STEPS = [
    {
        "title": "第一步",
        "headline": "添加您的药品",
        "body": "点击首页「+ 添加药品」，输入药名，\n"
                "再给药品拍张照片，下次提醒就能认出来。",
        "icon": "assets/pill_default.png",
    },
    {
        "title": "第二步",
        "headline": "设置提醒时间",
        "body": "选择每天吃几次、几点吃。\n"
                "可以设每天、隔天、每周或每月。",
        "icon": "assets/pill_default.png",
    },
    {
        "title": "第三步",
        "headline": "按时服药",
        "body": "到时间会响铃、振动、语音提醒，\n"
                "看清药品照片后，点「已服用」就好。",
        "icon": "assets/pill_default.png",
    },
]


def get_steps():
    return GUIDE_STEPS
