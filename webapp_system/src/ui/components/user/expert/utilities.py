import flet as ft
from ui.theme import glass_container


def build_expert_utilities():
    return ft.Column(
        expand=True,
        spacing=14,
        controls=[
            ft.Text("Tiện ích", size=26, weight=ft.FontWeight.W_700),
            ft.Row(
                spacing=12,
                controls=[
                    ft.Container(
                        expand=1,
                        content=glass_container(
                            ft.Column(
                                spacing=8,
                                controls=[
                                    ft.Text("Tìm kiếm nhanh", weight=ft.FontWeight.W_600),
                                    ft.TextField(label="Tìm ca/người dùng/tập tin", prefix_icon=ft.Icons.SEARCH),
                                    ft.FilledButton("Tìm"),
                                ],
                            ),
                            padding=16,
                            radius=18,
                        ),
                    ),
                    ft.Container(
                        expand=1,
                        content=glass_container(
                            ft.Column(
                                spacing=8,
                                controls=[
                                    ft.Text("Xuất báo cáo", weight=ft.FontWeight.W_600),
                                    ft.Dropdown(
                                        label="Định dạng",
                                        options=[ft.dropdown.Option("pdf", "PDF"), ft.dropdown.Option("csv", "CSV")],
                                        value="pdf",
                                    ),
                                    ft.FilledButton("Tạo báo cáo"),
                                ],
                            ),
                            padding=16,
                            radius=18,
                        ),
                    ),
                ],
            ),
        ],
    )
