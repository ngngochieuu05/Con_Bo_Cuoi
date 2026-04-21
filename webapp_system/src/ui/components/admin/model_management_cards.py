from __future__ import annotations

from pathlib import Path

import flet as ft

from bll.admin.model_management import (
    promote_model,
    resolve_model_path,
    set_model_testing,
    update_model,
    update_model_status,
)
from ui.theme import (
    PRIMARY,
    WARNING,
    button_style,
    fmt_dt,
    inline_field,
    open_bottom_sheet,
    overflow_action_button,
    severity_badge,
    status_badge,
)

TYPE_META = {
    "cattle_detect": {"label": "Nhan dien bo", "icon": ft.Icons.PETS, "accent": PRIMARY},
    "behavior": {"label": "Hanh vi bo", "icon": ft.Icons.DIRECTIONS_RUN, "accent": ft.Colors.CYAN_300},
    "disease": {"label": "Benh tren bo", "icon": ft.Icons.MEDICAL_SERVICES, "accent": WARNING},
    "custom": {"label": "Tuy chinh", "icon": ft.Icons.SMART_TOY, "accent": ft.Colors.WHITE70},
}

STATUS_META = {
    "online": ("Production", "primary"),
    "testing": ("Testing", "warning"),
    "offline": ("Offline", "neutral"),
}


def build_model_card(model: dict, all_models: list[dict], on_refresh) -> ft.Control:
    model_type = model.get("loai_mo_hinh", "custom")
    meta = TYPE_META.get(model_type, TYPE_META["custom"])
    model_id = int(model.get("id_model") or 0)
    path_value = str(model.get("duong_dan_file", "") or "").strip()
    resolved_path = resolve_model_path(path_value)
    path_exists = bool(resolved_path and Path(resolved_path).exists())
    replace_target = next(
        (
            item for item in all_models
            if item.get("loai_mo_hinh") == model_type
            and item.get("trang_thai") == "online"
            and int(item.get("id_model") or 0) != model_id
        ),
        None,
    )
    status_label, status_kind = STATUS_META.get(model.get("trang_thai", "offline"), ("Offline", "neutral"))

    def _open_actions(e):
        if not e.page:
            return
        version_field = inline_field("Version", ft.Icons.TAG, value=str(model.get("phien_ban", "")), expand=True)
        path_field = inline_field("Model .pt path", ft.Icons.FOLDER_OPEN, value=path_value, expand=True)
        conf_field = inline_field("conf", ft.Icons.TUNE, value=f"{float(model.get('conf', 0.5)):.2f}", expand=1)
        iou_field = inline_field("iou", ft.Icons.FILTER_ALT, value=f"{float(model.get('iou', 0.45)):.2f}", expand=1)
        feedback = ft.Text("", size=11, color=ft.Colors.WHITE70)

        def _set_feedback(text: str, color) -> None:
            feedback.value = text
            feedback.color = color
            if feedback.page:
                feedback.update()

        def _save_config(_):
            path = (path_field.value or "").strip()
            if path and not path.endswith(".pt"):
                _set_feedback("Path model phai ket thuc bang .pt", ft.Colors.RED_300)
                return
            try:
                conf_value = round(float(conf_field.value or 0.5), 3)
                iou_value = round(float(iou_field.value or 0.45), 3)
            except ValueError:
                _set_feedback("conf / iou phai la so hop le", ft.Colors.RED_300)
                return
            update_model(
                model_id,
                {
                    "phien_ban": (version_field.value or "").strip() or str(model.get("phien_ban", "")),
                    "duong_dan_file": path,
                    "conf": conf_value,
                    "iou": iou_value,
                },
            )
            _set_feedback("Da luu config model.", ft.Colors.GREEN_300)
            on_refresh()

        def _mark_testing(_):
            success, message = set_model_testing(model_id)
            _set_feedback(message, ft.Colors.GREEN_300 if success else ft.Colors.RED_300)
            on_refresh()

        def _apply_production(_):
            success, message = promote_model(model_id)
            _set_feedback(message, ft.Colors.GREEN_300 if success else ft.Colors.RED_300)
            on_refresh()

        def _disable(_):
            result = update_model_status(model_id, "offline")
            _set_feedback(
                "Da dua model ve offline." if result else "Khong the cap nhat model.",
                ft.Colors.GREEN_300 if result else ft.Colors.RED_300,
            )
            on_refresh()

        open_bottom_sheet(
            e.page,
            model.get("ten_mo_hinh", "Model detail"),
            ft.Column(
                spacing=10,
                controls=[
                    ft.Row(
                        spacing=8,
                        wrap=True,
                        controls=[
                            status_badge(status_label, status_kind),
                            status_badge(meta["label"], "secondary"),
                            severity_badge("high" if model.get("trang_thai") == "online" else "medium"),
                        ],
                    ),
                    ft.Text(model.get("mo_ta", "Chua co mo ta."), size=11, color=ft.Colors.WHITE70),
                    ft.Text(
                        f"Cap nhat: {fmt_dt(model.get('updated_at', ''))}",
                        size=10,
                        color=ft.Colors.WHITE54,
                    ),
                    ft.Text(
                        f"Resolved path: {resolved_path or 'Chua co'}",
                        size=10,
                        color=ft.Colors.GREEN_300 if path_exists else ft.Colors.AMBER_200,
                    ),
                    ft.Text(
                        (
                            f"Apply se thay model dang online: {replace_target.get('ten_mo_hinh')}"
                            if replace_target else
                            "Khong co model online cung loai dang bi thay the."
                        ),
                        size=10,
                        color=ft.Colors.WHITE60,
                    ),
                    version_field,
                    path_field,
                    ft.Row(spacing=8, controls=[conf_field, iou_field]),
                    ft.Row(
                        spacing=8,
                        wrap=True,
                        controls=[
                            ft.ElevatedButton("Save config", icon=ft.Icons.SAVE, style=button_style("primary"), on_click=_save_config),
                            ft.ElevatedButton("Mark testing", icon=ft.Icons.SCIENCE, style=button_style("secondary"), on_click=_mark_testing),
                            ft.ElevatedButton("Apply production", icon=ft.Icons.VERIFIED, style=button_style("warning"), on_click=_apply_production),
                            ft.ElevatedButton("Disable", icon=ft.Icons.POWER_SETTINGS_NEW, style=button_style("danger"), on_click=_disable),
                        ],
                    ),
                    feedback,
                ],
            ),
        )

    return ft.Container(
        border_radius=18,
        padding=14,
        bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.WHITE),
        border=ft.border.all(1, ft.Colors.with_opacity(0.14, ft.Colors.WHITE)),
        content=ft.Column(
            spacing=8,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(
                            spacing=10,
                            controls=[
                                ft.Container(
                                    width=40,
                                    height=40,
                                    border_radius=12,
                                    bgcolor=ft.Colors.with_opacity(0.18, meta["accent"]),
                                    alignment=ft.alignment.center,
                                    content=ft.Icon(meta["icon"], size=18, color=meta["accent"]),
                                ),
                                ft.Column(
                                    tight=True,
                                    spacing=2,
                                    controls=[
                                        ft.Text(model.get("ten_mo_hinh", "Model"), size=14, weight=ft.FontWeight.W_700),
                                        ft.Text(str(model.get("phien_ban", "v0.0.0")), size=11, color=ft.Colors.WHITE60),
                                    ],
                                ),
                            ],
                        ),
                        overflow_action_button([("Mo workflow", "OPEN_IN_NEW", _open_actions)]),
                    ],
                ),
                ft.Row(
                    spacing=8,
                    wrap=True,
                    controls=[
                        status_badge(status_label, status_kind),
                        status_badge(meta["label"], "secondary"),
                        status_badge("Path OK" if path_exists else "Path missing", "success" if path_exists else "danger"),
                    ],
                ),
                ft.Text(model.get("mo_ta", "Chua co mo ta."), size=11, color=ft.Colors.WHITE70, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Row(
                    spacing=12,
                    wrap=True,
                    controls=[
                        ft.Text(f"conf {float(model.get('conf', 0.5)):.2f}", size=10, color=meta["accent"]),
                        ft.Text(f"iou {float(model.get('iou', 0.45)):.2f}", size=10, color=ft.Colors.WHITE70),
                        ft.Text(f"Updated {fmt_dt(model.get('updated_at', ''))}", size=10, color=ft.Colors.WHITE54),
                    ],
                ),
                ft.Text(
                    resolved_path or "Chua co duong dan model",
                    size=10,
                    color=ft.Colors.GREEN_300 if path_exists else ft.Colors.AMBER_200,
                    max_lines=2,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            ],
        ),
    )
