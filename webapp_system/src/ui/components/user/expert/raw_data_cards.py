from __future__ import annotations

import os

import flet as ft

from ui.theme import PRIMARY, SECONDARY, SUCCESS, WARNING, fmt_dt, glass_container, info_strip, status_badge

STATUS_META = {
    "PENDING_REVIEW": ("Chờ duyệt", "warning"),
    "AI_SCANNED": ("Đã quét AI", "secondary"),
    "NEEDS_VERIFICATION": ("Cần xác minh", "secondary"),
    "WAITING_MORE_DATA": ("Chờ bổ sung", "neutral"),
    "VERIFIED_DATASET": ("Đã xác nhận", "success"),
    "REJECTED": ("Từ chối", "danger"),
}
FILTERS = [
    ("all", "Tất cả"),
    ("PENDING_REVIEW", "Chờ duyệt"),
    ("AI_SCANNED", "Đã quét AI"),
    ("NEEDS_VERIFICATION", "Cần xác minh"),
    ("WAITING_MORE_DATA", "Chờ bổ sung"),
    ("VERIFIED_DATASET", "Đã xác nhận"),
    ("REJECTED", "Từ chối"),
]
STATUS_ACCENT = {
    "PENDING_REVIEW": WARNING,
    "AI_SCANNED": SECONDARY,
    "NEEDS_VERIFICATION": SECONDARY,
    "WAITING_MORE_DATA": "#AAB7C4",
    "VERIFIED_DATASET": SUCCESS,
    "REJECTED": "#FF8B8B",
}


def build_status_chip(selected_key: str, key: str, label: str, on_click) -> ft.Control:
    active = selected_key == key
    accent = STATUS_ACCENT.get(key, PRIMARY)
    return ft.Container(
        ink=True,
        on_click=lambda e: on_click(key),
        padding=ft.padding.symmetric(horizontal=14, vertical=8),
        border_radius=999,
        bgcolor=ft.Colors.with_opacity(0.22, accent) if active else ft.Colors.with_opacity(0.08, "#EAF3F8"),
        border=ft.border.all(1, ft.Colors.with_opacity(0.44, accent) if active else ft.Colors.with_opacity(0.12, "#EAF3F8")),
        content=ft.Text(label, size=11, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE, no_wrap=True),
    )


def build_queue_card(item: dict, selected_id: int | None, on_select) -> ft.Control:
    label, kind = STATUS_META.get(item.get("trang_thai"), ("Mở", "secondary"))
    accent = STATUS_ACCENT.get(item.get("trang_thai"), PRIMARY)
    active = selected_id == item["id_hinh_anh"]
    ai_label = item.get("ai_primary_label") or "Chưa scan"
    linked_text = item.get("linked_case_summary") or item.get("duong_dan", "")
    return ft.Container(
        margin=ft.margin.only(bottom=12),
        padding=16,
        border_radius=22,
        bgcolor=ft.Colors.with_opacity(0.20, accent) if active else ft.Colors.with_opacity(0.08, "#EAF3F8"),
        border=ft.border.all(1, ft.Colors.with_opacity(0.40, accent) if active else ft.Colors.with_opacity(0.12, "#EAF3F8")),
        ink=True,
        on_click=lambda e, image_id=item["id_hinh_anh"]: on_select(image_id),
        content=ft.Column(
            tight=True,
            spacing=10,
            controls=[
                ft.Row(
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        ft.Column(
                            expand=True,
                            tight=True,
                            spacing=4,
                            controls=[
                                ft.Text(item.get("file_name", "dataset-image"), size=13, weight=ft.FontWeight.W_700, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(f"AI: {ai_label} • User #{item.get('id_user', '?')}", size=10, color=ft.Colors.WHITE70, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ],
                        ),
                        status_badge(label, kind),
                    ],
                ),
                ft.Text(linked_text, size=10.5, color=ft.Colors.WHITE60, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(fmt_dt(item.get("created_at", "")), size=10, color=ft.Colors.WHITE38),
                        ft.Container(
                            padding=ft.padding.symmetric(horizontal=10, vertical=4),
                            border_radius=999,
                            bgcolor=ft.Colors.with_opacity(0.10, accent),
                            content=ft.Text("Chờ duyệt" if active else "Xem chi tiết", size=10, color=ft.Colors.WHITE70, weight=ft.FontWeight.W_600, no_wrap=True),
                        ),
                    ],
                ),
            ],
        ),
    )


def build_metrics(summary: dict, compact: bool = False) -> ft.Control:
    cards = [
        ("Chờ xử lý", str(summary["pending"]), ft.Icons.INBOX_OUTLINED, WARNING),
        ("Đã xác nhận", str(summary["approved"]), ft.Icons.VERIFIED_OUTLINED, SUCCESS),
        ("Chờ bổ sung", str(summary["waiting_more_data"]), ft.Icons.HOURGLASS_TOP_ROUNDED, SECONDARY),
    ]
    if compact:
        return ft.Row(spacing=10, controls=[_metric_tile(*card, compact=True) for card in cards])
    return ft.Row(spacing=10, controls=[_metric_tile(*card) for card in cards])


def _metric_tile(title: str, value: str, icon, accent: str, compact: bool = False) -> ft.Control:
    return glass_container(
        expand=1,
        padding=12 if compact else 16,
        radius=18 if compact else 20,
        content=ft.Column(
            tight=True,
            spacing=6 if compact else 8,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(title, size=10 if compact else 11, color=ft.Colors.WHITE70, expand=True, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Container(width=24 if compact else 30, height=24 if compact else 30, border_radius=8 if compact else 10, bgcolor=ft.Colors.with_opacity(0.18, accent), alignment=ft.alignment.center, content=ft.Icon(icon, size=13 if compact else 16, color=accent)),
                    ],
                ),
                ft.Text(value, size=18 if compact else 24, weight=ft.FontWeight.W_700),
            ],
        ),
    )


def build_preview(path: str) -> ft.Control:
    if path and os.path.exists(path):
        return ft.Image(src=path, height=220, fit=ft.ImageFit.CONTAIN, border_radius=16)
    return ft.Container(
        height=220,
        border_radius=16,
        bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.WHITE),
        alignment=ft.alignment.center,
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
            controls=[
                ft.Icon(ft.Icons.IMAGE_NOT_SUPPORTED_OUTLINED, size=28, color=ft.Colors.WHITE54),
                ft.Text(path or "Không có đường dẫn ảnh", size=11, color=ft.Colors.WHITE54, text_align=ft.TextAlign.CENTER),
            ],
        ),
    )


def build_history_controls(history: list[dict]) -> list[ft.Control]:
    controls = [
        ft.Container(
            padding=12,
            border_radius=16,
            bgcolor=ft.Colors.with_opacity(0.08, "#EAF3F8"),
            border=ft.border.all(1, ft.Colors.with_opacity(0.08, "#EAF3F8")),
            content=ft.Column(
                tight=True,
                spacing=4,
                controls=[
                    ft.Text(f"{item.get('action', 'review')} -> {item.get('to_status', '-')}", size=11, weight=ft.FontWeight.W_700),
                    ft.Text(f"{fmt_dt(item.get('thoi_gian_duyet', ''))} • user #{item.get('id_user', '?')}", size=10, color=ft.Colors.WHITE60),
                    ft.Text(item.get("reason", ""), size=10, color=ft.Colors.WHITE54) if item.get("reason") else ft.Container(),
                ],
            ),
        )
        for item in history[-6:]
    ]
    return controls or [info_strip("Chưa có lịch sử duyệt.", tone="neutral")]
