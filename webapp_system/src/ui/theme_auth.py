from __future__ import annotations

import flet as ft

from .theme_primitives import glass_container
from .theme_tokens import PRIMARY
from .theme_shells import build_background


def auth_text_field(
    label: str,
    icon=None,
    password: bool = False,
    can_reveal: bool = False,
) -> ft.TextField:
    return ft.TextField(
        label=label,
        prefix_icon=icon,
        password=password,
        can_reveal_password=can_reveal,
        border_radius=14,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.28, ft.Colors.WHITE),
        focused_border_color=PRIMARY,
        focused_border_width=2,
        label_style=ft.TextStyle(color=ft.Colors.WHITE70, size=13),
        text_style=ft.TextStyle(color=ft.Colors.WHITE, size=14),
        cursor_color=ft.Colors.WHITE,
        content_padding=ft.padding.symmetric(horizontal=16, vertical=14),
    )


def auth_dropdown(label: str, options: list[tuple[str, str]], value: str = None) -> ft.Dropdown:
    return ft.Dropdown(
        label=label,
        value=value,
        border_radius=14,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.28, ft.Colors.WHITE),
        focused_border_color=PRIMARY,
        focused_border_width=2,
        label_style=ft.TextStyle(color=ft.Colors.WHITE70, size=13),
        options=[ft.dropdown.Option(key, text) for key, text in options],
    )


def build_auth_shell(title: str, description: str, form_controls: list[ft.Control]):
    form_card = glass_container(
        padding=ft.padding.symmetric(horizontal=24, vertical=28),
        radius=24,
        content=ft.Column(
            tight=True,
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Text(title, size=26, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE),
                ft.Text(description, color=ft.Colors.WHITE60, size=12),
                ft.Divider(color=ft.Colors.with_opacity(0.15, ft.Colors.WHITE), height=1),
                *form_controls,
            ],
        ),
    )
    logo = ft.Container(
        top=12,
        right=12,
        width=80,
        height=80,
        content=ft.Image(src="logo.png", fit="contain"),
    )
    return build_background(
        ft.Stack(
            expand=True,
            controls=[
                ft.Container(
                    expand=True,
                    alignment=ft.alignment.center,
                    padding=ft.padding.symmetric(horizontal=16, vertical=36),
                    content=form_card,
                ),
                logo,
            ],
        )
    )
