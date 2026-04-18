import flet as ft
from ui.theme import (
    PRIMARY, SECONDARY, WARNING, DANGER,
    data_table, metric_card, status_badge, glass_container, fmt_dt, section_title,
    empty_state,
)
from bll.admin.dashboard_service import (
    get_dashboard_stats, get_recent_alerts, get_all_cameras_info, get_recent_activity,
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
    stats = get_dashboard_stats()

    # ── KPI row 1: users / models / open alerts ───────────────────────────
    kpi_row1 = ft.Row(
        spacing=8,
        controls=[
            ft.Container(expand=1, content=metric_card(
                "Tài khoản", str(stats["users"]),
                ft.Icons.GROUPS, SECONDARY,
            )),
            ft.Container(expand=1, content=metric_card(
                "Mô hình",
                f"{stats['models_online']}/{stats['models_total']}",
                ft.Icons.SMART_TOY, PRIMARY,
            )),
            ft.Container(expand=1, content=metric_card(
                "Chưa xử lý", str(stats["alerts_open"]),
                ft.Icons.WARNING_AMBER, WARNING,
            )),
        ],
    )

    # ── KPI row 2: cameras / alerts today / offline cams ─────────────────
    cam_total   = stats["cameras"]
    cam_online  = stats["cameras_online"]
    cam_offline = stats["cameras_offline"]
    kpi_row2 = ft.Row(
        spacing=8,
        controls=[
            ft.Container(expand=1, content=metric_card(
                "Camera",
                f"{cam_online}/{cam_total}",
                ft.Icons.VIDEOCAM, PRIMARY,
            )),
            ft.Container(expand=1, content=metric_card(
                "Hôm nay",
                str(stats["alerts_today"]),
                ft.Icons.NOTIFICATIONS_ACTIVE, WARNING,
            )),
            ft.Container(expand=1, content=metric_card(
                "Offline",
                str(cam_offline),
                ft.Icons.VIDEOCAM_OFF,
                DANGER if cam_offline else SECONDARY,
            )),
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
    alerts = sorted(
        get_recent_alerts(),
        key=lambda a: a.get("created_at", ""),
        reverse=True,
    )[:5]
    alert_rows = []
    for a in alerts:
        loai = _ALERT_LABEL.get(a.get("loai_canh_bao", ""), a.get("loai_canh_bao", "—"))
        st_label, st_kind = _ALERT_STATUS.get(a.get("trang_thai", ""), ("—", "warning"))
        alert_rows.append([
            ft.Text(f"#{a.get('id_canh_bao', '')}", size=12, color=ft.Colors.WHITE54),
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

    # ── recent activity feed ──────────────────────────────────────────────
    activities = get_recent_activity(10)

    def _activity_row(act: dict) -> ft.Control:
        label  = act.get("label", act.get("action", "—"))
        kind   = act.get("kind", "warning")
        detail = act.get("details", "")
        ts     = fmt_dt(act.get("timestamp", ""))
        uid    = act.get("user_id")
        uid_text = f"User #{uid}" if uid else "Hệ thống"
        return ft.Container(
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=10,
            bgcolor=ft.Colors.with_opacity(0.07, ft.Colors.WHITE),
            content=ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    status_badge(label, kind),
                    ft.Column(
                        expand=True, tight=True, spacing=1,
                        controls=[
                            ft.Text(detail or label, size=12,
                                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(uid_text, size=10, color=ft.Colors.WHITE38),
                        ],
                    ),
                    ft.Text(ts, size=10, color=ft.Colors.WHITE38),
                ],
            ),
        )

    activity_controls = (
        [_activity_row(a) for a in activities]
        if activities
        else [empty_state("Chưa có hoạt động nào")]
    )
    activity_section = ft.Column(spacing=8, controls=[
        section_title("HISTORY", "Hoạt động gần đây"),
        ft.Column(spacing=4, controls=activity_controls),
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
            kpi_row1,
            kpi_row2,
            glass_container(padding=14, radius=16, content=cam_section),
            glass_container(padding=14, radius=16, content=alert_section),
            glass_container(padding=14, radius=16, content=activity_section),
        ],
    )


