import flet as ft
from ui.theme import glass_container, status_badge


def _consulting_item(title: str, detail: str, tag: str, kind: str):
    return glass_container(
        padding=16,
        radius=18,
        content=ft.Column(
            spacing=8,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[ft.Text(title, weight=ft.FontWeight.W_700), status_badge(tag, kind)],
                ),
                ft.Text(detail, size=13, color=ft.Colors.WHITE70),
                ft.Row(
                    controls=[
                        ft.TextButton("Xem chi tiết", icon=ft.Icons.VISIBILITY),
                        ft.OutlinedButton("Chấp nhận"),
                        ft.FilledButton("Yêu cầu bổ sung"),
                    ]
                ),
            ],
        ),
    )


def build_consulting_review():
    return ft.Column(
        expand=True,
        spacing=12,
        controls=[
            ft.Text("Duyệt tư vấn", size=26, weight=ft.FontWeight.W_700),
            _consulting_item(
                "Khuyến nghị khẩu phần - Khu A",
                "Hệ thống đề xuất điều chỉnh 7% lượng ăn trong 5 ngày tới.",
                "Độ ưu tiên cao",
                "danger",
            ),
            _consulting_item(
                "Lịch tiêm phòng bổ sung",
                "Cần xác nhận thông tin số lượng cho đợt tiêm phòng mới.",
                "Chờ phê duyệt",
                "warning",
            ),
        ],
    )
