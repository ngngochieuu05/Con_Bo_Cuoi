from __future__ import annotations

import flet as ft

from bll.admin.user_management import list_users
from bll.services import chat_service
from bll.services.auth_service import get_session_value
from ui.theme import PRIMARY, WARNING


def _get_experts() -> list[dict]:
    try:
        return [user for user in list_users() if user.get("vai_tro") == "expert"]
    except Exception:
        return []


def _safe_update(page: ft.Page | None) -> None:
    if not page:
        return
    try:
        page.update()
    except Exception:
        pass


def make_expert_chat(page: ft.Page, on_back=None):
    experts = _get_experts()
    selected_expert = {"user": experts[0] if experts else None}
    farmer_id = int(get_session_value(page, "user_id", 0) or 0)
    farmer_name = get_session_value(page, "ho_ten", "Nông dân") or "Nông dân"

    def _get_conversation() -> dict | None:
        expert = selected_expert["user"]
        if not expert:
            return None
        expert_id = int(expert.get("id_user") or 0)
        if not expert_id:
            return None
        conversation = chat_service.get_or_create_conversation(farmer_id, farmer_name, expert_id)
        if not conversation["messages"]:
            expert_name = expert.get("ho_ten") or expert.get("ten_dang_nhap", "Chuyên gia")
            conversation["messages"].append(
                {
                    "sender": "expert",
                    "text": f"Xin chào! Tôi là {expert_name}.\nHãy mô tả tình trạng con bò của bạn hoặc gửi ảnh để tôi hỗ trợ.",
                    "img_src": None,
                    "time": "08:00",
                }
            )
        return conversation

    conversation_ref: dict[str, dict | None] = {"current": _get_conversation()}
    list_ref = ft.Ref[ft.ListView]()
    input_ref = ft.Ref[ft.TextField]()

    def _bubble(msg: dict) -> ft.Control:
        sender = msg.get("sender", "farmer")
        is_me = sender == "farmer"
        if is_me:
            align = ft.MainAxisAlignment.END
            bg = ft.Colors.with_opacity(0.30, PRIMARY)
            border_col = ft.Colors.with_opacity(0.40, PRIMARY)
            avatar_color = PRIMARY
            avatar_icon = ft.Icons.PERSON
        else:
            align = ft.MainAxisAlignment.START
            bg = ft.Colors.with_opacity(0.16, ft.Colors.TEAL_300)
            border_col = ft.Colors.with_opacity(0.30, ft.Colors.TEAL_300)
            avatar_color = ft.Colors.TEAL_300
            avatar_icon = ft.Icons.SUPPORT_AGENT

        inner: list[ft.Control] = []
        if msg.get("img_src"):
            inner.append(
                ft.Image(src=msg["img_src"], width=200, border_radius=10, fit=ft.ImageFit.COVER)
            )
        if msg.get("text"):
            inner.append(ft.Text(msg["text"], size=13, color=ft.Colors.WHITE, selectable=True))
        inner.append(
            ft.Text(
                msg["time"],
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
            width=30,
            height=30,
            border_radius=15,
            bgcolor=ft.Colors.with_opacity(0.20, avatar_color),
            alignment=ft.alignment.center,
            content=ft.Icon(avatar_icon, size=16, color=avatar_color),
        )

        row_controls = [bubble, avatar] if is_me else [avatar, bubble]
        return ft.Row(
            alignment=align,
            vertical_alignment=ft.CrossAxisAlignment.END,
            spacing=6,
            controls=row_controls,
        )

    def _append_bubble(msg: dict):
        if list_ref.current and list_ref.current.page:
            list_ref.current.controls.append(_bubble(msg))
            _safe_update(page)

    def _reset_chat():
        conversation_ref["current"] = _get_conversation()
        messages = conversation_ref["current"]["messages"] if conversation_ref["current"] else []
        if not list_ref.current:
            return
        list_ref.current.controls.clear()
        for message in messages:
            list_ref.current.controls.append(_bubble(message))
        _safe_update(page)

    def _send_text(e=None):
        text = (input_ref.current.value or "").strip()
        if not text:
            return
        conversation = conversation_ref["current"]
        if not conversation:
            return
        chat_service.send_message(conversation["id"], "farmer", text=text)
        input_ref.current.value = ""
        _append_bubble(conversation["messages"][-1])

    def _on_pick_image(e: ft.FilePickerResultEvent):
        if not e.files:
            return
        conversation = conversation_ref["current"]
        if not conversation:
            return
        chat_service.send_message(conversation["id"], "farmer", img_src=e.files[0].path)
        _append_bubble(conversation["messages"][-1])

    picker_img = ft.FilePicker(on_result=_on_pick_image)
    if page:
        page.overlay.append(picker_img)
        _safe_update(page)

    expert_options = [
        ft.dropdown.Option(
            key=str(user.get("id_user")),
            text=user.get("ho_ten") or user.get("ten_dang_nhap", f"ID {user.get('id_user')}"),
        )
        for user in experts
    ]
    expert_name_label = ft.Text(
        (experts[0].get("ho_ten") or experts[0].get("ten_dang_nhap", "Chuyên gia"))
        if experts
        else "Chuyên gia",
        size=14,
        weight=ft.FontWeight.W_700,
    )

    def _on_expert_change(e):
        try:
            chosen_id = int(e.control.value)
        except (TypeError, ValueError):
            return
        selected_expert["user"] = next(
            (user for user in experts if user.get("id_user") == chosen_id),
            None,
        )
        expert_name_label.value = (
            selected_expert["user"].get("ho_ten")
            or selected_expert["user"].get("ten_dang_nhap", "Chuyên gia")
        ) if selected_expert["user"] else "Chuyên gia"
        _reset_chat()
        _safe_update(page)

    expert_dropdown = ft.Dropdown(
        options=expert_options,
        value=str(experts[0].get("id_user")) if experts else None,
        border_radius=12,
        text_size=12,
        content_padding=ft.padding.symmetric(horizontal=10, vertical=2),
        bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.22, ft.Colors.TEAL_300),
        focused_border_color=ft.Colors.TEAL_300,
        hint_text="Chọn chuyên gia…" if not experts else None,
        hint_style=ft.TextStyle(color=ft.Colors.WHITE38, size=12),
        text_style=ft.TextStyle(color=ft.Colors.WHITE, size=12),
        on_change=_on_expert_change,
    )

    initial_messages = conversation_ref["current"]["messages"] if conversation_ref["current"] else []
    chat_list = ft.ListView(
        ref=list_ref,
        expand=True,
        spacing=8,
        padding=ft.padding.symmetric(horizontal=10, vertical=10),
        controls=[_bubble(message) for message in initial_messages],
        auto_scroll=True,
    )

    txt_input = ft.TextField(
        ref=input_ref,
        hint_text="Nhắn tin cho chuyên gia...",
        expand=True,
        border_radius=20,
        min_lines=1,
        max_lines=4,
        shift_enter=True,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.20, ft.Colors.WHITE),
        focused_border_color=ft.Colors.TEAL_300,
        hint_style=ft.TextStyle(color=ft.Colors.WHITE38, size=13),
        text_style=ft.TextStyle(color=ft.Colors.WHITE, size=13),
        cursor_color=ft.Colors.WHITE,
        content_padding=ft.padding.symmetric(horizontal=14, vertical=10),
        on_submit=_send_text,
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
                    icon_color=ft.Colors.TEAL_300,
                    icon_size=22,
                    tooltip="Gửi ảnh",
                    on_click=lambda e: picker_img.pick_files(
                        allow_multiple=False,
                        file_type=ft.FilePickerFileType.IMAGE,
                    ),
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

    header = ft.Container(
        padding=ft.padding.symmetric(horizontal=8, vertical=8),
        bgcolor=ft.Colors.with_opacity(0.14, ft.Colors.WHITE),
        border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.12, ft.Colors.WHITE))),
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Row(
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK_IOS_NEW,
                            icon_color=ft.Colors.WHITE70,
                            icon_size=18,
                            tooltip="Quay lại",
                            on_click=lambda e: on_back() if on_back else None,
                        ),
                        ft.Container(
                            width=34,
                            height=34,
                            border_radius=17,
                            bgcolor=ft.Colors.with_opacity(0.20, ft.Colors.TEAL_300),
                            alignment=ft.alignment.center,
                            content=ft.Icon(ft.Icons.SUPPORT_AGENT, size=18, color=ft.Colors.TEAL_300),
                        ),
                        ft.Column(
                            tight=True,
                            spacing=1,
                            expand=True,
                            controls=[
                                expert_name_label,
                                ft.Text("Chuyên gia thú y", size=10, color=ft.Colors.WHITE60),
                            ],
                        ),
                    ],
                ),
                ft.Row(
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.PERSON_SEARCH, size=16, color=ft.Colors.TEAL_300),
                        ft.Text("Chọn chuyên gia:", size=12, color=ft.Colors.WHITE70),
                        ft.Container(expand=True, content=expert_dropdown),
                    ],
                )
                if experts
                else ft.Container(
                    padding=ft.padding.symmetric(vertical=4),
                    content=ft.Text(
                        "⚠️ Chưa có chuyên gia trong hệ thống.",
                        size=12,
                        color=WARNING,
                    ),
                ),
            ],
        ),
    )

    return ft.Column(
        expand=True,
        spacing=0,
        controls=[
            header,
            ft.Container(expand=True, content=chat_list),
            input_bar,
        ],
    )
