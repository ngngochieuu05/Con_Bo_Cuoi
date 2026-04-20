"""Train management screen."""
from __future__ import annotations

import flet as ft

from bll.admin.train_management import check_ultralytics, is_training
from ui.theme import WARNING, button_style, glass_container, section_title

from .train_management_actions import (
    create_apply_model_handler,
    create_install_ultra_handler,
    create_start_handler,
    create_stop_handler,
)
from .train_management_form import (
    TRAIN_PURPLE2,
    TRAIN_SUCCESS,
    build_train_config_panel,
    build_train_form_controls,
)
from .train_management_runtime import (
    TrainRuntimeController,
    build_log_area,
    build_progress_box,
)


def build_train_management():
    form = build_train_form_controls()
    runtime = TrainRuntimeController()

    on_start = create_start_handler(form, runtime)
    on_stop = create_stop_handler(runtime)
    on_apply_model = create_apply_model_handler(runtime)
    on_install_ultra = create_install_ultra_handler(runtime)

    config_panel = build_train_config_panel(
        form,
        ultra_status=runtime.ultra_status,
        on_install_ultra=on_install_ultra,
    )

    btn_start = ft.ElevatedButton(
        ref=runtime.start_btn_ref,
        text="Bat dau Train",
        icon=ft.Icons.PLAY_ARROW,
        style=button_style("primary"),
        height=40,
        expand=True,
        on_click=on_start,
    )
    btn_stop = ft.ElevatedButton(
        ref=runtime.stop_btn_ref,
        text="Dung",
        icon=ft.Icons.STOP,
        style=button_style("danger"),
        height=40,
        disabled=True,
        on_click=on_stop,
    )
    btn_apply = ft.ElevatedButton(
        ref=runtime.apply_btn_ref,
        text="Ap dung model vao he thong",
        icon=ft.Icons.PUBLISHED_WITH_CHANGES,
        style=button_style("secondary"),
        height=38,
        disabled=True,
        on_click=on_apply_model,
    )

    progress_box = build_progress_box(runtime, runtime.clear_log)
    log_area = build_log_area(runtime)
    result_row = ft.Container(
        ref=runtime.result_row_ref,
        visible=False,
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        border_radius=10,
        bgcolor=ft.Colors.with_opacity(0.14, TRAIN_SUCCESS),
        border=ft.border.all(1, ft.Colors.with_opacity(0.35, TRAIN_SUCCESS)),
        content=ft.Column(
            spacing=6,
            controls=[runtime.result_path_txt, btn_apply],
        ),
    )

    runtime.start_ultralytics_check(check_ultralytics)
    if is_training():
        runtime.set_training_state(True)
        runtime.set_status("Dang train...", WARNING)
        runtime.start_polling()

    return ft.Column(
        expand=True,
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(
                        tight=True,
                        spacing=1,
                        controls=[
                            ft.Text(
                                "Huan luyen mo hinh",
                                size=20,
                                weight=ft.FontWeight.W_700,
                            ),
                            ft.Text(
                                "YOLOv8 · Phat hien benh bo · Chi Admin",
                                size=11,
                                color=ft.Colors.WHITE54,
                            ),
                        ],
                    ),
                    ft.Icon(
                        ft.Icons.MODEL_TRAINING,
                        color=ft.Colors.with_opacity(0.3, TRAIN_PURPLE2),
                        size=28,
                    ),
                ],
            ),
            ft.Container(
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                border_radius=12,
                bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.AMBER),
                border=ft.border.all(1, ft.Colors.with_opacity(0.25, ft.Colors.AMBER)),
                content=ft.Row(
                    tight=True,
                    spacing=8,
                    controls=[
                        ft.Icon(ft.Icons.INFO_OUTLINE, size=14, color=ft.Colors.AMBER_200),
                        ft.Text(
                            "Qua trinh train chay ngam. Ket qua luu vao models/runs/. "
                            "Sau khi train xong, nhan 'Ap dung' de cap nhat model disease vao he thong.",
                            size=11,
                            color=ft.Colors.AMBER_100,
                            expand=True,
                        ),
                    ],
                ),
            ),
            glass_container(padding=14, radius=16, content=config_panel),
            ft.Row(spacing=8, controls=[btn_start, btn_stop]),
            glass_container(padding=14, radius=16, content=progress_box),
            result_row,
            glass_container(
                padding=0,
                radius=16,
                content=ft.Column(
                    spacing=0,
                    controls=[
                        ft.Container(
                            padding=ft.padding.symmetric(horizontal=14, vertical=10),
                            content=ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[section_title("TERMINAL", "Training Log")],
                            ),
                        ),
                        ft.Container(
                            height=280,
                            bgcolor=ft.Colors.with_opacity(0.35, ft.Colors.BLACK),
                            border_radius=ft.border_radius.only(
                                bottom_left=16,
                                bottom_right=16,
                            ),
                            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                            content=log_area,
                        ),
                    ],
                ),
            ),
        ],
    )
