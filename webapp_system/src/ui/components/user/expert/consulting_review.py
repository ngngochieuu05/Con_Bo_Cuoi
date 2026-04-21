from __future__ import annotations

import flet as ft

from bll.services import chat_service
from bll.services.auth_service import get_session_value
from ui.components.user.expert.consulting_chat import show_chat_view
from ui.theme import info_strip, page_header, severity_badge, status_badge

_FILTER_OPTS = [("all", "Tat ca"), ("urgent", "Khan"), ("mine", "Ca toi"), ("waiting", "Cho")]
_STATUS_META = {
    "new": ("Moi", "warning"),
    "claimed": ("Mo", "secondary"),
    "under_review": ("Xu ly", "secondary"),
    "waiting_farmer": ("Cho", "neutral"),
    "escalated": ("Khan", "danger"),
    "closed": ("Xong", "success"),
}


def build_consulting_review(page: ft.Page = None, on_navigate=None):  # noqa: ARG001
    expert_id = int(get_session_value(page, "user_id", 0) or 0)
    chat_service.ensure_demo_data(expert_id)
    content_area = ft.Container(expand=True)
    selected = {"filter": "all"}

    def _update():
        if page:
            try:
                page.update()
            except Exception:
                pass

    def _filtered():
        cases = chat_service.list_conversations_for_expert(expert_id)
        if selected["filter"] == "urgent":
            return [c for c in cases if c.get("severity") in ("critical", "high") or c.get("status") == "escalated"]
        if selected["filter"] == "mine":
            return [c for c in cases if c.get("claimed_by") == expert_id or c.get("status") in ("claimed", "under_review")]
        if selected["filter"] == "waiting":
            return [c for c in cases if c.get("status") == "waiting_farmer"]
        return cases

    def _chip(key: str, label: str) -> ft.Control:
        is_selected = selected["filter"] == key
        return ft.Container(
            ink=True,
            on_click=lambda e, value=key: _set_filter(value),
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            border_radius=999,
            bgcolor=ft.Colors.with_opacity(0.22, "#56CCF2") if is_selected else ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
            border=ft.border.all(1, ft.Colors.with_opacity(0.24, "#56CCF2") if is_selected else ft.Colors.with_opacity(0.12, ft.Colors.WHITE)),
            content=ft.Text(label, size=11, color=ft.Colors.WHITE),
        )

    def _case_card(case: dict) -> ft.Control:
        status_label, status_kind = _STATUS_META.get(case.get("status"), ("Mo", "secondary"))
        unread = case.get("unread_expert", 0)
        return ft.Container(
            margin=ft.margin.only(bottom=10),
            padding=14,
            border_radius=18,
            bgcolor=ft.Colors.with_opacity(0.14, ft.Colors.WHITE),
            border=ft.border.all(1, ft.Colors.with_opacity(0.14, ft.Colors.WHITE)),
            ink=True,
            on_click=lambda e, item=case: show_chat_view(content_area, item, page, _show_list),
            content=ft.Column(
                spacing=6,
                tight=True,
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(f"Case-{case['id']:04d}", size=13, weight=ft.FontWeight.W_700, expand=True),
                            severity_badge(case.get("severity", "medium")),
                            status_badge(status_label, status_kind),
                        ],
                    ),
                    ft.Text(
                        f"{case.get('farmer_name', '—')}  •  {case.get('farm_name', '—')}  •  {case.get('cow_id', '—')}",
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
                            ft.Text(
                                f"{case.get('case_type', 'Tu van')}  •  SLA {case.get('sla_due_at', '')[11:16] or '—'}",
                                size=10,
                                color=ft.Colors.WHITE38,
                            ),
                            ft.Text(
                                f"{unread} unread" if unread else "Mo workspace",
                                size=10,
                                color=ft.Colors.WHITE60,
                            ),
                        ],
                    ),
                ],
            ),
        )

    def _set_filter(key: str):
        selected["filter"] = key
        _show_list()

    def _show_list():
        cases = _filtered()
        preselected_case_id = None
        if page and isinstance(page.data, dict):
            preselected_case_id = page.data.pop("expert_selected_case_id", None)
        content_area.content = ft.Column(
            expand=True,
            spacing=12,
            controls=[
                page_header(
                    "Workspace case",
                    "Case la trung tam. Chat chi la mot tab trong chi tiet case.",
                    icon_name="RECORD_VOICE_OVER",
                ),
                info_strip(
                    "Dashboard khong giu inbox nua. Tu day chi loc, mo case va day workflow theo SLA.",
                    tone="neutral",
                ),
                ft.Row(spacing=8, scroll=ft.ScrollMode.AUTO, controls=[_chip(k, label) for k, label in _FILTER_OPTS]),
                ft.Container(
                    expand=True,
                    content=ft.ListView(
                        expand=True,
                        spacing=0,
                        controls=[_case_card(case) for case in cases]
                        if cases
                        else [ft.Text("Chua co case phu hop bo loc.", size=12, color=ft.Colors.WHITE54)],
                    ),
                ),
            ],
        )
        _update()
        if preselected_case_id:
            selected_case = next((case for case in cases if case["id"] == preselected_case_id), None)
            if selected_case:
                show_chat_view(content_area, selected_case, page, _show_list)

    _show_list()
    return content_area
