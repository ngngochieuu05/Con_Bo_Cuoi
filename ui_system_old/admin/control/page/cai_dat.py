"""
Trang: Cài Đặt Admin
Cấu hình hệ thống, thông báo, bảo mật, giao diện
"""
import flet as ft
import json
import os
from src.config_loader import (
    get_webapp_auto_start,
    get_webapp_enabled,
    get_webapp_host,
    get_webapp_port,
    set_webapp_auto_start,
    set_webapp_enabled,
    set_webapp_host,
    set_webapp_port,
)

class CaiDatPage(ft.Column):
    def __init__(self):
        super().__init__(expand=True, scroll=ft.ScrollMode.AUTO)
        self.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self.spacing = 0
        self._build_ui()

    def _build_ui(self):
        def setting_row(icon, label, desc, value=True, color="#4A5C6B"):
            sw = ft.Switch(value=value, active_color=color)
            return ft.Container(
                bgcolor="surface", padding=15, border_radius=12,
                border=ft.border.all(1, "outlineVariant"),
                content=ft.Row([
                    ft.Container(
                        width=40, height=40, border_radius=20,
                        bgcolor=ft.Colors.with_opacity(0.12, color),
                        alignment=ft.alignment.center,
                        content=ft.Icon(icon, color=color, size=20),
                    ),
                    ft.Column([
                        ft.Text(label, weight=ft.FontWeight.BOLD, size=13, color="onBackground"),
                        ft.Text(desc,   size=11, color="onSurfaceVariant"),
                    ], expand=True, spacing=2),
                    sw,
                ], spacing=12)
            )

        def dropdown_row(icon, label, options, value, color="#4A5C6B"):
            return ft.Container(
                bgcolor="surface", padding=15, border_radius=12,
                border=ft.border.all(1, "outlineVariant"),
                content=ft.Row([
                    ft.Container(
                        width=40, height=40, border_radius=20,
                        bgcolor=ft.Colors.with_opacity(0.12, color),
                        alignment=ft.alignment.center,
                        content=ft.Icon(icon, color=color, size=20),
                    ),
                    ft.Text(label, weight=ft.FontWeight.BOLD, size=13, expand=True, color="onBackground"),
                    ft.Dropdown(
                        options=[ft.dropdown.Option(o) for o in options],
                        value=value, width=160, content_padding=8, text_size=13,
                        border_radius=8, bgcolor=ft.Colors.GREY_50,
                    ),
                ], spacing=12)
            )

        def section_header(title):
            return ft.Container(
                padding=ft.padding.only(top=20, bottom=8),
                content=ft.Text(title, size=15, weight=ft.FontWeight.BOLD,
                                color="onBackground")
            )

        # --- Thông tin hệ thống (Editable Form) ---
        SYSTEM_INFO_FILE = "src/ui/data/system_info.json"
        
        # Load current data
        current_sys_data = {}
        if os.path.exists(SYSTEM_INFO_FILE):
            try:
                with open(SYSTEM_INFO_FILE, "r", encoding="utf-8") as f:
                    current_sys_data = json.load(f)
            except:
                pass
        
        # Fields
        f_app_name = ft.TextField(label="Tên ứng dụng", value=current_sys_data.get("app_name", "Con Bò Cười"), content_padding=10)
        f_author   = ft.TextField(label="Tác giả", value=current_sys_data.get("author", ""), content_padding=10)
        f_contact  = ft.TextField(label="Liên hệ (Email/SĐT)", value=current_sys_data.get("contact", ""), content_padding=10)
        f_version  = ft.TextField(label="Phiên bản", value=current_sys_data.get("version", "v2.5.0"), content_padding=10)
        f_desc     = ft.TextField(label="Mô tả hệ thống", value=current_sys_data.get("description", ""), multiline=True, min_lines=2, content_padding=10)
        sys_status = ft.Text("", size=12)

        def save_system_info(e):
            new_data = {
                "app_name": f_app_name.value,
                "author": f_author.value,
                "contact": f_contact.value,
                "version": f_version.value,
                "description": f_desc.value
            }
            try:
                os.makedirs(os.path.dirname(SYSTEM_INFO_FILE), exist_ok=True)
                with open(SYSTEM_INFO_FILE, "w", encoding="utf-8") as f:
                    json.dump(new_data, f, ensure_ascii=False, indent=2)
                sys_status.value = "✅ Đã lưu cấu hình hệ thống!"
                sys_status.color = ft.Colors.GREEN_700
            except Exception as ex:
                sys_status.value = f"❌ Lỗi: {ex}"
                sys_status.color = ft.Colors.RED
            try: sys_status.update()
            except: pass

        sys_info = ft.Container(
            bgcolor="surface", border_radius=14, padding=20,
            shadow=ft.BoxShadow(blur_radius=6, color=ft.Colors.with_opacity(0.1, "shadow")),
            border=ft.border.all(1, "outlineVariant"),
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.AUTO_AWESOME_MOTION_OUTLINED, color="primary"),
                    ft.Text("Thông Tin Ứng Dụng", size=15, weight=ft.FontWeight.BOLD, color="onBackground"),
                ]),
                ft.Divider(color="outlineVariant"),
                ft.Row([f_app_name, f_version], spacing=10),
                f_author,
                f_contact,
                f_desc,
                ft.Row([
                    ft.ElevatedButton("Lưu Thông Tin", icon=ft.Icons.SAVE_ROUNDED,
                                      bgcolor="primary", color=ft.Colors.WHITE,
                                      on_click=save_system_info),
                    sys_status
                ], spacing=10),
            ], spacing=10)
        )

        # --- Đổi mật khẩu admin ---
        old_pw  = ft.TextField(label="Mật khẩu cũ",   password=True, can_reveal_password=True, content_padding=10)
        new_pw  = ft.TextField(label="Mật khẩu mới",  password=True, can_reveal_password=True, content_padding=10)
        conf_pw = ft.TextField(label="Xác nhận mật khẩu", password=True, can_reveal_password=True, content_padding=10)
        pw_status = ft.Text("", size=12)

        def change_password(e):
            if new_pw.value != conf_pw.value:
                pw_status.value = "❌ Mật khẩu xác nhận không khớp!"
                pw_status.color = ft.Colors.RED
            elif len(new_pw.value) < 6:
                pw_status.value = "⚠️ Mật khẩu phải ít nhất 6 ký tự"
                pw_status.color = ft.Colors.ORANGE
            else:
                pw_status.value = "✅ Đã cập nhật mật khẩu thành công!"
                pw_status.color = ft.Colors.GREEN_700
                old_pw.value = new_pw.value = conf_pw.value = ""
                for f in [old_pw, new_pw, conf_pw]:
                    try: f.update()
                    except: pass
            try: pw_status.update()
            except: pass


        webapp_enabled_sw = ft.Switch(value=get_webapp_enabled(), active_color="#4A5C6B")
        webapp_auto_start_sw = ft.Switch(value=get_webapp_auto_start(), active_color="#4A5C6B")
        webapp_host_field = ft.TextField(label="Web Host", value=get_webapp_host(), content_padding=10)
        webapp_port_field = ft.TextField(label="Web Port", value=str(get_webapp_port()), content_padding=10)
        webapp_status = ft.Text("", size=12)

        def save_webapp_settings(e):
            try:
                host = (webapp_host_field.value or "").strip() or "0.0.0.0"
                port = int((webapp_port_field.value or "").strip())
                set_webapp_enabled(webapp_enabled_sw.value)
                set_webapp_auto_start(webapp_auto_start_sw.value)
                set_webapp_host(host)
                set_webapp_port(port)
                webapp_status.value = f"✅ Đã lưu WebApp User: http://{host}:{port}"
                webapp_status.color = ft.Colors.GREEN_700
            except ValueError:
                webapp_status.value = "❌ Port phải là số từ 1-65535"
                webapp_status.color = ft.Colors.RED
            except Exception as ex:
                webapp_status.value = f"❌ Lỗi: {ex}"
                webapp_status.color = ft.Colors.RED
            try:
                webapp_status.update()
            except:
                pass

        webapp_card = ft.Container(
            bgcolor="surface", border_radius=14, padding=20,
            shadow=ft.BoxShadow(blur_radius=6, color=ft.Colors.with_opacity(0.1, "shadow")),
            border=ft.border.all(1, "outlineVariant"),
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.PHONE_IPHONE, color="primary"),
                    ft.Text("WebApp User (Phone)", size=15, weight=ft.FontWeight.BOLD, color="onBackground"),
                ]),
                ft.Divider(color="outlineVariant"),
                ft.Row([
                    ft.Text("Bật WebApp User", expand=True, color="onBackground"),
                    webapp_enabled_sw,
                ]),
                ft.Row([
                    ft.Text("Tự khởi động cùng main.py", expand=True, color="onBackground"),
                    webapp_auto_start_sw,
                ]),
                ft.Row([webapp_host_field, webapp_port_field], spacing=10),
                ft.Row([
                    ft.ElevatedButton(
                        "Lưu WebApp",
                        icon=ft.Icons.SAVE_ROUNDED,
                        bgcolor="primary",
                        color=ft.Colors.WHITE,
                        on_click=save_webapp_settings,
                    ),
                    webapp_status,
                ], spacing=10),
            ], spacing=10)
        )

        security_card = ft.Container(
            bgcolor="surface", border_radius=14, padding=20,
            shadow=ft.BoxShadow(blur_radius=6, color=ft.Colors.with_opacity(0.1, "shadow")),
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.LOCK_OUTLINE, color="error"),
                    ft.Text("Bảo Mật – Đổi Mật Khẩu Admin", size=15, weight=ft.FontWeight.BOLD, color="onBackground"),
                ]),
                ft.Divider(color="outlineVariant"),
                old_pw, new_pw, conf_pw,
                ft.Container(height=5),
                ft.Row([
                    ft.ElevatedButton("Đổi Mật Khẩu", icon=ft.Icons.LOCK_RESET,
                                      bgcolor="#E57373", color=ft.Colors.WHITE,
                                      on_click=change_password),
                    pw_status,
                ], spacing=10),
            ], spacing=10)
        )

        # --- Cài đặt thông báo ---
        notif_card = ft.Container(
            bgcolor="surface", border_radius=14, padding=20,
            shadow=ft.BoxShadow(blur_radius=6, color=ft.Colors.with_opacity(0.1, "shadow")),
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE, color="secondary"),
                    ft.Text("Thông Báo & Cảnh Báo", size=15, weight=ft.FontWeight.BOLD, color="onBackground"),
                ]),
                ft.Divider(color="outlineVariant"),
                setting_row(ft.Icons.WARNING_AMBER, "Cảnh báo vi phạm AI",
                            "Thông báo khi camera phát hiện vi phạm", True, "#E57373"),
                ft.Container(height=6),
                setting_row(ft.Icons.ASSIGNMENT, "Đơn xin nghỉ mới",
                            "Thông báo khi nhân viên nộp đơn", True, "#FFCA28"),
                ft.Container(height=6),
                setting_row(ft.Icons.EMAIL, "Email báo cáo hàng ngày",
                            "Gửi tổng kết cuối ngày qua email", False, "#4CAF50"),
                ft.Container(height=6),
                setting_row(ft.Icons.TELEGRAM, "Telegram Bot Alert",
                            "Gửi cảnh báo qua Telegram", True, "#2E86AB"),
            ], spacing=0)
        )

        # --- Cài đặt giao diện ---
        display_card = ft.Container(
            bgcolor="surface", border_radius=14, padding=20,
            shadow=ft.BoxShadow(blur_radius=6, color=ft.Colors.with_opacity(0.1, "shadow")),
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.PALETTE_OUTLINED, color="primary"),
                    ft.Text("Giao Diện", size=15, weight=ft.FontWeight.BOLD, color="onBackground"),
                ]),
                ft.Divider(color="outlineVariant"),
                dropdown_row(ft.Icons.LANGUAGE, "Ngôn ngữ",
                             ["Tiếng Việt", "English"], "Tiếng Việt", "#4A5C6B"),
                ft.Container(height=6),
                dropdown_row(ft.Icons.DARK_MODE, "Chủ đề",
                             ["Sáng", "Tối", "Hệ thống"], "Sáng", "#4A5C6B"),
                ft.Container(height=6),
                dropdown_row(ft.Icons.REFRESH, "Tự động làm mới",
                             ["30 giây", "1 phút", "5 phút", "Tắt"], "1 phút", "#4A5C6B"),
            ], spacing=0)
        )

        # --- Backup & Restore ---
        backup_card = ft.Container(
            bgcolor="surface", border_radius=14, padding=20,
            shadow=ft.BoxShadow(blur_radius=6, color=ft.Colors.with_opacity(0.1, "shadow")),
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.BACKUP, color="tertiary"),
                    ft.Text("Sao Lưu & Khôi Phục", size=15, weight=ft.FontWeight.BOLD, color="onBackground"),
                ]),
                ft.Divider(color="outlineVariant"),
                ft.Row([
                    ft.ElevatedButton("💾 Sao Lưu Dữ Liệu", bgcolor="#9C27B0",
                                      color=ft.Colors.WHITE, icon=ft.Icons.SAVE),
                    ft.ElevatedButton("📂 Khôi Phục",       bgcolor=ft.Colors.GREY_700,
                                      color=ft.Colors.WHITE, icon=ft.Icons.RESTORE),
                    ft.ElevatedButton("🗑️ Xóa Log Cũ",      bgcolor=ft.Colors.RED_700,
                                      color=ft.Colors.WHITE, icon=ft.Icons.DELETE_SWEEP),
                ], spacing=10, wrap=True),
                ft.Container(height=8),
                ft.Text("Sao lưu cuối: Hôm nay 08:00 – accounts.json (12 KB)",
                        size=11, color=ft.Colors.GREY_600, italic=True),
            ], spacing=8)
        )

        self.controls = [
            ft.Container(
                width=700,
                content=ft.Column([
                    ft.Text("⚙️ Cài Đặt Hệ Thống Admin", size=22,
                            weight=ft.FontWeight.BOLD, color="onBackground"),
                    ft.Container(height=5),
                    ft.Text("Quản lý cấu hình, thông báo và bảo mật hệ thống",
                            size=13, color="onSurfaceVariant"),
                    ft.Container(height=20),
                    sys_info,
                    section_header("📱 WebApp User"),
                    webapp_card,
                    section_header("🔒 Bảo Mật"),
                    security_card,
                    section_header("🔔 Thông Báo"),
                    notif_card,
                    section_header("🎨 Giao Diện"),
                    display_card,
                    section_header("💾 Sao Lưu"),
                    backup_card,
                    ft.Container(height=30),
                ], spacing=8),
                padding=ft.padding.symmetric(vertical=20, horizontal=10),
            )
        ]
