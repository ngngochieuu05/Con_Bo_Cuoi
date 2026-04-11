from __future__ import annotations
import flet as ft
from collections import Counter
from ui.theme import (
    PRIMARY, WARNING, DANGER, SECONDARY,
    glass_container, metric_card, status_badge,
    data_table, section_title, empty_state, fmt_dt,
)
from dal.canh_bao_repo import get_all as get_all_alerts, resolve_alert
from dal.camera_chuong_repo import get_all_cameras

_ALERT_LABEL = {
    "cow_fight": "Va chạm",
    "cow_lie":   "Nằm lâu",
    "cow_sick":  "Sức khỏe",
    "heat_high": "Nhiệt cao",
}
_STATUS_MAP = {
    "CHUA_XU_LY": ("Chưa xử lý", "danger"),
    "DA_XU_LY":   ("Đã xử lý",   "primary"),
    "QUA_HAN":    ("Quá hạn",    "warning"),
}
_CAM_STATUS = {
    "online":  ("Online",   "primary"),
    "warning": ("Cần xem",  "warning"),
    "offline": ("Ngoại tuyến", "danger"),
}


def build_oa_management():
    list_ref = ft.Ref[ft.Column]()
    msg      = ft.Text("", size=12)

    def refresh():
        alerts  = sorted(get_all_alerts(), key=lambda a: a.get("created_at", ""), reverse=True)
        cameras = get_all_cameras()

        # --- Metrics from real data ---
        total   = len(alerts)
        open_c  = sum(1 for a in alerts if a.get("trang_thai") == "CHUA_XU_LY")
        done_c  = sum(1 for a in alerts if a.get("trang_thai") == "DA_XU_LY")
        cam_ok  = sum(1 for c in cameras if c.get("trang_thai") == "online")

        metrics = ft.Row(spacing=8, controls=[
            ft.Container(expand=1, content=metric_card("Tổng cảnh báo", str(total),  ft.Icons.NOTIFICATIONS, SECONDARY)),
            ft.Container(expand=1, content=metric_card("Chưa xử lý",   str(open_c), ft.Icons.ERROR_OUTLINE,  DANGER)),
            ft.Container(expand=1, content=metric_card("Đã xử lý",     str(done_c), ft.Icons.CHECK_CIRCLE,   PRIMARY)),
        ])

        # --- Alert type breakdown ---
        type_counts = Counter(a.get("loai_canh_bao", "?") for a in alerts)
        breakdown_rows = [
            [
                ft.Text(_ALERT_LABEL.get(t, t), size=12),
                ft.Text(str(n), size=13, weight=ft.FontWeight.W_700),
                ft.Container(
                    expand=True,
                    height=6,
                    border_radius=3,
                    bgcolor=ft.Colors.with_opacity(0.15, PRIMARY),
                    content=ft.Container(
                        width=None,
                        height=6,
                        border_radius=3,
                        bgcolor=PRIMARY,
                        expand=(n / max(type_counts.values(), default=1)),
                    ),
                ),
            ]
            for t, n in sorted(type_counts.items(), key=lambda x: -x[1])
        ]

        breakdown_section = ft.Column(spacing=8, controls=[
            section_title("PIE_CHART", "Phân loại cảnh báo"),
            data_table(["Loại", "Số lượng", "Tỉ lệ"], breakdown_rows, col_flex=[3, 1, 4])
            if breakdown_rows else empty_state("Chưa có dữ liệu"),
        ])

        # --- Camera health ---
        cam_rows = []
        for c in cameras:
            st = c.get("trang_thai", "offline")
            lbl, kind = _CAM_STATUS.get(st, ("—", "warning"))
            cam_rows.append([
                ft.Text(c.get("id_camera", "—"), size=12, weight=ft.FontWeight.W_600),
                ft.Text(c.get("khu_vuc_chuong", "—"), size=12),
                status_badge(lbl, kind),
            ])

        cam_section = ft.Column(spacing=8, controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    section_title("VIDEOCAM", f"Camera ({cam_ok}/{len(cameras)} online)"),
                ],
            ),
            data_table(["ID", "Khu vực", "Trạng thái"], cam_rows, col_flex=[2, 2, 2])
            if cam_rows else empty_state("Chưa có camera"),
        ])

        # --- Recent alerts list ---
        def _on_resolve(e, aid):
            resolve_alert(aid)
            msg.value = f"Đã xử lý cảnh báo #{aid}."
            msg.color = ft.Colors.GREEN_300
            msg.update()
            refresh()

        alert_rows = []
        for a in alerts[:10]:
            loai    = _ALERT_LABEL.get(a.get("loai_canh_bao", ""), a.get("loai_canh_bao", "—"))
            sl, sk  = _STATUS_MAP.get(a.get("trang_thai", ""), ("—", "warning"))
            aid     = a.get("id_canh_bao")
            resolve_btn = ft.Container()
            if a.get("trang_thai") == "CHUA_XU_LY":
                resolve_btn = ft.IconButton(
                    ft.Icons.CHECK_CIRCLE_OUTLINE,
                    icon_color=ft.Colors.GREEN_300,
                    icon_size=16,
                    tooltip="Đánh dấu đã xử lý",
                    on_click=lambda e, i=aid: _on_resolve(e, i),
                )
            alert_rows.append([
                ft.Text(f"#{aid}", size=11, color=ft.Colors.WHITE54),
                ft.Text(loai, size=12),
                status_badge(sl, sk),
                ft.Text(fmt_dt(a.get("created_at", "")), size=11, color=ft.Colors.WHITE60),
                resolve_btn,
            ])

        alert_list_section = ft.Column(spacing=8, controls=[
            section_title("LIST_ALT", "Chi tiết cảnh báo (10 gần nhất)"),
            data_table(
                ["ID", "Loại", "Trạng thái", "Thời gian", ""],
                alert_rows,
                col_flex=[1, 2, 2, 3, 1],
            ) if alert_rows else empty_state("Chưa có cảnh báo"),
        ])

        # --- Assemble page ---
        list_ref.current.controls = [
            metrics,
            glass_container(padding=14, radius=16, content=breakdown_section),
            glass_container(padding=14, radius=16, content=cam_section),
            glass_container(padding=14, radius=16, content=alert_list_section),
        ]
        if list_ref.current.page:
            list_ref.current.update()

    content = ft.Column(ref=list_ref, spacing=12, controls=[])
    refresh()  # populate on init (update() is no-op until page is set)

    return ft.Column(
        expand=True,
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(tight=True, spacing=1, controls=[
                        ft.Text("Phân tích vận hành", size=20, weight=ft.FontWeight.W_700),
                        ft.Text("Thống kê camera & cảnh báo", size=11, color=ft.Colors.WHITE54),
                    ]),
                    ft.IconButton(
                        ft.Icons.REFRESH,
                        icon_color=ft.Colors.WHITE70,
                        tooltip="Làm mới",
                        on_click=lambda e: refresh(),
                    ),
                ],
            ),
            msg,
            content,
        ],
    )

