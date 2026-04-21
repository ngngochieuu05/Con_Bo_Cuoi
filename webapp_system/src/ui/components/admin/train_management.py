"""Train management screen."""
from __future__ import annotations

import flet as ft

from bll.admin.train_management import check_ultralytics, is_training
from ui.theme import WARNING, button_style, collapsible_section, glass_container

from .train_management_actions import (
    create_apply_model_handler,
    create_install_ultra_handler,
    create_start_handler,
    create_stop_handler,
)
from .train_management_form import (
    TRAIN_PURPLE2,
    TRAIN_SUCCESS,
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
    wizard_state = {"step": 0}
    step_content_ref = ft.Ref[ft.Column]()
    back_btn_ref = ft.Ref[ft.OutlinedButton]()
    next_btn_ref = ft.Ref[ft.OutlinedButton]()
    wizard_note = ft.Text("Buoc 1/3: Chon du lieu va thu muc output", size=11, color=ft.Colors.WHITE60)

    on_start = create_start_handler(form, runtime)
    on_stop = create_stop_handler(runtime)
    on_apply_model = create_apply_model_handler(runtime)
    on_install_ultra = create_install_ultra_handler(runtime)

    def _step_controls(step: int) -> list[ft.Control]:
        if step == 0:
            return [
                ft.Text("Buoc 1: Dataset va output", size=12, weight=ft.FontWeight.W_700),
                form.tf_yaml,
                form.tf_outdir,
            ]
        if step == 1:
            return [
                ft.Text("Buoc 2: Cau hinh train co ban", size=12, weight=ft.FontWeight.W_700),
                ft.Row(spacing=8, controls=[form.dd_task, form.dd_preset]),
                ft.Row(spacing=8, controls=[form.dd_model, form.dd_optimizer]),
                ft.Row(
                    spacing=6,
                    wrap=True,
                    controls=[
                        form.tf_epochs,
                        form.tf_batch,
                        form.tf_imgsz,
                        form.tf_lr,
                        form.tf_patience,
                        form.tf_workers,
                    ],
                ),
            ]
        return [
            ft.Text("Buoc 3: Device, export va advanced", size=12, weight=ft.FontWeight.W_700),
            ft.Row(spacing=12, controls=[form.dd_device, form.dd_export]),
            ft.Row(spacing=12, controls=[form.cb_amp, form.cb_cache, form.cb_cos_lr]),
            collapsible_section(
                "Advanced augmentation",
                ft.Row(
                    spacing=6,
                    wrap=True,
                    controls=[
                        form.tf_mosaic,
                        form.tf_mixup,
                        form.tf_degrees,
                        form.tf_hsv_s,
                        form.tf_hsv_v,
                    ],
                ),
                note="An mac dinh tren mobile, mo khi can tinh chinh",
                icon_name="TUNE",
                initially_open=False,
            ),
            ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.MEMORY, size=14, color=ft.Colors.WHITE38),
                    runtime.ultra_status,
                    ft.TextButton(
                        "Cai",
                        on_click=on_install_ultra,
                        style=ft.ButtonStyle(
                            color=TRAIN_PURPLE2,
                            padding=ft.padding.symmetric(horizontal=6, vertical=0),
                        ),
                    ),
                ],
            ),
        ]

    def _render_step() -> None:
        step = wizard_state["step"]
        wizard_note.value = f"Buoc {step + 1}/3"
        step_content_ref.current.controls = _step_controls(step)
        if back_btn_ref.current and back_btn_ref.current.page:
            back_btn_ref.current.disabled = step == 0
            back_btn_ref.current.update()
        if next_btn_ref.current and next_btn_ref.current.page:
            next_btn_ref.current.disabled = step == 2
            next_btn_ref.current.update()
        if wizard_note.page:
            wizard_note.update()
        if step_content_ref.current.page:
            step_content_ref.current.update()

    def _goto(step: int):
        wizard_state["step"] = max(0, min(2, step))
        _render_step()

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

    ui = ft.Column(
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
            glass_container(
                padding=14,
                radius=16,
                content=ft.Column(
                    spacing=10,
                    controls=[
                        wizard_note,
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.OutlinedButton(
                                    ref=back_btn_ref,
                                    text="Back",
                                    icon=ft.Icons.ARROW_BACK,
                                    disabled=wizard_state["step"] == 0,
                                    on_click=lambda e: _goto(wizard_state["step"] - 1),
                                ),
                                ft.OutlinedButton(
                                    ref=next_btn_ref,
                                    text="Next",
                                    icon=ft.Icons.ARROW_FORWARD,
                                    disabled=wizard_state["step"] == 2,
                                    on_click=lambda e: _goto(wizard_state["step"] + 1),
                                ),
                            ],
                        ),
                        ft.Column(ref=step_content_ref, spacing=8, controls=[]),
                    ],
                ),
            ),
            ft.Row(spacing=8, controls=[btn_start, btn_stop]),
            glass_container(padding=14, radius=16, content=progress_box),
            result_row,
            glass_container(
                padding=12,
                radius=16,
                content=collapsible_section(
                    "Training log",
                    ft.Container(
                        height=220,
                        bgcolor=ft.Colors.with_opacity(0.35, ft.Colors.BLACK),
                        border_radius=12,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                        content=log_area,
                    ),
                    note="Mac dinh dong de tap trung vao workflow train",
                    icon_name="TERMINAL",
                    initially_open=False,
                ),
            ),
        ],
    )
    _render_step()
    return ui
