import flet as ft

from ui.components.user.framer.dashboard import build_farmer_dashboard
from ui.components.user.framer.health_consulting import build_health_consulting
from ui.components.user.framer.live_monitoring import build_live_monitoring
from ui.components.user.framer.profile_farmer import build_profile_farmer
from ui.components.user.framer.session_history import build_session_history
from ui.components.user.framer.settings import build_farmer_settings
from ui.components.user.framer.utilities import build_farmer_utilities
from ui.theme import build_role_shell


def FarmerMainScreen(page: ft.Page, on_logout=None):
    views = {
        "dashboard": build_farmer_dashboard,
        "monitoring": build_live_monitoring,
        "consulting": build_health_consulting,
        "history": build_session_history,
        "utilities": build_farmer_utilities,
        "settings": build_farmer_settings,
    }
    navigation_items = [
        ("dashboard", "Tổng quan", "DASHBOARD"),
        ("monitoring", "Giám sát", "LIVE_TV"),
        ("consulting", "Tư vấn", "HEALTH_AND_SAFETY"),
        ("history", "Lịch sử", "HISTORY"),
        ("utilities", "Tiện ích", "BUILD"),
        ("settings", "Cài đặt", "SETTINGS"),
    ]
    selected = {"key": "monitoring"}
    content_holder = ft.Container(expand=True)
    root = ft.Container(expand=True)

    def select_view(key: str):
        selected["key"] = key
        render()

    def render():
        if selected["key"] == "profile":
            content_holder.content = build_profile_farmer(page, on_back=lambda: select_view("monitoring"))
        elif selected["key"] == "settings":
            content_holder.content = build_farmer_settings(on_logout=on_logout)
        elif selected["key"] == "consulting":
            content_holder.content = build_health_consulting(page=page)
        else:
            content_holder.content = views.get(selected["key"], build_farmer_dashboard)()
        root.content = build_role_shell(
            role_title="NGƯỜI DÙNG",
            role_subtitle="Giám sát hành vi bò từ camera",
            navigation_items=navigation_items,
            selected_key=selected["key"],
            on_select=select_view,
            main_content=content_holder,
            on_logout=on_logout or (lambda: None),
            on_profile=lambda: select_view("profile"),
            page=page,
        )
        try:
            if root.page:
                root.update()
        except RuntimeError:
            pass

    render()
    return root
