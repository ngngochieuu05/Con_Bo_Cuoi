import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
import subprocess
import time
from pathlib import Path

import customtkinter as ctk

from bll.train.session_service import detect_stream_tag, parse_epoch_progress, stream_inline_job
from bll.train.yolo_train_service import prepare_yolo_ablation, prepare_yolo_cls_training, prepare_yolo_training
from ui.ui_theme import (
    ACCENT, ACCENT2, ACCENT3, BG, BG2, BG3, BG4, BORDER,
    DANGER, SUCCESS, TEXT, TEXT_DIM, TEXT_MUTED, WARNING, INFO,
    UI_FONT, INPUT_BG,
    build_section_label, build_ctk_spinbox,
    build_epoch_header_ctk, build_log_textbox,
)
from bll.train.common import DEFAULT_YAML, EXPORT_FORMATS, OUTPUT_DIR, PRESETS, PYTHON_EXE, ROOT_DIR, TASK_TYPES


class YoloTrainerMixin:
    # ─────────────────────────────────────────────────────────────────────────
    # LEFT PANEL
    # ─────────────────────────────────────────────────────────────────────────
    def _build_left(self, parent):
        """Build the YOLO configuration left panel using CTk widgets."""

        # helper: tạo row label + spinbox ĐÚNG parent
        def _spin_row(label: str, var, from_: float, to: float, inc: float = 1):
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.pack(fill="x", pady=2)
            ctk.CTkLabel(f, text=label, font=(UI_FONT, 11), text_color=TEXT_DIM,
                         width=130, anchor="w").pack(side="left")
            build_ctk_spinbox(ctk, f, var, from_, to, inc).pack(side="left")

        # helper: tạo row label + combobox
        def _combo_row(label: str, var, values, width=120):
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.pack(fill="x", pady=2)
            ctk.CTkLabel(f, text=label, font=(UI_FONT, 11), text_color=TEXT_DIM,
                         width=130, anchor="w").pack(side="left")
            return ctk.CTkComboBox(
                f, variable=var, values=values, state="readonly",
                font=(UI_FONT, 11), width=width,
                fg_color=INPUT_BG, border_color=BORDER,
                button_color=BG3, button_hover_color=ACCENT,
                text_color=TEXT, dropdown_fg_color=BG3, dropdown_text_color=TEXT,
            )

        # ── Dataset ──────────────────────────────────────────────────────────
        build_section_label(ctk, parent, "📂 Dataset")

        f_yaml = ctk.CTkFrame(parent, fg_color="transparent")
        f_yaml.pack(fill="x", pady=2)
        ctk.CTkLabel(f_yaml, text="data.yaml", font=(UI_FONT, 11), text_color=TEXT_DIM,
                     width=110, anchor="w").pack(side="left")
        self._yaml_var = tk.StringVar(value=str(DEFAULT_YAML))
        ctk.CTkEntry(f_yaml, textvariable=self._yaml_var, font=(UI_FONT, 10),
                     fg_color=INPUT_BG, border_color=BORDER, text_color=TEXT).pack(
            side="left", fill="x", expand=True, padx=(4, 4))
        ctk.CTkButton(f_yaml, text="📂", width=32, height=28,
                      font=(UI_FONT, 11), fg_color=BG3, hover_color=BG4,
                      text_color=TEXT, corner_radius=6,
                      command=self._browse_yaml).pack(side="left")

        # ── Task type ────────────────────────────────────────────────────────
        build_section_label(ctk, parent, "🎯 Loại Task")
        self._task_var = tk.StringVar(value=TASK_TYPES[0])
        ctk.CTkComboBox(
            parent, variable=self._task_var,
            values=TASK_TYPES, state="readonly",
            font=(UI_FONT, 11),
            fg_color=INPUT_BG, border_color=BORDER,
            button_color=BG3, button_hover_color=ACCENT,
            text_color=TEXT, dropdown_fg_color=BG3, dropdown_text_color=TEXT,
            command=lambda v: self._on_task_changed(),
        ).pack(fill="x", pady=2)

        # ── Preset ───────────────────────────────────────────────────────────
        build_section_label(ctk, parent, "⚡ Preset (theo VRAM)")
        self._preset_var = tk.StringVar()
        ctk.CTkComboBox(
            parent, variable=self._preset_var,
            values=list(PRESETS.keys()), state="readonly",
            font=(UI_FONT, 11),
            fg_color=INPUT_BG, border_color=BORDER,
            button_color=BG3, button_hover_color=ACCENT,
            text_color=TEXT, dropdown_fg_color=BG3, dropdown_text_color=TEXT,
            command=lambda v: self._apply_preset(self._preset_var.get()),
        ).pack(fill="x", pady=2)

        # ── Hyperparameters ──────────────────────────────────────────────────
        build_section_label(ctk, parent, "🔧 Hyperparameters")

        self._model_var        = tk.StringVar()
        self._epochs_var       = tk.IntVar(value=80)
        self._batch_var        = tk.IntVar(value=16)
        self._imgsz_var        = tk.IntVar(value=224)
        self._lr_var           = tk.DoubleVar(value=0.0002)
        self._patience_var     = tk.IntVar(value=20)
        self._workers_var      = tk.IntVar(value=8)
        self._device_var       = tk.StringVar(value="0")
        self._amp_var          = tk.BooleanVar(value=True)
        self._cache_var        = tk.BooleanVar(value=False)
        self._optimizer_var    = tk.StringVar(value="AdamW")
        self._weight_decay_var = tk.DoubleVar(value=0.005)
        self._dropout_var      = tk.DoubleVar(value=0.5)
        self._freeze_var       = tk.IntVar(value=0)
        self._label_smoothing_var = tk.DoubleVar(value=0.15)
        self._cos_lr_var       = tk.BooleanVar(value=True)
        self._mosaic_var       = tk.DoubleVar(value=0.0)
        self._mixup_var        = tk.DoubleVar(value=0.3)
        self._degrees_var      = tk.IntVar(value=15)
        self._hsv_s_var        = tk.DoubleVar(value=0.5)
        self._hsv_v_var        = tk.DoubleVar(value=0.4)

        # Model combobox row
        f_model = ctk.CTkFrame(parent, fg_color="transparent")
        f_model.pack(fill="x", pady=2)
        ctk.CTkLabel(f_model, text="Model", font=(UI_FONT, 11), text_color=TEXT_DIM,
                     width=130, anchor="w").pack(side="left")
        self._model_cb = ctk.CTkComboBox(
            f_model, variable=self._model_var,
            values=["yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt"],
            state="readonly", font=(UI_FONT, 11), width=160,
            fg_color=INPUT_BG, border_color=BORDER,
            button_color=BG3, button_hover_color=ACCENT,
            text_color=TEXT, dropdown_fg_color=BG3, dropdown_text_color=TEXT,
        )
        self._model_cb.pack(side="left")

        # Spinbox rows – parent cho build_ctk_spinbox là ROW FRAME f, không phải parent
        _spin_row("Epochs",        self._epochs_var,       1,      1000)
        _spin_row("Batch size",    self._batch_var,        1,       128)
        _spin_row("Img size",      self._imgsz_var,      128,      1024, 32)
        _spin_row("LR (lr0)",      self._lr_var,       0.00005,    0.01, 0.00005)
        _spin_row("Weight decay",  self._weight_decay_var, 0.0,    0.1,  0.0005)
        _spin_row("Dropout",       self._dropout_var,      0.0,    0.9,  0.05)
        _spin_row("Freeze",        self._freeze_var,        0,      24)
        _spin_row("Label smooth",  self._label_smoothing_var, 0.0, 0.5,  0.01)
        _spin_row("Patience",      self._patience_var,      1,     200)
        _spin_row("Workers",       self._workers_var,       0,      16)

        # Device row
        cb_dev = _combo_row("Device", self._device_var, ["0", "cpu"], width=100)
        cb_dev.pack(side="left")

        # Optimizer row
        cb_opt = _combo_row("Optimizer", self._optimizer_var,
                            ["auto", "SGD", "Adam", "AdamW"], width=120)
        cb_opt.pack(side="left")

        # Hint
        ctk.CTkLabel(
            parent,
            text="💡 Batch=16 · Epochs=80 · lr0=0.0002 · AdamW · WD=0.005\n"
                 "   Dropout=0.5 · Freeze=10 · Mixup=0.3 · Mosaic=0.0 · CosLR",
            font=(UI_FONT, 9), text_color=TEXT_MUTED,
            justify="left", wraplength=290,
        ).pack(anchor="w", pady=(4, 6))

        # ── Data Augmentation Pro ─────────────────────────────────────────────
        build_section_label(ctk, parent, "📈 Data Augmentation (Pro)")
        _spin_row("Mosaic",    self._mosaic_var,  0.0, 1.0, 0.1)
        _spin_row("Mixup",     self._mixup_var,   0.0, 1.0, 0.1)
        _spin_row("Degrees",   self._degrees_var,   0,  45)
        _spin_row("HSV (Sat)", self._hsv_s_var,   0.0, 1.0, 0.1)
        _spin_row("HSV (Val)", self._hsv_v_var,   0.0, 1.0, 0.1)

        # Checkboxes
        chk_row = ctk.CTkFrame(parent, fg_color="transparent")
        chk_row.pack(fill="x", pady=(6, 2))
        ctk.CTkCheckBox(chk_row, text="AMP", variable=self._amp_var,
                        font=(UI_FONT, 11), text_color=TEXT_DIM,
                        fg_color=ACCENT, hover_color=ACCENT2,
                        border_color=BORDER, checkmark_color="white").pack(side="left")
        ctk.CTkCheckBox(chk_row, text="Cache RAM", variable=self._cache_var,
                        font=(UI_FONT, 11), text_color=TEXT_DIM,
                        fg_color=ACCENT, hover_color=ACCENT2,
                        border_color=BORDER, checkmark_color="white").pack(side="left", padx=(10, 0))
        ctk.CTkCheckBox(chk_row, text="Cosine LR", variable=self._cos_lr_var,
                        font=(UI_FONT, 11), text_color=TEXT_DIM,
                        fg_color=ACCENT, hover_color=ACCENT2,
                        border_color=BORDER, checkmark_color="white").pack(side="left", padx=(10, 0))

        # ── Export format ─────────────────────────────────────────────────────
        build_section_label(ctk, parent, "📦 Xuất định dạng")
        self._export_var = tk.StringVar(value=EXPORT_FORMATS[0])
        ctk.CTkComboBox(
            parent, variable=self._export_var,
            values=EXPORT_FORMATS, state="readonly",
            font=(UI_FONT, 11),
            fg_color=INPUT_BG, border_color=BORDER,
            button_color=BG3, button_hover_color=ACCENT,
            text_color=TEXT, dropdown_fg_color=BG3, dropdown_text_color=TEXT,
        ).pack(fill="x", pady=2)

        # ── Output dir ───────────────────────────────────────────────────────
        build_section_label(ctk, parent, "💾 Lưu kết quả")
        f_out = ctk.CTkFrame(parent, fg_color="transparent")
        f_out.pack(fill="x", pady=2)
        self._out_var = tk.StringVar(value=str(OUTPUT_DIR))
        ctk.CTkEntry(f_out, textvariable=self._out_var, font=(UI_FONT, 10),
                     fg_color=INPUT_BG, border_color=BORDER, text_color=TEXT).pack(
            side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(f_out, text="📁", width=32, height=28,
                      font=(UI_FONT, 11), fg_color=BG3, hover_color=BG4,
                      text_color=TEXT, corner_radius=6,
                      command=self._browse_output).pack(side="left")

        # ── Action buttons ────────────────────────────────────────────────────
        ctk.CTkFrame(parent, fg_color=BORDER, height=1).pack(fill="x", pady=(14, 8))

        self._start_btn = ctk.CTkButton(
            parent, text="▶  Bắt đầu Train",
            font=(UI_FONT, 13, "bold"), height=42,
            fg_color=SUCCESS, hover_color="#3ab558",
            text_color="white", corner_radius=8,
            command=self._start_training,
        )
        self._start_btn.pack(fill="x", pady=(0, 4))

        self._stop_btn = ctk.CTkButton(
            parent, text="⏹  Dừng lại",
            font=(UI_FONT, 13, "bold"), height=38,
            fg_color=DANGER, hover_color="#cc3333",
            text_color="white", corner_radius=8,
            command=self._stop_training, state="disabled",
        )
        self._stop_btn.pack(fill="x", pady=(0, 4))

        ctk.CTkButton(
            parent, text="🗑  Xóa Log",
            font=(UI_FONT, 11), height=32,
            fg_color=BG3, hover_color=BG4,
            text_color=TEXT_DIM, corner_radius=8,
            command=self._clear_log,
        ).pack(fill="x", pady=(0, 4))

        self._stats_lbl = ctk.CTkLabel(
            parent, text="",
            font=(UI_FONT, 10), text_color=TEXT_MUTED,
            justify="left", wraplength=280,
        )
        self._stats_lbl.pack(anchor="w", pady=(4, 0))

    # ─────────────────────────────────────────────────────────────────────────
    # RIGHT PANEL
    # ─────────────────────────────────────────────────────────────────────────
    def _build_right(self, parent):
        (self._epoch_big_lbl,
         self._epoch_pct_lbl,
         self._elapsed_lbl,
         _acc,
         self._prog_lbl,
         self._progressbar) = build_epoch_header_ctk(
            ctk, parent,
            epoch_lbl_attr="_epoch_big_lbl",
            pct_lbl_attr="_epoch_pct_lbl",
            elapsed_lbl_attr="_elapsed_lbl",
            acc_lbl_attr=None,
            prog_lbl_attr="_prog_lbl",
            accent_color=ACCENT,
        )

        self._log = build_log_textbox(
            ctk, parent,
            title="📋 Training Log  —  YOLOv8",
            accent_color=ACCENT2,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _fmt_time(seconds: float) -> str:
        seconds = int(seconds)
        h, r = divmod(seconds, 3600)
        m, s = divmod(r, 60)
        if h:
            return f"{h}h {m}m {s}s"
        if m:
            return f"{m}m {s}s"
        return f"{s}s"

    def _apply_preset(self, name: str):
        if name not in PRESETS:
            return
        cfg = PRESETS[name]
        self._preset_var.set(name)
        task = self._task_var.get()
        if task == "Instance Segmentation":
            suffix = "-seg.pt"
        elif task == "Classification":
            suffix = "-cls.pt"
        else:
            suffix = ".pt"
        self._model_var.set(cfg["model"] + suffix)
        self._batch_var.set(cfg["batch"])
        self._imgsz_var.set(cfg["imgsz"])
        self._workers_var.set(cfg["workers"])

    def _on_task_changed(self):
        """Khi đổi task type, cập nhật danh sách model và giá trị hiện tại."""
        task = self._task_var.get()
        if task == "Instance Segmentation":
            models = ["yolov8n-seg.pt", "yolov8s-seg.pt", "yolov8m-seg.pt",
                      "yolov8l-seg.pt", "yolov8x-seg.pt"]
            suffix = "-seg.pt"
        elif task == "Classification":
            models = ["yolov8n-cls.pt", "yolov8s-cls.pt", "yolov8m-cls.pt",
                      "yolov8l-cls.pt", "yolov8x-cls.pt"]
            suffix = "-cls.pt"
            self._epochs_var.set(100)
            self._batch_var.set(32)
            self._imgsz_var.set(224)
            self._lr_var.set(0.0005)
            self._patience_var.set(25)
            self._workers_var.set(2)
            self._optimizer_var.set("AdamW")
            self._cos_lr_var.set(True)
            self._amp_var.set(True)
            self._freeze_var.set(10)
            self._mosaic_var.set(0.0)
            self._mixup_var.set(0.15)
            self._degrees_var.set(10)
            self._hsv_s_var.set(0.5)
            self._hsv_v_var.set(0.4)
        else:
            models = ["yolov8n.pt", "yolov8s.pt", "yolov8m.pt",
                      "yolov8l.pt", "yolov8x.pt"]
            suffix = ".pt"
        if self._model_cb is not None:
            self._model_cb.configure(values=models)
        cur = self._model_var.get()
        base = cur.replace("-seg.pt", "").replace("-cls.pt", "").replace(".pt", "")
        self._model_var.set(base + suffix)

    def _browse_yaml(self):
        f = filedialog.askopenfilename(
            title="Chọn data.yaml",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")],
            initialdir=str(ROOT_DIR / "dataset")
        )
        if f:
            self._yaml_var.set(f)

    def _browse_output(self):
        d = filedialog.askdirectory(title="Chọn thư mục lưu kết quả",
                                    initialdir=str(ROOT_DIR))
        if d:
            self._out_var.set(d)

    def _clear_log(self):
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")

    def _log_write(self, text: str, tag: str = ""):
        self._log.configure(state="normal")
        if tag:
            self._log.insert("end", text, tag)
        else:
            self._log.insert("end", text)
        self._log.configure(state="disabled")
        self._log.see("end")

    def _update_progress_ui(self, cur, tot, pct, elapsed_str, eta):
        self._progressbar.set(pct / 100)
        if self._prog_lbl:
            self._prog_lbl.configure(text=f"Epoch {cur} / {tot}  ({pct}%)")
        self._epoch_big_lbl.configure(text=f"{cur} / {tot}")
        self._epoch_pct_lbl.configure(text=f"{pct}%")
        self._elapsed_lbl.configure(text=f"⏱ {elapsed_str}  |  ETA: {eta}")

    def _check_ultralytics_async(self):
        """Check ultralytics availability (called after UI shown)."""
        def _check():
            try:
                import ultralytics  # noqa: F401
                self.after(0, lambda: self._status_lbl.configure(
                    text="✓ Ultralytics sẵn sàng", text_color=SUCCESS))
            except ImportError:
                self.after(0, lambda: self._status_lbl.configure(
                    text="⚠ Chưa cài ultralytics", text_color=WARNING))
        threading.Thread(target=_check, daemon=True).start()

    # ─────────────────────────────────────────────────────────────────────────
    # YOLO TRAINING LOGIC (unchanged from original)
    # ─────────────────────────────────────────────────────────────────────────
    def _start_training(self):
        try:
            payload = prepare_yolo_training({
                "yaml_path": self._yaml_var.get(),
                "task": self._task_var.get(),
                "model": self._model_var.get(),
                "epochs": self._epochs_var.get(),
                "batch": self._batch_var.get(),
                "imgsz": self._imgsz_var.get(),
                "lr0": self._lr_var.get(),
                "patience": self._patience_var.get(),
                "workers": self._workers_var.get(),
                "device": self._device_var.get(),
                "amp": self._amp_var.get(),
                "cache": self._cache_var.get(),
                "optimizer": self._optimizer_var.get(),
                "weight_decay": self._weight_decay_var.get(),
                "dropout": self._dropout_var.get(),
                "freeze": self._freeze_var.get(),
                "label_smoothing": self._label_smoothing_var.get(),
                "cos_lr": self._cos_lr_var.get(),
                "mosaic": self._mosaic_var.get(),
                "mixup": self._mixup_var.get(),
                "degrees": self._degrees_var.get(),
                "hsv_s": self._hsv_s_var.get(),
                "hsv_v": self._hsv_v_var.get(),
                "export": self._export_var.get(),
                "out_dir": self._out_var.get(),
            })
        except (ValueError, FileNotFoundError) as ex:
            messagebox.showerror("Lỗi", str(ex))
            return

        self._training = True
        self._log_lines = 0
        self._start_time = time.time()
        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._status_lbl.configure(text="🔄 Đang train...", text_color=WARNING)
        self._progressbar.set(0)
        self._epoch_big_lbl.configure(text=f"0 / {payload['epochs']}")
        self._epoch_pct_lbl.configure(text="0%")
        self._elapsed_lbl.configure(text="")

        self._log_write(f"\n{'='*60}\n", "dim")
        self._log_write(f"  YOLOv8 Training  —  Task: {payload['task']}\n", "info")
        self._log_write(f"  Model  : {payload['model']}\n", "info")
        self._log_write(f"  Data   : {payload['yaml_path']}\n", "info")
        self._log_write(f"  Epochs : {payload['epochs']}  Batch: {payload['batch']}  ImgSz: {payload['imgsz']}\n", "info")
        self._log_write(f"  LR     : {payload['lr0']}  Optimizer: {payload['optimizer']}\n", "info")
        self._log_write(f"{'='*60}\n\n", "dim")
        threading.Thread(target=self._run_training,
                         args=(payload["script"], payload["epochs"]),
                         daemon=True).start()

    def _run_training(self, script: str, total_epochs: int):
        retcode, ex = stream_inline_job(
            script, str(PYTHON_EXE), str(ROOT_DIR),
            lambda line: self._parse_yolo_line(line, total_epochs),
            lambda: self._training,
            on_process_started=lambda proc: setattr(self, "_process", proc),
        )
        if ex is not None:
            self.after(0, self._log_write, f"\n[ERROR] {ex}\n", "err")
        self.after(0, self._on_training_done, retcode)

    def _parse_yolo_line(self, line: str, total_epochs: int):
        stripped = line.rstrip()
        tag = detect_stream_tag(line)
        self.after(0, self._log_write, stripped + "\n", tag)
        progress = parse_epoch_progress(line, getattr(self, "_start_time", time.time()))
        if progress:
            self.after(0, self._update_progress_ui,
                       progress["cur"], progress["tot"], progress["pct"],
                       self._fmt_time(progress["elapsed"]),
                       self._fmt_time(progress["eta_s"]))

    def _on_training_done(self, retcode: int):
        self._training = False
        self._start_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        if retcode == 0:
            self._progressbar.set(1.0)
            self._epoch_pct_lbl.configure(text="100%")
            self._status_lbl.configure(text="✓ Hoàn thành!", text_color=SUCCESS)
            self._log_write("\n✓ YOLOv8 training hoàn thành!\n", "ok")
            messagebox.showinfo("Xong!", f"Training hoàn thành!\nModel lưu tại:\n{self._out_var.get()}")
        else:
            self._status_lbl.configure(text="✗ Lỗi / Đã dừng", text_color=DANGER)
            self._log_write(f"\n✗ Kết thúc bất thường (code {retcode})\n", "err")

    def _stop_training(self):
        if self._process and self._process.poll() is None:
            self._training = False
            self._process.terminate()
            self._log_write("\n⏹ Đã gửi lệnh dừng...\n", "warn")
            self._status_lbl.configure(text="⏹ Đang dừng...", text_color=WARNING)
