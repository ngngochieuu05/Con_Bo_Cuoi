"""
Phien Giam Sat - Mobile Client
Ket noi den Edge Server qua LAN Wi-Fi, hien thi live stream & du lieu AI.
Ho tro Offline mode: doc cache khi mat ket noi server.
"""
import flet as ft
import threading
import time
import json
import os

try:
    import requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

try:
    from src.bll.oa_core.sua_thong_bao.tuy_chinh_thong_bao import get_thong_bao_service
    _HAS_OA = True
except Exception:
    _HAS_OA = False
    def get_thong_bao_service(): return None

_CFG_PATH   = "src/ui/data/app_config.json"
_CACHE_PATH = "src/ui/data/monitor_cache.json"


def _load_server_url() -> str:
    for path in [_CFG_PATH, "ui/data/app_config.json"]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                return cfg.get("server_url", "http://192.168.1.100:8000")
            except Exception:
                pass
    return "http://192.168.1.100:8000"


def _load_cache() -> dict:
    for path in [_CACHE_PATH, "ui/data/monitor_cache.json"]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return {}


def _save_cache(data: dict):
    path = _CACHE_PATH
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


class PhienGiamSatPage(ft.Column):
    """Trang giam sat trang trai - ket noi Edge Server qua Wi-Fi LAN."""

    def __init__(self, user_account=None):
        super().__init__(expand=True, scroll=ft.ScrollMode.AUTO, spacing=0)
        self.user_account = user_account or {}
        self.server_url   = _load_server_url()
        self.is_connected = False
        self._polling     = False
        self._poll_thread = None
        try:
            self.oa_service = get_thong_bao_service()
        except Exception:
            self.oa_service = None
        self._build_ui()

    def _build_ui(self):
        from src.ui.theme import (
            BG_PANEL, PRIMARY, TEXT_MAIN, TEXT_SUB, TEXT_MUTED,
            DANGER, SUCCESS, BORDER, RADIUS_CARD,
        )
        self._status_dot = ft.Container(width=10, height=10, border_radius=5, bgcolor=DANGER)
        self._status_text = ft.Text("Chua ket noi server", size=12, color=TEXT_SUB)
        self._offline_banner = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.WIFI_OFF_ROUNDED, size=14, color="errorContainer"),
                ft.Text("Che do Offline - Du lieu luu tru", size=11, color="errorContainer"),
            ], spacing=6),
            bgcolor=ft.Colors.with_opacity(0.12, "errorContainer"),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            visible=False,
        )
        status_bar = ft.Container(
            content=ft.Row([
                self._status_dot, self._status_text,
                ft.Container(expand=True), self._offline_banner,
            ], spacing=8),
            bgcolor=BG_PANEL, border_radius=10,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border=ft.border.all(1, BORDER),
        )
        self._stream_img = ft.Image(
            src="", src_base64=None, fit=ft.ImageFit.CONTAIN, border_radius=12,
            error_content=ft.Column([
                ft.Icon(ft.Icons.VIDEOCAM_OFF_ROUNDED, size=48, color=TEXT_MUTED),
                ft.Text("Khong co tin hieu camera", size=12, color=TEXT_MUTED),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
               alignment=ft.MainAxisAlignment.CENTER),
        )
        stream_panel = ft.Container(
            content=ft.Stack([
                ft.Container(content=self._stream_img, bgcolor=ft.Colors.BLACK,
                             border_radius=12, alignment=ft.alignment.center, height=220),
                ft.Container(
                    content=ft.Text("LIVE", size=10, color=SUCCESS, weight=ft.FontWeight.BOLD),
                    bgcolor=ft.Colors.with_opacity(0.6, ft.Colors.BLACK),
                    border_radius=6, padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    top=8, left=8,
                ),
            ]),
        )
        self._txt_cattle  = ft.Text("--", size=26, weight=ft.FontWeight.BOLD, color=TEXT_MAIN)
        self._txt_alerts  = ft.Text("--", size=26, weight=ft.FontWeight.BOLD, color=DANGER)
        self._txt_updated = ft.Text("", size=9, color=TEXT_MUTED)

        def _mini_kpi(icon, label, value_ctrl, color):
            return ft.Container(
                content=ft.Column([
                    ft.Row([ft.Icon(icon, size=16, color=color),
                            ft.Text(label, size=10, color=TEXT_SUB)], spacing=4),
                    value_ctrl,
                ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=BG_PANEL, border_radius=RADIUS_CARD,
                padding=ft.padding.symmetric(horizontal=16, vertical=12),
                border=ft.border.all(1, BORDER), expand=True,
                alignment=ft.alignment.center,
            )

        kpi_row = ft.Row([
            _mini_kpi(ft.Icons.PETS_ROUNDED,   "So bo hien tai",    self._txt_cattle, PRIMARY),
            _mini_kpi(ft.Icons.WARNING_ROUNDED, "Canh bao hom nay", self._txt_alerts, DANGER),
        ], spacing=10)

        self._log_list = ft.Column(
            controls=[self._log_item("SYS", "Nhan Ket Noi de bat dau giam sat", "info")],
            spacing=6, scroll=ft.ScrollMode.AUTO,
        )
        log_panel = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.LIST_ALT_ROUNDED, size=16, color=PRIMARY),
                    ft.Text("Nhat ky canh bao", size=13, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                    ft.Container(expand=True), self._txt_updated,
                ], spacing=6),
                ft.Divider(color=BORDER, height=12),
                ft.Container(content=self._log_list, height=260),
            ], spacing=0),
            bgcolor=BG_PANEL, border_radius=RADIUS_CARD,
            padding=ft.padding.all(14), border=ft.border.all(1, BORDER),
        )
        self._btn_connect = ft.ElevatedButton(
            text="Ket Noi Server", icon=ft.Icons.WIFI_ROUNDED,
            bgcolor=PRIMARY, color=ft.Colors.WHITE, on_click=self._toggle_connection,
            style=ft.ButtonStyle(
                padding=ft.padding.symmetric(horizontal=20, vertical=14),
                shape=ft.RoundedRectangleBorder(radius=10),
            ), expand=True,
        )
        self._btn_snapshot = ft.OutlinedButton(
            text="Chup anh", icon=ft.Icons.CAMERA_ALT_ROUNDED,
            on_click=self._do_snapshot, visible=False, expand=True,
        )
        self.controls.extend([
            ft.Container(
                content=ft.Column([
                    status_bar, ft.Container(height=8),
                    stream_panel, ft.Container(height=10),
                    kpi_row, ft.Container(height=10),
                    ft.Row([self._btn_connect, self._btn_snapshot], spacing=10),
                    ft.Container(height=10), log_panel, ft.Container(height=16),
                ], spacing=0),
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
            )
        ])

    def _log_item(self, t: str, msg: str, kind: str = "info") -> ft.Container:
        from src.ui.theme import PRIMARY, DANGER, TEXT_SUB, TEXT_MUTED, BORDER
        color_map = {"warning": DANGER, "success": PRIMARY, "info": TEXT_SUB, "error": DANGER}
        icon_map  = {
            "warning": ft.Icons.WARNING_AMBER_ROUNDED, "success": ft.Icons.CHECK_CIRCLE_ROUNDED,
            "info": ft.Icons.INFO_ROUNDED, "error": ft.Icons.ERROR_ROUNDED,
        }
        return ft.Container(
            content=ft.Row([
                ft.Icon(icon_map.get(kind, ft.Icons.INFO_ROUNDED),
                        size=16, color=color_map.get(kind, TEXT_SUB)),
                ft.Column([
                    ft.Text(t, size=10, color=TEXT_MUTED, italic=True),
                    ft.Text(msg, size=12, color=TEXT_SUB),
                ], spacing=1, expand=True),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.START),
            bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.WHITE),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            border=ft.border.all(1, BORDER),
        )

    def _add_log(self, t: str, msg: str, kind: str = "info"):
        self._log_list.controls.insert(0, self._log_item(t, msg, kind))
        if len(self._log_list.controls) > 60:
            self._log_list.controls.pop()
        try:
            self._log_list.update()
        except Exception:
            pass

    def _toggle_connection(self, e):
        if self.is_connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        if not _HAS_REQUESTS:
            self._set_status(False, "Thieu thu vien requests")
            return
        self._btn_connect.text     = "Dang ket noi..."
        self._btn_connect.disabled = True
        try:
            self._btn_connect.update()
        except Exception:
            pass

        def _try():
            try:
                resp = requests.get(f"{self.server_url}/api/dashboard", timeout=4)
                if resp.status_code == 200:
                    self.is_connected = True
                    self._set_status(True, f"Online - {self.server_url}")
                    self._offline_banner.visible = False
                    self._btn_snapshot.visible   = True
                    self._update_from_data(resp.json())
                    self._start_polling()
                else:
                    self._set_status(False, f"Loi HTTP {resp.status_code}")
                    self._show_offline_mode()
            except Exception as err:
                self._set_status(False, "Khong ket noi duoc server")
                self._show_offline_mode()
                self._add_log(time.strftime("%H:%M"), str(err)[:80], "error")
            finally:
                self._btn_connect.text = "Ngat Ket Noi" if self.is_connected else "Thu Lai"
                self._btn_connect.icon = (ft.Icons.WIFI_OFF_ROUNDED if self.is_connected
                                          else ft.Icons.WIFI_ROUNDED)
                self._btn_connect.disabled = False
                try:
                    self._btn_connect.update()
                    self._btn_snapshot.update()
                except Exception:
                    pass

        threading.Thread(target=_try, daemon=True).start()

    def _disconnect(self):
        self._polling     = False
        self.is_connected = False
        self._set_status(False, "Da ngat ket noi")
        self._btn_connect.text       = "Ket Noi Server"
        self._btn_connect.icon       = ft.Icons.WIFI_ROUNDED
        self._btn_snapshot.visible   = False
        self._offline_banner.visible = False
        try:
            self._btn_connect.update()
            self._btn_snapshot.update()
            self._offline_banner.update()
        except Exception:
            pass
        self._add_log(time.strftime("%H:%M"), "Da ngat ket noi server", "info")

    def _set_status(self, online: bool, text: str):
        from src.ui.theme import PRIMARY, DANGER
        self._status_dot.bgcolor = PRIMARY if online else DANGER
        self._status_text.value  = text
        try:
            self._status_dot.update()
            self._status_text.update()
        except Exception:
            pass

    def _show_offline_mode(self):
        cache = _load_cache()
        if cache:
            self._offline_banner.visible = True
            try:
                self._offline_banner.update()
            except Exception:
                pass
            self._update_from_data(cache, offline=True)
            self._add_log(time.strftime("%H:%M"), "Offline mode - dung du lieu cache", "info")
        else:
            self._add_log(time.strftime("%H:%M"),
                          "Khong co cache - can ket noi Wi-Fi lan dau", "warning")

    def _start_polling(self):
        self._polling = True
        self._stream_img.src       = f"{self.server_url}/api/stream"
        self._stream_img.src_base64 = None
        try:
            self._stream_img.update()
        except Exception:
            pass

        def _poll():
            while self._polling and self.is_connected:
                try:
                    resp = requests.get(f"{self.server_url}/api/dashboard", timeout=5)
                    if resp.status_code == 200:
                        data = resp.json()
                        _save_cache(data)
                        self._update_from_data(data)
                        if self._offline_banner.visible:
                            self._offline_banner.visible = False
                            try:
                                self._offline_banner.update()
                            except Exception:
                                pass
                except Exception:
                    if self.is_connected:
                        self.is_connected = False
                        self._set_status(False, "Mat ket noi server")
                        self._show_offline_mode()
                        self._btn_connect.text = "Thu Lai"
                        self._btn_connect.icon = ft.Icons.WIFI_ROUNDED
                        try:
                            self._btn_connect.update()
                        except Exception:
                            pass
                time.sleep(5)

        self._poll_thread = threading.Thread(target=_poll, daemon=True)
        self._poll_thread.start()
        self._add_log(time.strftime("%H:%M"), "Bat dau nhan du lieu tu server", "success")

    def _update_from_data(self, data: dict, offline: bool = False):
        self._txt_cattle.value  = str(data.get("total_cows", "--"))
        self._txt_alerts.value  = str(data.get("active_alerts", "--"))
        ts = data.get("timestamp", "")
        self._txt_updated.value = f"Cap nhat: {ts}" if ts else ""
        try:
            self._txt_cattle.update()
            self._txt_alerts.update()
            self._txt_updated.update()
        except Exception:
            pass
        for alert in data.get("recent_alerts", [])[-3:]:
            kind   = "warning" if "Fighting" in alert.get("type", "") else "info"
            a_type = alert.get("type", "Canh bao")
            a_time = alert.get("time", time.strftime("%H:%M"))
            self._add_log(a_time, a_type, kind)
            if kind == "warning" and not offline:
                self._send_telegram_alert(a_time, a_type)

    def _send_telegram_alert(self, t: str, msg: str):
        def _send():
            try:
                if not self.oa_service or not self.oa_service.is_alert_enabled():
                    return
                token   = self.oa_service.get_default_token()
                chat_id = self.oa_service.get_default_chat_id()
                if not (token and chat_id):
                    return
                tele_msg = (
                    f"CANH BAO TRANG TRAI\n"
                    f"Thoi gian: {t}\n"
                    f"Noi dung: {msg}\n"
                    f"Phat hien tu Edge Server AI."
                )
                self.oa_service.send_message(token, chat_id, tele_msg)
            except Exception as err:
                print(f"[TELEGRAM] {err}")
        threading.Thread(target=_send, daemon=True).start()

    def _do_snapshot(self, e):
        if not _HAS_REQUESTS:
            return

        def _fetch():
            try:
                import base64
                resp = requests.get(f"{self.server_url}/api/snapshot", timeout=5)
                if resp.status_code == 200:
                    b64 = base64.b64encode(resp.content).decode()
                    self._stream_img.src_base64 = b64
                    self._stream_img.src = ""
                    try:
                        self._stream_img.update()
                    except Exception:
                        pass
                    self._add_log(time.strftime("%H:%M"), "Da chup snapshot", "success")
                else:
                    self._add_log(time.strftime("%H:%M"),
                                  f"Snapshot loi HTTP {resp.status_code}", "error")
            except Exception as err:
                self._add_log(time.strftime("%H:%M"),
                              f"Khong lay duoc snapshot: {str(err)[:50]}", "error")

        threading.Thread(target=_fetch, daemon=True).start()

    def will_unmount(self):
        super().will_unmount()
        self._polling     = False
        self.is_connected = False
