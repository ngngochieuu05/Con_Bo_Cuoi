from __future__ import annotations

import flet as ft

from bll.admin.model_management import (
    list_models as get_all_models,
    update_model_config,
    update_model_status,
)
from ui.theme import DANGER, PRIMARY, SECONDARY, WARNING, button_style, status_badge

MODEL_META = {
    "cattle_detect": ("Nhan dien bo", ft.Icons.PETS, PRIMARY),
    "behavior": ("Hanh vi bo", ft.Icons.DIRECTIONS_RUN, SECONDARY),
}


def build_model_controls(role: str, on_refresh) -> list[ft.Control]:
    if role not in ("farmer", "expert"):
        return []

    user_models = [m for m in get_all_models() if m.get("loai_mo_hinh") in MODEL_META]
    if not user_models:
        return []

    blocks: list[ft.Control] = [
        ft.Divider(color=ft.Colors.with_opacity(0.10, ft.Colors.WHITE), height=1),
        ft.Row(
            tight=True,
            spacing=5,
            controls=[
                ft.Icon(ft.Icons.TUNE, size=12, color=ft.Colors.WHITE54),
                ft.Text(
                    "Cau hinh Model YOLO",
                    size=11,
                    weight=ft.FontWeight.W_600,
                    color=ft.Colors.WHITE70,
                ),
            ],
        ),
    ]

    for model in user_models:
        model_type = model.get("loai_mo_hinh")
        model_id = model["id_model"]
        name, icon, accent = MODEL_META[model_type]
        conf_v = float(model.get("conf", 0.50))
        iou_v = float(model.get("iou", 0.45))
        path_v = model.get("duong_dan_file", "")
        status_key = model.get("trang_thai", "offline")
        slider_values = {"conf": conf_v, "iou": iou_v}

        lbl_conf = ft.Text(
            f"{conf_v:.2f}",
            size=11,
            weight=ft.FontWeight.W_700,
            color=accent,
            width=34,
        )
        lbl_iou = ft.Text(
            f"{iou_v:.2f}",
            size=11,
            weight=ft.FontWeight.W_700,
            color=SECONDARY,
            width=34,
        )

        def _chg_conf(e, values=slider_values, label=lbl_conf):
            values["conf"] = round(float(e.control.value), 2)
            label.value = f"{values['conf']:.2f}"
            label.update()

        def _chg_iou(e, values=slider_values, label=lbl_iou):
            values["iou"] = round(float(e.control.value), 2)
            label.value = f"{values['iou']:.2f}"
            label.update()

        path_field = ft.TextField(
            value=path_v,
            label="File .pt",
            hint_text=f"models/{model_type}.pt",
            prefix_icon=ft.Icons.FOLDER_OPEN,
            border_radius=8,
            expand=True,
            bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.WHITE),
            border_color=ft.Colors.with_opacity(0.18, ft.Colors.WHITE),
            focused_border_color=accent,
            label_style=ft.TextStyle(color=ft.Colors.WHITE54, size=10),
            text_style=ft.TextStyle(color=ft.Colors.WHITE, size=11),
            cursor_color=ft.Colors.WHITE,
            content_padding=ft.padding.symmetric(horizontal=8, vertical=5),
        )
        save_label = ft.Text("", size=10, color=ft.Colors.GREEN_300)

        def _copy_path(e, field=path_field, label=save_label):
            value = (field.value or "").strip()
            if value and e.page:
                e.page.set_clipboard(value)
                label.value = "Da sao chep!"
                label.color = ft.Colors.CYAN_300
                label.update()

        def _paste_path(e, field=path_field, label=save_label):
            async def _do(e=e, field=field, label=label):
                try:
                    clip = await e.page.get_clipboard_async()
                except Exception:
                    return
                if not clip:
                    return
                field.value = clip.strip()
                field.update()
                label.value = "Da dan!"
                label.color = ft.Colors.GREEN_300
                label.update()

            e.page.run_task(_do)

        def _save_model(e, current_model_id=model_id, values=slider_values, field=path_field, label=save_label):
            path = (field.value or "").strip()
            if path and not path.endswith(".pt"):
                label.value = "Phai la .pt"
                label.color = ft.Colors.AMBER_300
                label.update()
                return
            update_model_config(current_model_id, values["conf"], values["iou"], path)
            label.value = "Da luu"
            label.color = ft.Colors.GREEN_300
            label.update()

        def _toggle_status(e, current_model_id=model_id, current_status=status_key):
            new_status = "online" if current_status in ("offline", "testing") else "offline"
            update_model_status(current_model_id, new_status)
            on_refresh()

        status_label = "Dang chay" if status_key == "online" else "Ngoai tuyen"
        status_kind = "primary" if status_key == "online" else "danger"
        toggle_label = "Tat" if status_key == "online" else "Bat"
        toggle_color = DANGER if status_key == "online" else PRIMARY

        blocks.append(
            ft.Container(
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
                border_radius=10,
                bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
                border=ft.border.all(1, ft.Colors.with_opacity(0.12, accent)),
                content=ft.Column(
                    spacing=5,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Row(
                                    tight=True,
                                    spacing=5,
                                    controls=[
                                        ft.Icon(icon, size=13, color=accent),
                                        ft.Text(
                                            name,
                                            size=12,
                                            weight=ft.FontWeight.W_600,
                                            color=accent,
                                        ),
                                    ],
                                ),
                                ft.Row(
                                    tight=True,
                                    spacing=4,
                                    controls=[
                                        status_badge(status_label, status_kind),
                                        ft.TextButton(
                                            toggle_label,
                                            style=ft.ButtonStyle(color=toggle_color),
                                            on_click=_toggle_status,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text("conf", size=10, color=ft.Colors.WHITE54),
                                lbl_conf,
                            ],
                        ),
                        ft.Slider(
                            value=conf_v,
                            min=0.05,
                            max=0.95,
                            divisions=18,
                            active_color=accent,
                            inactive_color=ft.Colors.with_opacity(0.15, ft.Colors.WHITE),
                            thumb_color=accent,
                            expand=True,
                            on_change=_chg_conf,
                        ),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text("iou", size=10, color=ft.Colors.WHITE54),
                                lbl_iou,
                            ],
                        ),
                        ft.Slider(
                            value=iou_v,
                            min=0.05,
                            max=0.95,
                            divisions=18,
                            active_color=SECONDARY,
                            inactive_color=ft.Colors.with_opacity(0.15, ft.Colors.WHITE),
                            thumb_color=SECONDARY,
                            expand=True,
                            on_change=_chg_iou,
                        ),
                        ft.Row(
                            spacing=4,
                            controls=[
                                path_field,
                                ft.IconButton(
                                    ft.Icons.COPY,
                                    icon_size=16,
                                    tooltip="Sao chep duong dan",
                                    icon_color=ft.Colors.WHITE54,
                                    on_click=_copy_path,
                                ),
                                ft.IconButton(
                                    ft.Icons.CONTENT_PASTE,
                                    icon_size=16,
                                    tooltip="Dan duong dan",
                                    icon_color=ft.Colors.WHITE54,
                                    on_click=_paste_path,
                                ),
                            ],
                        ),
                        ft.Row(
                            spacing=6,
                            controls=[
                                ft.ElevatedButton(
                                    "Luu",
                                    icon=ft.Icons.SAVE,
                                    style=button_style("primary"),
                                    height=28,
                                    on_click=_save_model,
                                ),
                                save_label,
                            ],
                        ),
                    ],
                ),
            )
        )

    return blocks
