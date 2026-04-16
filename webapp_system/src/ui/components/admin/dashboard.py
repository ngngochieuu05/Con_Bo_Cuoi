import flet as ft
from ui.theme import (
    PRIMARY, SECONDARY, WARNING, DANGER,
    data_table, metric_card, status_badge, glass_container, fmt_dt, section_title,
    empty_state,
)
from bll.admin.dashboard_service import (
    get_dashboard_stats, get_recent_alerts, get_all_cameras_info,
)


_CAM_STATUS = {
    "online":  ("Online",   "primary"),
    "warning": ("Cần xem",  "warning"),
    "offline": ("Cảnh báo", "danger"),
}

_ALERT_LABEL = {
    "cow_fight":  "Va chạm",
    "cow_lie":    "Nằm lâu",
    "cow_sick":   "Sức khỏe",
    "heat_high":  "Nhiệt cao",
}

_ALERT_STATUS = {
    "CHUA_XU_LY": ("Chưa xử lý", "danger"),
    "DA_XU_LY":   ("Đã xử lý",   "primary"),
    "QUA_HAN":    ("Quá hạn",    "warning"),
}


def build_admin_dashboard():
    # ── metrics ───────────────────────────────────────────────────────────
    stats         = get_dashboard_stats()
    total_users   = stats["users"]
    online_models = stats["models_online"]
    open_alerts   = stats["alerts_open"]

    metric_row = ft.Row(
        spacing=8,
        controls=[
            ft.Container(expand=1, content=metric_card("Tài khoản", str(total_users), ft.Icons.GROUPS, SECONDARY)),
            ft.Container(expand=1, content=metric_card("Mô hình", str(online_models), ft.Icons.SMART_TOY, PRIMARY)),
            ft.Container(expand=1, content=metric_card("Cảnh báo", str(open_alerts), ft.Icons.WARNING_AMBER, WARNING)),
        ],
    )

    # ── camera table ──────────────────────────────────────────────────────
    cameras = get_all_cameras_info()
    cam_rows = []
    for cam in cameras:
        st = cam.get("trang_thai", "offline")
        label, kind = _CAM_STATUS.get(st, ("—", "warning"))
        cam_rows.append([
            ft.Text(cam.get("id_camera", "—"), size=12, weight=ft.FontWeight.W_600),
            ft.Text(cam.get("khu_vuc_chuong", "—"), size=12),
            status_badge(label, kind),
            ft.Text(fmt_dt(cam.get("updated_at", "")), size=11, color=ft.Colors.WHITE60),
        ])

    cam_section = ft.Column(spacing=8, controls=[
        section_title("VIDEOCAM", "Trạng thái camera"),
        data_table(
            ["Camera", "Khu vực", "Trạng thái", "Cập nhật"],
            cam_rows,
            col_flex=[2, 2, 2, 3],
        ) if cam_rows else empty_state("Chưa có camera nào"),
    ])

    # ── recent alerts ─────────────────────────────────────────────────────
    alerts = sorted(get_recent_alerts(), key=lambda a: a.get("created_at", ""), reverse=True)[:5]
    alert_rows = []
    for a in alerts:
        loai = _ALERT_LABEL.get(a.get("loai_canh_bao", ""), a.get("loai_canh_bao", "—"))
        st_label, st_kind = _ALERT_STATUS.get(a.get("trang_thai", ""), ("—", "warning"))
        alert_rows.append([
            ft.Text(f"#{a.get('id_canh_bao','')}", size=12, color=ft.Colors.WHITE54),
            ft.Text(loai, size=12),
            status_badge(st_label, st_kind),
            ft.Text(fmt_dt(a.get("created_at", "")), size=11, color=ft.Colors.WHITE60),
        ])

    alert_section = ft.Column(spacing=8, controls=[
        section_title("NOTIFICATIONS_ACTIVE", "Cảnh báo gần đây"),
        data_table(
            ["ID", "Loại", "Trạng thái", "Thời gian"],
            alert_rows,
            col_flex=[1, 2, 2, 3],
        ) if alert_rows else empty_state("Không có cảnh báo"),
    ])

    return ft.Column(
        expand=True,
        spacing=16,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(tight=True, spacing=1, controls=[
                        ft.Text("Bảng điều khiển", size=22, weight=ft.FontWeight.W_700),
                        ft.Text("Tổng quan hệ thống", size=11, color=ft.Colors.WHITE54),
                    ]),
                    ft.Icon(ft.Icons.DASHBOARD, color=ft.Colors.WHITE24, size=28),
                ],
            ),
            metric_row,
            glass_container(padding=14, radius=16, content=cam_section),
            glass_container(padding=14, radius=16, content=alert_section),
        ],
    )


