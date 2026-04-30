from __future__ import annotations

import flet as ft

from ui.components.user.expert.consulting_ai_panel import build_ai_result_panel
from ui.components.user.expert.raw_data_cards import STATUS_META, build_preview
from ui.theme import button_style, fmt_dt, glass_container, info_strip, status_badge, sticky_action_bar


def build_detail_panel(*, image: dict | None, behaviors: list[dict], history_controls: list[ft.Control], ai_result: dict | None, linked_case_text: str, selected_case: str | None, cases: list[dict], label_ref, symptom_ref, review_note_ref, request_more_ref, reject_ref, case_ref, on_scan_ai, on_apply_review, on_link_case) -> ft.Control:
    if not image:
        return info_strip("Chọn một ảnh trong danh sách để mở vùng duyệt.", tone="neutral")
    label, kind = STATUS_META.get(image.get("trang_thai"), ("Mở", "secondary"))
    behaviors_text = ", ".join(item.get("ten_hanh_vi", "") for item in behaviors) or "Chưa có nhãn bbox"
    return glass_container(
        expand=True,
        padding=18,
        radius=24,
        content=ft.Column(
            expand=True,
            spacing=14,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        ft.Column(expand=True, tight=True, spacing=5, controls=[ft.Text(image.get("file_name", "dataset-image"), size=17, weight=ft.FontWeight.W_700, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS), ft.Text(f"User #{image.get('id_user', '?')} • {fmt_dt(image.get('created_at', ''))}", size=10.5, color=ft.Colors.WHITE70)]),
                        status_badge(label, kind),
                    ],
                ),
                info_strip(linked_case_text or "Ảnh này chưa được gắn vào ca tư vấn nào.", tone="neutral", icon_name="LINK"),
                ft.Tabs(
                    expand=True,
                    animation_duration=180,
                    indicator_color=ft.Colors.with_opacity(0.92, "#6FB7FF"),
                    label_color=ft.Colors.WHITE,
                    unselected_label_color=ft.Colors.WHITE60,
                    tabs=[
                        ft.Tab(text="Xem ảnh", content=_preview_tab(image, behaviors_text)),
                        ft.Tab(text="Quét AI", content=_ai_tab(image, ai_result, on_scan_ai)),
                        ft.Tab(text="Xác minh", content=_verify_tab(image, selected_case, cases, label_ref, symptom_ref, review_note_ref, request_more_ref, reject_ref, case_ref, on_apply_review, on_link_case)),
                        ft.Tab(text="Lịch sử", content=_history_tab(image, history_controls)),
                    ],
                ),
            ],
        ),
    )


def _preview_tab(image: dict, behaviors_text: str) -> ft.Control:
    return ft.ListView(expand=True, spacing=12, controls=[build_preview(image.get("duong_dan", "")), _meta_block("Đường dẫn file", image.get("duong_dan", "")), _meta_block("Nhãn bbox", behaviors_text), _meta_block("Nhãn chuyên gia", image.get("expert_label", "") or "Chưa xác nhận")])


def _ai_tab(image: dict, ai_result: dict | None, on_scan_ai) -> ft.Control:
    return ft.ListView(expand=True, spacing=12, controls=[info_strip(f"Lần quét gần nhất: {fmt_dt(image.get('last_ai_scan_at', ''))}", tone="neutral", icon_name="BIOTECH"), ft.ElevatedButton("Quét AI", icon=ft.Icons.BIOTECH, style=button_style("primary"), on_click=lambda e, image_id=image["id_hinh_anh"]: on_scan_ai(image_id)), build_ai_result_panel(ai_result) if ai_result else info_strip("Chưa có kết quả AI cho ảnh này.", tone="warning")])


def _verify_tab(image: dict, selected_case: str | None, cases: list[dict], label_ref, symptom_ref, review_note_ref, request_more_ref, reject_ref, case_ref, on_apply_review, on_link_case) -> ft.Control:
    return ft.ListView(
        expand=True,
        spacing=12,
        controls=[
            _review_field(label_ref, "Nhãn cuối cùng của chuyên gia", image.get("expert_label", "")),
            _review_field(symptom_ref, "Ghi chú triệu chứng", image.get("symptom_notes", ""), 2, 4),
            _review_field(review_note_ref, "Ghi chú nội bộ", image.get("review_note", ""), 2, 4),
            _review_field(request_more_ref, "Lý do cần bổ sung dữ liệu", image.get("request_more_reason", ""), 2, 3),
            _review_field(reject_ref, "Lý do từ chối", image.get("reject_reason", ""), 2, 3),
            sticky_action_bar([ft.ElevatedButton("Duyệt", style=button_style("primary"), on_click=lambda e: on_apply_review("approve")), ft.ElevatedButton("Yêu cầu bổ sung", style=button_style("warning"), on_click=lambda e: on_apply_review("request_more")), ft.ElevatedButton("Từ chối", style=button_style("danger"), on_click=lambda e: on_apply_review("reject"))]),
            ft.Row(spacing=10, vertical_alignment=ft.CrossAxisAlignment.END, controls=[ft.Dropdown(ref=case_ref, label="Ca liên kết", value=selected_case, expand=True, bgcolor=ft.Colors.with_opacity(0.14, "#D9E5ED"), border_color=ft.Colors.with_opacity(0.26, "#D9E5ED"), focused_border_color="#4FC38A", options=[ft.dropdown.Option(str(item["id"]), f"Case-{item['id']:04d}") for item in cases]), ft.ElevatedButton("Liên kết ca", style=button_style("surface"), on_click=lambda e: on_link_case())]),
        ],
    )


def _history_tab(image: dict, history_controls: list[ft.Control]) -> ft.Control:
    return ft.ListView(expand=True, spacing=10, controls=[info_strip(f"Người duyệt: {image.get('reviewer_name') or 'Chưa có'} • {fmt_dt(image.get('reviewed_at', ''))}", tone="neutral", icon_name="FACT_CHECK"), *history_controls])


def _review_field(ref, label: str, value: str, min_lines: int = 1, max_lines: int = 1) -> ft.Control:
    return ft.TextField(ref=ref, label=label, value=value, min_lines=min_lines, max_lines=max_lines, border_radius=14, bgcolor=ft.Colors.with_opacity(0.14, "#D9E5ED"), border_color=ft.Colors.with_opacity(0.26, "#D9E5ED"), focused_border_color="#4FC38A", focused_border_width=2, label_style=ft.TextStyle(color="#D2DEE6", size=12), text_style=ft.TextStyle(color=ft.Colors.WHITE, size=13), content_padding=ft.padding.symmetric(horizontal=12, vertical=12))


def _meta_block(label: str, value: str) -> ft.Control:
    return ft.Container(padding=12, border_radius=16, bgcolor=ft.Colors.with_opacity(0.08, "#EAF3F8"), border=ft.border.all(1, ft.Colors.with_opacity(0.08, "#EAF3F8")), content=ft.Column(tight=True, spacing=4, controls=[ft.Text(label, size=10.5, color=ft.Colors.WHITE54), ft.Text(value or "Không có dữ liệu", size=11.5, color=ft.Colors.WHITE70)]))
