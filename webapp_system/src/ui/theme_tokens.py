from __future__ import annotations

import flet as ft

PRIMARY = "#4CAF50"
SECONDARY = "#56CCF2"
WARNING = "#F2C94C"
DANGER = "#FF7A7A"
SUCCESS = "#6BD38B"
NEUTRAL = "#A9B4C2"
TEXT_DARK = "#06131B"

_BTN_NEAR_BLACK = "#222222"
_BTN_RAUSCH = "#ff385c"
_BTN_DEEP_RAUSCH = "#e00b41"
_BTN_SURFACE = "#F2F2F2"
_BTN_ERROR = "#C13515"
_BTN_ERROR_DARK = "#B32505"

GLASS_BG = ft.Colors.with_opacity(0.30, "#22323D")
GLASS_BORDER = ft.Colors.with_opacity(0.24, ft.Colors.WHITE)
GLASS_SHADOW = ft.BoxShadow(
    blur_radius=24,
    color=ft.Colors.with_opacity(0.28, ft.Colors.BLACK),
    offset=ft.Offset(0, 12),
)

BUTTON_PALETTE = {
    "primary": (_BTN_NEAR_BLACK, ft.Colors.WHITE, _BTN_RAUSCH),
    "secondary": (_BTN_RAUSCH, ft.Colors.WHITE, _BTN_DEEP_RAUSCH),
    "surface": (_BTN_SURFACE, _BTN_NEAR_BLACK, ft.Colors.with_opacity(0.12, ft.Colors.BLACK)),
    "warning": (WARNING, TEXT_DARK, WARNING),
    "danger": (_BTN_ERROR, ft.Colors.WHITE, _BTN_ERROR_DARK),
}
