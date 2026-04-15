from __future__ import annotations
import base64
import datetime
import mimetypes
import os
import tempfile
import threading
import time
from pathlib import Path

import flet as ft

from bll.services.monitor_service import load_config
from bll.user.farmer import tu_van_ai
from ui.theme import PRIMARY, SECONDARY, WARNING, DANGER

_EXPERT_NAME   = "Hệ thống AI Thú Y"
_AI_MODEL_CONF = 0.30

_SEED_MESSAGES = [
    {
        "sender": "system",
        "text": "Xin chào! Tôi là hệ thống AI tư vấn bệnh bò.\n"
                "Hãy gửi ảnh con bò để tôi phân tích sức khỏe cho bạn.",
        "img_src": None,
        "file_name": None,
        "time": "08:00",
        "ai_result": None,
    }
]


def _now() -> str:
    return datetime.datetime.now().strftime("%H:%M")


def build_health_consulting(page: ft.Page = None):  # noqa: C901
    messages: list[dict] = list(_SEED_MESSAGES)
    list_ref       = ft.Ref[ft.ListView]()
    input_ref      = ft.Ref[ft.TextField]()
    gemini_key_ref = ft.Ref[ft.TextField]()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _show_snack(msg: str):
        if page:
            try:
                page.snack_bar = ft.SnackBar(ft.Text(msg), open=True)
                page.update()
            except Exception:
                pass

    def _close_dlg(dlg):
        if page:
            try:
                page.close(dlg)
            except Exception:
                dlg.open = False
                page.update()

    def _open_detail_dialog(ai_result: dict):
        """Popup chi tiết: ảnh chú thích + bảng bệnh + tư vấn Gemini."""
        diagnosis  = ai_result.get("diagnosis", {})
        detected   = diagnosis.get("detected", [])
        b64_img    = ai_result.get("annotated_b64", "")
        model_name = ai_result.get("model_name", "AI Model")

        gemini_text    = ft.Text(
            "Nhấn 'Tư vấn AI' để lấy lời khuyên từ Gemini…",
            size=12, color=ft.Colors.WHITE60, italic=True,
        )
        gemini_loading = ft.ProgressRing(width=20, height=20, visible=False,
                                         color=SECONDARY)
        gemini_btn     = ft.Ref[ft.ElevatedButton]()

        def _fetch_gemini(e):
            api_key = (gemini_key_ref.current.value or "").strip() \
                if gemini_key_ref.current else ""
            if not api_key:
                gemini_text.value = "⚠️ Vui lòng nhập Gemini API key."
                if page:
                    page.update()
                return
            if gemini_btn.current:
                gemini_btn.current.disabled = True
            gemini_loading.visible = True
            if page:
                page.update()
            prompt = tu_van_ai.build_gemini_prompt(diagnosis)

            def _on_gemini(text: str):
                gemini_text.value = text
                gemini_loading.visible = False
                if page:
                    try:
                        page.update()
                    except Exception:
                        pass

            tu_van_ai.call_gemini_async(api_key, prompt, _on_gemini)

        # Bảng bệnh phát hiện
        disease_rows: list[ft.Control] = []
        if detected:
            for d in detected:
                disease_rows.append(
                    ft.Container(
                        margin=ft.margin.only(bottom=4),
                        padding=ft.padding.symmetric(horizontal=10, vertical=6),
                        border_radius=8,
                        bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.RED_300),
                        border=ft.border.all(
                            1, ft.Colors.with_opacity(0.30, ft.Colors.RED_300)
                        ),
                        content=ft.Row(spacing=8, controls=[
                            ft.Icon(ft.Icons.CORONAVIRUS, size=16,
                                    color=ft.Colors.RED_300),
                            ft.Text(d["class"], size=12, color=ft.Colors.WHITE,
                                    expand=True),
                            ft.Text(f"{d['confidence']:.0%}", size=12,
                                    color=ft.Colors.AMBER_300,
                                    weight=ft.FontWeight.W_700),
                        ]),
                    )
                )
        else:
            disease_rows.append(
                ft.Text("✅ Không phát hiện bệnh.", size=12,
                        color=ft.Colors.GREEN_300)
            )

        annotated_ctrl = (
            ft.Image(src_base64=b64_img, width=300, height=225,
                     border_radius=8, fit=ft.ImageFit.CONTAIN)
            if b64_img
            else ft.Text("(Không có ảnh)", size=11, color=ft.Colors.WHITE38)
        )

        dlg_content = ft.Column(
            scroll=ft.ScrollMode.AUTO, width=340, spacing=10,
            controls=[
                annotated_ctrl,
                ft.Text(f"Model: {model_name}", size=10, color=ft.Colors.WHITE38),
                ft.Divider(height=1,
                           color=ft.Colors.with_opacity(0.15, ft.Colors.WHITE)),
                ft.Text("Kết quả phát hiện bệnh:", size=13,
                        weight=ft.FontWeight.W_600),
                *disease_rows,
                ft.Divider(height=1,
                           color=ft.Colors.with_opacity(0.15, ft.Colors.WHITE)),
                ft.Text("Tư vấn từ AI:", size=13, weight=ft.FontWeight.W_600),
                ft.Row(spacing=8, controls=[
                    ft.ElevatedButton(
                        ref=gemini_btn,
                        text="Tư vấn AI",
                        icon=ft.Icons.SMART_TOY,
                        on_click=_fetch_gemini,
                        style=ft.ButtonStyle(
                            bgcolor=SECONDARY, color=ft.Colors.WHITE,
                            shape=ft.RoundedRectangleBorder(radius=8),
                        ),
                    ),
                    gemini_loading,
                ]),
                gemini_text,
            ],
        )

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=ft.Colors.with_opacity(0.95, ft.Colors.GREY_900),
            title=ft.Row(spacing=8, controls=[
                ft.Icon(ft.Icons.BIOTECH, color=SECONDARY, size=20),
                ft.Text("Kết quả phân tích AI", size=15,
                        weight=ft.FontWeight.W_700),
            ]),
            content=dlg_content,
            actions=[
                ft.TextButton("Đóng", on_click=lambda e: _close_dlg(dlg)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        if page:
            try:
                page.open(dlg)
            except Exception:
                page.dialog = dlg
                dlg.open = True
                page.update()

    # ── bubble renderer ──────────────────────────────────────────────────────

    def _bubble(msg: dict) -> ft.Control:
        sender    = msg.get("sender", "farmer")
        is_me     = sender == "farmer"
        is_system = sender == "system"
        ai_result = msg.get("ai_result")

        if is_system:
            align        = ft.MainAxisAlignment.START
            bg           = ft.Colors.with_opacity(0.16, SECONDARY)
            border_col   = ft.Colors.with_opacity(0.25, SECONDARY)
            avatar_color = SECONDARY
            avatar_icon  = ft.Icons.SMART_TOY
        elif is_me:
            align        = ft.MainAxisAlignment.END
            bg           = ft.Colors.with_opacity(0.30, PRIMARY)
            border_col   = ft.Colors.with_opacity(0.40, PRIMARY)
            avatar_color = PRIMARY
            avatar_icon  = ft.Icons.PERSON
        else:
            align        = ft.MainAxisAlignment.START
            bg           = ft.Colors.with_opacity(0.16, ft.Colors.WHITE)
            border_col   = ft.Colors.with_opacity(0.18, ft.Colors.WHITE)
            avatar_color = SECONDARY
            avatar_icon  = ft.Icons.SUPPORT_AGENT

        inner: list[ft.Control] = []

        if msg.get("img_src"):
            inner.append(
                ft.Image(src=msg["img_src"], width=200, border_radius=10,
                         fit=ft.ImageFit.COVER)
            )

        if msg.get("file_name"):
            inner.append(
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    border_radius=8,
                    bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.WHITE),
                    content=ft.Row(tight=True, spacing=6, controls=[
                        ft.Icon(ft.Icons.INSERT_DRIVE_FILE, size=16,
                                color=SECONDARY),
                        ft.Text(msg["file_name"], size=12, color=ft.Colors.WHITE,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                    ]),
                )
            )

        if msg.get("text"):
            inner.append(
                ft.Text(msg["text"], size=13, color=ft.Colors.WHITE,
                        selectable=True)
            )

        # AI result chips + "Xem chi tiết" button
        if ai_result:
            detected  = ai_result.get("diagnosis", {}).get("detected", [])
            chips: list[ft.Control] = []
            if detected:
                for d in detected[:4]:
                    chips.append(
                        ft.Container(
                            padding=ft.padding.symmetric(horizontal=7, vertical=3),
                            border_radius=12,
                            bgcolor=ft.Colors.with_opacity(0.22, ft.Colors.RED_400),
                            border=ft.border.all(
                                1, ft.Colors.with_opacity(0.40, ft.Colors.RED_300)
                            ),
                            content=ft.Row(tight=True, spacing=4, controls=[
                                ft.Icon(ft.Icons.CORONAVIRUS, size=10,
                                        color=ft.Colors.RED_300),
                                ft.Text(d["class"], size=10,
                                        color=ft.Colors.WHITE),
                            ]),
                        )
                    )
            else:
                chips.append(
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=7, vertical=3),
                        border_radius=12,
                        bgcolor=ft.Colors.with_opacity(0.18, ft.Colors.GREEN_400),
                        content=ft.Text("Không phát hiện bệnh", size=10,
                                        color=ft.Colors.GREEN_300),
                    )
                )
            inner.append(ft.Row(wrap=True, spacing=4, run_spacing=4,
                                controls=chips))
            _ar = ai_result  # local capture for closure
            inner.append(
                ft.TextButton(
                    "Xem chi tiết",
                    icon=ft.Icons.INFO_OUTLINE,
                    style=ft.ButtonStyle(color=SECONDARY),
                    on_click=lambda e, ar=_ar: _open_detail_dialog(ar),
                )
            )

        inner.append(
            ft.Text(
                msg["time"], size=9, color=ft.Colors.WHITE38,
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
            alignment=ft.alignment.center,
            content=ft.Icon(avatar_icon, size=16, color=avatar_color),
        )

        row_ctrls = [bubble, avatar] if is_me else [avatar, bubble]
        return ft.Row(
            alignment=align,
            vertical_alignment=ft.CrossAxisAlignment.END,
            spacing=6,
            controls=row_ctrls,
        )

    # ── chat helpers ─────────────────────────────────────────────────────────

    def _append_bubble(msg: dict):
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
            "img_src": None, "file_name": None,
            "time": _now(), "ai_result": None,
        }
        messages.append(msg)
        input_ref.current.value = ""
        _append_bubble(msg)

    def _run_ai_analysis(img_path: str):
        """Chạy phân tích bệnh AI sau khi ảnh được gửi."""
        wait_msg = {
            "sender": "system",
            "text": "🔍 Đang phân tích ảnh với AI…",
            "img_src": None, "file_name": None,
            "time": _now(), "ai_result": None,
        }
        messages.append(wait_msg)
        _append_bubble(wait_msg)

        def _on_result(result_dict: dict):
            # Xoá bubble "Đang phân tích..."
            if list_ref.current and list_ref.current.controls:
                list_ref.current.controls.pop()
            detected = result_dict["diagnosis"]["detected"]
            n        = result_dict["diagnosis"]["n_objects"]
            if detected:
                names   = ", ".join(d["class"] for d in detected[:3])
                summary = f"Phát hiện {n} đối tượng — {names}."
            else:
                summary = "Không phát hiện dấu hiệu bệnh trong ảnh."
            ai_msg = {
                "sender": "system", "text": summary,
                "img_src": None, "file_name": None,
                "time": _now(), "ai_result": result_dict,
            }
            messages.append(ai_msg)
            if list_ref.current and list_ref.current.page:
                list_ref.current.controls.append(_bubble(ai_msg))
                if page:
                    try:
                        page.update()
                    except Exception:
                        pass

        def _on_error(err: str):
            if list_ref.current and list_ref.current.controls:
                list_ref.current.controls.pop()
            err_msg = {
                "sender": "system", "text": f"⚠️ {err}",
                "img_src": None, "file_name": None,
                "time": _now(), "ai_result": None,
            }
            messages.append(err_msg)
            if list_ref.current and list_ref.current.page:
                list_ref.current.controls.append(_bubble(err_msg))
                if page:
                    try:
                        page.update()
                    except Exception:
                        pass

        tu_van_ai.analyze_image_async(
            img_source=img_path,
            conf_thresh=_AI_MODEL_CONF,
            on_result=_on_result,
            on_error=_on_error,
        )

    def _on_pick_image(e: ft.FilePickerResultEvent):
        if not e.files:
            return
        f = e.files[0]
        try:
            with open(f.path, "rb") as fp:
                data = base64.b64encode(fp.read()).decode()
            mime = mimetypes.guess_type(f.name)[0] or "image/jpeg"
            src  = f"data:{mime};base64,{data}"
        except Exception:
            src = f.path
        msg = {
            "sender": "farmer", "text": None,
            "img_src": src, "file_name": None,
            "time": _now(), "ai_result": None,
        }
        messages.append(msg)
        _append_bubble(msg)
        _run_ai_analysis(f.path)

    def _on_pick_file(e: ft.FilePickerResultEvent):
        if not e.files:
            return
        msg = {
            "sender": "farmer", "text": None,
            "img_src": None, "file_name": e.files[0].name,
            "time": _now(), "ai_result": None,
        }
        messages.append(msg)
        _append_bubble(msg)

    def _open_camera_live(e):
        """Mo dialog xem camera realtime, cho phep chup anh gui vao chat."""
        stop_evt   = threading.Event()
        last_frame = [None]

        live_img = ft.Image(
            width=300, height=225,
            border_radius=8,
            fit=ft.ImageFit.CONTAIN,
            src_base64="",
            visible=False,
        )
        # Placeholder hien thi khi camera chua bat
        placeholder = ft.Container(
            width=300, height=225,
            border_radius=8,
            bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.WHITE),
            alignment=ft.alignment.center,
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
            try:
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
                    if stop_evt.is_set():  # không update nữa khi đang dừng
                        break
                    try:
                        if page:
                            page.update()
                    except Exception:
                        break
                    elapsed = time.time() - t0
                    wait = _interval - elapsed
                    if wait > 0:
                        time.sleep(wait)
            finally:
                cap.release()

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
                "img_src": path,  # dùng path trực tiếp, không base64 (tránh WebSocket overflow)
                "file_name": None,
                "time": _now(), "ai_result": None,
            }
            messages.append(msg)
            # stop_evt đã ngăn stream gọi page.update() thêm → đây là update duy nhất
            stop_evt.set()
            dlg.open = False
            _append_bubble(msg)
            _run_ai_analysis(path)

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
        hint_text="Nhắn tin...",
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

    gemini_key_field = ft.TextField(
        ref=gemini_key_ref,
        hint_text="Gemini API key (để lấy tư vấn AI)",
        border_radius=16,
        height=36,
        text_size=11,
        password=True,
        can_reveal_password=True,
        bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.15, ft.Colors.WHITE),
        focused_border_color=SECONDARY,
        hint_style=ft.TextStyle(color=ft.Colors.WHITE38, size=11),
        text_style=ft.TextStyle(color=ft.Colors.WHITE, size=11),
        cursor_color=ft.Colors.WHITE,
        content_padding=ft.padding.symmetric(horizontal=10, vertical=4),
        prefix_icon=ft.Icons.KEY_OUTLINED,
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
        alignment=ft.alignment.center,
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
        content=ft.Column(
            spacing=4, tight=True,
            controls=[
                gemini_key_field,
                ft.Row(
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
                            lambda e: picker_file.pick_files(
                                allow_multiple=False),
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
                    alignment=ft.alignment.center,
                    content=ft.Icon(ft.Icons.SMART_TOY, size=22, color=SECONDARY),
                ),
                ft.Column(
                    tight=True, spacing=2, expand=True,
                    controls=[
                        ft.Text(_EXPERT_NAME, size=14, weight=ft.FontWeight.W_700),
                        ft.Row(tight=True, spacing=5, controls=[
                            ft.Container(width=7, height=7, border_radius=4, bgcolor=PRIMARY),
                            ft.Text("AI sẵn sàng · conf ≥ 30%", size=10,
                                    color=ft.Colors.WHITE60),
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
