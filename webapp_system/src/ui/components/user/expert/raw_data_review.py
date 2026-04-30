from __future__ import annotations

import flet as ft

from bll.services import chat_service
from bll.services.auth_service import get_session_value
from bll.user.expert.kiem_duyet import (
    approve_image,
    assign_image_to_case,
    get_all_dataset_images,
    get_image_detail,
    get_review_summary,
    reject_image,
    request_more_data,
    store_ai_scan,
)
from bll.user.farmer.tu_van_ai import analyze_image_async
from ui.components.user.expert.raw_data_cards import (
    FILTERS,
    build_history_controls,
    build_metrics,
    build_queue_card,
)
from ui.components.user.expert.raw_data_detail import build_detail_panel
from ui.theme import glass_container, info_strip, page_header


def _safe_update(page: ft.Page | None) -> None:
    try:
        if page:
            page.update()
    except Exception:
        pass


def build_raw_data_review(page: ft.Page | None = None):
    expert_id = int(get_session_value(page, "user_id", 0) or 0)
    reviewer_name = (
        get_session_value(page, "full_name", "")
        or get_session_value(page, "username", "")
        or f"Expert #{expert_id or '?'}"
    )
    chat_service.ensure_demo_data(expert_id)
    state = {"filters": set(), "query": "", "selected_id": None, "mobile_view": "queue"}
    label_ref = ft.Ref[ft.TextField]()
    symptom_ref = ft.Ref[ft.TextField]()
    review_note_ref = ft.Ref[ft.TextField]()
    request_more_ref = ft.Ref[ft.TextField]()
    reject_ref = ft.Ref[ft.TextField]()
    case_ref = ft.Ref[ft.Dropdown]()
    root = ft.Container(expand=True)

    def _is_mobile() -> bool:
        width = getattr(page, "width", 0) or 0
        return 0 < width <= 900

    def _show_message(message: str, color: str):
        if page:
            page.snack_bar = ft.SnackBar(content=ft.Text(message, color=color))
            page.snack_bar.open = True
        _safe_update(page)

    def _active_filters() -> list[str]:
        return sorted(key for key in state["filters"] if key != "all")

    def _filter_text() -> str:
        labels = {key: label for key, label in FILTERS}
        active = _active_filters()
        if not active:
            return "Tất cả trạng thái"
        if len(active) == 1:
            return labels.get(active[0], "Bộ lọc")
        return f"Đã chọn {len(active)} trạng thái"

    def _images() -> list[dict]:
        query = state["query"].strip().lower()
        selected = set(_active_filters())
        images = sorted(
            get_all_dataset_images(),
            key=lambda item: item.get("created_at", ""),
            reverse=True,
        )
        filtered = []
        for item in images:
            if selected and item.get("trang_thai") not in selected:
                continue
            searchable = " ".join(
                str(item.get(key, ""))
                for key in (
                    "file_name",
                    "duong_dan",
                    "ai_primary_label",
                    "expert_label",
                    "linked_case_summary",
                )
            ).lower()
            if not query or query in searchable:
                filtered.append(item)
        return filtered

    def _selected_detail() -> dict | None:
        images = _images()
        if not images:
            state["selected_id"], state["mobile_view"] = None, "queue"
            return None
        if state["selected_id"] not in {item["id_hinh_anh"] for item in images}:
            state["selected_id"] = images[0]["id_hinh_anh"]
        return get_image_detail(int(state["selected_id"]))

    def _scan_ai(image_id: int):
        current = get_image_detail(image_id).get("image")
        if not current:
            return
        _show_message("Đang quét AI...", ft.Colors.BLUE_300)

        def _done(result: dict):
            ok, message = store_ai_scan(image_id, expert_id, result)
            _show_message(message, ft.Colors.GREEN_300 if ok else ft.Colors.RED_300)
            _render()

        analyze_image_async(
            current.get("duong_dan", ""),
            conf_thresh=0.25,
            on_result=_done,
            on_error=lambda message: _show_message(message, ft.Colors.RED_300),
        )

    def _apply_review(action: str):
        detail = _selected_detail()
        image = detail.get("image") if detail else None
        if not image:
            return
        common = {
            "reviewer_name": reviewer_name,
            "review_note": (review_note_ref.current.value or "").strip()
            if review_note_ref.current
            else "",
        }
        if action == "approve":
            ok, message = approve_image(
                image["id_hinh_anh"],
                expert_id,
                expert_label=(label_ref.current.value or "").strip()
                if label_ref.current
                else "",
                symptom_notes=(symptom_ref.current.value or "").strip()
                if symptom_ref.current
                else "",
                **common,
            )
        elif action == "reject":
            ok, message = reject_image(
                image["id_hinh_anh"],
                expert_id,
                reject_reason=(reject_ref.current.value or "").strip()
                if reject_ref.current
                else "",
                **common,
            )
        else:
            ok, message = request_more_data(
                image["id_hinh_anh"],
                expert_id,
                request_reason=(request_more_ref.current.value or "").strip()
                if request_more_ref.current
                else "",
                **common,
            )
        _show_message(message, ft.Colors.GREEN_300 if ok else ft.Colors.RED_300)
        _render()

    def _link_case():
        detail = _selected_detail()
        image = detail.get("image") if detail else None
        if not image or not case_ref.current:
            return
        raw = case_ref.current.value or ""
        case_id = int(raw) if raw else None
        case = next(
            (
                item
                for item in chat_service.list_conversations_for_expert(expert_id)
                if item["id"] == case_id
            ),
            None,
        )
        ok, message = assign_image_to_case(
            image["id_hinh_anh"],
            expert_id,
            case_id=case_id,
            case_summary=case.get("summary", "") if case else "",
        )
        _show_message(message, ft.Colors.GREEN_300 if ok else ft.Colors.RED_300)
        _render()

    def _select(image_id: int):
        state["selected_id"] = image_id
        if _is_mobile():
            state["mobile_view"] = "detail"
        _render()

    def _open_filter_dialog(_=None):
        if not page:
            return
        refs = {}
        checks = []
        for key, label in FILTERS:
            if key == "all":
                continue
            refs[key] = ft.Ref[ft.Checkbox]()
            checks.append(
                ft.Checkbox(
                    ref=refs[key],
                    label=label,
                    value=key in state["filters"],
                    active_color="#4FC38A",
                )
            )

        def _apply(_):
            state["filters"] = {
                key for key, ref in refs.items() if ref.current and ref.current.value
            }
            page.close(dialog)
            _render()

        def _clear(_):
            state["filters"] = set()
            page.close(dialog)
            _render()

        dialog = ft.AlertDialog(
            modal=True,
            bgcolor="#182833",
            title=ft.Text(
                "Lọc trạng thái",
                color=ft.Colors.WHITE,
                weight=ft.FontWeight.W_700,
            ),
            content=ft.Container(
                width=320,
                content=ft.Column(tight=True, spacing=6, controls=checks),
            ),
            actions=[
                ft.TextButton("Bỏ lọc", on_click=_clear),
                ft.TextButton("Áp dụng", on_click=_apply),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dialog)

    def _search_and_filters() -> ft.Control:
        return ft.Column(
            spacing=10,
            controls=[
                ft.Row(
                    spacing=10,
                    controls=[
                        ft.Container(
                            expand=True,
                            content=ft.TextField(
                                label="Tìm theo ảnh / nhãn AI / ca liên kết",
                                value=state["query"],
                                on_change=lambda e: (
                                    state.__setitem__("query", e.control.value),
                                    state.__setitem__("mobile_view", "queue"),
                                    _render(),
                                ),
                                prefix_icon=ft.Icons.SEARCH,
                                border_radius=18,
                                bgcolor=ft.Colors.with_opacity(0.12, "#D9E5ED"),
                                border_color=ft.Colors.with_opacity(
                                    0.18, "#D9E5ED"
                                ),
                                focused_border_color="#4FC38A",
                                focused_border_width=2,
                                label_style=ft.TextStyle(
                                    color="#D2DEE6", size=12
                                ),
                                text_style=ft.TextStyle(
                                    color=ft.Colors.WHITE, size=13
                                ),
                                content_padding=ft.padding.symmetric(
                                    horizontal=14, vertical=14
                                ),
                            ),
                        ),
                        ft.Container(
                            width=52,
                            height=52,
                            border_radius=16,
                            bgcolor=ft.Colors.with_opacity(0.10, "#D9E5ED"),
                            border=ft.border.all(
                                1, ft.Colors.with_opacity(0.14, "#D9E5ED")
                            ),
                            content=ft.IconButton(
                                icon=ft.Icons.FILTER_ALT_OUTLINED,
                                icon_color=ft.Colors.WHITE70,
                                on_click=_open_filter_dialog,
                            ),
                        ),
                    ],
                ),
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    border_radius=14,
                    bgcolor=ft.Colors.with_opacity(0.08, "#D9E5ED"),
                    border=ft.border.all(
                        1, ft.Colors.with_opacity(0.10, "#D9E5ED")
                    ),
                    content=ft.Row(
                        spacing=8,
                        controls=[
                            ft.Icon(ft.Icons.TUNE, size=16, color=ft.Colors.WHITE60),
                            ft.Text(
                                _filter_text(),
                                size=11,
                                color=ft.Colors.WHITE70,
                            ),
                        ],
                    ),
                ),
            ],
        )

    def _queue_section(queue_controls: list[ft.Control], queue_count: int) -> ft.Control:
        return glass_container(
            padding=18,
            radius=24,
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Column(
                        tight=True,
                        spacing=3,
                        controls=[
                            ft.Text(
                                "Hàng chờ duyệt",
                                size=16,
                                weight=ft.FontWeight.W_700,
                            ),
                            ft.Text(
                                f"{queue_count} mục đang chờ lọc và xác minh.",
                                size=10.5,
                                color=ft.Colors.WHITE60,
                            ),
                        ],
                    ),
                    *queue_controls,
                ],
            ),
        )

    def _mobile_title(title: str) -> ft.Control:
        return ft.Text(
            title,
            size=24,
            weight=ft.FontWeight.W_700,
            color=ft.Colors.WHITE,
        )

    def _render():
        summary, queue, detail = get_review_summary(), _images(), _selected_detail()
        image = detail.get("image") if detail else None
        queue_controls = [
            build_queue_card(item, state["selected_id"], _select) for item in queue
        ] or [info_strip("Không có ảnh nào khớp bộ lọc và từ khóa hiện tại.", tone="neutral")]
        detail_panel = build_detail_panel(
            image=image,
            behaviors=detail.get("behaviors", []) if detail else [],
            history_controls=build_history_controls(
                detail.get("history", []) if detail else []
            ),
            ai_result=image.get("ai_result") if image else None,
            linked_case_text=image.get("linked_case_summary", "") if image else "",
            selected_case=str(image.get("linked_case_id"))
            if image and image.get("linked_case_id")
            else None,
            cases=chat_service.list_conversations_for_expert(expert_id),
            label_ref=label_ref,
            symptom_ref=symptom_ref,
            review_note_ref=review_note_ref,
            request_more_ref=request_more_ref,
            reject_ref=reject_ref,
            case_ref=case_ref,
            on_scan_ai=_scan_ai,
            on_apply_review=_apply_review,
            on_link_case=_link_case,
        )
        mobile = _is_mobile()
        actions = (
            [
                ft.TextButton(
                    "Danh sách",
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda e: (
                        state.__setitem__("mobile_view", "queue"),
                        _render(),
                    ),
                )
            ]
            if mobile and state["mobile_view"] == "detail"
            else []
        )
        if mobile and state["mobile_view"] == "queue":
            body = ft.ListView(
                expand=True,
                spacing=14,
                padding=ft.padding.only(bottom=8),
                controls=[
                    _mobile_title("Xác thực dữ liệu"),
                    build_metrics(summary, compact=True),
                    _search_and_filters(),
                    _queue_section(queue_controls, len(queue)),
                ],
            )
        elif mobile:
            body = ft.Column(
                expand=True,
                spacing=12,
                controls=[
                    _mobile_title("Xác thực dữ liệu"),
                    ft.Row(controls=actions) if actions else ft.Container(),
                    ft.Container(expand=True, content=detail_panel),
                ],
            )
        else:
            body = ft.Column(
                expand=True,
                spacing=14,
                controls=[
                    page_header(
                        "Không gian duyệt dữ liệu",
                        "Tìm kiếm, phân loại, quét AI, xác minh chuyên gia và liên kết ca xử lý.",
                        icon_name="DATA_OBJECT",
                    ),
                    build_metrics(summary),
                    _search_and_filters(),
                    ft.ResponsiveRow(
                        columns=12,
                        controls=[
                            ft.Column(
                                col={"xs": 12, "lg": 4},
                                controls=[
                                    ft.Container(
                                        height=560,
                                        content=ft.ListView(
                                            expand=True,
                                            spacing=14,
                                            controls=[
                                                _queue_section(
                                                    queue_controls, len(queue)
                                                )
                                            ],
                                        ),
                                    )
                                ],
                            ),
                            ft.Column(
                                col={"xs": 12, "lg": 8},
                                controls=[
                                    ft.Container(height=560, content=detail_panel)
                                ],
                            ),
                        ],
                    ),
                ],
            )
        root.content = ft.Container(expand=True, content=body)
        _safe_update(page)

    _render()
    return root
