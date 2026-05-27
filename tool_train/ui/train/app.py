"""Vỏ giao diện cho không gian huấn luyện bằng CustomTkinter."""

import subprocess
import sys
from pathlib import Path

import customtkinter as ctk
from tkinter import ttk

SRC_DIR = Path(__file__).resolve().parents[2]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ui.ui_theme import (
    ACCENT,
    BG,
    BORDER,
    apply_ttk_theme,
    build_app_taskbar,
    build_dashboard_banner,
    build_metric_strip,
    build_page_body,
    build_tabview,
    setup_ctk,
    silence_console_output,
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
        self.title("Con Bò Cười - Không gian huấn luyện")
        self.geometry("1440x920")
        self.minsize(1180, 760)
        self.configure(fg_color=BG)
        self.resizable(True, True)

        self._process: subprocess.Popen | None = None
        self._training = False
        self._log_lines = 0
        self._model_cb = None
        self._ab_training = False
        self._ab_process: subprocess.Popen | None = None
        self._ab_start_time = 0.0
        self._ab_current_epochs = 50
        self._cls_training = False
        self._cls_process: subprocess.Popen | None = None
        self._cls_start_time = 0.0
        self._cls_current_epochs = 50
        self._jilsa_training = False
        self._jilsa_process: subprocess.Popen | None = None
        self._jilsa_start_time = 0.0
        self._jilsa_current_epochs = 50
        self._plos_training = False
        self._plos_process: subprocess.Popen | None = None
        self._plos_start_time = 0.0
        self._plos_current_epochs = 50
        self._start_time = 0.0

        self._build_ui()
        self._apply_preset(list(PRESETS.keys())[1])
        self.after(100, self._check_ultralytics_async)

    def _build_scrollable_left(self, parent, *, width=320, minsize=280, padx=12, pady=10):
        container = ctk.CTkFrame(
            parent,
            fg_color="#343942",
            corner_radius=24,
            border_width=1,
            border_color=BORDER,
        )
        inner = ctk.CTkScrollableFrame(
            container,
            fg_color="#343942",
            corner_radius=18,
            scrollbar_button_color=ACCENT,
            scrollbar_button_hover_color="#7360FF",
        )
        inner.pack(fill="both", expand=True, padx=8, pady=8)
        return container, inner, minsize

    def _build_ui(self):
        host = ctk.CTkFrame(self, fg_color="transparent")
        host.pack(fill="both", expand=True)

        hdr, self._status_lbl = build_app_taskbar(
            ctk,
            host,
            title="Không gian huấn luyện",
            subtitle="YOLOv8, CNN JILSA và MobileNet PLOS trong cùng một lớp giao diện thống nhất.",
            status_text="Sẵn sàng",
            status_color=ACCENT,
        )
        hdr.pack(fill="x", padx=18, pady=(18, 0))

        metrics = build_metric_strip(
            ctk,
            host,
            [
                {"title": "Không gian", "value": "3", "hint": "YOLO, CNN JILSA, MobileNet PLOS", "accent": ACCENT},
                {"title": "Phản hồi", "value": "Log trực tiếp", "hint": "Epoch, ETA, tiến trình, validation", "accent": "#4BDC6B"},
                {"title": "Phạm vi", "value": "Chỉ UI", "hint": "Service huấn luyện giữ nguyên", "accent": "#F59E0B"},
            ],
            columns=3,
        )
        metrics.pack(fill="x", padx=18, pady=(14, 8))

        style = ttk.Style(self)
        apply_ttk_theme(style)
        nb = build_tabview(ctk, host)
        nb.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        nb.add("YOLO")
        nb.add("CNN JILSA")
        nb.add("MobileNet PLOS")

        tab1 = build_page_body(ctk, nb.tab("YOLO"), padx=6, pady=8)
        self._build_yolo_tab(tab1)

        tab_jilsa = build_page_body(ctk, nb.tab("CNN JILSA"), padx=6, pady=8)
        self._build_jilsa_tab(tab_jilsa)

        tab_plos = build_page_body(ctk, nb.tab("MobileNet PLOS"), padx=6, pady=8)
        self._build_plos_tab(tab_plos)

    def _build_yolo_tab(self, parent):
        banner = build_dashboard_banner(
            ctk,
            parent,
            eyebrow="HUẤN LUYỆN YOLO",
            title="Không gian thử nghiệm cho detection, segmentation và classification",
            description="Cột trái tập trung vào cấu hình. Khu vực phải ưu tiên tiến trình, trạng thái và nhật ký huấn luyện.",
            accent=ACCENT,
            compact=True,
        )
        banner.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(8, 0))

        parent.grid_columnconfigure(0, weight=0, minsize=340)
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        left_container, left, _left_minsize = self._build_scrollable_left(parent, width=340, minsize=300)
        right = ctk.CTkFrame(parent, fg_color=BG, corner_radius=24)
        left_container.grid(row=1, column=0, sticky="nsew", padx=(8, 10), pady=8)
        right.grid(row=1, column=1, sticky="nsew", padx=(0, 8), pady=8)
        self._build_left(left)
        self._build_right(right)

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


if __name__ == "__main__":
    app = TrainerApp()
    app.mainloop()
