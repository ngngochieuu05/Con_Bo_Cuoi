import flet as ft
import time

DEFAULT_ADMIN = {
    "username": "admin",
    "password": "admin123",
    "name": "Quản Trị Viên Trang Trại",
}

# ── Farm palette ──
GREEN_DARK  = "#1B5E20"
GREEN_MID   = "#2E7D32"
GREEN_LIGHT = "#4CAF50"
YELLOW_WARM = "#F9A825"
CREAM       = "#F1F8E9"


class FarmAdminLoginUI:
    def __init__(self, page: ft.Page, go_back_callback=None):
        self.page              = page
        self.go_back_callback  = go_back_callback
        self.page.title        = "🐄 Con Bò Cười Admin - Đăng Nhập"
        self.page.padding      = 0
        from src.ui.theme import apply_theme
        apply_theme(self.page)
        self.page.theme_mode   = ft.ThemeMode.DARK

        self.bg_image_path    = r"src/ui/data/image_user/backround.jpg"
        self.admin_icon_path  = r"src/ui/data/image_admin/image_btnlogo_admin.png"

        self.show_login_view()

    def show_login_view(self):
        self.page.clean()

        input_style = {
            "border_radius": 12,
            "bgcolor":       ft.Colors.with_opacity(0.05, "onSurface"),
            "text_size":     14,
            "content_padding": 16,
            "border_color":  "outlineVariant",
            "focused_border_color": "primary",
            "focused_color": "primary",
            "cursor_color":  "primary",
            "label_style":   ft.TextStyle(color="onSurfaceVariant"),
            "text_style":    ft.TextStyle(color="onBackground"),
        }

        user_input = ft.TextField(
            label="Tài khoản quản trị", value="admin",
            prefix_icon=ft.Icons.MANAGE_ACCOUNTS_ROUNDED, **input_style,
        )
        pass_input = ft.TextField(
            label="Mật khẩu", value="admin123",
            prefix_icon=ft.Icons.LOCK_OUTLINE_ROUNDED,
            password=True, can_reveal_password=True, **input_style,
        )
        error_text = ft.Text("", color=ft.Colors.RED_600, size=12,
                             visible=False, text_align=ft.TextAlign.CENTER)

        def handle_login(e):
            error_text.visible = False
            error_text.update()
            username = user_input.value.strip()
            password = pass_input.value.strip()

            if username != DEFAULT_ADMIN["username"]:
                user_input.error_text = "Tài khoản không tồn tại!"
                user_input.update(); return

            if password != DEFAULT_ADMIN["password"]:
                pass_input.error_text = "Mật khẩu không đúng!"
                pass_input.update(); return

            # ✅ success
            self.page.open(ft.SnackBar(
                ft.Text(f"🌾 Chào mừng, {DEFAULT_ADMIN['name']}"),
                bgcolor="primary",
            ))
            self.page.update()
            time.sleep(0.5)
            self.page.controls.clear()
            self.page.update()
            from .laucher_admin import main as admin_main
            admin_main(self.page, go_back_callback=self.go_back_callback)

        # ── Login card ──
        login_card = ft.Container(
            width=420, padding=40,
            bgcolor="surface",
            border_radius=22,
            border=ft.border.all(1, "outlineVariant"),
            shadow=ft.BoxShadow(blur_radius=32, color=ft.Colors.with_opacity(0.2, "shadow"),
                                spread_radius=2),
            content=ft.Column([
                # Back button + Logo
                ft.Stack([
                    ft.Container(
                        content=ft.Column([
                            ft.Container(
                                content=ft.Image(
                                    src=self.admin_icon_path,
                                    width=80, height=70,
                                    fit=ft.ImageFit.CONTAIN,
                                    error_content=ft.Icon(
                                        ft.Icons.MANAGE_ACCOUNTS_ROUNDED,
                                        size=56, color="primary",
                                    ),
                                ),
                                alignment=ft.alignment.center,
                            ),
                            ft.Container(height=8),
                            ft.Text("ĐĂNG NHẬP QUẢN TRỊ", size=22,
                                    weight=ft.FontWeight.BOLD, color="onBackground",
                                    text_align=ft.TextAlign.CENTER),
                            ft.Text("Con Bò Cười · Trang Trại Thông Minh",
                                    size=12, color="primary",
                                    italic=True, text_align=ft.TextAlign.CENTER),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        alignment=ft.alignment.center,
                    ),
                    ft.Container(
                        content=ft.IconButton(
                            icon=ft.Icons.ARROW_BACK_IOS_ROUNDED,
                            icon_color="onBackground", icon_size=20,
                            on_click=lambda e: self._go_back_to_main(),
                            tooltip="Quay lại",
                        ),
                        left=0, top=0,
                    ),
                ], height=140),

                ft.Container(height=12),

                # Hint badge
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.INFO_OUTLINE_ROUNDED, size=14,
                                color="tertiary"),
                        ft.Text("admin / admin123", size=11, color="tertiary",
                                italic=True),
                    ], spacing=6, alignment=ft.MainAxisAlignment.CENTER),
                    bgcolor=ft.Colors.with_opacity(0.1, "tertiary"), border_radius=10,
                    padding=ft.padding.symmetric(horizontal=14, vertical=7),
                    border=ft.border.all(1, ft.Colors.with_opacity(0.2, "tertiary")),
                ),
                ft.Container(height=14),

                user_input,
                ft.Container(height=12),
                pass_input,
                ft.Container(height=6),
                error_text,
                ft.Container(height=16),

                # Login button
                ft.ElevatedButton(
                    "🌾  Đăng Nhập", width=float("inf"), height=52,
                    on_click=handle_login,
                    style=ft.ButtonStyle(
                        bgcolor="primary",
                        color=ft.Colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=12),
                        elevation=4,
                        overlay_color=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
                    ),
                ),
                ft.Container(height=10),
                ft.Text("© 2026 Con Bò Cười", size=10,
                        color="onSurfaceVariant", text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
        )

        self._render_background(login_card)

    def _render_background(self, card):
        layout = ft.Stack([
            ft.Image(src=self.bg_image_path, width=float("inf"), height=float("inf"),
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
            ft.Container(expand=True, alignment=ft.alignment.center, content=card),
        ], expand=True)
        self.page.add(layout)

    def _go_back_to_main(self):
        if self.go_back_callback:
            self.page.controls.clear()
            self.page.update()
            self.go_back_callback()


def main(page: ft.Page, go_back_callback=None):
    FarmAdminLoginUI(page, go_back_callback=go_back_callback)
