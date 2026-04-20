from __future__ import annotations

import flet as ft

from ui.theme import PRIMARY

ROLE_FILTER = [
    ("all", "Tat ca"),
    ("admin", "Quan tri"),
    ("expert", "Chuyen gia"),
    ("farmer", "Nong dan"),
]


def filter_users(users: list[dict], keyword: str = "", role_filter: str = "all") -> list[dict]:
    filtered = users
    if role_filter != "all":
        filtered = [user for user in filtered if user.get("vai_tro") == role_filter]

    keyword = keyword.lower()
    if not keyword:
        return filtered

    return [
        user
        for user in filtered
        if keyword in user.get("ten_dang_nhap", "").lower()
        or keyword in user.get("ho_ten", "").lower()
    ]


def build_filter_chips(active_role: str, on_filter) -> list[ft.Control]:
    chips: list[ft.Control] = []
    for key, label in ROLE_FILTER:
        is_active = active_role == key
        chips.append(
            ft.Container(
                ink=True,
                border_radius=20,
                padding=ft.padding.symmetric(horizontal=12, vertical=5),
                bgcolor=ft.Colors.with_opacity(
                    0.28 if is_active else 0.10,
                    PRIMARY if is_active else ft.Colors.WHITE,
                ),
                border=ft.border.all(
                    1,
                    ft.Colors.with_opacity(
                        0.4 if is_active else 0.15,
                        PRIMARY if is_active else ft.Colors.WHITE,
                    ),
                ),
                on_click=lambda e, role_key=key: on_filter(role_key),
                content=ft.Text(
                    label,
                    size=12,
                    weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.W_400,
                ),
            )
        )
    return chips
