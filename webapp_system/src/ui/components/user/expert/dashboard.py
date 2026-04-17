import flet as ft
from ui.theme import glass_container, metric_card, status_badge, WARNING, PRIMARY

_MOCK_CASES = [
    {"id": "Case-2026-001", "status": "Mới", "kind": "warning",
     "type": "Bất thường hành vi", "time": "09:40", "desc": "Bò #12 hung hăng bất thường"},
    {"id": "Case-2026-002", "status": "Đang xử lý", "kind": "secondary",
     "type": "Dự báo sức khỏe", "time": "09:31", "desc": "Bò #07 sụt cân"},
    {"id": "Case-2026-003", "status": "Đã đóng", "kind": "primary",
     "type": "Kết quả tư vấn", "time": "09:10", "desc": "Bò #03 hồi phục"},
    {"id": "Case-2026-004", "status": "Mới", "kind": "warning",
     "type": "Cảnh báo bệnh", "time": "08:55", "desc": "Bò #18 triệu chứng lở mồm"},
    {"id": "Case-2026-005", "status": "Đang xử lý", "kind": "secondary",
     "type": "Tư vấn dinh dưỡng", "time": "08:30", "desc": "Bò #05 ăn kém"},
    {"id": "Case-2026-006", "status": "Đã đóng", "kind": "primary",
     "type": "Kiểm tra định kỳ", "time": "08:00", "desc": "Bò #09 ổn định"},
]
_FILTER_OPTS = [
    ("all", "Tất cả"), ("Mới", "Mới"),
    ("Đang xử lý", "Đang xử lý"), ("Đã đóng", "Đã đóng"),
]
_TYPE_ICONS = {
    "Bất thường hành vi": ft.Icons.WARNING_AMBER,
    "Dự báo sức khỏe":    ft.Icons.MONITOR_HEART,
    "Kết quả tư vấn":     ft.Icons.CHAT,
    "Cảnh báo bệnh":      ft.Icons.BUG_REPORT,
    "Tư vấn dinh dưỡng":  ft.Icons.GRASS,
    "Kiểm tra định kỳ":   ft.Icons.FACT_CHECK,
}


def _case_card(case: dict) -> ft.Control:
    icon = _TYPE_ICONS.get(case["type"], ft.Icons.ARTICLE)
    return ft.Container(
        margin=ft.margin.only(bottom=8),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_radius=14,
        border=ft.border.all(1, ft.Colors.with_opacity(0.14, ft.Colors.WHITE)),
        ink=True,
        content=ft.Row(
            spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    width=40, height=40, border_radius=12,
                    bgcolor=ft.Colors.with_opacity(0.14, ft.Colors.TEAL_300),
                    alignment=ft.alignment.center,
                    content=ft.Icon(icon, size=20, color=ft.Colors.TEAL_300),
                ),
                ft.Column(
                    expand=True, spacing=3, tight=True,
                    controls=[
                        ft.Row(controls=[
                            ft.Text(case["id"], size=12, weight=ft.FontWeight.W_700, expand=True),
                            status_badge(case["status"], case["kind"]),
                        ]),
                        ft.Text(case["type"], size=11, color=ft.Colors.WHITE70),
                        ft.Row(controls=[
                            ft.Text(case["desc"], size=11, color=ft.Colors.WHITE54,
                                    expand=True, max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(case["time"], size=10, color=ft.Colors.WHITE38),
                        ]),
                    ],
                ),
            ],
        ),
    )


def _sla_metric_card(value: float) -> ft.Control:
    color = (ft.Colors.GREEN_400 if value >= 90
             else ft.Colors.AMBER_400 if value >= 75
             else ft.Colors.RED_400)
    return glass_container(
        padding=16, radius=20,
        content=ft.Column(tight=True, spacing=8, controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text("SLA đúng hạn", size=13, color=ft.Colors.WHITE70),
                    ft.Icon(ft.Icons.AV_TIMER, color=color, size=18),
                ],
            ),
            ft.Text(f"{value:.0f}%", size=24, weight=ft.FontWeight.W_700, color=color),
            ft.ProgressBar(value=value / 100, color=color, bgcolor=ft.Colors.WHITE12),
        ]),
    )


def build_expert_dashboard(page: ft.Page = None):
    selected = {"filter": "all"}
    chips_ref = ft.Ref[ft.Row]()
    list_ref  = ft.Ref[ft.ListView]()

    def _update():
        if page:
            try:
                page.update()
            except Exception:
                pass

    def _chip(key, label):
        is_sel = selected["filter"] == key
        return ft.Container(
            on_click=lambda e, k=key: _set_filter(k),
            ink=True,
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            border_radius=20,
            bgcolor=(ft.Colors.with_opacity(0.30, PRIMARY) if is_sel
                     else ft.Colors.with_opacity(0.10, ft.Colors.WHITE)),
            border=ft.border.all(
                1, ft.Colors.with_opacity(0.45, PRIMARY) if is_sel
                else ft.Colors.with_opacity(0.20, ft.Colors.WHITE),
            ),
            content=ft.Text(
                label, size=12,
                weight=ft.FontWeight.W_600 if is_sel else ft.FontWeight.W_400,
                color=ft.Colors.WHITE if is_sel else ft.Colors.WHITE70,
            ),
        )

    def _filtered():
        f = selected["filter"]
        return [c for c in _MOCK_CASES if f == "all" or c["status"] == f]

    def _set_filter(key):
        selected["filter"] = key
        if chips_ref.current:
            chips_ref.current.controls = [_chip(k, l) for k, l in _FILTER_OPTS]
        if list_ref.current:
            list_ref.current.controls = [_case_card(c) for c in _filtered()]
        _update()

    return ft.Column(
        expand=True, spacing=16,
        controls=[
            ft.Text("Bảng điều khiển chuyên gia", size=26, weight=ft.FontWeight.W_700),
            ft.Row(
                spacing=12,
                controls=[
                    ft.Container(expand=1,
                                 content=metric_card("Ca đang mở", "21",
                                                     ft.Icons.MARK_EMAIL_UNREAD, WARNING)),
                    ft.Container(expand=1,
                                 content=metric_card("Đánh giá hôm nay", "37",
                                                     ft.Icons.FACT_CHECK, PRIMARY)),
                    ft.Container(expand=1, content=_sla_metric_card(96)),
                ],
            ),
            ft.Row(
                ref=chips_ref, spacing=8, scroll=ft.ScrollMode.AUTO,
                controls=[_chip(k, l) for k, l in _FILTER_OPTS],
            ),
            ft.Container(
                expand=True,
                content=ft.ListView(
                    ref=list_ref, expand=True, spacing=0,
                    controls=[_case_card(c) for c in _filtered()],
                ),
            ),
        ],
    )
