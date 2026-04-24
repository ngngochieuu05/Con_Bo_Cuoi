from __future__ import annotations

import flet as ft

from ui.components.user.expert.consulting_ai_panel import build_ai_result_panel, build_chat_bubble
from ui.components.user.expert.consulting_chat_widgets import build_data_card, build_history_item, build_quick_reply_row, TEAL
from ui.theme import collapsible_section, info_strip


def build_overview_tab(current: dict, waiting_ref, conclusion_ref, notes_ref, note_ref, on_add_note) -> ft.Control:
    return ft.Column(
        spacing=10,
        controls=[
            info_strip(current.get("summary", "Chua co tom tat case."), tone="neutral", icon_name="DESCRIPTION_OUTLINED"),
            ft.TextField(ref=waiting_ref, label="Waiting reason / missing data request", value=current.get("waiting_reason", ""), min_lines=1, max_lines=3, border_radius=14, bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE)),
            ft.TextField(ref=conclusion_ref, label="Final conclusion", value=current.get("final_conclusion", ""), min_lines=2, max_lines=4, border_radius=14, bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE)),
            collapsible_section(
                "Owner and internal notes",
                ft.Column(
                    spacing=8,
                    controls=[
                        ft.Row(spacing=10, controls=[ft.Text(f"Farmer: {current.get('farmer_name', '—')}", size=11, color=ft.Colors.WHITE70), ft.Text(f"Farm: {current.get('farm_name', '—')}", size=11, color=ft.Colors.WHITE70)]),
                        ft.Column(ref=notes_ref, spacing=6, controls=[]),
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.TextField(ref=note_ref, hint_text="Them ghi chu noi bo...", expand=True, border_radius=12, bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE), border_color=ft.Colors.with_opacity(0.20, ft.Colors.WHITE), focused_border_color=TEAL, hint_style=ft.TextStyle(color=ft.Colors.WHITE38, size=12), text_style=ft.TextStyle(color=ft.Colors.WHITE, size=12), cursor_color=ft.Colors.WHITE, content_padding=ft.padding.symmetric(horizontal=12, vertical=10), on_submit=on_add_note),
                                ft.IconButton(icon=ft.Icons.ADD_COMMENT, icon_color=TEAL, on_click=on_add_note),
                            ],
                        ),
                    ],
                ),
                note="Collapse metadata and notes when not needed.",
                initially_open=False,
            ),
        ],
    )


def build_data_tab(linked_images: list[dict], inline_images: list[dict]) -> ft.Control:
    return ft.Column(
        spacing=10,
        controls=[
            info_strip(f"{len(linked_images)} dataset item(s) linked to this case. Chat images stay in the discussion tab.", tone="neutral", icon_name="DATA_OBJECT"),
            *([build_data_card(item) for item in linked_images] or [ft.Text("Chua co dataset item nao duoc link vao case nay.", size=11, color=ft.Colors.WHITE38)]),
            collapsible_section(
                "Images sent in chat",
                ft.Column(
                    spacing=8,
                    controls=[build_history_item(msg.get("img_src", ""), "Anh da gui trong hoi thoai", ft.Icons.IMAGE_OUTLINED) for msg in inline_images] or [ft.Text("Chua co anh nao trong chat.", size=11, color=ft.Colors.WHITE38)],
                ),
                initially_open=False,
            ),
        ],
    )


def build_ai_tab(linked_ai: list[dict]) -> ft.Control:
    cards = [
        ft.Container(
            padding=12,
            border_radius=16,
            bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
            content=ft.Column(
                spacing=8,
                tight=True,
                controls=[
                    ft.Row(controls=[ft.Text(item.get("file_name", "dataset-image"), size=11, weight=ft.FontWeight.W_700, expand=True), ft.Text(item.get("ai_model_name", "AI"), size=10, color=ft.Colors.WHITE54)]),
                    build_ai_result_panel(item.get("ai_result", {})),
                ],
            ),
        )
        for item in linked_ai
    ] or [ft.Text("Chua co AI result nao tu dataset duoc link.", size=11, color=ft.Colors.WHITE38)]
    return ft.Column(
        spacing=10,
        controls=[
            info_strip("AI summary now comes from linked dataset reviews. Inline chat image analysis still works in the discussion tab.", tone="warning"),
            *cards,
        ],
    )


def build_chat_tab(current: dict, chat_list_ref, input_ref, picker, on_analyze, on_send_text, page: ft.Page | None) -> ft.Control:
    return ft.Column(
        spacing=10,
        controls=[
            collapsible_section("Tra loi nhanh", build_quick_reply_row(input_ref, page), note="Only expand when needed.", initially_open=False),
            ft.Container(
                height=320,
                content=ft.ListView(ref=chat_list_ref, expand=True, spacing=8, padding=ft.padding.symmetric(horizontal=4, vertical=4), controls=[build_chat_bubble(message, on_analyze) for message in current["messages"]], auto_scroll=True),
            ),
            ft.Row(
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.END,
                controls=[
                    ft.IconButton(icon=ft.Icons.IMAGE_OUTLINED, icon_color=TEAL, tooltip="Gui anh", on_click=lambda e: picker.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.IMAGE)),
                    ft.TextField(ref=input_ref, hint_text="Tra loi farmer...", expand=True, min_lines=1, max_lines=4, border_radius=18, bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE), border_color=ft.Colors.with_opacity(0.20, ft.Colors.WHITE), focused_border_color=TEAL, hint_style=ft.TextStyle(color=ft.Colors.WHITE38, size=12), text_style=ft.TextStyle(color=ft.Colors.WHITE, size=12), cursor_color=ft.Colors.WHITE, content_padding=ft.padding.symmetric(horizontal=12, vertical=10), on_submit=on_send_text),
                    ft.IconButton(icon=ft.Icons.SEND_ROUNDED, icon_color=TEAL, on_click=on_send_text),
                ],
            ),
        ],
    )
