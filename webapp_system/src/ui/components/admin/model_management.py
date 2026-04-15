"""
Quan ly 3 mo hinh YOLO doc lap: Nhan dien bo, Hanh vi bo, Benh tren bo.
Moi mo hinh co cau hinh rieng: conf, IOU, duong dan file .pt
"""
from __future__ import annotations
import flet as ft
from ui.theme import (
    PRIMARY, WARNING, DANGER, SECONDARY,
    glass_container, status_badge, button_style,
    inline_field, section_title, empty_state, fmt_dt,
)
from dal.model_repo import (
    get_all_models, update_model_status, update_model_config, update_model,
)

_LOAI_LABEL = {
    "cattle_detect": ("Nhận diện bò",  ft.Icons.PETS,              PRIMARY),
    "behavior":      ("Hành vi bò",    ft.Icons.DIRECTIONS_RUN,    SECONDARY),
    "disease":       ("Bệnh trên bò",  ft.Icons.MEDICAL_SERVICES,  WARNING),
    "custom":        ("Tùy chỉnh",     ft.Icons.SMART_TOY,         ft.Colors.WHITE54),
}

_STATUS_MAP = {
    "online":  ("Đang chạy",   "primary", ft.Icons.PLAY_CIRCLE),
    "testing": ("Thử nghiệm",  "warning", ft.Icons.SCIENCE),
    "offline": ("Ngoại tuyến", "danger",  ft.Icons.PAUSE_CIRCLE),
}


def _yolo_slider(label: str, value: float, accent, on_change) -> ft.Column:
    """Slider YOLO voi mau sac theo loai mo hinh."""
    val_text = ft.Text(
        f"{value:.2f}", size=13, weight=ft.FontWeight.W_700,
        color=accent, width=40,
    )

    def _changed(e):
        val_text.value = f"{float(e.control.value):.2f}"
        val_text.update()
        on_change(float(e.control.value))

    slider = ft.Slider(
        value=value, min=0.05, max=0.95, divisions=18,
        label="{value:.2f}",
        active_color=accent,
        inactive_color=ft.Colors.with_opacity(0.18, ft.Colors.WHITE),
        thumb_color=accent,
        expand=True,
        on_change=_changed,
    )
    return ft.Column(
        spacing=2,
        controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(label, size=11, color=ft.Colors.WHITE70),
                    val_text,
                ],
            ),
            ft.Row(spacing=0, controls=[slider]),
        ],
    )


def _model_card(m: dict, on_refresh) -> ft.Control:
    mid      = m.get("id_model")
    name     = m.get("ten_mo_hinh", "Mô hình AI")
    version  = m.get("phien_ban", "v0.0.0")
    desc     = m.get("mo_ta", "")
    st_key   = m.get("trang_thai", "offline")
    loai     = m.get("loai_mo_hinh", "custom")
    conf_val = float(m.get("conf", 0.50))
    iou_val  = float(m.get("iou", 0.45))
    pt_path  = m.get("duong_dan_file", "")

    loai_label, loai_icon, loai_color = _LOAI_LABEL.get(loai, _LOAI_LABEL["custom"])
    st_label, st_kind, _ = _STATUS_MAP.get(st_key, ("Không rõ", "warning", None))

    cfg_panel_ref = ft.Ref[ft.Container]()
    save_msg      = ft.Text("", size=11, color=ft.Colors.GREEN_300)
    _state        = {"conf": conf_val, "iou": iou_val}

    pt_field = ft.TextField(
        value=pt_path,
        label="Đường dẫn file .pt",
        hint_text="models/Dataset/model.pt",
        prefix_icon=ft.Icons.FOLDER_OPEN,
        border_radius=12, expand=True,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.28, ft.Colors.WHITE),
        focused_border_color=loai_color,
        label_style=ft.TextStyle(color=ft.Colors.WHITE70, size=12),
        text_style=ft.TextStyle(color=ft.Colors.WHITE, size=12),
        cursor_color=ft.Colors.WHITE,
        content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
    )

    ver_field = ft.TextField(
        value=version, label="Phiên bản",
        border_radius=12, width=90,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.28, ft.Colors.WHITE),
        focused_border_color=loai_color,
        label_style=ft.TextStyle(color=ft.Colors.WHITE70, size=12),
        text_style=ft.TextStyle(color=ft.Colors.WHITE, size=12),
        cursor_color=ft.Colors.WHITE,
        content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
    )

    def _toggle(e):
        new_st = "online" if st_key in ("offline", "testing") else "offline"
        update_model_status(mid, new_st)
        on_refresh()

    def _save_cfg(e):
        path = (pt_field.value or "").strip()
        if path and not path.endswith(".pt"):
            save_msg.value = "File phải có đuôi .pt"
            save_msg.color = ft.Colors.AMBER_300
            save_msg.update()
            return
        update_model_config(mid, _state["conf"], _state["iou"], path)
        new_ver = (ver_field.value or "v1.0.0").strip()
        if new_ver != version:
            update_model(mid, {"phien_ban": new_ver})
        save_msg.value = "Đã lưu cấu hình"
        save_msg.color = ft.Colors.GREEN_300
        save_msg.update()

    def _toggle_cfg(e):
        p = cfg_panel_ref.current
        p.visible = not p.visible
        p.update()

    conf_slider = _yolo_slider("Confidence (conf)", conf_val, loai_color,
                               lambda v: _state.update({"conf": v}))
    iou_slider  = _yolo_slider("IoU Threshold (iou)", iou_val, SECONDARY,
                               lambda v: _state.update({"iou": v}))

    cfg_panel = ft.Container(
        ref=cfg_panel_ref, visible=False,
        padding=ft.padding.only(top=10),
        content=ft.Column(spacing=10, controls=[
            ft.Divider(color=ft.Colors.with_opacity(0.15, ft.Colors.WHITE), height=1),
            ft.Text(f"Cấu hình YOLO - {name}", size=12,
                    weight=ft.FontWeight.W_600, color=ft.Colors.WHITE70),
            conf_slider,
            iou_slider,
            ft.Row(spacing=8, controls=[pt_field, ver_field]),
            ft.Text(
                "conf: ngưỡng tin cậy (0.05-0.95)  |  iou: độ chồng lấp NMS (0.05-0.95)",
                size=10, color=ft.Colors.WHITE38,
            ),
            ft.Row(spacing=8, controls=[
                ft.ElevatedButton(
                    "Lưu cấu hình", icon=ft.Icons.SAVE,
                    style=button_style("primary"), height=34,
                    on_click=_save_cfg,
                ),
                save_msg,
            ]),
        ]),
    )

    has_pt = bool(pt_path and pt_path.endswith(".pt"))
    pt_indicator = ft.Row(tight=True, spacing=4, controls=[
        ft.Icon(
            ft.Icons.CHECK_CIRCLE if has_pt else ft.Icons.RADIO_BUTTON_UNCHECKED,
            size=12,
            color=ft.Colors.GREEN_300 if has_pt else ft.Colors.WHITE38,
        ),
        ft.Text(
            pt_path.split("/")[-1] if has_pt else "Chưa có file .pt",
            size=10,
            color=ft.Colors.GREEN_300 if has_pt else ft.Colors.WHITE38,
            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
        ),
    ])

    return glass_container(
        padding=14, radius=16,
        content=ft.Column(spacing=6, controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    ft.Row(spacing=10, tight=True, controls=[
                        ft.Container(
                            width=40, height=40, border_radius=14,
                            bgcolor=ft.Colors.with_opacity(0.18, loai_color),
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(loai_icon, size=20, color=loai_color),
                        ),
                        ft.Column(tight=True, spacing=2, controls=[
                            ft.Text(name, size=15, weight=ft.FontWeight.W_700,
                                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(loai_label, size=10, color=ft.Colors.WHITE54),
                        ]),
                    ]),
                    status_badge(st_label, st_kind),
                ],
            ),
            ft.Text(desc, size=11, color=ft.Colors.WHITE60,
                    max_lines=2, overflow=ft.TextOverflow.ELLIPSIS) if desc else ft.Container(height=0),
            pt_indicator,
            ft.Row(spacing=8, tight=True, controls=[
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=8,
                    bgcolor=ft.Colors.with_opacity(0.14, loai_color),
                    content=ft.Row(tight=True, spacing=4, controls=[
                        ft.Text("conf", size=10, color=ft.Colors.WHITE54),
                        ft.Text(f"{conf_val:.2f}", size=12,
                                weight=ft.FontWeight.W_700, color=loai_color),
                    ]),
                ),
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=8,
                    bgcolor=ft.Colors.with_opacity(0.14, SECONDARY),
                    content=ft.Row(tight=True, spacing=4, controls=[
                        ft.Text("iou", size=10, color=ft.Colors.WHITE54),
                        ft.Text(f"{iou_val:.2f}", size=12,
                                weight=ft.FontWeight.W_700, color=SECONDARY),
                    ]),
                ),
                ft.Text(
                    f"Cập nhật: {fmt_dt(m.get('updated_at', ''))}",
                    size=10, color=ft.Colors.WHITE38,
                ),
            ]),
            ft.Row(spacing=6, controls=[
                ft.ElevatedButton(
                    "Bật" if st_key in ("offline", "testing") else "Tắt",
                    icon=ft.Icons.PLAY_ARROW if st_key in ("offline", "testing") else ft.Icons.STOP,
                    style=button_style("primary" if st_key in ("offline", "testing") else "danger"),
                    height=32,
                    on_click=_toggle,
                ),
                ft.OutlinedButton(
                    "Cấu hình YOLO", icon=ft.Icons.TUNE,
                    height=32,
                    style=ft.ButtonStyle(
                        color=ft.Colors.WHITE70,
                        side=ft.BorderSide(1, ft.Colors.WHITE24),
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                    on_click=_toggle_cfg,
                ),
            ]),
            cfg_panel,
        ]),
    )


def build_model_management():
    list_ref = ft.Ref[ft.Column]()

    def refresh():
        all_models = get_all_models()
        models = [m for m in all_models if m.get("loai_mo_hinh") == "disease"]
        cards = (
            [_model_card(m, refresh) for m in models]
            if models else [empty_state("Chưa có mô hình nào")]
        )
        list_ref.current.controls = cards
        if list_ref.current.page:
            list_ref.current.update()

    model_list = ft.Column(ref=list_ref, spacing=10, controls=[])
    refresh()

    return ft.Column(
        expand=True, spacing=12, scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(tight=True, spacing=1, controls=[
                        ft.Text("Mô hình YOLO", size=20, weight=ft.FontWeight.W_700),
                        ft.Text("Nhận diện bò  ·  Hành vi  ·  Bệnh trên bò",
                                size=11, color=ft.Colors.WHITE54),
                    ]),
                    ft.IconButton(
                        ft.Icons.REFRESH, icon_color=ft.Colors.WHITE60,
                        tooltip="Làm mới", on_click=lambda e: refresh(),
                    ),
                ],
            ),
            ft.Container(
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                border_radius=12,
                bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.AMBER),
                border=ft.border.all(1, ft.Colors.with_opacity(0.25, ft.Colors.AMBER)),
                content=ft.Row(tight=True, spacing=8, controls=[
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=14, color=ft.Colors.AMBER_200),
                    ft.Text(
                        "Mỗi mô hình hoạt động độc lập. "
                        "Nhấn 'Cấu hình YOLO' để chỉnh conf, IoU và chọn file .pt",
                        size=11, color=ft.Colors.AMBER_100, expand=True,
                    ),
                ]),
            ),
            model_list,
        ],
    )
