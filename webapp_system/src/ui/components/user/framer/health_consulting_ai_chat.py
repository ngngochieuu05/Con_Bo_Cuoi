from __future__ import annotations

import datetime

import flet as ft

from bll.user.farmer import tu_van_ai
from ui.theme import PRIMARY, SECONDARY, WARNING

from .health_consulting_ai_widgets import build_ai_bubble, build_attach_button
from .health_consulting_camera import open_camera_live

_AI_MODEL_CONF = 0.30

_SEED_MESSAGES = [
    {
        "sender": "system",
        "text": "Xin chào! Tôi là hệ thống AI tư vấn bệnh bò.\n"
        "Hãy gửi ảnh con bò để tôi phân tích sức khỏe cho bạn.",
        "img_src": None,
        "file_name": None,
        "time": "08:00",
        "ai_result": None,
    }
]


def _now() -> str:
    return datetime.datetime.now().strftime("%H:%M")


def _safe_update(page: ft.Page | None) -> None:
    if not page:
        return
    try:
        page.update()
    except Exception:
        pass


def make_ai_chat(page: ft.Page, on_back=None):
    messages: list[dict] = list(_SEED_MESSAGES)
    list_ref = ft.Ref[ft.ListView]()
    input_ref = ft.Ref[ft.TextField]()
    gemini_key_ref = ft.Ref[ft.TextField]()

    def _bubble(msg: dict) -> ft.Control:
        return build_ai_bubble(page, msg, gemini_key_ref)

    def _append_bubble(msg: dict):
        if list_ref.current and list_ref.current.page:
            list_ref.current.controls.append(_bubble(msg))
            _safe_update(page)

    def _send_text(e=None):
        text = (input_ref.current.value or "").strip()
        if not text:
            return
        msg = {
            "sender": "farmer",
            "text": text,
            "img_src": None,
            "file_name": None,
            "time": _now(),
            "ai_result": None,
        }
        messages.append(msg)
        input_ref.current.value = ""
        _append_bubble(msg)

    def _run_ai_analysis(img_path: str):
        wait_msg = {
            "sender": "system",
            "text": "🔍 Đang phân tích ảnh với AI…",
            "img_src": None,
            "file_name": None,
            "time": _now(),
            "ai_result": None,
        }
        messages.append(wait_msg)
        _append_bubble(wait_msg)

        def _on_result(result_dict: dict):
            if list_ref.current and list_ref.current.controls:
                list_ref.current.controls.pop()
            detected = result_dict["diagnosis"]["detected"]
            objects_count = result_dict["diagnosis"]["n_objects"]
            if detected:
                names = ", ".join(item["class"] for item in detected[:3])
                summary = f"Phát hiện {objects_count} đối tượng — {names}."
            else:
                summary = "Không phát hiện dấu hiệu bệnh trong ảnh."
            ai_msg = {
                "sender": "system",
                "text": summary,
                "img_src": None,
                "file_name": None,
                "time": _now(),
                "ai_result": result_dict,
            }
            messages.append(ai_msg)
            if list_ref.current and list_ref.current.page:
                list_ref.current.controls.append(_bubble(ai_msg))
                _safe_update(page)

        def _on_error(err: str):
            if list_ref.current and list_ref.current.controls:
                list_ref.current.controls.pop()
            err_msg = {
                "sender": "system",
                "text": f"⚠️ {err}",
                "img_src": None,
                "file_name": None,
                "time": _now(),
                "ai_result": None,
            }
            messages.append(err_msg)
            if list_ref.current and list_ref.current.page:
                list_ref.current.controls.append(_bubble(err_msg))
                _safe_update(page)

        tu_van_ai.analyze_image_async(
            img_source=img_path,
            conf_thresh=_AI_MODEL_CONF,
            on_result=_on_result,
            on_error=_on_error,
        )

    def _on_pick_image(e: ft.FilePickerResultEvent):
        if not e.files:
            return
        img_path = e.files[0].path
        msg = {
            "sender": "farmer",
            "text": None,
            "img_src": img_path,
            "file_name": None,
            "time": _now(),
            "ai_result": None,
        }
        messages.append(msg)
        _append_bubble(msg)
        _run_ai_analysis(img_path)

    def _on_pick_file(e: ft.FilePickerResultEvent):
        if not e.files:
            return
        msg = {
            "sender": "farmer",
            "text": None,
            "img_src": None,
            "file_name": e.files[0].name,
            "time": _now(),
            "ai_result": None,
        }
        messages.append(msg)
        _append_bubble(msg)

    picker_img = ft.FilePicker(on_result=_on_pick_image)
    picker_file = ft.FilePicker(on_result=_on_pick_file)
    if page:
        page.overlay.extend([picker_img, picker_file])
        _safe_update(page)

    chat_list = ft.ListView(
        ref=list_ref,
        expand=True,
        spacing=8,
        padding=ft.padding.symmetric(horizontal=10, vertical=10),
        controls=[_bubble(message) for message in messages],
        auto_scroll=True,
    )

    txt_input = ft.TextField(
        ref=input_ref,
        hint_text="Nhắn tin...",
        expand=True,
        border_radius=20,
        min_lines=1,
        max_lines=4,
        shift_enter=True,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.20, ft.Colors.WHITE),
        focused_border_color=PRIMARY,
        hint_style=ft.TextStyle(color=ft.Colors.WHITE38, size=13),
        text_style=ft.TextStyle(color=ft.Colors.WHITE, size=13),
        cursor_color=ft.Colors.WHITE,
        content_padding=ft.padding.symmetric(horizontal=14, vertical=10),
        on_submit=_send_text,
    )

    gemini_key_field = ft.TextField(
        ref=gemini_key_ref,
        hint_text="Gemini API key (để lấy tư vấn AI)",
        border_radius=16,
        height=36,
        text_size=11,
        password=True,
        can_reveal_password=True,
        bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.15, ft.Colors.WHITE),
        focused_border_color=SECONDARY,
        hint_style=ft.TextStyle(color=ft.Colors.WHITE38, size=11),
        text_style=ft.TextStyle(color=ft.Colors.WHITE, size=11),
        cursor_color=ft.Colors.WHITE,
        content_padding=ft.padding.symmetric(horizontal=10, vertical=4),
        prefix_icon=ft.Icons.KEY_OUTLINED,
    )

    send_btn = ft.Container(
        width=40,
        height=40,
        border_radius=20,
        bgcolor=PRIMARY,
        alignment=ft.alignment.center,
        ink=True,
        on_click=_send_text,
        content=ft.Icon(ft.Icons.SEND_ROUNDED, size=18, color=ft.Colors.WHITE),
    )

    input_bar = ft.Container(
        padding=ft.padding.symmetric(horizontal=8, vertical=6),
        bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.WHITE),
        border=ft.border.only(top=ft.BorderSide(1, ft.Colors.with_opacity(0.14, ft.Colors.WHITE))),
        content=ft.Column(
            spacing=4,
            tight=True,
            controls=[
                gemini_key_field,
                ft.Row(
                    spacing=2,
                    vertical_alignment=ft.CrossAxisAlignment.END,
                    controls=[
                        build_attach_button(
                            ft.Icons.IMAGE_OUTLINED,
                            "Gửi ảnh",
                            SECONDARY,
                            lambda e: picker_img.pick_files(
                                allow_multiple=False,
                                file_type=ft.FilePickerFileType.IMAGE,
                            ),
                        ),
                        build_attach_button(
                            ft.Icons.ATTACH_FILE,
                            "Gửi file",
                            WARNING,
                            lambda e: picker_file.pick_files(allow_multiple=False),
                        ),
                        build_attach_button(
                            ft.Icons.CAMERA_ALT_OUTLINED,
                            "Mở camera trực tiếp",
                            ft.Colors.AMBER_300,
                            lambda e: open_camera_live(
                                page,
                                messages,
                                _append_bubble,
                                _run_ai_analysis,
                                _now,
                            ),
                        ),
                        txt_input,
                        send_btn,
                    ],
                ),
            ],
        ),
    )

    header = ft.Container(
        padding=ft.padding.symmetric(horizontal=8, vertical=10),
        bgcolor=ft.Colors.with_opacity(0.14, ft.Colors.WHITE),
        border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.12, ft.Colors.WHITE))),
        content=ft.Row(
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
                    bgcolor=ft.Colors.with_opacity(0.20, SECONDARY),
                    alignment=ft.alignment.center,
                    content=ft.Icon(ft.Icons.SMART_TOY, size=18, color=SECONDARY),
                ),
                ft.Column(
                    tight=True,
                    spacing=2,
                    expand=True,
                    controls=[
                        ft.Text("AI Tư vấn bệnh bò", size=14, weight=ft.FontWeight.W_700),
                        ft.Row(
                            tight=True,
                            spacing=5,
                            controls=[
                                ft.Container(width=7, height=7, border_radius=4, bgcolor=PRIMARY),
                                ft.Text("AI sẵn sàng · conf ≥ 30%", size=10, color=ft.Colors.WHITE60),
                            ],
                        ),
                    ],
                ),
                ft.Icon(ft.Icons.MORE_VERT, color=ft.Colors.WHITE38, size=20),
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
