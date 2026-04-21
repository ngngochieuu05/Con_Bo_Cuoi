from __future__ import annotations

import threading
import time
from typing import Callable

import flet as ft

from bll.admin.train_management import get_current_job
from ui.theme import DANGER, WARNING

from .train_management_form import TRAIN_PURPLE, TRAIN_PURPLE2, TRAIN_SUCCESS


def _log_tag_color(line: str) -> str:
    if "[INFO]" in line:
        return "#38bdf8"
    if "[DONE]" in line or "[RESULT]" in line or "✔" in line:
        return TRAIN_SUCCESS
    if "[ERROR]" in line or "Error" in line or "Traceback" in line:
        return DANGER
    if "WARNING" in line or "warn" in line.lower():
        return WARNING
    if line.strip().startswith("Epoch"):
        return TRAIN_PURPLE2
    return ft.Colors.WHITE70


class TrainRuntimeController:
    def __init__(self) -> None:
        self.log_list_ref = ft.Ref[ft.ListView]()
        self.prog_bar_ref = ft.Ref[ft.ProgressBar]()
        self.epoch_lbl_ref = ft.Ref[ft.Text]()
        self.pct_lbl_ref = ft.Ref[ft.Text]()
        self.eta_lbl_ref = ft.Ref[ft.Text]()
        self.status_lbl_ref = ft.Ref[ft.Text]()
        self.start_btn_ref = ft.Ref[ft.ElevatedButton]()
        self.stop_btn_ref = ft.Ref[ft.ElevatedButton]()
        self.apply_btn_ref = ft.Ref[ft.ElevatedButton]()
        self.result_row_ref = ft.Ref[ft.Container]()
        self.result_path_txt = ft.Text("", size=11, color=TRAIN_SUCCESS, selectable=True)
        self.ultra_status = ft.Text(
            "Dang kiem tra ultralytics...",
            size=11,
            color=ft.Colors.WHITE54,
        )
        self._state: dict[str, str] = {"result_path": ""}
        self._polling = {"active": False}

    @property
    def result_path(self) -> str:
        return self._state.get("result_path", "")

    def add_log(self, line: str) -> None:
        log_view = self.log_list_ref.current
        if log_view is None:
            return
        log_view.controls.append(
            ft.Text(
                line,
                size=10,
                color=_log_tag_color(line),
                font_family="monospace",
                selectable=True,
                no_wrap=True,
            )
        )
        if len(log_view.controls) > 600:
            log_view.controls = log_view.controls[-500:]
        if log_view.page:
            log_view.update()

    def clear_log(self) -> None:
        log_view = self.log_list_ref.current
        if not log_view:
            return
        log_view.controls.clear()
        if log_view.page:
            log_view.update()

    def set_status(self, text: str, color: str = ft.Colors.WHITE70) -> None:
        label = self.status_lbl_ref.current
        if label and label.page:
            label.value = text
            label.color = color
            label.update()

    def set_training_state(self, running: bool) -> None:
        start_btn = self.start_btn_ref.current
        if start_btn and start_btn.page:
            start_btn.disabled = running
            start_btn.update()
        stop_btn = self.stop_btn_ref.current
        if stop_btn and stop_btn.page:
            stop_btn.disabled = not running
            stop_btn.update()

    def update_ui_from_snap(self, snap: dict) -> None:
        try:
            pct = snap["pct"]
            current_epoch = snap["epoch_cur"]
            total_epoch = snap["epoch_total"]
            status = snap["status"]
            eta = snap["eta"]
            elapsed = snap["elapsed"]

            progress_bar = self.prog_bar_ref.current
            if progress_bar:
                progress_bar.value = pct / 100
                progress_bar.update()

            epoch_label = self.epoch_lbl_ref.current
            if epoch_label:
                epoch_label.value = f"{current_epoch} / {total_epoch}"
                epoch_label.update()

            pct_label = self.pct_lbl_ref.current
            if pct_label:
                pct_label.value = f"{pct}%"
                pct_label.update()

            eta_label = self.eta_lbl_ref.current
            if eta_label:
                eta_label.value = f"Elapsed {elapsed}  |  ETA: {eta}"
                eta_label.update()

            log_view = self.log_list_ref.current
            if log_view:
                existing = len(log_view.controls)
                for line in snap["log_lines"][existing:]:
                    self.add_log(line)

            if status not in ("done", "error", "stopped"):
                return

            self.set_training_state(False)
            if status == "done":
                self.set_status("Hoan thanh!", TRAIN_SUCCESS)
                if progress_bar:
                    progress_bar.value = 1.0
                    progress_bar.update()

                result_path = snap.get("result_path", "")
                if result_path and self.result_path_txt.page:
                    self.result_path_txt.value = f"Luu tai: {result_path}/weights/best.pt"
                    self.result_path_txt.update()

                result_row = self.result_row_ref.current
                if result_row and result_row.page:
                    result_row.visible = True
                    result_row.update()

                apply_btn = self.apply_btn_ref.current
                if apply_btn and apply_btn.page:
                    apply_btn.disabled = False
                    apply_btn.update()

                self._state["result_path"] = result_path
            elif status == "error":
                self.set_status("Loi / Bi dung", DANGER)
            else:
                self.set_status("Da dung", WARNING)
        except Exception:
            pass

    def _poll(self) -> None:
        while self._polling["active"]:
            time.sleep(2)
            job = get_current_job()
            if job is None:
                continue
            snap = job.snapshot()
            self.update_ui_from_snap(snap)
            if snap["status"] != "running":
                self._polling["active"] = False
                break

    def start_polling(self) -> None:
        if self._polling["active"]:
            return
        self._polling["active"] = True
        threading.Thread(target=self._poll, daemon=True).start()

    def start_ultralytics_check(self, checker: Callable[[], bool]) -> None:
        def _check() -> None:
            if checker():
                self.ultra_status.value = "ultralytics da cai dat"
                self.ultra_status.color = TRAIN_SUCCESS
            else:
                self.ultra_status.value = "ultralytics chua cai - nhan 'Cai' de cai tu dong"
                self.ultra_status.color = WARNING
            if self.ultra_status.page:
                self.ultra_status.update()

        threading.Thread(target=_check, daemon=True).start()


def build_progress_box(runtime: TrainRuntimeController, on_clear_log) -> ft.Column:
    return ft.Column(
        spacing=6,
        controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(
                        tight=True,
                        spacing=8,
                        controls=[
                            ft.Text(
                                "EPOCH",
                                size=9,
                                weight=ft.FontWeight.W_700,
                                color=ft.Colors.WHITE38,
                            ),
                            ft.Text(
                                ref=runtime.epoch_lbl_ref,
                                value="- / -",
                                size=20,
                                weight=ft.FontWeight.W_700,
                                color=TRAIN_PURPLE2,
                            ),
                            ft.Text(
                                ref=runtime.pct_lbl_ref,
                                value="0%",
                                size=13,
                                color=ft.Colors.WHITE54,
                            ),
                        ],
                    ),
                    ft.Text(
                        ref=runtime.eta_lbl_ref,
                        value="",
                        size=11,
                        color=ft.Colors.WHITE38,
                    ),
                ],
            ),
            ft.ProgressBar(
                ref=runtime.prog_bar_ref,
                value=0,
                color=TRAIN_PURPLE,
                bgcolor=ft.Colors.with_opacity(0.18, ft.Colors.WHITE),
                height=8,
                border_radius=4,
            ),
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(
                        ref=runtime.status_lbl_ref,
                        value="Chua chay",
                        size=12,
                        color=ft.Colors.WHITE54,
                    ),
                    ft.OutlinedButton(
                        text="Xoa log",
                        height=36,
                        style=ft.ButtonStyle(
                            color=ft.Colors.WHITE54,
                            side=ft.BorderSide(1, ft.Colors.WHITE24),
                            shape=ft.RoundedRectangleBorder(radius=8),
                        ),
                        on_click=lambda e: on_clear_log(),
                    ),
                ],
            ),
        ],
    )


def build_log_area(runtime: TrainRuntimeController) -> ft.ListView:
    return ft.ListView(
        ref=runtime.log_list_ref,
        expand=True,
        spacing=0,
        auto_scroll=True,
        padding=ft.padding.symmetric(horizontal=8, vertical=6),
    )
