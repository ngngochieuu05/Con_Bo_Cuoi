import threading
import time

import flet as ft

from bll.services.monitor_service import (
    fetch_dashboard,
    fetch_snapshot_base64,
    load_cache,
    load_config,
    save_cache,
    stream_url,
)
from ui.theme import PRIMARY, DANGER, glass_container, status_badge


class LiveMonitoringController:
    def __init__(self):
        self.config = load_config()
        self.server_url = self.config.get("server_url", "http://127.0.0.1:8000")
        self.is_connected = False
        self._polling = False

        self.root = ft.Column(expand=True, spacing=12, scroll=ft.ScrollMode.AUTO)

        self.status_chip = status_badge("Ngoại tuyến", "danger")
        self.last_update = ft.Text("", size=11, color=ft.Colors.WHITE70)

        self.stream_image = ft.Image(
            src="",
            fit=ft.ImageFit.CONTAIN,
            border_radius=12,
            error_content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.VIDEOCAM_OFF, size=40, color=ft.Colors.WHITE60),
                    ft.Text("Không có tín hiệu camera", size=12, color=ft.Colors.WHITE70),
                ],
            ),
        )

        self.total_cows = ft.Text("--", size=24, weight=ft.FontWeight.W_700)
        self.active_alerts = ft.Text("--", size=24, weight=ft.FontWeight.W_700, color=DANGER)
        self.camera_online = ft.Text("--", size=24, weight=ft.FontWeight.W_700, color=PRIMARY)

        self.log_rows = ft.Column(spacing=8)
        self.connect_btn = ft.ElevatedButton("Kết nối máy chủ", icon=ft.Icons.WIFI, on_click=self.toggle_connection)
        self.snapshot_btn = ft.OutlinedButton("Chụp ảnh", icon=ft.Icons.CAMERA_ALT, on_click=self.take_snapshot, visible=False)

        self._build_ui()

    def _safe_update(self, *controls):
        """Call .update() only when the control is already in the page tree."""
        for ctrl in controls:
            try:
                if ctrl.page:
                    ctrl.update()
            except RuntimeError:
                pass

    def _build_ui(self):
        self.root.controls = [
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text("Giám sát trực tiếp", size=24, weight=ft.FontWeight.W_700),
                    self.status_chip,
                ],
            ),
            ft.Text(f"Máy chủ: {self.server_url}", size=12, color=ft.Colors.WHITE70),
            glass_container(
                padding=12,
                radius=18,
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Container(
                            height=220,
                            border_radius=12,
                            bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
                            alignment=ft.alignment.center,
                            content=self.stream_image,
                        ),
                        ft.Row(controls=[self.connect_btn, self.snapshot_btn]),
                    ],
                ),
            ),
            ft.Row(
                spacing=10,
                controls=[
                    ft.Container(expand=1, content=self._kpi_card("Tổng bò", self.total_cows, ft.Icons.PETS)),
                    ft.Container(expand=1, content=self._kpi_card("Cảnh báo", self.active_alerts, ft.Icons.WARNING_AMBER)),
                    ft.Container(expand=1, content=self._kpi_card("Camera trực tuyến", self.camera_online, ft.Icons.VIDEOCAM)),
                ],
            ),
            glass_container(
                padding=14,
                radius=18,
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text("Nhật ký cảnh báo", size=16, weight=ft.FontWeight.W_600),
                                self.last_update,
                            ],
                        ),
                        self.log_rows,
                    ],
                ),
            ),
        ]

    def _kpi_card(self, title: str, value_control: ft.Control, icon):
        return glass_container(
            padding=12,
            radius=16,
            content=ft.Column(
                tight=True,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[ft.Text(title, size=12, color=ft.Colors.WHITE70), ft.Icon(icon, size=16, color=PRIMARY)],
                    ),
                    value_control,
                ],
            ),
        )

    def _set_status(self, online: bool):
        self.status_chip.content.value = "Trực tuyến" if online else "Ngoại tuyến"
        self.status_chip.bgcolor = ft.Colors.with_opacity(0.2, PRIMARY if online else DANGER)
        self.status_chip.border = ft.border.all(1, ft.Colors.with_opacity(0.4, PRIMARY if online else DANGER))
        self._safe_update(self.status_chip)

    def _append_log(self, time_label: str, message: str, kind: str = "info"):
        color = DANGER if kind == "warning" else (PRIMARY if kind == "success" else ft.Colors.WHITE70)
        self.log_rows.controls.insert(
            0,
            ft.Container(
                padding=10,
                border_radius=10,
                bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
                content=ft.Row(
                    controls=[
                        ft.Text(time_label, size=11, color=ft.Colors.WHITE60, width=70),
                        ft.Text(message, size=12, color=color, expand=True),
                    ],
                ),
            ),
        )
        if len(self.log_rows.controls) > 8:
            self.log_rows.controls.pop()
        self._safe_update(self.log_rows)

    def _apply_dashboard_data(self, data: dict, offline: bool = False):
        self.total_cows.value = str(data.get("total_cows", "--"))
        self.active_alerts.value = str(data.get("active_alerts", "--"))
        self.camera_online.value = str(data.get("cameras_online", "--"))
        self.last_update.value = f"Cập nhật: {data.get('timestamp', '')}"

        self._safe_update(self.total_cows, self.active_alerts, self.camera_online, self.last_update)

        recent_alerts = data.get("recent_alerts", [])[-3:]
        for alert in recent_alerts:
            a_time = alert.get("time", time.strftime("%H:%M"))
            a_type = alert.get("type", "Cảnh báo")
            kind = "warning" if "Fighting" in a_type or "bat thuong" in a_type.lower() else "info"
            self._append_log(a_time, a_type, kind)

        if offline:
            self._append_log(time.strftime("%H:%M"), "Đang dùng dữ liệu bộ nhớ đệm ngoại tuyến", "info")

    def _load_offline_cache(self):
        cache = load_cache()
        if cache:
            self._apply_dashboard_data(cache, offline=True)
        else:
            self._append_log(time.strftime("%H:%M"), "Không có dữ liệu bộ nhớ đệm", "warning")

    def _start_polling(self):
        self._polling = True
        self.stream_image.src = stream_url(self.server_url)
        self.stream_image.src_base64 = None
        self._safe_update(self.stream_image)

        def _poll_loop():
            while self._polling and self.is_connected:
                try:
                    data = fetch_dashboard(self.server_url)
                    save_cache(data)
                    self._apply_dashboard_data(data)
                except Exception as err:
                    self.is_connected = False
                    self._set_status(False)
                    self.connect_btn.text = "Thử lại"
                    self.connect_btn.icon = ft.Icons.WIFI
                    self._safe_update(self.connect_btn)
                    self._append_log(time.strftime("%H:%M"), f"Mất kết nối: {str(err)[:60]}", "warning")
                    self._load_offline_cache()
                    break
                time.sleep(5)

        threading.Thread(target=_poll_loop, daemon=True).start()

    def toggle_connection(self, e):
        if self.is_connected:
            self._polling = False
            self.is_connected = False
            self._set_status(False)
            self.connect_btn.text = "Kết nối máy chủ"
            self.connect_btn.icon = ft.Icons.WIFI
            self.snapshot_btn.visible = False
            self._safe_update(self.connect_btn, self.snapshot_btn)
            self._append_log(time.strftime("%H:%M"), "Đã ngắt kết nối máy chủ", "info")
            return

        self.connect_btn.text = "Đang kết nối..."
        self.connect_btn.disabled = True
        self._safe_update(self.connect_btn)

        def _connect():
            try:
                data = fetch_dashboard(self.server_url)
                save_cache(data)
                self.is_connected = True
                self._set_status(True)
                self._apply_dashboard_data(data)
                self.connect_btn.text = "Ngắt kết nối"
                self.connect_btn.icon = ft.Icons.WIFI_OFF
                self.snapshot_btn.visible = True
                self._append_log(time.strftime("%H:%M"), "Kết nối máy chủ thành công", "success")
                self._start_polling()
            except Exception as err:
                self.is_connected = False
                self._set_status(False)
                self.connect_btn.text = "Thử lại"
                self.connect_btn.icon = ft.Icons.WIFI
                self.snapshot_btn.visible = False
                self._append_log(time.strftime("%H:%M"), f"Không kết nối được máy chủ: {str(err)[:60]}", "warning")
                self._load_offline_cache()
            finally:
                self.connect_btn.disabled = False
                self._safe_update(self.connect_btn, self.snapshot_btn)

        threading.Thread(target=_connect, daemon=True).start()

    def take_snapshot(self, e):
        if not self.is_connected:
            self._append_log(time.strftime("%H:%M"), "Cần kết nối máy chủ trước", "warning")
            return

        def _snapshot():
            try:
                b64_data = fetch_snapshot_base64(self.server_url)
                self.stream_image.src = ""
                self.stream_image.src_base64 = b64_data
                self._safe_update(self.stream_image)
                self._append_log(time.strftime("%H:%M"), "Đã chụp ảnh từ camera", "success")
            except Exception as err:
                self._append_log(time.strftime("%H:%M"), f"Lỗi chụp ảnh: {str(err)[:60]}", "warning")

        threading.Thread(target=_snapshot, daemon=True).start()



def build_live_monitoring():
    controller = LiveMonitoringController()
    if controller.config.get("auto_connect", False):
        threading.Thread(target=lambda: controller.toggle_connection(None), daemon=True).start()
    return controller.root
