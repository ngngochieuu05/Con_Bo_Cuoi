"""
Trang Chu User  Mobile Dashboard
Layout 2x2 KPI grid, fetch tu Edge Server (fallback demo).
Con Bo Cuoi Design System
"""
import flet as ft
from datetime import datetime, timedelta
import threading
import json
import os

try:
    import requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

from src.ui.theme import (
    BG_MAIN, BG_PANEL, PRIMARY, SECONDARY, ACCENT,
    TEXT_MAIN, TEXT_SUB, TEXT_MUTED,
    WARNING, DANGER, SUCCESS, BORDER,
    GRAD_TEAL, GRAD_CYAN, GRAD_WARN,
    RADIUS_CARD, SIZE_H2, SIZE_H3, SIZE_BODY, SIZE_CAPTION,
    panel,
)

_CFG_PATH = "src/ui/data/app_config.json"


def _load_server_url() -> str:
    for path in [_CFG_PATH, "ui/data/app_config.json"]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                return cfg.get("server_url", "http://192.168.1.100:8000")
            except Exception:
                pass
    return "http://192.168.1.100:8000"


def _hour_greeting() -> str:
    h = datetime.now().hour
    if h < 12:
        return "Chao buoi sang"
    if h < 18:
        return "Chao buoi chieu"
    return "Chao buoi toi"


#  Demo sessions (fallback) 
_TODAY = datetime.now()
_SESSIONS = [
    {
        "date": _TODAY.strftime("%d/%m/%Y"),
        "label": "Hom nay",
        "cows": 87, "alerts": 5, "online": 4,
        "events": [
            {"t": "05:12", "cam": "CAM-01", "msg": "Bo #B042 bat thuong",       "sev": "Cao"},
            {"t": "07:30", "cam": "CAM-02", "msg": "Bo #B017 bo an",            "sev": "TB"},
            {"t": "09:00", "cam": "SYS",    "msg": "Snapshot tu dong -- 87 bo", "sev": "OK"},
            {"t": "10:15", "cam": "CAM-04", "msg": "Bo #B055 ra ngoai khu vuc", "sev": "Cao"},
        ],
    },
    {
        "date": (_TODAY - timedelta(days=1)).strftime("%d/%m/%Y"),
        "label": "Hom qua",
        "cows": 84, "alerts": 3, "online": 4,
        "events": [
            {"t": "06:00", "cam": "SYS",    "msg": "He thong khoi dong OK",      "sev": "OK"},
            {"t": "08:20", "cam": "CAM-01", "msg": "Bo #B031 bat dong 10 phut",  "sev": "TB"},
            {"t": "18:00", "cam": "SYS",    "msg": "Bao cao ngay -- 84 bo",      "sev": "OK"},
        ],
    },
]


class TrangChuUser(ft.Column):
    """Trang Chu user -- mobile layout 2x2 KPI, fetch server data on mount."""

    def __init__(self, user_info: dict = None, on_refresh=None):
        super().__init__()
        self.user_info  = user_info or {}
        self.on_refresh = on_refresh
        self.server_url = _load_server_url()
        self.expand     = True
        self.scroll     = ft.ScrollMode.AUTO
        self.spacing    = 0

        # Mutable KPI text references
        self._kpi_cattle = ft.Text("87",  size=24, weight=ft.FontWeight.BOLD,
                                   color=ft.Colors.WHITE)
        self._kpi_cam    = ft.Text("4/4", size=24, weight=ft.FontWeight.BOLD,
                                   color=ft.Colors.WHITE)
        self._kpi_alerts = ft.Text("5",   size=24, weight=ft.FontWeight.BOLD,
                                   color=ft.Colors.WHITE)
        self._kpi_model  = ft.Text(self.user_info.get("model", "YOLOv9"),
                                   size=16, weight=ft.FontWeight.BOLD,
                                   color=ft.Colors.WHITE)
        self._srv_status = ft.Text("", size=10, color=TEXT_MUTED)

        self.controls = self._build_controls()

    #  Build 
    def _build_controls(self):
        today = datetime.now().strftime("%d/%m/%Y")

        # Mini KPI card -- phone width friendly
        def _mini_kpi(icon, title, value_ctrl, subtitle, grad):
            return ft.Container(
                content=ft.Column([
                    ft.Container(
                        content=ft.Icon(icon, color=ft.Colors.WHITE, size=18),
                        width=36, height=36, border_radius=18,
                        bgcolor=ft.Colors.with_opacity(0.25, ft.Colors.WHITE),
                        alignment=ft.alignment.center,
                    ),
                    ft.Container(height=8),
                    value_ctrl,
                    ft.Text(title,    size=11, color=ft.Colors.WHITE,
                            weight=ft.FontWeight.W_500),
                    ft.Text(subtitle, size=9,
                            color=ft.Colors.with_opacity(0.7, ft.Colors.WHITE)),
                ], spacing=2),
                gradient=ft.LinearGradient(
                    begin=ft.alignment.top_left,
                    end=ft.alignment.bottom_right,
                    colors=grad,
                ),
                border_radius=RADIUS_CARD,
                padding=ft.padding.symmetric(vertical=14, horizontal=14),
                shadow=ft.BoxShadow(
                    blur_radius=18, offset=ft.Offset(0, 5),
                    color=ft.Colors.with_opacity(0.3, grad[0]),
                ),
                expand=True,
            )

        kpi_row1 = ft.Row([
            _mini_kpi(ft.Icons.PETS_ROUNDED,
                      "Tong Dan Bo",  self._kpi_cattle, "Hom nay",    GRAD_TEAL),
            _mini_kpi(ft.Icons.VIDEOCAM_ROUNDED,
                      "Camera Online", self._kpi_cam,   "Truc tuyen", GRAD_CYAN),
        ], spacing=10)

        kpi_row2 = ft.Row([
            _mini_kpi(ft.Icons.WARNING_AMBER_ROUNDED,
                      "Canh Bao",   self._kpi_alerts, "Hom nay",     GRAD_WARN),
            _mini_kpi(ft.Icons.SMART_TOY_ROUNDED,
                      "Model AI",   self._kpi_model,  "Do chinh xac",
                      ["#7C4DFF", "#4527A0"]),
        ], spacing=10)

        kpi_grid = ft.Column([kpi_row1, kpi_row2], spacing=10)

        # Bar chart (static 7-day)
        hour_data = [
            ("T2", 82), ("T3", 85), ("T4", 80), ("T5", 88),
            ("T6", 84), ("T7", 90), ("CN", 87),
        ]
        bar_chart = ft.BarChart(
            bar_groups=[
                ft.BarChartGroup(x=i, bar_rods=[
                    ft.BarChartRod(
                        from_y=0, to_y=val, width=20,
                        gradient=ft.LinearGradient(
                            begin=ft.alignment.bottom_center,
                            end=ft.alignment.top_center,
                            colors=[SECONDARY, PRIMARY],
                        ),
                        tooltip=f"{label}: {val} bo",
                        border_radius=ft.BorderRadius(4, 4, 0, 0),
                    )
                ])
                for i, (label, val) in enumerate(hour_data)
            ],
            left_axis=ft.ChartAxis(labels_size=28),
            bottom_axis=ft.ChartAxis(labels=[
                ft.ChartAxisLabel(
                    value=i,
                    label=ft.Text(label, size=9, color=TEXT_SUB),
                )
                for i, (label, _) in enumerate(hour_data)
            ]),
            horizontal_grid_lines=ft.ChartGridLines(
                color=ft.Colors.with_opacity(0.06, ft.Colors.WHITE), width=1,
            ),
            tooltip_bgcolor=ft.Colors.with_opacity(0.85, BG_PANEL),
            max_y=100, expand=True, bgcolor=ft.Colors.TRANSPARENT, interactive=True,
        )

        chart_panel = panel(
            content=bar_chart,
            title="So Bo -- 7 Ngay",
            icon=ft.Icons.SHOW_CHART_ROUNDED,
            expand=True,
        )

        # Session log blocks
        def _event_row(ev: dict) -> ft.Container:
            sev   = ev["sev"]
            color = DANGER if sev == "Cao" else WARNING if sev == "TB" else PRIMARY
            icon  = (ft.Icons.WARNING_ROUNDED if sev == "Cao"
                     else ft.Icons.ERROR_OUTLINE_ROUNDED if sev == "TB"
                     else ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED)
            return ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon(icon, color=ft.Colors.WHITE, size=11),
                        width=24, height=24, border_radius=12,
                        bgcolor=color, alignment=ft.alignment.center,
                    ),
                    ft.Text(ev["t"],   size=9,       color=TEXT_MUTED, width=34),
                    ft.Text(ev["cam"], size=9,       color=TEXT_SUB,   width=50),
                    ft.Text(ev["msg"], size=SIZE_BODY, color=TEXT_MAIN, expand=True),
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=ft.Colors.with_opacity(0.02, ft.Colors.WHITE),
                border_radius=6,
                padding=ft.padding.symmetric(horizontal=8, vertical=5),
                border=ft.border.all(1, ft.Colors.with_opacity(0.04, ft.Colors.WHITE)),
            )

        def _session_block(sess: dict) -> ft.Container:
            is_today = sess["label"] == "Hom nay"
            color    = PRIMARY if is_today else TEXT_SUB
            mini_stats = ft.Row([
                ft.Container(
                    content=ft.Column([
                        ft.Text(str(sess["cows"]), size=16, color=TEXT_MAIN,
                                weight=ft.FontWeight.BOLD),
                        ft.Text("Bo", size=9, color=TEXT_SUB),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=1),
                    bgcolor=ft.Colors.with_opacity(0.06, PRIMARY),
                    border_radius=8,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.15, PRIMARY)),
                    padding=ft.padding.symmetric(horizontal=12, vertical=7),
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text(str(sess["alerts"]), size=16, color=WARNING,
                                weight=ft.FontWeight.BOLD),
                        ft.Text("Alert", size=9, color=TEXT_SUB),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=1),
                    bgcolor=ft.Colors.with_opacity(0.06, WARNING),
                    border_radius=8,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.15, WARNING)),
                    padding=ft.padding.symmetric(horizontal=12, vertical=7),
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"{sess['online']}/4", size=16, color=SECONDARY,
                                weight=ft.FontWeight.BOLD),
                        ft.Text("Cam On", size=9, color=TEXT_SUB),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=1),
                    bgcolor=ft.Colors.with_opacity(0.06, SECONDARY),
                    border_radius=8,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.15, SECONDARY)),
                    padding=ft.padding.symmetric(horizontal=12, vertical=7),
                ),
            ], spacing=8)

            events_col = ft.Column(
                [r for ev in sess["events"]
                 for r in [_event_row(ev), ft.Divider(color=BORDER, height=1)]],
                spacing=0,
            )

            return ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Container(
                            content=ft.Text(sess["label"], size=10,
                                            color=ft.Colors.WHITE,
                                            weight=ft.FontWeight.BOLD),
                            bgcolor=(color if is_today
                                     else ft.Colors.with_opacity(0.12, ft.Colors.WHITE)),
                            border_radius=20,
                            padding=ft.padding.symmetric(horizontal=9, vertical=3),
                        ),
                        ft.Text(sess["date"], size=10, color=TEXT_MUTED),
                    ], spacing=8),
                    ft.Container(height=8),
                    mini_stats,
                    ft.Container(height=8),
                    ft.Divider(color=BORDER, height=1),
                    events_col,
                ]),
                bgcolor=ft.Colors.with_opacity(0.04 if is_today else 0.02, ft.Colors.WHITE),
                border_radius=10,
                padding=ft.padding.all(12),
                border=ft.border.all(
                    2 if is_today else 1,
                    ft.Colors.with_opacity(
                        0.2 if is_today else 0.06,
                        PRIMARY if is_today else ft.Colors.WHITE,
                    ),
                ),
            )

        sessions_panel = panel(
            content=ft.Column([_session_block(s) for s in _SESSIONS], spacing=10),
            title="Thong Bao Phien",
            icon=ft.Icons.NOTIFICATIONS_ROUNDED,
            action_widget=ft.Container(
                content=ft.Text("5 chua doc", size=10, color=ft.Colors.WHITE,
                                weight=ft.FontWeight.BOLD),
                bgcolor=DANGER, border_radius=12,
                padding=ft.padding.symmetric(horizontal=9, vertical=3),
            ),
            expand=True,
        )

        # Page header
        header = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Column([
                        ft.Text(f"{_hour_greeting()} \U0001f404",
                                size=SIZE_H2, weight=ft.FontWeight.BOLD,
                                color=TEXT_MAIN),
                        ft.Text(f"Hom nay: {today}",
                                size=SIZE_CAPTION, color=TEXT_SUB),
                    ], spacing=2, expand=True),
                    ft.IconButton(
                        icon=ft.Icons.REFRESH_ROUNDED,
                        icon_color=PRIMARY, icon_size=22,
                        on_click=self.on_refresh,
                        tooltip="Lam moi",
                    ),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                self._srv_status,
            ], spacing=2),
            padding=ft.padding.symmetric(horizontal=2, vertical=6),
        )

        return [
            header,
            ft.Container(height=12),
            kpi_grid,
            ft.Container(height=14),
            chart_panel,
            ft.Container(height=14),
            sessions_panel,
            ft.Container(height=20),
        ]

    #  Lifecycle 
    def did_mount(self):
        threading.Thread(target=self._fetch_server_data, daemon=True).start()

    def _fetch_server_data(self):
        if not _HAS_REQUESTS:
            return
        try:
            resp = requests.get(f"{self.server_url}/api/dashboard", timeout=3)
            data = resp.json()
            self._kpi_cattle.value = str(data.get("total_cows",      ""))
            self._kpi_cam.value    = f"{data.get('cameras_online', '')}/4"
            self._kpi_alerts.value = str(data.get("active_alerts",   ""))
            self._srv_status.value = f"Server {self.server_url} -- da dong bo"
            self._srv_status.color = SUCCESS
            try:
                self._kpi_cattle.update()
                self._kpi_cam.update()
                self._kpi_alerts.update()
                self._srv_status.update()
            except Exception:
                pass
        except Exception:
            self._srv_status.value = "Offline -- dang dung du lieu mau"
            self._srv_status.color = TEXT_MUTED
            try:
                self._srv_status.update()
            except Exception:
                pass
