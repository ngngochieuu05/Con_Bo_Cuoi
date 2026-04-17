"""
Expert — Chat View
Chat window with quick replies and AI image analysis.
Bubble/panel widgets live in consulting_ai_panel.py.
"""
from __future__ import annotations
import flet as ft
from bll.services import chat_service
from bll.user.farmer.tu_van_ai import analyze_image_async
from ui.components.user.expert.consulting_ai_panel import build_ai_result_panel, build_chat_bubble

_TEAL = ft.Colors.TEAL_300
_QUICK_REPLIES = ["Cần cách ly ngay", "Theo dõi thêm 24h", "Đưa đến thú y", "Bình thường, không lo"]


def _quick_reply_row(input_ref: ft.Ref, page) -> ft.Control:
    def _fill(text: str):
        if input_ref.current:
            input_ref.current.value = text
            if page:
                try:
                    page.update()
                except Exception:
                    pass

    return ft.Container(
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        content=ft.Row(
            spacing=6, scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.OutlinedButton(
                    text=r,
                    style=ft.ButtonStyle(
                        color=_TEAL,
                        side=ft.BorderSide(1, ft.Colors.with_opacity(0.35, _TEAL)),
                        shape=ft.RoundedRectangleBorder(radius=14),
                        padding=ft.padding.symmetric(horizontal=10, vertical=4),
                        text_style=ft.TextStyle(size=11),
                    ),
                    on_click=lambda e, t=r: _fill(t),
                ) for r in _QUICK_REPLIES
            ],
        ),
    )


def show_chat_view(content_area: ft.Container, convo: dict, page, on_back) -> None:
    chat_service.mark_read_expert(convo["id"])
    chat_list_ref = ft.Ref[ft.ListView]()
    input_ref     = ft.Ref[ft.TextField]()

    def _update():
        if page:
            try:
                page.update()
            except Exception:
                pass

    def _on_analyze(img_path: str, result_ctr: ft.Container):
        result_ctr.content = ft.Row(spacing=6, controls=[
            ft.ProgressRing(width=18, height=18, stroke_width=2),
            ft.Text("Đang phân tích...", size=11, color=ft.Colors.WHITE54),
        ])
        result_ctr.visible = True
        _update()

        def on_result(r):
            result_ctr.content = build_ai_result_panel(r)
            _update()

        def on_error(msg):
            result_ctr.content = ft.Text(msg, color=ft.Colors.RED_300, size=11)
            _update()

        analyze_image_async(img_path, conf_thresh=0.25, on_result=on_result, on_error=on_error)

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
                build_chat_bubble(convo["messages"][-1], _on_analyze)
            )
        _update()

    def _on_pick_img(ev: ft.FilePickerResultEvent):
        if not ev.files:
            return
        chat_service.send_message(convo["id"], "expert", img_src=ev.files[0].path)
        if chat_list_ref.current:
            chat_list_ref.current.controls.append(
                build_chat_bubble(convo["messages"][-1], _on_analyze)
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
        border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.12, ft.Colors.WHITE))),
        content=ft.Row(
            spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.IconButton(icon=ft.Icons.ARROW_BACK_IOS_NEW, icon_color=ft.Colors.WHITE70,
                              icon_size=18, tooltip="Quay lại", on_click=lambda e: on_back()),
                ft.Container(
                    width=36, height=36, border_radius=18,
                    bgcolor=ft.Colors.with_opacity(0.26, ft.Colors.BLUE_300),
                    alignment=ft.alignment.center,
                    content=ft.Text(initial, size=14, weight=ft.FontWeight.W_700,
                                    color=ft.Colors.BLUE_100),
                ),
                ft.Column(tight=True, spacing=1, expand=True, controls=[
                    ft.Text(name, size=14, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE,
                            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Row(tight=True, spacing=5, controls=[
                        ft.Container(width=7, height=7, border_radius=4, bgcolor=ft.Colors.GREEN_400),
                        ft.Text("Nông dân", size=10, color=ft.Colors.WHITE60),
                    ]),
                ]),
            ],
        ),
    )

    txt_input = ft.TextField(
        ref=input_ref, hint_text="Trả lời nông dân...", expand=True,
        border_radius=20, min_lines=1, max_lines=4, shift_enter=True,
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
        border=ft.border.only(top=ft.BorderSide(1, ft.Colors.with_opacity(0.14, ft.Colors.WHITE))),
        content=ft.Row(
            spacing=4, vertical_alignment=ft.CrossAxisAlignment.END,
            controls=[
                ft.IconButton(icon=ft.Icons.IMAGE_OUTLINED, icon_color=_TEAL, icon_size=22,
                              tooltip="Gửi ảnh",
                              on_click=lambda e: picker.pick_files(
                                  allow_multiple=False, file_type=ft.FilePickerFileType.IMAGE,
                              )),
                txt_input,
                ft.Container(
                    width=40, height=40, border_radius=20, bgcolor=ft.Colors.TEAL_700,
                    alignment=ft.alignment.center, ink=True, on_click=_send_text,
                    content=ft.Icon(ft.Icons.SEND_ROUNDED, size=18, color=ft.Colors.WHITE),
                ),
            ],
        ),
    )

    content_area.content = ft.Column(
        expand=True, spacing=0,
        controls=[
            chat_header,
            ft.Container(expand=True, content=ft.ListView(
                ref=chat_list_ref, expand=True, spacing=8,
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
                controls=[build_chat_bubble(m, _on_analyze) for m in convo["messages"]],
                auto_scroll=True,
            )),
            _quick_reply_row(input_ref, page),
            input_bar,
        ],
    )
    _update()
