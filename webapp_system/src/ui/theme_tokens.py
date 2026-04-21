from __future__ import annotations

import flet as ft

PRIMARY = "#4FC38A"
SECONDARY = "#6FB7FF"
WARNING = "#E7B754"
DANGER = "#FF8B8B"
SUCCESS = "#73D79A"
NEUTRAL = "#AAB7C4"
TEXT_DARK = "#08141B"

_BTN_NEAR_BLACK = "#1B2730"
_BTN_RAUSCH = "#3FA877"
_BTN_DEEP_RAUSCH = "#2D875D"
_BTN_SURFACE = "#E8EDF1"
_BTN_ERROR = "#C84833"
_BTN_ERROR_DARK = "#AC3623"

GLASS_BG = ft.Colors.with_opacity(0.74, "#182833")
GLASS_BORDER = ft.Colors.with_opacity(0.14, "#F4F7FA")
GLASS_SHADOW = ft.BoxShadow(
    blur_radius=34,
    color=ft.Colors.with_opacity(0.30, ft.Colors.BLACK),
    offset=ft.Offset(0, 18),
)

BUTTON_PALETTE = {
    "primary": (PRIMARY, ft.Colors.WHITE, _BTN_RAUSCH),
    "secondary": (_BTN_NEAR_BLACK, ft.Colors.WHITE, "#22323D"),
    "surface": (_BTN_SURFACE, _BTN_NEAR_BLACK, ft.Colors.with_opacity(0.12, ft.Colors.BLACK)),
    "warning": (WARNING, TEXT_DARK, WARNING),
    "danger": (_BTN_ERROR, ft.Colors.WHITE, _BTN_ERROR_DARK),
}
