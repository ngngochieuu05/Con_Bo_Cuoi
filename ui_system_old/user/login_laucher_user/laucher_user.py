import flet as ft
import os
import time

# ── Farm palette ──
GREEN_DARK  = "#1B5E20"
GREEN_MID   = "#2E7D32"
GREEN_LIGHT = "#4CAF50"
YELLOW_WARM = "#F9A825"
BROWN       = "#5D4037"
TEAL        = "#00897B"
CREAM       = "#F1F8E9"


def main(page: ft.Page, go_back_callback=None, user_account=None):
    page.title           = "Con Bo Cuoi - Trang Chu Nong Ho"
    _is_mobile = getattr(page, 'web', False) or (
        getattr(page, 'platform', None) in (
            ft.PagePlatform.ANDROID, ft.PagePlatform.IOS
        )
    )
    if not _is_mobile:
        page.window_width    = 1280
        page.window_height   = 800
        page.window_min_width  = 400
        page.window_min_height = 600
        page.window_resizable  = True
    page.padding         = 0
    from src.ui.theme import apply_theme
    apply_theme(page)
    page.theme_mode      = ft.ThemeMode.DARK
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    bg_image_src = r"src/ui/data/image_user/backround.jpg"
    logo_src     = r"src/ui/data/image_user/Logo-removebg-preview.png"
    avatar_src   = "https://avatars.githubusercontent.com/u/1?v=4"

    # ── User info ──
    user_name     = user_account.get("name",      "Nông Hộ") if user_account else "Nông Hộ"
    user_id       = user_account.get("driver_id", "N/A")    if user_account else "N/A"
    user_plan     = user_account.get("plan",      "Free")    if user_account else "Free"
    plan_color    = YELLOW_WARM if user_plan == "Pro" else TEAL
    plan_label    = f"🌿 {user_plan}"

    # ── Actions ──
    def handle_start_click(e):
        sb = ft.SnackBar(ft.Text("🌾 Đang khởi động phiên giám sát..."),
                         bgcolor="primary")
        page.overlay.append(sb)
        sb.open = True
        page.update()
        time.sleep(0.4)

        def go_back_to_launcher():
            page.clean()
            main(page, go_back_callback, user_account)

        try:
            page.controls.clear()
            page.update()
            from ..control import main_user
            main_user.FarmUserApp(page,
                              go_back_callback=go_back_to_launcher,
                              user_account=user_account)
        except Exception as ex:
            import traceback; traceback.print_exc()
            page.open(ft.SnackBar(ft.Text(f"Lỗi: {ex}"), bgcolor=ft.Colors.RED_600))

    def handle_history_click(e):
        page.open(ft.SnackBar(ft.Text("📋 Đang tải lịch sử sự kiện..."),
                               bgcolor=TEAL))

    def handle_settings_click(e):
        def close_sheet(evt):
            sheet.open = False
            page.update()

        sheet = ft.BottomSheet(
            ft.Container(
                padding=24,
                bgcolor="surface",
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.SETTINGS_ROUNDED, color="primary", size=22),
                        ft.Text("Cài Đặt Nhanh", size=20, weight=ft.FontWeight.BOLD,
                                color="onBackground"),
                    ], spacing=8),
                    ft.Divider(color="outlineVariant"),
                    ft.Switch(label="Thông báo cảnh báo bò", value=True,
                              active_color=GREEN_LIGHT),
                    ft.Switch(label="Tự động ghi hình sự kiện", value=True,
                              active_color=GREEN_LIGHT),
                    ft.Switch(label="Rung khi có cảnh báo", value=False,
                              active_color=GREEN_LIGHT),
                    ft.Switch(label="Chế độ ban đêm", value=False,
                              active_color=GREEN_LIGHT),
                    ft.Divider(color="outlineVariant"),
                    ft.ElevatedButton("Đóng", on_click=close_sheet,
                                      width=float("inf"), bgcolor="primary",
                                      color=ft.Colors.WHITE,
                                      style=ft.ButtonStyle(
                                          shape=ft.RoundedRectangleBorder(radius=10)
                                      )),
                ], scroll=ft.ScrollMode.AUTO, tight=True, spacing=10),
            )
        )
        page.overlay.append(sheet)
        sheet.open = True
        page.update()

    def handle_logout(e):
        sb = ft.SnackBar(ft.Text("Đang đăng xuất..."),
                         bgcolor=ft.Colors.RED_700)
        page.overlay.append(sb)
        sb.open = True
        page.update()
        time.sleep(0.4)
        if go_back_callback:
            page.controls.clear()
            page.update()
            go_back_callback()
        else:
            try:
                from . import login_user
                page.controls.clear()
                page.update()
                login_user.main(page, go_back_callback)
            except Exception as ex:
                page.open(ft.SnackBar(ft.Text(f"Lỗi: {ex}"), bgcolor=ft.Colors.RED))

    # ── Button factory ──
    def farm_button(icon, title, gradient_colors, action):
        return ft.Container(
            width=330, height=88,
            gradient=ft.LinearGradient(
                begin=ft.alignment.center_left,
                end=ft.alignment.center_right,
                colors=gradient_colors,
            ),
            border_radius=18,
            shadow=ft.BoxShadow(blur_radius=14, color=ft.Colors.BLACK38,
                                offset=ft.Offset(0, 5)),
            border=ft.border.all(1.5, ft.Colors.with_opacity(0.1, "onSurface")),
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(icon, size=30, color=ft.Colors.WHITE),
                    width=56, height=56, border_radius=28,
                    bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
                    alignment=ft.alignment.center,
                ),
                ft.Container(width=10),
                ft.Text(title, size=18, weight=ft.FontWeight.BOLD,
                        color="onBackground"),
            ], alignment=ft.MainAxisAlignment.START,
               vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.only(left=18),
            ink=True, on_click=action,
            animate_scale=ft.Animation(110, ft.AnimationCurve.EASE_OUT),
            on_hover=lambda e: (
                setattr(e.control, "scale", 1.03 if e.data == "true" else 1.0),
                e.control.update()
            ),
        )

    btn_start   = farm_button(ft.Icons.PLAY_CIRCLE_ROUNDED,
                               "Bắt Đầu Giám Sát",
                               [ft.Colors.with_opacity(0.8, "secondary"), ft.Colors.with_opacity(0.6, "secondary")], handle_start_click)
    btn_history = farm_button(ft.Icons.HISTORY_ROUNDED,
                               "Xem Lịch Sử Sự Kiện",
                               [ft.Colors.with_opacity(0.8, "tertiary"), ft.Colors.with_opacity(0.6, "tertiary")], handle_history_click)
    btn_settings = farm_button(ft.Icons.SETTINGS_ROUNDED,
                                "Cài Đặt",
                                [ft.Colors.with_opacity(0.8, "primary"), ft.Colors.with_opacity(0.6, "primary")], handle_settings_click)

    # ── User card ──
    user_card = ft.Container(
        width=330, height=116,
        bgcolor="surface",
        border=ft.border.all(1, "outlineVariant"),
        border_radius=22,
        shadow=ft.BoxShadow(blur_radius=16, color=ft.Colors.with_opacity(0.2, "shadow"),
                            offset=ft.Offset(0, 4)),
        content=ft.Row([
            ft.Container(
                width=72, height=72, border_radius=36,
                border=ft.border.all(2.5, "primary"),
                content=ft.CircleAvatar(
                    foreground_image_src=avatar_src,
                    radius=32, bgcolor=ft.Colors.GREY_800,
                ),
            ),
            ft.Container(width=12),
            ft.Column([
                ft.Text(user_name, size=17, weight=ft.FontWeight.BOLD,
                        color="onBackground"),
                ft.Text(f"ID: {user_id}", size=12, color="onSurfaceVariant"),
                ft.Container(
                    content=ft.Text(plan_label, size=11, color=ft.Colors.WHITE,
                                    weight=ft.FontWeight.BOLD),
                    bgcolor=plan_color, border_radius=14,
                    padding=ft.padding.symmetric(horizontal=10, vertical=4),
                ),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=4),
        ], alignment=ft.MainAxisAlignment.START,
           vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.padding.only(left=18),
    )

    # ── Quick stat chips ──
    def chip(icon, label, val, color):
        return ft.Container(
            content=ft.Column([
                ft.Icon(icon, size=18, color=color),
                ft.Text(val, size=15, weight=ft.FontWeight.BOLD,
                        color="onBackground"),
                ft.Text(label, size=9, color="onSurfaceVariant"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=1),
            width=90, padding=ft.padding.symmetric(vertical=10, horizontal=6),
            bgcolor=ft.Colors.with_opacity(0.05, "onSurface"),
            border_radius=14,
            border=ft.border.all(1, "outlineVariant"),
        )

    stats_row = ft.Row([
        chip(ft.Icons.PETS,          "Đàn Bò",    "124", "error"),
        chip(ft.Icons.WARNING_AMBER, "Cảnh Báo",  "7",   "errorContainer"),
        chip(ft.Icons.VIDEOCAM,      "Camera",    "4",   "primary"),
    ], spacing=10, alignment=ft.MainAxisAlignment.CENTER)

    # Logo
    logo_widget = ft.Container(
        content=ft.Image(src=logo_src, width=86, height=86, fit=ft.ImageFit.CONTAIN,
                         error_content=ft.Icon(ft.Icons.ECO, size=70,
                                               color="primary")),
        alignment=ft.alignment.center,
    )
    title_block = ft.Column([
        ft.Text("CON BÒ CƯỜI", size=22, weight=ft.FontWeight.BOLD,
                color="onBackground", text_align=ft.TextAlign.CENTER),
        ft.Text("Nhận diện hành vi bò · Nông hộ",
                size=11, color="onSurfaceVariant", italic=True,
                text_align=ft.TextAlign.CENTER),
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4)

    main_column = ft.Column([
        ft.Container(height=44),
        logo_widget,
        ft.Container(height=6),
        title_block,
        ft.Container(height=16),
        stats_row,
        ft.Container(height=20),
        user_card,
        ft.Container(height=20),
        btn_start,
        ft.Container(height=12),
        btn_history,
        ft.Container(height=12),
        btn_settings,
        ft.Container(height=30),
        ft.TextButton(
            "Đăng xuất",
            icon=ft.Icons.LOGOUT_ROUNDED,
            icon_color="error",
            style=ft.ButtonStyle(color="error"),
            on_click=handle_logout,
        ),
        ft.Text("© 2026 Con Bò Cười", size=10, color="onSurfaceVariant",
                weight=ft.FontWeight.BOLD),
        ft.Container(height=20),
    ], alignment=ft.MainAxisAlignment.START,
       horizontal_alignment=ft.CrossAxisAlignment.CENTER,
       scroll=ft.ScrollMode.AUTO)

    # ── Background overlay ──
    bg_layer = ft.Stack([
        ft.Image(src=bg_image_src, width=float("inf"), height=float("inf"),
                 fit=ft.ImageFit.COVER,
                 error_content=ft.Container(
                     bgcolor="background", expand=True,
                 )),
        ft.Container(
            expand=True,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_center,
                end=ft.alignment.bottom_center,
                colors=[ft.Colors.with_opacity(0.85, "background"),
                        ft.Colors.with_opacity(0.95, "background")],
            )
        ),
    ])

    layout = ft.Stack([
        bg_layer,
        ft.Container(content=main_column, alignment=ft.alignment.center,
                     width=float("inf")),
    ], expand=True)

    page.add(layout)


if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.FLET_APP)