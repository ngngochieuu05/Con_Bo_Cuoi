from __future__ import annotations
import base64
import ctypes
import datetime
import json
import mimetypes
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import flet as ft

from bll.services.monitor_service import load_config
from ui.theme import PRIMARY, SECONDARY, WARNING, DANGER

_CAMERA_HELPER = str(Path(__file__).parent / "_camera_capture.py")

_EXPERT_NAME = "Chuyên gia thú y"

_SEED_MESSAGES = [
    {
        "sender": "expert",
        "text": "Xin chào! Tôi là chuyên gia thú y trực tuyến. "
                "Bạn cần tư vấn về sức khỏe đàn bò không?",
        "img_src": None,
        "file_name": None,
        "time": "08:00",
    }
]


def _now() -> str:
    return datetime.datetime.now().strftime("%H:%M")


def _bubble(msg: dict) -> ft.Control:
    is_me = msg["sender"] == "farmer"
    align = ft.MainAxisAlignment.END if is_me else ft.MainAxisAlignment.START
    bg = ft.Colors.with_opacity(0.30, PRIMARY) if is_me \
        else ft.Colors.with_opacity(0.16, ft.Colors.WHITE)
    border_col = ft.Colors.with_opacity(0.40, PRIMARY) if is_me \
        else ft.Colors.with_opacity(0.18, ft.Colors.WHITE)
    avatar_color = PRIMARY if is_me else SECONDARY
    avatar_icon  = ft.Icons.PERSON if is_me else ft.Icons.SUPPORT_AGENT

    inner: list[ft.Control] = []

    if msg.get("img_src"):
        inner.append(
            ft.Image(
                src=msg["img_src"],
                width=200, border_radius=10,
                fit="cover",
            )
        )

    if msg.get("file_name"):
        inner.append(
            ft.Container(
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                border_radius=8,
                bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.WHITE),
                content=ft.Row(tight=True, spacing=6, controls=[
                    ft.Icon(ft.Icons.INSERT_DRIVE_FILE, size=16, color=SECONDARY),
                    ft.Text(
                        msg["file_name"], size=12, color=ft.Colors.WHITE,
                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                        expand=True,
                    ),
                ]),
            )
        )

    if msg.get("text"):
        inner.append(
            ft.Text(msg["text"], size=13, color=ft.Colors.WHITE, selectable=True)
        )

    inner.append(
        ft.Text(
            msg["time"], size=9,
            color=ft.Colors.WHITE38,
            text_align=ft.TextAlign.RIGHT if is_me else ft.TextAlign.LEFT,
        )
    )

    bubble = ft.Container(
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        border_radius=ft.border_radius.only(
            top_left=16, top_right=16,
            bottom_left=4 if is_me else 16,
            bottom_right=16 if is_me else 4,
        ),
        bgcolor=bg,
        border=ft.border.all(1, border_col),
        content=ft.Column(spacing=4, tight=True, controls=inner),
    )

    avatar = ft.Container(
        width=30, height=30, border_radius=15,
        bgcolor=ft.Colors.with_opacity(0.20, avatar_color),
        alignment=ft.Alignment.CENTER,
        content=ft.Icon(avatar_icon, size=16, color=avatar_color),
    )

    row_ctrls = [bubble, avatar] if is_me else [avatar, bubble]

    return ft.Row(
        alignment=align,
        vertical_alignment=ft.CrossAxisAlignment.END,
        spacing=6,
        controls=row_ctrls,
    )


def build_health_consulting(page: ft.Page = None):
    messages: list[dict] = list(_SEED_MESSAGES)
    list_ref  = ft.Ref[ft.ListView]()
    input_ref = ft.Ref[ft.TextField]()

    def _append_bubble(msg: dict):
        """Them bubble moi va update page - an toan voi thread."""
        if list_ref.current and list_ref.current.page:
            list_ref.current.controls.append(_bubble(msg))
            if page:
                page.update()

    def _send_text(e=None):
        txt = (input_ref.current.value or "").strip()
        if not txt:
            return
        msg = {
            "sender": "farmer", "text": txt,
            "img_src": None, "file_name": None, "time": _now(),
        }
        messages.append(msg)
        input_ref.current.value = ""
        if list_ref.current and list_ref.current.page:
            list_ref.current.controls.append(_bubble(msg))
        if page:
            page.update()

    def _on_pick_image(e: ft.FilePickerResultEvent):
        if not e.files:
            return
        f = e.files[0]
        try:
            with open(f.path, "rb") as fp:
                data = base64.b64encode(fp.read()).decode()
            mime = mimetypes.guess_type(f.name)[0] or "image/jpeg"
            src = f"data:{mime};base64,{data}"
        except Exception:
            src = f.path
        msg = {
            "sender": "farmer", "text": None,
            "img_src": src, "file_name": None, "time": _now(),
        }
        messages.append(msg)
        _append_bubble(msg)

    def _on_pick_file(e: ft.FilePickerResultEvent):
        if not e.files:
            return
        msg = {
            "sender": "farmer", "text": None,
            "img_src": None, "file_name": e.files[0].name, "time": _now(),
        }
        messages.append(msg)
        _append_bubble(msg)

    def _show_snack(msg: str):
        if page:
            try:
                page.snack_bar = ft.SnackBar(ft.Text(msg), open=True)
                page.update()
            except Exception:
                pass

    def _open_camera_live(e):
        """Mo dialog xem camera realtime, cho phep chup anh gui vao chat."""
        stop_evt   = threading.Event()
        last_frame = [None]

        live_img = ft.Image(
            width=300, height=225,
            border_radius=8,
            fit="contain",
            src_base64="",
            visible=False,
        )
        # Placeholder hien thi khi camera chua bat
        placeholder = ft.Container(
            width=300, height=225,
            border_radius=8,
            bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.WHITE),
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True, spacing=8,
                controls=[
                    ft.Icon(ft.Icons.VIDEOCAM, size=40, color=ft.Colors.WHITE38),
                    ft.Text("Đang khởi động camera…", size=12, color=ft.Colors.WHITE60),
                ],
            ),
        )
        cam_msg = ft.Text("", size=11, color=ft.Colors.RED_300)
        video_stack = ft.Stack(width=300, height=225, controls=[placeholder, live_img])

        def _stream():
            try:
                import cv2
            except ImportError:
                placeholder.content = ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    tight=True, spacing=8,
                    controls=[
                        ft.Icon(ft.Icons.ERROR_OUTLINE, size=36, color=ft.Colors.RED_300),
                        ft.Text("Chưa cài opencv-python.", size=11, color=ft.Colors.RED_300),
                    ],
                )
                try:
                    placeholder.update()
                except Exception:
                    pass
                return
            try:
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
                    tight=True, spacing=8,
                    controls=[
                        ft.Icon(ft.Icons.VIDEOCAM_OFF, size=36, color=ft.Colors.RED_300),
                        ft.Text(f"Không mở được camera {idx}.", size=11, color=ft.Colors.RED_300),
                    ],
                )
                try:
                    placeholder.update()
                except Exception:
                    pass
                return

            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc("M", "J", "P", "G"))
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            for _ in range(3):
                cap.grab()

            # An placeholder, hien live image
            placeholder.visible = False
            live_img.visible = True
            try:
                if page:
                    page.update()
            except Exception:
                pass

            _interval = 1.0 / 30  # 30 FPS
            while not stop_evt.is_set():
                t0 = time.time()
                ret, frame = cap.read()
                if not ret:
                    break
                last_frame[0] = frame

                small = cv2.resize(frame, (300, 225))
                _, buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 60])
                b64 = base64.b64encode(bytes(buf)).decode()
                live_img.src_base64 = b64
                try:
                    if page:
                        page.update()
                except Exception:
                    break
                elapsed = time.time() - t0
                wait = _interval - elapsed
                if wait > 0:
                    time.sleep(wait)

        def _do_capture(e):
            frame = last_frame[0]
            if frame is None:
                return
            import cv2
            fd, path = tempfile.mkstemp(suffix=".jpg", prefix="cam_snap_")
            os.close(fd)
            cv2.imwrite(path, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            msg = {
                "sender": "farmer", "text": None,
                "img_src": path, "file_name": None, "time": _now(),
            }
            messages.append(msg)
            _close_cam(None)
            _append_bubble(msg)

        def _close_cam(e):
            stop_evt.set()
            if page:
                try:
                    page.close(dlg)
                except Exception:
                    try:
                        dlg.open = False
                        page.update()
                    except Exception:
                        pass

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=ft.Colors.with_opacity(0.92, ft.Colors.GREY_900),
            title=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.CAMERA_ALT, color=ft.Colors.AMBER_300, size=20),
                    ft.Text("Camera trực tiếp", size=15, weight=ft.FontWeight.W_700),
                ],
            ),
            content=ft.Column(
                tight=True, spacing=6,
                controls=[video_stack, cam_msg],
            ),
            actions=[
                ft.ElevatedButton(
                    "Chụp",
                    icon=ft.Icons.CAMERA,
                    on_click=_do_capture,
                    style=ft.ButtonStyle(
                        bgcolor=PRIMARY,
                        color=ft.Colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                ),
                ft.OutlinedButton("Đóng", on_click=_close_cam),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            on_dismiss=lambda e: stop_evt.set(),
        )

        if page:
            try:
                page.open(dlg)
            except Exception:
                page.dialog = dlg
                dlg.open = True
                page.update()
            threading.Thread(target=_stream, daemon=True).start()

    picker_img  = ft.FilePicker(on_result=_on_pick_image)
    picker_file = ft.FilePicker(on_result=_on_pick_file)

    if page:
        page.overlay.extend([picker_img, picker_file])
        page.update()

    chat_list = ft.ListView(
        ref=list_ref,
        expand=True,
        spacing=8,
        padding=ft.padding.symmetric(horizontal=10, vertical=10),
        controls=[_bubble(m) for m in messages],
        auto_scroll=True,
    )

    txt_input = ft.TextField(
        ref=input_ref,
        hint_text="Nhắn tin với chuyên gia...",
        expand=True,
        border_radius=20,
        min_lines=1,
        max_lines=4,
        shift_enter=True,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.20, ft.Colors.WHITE),
        focused_border_color=PRIMARY,
        hint_style=ft.TextStyle(color=ft.Colors.WHITE38, size=13),
        text_style=ft.TextStyle(color=ft.Colors.WHITE, size=13),
        cursor_color=ft.Colors.WHITE,
        content_padding=ft.padding.symmetric(horizontal=14, vertical=10),
        on_submit=_send_text,
    )

    def _attach_btn(icon, tip, color, on_click):
        return ft.IconButton(
            icon=icon, icon_color=color,
            icon_size=22, tooltip=tip,
            on_click=on_click,
        )

    send_btn = ft.Container(
        width=40, height=40, border_radius=20,
        bgcolor=PRIMARY,
        alignment=ft.Alignment.CENTER,
        ink=True,
        on_click=_send_text,
        content=ft.Icon(ft.Icons.SEND_ROUNDED, size=18, color=ft.Colors.WHITE),
    )

    input_bar = ft.Container(
        padding=ft.padding.symmetric(horizontal=8, vertical=6),
        bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.WHITE),
        border=ft.border.only(
            top=ft.BorderSide(1, ft.Colors.with_opacity(0.14, ft.Colors.WHITE))
        ),
        content=ft.Row(
            spacing=2,
            vertical_alignment=ft.CrossAxisAlignment.END,
            controls=[
                _attach_btn(
                    ft.Icons.IMAGE_OUTLINED, "Gửi ảnh", SECONDARY,
                    lambda e: picker_img.pick_files(
                        allow_multiple=False,
                        file_type=ft.FilePickerFileType.IMAGE,
                    ),
                ),
                _attach_btn(
                    ft.Icons.ATTACH_FILE, "Gửi file", WARNING,
                    lambda e: picker_file.pick_files(allow_multiple=False),
                ),
                _attach_btn(
                    ft.Icons.CAMERA_ALT_OUTLINED, "Mở camera trực tiếp",
                    ft.Colors.AMBER_300,
                    _open_camera_live,
                ),
                txt_input,
                send_btn,
            ],
        ),
    )

    header = ft.Container(
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        bgcolor=ft.Colors.with_opacity(0.14, ft.Colors.WHITE),
        border=ft.border.only(
            bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.12, ft.Colors.WHITE))
        ),
        content=ft.Row(
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    width=38, height=38, border_radius=19,
                    bgcolor=ft.Colors.with_opacity(0.20, SECONDARY),
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(ft.Icons.SUPPORT_AGENT, size=22, color=SECONDARY),
                ),
                ft.Column(
                    tight=True, spacing=2, expand=True,
                    controls=[
                        ft.Text(_EXPERT_NAME, size=14, weight=ft.FontWeight.W_700),
                        ft.Row(tight=True, spacing=5, controls=[
                            ft.Container(width=7, height=7, border_radius=4, bgcolor=PRIMARY),
                            ft.Text("Đang trực tuyến", size=10, color=ft.Colors.WHITE60),
                        ]),
                    ],
                ),
                ft.Icon(ft.Icons.MORE_VERT, color=ft.Colors.WHITE38, size=20),
            ],
        ),
    )

    return ft.Column(
        expand=True,
        spacing=0,
        controls=[
            header,
            ft.Container(expand=True, content=chat_list),
            input_bar,
        ],
    )
