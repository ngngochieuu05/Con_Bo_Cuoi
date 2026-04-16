"""
Expert — Tư vấn (Mobile Navigation Stack)
Màn hình 1: Danh sách hội thoại từ các farmer (full width).
Màn hình 2: Chat window cho cuộc trò chuyện được chọn (full width).
"""
from __future__ import annotations
import datetime

import flet as ft

from ui.theme import WARNING
from bll.services import chat_service

_TEAL = ft.Colors.TEAL_300

# ── Seed data (only used if expert has no conversations yet) ───────────────────
_SEED_CONVOS = [
    {
        "farmer_id": 101,
        "farmer_name": "Trần Thị Nông",
        "unread": 2,
        "messages": [
            {"sender": "farmer",
             "text": "Chào chuyên gia! Con bò của tôi đang có dấu hiệu bất thường.",
             "time": "08:12"},
            {"sender": "expert",
             "text": "Chào bạn! Bạn có thể mô tả cụ thể hơn hoặc gửi ảnh cho tôi xem.",
             "time": "08:14"},
            {"sender": "farmer",
             "text": "Con bò bị sưng chân và ăn ít hơn bình thường từ hôm qua.",
             "time": "08:15"},
        ],
    },
    {
        "farmer_id": 102,
        "farmer_name": "Nguyễn Văn Hùng",
        "unread": 0,
        "messages": [
            {"sender": "farmer",
             "text": "Cho tôi hỏi về bệnh lở mồm long móng ạ.",
             "time": "07:30"},
            {"sender": "expert",
             "text": "Bệnh lở mồm long móng (FMD) là bệnh virus rất dễ lây. "
                     "Triệu chứng: bọng nước ở miệng, chân, vú. "
                     "Cần cách ly ngay và báo thú y.",
             "time": "07:45"},
            {"sender": "farmer", "text": "Cảm ơn chuyên gia nhiều!", "time": "07:46"},
        ],
    },
    {
        "farmer_id": 103,
        "farmer_name": "Lê Thị Mai",
        "unread": 1,
        "messages": [
            {"sender": "farmer",
             "text": "Bò nhà tôi ho nhiều và chảy nước mũi.",
             "time": "09:00"},
        ],
    },
]


def _now() -> str:
    return datetime.datetime.now().strftime("%H:%M")


# ── Main entry ─────────────────────────────────────────────────────────────────

def build_consulting_review(page: ft.Page = None):  # noqa: C901
    expert_id = int((page.client_storage.get("user_id") or 0) if page else 0)

    # Seed demo conversations once per expert_id
    if not chat_service.list_conversations_for_expert(expert_id):
        for seed in _SEED_CONVOS:
            convo = chat_service.get_or_create_conversation(
                seed["farmer_id"], seed["farmer_name"], expert_id
            )
            for m in seed["messages"]:
                convo["messages"].append({
                    "sender": m["sender"], "text": m["text"],
                    "img_src": None, "time": m["time"],
                })
            convo["unread_expert"] = seed["unread"]

    # ─ shared state ──────────────────────────────────────────────────────────
    content_area = ft.Container(expand=True)

    def _update():
        if page:
            try:
                page.update()
            except Exception:
                pass

    # ─ bubble ────────────────────────────────────────────────────────────────

    def _bubble(msg: dict) -> ft.Control:
        is_me = msg.get("sender") == "expert"
        align      = ft.MainAxisAlignment.END if is_me else ft.MainAxisAlignment.START
        bg         = (ft.Colors.with_opacity(0.28, _TEAL) if is_me
                      else ft.Colors.with_opacity(0.18, ft.Colors.WHITE))
        border_col = (ft.Colors.with_opacity(0.40, _TEAL) if is_me
                      else ft.Colors.with_opacity(0.20, ft.Colors.WHITE))
        av_color   = _TEAL if is_me else ft.Colors.BLUE_300
        av_icon    = ft.Icons.SUPPORT_AGENT if is_me else ft.Icons.PERSON

        inner: list[ft.Control] = []
        if msg.get("img_src"):
            inner.append(
                ft.Image(src=msg["img_src"], width=180, border_radius=10,
                         fit=ft.ImageFit.COVER)
            )
        if msg.get("text"):
            inner.append(
                ft.Text(msg["text"], size=13, color=ft.Colors.WHITE,
                        selectable=True)
            )
        inner.append(
            ft.Text(
                msg.get("time", ""), size=9, color=ft.Colors.WHITE38,
                text_align=ft.TextAlign.RIGHT if is_me else ft.TextAlign.LEFT,
            )
        )

        bubble = ft.Container(
            width=270,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=ft.border_radius.only(
                top_left=16, top_right=16,
                bottom_left=4 if is_me else 16,
                bottom_right=16 if is_me else 4,
            ),
            bgcolor=bg,
            border=ft.border.all(1, border_col),
            content=ft.Column(spacing=4, tight=True, controls=inner),
        )
        avatar = ft.Container(
            width=28, height=28, border_radius=14,
            bgcolor=ft.Colors.with_opacity(0.20, av_color),
            alignment=ft.alignment.center,
            content=ft.Icon(av_icon, size=14, color=av_color),
        )
        row_ctrls = [bubble, avatar] if is_me else [avatar, bubble]
        return ft.Row(
            alignment=align,
            vertical_alignment=ft.CrossAxisAlignment.END,
            spacing=6, controls=row_ctrls,
        )

    # ─ list item ─────────────────────────────────────────────────────────────

    def _list_item(convo: dict) -> ft.Control:
        name    = convo.get("farmer_name", "?")
        initial = name[0].upper()
        unread  = convo.get("unread_expert", 0)
        msgs    = convo.get("messages", [])
        last    = msgs[-1] if msgs else {}
        preview = last.get("text") or ("[Ảnh]" if last.get("img_src") else "Chưa có tin nhắn")
        if len(preview) > 40:
            preview = preview[:40] + "…"

        return ft.Container(
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border=ft.border.only(
                bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE))
            ),
            ink=True,
            on_click=lambda e, c=convo: _show_chat(c),
            content=ft.Row(
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Stack(
                        width=46, height=46,
                        controls=[
                            ft.Container(
                                width=46, height=46, border_radius=23,
                                bgcolor=ft.Colors.with_opacity(0.26, ft.Colors.BLUE_300),
                                alignment=ft.alignment.center,
                                content=ft.Text(
                                    initial, size=16,
                                    weight=ft.FontWeight.W_700,
                                    color=ft.Colors.BLUE_100,
                                ),
                            ),
                            ft.Container(
                                right=0, top=0,
                                width=18, height=18, border_radius=9,
                                bgcolor=ft.Colors.RED_400,
                                alignment=ft.alignment.center,
                                visible=unread > 0,
                                content=ft.Text(
                                    str(unread), size=9,
                                    color=ft.Colors.WHITE,
                                    weight=ft.FontWeight.W_700,
                                ),
                            ),
                        ],
                    ),
                    ft.Column(
                        expand=True, spacing=3, tight=True,
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        name, size=14,
                                        weight=ft.FontWeight.W_700 if unread
                                               else ft.FontWeight.W_500,
                                        color=ft.Colors.WHITE if unread
                                              else ft.Colors.WHITE70,
                                        expand=True, max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                    ft.Text(
                                        last.get("time", ""), size=10,
                                        color=ft.Colors.WHITE38,
                                    ),
                                ],
                            ),
                            ft.Text(
                                preview, size=12,
                                weight=ft.FontWeight.W_600 if unread
                                       else ft.FontWeight.NORMAL,
                                color=ft.Colors.WHITE70 if unread
                                      else ft.Colors.WHITE38,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                    ),
                ],
            ),
        )

    # ─ show list view ────────────────────────────────────────────────────────

    def _show_list():
        convos       = chat_service.list_conversations_for_expert(expert_id)
        total_unread = sum(c.get("unread_expert", 0) for c in convos)

        if convos:
            items: list[ft.Control] = [_list_item(c) for c in convos]
        else:
            items = [
                ft.Container(
                    padding=ft.padding.all(40),
                    alignment=ft.alignment.center,
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=12,
                        controls=[
                            ft.Icon(ft.Icons.CHAT_BUBBLE_OUTLINE,
                                    size=52, color=ft.Colors.WHITE24),
                            ft.Text("Chưa có hội thoại nào",
                                    size=14, color=ft.Colors.WHITE38),
                        ],
                    ),
                )
            ]

        list_header = ft.Container(
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.WHITE),
            border=ft.border.only(
                bottom=ft.BorderSide(
                    1, ft.Colors.with_opacity(0.10, ft.Colors.WHITE)
                )
            ),
            content=ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.FORUM_OUTLINED, size=20, color=_TEAL),
                    ft.Container(width=8),
                    ft.Text(
                        "Hội thoại tư vấn", size=16,
                        weight=ft.FontWeight.W_700,
                        color=ft.Colors.WHITE, expand=True,
                    ),
                    ft.Container(
                        width=22, height=22, border_radius=11,
                        bgcolor=ft.Colors.RED_400,
                        alignment=ft.alignment.center,
                        visible=total_unread > 0,
                        content=ft.Text(
                            str(total_unread), size=10,
                            color=ft.Colors.WHITE,
                            weight=ft.FontWeight.W_700,
                        ),
                    ),
                ],
            ),
        )

        content_area.content = ft.Column(
            expand=True, spacing=0,
            controls=[
                list_header,
                ft.Container(
                    expand=True,
                    content=ft.ListView(expand=True, spacing=0, controls=items),
                ),
            ],
        )
        _update()

    # ─ show chat view ────────────────────────────────────────────────────────

    def _show_chat(convo: dict):
        chat_service.mark_read_expert(convo["id"])

        chat_list_ref = ft.Ref[ft.ListView]()
        input_ref     = ft.Ref[ft.TextField]()

        def _send_text(e=None):
            if not input_ref.current:
                return
            txt = (input_ref.current.value or "").strip()
            if not txt:
                return
            chat_service.send_message(convo["id"], "expert", text=txt)
            input_ref.current.value = ""
            if chat_list_ref.current:
                chat_list_ref.current.controls.append(
                    _bubble(convo["messages"][-1])
                )
            _update()

        def _on_pick_img(ev: ft.FilePickerResultEvent):
            if not ev.files:
                return
            chat_service.send_message(convo["id"], "expert",
                                       img_src=ev.files[0].path)
            if chat_list_ref.current:
                chat_list_ref.current.controls.append(
                    _bubble(convo["messages"][-1])
                )
            _update()

        picker = ft.FilePicker(on_result=_on_pick_img)
        if page:
            page.overlay.append(picker)
            page.update()

        name    = convo.get("farmer_name", "?")
        initial = name[0].upper()

        chat_header = ft.Container(
            padding=ft.padding.symmetric(horizontal=8, vertical=10),
            bgcolor=ft.Colors.with_opacity(0.14, ft.Colors.WHITE),
            border=ft.border.only(
                bottom=ft.BorderSide(
                    1, ft.Colors.with_opacity(0.12, ft.Colors.WHITE)
                )
            ),
            content=ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.ARROW_BACK_IOS_NEW,
                        icon_color=ft.Colors.WHITE70,
                        icon_size=18,
                        tooltip="Quay lại",
                        on_click=lambda e: _show_list(),
                    ),
                    ft.Container(
                        width=36, height=36, border_radius=18,
                        bgcolor=ft.Colors.with_opacity(0.26, ft.Colors.BLUE_300),
                        alignment=ft.alignment.center,
                        content=ft.Text(
                            initial, size=14,
                            weight=ft.FontWeight.W_700,
                            color=ft.Colors.BLUE_100,
                        ),
                    ),
                    ft.Column(
                        tight=True, spacing=1, expand=True,
                        controls=[
                            ft.Text(
                                name, size=14,
                                weight=ft.FontWeight.W_700,
                                color=ft.Colors.WHITE,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Row(tight=True, spacing=5, controls=[
                                ft.Container(
                                    width=7, height=7, border_radius=4,
                                    bgcolor=ft.Colors.GREEN_400,
                                ),
                                ft.Text("Nông dân", size=10,
                                        color=ft.Colors.WHITE60),
                            ]),
                        ],
                    ),
                ],
            ),
        )

        chat_list = ft.ListView(
            ref=chat_list_ref,
            expand=True, spacing=8,
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            controls=[_bubble(m) for m in convo["messages"]],
            auto_scroll=True,
        )

        txt_input = ft.TextField(
            ref=input_ref,
            hint_text="Trả lời nông dân...",
            expand=True,
            border_radius=20,
            min_lines=1, max_lines=4,
            shift_enter=True,
            bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
            border_color=ft.Colors.with_opacity(0.20, ft.Colors.WHITE),
            focused_border_color=_TEAL,
            hint_style=ft.TextStyle(color=ft.Colors.WHITE38, size=13),
            text_style=ft.TextStyle(color=ft.Colors.WHITE, size=13),
            cursor_color=ft.Colors.WHITE,
            content_padding=ft.padding.symmetric(horizontal=14, vertical=10),
            on_submit=_send_text,
        )

        input_bar = ft.Container(
            padding=ft.padding.symmetric(horizontal=8, vertical=8),
            bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.WHITE),
            border=ft.border.only(
                top=ft.BorderSide(1, ft.Colors.with_opacity(0.14, ft.Colors.WHITE))
            ),
            content=ft.Row(
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.END,
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.IMAGE_OUTLINED,
                        icon_color=_TEAL, icon_size=22,
                        tooltip="Gửi ảnh",
                        on_click=lambda e: picker.pick_files(
                            allow_multiple=False,
                            file_type=ft.FilePickerFileType.IMAGE,
                        ),
                    ),
                    txt_input,
                    ft.Container(
                        width=40, height=40, border_radius=20,
                        bgcolor=ft.Colors.TEAL_700,
                        alignment=ft.alignment.center,
                        ink=True, on_click=_send_text,
                        content=ft.Icon(ft.Icons.SEND_ROUNDED, size=18,
                                        color=ft.Colors.WHITE),
                    ),
                ],
            ),
        )

        content_area.content = ft.Column(
            expand=True, spacing=0,
            controls=[
                chat_header,
                ft.Container(expand=True, content=chat_list),
                input_bar,
            ],
        )
        _update()

    # ─ initial render ────────────────────────────────────────────────────────
    _show_list()
    return content_area

