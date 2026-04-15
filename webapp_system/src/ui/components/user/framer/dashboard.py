import flet as ft

from bll.services.monitor_service import load_cache, load_config
from ui.theme import data_table, metric_card, status_badge


def _safe(v, fallback="--"):
    return str(v) if v is not None else fallback


def build_farmer_dashboard():
    cache = load_cache()
    cfg = load_config()

    total_cows = _safe(cache.get("total_cows"), "0")
    active_alerts = _safe(cache.get("active_alerts"), "0")
    cameras_online = _safe(cache.get("cameras_online"), "0")

    rows = []
    for alert in cache.get("recent_alerts", [])[-5:]:
        a_type = alert.get("type", "Cảnh báo")
        a_time = alert.get("time", "--")
        severity = "danger" if "Fighting" in a_type or "bat thuong" in a_type.lower() else "warning"
        rows.append([ft.Text(a_time), ft.Text(a_type), status_badge("Mới", severity), ft.Text("Luồng camera")])

    if not rows:
        rows = [[ft.Text("--"), ft.Text("Chưa có dữ liệu cảnh báo"), status_badge("Ngoại tuyến", "warning"), ft.Text(cfg.get("server_url", "--"))]]

    return ft.Column(
        expand=True,
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Text("Tổng quan trang trại", size=24, weight=ft.FontWeight.W_700),
            ft.Row(
                spacing=10,
                controls=[
                    ft.Container(expand=1, content=metric_card("Tổng bò", total_cows, ft.Icons.PETS)),
                    ft.Container(expand=1, content=metric_card("Cảnh báo hiện tại", active_alerts, ft.Icons.WARNING_AMBER)),
                    ft.Container(expand=1, content=metric_card("Camera trực tuyến", cameras_online, ft.Icons.VIDEOCAM)),
                ],
            ),
            ft.Text("Cảnh báo gần nhất từ hệ thống camera", size=15, weight=ft.FontWeight.W_600),
            data_table(["Thời gian", "Sự kiện", "Mức độ", "Nguồn"], rows),
        ],
    )
