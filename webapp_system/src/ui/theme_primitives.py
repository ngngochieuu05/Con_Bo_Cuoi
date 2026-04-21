from __future__ import annotations

from datetime import datetime as _dt

import flet as ft

from .theme_tokens import (
    BUTTON_PALETTE,
    DANGER,
    GLASS_BG,
    GLASS_BORDER,
    GLASS_SHADOW,
    NEUTRAL,
    PRIMARY,
    SECONDARY,
    SUCCESS,
    WARNING,
)


def glass_container(content, width=None, height=None, padding=24, radius=28, expand=None):
    return ft.Container(
        width=width,
        height=height,
        expand=expand,
        padding=padding,
        bgcolor=GLASS_BG,
        border=ft.border.all(1, GLASS_BORDER),
        border_radius=radius,
        shadow=GLASS_SHADOW,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=content,
    )


def button_style(kind="primary", radius=8):
    bg, fg, hover = BUTTON_PALETTE.get(kind, BUTTON_PALETTE["primary"])
    border_color = ft.Colors.with_opacity(0.18, ft.Colors.BLACK) if kind == "surface" else bg
    return ft.ButtonStyle(
        bgcolor={
            ft.ControlState.DEFAULT: bg,
            ft.ControlState.HOVERED: hover,
        },
        color=fg,
        shape=ft.RoundedRectangleBorder(radius=radius),
        side=ft.BorderSide(1, border_color),
        text_style=ft.TextStyle(weight=ft.FontWeight.W_500),
        overlay_color=ft.Colors.with_opacity(0.08, ft.Colors.BLACK),
    )


def status_badge(label: str, kind: str = "primary"):
    palette = {
        "primary": PRIMARY,
        "secondary": SECONDARY,
        "warning": WARNING,
        "danger": DANGER,
        "success": SUCCESS,
        "neutral": NEUTRAL,
    }
    color = palette.get(kind, PRIMARY)
    text_color = ft.Colors.WHITE if kind != "warning" else "#1A1A1A"
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=10, vertical=4),
        border_radius=999,
        bgcolor=ft.Colors.with_opacity(0.28, color),
        border=ft.border.all(1, ft.Colors.with_opacity(0.62, color)),
        content=ft.Text(
            label,
            size=11,
            weight=ft.FontWeight.W_600,
            color=text_color,
            max_lines=1,
            no_wrap=True,
            overflow=ft.TextOverflow.CLIP,
        ),
    )


def severity_badge(level: str):
    severity_map = {
        "critical": ("Nguy cap", "danger"),
        "high": ("Cao", "warning"),
        "medium": ("Trung binh", "secondary"),
        "low": ("Thap", "neutral"),
    }
    label, kind = severity_map.get((level or "").lower(), ("Trung binh", "secondary"))
    return status_badge(label, kind)


def fmt_dt(iso_str: str, fmt: str = "%d/%m %H:%M") -> str:
    if not iso_str:
        return "—"
    try:
        return _dt.fromisoformat(iso_str[:19]).strftime(fmt)
    except Exception:
        return iso_str[:16]


def section_title(icon_name: str, text: str, subtitle: str = "") -> ft.Control:
    icon = getattr(ft.Icons, icon_name, ft.Icons.CIRCLE)
    controls: list[ft.Control] = [
        ft.Row(
            tight=True,
            spacing=8,
            controls=[
                ft.Icon(icon, size=18, color=ft.Colors.WHITE70),
                ft.Text(text, size=17, weight=ft.FontWeight.W_700),
            ],
        )
    ]
    if subtitle:
        controls.append(ft.Text(subtitle, size=11, color=ft.Colors.WHITE54))
    return ft.Column(tight=True, spacing=2, controls=controls)


def page_header(
    title: str,
    subtitle: str = "",
    icon_name: str = "INSIGHTS",
    actions: list[ft.Control] | None = None,
) -> ft.Control:
    icon = getattr(ft.Icons, icon_name, ft.Icons.CIRCLE)
    return ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Column(
                tight=True,
                spacing=2,
                controls=[
                    ft.Row(
                        tight=True,
                        spacing=10,
                        controls=[
                            ft.Icon(icon, size=20, color=ft.Colors.WHITE60),
                            ft.Text(title, size=24, weight=ft.FontWeight.W_700),
                        ],
                    ),
                    ft.Text(subtitle, size=11, color=ft.Colors.WHITE54) if subtitle else ft.Container(),
                ],
            ),
            ft.Row(spacing=8, controls=actions or []),
        ],
    )


def info_strip(
    text: str,
    tone: str = "neutral",
    icon_name: str = "INFO_OUTLINE",
) -> ft.Control:
    tone_color = {
        "neutral": NEUTRAL,
        "warning": WARNING,
        "success": SUCCESS,
        "danger": DANGER,
    }.get(tone, NEUTRAL)
    icon = getattr(ft.Icons, icon_name, ft.Icons.INFO_OUTLINE)
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        border_radius=14,
        bgcolor=ft.Colors.with_opacity(0.12, tone_color),
        border=ft.border.all(1, ft.Colors.with_opacity(0.24, tone_color)),
        content=ft.Row(
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Icon(icon, size=16, color=tone_color),
                ft.Text(text, size=11, color=ft.Colors.WHITE70, expand=True),
            ],
        ),
    )


def empty_state(text: str = "Không có dữ liệu") -> ft.Control:
    return ft.Container(
        padding=24,
        alignment=ft.alignment.center,
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
            spacing=8,
            controls=[
                ft.Icon(ft.Icons.INBOX_OUTLINED, size=32, color=ft.Colors.WHITE24),
                ft.Text(text, color=ft.Colors.WHITE50, size=13, text_align=ft.TextAlign.CENTER),
            ],
        ),
    )


def inline_field(
    label: str,
    icon=None,
    value: str = "",
    password: bool = False,
    keyboard_type=None,
    expand: bool | int = True,
    hint: str = "",
) -> ft.TextField:
    return ft.TextField(
        label=label,
        hint_text=hint or None,
        prefix_icon=icon,
        value=value,
        password=password,
        can_reveal_password=password,
        keyboard_type=keyboard_type,
        border_radius=12,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.28, ft.Colors.WHITE),
        focused_border_color=PRIMARY,
        focused_border_width=2,
        label_style=ft.TextStyle(color=ft.Colors.WHITE70, size=12),
        text_style=ft.TextStyle(color=ft.Colors.WHITE, size=13),
        cursor_color=ft.Colors.WHITE,
        content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
        expand=expand,
    )


def metric_card(title: str, value: str, icon=ft.Icons.INSIGHTS, accent=PRIMARY):
    return glass_container(
        padding=18,
        radius=20,
        content=ft.Column(
            tight=True,
            spacing=8,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(title, size=12, color=ft.Colors.WHITE60),
                        ft.Icon(icon, color=accent, size=18),
                    ],
                ),
                ft.Text(value, size=26, weight=ft.FontWeight.W_700),
            ],
        ),
    )


def overflow_action_button(items: list[tuple[str, str, object]]) -> ft.PopupMenuButton:
    return ft.PopupMenuButton(
        icon=ft.Icons.MORE_VERT,
        icon_color=ft.Colors.WHITE70,
        tooltip="Them thao tac",
        items=[
            ft.PopupMenuItem(
                text=text,
                icon=getattr(ft.Icons, icon_name, ft.Icons.CIRCLE),
                on_click=on_click,
            )
            for text, icon_name, on_click in items
        ],
    )


def open_bottom_sheet(page: ft.Page, title: str, body: ft.Control) -> ft.BottomSheet:
    sheet = ft.BottomSheet(
        enable_drag=True,
        show_drag_handle=True,
        is_scroll_controlled=True,
        content=ft.SafeArea(
            minimum_padding=ft.padding.only(left=12, right=12, top=8, bottom=12),
            content=ft.Container(
                border_radius=16,
                bgcolor=ft.Colors.with_opacity(0.98, "#17232D"),
                border=ft.border.all(1, ft.Colors.with_opacity(0.18, ft.Colors.WHITE)),
                padding=ft.padding.all(12),
                content=ft.Column(
                    tight=True,
                    spacing=10,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(title, size=15, weight=ft.FontWeight.W_700),
                                ft.IconButton(
                                    icon=ft.Icons.CLOSE,
                                    icon_size=16,
                                    on_click=lambda e: page.close(sheet),
                                ),
                            ],
                        ),
                        body,
                    ],
                ),
            ),
        ),
    )
    page.open(sheet)
    return sheet


def collapsible_section(
    title: str,
    content: ft.Control,
    note: str = "",
    icon_name: str = "UNFOLD_MORE",
    initially_open: bool = False,
) -> ft.Control:
    state = {"open": initially_open}
    body_ref = ft.Ref[ft.Container]()
    chevron_ref = ft.Ref[ft.Icon]()

    def _toggle(e):
        state["open"] = not state["open"]
        if body_ref.current:
            body_ref.current.visible = state["open"]
            body_ref.current.update()
        if chevron_ref.current:
            chevron_ref.current.name = (
                ft.Icons.KEYBOARD_ARROW_UP if state["open"] else ft.Icons.KEYBOARD_ARROW_DOWN
            )
            chevron_ref.current.update()

    return ft.Container(
        border_radius=16,
        bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.WHITE),
        border=ft.border.all(1, ft.Colors.with_opacity(0.14, ft.Colors.WHITE)),
        content=ft.Column(
            spacing=0,
            controls=[
                ft.Container(
                    ink=True,
                    on_click=_toggle,
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Row(
                                tight=True,
                                spacing=8,
                                controls=[
                                    ft.Icon(
                                        getattr(ft.Icons, icon_name, ft.Icons.CIRCLE),
                                        size=16,
                                        color=ft.Colors.WHITE60,
                                    ),
                                    ft.Column(
                                        tight=True,
                                        spacing=1,
                                        controls=[
                                            ft.Text(title, size=12, weight=ft.FontWeight.W_700),
                                            ft.Text(note, size=10, color=ft.Colors.WHITE54)
                                            if note
                                            else ft.Container(),
                                        ],
                                    ),
                                ],
                            ),
                            ft.Icon(
                                ref=chevron_ref,
                                name=ft.Icons.KEYBOARD_ARROW_UP
                                if initially_open
                                else ft.Icons.KEYBOARD_ARROW_DOWN,
                                size=18,
                                color=ft.Colors.WHITE54,
                            ),
                        ],
                    ),
                ),
                ft.Container(
                    ref=body_ref,
                    visible=initially_open,
                    padding=ft.padding.only(left=12, right=12, bottom=12),
                    content=content,
                ),
            ],
        ),
    )


def sticky_action_bar(actions: list[ft.Control]) -> ft.Control:
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=10, vertical=10),
        border_radius=20,
        bgcolor=ft.Colors.with_opacity(0.26, "#17232D"),
        border=ft.border.all(1, ft.Colors.with_opacity(0.16, ft.Colors.WHITE)),
        shadow=ft.BoxShadow(
            blur_radius=18,
            color=ft.Colors.with_opacity(0.24, ft.Colors.BLACK),
            offset=ft.Offset(0, 8),
        ),
        content=ft.Row(
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=actions,
        ),
    )
