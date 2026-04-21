import flet as ft

from bll.services import chat_service
from bll.services.auth_service import get_session_value
from dal.dataset_repo import get_images_pending
from ui.theme import (
    DANGER,
    PRIMARY,
    SECONDARY,
    SUCCESS,
    WARNING,
    glass_container,
    info_strip,
    page_header,
    severity_badge,
    status_badge,
)

_STATUS_META = {
    "new": ("Moi", "warning"),
    "claimed": ("Mo", "secondary"),
    "under_review": ("Xu ly", "secondary"),
    "waiting_farmer": ("Cho", "neutral"),
    "escalated": ("Khan", "danger"),
    "closed": ("Xong", "success"),
}


def _metric_tile(title: str, value: str, icon, accent: str, note: str) -> ft.Control:
    return ft.Container(
        expand=1,
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
                ft.Text(note, size=10, color=ft.Colors.WHITE54, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            ],
        ),
    )


def _quick_action(title: str, icon, accent: str, on_click) -> ft.Control:
    return ft.Container(
        expand=1,
        ink=True,
        on_click=lambda e: on_click(),
        padding=14,
        border_radius=18,
        bgcolor=ft.Colors.with_opacity(0.14, ft.Colors.WHITE),
        border=ft.border.all(1, ft.Colors.with_opacity(0.14, ft.Colors.WHITE)),
        content=ft.Column(
            spacing=8,
            tight=True,
            controls=[
                ft.Container(
                    width=34,
                    height=34,
                    border_radius=12,
                    bgcolor=ft.Colors.with_opacity(0.18, accent),
                    alignment=ft.alignment.center,
                    content=ft.Icon(icon, color=accent, size=18),
                ),
                ft.Text(title, size=12, weight=ft.FontWeight.W_700, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
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
                    f"{case.get('farm_name', '—')}  •  {case.get('cow_id', '—')}",
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
                        ft.Text(case.get("case_type", "Tu van"), size=10, color=ft.Colors.WHITE38),
                        ft.Text(case.get("sla_due_at", "")[11:16] or "—", size=10, color=ft.Colors.AMBER_200),
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
    closed_cases = [c for c in cases if c.get("status") == "closed"]
    open_cases = [c for c in cases if c.get("status") != "closed"]
    snapshot_cases = (urgent_cases or waiting_cases or open_cases)[:3]

    def _navigate(target: str):
        if on_navigate:
            on_navigate(target)

    def _open_case(case_id: int):
        if page and isinstance(page.data, dict):
            page.data["expert_selected_case_id"] = case_id
        _navigate("consulting")

    return ft.Column(
        expand=True,
        spacing=14,
        controls=[
            page_header(
                "Tong quan chuyen gia",
                "Snapshot nhanh de mo dung workflow, khong dung dashboard lam queue thu hai.",
                icon_name="SPACE_DASHBOARD",
            ),
            info_strip(
                "Dashboard chi hien top case can xu ly va lo du lieu dang cho. Muon thao tac sau hon thi vao Tu van hoac Du lieu.",
                tone="warning",
            ),
            ft.Row(
                spacing=10,
                controls=[
                    _metric_tile("Ca mo", str(len(open_cases)), ft.Icons.FOLDER_OPEN, PRIMARY, "Hang cho hien tai"),
                    _metric_tile("Ca khan", str(len(urgent_cases)), ft.Icons.PRIORITY_HIGH, DANGER, "Can xu ly som"),
                    _metric_tile("Cho data", str(review_count), ft.Icons.FACT_CHECK, WARNING, "Review thu cong"),
                ],
            ),
            ft.Row(
                spacing=10,
                controls=[
                    _metric_tile("Cho farmer", str(len(waiting_cases)), ft.Icons.HOURGLASS_TOP, SECONDARY, "Dang doi phan hoi"),
                    _metric_tile("Da dong", str(len(closed_cases)), ft.Icons.CHECK_CIRCLE, SUCCESS, "Hoan tat gan day"),
                    _quick_action("Mo Tu van", ft.Icons.RECORD_VOICE_OVER, PRIMARY, lambda: _navigate("consulting")),
                ],
            ),
            glass_container(
                padding=14,
                radius=18,
                content=ft.Column(
                    spacing=10,
                    tight=True,
                    controls=[
                        ft.Text("Tac vu nhanh", size=14, weight=ft.FontWeight.W_700),
                        ft.Row(
                            spacing=10,
                            controls=[
                                _quick_action("Case workspace", ft.Icons.RECORD_VOICE_OVER, PRIMARY, lambda: _navigate("consulting")),
                                _quick_action("Review du lieu", ft.Icons.DATA_OBJECT, WARNING, lambda: _navigate("raw_data")),
                                _quick_action("Tien ich", ft.Icons.BUILD, SECONDARY, lambda: _navigate("utilities")),
                            ],
                        ),
                    ],
                ),
            ),
            glass_container(
                expand=True,
                padding=14,
                radius=18,
                content=ft.Column(
                    expand=True,
                    spacing=10,
                    tight=True,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text("Can xu ly ngay", size=14, weight=ft.FontWeight.W_700),
                                ft.Text("Top 3", size=10, color=ft.Colors.WHITE54),
                            ],
                        ),
                        *[_case_card(case, _open_case) for case in snapshot_cases],
                    ]
                    if snapshot_cases
                    else [
                        ft.Text("Chua co case uu tien cao.", size=12, color=ft.Colors.WHITE54),
                    ],
                ),
            ),
        ],
    )
