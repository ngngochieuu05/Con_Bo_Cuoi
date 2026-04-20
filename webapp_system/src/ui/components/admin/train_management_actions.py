from __future__ import annotations

import flet as ft

from bll.admin.model_management import get_model_by_type, update_model_config
from bll.admin.train_management import install_ultralytics, start_training, stop_training
from ui.theme import DANGER, WARNING

from .train_management_form import TRAIN_SUCCESS, TrainFormControls
from .train_management_runtime import TrainRuntimeController


def create_start_handler(form: TrainFormControls, runtime: TrainRuntimeController):
    def on_start(e):
        try:
            ok, msg = start_training(**form.build_start_payload())
            if not ok:
                runtime.set_status(msg, DANGER)
                return

            runtime.clear_log()
            runtime.add_log(f"[INFO] Job ID: {msg}")
            runtime.add_log(
                f"[INFO] Model : {form.dd_model.value}  |  Task: {form.dd_task.value}"
            )
            runtime.add_log(
                f"[INFO] Epochs: {form.tf_epochs.value}  |  Batch: {form.tf_batch.value}"
            )
            runtime.set_status("Dang train...", WARNING)
            runtime.set_training_state(True)

            apply_btn = runtime.apply_btn_ref.current
            if apply_btn and apply_btn.page:
                apply_btn.disabled = True
                apply_btn.update()

            result_row = runtime.result_row_ref.current
            if result_row and result_row.page:
                result_row.visible = False
                result_row.update()

            progress_bar = runtime.prog_bar_ref.current
            if progress_bar and progress_bar.page:
                progress_bar.value = 0
                progress_bar.update()

            runtime.start_polling()
        except ValueError as ex:
            runtime.set_status(f"Tham so khong hop le: {ex}", DANGER)

    return on_start


def create_stop_handler(runtime: TrainRuntimeController):
    def on_stop(e):
        stop_training()
        runtime.set_status("Dang dung...", WARNING)

    return on_stop


def create_apply_model_handler(runtime: TrainRuntimeController):
    def on_apply_model(e):
        if not runtime.result_path:
            return
        best_pt = f"{runtime.result_path}/weights/best.pt"
        try:
            model = get_model_by_type("disease")
            if not model:
                return
            update_model_config(
                model["id_model"],
                model.get("conf", 0.5),
                model.get("iou", 0.45),
                best_pt,
            )
            runtime.set_status("Da cap nhat duong dan model disease!", TRAIN_SUCCESS)
        except Exception as ex:
            runtime.set_status(f"Loi cap nhat: {ex}", DANGER)

    return on_apply_model


def create_install_ultra_handler(runtime: TrainRuntimeController):
    def on_install_ultra(e):
        runtime.ultra_status.value = "Dang cai ultralytics..."
        runtime.ultra_status.color = ft.Colors.WHITE60
        if runtime.ultra_status.page:
            runtime.ultra_status.update()

        def _log(line: str) -> None:
            runtime.add_log(line)
            if "[DONE]" in line:
                runtime.ultra_status.value = "Da cai xong ultralytics"
                runtime.ultra_status.color = TRAIN_SUCCESS
            elif "[ERROR]" in line:
                runtime.ultra_status.value = "Cai loi - xem log"
                runtime.ultra_status.color = DANGER
            if runtime.ultra_status.page:
                runtime.ultra_status.update()

        install_ultralytics(on_log=_log)

    return on_install_ultra
