from __future__ import annotations

import flet as ft

from bll.services import chat_service
from bll.user.expert.kiem_duyet import get_case_images
from bll.user.farmer.tu_van_ai import analyze_image_async
from ui.components.user.expert.consulting_ai_panel import build_ai_result_panel, build_chat_bubble
from ui.components.user.expert.consulting_chat_tabs import build_ai_tab, build_chat_tab, build_data_tab, build_overview_tab
from ui.components.user.expert.consulting_chat_widgets import STATUS_META, TEAL, build_history_item
from ui.theme import button_style, glass_container, info_strip, severity_badge, status_badge, sticky_action_bar


def show_chat_view(content_area: ft.Container, convo: dict, page: ft.Page | None, on_back) -> None:
    convo_id = convo["id"]
    chat_service.mark_read_expert(convo_id)
    chat_list_ref = ft.Ref[ft.ListView]()
    history_ref = ft.Ref[ft.Column]()
    notes_ref = ft.Ref[ft.Column]()
    input_ref = ft.Ref[ft.TextField]()
    note_ref = ft.Ref[ft.TextField]()
    waiting_ref = ft.Ref[ft.TextField]()
    conclusion_ref = ft.Ref[ft.TextField]()
    context_header = ft.Row(spacing=6)

    def current_case() -> dict:
        return chat_service.get_conversation(convo_id) or convo

    def safe_update():
        if page:
            try:
                page.update()
            except Exception:
                pass

    def refresh_context():
        current = current_case()
        label, kind = STATUS_META.get(current.get("status"), ("Mo", "secondary"))
        owner = current.get("owner_name") or ("Expert #{}".format(current["claimed_by"]) if current.get("claimed_by") else "Unassigned")
        context_header.controls = [
            severity_badge(current.get("severity", "medium")),
            status_badge(label, kind),
            ft.Text(current.get("cow_id", "—"), size=10, color=ft.Colors.WHITE54),
            ft.Text(owner, size=10, color=ft.Colors.WHITE54),
        ]
        safe_update()

    def refresh_notes():
        current = current_case()
        notes = current.get("internal_notes", [])[-4:]
        if notes_ref.current:
            notes_ref.current.controls = [
                build_history_item(note.get("text", ""), note.get("time", ""), ft.Icons.STICKY_NOTE_2_OUTLINED)
                for note in notes
            ] or [ft.Text("Chua co ghi chu noi bo.", size=11, color=ft.Colors.WHITE38)]
            safe_update()

    def refresh_history():
        current = current_case()
        items = [
            build_history_item(
                f"{msg.get('sender', 'user').title()}: {msg.get('text') or '[Anh]'}",
                msg.get("time", ""),
                ft.Icons.CHAT_BUBBLE_OUTLINE if msg.get("sender") == "farmer" else ft.Icons.SUPPORT_AGENT,
            )
            for msg in current.get("messages", [])[-8:]
        ]
        items.extend(
            build_history_item(note.get("text", ""), note.get("time", ""), ft.Icons.EVENT_NOTE)
            for note in current.get("internal_notes", [])[-4:]
        )
        if current.get("closed_at"):
            items.append(build_history_item("Case closed", current.get("closed_at", ""), ft.Icons.CHECK_CIRCLE))
        if history_ref.current:
            history_ref.current.controls = items or [ft.Text("Chua co lich su.", size=11, color=ft.Colors.WHITE38)]
            safe_update()

    def sync_chat_messages():
        current = current_case()
        if chat_list_ref.current:
            chat_list_ref.current.controls = [build_chat_bubble(message, on_analyze) for message in current["messages"]]
            safe_update()

    def log_note(text: str):
        if text.strip():
            chat_service.add_internal_note(convo_id, text)
            refresh_notes()
            refresh_history()

    def claim_case(e=None):
        current = current_case()
        if current.get("claimed_by"):
            return
        chat_service.update_case(convo_id, claimed_by=current.get("expert_id"), status="claimed")
        log_note("Da nhan ownership cho case.")
        refresh_context()

    def request_data(e=None):
        current = current_case()
        waiting_reason = (waiting_ref.current.value or "").strip() if waiting_ref.current else ""
        waiting_reason = waiting_reason or "Can them anh can canh va mo ta trieu chung."
        chat_service.send_message(convo_id, "expert", text=f"Vui long gui them du lieu: {waiting_reason}")
        chat_service.update_case(convo_id, status="waiting_farmer", claimed_by=current.get("expert_id"), waiting_reason=waiting_reason)
        log_note(f"Da yeu cau them du lieu. Reason: {waiting_reason}")
        sync_chat_messages()
        refresh_context()
        refresh_history()

    def save_conclusion(e=None):
        current = current_case()
        final_conclusion = (conclusion_ref.current.value or "").strip() if conclusion_ref.current else ""
        final_conclusion = final_conclusion or "Da co ket luan so bo. Theo doi them va cap nhat neu trieu chung thay doi."
        chat_service.send_message(convo_id, "expert", text=final_conclusion)
        chat_service.update_case(convo_id, status="under_review", claimed_by=current.get("expert_id"), final_conclusion=final_conclusion)
        log_note("Da cap nhat ket luan case.")
        sync_chat_messages()
        refresh_context()
        refresh_history()

    def escalate_case(e=None):
        chat_service.update_case(convo_id, status="escalated")
        log_note("Da escalate case.")
        refresh_context()
        refresh_history()

    def close_case(e=None):
        current = current_case()
        chat_service.update_case(
            convo_id,
            status="closed",
            claimed_by=current.get("expert_id"),
            final_conclusion=(conclusion_ref.current.value or "").strip() if conclusion_ref.current else current.get("final_conclusion", ""),
        )
        log_note("Da dong case.")
        refresh_context()
        refresh_history()

    def add_note(e=None):
        if not note_ref.current:
            return
        text = (note_ref.current.value or "").strip()
        if text:
            note_ref.current.value = ""
            safe_update()
            log_note(text)

    def on_analyze(img_path: str, result_ctr: ft.Container):
        result_ctr.content = ft.Row(
            spacing=6,
            controls=[ft.ProgressRing(width=18, height=18, stroke_width=2), ft.Text("Dang phan tich...", size=11, color=ft.Colors.WHITE54)],
        )
        result_ctr.visible = True
        safe_update()

        def on_result(result: dict):
            result_ctr.content = build_ai_result_panel(result)
            safe_update()

        def on_error(message: str):
            result_ctr.content = ft.Text(message, color=ft.Colors.RED_300, size=11)
            safe_update()

        analyze_image_async(img_path, conf_thresh=0.25, on_result=on_result, on_error=on_error)

    def send_text(e=None):
        if not input_ref.current:
            return
        text = (input_ref.current.value or "").strip()
        if not text:
            return
        current = current_case()
        chat_service.send_message(convo_id, "expert", text=text)
        chat_service.update_case(convo_id, status="under_review", claimed_by=current.get("expert_id"))
        input_ref.current.value = ""
        sync_chat_messages()
        refresh_context()
        refresh_history()

    def on_pick_img(event: ft.FilePickerResultEvent):
        if not event.files:
            return
        chat_service.send_message(convo_id, "expert", img_src=event.files[0].path)
        sync_chat_messages()
        refresh_history()

    picker = ft.FilePicker(on_result=on_pick_img)
    if page and picker not in page.overlay:
        page.overlay.append(picker)
        page.update()

    current = current_case()
    linked_images = get_case_images(convo_id)
    linked_ai = [item for item in linked_images if item.get("ai_result")]
    inline_images = [msg for msg in current.get("messages", []) if msg.get("img_src")]

    header = ft.Container(
        padding=ft.padding.symmetric(horizontal=8, vertical=10),
        bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.BLACK),
        content=ft.Row(
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.IconButton(icon=ft.Icons.ARROW_BACK_IOS_NEW, icon_color=ft.Colors.WHITE70, icon_size=18, on_click=lambda e: on_back()),
                ft.Column(
                    tight=True,
                    spacing=2,
                    expand=True,
                    controls=[
                        ft.Text(current.get("farmer_name", "?"), size=14, weight=ft.FontWeight.W_700, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(f"{current.get('farm_name', '—')}  •  {current.get('case_type', 'Consultation')}", size=10, color=ft.Colors.WHITE60),
                    ],
                ),
            ],
        ),
    )

    content_area.content = ft.Column(
        expand=True,
        spacing=10,
        controls=[
            header,
            glass_container(
                padding=12,
                radius=16,
                content=ft.Column(
                    tight=True,
                    spacing=8,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[ft.Text(f"Case-{current['id']:04d}", size=14, weight=ft.FontWeight.W_700), context_header],
                        ),
                    ],
                ),
            ),
            ft.Container(
                expand=True,
                content=ft.Tabs(
                    selected_index=0,
                    animation_duration=200,
                    expand=True,
                    divider_color=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
                    label_color=ft.Colors.WHITE,
                    unselected_label_color=ft.Colors.WHITE60,
                    indicator_color=TEAL,
                    tabs=[
                        ft.Tab(text="Tổng quan", content=build_overview_tab(current, waiting_ref, conclusion_ref, notes_ref, note_ref, add_note)),
                        ft.Tab(text="Dữ liệu", content=build_data_tab(linked_images, inline_images)),
                        ft.Tab(text="AI", content=build_ai_tab(linked_ai)),
                        ft.Tab(text="Trao đổi", content=build_chat_tab(current, chat_list_ref, input_ref, picker, on_analyze, send_text, page)),
                        ft.Tab(text="Lịch sử", content=ft.Column(ref=history_ref, spacing=8, controls=[])),
                    ],
                ),
            ),
            sticky_action_bar(
                [
                    ft.ElevatedButton("Nhan case", icon=ft.Icons.ASSIGNMENT_IND, style=button_style("surface"), on_click=claim_case),
                    ft.ElevatedButton("Yeu cau data", icon=ft.Icons.DATA_OBJECT, style=button_style("warning"), on_click=request_data),
                    ft.ElevatedButton("Luu ket luan", icon=ft.Icons.FACT_CHECK, style=button_style("primary"), on_click=save_conclusion),
                    ft.ElevatedButton("Escalate", icon=ft.Icons.PRIORITY_HIGH, style=button_style("danger"), on_click=escalate_case),
                    ft.ElevatedButton("Dong case", icon=ft.Icons.CHECK_CIRCLE, style=button_style("surface"), on_click=close_case),
                ]
            ),
        ],
    )
    refresh_context()
    refresh_notes()
    refresh_history()
    sync_chat_messages()
    safe_update()
