import flet as ft

from ui.components.user.framer.dashboard import build_farmer_dashboard
from ui.components.user.framer.health_consulting import build_health_consulting
from ui.components.user.framer.live_monitoring import build_live_monitoring
from ui.components.user.framer.notification_history import build_notification_history
from ui.components.user.framer.profile_farmer import build_profile_farmer
from ui.components.user.framer.session_history import build_session_history
from ui.components.user.framer.settings import build_farmer_settings
from ui.components.user.framer.utilities import build_farmer_utilities
from ui.theme import build_role_shell


def FarmerMainScreen(page: ft.Page, on_logout=None):
    views = {
        "dashboard": lambda: build_farmer_dashboard(page),
        "monitoring": build_live_monitoring,
        "consulting": build_health_consulting,
        "history": lambda: build_session_history(page),
        "notifications": lambda: build_notification_history(page),
        "utilities": lambda: build_farmer_utilities(page=page, on_navigate=select_view),
        "settings": build_farmer_settings,
    }
    navigation_items = [
        ("dashboard", "Tổng quan", "DASHBOARD"),
        ("monitoring", "Giám sát", "LIVE_TV"),
        ("consulting", "Tư vấn", "HEALTH_AND_SAFETY"),
        ("notifications", "Thông báo", "NOTIFICATIONS"),
        ("history", "Lịch sử", "HISTORY"),
        ("utilities", "Tiện ích", "BUILD"),
        ("settings", "Cài đặt", "SETTINGS"),
    ]
    selected = {"key": "dashboard"}
    content_holder = ft.Container(expand=True)
    root = ft.Container(expand=True)
    _ctrl_cache: dict = {}

    def select_view(key: str):
        if selected["key"] == "monitoring" and key != "monitoring":
            if "monitoring" in _ctrl_cache:
                try:
                    _ctrl_cache["monitoring"].stop_stream()
                except Exception:
                    pass
        selected["key"] = key
        render()


    def render():
        if selected["key"] == "profile":
            content_holder.content = build_profile_farmer(page, on_back=lambda: select_view("dashboard"))
        elif selected["key"] == "settings":
            content_holder.content = build_farmer_settings(on_logout=on_logout, page=page)
        elif selected["key"] == "consulting":
            content_holder.content = build_health_consulting(page=page)
        elif selected["key"] == "notifications":
            content_holder.content = build_notification_history(page)
        elif selected["key"] == "monitoring":
            if "monitoring" not in _ctrl_cache:
                from ui.components.user.framer.live_monitoring import LiveMonitoringController
                _ctrl_cache["monitoring"] = LiveMonitoringController(page)
            content_holder.content = _ctrl_cache["monitoring"].root
        elif selected["key"] == "utilities":
            content_holder.content = build_farmer_utilities(page=page, on_navigate=select_view)
        elif selected["key"] == "history":
            content_holder.content = build_session_history(page)
        else:
            content_holder.content = views.get(selected["key"], lambda: build_farmer_dashboard(page))()
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
