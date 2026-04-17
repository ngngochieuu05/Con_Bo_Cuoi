from __future__ import annotations
import flet as ft

PRIMARY = "#4CAF50"
SECONDARY = "#56CCF2"
WARNING = "#F2C94C"
DANGER = "#FF7A7A"
TEXT_DARK = "#06131B"

# ── Airbnb button tokens ────────────────────────────────────────────────────
_BTN_NEAR_BLACK  = "#222222"   # primary bg
_BTN_RAUSCH      = "#ff385c"   # brand accent / hover
_BTN_DEEP_RAUSCH = "#e00b41"   # secondary hover (pressed)
_BTN_SURFACE     = "#f2f2f2"   # surface bg
_BTN_ERROR       = "#c13515"   # danger / error
_BTN_ERROR_DARK  = "#b32505"   # danger hover
# ───────────────────────────────────────────────────────────────────────────

GLASS_BG = ft.Colors.with_opacity(0.16, ft.Colors.WHITE)
GLASS_BORDER = ft.Colors.with_opacity(0.18, ft.Colors.WHITE)
GLASS_SHADOW = ft.BoxShadow(
    blur_radius=28,
    color=ft.Colors.BLACK45,
    offset=ft.Offset(0, 14),
)


def glass_container(content, width=None, height=None, padding: int | ft.Padding = 24, radius=28):
    return ft.Container(
        width=width,
        height=height,
        padding=padding,
        bgcolor=GLASS_BG,
        border=ft.border.all(1, GLASS_BORDER),
        border_radius=radius,
        shadow=GLASS_SHADOW,
        content=content,
    )


def button_style(kind="primary", radius=8):
    """
    Airbnb-inspired button style.
      primary   → near-black #222222, hover → Rausch Red #ff385c
      secondary → Rausch Red #ff385c, hover → Deep Rausch #e00b41
      surface   → light #f2f2f2 (circular/utility buttons)
      warning   → amber (functional, kept as-is)
      danger    → error red #c13515
    """
    palette = {
        "primary":   (_BTN_NEAR_BLACK,  ft.Colors.WHITE,  _BTN_RAUSCH),
        "secondary": (_BTN_RAUSCH,      ft.Colors.WHITE,  _BTN_DEEP_RAUSCH),
        "surface":   (_BTN_SURFACE,     _BTN_NEAR_BLACK,  ft.Colors.with_opacity(0.12, ft.Colors.BLACK)),
        "warning":   (WARNING,          TEXT_DARK,        WARNING),
        "danger":    (_BTN_ERROR,       ft.Colors.WHITE,  _BTN_ERROR_DARK),
    }
    bg, fg, hover = palette.get(kind, palette["primary"])

    border_color = (
        ft.Colors.with_opacity(0.18, ft.Colors.BLACK)
        if kind == "surface"
        else bg
    )

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
    }
    color = palette.get(kind, PRIMARY)
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
        border_radius=10,
        bgcolor=ft.Colors.with_opacity(0.22, color),
        border=ft.border.all(1, ft.Colors.with_opacity(0.45, color)),
        content=ft.Text(
            label, size=11, weight=ft.FontWeight.W_600,
            max_lines=1, no_wrap=True,
            overflow=ft.TextOverflow.CLIP,
        ),
    )


def fmt_dt(iso_str: str, fmt: str = "%d/%m %H:%M") -> str:
    """Format ISO datetime thành chuỗi ngắn dễ đọc."""
    if not iso_str:
        return "—"
    try:
        from datetime import datetime as _dt
        return _dt.fromisoformat(iso_str[:19]).strftime(fmt)
    except Exception:
        return iso_str[:16]


def section_title(icon_name: str, text: str, subtitle: str = "") -> ft.Control:
    """Tiêu đề section với icon + text, tùy chọn subtitle."""
    icon = getattr(ft.Icons, icon_name, ft.Icons.CIRCLE)
    controls: list[ft.Control] = [
        ft.Row(tight=True, spacing=8, controls=[
            ft.Icon(icon, size=18, color=ft.Colors.WHITE70),
            ft.Text(text, size=17, weight=ft.FontWeight.W_700),
        ])
    ]
    if subtitle:
        controls.append(ft.Text(subtitle, size=11, color=ft.Colors.WHITE54))
    return ft.Column(tight=True, spacing=2, controls=controls)


def empty_state(text: str = "Không có dữ liệu") -> ft.Control:
    return ft.Container(
        padding=24,
        alignment=ft.Alignment.CENTER,
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
            spacing=8,
            controls=[
                ft.Icon(ft.Icons.INBOX, size=36, color=ft.Colors.WHITE24),
                ft.Text(text, color=ft.Colors.WHITE38, size=13),
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
    """TextField compact dùng bên trong form của các page (không phải auth)."""
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
                        ft.Text(title, size=13, color=ft.Colors.WHITE70),
                        ft.Icon(icon, color=accent, size=18),
                    ],
                ),
                ft.Text(value, size=24, weight=ft.FontWeight.W_700),
            ],
        ),
    )


def _on_row_hover(e: ft.ControlEvent):
    e.control.bgcolor = (
        ft.Colors.with_opacity(0.22, ft.Colors.WHITE)
        if e.data == "true"
        else ft.Colors.with_opacity(0.09, ft.Colors.WHITE)
    )
    e.control.update()


def data_table(
    headers: list[str],
    rows: list[list[ft.Control]],
    col_flex: list[int] | None = None,
):
    """Bảng dữ liệu glassmorphism.
    col_flex: danh sách flex weight cho từng cột (mặc định bằng nhau).
    """
    n = len(headers)
    flex = col_flex if (col_flex and len(col_flex) == n) else [1] * n

    header = ft.Container(
        padding=ft.padding.symmetric(horizontal=12, vertical=9),
        border_radius=12,
        bgcolor=ft.Colors.with_opacity(0.28, ft.Colors.WHITE),
        content=ft.Row(
            controls=[
                ft.Container(
                    expand=flex[i],
                    content=ft.Text(
                        h, weight=ft.FontWeight.W_700, size=12,
                        max_lines=1, overflow=ft.TextOverflow.CLIP,
                    ),
                )
                for i, h in enumerate(headers)
            ]
        ),
    )
    body_rows = []
    for row in rows:
        body_rows.append(
            ft.Container(
                ink=True,
                bgcolor=ft.Colors.with_opacity(0.09, ft.Colors.WHITE),
                border_radius=10,
                padding=ft.padding.symmetric(horizontal=12, vertical=9),
                on_hover=_on_row_hover,
                content=ft.Row(
                    controls=[
                        ft.Container(expand=flex[i], content=cell)
                        for i, cell in enumerate(row)
                    ]
                ),
            )
        )
    return ft.Column(
        spacing=5,
        controls=[header, ft.Column(spacing=4, controls=body_rows)],
    )


def build_background(content: ft.Control):
    return ft.Stack(
        expand=True,
        controls=[
            ft.Container(
                expand=True,
                image=ft.DecorationImage(src="backround.png", fit="cover"),
                gradient=ft.LinearGradient(
                    begin=ft.Alignment.TOP_LEFT,
                    end=ft.Alignment.BOTTOM_RIGHT,
                    colors=["#0B1E2A99", "#17384Acc"],
                ),
            ),
            ft.Container(expand=True, bgcolor=ft.Colors.with_opacity(0.52, ft.Colors.BLACK)),
            content,
        ],
    )


def _build_glass_nav_bar(navigation_items, selected_key, on_select):
    """Apple Liquid Glass floating bottom nav bar."""

    def _on_hover(e, is_sel):
        if not is_sel:
            e.control.bgcolor = (
                ft.Colors.with_opacity(0.14, ft.Colors.WHITE)
                if e.data == "true"
                else ft.Colors.TRANSPARENT
            )
            e.control.update()

    items = []
    for key, label, icon_name in navigation_items:
        icon = getattr(ft.Icons, icon_name, ft.Icons.CIRCLE)
        is_selected = key == selected_key
        # Rút gọn label xuống tối đa 6 ký tự để vừa phone
        short_label = label if len(label) <= 7 else label[:6] + "…"
        items.append(
            ft.Container(
                expand=1,
                on_click=lambda e, k=key: on_select(k),
                on_hover=lambda e, s=is_selected: _on_hover(e, s),
                border_radius=20,
                animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
                bgcolor=(
                    ft.Colors.with_opacity(0.30, PRIMARY)
                    if is_selected
                    else ft.Colors.TRANSPARENT
                ),
                padding=ft.padding.symmetric(vertical=7, horizontal=2),
                content=ft.Column(
                    tight=True,
                    spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(
                            icon,
                            color=ft.Colors.WHITE if is_selected else ft.Colors.WHITE54,
                            size=20,
                        ),
                        ft.Text(
                            short_label,
                            size=8,
                            color=ft.Colors.WHITE if is_selected else ft.Colors.WHITE54,
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
        bgcolor=ft.Colors.with_opacity(0.20, ft.Colors.WHITE),
        border=ft.border.all(1, ft.Colors.with_opacity(0.32, ft.Colors.WHITE)),
        shadow=ft.BoxShadow(
            blur_radius=36,
            spread_radius=0,
            color=ft.Colors.with_opacity(0.40, ft.Colors.BLACK),
            offset=ft.Offset(0, 10),
        ),
        padding=ft.padding.symmetric(horizontal=10, vertical=0),
        content=ft.Row(spacing=0, controls=items),
    )


def _build_avatar_btn(page: ft.Page | None, on_profile=None) -> ft.Control:
    """Circular avatar button shown in the top-right header corner."""
    b64 = None
    ho_ten = "?"
    if page is not None:
        try:
            b64 = page.data.get("anh_dai_dien") if isinstance(page.data, dict) else None
            ho_ten = (page.data.get("ho_ten") if isinstance(page.data, dict) else None) or "?"
        except Exception:
            pass
    initial = (ho_ten or "?")[0].upper()
    inner = (
        ft.Image(src_base64=b64, width=36, height=36, fit="cover")
        if b64
        else ft.Text(initial, size=14, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE)
    )
    return ft.Container(
        width=38, height=38,
        border_radius=19,
        bgcolor=ft.Colors.with_opacity(0.30, PRIMARY),
        border=ft.border.all(2, ft.Colors.with_opacity(0.55, ft.Colors.WHITE)),
        alignment=ft.Alignment.CENTER,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        tooltip="Hồ sơ cá nhân",
        on_click=lambda e: on_profile() if on_profile else None,
        content=inner,
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
    # Đọc is_mobile từ page.data (đặt từ main.py) — đảm bảo nhất quán
    is_mobile = True
    if page is not None:
        try:
            data = page.data
            if isinstance(data, dict):
                is_mobile = data.get("is_mobile", True)
            else:
                # fallback: cố gắng đọc window.width
                win_w = page.window.width
                if win_w and win_w > 100:
                    is_mobile = win_w <= 900
        except Exception:
            is_mobile = True

    if is_mobile:
        header = ft.Container(
            padding=ft.padding.only(left=16, right=16, top=14, bottom=10),
            bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.WHITE),
            border=ft.border.only(
                bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.14, ft.Colors.WHITE))
            ),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(
                        spacing=1,
                        tight=True,
                        controls=[
                            ft.Text(role_title, size=15, weight=ft.FontWeight.W_700),
                            ft.Text(role_subtitle, size=10, color=ft.Colors.WHITE60),
                        ],
                    ),
                    _build_avatar_btn(page, on_profile),
                ],
            ),
        )

        glass_nav = _build_glass_nav_bar(navigation_items, selected_key, on_select)

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
                                padding=ft.padding.only(
                                    left=10, right=10, top=8, bottom=96
                                ),
                                content=glass_container(main_content, padding=14, radius=18),
                            ),
                        ],
                    ),
                    glass_nav,
                ],
            )
        )

    sidebar_controls = [
        ft.Text(role_title, size=22, weight=ft.FontWeight.W_700),
        ft.Text(role_subtitle, size=12, color=ft.Colors.WHITE70),
        ft.Divider(color=ft.Colors.WHITE24),
    ]
    for key, label, icon_name in navigation_items:
        icon = getattr(ft.Icons, icon_name, ft.Icons.CIRCLE)
        sidebar_controls.append(
            ft.TextButton(
                text=label,
                icon=icon,
                style=ft.ButtonStyle(
                    color=ft.Colors.WHITE,
                    bgcolor=(
                        ft.Colors.with_opacity(0.28, PRIMARY)
                        if selected_key == key
                        else ft.Colors.TRANSPARENT
                    ),
                    shape=ft.RoundedRectangleBorder(radius=12),
                ),
                on_click=lambda e, k=key: on_select(k),
            )
        )
    sidebar_controls.append(ft.Container(expand=True))

    top_bar = ft.Container(
        padding=ft.padding.only(left=18, right=18, top=10, bottom=10),
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border=ft.border.only(
            bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.12, ft.Colors.WHITE))
        ),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.END,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[_build_avatar_btn(page, on_profile)],
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
                            width=280,
                            padding=18,
                            content=glass_container(
                                ft.Column(expand=True, spacing=10, controls=sidebar_controls),
                                padding=20,
                            ),
                        ),
                        ft.Container(
                            expand=True,
                            padding=ft.padding.only(top=14, right=18, bottom=18),
                            content=glass_container(main_content, padding=20),
                        ),
                    ],
                ),
            ],
        )
    )


def auth_text_field(
    label: str,
    icon=None,
    password: bool = False,
    can_reveal: bool = False,
) -> ft.TextField:
    """TextField glassmorphism chuẩn cho màn hình auth."""
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


def auth_dropdown(
    label: str,
    options: list[tuple[str, str]],
    value: str | None = None,
) -> ft.Dropdown:
    """Dropdown glassmorphism chuẩn cho màn hình auth."""
    return ft.Dropdown(
        label=label,
        value=value,
        border_radius=14,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.28, ft.Colors.WHITE),
        focused_border_color=PRIMARY,
        focused_border_width=2,
        label_style=ft.TextStyle(color=ft.Colors.WHITE70, size=13),
        options=[ft.dropdown.Option(k, v) for k, v in options],
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
                    alignment=ft.Alignment.CENTER,
                    padding=ft.padding.symmetric(horizontal=16, vertical=36),
                    content=form_card,
                ),
                logo,
            ],
        )
    )
