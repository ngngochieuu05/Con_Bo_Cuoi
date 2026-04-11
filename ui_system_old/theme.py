"""
Con Bò Cười — Design System / Theme Constants
Dynamic Theme mode: adapts to Light / Dark automatically via Flet semantic colors.
"""
import flet as ft

# ═══════════════════════════════════════════
#  COLOR PALETTE (SEMANTIC MAPPING)
# ═══════════════════════════════════════════
BG_MAIN      = "background"
BG_PANEL     = "surface"
BG_SIDEBAR   = "surfaceContainerLow"
BG_HEADER    = "surfaceContainerHigh"

PRIMARY      = "primary"
PRIMARY_DARK = "primaryContainer"
SECONDARY    = "secondary"
ACCENT       = "tertiary"

TEXT_MAIN    = "onBackground"
TEXT_SUB     = "onSurfaceVariant"
TEXT_MUTED   = "outline"

WARNING      = "errorContainer"
DANGER       = "error"
SUCCESS      = "primary"
INFO         = "tertiary"

BORDER       = "outlineVariant"
HOVER_OVERLAY = "shadow"

# Màu gradient card KPI (semantic mapping)
GRAD_TEAL    = ["primary", "primaryContainer"]
GRAD_CYAN    = ["tertiary", "secondary"]
GRAD_WARN    = ["errorContainer", "onErrorContainer"]
GRAD_DANGER  = ["error", "onError"]
GRAD_PURPLE  = ["secondary", "secondaryContainer"]

# ═══════════════════════════════════════════
#  TYPOGRAPHY
# ═══════════════════════════════════════════
FONT_MAIN    = "Segoe UI"

SIZE_H1      = 24
SIZE_H2      = 18
SIZE_H3      = 15
SIZE_BODY    = 13
SIZE_CAPTION = 11

# ═══════════════════════════════════════════
#  SPACING & SHAPE
# ═══════════════════════════════════════════
RADIUS_CARD  = 14
RADIUS_BTN   = 8
RADIUS_INPUT = 8
RADIUS_BADGE = 20

PAD_CARD     = ft.padding.all(20)
PAD_PAGE     = ft.padding.all(20)

SHADOW_CARD  = ft.BoxShadow(
    blur_radius=18,
    color=ft.Colors.with_opacity(0.25, "shadow"),
    offset=ft.Offset(0, 4),
)
SHADOW_CARD_GLOW = ft.BoxShadow(
    blur_radius=24,
    color=ft.Colors.with_opacity(0.08, "primary"),
    offset=ft.Offset(0, 4),
)

# ═══════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════
SIDEBAR_WIDTH        = 235
SIDEBAR_COLLAPSED_W  = 64
HEADER_HEIGHT        = 60

# ═══════════════════════════════════════════
#  THEME FACTORIES
# ═══════════════════════════════════════════
def get_dark_theme() -> ft.Theme:
    return ft.Theme(
        color_scheme=ft.ColorScheme(
            background="#0F1117",
            surface="#1A1D2E",
            surface_container_low="#141720",
            surface_container_high="#12151F",
            primary="#00C897",
            primary_container="#009E7A",
            secondary="#1DB8A4",
            tertiary="#00E5FF",
            on_background="#E8EAF6",
            on_surface_variant="#8892A4",
            outline="#4A5568",
            outline_variant="#2A2D3E",
            error_container="#FFB300",
            error="#FF5252",
            shadow="#000000",
        )
    )

def get_light_theme() -> ft.Theme:
    return ft.Theme(
        color_scheme=ft.ColorScheme(
            background="#F4F7F6",
            surface="#FFFFFF",
            surface_container_low="#DFE6E5",
            surface_container_high="#EAEFEF",
            primary="#00C897",
            primary_container="#009E7A",
            secondary="#1DB8A4",
            tertiary="#00E5FF",
            on_background="#1A1D2E",
            on_surface_variant="#556270",
            outline="#A0ABC0",
            outline_variant="#D1D9E6",
            error_container="#F57F17",
            error="#D32F2F",
            shadow="#1D2A35",
        )
    )


def apply_theme(page: ft.Page):
    """Áp dụng bộ theme đồng bộ cho toàn app."""
    page.theme = get_light_theme()
    page.dark_theme = get_dark_theme()


# ═══════════════════════════════════════════
#  COMPONENT BUILDERS (reusable)
# ═══════════════════════════════════════════
def kpi_card(icon, title: str, value: str, subtitle: str,
             grad_colors=None, icon_bg: str = "primary") -> ft.Container:
    if grad_colors is None:
        grad_colors = GRAD_TEAL
    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Container(
                    content=ft.Icon(icon, color=ft.Colors.WHITE, size=20),
                    width=42, height=42, border_radius=21,
                    bgcolor=ft.Colors.with_opacity(0.25, ft.Colors.WHITE),
                    alignment=ft.alignment.center,
                ),
                ft.Container(expand=True),
                ft.Container(
                    content=ft.Text("▲ hôm nay", size=9,
                                    color=ft.Colors.with_opacity(0.75, ft.Colors.WHITE)),
                    bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.WHITE),
                    border_radius=10,
                    padding=ft.padding.symmetric(horizontal=7, vertical=3),
                ),
            ]),
            ft.Container(height=10),
            ft.Text(value, size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            ft.Text(title, size=12, color=ft.Colors.WHITE, weight=ft.FontWeight.W_500),
            ft.Text(subtitle, size=10, color=ft.Colors.with_opacity(0.7, ft.Colors.WHITE)),
        ], spacing=2),
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_left,
            end=ft.alignment.bottom_right,
            colors=grad_colors,
        ),
        border_radius=RADIUS_CARD,
        padding=ft.padding.symmetric(vertical=16, horizontal=18),
        shadow=ft.BoxShadow(
            blur_radius=20, offset=ft.Offset(0, 6),
            color=ft.Colors.with_opacity(0.3, grad_colors[0]),
        ),
        expand=True,
        animate_scale=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
    )


def panel(content, title: str = "", icon=None, action_widget=None,
          expand=False, width=None) -> ft.Container:
    header_row_items = []
    if icon:
        header_row_items.append(ft.Icon(icon, color=PRIMARY, size=18))
    if title:
        header_row_items.append(
            ft.Text(title, size=SIZE_H3, weight=ft.FontWeight.BOLD, color=TEXT_MAIN)
        )
    header_row_items.append(ft.Container(expand=True))
    if action_widget:
        header_row_items.append(action_widget)

    col = ft.Column([
        ft.Row(header_row_items, spacing=8),
        ft.Divider(color=BORDER, height=16),
        content,
    ], spacing=0)

    return ft.Container(
        content=col,
        bgcolor=BG_PANEL,
        border_radius=RADIUS_CARD,
        padding=PAD_CARD,
        border=ft.border.all(1, BORDER),
        shadow=SHADOW_CARD_GLOW,
        expand=expand,
        width=width,
    )


def primary_button(text: str, icon=None, on_click=None,
                   width=None, small=False) -> ft.Container:
    size = SIZE_CAPTION if small else SIZE_BODY
    pad = ft.padding.symmetric(horizontal=14, vertical=7) if small else \
          ft.padding.symmetric(horizontal=18, vertical=10)
    row_items = []
    if icon:
        row_items.append(ft.Icon(icon, color=ft.Colors.WHITE, size=14 if small else 16))
    row_items.append(ft.Text(text, color=ft.Colors.WHITE, size=size, weight=ft.FontWeight.W_600))
    return ft.Container(
        content=ft.Row(row_items, spacing=6, tight=True),
        bgcolor=PRIMARY,
        border_radius=RADIUS_BTN,
        padding=pad,
        ink=True,
        on_click=on_click,
        width=width,
        animate_scale=ft.Animation(120, ft.AnimationCurve.EASE_OUT),
    )


def status_badge(text: str, color: str = PRIMARY) -> ft.Container:
    return ft.Container(
        content=ft.Text(text, size=10, color=ft.Colors.WHITE,
                        weight=ft.FontWeight.BOLD),
        bgcolor=color,
        border_radius=RADIUS_BADGE,
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
    )


def avatar_initials(name: str, size: int = 36) -> ft.Container:
    initial = name[0].upper() if name else "?"
    return ft.Container(
        content=ft.Text(initial, color=ft.Colors.WHITE, size=size // 2.5,
                        weight=ft.FontWeight.BOLD),
        width=size, height=size, border_radius=size // 2,
        bgcolor=PRIMARY, alignment=ft.alignment.center,
    )


def divider() -> ft.Divider:
    return ft.Divider(color=BORDER, height=1)


def section_label(text: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(
            text.upper(), size=9, color=TEXT_SUB,
            weight=ft.FontWeight.BOLD,
            style=ft.TextStyle(letter_spacing=1.2),
        ),
        padding=ft.padding.only(left=14, top=12, bottom=4),
    )


def styled_input(label: str, hint: str = "", password: bool = False,
                 icon=None, width=None, expand=False) -> ft.TextField:
    return ft.TextField(
        label=label,
        hint_text=hint,
        password=password,
        can_reveal_password=password,
        prefix_icon=icon,
        width=width,
        expand=expand,
        border_radius=RADIUS_INPUT,
        border_color=BORDER,
        focused_border_color=PRIMARY,
        cursor_color=PRIMARY,
        label_style=ft.TextStyle(color=TEXT_SUB, size=SIZE_BODY),
        text_style=ft.TextStyle(color=TEXT_MAIN, size=SIZE_BODY),
        bgcolor=ft.Colors.with_opacity(0.05, "onSurface"),
        content_padding=ft.padding.symmetric(horizontal=14, vertical=12),
    )
