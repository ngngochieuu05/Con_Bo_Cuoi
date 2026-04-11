import flet as ft
from ui.theme import data_table, status_badge


def build_raw_data_review():
    rows = [
        [ft.Text("cam01_1045.mp4"), ft.Text("Video"), status_badge("Đã xử lý", "primary"), ft.Text("128MB")],
        [ft.Text("sensor_zoneb.csv"), ft.Text("CSV"), status_badge("Cần duyệt", "warning"), ft.Text("12MB")],
        [ft.Text("alert_431.json"), ft.Text("JSON"), status_badge("Lỗi định dạng", "danger"), ft.Text("2MB")],
    ]
    return ft.Column(
        expand=True,
        spacing=14,
        controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text("Duyệt dữ liệu thô", size=26, weight=ft.FontWeight.W_700),
                    ft.Row(controls=[ft.OutlinedButton("Tải dữ liệu"), ft.FilledButton("Xác nhận lô dữ liệu")]),
                ],
            ),
            data_table(["Tập tin", "Loại", "Trạng thái", "Kích thước"], rows),
        ],
    )
