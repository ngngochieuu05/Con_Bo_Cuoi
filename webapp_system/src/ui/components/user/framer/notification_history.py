"""
Farmer — Lịch sử thông báo
Hiển thị tất cả cảnh báo hệ thống nhận được từ canh_bao_repo.
Hỗ trợ lọc theo loại (cow_fight / cow_lie / tất cả) và trạng thái.
"""
from __future__ import annotations

import flet as ft

from ui.theme import (
    PRIMARY, SECONDARY, WARNING, DANGER,
    glass_container, status_badge, button_style,
    section_title, empty_state, fmt_dt,
)


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────

_TYPE_MAP = {
    "cow_fight": ("⚡ Húc nhau",  DANGER,   "danger"),
    "cow_lie":   ("🐄 Bỏ ăn",    WARNING,  "warning"),
}
_STATUS_MAP = {
    "CHUA_XU_LY": ("Chưa xử lý", "danger"),
    "DA_XU_LY":   ("Đã xử lý",   "primary"),
}


def _alert_card(a: dict, on_resolve) -> ft.Control:
    """Card một cảnh báo."""
    loai      = a.get("loai_canh_bao", "")
    trang_thai= a.get("trang_thai", "CHUA_XU_LY")
    cam       = a.get("id_camera_chuong", "?")
    created   = a.get("created_at", "")
    a_id      = a.get("id_canh_bao")

    type_label, type_color, _ = _TYPE_MAP.get(loai, ("Cảnh báo", WARNING, "warning"))
    st_label, st_kind         = _STATUS_MAP.get(trang_thai, ("Không rõ", "warning"))

    is_open = trang_thai == "CHUA_XU_LY"

    def _do_resolve(e):
        if not is_open:
            return
        try:
            from bll.services.alert_service import resolve_farmer_alert
            resolve_farmer_alert(a_id)
        except Exception:
            pass
        on_resolve()

    resolve_btn = ft.ElevatedButton(
        "Đánh dấu đã xử lý",
        icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
        style=button_style("primary"),
        height=30,
        visible=is_open,
        on_click=_do_resolve,
    )

    return ft.Container(
        border_radius=14,
        padding=ft.padding.symmetric(horizontal=14, vertical=12),
        bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.WHITE),
        border=ft.border.all(
            1,
            ft.Colors.with_opacity(0.30 if is_open else 0.10, type_color),
        ),
        content=ft.Column(spacing=8, controls=[
            # Header row
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(tight=True, spacing=8, controls=[
                        ft.Container(
                            width=4, height=36, border_radius=2,
                            bgcolor=type_color,
                        ),
                        ft.Column(tight=True, spacing=2, controls=[
                            ft.Text(
                                type_label, size=14,
                                weight=ft.FontWeight.W_700,
                                color=type_color,
                            ),
                            ft.Text(
                                f"Camera #{cam}",
                                size=11, color=ft.Colors.WHITE54,
                            ),
                        ]),
                    ]),
                    status_badge(st_label, st_kind),
                ],
            ),
            # Time + ID row
            ft.Row(spacing=10, tight=True, controls=[
                ft.Icon(ft.Icons.ACCESS_TIME, size=12, color=ft.Colors.WHITE38),
                ft.Text(
                    fmt_dt(created) if created else "--",
                    size=11, color=ft.Colors.WHITE54,
                ),
                ft.Text("·", size=11, color=ft.Colors.WHITE24),
                ft.Icon(ft.Icons.TAG, size=11, color=ft.Colors.WHITE38),
                ft.Text(f"#{a_id}", size=11, color=ft.Colors.WHITE38),
            ]),
            # Resolve button (chỉ hiện nếu chưa xử lý)
            resolve_btn if is_open else ft.Container(height=0),
        ]),
    )


# ──────────────────────────────────────────────────────────────────
# Main builder
# ──────────────────────────────────────────────────────────────────

def build_notification_history(page: ft.Page = None):
    """Màn hình Lịch sử thông báo — lấy cảnh báo theo id_user từ page.data."""
    id_user: int | None = None
    if page and isinstance(page.data, dict):
        try:
            id_user = int(page.data.get("user_id", 0)) or None
        except (TypeError, ValueError):
            id_user = None

    active_filter = {"type": "all", "status": "all"}
    list_ref      = ft.Ref[ft.Column]()
    count_ref     = ft.Ref[ft.Text]()

    def _load_alerts() -> list[dict]:
        try:
            from bll.services.alert_service import get_alerts_by_user_or_all
            alerts = get_alerts_by_user_or_all(id_user)
        except Exception:
            alerts = []
        return sorted(alerts, key=lambda a: a.get("created_at", ""), reverse=True)

    def refresh():
        alerts = _load_alerts()

        # Filter
        t_f = active_filter["type"]
        s_f = active_filter["status"]
        if t_f != "all":
            alerts = [a for a in alerts if a.get("loai_canh_bao") == t_f]
        if s_f != "all":
            alerts = [a for a in alerts if a.get("trang_thai") == s_f]

        # Count badge
        open_n = sum(1 for a in _load_alerts() if a.get("trang_thai") == "CHUA_XU_LY")
        if count_ref.current:
            count_ref.current.value = f"{open_n} chưa xử lý" if open_n else "Tất cả đã xử lý"
            count_ref.current.color = DANGER if open_n else ft.Colors.GREEN_300
            count_ref.current.update()

        cards = (
            [_alert_card(a, refresh) for a in alerts]
            if alerts
            else [empty_state("Không có thông báo nào")]
        )
        if list_ref.current:
            list_ref.current.controls = cards
            list_ref.current.update()

    # ── Filter chips ──────────────────────────────────────────────
    type_filter_ref   = ft.Ref[ft.Row]()
    status_filter_ref = ft.Ref[ft.Row]()

    _TYPE_FILTERS   = [("all", "Tất cả"), ("cow_fight", "⚡ Húc nhau"), ("cow_lie", "🐄 Bỏ ăn")]
    _STATUS_FILTERS = [("all", "Tất cả"), ("CHUA_XU_LY", "Chưa xử lý"), ("DA_XU_LY", "Đã xử lý")]

    def _chip(label, is_active, on_click_fn, accent=PRIMARY):
        return ft.Container(
            ink=True, border_radius=20,
            padding=ft.padding.symmetric(horizontal=12, vertical=5),
            bgcolor=ft.Colors.with_opacity(0.28 if is_active else 0.10,
                                           accent if is_active else ft.Colors.WHITE),
            border=ft.border.all(1, ft.Colors.with_opacity(
                0.45 if is_active else 0.15,
                accent if is_active else ft.Colors.WHITE,
            )),
            on_click=on_click_fn,
            content=ft.Text(
                label, size=12,
                weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.W_400,
            ),
        )

    def _build_type_chips():
        return [
            _chip(lbl, active_filter["type"] == k, lambda e, k=k: _on_type(k))
            for k, lbl in _TYPE_FILTERS
        ]

    def _build_status_chips():
        return [
            _chip(lbl, active_filter["status"] == k, lambda e, k=k: _on_status(k),
                  accent=SECONDARY)
            for k, lbl in _STATUS_FILTERS
        ]

    def _on_type(key):
        active_filter["type"] = key
        type_filter_ref.current.controls = _build_type_chips()
        type_filter_ref.current.update()
        refresh()

    def _on_status(key):
        active_filter["status"] = key
        status_filter_ref.current.controls = _build_status_chips()
        status_filter_ref.current.update()
        refresh()

    # ── Initial load ──────────────────────────────────────────────
    alerts_init = _load_alerts()
    open_n_init = sum(1 for a in alerts_init if a.get("trang_thai") == "CHUA_XU_LY")
    cards_init  = (
        [_alert_card(a, refresh) for a in alerts_init]
        if alerts_init
        else [empty_state("Không có thông báo nào")]
    )

    return ft.Column(
        expand=True, spacing=14, scroll=ft.ScrollMode.AUTO,
        controls=[
            # Title + count
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(tight=True, spacing=2, controls=[
                        ft.Text("Lịch sử thông báo", size=20,
                                weight=ft.FontWeight.W_700),
                        ft.Text(
                            ref=count_ref,
                            value=f"{open_n_init} chưa xử lý" if open_n_init else "Tất cả đã xử lý",
                            size=11,
                            color=DANGER if open_n_init else ft.Colors.GREEN_300,
                        ),
                    ]),
                    ft.IconButton(
                        ft.Icons.REFRESH,
                        icon_color=ft.Colors.WHITE70,
                        tooltip="Làm mới",
                        on_click=lambda e: refresh(),
                    ),
                ],
            ),
            # Loại cảnh báo
            ft.Text("Loại:", size=11, color=ft.Colors.WHITE54),
            ft.Row(
                ref=type_filter_ref, spacing=6, scroll=ft.ScrollMode.AUTO,
                controls=_build_type_chips(),
            ),
            # Trạng thái
            ft.Text("Trạng thái:", size=11, color=ft.Colors.WHITE54),
            ft.Row(
                ref=status_filter_ref, spacing=6, scroll=ft.ScrollMode.AUTO,
                controls=_build_status_chips(),
            ),
            ft.Divider(color=ft.Colors.with_opacity(0.10, ft.Colors.WHITE), height=1),
            # Danh sách
            ft.Column(
                ref=list_ref, spacing=10,
                controls=cards_init,
            ),
        ],
    )
