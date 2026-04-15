from __future__ import annotations
import base64
import datetime
import os
import tempfile
import threading
import time

import flet as ft

from bll.admin.user_management import list_users
from bll.services.monitor_service import load_config
from bll.services import chat_service
from bll.user.farmer import tu_van_ai
from ui.theme import PRIMARY, SECONDARY, WARNING, DANGER

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


def _get_experts() -> list[dict]:
    """Lấy danh sách tài khoản có vai_tro='expert' từ BLL."""
    try:
        return [u for u in list_users() if u.get("vai_tro") == "expert"]
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ENTRY
# ─────────────────────────────────────────────────────────────────────────────

def build_health_consulting(page: ft.Page = None):  # noqa: C901
    content_area = ft.Container(expand=True)

    def _update():
        if page and content_area.page:
            try:
                page.update()
            except Exception:
                pass

    def _show_selection():
        content_area.content = _make_selection_screen(_show_ai_chat, _show_expert_chat)
        _update()

    def _show_ai_chat():
        content_area.content = _make_ai_chat(page, on_back=_show_selection)
        _update()

    def _show_expert_chat():
        content_area.content = _make_expert_chat(page, on_back=_show_selection)
        _update()

    _show_selection()

    return ft.Column(
        expand=True,
        spacing=0,
        controls=[content_area],
    )


# ─────────────────────────────────────────────────────────────────────────────
# SELECTION SCREEN
# ─────────────────────────────────────────────────────────────────────────────

def _make_selection_screen(on_ai, on_expert):
    def _card(icon, title, subtitle, color, on_click):
        return ft.Container(
            height=190,
            padding=24,
            border_radius=20,
            bgcolor=ft.Colors.with_opacity(0.12, color),
            border=ft.border.all(1.5, ft.Colors.with_opacity(0.35, color)),
            ink=True,
            on_click=on_click,
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=12,
                controls=[
                    ft.Container(
                        width=64, height=64, border_radius=32,
                        bgcolor=ft.Colors.with_opacity(0.20, color),
                        alignment=ft.alignment.center,
                        content=ft.Icon(icon, size=32, color=color),
                    ),
                    ft.Text(
                        title, size=16, weight=ft.FontWeight.W_700,
                        color=ft.Colors.WHITE,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        subtitle, size=12, color=ft.Colors.WHITE60,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
            ),
        )

    return ft.Column(
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=0,
        controls=[
            ft.Container(
                padding=ft.padding.symmetric(horizontal=16, vertical=18),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=6,
                    controls=[
                        ft.Container(
                            width=52, height=52, border_radius=26,
                            bgcolor=ft.Colors.with_opacity(0.18, SECONDARY),
                            alignment=ft.alignment.center,
                            content=ft.Icon(
                                ft.Icons.HEALTH_AND_SAFETY,
                                size=28, color=SECONDARY,
                            ),
                        ),
                        ft.Text(
                            "Tư vấn sức khỏe bò",
                            size=20, weight=ft.FontWeight.W_700,
                            color=ft.Colors.WHITE,
                        ),
                        ft.Text(
                            "Chọn hình thức tư vấn phù hợp với bạn",
                            size=13, color=ft.Colors.WHITE60,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                ),
            ),
            ft.Container(
                expand=True,
                padding=ft.padding.symmetric(horizontal=16, vertical=8),
                content=ft.Column(
                    expand=True,
                    spacing=16,
                    controls=[
                        _card(
                            icon=ft.Icons.SMART_TOY,
                            title="Tư vấn qua AI",
                            subtitle="Gửi ảnh con bò để AI phân tích bệnh tật\n"
                                     "và đưa ra lời khuyên ngay lập tức.",
                            color=SECONDARY,
                            on_click=lambda e: on_ai(),
                        ),
                        _card(
                            icon=ft.Icons.SUPPORT_AGENT,
                            title="Tư vấn chuyên gia",
                            subtitle="Chọn chuyên gia thú y để nhận tư vấn\n"
                                     "trực tiếp từ người có kinh nghiệm.",
                            color=ft.Colors.TEAL_300,
                            on_click=lambda e: on_expert(),
                        ),
                    ],
                ),
            ),
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
# AI CHAT
# ─────────────────────────────────────────────────────────────────────────────

def _make_ai_chat(page: ft.Page, on_back=None):  # noqa: C901
    messages: list[dict] = list(_SEED_MESSAGES)
    list_ref       = ft.Ref[ft.ListView]()
    input_ref      = ft.Ref[ft.TextField]()
    gemini_key_ref = ft.Ref[ft.TextField]()

    # ── helpers ──────────────────────────────────────────────────────────────

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
            width=270,
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
        # Dùng path trực tiếp — KHÔNG base64 encode (tránh WebSocket overflow khi gửi ảnh nhiều lần)
        img_path = e.files[0].path
        msg = {
            "sender": "farmer", "text": None,
            "img_src": img_path, "file_name": None,
            "time": _now(), "ai_result": None,
        }
        messages.append(msg)
        _append_bubble(msg)
        _run_ai_analysis(img_path)

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
        """Camera dialog: live preview → chụp → xem lại → gửi / chụp lại."""
        stop_evt   = threading.Event()
        last_frame = {"frame": None}
        snap_path  = {"path": None}     # ảnh đã chụp
        is_preview = {"on": False}      # đang xem ảnh đã chụp?

        # ── controls ──────────────────────────────────────────────────────
        live_img = ft.Image(
            width=300, height=225, border_radius=8,
            fit=ft.ImageFit.COVER,
            src_base64="", visible=False,
        )
        snap_img = ft.Image(
            width=300, height=225, border_radius=8,
            fit=ft.ImageFit.COVER,
            visible=False,
        )
        placeholder = ft.Container(
            width=300, height=225, border_radius=8,
            bgcolor=ft.Colors.with_opacity(0.14, ft.Colors.WHITE),
            alignment=ft.alignment.center,
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True, spacing=10,
                controls=[
                    ft.ProgressRing(width=32, height=32, color=ft.Colors.AMBER_300),
                    ft.Text("Đang khởi động camera…", size=12,
                            color=ft.Colors.WHITE60),
                ],
            ),
        )
        status_lbl  = ft.Text("", size=11, color=ft.Colors.RED_300)
        fps_lbl     = ft.Text("", size=9, color=ft.Colors.WHITE24)

        video_stack = ft.Stack(
            width=300, height=225,
            controls=[placeholder, live_img, snap_img],
        )

        # ── action buttons ────────────────────────────────────────────────
        capture_btn_ref = ft.Ref[ft.ElevatedButton]()
        retake_btn_ref  = ft.Ref[ft.OutlinedButton]()
        close_btn_ref   = ft.Ref[ft.OutlinedButton]()

        def _set_preview_mode(on: bool):
            is_preview["on"] = on
            live_img.visible  = not on and last_frame["frame"] is not None
            snap_img.visible  = on
            btn = capture_btn_ref.current
            if btn:
                if on:
                    btn.text     = "Gửi"
                    btn.icon     = ft.Icons.SEND
                    btn.on_click = _do_send
                    btn.style    = ft.ButtonStyle(
                        bgcolor=PRIMARY,
                        color=ft.Colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=10),
                    )
                else:
                    btn.text     = "Chụp"
                    btn.icon     = ft.Icons.CAMERA
                    btn.on_click = _do_capture
                    btn.style    = ft.ButtonStyle(
                        bgcolor=ft.Colors.AMBER_700,
                        color=ft.Colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=10),
                    )
            if retake_btn_ref.current:
                retake_btn_ref.current.visible = on
            if close_btn_ref.current:
                close_btn_ref.current.visible  = not on
            status_lbl.value = "✅ Ảnh đã chụp — Gửi hoặc Chụp lại" if on else ""
            status_lbl.color = ft.Colors.GREEN_300 if on else ft.Colors.RED_300
            try:
                if page:
                    page.update()
            except Exception:
                pass

        def _stream():
            try:
                import cv2
            except ImportError:
                placeholder.content = ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    tight=True, spacing=8,
                    controls=[
                        ft.Icon(ft.Icons.ERROR_OUTLINE, size=36,
                                color=ft.Colors.RED_300),
                        ft.Text("Chưa cài opencv-python.\n"
                                "Cài bằng: pip install opencv-python",
                                size=11, color=ft.Colors.RED_300,
                                text_align=ft.TextAlign.CENTER),
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

            # Thử CAP_DSHOW trước (Windows nhanh hơn), fallback generic
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(idx)
            if not cap.isOpened():
                placeholder.content = ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    tight=True, spacing=8,
                    controls=[
                        ft.Icon(ft.Icons.VIDEOCAM_OFF, size=36,
                                color=ft.Colors.RED_300),
                        ft.Text(
                            f"Không mở được camera (index={idx}).\n"
                            "Kiểm tra kết nối webcam.",
                            size=11, color=ft.Colors.RED_300,
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
            for _ in range(4):      # flush buffered frames
                cap.grab()

            placeholder.visible = False
            live_img.visible    = True
            try:
                if page:
                    page.update()
            except Exception:
                pass

            _target_fps = 20
            _interval   = 1.0 / _target_fps
            _frame_t    = time.time()

            try:
                while not stop_evt.is_set():
                    if is_preview["on"]:    # không stream khi đang xem ảnh
                        time.sleep(0.05)
                        continue
                    t0 = time.time()
                    ret, frame = cap.read()
                    if not ret:
                        break
                    last_frame["frame"] = frame

                    small = cv2.resize(frame, (300, 225))
                    _, buf = cv2.imencode(
                        ".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 55]
                    )
                    live_img.src_base64 = base64.b64encode(bytes(buf)).decode()

                    elapsed = time.time() - t0
                    actual_fps = 1.0 / max(elapsed, 0.001)
                    fps_lbl.value = f"{actual_fps:.0f} fps"

                    if stop_evt.is_set():
                        break
                    try:
                        if page:
                            page.update()
                    except Exception:
                        break

                    wait = _interval - (time.time() - t0)
                    if wait > 0:
                        time.sleep(wait)
            finally:
                cap.release()

        def _do_capture(e):
            """Chụp frame hiện tại → hiển thị preview, chưa gửi."""
            frame = last_frame["frame"]
            if frame is None:
                status_lbl.value = "⚠️ Camera chưa sẵn sàng, thử lại."
                try:
                    if page:
                        page.update()
                except Exception:
                    pass
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
                try:
                    if page:
                        page.update()
                except Exception:
                    pass

        def _do_send(e):
            """Gửi ảnh đã chụp vào chat và chạy AI."""
            path = snap_path["path"]
            if not path:
                return
            stop_evt.set()
            try:
                page.close(dlg)
            except Exception:
                try:
                    dlg.open = False
                    page.update()
                except Exception:
                    pass
            msg = {
                "sender": "farmer", "text": None,
                "img_src": path, "file_name": None,
                "time": _now(), "ai_result": None,
            }
            messages.append(msg)
            _append_bubble(msg)
            _run_ai_analysis(path)

        def _do_retake(e):
            """Huỷ ảnh, quay lại xem live."""
            snap_path["path"] = None
            _set_preview_mode(False)

        def _close_cam(e):
            stop_evt.set()
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
            bgcolor=ft.Colors.with_opacity(0.93, ft.Colors.GREY_900),
            title=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.CAMERA_ALT, color=ft.Colors.AMBER_300,
                            size=20),
                    ft.Text("Camera trực tiếp", size=15,
                            weight=ft.FontWeight.W_700,
                            color=ft.Colors.WHITE),
                    ft.Container(expand=True),
                    fps_lbl,
                ],
            ),
            content=ft.Column(
                tight=True, spacing=8,
                controls=[
                    video_stack,
                    status_lbl,
                ],
            ),
            actions=[
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
                    on_click=_close_cam,
                ),
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

    # ── header ───────────────────────────────────────────────────────────────

    back_btn = ft.IconButton(
        icon=ft.Icons.ARROW_BACK_IOS_NEW,
        icon_color=ft.Colors.WHITE70,
        icon_size=18,
        tooltip="Quay lại",
        on_click=lambda e: on_back() if on_back else None,
    )

    header = ft.Container(
        padding=ft.padding.symmetric(horizontal=8, vertical=10),
        bgcolor=ft.Colors.with_opacity(0.14, ft.Colors.WHITE),
        border=ft.border.only(
            bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.12, ft.Colors.WHITE))
        ),
        content=ft.Row(
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                back_btn,
                ft.Container(
                    width=34, height=34, border_radius=17,
                    bgcolor=ft.Colors.with_opacity(0.20, SECONDARY),
                    alignment=ft.alignment.center,
                    content=ft.Icon(ft.Icons.SMART_TOY, size=18, color=SECONDARY),
                ),
                ft.Column(
                    tight=True, spacing=2, expand=True,
                    controls=[
                        ft.Text("AI Tư vấn bệnh bò", size=14,
                                weight=ft.FontWeight.W_700),
                        ft.Row(tight=True, spacing=5, controls=[
                            ft.Container(width=7, height=7, border_radius=4,
                                         bgcolor=PRIMARY),
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


# ─────────────────────────────────────────────────────────────────────────────
# EXPERT CHAT
# ─────────────────────────────────────────────────────────────────────────────

def _make_expert_chat(page: ft.Page, on_back=None):  # noqa: C901
    experts      = _get_experts()
    selected_exp = {"user": experts[0] if experts else None}

    # ── resolve farmer identity from session ──────────────────────────────────
    farmer_id   = int((page.client_storage.get("user_id") or 0) if page else 0)
    farmer_name = (page.client_storage.get("ho_ten") or "Nông dân") if page else "Nông dân"

    # ── shared conversation via chat_service ──────────────────────────────────
    def _get_convo() -> dict | None:
        exp = selected_exp["user"]
        if not exp:
            return None
        exp_id = int(exp.get("id_user") or 0)
        if not exp_id:
            return None
        convo = chat_service.get_or_create_conversation(farmer_id, farmer_name, exp_id)
        # Seed greeting if conversation is new
        if not convo["messages"]:
            name = exp.get("ho_ten") or exp.get("ten_dang_nhap", "Chuyên gia")
            convo["messages"].append({
                "sender": "expert",
                "text": f"Xin chào! Tôi là {name}.\nHãy mô tả tình trạng con bò của bạn hoặc gửi ảnh để tôi hỗ trợ.",
                "img_src": None, "time": "08:00",
            })
        return convo

    convo_ref: dict[str, dict | None] = {"c": _get_convo()}

    list_ref  = ft.Ref[ft.ListView]()
    input_ref = ft.Ref[ft.TextField]()

    def _reset_chat(expert: dict | None):
        convo_ref["c"] = _get_convo()
        convo = convo_ref["c"]
        msgs = convo["messages"] if convo else []
        if list_ref.current:
            list_ref.current.controls.clear()
            for m in msgs:
                list_ref.current.controls.append(_bubble(m))
            if page:
                try:
                    page.update()
                except Exception:
                    pass

    # ── bubble ────────────────────────────────────────────────────────────────

    def _bubble(msg: dict) -> ft.Control:
        sender = msg.get("sender", "farmer")
        is_me  = sender == "farmer"

        if is_me:
            align        = ft.MainAxisAlignment.END
            bg           = ft.Colors.with_opacity(0.30, PRIMARY)
            border_col   = ft.Colors.with_opacity(0.40, PRIMARY)
            avatar_color = PRIMARY
            avatar_icon  = ft.Icons.PERSON
        else:
            align        = ft.MainAxisAlignment.START
            bg           = ft.Colors.with_opacity(0.16, ft.Colors.TEAL_300)
            border_col   = ft.Colors.with_opacity(0.30, ft.Colors.TEAL_300)
            avatar_color = ft.Colors.TEAL_300
            avatar_icon  = ft.Icons.SUPPORT_AGENT

        inner: list[ft.Control] = []

        if msg.get("img_src"):
            inner.append(
                ft.Image(src=msg["img_src"], width=200, border_radius=10,
                         fit=ft.ImageFit.COVER)
            )

        if msg.get("text"):
            inner.append(
                ft.Text(msg["text"], size=13, color=ft.Colors.WHITE,
                        selectable=True)
            )

        inner.append(
            ft.Text(
                msg["time"], size=9, color=ft.Colors.WHITE38,
                text_align=ft.TextAlign.RIGHT if is_me else ft.TextAlign.LEFT,
            )
        )

        bubble = ft.Container(
            width=270,
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

    # ── chat helpers ──────────────────────────────────────────────────────────

    def _append_bubble(msg: dict):
        if list_ref.current and list_ref.current.page:
            list_ref.current.controls.append(_bubble(msg))
            if page:
                page.update()

    def _send_text(e=None):
        txt = (input_ref.current.value or "").strip()
        if not txt:
            return
        convo = convo_ref["c"]
        if not convo:
            return
        chat_service.send_message(convo["id"], "farmer", text=txt)
        input_ref.current.value = ""
        _append_bubble(convo["messages"][-1])

    def _on_pick_image_exp(ev: ft.FilePickerResultEvent):
        if not ev.files:
            return
        convo = convo_ref["c"]
        if not convo:
            return
        chat_service.send_message(convo["id"], "farmer", img_src=ev.files[0].path)
        _append_bubble(convo["messages"][-1])

    picker_img = ft.FilePicker(on_result=_on_pick_image_exp)
    if page:
        page.overlay.append(picker_img)
        page.update()

    # ── expert dropdown ───────────────────────────────────────────────────────

    expert_options = [
        ft.dropdown.Option(
            key=str(u.get("id_user")),
            text=u.get("ho_ten") or u.get("ten_dang_nhap", f"ID {u.get('id_user')}"),
        )
        for u in experts
    ]

    exp_name_lbl = ft.Text(
        (experts[0].get("ho_ten") or experts[0].get("ten_dang_nhap", "Chuyên gia"))
        if experts else "Chuyên gia",
        size=14, weight=ft.FontWeight.W_700,
    )

    def _on_expert_change(e):
        try:
            chosen_id = int(e.control.value)
        except (TypeError, ValueError):
            return
        chosen = next((u for u in experts
                       if u.get("id_user") == chosen_id), None)
        selected_exp["user"] = chosen
        _reset_chat(chosen)
        exp_name_lbl.value = (
            chosen.get("ho_ten") or chosen.get("ten_dang_nhap", "Chuyên gia")
        ) if chosen else "Chuyên gia"
        if page:
            try:
                page.update()
            except Exception:
                pass

    expert_dd = ft.Dropdown(
        options=expert_options,
        value=str(experts[0].get("id_user")) if experts else None,
        border_radius=12,
        text_size=12,
        content_padding=ft.padding.symmetric(horizontal=10, vertical=2),
        bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.22, ft.Colors.TEAL_300),
        focused_border_color=ft.Colors.TEAL_300,
        hint_text="Chọn chuyên gia…" if not experts else None,
        hint_style=ft.TextStyle(color=ft.Colors.WHITE38, size=12),
        text_style=ft.TextStyle(color=ft.Colors.WHITE, size=12),
        on_change=_on_expert_change,
    )

    # ── header ────────────────────────────────────────────────────────────────

    back_btn = ft.IconButton(
        icon=ft.Icons.ARROW_BACK_IOS_NEW,
        icon_color=ft.Colors.WHITE70,
        icon_size=18,
        tooltip="Quay lại",
        on_click=lambda e: on_back() if on_back else None,
    )

    header = ft.Container(
        padding=ft.padding.symmetric(horizontal=8, vertical=8),
        bgcolor=ft.Colors.with_opacity(0.14, ft.Colors.WHITE),
        border=ft.border.only(
            bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.12, ft.Colors.WHITE))
        ),
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Row(
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        back_btn,
                        ft.Container(
                            width=34, height=34, border_radius=17,
                            bgcolor=ft.Colors.with_opacity(
                                0.20, ft.Colors.TEAL_300),
                            alignment=ft.alignment.center,
                            content=ft.Icon(ft.Icons.SUPPORT_AGENT, size=18,
                                            color=ft.Colors.TEAL_300),
                        ),
                        ft.Column(
                            tight=True, spacing=1, expand=True,
                            controls=[
                                exp_name_lbl,
                                ft.Text("Chuyên gia thú y", size=10,
                                        color=ft.Colors.WHITE60),
                            ],
                        ),
                    ],
                ),
                ft.Row(
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.PERSON_SEARCH,
                                size=16, color=ft.Colors.TEAL_300),
                        ft.Text("Chọn chuyên gia:", size=12,
                                color=ft.Colors.WHITE70),
                        ft.Container(expand=True, content=expert_dd),
                    ],
                ) if experts else ft.Container(
                    padding=ft.padding.symmetric(vertical=4),
                    content=ft.Text(
                        "⚠️ Chưa có chuyên gia trong hệ thống.",
                        size=12, color=WARNING,
                    ),
                ),
            ],
        ),
    )

    # ── chat list ─────────────────────────────────────────────────────────────

    _initial_msgs = convo_ref["c"]["messages"] if convo_ref["c"] else []
    chat_list = ft.ListView(
        ref=list_ref,
        expand=True,
        spacing=8,
        padding=ft.padding.symmetric(horizontal=10, vertical=10),
        controls=[_bubble(m) for m in _initial_msgs],
        auto_scroll=True,
    )

    # ── input bar ─────────────────────────────────────────────────────────────

    txt_input = ft.TextField(
        ref=input_ref,
        hint_text="Nhắn tin cho chuyên gia...",
        expand=True,
        border_radius=20,
        min_lines=1,
        max_lines=4,
        shift_enter=True,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.20, ft.Colors.WHITE),
        focused_border_color=ft.Colors.TEAL_300,
        hint_style=ft.TextStyle(color=ft.Colors.WHITE38, size=13),
        text_style=ft.TextStyle(color=ft.Colors.WHITE, size=13),
        cursor_color=ft.Colors.WHITE,
        content_padding=ft.padding.symmetric(horizontal=14, vertical=10),
        on_submit=_send_text,
    )

    send_btn_exp = ft.Container(
        width=40, height=40, border_radius=20,
        bgcolor=ft.Colors.TEAL_700,
        alignment=ft.alignment.center,
        ink=True,
        on_click=_send_text,
        content=ft.Icon(ft.Icons.SEND_ROUNDED, size=18, color=ft.Colors.WHITE),
    )

    input_bar = ft.Container(
        padding=ft.padding.symmetric(horizontal=8, vertical=8),
        bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.WHITE),
        border=ft.border.only(
            top=ft.BorderSide(1, ft.Colors.with_opacity(0.14, ft.Colors.WHITE))
        ),
        content=ft.Row(
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.END,
            controls=[
                ft.IconButton(
                    icon=ft.Icons.IMAGE_OUTLINED,
                    icon_color=ft.Colors.TEAL_300,
                    icon_size=22,
                    tooltip="Gửi ảnh",
                    on_click=lambda e: picker_img.pick_files(
                        allow_multiple=False,
                        file_type=ft.FilePickerFileType.IMAGE,
                    ),
                ),
                txt_input,
                send_btn_exp,
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

