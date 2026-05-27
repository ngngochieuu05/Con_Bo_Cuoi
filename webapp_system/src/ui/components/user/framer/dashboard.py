import flet as ft

from bll.services.monitor_service import load_cache
from bll.services.system_overview_service import get_system_overview
from ui.theme import glass_container, metric_card, status_badge


def _metric_grid(items: list[ft.Control]) -> ft.Column:
    rows: list[ft.Control] = []
    for i in range(0, len(items), 2):
        pair = items[i:i + 2]
        rows.append(
            ft.Row(
                spacing=10,
                controls=[
                    ft.Container(expand=1, content=pair[0]),
                    ft.Container(expand=1, content=pair[1]) if len(pair) > 1 else ft.Container(expand=1),
                ],
            )
        )
    return ft.Column(spacing=10, controls=rows)


def build_farmer_dashboard(page: ft.Page | None = None):
    cache = load_cache()
    user_id = int((page.client_storage.get("user_id") or 0) if page else 0)
    overview = get_system_overview(user_id=user_id, role="farmer")

    total_cows = str(cache.get("total_cows", 0))
    active_alerts = str(overview.get("own_alerts_open", 0) or cache.get("active_alerts", 0))
    cameras_online = str(overview.get("own_cameras_online", 0))

    metric_wrap = _metric_grid([
        metric_card("Tổng bò", total_cows, ft.Icons.PETS),
        metric_card("Cảnh báo mở", active_alerts, ft.Icons.WARNING_AMBER),
        metric_card("Camera online", cameras_online, ft.Icons.VIDEOCAM),
    ])

    system_rows = _metric_grid([
        metric_card("Model online", f"{overview.get('models_online', 0)}/{overview.get('models_total', 0)}", ft.Icons.SMART_TOY),
        metric_card("Hệ thống camera", f"{overview.get('cameras_online', 0)}/{overview.get('cameras_total', 0)}", ft.Icons.CAMERA_OUTDOOR),
        metric_card("Cảnh báo hôm nay", str(overview.get('alerts_today', 0)), ft.Icons.NOTIFICATIONS_ACTIVE),
        metric_card("Hoạt động hôm nay", str(overview.get('activity_today', 0)), ft.Icons.TIMELINE),
    ])

    alert_cards: list[ft.Control] = []
    for alert in cache.get("recent_alerts", [])[-5:]:
        a_type = alert.get("type", "Cảnh báo")
        a_time = alert.get("time", "--")
        severity = "danger" if "Fighting" in a_type or "bất thường" in a_type.lower() else "warning"
        alert_cards.append(
            ft.Container(
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                border_radius=14,
                bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
                border=ft.border.all(1, ft.Colors.with_opacity(0.10, ft.Colors.WHITE)),
                content=ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        ft.Column(
                            expand=True,
                            spacing=3,
                            tight=True,
                            controls=[
                                ft.Text(a_type, size=12, weight=ft.FontWeight.W_600, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(a_time, size=10, color=ft.Colors.WHITE54),
                            ],
                        ),
                        status_badge("Mới", severity),
                    ],
                ),
            )
        )

    if not alert_cards:
        alert_cards.append(ft.Text("Chưa có dữ liệu cảnh báo.", size=12, color=ft.Colors.WHITE70))

    return ft.Column(
        expand=True,
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Text("Tổng quan trang trại", size=22, weight=ft.FontWeight.W_700),
            metric_wrap,
            glass_container(
                padding=14,
                radius=18,
                content=ft.Column(
                    spacing=10,
                    controls=[
                        ft.Text("Thông số hệ thống", size=15, weight=ft.FontWeight.W_600),
                        system_rows,
                        ft.Text(
                            f"Máy chủ {overview.get('server_url', '--')} | app {overview.get('app_mode', '--')}:{overview.get('app_port', '--')} | YOLO {overview.get('yolo_mode', '--')}",
                            size=11,
                            color=ft.Colors.WHITE60,
                        ),
                    ],
                ),
            ),
            glass_container(
                padding=14,
                radius=18,
                content=ft.Column(
                    spacing=10,
                    controls=[
                        ft.Text("Cảnh báo gần nhất từ hệ thống camera", size=15, weight=ft.FontWeight.W_600),
                        *alert_cards,
                    ],
                ),
            ),
        ],
    )
