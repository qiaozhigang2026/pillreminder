# -*- coding: utf-8 -*-
"""
用药提醒 App - 安卓主入口
老年人专用设计：
- 大字体（默认 22sp，可放大到 30sp）
- 高对比配色，主色为深绿 #1E8460
- 每个按钮都够大，间距宽松
- 关键操作有震动反馈
"""
import os

os.environ.setdefault("KIVY_NO_ARGS", "1")
os.environ.setdefault("KIVY_NO_CONSOLELOG", "1")

from kivy.app import App
from kivy.config import Config
from kivy.core.window import Window
from kivy import platform

# 竖屏锁定
Config.set("graphics", "resizable", "0")
Config.set("graphics", "width", "400")
Config.set("graphics", "height", "760")

from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.image import Image as KImage
from kivy.uix.widget import Widget
from kivy.clock import Clock, mainthread
from kivy.properties import StringProperty, NumericProperty, ObjectProperty
from kivy.utils import get_color_from_hex
from kivy.lang import Builder

from storage import (
    list_medicines, save_medicine, delete_medicine,
    load_schedules, save_schedule, delete_schedule,
    add_log, load_logs,
)
from scheduler import (
    next_fire_time, upcoming, today_schedules,
    format_time, format_datetime, period_label,
)
from alarm_service import get_alarm_service
from notifications import ensure_channels, show_reminder_notification

# 加载 kv 界面定义
KV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui.kv")
if os.path.exists(KV_PATH):
    Builder.load_file(KV_PATH)

# ==================== 主题色 ====================
COLOR_PRIMARY = "1E8460"
COLOR_PRIMARY_DARK = "156149"
COLOR_ACCENT = "FFD13B"
COLOR_BG = "F0F9F5"
COLOR_CARD = "FFFFFF"
COLOR_TEXT = "1F2A24"
COLOR_TEXT_SUB = "5C6B64"
COLOR_RED = "D9434B"
COLOR_GREEN = "2E9E5B"


def hex2(c):
    return get_color_from_hex(c)


# ==================== 全局字号（老年人可放大） ====================
class FontScale(object):
    SIZES = {"标准": 18, "大": 22, "特大": 28}
    current = "大"

    @classmethod
    def base(cls):
        return cls.SIZES[cls.current]

    @classmethod
    def of(cls, key):
        """按语义取字号：title / subtitle / body / big / huge"""
        table = {
            "标准": {"title": 24, "subtitle": 20, "body": 18, "big": 30, "huge": 42, "btn": 20, "chip": 16},
            "大":   {"title": 30, "subtitle": 24, "body": 22, "big": 38, "huge": 54, "btn": 26, "chip": 20},
            "特大": {"title": 38, "subtitle": 30, "body": 28, "big": 48, "huge": 68, "btn": 32, "chip": 24},
        }
        return table[cls.current][key]


# ==================== 主屏幕：今日服药列表 ====================
class HomeScreen(Screen):
    def on_enter(self, *args):
        self.refresh()

    def refresh(self):
        layout = self.ids.get("list_layout")
        if layout is None:
            return
        layout.clear_widgets()

        # 顶部问候
        from datetime import datetime
        h = datetime.now().hour
        greet = "早上好"
        if h >= 12: greet = "下午好"
        if h >= 18: greet = "晚上好"
        greet_lbl = BigLabel(text="[b]%s[/b]" % greet, size_hint_y=None, height=60)
        layout.add_widget(greet_lbl)

        sub = BigLabel(text="今天是服药日，请按时服药", subtitle=True, size_hint_y=None, height=40)
        layout.add_widget(sub)

        items = today_schedules()
        if not items:
            empty = EmptyState()
            layout.add_widget(empty)

        for it in items:
            card = TodayCard(it)
            layout.add_widget(card)

        # 底部留白 + 添加按钮提示
        layout.add_widget(Widget(size_hint_y=None, height=20))


# ==================== 药品库屏幕 ====================
class MedicineScreen(Screen):
    def on_enter(self, *args):
        self.refresh()

    def refresh(self):
        layout = self.ids.get("med_layout")
        if layout is None:
            return
        layout.clear_widgets()
        meds = list_medicines()
        if not meds:
            layout.add_widget(EmptyState(text="还没有药品\n点击右上角添加"))
            return
        for m in meds:
            layout.add_widget(MedicineRow(m))


# ==================== 记录屏幕 ====================
class LogScreen(Screen):
    def on_enter(self, *args):
        self.refresh()

    def refresh(self):
        layout = self.ids.get("log_layout")
        if layout is None:
            return
        layout.clear_widgets()
        from storage import list_medicines
        meds = {m["id"]: m for m in list_medicines()}
        logs = sorted(load_logs(), key=lambda x: x.get("ts", 0), reverse=True)
        if not logs:
            layout.add_widget(EmptyState(text="还没有服药记录"))
            return
        # 按日期分组
        from datetime import datetime, date
        last_date = None
        for l in logs[:60]:
            d = datetime.fromtimestamp(l.get("ts", 0)).date()
            if d != last_date:
                last_date = d
                is_today = (d == date.today())
                layout.add_widget(DateHeader(d, is_today))
            m = meds.get(l.get("medicine_id"), {"name": "未知药品"})
            layout.add_widget(LogRow(l, m))


# ==================== 设置屏幕 ====================
class SettingsScreen(Screen):
    pass


# ==================== 提醒弹窗（覆盖式全屏）====================
class ReminderPopup(FloatLayout):
    """全屏覆盖式提醒，显示药品图片与用量。持续响 60 秒或直到按「已服用」。"""
    current_item = None

    def open(self, item):
        self.current_item = item
        med = item["medicine"]
        self.ids.pop_img.source = med.get("image") or "assets/pill_default.png"
        self.ids.pop_name.text = med.get("name", "药品")
        self.ids.pop_dose.text = "用量：%s" % item["schedule"].get("dose", "按医嘱")
        self.ids.pop_time.text = format_time(item["fire_ts"])
        self.ids.popup_root.opacity = 1
        self.ids.popup_root.disabled = False
        # 震动反馈
        App.get_running_app().haptic()

    def close(self):
        self.ids.popup_root.opacity = 0
        self.ids.popup_root.disabled = True

    def on_taken(self):
        item = self.current_item
        if item:
            add_log(item["medicine"]["id"], item["schedule"].get("dose", ""))
            App.get_running_app().toast("已记录服药")
        get_alarm_service().stop()
        self.close()
        App.get_running_app().sm.current = "home"

    def on_snooze(self):
        get_alarm_service().stop()
        self.close()
        App.get_running_app().toast("10 分钟后再次提醒")
        from kivy.clock import Clock as _C
        _C.schedule_once(lambda dt: App.get_running_app().fire_test_reminder(), 600)


# ==================== 自定义大字体控件 ====================
class BigLabel(Label):
    def __init__(self, text="", subtitle=False, **kw):
        kw.setdefault("markup", True)
        kw.setdefault("color", hex2(COLOR_TEXT_SUB if subtitle else COLOR_TEXT))
        kw.setdefault("halign", "left")
        kw.setdefault("valign", "middle")
        kw.setdefault("font_size", str(FontScale.of("subtitle" if subtitle else "title")) + "sp")
        kw.setdefault("text_size", (None, None))
        if "size_hint_y" not in kw:
            kw["size_hint_y"] = None
        super().__init__(text=text, **kw)


# ==================== 今日卡片 ====================
class TodayCard(BoxLayout):
    def __init__(self, item, **kw):
        kw.setdefault("orientation", "horizontal")
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", "90dp")
        kw.setdefault("spacing", "12dp")
        kw.setdefault("padding", ["12dp", "10dp"])
        super().__init__(**kw)
        self.item = item
        med = item["medicine"]
        sch = item["schedule"]

        self.bind(minimum_height=lambda *a: None)

        # 图片
        img = KImage(source=med.get("image") or "assets/pill_default.png",
                     size_hint=(None, None), size=("64dp", "64dp"),
                     allow_stretch=True, keep_ratio=True)
        self.add_widget(img)

        # 中间文字
        mid = BoxLayout(orientation="vertical", spacing="4dp", size_hint_x=1)
        name = Label(text="[b]%s[/b]" % med.get("name", ""),
                     markup=True, color=hex2(COLOR_TEXT),
                     font_size=str(FontScale.of("subtitle")) + "sp",
                     halign="left", valign="middle", size_hint_y=0.5)
        name.bind(size=lambda s, v: setattr(s, "text_size", (s.width, None)))
        mid.add_widget(name)

        dose = Label(text="用量：%s" % sch.get("dose", ""), color=hex2(COLOR_TEXT_SUB),
                     font_size=str(FontScale.of("body")) + "sp",
                     halign="left", valign="middle", size_hint_y=0.5)
        dose.bind(size=lambda s, v: setattr(s, "text_size", (s.width, None)))
        mid.add_widget(dose)
        self.add_widget(mid)

        # 右侧时间
        right = BoxLayout(orientation="vertical", size_hint=(None, None), width="90dp", spacing="4dp")
        t = Label(text="[b]%s[/b]" % format_time(item["fire_ts"]),
                  markup=True, color=hex2(COLOR_PRIMARY),
                  font_size=str(FontScale.of("big")) + "sp",
                  halign="right", valign="middle")
        right.add_widget(t)
        per = Label(text=period_label(sch), color=hex2(COLOR_TEXT_SUB),
                    font_size=str(FontScale.of("chip")) + "sp",
                    halign="right", valign="middle")
        right.add_widget(per)
        self.add_widget(right)


# ==================== 药品行 ====================
class MedicineRow(BoxLayout):
    def __init__(self, med, **kw):
        kw.setdefault("orientation", "horizontal")
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", "80dp")
        kw.setdefault("spacing", "12dp")
        kw.setdefault("padding", ["12dp", "8dp"])
        super().__init__(**kw)
        self.med = med

        img = KImage(source=med.get("image") or "assets/pill_default.png",
                     size_hint=(None, None), size=("56dp", "56dp"),
                     allow_stretch=True, keep_ratio=True)
        self.add_widget(img)

        mid = BoxLayout(orientation="vertical", size_hint_x=1, spacing="2dp")
        name = Label(text="[b]%s[/b]" % med.get("name", ""), markup=True,
                     color=hex2(COLOR_TEXT), font_size=str(FontScale.of("subtitle")) + "sp",
                     halign="left", valign="middle", size_hint_y=0.55)
        name.bind(size=lambda s, v: setattr(s, "text_size", (s.width, None)))
        mid.add_widget(name)
        note = med.get("note") or ""
        if note:
            n = Label(text=note, color=hex2(COLOR_TEXT_SUB),
                      font_size=str(FontScale.of("body")) + "sp",
                      halign="left", valign="middle", size_hint_y=0.45)
            n.bind(size=lambda s, v: setattr(s, "text_size", (s.width, None)))
            mid.add_widget(n)
        self.add_widget(mid)

        btn = BigButton(text="添加\n提醒", size_hint=(None, None),
                        size=("72dp", "56dp"), font_size=str(FontScale.of("chip")) + "sp")
        btn.bind(on_release=lambda x: App.get_running_app().open_add_schedule(med))
        self.add_widget(btn)


# ==================== 空状态 ====================
class EmptyState(BoxLayout):
    def __init__(self, text="还没有内容", **kw):
        kw.setdefault("orientation", "vertical")
        kw.setdefault("spacing", "16dp")
        kw.setdefault("padding", ["20dp", "40dp"])
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", "300dp")
        super().__init__(**kw)
        img = KImage(source="assets/onboard.png", size_hint=(1, 0.6))
        self.add_widget(img)
        lbl = Label(text=text, color=hex2(COLOR_TEXT_SUB),
                    font_size=str(FontScale.of("subtitle")) + "sp",
                    halign="center", size_hint_y=0.4)
        self.add_widget(lbl)


# ==================== 日期分组头 ====================
class DateHeader(BoxLayout):
    def __init__(self, d, is_today=False, **kw):
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", "44dp")
        kw.setdefault("padding", ["12dp", 0])
        super().__init__(**kw)
        from datetime import date
        wk = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        text = "今天" if is_today else ("%d月%d日 %s" % (d.month, d.day, wk[d.weekday()]))
        self.add_widget(Label(text="[b]%s[/b]" % text, markup=True,
                              color=hex2(COLOR_PRIMARY),
                              font_size=str(FontScale.of("subtitle")) + "sp",
                              halign="left"))


# ==================== 记录行 ====================
class LogRow(BoxLayout):
    def __init__(self, log, med, **kw):
        kw.setdefault("orientation", "horizontal")
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", "56dp")
        kw.setdefault("spacing", "10dp")
        kw.setdefault("padding", ["12dp", "6dp"])
        super().__init__(**kw)
        img = KImage(source=med.get("image") or "assets/pill_default.png",
                     size_hint=(None, None), size=("40dp", "40dp"),
                     allow_stretch=True, keep_ratio=True)
        self.add_widget(img)
        mid = BoxLayout(orientation="vertical", size_hint_x=1)
        name = Label(text=med.get("name", ""), color=hex2(COLOR_TEXT),
                     font_size=str(FontScale.of("body")) + "sp",
                     halign="left", valign="middle", size_hint_y=0.5)
        name.bind(size=lambda s, v: setattr(s, "text_size", (s.width, None)))
        mid.add_widget(name)
        dose = Label(text=log.get("dose", ""), color=hex2(COLOR_TEXT_SUB),
                     font_size=str(FontScale.of("chip")) + "sp",
                     halign="left", valign="middle", size_hint_y=0.5)
        dose.bind(size=lambda s, v: setattr(s, "text_size", (s.width, None)))
        mid.add_widget(dose)
        self.add_widget(mid)
        t = Label(text=format_time(log.get("ts", 0)), color=hex2(COLOR_PRIMARY),
                  font_size=str(FontScale.of("body")) + "sp",
                  halign="right", size_hint=(None, None), width="60dp")
        self.add_widget(t)


# ==================== 大按钮 ====================
class BigButton(Button):
    def __init__(self, **kw):
        kw.setdefault("background_normal", "")
        kw.setdefault("background_color", hex2(COLOR_PRIMARY))
        kw.setdefault("color", (1, 1, 1, 1))
        kw.setdefault("bold", True)
        if "font_size" not in kw:
            kw["font_size"] = str(FontScale.of("btn")) + "sp"
        super().__init__(**kw)

    def on_release(self):
        App.get_running_app().haptic()


# ==================== 主应用 ====================
class PillApp(App):
    def build(self):
        self.icon = "assets/icon.png"
        # 全局字号
        from kivy.metrics import dp
        # 屏幕管理器
        self.sm = ScreenManager(transition=SlideTransition(duration=0.25))
        self.sm.add_widget(HomeScreen(name="home"))
        self.sm.add_widget(MedicineScreen(name="medicines"))
        self.sm.add_widget(LogScreen(name="logs"))
        self.sm.add_widget(SettingsScreen(name="settings"))

        root = FloatLayout()
        root.add_widget(self.sm)

        # 提醒弹窗层（始终在最上层）
        self.popup = ReminderPopup()
        self.popup.close()
        root.add_widget(self.popup)

        # 状态栏
        self._status = Label(text="", size_hint=(1, None), height="32dp",
                             pos_hint={"x": 0, "top": 1}, color=(1, 1, 1, 0.95),
                             font_size="16sp", halign="center")
        # 不添加到 root，避免挡内容
        return root

    def on_start(self):
        ensure_channels()
        # 前台服务保活
        if platform == "android":
            try:
                from service_main import start_foreground_service
                start_foreground_service()
            except Exception as e:
                print("[App] foreground service error:", e)
        # 启动后台检查循环
        Clock.schedule_interval(self._check_reminders, 15)
        Clock.schedule_once(lambda dt: self._check_reminders(0), 2)

    def _check_reminders(self, dt):
        """每 15 秒检查一次：是否有到点的提醒。"""
        from time import time
        now = int(time())
        for it in upcoming(limit=5):
            ts = it["fire_ts"]
            # 在 60 秒窗口内认为到时
            if abs(ts - now) <= 60:
                # 避免重复触发
                if getattr(self, "_last_fire", 0) == ts:
                    continue
                self._last_fire = ts
                self._show_reminder(it)
                break

    def _show_reminder(self, item):
        med = item["medicine"]
        show_reminder_notification(
            "服药时间到",
            "%s  用量：%s" % (med.get("name", "药品"), item["schedule"].get("dose", "")),
            item["fire_ts"],
        )
        self.popup.open(item)
        get_alarm_service().start(on_stop=lambda: None)
        # 自动切到首页，弹窗是覆盖层不受屏幕影响
        self.sm.current = "home"

    # ---------- 公开方法 ----------
    def open_add_medicine(self):
        self._open_form("medicine", None)

    def open_add_schedule(self, medicine):
        self._open_form("schedule", medicine)

    def _open_form(self, kind, obj):
        """打开添加表单。简化版：用 Popup 承载。"""
        from kivy.uix.popup import Popup
        if kind == "medicine":
            content = MedicineForm()
        else:
            content = ScheduleForm(obj)
        content.app = self
        p = Popup(title="添加药品" if kind == "medicine" else "添加提醒",
                  content=content, size_hint=(0.92, 0.85),
                  title_size=str(FontScale.of("subtitle")) + "sp",
                  title_color=hex2(COLOR_TEXT))
        content.popup = p
        p.open()

    def fire_test_reminder(self, dt=None):
        """测试提醒：取第一个即将到来的计划弹出。"""
        items = today_schedules()
        if not items:
            from time import time
            items = upcoming(limit=3)
            if not items:
                self.toast("请先添加药品和提醒")
                return
        self._show_reminder(items[0])

    def haptic(self):
        """震动反馈。"""
        if platform == "android":
            try:
                from jnius import autoclass
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                activity = PythonActivity.mActivity
                vibrator = activity.getSystemService(autoclass("android.content.Context").VIBRATOR_SERVICE)
                vibrator.vibrate(30)
            except Exception:
                pass

    def toast(self, msg):
        if platform == "android":
            try:
                from jnius import autoclass
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                Toast = autoclass("android.widget.Toast")
                Toast.makeText(PythonActivity.mActivity, msg, Toast.LENGTH_SHORT).show()
            except Exception:
                pass
        print("[Toast]", msg)


# ==================== 表单：添加药品 ====================
class MedicineForm(BoxLayout):
    popup = None
    app = None

    def __init__(self, **kw):
        kw.setdefault("orientation", "vertical")
        kw.setdefault("spacing", "16dp")
        kw.setdefault("padding", ["20dp", "20dp"])
        super().__init__(**kw)
        self._build()

    def _build(self):
        self.add_widget(Label(text="药品名称", color=hex2(COLOR_TEXT),
                              font_size=str(FontScale.of("body")) + "sp",
                              halign="left", size_hint_y=None, height="32dp"))
        self.name_input = TextInput(hint_text="如：降压药、维生素D",
                                    font_size=str(FontScale.of("subtitle")) + "sp",
                                    size_hint_y=None, height="56dp",
                                    multiline=False)
        self.add_widget(self.name_input)

        self.add_widget(Label(text="用量说明", color=hex2(COLOR_TEXT),
                              font_size=str(FontScale.of("body")) + "sp",
                              halign="left", size_hint_y=None, height="32dp"))
        self.dose_input = TextInput(hint_text="如：每次1粒，饭后服用",
                                    font_size=str(FontScale.of("body")) + "sp",
                                    size_hint_y=None, height="56dp", multiline=False)
        self.add_widget(self.dose_input)

        self.add_widget(Label(text="药品图片", color=hex2(COLOR_TEXT),
                              font_size=str(FontScale.of("body")) + "sp",
                              halign="left", size_hint_y=None, height="32dp"))
        # 图片选择按钮
        pic_box = BoxLayout(orientation="horizontal", size_hint_y=None, height="100dp", spacing="12dp")
        self.pic_img = KImage(source="assets/pill_default.png", size_hint=(None, None),
                              size=("84dp", "84dp"), allow_stretch=True, keep_ratio=True)
        pic_box.add_widget(self.pic_img)
        pic_btn = BigButton(text="拍照 / 选图", size_hint=(1, None), height="64dp")
        pic_btn.bind(on_release=self._pick_image)
        pic_box.add_widget(pic_btn)
        self.add_widget(pic_box)
        self.picked_image = None

        # 保存按钮
        save = BigButton(text="保存", size_hint_y=None, height="64dp",
                         background_color=hex2(COLOR_PRIMARY))
        save.bind(on_release=self._save)
        self.add_widget(save)

    def _pick_image(self, *args):
        """调用安卓图片选择器。"""
        from kivy import platform as pf
        if pf == "android":
            try:
                from jnius import autoclass
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                Intent = autoclass("android.content.Intent")
                activity = PythonActivity.mActivity
                intent = Intent(Intent.ACTION_GET_CONTENT)
                intent.setType("image/*")
                activity.startActivityForResult(intent, 1001)
                # 注意：回调需自行处理，此处简化为提示
                self.app.toast("请在系统选择器中选图")
            except Exception as e:
                self.app.toast("选图失败")
        else:
            self.app.toast("桌面测试：图片已用默认图标")

    def _save(self, *args):
        name = self.name_input.text.strip()
        if not name:
            self.app.toast("请填写药品名称")
            return
        med = {
            "name": name,
            "note": self.dose_input.text.strip(),
            "image": self.picked_image or "assets/pill_default.png",
            "color": (30, 132, 96),
        }
        save_medicine(med)
        self.app.toast("已保存")
        screens = self.app.sm.children
        self.popup.dismiss()
        self.app.sm.get_screen("home").refresh()
        self.app.sm.get_screen("medicines").refresh()


# ==================== 表单：添加提醒 ====================
class ScheduleForm(BoxLayout):
    popup = None
    app = None

    PERIODS = [
        ("每天", "everyday"),
        ("隔天", "every2days"),
        ("每周", "weekly"),
        ("每月", "monthly"),
    ]
    WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]

    def __init__(self, medicine, **kw):
        self.medicine = medicine
        kw.setdefault("orientation", "vertical")
        kw.setdefault("spacing", "14dp")
        kw.setdefault("padding", ["20dp", "20dp"])
        super().__init__(**kw)
        self._period = "everyday"
        self._weekdays = []
        self._monthdays = []
        self._build()

    def _build(self):
        # 药品名
        self.add_widget(Label(text="药品：[b]%s[/b]" % self.medicine.get("name", ""),
                              markup=True, color=hex2(COLOR_PRIMARY),
                              font_size=str(FontScale.of("subtitle")) + "sp",
                              halign="left", size_hint_y=None, height="36dp"))

        # 提醒时间
        self.add_widget(Label(text="提醒时间", color=hex2(COLOR_TEXT),
                              font_size=str(FontScale.of("body")) + "sp",
                              halign="left", size_hint_y=None, height="30dp"))
        self.time_input = TextInput(text="08:00", size_hint_y=None, height="56dp",
                                    font_size=str(FontScale.of("big")) + "sp",
                                    multiline=False, halign="center")
        self.add_widget(self.time_input)

        # 用量
        self.add_widget(Label(text="每次用量", color=hex2(COLOR_TEXT),
                              font_size=str(FontScale.of("body")) + "sp",
                              halign="left", size_hint_y=None, height="30dp"))
        self.dose_input = TextInput(text="1粒", size_hint_y=None, height="56dp",
                                    font_size=str(FontScale.of("subtitle")) + "sp",
                                    multiline=False, halign="center")
        self.add_widget(self.dose_input)

        # 周期
        self.add_widget(Label(text="服药周期", color=hex2(COLOR_TEXT),
                              font_size=str(FontScale.of("body")) + "sp",
                              halign="left", size_hint_y=None, height="30dp"))
        self.period_box = BoxLayout(orientation="horizontal", size_hint_y=None, height="56dp", spacing="8dp")
        for label, val in self.PERIODS:
            tb = ToggleButton(text=label, group="period", size_hint_x=1,
                              font_size=str(FontScale.of("chip")) + "sp", bold=True)
            if val == "everyday":
                tb.state = "down"
            tb.bind(on_release=lambda btn, v=val: self._set_period(v))
            self.period_box.add_widget(tb)
        self.add_widget(self.period_box)

        # 每周 / 每月 选择区
        self.detail_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing="10dp")
        self.detail_box.bind(minimum_height=self.detail_box.setter("height"))
        self.add_widget(self.detail_box)
        self._render_detail()

        # 保存
        save = BigButton(text="保存提醒", size_hint_y=None, height="64dp")
        save.bind(on_release=self._save)
        self.add_widget(save)

    def _set_period(self, val):
        self._period = val
        self._render_detail()

    def _render_detail(self):
        self.detail_box.clear_widgets()
        if self._period == "weekly":
            self.detail_box.add_widget(Label(text="选择星期（可多选）", color=hex2(COLOR_TEXT_SUB),
                                             font_size=str(FontScale.of("body")) + "sp",
                                             halign="left", size_hint_y=None, height="30dp"))
            grid = GridLayout(cols=7, spacing="6dp", size_hint_y=None, height="52dp")
            self._wd_btns = []
            for i, w in enumerate(self.WEEKDAYS):
                tb = ToggleButton(text=w, size_hint_x=1,
                                  font_size=str(FontScale.of("chip")) + "sp", bold=True)
                tb.bind(on_release=lambda btn, idx=i: self._toggle_weekday(idx, btn))
                self._wd_btns.append(tb)
                grid.add_widget(tb)
            self.detail_box.add_widget(grid)
        elif self._period == "monthly":
            self.detail_box.add_widget(Label(text="选择日期（可多选，如 1、15）", color=hex2(COLOR_TEXT_SUB),
                                             font_size=str(FontScale.of("body")) + "sp",
                                             halign="left", size_hint_y=None, height="30dp"))
            self.md_input = TextInput(hint_text="用逗号分隔，如：1,15",
                                      size_hint_y=None, height="52dp",
                                      font_size=str(FontScale.of("subtitle")) + "sp",
                                      multiline=False, halign="center")
            self.detail_box.add_widget(self.md_input)

    def _toggle_weekday(self, idx, btn):
        if btn.state == "down":
            if idx not in self._weekdays:
                self._weekdays.append(idx)
        else:
            if idx in self._weekdays:
                self._weekdays.remove(idx)

    def _save(self, *args):
        time_str = self.time_input.text.strip()
        if not _is_valid_time(time_str):
            self.app.toast("时间格式应为 HH:MM，如 08:00")
            return
        sch = {
            "medicine_id": self.medicine.get("id"),
            "time": time_str,
            "period": self._period,
            "dose": self.dose_input.text.strip() or "按医嘱",
            "enabled": True,
        }
        if self._period == "weekly":
            if not self._weekdays:
                self.app.toast("请至少选择一个星期")
                return
            sch["weekdays"] = sorted(self._weekdays)
        if self._period == "monthly":
            mds = _parse_monthdays(getattr(self, "md_input", None) and self.md_input.text or "")
            if not mds:
                self.app.toast("请填写日期，如 1,15")
                return
            sch["monthdays"] = mds
        save_schedule(sch)
        self.app.toast("提醒已保存")
        self.popup.dismiss()
        self.app.sm.get_screen("home").refresh()


def _is_valid_time(s):
    try:
        hh, mm = s.split(":")
        hh, mm = int(hh), int(mm)
        return 0 <= hh < 24 and 0 <= mm < 60 and len(hh) <= 2
    except Exception:
        return False


def _parse_monthdays(s):
    out = []
    for p in s.replace("，", ",").split(","):
        p = p.strip()
        if p.isdigit():
            d = int(p)
            if 1 <= d <= 31:
                out.append(d)
    return sorted(set(out))


# ==================== 前台服务（保活）====================
def start_foreground_service():
    from jnius import autoclass
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    activity = PythonActivity.mActivity
    Intent = autoclass("android.content.Intent")
    intent = Intent(activity, autoclass("org.kivy.android.PythonService"))
    intent.setClass(activity, autoclass("org.renpy.android.PythonService"))
    from notifications import start_foreground
    start_foreground(activity, "用药提醒正在运行", "保持提醒在后台正常运行")


# ==================== 启动 ====================
if __name__ == "__main__":
    PillApp().run()
