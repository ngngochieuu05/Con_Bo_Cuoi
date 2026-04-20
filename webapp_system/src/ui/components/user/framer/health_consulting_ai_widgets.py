from __future__ import annotations

import flet as ft

from bll.user.farmer import tu_van_ai
from ui.theme import PRIMARY, SECONDARY


def _safe_update(page: ft.Page | None) -> None:
    if not page:
        return
    try:
        page.update()
    except Exception:
        pass


def _close_dialog(page: ft.Page | None, dialog: ft.AlertDialog) -> None:
    if not page:
        return
    try:
        page.close(dialog)
    except Exception:
        dialog.open = False
        _safe_update(page)


def open_ai_detail_dialog(
    page: ft.Page | None,
    gemini_key_ref: ft.Ref[ft.TextField],
    ai_result: dict,
) -> None:
    diagnosis = ai_result.get("diagnosis", {})
    detected = diagnosis.get("detected", [])
    b64_img = ai_result.get("annotated_b64", "")
    model_name = ai_result.get("model_name", "AI Model")

    gemini_text = ft.Text(
        "Nhấn 'Tư vấn AI' để lấy lời khuyên từ Gemini…",
        size=12,
        color=ft.Colors.WHITE60,
        italic=True,
    )
    gemini_loading = ft.ProgressRing(
        width=20,
        height=20,
        visible=False,
        color=SECONDARY,
    )
    gemini_btn = ft.Ref[ft.ElevatedButton]()

    def _fetch_gemini(e):
        api_key = (gemini_key_ref.current.value or "").strip() if gemini_key_ref.current else ""
        if not api_key:
            gemini_text.value = "⚠️ Vui lòng nhập Gemini API key."
            _safe_update(page)
            return
        if gemini_btn.current:
            gemini_btn.current.disabled = True
        gemini_loading.visible = True
        _safe_update(page)
        prompt = tu_van_ai.build_gemini_prompt(diagnosis)

        def _on_gemini(text: str):
            gemini_text.value = text
            gemini_loading.visible = False
            _safe_update(page)

        tu_van_ai.call_gemini_async(api_key, prompt, _on_gemini)

    disease_rows: list[ft.Control] = []
    if detected:
        for item in detected:
            disease_rows.append(
                ft.Container(
                    margin=ft.margin.only(bottom=4),
                    padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    border_radius=8,
                    bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.RED_300),
                    border=ft.border.all(1, ft.Colors.with_opacity(0.30, ft.Colors.RED_300)),
                    content=ft.Row(
                        spacing=8,
                        controls=[
                            ft.Icon(ft.Icons.CORONAVIRUS, size=16, color=ft.Colors.RED_300),
                            ft.Text(item["class"], size=12, color=ft.Colors.WHITE, expand=True),
                            ft.Text(
                                f"{item['confidence']:.0%}",
                                size=12,
                                color=ft.Colors.AMBER_300,
                                weight=ft.FontWeight.W_700,
                            ),
                        ],
                    ),
                )
            )
    else:
        disease_rows.append(
            ft.Text("✅ Không phát hiện bệnh.", size=12, color=ft.Colors.GREEN_300)
        )

    annotated_ctrl = (
        ft.Image(
            src_base64=b64_img,
            width=300,
            height=225,
            border_radius=8,
            fit=ft.ImageFit.CONTAIN,
        )
        if b64_img
        else ft.Text("(Không có ảnh)", size=11, color=ft.Colors.WHITE38)
    )

    dialog = ft.AlertDialog(
        modal=True,
        bgcolor=ft.Colors.with_opacity(0.95, ft.Colors.GREY_900),
        title=ft.Row(
            spacing=8,
            controls=[
                ft.Icon(ft.Icons.BIOTECH, color=SECONDARY, size=20),
                ft.Text("Kết quả phân tích AI", size=15, weight=ft.FontWeight.W_700),
            ],
        ),
        content=ft.Column(
            scroll=ft.ScrollMode.AUTO,
            width=340,
            spacing=10,
            controls=[
                annotated_ctrl,
                ft.Text(f"Model: {model_name}", size=10, color=ft.Colors.WHITE38),
                ft.Divider(height=1, color=ft.Colors.with_opacity(0.15, ft.Colors.WHITE)),
                ft.Text("Kết quả phát hiện bệnh:", size=13, weight=ft.FontWeight.W_600),
                *disease_rows,
                ft.Divider(height=1, color=ft.Colors.with_opacity(0.15, ft.Colors.WHITE)),
                ft.Text("Tư vấn từ AI:", size=13, weight=ft.FontWeight.W_600),
                ft.Row(
                    spacing=8,
                    controls=[
                        ft.ElevatedButton(
                            ref=gemini_btn,
                            text="Tư vấn AI",
                            icon=ft.Icons.SMART_TOY,
                            on_click=_fetch_gemini,
                            style=ft.ButtonStyle(
                                bgcolor=SECONDARY,
                                color=ft.Colors.WHITE,
                                shape=ft.RoundedRectangleBorder(radius=8),
                            ),
                        ),
                        gemini_loading,
                    ],
                ),
                gemini_text,
            ],
        ),
        actions=[
            ft.TextButton("Đóng", on_click=lambda e: _close_dialog(page, dialog)),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    if not page:
        return
    try:
        page.open(dialog)
    except Exception:
        page.dialog = dialog
        dialog.open = True
        _safe_update(page)


def build_ai_bubble(
    page: ft.Page | None,
    msg: dict,
    gemini_key_ref: ft.Ref[ft.TextField],
) -> ft.Control:
    sender = msg.get("sender", "farmer")
    is_me = sender == "farmer"
    is_system = sender == "system"
    ai_result = msg.get("ai_result")

    if is_system:
        align = ft.MainAxisAlignment.START
        bg = ft.Colors.with_opacity(0.16, SECONDARY)
        border_col = ft.Colors.with_opacity(0.25, SECONDARY)
        avatar_color = SECONDARY
        avatar_icon = ft.Icons.SMART_TOY
    elif is_me:
        align = ft.MainAxisAlignment.END
        bg = ft.Colors.with_opacity(0.30, PRIMARY)
        border_col = ft.Colors.with_opacity(0.40, PRIMARY)
        avatar_color = PRIMARY
        avatar_icon = ft.Icons.PERSON
    else:
        align = ft.MainAxisAlignment.START
        bg = ft.Colors.with_opacity(0.16, ft.Colors.WHITE)
        border_col = ft.Colors.with_opacity(0.18, ft.Colors.WHITE)
        avatar_color = SECONDARY
        avatar_icon = ft.Icons.SUPPORT_AGENT

    inner: list[ft.Control] = []

    if msg.get("img_src"):
        inner.append(
            ft.Image(src=msg["img_src"], width=200, border_radius=10, fit=ft.ImageFit.COVER)
        )

    if msg.get("file_name"):
        inner.append(
            ft.Container(
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                border_radius=8,
                bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.WHITE),
                content=ft.Row(
                    tight=True,
                    spacing=6,
                    controls=[
                        ft.Icon(ft.Icons.INSERT_DRIVE_FILE, size=16, color=SECONDARY),
                        ft.Text(
                            msg["file_name"],
                            size=12,
                            color=ft.Colors.WHITE,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            expand=True,
                        ),
                    ],
                ),
            )
        )

    if msg.get("text"):
        inner.append(ft.Text(msg["text"], size=13, color=ft.Colors.WHITE, selectable=True))

    if ai_result:
        detected = ai_result.get("diagnosis", {}).get("detected", [])
        chips: list[ft.Control] = []
        if detected:
            for item in detected[:4]:
                chips.append(
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=7, vertical=3),
                        border_radius=12,
                        bgcolor=ft.Colors.with_opacity(0.22, ft.Colors.RED_400),
                        border=ft.border.all(1, ft.Colors.with_opacity(0.40, ft.Colors.RED_300)),
                        content=ft.Row(
                            tight=True,
                            spacing=4,
                            controls=[
                                ft.Icon(ft.Icons.CORONAVIRUS, size=10, color=ft.Colors.RED_300),
                                ft.Text(item["class"], size=10, color=ft.Colors.WHITE),
                            ],
                        ),
                    )
                )
        else:
            chips.append(
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=7, vertical=3),
                    border_radius=12,
                    bgcolor=ft.Colors.with_opacity(0.18, ft.Colors.GREEN_400),
                    content=ft.Text("Không phát hiện bệnh", size=10, color=ft.Colors.GREEN_300),
                )
            )
        inner.append(ft.Row(wrap=True, spacing=4, run_spacing=4, controls=chips))
        inner.append(
            ft.TextButton(
                "Xem chi tiết",
                icon=ft.Icons.INFO_OUTLINE,
                style=ft.ButtonStyle(color=SECONDARY),
                on_click=lambda e: open_ai_detail_dialog(page, gemini_key_ref, ai_result),
            )
        )

    inner.append(
        ft.Text(
            msg["time"],
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
        bgcolor=bg,
        border=ft.border.all(1, border_col),
        content=ft.Column(spacing=4, tight=True, controls=inner),
    )

    avatar = ft.Container(
        width=30,
        height=30,
        border_radius=15,
        bgcolor=ft.Colors.with_opacity(0.20, avatar_color),
        alignment=ft.alignment.center,
        content=ft.Icon(avatar_icon, size=16, color=avatar_color),
    )

    row_controls = [bubble, avatar] if is_me else [avatar, bubble]
    return ft.Row(
        alignment=align,
        vertical_alignment=ft.CrossAxisAlignment.END,
        spacing=6,
        controls=row_controls,
    )


def build_attach_button(icon, tip, color, on_click):
    return ft.IconButton(
        icon=icon,
        icon_color=color,
        icon_size=22,
        tooltip=tip,
        on_click=on_click,
    )
