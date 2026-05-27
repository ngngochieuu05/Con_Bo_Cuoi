"""Launcher - Bộ công cụ AI Con Bò Cười."""

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
    ACCENT, ACCENT2, ACCENT3, BG, BG2, BG3, BG4, BORDER,
    INFO, SUCCESS, TEXT, TEXT_DIM, TEXT_MUTED, WARNING,
    UI_FONT,
    silence_console_output, setup_ctk,
)

silence_console_output()
setup_ctk(ctk)

TOOLS = [
    {
        "icon": "🧠",
        "label": "Huấn luyện mô hình",
        "sub": "YOLOv8 Detection · Segmentation · Classification  |  CNN JILSA 2022  |  MobileNetV2 PLOS 2024",
        "module": "ui.train.app",
        "cls": "TrainerApp",
        "badge": "TRAIN",
        "badge_color": ACCENT,
        "btn_color": ACCENT,
        "btn_hover": ACCENT2,
    },
    {
        "icon": "🔬",
        "label": "Đánh giá mô hình",
        "sub": "Kiểm thử model, so sánh model, đánh giá batch, phân tích kết quả với Gemini AI.",
        "module": "ui.test.app",
        "cls": "TesterApp",
        "badge": "TEST",
        "badge_color": SUCCESS,
        "btn_color": SUCCESS,
        "btn_hover": "#3ab558",
    },
    {
        "icon": "🛠",
        "label": "Công cụ dữ liệu",
        "sub": "Sao chép dataset an toàn · Chia tỉ lệ train/val/test · Tăng cường ảnh Albumentations.",
        "module": "ui.tools.app",
        "cls": "ToolsApp",
        "badge": "TOOLS",
        "badge_color": WARNING,
        "btn_color": WARNING,
        "btn_hover": "#d97706",
    },
]


class Launcher(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Con Bò Cười - Bộ công cụ AI")
        self.geometry("960x720")
        self.minsize(820, 580)
        self.configure(fg_color=BG)
        self._build_ui()

    def _build_ui(self):
        # ── Outer wrapper ──────────────────────────────────────────────────────
        shell = ctk.CTkFrame(self, fg_color="transparent")
        shell.pack(fill="both", expand=True, padx=24, pady=20)

        # ── Header card ────────────────────────────────────────────────────────
        hero = ctk.CTkFrame(
            shell,
            fg_color=BG2,
            corner_radius=18,
            border_width=1,
            border_color=ACCENT,
        )
        hero.pack(fill="x")

        hero_inner = ctk.CTkFrame(hero, fg_color="transparent")
        hero_inner.pack(fill="x", padx=28, pady=20)

        # Left: title + subtitle
        title_col = ctk.CTkFrame(hero_inner, fg_color="transparent")
        title_col.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            title_col,
            text="🐄  Con Bò Cười  AI Toolkit",
            font=(UI_FONT, 28, "bold"),
            text_color=TEXT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_col,
            text="Bộ công cụ huấn luyện · đánh giá · chuẩn bị dataset cho bệnh bò",
            font=(UI_FONT, 13),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", pady=(4, 0))

        # Right: version badge
        badge_col = ctk.CTkFrame(hero_inner, fg_color="transparent")
        badge_col.pack(side="right")
        ctk.CTkLabel(
            badge_col,
            text="v2.0",
            font=(UI_FONT, 12, "bold"),
            text_color="white",
            fg_color=ACCENT,
            corner_radius=999,
            padx=14,
            pady=6,
        ).pack()
        ctk.CTkLabel(
            badge_col,
            text="DESKTOP TOOL",
            font=(UI_FONT, 9, "bold"),
            text_color=TEXT_MUTED,
        ).pack(pady=(4, 0))

        # ── Tool cards ─────────────────────────────────────────────────────────
        cards_container = ctk.CTkScrollableFrame(
            shell,
            fg_color=BG2,
            corner_radius=18,
            border_width=1,
            border_color=BORDER,
            scrollbar_button_color=ACCENT,
            scrollbar_button_hover_color=ACCENT2,
        )
        cards_container.pack(fill="both", expand=True, pady=(16, 0))

        for tool in TOOLS:
            self._build_tool_card(cards_container, tool)

        # ── Footer ─────────────────────────────────────────────────────────────
        footer = ctk.CTkFrame(shell, fg_color="transparent")
        footer.pack(fill="x", pady=(10, 0))

        self.status = ctk.CTkLabel(
            footer,
            text="✅  Sẵn sàng — có thể mở nhiều tool song song",
            font=(UI_FONT, 12),
            text_color=TEXT_MUTED,
        )
        self.status.pack(side="left")

        py_ver = f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        ctk.CTkLabel(
            footer,
            text=py_ver,
            font=(UI_FONT, 11),
            text_color=BG4,
        ).pack(side="right")

    def _build_tool_card(self, parent, tool: dict):
        card = ctk.CTkFrame(
            parent,
            fg_color=BG3,
            corner_radius=16,
            border_width=1,
            border_color=BORDER,
        )
        card.pack(fill="x", padx=12, pady=8)

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=20, pady=16)

        # ── Icon + metadata ────────────────────────────────────────────────────
        left = ctk.CTkFrame(body, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        top_row = ctk.CTkFrame(left, fg_color="transparent")
        top_row.pack(anchor="w")

        # Icon circle
        icon_frame = ctk.CTkFrame(
            top_row,
            fg_color=tool["badge_color"],
            corner_radius=12,
            width=44,
            height=44,
        )
        icon_frame.pack(side="left")
        icon_frame.pack_propagate(False)
        ctk.CTkLabel(
            icon_frame,
            text=tool["icon"],
            font=(UI_FONT, 22),
            text_color="white",
        ).place(relx=0.5, rely=0.5, anchor="center")

        # Badge pill + title
        meta = ctk.CTkFrame(top_row, fg_color="transparent")
        meta.pack(side="left", padx=(12, 0))

        badge_row = ctk.CTkFrame(meta, fg_color="transparent")
        badge_row.pack(anchor="w")
        ctk.CTkLabel(
            badge_row,
            text=tool["badge"],
            fg_color=tool["badge_color"],
            corner_radius=999,
            text_color="white",
            font=(UI_FONT, 9, "bold"),
            padx=10,
            pady=3,
        ).pack(side="left")

        ctk.CTkLabel(
            meta,
            text=tool["label"],
            text_color=TEXT,
            font=(UI_FONT, 18, "bold"),
        ).pack(anchor="w", pady=(4, 0))

        ctk.CTkLabel(
            left,
            text=tool["sub"],
            text_color=TEXT_DIM,
            font=(UI_FONT, 12),
            justify="left",
            wraplength=580,
            anchor="w",
        ).pack(anchor="w", pady=(6, 0))

        # ── Open button ────────────────────────────────────────────────────────
        right = ctk.CTkFrame(body, fg_color="transparent")
        right.pack(side="right")

        ctk.CTkButton(
            right,
            text="  Mở  ",
            corner_radius=10,
            height=44,
            width=120,
            fg_color=tool["btn_color"],
            hover_color=tool["btn_hover"],
            text_color="white",
            font=(UI_FONT, 13, "bold"),
            command=lambda t=tool: self._launch(t),
        ).pack()

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
        self.status.configure(
            text=f"🚀  Đã mở: {tool['label']}",
            text_color=tool["btn_color"],
        )


if __name__ == "__main__":
    Launcher().mainloop()
