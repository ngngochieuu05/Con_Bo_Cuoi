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


def _metric_tile(title: str, value: str, detail: str, icon, accent: str) -> ft.Control:
    return ft.Container(
        expand=1,
        padding=16,
        border_radius=18,
        bgcolor=ft.Colors.with_opacity(0.12, accent),
        border=ft.border.all(1, ft.Colors.with_opacity(0.22, accent)),
        content=ft.Column(
            tight=True,
            spacing=10,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(title, size=11, color="#C2D0D8", weight=ft.FontWeight.W_600),
                        ft.Container(
                            width=30,
                            height=30,
                            border_radius=15,
                            bgcolor=ft.Colors.with_opacity(0.18, accent),
                            alignment=ft.alignment.center,
                            content=ft.Icon(icon, size=16, color=accent),
                        ),
                    ],
                ),
                ft.Text(value, size=28, weight=ft.FontWeight.W_700),
                ft.Text(detail, size=10, color=ft.Colors.WHITE54),
            ],
        ),
    )


def _section_card(title: str, subtitle: str, rows: list[ft.Control]) -> ft.Control:
    return glass_container(
        padding=14,
        radius=18,
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Column(
                    tight=True,
                    spacing=2,
                    controls=[
                        ft.Text(title, size=15, weight=ft.FontWeight.W_700),
                        ft.Text(subtitle, size=10, color=ft.Colors.WHITE54),
                    ],
                ),
                *rows,
            ],
        ),
    )


def _alert_row(alert: dict) -> ft.Control:
    label, kind = _ALERT_STATUS.get(alert.get("trang_thai"), ("Mo", "warning"))
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=10, vertical=10),
        border_radius=14,
        bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
        border=ft.border.all(1, ft.Colors.with_opacity(0.06, ft.Colors.WHITE)),
        content=ft.Row(
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    width=30,
                    height=30,
                    border_radius=15,
                    bgcolor=ft.Colors.with_opacity(0.16, DANGER),
                    alignment=ft.alignment.center,
                    content=ft.Icon(ft.Icons.WARNING_AMBER, size=16, color=DANGER),
                ),
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
        padding=ft.padding.symmetric(horizontal=10, vertical=10),
        border_radius=14,
        bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
        border=ft.border.all(1, ft.Colors.with_opacity(0.06, ft.Colors.WHITE)),
        content=ft.Row(
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    width=30,
                    height=30,
                    border_radius=15,
                    bgcolor=ft.Colors.with_opacity(0.16, PRIMARY),
                    alignment=ft.alignment.center,
                    content=ft.Icon(ft.Icons.VIDEOCAM, size=16, color=PRIMARY),
                ),
                ft.Column(
                    expand=True,
                    tight=True,
                    spacing=2,
                    controls=[
                        ft.Text(str(camera.get("id_camera", "-")), size=12, weight=ft.FontWeight.W_700),
                        ft.Text(camera.get("khu_vuc_chuong", "-"), size=10, color=ft.Colors.WHITE54),
                    ],
                ),
                status_badge(label, kind),
            ],
        ),
    )


def _action_tile(label: str, note: str, icon, accent: str) -> ft.Control:
    return ft.Container(
        expand=1,
        padding=14,
        border_radius=16,
        bgcolor=ft.Colors.with_opacity(0.10, accent),
        border=ft.border.all(1, ft.Colors.with_opacity(0.18, accent)),
        content=ft.Column(
            tight=True,
            spacing=8,
            controls=[
                ft.Row(
                    spacing=8,
                    controls=[
                        ft.Icon(icon, size=16, color=accent),
                        ft.Text(label, size=12, weight=ft.FontWeight.W_700),
                    ],
                ),
                ft.Text(note, size=10, color=ft.Colors.WHITE60),
            ],
        ),
    )


def build_admin_dashboard():
    stats = get_dashboard_stats()
    alerts = sorted(get_recent_alerts(), key=lambda item: item.get("created_at", ""), reverse=True)
    cameras = get_all_cameras_info()
    attention_cameras = [camera for camera in cameras if camera.get("trang_thai") != "online"][:4]
    offline_count = sum(1 for camera in cameras if camera.get("trang_thai") == "offline")
    warning_count = sum(1 for camera in cameras if camera.get("trang_thai") == "warning")
    open_alert_count = sum(1 for alert in alerts if alert.get("trang_thai") == "CHUA_XU_LY")
    overdue_alert_count = sum(1 for alert in alerts if alert.get("trang_thai") == "QUA_HAN")

    if overdue_alert_count:
        hero_tone = DANGER
        hero_title = "Can day xu ly gap"
        hero_note = f"{overdue_alert_count} alert qua han dang can admin chup quyet dinh."
    elif offline_count or open_alert_count:
        hero_tone = WARNING
        hero_title = "Ca truc dang co viec ton"
        hero_note = (
            f"{offline_count} camera offline, {open_alert_count} alert mo. "
            "Nen uu tien check camera va phan cong xu ly."
        )
    else:
        hero_tone = PRIMARY
        hero_title = "He thong dang on dinh"
        hero_note = "Khong co muc nao vuot nguong. Dashboard nay chi giu nhung diem can quet nhanh."

    return ft.Column(
        expand=True,
        spacing=14,
        controls=[
            page_header(
                "Tong quan admin",
                "Bo cuc dieu hanh mobile-first: uu tien viec can quyet dinh thay vi nhieu card trang tri.",
                icon_name="DASHBOARD",
            ),
            glass_container(
                padding=16,
                radius=20,
                content=ft.Column(
                    spacing=12,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.START,
                            controls=[
                                ft.Column(
                                    expand=True,
                                    tight=True,
                                    spacing=4,
                                    controls=[
                                        ft.Text(hero_title, size=18, weight=ft.FontWeight.W_700),
                                        ft.Text(hero_note, size=11, color=ft.Colors.WHITE70),
                                    ],
                                ),
                                status_badge("Overdue" if overdue_alert_count else "Stable", "danger" if overdue_alert_count else "primary"),
                            ],
                        ),
                        ft.Row(
                            spacing=8,
                            wrap=True,
                            controls=[
                                status_badge(f"{offline_count} camera offline", "danger" if offline_count else "neutral"),
                                status_badge(f"{warning_count} camera can xem", "warning" if warning_count else "neutral"),
                                status_badge(f"{open_alert_count} alert mo", "warning" if open_alert_count else "neutral"),
                            ],
                        ),
                    ],
                ),
            ),
            ft.Row(
                spacing=10,
                wrap=True,
                run_spacing=10,
                controls=[
                    _metric_tile("Tai khoan", str(stats["users"]), "Tong nhan su co quyen trong he thong", ft.Icons.GROUPS, SECONDARY),
                    _metric_tile("Model production", str(stats["models_online"]), "So model dang online cho van hanh that", ft.Icons.SMART_TOY, PRIMARY),
                    _metric_tile("Alert mo", str(stats["alerts_open"]), "Bao gom ca muc can phan cong va can xac nhan", ft.Icons.WARNING_AMBER, WARNING),
                ],
            ),
            _section_card(
                "Hang doi uu tien",
                "Nhung muc can admin quet truoc khi di sang modules chi tiet.",
                [
                    _alert_row(alert) for alert in alerts[:4]
                ] or [
                    ft.Text("Khong co alert dang mo.", size=11, color=ft.Colors.WHITE54)
                ],
            ),
            _section_card(
                "Camera can xem",
                "Chi hien thi camera warning/offline de tranh lam loang dashboard.",
                [
                    _camera_row(camera) for camera in attention_cameras
                ] or [
                    ft.Text("Tat ca camera dang on.", size=11, color=ft.Colors.WHITE54)
                ],
            ),
            _section_card(
                "Tac vu nhanh",
                "Lo trinh thao tac de dieu huong qua cac module con.",
                [
                    ft.Row(
                        spacing=10,
                        wrap=True,
                        run_spacing=10,
                        controls=[
                            _action_tile("Tai khoan", "Soat role, reset mat khau, xoa tai khoan treo.", ft.Icons.GROUPS, SECONDARY),
                            _action_tile("Model registry", "Xac nhan candidate, apply production, disable model loi.", ft.Icons.SMART_TOY, PRIMARY),
                            _action_tile("Train queue", "Theo doi job train, retry va soat pipeline dataset.", ft.Icons.MODEL_TRAINING, WARNING),
                        ],
                    )
                ],
            ),
        ],
    )
