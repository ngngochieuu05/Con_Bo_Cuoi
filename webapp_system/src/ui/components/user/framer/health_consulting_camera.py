from __future__ import annotations

import base64
import os
import tempfile
import threading
import time

import flet as ft

from bll.services.monitor_service import load_config
from ui.theme import PRIMARY


def _safe_update(page: ft.Page | None) -> None:
    if not page:
        return
    try:
        page.update()
    except Exception:
        pass


def _close_dialog(page: ft.Page | None, dialog: ft.AlertDialog, stop_evt: threading.Event) -> None:
    stop_evt.set()
    if not page:
        return
    try:
        page.close(dialog)
    except Exception:
        dialog.open = False
        _safe_update(page)


def open_camera_live(page, messages, append_bubble, run_ai_analysis, now_fn) -> None:
    stop_evt = threading.Event()
    last_frame = {"frame": None}
    snap_path = {"path": None}
    is_preview = {"on": False}

    live_img = ft.Image(
        width=300,
        height=225,
        border_radius=8,
        fit=ft.ImageFit.COVER,
        src_base64="",
        visible=False,
    )
    snap_img = ft.Image(
        width=300,
        height=225,
        border_radius=8,
        fit=ft.ImageFit.COVER,
        visible=False,
    )
    placeholder = ft.Container(
        width=300,
        height=225,
        border_radius=8,
        bgcolor=ft.Colors.with_opacity(0.14, ft.Colors.WHITE),
        alignment=ft.alignment.center,
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
            spacing=10,
            controls=[
                ft.ProgressRing(width=32, height=32, color=ft.Colors.AMBER_300),
                ft.Text("Đang khởi động camera…", size=12, color=ft.Colors.WHITE60),
            ],
        ),
    )
    status_lbl = ft.Text("", size=11, color=ft.Colors.RED_300)
    fps_lbl = ft.Text("", size=9, color=ft.Colors.WHITE24)

    video_stack = ft.Stack(width=300, height=225, controls=[placeholder, live_img, snap_img])

    capture_btn_ref = ft.Ref[ft.ElevatedButton]()
    retake_btn_ref = ft.Ref[ft.OutlinedButton]()
    close_btn_ref = ft.Ref[ft.OutlinedButton]()

    dialog = ft.AlertDialog(
        modal=True,
        bgcolor=ft.Colors.with_opacity(0.93, ft.Colors.GREY_900),
        title=ft.Row(
            spacing=8,
            controls=[
                ft.Icon(ft.Icons.CAMERA_ALT, color=ft.Colors.AMBER_300, size=20),
                ft.Text("Camera trực tiếp", size=15, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE),
                ft.Container(expand=True),
                fps_lbl,
            ],
        ),
        content=ft.Column(tight=True, spacing=8, controls=[video_stack, status_lbl]),
        actions=[],
        actions_alignment=ft.MainAxisAlignment.END,
        on_dismiss=lambda e: stop_evt.set(),
    )

    def _set_preview_mode(on: bool):
        is_preview["on"] = on
        live_img.visible = not on and last_frame["frame"] is not None
        snap_img.visible = on
        if capture_btn_ref.current:
            if on:
                capture_btn_ref.current.text = "Gửi"
                capture_btn_ref.current.icon = ft.Icons.SEND
                capture_btn_ref.current.on_click = _do_send
                capture_btn_ref.current.style = ft.ButtonStyle(
                    bgcolor=PRIMARY,
                    color=ft.Colors.WHITE,
                    shape=ft.RoundedRectangleBorder(radius=10),
                )
            else:
                capture_btn_ref.current.text = "Chụp"
                capture_btn_ref.current.icon = ft.Icons.CAMERA
                capture_btn_ref.current.on_click = _do_capture
                capture_btn_ref.current.style = ft.ButtonStyle(
                    bgcolor=ft.Colors.AMBER_700,
                    color=ft.Colors.WHITE,
                    shape=ft.RoundedRectangleBorder(radius=10),
                )
        if retake_btn_ref.current:
            retake_btn_ref.current.visible = on
        if close_btn_ref.current:
            close_btn_ref.current.visible = not on
        status_lbl.value = "✅ Ảnh đã chụp — Gửi hoặc Chụp lại" if on else ""
        status_lbl.color = ft.Colors.GREEN_300 if on else ft.Colors.RED_300
        _safe_update(page)

    def _stream():
        try:
            import cv2
        except ImportError:
            placeholder.content = ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.ERROR_OUTLINE, size=36, color=ft.Colors.RED_300),
                    ft.Text(
                        "Chưa cài opencv-python.\nCài bằng: pip install opencv-python",
                        size=11,
                        color=ft.Colors.RED_300,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
            )
            try:
                placeholder.update()
            except Exception:
                pass
            return

        try:
            import ctypes

            ctypes.windll.kernel32.SetErrorMode(0x8007)
        except Exception:
            pass

        cfg = load_config()
        try:
            idx = int(cfg.get("camera_index", 0))
        except (ValueError, TypeError):
            idx = 0

        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(idx)
        if not cap.isOpened():
            placeholder.content = ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.VIDEOCAM_OFF, size=36, color=ft.Colors.RED_300),
                    ft.Text(
                        f"Không mở được camera (index={idx}).\nKiểm tra kết nối webcam.",
                        size=11,
                        color=ft.Colors.RED_300,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
            )
            try:
                placeholder.update()
            except Exception:
                pass
            return

        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc("M", "J", "P", "G"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        for _ in range(4):
            cap.grab()

        placeholder.visible = False
        live_img.visible = True
        _safe_update(page)

        target_fps = 20
        interval = 1.0 / target_fps

        try:
            while not stop_evt.is_set():
                if is_preview["on"]:
                    time.sleep(0.05)
                    continue
                started = time.time()
                ret, frame = cap.read()
                if not ret:
                    break
                last_frame["frame"] = frame
                small = cv2.resize(frame, (300, 225))
                _, buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 55])
                live_img.src_base64 = base64.b64encode(bytes(buf)).decode()
                fps_lbl.value = f"{1.0 / max(time.time() - started, 0.001):.0f} fps"
                if stop_evt.is_set():
                    break
                _safe_update(page)
                wait = interval - (time.time() - started)
                if wait > 0:
                    time.sleep(wait)
        finally:
            cap.release()

    def _do_capture(e):
        frame = last_frame["frame"]
        if frame is None:
            status_lbl.value = "⚠️ Camera chưa sẵn sàng, thử lại."
            _safe_update(page)
            return
        try:
            import cv2

            fd, path = tempfile.mkstemp(suffix=".jpg", prefix="cam_snap_")
            os.close(fd)
            cv2.imwrite(path, frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
            snap_path["path"] = path
            snap_img.src = path
            _set_preview_mode(True)
        except Exception as ex:
            status_lbl.value = f"⚠️ Lỗi lưu ảnh: {ex}"
            _safe_update(page)

    def _do_send(e):
        path = snap_path["path"]
        if not path:
            return
        _close_dialog(page, dialog, stop_evt)
        msg = {
            "sender": "farmer",
            "text": None,
            "img_src": path,
            "file_name": None,
            "time": now_fn(),
            "ai_result": None,
        }
        messages.append(msg)
        append_bubble(msg)
        run_ai_analysis(path)

    def _do_retake(e):
        snap_path["path"] = None
        _set_preview_mode(False)

    dialog.actions = [
        ft.ElevatedButton(
            ref=capture_btn_ref,
            text="Chụp",
            icon=ft.Icons.CAMERA,
            on_click=_do_capture,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.AMBER_700,
                color=ft.Colors.WHITE,
                shape=ft.RoundedRectangleBorder(radius=10),
            ),
        ),
        ft.OutlinedButton(
            ref=retake_btn_ref,
            text="Chụp lại",
            icon=ft.Icons.REPLAY,
            visible=False,
            on_click=_do_retake,
        ),
        ft.OutlinedButton(
            ref=close_btn_ref,
            text="Đóng",
            on_click=lambda e: _close_dialog(page, dialog, stop_evt),
        ),
    ]

    if not page:
        return
    try:
        page.open(dialog)
    except Exception:
        page.dialog = dialog
        dialog.open = True
        _safe_update(page)
    threading.Thread(target=_stream, daemon=True).start()
