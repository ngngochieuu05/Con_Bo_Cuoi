"""
Phiên Giám Sát – Farmer (Realtime Webcam)
- Chọn camera chuồng (DB) để liên kết cảnh báo
- Chọn thiết bị camera (index 0/1/2...)
- Chạy YOLO inference realtime trên từng frame
- Hiển thị frame có annotation, KPI, nhật ký phát hiện
"""
from __future__ import annotations

import threading
import time

import flet as ft

from bll.services.monitor_service import (
    get_farmer_cameras,
    run_inference_frame,
)
from dal.model_repo import get_all_models
from ui.theme import DANGER, PRIMARY, WARNING, glass_container, status_badge


_ALERT_LABELS: dict[str, tuple[str, str]] = {
    "cow_fight": ("⚔ Bò húc nhau",          DANGER),
    "cow_lie":   ("😴 Bò nằm bất thường",   WARNING),
    "cow_sick":  ("🤒 Bò có dấu hiệu bệnh", DANGER),
    "heat_high": ("🌡 Nhiệt độ cao",         WARNING),
}

_COLOR_RUNNING = "#22c55e"
_COLOR_STOPPED = "#94a3b8"

# Infer every frame; update UI every DISPLAY_EVERY frames
DISPLAY_EVERY = 1


# ─────────────────────────────────────────────────────────────────────────────
def build_live_monitoring(page: ft.Page = None) -> ft.Control:
    return LiveMonitoringController(page).root


# ─────────────────────────────────────────────────────────────────────────────
class LiveMonitoringController:
    def __init__(self, page: ft.Page | None):
        self._page         = page
        self._selected_cam = None
        self._is_streaming = False
        self._stop_flag    = threading.Event()
        self._frame_count  = 0

        self.root = ft.Column(expand=True, spacing=12, scroll=ft.ScrollMode.AUTO)
        self._build_ui()
        self._refresh_cameras()
        self._refresh_model_status()

    # ── helpers ───────────────────────────────────────────────────────────────
    def _safe_update(self, *controls):
        for ctrl in controls:
            try:
                if ctrl.page:
                    ctrl.update()
            except Exception:
                pass

    def _page_update(self):
        try:
            if self._page:
                self._page.update()
        except Exception:
            pass

    def _get_user_id(self) -> int | None:
        data = getattr(self._page, "data", None)
        if isinstance(data, dict):
            uid = data.get("user_id") or data.get("id_user")
            if uid:
                try:
                    return int(uid)
                except (ValueError, TypeError):
                    pass
        return None

    # ── build UI ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        self._status_chip = status_badge("Ngoại tuyến", "danger")
        self._last_update  = ft.Text("", size=11, color=ft.Colors.WHITE70)

        # Stream image (same style as original)
        self._stream_image = ft.Image(
            src="",
            fit=ft.ImageFit.CONTAIN,
            border_radius=12,
            error_content=ft.Text(
                "Không có tín hiệu camera",
                size=12,
                color=ft.Colors.WHITE70,
                text_align=ft.TextAlign.CENTER,
            ),
        )

        # KPI values
        self._kpi_objects = ft.Text("--", size=24, weight=ft.FontWeight.W_700)
        self._kpi_alerts  = ft.Text("--", size=24, weight=ft.FontWeight.W_700, color=DANGER)
        self._kpi_fps     = ft.Text("--", size=24, weight=ft.FontWeight.W_700, color=PRIMARY)

        # Camera dropdown (DB cameras for alert context)
        self._cam_dropdown = ft.Dropdown(
            label="Camera chuồng",
            hint_text="Chưa có camera",
            options=[],
            on_change=self._on_camera_change,
            width=260,
        )
        self._refresh_cam_btn = ft.TextButton(
            "Làm mới",
            on_click=lambda _: self._refresh_cameras(),
        )

        # Device camera index
        self._cam_idx_field = ft.TextField(
            value="0",
            label="Cam index",
            width=100,
            text_align=ft.TextAlign.CENTER,
            hint_text="0, 1, 2...",
        )

        # Start / Stop buttons
        self._start_btn = ft.ElevatedButton(
            "Bắt đầu",
            on_click=self._on_start,
        )
        self._stop_btn = ft.ElevatedButton(
            "Dừng",
            on_click=self._on_stop,
            disabled=True,
            style=ft.ButtonStyle(
                bgcolor={ft.ControlState.DEFAULT: ft.Colors.with_opacity(0.25, DANGER)},
                color=DANGER,
            ),
        )

        # Camera info line
        self._cam_info = ft.Text("", size=11, color=ft.Colors.WHITE70)

        # Alert log
        self._log_rows = ft.Column(spacing=8)

        # Model status chips
        self._model_chips = ft.Row(spacing=6, wrap=False)

        # ── layout ────────────────────────────────────────────────────────────
        self.root.controls = [
            # Header
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text("Giám sát trực tiếp", size=24, weight=ft.FontWeight.W_700),
                    self._status_chip,
                ],
            ),
            self._cam_info,

            # Stream panel
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
                            content=self._stream_image,
                        ),
                        ft.Row(
                            controls=[
                                self._cam_dropdown,
                                self._refresh_cam_btn,
                                self._cam_idx_field,
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=6,
                        ),
                        ft.Row(
                            controls=[
                                self._start_btn,
                                self._stop_btn,
                            ],
                            spacing=8,
                        ),
                    ],
                ),
            ),

            # Model status row
            glass_container(
                padding=10,
                radius=14,
                content=ft.Column(
                    spacing=6,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text("Trạng thái mô hình AI", size=13, weight=ft.FontWeight.W_600),
                                ft.TextButton("Làm mới", on_click=lambda _: self._refresh_model_status()),
                            ],
                        ),
                        self._model_chips,
                    ],
                ),
            ),

            # KPI row
            ft.Row(
                spacing=10,
                controls=[
                    ft.Container(
                        expand=1,
                        content=self._kpi_card("Phát hiện / frame", self._kpi_objects),
                    ),
                    ft.Container(
                        expand=1,
                        content=self._kpi_card("Cảnh báo mở", self._kpi_alerts),
                    ),
                    ft.Container(
                        expand=1,
                        content=self._kpi_card("FPS suy luận", self._kpi_fps),
                    ),
                ],
            ),

            # Alert / detection log
            glass_container(
                padding=14,
                radius=18,
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(
                                    "Nhật ký phát hiện",
                                    size=16,
                                    weight=ft.FontWeight.W_600,
                                ),
                                self._last_update,
                            ],
                        ),
                        self._log_rows,
                    ],
                ),
            ),
        ]

    def _kpi_card(self, title: str, value_control: ft.Control):
        return glass_container(
            padding=12,
            radius=16,
            content=ft.Column(
                tight=True,
                controls=[
                    ft.Text(title, size=12, color=ft.Colors.WHITE70),
                    value_control,
                ],
            ),
        )

    # ── model status ──────────────────────────────────────────────────────────
    def _refresh_model_status(self):
        _TYPE_LABEL = {
            "cattle_detect": "Nhận diện bò",
            "behavior":      "Hành vi",
            "disease":       "Bệnh",
        }
        try:
            models = get_all_models()
        except Exception:
            models = []

        chips = []
        for m in models:
            loai     = m.get("loai_mo_hinh", "custom")
            label    = _TYPE_LABEL.get(loai, loai)
            status   = m.get("trang_thai", "offline")
            has_file = bool(m.get("duong_dan_file", "").strip())

            if status == "online" and has_file:
                bg, txt_color, note = "#1a3a1f", "#4ade80", "Hoạt động"
            elif status == "online" and not has_file:
                bg, txt_color, note = "#3a2e0a", "#facc15", "Thiếu file"
            elif status == "testing":
                bg, txt_color, note = "#0f2a3a", "#38bdf8", "Thử nghiệm"
            else:
                bg, txt_color, note = "#1e1e2e", "#94a3b8", "Ngoại tuyến"

            chips.append(
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    border_radius=10,
                    bgcolor=bg,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.3, txt_color)),
                    content=ft.Column(
                        spacing=2,
                        tight=True,
                        controls=[
                            ft.Text(label, size=11, weight=ft.FontWeight.W_600, color=txt_color),
                            ft.Text(note, size=10, color=ft.Colors.with_opacity(0.8, txt_color)),
                        ],
                    ),
                )
            )

        self._model_chips.controls = chips
        self._safe_update(self._model_chips)

    # ── camera management ─────────────────────────────────────────────────────
    def _refresh_cameras(self):
        user_id = self._get_user_id()
        cameras = get_farmer_cameras(user_id) if user_id else []

        opts = []
        for cam in cameras:
            area     = cam.get("khu_vuc_chuong") or cam.get("id_chuong") or "?"
            cam_code = cam.get("id_camera", "?")
            status   = cam.get("trang_thai", "")
            icon     = "🟢" if status == "online" else ("🟡" if status == "warning" else "🔴")
            opts.append(ft.dropdown.Option(
                key=str(cam.get("id_camera_chuong")),
                text=f"{icon} {area} – {cam_code}",
            ))

        self._cam_dropdown.options = opts
        if opts:
            self._cam_dropdown.value = opts[0].key
            self._on_camera_change(None)
        else:
            self._cam_info.value = "Chưa có camera nào được gán cho tài khoản này."
        self._safe_update(self._cam_dropdown, self._cam_info)

    def _on_camera_change(self, _e):
        val = self._cam_dropdown.value
        if not val:
            return
        user_id = self._get_user_id()
        cameras = get_farmer_cameras(user_id) if user_id else []
        cam = next(
            (c for c in cameras if str(c.get("id_camera_chuong")) == str(val)),
            None,
        )
        if cam:
            self._selected_cam = cam
            status_map = {
                "online":  "Trực tuyến",
                "warning": "Cảnh báo",
                "offline": "Ngoại tuyến",
            }
            status_txt = status_map.get(cam.get("trang_thai", ""), cam.get("trang_thai", ""))
            area = cam.get("khu_vuc_chuong") or cam.get("id_chuong") or "?"
            id_camera = cam.get("id_camera", "")
            self._cam_info.value = (
                f"{area} · Camera: {id_camera} · Trạng thái: {status_txt}"
            )
            # Đồng bộ cam index từ id_camera (CAM-01 → 0, CAM-02 → 1...)
            import re as _re
            digits = _re.search(r"\d+", id_camera)
            if digits:
                idx = max(0, int(digits.group()) - 1)
                self._cam_idx_field.value = str(idx)
            self._safe_update(self._cam_info, self._cam_idx_field)

    # ── stream control ────────────────────────────────────────────────────────
    def _on_start(self, _e):
        if self._is_streaming:
            return
        try:
            cam_idx = int(self._cam_idx_field.value or "0")
        except ValueError:
            cam_idx = 0

        self._is_streaming  = True
        self._frame_count   = 0
        self._stop_flag.clear()
        self._start_btn.disabled = True
        self._stop_btn.disabled  = False
        self._status_chip.content.value = "Đang chạy"
        self._status_chip.bgcolor = ft.Colors.with_opacity(0.18, _COLOR_RUNNING)
        self._status_chip.border  = ft.border.all(1, ft.Colors.with_opacity(0.4, _COLOR_RUNNING))
        self._safe_update(self._start_btn, self._stop_btn, self._status_chip)

        threading.Thread(
            target=self._stream_loop,
            args=(cam_idx,),
            daemon=True,
        ).start()

    def _on_stop(self, _e):
        self._stop_flag.set()

    def _set_stopped_ui(self):
        self._is_streaming = False
        self._start_btn.disabled = False
        self._stop_btn.disabled  = True
        self._status_chip.content.value = "Đã dừng"
        self._status_chip.bgcolor = ft.Colors.with_opacity(0.18, _COLOR_STOPPED)
        self._status_chip.border  = ft.border.all(1, ft.Colors.with_opacity(0.4, _COLOR_STOPPED))
        self._page_update()

    # ── inference loop ────────────────────────────────────────────────────────
    def _stream_loop(self, cam_idx: int):
        try:
            import cv2
        except ImportError:
            self._append_log(
                time.strftime("%H:%M"),
                "❌ opencv-python chưa được cài đặt.",
                "warning",
            )
            self._set_stopped_ui()
            return

        cap = cv2.VideoCapture(cam_idx)
        if not cap.isOpened():
            self._append_log(
                time.strftime("%H:%M"),
                f"❌ Không mở được camera index {cam_idx}.",
                "warning",
            )
            self._set_stopped_ui()
            return

        self._append_log(time.strftime("%H:%M"), f"Camera {cam_idx} đã kết nối", "success")

        user_id = self._get_user_id() or 0
        cam_id  = int((self._selected_cam or {}).get("id_camera_chuong", 0))

        while not self._stop_flag.is_set():
            t0 = time.perf_counter()
            ok, frame = cap.read()
            if not ok:
                self._append_log(time.strftime("%H:%M"), "Camera mất tín hiệu", "warning")
                break

            result  = run_inference_frame(frame, user_id, cam_id)
            elapsed = time.perf_counter() - t0
            fps     = max(1, round(1.0 / elapsed))

            self._frame_count += 1
            self._apply_result(result, fps)

        cap.release()
        self._set_stopped_ui()
        self._append_log(time.strftime("%H:%M"), "Camera đã ngắt kết nối", "info")

    def _apply_result(self, result: dict, fps: int):
        b64 = result.get("annotated_base64")
        if b64:
            self._stream_image.src        = ""
            self._stream_image.src_base64 = b64

        detections = result.get("detections", [])
        alerts     = result.get("alerts_created", [])
        error      = result.get("error")

        self._kpi_objects.value      = str(len(detections))
        self._kpi_fps.value          = str(fps)
        self._last_update.value      = f"Cập nhật: {time.strftime('%H:%M:%S')}"

        if alerts:
            try:
                from dal.canh_bao_repo import count_open
                self._kpi_alerts.value = str(count_open())
            except Exception:
                pass
            for at in alerts:
                label, _ = _ALERT_LABELS.get(at, (at, DANGER))
                self._append_log(time.strftime("%H:%M"), f"⚠ {label}", "warning")

        if error:
            self._append_log(time.strftime("%H:%M"), f"Lỗi: {error[:80]}", "warning")

        # Log detections every 50 frames (~5s at 10fps)
        if detections and self._frame_count % 50 == 1:
            names = ", ".join(d["class"] for d in detections[:4])
            self._append_log(
                time.strftime("%H:%M"),
                f"Phát hiện: {names}",
                "info",
            )

        self._page_update()

    # ── alert log ─────────────────────────────────────────────────────────────
    def _append_log(self, time_label: str, message: str, kind: str = "info"):
        color_map = {
            "warning": DANGER,
            "success": PRIMARY,
            "info":    ft.Colors.WHITE70,
        }
        color = color_map.get(kind, ft.Colors.WHITE70)
        self._log_rows.controls.insert(
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
        if len(self._log_rows.controls) > 10:
            self._log_rows.controls.pop()