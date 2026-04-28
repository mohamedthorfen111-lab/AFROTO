# main.py — The Ghost Architect
# ================================
# Architecture: 3-Layer System
# Layer 1: Sonic Radar (Audio Analysis)
# Layer 2: Performance Monitor (Real-time Dashboard)
# Layer 3: Haptic Feedback Engine

import threading
import time
import psutil
import numpy as np
from collections import deque

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard
from kivymd.uix.button import MDRaisedButton, MDIconButton
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle
from kivy.core.window import Window

# ── Android-specific imports (يشتغل بس على الأندرويد)
try:
    from jnius import autoclass
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Context        = autoclass('android.content.Context')
    Vibrator       = autoclass('android.os.Vibrator')
    VibrationEffect = autoclass('android.os.VibrationEffect')
    ANDROID = True
except Exception:
    ANDROID = False  # Desktop fallback للتطوير


# ════════════════════════════════════════════
# LAYER 1: SONIC RADAR ENGINE
# ════════════════════════════════════════════
class SonicRadarEngine:
    """
    يلتقط صوت النظام، يعزل ترددات الخطوات (800-1200Hz)
    ويحسب الاتجاه من الـ Stereo balance.
    """
    SAMPLE_RATE = 44100
    BUFFER_SIZE = 1024
    # نطاقات ترددية للأحداث التكتيكية
    FREQ_BANDS = {
        "footsteps": (600, 1400),
        "reload":    (1500, 3500),
        "explosion": (80,  400),
    }

    def __init__(self, callback):
        self.callback = callback  # دالة بتستقبل نتيجة التحليل
        self.running  = False
        self._thread  = None

    def start(self):
        self.running = True
        self._thread = threading.Thread(
            target=self._capture_loop, daemon=True
        )
        self._thread.start()

    def stop(self):
        self.running = False

    def _capture_loop(self):
        try:
            import sounddevice as sd

            def audio_callback(indata, frames, t, status):
                if not self.running:
                    return
                left  = indata[:, 0]
                right = indata[:, 1] if indata.shape[1] > 1 else left
                result = self._analyze(left, right)
                if result:
                    Clock.schedule_once(
                        lambda dt: self.callback(result), 0
                    )

            with sd.InputStream(
                samplerate=self.SAMPLE_RATE,
                blocksize=self.BUFFER_SIZE,
                channels=2,
                callback=audio_callback
            ):
                while self.running:
                    time.sleep(0.05)

        except Exception as e:
            print(f"[SonicRadar] Error: {e}")

    def _analyze(self, left, right):
        spectrum = np.abs(np.fft.rfft(left + right))
        freqs    = np.fft.rfftfreq(len(left + right),
                                    1 / self.SAMPLE_RATE)
        detected = {}

        for event, (lo, hi) in self.FREQ_BANDS.items():
            mask   = (freqs >= lo) & (freqs <= hi)
            energy = spectrum[mask].mean() if mask.any() else 0
            # Threshold ديناميكي بسيط
            if energy > 15.0:
                detected[event] = float(energy)

        if not detected:
            return None

        # تحديد الاتجاه من الـ Stereo balance
        l_rms = float(np.sqrt(np.mean(left**2)) + 1e-9)
        r_rms = float(np.sqrt(np.mean(right**2)) + 1e-9)
        ratio = r_rms / (l_rms + r_rms)  # 0.0 = يسار, 1.0 = يمين

        if ratio > 0.6:
            direction = "RIGHT"
        elif ratio < 0.4:
            direction = "LEFT"
        else:
            direction = "CENTER"

        return {
            "events":    detected,
            "direction": direction,
            "intensity": max(detected.values()),
        }


# ════════════════════════════════════════════
# LAYER 2: PERFORMANCE MONITOR
# ════════════════════════════════════════════
class PerformanceMonitor:
    """
    يجمع بيانات الأداء Real-time:
    CPU%, RAM%, درجة الحرارة، عدد العمليات النشطة
    """
    def __init__(self):
        self.history = {
            "cpu":  deque(maxlen=30),
            "ram":  deque(maxlen=30),
            "temp": deque(maxlen=30),
        }

    def snapshot(self) -> dict:
        cpu  = psutil.cpu_percent(interval=None)
        ram  = psutil.virtual_memory().percent
        temp = self._get_temp()
        procs = len(psutil.pids())

        self.history["cpu"].append(cpu)
        self.history["ram"].append(ram)
        self.history["temp"].append(temp)

        return {
            "cpu":   cpu,
            "ram":   ram,
            "temp":  temp,
            "procs": procs,
            # متوسط آخر 5 قراءات للـ Touch response estimate
            "touch_avg": round(
                sum(list(self.history["cpu"])[-5:]) /
                min(5, len(self.history["cpu"])), 1
            ),
        }

    def _get_temp(self) -> float:
        try:
            temps = psutil.sensors_temperatures()
            if not temps:
                return 0.0
            # نأخذ أعلى قراءة متاحة
            all_t = [t.current for v in temps.values() for t in v]
            return round(max(all_t), 1) if all_t else 0.0
        except Exception:
            return 0.0


# ════════════════════════════════════════════
# LAYER 3: HAPTIC FEEDBACK ENGINE
# ════════════════════════════════════════════
class HapticEngine:
    """
    يحول إشارات الرادار السمعي لاهتزازات اتجاهية
    """
    PATTERNS = {
        "LEFT":      [50, 30, 50],          # نبضتين قصيرتين
        "RIGHT":     [100],                  # نبضة طويلة
        "CENTER":    [30, 20, 30, 20, 30],  # ثلاث نبضات سريعة
        "footsteps": [40, 20, 40],
        "reload":    [200],
        "explosion": [500],
    }

    def vibrate(self, pattern_key: str):
        if not ANDROID:
            print(f"[Haptic] Pattern: {pattern_key}")
            return
        try:
            ctx      = PythonActivity.mActivity
            vibrator = ctx.getSystemService(Context.VIBRATOR_SERVICE)
            pattern  = self.PATTERNS.get(pattern_key, [100])
            timings  = [0] + pattern  # delay أول = 0
            amps     = [-1] * len(timings)
            effect   = VibrationEffect.createWaveform(
                timings, amps, -1   # -1 = لا تكرار
            )
            vibrator.vibrate(effect)
        except Exception as e:
            print(f"[Haptic] Error: {e}")


# ════════════════════════════════════════════
# THE CYBER UI — KivyMD Gaming Dashboard
# ════════════════════════════════════════════
KV = """
MDScreen:
    md_bg_color: 0.05, 0.05, 0.08, 1

    MDBoxLayout:
        orientation: 'vertical'
        padding: dp(16)
        spacing: dp(12)

        # ── Header
        MDBoxLayout:
            size_hint_y: None
            height: dp(56)
            MDLabel:
                text: "👻 THE GHOST ARCHITECT"
                font_style: "H5"
                theme_text_color: "Custom"
                text_color: 0.0, 0.9, 1.0, 1
                bold: True
            MDLabel:
                id: status_dot
                text: "● IDLE"
                halign: "right"
                theme_text_color: "Custom"
                text_color: 0.5, 0.5, 0.5, 1

        # ── Stats Grid
        MDGridLayout:
            cols: 2
            spacing: dp(10)
            size_hint_y: None
            height: dp(200)

            StatCard:
                id: card_cpu
                title: "CPU"
                value: "0%"
                icon: "cpu-64-bit"
                accent: 0.0, 0.9, 1.0, 1

            StatCard:
                id: card_ram
                title: "RAM"
                value: "0%"
                icon: "memory"
                accent: 0.6, 0.2, 1.0, 1

            StatCard:
                id: card_temp
                title: "TEMP"
                value: "0°C"
                icon: "thermometer"
                accent: 1.0, 0.4, 0.0, 1

            StatCard:
                id: card_touch
                title: "TOUCH MS"
                value: "—"
                icon: "gesture-tap"
                accent: 0.0, 1.0, 0.5, 1

        # ── Sonic Radar Panel
        MDCard:
            size_hint_y: None
            height: dp(110)
            md_bg_color: 0.08, 0.08, 0.14, 1
            radius: [16]
            padding: dp(14)

            MDBoxLayout:
                orientation: 'vertical'
                spacing: dp(6)

                MDLabel:
                    text: "🎧 SONIC RADAR"
                    font_style: "Caption"
                    theme_text_color: "Custom"
                    text_color: 0.0, 0.9, 1.0, 1
                    bold: True

                MDLabel:
                    id: radar_direction
                    text: "Direction: —"
                    theme_text_color: "Custom"
                    text_color: 0.9, 0.9, 0.9, 1

                MDLabel:
                    id: radar_event
                    text: "Event: —"
                    theme_text_color: "Custom"
                    text_color: 0.7, 0.7, 0.7, 1

                MDLabel:
                    id: radar_intensity
                    text: "Intensity: —"
                    theme_text_color: "Custom"
                    text_color: 0.5, 0.5, 0.5, 1

        # ── Nitro Button
        MDRaisedButton:
            id: nitro_btn
            text: "⚡  ACTIVATE NITRO MODE"
            size_hint_x: 1
            height: dp(56)
            md_bg_color: 0.0, 0.7, 1.0, 1
            font_size: "16sp"
            on_release: app.toggle_nitro()

        # ── Processes info
        MDLabel:
            id: procs_label
            text: "Active Processes: —"
            halign: "center"
            theme_text_color: "Custom"
            text_color: 0.4, 0.4, 0.4, 1
            font_style: "Caption"
"""

from kivymd.uix.card import MDCard
from kivy.lang import Builder
from kivy.metrics import dp
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout

# Custom StatCard Widget
Builder.load_string("""
<StatCard>:
    md_bg_color: 0.08, 0.08, 0.14, 1
    radius: [16]
    padding: dp(12)
    orientation: 'vertical'

    MDLabel:
        id: icon_lbl
        text: "?"
        halign: "center"
        font_style: "H6"
        theme_text_color: "Custom"
        text_color: root.accent

    MDLabel:
        id: value_lbl
        text: root.value
        halign: "center"
        font_style: "H5"
        bold: True
        theme_text_color: "Custom"
        text_color: 0.95, 0.95, 0.95, 1

    MDLabel:
        id: title_lbl
        text: root.title
        halign: "center"
        font_style: "Caption"
        theme_text_color: "Custom"
        text_color: 0.5, 0.5, 0.5, 1
""")

class StatCard(MDCard):
    from kivy.properties import StringProperty, ListProperty
    title  = StringProperty("STAT")
    value  = StringProperty("0")
    icon   = StringProperty("help")
    accent = ListProperty([0.0, 0.9, 1.0, 1])

    def update(self, new_value: str):
        self.ids.value_lbl.text = new_value


# ════════════════════════════════════════════
# MAIN APPLICATION
# ════════════════════════════════════════════
class GhostArchitectApp(MDApp):

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Cyan"

        self.monitor = PerformanceMonitor()
        self.haptic  = HapticEngine()
        self.radar   = SonicRadarEngine(callback=self.on_radar_event)

        self.nitro_active = False

        return Builder.load_string(KV)

    def on_start(self):
        # بدء دورة تحديث الأداء كل 500ms
        Clock.schedule_interval(self.update_dashboard, 0.5)

    def update_dashboard(self, dt):
        data = self.monitor.snapshot()
        root = self.root

        root.ids.card_cpu.update(f"{data['cpu']:.0f}%")
        root.ids.card_ram.update(f"{data['ram']:.0f}%")
        root.ids.card_temp.update(
            f"{data['temp']:.0f}°C" if data['temp'] > 0 else "N/A"
        )
        root.ids.card_touch.update(f"~{data['touch_avg']}ms")
        root.ids.procs_label.text = (
            f"Active Processes: {data['procs']}"
        )

    def toggle_nitro(self):
        self.nitro_active = not self.nitro_active
        btn = self.root.ids.nitro_btn
        dot = self.root.ids.status_dot

        if self.nitro_active:
            self.radar.start()
            btn.text = "🛑  DEACTIVATE NITRO"
            btn.md_bg_color = (1.0, 0.2, 0.2, 1)
            dot.text = "● ACTIVE"
            dot.text_color = (0.0, 1.0, 0.4, 1)
            self.haptic.vibrate("CENTER")  # تأكيد التشغيل
        else:
            self.radar.stop()
            btn.text = "⚡  ACTIVATE NITRO MODE"
            btn.md_bg_color = (0.0, 0.7, 1.0, 1)
            dot.text = "● IDLE"
            dot.text_color = (0.5, 0.5, 0.5, 1)

    def on_radar_event(self, result: dict):
        """بيتنادى من الـ SonicRadar كل ما يرصد حدث"""
        root = self.root
        direction = result["direction"]
        events    = result["events"]
        intensity = result["intensity"]

        # تحديث الـ UI
        root.ids.radar_direction.text = f"Direction: {direction}"
        top_event = max(events, key=events.get)
        root.ids.radar_event.text    = f"Event: {top_event.upper()}"
        root.ids.radar_intensity.text = f"Intensity: {intensity:.1f}"

        # اهتزاز بالاتجاه
        if self.nitro_active:
            self.haptic.vibrate(direction)
            self.haptic.vibrate(top_event)


if __name__ == "__main__":
    GhostArchitectApp().run()
