from __future__ import annotations

from collections import Counter

import flet as ft

from bll.admin.oa_management import get_all_alerts, get_all_cameras, resolve_alert
from ui.theme import (
    PRIMARY,
    SECONDARY,
    empty_state,
    fmt_dt,
    glass_container,
    metric_card,
    open_bottom_sheet,
    page_header,
    severity_badge,
    status_badge,
)

_ALERT_LABEL = {
    "cow_fight": "Va cham",
    "cow_lie": "Nam lau",
    "cow_sick": "Suc khoe",
    "heat_high": "Nhiet cao",
}
_CAM_STATUS = {
    "online": ("Can xem", "primary"),
    "warning": ("Can xem", "warning"),
    "offline": ("Offline", "danger"),
}


def _alert_severity(code: str) -> str:
    if code == "cow_fight":
        return "critical"
    if code in {"cow_sick", "heat_high"}:
        return "high"
    return "medium"


def _build_export_sheet(page: ft.Page, total: int, open_count: int) -> None:
    body = ft.Column(
        tight=True,
        spacing=10,
        controls=[
            ft.Text(f"Tong canh bao: {total}", size=12, color=ft.Colors.WHITE70),
            ft.Text(f"Chua xu ly: {open_count}", size=12, color=ft.Colors.WHITE70),
            ft.ElevatedButton(
                "Export CSV (sap ho tro)",
                icon=ft.Icons.DOWNLOAD,
                disabled=True,
            ),
            ft.Text(
                "Tam thoi dung sheet nay de gom hanh dong secondary tren mobile.",
                size=11,
                color=ft.Colors.WHITE54,
            ),
        ],
    )
    open_bottom_sheet(page, "Export va hanh dong", body)


def build_oa_management():
    msg = ft.Text("", size=12)
    content_ref = ft.Ref[ft.Column]()
    state = {"tab": 0}
    content_holder = ft.Column(ref=content_ref, spacing=10, controls=[])

    def refresh():
        alerts = sorted(get_all_alerts(), key=lambda a: a.get("created_at", ""), reverse=True)
        cameras = get_all_cameras()
        total = len(alerts)
        open_count = sum(1 for a in alerts if a.get("trang_thai") == "CHUA_XU_LY")
        done_count = sum(1 for a in alerts if a.get("trang_thai") == "DA_XU_LY")
        cam_ok = sum(1 for c in cameras if c.get("trang_thai") == "online")

        def _resolve(aid: int):
            resolve_alert(aid)
            msg.value = f"Da xu ly canh bao #{aid}."
            msg.color = ft.Colors.GREEN_300
            if msg.page:
                msg.update()
            refresh()

        stats_cards = ft.Row(
            wrap=True,
            spacing=8,
            run_spacing=8,
            controls=[
                ft.Container(expand=1, content=metric_card("Tong canh bao", str(total), ft.Icons.NOTIFICATIONS, SECONDARY)),
                ft.Container(expand=1, content=metric_card("Can xu ly", str(open_count), ft.Icons.ERROR_OUTLINE, ft.Colors.RED_300)),
            ],
        )

        types = Counter(a.get("loai_canh_bao", "?") for a in alerts)
        type_cards = [
            ft.Container(
                border_radius=12,
                padding=10,
                bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
                border=ft.border.all(1, ft.Colors.with_opacity(0.14, ft.Colors.WHITE)),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(_ALERT_LABEL.get(code, code), size=12),
                        ft.Row(
                            tight=True,
                            spacing=8,
                            controls=[
                                ft.Container(
                                    width=120,
                                    height=6,
                                    border_radius=3,
                                    bgcolor=ft.Colors.with_opacity(0.15, PRIMARY),
                                    content=ft.Container(
                                        width=max(12, min(120, int((count / max(types.values(), default=1)) * 120))),
                                        height=6,
                                        border_radius=3,
                                        bgcolor=PRIMARY,
                                    ),
                                ),
                                ft.Text(str(count), size=16, weight=ft.FontWeight.W_700),
                            ],
                        ),
                    ],
                ),
            )
            for code, count in sorted(types.items(), key=lambda x: -x[1])[:5]
        ]

        alert_cards = [
            ft.Container(
                border_radius=14,
                padding=12,
                bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
                border=ft.border.all(1, ft.Colors.with_opacity(0.14, ft.Colors.WHITE)),
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(f"Case-{item.get('id_canh_bao', '--')}", size=15, weight=ft.FontWeight.W_700),
                                severity_badge(_alert_severity(item.get("loai_canh_bao", ""))),
                            ],
                        ),
                        ft.Text(_ALERT_LABEL.get(item.get("loai_canh_bao", ""), "Canh bao"), size=12, color=ft.Colors.WHITE70),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(fmt_dt(item.get("created_at", "")), size=11, color=ft.Colors.WHITE54),
                                status_badge(
                                    "Da xu ly" if item.get("trang_thai") == "DA_XU_LY" else "Cho xu ly",
                                    "primary" if item.get("trang_thai") == "DA_XU_LY" else "warning",
                                ),
                            ],
                        ),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.END,
                            controls=[
                                ft.TextButton(
                                    "Dong case",
                                    disabled=item.get("trang_thai") != "CHUA_XU_LY",
                                    on_click=lambda e, aid=item.get("id_canh_bao"): _resolve(aid),
                                )
                            ],
                        ),
                    ],
                ),
            )
            for item in alerts[:5]
        ]

        cam_cards = [
            ft.Container(
                border_radius=12,
                padding=10,
                bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
                border=ft.border.all(1, ft.Colors.with_opacity(0.14, ft.Colors.WHITE)),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Column(
                            tight=True,
                            controls=[
                                ft.Text(cam.get("id_camera", "--"), size=13, weight=ft.FontWeight.W_700),
                                ft.Text(cam.get("khu_vuc_chuong", "--"), size=11, color=ft.Colors.WHITE54),
                            ],
                        ),
                        status_badge(*_CAM_STATUS.get(cam.get("trang_thai", "offline"), ("Can xem", "warning"))),
                    ],
                ),
            )
            for cam in cameras[:5]
        ]

        tabs = ft.Tabs(
            selected_index=state["tab"],
            on_change=lambda e: state.__setitem__("tab", e.control.selected_index),
            animation_duration=250,
            tabs=[
                ft.Tab(
                    text="Snapshot",
                    content=ft.Column(
                        spacing=10,
                        controls=[
                            stats_cards,
                            ft.Container(
                                padding=ft.padding.symmetric(horizontal=10, vertical=8),
                                border_radius=10,
                                bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
                                border=ft.border.all(1, ft.Colors.with_opacity(0.12, ft.Colors.WHITE)),
                                content=ft.Text(
                                    f"Da dong: {done_count} • Camera online: {cam_ok}/{len(cameras)}",
                                    size=11,
                                    color=ft.Colors.WHITE60,
                                ),
                            ),
                            *(type_cards or [empty_state("Chua co du lieu")]),
                        ],
                    ),
                ),
                ft.Tab(
                    text="Canh bao",
                    content=ft.Column(spacing=10, controls=alert_cards or [empty_state("Chua co canh bao")]),
                ),
                ft.Tab(
                    text="Camera",
                    content=ft.Column(spacing=10, controls=cam_cards or [empty_state("Chua co camera")]),
                ),
            ],
            expand=1,
        )

        if not content_ref.current:
            return
        content_ref.current.controls = [tabs]
        if content_ref.current.page:
            content_ref.current.update()

    refresh()

    return ft.Column(
        expand=True,
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            page_header(
                "Tong quan admin",
                "Snapshot triage cho mobile. Khong dua bang desktop day dac len day.",
                icon_name="DASHBOARD",
                actions=[
                    ft.IconButton(
                        ft.Icons.DOWNLOAD,
                        tooltip="Export",
                        on_click=lambda e: _build_export_sheet(e.page, len(get_all_alerts()), sum(1 for a in get_all_alerts() if a.get("trang_thai") == "CHUA_XU_LY")),
                    ),
                    ft.IconButton(ft.Icons.REFRESH, tooltip="Lam moi", on_click=lambda e: refresh()),
                ],
            ),
            msg,
            glass_container(padding=12, radius=16, content=content_holder),
        ],
    )
