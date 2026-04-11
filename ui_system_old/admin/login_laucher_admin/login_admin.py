import flet as ft
import time
import os
import sys
import json

# Class quản lý Đăng nhập Admin
class AdminUI:
    def __init__(self, page: ft.Page, go_back_callback=None):
        self.page = page
        self.go_back_callback = go_back_callback
        self.page.title = "Đăng Nhập Quản Trị Viên"
        self.page.padding = 0
        self.page.theme_mode = ft.ThemeMode.LIGHT
        
        # Cấu hình ảnh
        self.bg_image_path = r"src\ui\data\image_user\backround.jpg"
        self.admin_icon_path = r"src\ui\data\image_admin\image_btnlogo_admin.png"
        self.primary_color = "#4a6fa5" 

        self.show_login_view()

    # Màn hình đăng nhập
    def show_login_view(self):
        self.page.clean()
        
        input_style = {"border_radius": 10, "bgcolor": ft.Colors.WHITE, "text_size": 14, "content_padding": 15, "border_color": self.primary_color}
        
        # Sẵn tài khoản để test
        user_input = ft.TextField(label="Tài khoản", value="admin", prefix_icon=ft.Icons.ADMIN_PANEL_SETTINGS, **input_style)
        pass_input = ft.TextField(label="Mật khẩu", value="admin", prefix_icon=ft.Icons.LOCK, password=True, can_reveal_password=True, **input_style)

        login_card = ft.Container(
            width=400, padding=40, bgcolor=ft.Colors.WHITE, border_radius=20,
            shadow=ft.BoxShadow(blur_radius=20, color=ft.Colors.BLACK12),
            content=ft.Column([
                # Nút quay lại và Logo
                ft.Container(
                    content=ft.Stack([
                        ft.Container(
                            content=ft.Column([
                                ft.Image(src=self.admin_icon_path, width=100, height=80, fit=ft.ImageFit.CONTAIN,
                                    error_content=ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS, size=60, color=self.primary_color)),
                                ft.Text("ĐĂNG NHẬP", size=26, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_800),
                                ft.Text("Hệ thống quản trị", size=14, color=ft.Colors.GREY),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            alignment=ft.alignment.center
                        ),
                        ft.Container(
                            content=ft.IconButton(
                                icon=ft.Icons.ARROW_BACK,
                                icon_color=ft.Colors.BLUE_GREY_700,
                                on_click=lambda e: self._go_back_to_main(),
                                tooltip="Quay lại"
                            ),
                            left=0,
                            top=0
                        )
                    ]),
                    height=150
                ),
                ft.Container(height=10),
                user_input, ft.Container(height=15),
                pass_input, ft.Container(height=25),
                
                ft.ElevatedButton("Đăng nhập", width=float("inf"), height=50,
                    style=ft.ButtonStyle(bgcolor=self.primary_color, color=ft.Colors.WHITE, shape=ft.RoundedRectangleBorder(radius=10)),
                    on_click=lambda e: self._handle_login(user_input.value, pass_input.value)
                ),
                
                 ft.Container(height=20),
                 ft.Row([ft.Container(content=ft.Divider(), expand=True), ft.Text("HOẶC", size=12, color=ft.Colors.GREY), ft.Container(content=ft.Divider(), expand=True)], alignment=ft.MainAxisAlignment.CENTER),
                 ft.Container(height=20),
                 ft.TextButton(content=ft.Text("Đăng ký tài khoản Admin mới", color=self.primary_color, weight=ft.FontWeight.BOLD),
                    on_click=lambda e: self.show_register_view()
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )
        self._render_background(login_card)

    def show_register_view(self):
        self.page.clean()
        # Code đăng ký (rút gọn để tập trung vào logic chuyển trang)
        self.page.add(ft.Container(alignment=ft.alignment.center, content=ft.Column([
            ft.Text("Màn hình Đăng Ký (Demo)", size=30),
            ft.ElevatedButton("Quay lại", on_click=lambda e: self.show_login_view())
        ])))

    def _render_background(self, card):
        layout = ft.Stack([
            ft.Image(src=self.bg_image_path, width=float("inf"), height=float("inf"), fit=ft.ImageFit.COVER),
            ft.Container(expand=True, bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLUE_GREY_900)),
            ft.Container(expand=True, alignment=ft.alignment.center, content=card)
        ], expand=True)
        self.page.add(layout)

    def _go_back_to_main(self):
        if self.go_back_callback:
            self.page.controls.clear()
            self.page.update()
            self.go_back_callback()
        else:
            self.page.snack_bar = ft.SnackBar(ft.Text("Không thể quay lại"), bgcolor=ft.Colors.RED)
            self.page.snack_bar.open = True
            self.page.update()

    # === QUAN TRỌNG: Import launcher ở đây để tránh lỗi ===
    def _handle_login(self, user, pwd):
        # Kiểm tra tài khoản trống
        if not user:
            self.page.open(ft.SnackBar(ft.Text("⚠️ Tài khoản không được để trống!"), bgcolor=ft.Colors.RED_400))
            self.page.update()
            return
        
        # Kiểm tra mật khẩu trống
        if not pwd:
            self.page.open(ft.SnackBar(ft.Text("⚠️ Mật khẩu không được để trống!"), bgcolor=ft.Colors.RED_400))
            self.page.update()
            return
        
        # Đọc tài khoản từ file JSON
        try:
            accounts_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "accounts.json")
            with open(accounts_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                admin_accounts = data.get("admin_accounts", [])
            
            # Kiểm tra tài khoản
            account_found = None
            for acc in admin_accounts:
                if acc["username"] == user and acc["password"] == pwd:
                    account_found = acc
                    break
            
            if account_found:
                self.page.open(ft.SnackBar(ft.Text(f"Xin chào {account_found['name']}!"), bgcolor=ft.Colors.GREEN))
                self.page.update()
                time.sleep(0.3)
                
                # --- CHUYỂN SANG FILE LAUNCHER ---
                try:
                    # Xóa toàn bộ nội dung trang hiện tại trước khi chuyển
                    self.page.controls.clear()
                    self.page.update()
                    
                    from . import laucher_admin
                    laucher_admin.main(self.page, self.go_back_callback)
                except Exception as e:
                    self.page.open(ft.SnackBar(ft.Text(f"Lỗi mở Launcher: {e}"), bgcolor=ft.Colors.RED))
            else:
                self.page.open(ft.SnackBar(ft.Text("Sai tài khoản/mật khẩu!"), bgcolor=ft.Colors.RED))
        except Exception as e:
            self.page.open(ft.SnackBar(ft.Text(f"Lỗi đọc file tài khoản: {e}"), bgcolor=ft.Colors.RED))

def main(page: ft.Page, go_back_callback=None):
    AdminUI(page, go_back_callback)

if __name__ == "__main__":
    ft.app(target=main)