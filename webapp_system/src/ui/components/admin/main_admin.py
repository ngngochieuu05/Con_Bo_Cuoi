import flet as ft

from ui.components.admin.dashboard import build_admin_dashboard
from ui.components.admin.model_management import build_model_management
from ui.components.admin.oa_management import build_oa_management
from ui.components.admin.profile_admin import build_profile_admin
from ui.components.admin.settings import build_admin_settings
from ui.components.admin.user_management import build_user_management
from ui.theme import build_role_shell


def AdminMainScreen(page: ft.Page, on_logout=None):
    views = {
        "dashboard": build_admin_dashboard,
        "users": build_user_management,
        "models": build_model_management,
        "analytics": build_oa_management,
        "settings": build_admin_settings,
    }
    navigation_items = [
        ("dashboard", "Tổng quan", "DASHBOARD"),
        ("users", "Tài khoản", "GROUP"),
        ("models", "Mô hình", "SMART_TOY"),
        ("analytics", "Thống kê", "ANALYTICS"),
        ("settings", "Cài đặt", "SETTINGS"),
    ]
    selected = {"key": "dashboard"}
    content_holder = ft.Container(expand=True)
    root = ft.Container(expand=True)

    def select_view(key: str):
        selected["key"] = key
        render()

    def render():
        view_builder = views.get(selected["key"], build_admin_dashboard)
        if selected["key"] == "profile":
            content_holder.content = build_profile_admin(page, on_back=lambda: select_view("dashboard"))
        elif selected["key"] == "settings":
            content_holder.content = build_admin_settings(on_logout=on_logout)
        else:
            content_holder.content = view_builder()
        root.content = build_role_shell(
            role_title="QUẢN TRỊ",
            role_subtitle="Trung tâm điều hành hệ thống",
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
