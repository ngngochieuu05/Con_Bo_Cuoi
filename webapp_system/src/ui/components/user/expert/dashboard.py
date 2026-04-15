import flet as ft
from ui.theme import data_table, metric_card, status_badge


def build_expert_dashboard():
    rows = [
        [ft.Text("Case-2026-001"), status_badge("Mới", "warning"), ft.Text("Bất thường hành vi"), ft.Text("09:40")],
        [ft.Text("Case-2026-002"), status_badge("Đang xử lý", "secondary"), ft.Text("Dự báo sức khỏe"), ft.Text("09:31")],
        [ft.Text("Case-2026-003"), status_badge("Đã đóng", "primary"), ft.Text("Kết quả tư vấn"), ft.Text("09:10")],
    ]
    return ft.Column(
        expand=True,
        spacing=16,
        controls=[
            ft.Text("Bảng điều khiển chuyên gia", size=28, weight=ft.FontWeight.W_700),
            ft.Row(
                spacing=12,
                controls=[
                    ft.Container(expand=1, content=metric_card("Ca đang mở", "21", ft.Icons.MARK_EMAIL_UNREAD)),
                    ft.Container(expand=1, content=metric_card("Đánh giá hôm nay", "37", ft.Icons.FACT_CHECK)),
                    ft.Container(expand=1, content=metric_card("SLA đúng hạn", "96%", ft.Icons.AV_TIMER)),
                ],
            ),
            data_table(["Mã ca", "Trạng thái", "Loại", "Cập nhật"], rows),
        ],
    )
