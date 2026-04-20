from __future__ import annotations

import flet as ft

from bll.services import chat_service
from bll.user.farmer.tu_van_ai import analyze_image_async
from ui.components.user.expert.consulting_ai_panel import build_ai_result_panel, build_chat_bubble
from ui.theme import (
    button_style,
    collapsible_section,
    glass_container,
    info_strip,
    severity_badge,
    status_badge,
    sticky_action_bar,
)

_TEAL = ft.Colors.TEAL_300
_QUICK_REPLIES = ["Can them anh", "Theo doi 24h", "Can cach ly", "Chuyen thu y"]
_STATUS_META = {
    "new": ("Moi", "warning"),
    "claimed": ("Mo", "secondary"),
    "under_review": ("Xu ly", "secondary"),
    "waiting_farmer": ("Cho", "neutral"),
    "escalated": ("Khan", "danger"),
    "closed": ("Xong", "success"),
}


def _history_item(title: str, subtitle: str, icon) -> ft.Control:
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        border_radius=12,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        content=ft.Row(
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Icon(icon, size=16, color=_TEAL),
                ft.Column(
                    expand=True,
                    tight=True,
                    spacing=2,
                    controls=[
                        ft.Text(title, size=11, weight=ft.FontWeight.W_700),
                        ft.Text(subtitle, size=10, color=ft.Colors.WHITE54),
                    ],
                ),
            ],
        ),
    )


def _quick_reply_row(input_ref: ft.Ref, page) -> ft.Control:
    def _fill(text: str):
        if input_ref.current:
            input_ref.current.value = text
            if page:
                try:
                    page.update()
                except Exception:
                    pass

    return ft.Row(
        spacing=6,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.OutlinedButton(
                text=reply,
                style=ft.ButtonStyle(
                    color=_TEAL,
                    side=ft.BorderSide(1, ft.Colors.with_opacity(0.35, _TEAL)),
                    shape=ft.RoundedRectangleBorder(radius=14),
                    padding=ft.padding.symmetric(horizontal=10, vertical=4),
                    text_style=ft.TextStyle(size=11),
                ),
                on_click=lambda e, text=reply: _fill(text),
            )
            for reply in _QUICK_REPLIES
        ],
    )


def show_chat_view(content_area: ft.Container, convo: dict, page, on_back) -> None:
    chat_service.mark_read_expert(convo["id"])
    chat_list_ref = ft.Ref[ft.ListView]()
    history_ref = ft.Ref[ft.Column]()
    notes_ref = ft.Ref[ft.Column]()
    input_ref = ft.Ref[ft.TextField]()
    note_ref = ft.Ref[ft.TextField]()
    context_header = ft.Row(spacing=6)

    def _update():
        if page:
            try:
                page.update()
            except Exception:
                pass

    def _status_meta():
        return _STATUS_META.get(convo.get("status"), ("Mo", "secondary"))

    def _refresh_context():
        label, kind = _status_meta()
        context_header.controls = [
            severity_badge(convo.get("severity", "medium")),
            status_badge(label, kind),
            ft.Text(convo.get("cow_id", "—"), size=10, color=ft.Colors.WHITE54),
            ft.Text(convo.get("sla_due_at", "")[:16].replace("T", " "), size=10, color=ft.Colors.AMBER_200),
        ]
        _update()

    def _refresh_notes():
        notes = convo.get("internal_notes", [])[-4:]
        if notes_ref.current:
            notes_ref.current.controls = [
                _history_item(note.get("text", ""), note.get("time", ""), ft.Icons.STICKY_NOTE_2_OUTLINED)
                for note in notes
            ] or [ft.Text("Chua co ghi chu noi bo.", size=11, color=ft.Colors.WHITE38)]
            _update()

    def _refresh_history():
        items: list[ft.Control] = [
            _history_item(
                f"{msg.get('sender', 'user').title()}: {msg.get('text') or '[Anh]'}",
                msg.get("time", ""),
                ft.Icons.CHAT_BUBBLE_OUTLINE if msg.get("sender") == "farmer" else ft.Icons.SUPPORT_AGENT,
            )
            for msg in convo.get("messages", [])[-6:]
        ]
        items.extend(
            _history_item(note.get("text", ""), note.get("time", ""), ft.Icons.EVENT_NOTE)
            for note in convo.get("internal_notes", [])[-4:]
        )
        if history_ref.current:
            history_ref.current.controls = items or [ft.Text("Chua co lich su.", size=11, color=ft.Colors.WHITE38)]
            _update()

    def _log_note(text: str):
        chat_service.add_internal_note(convo["id"], text)
        _refresh_notes()
        _refresh_history()

    def _apply_status(status: str, note: str):
        updates = {"status": status}
        if status in ("claimed", "under_review"):
            updates["claimed_by"] = convo.get("expert_id")
        chat_service.update_case(convo["id"], **updates)
        convo.update(updates)
        _log_note(note)
        _refresh_context()

    def _request_data(e=None):
        chat_service.send_message(convo["id"], "expert", text="Vui long gui them anh/camera canh can de danh gia ro hon.")
        _apply_status("waiting_farmer", "Da yeu cau them du lieu")
        if chat_list_ref.current:
            chat_list_ref.current.controls.append(build_chat_bubble(convo["messages"][-1], _on_analyze))
            _update()

    def _send_conclusion(e=None):
        chat_service.send_message(convo["id"], "expert", text="Da co ket luan so bo. Neu thay doi trieu chung, vui long cap nhat ngay.")
        _apply_status("under_review", "Da gui ket luan so bo")
        if chat_list_ref.current:
            chat_list_ref.current.controls.append(build_chat_bubble(convo["messages"][-1], _on_analyze))
            _update()

    def _escalate(e=None):
        _apply_status("escalated", "Da escalate case")

    def _close_case(e=None):
        _apply_status("closed", "Da dong case")

    def _add_note(e=None):
        if not note_ref.current:
            return
        text = (note_ref.current.value or "").strip()
        if not text:
            return
        note_ref.current.value = ""
        _update()
        _log_note(text)

    def _on_analyze(img_path: str, result_ctr: ft.Container):
        result_ctr.content = ft.Row(
            spacing=6,
            controls=[
                ft.ProgressRing(width=18, height=18, stroke_width=2),
                ft.Text("Dang phan tich...", size=11, color=ft.Colors.WHITE54),
            ],
        )
        result_ctr.visible = True
        _update()

        def on_result(result):
            result_ctr.content = build_ai_result_panel(result)
            _update()

        def on_error(message):
            result_ctr.content = ft.Text(message, color=ft.Colors.RED_300, size=11)
            _update()

        analyze_image_async(img_path, conf_thresh=0.25, on_result=on_result, on_error=on_error)

    def _send_text(e=None):
        if not input_ref.current:
            return
        text = (input_ref.current.value or "").strip()
        if not text:
            return
        chat_service.send_message(convo["id"], "expert", text=text)
        convo["status"] = "under_review"
        input_ref.current.value = ""
        _update()
        if chat_list_ref.current:
            chat_list_ref.current.controls.append(build_chat_bubble(convo["messages"][-1], _on_analyze))
            _update()
        _refresh_context()
        _refresh_history()

    def _on_pick_img(event: ft.FilePickerResultEvent):
        if not event.files:
            return
        chat_service.send_message(convo["id"], "expert", img_src=event.files[0].path)
        if chat_list_ref.current:
            chat_list_ref.current.controls.append(build_chat_bubble(convo["messages"][-1], _on_analyze))
            _update()
        _refresh_history()

    picker = ft.FilePicker(on_result=_on_pick_img)
    if page and picker not in page.overlay:
        page.overlay.append(picker)
        page.update()

    data_items = [
        _history_item(msg.get("img_src", ""), "Anh da gui trong hoi thoai", ft.Icons.IMAGE_OUTLINED)
        for msg in convo.get("messages", [])
        if msg.get("img_src")
    ] or [ft.Text("Chua co anh/du lieu bo sung trong case nay.", size=11, color=ft.Colors.WHITE38)]

    overview_tab = ft.Column(
        spacing=10,
        controls=[
            info_strip(convo.get("summary", "Chua co tom tat case."), tone="neutral", icon_name="DESCRIPTION_OUTLINED"),
            collapsible_section(
                "Meta va ghi chu",
                ft.Column(
                    spacing=8,
                    controls=[
                        ft.Row(
                            spacing=10,
                            controls=[
                                ft.Text(f"Farmer: {convo.get('farmer_name', '—')}", size=11, color=ft.Colors.WHITE70),
                                ft.Text(f"Trang trai: {convo.get('farm_name', '—')}", size=11, color=ft.Colors.WHITE70),
                            ],
                        ),
                        ft.Column(ref=notes_ref, spacing=6, controls=[]),
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.TextField(
                                    ref=note_ref,
                                    hint_text="Them ghi chu noi bo...",
                                    expand=True,
                                    border_radius=12,
                                    bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
                                    border_color=ft.Colors.with_opacity(0.20, ft.Colors.WHITE),
                                    focused_border_color=_TEAL,
                                    hint_style=ft.TextStyle(color=ft.Colors.WHITE38, size=12),
                                    text_style=ft.TextStyle(color=ft.Colors.WHITE, size=12),
                                    cursor_color=ft.Colors.WHITE,
                                    content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
                                    on_submit=_add_note,
                                ),
                                ft.IconButton(icon=ft.Icons.ADD_COMMENT, icon_color=_TEAL, on_click=_add_note),
                            ],
                        ),
                    ],
                ),
                note="An bot metadata va note khoi luong lon",
                initially_open=False,
            ),
        ],
    )
    data_tab = ft.Column(spacing=10, controls=[*data_items])
    ai_tab = ft.Column(
        spacing=10,
        controls=[
            info_strip("Anh trong hoi thoai co the bam 'Phan tich AI' de sinh ket qua nhanh ngay trong case.", tone="warning"),
            collapsible_section(
                "Huong dan AI",
                ft.Column(
                    spacing=6,
                    controls=[
                        ft.Text("1. Xem anh trong tab Trao doi.", size=11, color=ft.Colors.WHITE70),
                        ft.Text("2. Bam Phan tich AI o bong chat co anh.", size=11, color=ft.Colors.WHITE70),
                        ft.Text("3. Kiem tra ket qua truoc khi gui ket luan cho farmer.", size=11, color=ft.Colors.WHITE70),
                    ],
                ),
                initially_open=True,
            ),
        ],
    )
    trao_doi_tab = ft.Column(
        spacing=10,
        controls=[
            collapsible_section("Tra loi nhanh", _quick_reply_row(input_ref, page), note="Chi mo khi can", initially_open=False),
            ft.Container(
                height=320,
                content=ft.ListView(
                    ref=chat_list_ref,
                    expand=True,
                    spacing=8,
                    padding=ft.padding.symmetric(horizontal=4, vertical=4),
                    controls=[build_chat_bubble(message, _on_analyze) for message in convo["messages"]],
                    auto_scroll=True,
                ),
            ),
            ft.Row(
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.END,
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.IMAGE_OUTLINED,
                        icon_color=_TEAL,
                        tooltip="Gui anh",
                        on_click=lambda e: picker.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.IMAGE),
                    ),
                    ft.TextField(
                        ref=input_ref,
                        hint_text="Tra loi farmer...",
                        expand=True,
                        min_lines=1,
                        max_lines=4,
                        border_radius=18,
                        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
                        border_color=ft.Colors.with_opacity(0.20, ft.Colors.WHITE),
                        focused_border_color=_TEAL,
                        hint_style=ft.TextStyle(color=ft.Colors.WHITE38, size=12),
                        text_style=ft.TextStyle(color=ft.Colors.WHITE, size=12),
                        cursor_color=ft.Colors.WHITE,
                        content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
                        on_submit=_send_text,
                    ),
                    ft.IconButton(icon=ft.Icons.SEND_ROUNDED, icon_color=_TEAL, on_click=_send_text),
                ],
            ),
        ],
    )
    history_tab = ft.Column(ref=history_ref, spacing=8, controls=[])

    header = ft.Container(
        padding=ft.padding.symmetric(horizontal=8, vertical=10),
        bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.BLACK),
        content=ft.Row(
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK_IOS_NEW,
                    icon_color=ft.Colors.WHITE70,
                    icon_size=18,
                    on_click=lambda e: on_back(),
                ),
                ft.Column(
                    tight=True,
                    spacing=2,
                    expand=True,
                    controls=[
                        ft.Text(convo.get("farmer_name", "?"), size=14, weight=ft.FontWeight.W_700, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(f"{convo.get('farm_name', '—')}  •  {convo.get('case_type', 'Tu van')}", size=10, color=ft.Colors.WHITE60),
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
                            controls=[
                                ft.Text(f"Case-{convo['id']:04d}", size=14, weight=ft.FontWeight.W_700),
                                context_header,
                            ],
                        ),
                        info_strip("Case detail gom overview, data, AI, trao doi va lich su. Khong de chat chiem toan bo man hinh.", tone="neutral"),
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
                    indicator_color=_TEAL,
                    tabs=[
                        ft.Tab(text="Tong quan", content=overview_tab),
                        ft.Tab(text="Du lieu", content=data_tab),
                        ft.Tab(text="AI", content=ai_tab),
                        ft.Tab(text="Trao doi", content=trao_doi_tab),
                        ft.Tab(text="Lich su", content=history_tab),
                    ],
                ),
            ),
            sticky_action_bar(
                [
                    ft.ElevatedButton("Yeu cau data", icon=ft.Icons.DATA_OBJECT, style=button_style("surface"), on_click=_request_data),
                    ft.ElevatedButton("Ket luan", icon=ft.Icons.FACT_CHECK, style=button_style("primary"), on_click=_send_conclusion),
                    ft.ElevatedButton("Escalate", icon=ft.Icons.PRIORITY_HIGH, style=button_style("warning"), on_click=_escalate),
                    ft.ElevatedButton("Dong case", icon=ft.Icons.CHECK_CIRCLE, style=button_style("danger"), on_click=_close_case),
                ]
            ),
        ],
    )
    _refresh_context()
    _refresh_notes()
    _refresh_history()
    _update()
