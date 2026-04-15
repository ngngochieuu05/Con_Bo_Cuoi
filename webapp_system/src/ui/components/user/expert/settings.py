import flet as ft
from ui.theme import glass_container, button_style


def build_expert_settings(on_logout=None):
    return ft.Column(
        expand=True,
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Text("Cài đặt chuyên gia", size=22, weight=ft.FontWeight.W_700),
            glass_container(
                padding=16, radius=18,
                content=ft.Column(spacing=10, controls=[
                    ft.Text("Thông báo", size=14, weight=ft.FontWeight.W_600),
                    ft.Switch(label="Nhận thông báo ca mới", value=True),
                    ft.Switch(label="Nhận thông báo vi phạm SLA", value=True),
                    ft.Divider(color=ft.Colors.WHITE12),
                    ft.Text("Ưu tiên", size=14, weight=ft.FontWeight.W_600),
                    ft.Dropdown(
                        label="Mức ưu tiên mặc định",
                        border_radius=12,
                        options=[
                            ft.dropdown.Option("high", "Cao"),
                            ft.dropdown.Option("normal", "Trung bình"),
                            ft.dropdown.Option("low", "Thấp"),
                        ],
                        value="normal",
                    ),
                    ft.ElevatedButton("Lưu cài đặt", icon=ft.Icons.SAVE, style=button_style("primary")),
                ]),
            ),
            glass_container(
                padding=16, radius=18,
                content=ft.Column(spacing=10, controls=[
                    ft.Text("Phiên làm việc", size=14, weight=ft.FontWeight.W_600),
                    ft.Text("Kết thúc phiên và quay về đăng nhập.", size=11, color=ft.Colors.WHITE60),
                    ft.ElevatedButton(
                        "Đăng xuất",
                        icon=ft.Icons.LOGOUT,
                        style=button_style("danger"),
                        on_click=lambda e: on_logout() if on_logout else None,
                    ),
                ]),
            ),
        ],
    )
