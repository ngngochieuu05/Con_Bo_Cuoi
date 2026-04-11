"""
Con Bò Cười — User Shell (Mobile Dark Theme)
Bottom Navigation + Header + Page Router
Designed for Android Phone (Flet APK)
"""
import flet as ft
from datetime import datetime
import threading
import time
import json
import os

from .page.phien_giam_sat       import PhienGiamSatPage
from .page.cai_dat              import CaiDatPage
from .page.tien_ich             import TienIchPage

try:
    from .page.thong_ke import ThongKePage as UserThongKe
except ImportError:
    UserThongKe = None

try:
    from .page.trang_chu import TrangChuUser
except ImportError:
    TrangChuUser = None

try:
    from .page.thong_tin_tai_khoan import ThongTinTaiKhoan
except ImportError:
    ThongTinTaiKhoan = None

from src.ui.theme import (
    BG_MAIN, BG_PANEL, BG_SIDEBAR, BG_HEADER,
    PRIMARY, SECONDARY, ACCENT,
    TEXT_MAIN, TEXT_SUB, TEXT_MUTED,
    BORDER, DANGER, WARNING,
    SIDEBAR_WIDTH, HEADER_HEIGHT,
    SIZE_BODY, SIZE_CAPTION,
    section_label, divider, avatar_initials,
    SUCCESS,
)

JSON_FILE = "src/ui/data/accounts.json"

MENU_ITEMS_DEF = [
    (ft.Icons.HOME_ROUNDED,      "Trang Chủ",          "home"),
    (ft.Icons.VIDEOCAM_ROUNDED,  "Giám Sát Trang Trại","monitor"),
    (ft.Icons.INSIGHTS_ROUNDED,  "Thống Kê",            "stats"),
    (ft.Icons.WIDGETS_ROUNDED,   "Tiện Ích",            "utilities"),
    (ft.Icons.TUNE_ROUNDED,      "Cài Đặt",             "settings"),
]


class FarmUserApp:
    def __init__(self, page: ft.Page, go_back_callback=None, user_account=None):
        self.page              = page
        self.go_back_callback  = go_back_callback
        self.menu_items        = {}
        self.current_page      = "home"
        self.running           = True

        # Load user info
        if user_account:
            self.user_info = user_account
            self.username  = user_account.get("username", "user01")
        else:
            self.username  = "user01"
            self.user_info = self._get_user_info(self.username)

        # ── Mobile (Android) page settings ──
        self.page.title      = "Con Bò Cười"
        self.page.padding    = 0
        from src.ui.theme import apply_theme
        apply_theme(self.page)
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor    = BG_MAIN
        # Phone-sized window for desktop testing; ignored on actual APK
        self.page.window_width      = 400
        self.page.window_height     = 780
        self.page.window_min_width  = 320
        self.page.window_min_height = 580
        self.page.window_resizable  = True

        self.content_area = ft.Container(
            expand=True,
            bgcolor=BG_MAIN,
        )
        self.nav_bar          = None
        self.sidebar_container = None  # kept for compat, unused on mobile

        self._build_ui()

    # ────────────────────────────────────────────────────────────────────────
    def _get_user_info(self, username: str) -> dict:
        default = {"name": "Nông Hộ", "driver_id": "N/A",
                   "username": username, "farm": "Trang trại của tôi"}
        for path in [JSON_FILE, "data/accounts.json"]:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    for u in data.get("user_accounts", []):
                        if u.get("username") == username:
                            return u
                except Exception:
                    pass
        return default

    def _start_clock(self):
        def _tick():
            while self.running:
                try:
                    self.time_text.value = datetime.now().strftime("%d/%m/%Y  %H:%M")
                    self.time_text.update()
                except Exception:
                    break
                time.sleep(1)
        threading.Thread(target=_tick, daemon=True).start()

    # ────────────────────────────────────────────────────────────────────────
    def _switch_page(self, e):
        """Sidebar click handler — kept for compatibility."""
        selected = e.control.data
        self.current_page = selected
        self.content_area.content = self._build_page(selected)
        try:
            self.content_area.update()
        except Exception:
            pass

    def _nav_change(self, e):
        """Bottom NavigationBar tab change."""
        idx = e.control.selected_index
        page_key = MENU_ITEMS_DEF[idx][2]
        self.current_page = page_key
        self.content_area.content = self._build_page(page_key)
        try:
            self.content_area.update()
        except Exception:
            pass

    def _open_notifications(self, e):
        """Hiển thị popup thông báo cho Nông Hộ."""
        notifications = [
            ("🚩 Sức khỏe bò", "Bò #B042 có dấu hiệu mệt mỏi", WARNING, "2 phút trước"),
            ("🐄 Hệ thống", "Hoàn thành kiểm kê đàn bò", SUCCESS, "1 giờ trước"),
            ("📸 Camera", "Phát hiện mục tiêu tại Chuồng 1", PRIMARY, "5 giờ trước"),
        ]
        
        items = []
        for title, subtitle, color, time_val in notifications:
            items.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.NOTIFICATIONS_ROUNDED, color=color),
                    title=ft.Text(title, weight=ft.FontWeight.BOLD, size=13),
                    subtitle=ft.Column([
                        ft.Text(subtitle, size=12, color=TEXT_SUB),
                        ft.Text(time_val, size=10, italic=True, color=TEXT_MUTED),
                    ], spacing=1),
                    content_padding=ft.padding.all(5),
                )
            )

        dialog = ft.AlertDialog(
            title=ft.Text("Thông báo nông trại", weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column(items, tight=True, spacing=0),
                width=350,
            ),
            actions=[
                ft.TextButton("Đóng", on_click=lambda _: self.page.close(dialog))
            ],
        )
        self.page.open(dialog)

    def _refresh_page(self):
        """Làm mới nội dung trang hiện tại."""
        self.content_area.content = self._build_page(self.current_page)
        self.content_area.update()

    def _build_page(self, name: str):
        if name == "home":
            return TrangChuUser(self.user_info, on_refresh=lambda _: self._refresh_page()) if TrangChuUser else _placeholder("Trang Chủ")
        elif name == "monitor":
            return PhienGiamSatPage(user_account=self.user_info)
        elif name == "stats":
            return UserThongKe() if UserThongKe else _placeholder("Thống Kê")
        elif name == "utilities":
            try:
                from src.ui.user.control.page.tien_ich import TienIchPage
                return TienIchPage()
            except Exception as e:
                import traceback; traceback.print_exc()
                return _placeholder(f"Lỗi: {e}")
        elif name == "settings":
            return CaiDatPage(
                page=self.page,
                current_username=self.username,
                on_plan_changed=self._reload_sidebar,
            )
        elif name == "profile":
            def _back_from_profile():
                self.content_area.content = self._build_page(self.current_page)
                try:
                    self.content_area.update()
                except Exception:
                    pass
            return (ThongTinTaiKhoan(username=self.username, on_back=_back_from_profile)
                    if ThongTinTaiKhoan else _placeholder("Hồ Sơ"))
        return _placeholder(name)

    # ────────────────────────────────────────────────────────────────────────
    def _menu_item(self, icon, text: str, page_name: str) -> ft.Container:
        is_active = (page_name == self.current_page)
        item = ft.Container(
            content=ft.Row([
                ft.Icon(icon,
                        color=PRIMARY if is_active else TEXT_SUB,
                        size=18),
                ft.Text(text,
                        color=TEXT_MAIN if is_active else TEXT_SUB,
                        size=SIZE_BODY,
                        weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.W_400),
            ], spacing=12),
            padding=ft.padding.symmetric(vertical=11, horizontal=14),
            border_radius=10,
            ink=True,
            on_click=self._switch_page,
            data=page_name,
            bgcolor=ft.Colors.with_opacity(0.12, PRIMARY) if is_active else None,
            border=ft.border.only(
                left=ft.BorderSide(3, PRIMARY if is_active else "transparent")
            ),
        )
        self.menu_items[page_name] = item
        return item

    # ────────────────────────────────────────────────────────────────────────
    def _build_sidebar_column(self) -> ft.Column:
        info  = self.user_info
        name  = info.get("name", "Nông Hộ")
        uid   = info.get("driver_id", info.get("username", "N/A"))
        farm  = info.get("farm", "Trang trại của tôi")

        # User profile block
        profile = ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Text(name[0].upper(), color=ft.Colors.WHITE,
                                    size=22, weight=ft.FontWeight.BOLD),
                    width=60, height=60, border_radius=30,
                    bgcolor=ft.Colors.with_opacity(0.2, PRIMARY),
                    border=ft.border.all(2, PRIMARY),
                    alignment=ft.alignment.center,
                ),
                ft.Container(height=8),
                ft.Text(name, color=TEXT_MAIN, weight=ft.FontWeight.BOLD,
                        size=14, text_align=ft.TextAlign.CENTER),
                ft.Text(f"ID: {uid}", color=TEXT_SUB, size=10),
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.AGRICULTURE_ROUNDED, size=10, color=PRIMARY),
                        ft.Text(farm, size=10, color=PRIMARY,
                                weight=ft.FontWeight.W_500),
                    ], spacing=4, tight=True),
                    bgcolor=ft.Colors.with_opacity(0.1, PRIMARY),
                    border_radius=SIDEBAR_WIDTH,
                    padding=ft.padding.symmetric(horizontal=10, vertical=4),
                ),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
            padding=ft.padding.symmetric(vertical=20, horizontal=10),
            alignment=ft.alignment.center,
        )

        items = [
            # Logo minimal
            ft.Container(
                content=ft.Row([
                    ft.Text("🐄", size=20),
                    ft.Text("Con Bò Cười", size=13,
                            weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                ], spacing=8),
                padding=ft.padding.symmetric(horizontal=14, vertical=14),
            ),
            ft.Divider(color=BORDER, height=1),
            profile,
            ft.Divider(color=BORDER, height=1),
            section_label("CHỨC NĂNG"),
            *[self._menu_item(ic, lb, pg)
              for ic, lb, pg in MENU_ITEMS_DEF],
            ft.Container(expand=True),
            ft.Divider(color=BORDER, height=1),
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.LOGOUT_ROUNDED, color=DANGER, size=18),
                    ft.Text("Đăng Xuất", color=DANGER, size=SIZE_BODY,
                            weight=ft.FontWeight.W_500),
                ], spacing=10),
                padding=ft.padding.symmetric(vertical=12, horizontal=14),
                border_radius=10, ink=True,
                on_click=lambda e: self._logout(),
            ),
            ft.Container(height=8),
        ]

        return ft.Column(items, spacing=2, expand=True, scroll=ft.ScrollMode.AUTO)

    # ────────────────────────────────────────────────────────────────────────
    def _reload_sidebar(self):
        self.user_info = self._get_user_info(self.username)
        if self.sidebar_container:
            self.sidebar_container.content = self._build_sidebar_column()
            try:
                self.sidebar_container.update()
            except Exception:
                pass

    def _build_header(self) -> ft.Container:
        name = self.user_info.get("name", "Nông Hộ")
        farm = self.user_info.get("farm", "Trang trại")
        return ft.Container(
            height=54,
            bgcolor=BG_HEADER,
            border=ft.border.only(bottom=ft.BorderSide(1, BORDER)),
            content=ft.Row([
                # Brand
                ft.Row([
                    ft.Text("🐄", size=22),
                    ft.Column([
                        ft.Text("FarmVision AI",
                                size=13, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                        ft.Text(farm, size=10, color=TEXT_SUB),
                    ], spacing=0),
                ], spacing=8),
                # Actions
                ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.NOTIFICATIONS_NONE_ROUNDED,
                        icon_color=TEXT_SUB,
                        icon_size=22,
                        on_click=self._open_notifications,
                        tooltip="Thông báo",
                    ),
                    ft.GestureDetector(
                        content=avatar_initials(name, size=34),
                        on_tap=self._go_to_profile,
                    ),
                ], spacing=4),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=ft.padding.symmetric(horizontal=16),
        )

    # ────────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        header = self._build_header()

        # Default page
        self.content_area.content = (
            TrangChuUser(self.user_info) if TrangChuUser
            else PhienGiamSatPage(user_account=self.user_info)
        )

        # ── Mobile: Bottom Navigation Bar ──
        self.nav_bar = ft.NavigationBar(
            destinations=[
                ft.NavigationBarDestination(
                    icon=ic,
                    selected_icon=ic,
                    label=lb,
                )
                for ic, lb, _ in MENU_ITEMS_DEF
            ],
            selected_index=0,
            on_change=self._nav_change,
            bgcolor=BG_SIDEBAR,
            indicator_color=ft.Colors.with_opacity(0.15, PRIMARY),
            label_behavior=ft.NavigationBarLabelBehavior.ALWAYS_SHOW,
        )

        layout = ft.Column([
            header,
            self.content_area,
            self.nav_bar,
        ], spacing=0, expand=True)

        self.page.add(layout)

    # ────────────────────────────────────────────────────────────────────────
    def _logout(self):
        self.running = False
        if self.go_back_callback:
            self.page.controls.clear()
            self.page.update()
            self.go_back_callback()

    def _go_to_profile(self, e=None):
        """Click avatar → trang hồ sơ cá nhân."""
        def _back():
            self.content_area.content = self._build_page(self.current_page)
            try:
                self.content_area.update()
            except Exception:
                pass
        page_content = (
            ThongTinTaiKhoan(username=self.username, on_back=_back)
            if ThongTinTaiKhoan else _placeholder("Hồ Sơ")
        )
        self.content_area.content = page_content
        try:
            self.content_area.update()
        except Exception:
            pass

    def _reload_sidebar(self):
        self.user_info = self._get_user_info(self.username)
        if self.sidebar_container:
            self.sidebar_container.content = self._build_sidebar_column()
            try:
                self.sidebar_container.update()
            except Exception:
                pass

    def handle_logout(self, e):
        self._logout()



# ────────────────────────────────────────────────────────────────────────────
def _placeholder(name: str) -> ft.Container:
    return ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.CONSTRUCTION_ROUNDED, size=48, color=TEXT_SUB),
            ft.Text(f"Trang «{name}» đang phát triển",
                    size=16, color=TEXT_SUB, italic=True),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
           alignment=ft.MainAxisAlignment.CENTER),
        expand=True,
        alignment=ft.alignment.center,
    )


SIDEBAR_WIDTH = 235  # reuse local


def main(page: ft.Page, go_back_callback=None, user_account=None):
    FarmUserApp(page, go_back_callback, user_account)


if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.FLET_APP)