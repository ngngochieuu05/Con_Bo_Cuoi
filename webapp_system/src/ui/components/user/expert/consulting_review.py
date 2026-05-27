from __future__ import annotations

import datetime
import threading

import flet as ft

from bll.services import chat_service, local_chat_store
from ui.upload_bridge import build_upload_batch, is_web_picker_file, wait_for_uploaded_file

_TEAL = ft.Colors.TEAL_300


def _now() -> str:
    return datetime.datetime.now().strftime("%H:%M")


def build_consulting_review(page: ft.Page = None):  # noqa: C901
    expert_id = 0
    if page:
        try:
            expert_id = int(page.client_storage.get("user_id") or 0)
        except Exception:
            expert_id = 0
        if not expert_id:
            try:
                expert_id = int((page.data or {}).get("user_id") or 0)
            except Exception:
                expert_id = 0

    content_area = ft.Container(expand=True)
    stop_sync_evt = threading.Event()
    view_state = {"mode": "list", "chat_id": None, "list_sig": "", "chat_sync": None}

    def _update():
        if page:
            try:
                page.update()
            except Exception:
                pass

    def _bubble(msg: dict) -> ft.Control:
        is_me = msg.get("sender") == "expert"
        align = ft.MainAxisAlignment.END if is_me else ft.MainAxisAlignment.START
        bg = ft.Colors.with_opacity(0.28, _TEAL) if is_me else ft.Colors.with_opacity(0.18, ft.Colors.WHITE)
        border_col = ft.Colors.with_opacity(0.40, _TEAL) if is_me else ft.Colors.with_opacity(0.20, ft.Colors.WHITE)
        av_color = _TEAL if is_me else ft.Colors.BLUE_300
        av_icon = ft.Icons.SUPPORT_AGENT if is_me else ft.Icons.PERSON

        inner: list[ft.Control] = []
        if msg.get("img_b64"):
            inner.append(
                ft.Image(src_base64=msg["img_b64"], width=180, border_radius=10, fit=ft.ImageFit.COVER)
            )
        elif msg.get("img_src"):
            inner.append(
                ft.Image(src=msg["img_src"], width=180, border_radius=10, fit=ft.ImageFit.COVER)
            )
        if msg.get("text"):
            inner.append(ft.Text(msg["text"], size=13, color=ft.Colors.WHITE, selectable=True))
        inner.append(
            ft.Text(
                msg.get("time", ""),
                size=9,
                color=ft.Colors.WHITE38,
                text_align=ft.TextAlign.RIGHT if is_me else ft.TextAlign.LEFT,
            )
        )

        bubble = ft.Container(
            width=270,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=ft.border_radius.only(
                top_left=16,
                top_right=16,
                bottom_left=4 if is_me else 16,
                bottom_right=16 if is_me else 4,
            ),
            bgcolor=bg,
            border=ft.border.all(1, border_col),
            content=ft.Column(spacing=4, tight=True, controls=inner),
        )
        avatar = ft.Container(
            width=28,
            height=28,
            border_radius=14,
            bgcolor=ft.Colors.with_opacity(0.20, av_color),
            alignment=ft.alignment.center,
            content=ft.Icon(av_icon, size=14, color=av_color),
        )
        return ft.Row(
            alignment=align,
            vertical_alignment=ft.CrossAxisAlignment.END,
            spacing=6,
            controls=[bubble, avatar] if is_me else [avatar, bubble],
        )

    def _list_item(convo: dict) -> ft.Control:
        name = convo.get("farmer_name", "?")
        initial = name[0].upper()
        unread = int(convo.get("unread_expert", 0) or 0)
        msgs = convo.get("messages", [])
        last = msgs[-1] if msgs else {}
        preview = last.get("text") or ("[Ảnh]" if (last.get("img_src") or last.get("img_b64")) else "Chưa có tin nhắn")
        if len(preview) > 40:
            preview = preview[:40] + "…"

        return ft.Container(
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE))),
            ink=True,
            on_click=lambda e, c=convo: _show_chat(c),
            content=ft.Row(
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Stack(
                        width=46,
                        height=46,
                        controls=[
                            ft.Container(
                                width=46,
                                height=46,
                                border_radius=23,
                                bgcolor=ft.Colors.with_opacity(0.26, ft.Colors.BLUE_300),
                                alignment=ft.alignment.center,
                                content=ft.Text(initial, size=16, weight=ft.FontWeight.W_700, color=ft.Colors.BLUE_100),
                            ),
                            ft.Container(
                                right=0,
                                top=0,
                                width=18,
                                height=18,
                                border_radius=9,
                                bgcolor=ft.Colors.RED_400,
                                alignment=ft.alignment.center,
                                visible=unread > 0,
                                content=ft.Text(str(unread), size=9, color=ft.Colors.WHITE, weight=ft.FontWeight.W_700),
                            ),
                        ],
                    ),
                    ft.Column(
                        expand=True,
                        spacing=3,
                        tight=True,
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        name,
                                        size=14,
                                        weight=ft.FontWeight.W_700 if unread else ft.FontWeight.W_500,
                                        color=ft.Colors.WHITE if unread else ft.Colors.WHITE70,
                                        expand=True,
                                        max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                    ft.Text(last.get("time", ""), size=10, color=ft.Colors.WHITE38),
                                ],
                            ),
                            ft.Text(
                                preview,
                                size=12,
                                weight=ft.FontWeight.W_600 if unread else ft.FontWeight.NORMAL,
                                color=ft.Colors.WHITE70 if unread else ft.Colors.WHITE38,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                    ),
                ],
            ),
        )

    def _conversation_list_signature(convos: list[dict]) -> str:
        return "|".join(
            f"{c.get('id')}::{c.get('unread_expert', 0)}::{len(c.get('messages', []))}::{(c.get('messages', [])[-1].get('time', '') if c.get('messages') else '')}"
            for c in convos
        )

    def _show_list():
        view_state["mode"] = "list"
        view_state["chat_id"] = None
        view_state["chat_sync"] = None
        convos = chat_service.list_conversations_for_expert(expert_id)
        view_state["list_sig"] = _conversation_list_signature(convos)
        total_unread = sum(int(c.get("unread_expert", 0) or 0) for c in convos)

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
                            ft.Icon(ft.Icons.CHAT_BUBBLE_OUTLINE, size=52, color=ft.Colors.WHITE24),
                            ft.Text("Chưa có hội thoại nào.", size=14, color=ft.Colors.WHITE38),
                        ],
                    ),
                )
            ]

        list_header = ft.Container(
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.WHITE),
            border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.10, ft.Colors.WHITE))),
            content=ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.FORUM_OUTLINED, size=20, color=_TEAL),
                    ft.Container(width=8),
                    ft.Text("Hội thoại tư vấn", size=16, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE, expand=True),
                    ft.Container(
                        width=22,
                        height=22,
                        border_radius=11,
                        bgcolor=ft.Colors.RED_400,
                        alignment=ft.alignment.center,
                        visible=total_unread > 0,
                        content=ft.Text(str(total_unread), size=10, color=ft.Colors.WHITE, weight=ft.FontWeight.W_700),
                    ),
                ],
            ),
        )

        content_area.content = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                list_header,
                ft.Container(expand=True, content=ft.ListView(expand=True, spacing=0, controls=items)),
            ],
        )
        _update()

    def _show_chat(convo: dict):
        view_state["mode"] = "chat"
        view_state["chat_id"] = convo["id"]
        chat_service.mark_read_expert(convo["id"])

        chat_list_ref = ft.Ref[ft.ListView]()
        input_ref = ft.Ref[ft.TextField]()
        typing_status_text = ft.Text(value="", size=10, color=ft.Colors.WHITE54)

        def _message_signature(current: dict | None) -> str:
            if not current:
                return "none"
            return "|".join(
                f"{msg.get('sender')}::{msg.get('time')}::{msg.get('text') or ''}::{bool(msg.get('img_src') or msg.get('img_b64'))}"
                for msg in current.get("messages", [])
            )

        sync_chat_state = {"sig": _message_signature(convo), "typing": ""}

        def _refresh_typing(current: dict | None):
            status = ""
            if chat_service.is_typing_active(current, "farmer"):
                status = f"{current.get('farmer_name', 'Nông dân')} đang soạn tin nhắn..."
            elif chat_service.is_typing_active(current, "expert"):
                status = "Bạn đang soạn tin nhắn..."
            typing_status_text.value = status

        def _sync_chat(force: bool = False):
            fresh = chat_service.get_conversation_by_id(convo["id"])
            if not fresh or view_state["chat_id"] != convo["id"] or view_state["mode"] != "chat":
                return
            convo.clear()
            convo.update(fresh)
            sig = _message_signature(convo)
            typing_sig = f"{convo.get('typing_farmer_at', '')}|{convo.get('typing_expert_at', '')}"
            if force or sig != sync_chat_state["sig"]:
                if chat_list_ref.current:
                    chat_list_ref.current.controls = [_bubble(m) for m in convo["messages"]]
                sync_chat_state["sig"] = sig
            if force or typing_sig != sync_chat_state["typing"]:
                _refresh_typing(convo)
                sync_chat_state["typing"] = typing_sig
            _update()
        view_state["chat_sync"] = _sync_chat

        def _send_text(_e=None):
            if not input_ref.current:
                return
            txt = (input_ref.current.value or "").strip()
            if not txt:
                return
            chat_service.send_message(convo["id"], "expert", text=txt)
            chat_service.set_typing(convo["id"], "expert", False)
            input_ref.current.value = ""
            _sync_chat(True)

        def _on_pick_img(ev: ft.FilePickerResultEvent):
            if not ev.files:
                return
            file_obj = ev.files[0]
            if is_web_picker_file(file_obj):
                items, jobs = build_upload_batch(page, [file_obj], subdir="expert_chat/expert")
                picker.data = {"pending": items}
                picker.upload(jobs)
                return
            chat_service.send_message(
                convo["id"],
                "expert",
                img_src=file_obj.path,
                img_b64=local_chat_store.read_image_base64_from_source(file_obj.path),
            )
            chat_service.set_typing(convo["id"], "expert", False)
            _sync_chat(True)

        def _on_pick_img_upload(ev: ft.FilePickerUploadEvent):
            state = picker.data if isinstance(picker.data, dict) else None
            if not state:
                return
            if ev.error:
                picker.data = None
                return
            if ev.progress != 1.0:
                return
            item = state["pending"][0]
            uploaded = wait_for_uploaded_file(item["server_path"])
            if not uploaded:
                picker.data = None
                return
            chat_service.send_message(
                convo["id"],
                "expert",
                img_src=item["public_src"],
                img_b64=local_chat_store.read_image_base64_from_source(str(uploaded)),
            )
            picker.data = None
            chat_service.set_typing(convo["id"], "expert", False)
            _sync_chat(True)

        picker = ft.FilePicker(on_result=_on_pick_img, on_upload=_on_pick_img_upload)
        if page:
            page.overlay.append(picker)
            page.update()

        name = convo.get("farmer_name", "?")
        initial = name[0].upper()

        chat_header = ft.Container(
            padding=ft.padding.symmetric(horizontal=8, vertical=10),
            bgcolor=ft.Colors.with_opacity(0.14, ft.Colors.WHITE),
            border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.12, ft.Colors.WHITE))),
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
                        width=36,
                        height=36,
                        border_radius=18,
                        bgcolor=ft.Colors.with_opacity(0.26, ft.Colors.BLUE_300),
                        alignment=ft.alignment.center,
                        content=ft.Text(initial, size=14, weight=ft.FontWeight.W_700, color=ft.Colors.BLUE_100),
                    ),
                    ft.Column(
                        tight=True,
                        spacing=1,
                        expand=True,
                        controls=[
                            ft.Text(name, size=14, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text("Nông dân", size=10, color=ft.Colors.WHITE60),
                            typing_status_text,
                        ],
                    ),
                ],
            ),
        )

        chat_list = ft.ListView(
            ref=chat_list_ref,
            expand=True,
            spacing=8,
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            controls=[_bubble(m) for m in convo["messages"]],
            auto_scroll=True,
        )

        txt_input = ft.TextField(
            ref=input_ref,
            hint_text="Trả lời nông dân...",
            expand=True,
            border_radius=20,
            min_lines=1,
            max_lines=4,
            shift_enter=True,
            bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
            border_color=ft.Colors.with_opacity(0.20, ft.Colors.WHITE),
            focused_border_color=_TEAL,
            hint_style=ft.TextStyle(color=ft.Colors.WHITE38, size=13),
            text_style=ft.TextStyle(color=ft.Colors.WHITE, size=13),
            cursor_color=ft.Colors.WHITE,
            content_padding=ft.padding.symmetric(horizontal=14, vertical=10),
            on_submit=_send_text,
            on_change=lambda e: chat_service.set_typing(
                convo["id"],
                "expert",
                bool((e.control.value or "").strip()),
            ),
        )

        input_bar = ft.Container(
            padding=ft.padding.symmetric(horizontal=8, vertical=8),
            bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.WHITE),
            border=ft.border.only(top=ft.BorderSide(1, ft.Colors.with_opacity(0.14, ft.Colors.WHITE))),
            content=ft.Row(
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.END,
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.IMAGE_OUTLINED,
                        icon_color=_TEAL,
                        icon_size=22,
                        tooltip="Gửi ảnh",
                        on_click=lambda e: picker.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.IMAGE),
                    ),
                    txt_input,
                    ft.Container(
                        width=40,
                        height=40,
                        border_radius=20,
                        bgcolor=ft.Colors.TEAL_700,
                        alignment=ft.alignment.center,
                        ink=True,
                        on_click=_send_text,
                        content=ft.Icon(ft.Icons.SEND_ROUNDED, size=18, color=ft.Colors.WHITE),
                    ),
                ],
            ),
        )

        content_area.content = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                chat_header,
                ft.Container(expand=True, content=chat_list),
                input_bar,
            ],
        )
        _sync_chat(True)

    _show_list()

    def _poll_sync():
        while not stop_sync_evt.wait(0.8):
            if view_state["mode"] == "list":
                convos = chat_service.list_conversations_for_expert(expert_id)
                sig = _conversation_list_signature(convos)
                if sig != view_state["list_sig"]:
                    _show_list()
            elif view_state["chat_id"] and callable(view_state.get("chat_sync")):
                view_state["chat_sync"]()

    threading.Thread(target=_poll_sync, daemon=True).start()
    return content_area
