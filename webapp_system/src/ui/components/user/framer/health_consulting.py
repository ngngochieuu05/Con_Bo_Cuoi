from __future__ import annotations

import flet as ft

from .health_consulting_ai_chat import make_ai_chat
from .health_consulting_expert_chat import make_expert_chat
from .health_consulting_selection import make_selection_screen


def build_health_consulting(page: ft.Page = None):
    content_area = ft.Container(expand=True)

    def _update():
        if page and content_area.page:
            try:
                page.update()
            except Exception:
                pass

    def _show_selection():
        content_area.content = make_selection_screen(_show_ai_chat, _show_expert_chat)
        _update()

    def _show_ai_chat():
        content_area.content = make_ai_chat(page, on_back=_show_selection)
        _update()

    def _show_expert_chat():
        content_area.content = make_expert_chat(page, on_back=_show_selection)
        _update()

    _show_selection()

    return ft.Column(expand=True, spacing=0, controls=[content_area])
