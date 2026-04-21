import flet as ft

from bll.admin.dashboard_service import get_all_cameras_info, get_dashboard_stats, get_recent_alerts
from ui.theme import DANGER, PRIMARY, SECONDARY, WARNING, glass_container, page_header, status_badge

_CAM_STATUS = {
    "online": ("On", "primary"),
    "warning": ("Can xem", "warning"),
    "offline": ("Offline", "danger"),
}
_ALERT_LABEL = {
    "cow_fight": "Va cham",
    "cow_lie": "Nam lau",
    "cow_sick": "Suc khoe",
    "heat_high": "Nhiet cao",
}
_ALERT_STATUS = {
    "CHUA_XU_LY": ("Mo", "danger"),
    "DA_XU_LY": ("Xong", "primary"),
    "QUA_HAN": ("Qua han", "warning"),
}


def _metric_tile(title: str, value: str, icon, accent: str) -> ft.Control:
    return ft.Container(
        expand=1,
        padding=14,
        border_radius=18,
        bgcolor=ft.Colors.with_opacity(0.20, accent),
        border=ft.border.all(1, ft.Colors.with_opacity(0.30, accent)),
        content=ft.Column(
            tight=True,
            spacing=8,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(title, size=11, color=ft.Colors.WHITE70),
                        ft.Icon(icon, size=18, color=accent),
                    ],
                ),
                ft.Text(value, size=26, weight=ft.FontWeight.W_700),
            ],
        ),
    )


def _snapshot_card(title: str, rows: list[ft.Control]) -> ft.Control:
    return glass_container(
        padding=14,
        radius=18,
        content=ft.Column(
            spacing=8,
            tight=True,
            controls=[ft.Text(title, size=14, weight=ft.FontWeight.W_700), *rows],
        ),
    )


def _shortcut_chip(label: str, icon, accent: str) -> ft.Control:
    return ft.Container(
        expand=1,
        padding=ft.padding.symmetric(horizontal=10, vertical=10),
        border_radius=14,
        bgcolor=ft.Colors.with_opacity(0.14, accent),
        border=ft.border.all(1, ft.Colors.with_opacity(0.20, accent)),
        content=ft.Row(
            spacing=6,
            controls=[
                ft.Icon(icon, size=16, color=accent),
                ft.Text(label, size=11, weight=ft.FontWeight.W_700),
            ],
        ),
    )


def _alert_row(alert: dict) -> ft.Control:
    label, kind = _ALERT_STATUS.get(alert.get("trang_thai"), ("Mo", "warning"))
    return ft.Container(
        padding=ft.padding.symmetric(vertical=8),
        border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE))),
        content=ft.Row(
            spacing=8,
            controls=[
                ft.Icon(ft.Icons.WARNING_AMBER, size=16, color=DANGER),
                ft.Column(
                    expand=True,
                    tight=True,
                    spacing=2,
                    controls=[
                        ft.Text(_ALERT_LABEL.get(alert.get("loai_canh_bao"), "Canh bao"), size=12, weight=ft.FontWeight.W_700),
                        ft.Text(alert.get("created_at", "")[:16].replace("T", " "), size=10, color=ft.Colors.WHITE54),
                    ],
                ),
                status_badge(label, kind),
            ],
        ),
    )


def _camera_row(camera: dict) -> ft.Control:
    label, kind = _CAM_STATUS.get(camera.get("trang_thai"), ("Mo", "warning"))
    return ft.Container(
        padding=ft.padding.symmetric(vertical=8),
        border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE))),
        content=ft.Row(
            spacing=8,
            controls=[
                ft.Icon(ft.Icons.VIDEOCAM, size=16, color=PRIMARY),
                ft.Column(
                    expand=True,
                    tight=True,
                    spacing=2,
                    controls=[
                        ft.Text(str(camera.get("id_camera", "—")), size=12, weight=ft.FontWeight.W_700),
                        ft.Text(camera.get("khu_vuc_chuong", "—"), size=10, color=ft.Colors.WHITE54),
                    ],
                ),
                status_badge(label, kind),
            ],
        ),
    )


def build_admin_dashboard():
    stats = get_dashboard_stats()
    alerts = sorted(get_recent_alerts(), key=lambda item: item.get("created_at", ""), reverse=True)
    cameras = get_all_cameras_info()
    attention_cameras = [camera for camera in cameras if camera.get("trang_thai") != "online"][:5]

    return ft.Column(
        expand=True,
        spacing=14,
        controls=[
            page_header(
                "Tong quan admin",
                "Snapshot triage cho mobile. Khong dua bang van hanh day dac len dashboard.",
                icon_name="DASHBOARD",
            ),
            ft.Row(
                spacing=10,
                controls=[
                    _metric_tile("Tai khoan", str(stats["users"]), ft.Icons.GROUPS, SECONDARY),
                    _metric_tile("Model on", str(stats["models_online"]), ft.Icons.SMART_TOY, PRIMARY),
                    _metric_tile("Alert mo", str(stats["alerts_open"]), ft.Icons.WARNING_AMBER, WARNING),
                ],
            ),
            ft.Row(
                spacing=10,
                controls=[
                    _snapshot_card("Alert gan day", [_alert_row(alert) for alert in alerts[:5]] or [ft.Text("Khong co alert.", size=11, color=ft.Colors.WHITE54)]),
                    _snapshot_card("Camera can xem", [_camera_row(camera) for camera in attention_cameras] or [ft.Text("Tat ca camera dang on.", size=11, color=ft.Colors.WHITE54)]),
                ],
            ),
            _snapshot_card(
                "Tac vu nhanh",
                [
                    ft.Row(
                        spacing=10,
                        controls=[
                            _shortcut_chip("Tai khoan", ft.Icons.GROUPS, SECONDARY),
                            _shortcut_chip("Model", ft.Icons.SMART_TOY, PRIMARY),
                            _shortcut_chip("Train", ft.Icons.MODEL_TRAINING, WARNING),
                        ],
                    )
                ],
            ),
        ],
    )
