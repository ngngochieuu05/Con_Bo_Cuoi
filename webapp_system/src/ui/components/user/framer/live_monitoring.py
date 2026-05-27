from __future__ import annotations

import threading
import time
from pathlib import Path

import flet as ft

from bll.services.monitor_service import (
    get_farmer_cameras,
    load_config,
    run_inference_frame,
    count_open_alerts,
    get_all_models_info,
    create_monitor_session,
    finish_monitor_session,
)
from ui.theme import DANGER, PRIMARY, WARNING, glass_container, status_badge
from ui.upload_bridge import (
    build_upload_batch,
    get_app_mode,
    is_web_picker_file,
    wait_for_uploaded_file,
)


_ALERT_LABELS: dict[str, tuple[str, str]] = {
    "cow_fight": ("Bò húc nhau", DANGER),
    "cow_lie": ("Bò nằm bất thường", WARNING),
    "cow_sick": ("Bò có dấu hiệu bệnh", DANGER),
    "heat_high": ("Nhiệt độ cao", WARNING),
}

_MODEL_LABELS = {
    "cattle_detect": "Nhận diện bò",
    "behavior": "Hành vi",
    "disease": "Bệnh",
    "disease_cls": "Phân loại bệnh",
}

_RUNNING_COLOR = "#22c55e"
_STOPPED_COLOR = "#94a3b8"
_HOST_CAMERA_SLOTS = 2


def build_live_monitoring(page: ft.Page | None = None) -> ft.Control:
    return LiveMonitoringController(page).root


class LiveMonitoringController:
    def __init__(self, page: ft.Page | None):
        self._page = page
        self._app_mode = get_app_mode(page)
        self._selected_cam: dict | None = None
        self._all_cameras: list[dict] = []
        self._test_source: dict | None = None


def build_live_monitoring(page: ft.Page | None = None) -> ft.Control:
    return LiveMonitoringController(page).root


class LiveMonitoringController:
    def __init__(self, page: ft.Page | None):
        self._page = page
        self._app_mode = get_app_mode(page)
        self._selected_cam: dict | None = None
        self._all_cameras: list[dict] = []
        self._test_source: dict | None = None
        self._pending_picker_uploads: dict[str, dict] = {}
        self._is_streaming = False
        self._stop_flag = threading.Event()
        self._frame_count = 0
        self._active_session_id: int | None = None
        self._host_cameras: list[dict] = []
        self._cached_alert_count = "--"
        self._last_alert_count_update_frame = -999

        self.root = ft.Column(expand=True, spacing=12, scroll=ft.ScrollMode.AUTO)
        self._build_ui()
        self._refresh_host_cameras(force=True)
        self._refresh_cameras()
        self._refresh_model_status()
        self._start_camera_inventory_poll()

    def _build_ui(self) -> None:
        cfg = load_config()
        monitor_idx = str(cfg.get("monitor_camera_index", cfg.get("camera_index", 0)))

        self._status_chip = status_badge("Ngoại tuyến", "danger")
        self._mode_chip = status_badge(
            "Web mode: camera máy chủ" if self._app_mode == "web" else "Desktop mode",
            "warning" if self._app_mode == "web" else "primary",
        )
        self._cam_info = ft.Text("", size=11, color=ft.Colors.WHITE70)
        self._last_update = ft.Text("", size=11, color=ft.Colors.WHITE54)

        self._stream_image = ft.Image(
            src="",
            fit=ft.ImageFit.CONTAIN,
            border_radius=16,
            error_content=ft.Column(
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.VIDEOCAM_OFF_OUTLINED, size=36, color=ft.Colors.WHITE30),
                    ft.Text(
                        "Chưa có tín hiệu camera hoặc nguồn test.",
                        size=12,
                        color=ft.Colors.WHITE60,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
            ),
        )

        self._kpi_objects = ft.Text("--", size=24, weight=ft.FontWeight.W_700)
        self._kpi_alerts = ft.Text("--", size=24, weight=ft.FontWeight.W_700, color=DANGER)
        self._kpi_fps = ft.Text("--", size=24, weight=ft.FontWeight.W_700, color=PRIMARY)

        self._cam_idx_field = ft.Dropdown(
            value=monitor_idx,
            label="Chọn camera máy chủ",
            options=self._build_camera_options(monitor_idx),
            expand=True,
            text_size=12,
            border_radius=12,
            content_padding=ft.padding.symmetric(horizontal=10, vertical=6),
        )

        self._test_source_text = ft.Text(
            "Nguồn camera trực tiếp",
            size=11,
            color=ft.Colors.WHITE60,
            expand=True,
            max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self._file_picker_video = ft.FilePicker(
            on_result=self._on_pick_video,
            on_upload=self._on_video_picker_upload,
        )
        self._file_picker_images = ft.FilePicker(
            on_result=self._on_pick_images,
            on_upload=self._on_images_picker_upload,
        )
        self._clear_test_btn = ft.IconButton(
            icon=ft.Icons.CLOSE,
            icon_color=ft.Colors.RED_300,
            tooltip="Quay lại camera trực tiếp",
            visible=False,
            on_click=self._on_clear_test,
        )

        self._start_btn = ft.ElevatedButton(
            "Bắt đầu",
            expand=True,
            style=ft.ButtonStyle(
                bgcolor={ft.ControlState.DEFAULT: PRIMARY},
                color=ft.Colors.WHITE,
                shape=ft.RoundedRectangleBorder(radius=12),
            ),
            on_click=self._on_start,
        )
        self._stop_btn = ft.ElevatedButton(
            "Dừng",
            expand=True,
            disabled=True,
            style=ft.ButtonStyle(
                bgcolor={ft.ControlState.DEFAULT: ft.Colors.with_opacity(0.18, DANGER)},
                color={ft.ControlState.DEFAULT: DANGER, ft.ControlState.DISABLED: ft.Colors.WHITE30},
                shape=ft.RoundedRectangleBorder(radius=12),
            ),
            on_click=self._on_stop,
        )

        self._model_chips = ft.Row(spacing=8, scroll=ft.ScrollMode.AUTO)
        self._log_rows = ft.Column(spacing=8)

        self.root.controls = [
            ft.Column(
                spacing=4,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("Giám sát trực tiếp", size=22, weight=ft.FontWeight.W_700),
                            self._status_chip,
                        ],
                    ),
                    ft.Row(
                        spacing=8,
                        controls=[
                            self._mode_chip,
                            status_badge("Cho phép camera máy chủ" if self._app_mode == "web" else "Luồng camera cục bộ"),
                        ],
                    ),
                    self._cam_info,
                ],
            ),
            glass_container(
                padding=14,
                radius=20,
                content=ft.Column(
                    spacing=12,
                    controls=[
                        ft.Container(
                            height=240,
                            border_radius=16,
                            bgcolor=ft.Colors.with_opacity(0.22, ft.Colors.BLACK),
                            alignment=ft.alignment.center,
                            content=self._stream_image,
                        ),
                        ft.Column(
                            spacing=8,
                            controls=[
                                ft.Row(
                                    spacing=8,
                                    controls=[
                                        self._cam_idx_field,
                                        self._icon_action(
                                            ft.Icons.VIDEO_FILE_OUTLINED,
                                            "Chọn video test",
                                            ft.Colors.AMBER_300,
                                            self._pick_video_direct,
                                        ),
                                        self._icon_action(
                                            ft.Icons.PHOTO_LIBRARY_OUTLINED,
                                            "Chọn ảnh test",
                                            ft.Colors.LIGHT_BLUE_300,
                                            self._pick_images_direct,
                                        ),
                                    ],
                                ),
                                ft.Row(
                                    spacing=8,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    controls=[self._test_source_text, self._clear_test_btn],
                                ),
                                ft.Row(
                                    spacing=8,
                                    controls=[self._start_btn, self._stop_btn],
                                ),
                                ft.Row(
                                    spacing=8,
                                    controls=[
                                        ft.OutlinedButton(
                                            "Testcase bò húc nhau",
                                            icon=ft.Icons.WARNING_AMBER_ROUNDED,
                                            on_click=lambda _e: self._on_test_alert("cow_fight"),
                                        ),
                                        ft.OutlinedButton(
                                            "Testcase bò bỏ ăn",
                                            icon=ft.Icons.RESTAURANT_OUTLINED,
                                            on_click=lambda _e: self._on_test_alert("cow_lie"),
                                        ),
                                    ],
                                ),
                                self._last_update,
                            ],
                        ),
                    ],
                ),
            ),
            ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.Container(expand=1, content=self._metric_card("Phát hiện / frame", self._kpi_objects)),
                            ft.Container(expand=1, content=self._metric_card("Cảnh báo đang mở", self._kpi_alerts)),
                        ],
                    ),
                    ft.Container(expand=False, content=self._metric_card("FPS suy luận", self._kpi_fps)),
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
                                ft.Text("Mô hình AI đang dùng", size=15, weight=ft.FontWeight.W_600),
                                ft.TextButton("Làm mới", on_click=lambda _: self._refresh_model_status()),
                            ],
                        ),
                        self._model_chips,
                    ],
                ),
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
                                ft.Text("Nhật ký phát hiện", size=15, weight=ft.FontWeight.W_600),
                                ft.TextButton("Xóa", on_click=lambda _: self._clear_log()),
                            ],
                        ),
                        self._log_rows,
                    ],
                ),
            ),
        ]

    def _icon_action(self, icon_name, tooltip: str, color: str, on_click) -> ft.Control:
        return ft.IconButton(
            icon=icon_name,
            tooltip=tooltip,
            icon_color=color,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.with_opacity(0.14, color),
                shape=ft.RoundedRectangleBorder(radius=12),
            ),
            on_click=on_click,
        )

    def _metric_card(self, title: str, value_control: ft.Control) -> ft.Control:
        return glass_container(
            padding=12,
            radius=16,
            content=ft.Column(
                tight=True,
                spacing=4,
                controls=[
                    ft.Text(title, size=12, color=ft.Colors.WHITE70),
                    value_control,
                ],
            ),
        )

    def _build_camera_options(self, current_value: str | None = None) -> list[ft.dropdown.Option]:
        current_index = 0
        try:
            current_index = max(0, int(str(current_value or "0").strip()))
        except (TypeError, ValueError):
            current_index = 0
        if self._host_cameras:
            options = [
                ft.dropdown.Option(key=str(cam["index"]), text=str(cam["label"]))
                for cam in self._host_cameras
            ]
            if not any(opt.key == str(current_index) for opt in options):
                options.append(ft.dropdown.Option(key=str(current_index), text=f"cam{current_index + 1}"))
            return options
        total_slots = max(_HOST_CAMERA_SLOTS, current_index + 1)
        return [ft.dropdown.Option(key=str(idx), text=f"cam{idx + 1}") for idx in range(total_slots)]

    def _camera_name(self, cam_idx: int) -> str:
        normalized = max(0, int(cam_idx))
        for cam in self._host_cameras:
            if int(cam.get("index", -1)) == normalized:
                return str(cam.get("label") or f"cam{normalized + 1}")
        return f"cam{normalized + 1}"

    def _refresh_host_cameras(self, force: bool = False) -> None:
        discovered = [{"index": idx, "label": f"cam{idx + 1}"} for idx in range(_HOST_CAMERA_SLOTS)]
        if not force and discovered == self._host_cameras:
            return
        self._host_cameras = discovered
        current_value = self._cam_idx_field.value or "0"
        available_keys = {str(item["index"]) for item in discovered}
        if current_value not in available_keys:
            current_value = str(discovered[0]["index"])
            self._cam_idx_field.value = current_value
        self._cam_idx_field.options = self._build_camera_options(current_value)
        self._safe_update(self._cam_idx_field)

    def _start_camera_inventory_poll(self) -> None:
        return

    def _safe_update(self, *controls: ft.Control) -> None:
        for control in controls:
            try:
                if control.page:
                    control.update()
            except Exception:
                pass

    def _page_update(self) -> None:
        try:
            if self._page:
                self._page.update()
        except Exception:
            pass

    def _get_user_id(self) -> int | None:
        data = getattr(self._page, "data", None)
        if isinstance(data, dict):
            uid = data.get("user_id") or data.get("id_user")
            if uid is not None:
                try:
                    return int(uid)
                except (TypeError, ValueError):
                    pass
        if self._page:
            try:
                uid = self._page.client_storage.get("user_id")
                if uid is not None:
                    return int(uid)
            except Exception:
                pass
        return None

    def _refresh_cameras(self) -> None:
        user_id = self._get_user_id()
        self._all_cameras = get_farmer_cameras(user_id) if user_id else []
        if not self._all_cameras:
            self._selected_cam = None
            self._cam_info.value = "Chưa có camera nào được gán cho tài khoản này."
            self._safe_update(self._cam_info)
            return
        self._select_camera(self._all_cameras[0])

    def _select_camera(self, camera: dict) -> None:
        self._selected_cam = camera
        status_map = {
            "online": "Trực tuyến",
            "warning": "Cảnh báo",
            "offline": "Ngoại tuyến",
        }
        status = status_map.get(camera.get("trang_thai"), str(camera.get("trang_thai", "--")))
        area = camera.get("khu_vuc_chuong") or camera.get("id_chuong") or "Khu chưa đặt tên"
        camera_code = camera.get("id_camera") or camera.get("ten_camera") or f"Cam {camera.get('id_camera_chuong', '--')}"
        self._cam_info.value = f"{area} • {camera_code} • {status}"
        self._safe_update(self._cam_info)

    def _refresh_model_status(self) -> None:
        try:
            models = get_all_models_info()
        except Exception:
            models = []

        chips: list[ft.Control] = []
        for model in models:
            model_type = model.get("loai_mo_hinh", "custom")
            label = _MODEL_LABELS.get(model_type, model_type)
            status = model.get("trang_thai", "offline")
            has_file = bool(str(model.get("duong_dan_file", "")).strip())
            if status == "online" and has_file:
                bg, text_color, note = "#1a3a1f", "#4ade80", "Hoạt động"
            elif status == "online":
                bg, text_color, note = "#3a2e0a", "#facc15", "Thiếu file"
            elif status == "testing":
                bg, text_color, note = "#0f2a3a", "#38bdf8", "Thử nghiệm"
            else:
                bg, text_color, note = "#1e1e2e", "#94a3b8", "Ngoại tuyến"
            chips.append(
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=10, vertical=8),
                    border_radius=12,
                    bgcolor=bg,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.28, text_color)),
                    content=ft.Column(
                        tight=True,
                        spacing=2,
                        controls=[
                            ft.Text(label, size=11, color=text_color, weight=ft.FontWeight.W_600),
                            ft.Text(note, size=10, color=ft.Colors.with_opacity(0.85, text_color)),
                        ],
                    ),
                )
            )
        if not chips:
            chips = [ft.Text("Chưa có model nào khả dụng.", size=12, color=ft.Colors.WHITE60)]
        self._model_chips.controls = chips
        self._safe_update(self._model_chips)

    def _ensure_pickers_on_page(self) -> bool:
        if not self._page:
            return False
        changed = False
        if self._file_picker_video not in self._page.overlay:
            self._page.overlay.append(self._file_picker_video)
            changed = True
        if self._file_picker_images not in self._page.overlay:
            self._page.overlay.append(self._file_picker_images)
            changed = True
        if changed:
            self._page.update()
        return True

    def stop_stream(self) -> None:
        if self._is_streaming:
            self._stop_flag.set()

    def _queue_picker_upload(self, picker: ft.FilePicker, key: str, files: list, subdir: str, kind: str) -> None:
        if not self._page:
            return
        items, jobs = build_upload_batch(self._page, files, subdir=subdir)
        self._pending_picker_uploads[key] = {"kind": kind, "items": items}
        self._append_log(time.strftime("%H:%M"), "Đang tải nguồn từ thiết bị lên server...", "info")
        picker.upload(jobs)

    def _handle_picker_upload(self, key: str, event: ft.FilePickerUploadEvent) -> None:
        state = self._pending_picker_uploads.get(key)
        if not state:
            return
        if event.error:
            self._pending_picker_uploads.pop(key, None)
            self._append_log(time.strftime("%H:%M"), f"Upload lỗi: {event.error}", "warning")
            return
        if event.progress != 1.0:
            return
        for item in state["items"]:
            if item["name"] == event.file_name and not item["done"]:
                item["done"] = True
                break
        if all(item["done"] for item in state["items"]):
            self._finalize_picker_upload(key)

    def _finalize_picker_upload(self, key: str) -> None:
        state = self._pending_picker_uploads.pop(key, None)
        if not state:
            return
        kind = state["kind"]
        items = state["items"]
        if kind == "video":
            uploaded = wait_for_uploaded_file(items[0]["server_path"])
            if not uploaded:
                self._append_log(time.strftime("%H:%M"), "Video chưa được lưu thành công lên server.", "warning")
                return
            self._set_test_source({"type": "video", "path": str(uploaded)}, f"Video: {items[0]['name']}", ft.Colors.AMBER_300)
            self._append_log(time.strftime("%H:%M"), "Video đã sẵn sàng để chạy realtime.", "success")
            return
        uploaded_paths = []
        for item in items:
            saved = wait_for_uploaded_file(item["server_path"])
            if saved:
                uploaded_paths.append(str(saved))
        if not uploaded_paths:
            self._append_log(time.strftime("%H:%M"), "Ảnh chưa được lưu thành công lên server.", "warning")
            return
        self._set_test_source(
            {"type": "images", "paths": uploaded_paths},
            f"{len(uploaded_paths)} ảnh đã chọn",
            ft.Colors.LIGHT_BLUE_300,
        )
        self._append_log(time.strftime("%H:%M"), f"Đã nhận {len(uploaded_paths)} ảnh từ thiết bị.", "success")

    def _set_test_source(self, source: dict, label: str, color: str) -> None:
        self._test_source = source
        self._test_source_text.value = label
        self._test_source_text.color = color
        self._clear_test_btn.visible = True
        self._safe_update(self._test_source_text, self._clear_test_btn)

    def _on_video_picker_upload(self, event: ft.FilePickerUploadEvent) -> None:
        self._handle_picker_upload("video", event)

    def _on_images_picker_upload(self, event: ft.FilePickerUploadEvent) -> None:
        self._handle_picker_upload("images", event)

    def _pick_video_direct(self, _event) -> None:
        if not self._ensure_pickers_on_page():
            return
        self._file_picker_video.pick_files(
            dialog_title="Chọn video từ thiết bị",
            file_type=ft.FilePickerFileType.VIDEO,
            allowed_extensions=["mp4", "avi", "mov", "mkv", "wmv"],
        )

    def _pick_images_direct(self, _event) -> None:
        if not self._ensure_pickers_on_page():
            return
        self._file_picker_images.pick_files(
            dialog_title="Chụp ảnh hoặc chọn từ thư viện",
            file_type=ft.FilePickerFileType.IMAGE,
            allowed_extensions=["jpg", "jpeg", "png", "bmp", "webp"],
            allow_multiple=True,
        )

    def _on_pick_video(self, event: ft.FilePickerResultEvent) -> None:
        if not event.files:
            return
        file_obj = event.files[0]
        if is_web_picker_file(file_obj):
            self._queue_picker_upload(
                self._file_picker_video,
                "video",
                [file_obj],
                subdir="live_monitoring/videos",
                kind="video",
            )
            return
        if getattr(file_obj, "path", None):
            self._set_test_source(
                {"type": "video", "path": file_obj.path},
                f"Video: {file_obj.name}",
                ft.Colors.AMBER_300,
            )

    def _on_pick_images(self, event: ft.FilePickerResultEvent) -> None:
        if not event.files:
            return
        if any(is_web_picker_file(file_obj) for file_obj in event.files):
            self._queue_picker_upload(
                self._file_picker_images,
                "images",
                list(event.files),
                subdir="live_monitoring/images",
                kind="images",
            )
            return
        paths = [file_obj.path for file_obj in event.files if getattr(file_obj, "path", None)]
        if not paths:
            self._append_log(time.strftime("%H:%M"), "Không lấy được đường dẫn ảnh đã chọn.", "warning")
            return
        self._set_test_source(
            {"type": "images", "paths": paths},
            f"{len(paths)} ảnh đã chọn",
            ft.Colors.LIGHT_BLUE_300,
        )

    def _on_clear_test(self, _event) -> None:
        self._test_source = None
        self._test_source_text.value = "Nguồn camera trực tiếp"
        self._test_source_text.color = ft.Colors.WHITE60
        self._clear_test_btn.visible = False
        self._safe_update(self._test_source_text, self._clear_test_btn)

    def _on_start(self, _event) -> None:
        if self._is_streaming:
            return
        self._frame_count = 0
        self._stop_flag.clear()
        try:
            from bll.services.alert_service import reset_camera_state

            reset_camera_state(int((self._selected_cam or {}).get("id_camera_chuong", 0)))
        except Exception:
            pass
        self._is_streaming = True
        self._start_btn.disabled = True
        self._stop_btn.disabled = False
        self._status_chip.content.value = "Đang chạy"
        self._status_chip.bgcolor = ft.Colors.with_opacity(0.18, _RUNNING_COLOR)
        self._status_chip.border = ft.border.all(1, ft.Colors.with_opacity(0.40, _RUNNING_COLOR))
        self._safe_update(self._start_btn, self._stop_btn, self._status_chip)
        self._begin_monitor_session()

        if self._test_source:
            threading.Thread(target=self._stream_loop_test, args=(self._test_source,), daemon=True).start()
            return

        try:
            cam_idx = int((self._cam_idx_field.value or "0").strip())
        except ValueError:
            cam_idx = 0
        if self._app_mode == "web":
            self._append_log(
                time.strftime("%H:%M"),
                f"Web mode đang mở {self._camera_name(cam_idx)} của máy chủ.",
                "info",
            )
        threading.Thread(target=self._stream_loop, args=(cam_idx,), daemon=True).start()

    def _on_stop(self, _event) -> None:
        self._stop_flag.set()

    def _on_test_alert(self, alert_type: str) -> None:
        user_id = self._get_user_id() or 0
        camera_id = int((self._selected_cam or {}).get("id_camera_chuong", 0))
        try:
            from bll.services.alert_service import send_test_alert

            ok = bool(send_test_alert(alert_type, user_id, camera_id))
            if ok:
                label, _color = _ALERT_LABELS.get(alert_type, (alert_type, DANGER))
                self._append_log(time.strftime("%H:%M"), f"Đã gửi testcase Telegram: {label}", "success")
            else:
                self._append_log(time.strftime("%H:%M"), "Không gửi được testcase Telegram.", "warning")
        except Exception as ex:
            self._append_log(time.strftime("%H:%M"), f"Lỗi testcase Telegram: {str(ex)[:120]}", "warning")

    def _begin_monitor_session(self) -> None:
        user_id = self._get_user_id() or 0
        source_type = "camera"
        try:
            source_label = self._camera_name(int(self._cam_idx_field.value or "0"))
        except (TypeError, ValueError):
            source_label = "cam1"
        if self._test_source:
            source_type = self._test_source.get("type", "test")
            if source_type == "video":
                source_label = Path(self._test_source.get("path", "")).name
            elif source_type == "images":
                source_label = f"{len(self._test_source.get('paths', []))} ảnh"
        camera_label = self._cam_info.value or "Camera giám sát"
        try:
            session = create_monitor_session(
                id_user=user_id,
                camera_label=camera_label,
                source_type=source_type,
                source_label=source_label,
                status="running",
            )
            self._active_session_id = int(session.get("id_session") or 0)
        except Exception:
            self._active_session_id = None

    def _finish_monitor_session(self, status: str) -> None:
        if not self._active_session_id:
            return
        try:
            finish_monitor_session(self._active_session_id, status=status, frame_count=self._frame_count)
        finally:
            self._active_session_id = None

    def _finalize_stream(self, status: str, message: str | None = None, kind: str = "info") -> None:
        self._is_streaming = False
        self._start_btn.disabled = False
        self._stop_btn.disabled = True
        self._status_chip.content.value = "Đã dừng"
        self._status_chip.bgcolor = ft.Colors.with_opacity(0.18, _STOPPED_COLOR)
        self._status_chip.border = ft.border.all(1, ft.Colors.with_opacity(0.40, _STOPPED_COLOR))
        self._finish_monitor_session(status)
        if message:
            self._append_log(time.strftime("%H:%M"), message, kind)
        self._page_update()

    def _stream_loop(self, cam_idx: int) -> None:
        try:
            import cv2
        except ImportError:
            self._finalize_stream("failed", "Thiếu gói opencv-python.", "warning")
            return

        cap = cv2.VideoCapture(cam_idx)
        if not cap.isOpened():
            self._finalize_stream("failed", f"Không mở được {self._camera_name(cam_idx)} của máy chủ.", "warning")
            return

        self._append_log(time.strftime("%H:%M"), f"{self._camera_name(cam_idx)} của máy chủ đã kết nối.", "success")
        user_id = self._get_user_id() or 0
        camera_id = int((self._selected_cam or {}).get("id_camera_chuong", 0))
        try:
            while not self._stop_flag.is_set():
                started = time.perf_counter()
                ok, frame = cap.read()
                if not ok:
                    self._append_log(time.strftime("%H:%M"), "Camera mất tín hiệu.", "warning")
                    break
                result = run_inference_frame(frame, user_id, camera_id)
                elapsed = time.perf_counter() - started
                fps = max(1, round(1.0 / max(elapsed, 1e-6)))
                self._frame_count += 1
                self._apply_result(result, fps)
        finally:
            cap.release()

        status = "stopped" if self._stop_flag.is_set() else "completed"
        self._finalize_stream(status, "Phiên camera máy chủ đã kết thúc.")

    def _stream_loop_test(self, source: dict) -> None:
        try:
            import cv2
        except ImportError:
            self._finalize_stream("failed", "Thiếu gói opencv-python.", "warning")
            return

        source_type = source.get("type")
        user_id = self._get_user_id() or 0
        camera_id = int((self._selected_cam or {}).get("id_camera_chuong", 0))
        if source_type == "video":
            path = str(source.get("path", ""))
            cap = cv2.VideoCapture(path)
            if not cap.isOpened():
                self._finalize_stream("failed", f"Không mở được video: {Path(path).name}", "warning")
                return
            self._append_log(
                time.strftime("%H:%M"),
                f"Đang chạy video test: {Path(path).name}.",
                "success",
            )
            target_fps = 60.0
            frame_delay = 1.0 / target_fps
            try:
                while not self._stop_flag.is_set():
                    started = time.perf_counter()
                    ok, frame = cap.read()
                    if not ok:
                        # Re-open video to loop reliably across all codecs, avoiding infinite freezes
                        cap.release()
                        time.sleep(0.03)  # Small safety delay
                        cap = cv2.VideoCapture(path)
                        ok, frame = cap.read()
                        if not ok:
                            break
                        continue
                    result = run_inference_frame(frame, user_id, camera_id)
                    elapsed = time.perf_counter() - started
                    
                    # Target 60 FPS pacing
                    sleep_time = frame_delay - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                        
                    total_elapsed = time.perf_counter() - started
                    fps = max(1, round(1.0 / max(total_elapsed, 1e-6)))
                    self._frame_count += 1
                    self._apply_result(result, fps)
            finally:
                cap.release()
            self._finalize_stream("completed", "Phiên video test đã kết thúc.")
            return

        image_paths = [path for path in source.get("paths", []) if path]
        if not image_paths:
            self._finalize_stream("failed", "Không có ảnh test để chạy.", "warning")
            return
        self._append_log(time.strftime("%H:%M"), f"Đang chạy {len(image_paths)} ảnh test.", "success")
        index = 0
        while not self._stop_flag.is_set():
            started = time.perf_counter()
            frame = cv2.imread(image_paths[index % len(image_paths)])
            index += 1
            if frame is None:
                continue
            result = run_inference_frame(frame, user_id, camera_id)
            elapsed = time.perf_counter() - started
            fps = max(1, round(1.0 / max(elapsed, 1e-6)))
            self._frame_count += 1
            self._apply_result(result, fps)
        self._finalize_stream("stopped", "Phiên ảnh test đã dừng.")
        self._safe_update(self._log_rows)

    def _apply_result(self, result: dict, fps: int) -> None:
        annotated_base64 = result.get("annotated_base64")
        if annotated_base64:
            self._stream_image.src = ""
            self._stream_image.src_base64 = annotated_base64

        detections = result.get("detections", [])
        alerts = result.get("alerts_created", [])
        error = result.get("error")

        self._kpi_objects.value = str(len(detections))
        self._kpi_fps.value = str(fps)
        self._last_update.value = f"Cập nhật: {time.strftime('%H:%M:%S')}"

        # Update alert count with lower frequency / caching to avoid PostgreSQL query bottleneck
        should_update_alert_count = (
            len(alerts) > 0 
            or self._frame_count <= 5 
            or (self._frame_count - self._last_alert_count_update_frame) >= 60
        )
        if should_update_alert_count:
            try:
                self._cached_alert_count = str(count_open_alerts())
                self._last_alert_count_update_frame = self._frame_count
            except Exception:
                if alerts:
                    self._cached_alert_count = str(len(alerts))
        
        self._kpi_alerts.value = self._cached_alert_count

        if alerts:
            for alert_type in alerts:
                label, _color = _ALERT_LABELS.get(alert_type, (alert_type, DANGER))
                self._append_log(time.strftime("%H:%M"), label, "warning")

        if error:
            self._append_log(time.strftime("%H:%M"), f"Lỗi suy luận: {str(error)[:120]}", "warning")

        if detections and self._frame_count % 40 == 1:
            names = ", ".join(det.get("class", "--") for det in detections[:4])
            self._append_log(time.strftime("%H:%M"), f"Phát hiện: {names}", "info")

        self._page_update()

    def _append_log(self, time_label: str, message: str, kind: str = "info") -> None:
        color_map = {
            "warning": DANGER,
            "success": PRIMARY,
            "info": ft.Colors.WHITE70,
        }
        self._log_rows.controls.insert(
            0,
            ft.Container(
                padding=10,
                border_radius=12,
                bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
                content=ft.Row(
                    spacing=10,
                    controls=[
                        ft.Text(time_label, width=52, size=11, color=ft.Colors.WHITE54),
                        ft.Text(message, expand=True, size=12, color=color_map.get(kind, ft.Colors.WHITE70)),
                    ],
                ),
            ),
        )
        if len(self._log_rows.controls) > 12:
            self._log_rows.controls.pop()
        self._safe_update(self._log_rows)

    def _clear_log(self) -> None:
        self._log_rows.controls.clear()
        self._safe_update(self._log_rows)
