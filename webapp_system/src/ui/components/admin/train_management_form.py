from __future__ import annotations

from dataclasses import dataclass

import flet as ft

from bll.admin.train_management import (
    DEFAULT_OUT,
    DEFAULT_YAML,
    EXPORT_FORMATS,
    OPTIMIZERS,
    PRESETS,
    TASK_TYPES,
)

TRAIN_PURPLE = "#7c3aed"
TRAIN_PURPLE2 = "#a78bfa"
TRAIN_SUCCESS = "#22c55e"


def _compact_field(
    label: str,
    value: str = "",
    width: int | None = None,
    keyboard_type=None,
    hint: str = "",
) -> ft.TextField:
    return ft.TextField(
        label=label,
        value=value,
        hint_text=hint or None,
        keyboard_type=keyboard_type,
        width=width,
        border_radius=10,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.28, ft.Colors.WHITE),
        focused_border_color=TRAIN_PURPLE2,
        label_style=ft.TextStyle(color=ft.Colors.WHITE60, size=11),
        text_style=ft.TextStyle(color=ft.Colors.WHITE, size=12),
        cursor_color=ft.Colors.WHITE,
        content_padding=ft.padding.symmetric(horizontal=10, vertical=8),
        dense=True,
    )


def _compact_dd(
    label: str,
    options: list[str],
    value: str = "",
    width: int | None = None,
) -> ft.Dropdown:
    return ft.Dropdown(
        label=label,
        value=value,
        width=width,
        border_radius=10,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.28, ft.Colors.WHITE),
        focused_border_color=TRAIN_PURPLE2,
        label_style=ft.TextStyle(color=ft.Colors.WHITE60, size=11),
        text_style=ft.TextStyle(color=ft.Colors.WHITE, size=12),
        content_padding=ft.padding.symmetric(horizontal=8, vertical=6),
        options=[ft.dropdown.Option(option) for option in options],
    )


def _section_label(text: str) -> ft.Text:
    return ft.Text(
        text,
        size=11,
        weight=ft.FontWeight.W_700,
        color=TRAIN_PURPLE2,
    )


def _model_options(is_segment: bool) -> list[str]:
    return [f"yolov8{size}{'-seg' if is_segment else ''}.pt" for size in ("n", "s", "m", "l", "x")]


@dataclass
class TrainFormControls:
    dd_preset: ft.Dropdown
    dd_task: ft.Dropdown
    dd_model: ft.Dropdown
    dd_optimizer: ft.Dropdown
    dd_device: ft.Dropdown
    dd_export: ft.Dropdown
    tf_epochs: ft.TextField
    tf_batch: ft.TextField
    tf_imgsz: ft.TextField
    tf_lr: ft.TextField
    tf_patience: ft.TextField
    tf_workers: ft.TextField
    tf_yaml: ft.TextField
    tf_outdir: ft.TextField
    tf_mosaic: ft.TextField
    tf_mixup: ft.TextField
    tf_degrees: ft.TextField
    tf_hsv_s: ft.TextField
    tf_hsv_v: ft.TextField
    cb_amp: ft.Checkbox
    cb_cache: ft.Checkbox
    cb_cos_lr: ft.Checkbox

    def bind_events(self) -> None:
        self.dd_preset.on_change = lambda e: self.apply_preset()
        self.dd_task.on_change = lambda e: self.on_task_changed()

    def apply_preset(self) -> None:
        name = self.dd_preset.value
        if name not in PRESETS:
            return
        cfg = PRESETS[name]
        suffix = "-seg.pt" if self.dd_task.value == "segment" else ".pt"
        self.dd_model.value = cfg["model"] + suffix
        self.tf_batch.value = str(cfg["batch"])
        self.tf_imgsz.value = str(cfg["imgsz"])
        self.tf_workers.value = str(cfg["workers"])
        if self.dd_model.page:
            self.dd_model.update()
            self.tf_batch.update()
            self.tf_imgsz.update()
            self.tf_workers.update()

    def on_task_changed(self) -> None:
        is_segment = self.dd_task.value == "segment"
        suffix = "-seg.pt" if is_segment else ".pt"
        current = self.dd_model.value or "yolov8s.pt"
        base = current.replace("-seg.pt", "").replace(".pt", "")
        self.dd_model.options = [
            ft.dropdown.Option(option)
            for option in _model_options(is_segment)
        ]
        self.dd_model.value = base + suffix
        if self.dd_model.page:
            self.dd_model.update()

    def build_start_payload(self) -> dict[str, object]:
        device_raw = (self.dd_device.value or "0 (GPU)").split()[0]
        return {
            "yaml_path": (self.tf_yaml.value or "").strip(),
            "model": self.dd_model.value or "yolov8s.pt",
            "task": self.dd_task.value or "detect",
            "epochs": int(self.tf_epochs.value or 50),
            "batch": int(self.tf_batch.value or 16),
            "imgsz": int(self.tf_imgsz.value or 640),
            "lr0": float(self.tf_lr.value or 0.001),
            "patience": int(self.tf_patience.value or 30),
            "workers": int(self.tf_workers.value or 8),
            "device": device_raw,
            "optimizer": self.dd_optimizer.value or "AdamW",
            "amp": self.cb_amp.value,
            "cache": self.cb_cache.value,
            "cos_lr": self.cb_cos_lr.value,
            "mosaic": float(self.tf_mosaic.value or 1.0),
            "mixup": float(self.tf_mixup.value or 0.2),
            "degrees": int(self.tf_degrees.value or 15),
            "hsv_s": float(self.tf_hsv_s.value or 0.5),
            "hsv_v": float(self.tf_hsv_v.value or 0.4),
            "output_dir": (self.tf_outdir.value or str(DEFAULT_OUT)).strip(),
            "export_format": self.dd_export.value or "pt",
        }


def build_train_form_controls() -> TrainFormControls:
    form = TrainFormControls(
        dd_preset=_compact_dd(
            "Preset VRAM",
            list(PRESETS.keys()),
            value="Can bang (yolov8s)",
        ),
        dd_task=_compact_dd("Task", TASK_TYPES, value="detect"),
        dd_model=_compact_dd("Model", _model_options(False), value="yolov8s.pt"),
        dd_optimizer=_compact_dd("Optimizer", OPTIMIZERS, value="AdamW"),
        dd_device=_compact_dd("Device", ["0 (GPU)", "cpu"], value="0 (GPU)"),
        dd_export=_compact_dd("Export", EXPORT_FORMATS, value="pt"),
        tf_epochs=_compact_field(
            "Epochs",
            "50",
            width=70,
            keyboard_type=ft.KeyboardType.NUMBER,
        ),
        tf_batch=_compact_field(
            "Batch",
            "16",
            width=70,
            keyboard_type=ft.KeyboardType.NUMBER,
        ),
        tf_imgsz=_compact_field(
            "Img size",
            "640",
            width=70,
            keyboard_type=ft.KeyboardType.NUMBER,
        ),
        tf_lr=_compact_field(
            "LR (lr0)",
            "0.001",
            width=80,
            keyboard_type=ft.KeyboardType.NUMBER,
        ),
        tf_patience=_compact_field(
            "Patience",
            "30",
            width=70,
            keyboard_type=ft.KeyboardType.NUMBER,
        ),
        tf_workers=_compact_field(
            "Workers",
            "8",
            width=70,
            keyboard_type=ft.KeyboardType.NUMBER,
        ),
        tf_yaml=_compact_field(
            "data.yaml",
            str(DEFAULT_YAML),
            hint="Duong dan .yaml",
        ),
        tf_outdir=_compact_field(
            "Output dir",
            str(DEFAULT_OUT),
            hint="Thu muc luu ket qua",
        ),
        tf_mosaic=_compact_field("Mosaic", "1.0", width=70),
        tf_mixup=_compact_field("Mixup", "0.2", width=70),
        tf_degrees=_compact_field("Degrees", "15", width=70),
        tf_hsv_s=_compact_field("HSV-S", "0.5", width=70),
        tf_hsv_v=_compact_field("HSV-V", "0.4", width=70),
        cb_amp=ft.Checkbox(
            label="AMP (Mixed Precision)",
            value=True,
            fill_color=TRAIN_PURPLE2,
            check_color=ft.Colors.WHITE,
        ),
        cb_cache=ft.Checkbox(
            label="Cache RAM",
            value=False,
            fill_color=TRAIN_PURPLE2,
            check_color=ft.Colors.WHITE,
        ),
        cb_cos_lr=ft.Checkbox(
            label="Cosine LR",
            value=True,
            fill_color=TRAIN_PURPLE2,
            check_color=ft.Colors.WHITE,
        ),
    )
    form.bind_events()
    return form


def build_train_config_panel(
    form: TrainFormControls,
    *,
    ultra_status: ft.Text,
    on_install_ultra,
) -> ft.Column:
    return ft.Column(
        spacing=8,
        controls=[
            _section_label("Dataset"),
            form.tf_yaml,
            _section_label("Output"),
            form.tf_outdir,
            ft.Divider(color=ft.Colors.with_opacity(0.12, ft.Colors.WHITE), height=1),
            _section_label("Task And Preset"),
            ft.Row(spacing=6, controls=[form.dd_task, form.dd_preset]),
            ft.Row(spacing=6, controls=[form.dd_model, form.dd_optimizer]),
            ft.Divider(color=ft.Colors.with_opacity(0.12, ft.Colors.WHITE), height=1),
            _section_label("Hyperparameters"),
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
            ft.Row(spacing=16, controls=[form.dd_device, form.dd_export]),
            ft.Row(
                spacing=12,
                controls=[form.cb_amp, form.cb_cache, form.cb_cos_lr],
            ),
            ft.Divider(color=ft.Colors.with_opacity(0.12, ft.Colors.WHITE), height=1),
            _section_label("Data Augmentation (Pro)"),
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
            ft.Divider(color=ft.Colors.with_opacity(0.12, ft.Colors.WHITE), height=1),
            ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.MEMORY, size=14, color=ft.Colors.WHITE38),
                    ultra_status,
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
        ],
    )
