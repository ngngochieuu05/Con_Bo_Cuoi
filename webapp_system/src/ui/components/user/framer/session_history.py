import flet as ft

from bll.services.monitor_service import load_cache
from ui.theme import data_table, status_badge


def build_session_history():
    cache = load_cache()
    rows = []
    for i, alert in enumerate(reversed(cache.get("recent_alerts", [])[-10:]), start=1):
        a_type = alert.get("type", "Cảnh báo")
        a_time = alert.get("time", "--")
        severity = "danger" if "Fighting" in a_type or "bat thuong" in a_type.lower() else "warning"
        rows.append([
            ft.Text(f"S-{i:03d}"),
            ft.Text(a_time),
            ft.Text(a_type),
            status_badge("Cảnh báo" if severity == "danger" else "Thông tin", severity),
        ])

    if not rows:
        rows = [[ft.Text("S-000"), ft.Text("--"), ft.Text("Chưa có lịch sử phiên"), status_badge("Ngoại tuyến", "warning")]]

    return ft.Column(
        expand=True,
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Text("Lịch sử phiên", size=24, weight=ft.FontWeight.W_700),
            data_table(["Phiên", "Thời gian", "Nội dung", "Trạng thái"], rows),
        ],
    )
