import flet as ft
import json
import os

# ===== DEFAULT TEST ACCOUNTS =====
DEFAULT_ACCOUNTS = {
    "user01": {
        "username": "user01",
        "password": "user123",
        "name": "Nguyễn Văn A",
        "driver_id": "NV001",
        "department": "Sales",
        "plan": "Free"
    },
    "user02": {
        "username": "user02",
        "password": "user123",
        "name": "Trần Thị B",
        "driver_id": "NV002",
        "department": "Marketing",
        "plan": "Pro"
    }
}

class UserLoginUI:
    def __init__(self, page: ft.Page, go_back_callback=None):
        self.page = page
        self.go_back_callback = go_back_callback
        self.page.title = "Đăng Nhập Nhân Viên"
        self.page.padding = 0
        self.page.theme_mode = ft.ThemeMode.LIGHT
        
        # Cấu hình ảnh
        self.bg_image_path = r"src/ui/data/image_user/backround.jpg"
        self.user_icon_path = r"src/ui/data/image_laucher/image_btnlogo_user.png"
        self.primary_color = "#2e7d6a"
        
        self.show_login_view()
    
    def show_login_view(self):
        self.page.clean()
        
        input_style = {
            "border_radius": 10,
            "bgcolor": ft.Colors.WHITE,
            "text_size": 14,
            "content_padding": 15,
            "border_color": self.primary_color
        }
        
        # Default account
        user_input = ft.TextField(label="Tài khoản", value="user01", prefix_icon=ft.Icons.PERSON, **input_style)
        pass_input = ft.TextField(label="Mật khẩu", value="user123", prefix_icon=ft.Icons.LOCK, password=True, can_reveal_password=True, **input_style)
        
        def handle_login(e):
            username = user_input.value.strip()
            password = pass_input.value.strip()
            
            if username not in DEFAULT_ACCOUNTS:
                user_input.error_text = "Tài khoản không tồn tại!"
                user_input.update()
                return
            
            account = DEFAULT_ACCOUNTS[username]
            if account["password"] != password:
                pass_input.error_text = "Mật khẩu sai!"
                pass_input.update()
                return
            
            # Login thành công - chuyển sang UserApp
            self.page.controls.clear()
            self.page.update()
            
            from .laucher_user import main as user_main
            user_main(self.page, go_back_callback=self.go_back_callback, user_account=account)
        
        login_card = ft.Container(
            width=400,
            padding=40,
            bgcolor=ft.Colors.WHITE,
            border_radius=20,
            shadow=ft.BoxShadow(blur_radius=20, color=ft.Colors.BLACK12),
            content=ft.Column([
                # Back button & Logo
                ft.Container(
                    content=ft.Stack([
                        ft.Container(
                            content=ft.Column([
                                ft.Image(
                                    src=self.user_icon_path,
                                    width=100,
                                    height=80,
                                    fit=ft.ImageFit.CONTAIN,
                                    error_content=ft.Icon(ft.Icons.PERSON, size=60, color=self.primary_color)
                                ),
                                ft.Text("ĐĂNG NHẬP", size=26, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_800),
                                ft.Text("Nhân viên", size=14, color=ft.Colors.GREY),
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
                
                # Inputs
                user_input,
                ft.Container(height=15),
                pass_input,
                ft.Container(height=5),
                
                # Help text
                ft.Text("Tài khoản mặc định: user01 / user02", size=10, color=ft.Colors.GREY_600, italic=True),
                ft.Text("Mật khẩu: user123", size=10, color=ft.Colors.GREY_600, italic=True),
                ft.Container(height=15),
                
                # Login button
                ft.ElevatedButton(
                    "Đăng nhập",
                    width=float("inf"),
                    height=50,
                    style=ft.ButtonStyle(
                        bgcolor=self.primary_color,
                        color=ft.Colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=10)
                    ),
                    on_click=handle_login
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )
        
        self._render_background(login_card)
    
    def _render_background(self, card):
        layout = ft.Stack([
            ft.Image(src=self.bg_image_path, width=float("inf"), height=float("inf"), fit=ft.ImageFit.COVER, 
                    error_content=ft.Container(bgcolor=ft.Colors.GREY_900)),
            ft.Container(expand=True, bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK)),
            ft.Container(expand=True, alignment=ft.alignment.center, content=card)
        ], expand=True)
        self.page.add(layout)
    
    def _go_back_to_main(self):
        if self.go_back_callback:
            self.page.controls.clear()
            self.page.update()
            self.go_back_callback()

def main(page: ft.Page, go_back_callback=None, user_account=None):
    """Entry point for User Login"""
    if user_account:
        # Already logged in, go straight to app
        from .laucher_user import main as user_main
        user_main(page, go_back_callback=go_back_callback, user_account=user_account)
    else:
        # Show login screen
        UserLoginUI(page, go_back_callback=go_back_callback)
