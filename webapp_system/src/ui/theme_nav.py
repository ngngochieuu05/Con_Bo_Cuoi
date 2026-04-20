from __future__ import annotations

import flet as ft

from .theme_tokens import PRIMARY


def build_glass_nav_bar(navigation_items, selected_key, on_select):
    def _on_hover(e, is_selected):
        if not is_selected:
            e.control.bgcolor = (
                ft.Colors.with_opacity(0.08, ft.Colors.WHITE)
                if e.data == "true"
                else ft.Colors.TRANSPARENT
            )
            e.control.update()

    items = []
    for key, label, icon_name in navigation_items:
        icon = getattr(ft.Icons, icon_name, ft.Icons.CIRCLE)
        is_selected = key == selected_key
        short_label = label if len(label) <= 7 else label[:6] + "…"
        items.append(
            ft.Container(
                expand=1,
                on_click=lambda e, nav_key=key: on_select(nav_key),
                on_hover=lambda e, selected=is_selected: _on_hover(e, selected),
                border_radius=18,
                animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
                bgcolor=ft.Colors.with_opacity(0.24, PRIMARY) if is_selected else ft.Colors.TRANSPARENT,
                border=ft.border.all(
                    1,
                    ft.Colors.with_opacity(0.38, PRIMARY) if is_selected else ft.Colors.TRANSPARENT,
                ),
                padding=ft.padding.symmetric(vertical=8, horizontal=2),
                content=ft.Column(
                    tight=True,
                    spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(icon, color=ft.Colors.WHITE if is_selected else ft.Colors.WHITE60, size=20),
                        ft.Text(
                            short_label,
                            size=10,
                            color=ft.Colors.WHITE if is_selected else ft.Colors.WHITE60,
                            weight=ft.FontWeight.W_700 if is_selected else ft.FontWeight.W_400,
                            text_align=ft.TextAlign.CENTER,
                            max_lines=1,
                            overflow=ft.TextOverflow.CLIP,
                        ),
                    ],
                ),
            )
        )
    return ft.Container(
        bottom=14,
        left=12,
        right=12,
        height=74,
        border_radius=28,
        bgcolor=ft.Colors.with_opacity(0.38, "#1E303B"),
        border=ft.border.all(1, ft.Colors.with_opacity(0.20, ft.Colors.WHITE)),
        shadow=ft.BoxShadow(
            blur_radius=20,
            spread_radius=0,
            color=ft.Colors.with_opacity(0.24, ft.Colors.BLACK),
            offset=ft.Offset(0, 6),
        ),
        padding=ft.padding.symmetric(horizontal=10, vertical=0),
        content=ft.Row(spacing=0, controls=items),
    )


def build_avatar_btn(page: ft.Page | None, on_profile=None) -> ft.Control:
    avatar_b64 = None
    full_name = "?"
    if page is not None:
        try:
            avatar_b64 = page.data.get("anh_dai_dien")
            full_name = page.data.get("ho_ten") or "?"
        except Exception:
            pass
    initial = (full_name or "?")[0].upper()
    inner = (
        ft.Image(src_base64=avatar_b64, width=36, height=36, fit="cover")
        if avatar_b64
        else ft.Text(initial, size=14, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE)
    )
    return ft.Container(
        width=38,
        height=38,
        border_radius=19,
        bgcolor=ft.Colors.with_opacity(0.20, ft.Colors.WHITE),
        border=ft.border.all(1, ft.Colors.with_opacity(0.22, ft.Colors.WHITE)),
        alignment=ft.alignment.center,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        tooltip="Ho so ca nhan",
        on_click=lambda e: on_profile() if on_profile else None,
        content=inner,
    )
