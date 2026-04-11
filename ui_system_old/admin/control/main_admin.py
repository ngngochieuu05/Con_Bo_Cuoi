"""
Con Bò Cười — Admin Shell (Dark Theme)
Sidebar + Header + Page Router
"""
import flet as ft
from datetime import datetime
import threading
import time

from .page.trang_chu    import TrangChu
from .page.quan_li_tai_khoan import QuanLiTaiKhoan
from .page.quan_li_model_login  import QuanLiModel as QuanLiModelLogin
from .page.cai_dat           import CaiDatPage
from .page.quan_li_thong_bao_OA import QuanLiThongBao
from .page.thong_tin_tai_khoan import ThongTinTaiKhoan

try:
    from .page.thong_ke import ThongKePage
except ImportError:
    ThongKePage = None

from src.ui.theme import (
    BG_MAIN, BG_PANEL, BG_SIDEBAR, BG_HEADER,
    PRIMARY, SECONDARY, ACCENT,
    TEXT_MAIN, TEXT_SUB, TEXT_MUTED,
    BORDER, HOVER_OVERLAY,
    DANGER, WARNING, SUCCESS,
    SIDEBAR_WIDTH, HEADER_HEIGHT,
    RADIUS_CARD, SIZE_BODY, SIZE_CAPTION,
    section_label, divider, avatar_initials,
)

# ─── Menu definition ────────────────────────────────────────────────────────
MENU_GROUPS = [
    {
        "label": "TỔNG QUAN",
        "items": [
            (ft.Icons.DASHBOARD_ROUNDED,    "Bảng Điều Khiển",   "dashboard"),
            (ft.Icons.BAR_CHART_ROUNDED,    "Thống Kê",          "statistics"),
        ],
    },
    {
        "label": "QUẢN LÝ",
        "items": [
            (ft.Icons.PEOPLE_ALT_ROUNDED,   "Quản Lý Tài Khoản", "customers"),
        ],
    },
    {
        "label": "HỆ THỐNG",
        "items": [
            (ft.Icons.FINGERPRINT_ROUNDED,  "Model Sinh Trắc Học", "login_models"),
            (ft.Icons.CAMPAIGN_OUTLINED,    "Bot Thông Báo OA",  "notifications"),
            (ft.Icons.SETTINGS_ROUNDED,     "Cài Đặt",           "settings"),
        ],
    },
]


class FarmAdminApp:
    def __init__(self, page: ft.Page, go_back_callback=None):
        self.page              = page
        self.go_back_callback  = go_back_callback
        self.menu_items        = {}
        self.current_page      = "dashboard"
        self.running           = True

        # ── Page settings ──
        self.page.title      = "Con Bò Cười — Admin"
        self.page.padding    = 0
        from src.ui.theme import apply_theme
        apply_theme(self.page)
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor    = BG_MAIN
        self.page.window_width      = 1400
        self.page.window_height     = 860
        self.page.window_min_width  = 1100
        self.page.window_min_height = 700
        self.page.window_resizable  = True

        # ── Shared controls ──
        self.time_text    = ft.Text("", size=SIZE_CAPTION, color=TEXT_SUB,
                                    weight=ft.FontWeight.W_500)
        self.content_area = ft.Container(
            expand=True,
            padding=ft.padding.symmetric(horizontal=20, vertical=16),
            bgcolor=BG_MAIN,
        )

        self._build_ui()
        self._start_clock()

    # ────────────────────────────────────────────────────────────────────────
    def _start_clock(self):
        def _tick():
            while self.running:
                try:
                    self.time_text.value = datetime.now().strftime("%d/%m/%Y  %H:%M:%S")
                    self.time_text.update()
                except Exception:
                    break
                time.sleep(1)
        threading.Thread(target=_tick, daemon=True).start()

    # ────────────────────────────────────────────────────────────────────────
    def _switch_page(self, e):
        selected = e.control.data

        # Bỏ highlight cũ
        if self.current_page in self.menu_items:
            old = self.menu_items[self.current_page]
            old.bgcolor = None
            old.border  = ft.border.only(left=ft.BorderSide(3, "transparent"))
            old.update()

        self.current_page = selected

        # Highlight mới
        if selected in self.menu_items:
            new = self.menu_items[selected]
            new.bgcolor = ft.Colors.with_opacity(0.12, PRIMARY)
            new.border  = ft.border.only(left=ft.BorderSide(3, PRIMARY))
            new.update()

        # Render page
        self.content_area.content = self._build_page(selected)
        self.content_area.update()

    def _switch_page_by_name(self, name: str):
        class DummyEvent:
            def __init__(self, data):
                self.control = type("DummyControl", (), {"data": data})()
        if name == "profile":
            # Profile is not in sidebar menu, so just render it
            if self.current_page in self.menu_items:
                old = self.menu_items[self.current_page]
                old.bgcolor = None
                old.border  = ft.border.only(left=ft.BorderSide(3, "transparent"))
                old.update()
            
            self.content_area.content = self._build_page(name)
            self.content_area.update()
        else:
            self._switch_page(DummyEvent(name))

    def _open_notifications(self, e):
        """Hiển thị popup thông báo hệ thống."""
        notifications = [
            ("🚩 Cảnh báo hành vi", "Bò C001 có dấu hiệu bất thường", WARNING, "2 phút trước"),
            ("✅ Hệ thống", "Cập nhật model login thành công", SUCCESS, "1 giờ trước"),
            ("🐄 Thiết bị", "Camera khu vực 2 đã kết nối", PRIMARY, "3 giờ trước"),
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
            title=ft.Text("Thông báo hệ thống", weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column(items, tight=True, spacing=0),
                width=350,
            ),
            actions=[
                ft.TextButton("Đóng", on_click=lambda _: self.page.close(dialog))
            ],
        )
        self.page.open(dialog)

    def _build_page(self, name: str):
        if name == "dashboard":
            return TrangChu()
        elif name == "statistics":
            return ThongKePage() if ThongKePage else _placeholder("Thống Kê")
        elif name == "customers":
            return QuanLiTaiKhoan()
        elif name == "login_models":
            return QuanLiModelLogin("Quản lý Model Sinh Trắc Học", self.page)
        elif name == "notifications":
            return QuanLiThongBao("Bot Thông Báo OA")
        elif name == "settings":
            return CaiDatPage()
        elif name == "profile":
            return ThongTinTaiKhoan(username="admin", on_back=lambda: self._switch_page_by_name(self.current_page))
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
            animate_opacity=ft.Animation(150, ft.AnimationCurve.EASE_IN_OUT),
        )
        self.menu_items[page_name] = item
        return item

    # ────────────────────────────────────────────────────────────────────────
    def _build_sidebar(self) -> ft.Container:
        # Logo block
        logo = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        content=ft.Text("🐄", size=24),
                        width=44, height=44,
                        bgcolor=ft.Colors.with_opacity(0.12, PRIMARY),
                        border_radius=12,
                        alignment=ft.alignment.center,
                    ),
                    ft.Column([
                        ft.Text("Con Bò Cười", size=15,
                                weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                        ft.Text("ADMIN PANEL", size=9, color=PRIMARY,
                                style=ft.TextStyle(letter_spacing=1.5),
                                weight=ft.FontWeight.BOLD),
                    ], spacing=0),
                ], spacing=10),
                ft.Container(height=4),
                # Online indicator
                ft.Row([
                    ft.Container(
                        width=7, height=7, border_radius=4,
                        bgcolor=PRIMARY,
                        shadow=ft.BoxShadow(blur_radius=6,
                                            color=ft.Colors.with_opacity(0.6, PRIMARY)),
                    ),
                    ft.Text("Hệ thống trực tuyến", size=10, color=TEXT_SUB),
                ], spacing=6),
            ], spacing=6),
            padding=ft.padding.symmetric(horizontal=16, vertical=18),
        )

        # Menu groups
        sidebar_items = [
            logo,
            ft.Divider(color=BORDER, height=1),
        ]

        for group in MENU_GROUPS:
            sidebar_items.append(section_label(group["label"]))
            for icon, label, name in group["items"]:
                sidebar_items.append(self._menu_item(icon, label, name))
            sidebar_items.append(ft.Container(height=4))

        # Spacer + logout
        sidebar_items.append(ft.Container(expand=True))
        sidebar_items.append(ft.Divider(color=BORDER, height=1))
        sidebar_items.append(
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.LOGOUT_ROUNDED, color=DANGER, size=18),
                    ft.Text("Đăng Xuất", color=DANGER, size=SIZE_BODY,
                            weight=ft.FontWeight.W_500),
                ], spacing=10),
                padding=ft.padding.symmetric(vertical=12, horizontal=14),
                border_radius=10, ink=True,
                on_click=lambda e: self._logout(),
            )
        )
        sidebar_items.append(ft.Container(height=8))

        return ft.Container(
            width=SIDEBAR_WIDTH,
            bgcolor=BG_SIDEBAR,
            content=ft.Column(sidebar_items, spacing=2,
                               scroll=ft.ScrollMode.AUTO, expand=True),
            border=ft.border.only(right=ft.BorderSide(1, BORDER)),
        )

    # ────────────────────────────────────────────────────────────────────────
    def _build_header(self) -> ft.Container:
        return ft.Container(
            height=HEADER_HEIGHT,
            bgcolor=BG_HEADER,
            border=ft.border.only(bottom=ft.BorderSide(1, BORDER)),
            content=ft.Row([
                # Left: page title area
                ft.Row([
                    ft.Icon(ft.Icons.GRASS_ROUNDED, color=PRIMARY, size=20),
                    ft.Text("Con Bò Cười  ·  Admin",
                            size=15, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                ], spacing=8),

                # Right: clock + bell + avatar
                ft.Row([
                    # Clock chip
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.ACCESS_TIME_ROUNDED,
                                    size=13, color=TEXT_SUB),
                            self.time_text,
                        ], spacing=5),
                        bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
                        border_radius=20, border=ft.border.all(1, BORDER),
                        padding=ft.padding.symmetric(horizontal=12, vertical=5),
                    ),
                    # Bell
                    ft.Container(
                        content=ft.Stack([
                            ft.Icon(ft.Icons.NOTIFICATIONS_NONE_ROUNDED,
                                    color=TEXT_SUB, size=22),
                            ft.Container(
                                content=ft.Text("3", size=8,
                                                color=ft.Colors.WHITE,
                                                weight=ft.FontWeight.BOLD),
                                bgcolor=DANGER, border_radius=8,
                                width=14, height=14,
                                alignment=ft.alignment.center,
                                right=0, top=0,
                            ),
                        ]),
                        width=36, height=36,
                        border_radius=18,
                        ink=True,
                        alignment=ft.alignment.center,
                        on_click=self._open_notifications,
                    ),
                    # Avatar + name
                    ft.Container(
                        content=ft.Row([
                            avatar_initials("Admin", size=34),
                            ft.Column([
                                ft.Text("Admin", size=12,
                                        color=TEXT_MAIN, weight=ft.FontWeight.W_600),
                                ft.Text("Quản trị viên", size=10, color=TEXT_SUB),
                            ], spacing=0),
                            ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED,
                                    color=TEXT_SUB, size=16),
                        ], spacing=8),
                        padding=ft.padding.symmetric(horizontal=10, vertical=4),
                        border_radius=10, ink=True,
                        border=ft.border.all(1, BORDER),
                        bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.WHITE),
                        on_click=lambda e: self._switch_page_by_name("profile"),
                    ),
                ], spacing=10),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=ft.padding.symmetric(horizontal=20),
        )

    # ────────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        sidebar = self._build_sidebar()
        header  = self._build_header()

        # Default page
        self.content_area.content = TrangChu()

        layout = ft.Row([
            sidebar,
            ft.Column([
                header,
                self.content_area,
            ], expand=True, spacing=0),
        ], expand=True, spacing=0)

        self.page.add(layout)

    # ────────────────────────────────────────────────────────────────────────
    def _logout(self):
        self.running = False
        if self.go_back_callback:
            self.page.controls.clear()
            self.page.update()
            self.go_back_callback()

    def go_back(self):
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


def main(page: ft.Page, go_back_callback=None):
    FarmAdminApp(page, go_back_callback)


if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.FLET_APP)