import flet as ft
import os
import time

# ── Farm palette ──
GREEN_DARK  = "#1B5E20"
GREEN_MID   = "#2E7D32"
GREEN_LIGHT = "#4CAF50"
YELLOW_WARM = "#F9A825"
BROWN       = "#5D4037"
CREAM       = "#F1F8E9"


def main(page: ft.Page, go_back_callback=None):
    page.title          = "Con Bò Cười Admin - Bảng Điều Hành"
    page.window_width   = 1280
    page.window_height  = 800
    page.window_min_width  = 400
    page.window_min_height = 600
    page.window_resizable  = True
    page.padding        = 0
    from src.ui.theme import apply_theme
    apply_theme(page)
    page.theme_mode     = ft.ThemeMode.DARK
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    bg_image_src = r"src/ui/data/image_user/backround.jpg"
    logo_src     = r"src/ui/data/image_laucher/Logo-removebg-preview.png"
    avatar_src   = r"src/ui/data/image_admin/avatar_super_admin.jpg"

    # ── Actions ──
    def handle_system_click(e):
        def go_back_to_launcher():
            page.clean()
            main(page, go_back_callback)
        try:
            from ..control import main_admin
            page.controls.clear()
            page.update()
            main_admin.main(page, go_back_to_launcher)
        except Exception as ex:
            import traceback; traceback.print_exc()
            page.open(ft.SnackBar(ft.Text(f"Lỗi: {ex}"), bgcolor=ft.Colors.RED))

    def handle_settings_click(e):
        def close_sheet(e):
            bottom_sheet.open = False
            page.update()

        bottom_sheet = ft.BottomSheet(
            ft.Container(
                padding=24,
                bgcolor="surface",
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.SETTINGS_ROUNDED, color="primary", size=22),
                        ft.Text("Cài Đặt Hệ Thống", size=20,
                                weight=ft.FontWeight.BOLD, color="onBackground"),
                    ], spacing=8),
                    ft.Divider(color="outlineVariant"),
                    ft.Switch(label="Thông báo âm thanh cảnh báo", value=True,
                              active_color=GREEN_LIGHT),
                    ft.Switch(label="Tự động sao lưu dữ liệu", value=True,
                              active_color=GREEN_LIGHT),
                    ft.Switch(label="Gửi email báo cáo hàng ngày", value=False,
                              active_color=GREEN_LIGHT),
                    ft.Switch(label="Chế độ đêm (Dark Mode)", value=False,
                              active_color=GREEN_LIGHT),
                    ft.Divider(color="outlineVariant"),
                    ft.ElevatedButton(
                        "Đóng", on_click=close_sheet,
                        width=float("inf"), bgcolor="primary",
                        color=ft.Colors.WHITE,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                    ),
                ], scroll=ft.ScrollMode.AUTO, tight=True, spacing=10),
            )
        )
        page.overlay.append(bottom_sheet)
        bottom_sheet.open = True
        page.update()

    def handle_logout(e):
        snackbar = ft.SnackBar(
            ft.Text("Đang đăng xuất..."), bgcolor=ft.Colors.RED_700,
        )
        page.overlay.append(snackbar)
        snackbar.open = True
        page.update()
        time.sleep(0.5)
        if go_back_callback:
            page.controls.clear()
            page.update()
            go_back_callback()
        else:
            try:
                from . import login_admin
                page.controls.clear()
                page.update()
                login_admin.main(page, go_back_callback)
            except Exception as ex:
                page.open(ft.SnackBar(ft.Text(f"Lỗi: {ex}"), bgcolor=ft.Colors.RED))

    # ── Button factory ──
    def farm_button(icon, title, subtitle, gradient_colors, action):
        return ft.Container(
            width=330, height=96,
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
                    content=ft.Icon(icon, size=32, color=ft.Colors.WHITE),
                    width=60, height=60, border_radius=30,
                    bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
                    alignment=ft.alignment.center,
                ),
                ft.Container(width=12),
                ft.Column([
                    ft.Text(title, size=18, weight=ft.FontWeight.BOLD,
                            color="onBackground"),
                    ft.Text(subtitle, size=11, color="onSurfaceVariant"),
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=2),
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

    btn_system = farm_button(
        ft.Icons.DASHBOARD_CUSTOMIZE_ROUNDED,
        "Hệ Thống Giám Sát",
        "Camera · AI · Báo cáo đàn bò",
        [ft.Colors.with_opacity(0.8, "secondary"), ft.Colors.with_opacity(0.6, "secondary")],
        handle_system_click,
    )
    btn_settings = farm_button(
        ft.Icons.SETTINGS_ROUNDED,
        "Cài Đặt",
        "Cấu hình Camera & Hệ thống",
        [ft.Colors.with_opacity(0.8, "primary"), ft.Colors.with_opacity(0.6, "primary")],
        handle_settings_click,
    )

    # ── Admin card ──
    admin_card = ft.Container(
        width=330, height=108,
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
                    radius=32,
                    bgcolor=ft.Colors.GREY_800,
                ),
            ),
            ft.Container(width=12),
            ft.Column([
                ft.Text("Admin Trang Trại", size=17,
                        weight=ft.FontWeight.BOLD, color="onBackground"),
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.SHIELD, size=12, color=ft.Colors.WHITE),
                        ft.Text("Super Admin", size=11, color=ft.Colors.WHITE,
                                weight=ft.FontWeight.BOLD),
                    ], spacing=4),
                    bgcolor="primary", border_radius=14,
                    padding=ft.padding.symmetric(horizontal=10, vertical=4),
                ),
                ft.Text("🌾 Con Bò Cười", size=10, color="onSurfaceVariant",
                        italic=True),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=4),
        ], alignment=ft.MainAxisAlignment.START,
           vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.padding.only(left=18),
    )

    # ── Logo from code (farm icon) ──
    logo_widget = ft.Container(
        content=ft.Image(
            src=logo_src, width=90, height=90, fit=ft.ImageFit.CONTAIN,
            error_content=ft.Icon(ft.Icons.ECO, size=70, color="primary"),
        ),
        alignment=ft.alignment.center,
    )

    logout_btn = ft.TextButton(
        "Đăng xuất",
        icon=ft.Icons.LOGOUT_ROUNDED,
        icon_color="error",
        style=ft.ButtonStyle(color="error"),
        on_click=handle_logout,
    )

    footer = ft.Text("© 2026 Con Bò Cười v2.0",
                     size=11, color="onSurfaceVariant",
                     weight=ft.FontWeight.BOLD)

    # ── Title block ──
    title_block = ft.Column([
        ft.Text("CON BÒ CƯỜI ADMIN", size=22, weight=ft.FontWeight.BOLD,
                color="onBackground", text_align=ft.TextAlign.CENTER),
        ft.Text("Hệ Thống Nhận Diện Hành Vi Bò", size=12,
                color="onSurfaceVariant", italic=True, text_align=ft.TextAlign.CENTER),
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4)

    main_column = ft.Column([
        ft.Container(height=50),
        logo_widget,
        ft.Container(height=6),
        title_block,
        ft.Container(height=26),
        admin_card,
        ft.Container(height=20),
        btn_system,
        ft.Container(height=14),
        btn_settings,
        ft.Container(height=36),
        logout_btn,
        footer,
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