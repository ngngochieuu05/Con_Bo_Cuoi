from __future__ import annotations

import flet as ft

from .theme_nav import build_avatar_btn, build_glass_nav_bar
from .theme_primitives import glass_container
from .theme_tokens import PRIMARY


def build_background(content: ft.Control):
    return ft.Stack(
        expand=True,
        controls=[
            ft.Container(
                expand=True,
                bgcolor="#0E171D",
                image=ft.DecorationImage(
                    src="backround.png",
                    fit="cover",
                    opacity=0.22,
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


def build_role_shell(
    role_title: str,
    role_subtitle: str,
    navigation_items: list[tuple[str, str, str]],
    selected_key: str,
    on_select,
    main_content: ft.Control,
    on_logout,
    page: ft.Page | None = None,
    on_profile=None,
):
    is_mobile = True
    if page is not None:
        try:
            data = page.data
            if isinstance(data, dict):
                is_mobile = data.get("is_mobile", True)
            else:
                window_width = page.window.width
                if window_width and window_width > 100:
                    is_mobile = window_width <= 900
        except Exception:
            is_mobile = True

    if is_mobile:
        header = ft.Container(
            padding=ft.padding.only(left=16, right=16, top=14, bottom=12),
            bgcolor=ft.Colors.with_opacity(0.62, "#182833"),
            border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.10, "#F4F7FA"))),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(
                        spacing=1,
                        tight=True,
                        controls=[
                            ft.Text(role_title, size=15, weight=ft.FontWeight.W_700),
                            ft.Text(role_subtitle, size=10, color="#D2DEE6"),
                        ],
                    ),
                    build_avatar_btn(page, on_profile),
                ],
            ),
        )
        return build_background(
            ft.Stack(
                expand=True,
                controls=[
                    ft.Column(
                        expand=True,
                        spacing=0,
                        controls=[
                            header,
                            ft.Container(
                                expand=True,
                                padding=ft.padding.only(left=10, right=10, top=10, bottom=96),
                                content=glass_container(main_content, padding=16, radius=26),
                            ),
                        ],
                    ),
                    build_glass_nav_bar(navigation_items, selected_key, on_select),
                ],
            )
        )

    sidebar_controls = [
        ft.Text(role_title, size=22, weight=ft.FontWeight.W_700),
        ft.Text(role_subtitle, size=12, color="#D2DEE6"),
        ft.Divider(color=ft.Colors.with_opacity(0.10, "#F4F7FA")),
    ]
    for key, label, icon_name in navigation_items:
        icon = getattr(ft.Icons, icon_name, ft.Icons.CIRCLE)
        sidebar_controls.append(
            ft.TextButton(
                text=label,
                icon=icon,
                style=ft.ButtonStyle(
                    color=ft.Colors.WHITE,
                    bgcolor=ft.Colors.with_opacity(0.24, PRIMARY) if selected_key == key else ft.Colors.TRANSPARENT,
                    shape=ft.RoundedRectangleBorder(radius=12),
                ),
                on_click=lambda e, nav_key=key: on_select(nav_key),
            )
        )
    sidebar_controls.append(ft.Container(expand=True))

    top_bar = ft.Container(
        padding=ft.padding.only(left=18, right=18, top=10, bottom=10),
        bgcolor=ft.Colors.with_opacity(0.62, "#182833"),
        border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.10, "#F4F7FA"))),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.END,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[build_avatar_btn(page, on_profile)],
        ),
    )

    return build_background(
        ft.Column(
            expand=True,
            spacing=0,
            controls=[
                top_bar,
                ft.Row(
                    expand=True,
                    controls=[
                        ft.Container(
                            width=276,
                            padding=18,
                            content=glass_container(
                                ft.Column(expand=True, spacing=10, controls=sidebar_controls),
                                padding=20,
                                radius=26,
                            ),
                        ),
                        ft.Container(
                            expand=True,
                            padding=ft.padding.only(top=14, right=18, bottom=18),
                            content=glass_container(main_content, padding=20, radius=26),
                        ),
                    ],
                ),
            ],
        )
    )
