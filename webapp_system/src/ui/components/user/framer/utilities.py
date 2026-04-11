import flet as ft

from bll.services.monitor_service import load_cache, load_config
from ui.theme import glass_container, status_badge


SUGGESTIONS = {
    "bất thường": "Có cảnh báo hành vi bất thường. Bạn nên kiểm tra ngay luồng trực tiếp và ảnh chụp.",
    "bat thuong": "Có cảnh báo hành vi bất thường. Bạn nên kiểm tra ngay luồng trực tiếp và ảnh chụp.",
    "camera": "Nếu camera mất kết nối, vui lòng kiểm tra Wi-Fi LAN, nguồn điện và địa chỉ máy chủ trong Cài đặt.",
    "mô hình": "Nên dùng mô hình đã được quản trị gán cho tài khoản để đảm bảo độ chính xác phù hợp trang trại.",
    "mo hinh": "Nên dùng mô hình đã được quản trị gán cho tài khoản để đảm bảo độ chính xác phù hợp trang trại.",
}


def build_farmer_utilities():
    cache = load_cache()
    cfg = load_config()

    input_box = ft.TextField(label="Hỏi nhanh hệ thống", hint_text="VD: camera, bất thường, mô hình")
    answer = ft.Text("", size=12, color=ft.Colors.WHITE70)

    def ask(e):
        text = (input_box.value or "").lower()
        answer.value = "Chưa có gợi ý cho từ khóa này. Thử: camera / bất thường / mô hình"
        for key, value in SUGGESTIONS.items():
            if key in text:
                answer.value = value
                break
        answer.update()

    alert_items = []
    for alert in cache.get("recent_alerts", [])[-5:]:
        a_type = alert.get("type", "Cảnh báo")
        kind = "danger" if "Fighting" in a_type or "bat thuong" in a_type.lower() else "warning"
        alert_items.append(
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(f"{alert.get('time', '--')} - {a_type}", size=12, expand=True),
                    status_badge("Cảnh báo", kind),
                ],
            )
        )

    if not alert_items:
        alert_items = [ft.Text("Chưa có cảnh báo gần đây.", size=12, color=ft.Colors.WHITE70)]

    return ft.Column(
        expand=True,
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Text("Tiện ích", size=24, weight=ft.FontWeight.W_700),
            glass_container(
                padding=16,
                radius=18,
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Text("Thông tin hệ thống", weight=ft.FontWeight.W_600),
                        ft.Text(f"Máy chủ: {cfg.get('server_url', '--')}", size=12, color=ft.Colors.WHITE70),
                        ft.Text(f"Chỉ số camera: {cfg.get('camera_index', '--')}", size=12, color=ft.Colors.WHITE70),
                    ],
                ),
            ),
            glass_container(
                padding=16,
                radius=18,
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Text("Trợ lý nhanh", weight=ft.FontWeight.W_600),
                        input_box,
                        ft.ElevatedButton("Trả lời", icon=ft.Icons.SMART_TOY, on_click=ask),
                        answer,
                    ],
                ),
            ),
            glass_container(
                padding=16,
                radius=18,
                content=ft.Column(
                    spacing=8,
                    controls=[ft.Text("Cảnh báo gần đây", weight=ft.FontWeight.W_600), *alert_items],
                ),
            ),
        ],
    )
