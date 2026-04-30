import flet as ft

from bll.services import chat_service
from bll.services.auth_service import get_session_value
from dal.dataset_repo import get_images_pending
from ui.components.user.expert.dashboard_overview_chart import build_case_overview_chart
from ui.theme import DANGER, PRIMARY, SECONDARY, WARNING, glass_container, page_header, severity_badge, status_badge

_STATUS_META = {
    "new": ("Moi", "warning"),
    "claimed": ("Mo", "secondary"),
    "under_review": ("Xu ly", "secondary"),
    "waiting_farmer": ("Cho", "neutral"),
    "escalated": ("Khan", "danger"),
    "closed": ("Xong", "success"),
}


def _metric_tile(title: str, value: str, icon, accent: str, action_hint: str, on_click=None) -> ft.Control:
    return ft.Container(
        ink=bool(on_click),
        on_click=(lambda e: on_click()) if on_click else None,
        padding=14,
        border_radius=18,
        bgcolor=ft.Colors.with_opacity(0.22, accent),
        border=ft.border.all(1, ft.Colors.with_opacity(0.32, accent)),
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
                ft.Text(value, size=26, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE),
                ft.Text(action_hint, size=10, color=ft.Colors.WHITE54, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            ],
        ),
    )


def _case_card(case: dict, on_open) -> ft.Control:
    status_label, status_kind = _STATUS_META.get(case.get("status"), ("Mo", "secondary"))
    return ft.Container(
        margin=ft.margin.only(bottom=8),
        padding=14,
        border_radius=18,
        bgcolor=ft.Colors.with_opacity(0.16, ft.Colors.WHITE),
        border=ft.border.all(1, ft.Colors.with_opacity(0.14, ft.Colors.WHITE)),
        ink=True,
        on_click=lambda e: on_open(case["id"]),
        content=ft.Column(
            spacing=6,
            tight=True,
            controls=[
                ft.Row(
                    spacing=6,
                    controls=[
                        ft.Text(f"Case-{case['id']:04d}", size=13, weight=ft.FontWeight.W_700, expand=True),
                        severity_badge(case.get("severity", "medium")),
                        status_badge(status_label, status_kind),
                    ],
                ),
                ft.Text(
                    f"{case.get('farm_name', '-')}  •  {case.get('cow_id', '-')}",
                    size=11,
                    color=ft.Colors.WHITE70,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Text(
                    case.get("summary", "Chua co tom tat."),
                    size=11,
                    color=ft.Colors.WHITE54,
                    max_lines=2,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(case.get("case_type", "Tư vấn"), size=10, color=ft.Colors.WHITE38),
                        ft.Text(case.get("sla_due_at", "")[11:16] or "-", size=10, color=ft.Colors.AMBER_200),
                    ],
                ),
            ],
        ),
    )


def build_expert_dashboard(page: ft.Page = None, on_navigate=None):
    expert_id = int(get_session_value(page, "user_id", 0) or 0)
    chat_service.ensure_demo_data(expert_id)
    cases = chat_service.list_conversations_for_expert(expert_id)
    urgent_cases = [c for c in cases if c.get("severity") in ("critical", "high") or c.get("status") == "escalated"]
    waiting_cases = [c for c in cases if c.get("status") == "waiting_farmer"]
    review_count = len(get_images_pending())
    snapshot_cases = (urgent_cases or waiting_cases or cases)[:3]

    def _navigate(target: str, payload: dict | None = None):
        if on_navigate:
            on_navigate(target, payload)

    def _open_case(case_id: int):
        if page and isinstance(page.data, dict):
            page.data["expert_selected_case_id"] = case_id
        _navigate("consulting")

    metric_controls = [
        ("Ca mới", str(sum(1 for case in cases if case.get("status") == "new")), ft.Icons.FOLDER_OPEN, PRIMARY, "Mở Tư vấn", lambda: _navigate("consulting", {"expert_consulting_filter": "new"}), {"xs": 6, "sm": 4}),
        ("Ca khẩn", str(len(urgent_cases)), ft.Icons.PRIORITY_HIGH, DANGER, "Mở Tư vấn", lambda: _navigate("consulting", {"expert_consulting_filter": "urgent"}), {"xs": 6, "sm": 4}),
        ("Chờ data", str(review_count), ft.Icons.FACT_CHECK, WARNING, "Mở Dữ liệu", lambda: _navigate("raw_data", {"expert_raw_data_filter": "PENDING_REVIEW"}), {"xs": 6, "sm": 4}),
        ("Chờ farmer", str(len(waiting_cases)), ft.Icons.HOURGLASS_TOP, SECONDARY, "Mở Tư vấn", lambda: _navigate("consulting", {"expert_consulting_filter": "waiting"}), {"xs": 6, "sm": 4}),
    ]

    return ft.Container(
        expand=True,
        content=ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=14,
            controls=[
                page_header("Tổng quan chuyên gia", icon_name="SPACE_DASHBOARD"),
                ft.ResponsiveRow(
                    columns=12,
                    spacing=10,
                    run_spacing=10,
                    controls=[
                        ft.Column(
                            col=col,
                            controls=[_metric_tile(title, value, icon, accent, action_hint, on_click)],
                        )
                        for title, value, icon, accent, action_hint, on_click, col in metric_controls
                    ],
                ),
                build_case_overview_chart(page, expert_id),
                glass_container(
                    padding=14,
                    radius=18,
                    content=ft.Column(
                        spacing=10,
                        tight=True,
                        controls=[
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text("Cần xử lý ngay", size=14, weight=ft.FontWeight.W_700),
                                    ft.Text("Top 3", size=10, color=ft.Colors.WHITE54),
                                ],
                            ),
                            *[_case_card(case, _open_case) for case in snapshot_cases],
                        ]
                        if snapshot_cases
                        else [ft.Text("Chưa có case ưu tiên cao.", size=12, color=ft.Colors.WHITE54)],
                    ),
                ),
            ],
        ),
    )
