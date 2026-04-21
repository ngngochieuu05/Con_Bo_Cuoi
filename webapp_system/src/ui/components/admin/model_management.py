from __future__ import annotations

import flet as ft

from bll.admin.model_management import list_models as get_all_models
from ui.theme import (
    PRIMARY,
    SECONDARY,
    WARNING,
    empty_state,
    glass_container,
    info_strip,
    inline_field,
    metric_card,
    page_header,
    status_badge,
)

from .model_management_cards import TYPE_META, build_model_card


def _filter_models(models: list[dict], keyword: str, type_filter: str) -> list[dict]:
    needle = (keyword or "").strip().lower()
    filtered = []
    for model in models:
        if type_filter != "all" and model.get("loai_mo_hinh") != type_filter:
            continue
        haystack = " ".join(
            [
                str(model.get("ten_mo_hinh", "")),
                str(model.get("loai_mo_hinh", "")),
                str(model.get("phien_ban", "")),
                str(model.get("mo_ta", "")),
            ]
        ).lower()
        if needle and needle not in haystack:
            continue
        filtered.append(model)
    return filtered


def build_model_management():
    search_field = inline_field("Tim model / version", ft.Icons.SEARCH)
    active_filter = {"value": "all"}
    cards_ref = ft.Ref[ft.Column]()
    chips_ref = ft.Ref[ft.Row]()
    summary_ref = ft.Ref[ft.Row]()
    summary_row = ft.Row(ref=summary_ref, spacing=8, wrap=True, run_spacing=8, controls=[])
    chips_row = ft.Row(
        ref=chips_ref,
        spacing=6,
        scroll=ft.ScrollMode.AUTO,
        controls=[],
    )
    cards_column = ft.Column(ref=cards_ref, spacing=10, controls=[])

    def refresh():
        all_models = get_all_models()
        filtered = _filter_models(all_models, search_field.value or "", active_filter["value"])
        online_count = sum(1 for model in all_models if model.get("trang_thai") == "online")
        testing_count = sum(1 for model in all_models if model.get("trang_thai") == "testing")
        missing_path = sum(1 for model in all_models if not str(model.get("duong_dan_file", "")).strip())

        summary_ref.current.controls = [
            ft.Container(expand=1, content=metric_card("Tong model", str(len(all_models)), ft.Icons.DATA_OBJECT, PRIMARY)),
            ft.Container(expand=1, content=metric_card("Dang production", str(online_count), ft.Icons.VERIFIED, SECONDARY)),
            ft.Container(expand=1, content=metric_card("Dang testing", str(testing_count), ft.Icons.SCIENCE, WARNING)),
            ft.Container(expand=1, content=metric_card("Thieu path", str(missing_path), ft.Icons.FOLDER_OFF, ft.Colors.RED_300)),
        ]
        cards_ref.current.controls = (
            [build_model_card(model, all_models, refresh) for model in filtered]
            if filtered
            else [empty_state("Khong co model khop bo loc hien tai")]
        )
        if summary_ref.current.page:
            summary_ref.current.update()
        if cards_ref.current.page:
            cards_ref.current.update()

    def _set_filter(filter_key: str):
        active_filter["value"] = filter_key
        chips_ref.current.controls = _build_type_chips(active_filter["value"], _set_filter)
        if chips_ref.current.page:
            chips_ref.current.update()
        refresh()

    refresh_button = ft.IconButton(
        ft.Icons.REFRESH,
        tooltip="Lam moi",
        on_click=lambda e: refresh(),
    )
    chips_row.controls = _build_type_chips(active_filter["value"], _set_filter)
    refresh()

    return ft.Column(
        expand=True,
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            page_header(
                "Model registry",
                "Quan ly candidate, testing va production cho tat ca model AI.",
                icon_name="DATA_OBJECT",
                actions=[refresh_button],
            ),
            info_strip(
                "Apply to production se dua model cung loai dang online ve offline. "
                "Rollback hien tai duoc thuc hien bang cach apply lai model truoc do, khong co lich su an.",
                tone="warning",
            ),
            summary_row,
            glass_container(
                padding=12,
                radius=16,
                content=ft.Column(
                    spacing=10,
                    controls=[
                        ft.Row(
                            spacing=8,
                            controls=[
                                search_field,
                                ft.IconButton(
                                    ft.Icons.SEARCH,
                                    icon_color=ft.Colors.WHITE70,
                                    on_click=lambda e: refresh(),
                                ),
                            ],
                        ),
                        chips_row,
                        ft.Row(
                            spacing=8,
                            wrap=True,
                            controls=[
                                status_badge("Online = production", "primary"),
                                status_badge("Testing = candidate", "warning"),
                                status_badge("Offline = disabled", "neutral"),
                            ],
                        ),
                    ],
                ),
            ),
            cards_column,
        ],
    )


def _build_type_chips(active: str, on_click) -> list[ft.Control]:
    def _chip(key: str, label: str) -> ft.Control:
        selected = active == key
        return ft.Container(
            ink=True,
            on_click=lambda e, value=key: on_click(value),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=999,
            bgcolor=ft.Colors.with_opacity(0.26, PRIMARY if selected else ft.Colors.WHITE),
            border=ft.border.all(
                1,
                ft.Colors.with_opacity(0.42, PRIMARY if selected else ft.Colors.WHITE),
            ),
            content=ft.Text(
                label,
                size=11,
                weight=ft.FontWeight.W_600 if selected else ft.FontWeight.W_400,
                color=ft.Colors.WHITE if selected else ft.Colors.WHITE70,
            ),
        )

    controls = [_chip("all", "Tat ca")]
    for model_type, meta in TYPE_META.items():
        controls.append(_chip(model_type, meta["label"]))
    return controls
