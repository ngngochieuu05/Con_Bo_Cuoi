"""
Expert — Tư vấn (orchestrator + conversation list)
Chat view is delegated to consulting_chat.py.
"""
from __future__ import annotations
import datetime
import flet as ft
from bll.services import chat_service
from ui.components.user.expert.consulting_chat import show_chat_view

_TEAL = ft.Colors.TEAL_300

_SEED_CONVOS = [
    {"farmer_id": 101, "farmer_name": "Trần Thị Nông", "unread": 2, "messages": [
        {"sender": "farmer", "text": "Chào chuyên gia! Con bò của tôi đang có dấu hiệu bất thường.", "time": "08:12"},
        {"sender": "expert", "text": "Chào bạn! Bạn có thể mô tả cụ thể hơn hoặc gửi ảnh cho tôi xem.", "time": "08:14"},
        {"sender": "farmer", "text": "Con bò bị sưng chân và ăn ít hơn bình thường từ hôm qua.", "time": "08:15"},
    ]},
    {"farmer_id": 102, "farmer_name": "Nguyễn Văn Hùng", "unread": 0, "messages": [
        {"sender": "farmer", "text": "Cho tôi hỏi về bệnh lở mồm long móng ạ.", "time": "07:30"},
        {"sender": "expert", "text": "Bệnh lở mồm long móng (FMD) là bệnh virus rất dễ lây. Cần cách ly ngay và báo thú y.", "time": "07:45"},
        {"sender": "farmer", "text": "Cảm ơn chuyên gia nhiều!", "time": "07:46"},
    ]},
    {"farmer_id": 103, "farmer_name": "Lê Thị Mai", "unread": 1, "messages": [
        {"sender": "farmer", "text": "Bò nhà tôi ho nhiều và chảy nước mũi.", "time": "09:00"},
    ]},
]


def _now() -> str:
    return datetime.datetime.now().strftime("%H:%M")


def build_consulting_review(page: ft.Page = None):  # noqa: C901
    expert_id = int((page.client_storage.get("user_id") or 0) if page else 0)

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

    content_area = ft.Container(expand=True)

    def _update():
        if page:
            try:
                page.update()
            except Exception:
                pass

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
            on_click=lambda e, c=convo: show_chat_view(content_area, c, page, _show_list),
            content=ft.Row(
                spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Stack(width=46, height=46, controls=[
                        ft.Container(
                            width=46, height=46, border_radius=23,
                            bgcolor=ft.Colors.with_opacity(0.26, ft.Colors.BLUE_300),
                            alignment=ft.alignment.center,
                            content=ft.Text(initial, size=16, weight=ft.FontWeight.W_700,
                                            color=ft.Colors.BLUE_100),
                        ),
                        ft.Container(
                            right=0, top=0, width=18, height=18, border_radius=9,
                            bgcolor=ft.Colors.RED_400, alignment=ft.alignment.center,
                            visible=unread > 0,
                            content=ft.Text(str(unread), size=9, color=ft.Colors.WHITE,
                                            weight=ft.FontWeight.W_700),
                        ),
                    ]),
                    ft.Column(
                        expand=True, spacing=3, tight=True,
                        controls=[
                            ft.Row(controls=[
                                ft.Text(
                                    name, size=14,
                                    weight=ft.FontWeight.W_700 if unread else ft.FontWeight.W_500,
                                    color=ft.Colors.WHITE if unread else ft.Colors.WHITE70,
                                    expand=True, max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                ft.Text(last.get("time", ""), size=10, color=ft.Colors.WHITE38),
                            ]),
                            ft.Text(
                                preview, size=12,
                                weight=ft.FontWeight.W_600 if unread else ft.FontWeight.NORMAL,
                                color=ft.Colors.WHITE70 if unread else ft.Colors.WHITE38,
                                max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                    ),
                ],
            ),
        )

    def _show_list():
        convos       = chat_service.list_conversations_for_expert(expert_id)
        total_unread = sum(c.get("unread_expert", 0) for c in convos)

        items = [_list_item(c) for c in convos] if convos else [
            ft.Container(
                padding=ft.padding.all(40), alignment=ft.alignment.center,
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12,
                    controls=[
                        ft.Icon(ft.Icons.CHAT_BUBBLE_OUTLINE, size=52, color=ft.Colors.WHITE24),
                        ft.Text("Chưa có hội thoại nào", size=14, color=ft.Colors.WHITE38),
                    ],
                ),
            )
        ]

        list_header = ft.Container(
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.WHITE),
            border=ft.border.only(
                bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.10, ft.Colors.WHITE))
            ),
            content=ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.FORUM_OUTLINED, size=20, color=_TEAL),
                    ft.Container(width=8),
                    ft.Text("Hội thoại tư vấn", size=16, weight=ft.FontWeight.W_700,
                            color=ft.Colors.WHITE, expand=True),
                    ft.Container(
                        width=22, height=22, border_radius=11,
                        bgcolor=ft.Colors.RED_400, alignment=ft.alignment.center,
                        visible=total_unread > 0,
                        content=ft.Text(str(total_unread), size=10, color=ft.Colors.WHITE,
                                        weight=ft.FontWeight.W_700),
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

    _show_list()
    return content_area
