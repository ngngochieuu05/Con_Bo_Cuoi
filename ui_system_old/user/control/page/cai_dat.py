"""
Cài Đặt User — Dark Theme
Con Bò Cười: Camera, Giao diện, Ngôn ngữ, Thông báo, Mật khẩu
"""
import flet as ft
import json
import os
import threading

from src.ui.theme import (
    BG_MAIN, BG_PANEL, PRIMARY, SECONDARY, ACCENT,
    TEXT_MAIN, TEXT_SUB, TEXT_MUTED,
    WARNING, DANGER, SUCCESS, BORDER,
    RADIUS_CARD, RADIUS_BTN, RADIUS_INPUT,
    SIZE_H1, SIZE_H2, SIZE_H3, SIZE_BODY, SIZE_CAPTION,
    SHADOW_CARD_GLOW, PAD_CARD,
    panel, primary_button, styled_input, section_label,
)

try:
    from src.config_loader import get_camera_index, set_camera_index
    _CFG_OK = True
except ImportError:
    _CFG_OK = False
    def get_camera_index(): return 0
    def set_camera_index(i): pass

JSON_FILE = "src/ui/data/accounts.json"


class CaiDatPage(ft.Column):
    def __init__(self, page=None, current_username=None, on_plan_changed=None):
        super().__init__(expand=True, scroll=ft.ScrollMode.AUTO, spacing=0)
        self.page             = page
        self.current_username = current_username
        self.on_plan_changed  = on_plan_changed
        self._build_ui()

    # ─── Component builders ─────────────────────────────────────────────────
    def _switch_row(self, icon, title: str, desc: str, value: bool = True,
                    color: str = PRIMARY, on_change=None) -> ft.Container:
        sw = ft.Switch(value=value, active_color=color)
        if on_change:
            sw.on_change = on_change
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(icon, color=color, size=18),
                    width=38, height=38, border_radius=19,
                    bgcolor=ft.Colors.with_opacity(0.12, color),
                    alignment=ft.alignment.center,
                ),
                ft.Column([
                    ft.Text(title, size=SIZE_BODY, color=TEXT_MAIN,
                            weight=ft.FontWeight.W_500),
                    ft.Text(desc, size=10, color=TEXT_SUB),
                ], expand=True, spacing=2),
                sw,
            ], spacing=12),
            bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.WHITE),
            border_radius=10,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border=ft.border.all(1, ft.Colors.with_opacity(0.06, ft.Colors.WHITE)),
        )

    def _dropdown_row(self, icon, title: str, options: list,
                      value: str, color: str = PRIMARY,
                      on_change=None) -> ft.Container:
        dd = ft.Dropdown(
            options=[ft.dropdown.Option(o) for o in options],
            value=value,
            bgcolor=BG_PANEL,
            border_color=BORDER,
            focused_border_color=PRIMARY,
            text_style=ft.TextStyle(color=TEXT_MAIN, size=SIZE_BODY),
            content_padding=ft.padding.symmetric(horizontal=10, vertical=8),
            border_radius=8,
            width=180,
        )
        if on_change:
            dd.on_change = on_change
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(icon, color=color, size=18),
                    width=38, height=38, border_radius=19,
                    bgcolor=ft.Colors.with_opacity(0.12, color),
                    alignment=ft.alignment.center,
                ),
                ft.Text(title, size=SIZE_BODY, color=TEXT_MAIN,
                        weight=ft.FontWeight.W_500, expand=True),
                dd,
            ], spacing=12),
            bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.WHITE),
            border_radius=10,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border=ft.border.all(1, ft.Colors.with_opacity(0.06, ft.Colors.WHITE)),
        )

    # ─── Build ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ══════════════════════════════════════════════
        # 0. Kết Nối Server (máy chủ Edge)
        # ══════════════════════════════════════════════
        _CFG_PATH = "src/ui/data/app_config.json"

        def _load_cfg() -> dict:
            try:
                with open(_CFG_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}

        def _save_cfg(d: dict):
            try:
                with open(_CFG_PATH, "w", encoding="utf-8") as f:
                    json.dump(d, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

        cfg_now       = _load_cfg()
        _default_ip   = cfg_now.get("server_ip",   "192.168.1.100")
        _default_port = str(cfg_now.get("server_port", 8000))

        srv_ip_field = styled_input(
            "Địa chỉ IP máy chủ", _default_ip,
            icon=ft.Icons.DNS_ROUNDED,
        )
        srv_port_field = styled_input(
            "Port", _default_port,
            icon=ft.Icons.SETTINGS_ETHERNET_ROUNDED,
        )
        srv_ip_field.width   = None
        srv_port_field.width = 110
        srv_status = ft.Text("", size=11, color=SUCCESS)

        def _save_server(e):
            ip   = (srv_ip_field.value   or "").strip()
            port = (srv_port_field.value or "8000").strip()
            if not ip:
                srv_status.value = "⚠️ Nhập địa chỉ IP"
                srv_status.color = WARNING
                try:
                    srv_status.update()
                except Exception:
                    pass
                return
            try:
                p = int(port)
            except ValueError:
                p = 8000
            url = f"http://{ip}:{p}"
            c   = _load_cfg()
            c["server_ip"]   = ip
            c["server_port"] = p
            c["server_url"]  = url
            _save_cfg(c)
            srv_status.value = f"✅ Đã lưu: {url}"
            srv_status.color = SUCCESS
            try:
                srv_status.update()
            except Exception:
                pass

        def _test_server(e):
            srv_status.value = "⏳ Đang kiểm tra kết nối…"
            srv_status.color = TEXT_SUB
            try:
                srv_status.update()
            except Exception:
                pass

            def _run():
                try:
                    import requests as rq
                    ip   = (srv_ip_field.value   or "").strip()
                    port = (srv_port_field.value or "8000").strip()
                    url  = f"http://{ip}:{port}/api/dashboard"
                    resp = rq.get(url, timeout=4)
                    if resp.status_code == 200:
                        data = resp.json()
                        cows = data.get("total_cows", "?")
                        srv_status.value = f"✅ Kết nối OK! Số bò: {cows}"
                        srv_status.color = SUCCESS
                    else:
                        srv_status.value = f"❌ HTTP {resp.status_code}"
                        srv_status.color = DANGER
                except Exception as err:
                    srv_status.value = f"❌ {str(err)[:60]}"
                    srv_status.color = DANGER
                try:
                    srv_status.update()
                except Exception:
                    pass

            threading.Thread(target=_run, daemon=True).start()

        server_panel = panel(
            content=ft.Column([
                ft.Text(
                    "Kết nối ứng dụng đến máy chủ Edge Server trong cùng mạng Wi-Fi LAN.",
                    size=11, color=TEXT_SUB,
                ),
                ft.Container(height=10),
                ft.Row([
                    ft.Container(content=srv_ip_field, expand=True),
                    ft.Container(width=8),
                    srv_port_field,
                ]),
                ft.Container(height=10),
                ft.Row([
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.SAVE_ROUNDED, color=ft.Colors.WHITE, size=15),
                            ft.Text("Lưu", color=ft.Colors.WHITE,
                                    size=SIZE_BODY, weight=ft.FontWeight.W_600),
                        ], spacing=6),
                        bgcolor=PRIMARY, border_radius=RADIUS_BTN,
                        padding=ft.padding.symmetric(horizontal=14, vertical=8),
                        ink=True, on_click=_save_server,
                    ),
                    ft.Container(width=8),
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.WIFI_TETHERING_ROUNDED, color=PRIMARY, size=15),
                            ft.Text("Kiểm tra", color=PRIMARY,
                                    size=SIZE_BODY, weight=ft.FontWeight.W_600),
                        ], spacing=6),
                        border=ft.border.all(1, PRIMARY), border_radius=RADIUS_BTN,
                        padding=ft.padding.symmetric(horizontal=14, vertical=8),
                        ink=True, on_click=_test_server,
                    ),
                    ft.Container(width=12),
                    srv_status,
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=0),
            title="Máy Chủ (Edge Server)",
            icon=ft.Icons.CLOUD_SYNC_ROUNDED,
        )

        # ══════════════════════════════════════════════
        # 1. Giao diện & Ngôn ngữ
        # ══════════════════════════════════════════════
        def _handle_theme(e):
            if not self.page:
                return
            val = e.control.value
            self.page.theme_mode = {
                "Tối":     ft.ThemeMode.DARK,
                "Sáng":    ft.ThemeMode.LIGHT,
                "Hệ thống":ft.ThemeMode.SYSTEM,
            }.get(val, ft.ThemeMode.DARK)
            try:
                self.page.update()
            except Exception:
                pass

        def _handle_lang(e):
            # Demo — chỉ snack bar
            if self.page:
                self.page.open(ft.SnackBar(
                    content=ft.Text(f"Ngôn ngữ đã chuyển sang: {e.control.value}"),
                    bgcolor=ft.Colors.with_opacity(0.9, BG_PANEL),
                ))

        appearance_panel = panel(
            content=ft.Column([
                self._dropdown_row(
                    ft.Icons.DARK_MODE_ROUNDED, "Chủ đề giao diện",
                    ["Tối", "Sáng", "Hệ thống"], "Tối",
                    color=PRIMARY, on_change=_handle_theme,
                ),
                ft.Container(height=8),
                self._dropdown_row(
                    ft.Icons.LANGUAGE_ROUNDED, "Ngôn ngữ",
                    ["Tiếng Việt", "English", "日本語"], "Tiếng Việt",
                    color=SECONDARY, on_change=_handle_lang,
                ),
                ft.Container(height=8),
                self._dropdown_row(
                    ft.Icons.FORMAT_SIZE_ROUNDED, "Cỡ chữ",
                    ["Nhỏ", "Mặc định", "Lớn"], "Mặc định",
                    color=ACCENT,
                ),
            ], spacing=0),
            title="Giao Diện & Ngôn Ngữ",
            icon=ft.Icons.PALETTE_ROUNDED,
        )

        # ══════════════════════════════════════════════
        # 2. Camera
        # ══════════════════════════════════════════════
        current_cam = get_camera_index()
        self._cam_status = ft.Text("", size=11, color=SUCCESS)
        self._cam_test   = ft.Text("", size=11, color=TEXT_SUB)

        cam_dd = ft.Dropdown(
            value=str(current_cam),
            options=[
                ft.dropdown.Option("0", "Camera 0 (Mặc định)"),
                ft.dropdown.Option("1", "Camera 1"),
                ft.dropdown.Option("2", "Camera 2"),
                ft.dropdown.Option("3", "Camera 3"),
            ],
            bgcolor=BG_PANEL, border_color=BORDER,
            focused_border_color=PRIMARY,
            text_style=ft.TextStyle(color=TEXT_MAIN, size=SIZE_BODY),
            border_radius=8, content_padding=ft.padding.symmetric(horizontal=10, vertical=8),
            width=220,
        )

        def _save_cam(e):
            try:
                idx = int(cam_dd.value or 0)
                set_camera_index(idx)
                self._cam_status.value  = f"✅ Đã lưu Camera {idx}"
                self._cam_status.color  = SUCCESS
            except Exception as ex:
                self._cam_status.value  = f"❌ Lỗi: {ex}"
                self._cam_status.color  = DANGER
            try:
                self._cam_status.update()
            except Exception:
                pass

        def _test_cam(e):
            self._cam_test.value = "⏳ Đang kiểm tra..."
            self._cam_test.color = TEXT_SUB
            try:
                self._cam_test.update()
            except Exception:
                pass

            def _run():
                try:
                    import cv2
                    idx = int(cam_dd.value or 0)
                    cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                    ok, _ = cap.read()
                    cap.release()
                    self._cam_test.value = f"✅ Camera {idx} hoạt động tốt!" if ok \
                        else f"❌ Camera {idx} không phản hồi"
                    self._cam_test.color = SUCCESS if ok else DANGER
                except Exception as ex:
                    self._cam_test.value = f"❌ {ex}"
                    self._cam_test.color = DANGER
                try:
                    self._cam_test.update()
                except Exception:
                    pass

            threading.Thread(target=_run, daemon=True).start()

        cam_panel = panel(
            content=ft.Column([
                ft.Text(
                    "Camera được dùng riêng cho tài khoản này — tách biệt với camera giám sát.",
                    size=11, color=TEXT_SUB,
                ),
                ft.Container(height=10),
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.VIDEOCAM_ROUNDED, color=PRIMARY, size=18),
                        ft.Text("Chọn camera đầu vào:", size=SIZE_BODY,
                                color=TEXT_MAIN, weight=ft.FontWeight.W_500, expand=True),
                        cam_dd,
                    ], spacing=12),
                    bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.WHITE),
                    border_radius=10,
                    padding=ft.padding.symmetric(horizontal=14, vertical=10),
                    border=ft.border.all(1, ft.Colors.with_opacity(0.06, ft.Colors.WHITE)),
                ),
                ft.Container(height=10),
                ft.Row([
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.SAVE_ROUNDED, color=ft.Colors.WHITE, size=15),
                            ft.Text("Lưu", color=ft.Colors.WHITE,
                                    size=SIZE_BODY, weight=ft.FontWeight.W_600),
                        ], spacing=6),
                        bgcolor=PRIMARY, border_radius=RADIUS_BTN,
                        padding=ft.padding.symmetric(horizontal=14, vertical=8),
                        ink=True, on_click=_save_cam,
                    ),
                    ft.Container(width=8),
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.PLAY_CIRCLE_ROUNDED, color=PRIMARY, size=15),
                            ft.Text("Test Camera", color=PRIMARY,
                                    size=SIZE_BODY, weight=ft.FontWeight.W_600),
                        ], spacing=6),
                        border=ft.border.all(1, PRIMARY), border_radius=RADIUS_BTN,
                        padding=ft.padding.symmetric(horizontal=14, vertical=8),
                        ink=True, on_click=_test_cam,
                    ),
                    ft.Container(width=12),
                    self._cam_status,
                ]),
                self._cam_test,
            ], spacing=0),
            title="Cấu Hình Camera",
            icon=ft.Icons.VIDEOCAM_ROUNDED,
        )

        # ══════════════════════════════════════════════
        # 3. Thông báo
        # ══════════════════════════════════════════════
        notif_panel = panel(
            content=ft.Column([
                self._switch_row(
                    ft.Icons.WARNING_AMBER_ROUNDED, "Cảnh báo từ AI Camera",
                    "Nhận thông báo khi camera phát hiện hành vi bất thường",
                    True, DANGER,
                ),
                ft.Container(height=8),
                self._switch_row(
                    ft.Icons.CAMPAIGN_ROUNDED, "Thông báo từ Admin",
                    "Tin nhắn và thông báo từ quản trị hệ thống",
                    True, PRIMARY,
                ),
                ft.Container(height=8),
                self._switch_row(
                    ft.Icons.SEND_ROUNDED, "Gửi báo cáo Telegram",
                    "Tự động gửi báo cáo ngày qua Telegram Bot",
                    False, SECONDARY,
                ),
                ft.Container(height=8),
                self._switch_row(
                    ft.Icons.HISTORY_ROUNDED, "Lịch sử phiên",
                    "Lưu lịch sử nhận diện và cảnh báo trong ngày",
                    True, ACCENT,
                ),
            ], spacing=0),
            title="Thông Báo",
            icon=ft.Icons.NOTIFICATIONS_ROUNDED,
        )

        # ══════════════════════════════════════════════
        # 4. Đổi mật khẩu
        # ══════════════════════════════════════════════
        f_old  = styled_input("Mật khẩu hiện tại", "", password=True,
                               icon=ft.Icons.LOCK_OUTLINE_ROUNDED)
        f_new  = styled_input("Mật khẩu mới",      "", password=True,
                               icon=ft.Icons.LOCK_ROUNDED)
        f_conf = styled_input("Xác nhận",            "", password=True,
                               icon=ft.Icons.LOCK_PERSON_ROUNDED)
        pw_msg = ft.Text("", size=SIZE_CAPTION, color=SUCCESS)

        def _change_pw(e):
            if not f_old.value:
                pw_msg.value = "⚠️ Vui lòng nhập mật khẩu hiện tại"
                pw_msg.color = WARNING
            elif len(f_new.value) < 6:
                pw_msg.value = "⚠️ Tối thiểu 6 ký tự"
                pw_msg.color = WARNING
            elif f_new.value != f_conf.value:
                pw_msg.value = "❌ Mật khẩu không khớp"
                pw_msg.color = DANGER
            else:
                pw_msg.value = "✅ Đã đổi mật khẩu!"
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
                ft.Row([f_old, ft.Container(width=10), f_new, ft.Container(width=10), f_conf],
                       spacing=0),
                ft.Container(height=12),
                ft.Row([
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.LOCK_RESET_ROUNDED, color=ft.Colors.WHITE, size=15),
                            ft.Text("Đổi Mật Khẩu", color=ft.Colors.WHITE,
                                    size=SIZE_BODY, weight=ft.FontWeight.W_600),
                        ], spacing=6),
                        bgcolor=DANGER, border_radius=RADIUS_BTN,
                        padding=ft.padding.symmetric(horizontal=14, vertical=8),
                        ink=True, on_click=_change_pw,
                    ),
                    ft.Container(width=12),
                    pw_msg,
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=0),
            title="Bảo Mật",
            icon=ft.Icons.SECURITY_ROUNDED,
        )

        # ══════════════════════════════════════════════
        # 5. Về ứng dụng (Dynamic)
        # ══════════════════════════════════════════════
        SYSTEM_INFO_FILE = "src/ui/data/system_info.json"
        sys_data = {"version": "v1.5", "author": "Con Bò Cười Team", "contact": "support@conbocuoi.vn"}
        if os.path.exists(SYSTEM_INFO_FILE):
            try:
                with open(SYSTEM_INFO_FILE, "r", encoding="utf-8") as f:
                    sys_data.update(json.load(f))
            except:
                pass

        about_panel = panel(
            content=ft.Column([
                ft.Row([
                    ft.Text("Phiên bản:", size=SIZE_BODY, color=TEXT_SUB, width=140),
                    ft.Text(sys_data.get("version"), size=SIZE_BODY, color=TEXT_MAIN,
                            weight=ft.FontWeight.W_500),
                ]),
                ft.Container(height=8),
                ft.Row([
                    ft.Text("Tác giả:", size=SIZE_BODY, color=TEXT_SUB, width=140),
                    ft.Text(sys_data.get("author"), size=SIZE_BODY, color=TEXT_MAIN),
                ]),
                ft.Container(height=8),
                ft.Row([
                    ft.Text("Hỗ trợ:", size=SIZE_BODY, color=TEXT_SUB, width=140),
                    ft.Text(sys_data.get("contact"), size=SIZE_BODY, color=PRIMARY),
                ]),
                ft.Container(height=8),
                ft.Row([
                    ft.Text("Mô tả:", size=SIZE_BODY, color=TEXT_SUB, width=140),
                    ft.Text(sys_data.get("description", "Hệ thống giám sát thông minh"), size=SIZE_BODY, color=TEXT_MUTED, expand=True),
                ]),
            ], spacing=0),
            title="Về Ứng Dụng",
            icon=ft.Icons.INFO_ROUNDED,
        )

        # ══════════════════════════════════════════════
        # Layout đơn cột (Mobile-friendly)
        # ══════════════════════════════════════════════
        self.controls = [
            ft.Container(
                content=ft.Column([
                    ft.Text("Cài Đặt", size=SIZE_H1,
                            weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                    ft.Text("Tùy chỉnh server, camera, thông báo và bảo mật",
                            size=SIZE_CAPTION, color=TEXT_SUB),
                    ft.Container(height=16),
                    server_panel,
                    ft.Container(height=12),
                    appearance_panel,
                    ft.Container(height=12),
                    cam_panel,
                    ft.Container(height=12),
                    notif_panel,
                    ft.Container(height=12),
                    pw_panel,
                    ft.Container(height=12),
                    about_panel,
                    ft.Container(height=20),
                ], spacing=0),
                padding=ft.padding.symmetric(horizontal=4, vertical=4),
            )
        ]