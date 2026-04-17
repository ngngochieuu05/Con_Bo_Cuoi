"""
Expert — AI result panel and chat bubble widgets.
Extracted from consulting_chat.py for 200-line compliance.
"""
import flet as ft

_TEAL = ft.Colors.TEAL_300


def build_ai_result_panel(result: dict) -> ft.Control:
    diag = result.get("diagnosis", {})
    detected = diag.get("detected", [])
    chips = [
        ft.Container(
            padding=ft.padding.symmetric(horizontal=8, vertical=3), border_radius=8,
            bgcolor=ft.Colors.with_opacity(
                0.22, ft.Colors.RED_400 if d["confidence"] > 0.5 else ft.Colors.AMBER_400
            ),
            content=ft.Text(
                f"{d['class']} {d['confidence']:.0%}", size=10,
                color=ft.Colors.WHITE, weight=ft.FontWeight.W_600,
            ),
        ) for d in detected
    ] or [ft.Text("Không phát hiện bệnh", size=11, color=ft.Colors.GREEN_300)]

    ctrls: list[ft.Control] = [
        ft.Text("Kết quả AI", size=11, weight=ft.FontWeight.W_700, color=_TEAL)
    ]
    if result.get("annotated_b64"):
        ctrls.append(ft.Image(src_base64=result["annotated_b64"], width=220,
                              border_radius=8, fit=ft.ImageFit.CONTAIN))
    ctrls.append(ft.Row(wrap=True, spacing=4, run_spacing=4, controls=chips))
    return ft.Container(
        margin=ft.margin.only(top=4), padding=ft.padding.all(8), border_radius=10,
        bgcolor=ft.Colors.with_opacity(0.12, _TEAL),
        border=ft.border.all(1, ft.Colors.with_opacity(0.25, _TEAL)),
        content=ft.Column(tight=True, spacing=6, controls=ctrls),
    )


def build_chat_bubble(msg: dict, on_analyze=None) -> ft.Control:
    is_me = msg.get("sender") == "expert"
    bg = ft.Colors.with_opacity(0.28 if is_me else 0.18, _TEAL if is_me else ft.Colors.WHITE)
    border_col = ft.Colors.with_opacity(0.40 if is_me else 0.20, _TEAL if is_me else ft.Colors.WHITE)
    av_color = _TEAL if is_me else ft.Colors.BLUE_300

    result_ctr = ft.Container(visible=False)
    inner: list[ft.Control] = []

    if msg.get("img_src"):
        inner.append(ft.Image(src=msg["img_src"], width=180, border_radius=10, fit=ft.ImageFit.COVER))
        if on_analyze:
            inner.append(ft.TextButton(
                "Phân tích AI", icon=ft.Icons.BIOTECH,
                style=ft.ButtonStyle(color=_TEAL),
                on_click=lambda e: on_analyze(msg["img_src"], result_ctr),
            ))
        inner.append(result_ctr)
    if msg.get("text"):
        inner.append(ft.Text(msg["text"], size=13, color=ft.Colors.WHITE, selectable=True))
    inner.append(ft.Text(
        msg.get("time", ""), size=9, color=ft.Colors.WHITE38,
        text_align=ft.TextAlign.RIGHT if is_me else ft.TextAlign.LEFT,
    ))

    bubble = ft.Container(
        width=270, padding=ft.padding.symmetric(horizontal=12, vertical=8),
        border_radius=ft.border_radius.only(
            top_left=16, top_right=16,
            bottom_left=4 if is_me else 16, bottom_right=16 if is_me else 4,
        ),
        bgcolor=bg, border=ft.border.all(1, border_col),
        content=ft.Column(spacing=4, tight=True, controls=inner),
    )
    avatar = ft.Container(
        width=28, height=28, border_radius=14,
        bgcolor=ft.Colors.with_opacity(0.20, av_color), alignment=ft.alignment.center,
        content=ft.Icon(
            ft.Icons.SUPPORT_AGENT if is_me else ft.Icons.PERSON, size=14, color=av_color
        ),
    )
    row_ctrls = [bubble, avatar] if is_me else [avatar, bubble]
    return ft.Row(
        alignment=ft.MainAxisAlignment.END if is_me else ft.MainAxisAlignment.START,
        vertical_alignment=ft.CrossAxisAlignment.END, spacing=6, controls=row_ctrls,
    )
