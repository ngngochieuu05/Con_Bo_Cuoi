import flet as ft

from ui.components.user.expert.consulting_review import build_consulting_review
from ui.components.user.expert.dashboard import build_expert_dashboard
from ui.components.user.expert.profile_expert import build_profile_expert
from ui.components.user.expert.raw_data_review import build_raw_data_review
from ui.components.user.expert.settings import build_expert_settings
from ui.components.user.expert.utilities import build_expert_utilities
from ui.theme import build_role_shell


def ExpertMainScreen(page: ft.Page, on_logout=None):
    views = {
        "dashboard": build_expert_dashboard,
        "raw_data": build_raw_data_review,
        "consulting": build_consulting_review,
        "utilities": build_expert_utilities,
        "settings": build_expert_settings,
    }
    navigation_items = [
        ("dashboard", "Tổng quan", "DASHBOARD"),
        ("raw_data", "Dữ liệu", "FACT_CHECK"),
        ("consulting", "Tư vấn", "RECORD_VOICE_OVER"),
        ("utilities", "Tiện ích", "BUILD"),
        ("settings", "Cài đặt", "SETTINGS"),
    ]
    selected = {"key": "dashboard"}
    content_holder = ft.Container(expand=True)
    root = ft.Container(expand=True)

    def select_view(key: str):
        selected["key"] = key
        render()

    def render():
        if selected["key"] == "profile":
            content_holder.content = build_profile_expert(page, on_back=lambda: select_view("dashboard"))
        elif selected["key"] == "settings":
            content_holder.content = build_expert_settings(on_logout=on_logout)
        elif selected["key"] == "consulting":
            content_holder.content = build_consulting_review(page=page)
        else:
            content_holder.content = views.get(selected["key"], build_expert_dashboard)()
        root.content = build_role_shell(
            role_title="CHUYÊN GIA",
            role_subtitle="Đánh giá và tư vấn chuyên môn",
            navigation_items=navigation_items,
            selected_key=selected["key"],
            on_select=select_view,
            main_content=content_holder,
            on_logout=on_logout or (lambda: None),
            on_profile=lambda: select_view("profile"),
            page=page,
        )
        if root.page:
            root.update()

    render()
    return root
