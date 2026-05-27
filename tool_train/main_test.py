"""Trình khởi chạy cho bộ công cụ desktop Con Bò Cười."""

import subprocess
import sys
from pathlib import Path

import customtkinter as ctk

LOCAL_SRC_DIR = Path(__file__).resolve().parent
if str(LOCAL_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(LOCAL_SRC_DIR))

from bll.app_context import SRC_DIR, UI_DIR, bootstrap_sys_path

bootstrap_sys_path(sys.path)

from ui.ui_theme import (
    ACCENT,
    INFO,
    SUCCESS,
    TEXT_MUTED,
    UI_FONT,
    WARNING,
    build_dashboard_banner,
    build_metric_strip,
    build_workspace_card,
    setup_ctk,
    silence_console_output,
)

silence_console_output()
setup_ctk(ctk)

TOOLS = [
    {
        "icon": "T",
        "label": "Huấn luyện mô hình",
        "sub": "YOLOv8, CNN JILSA 2022 và MobileNetV2 PLOS 2024 trong một không gian huấn luyện thống nhất.",
        "module": "ui.train.app",
        "cls": "TrainerApp",
        "badge": "TRAIN",
        "badge_color": ACCENT,
    },
    {
        "icon": "E",
        "label": "Đánh giá mô hình",
        "sub": "Kiểm thử nhanh, đánh giá theo lô, so sánh mô hình và theo dõi lịch sử đánh giá.",
        "module": "ui.test.app",
        "cls": "TesterApp",
        "badge": "EVALUATE",
        "badge_color": SUCCESS,
    },
    {
        "icon": "D",
        "label": "Công cụ dữ liệu",
        "sub": "Sao chép an toàn, đọc tỉ lệ chia tập và tăng cường ảnh dựa trên Albumentations.",
        "module": "ui.tools.app",
        "cls": "ToolsApp",
        "badge": "DATASET",
        "badge_color": WARNING,
    },
]


class Launcher(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Con Bò Cười - Bộ công cụ AI")
        self.geometry("1120x760")
        self.minsize(920, 640)
        self._build_ui()

    def _build_ui(self):
        shell = ctk.CTkFrame(self, fg_color="transparent")
        shell.pack(fill="both", expand=True, padx=24, pady=20)

        hero = build_dashboard_banner(
            ctk,
            shell,
            eyebrow="BỘ CÔNG CỤ AI CON BÒ CƯỜI",
            title="Không gian desktop cho huấn luyện, đánh giá và chuẩn bị dữ liệu",
            description=(
                "Màn hình khởi chạy giờ hoạt động như bộ chọn không gian làm việc. "
                "Mỗi mô-đun mở thành một luồng riêng, tập trung và không làm thay đổi logic bên dưới."
            ),
            accent=ACCENT,
        )
        hero.pack(fill="x")

        metrics = build_metric_strip(
            ctk,
            shell,
            [
                {"title": "Không gian", "value": "3", "hint": "Huấn luyện, Đánh giá, Công cụ dữ liệu", "accent": ACCENT},
                {"title": "Phạm vi", "value": "Chỉ UI", "hint": "Không đổi logic nghiệp vụ", "accent": SUCCESS},
                {"title": "Chế độ", "value": "Máy tính", "hint": "Chạy trực tiếp bằng Python cục bộ", "accent": WARNING},
                {
                    "title": "Môi trường",
                    "value": f"Python {sys.version_info.major}.{sys.version_info.minor}",
                    "hint": "Có thể mở nhiều mô-đun song song",
                    "accent": INFO,
                },
            ],
        )
        metrics.pack(fill="x", pady=(14, 8))

        cards = ctk.CTkFrame(shell, fg_color="transparent")
        cards.pack(fill="both", expand=True, pady=(8, 0))
        for col in range(3):
            cards.grid_columnconfigure(col, weight=1)

        for idx, tool in enumerate(TOOLS):
            card, _ = build_workspace_card(
                ctk,
                cards,
                icon=tool["icon"],
                eyebrow=tool["badge"],
                title=tool["label"],
                description=tool["sub"],
                accent=tool["badge_color"],
                command=lambda t=tool: self._launch(t),
                button_text="Mở không gian làm việc",
            )
            card.grid(row=0, column=idx, sticky="nsew", padx=8, pady=8)

        footer = ctk.CTkFrame(shell, fg_color="transparent")
        footer.pack(fill="x", pady=(10, 0))

        self.status = ctk.CTkLabel(
            footer,
            text="Sẵn sàng - chọn một không gian làm việc để bắt đầu",
            font=(UI_FONT, 12),
            text_color=TEXT_MUTED,
        )
        self.status.pack(side="left")

        ctk.CTkLabel(
            footer,
            text=f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            font=(UI_FONT, 11),
            text_color=TEXT_MUTED,
        ).pack(side="right")

    def _launch(self, tool: dict):
        script = (
            "import sys; "
            f"sys.path.insert(0, {str(SRC_DIR)!r}); "
            f"sys.path.insert(0, {str(UI_DIR)!r}); "
            f"from {tool['module']} import {tool['cls']}; "
            f"app = {tool['cls']}(); "
            "app.mainloop()"
        )
        subprocess.Popen([sys.executable, "-c", script], cwd=str(UI_DIR))
        self.status.configure(text=f"Đã mở: {tool['label']}", text_color=tool["badge_color"])


if __name__ == "__main__":
    Launcher().mainloop()
