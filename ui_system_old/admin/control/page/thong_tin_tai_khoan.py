"""
Thông Tin Tài Khoản — User
Hồ Sơ Cá Nhân — Con Bò Cười Dark Theme
"""
import flet as ft
import json
import os
from datetime import datetime

from src.ui.theme import (
    BG_MAIN, BG_PANEL, PRIMARY, SECONDARY, ACCENT,
    TEXT_MAIN, TEXT_SUB, TEXT_MUTED,
    WARNING, DANGER, SUCCESS, BORDER,
    RADIUS_CARD, RADIUS_BTN, RADIUS_INPUT,
    SIZE_H1, SIZE_H2, SIZE_H3, SIZE_BODY, SIZE_CAPTION,
    SHADOW_CARD_GLOW, PAD_CARD,
    panel, primary_button, styled_input, avatar_initials,
    GRAD_TEAL,
)

JSON_FILE = "src/ui/data/accounts.json"


class ThongTinTaiKhoan(ft.Column):
    """Trang thông tin & chỉnh sửa hồ sơ cá nhân."""

    def __init__(self, username: str = "user01", on_back=None):
        super().__init__(expand=True, scroll=ft.ScrollMode.AUTO, spacing=0)
        self.username = username
        self.on_back  = on_back
        self.user_data = self._load_user()
        self._build()

    # ── Load ─────────────────────────────────────────────────────────────────
    def _load_user(self) -> dict:
        default = {
            "username": self.username,
            "name": "Admin",
            "phone": "",
            "email": "",
            "farm": "Con Bò Cười",
            "role": "Quản trị viên",
            "created_at": datetime.now().strftime("%d/%m/%Y"),
        }
        for path in [JSON_FILE, "data/accounts.json"]:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    # Check admin first since this is admin page
                    for u in data.get("admin_accounts", []):
                        if u.get("username") == self.username:
                            return {**default, **u}
                    # Then check users
                    for u in data.get("user_accounts", []):
                        if u.get("username") == self.username:
                            return {**default, **u}
                except Exception:
                    pass
        return default

    def _save_user(self, new_data: dict) -> bool:
        for path in [JSON_FILE, "data/accounts.json"]:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    saved = False
                    # Update admin_accounts
                    admins = data.get("admin_accounts", [])
                    for i, u in enumerate(admins):
                        if u.get("username") == self.username:
                            admins[i] = {**u, **new_data}
                            saved = True
                            break
                    
                    if not saved:
                        # Update user_accounts
                        users = data.get("user_accounts", [])
                        for i, u in enumerate(users):
                            if u.get("username") == self.username:
                                users[i] = {**u, **new_data}
                                saved = True
                                break
                    
                    if not saved:
                        # If not found, add to user_accounts as default? 
                        # For admin profile, we probably want to add to admin if it's admin
                        if self.username == "admin":
                            if "admin_accounts" not in data: data["admin_accounts"] = []
                            data["admin_accounts"].append({**self.user_data, **new_data})
                        else:
                            if "user_accounts" not in data: data["user_accounts"] = []
                            data["user_accounts"].append({**self.user_data, **new_data})
                    
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    return True
                except Exception:
                    pass
        return False

    # ── Build ─────────────────────────────────────────────────────────────────
    def _build(self):
        u = self.user_data
        name     = u.get("name", "Nông Hộ")
        username = u.get("username", self.username)
        phone    = u.get("phone", "")
        email    = u.get("email", "")
        farm     = u.get("farm", "")
        role     = u.get("role", "Nhân Viên")
        created  = u.get("created_at", "N/A")

        # ── Avatar block ─────────────────────────────────────────────────────
        self._avatar_text = ft.Text(
            name[0].upper(), color=ft.Colors.WHITE, size=40,
            weight=ft.FontWeight.BOLD,
        )
        avatar_ring = ft.Container(
            content=self._avatar_text,
            width=100, height=100, border_radius=50,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=GRAD_TEAL,
            ),
            border=ft.border.all(3, PRIMARY),
            alignment=ft.alignment.center,
            shadow=ft.BoxShadow(
                blur_radius=20,
                color=ft.Colors.with_opacity(0.4, PRIMARY),
                offset=ft.Offset(0, 4),
            ),
        )

        avatar_block = ft.Container(
            content=ft.Column([
                ft.Stack([
                    avatar_ring,
                    ft.Container(
                        content=ft.Icon(ft.Icons.CAMERA_ALT_ROUNDED,
                                        color=ft.Colors.WHITE, size=16),
                        width=30, height=30, border_radius=15,
                        bgcolor=PRIMARY,
                        alignment=ft.alignment.center,
                        right=0, bottom=0,
                        ink=True,
                        on_click=lambda e: None,  # avatar upload placeholder
                    ),
                ]),
                ft.Container(height=10),
                ft.Text(name, size=SIZE_H2, color=TEXT_MAIN,
                        weight=ft.FontWeight.BOLD),
                ft.Text(f"@{username}", size=SIZE_BODY, color=TEXT_SUB),
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.VERIFIED_ROUNDED, size=12, color=PRIMARY),
                        ft.Text(role, size=SIZE_CAPTION, color=PRIMARY,
                                weight=ft.FontWeight.W_600),
                    ], spacing=4, tight=True),
                    bgcolor=ft.Colors.with_opacity(0.1, PRIMARY),
                    border_radius=20,
                    padding=ft.padding.symmetric(horizontal=12, vertical=5),
                ),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
            bgcolor=BG_PANEL,
            border_radius=RADIUS_CARD,
            padding=ft.padding.symmetric(vertical=30, horizontal=20),
            border=ft.border.all(1, BORDER),
            shadow=SHADOW_CARD_GLOW,
            alignment=ft.alignment.center,
        )

        # Stats row
        def _stat(label, value, icon, color):
            return ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(icon, size=16, color=color),
                        ft.Text(value, size=SIZE_H3, color=TEXT_MAIN,
                                weight=ft.FontWeight.BOLD),
                    ], spacing=6),
                    ft.Text(label, size=SIZE_CAPTION, color=TEXT_SUB),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                bgcolor=ft.Colors.with_opacity(0.06, color),
                border_radius=10,
                padding=ft.padding.symmetric(horizontal=20, vertical=14),
                border=ft.border.all(1, ft.Colors.with_opacity(0.15, color)),
                expand=True,
                alignment=ft.alignment.center,
            )

        stats_row = ft.Row([
            _stat("Ngày tham gia", created,   ft.Icons.CALENDAR_TODAY_ROUNDED, PRIMARY),
            _stat("Trang trại",    farm or "—", ft.Icons.AGRICULTURE_ROUNDED,  SECONDARY),
            _stat("Vai trò",       role,        ft.Icons.BADGE_ROUNDED,         ACCENT),
        ], spacing=12)

        # ── Edit form ────────────────────────────────────────────────────────
        self._f_name  = styled_input("Họ và tên", "Nguyễn Văn A",
                                      icon=ft.Icons.PERSON_ROUNDED, expand=True)
        self._f_phone = styled_input("Số điện thoại", "09xxxxxxxx",
                                      icon=ft.Icons.PHONE_ROUNDED)
        self._f_email = styled_input("Email", "example@farm.vn",
                                      icon=ft.Icons.EMAIL_ROUNDED, expand=True)
        self._f_farm  = styled_input("Tên trang trại", "Trang trại A",
                                      icon=ft.Icons.AGRICULTURE_ROUNDED, expand=True)

        self._f_name.value  = name
        self._f_phone.value = phone
        self._f_email.value = email
        self._f_farm.value  = farm

        self._save_msg = ft.Text("", size=SIZE_CAPTION, color=SUCCESS)

        def _save_profile(e):
            updated = {
                "name":  self._f_name.value.strip() or name,
                "phone": self._f_phone.value.strip(),
                "email": self._f_email.value.strip(),
                "farm":  self._f_farm.value.strip(),
            }
            ok = self._save_user(updated)
            # Cập nhật avatar chữ cái
            new_name = updated["name"]
            self._avatar_text.value = new_name[0].upper() if new_name else "?"
            self._save_msg.value = "✅ Đã lưu thông tin thành công!" if ok \
                else "⚠️ Lưu vào memory (file JSON không tìm thấy)"
            self._save_msg.color = SUCCESS if ok else WARNING
            try:
                self._avatar_text.update()
                self._save_msg.update()
            except Exception:
                pass

        profile_form = panel(
            content=ft.Column([
                ft.Row([self._f_name, ft.Container(width=12), self._f_phone], spacing=0),
                ft.Container(height=10),
                ft.Row([self._f_email, ft.Container(width=12), self._f_farm], spacing=0),
                ft.Container(height=16),
                ft.Row([
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.SAVE_ROUNDED, color=ft.Colors.WHITE, size=16),
                            ft.Text("Lưu thay đổi", color=ft.Colors.WHITE,
                                    size=SIZE_BODY, weight=ft.FontWeight.W_600),
                        ], spacing=8),
                        bgcolor=PRIMARY, border_radius=RADIUS_BTN,
                        padding=ft.padding.symmetric(horizontal=18, vertical=10),
                        ink=True, on_click=_save_profile,
                    ),
                    ft.Container(width=12),
                    self._save_msg,
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=0),
            title="Chỉnh Sửa Hồ Sơ",
            icon=ft.Icons.EDIT_ROUNDED,
            expand=True,
        )

        # ── Đổi mật khẩu ────────────────────────────────────────────────────
        f_old  = styled_input("Mật khẩu hiện tại", "", password=True,
                               icon=ft.Icons.LOCK_OUTLINE_ROUNDED)
        f_new  = styled_input("Mật khẩu mới",      "", password=True,
                               icon=ft.Icons.LOCK_ROUNDED)
        f_conf = styled_input("Xác nhận mật khẩu", "", password=True,
                               icon=ft.Icons.LOCK_PERSON_ROUNDED)
        pw_msg = ft.Text("", size=SIZE_CAPTION, color=SUCCESS)

        def _change_pw(e):
            if not f_old.value:
                pw_msg.value = "⚠️ Vui lòng nhập mật khẩu hiện tại"
                pw_msg.color = WARNING
            elif len(f_new.value) < 6:
                pw_msg.value = "⚠️ Mật khẩu mới tối thiểu 6 ký tự"
                pw_msg.color = WARNING
            elif f_new.value != f_conf.value:
                pw_msg.value = "❌ Mật khẩu xác nhận không khớp"
                pw_msg.color = DANGER
            else:
                pw_msg.value = "✅ Đã đổi mật khẩu thành công!"
                pw_msg.color = SUCCESS
                for f in [f_old, f_new, f_conf]:
                    f.value = ""
            try:
                pw_msg.update()
                for f in [f_old, f_new, f_conf]:
                    f.update()
            except Exception:
                pass

        pw_panel = panel(
            content=ft.Column([
                ft.Row([f_old, ft.Container(width=12), f_new, ft.Container(width=12), f_conf], spacing=0),
                ft.Container(height=16),
                ft.Row([
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.LOCK_RESET_ROUNDED, color=ft.Colors.WHITE, size=16),
                            ft.Text("Đổi Mật Khẩu", color=ft.Colors.WHITE,
                                    size=SIZE_BODY, weight=ft.FontWeight.W_600),
                        ], spacing=8),
                        bgcolor=DANGER, border_radius=RADIUS_BTN,
                        padding=ft.padding.symmetric(horizontal=18, vertical=10),
                        ink=True, on_click=_change_pw,
                    ),
                    ft.Container(width=12),
                    pw_msg,
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=0),
            title="Bảo Mật",
            icon=ft.Icons.SECURITY_ROUNDED,
            expand=True,
        )

        # ── Thông tin đăng nhập (readonly) ──────────────────────────────────
        def _info_row(label, value, icon):
            return ft.Row([
                ft.Icon(icon, size=16, color=TEXT_SUB),
                ft.Text(label, size=SIZE_BODY, color=TEXT_SUB, width=130),
                ft.Text(value or "Chưa cập nhật", size=SIZE_BODY, color=TEXT_MAIN,
                        weight=ft.FontWeight.W_500),
            ], spacing=10)

        account_info = panel(
            content=ft.Column([
                _info_row("Tên đăng nhập",  username, ft.Icons.ALTERNATE_EMAIL_ROUNDED),
                ft.Container(height=8),
                _info_row("Ngày tham gia",  created,  ft.Icons.CALENDAR_TODAY_ROUNDED),
                ft.Container(height=8),
                _info_row("Số điện thoại",  phone,    ft.Icons.PHONE_ROUNDED),
                ft.Container(height=8),
                _info_row("Email",           email,    ft.Icons.EMAIL_ROUNDED),
                ft.Container(height=8),
                _info_row("Trang trại",      farm,     ft.Icons.AGRICULTURE_ROUNDED),
            ], spacing=0),
            title="Thông Tin Tài Khoản",
            icon=ft.Icons.PERSON_ROUNDED,
            width=340,
        )

        # ── Layout ───────────────────────────────────────────────────────────
        self.controls = [
            ft.Container(
                content=ft.Column([
                    # Header
                    ft.Row([
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.Icons.ARROW_BACK_IOS_ROUNDED,
                                        color=TEXT_SUB, size=16),
                                ft.Text("Quay lại", size=SIZE_BODY, color=TEXT_SUB),
                            ], spacing=4),
                            ink=True, border_radius=8,
                            padding=ft.padding.symmetric(horizontal=10, vertical=6),
                            on_click=lambda e: (self.on_back() if self.on_back else None),
                        ),
                        ft.Container(expand=True),
                        ft.Text("Hồ Sơ Cá Nhân", size=SIZE_H1,
                                weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                        ft.Container(expand=True),
                        ft.Container(width=80),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),

                    ft.Container(height=20),

                    # Avatar + stats
                    avatar_block,
                    ft.Container(height=12),
                    stats_row,
                    ft.Container(height=16),

                    # Form + Account info
                    ft.Row([
                        profile_form,
                        ft.Container(width=12),
                        account_info,
                    ], expand=True, vertical_alignment=ft.CrossAxisAlignment.START),

                    ft.Container(height=16),
                    pw_panel,
                    ft.Container(height=24),
                ], spacing=0),
                padding=ft.padding.symmetric(horizontal=4, vertical=4),
            )
        ]
