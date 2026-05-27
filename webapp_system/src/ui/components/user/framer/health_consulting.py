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
from bll.services import chat_service, local_chat_store
from bll.user.farmer import tu_van_ai
from bll.user.expert.error_sample_service import create_error_sample
from ui.theme import PRIMARY, SECONDARY, WARNING, DANGER
from ui.upload_bridge import build_upload_batch, get_app_mode, is_web_picker_file, is_web_session, wait_for_uploaded_file

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


def _format_ai_history_day(day_key: str) -> str:
    try:
        dt = datetime.datetime.strptime(day_key, "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return day_key


def _get_experts() -> list[dict]:
    """Lấy danh sách chuyên gia đã merge profile, lọc và sắp xếp ổn định."""
    try:
        experts: list[dict] = []
        seen_ids: set[int] = set()
        for user in list_users():
            role = str(user.get("vai_tro") or "").strip().lower()
            if role != "expert":
                continue
            try:
                expert_id = int(user.get("id_user") or 0)
            except (TypeError, ValueError):
                continue
            if not expert_id or expert_id in seen_ids:
                continue
            seen_ids.add(expert_id)
            experts.append(user)
        experts.sort(
            key=lambda item: (
                str(item.get("ho_ten") or item.get("ten_dang_nhap") or "").strip().lower(),
                int(item.get("id_user") or 0),
            )
        )
        return experts
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ENTRY
# ─────────────────────────────────────────────────────────────────────────────

def build_health_consulting(page: ft.Page | None = None):  # noqa: C901
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
        scroll=ft.ScrollMode.AUTO,
        controls=[content_area],
    )


# ─────────────────────────────────────────────────────────────────────────────
# SELECTION SCREEN
# ─────────────────────────────────────────────────────────────────────────────

def _make_selection_screen(on_ai, on_expert):
    def _card(icon, title, subtitle, color, on_click):
        return ft.Container(
            height=196,
            expand=True,
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
        scroll=ft.ScrollMode.AUTO,
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
                padding=ft.padding.symmetric(horizontal=16, vertical=8),
                alignment=ft.alignment.top_center,
                content=ft.Column(
                    spacing=16,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            width=340,
                            content=_card(
                                icon=ft.Icons.SMART_TOY,
                                title="Tư vấn với AI",
                                subtitle="Gửi ảnh con bò để AI phân tích bệnh tật\n"
                                         "và đưa ra lời khuyên ngay lập tức.",
                                color=SECONDARY,
                                on_click=lambda e: on_ai(),
                            ),
                        ),
                        ft.Container(
                            width=340,
                            content=_card(
                                icon=ft.Icons.SUPPORT_AGENT,
                                title="Tư vấn chuyên gia",
                                subtitle="Chọn chuyên gia thú y để nhận tư vấn\n"
                                         "trực tiếp từ người có kinh nghiệm.",
                                color=ft.Colors.TEAL_300,
                                on_click=lambda e: on_expert(),
                            ),
                        ),
                    ],
                ),
            ),
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
# AI CHAT
# ─────────────────────────────────────────────────────────────────────────────

def _make_ai_chat(page: ft.Page | None, on_back=None):  # noqa: C901
    messages: list[dict] = local_chat_store.load_ai_messages(limit=80)
    if not messages:
        messages = list(_SEED_MESSAGES)
        for msg in messages:
            local_chat_store.save_ai_message(msg)
    list_ref       = ft.Ref[ft.ListView]()
    input_ref      = ft.Ref[ft.TextField]()
    pending_uploads: dict[str, dict] = {}
    app_mode = get_app_mode(page)

    def _current_farmer_context() -> tuple[int, str]:
        user_id = 0
        user_name = "Nông dân"
        if page:
            try:
                user_id = int(page.client_storage.get("user_id") or 0)
            except Exception:
                user_id = 0
            try:
                user_name = str(page.client_storage.get("user_name") or page.client_storage.get("full_name") or "").strip() or user_name
            except Exception:
                pass
            if not user_id:
                try:
                    user_id = int((page.data or {}).get("user_id") or 0)
                except Exception:
                    user_id = 0
            if user_name == "Nông dân":
                try:
                    user_name = str((page.data or {}).get("user_name") or (page.data or {}).get("full_name") or "").strip() or user_name
                except Exception:
                    pass
        return user_id, user_name

    def _snack(text: str, error: bool = False):
        if not page:
            return
        page.snack_bar = ft.SnackBar(
            content=ft.Text(text, color=ft.Colors.WHITE),
            bgcolor=DANGER if error else SECONDARY,
            open=True,
        )
        try:
            page.update()
        except Exception:
            pass

    # ── helpers ──────────────────────────────────────────────────────────────

    def _close_dlg(dlg):
        if page:
            try:
                page.close(dlg)
            except Exception:
                dlg.open = False
                page.update()

    def _save_error_sample_from_result(ai_result: dict, reason: str):
        farmer_id, farmer_name = _current_farmer_context()
        last_farmer_img = next(
            (
                msg for msg in reversed(messages)
                if msg.get("sender") == "farmer" and (msg.get("img_src") or msg.get("img_b64"))
            ),
            {},
        )
        create_error_sample(
            farmer_id=farmer_id,
            farmer_name=farmer_name,
            reason=reason,
            note="Tạo từ màn Tư vấn AI",
            image_src=last_farmer_img.get("img_src") or "",
            image_b64=last_farmer_img.get("img_b64") or "",
            ai_result=ai_result,
            source_page="farmer_consulting",
        )
        _snack("Đã lưu mẫu lỗi cho chuyên gia.", error=False)

    def _open_detail_dialog(ai_result: dict):
        """Popup chi tiết: ảnh chú thích + bảng bệnh + tư vấn Gemini."""
        diagnosis  = ai_result.get("diagnosis", {})
        detected   = diagnosis.get("detected", [])
        b64_img    = ai_result.get("annotated_b64", "")
        model_name = ai_result.get("model_name", "AI Model")
        cls_top1   = diagnosis.get("classification", {}).get("top1")
        cls_topk   = diagnosis.get("classification", {}).get("topk", [])
        cls_model  = ai_result.get("classification_model_name")
        pipeline_stage = ai_result.get("pipeline_stage", "disease_pipeline")
        conf_thresh = float(ai_result.get("conf_thresh") or 0.0)
        n_objects = int(diagnosis.get("n_objects", 0) or 0)
        segmentation_enabled = bool(ai_result.get("segmentation_enabled", False))
        is_seg = bool(ai_result.get("is_seg", False))

        gemini_text    = ft.Text(
            "Nhấn 'Tư vấn AI' để lấy lời khuyên từ Gemini…",
            size=12, color=ft.Colors.WHITE60, italic=True,
        )
        gemini_loading = ft.ProgressRing(width=20, height=20, visible=False,
                                         color=SECONDARY)
        gemini_btn     = ft.Ref[ft.ElevatedButton]()

        def _fetch_gemini(e):
            api_key = str(load_config().get("gemini_api_key") or "").strip()
            if not api_key:
                gemini_text.value = "⚠️ Admin chưa cấu hình Gemini API key trong phần Cài đặt."
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

        disease_metric_rows: list[ft.Control] = [
            ft.Container(
                margin=ft.margin.only(bottom=4),
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                border_radius=8,
                bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.CYAN_300),
                border=ft.border.all(
                    1, ft.Colors.with_opacity(0.24, ft.Colors.CYAN_300)
                ),
                content=ft.Row(
                    spacing=8,
                    controls=[
                        ft.Icon(ft.Icons.QUERY_STATS, size=16, color=ft.Colors.CYAN_200),
                        ft.Text("Số vùng bệnh phát hiện", size=12, color=ft.Colors.WHITE, expand=True),
                        ft.Text(str(n_objects), size=12, color=ft.Colors.CYAN_100, weight=ft.FontWeight.W_700),
                    ],
                ),
            ),
            ft.Container(
                margin=ft.margin.only(bottom=4),
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                border_radius=8,
                bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.DEEP_PURPLE_300),
                border=ft.border.all(
                    1, ft.Colors.with_opacity(0.24, ft.Colors.DEEP_PURPLE_300)
                ),
                content=ft.Row(
                    spacing=8,
                    controls=[
                        ft.Icon(ft.Icons.AUTO_GRAPH, size=16, color=ft.Colors.DEEP_PURPLE_200),
                        ft.Text("Ngưỡng tin cậy đang dùng", size=12, color=ft.Colors.WHITE, expand=True),
                        ft.Text(f"{conf_thresh:.0%}" if conf_thresh > 0 else "N/A", size=12, color=ft.Colors.DEEP_PURPLE_100, weight=ft.FontWeight.W_700),
                    ],
                ),
            ),
            ft.Container(
                margin=ft.margin.only(bottom=4),
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                border_radius=8,
                bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.TEAL_300),
                border=ft.border.all(
                    1, ft.Colors.with_opacity(0.24, ft.Colors.TEAL_300)
                ),
                content=ft.Row(
                    spacing=8,
                    controls=[
                        ft.Icon(ft.Icons.GRID_ON, size=16, color=ft.Colors.TEAL_200),
                        ft.Text("Kiểu đầu ra", size=12, color=ft.Colors.WHITE, expand=True),
                        ft.Text(
                            "Mask segmentation" if segmentation_enabled and is_seg else "Bounding box",
                            size=12,
                            color=ft.Colors.TEAL_100,
                            weight=ft.FontWeight.W_700,
                        ),
                    ],
                ),
            ),
        ]
        if cls_top1:
            disease_metric_rows.append(
                ft.Container(
                    margin=ft.margin.only(bottom=4),
                    padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    border_radius=8,
                    bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.BLUE_300),
                    border=ft.border.all(
                        1, ft.Colors.with_opacity(0.24, ft.Colors.BLUE_300)
                    ),
                    content=ft.Row(
                        spacing=8,
                        controls=[
                            ft.Icon(ft.Icons.PSYCHOLOGY_ALT, size=16, color=ft.Colors.BLUE_200),
                            ft.Text("Bệnh ưu tiên từ classification", size=12, color=ft.Colors.WHITE, expand=True),
                            ft.Text(f"{cls_top1['class']} ({cls_top1['confidence']:.0%})", size=12, color=ft.Colors.CYAN_100, weight=ft.FontWeight.W_700),
                        ],
                    ),
                )
            )
            if len(cls_topk) > 1:
                disease_metric_rows.append(
                    ft.Text(
                        "Top gợi ý bệnh: " + ", ".join(
                            f"{c['class']} ({c['confidence']:.0%})" for c in cls_topk[:3]
                        ),
                        size=11,
                        color=ft.Colors.WHITE60,
                    )
                )

        annotated_ctrl = (
            ft.Image(src_base64=b64_img, width=320, height=240,
                     border_radius=8, fit=ft.ImageFit.CONTAIN)
            if b64_img
            else ft.Text(
                "Không phát hiện vùng bệnh để vẽ mask trên ảnh này.",
                size=11,
                color=ft.Colors.WHITE54,
            )
        )

        dlg_content = ft.Column(
            scroll=ft.ScrollMode.AUTO, width=340, spacing=10,
            controls=[
                annotated_ctrl,
                ft.Text(f"Model: {model_name}", size=10, color=ft.Colors.WHITE38),
                ft.Text(
                    f"Luồng phân tích: {'Dừng ở bước sàng lọc nội bộ' if pipeline_stage == 'healthy_gate_only' else 'Phân loại bệnh và vẽ vùng bệnh'}",
                    size=10,
                    color=ft.Colors.WHITE38,
                ),
                ft.Text(
                    f"Classification bệnh: {cls_model or 'Chưa cấu hình'}",
                    size=10,
                    color=ft.Colors.WHITE38,
                ),
                ft.Divider(height=1,
                           color=ft.Colors.with_opacity(0.15, ft.Colors.WHITE)),
                ft.Text("Kết quả phát hiện bệnh:", size=13,
                        weight=ft.FontWeight.W_600),
                *disease_rows,
                ft.Divider(height=1,
                           color=ft.Colors.with_opacity(0.15, ft.Colors.WHITE)),
                ft.Text("Thông số bệnh và mask:", size=13,
                        weight=ft.FontWeight.W_600),
                *disease_metric_rows,
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
                ft.Divider(height=1,
                           color=ft.Colors.with_opacity(0.15, ft.Colors.WHITE)),
                ft.Text("Phản hồi cho chuyên gia:", size=13, weight=ft.FontWeight.W_600),
                ft.Row(
                    wrap=True,
                    spacing=8,
                    run_spacing=8,
                    controls=[
                        ft.OutlinedButton(
                            "Lưu ảnh lỗi",
                            icon=ft.Icons.BUG_REPORT_OUTLINED,
                            on_click=lambda e: _save_error_sample_from_result(ai_result, "prediction_error"),
                        ),
                        ft.OutlinedButton(
                            "Cần gán nhãn lại",
                            icon=ft.Icons.LABEL_IMPORTANT_OUTLINE,
                            on_click=lambda e: _save_error_sample_from_result(ai_result, "relabel_needed"),
                        ),
                    ],
                ),
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
                ft.TextButton(
                    "Lưu ảnh lỗi",
                    on_click=lambda e: _save_error_sample_from_result(ai_result, "prediction_error"),
                ),
                ft.TextButton("Đóng", on_click=lambda e: _close_dlg(dlg)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        if page:
            try:
                page.open(dlg)
            except Exception:
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

        if msg.get("img_b64"):
            inner.append(
                ft.Image(src_base64=msg["img_b64"], width=200, border_radius=10,
                         fit=ft.ImageFit.COVER)
            )
        elif msg.get("img_src"):
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
            cls_top1  = ai_result.get("diagnosis", {}).get("classification", {}).get("top1")
            chips: list[ft.Control] = []
            if detected:
                for d in detected[:4]:
                    chip_color = ft.Colors.BLUE_400 if d.get("source") == "classification" else ft.Colors.RED_400
                    chip_border = ft.Colors.BLUE_300 if d.get("source") == "classification" else ft.Colors.RED_300
                    chip_icon = ft.Icons.PSYCHOLOGY_ALT if d.get("source") == "classification" else ft.Icons.CORONAVIRUS
                    chips.append(
                        ft.Container(
                            padding=ft.padding.symmetric(horizontal=7, vertical=3),
                            border_radius=12,
                            bgcolor=ft.Colors.with_opacity(0.22, chip_color),
                            border=ft.border.all(
                                1, ft.Colors.with_opacity(0.40, chip_border)
                            ),
                            content=ft.Row(tight=True, spacing=4, controls=[
                                ft.Icon(chip_icon, size=10, color=chip_border),
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
            if cls_top1:
                inner.append(
                    ft.Text(
                        f"Classification ưu tiên: {cls_top1['class']} ({cls_top1['confidence']:.0%})",
                        size=10,
                        color=ft.Colors.CYAN_200,
                    )
                )
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

    def _open_ai_history():
        if not page:
            return

        def _history_tile(group: dict) -> ft.Control:
            day_label = _format_ai_history_day(group.get("day_key", ""))
            preview = (group.get("preview") or "").strip()
            if len(preview) > 70:
                preview = preview[:70] + "..."

            def _show_day_messages(e=None):
                day_messages = local_chat_store.load_ai_messages_by_day(group["day_key"])
                detail = ft.AlertDialog(
                    modal=True,
                    bgcolor=ft.Colors.with_opacity(0.96, ft.Colors.GREY_900),
                    title=ft.Row(
                        spacing=8,
                        controls=[
                            ft.Icon(ft.Icons.CALENDAR_MONTH, color=SECONDARY, size=18),
                            ft.Text(f"Lịch sử {day_label}", size=14, weight=ft.FontWeight.W_700),
                        ],
                    ),
                    content=ft.Container(
                        width=340,
                        height=460,
                        content=ft.ListView(
                            spacing=8,
                            auto_scroll=False,
                            controls=[_bubble(msg) for msg in day_messages],
                        ),
                    ),
                    actions=[ft.TextButton("Đóng", on_click=lambda ev: _close_dlg(detail))],
                    actions_alignment=ft.MainAxisAlignment.END,
                )
                page.open(detail)

            return ft.Container(
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                border_radius=14,
                bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
                border=ft.border.all(1, ft.Colors.with_opacity(0.10, ft.Colors.WHITE)),
                ink=True,
                on_click=_show_day_messages,
                content=ft.Column(
                    spacing=4,
                    tight=True,
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Text(day_label, size=13, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE, expand=True),
                                ft.Text(f"{group.get('total_messages', 0)} tin", size=10, color=ft.Colors.WHITE54),
                            ],
                        ),
                        ft.Text(
                            preview or "Ảnh hoặc kết quả AI",
                            size=11,
                            color=ft.Colors.WHITE70,
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                ),
            )

        groups = local_chat_store.list_ai_history_groups(limit_days=30)
        history_dialog = ft.AlertDialog(
            modal=True,
            bgcolor=ft.Colors.with_opacity(0.96, ft.Colors.GREY_900),
            title=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.HISTORY, color=SECONDARY, size=18),
                    ft.Text("Lịch sử tư vấn AI", size=14, weight=ft.FontWeight.W_700),
                ],
            ),
            content=ft.Container(
                width=340,
                height=460,
                content=(
                    ft.Column(
                        spacing=8,
                        scroll=ft.ScrollMode.AUTO,
                        controls=[_history_tile(group) for group in groups],
                    )
                    if groups
                    else ft.Container(
                        alignment=ft.alignment.center,
                        content=ft.Text("Chưa có lịch sử tư vấn AI.", size=12, color=ft.Colors.WHITE54),
                    )
                ),
            ),
            actions=[ft.TextButton("Đóng", on_click=lambda e: _close_dlg(history_dialog))],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(history_dialog)

    def _append_system_text(text: str):
        msg = {
            "sender": "system", "text": text,
            "img_src": None, "img_b64": None, "file_name": None,
            "time": _now(), "ai_result": None,
        }
        messages.append(msg)
        _append_bubble(msg)

    def _persist_ai_message(msg: dict):
        local_chat_store.save_ai_message(msg)

    def _send_text(e=None):
        txt = (input_ref.current.value or "").strip()
        if not txt:
            return
        api_key = str(load_config().get("gemini_api_key") or "").strip()
        msg = {
            "sender": "farmer", "text": txt,
            "img_src": None, "img_b64": None, "file_name": None,
            "time": _now(), "ai_result": None,
        }
        messages.append(msg)
        _persist_ai_message(msg)
        input_ref.current.value = ""
        _append_bubble(msg)
        if not api_key:
            err_msg = {
                "sender": "system",
                "text": "⚠️ Admin chưa cấu hình Gemini API key trong phần Cài đặt.",
                "img_src": None,
                "img_b64": None,
                "file_name": None,
                "time": _now(),
                "ai_result": None,
            }
            messages.append(err_msg)
            _persist_ai_message(err_msg)
            _append_bubble(err_msg)
            return

        wait_msg = {
            "sender": "system",
            "text": "💬 AI đang suy nghĩ…",
            "img_src": None,
            "img_b64": None,
            "file_name": None,
            "time": _now(),
            "ai_result": None,
        }
        messages.append(wait_msg)
        _append_bubble(wait_msg)

        history = [
            {"sender": item.get("sender"), "text": item.get("text")}
            for item in messages[:-1]
            if item.get("text")
        ]

        def _on_chat_result(text: str):
            if list_ref.current and list_ref.current.controls:
                list_ref.current.controls.pop()
            ai_msg = {
                "sender": "system",
                "text": text,
                "img_src": None,
                "img_b64": None,
                "file_name": None,
                "time": _now(),
                "ai_result": None,
            }
            messages.append(ai_msg)
            _persist_ai_message(ai_msg)
            if list_ref.current and list_ref.current.page:
                list_ref.current.controls.append(_bubble(ai_msg))
                if page:
                    try:
                        page.update()
                    except Exception:
                        pass

        tu_van_ai.call_farmer_chat_async(api_key, txt, history, _on_chat_result)

    def _run_ai_analysis(img_path: str):
        """Chạy phân tích bệnh AI sau khi ảnh được gửi."""
        wait_msg = {
            "sender": "system",
            "text": "🔍 Đang phân tích ảnh với AI…",
            "img_src": None, "img_b64": None, "file_name": None,
            "time": _now(), "ai_result": None,
        }
        messages.append(wait_msg)
        _append_bubble(wait_msg)

        def _on_result(result_dict: dict):
            # Xoá bubble "Đang phân tích..."
            if list_ref.current and list_ref.current.controls:
                list_ref.current.controls.pop()
            diagnosis = result_dict["diagnosis"]
            detected = diagnosis.get("detected", [])
            n = diagnosis.get("n_objects", 0)
            cls_top1 = diagnosis.get("classification", {}).get("top1")
            seg_names = [d["class"] for d in detected if d.get("source") != "classification"]
            if seg_names and cls_top1:
                summary = (
                    f"Phát hiện {n} vùng bệnh — {', '.join(seg_names[:3])}. "
                    f"Ưu tiên bệnh: {cls_top1['class']} ({cls_top1['confidence']:.0%})."
                )
            elif seg_names:
                summary = f"Phát hiện {n} vùng bệnh — {', '.join(seg_names[:3])}."
            elif cls_top1:
                summary = f"Nghi nhiều nhất: {cls_top1['class']} ({cls_top1['confidence']:.0%})."
            else:
                summary = "Không phát hiện dấu hiệu bệnh rõ ràng trong ảnh."
            ai_msg = {
                "sender": "system", "text": summary,
                "img_src": None, "img_b64": None, "file_name": None,
                "time": _now(), "ai_result": result_dict,
            }
            messages.append(ai_msg)
            _persist_ai_message(ai_msg)
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
                "img_src": None, "img_b64": None, "file_name": None,
                "time": _now(), "ai_result": None,
            }
            messages.append(err_msg)
            _persist_ai_message(err_msg)
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

    def _queue_picker_upload(
        picker: ft.FilePicker,
        key: str,
        files: list,
        subdir: str,
        kind: str,
    ):
        nonlocal pending_uploads
        if not page:
            return
        items, jobs = build_upload_batch(page, files, subdir=subdir)
        pending_uploads[key] = {
            "kind": kind,
            "items": items,
        }
        _append_system_text(
            "⏫ Đang tải ảnh từ thiết bị..." if kind == "image"
            else "⏫ Đang tải tệp từ thiết bị..."
        )
        picker.upload(jobs)

    def _finish_picker_upload(key: str):
        state = pending_uploads.pop(key, None)
        if not state:
            return
        items = state["items"]
        if not items:
            return
        if messages and messages[-1].get("sender") == "system" and "Đang tải" in (messages[-1].get("text") or ""):
            messages.pop()
            if list_ref.current and list_ref.current.controls:
                list_ref.current.controls.pop()
        if state["kind"] == "image":
            item = items[0]
            uploaded = wait_for_uploaded_file(item["server_path"])
            if not uploaded:
                _append_system_text("⚠️ Ảnh đã chọn nhưng chưa lưu được lên server.")
                return
            msg = {
                "sender": "farmer", "text": "Ảnh đã gửi để AI phân tích.",
                "img_src": item["public_src"],
                "img_b64": local_chat_store.read_image_base64_from_source(str(uploaded)),
                "file_name": None,
                "time": _now(), "ai_result": None,
            }
            messages.append(msg)
            _persist_ai_message(msg)
            _append_bubble(msg)
            _run_ai_analysis(str(uploaded))
        else:
            item = items[0]
            uploaded = wait_for_uploaded_file(item["server_path"])
            if not uploaded:
                _append_system_text("⚠️ Tệp đã chọn nhưng chưa lưu được lên server.")
                return
            msg = {
                "sender": "farmer", "text": None,
                "img_src": None, "img_b64": None, "file_name": item["name"],
                "time": _now(), "ai_result": None,
            }
            messages.append(msg)
            _persist_ai_message(msg)
            _append_bubble(msg)

    def _on_pick_image(e: ft.FilePickerResultEvent):
        if not e.files:
            return
        file_obj = e.files[0]
        if is_web_picker_file(file_obj):
            _queue_picker_upload(
                picker_img,
                "img",
                [file_obj],
                subdir="health_consulting/images",
                kind="image",
            )
            return
        img_path = file_obj.path
        msg = {
            "sender": "farmer", "text": "Ảnh đã gửi để AI phân tích.",
            "img_src": img_path,
            "img_b64": local_chat_store.read_image_base64_from_source(img_path),
            "file_name": None,
            "time": _now(), "ai_result": None,
        }
        messages.append(msg)
        _persist_ai_message(msg)
        _append_bubble(msg)
        _run_ai_analysis(img_path)

    def _on_pick_file(e: ft.FilePickerResultEvent):
        if not e.files:
            return
        file_obj = e.files[0]
        if is_web_picker_file(file_obj):
            _queue_picker_upload(
                picker_file,
                "file",
                [file_obj],
                subdir="health_consulting/files",
                kind="file",
            )
            return
        msg = {
            "sender": "farmer", "text": None,
            "img_src": None, "img_b64": None, "file_name": file_obj.name,
            "time": _now(), "ai_result": None,
        }
        messages.append(msg)
        _persist_ai_message(msg)
        _append_bubble(msg)

    def _handle_picker_upload(key: str, e: ft.FilePickerUploadEvent):
        state = pending_uploads.get(key)
        if not state:
            return
        if e.error:
            pending_uploads.pop(key, None)
            err_msg = {
                "sender": "system", "text": f"⚠️ Upload thất bại: {e.error}",
                "img_src": None, "file_name": None,
                "time": _now(), "ai_result": None,
            }
            messages.append(err_msg)
            _append_bubble(err_msg)
            return
        if e.progress != 1.0:
            return
        for item in state["items"]:
            if item["name"] == e.file_name and not item["done"]:
                item["done"] = True
                break
        if all(item["done"] for item in state["items"]):
            _finish_picker_upload(key)

    def _on_picker_img_upload(e: ft.FilePickerUploadEvent):
        _handle_picker_upload("img", e)

    def _on_picker_file_upload(e: ft.FilePickerUploadEvent):
        _handle_picker_upload("file", e)

    def _open_camera_live(e):
        """Camera dialog: live preview → chụp → xem lại → gửi / chụp lại."""
        if app_mode == "web" or is_web_session(page):
            picker_img.pick_files(
                allow_multiple=False,
                file_type=ft.FilePickerFileType.IMAGE,
                dialog_title="Chụp ảnh hoặc chọn từ thư viện",
            )
            return
        stop_evt   = threading.Event()
        last_frame: dict = {"frame": None}
        snap_path: dict  = {"path": None}     # ảnh đã chụp
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
            if page:
                try:
                    page.close(dlg)
                except Exception:
                    try:
                        dlg.open = False
                        page.update()
                    except Exception:
                        pass
            msg = {
                "sender": "farmer", "text": "Ảnh đã chụp để AI phân tích.",
                "img_src": path,
                "img_b64": local_chat_store.read_image_base64_from_source(path),
                "file_name": None,
                "time": _now(), "ai_result": None,
            }
            messages.append(msg)
            _persist_ai_message(msg)
            _append_bubble(msg)
            _run_ai_analysis(path)

        def _do_retake(e):
            """Huỷ ảnh, quay lại xem live."""
            snap_path["path"] = None
            _set_preview_mode(False)

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
                dlg.open = True
                page.update()
            threading.Thread(target=_stream, daemon=True).start()

    picker_img  = ft.FilePicker(on_result=_on_pick_image, on_upload=_on_picker_img_upload)
    picker_file = ft.FilePicker(on_result=_on_pick_file, on_upload=_on_picker_file_upload)

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
                ft.Row(
                    spacing=2,
                    vertical_alignment=ft.CrossAxisAlignment.END,
                    controls=[
                        _attach_btn(
                            ft.Icons.IMAGE_OUTLINED, "Chụp ảnh / thư viện", SECONDARY,
                            lambda e: picker_img.pick_files(
                                allow_multiple=False,
                                file_type=ft.FilePickerFileType.IMAGE,
                                dialog_title="Chụp ảnh hoặc chọn từ thư viện",
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
                ft.IconButton(
                    icon=ft.Icons.HISTORY,
                    icon_color=ft.Colors.WHITE70,
                    icon_size=18,
                    tooltip="Lịch sử tư vấn AI",
                    on_click=lambda e: _open_ai_history(),
                ),
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

def _make_expert_chat(page: ft.Page | None, on_back=None):  # noqa: C901
    experts = _get_experts()
    holder = ft.Container(expand=True)

    def _safe_page_update():
        if page:
            try:
                page.update()
            except Exception:
                pass

    def _expert_id_of(expert: dict | None) -> int:
        if not expert:
            return 0
        try:
            return int(expert.get("id_user") or 0)
        except (TypeError, ValueError):
            return 0

    def _expert_name(expert: dict | None) -> str:
        if not expert:
            return "Chuyên gia"
        return (
            str(expert.get("ho_ten") or "").strip()
            or str(expert.get("ten_dang_nhap") or "").strip()
            or f"ID {_expert_id_of(expert)}"
        )

    farmer_id = 0
    farmer_name = "Nông dân"
    farmer_avatar = ""
    if page:
        try:
            farmer_id = int(page.client_storage.get("user_id") or 0)
            farmer_name = page.client_storage.get("ho_ten") or "Nông dân"
            farmer_avatar = page.client_storage.get("anh_dai_dien") or ""
        except Exception:
            farmer_id = 0
        if not farmer_id:
            try:
                farmer_id = int((page.data or {}).get("user_id") or 0)
                farmer_name = (page.data or {}).get("ho_ten") or farmer_name
                farmer_avatar = (page.data or {}).get("anh_dai_dien") or farmer_avatar
            except Exception:
                pass

    def _avatar_thumb(src: str | None, fallback_icon, tint: str, size: int = 32, label: str = "") -> ft.Control:
        fallback = ft.Container(
            width=size,
            height=size,
            border_radius=size / 2,
            bgcolor=ft.Colors.with_opacity(0.20, tint),
            alignment=ft.alignment.center,
            content=ft.Icon(fallback_icon, size=max(14, size // 2), color=tint),
        )
        if not src:
            return fallback
        return ft.Container(
            width=size,
            height=size,
            border_radius=size / 2,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.WHITE),
            content=ft.Image(
                src=src,
                fit=ft.ImageFit.COVER,
                error_content=fallback,
            ),
        )

    def _open_expert_profile_dialog(expert: dict):
        if not page:
            return
        details = ft.Column(
            width=340,
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Row(
                    spacing=10,
                    controls=[
                        _avatar_thumb(
                            expert.get("anh_dai_dien"),
                            ft.Icons.SUPPORT_AGENT,
                            ft.Colors.TEAL_300,
                            size=46,
                        ),
                        ft.Column(
                            tight=True,
                            spacing=2,
                            controls=[
                                ft.Text(_expert_name(expert), size=17, weight=ft.FontWeight.W_700),
                                ft.Text(str(expert.get("chuyen_mon") or "Chưa cập nhật chuyên môn."), size=13, color=ft.Colors.WHITE70),
                            ],
                        ),
                    ],
                ),
                ft.Text(f"Kinh nghiệm: {expert.get('so_nam_kinh_nghiem', 0) or 0} năm", size=12, color=ft.Colors.WHITE70),
                ft.Text(f"Chứng chỉ: {expert.get('ma_chung_chi') or 'Chưa cập nhật'}", size=12, color=ft.Colors.WHITE70),
                ft.Text(f"Số điện thoại: {expert.get('so_dien_thoai') or 'Chưa cập nhật'}", size=12, color=ft.Colors.WHITE70),
                ft.Text(f"Email: {expert.get('email') or 'Chưa cập nhật'}", size=12, color=ft.Colors.WHITE70),
                ft.Text(f"Địa chỉ: {expert.get('dia_chi') or 'Chưa cập nhật'}", size=12, color=ft.Colors.WHITE70),
            ],
        )
        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=ft.Colors.with_opacity(0.96, ft.Colors.GREY_900),
            title=ft.Text("Hồ sơ chuyên gia", size=15, weight=ft.FontWeight.W_700),
            content=details,
            actions=[ft.TextButton("Đóng", on_click=lambda e: page.close(dlg))],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        try:
            page.open(dlg)
        except Exception:
            dlg.open = True
            page.update()

    def _make_expert_chat_detail(expert: dict, on_back_to_lobby) -> ft.Control:
        convo = chat_service.get_or_create_conversation(farmer_id, farmer_name, _expert_id_of(expert))
        if not convo["messages"]:
            chat_service.send_message(
                convo["id"],
                "expert",
                text=f"Xin chào! Tôi là {_expert_name(expert)}.\nHãy mô tả tình trạng con bò của bạn hoặc gửi ảnh để tôi hỗ trợ.",
                time_text="08:00",
            )
            convo = chat_service.get_conversation_pair(farmer_id, _expert_id_of(expert)) or convo

        convo_ref: dict[str, dict | None] = {"c": convo}
        stop_sync_evt = threading.Event()
        sync_state = {"sig": "", "typing": ""}
        list_ref = ft.Ref[ft.ListView]()
        input_ref = ft.Ref[ft.TextField]()
        typing_status_text = ft.Text(value="", size=10, color=ft.Colors.WHITE54)
        expert_avatar = str(expert.get("anh_dai_dien") or "").strip()

        def _messages_signature(current: dict | None) -> str:
            if not current:
                return "none"
            return "|".join(
                f"{msg.get('sender')}::{msg.get('time')}::{msg.get('text') or ''}::{bool(msg.get('img_src') or msg.get('img_b64'))}"
                for msg in current.get("messages", [])
            )

        def _bubble(msg: dict) -> ft.Control:
            is_me = msg.get("sender") == "farmer"
            bubble_color = ft.Colors.with_opacity(0.30, PRIMARY) if is_me else ft.Colors.with_opacity(0.16, ft.Colors.TEAL_300)
            border_color = ft.Colors.with_opacity(0.40, PRIMARY) if is_me else ft.Colors.with_opacity(0.30, ft.Colors.TEAL_300)
            avatar = _avatar_thumb(
                farmer_avatar if is_me else expert_avatar,
                ft.Icons.PERSON if is_me else ft.Icons.SUPPORT_AGENT,
                PRIMARY if is_me else ft.Colors.TEAL_300,
                size=28,
            )
            inner: list[ft.Control] = []
            if msg.get("img_b64"):
                inner.append(ft.Image(src_base64=msg["img_b64"], width=200, border_radius=10, fit=ft.ImageFit.COVER))
            elif msg.get("img_src"):
                inner.append(ft.Image(src=msg["img_src"], width=200, border_radius=10, fit=ft.ImageFit.COVER))
            if msg.get("text"):
                inner.append(ft.Text(msg["text"], size=13, color=ft.Colors.WHITE, selectable=True))
            inner.append(
                ft.Text(
                    msg.get("time", ""),
                    size=9,
                    color=ft.Colors.WHITE38,
                    text_align=ft.TextAlign.RIGHT if is_me else ft.TextAlign.LEFT,
                )
            )
            bubble = ft.Container(
                width=270,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                border_radius=ft.border_radius.only(
                    top_left=16,
                    top_right=16,
                    bottom_left=4 if is_me else 16,
                    bottom_right=16 if is_me else 4,
                ),
                bgcolor=bubble_color,
                border=ft.border.all(1, border_color),
                content=ft.Column(spacing=4, tight=True, controls=inner),
            )
            return ft.Row(
                alignment=ft.MainAxisAlignment.END if is_me else ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.END,
                spacing=6,
                controls=[bubble, avatar] if is_me else [avatar, bubble],
            )

        def _render_chat_messages(current: dict | None):
            if list_ref.current:
                list_ref.current.controls = [_bubble(msg) for msg in ((current or {}).get("messages") or [])]

        def _refresh_typing_status(current: dict | None):
            status = ""
            if chat_service.is_typing_active(current, "expert"):
                status = f"{_expert_name(expert)} đang soạn tin nhắn..."
            elif chat_service.is_typing_active(current, "farmer"):
                status = "Bạn đang soạn tin nhắn..."
            typing_status_text.value = status

        def _sync_chat_view(force: bool = False):
            fresh = chat_service.get_conversation_pair(farmer_id, _expert_id_of(expert))
            if fresh is None:
                return
            convo_ref["c"] = fresh
            sig = _messages_signature(fresh)
            typing_sig = f"{fresh.get('typing_farmer_at', '')}|{fresh.get('typing_expert_at', '')}"
            if force or sig != sync_state["sig"]:
                _render_chat_messages(fresh)
                sync_state["sig"] = sig
            if force or typing_sig != sync_state["typing"]:
                _refresh_typing_status(fresh)
                sync_state["typing"] = typing_sig
            _safe_page_update()

        def _send_text(_e=None):
            txt = (input_ref.current.value or "").strip()
            if not txt or not convo_ref["c"]:
                return
            chat_service.send_message(convo_ref["c"]["id"], "farmer", text=txt)
            chat_service.set_typing(convo_ref["c"]["id"], "farmer", False)
            input_ref.current.value = ""
            _sync_chat_view(True)

        def _on_pick_image(ev: ft.FilePickerResultEvent):
            if not ev.files or not convo_ref["c"]:
                return
            file_obj = ev.files[0]
            if is_web_picker_file(file_obj):
                try:
                    items, jobs = build_upload_batch(page, [file_obj], subdir="expert_chat/farmer")
                    picker_img.data = {"pending": items, "convo_id": convo_ref["c"]["id"]}
                    picker_img.upload(jobs)
                except Exception:
                    pass
                return
            chat_service.send_message(
                convo_ref["c"]["id"],
                "farmer",
                img_src=file_obj.path,
                img_b64=local_chat_store.read_image_base64_from_source(file_obj.path),
            )
            chat_service.set_typing(convo_ref["c"]["id"], "farmer", False)
            _sync_chat_view(True)

        def _on_pick_image_upload(ev: ft.FilePickerUploadEvent):
            state = picker_img.data if isinstance(picker_img.data, dict) else None
            if not state:
                return
            if ev.error:
                picker_img.data = None
                return
            if ev.progress != 1.0:
                return
            for item in state["pending"]:
                if item["name"] == ev.file_name and not item["done"]:
                    item["done"] = True
                    break
            if not all(item["done"] for item in state["pending"]):
                return
            item = state["pending"][0]
            uploaded = wait_for_uploaded_file(item["server_path"])
            if not uploaded:
                picker_img.data = None
                return
            chat_service.send_message(
                state["convo_id"],
                "farmer",
                img_src=item["public_src"],
                img_b64=local_chat_store.read_image_base64_from_source(str(uploaded)),
            )
            chat_service.set_typing(state["convo_id"], "farmer", False)
            picker_img.data = None
            _sync_chat_view(True)

        picker_img = ft.FilePicker(on_result=_on_pick_image, on_upload=_on_pick_image_upload)
        if page:
            page.overlay.append(picker_img)
            page.update()

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
            on_change=lambda e: (
                convo_ref["c"]
                and chat_service.set_typing(
                    convo_ref["c"]["id"],
                    "farmer",
                    bool((e.control.value or "").strip()),
                )
            ),
        )

        chat_list = ft.ListView(
            ref=list_ref,
            expand=True,
            spacing=8,
            padding=ft.padding.symmetric(horizontal=10, vertical=10),
            controls=[],
            auto_scroll=True,
        )

        header = ft.Container(
            padding=ft.padding.symmetric(horizontal=8, vertical=8),
            bgcolor=ft.Colors.with_opacity(0.14, ft.Colors.WHITE),
            border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.12, ft.Colors.WHITE))),
            content=ft.Column(
                spacing=6,
                controls=[
                    ft.Row(
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.IconButton(
                                icon=ft.Icons.ARROW_BACK_IOS_NEW,
                                icon_color=ft.Colors.WHITE70,
                                icon_size=18,
                                tooltip="Quay lại danh sách",
                                on_click=lambda _e: (
                                    stop_sync_evt.set(),
                                    convo_ref["c"] and chat_service.set_typing(convo_ref["c"]["id"], "farmer", False),
                                    on_back_to_lobby(),
                                ),
                            ),
                            _avatar_thumb(expert_avatar, ft.Icons.SUPPORT_AGENT, ft.Colors.TEAL_300, size=34),
                            ft.Column(
                                tight=True,
                                spacing=2,
                                expand=True,
                                controls=[
                                    ft.Text(_expert_name(expert), size=14, weight=ft.FontWeight.W_700),
                                    ft.Text(str(expert.get("chuyen_mon") or "Chuyên gia thú y"), size=10, color=ft.Colors.WHITE60),
                                    typing_status_text,
                                ],
                            ),
                            ft.TextButton("Hồ sơ", on_click=lambda _e: _open_expert_profile_dialog(expert)),
                        ],
                    ),
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=10, vertical=10),
                        border_radius=14,
                        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.TEAL_300),
                        border=ft.border.all(1, ft.Colors.with_opacity(0.24, ft.Colors.TEAL_300)),
                        content=ft.Column(
                            tight=True,
                            spacing=4,
                            controls=[
                                ft.Text(f"Kinh nghiệm: {expert.get('so_nam_kinh_nghiem', 0) or 0} năm", size=11, color=ft.Colors.WHITE70),
                                ft.Text(f"Chứng chỉ: {expert.get('ma_chung_chi') or 'Chưa cập nhật'}", size=11, color=ft.Colors.WHITE60),
                            ],
                        ),
                    ),
                ],
            ),
        )

        input_bar = ft.Container(
            padding=ft.padding.symmetric(horizontal=8, vertical=8),
            bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.WHITE),
            border=ft.border.only(top=ft.BorderSide(1, ft.Colors.with_opacity(0.14, ft.Colors.WHITE))),
            content=ft.Row(
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.END,
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.IMAGE_OUTLINED,
                        icon_color=ft.Colors.TEAL_300,
                        icon_size=22,
                        tooltip="Chụp ảnh / thư viện",
                        on_click=lambda _e: picker_img.pick_files(
                            allow_multiple=False,
                            file_type=ft.FilePickerFileType.IMAGE,
                            dialog_title="Chụp ảnh hoặc chọn từ thư viện",
                        ),
                    ),
                    txt_input,
                    ft.Container(
                        width=40,
                        height=40,
                        border_radius=20,
                        bgcolor=ft.Colors.TEAL_700,
                        alignment=ft.alignment.center,
                        ink=True,
                        on_click=_send_text,
                        content=ft.Icon(ft.Icons.SEND_ROUNDED, size=18, color=ft.Colors.WHITE),
                    ),
                ],
            ),
        )

        root = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                header,
                ft.Container(expand=True, content=chat_list),
                input_bar,
            ],
        )
        _sync_chat_view(True)

        def _poll_chat():
            while not stop_sync_evt.wait(0.8):
                _sync_chat_view()

        threading.Thread(target=_poll_chat, daemon=True).start()
        return root

    def _show_lobby():
        cards: list[ft.Control] = []
        for expert in experts:
            expert_id = _expert_id_of(expert)
            convo = chat_service.get_conversation_pair(farmer_id, expert_id)
            messages = (convo or {}).get("messages", [])
            last = messages[-1] if messages else {}
            preview = last.get("text") or ("[Ảnh]" if (last.get("img_src") or last.get("img_b64")) else "Chưa có cuộc trò chuyện")
            cards.append(
                ft.Container(
                    padding=ft.padding.all(14),
                    border_radius=18,
                    bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.TEAL_300),
                    border=ft.border.all(1, ft.Colors.with_opacity(0.24, ft.Colors.TEAL_300)),
                    content=ft.Column(
                        spacing=8,
                        controls=[
                            ft.Row(
                                spacing=10,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    _avatar_thumb(expert.get("anh_dai_dien"), ft.Icons.SUPPORT_AGENT, ft.Colors.TEAL_300, size=42),
                                    ft.Column(
                                        expand=True,
                                        tight=True,
                                        spacing=2,
                                        controls=[
                                            ft.Text(_expert_name(expert), size=14, weight=ft.FontWeight.W_700),
                                            ft.Text(str(expert.get("chuyen_mon") or "Chưa cập nhật chuyên môn."), size=11, color=ft.Colors.WHITE70),
                                            ft.Text(preview, size=11, color=ft.Colors.WHITE54, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                                        ],
                                    ),
                                    ft.Text(last.get("time", ""), size=10, color=ft.Colors.WHITE38),
                                ],
                            ),
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text(
                                        f"Kinh nghiệm: {expert.get('so_nam_kinh_nghiem', 0) or 0} năm",
                                        size=11,
                                        color=ft.Colors.WHITE60,
                                    ),
                                    ft.Row(
                                        spacing=6,
                                        controls=[
                                            ft.TextButton("Xem hồ sơ", on_click=lambda _e, exp=expert: _open_expert_profile_dialog(exp)),
                                            ft.ElevatedButton(
                                                "Mở chat",
                                                style=ft.ButtonStyle(
                                                    bgcolor={ft.ControlState.DEFAULT: ft.Colors.TEAL_700},
                                                    color=ft.Colors.WHITE,
                                                ),
                                                on_click=lambda _e, exp=expert: _open_detail(exp),
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                )
            )

        if not cards:
            cards = [
                ft.Container(
                    padding=ft.padding.all(24),
                    border_radius=18,
                    bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
                    content=ft.Text("Chưa có chuyên gia nào trong hệ thống.", size=13, color=WARNING),
                )
            ]

        holder.content = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=8, vertical=10),
                    bgcolor=ft.Colors.with_opacity(0.14, ft.Colors.WHITE),
                    border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.12, ft.Colors.WHITE))),
                    content=ft.Row(
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.IconButton(
                                icon=ft.Icons.ARROW_BACK_IOS_NEW,
                                icon_color=ft.Colors.WHITE70,
                                icon_size=18,
                                tooltip="Quay lại",
                                on_click=lambda _e: on_back() if on_back else None,
                            ),
                            ft.Container(
                                width=34,
                                height=34,
                                border_radius=17,
                                bgcolor=ft.Colors.with_opacity(0.20, ft.Colors.TEAL_300),
                                alignment=ft.alignment.center,
                                content=ft.Icon(ft.Icons.FORUM_OUTLINED, size=18, color=ft.Colors.TEAL_300),
                            ),
                            ft.Column(
                                tight=True,
                                spacing=2,
                                expand=True,
                                controls=[
                                    ft.Text("Tư vấn chuyên gia", size=15, weight=ft.FontWeight.W_700),
                                    ft.Text("Chọn chuyên gia hoặc cuộc trò chuyện cần tiếp tục.", size=10, color=ft.Colors.WHITE60),
                                ],
                            ),
                        ],
                    ),
                ),
                ft.Container(
                    expand=True,
                    padding=ft.padding.all(10),
                    content=ft.ListView(spacing=10, controls=cards),
                ),
            ],
        )
        _safe_page_update()

    def _open_detail(expert: dict):
        holder.content = _make_expert_chat_detail(expert, _show_lobby)
        _safe_page_update()

    _show_lobby()
    return holder

