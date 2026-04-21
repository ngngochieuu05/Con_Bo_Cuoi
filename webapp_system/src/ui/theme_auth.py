from __future__ import annotations

import flet as ft

from .theme_tokens import PRIMARY, SECONDARY


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
        bgcolor=ft.Colors.with_opacity(0.14, "#D9E5ED"),
        border_color=ft.Colors.with_opacity(0.26, "#D9E5ED"),
        focused_border_color=PRIMARY,
        focused_border_width=2,
        label_style=ft.TextStyle(color="#D2DEE6", size=13),
        text_style=ft.TextStyle(color=ft.Colors.WHITE, size=14),
        cursor_color=ft.Colors.WHITE,
        content_padding=ft.padding.symmetric(horizontal=16, vertical=14),
    )


def auth_dropdown(label: str, options: list[tuple[str, str]], value: str = None) -> ft.Dropdown:
    return ft.Dropdown(
        label=label,
        value=value,
        border_radius=14,
        bgcolor=ft.Colors.with_opacity(0.14, "#D9E5ED"),
        border_color=ft.Colors.with_opacity(0.26, "#D9E5ED"),
        focused_border_color=PRIMARY,
        focused_border_width=2,
        label_style=ft.TextStyle(color="#D2DEE6", size=13),
        options=[ft.dropdown.Option(key, text) for key, text in options],
    )


def _build_auth_background(content: ft.Control) -> ft.Control:
    return ft.Stack(
        expand=True,
        controls=[
            ft.Container(
                expand=True,
                bgcolor="#0E171D",
                image=ft.DecorationImage(
                    src="backround.png",
                    fit="cover",
                    opacity=0.24,
                ),
                gradient=ft.LinearGradient(
                    begin=ft.alignment.top_left,
                    end=ft.alignment.bottom_right,
                    colors=["#112028D8", "#18303CD2", "#214A55CC"],
                ),
            ),
            ft.Container(
                expand=True,
                gradient=ft.LinearGradient(
                    begin=ft.alignment.center_left,
                    end=ft.alignment.center_right,
                    colors=["#091117D8", "#091117B8", "#09111742"],
                ),
            ),
            ft.Container(
                expand=True,
                gradient=ft.RadialGradient(
                    center=ft.Alignment(0.78, 0.72),
                    radius=0.92,
                    colors=["#83D9FF24", "#00000000"],
                ),
            ),
            ft.Container(
                expand=True,
                gradient=ft.RadialGradient(
                    center=ft.Alignment(-0.76, -0.70),
                    radius=1.08,
                    colors=["#6FD59D18", "#00000000"],
                ),
            ),
            ft.Container(
                expand=True,
                gradient=ft.LinearGradient(
                    begin=ft.alignment.top_center,
                    end=ft.alignment.bottom_center,
                    colors=["#0A131740", "#0A131714", "#0A131788"],
                ),
            ),
            content,
        ],
    )


def build_auth_shell(title: str, description: str, form_controls: list[ft.Control]):
    form_card = ft.Container(
        padding=ft.padding.symmetric(horizontal=24, vertical=28),
        border_radius=26,
        bgcolor=ft.Colors.with_opacity(0.74, "#182833"),
        border=ft.border.all(1, ft.Colors.with_opacity(0.14, "#F4F7FA")),
        shadow=ft.BoxShadow(
            blur_radius=34,
            color=ft.Colors.with_opacity(0.30, ft.Colors.BLACK),
            offset=ft.Offset(0, 18),
        ),
        content=ft.Column(
            tight=True,
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Text(title, size=26, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE),
                ft.Text(description, color="#D2DEE6", size=12),
                ft.Divider(color=ft.Colors.with_opacity(0.12, "#F4F7FA"), height=1),
                *form_controls,
            ],
        ),
    )
    logo = ft.Container(
        top=16,
        right=14,
        width=72,
        height=72,
        padding=5,
        border_radius=22,
        bgcolor=ft.Colors.with_opacity(0.12, "#FFF7EE"),
        border=ft.border.all(1, ft.Colors.with_opacity(0.12, "#FFF7EE")),
        content=ft.Image(src="logo.png", fit="contain"),
    )
    return _build_auth_background(
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
