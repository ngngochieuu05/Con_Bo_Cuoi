"""
YOLOv8 Trainer - UI bằng CustomTkinter
Dataset: Roboflow (Cattle Disease - 3 classes)
GPU: RTX 4060 8GB VRAM | CPU: i9-14900HX | RAM: 16GB
"""

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
import subprocess
import sys
from pathlib import Path
import customtkinter as ctk

SRC_DIR = Path(__file__).resolve().parents[2]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ui.ui_theme import (
    ACCENT, ACCENT2, ACCENT3, BG, BG2, BG3, BG4, BORDER,
    DANGER, SUCCESS, TEXT, TEXT_DIM, TEXT_MUTED, WARNING,
    UI_FONT,
    apply_ttk_theme,
    build_app_taskbar,
    build_app_shell,
    build_page_body,
    build_tabview,
    silence_console_output,
    setup_ctk,
)
from bll.train.common import PRESETS
from ui.train.yolo_mixin import YoloTrainerMixin
from ui.train.cnn_jilsa import CNNJilsaTrainerMixin
from ui.train.netmb_plos import NetmbPlosTrainerMixin


setup_ctk(ctk)
silence_console_output()


class TrainerApp(YoloTrainerMixin, CNNJilsaTrainerMixin, NetmbPlosTrainerMixin, ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Con Bò Cười - Huấn luyện mô hình")
        self.geometry("1440x920")
        self.minsize(1180, 760)
        self.configure(fg_color=BG)
        self.resizable(True, True)

        self._process: subprocess.Popen | None = None
        self._training = False
        self._log_lines = 0
        self._model_cb = None   # reference to model CTkComboBox for dynamic update
        # Ablation state
        self._ab_training = False
        self._ab_process: subprocess.Popen | None = None
        self._ab_start_time = 0.0
        self._ab_current_epochs = 50

        # Classification (JILSA 2022 simulation) state
        self._cls_training = False
        self._cls_process: subprocess.Popen | None = None
        self._cls_start_time = 0.0
        self._cls_current_epochs = 50

        # JILSA 2022 Custom CNN state
        self._jilsa_training = False
        self._jilsa_process: subprocess.Popen | None = None
        self._jilsa_start_time = 0.0
        self._jilsa_current_epochs = 50

        # PLOS ONE 2024 MobileNetV2 state
        self._plos_training = False
        self._plos_process: subprocess.Popen | None = None
        self._plos_start_time = 0.0
        self._plos_current_epochs = 50

        self._start_time = 0.0

        self._build_ui()
        self._apply_preset(list(PRESETS.keys())[1])   # mặc định: Cân bằng
        # Chạy sau khi UI đã hiển thị để tránh block main thread
        self.after(100, self._check_ultralytics_async)

    def _build_scrollable_left(self, parent, *, width=320, minsize=280, padx=12, pady=10):
        container = ctk.CTkFrame(parent, fg_color=BG2, corner_radius=24,
                                  border_width=1, border_color=BORDER)
        inner = ctk.CTkScrollableFrame(
            container,
            fg_color=BG2,
            corner_radius=18,
            scrollbar_button_color=ACCENT,
            scrollbar_button_hover_color=ACCENT2,
        )
        inner.pack(fill="both", expand=True, padx=8, pady=8)
        return container, inner, minsize

    # ─────────────────────────────────────────────────────────────────────────
    # BUILD UI
    # ─────────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        host = ctk.CTkFrame(self, fg_color="transparent")
        host.pack(fill="both", expand=True)

        hdr, self._status_lbl = build_app_taskbar(
            ctk,
            host,
            title="Huấn luyện mô hình AI",
            subtitle="YOLOv8 Detection · Segmentation · Classification  |  CNN JILSA 2022  |  MobileNetV2 PLOS 2024",
            status_text="Sẵn sàng",
            status_color=ACCENT,
        )
        hdr.pack(fill="x", padx=18, pady=(18, 0))

        style = ttk.Style(self)
        apply_ttk_theme(style)
        nb = build_tabview(ctk, host)
        nb.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        nb.add("🧠  YOLO")
        nb.add("🔬  CNN (JILSA)")
        nb.add("📱  MobileNet (PLOS)")

        # YOLO tab
        tab1 = build_page_body(ctk, nb.tab("🧠  YOLO"), padx=6, pady=8)
        tab1.grid_columnconfigure(0, weight=0, minsize=340)
        tab1.grid_columnconfigure(1, weight=1)
        tab1.grid_rowconfigure(0, weight=1)
        left_container, left, left_minsize = self._build_scrollable_left(tab1, width=340, minsize=300)
        right = ctk.CTkFrame(tab1, fg_color=BG, corner_radius=24)
        left_container.grid(row=0, column=0, sticky="nsew", padx=(8, 10), pady=8)
        right.grid(row=0, column=1, sticky="nsew", padx=(0, 8), pady=8)
        self._build_left(left)
        self._build_right(right)

        # CNN JILSA tab
        tab_jilsa = build_page_body(ctk, nb.tab("🔬  CNN (JILSA)"), padx=6, pady=8)
        self._build_jilsa_tab(tab_jilsa)

        # MobileNet PLOS tab
        tab_plos = build_page_body(ctk, nb.tab("📱  MobileNet (PLOS)"), padx=6, pady=8)
        self._build_plos_tab(tab_plos)

    # ── Static helper ─────────────────────────────────────────────────────────
    @staticmethod
    def _fmt_time(seconds: float) -> str:
        seconds = int(seconds)
        h, r = divmod(seconds, 3600)
        m, s = divmod(r, 60)
        if h:
            return f"{h}h {m}m {s}s"
        if m:
            return f"{m}m {s}s"
        return f"{s}s"


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = TrainerApp()
    app.mainloop()
