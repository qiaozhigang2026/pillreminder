# -*- coding: utf-8 -*-
"""
闹铃 + 振动 + 语音服务。
- 闹铃：循环播放 alarm.wav，持续约 60 秒
- 振动：节奏性振动（响 800ms / 停 400ms）
- 语音：播放中文语音提示音（循环）
在 Android 上优先调用系统 TTS 与振动器；桌面测试环境则静默播放 WAV。
"""
import os
import time
import threading

from kivy.clock import mainthread
from kivy import platform

try:
    from kivy.core.audio import SoundLoader
except Exception:
    SoundLoader = None

try:
    from jnius import autoclass
except Exception:
    autoclass = None

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
AUDIO_DIR = os.path.join(ASSETS, "audio")


class AlarmService(object):
    DURATION = 60  # 秒

    def __init__(self):
        self._alarm_sound = None
        self._voice_sound = None
        self._vibrate_timer = None
        self._running = False
        self._started_at = 0
        self._on_stop_callback = None
        self._alarm_lock = threading.Lock()

    # ---------- 公共接口 ----------
    def start(self, on_stop=None):
        with self._alarm_lock:
            if self._running:
                return
            self._running = True
            self._started_at = time.time()
            self._on_stop_callback = on_stop
            self._play_alarm()
            self._play_voice()
            self._start_vibration()
            # 60 秒后自动停止，防止无限响
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: self.stop(silent=True), self.DURATION)

    def stop(self, silent=False):
        with self._alarm_lock:
            if not self._running:
                return
            self._running = False
            self._stop_vibration()
            self._stop_sound()
            cb = self._on_stop_callback
            self._on_stop_callback = None
        if cb and not silent:
            cb()

    @property
    def is_running(self):
        return self._running

    # ---------- 闹铃音 ----------
    def _play_alarm(self):
        path = os.path.join(AUDIO_DIR, "alarm.wav")
        if not os.path.exists(path):
            return
        try:
            snd = SoundLoader.load(path)
            if snd:
                snd.loop = True
                snd.volume = 1.0
                snd.play()
                self._alarm_sound = snd
        except Exception as e:
            print("[Alarm] sound error:", e)

    def _stop_sound(self):
        for attr in ("_alarm_sound", "_voice_sound"):
            snd = getattr(self, attr, None)
            if snd:
                try:
                    snd.stop()
                except Exception:
                    pass
                setattr(self, attr, None)

    # ---------- 语音提示 ----------
    def _play_voice(self):
        # Android 上用系统 TTS 播报中文
        if platform == "android" and autoclass is not None:
            try:
                self._android_speak("该吃药了，请按时服药")
            except Exception as e:
                print("[Alarm] tts error:", e)
        else:
            path = os.path.join(AUDIO_DIR, "prompt.wav")
            if os.path.exists(path):
                try:
                    snd = SoundLoader.load(path)
                    if snd:
                        snd.volume = 1.0
                        snd.play()
                        self._voice_sound = snd
                except Exception:
                    pass

    def _android_speak(self, text):
        Locale = autoclass("java.util.Locale")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
        tts = autoclass("android.speech.tts.TextToSpeech")
        self._tts = tts(activity, autoclass("android.speech.tts.TextToSpeech$OnInitListener"))
        self._tts.setLanguage(Locale.CHINESE)
        self._tts.speak(text, tts.QUEUE_FLUSH, None)

    # ---------- 振动 ----------
    def _start_vibration(self):
        if platform == "android" and autoclass is not None:
            try:
                self._android_vibrate()
                return
            except Exception as e:
                print("[Alarm] vibrate error:", e)
        # 桌面：用短蜂鸣节奏模拟
        self._schedule_vibrate_tick(0)

    def _android_vibrate(self):
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
        vibrator = activity.getSystemService(autoclass("android.content.Context").VIBRATOR_SERVICE)
        # 节奏：响 800ms / 停 400ms 循环
        pattern = [0, 800, 400, 800, 400, 800, 400, 800, 400,
                   800, 400, 800, 400, 800, 400, 800, 400,
                   800, 400, 800, 400, 800, 400, 800, 400,
                   800, 400, 800, 400, 800, 400, 800, 400]
        vibrator.vibrate(pattern, 1)

    def _stop_vibration(self):
        if platform == "android" and autoclass is not None:
            try:
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                activity = PythonActivity.mActivity
                vibrator = activity.getSystemService(autoclass("android.content.Context").VIBRATOR_SERVICE)
                vibrator.cancel()
            except Exception:
                pass

    def _schedule_vibrate_tick(self, n):
        if not self._running or n >= 20:
            return
        from kivy.clock import Clock
        try:
            snd = SoundLoader.load(os.path.join(AUDIO_DIR, "prompt.wav"))
            if snd:
                snd.volume = 0.4
                snd.play()
        except Exception:
            pass
        Clock.schedule_once(lambda dt: self._schedule_vibrate_tick(n + 1), 1.2)


# 单例
_service = None


def get_alarm_service():
    global _service
    if _service is None:
        _service = AlarmService()
    return _service
