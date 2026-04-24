from __future__ import annotations

import datetime

import flet as ft

from bll.services import chat_service
from bll.services.auth_service import get_session_value
from ui.components.user.expert.consulting_chat import show_chat_view
from ui.theme import SECONDARY, SUCCESS, WARNING, glass_container, info_strip, severity_badge, status_badge

_FILTER_OPTS = [("all", "Tất cả"), ("urgent", "Khẩn"), ("mine", "Case tôi"), ("waiting", "Chờ farmer"), ("new", "Mới"), ("closed", "Đã đóng")]
_STATUS_META = {
    "new": ("Mới", "warning"),
    "claimed": ("Đã nhận", "secondary"),
    "under_review": ("Đang xử lý", "secondary"),
    "waiting_farmer": ("Chờ farmer", "neutral"),
    "escalated": ("Escalate", "danger"),
    "closed": ("Đóng", "success"),
}
_FILTER_ACCENT = {"all": SECONDARY, "urgent": WARNING, "mine": "#73D79A", "waiting": "#AAB7C4", "new": WARNING, "closed": SUCCESS}


def _fmt_short(iso_str: str) -> str:
    if not iso_str:
        return "—"
    try:
        return datetime.datetime.fromisoformat(iso_str[:19]).strftime("%d/%m %H:%M")
    except Exception:
        return iso_str[:16].replace("T", " ")


def _is_overdue(iso_str: str) -> bool:
    try:
        return datetime.datetime.fromisoformat(iso_str[:19]) < datetime.datetime.now()
    except Exception:
        return False


def _section_title() -> ft.Control:
    return ft.Column(
        tight=True,
        spacing=4,
        controls=[
            ft.Text("Tư vấn", size=24, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE),
            ft.Text("Theo dõi ca tư vấn, ưu tiên xử lý và mở nhanh từng cuộc trao đổi.", size=11, color=ft.Colors.WHITE60),
        ],
    )


def _unread_badge(unread: int) -> ft.Control:
    if unread <= 0:
        return ft.Text("Đã đọc", size=10, color=ft.Colors.WHITE60)
    label = "99+" if unread > 99 else str(unread)
    return ft.Container(
        width=22 if unread < 10 else 28,
        height=22,
        border_radius=999,
        bgcolor="#FF6B6B",
        alignment=ft.alignment.center,
        content=ft.Text(
            label,
            size=9,
            weight=ft.FontWeight.W_700,
            color=ft.Colors.WHITE,
        ),
    )


def build_consulting_review(page: ft.Page | None = None, on_navigate=None):  # noqa: ARG001
    expert_id = int(get_session_value(page, "user_id", 0) or 0)
    chat_service.ensure_demo_data(expert_id)
    content_area = ft.Container(expand=True)
    state = {"filter": "all", "query": ""}

    def _is_mobile() -> bool:
        width = getattr(page, "width", 0) or 0
        return 0 < width <= 900

    def _safe_update():
        if page:
            try:
                page.update()
            except Exception:
                pass

    def _all_cases() -> list[dict]:
        cases = chat_service.list_conversations_for_expert(expert_id)
        query = state["query"].strip().lower()
        filtered = []
        for case in cases:
            if state["filter"] == "urgent" and case.get("severity") not in ("critical", "high") and case.get("status") != "escalated":
                continue
            if state["filter"] == "mine" and case.get("claimed_by") != expert_id:
                continue
            if state["filter"] == "waiting" and case.get("status") != "waiting_farmer":
                continue
            if state["filter"] == "new" and case.get("status") != "new":
                continue
            if state["filter"] == "closed" and case.get("status") != "closed":
                continue
            haystack = " ".join([str(case.get("farmer_name", "")), str(case.get("farm_name", "")), str(case.get("cow_id", "")), str(case.get("summary", "")), str(case.get("case_type", ""))]).lower()
            if query and query not in haystack:
                continue
            filtered.append(case)
        return filtered

    def _chip(key: str, label: str) -> ft.Control:
        active = state["filter"] == key
        accent = _FILTER_ACCENT.get(key, SECONDARY)
        return ft.Container(
            ink=True,
            on_click=lambda e, value=key: _set_filter(value),
            padding=ft.padding.symmetric(horizontal=14, vertical=8),
            border_radius=999,
            bgcolor=ft.Colors.with_opacity(0.22, accent) if active else ft.Colors.with_opacity(0.08, "#EAF3F8"),
            border=ft.border.all(1, ft.Colors.with_opacity(0.44, accent) if active else ft.Colors.with_opacity(0.12, "#EAF3F8")),
            content=ft.Text(label, size=11, color=ft.Colors.WHITE, weight=ft.FontWeight.W_600),
        )

    def _metric_tile(title: str, value: str, icon, accent: str, compact: bool = False) -> ft.Control:
        return glass_container(
            expand=1,
            padding=12 if compact else 16,
            radius=18 if compact else 20,
            content=ft.Column(
                tight=True,
                spacing=6 if compact else 8,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                        controls=[
                            ft.Text(title, size=10 if compact else 11, color=ft.Colors.WHITE70, expand=True, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Container(width=24 if compact else 28, height=24 if compact else 28, border_radius=8 if compact else 9, bgcolor=ft.Colors.with_opacity(0.18, accent), alignment=ft.alignment.center, content=ft.Icon(icon, size=13 if compact else 15, color=accent)),
                        ],
                    ),
                    ft.Text(value, size=18 if compact else 24, weight=ft.FontWeight.W_700),
                ],
            ),
        )

    def _case_card(case: dict) -> ft.Control:
        status_label, status_kind = _STATUS_META.get(case.get("status"), ("Mở", "secondary"))
        unread = case.get("unread_expert", 0)
        overdue = _is_overdue(case.get("sla_due_at", "")) and case.get("status") != "closed"
        owner = case.get("owner_name") or (f"Expert #{case['claimed_by']}" if case.get("claimed_by") else "Chưa nhận")
        summary = case.get("summary", "Chưa có tóm tắt.")
        footer = case.get("waiting_reason") or case.get("final_conclusion") or "Mở workspace"
        return ft.Container(
            margin=ft.margin.only(bottom=12),
            padding=16,
            border_radius=22,
            bgcolor=ft.Colors.with_opacity(0.10, "#EAF3F8"),
            border=ft.border.all(1, ft.Colors.with_opacity(0.12, "#EAF3F8")),
            ink=True,
            on_click=lambda e, item=case: show_chat_view(content_area, item, page, _show_list),
            content=ft.Stack(
                controls=[
                    ft.Column(
                        tight=True,
                        spacing=10,
                        controls=[
                            ft.Row(
                                vertical_alignment=ft.CrossAxisAlignment.START,
                                controls=[
                                    ft.Text(f"Case-{case['id']:04d}", size=14, weight=ft.FontWeight.W_700, expand=True),
                                    severity_badge(case.get("severity", "medium")),
                                    status_badge(status_label, status_kind),
                                ],
                            ),
                            ft.Text(f"{case.get('farmer_name', '—')} • {case.get('farm_name', '—')} • {case.get('cow_id', '—')}", size=11, color=ft.Colors.WHITE70, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(summary, size=11, color=ft.Colors.WHITE60, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text(f"{case.get('case_type', 'Tư vấn bệnh')} • {owner}", size=10, color=ft.Colors.WHITE38, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                                    ft.Text(f"SLA {_fmt_short(case.get('sla_due_at', ''))}", size=10, color=ft.Colors.RED_300 if overdue else ft.Colors.WHITE60),
                                ],
                            ),
                            ft.Text(footer, size=10, color=ft.Colors.WHITE54, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                    ),
                    ft.Container(
                        right=-6,
                        top=-6,
                        content=_unread_badge(unread),
                    ),
                ],
            ),
        )

    def _set_filter(key: str):
        state["filter"] = key
        _show_list()

    def _summary_row(cases: list[dict]) -> ft.Control:
        compact = _is_mobile()
        return ft.Row(
            spacing=8 if compact else 10,
            controls=[
                _metric_tile("Case mới", str(sum(1 for item in cases if item.get("status") == "new")), ft.Icons.MARK_EMAIL_UNREAD_OUTLINED, WARNING, compact=compact),
                _metric_tile("Quá SLA", str(sum(1 for item in cases if _is_overdue(item.get("sla_due_at", "")) and item.get("status") != "closed")), ft.Icons.TIMER_OFF_OUTLINED, "#FF8B8B", compact=compact),
                _metric_tile("Chờ farmer", str(sum(1 for item in cases if item.get("status") == "waiting_farmer")), ft.Icons.HOURGLASS_TOP_ROUNDED, SECONDARY, compact=compact),
            ],
        )

    def _queue_section(cases: list[dict]) -> ft.Control:
        cards = [_case_card(case) for case in cases] if cases else [info_strip("Không có ca tư vấn nào khớp bộ lọc hiện tại.", tone="neutral")]
        return glass_container(
            expand=True,
            padding=18,
            radius=24,
            content=ft.Column(
                expand=True,
                spacing=12,
                controls=[
                    ft.Column(tight=True, spacing=3, controls=[ft.Text("Danh sách ca tư vấn", size=16, weight=ft.FontWeight.W_700), ft.Text(f"{len(cases)} case đang hiển thị trong hàng chờ xử lý.", size=10.5, color=ft.Colors.WHITE60)]),
                    ft.Container(expand=True, content=ft.ListView(expand=True, spacing=0, controls=cards)),
                ],
            ),
        )

    def _show_list():
        preselected_case_id = None
        if page and isinstance(page.data, dict):
            preloaded_filter = page.data.pop("expert_consulting_filter", None)
            if preloaded_filter in {key for key, _ in _FILTER_OPTS}:
                state["filter"] = preloaded_filter
            preselected_case_id = page.data.pop("expert_selected_case_id", None)
        all_cases = chat_service.list_conversations_for_expert(expert_id)
        cases = _all_cases()
        content_area.content = ft.Column(
            expand=True,
            spacing=14,
            controls=[
                _section_title(),
                _summary_row(all_cases),
                ft.TextField(
                    label="Tìm theo farmer / farm / bò / triệu chứng",
                    value=state["query"],
                    on_change=lambda e: (state.__setitem__("query", e.control.value), _show_list()),
                    prefix_icon=ft.Icons.SEARCH,
                    border_radius=18,
                    bgcolor=ft.Colors.with_opacity(0.12, "#D9E5ED"),
                    border_color=ft.Colors.with_opacity(0.18, "#D9E5ED"),
                    focused_border_color="#4FC38A",
                    focused_border_width=2,
                    label_style=ft.TextStyle(color="#D2DEE6", size=12),
                    text_style=ft.TextStyle(color=ft.Colors.WHITE, size=13),
                    content_padding=ft.padding.symmetric(horizontal=14, vertical=14),
                ),
                ft.Row(spacing=8, scroll=ft.ScrollMode.AUTO, controls=[_chip(k, label) for k, label in _FILTER_OPTS]),
                ft.Container(expand=True, content=_queue_section(cases)),
            ],
        )
        _safe_update()
        if preselected_case_id:
            selected_case = next((case for case in cases if case["id"] == preselected_case_id), None)
            if selected_case:
                show_chat_view(content_area, selected_case, page, _show_list)

    _show_list()
    return content_area
