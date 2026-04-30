from __future__ import annotations

import flet as ft

from ui.theme import status_badge

TEAL = ft.Colors.TEAL_300
STATUS_META = {
    "new": ("Moi", "warning"),
    "claimed": ("Da nhan", "secondary"),
    "under_review": ("Dang xu ly", "secondary"),
    "waiting_farmer": ("Cho farmer", "neutral"),
    "escalated": ("Escalate", "danger"),
    "closed": ("Dong", "success"),
}
QUICK_REPLIES = ["Can them anh gan", "Theo doi 24h", "Can cach ly", "Chuyen thu y tai cho"]


def build_history_item(title: str, subtitle: str, icon) -> ft.Control:
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        border_radius=12,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        content=ft.Row(
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Icon(icon, size=16, color=TEAL),
                ft.Column(
                    expand=True,
                    tight=True,
                    spacing=2,
                    controls=[ft.Text(title, size=11, weight=ft.FontWeight.W_700), ft.Text(subtitle, size=10, color=ft.Colors.WHITE54)],
                ),
            ],
        ),
    )


def build_data_card(item: dict) -> ft.Control:
    status_map = {
        "PENDING_REVIEW": ("Cho review", "warning"),
        "AI_SCANNED": ("Da quet AI", "secondary"),
        "NEEDS_VERIFICATION": ("Can xac minh", "secondary"),
        "WAITING_MORE_DATA": ("Cho bo sung", "neutral"),
        "VERIFIED_DATASET": ("Da xac nhan", "success"),
        "REJECTED": ("Tu choi", "danger"),
    }
    label, kind = status_map.get(item.get("trang_thai"), ("Mo", "secondary"))
    ai_line = item.get("ai_summary") or item.get("ai_primary_label") or "Chua co AI scan"
    return ft.Container(
        padding=12,
        border_radius=16,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border=ft.border.all(1, ft.Colors.with_opacity(0.10, ft.Colors.WHITE)),
        content=ft.Column(
            spacing=6,
            tight=True,
            controls=[
                ft.Row(controls=[ft.Text(item.get("file_name", "dataset-image"), size=11, weight=ft.FontWeight.W_700, expand=True), status_badge(label, kind)]),
                ft.Text(ai_line, size=10, color=ft.Colors.WHITE70),
                ft.Text(item.get("expert_label") or item.get("review_note") or item.get("duong_dan", ""), size=10, color=ft.Colors.WHITE54, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
            ],
        ),
    )


def build_quick_reply_row(input_ref: ft.Ref[ft.TextField], page: ft.Page | None) -> ft.Control:
    def fill(text: str):
        if input_ref.current:
            input_ref.current.value = text
            if page:
                try:
                    page.update()
                except Exception:
                    pass

    return ft.Row(
        spacing=6,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.OutlinedButton(
                text=reply,
                style=ft.ButtonStyle(
                    color=TEAL,
                    side=ft.BorderSide(1, ft.Colors.with_opacity(0.35, TEAL)),
                    shape=ft.RoundedRectangleBorder(radius=14),
                    padding=ft.padding.symmetric(horizontal=10, vertical=4),
                    text_style=ft.TextStyle(size=11),
                ),
                on_click=lambda e, text=reply: fill(text),
            )
            for reply in QUICK_REPLIES
        ],
    )
