import flet as ft

from bll.admin.dashboard_service import (
    get_all_cameras_info,
    get_dashboard_stats,
    get_recent_activity,
    get_recent_alerts,
)
from bll.services.system_overview_service import get_system_overview
from ui.theme import DANGER, PRIMARY, SECONDARY, WARNING, empty_state, fmt_dt, glass_container, metric_card, section_title, status_badge


_CAM_STATUS = {
    "online": ("Online", "primary"),
    "warning": ("Cần xem", "warning"),
    "offline": ("Cảnh báo", "danger"),
}

_ALERT_LABEL = {
    "cow_fight": "Va chạm",
    "cow_lie": "Nằm lâu",
    "cow_sick": "Sức khỏe",
    "heat_high": "Nhiệt cao",
}

_ALERT_STATUS = {
    "CHUA_XU_LY": ("Chưa xử lý", "danger"),
    "DA_XU_LY": ("Đã xử lý", "primary"),
    "QUA_HAN": ("Quá hạn", "warning"),
}


def _metric_grid(items: list[ft.Control]) -> ft.Column:
    rows: list[ft.Control] = []
    for i in range(0, len(items), 2):
        pair = items[i:i + 2]
        rows.append(
            ft.Row(
                spacing=8,
                controls=[
                    ft.Container(expand=1, content=pair[0]),
                    ft.Container(expand=1, content=pair[1]) if len(pair) > 1 else ft.Container(expand=1),
                ],
            )
        )
    return ft.Column(spacing=8, controls=rows)


def build_admin_dashboard():
    stats = get_dashboard_stats()
    overview = get_system_overview(role="admin")

    kpi_row1 = _metric_grid([
        metric_card("Tài khoản", str(stats["users"]), ft.Icons.GROUPS, SECONDARY),
        metric_card("Mô hình", f"{stats['models_online']}/{stats['models_total']}", ft.Icons.SMART_TOY, PRIMARY),
        metric_card("Cảnh báo mở", str(stats["alerts_open"]), ft.Icons.WARNING_AMBER, WARNING),
    ])
    kpi_row2 = _metric_grid([
        metric_card("Camera", f"{stats['cameras_online']}/{stats['cameras']}", ft.Icons.VIDEOCAM, PRIMARY),
        metric_card("Hôm nay", str(stats["alerts_today"]), ft.Icons.NOTIFICATIONS_ACTIVE, WARNING),
        metric_card("Offline", str(stats["cameras_offline"]), ft.Icons.VIDEOCAM_OFF, DANGER if stats["cameras_offline"] else SECONDARY),
    ])

    system_section = ft.Column(
        spacing=8,
        controls=[
            section_title("SETTINGS_ETHERNET", "Thông số hệ thống"),
            _metric_grid([
                metric_card("Người dùng", str(overview.get("users_total", 0)), ft.Icons.GROUPS, SECONDARY),
                metric_card("Chuyên gia", str(overview.get("experts_total", 0)), ft.Icons.SUPPORT_AGENT, PRIMARY),
                metric_card("Nông hộ", str(overview.get("farmers_total", 0)), ft.Icons.AGRICULTURE, PRIMARY),
                metric_card("Hoạt động hôm nay", str(overview.get("activity_today", 0)), ft.Icons.TIMELINE, WARNING),
            ]),
            ft.Text(
                f"Server {overview.get('server_url', '--')} | app {overview.get('app_mode', '--')}:{overview.get('app_port', '--')} | YOLO {overview.get('yolo_mode', '--')}",
                size=11,
                color=ft.Colors.WHITE60,
            ),
        ],
    )

    cameras = get_all_cameras_info()
    camera_controls: list[ft.Control] = []
    for cam in cameras[:8]:
        st = cam.get("trang_thai", "offline")
        label, kind = _CAM_STATUS.get(st, ("--", "warning"))
        camera_controls.append(
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
                                ft.Text(cam.get("id_camera", "--"), size=12, weight=ft.FontWeight.W_600),
                                ft.Text(cam.get("khu_vuc_chuong", "--"), size=11, color=ft.Colors.WHITE70, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ],
                        ),
                        ft.Column(
                            tight=True,
                            spacing=3,
                            horizontal_alignment=ft.CrossAxisAlignment.END,
                            controls=[
                                status_badge(label, kind),
                                ft.Text(fmt_dt(cam.get("updated_at", "")), size=10, color=ft.Colors.WHITE54),
                            ],
                        ),
                    ],
                ),
            )
        )

    alerts = sorted(get_recent_alerts(), key=lambda a: a.get("created_at", ""), reverse=True)[:6]
    alert_controls: list[ft.Control] = []
    for alert in alerts:
        label = _ALERT_LABEL.get(alert.get("loai_canh_bao", ""), alert.get("loai_canh_bao", "--"))
        st_label, st_kind = _ALERT_STATUS.get(alert.get("trang_thai", ""), ("--", "warning"))
        alert_controls.append(
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
                                ft.Text(label, size=12, weight=ft.FontWeight.W_600),
                                ft.Text(f"#{alert.get('id_canh_bao', '')} · {fmt_dt(alert.get('created_at', ''))}", size=10, color=ft.Colors.WHITE54),
                            ],
                        ),
                        status_badge(st_label, st_kind),
                    ],
                ),
            )
        )

    activities = get_recent_activity(8)
    activity_controls = []
    for act in activities:
        label = act.get("label", act.get("action", "--"))
        kind = act.get("kind", "warning")
        activity_controls.append(
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
                                ft.Text(act.get("details", "") or label, size=12, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(fmt_dt(act.get("timestamp", "")), size=10, color=ft.Colors.WHITE54),
                            ],
                        ),
                        status_badge(label, kind),
                    ],
                ),
            )
        )

    return ft.Column(
        expand=True,
        spacing=16,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(
                        tight=True,
                        spacing=1,
                        controls=[
                            ft.Text("Bảng điều khiển", size=22, weight=ft.FontWeight.W_700),
                            ft.Text("Tổng quan hệ thống", size=11, color=ft.Colors.WHITE54),
                        ],
                    ),
                    ft.Icon(ft.Icons.DASHBOARD, color=ft.Colors.WHITE24, size=28),
                ],
            ),
            kpi_row1,
            kpi_row2,
            glass_container(padding=14, radius=16, content=system_section),
            glass_container(
                padding=14,
                radius=16,
                content=ft.Column(spacing=8, controls=[section_title("VIDEOCAM", "Trạng thái camera"), *(camera_controls or [empty_state("Chưa có camera nào")])]),
            ),
            glass_container(
                padding=14,
                radius=16,
                content=ft.Column(spacing=8, controls=[section_title("NOTIFICATIONS_ACTIVE", "Cảnh báo gần đây"), *(alert_controls or [empty_state("Không có cảnh báo")])]),
            ),
            glass_container(
                padding=14,
                radius=16,
                content=ft.Column(spacing=8, controls=[section_title("HISTORY", "Hoạt động gần đây"), *(activity_controls or [empty_state("Chưa có hoạt động nào")])]),
            ),
        ],
    )
