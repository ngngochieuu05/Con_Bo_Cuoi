import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
import os
import time
from pathlib import Path

import customtkinter as ctk

from bll.train.classification_train_service import prepare_plos_training
from bll.train.session_service import detect_stream_tag, parse_epoch_progress, stream_inline_job
from ui.ui_theme import (
    ACCENT2, BG, BG2, BG3, BG4, BORDER,
    DANGER, SUCCESS, TEXT, TEXT_DIM, TEXT_MUTED, WARNING,
    UI_FONT, INPUT_BG,
    build_section_label, build_ctk_spinbox,
    build_epoch_header_ctk, build_log_textbox,
)
from bll.train.common import OUTPUT_DIR, PYTHON_EXE, ROOT_DIR

_PLOS_ACCENT = "#4ade80"
_PLOS_HOVER  = "#22c55e"


class NetmbPlosTrainerMixin:
    def _build_plos_tab(self, parent):
        # ── Two-column layout ─────────────────────────────────────────────────
        body = ctk.CTkFrame(parent, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=8, pady=8)
        body.grid_columnconfigure(0, weight=0, minsize=300)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        left_outer = ctk.CTkFrame(body, fg_color=BG2, corner_radius=14,
                                  border_width=1, border_color=BORDER)
        left_outer.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left = ctk.CTkScrollableFrame(left_outer, fg_color=BG2, corner_radius=12,
                                      scrollbar_button_color=_PLOS_ACCENT,
                                      scrollbar_button_hover_color=_PLOS_HOVER)
        left.pack(fill="both", expand=True, padx=6, pady=6)

        right = ctk.CTkFrame(body, fg_color=BG, corner_radius=14)
        right.grid(row=0, column=1, sticky="nsew")

        # helper: spinbox row – widget được tạo với ROW FRAME làm parent
        def _spin_row(label: str, var, from_: float, to: float, inc: float = 1):
            f = ctk.CTkFrame(left, fg_color="transparent")
            f.pack(fill="x", pady=2)
            ctk.CTkLabel(f, text=label, font=(UI_FONT, 11), text_color=TEXT_DIM,
                         width=130, anchor="w").pack(side="left")
            build_ctk_spinbox(ctk, f, var, from_, to, inc).pack(side="left")

        # ── LEFT: Dataset ─────────────────────────────────────────────────────
        build_section_label(ctk, left, "📂 Dataset (có train/ và val/)")

        f_data = ctk.CTkFrame(left, fg_color="transparent")
        f_data.pack(fill="x", pady=2)
        self._plos_data_var = tk.StringVar(
            value=r"D:\DACS\Dataset\desease\so_sanh\2.lumpy\classification")
        ctk.CTkEntry(f_data, textvariable=self._plos_data_var,
                     font=(UI_FONT, 10), fg_color=INPUT_BG,
                     border_color=BORDER, text_color=TEXT).pack(
            side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(f_data, text="📂", width=32, height=28,
                      font=(UI_FONT, 11), fg_color=BG3, hover_color=BG4,
                      text_color=TEXT, corner_radius=6,
                      command=self._plos_browse_data).pack(side="left")

        # ── LEFT: Hyperparameters ─────────────────────────────────────────────
        build_section_label(ctk, left, "⚙ Hyperparameters — PLOS ONE 2024")

        self._plos_imgsz_var    = tk.IntVar(value=224)
        self._plos_batch_var    = tk.IntVar(value=32)
        self._plos_epochs_var   = tk.IntVar(value=50)
        self._plos_lr_var       = tk.DoubleVar(value=0.0001)
        self._plos_patience_var = tk.IntVar(value=10)
        self._plos_workers_var  = tk.IntVar(value=0)
        self._plos_freeze_var   = tk.BooleanVar(value=False)
        self._plos_amp_var      = tk.BooleanVar(value=True)
        self._plos_cos_lr_var   = tk.BooleanVar(value=True)

        _spin_row("Img Size",        self._plos_imgsz_var,     32,  640, 8)
        _spin_row("Batch Size",      self._plos_batch_var,      1,  256)
        _spin_row("Epochs",          self._plos_epochs_var,     1,  500)
        _spin_row("LR",              self._plos_lr_var,    0.00001, 0.1, 0.00001)
        _spin_row("Early Stop Pat.", self._plos_patience_var,   0,   50)
        _spin_row("Workers",         self._plos_workers_var,    0,   16)

        # Optimizer row
        fo = ctk.CTkFrame(left, fg_color="transparent")
        fo.pack(fill="x", pady=2)
        ctk.CTkLabel(fo, text="Optimizer", font=(UI_FONT, 11), text_color=TEXT_DIM,
                     width=130, anchor="w").pack(side="left")
        self._plos_opt_var = tk.StringVar(value="RMSprop")
        ctk.CTkComboBox(fo, variable=self._plos_opt_var,
                        values=["Adam", "AdamW", "RMSprop", "SGD"], state="readonly",
                        font=(UI_FONT, 11), width=120,
                        fg_color=INPUT_BG, border_color=BORDER,
                        button_color=BG3, button_hover_color=_PLOS_HOVER,
                        text_color=TEXT, dropdown_fg_color=BG3,
                        dropdown_text_color=TEXT).pack(side="left")

        # Device row
        fd = ctk.CTkFrame(left, fg_color="transparent")
        fd.pack(fill="x", pady=2)
        ctk.CTkLabel(fd, text="Device", font=(UI_FONT, 11), text_color=TEXT_DIM,
                     width=130, anchor="w").pack(side="left")
        self._plos_device_var = tk.StringVar(value="cuda")
        ctk.CTkComboBox(fd, variable=self._plos_device_var,
                        values=["cuda", "cpu"], state="readonly",
                        font=(UI_FONT, 11), width=100,
                        fg_color=INPUT_BG, border_color=BORDER,
                        button_color=BG3, button_hover_color=_PLOS_HOVER,
                        text_color=TEXT, dropdown_fg_color=BG3,
                        dropdown_text_color=TEXT).pack(side="left")

        # Checkboxes
        chk_frz = ctk.CTkFrame(left, fg_color="transparent")
        chk_frz.pack(fill="x", pady=(6, 2))
        ctk.CTkCheckBox(chk_frz, text="Freeze backbone (chỉ train classifier head)",
                        variable=self._plos_freeze_var,
                        font=(UI_FONT, 11), text_color=TEXT_DIM,
                        fg_color=_PLOS_ACCENT, hover_color=_PLOS_HOVER,
                        border_color=BORDER, checkmark_color="white").pack(side="left")

        chk_row = ctk.CTkFrame(left, fg_color="transparent")
        chk_row.pack(fill="x", pady=2)
        ctk.CTkCheckBox(chk_row, text="AMP", variable=self._plos_amp_var,
                        font=(UI_FONT, 11), text_color=TEXT_DIM,
                        fg_color=_PLOS_ACCENT, hover_color=_PLOS_HOVER,
                        border_color=BORDER, checkmark_color="white").pack(side="left")
        ctk.CTkCheckBox(chk_row, text="Cosine LR", variable=self._plos_cos_lr_var,
                        font=(UI_FONT, 11), text_color=TEXT_DIM,
                        fg_color=_PLOS_ACCENT, hover_color=_PLOS_HOVER,
                        border_color=BORDER, checkmark_color="white").pack(side="left", padx=(10, 0))

        # ── Pretrained weights ────────────────────────────────────────────────
        build_section_label(ctk, left, "📦 Pretrained weights (.pth local — trống = tải online)")
        f_wt = ctk.CTkFrame(left, fg_color="transparent")
        f_wt.pack(fill="x", pady=2)
        self._plos_weights_var = tk.StringVar(value="")
        ctk.CTkEntry(f_wt, textvariable=self._plos_weights_var,
                     font=(UI_FONT, 10), fg_color=INPUT_BG,
                     border_color=BORDER, text_color=TEXT).pack(
            side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(f_wt, text="📂", width=32, height=28,
                      font=(UI_FONT, 11), fg_color=BG3, hover_color=BG4,
                      text_color=TEXT, corner_radius=6,
                      command=self._plos_browse_weights).pack(side="left")

        # ── Output dir ────────────────────────────────────────────────────────
        build_section_label(ctk, left, "💾 Lưu kết quả (.pth)")
        f_out = ctk.CTkFrame(left, fg_color="transparent")
        f_out.pack(fill="x", pady=2)
        self._plos_out_var = tk.StringVar(value=str(OUTPUT_DIR / "plos_mobilenetv2"))
        ctk.CTkEntry(f_out, textvariable=self._plos_out_var,
                     font=(UI_FONT, 10), fg_color=INPUT_BG,
                     border_color=BORDER, text_color=TEXT).pack(
            side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(f_out, text="📁", width=32, height=28,
                      font=(UI_FONT, 11), fg_color=BG3, hover_color=BG4,
                      text_color=TEXT, corner_radius=6,
                      command=self._plos_browse_output).pack(side="left")

        # ── Action buttons ────────────────────────────────────────────────────
        ctk.CTkFrame(left, fg_color=BORDER, height=1).pack(fill="x", pady=(12, 8))

        self._plos_start_btn = ctk.CTkButton(
            left, text="▶  Bắt đầu Train MobileNetV2",
            font=(UI_FONT, 13, "bold"), height=42,
            fg_color="#16a34a", hover_color="#15803d",
            text_color="white", corner_radius=8,
            command=self._start_plos,
        )
        self._plos_start_btn.pack(fill="x", pady=(0, 4))

        self._plos_stop_btn = ctk.CTkButton(
            left, text="⏹  Dừng lại",
            font=(UI_FONT, 13, "bold"), height=38,
            fg_color=DANGER, hover_color="#cc3333",
            text_color="white", corner_radius=8,
            command=self._stop_plos, state="disabled",
        )
        self._plos_stop_btn.pack(fill="x", pady=(0, 4))

        ctk.CTkButton(
            left, text="🗑  Xóa Log",
            font=(UI_FONT, 11), height=32,
            fg_color=BG3, hover_color=BG4,
            text_color=TEXT_DIM, corner_radius=8,
            command=self._plos_clear_log,
        ).pack(fill="x", pady=(0, 4))

        self._plos_status_lbl = ctk.CTkLabel(
            left, text="⏹ Chưa chạy",
            font=(UI_FONT, 11, "bold"), text_color=TEXT_DIM,
        )
        self._plos_status_lbl.pack(anchor="w", pady=(6, 0))

        # ── RIGHT: Epoch counter + log ────────────────────────────────────────
        (self._plos_epoch_lbl,
         self._plos_pct_lbl,
         self._plos_elapsed_lbl,
         self._plos_acc_lbl,
         self._plos_prog_lbl,
         self._plos_progressbar) = build_epoch_header_ctk(
            ctk, right,
            epoch_lbl_attr="_plos_epoch_lbl",
            pct_lbl_attr="_plos_pct_lbl",
            elapsed_lbl_attr="_plos_elapsed_lbl",
            acc_lbl_attr="_plos_acc_lbl",
            prog_lbl_attr="_plos_prog_lbl",
            accent_color=_PLOS_ACCENT,
        )

        self._plos_log = build_log_textbox(
            ctk, right,
            title="📋 PLOS ONE 2024 MobileNetV2 Log",
            accent_color=_PLOS_ACCENT,
            tags=[("epoch", _PLOS_ACCENT), ("best", "#fbbf24")],
        )

    # ── PLOS helpers ──────────────────────────────────────────────────────────
    def _plos_browse_data(self):
        d = filedialog.askdirectory(title="Chọn dataset folder (có train/ val/)")
        if d: self._plos_data_var.set(d)

    def _plos_browse_weights(self):
        f = filedialog.askopenfilename(
            title="Chọn file .pth MobileNetV2 pretrained",
            filetypes=[("PyTorch weights", "*.pth"), ("All files", "*.*")],
        )
        if f: self._plos_weights_var.set(f)

    def _plos_browse_output(self):
        d = filedialog.askdirectory(title="Chọn folder lưu model .pth")
        if d: self._plos_out_var.set(d)

    def _plos_log_write(self, text: str, tag: str = ""):
        self._plos_log.configure(state="normal")
        if tag: self._plos_log.insert("end", text, tag)
        else:   self._plos_log.insert("end", text)
        self._plos_log.configure(state="disabled")
        self._plos_log.see("end")

    def _plos_clear_log(self):
        self._plos_log.configure(state="normal")
        self._plos_log.delete("1.0", "end")
        self._plos_log.configure(state="disabled")

    # ── PLOS training (unchanged logic) ───────────────────────────────────────
    def _start_plos(self):
        try:
            payload = prepare_plos_training({
                "data_path": self._plos_data_var.get(),
                "imgsz": self._plos_imgsz_var.get(),
                "batch": self._plos_batch_var.get(),
                "epochs": self._plos_epochs_var.get(),
                "lr": self._plos_lr_var.get(),
                "patience": self._plos_patience_var.get(),
                "workers": self._plos_workers_var.get(),
                "device": self._plos_device_var.get(),
                "optimizer": self._plos_opt_var.get(),
                "freeze": self._plos_freeze_var.get(),
                "out_dir": self._plos_out_var.get(),
                "weights_path": self._plos_weights_var.get().strip(),
                "amp": self._plos_amp_var.get(),
                "cos_lr": self._plos_cos_lr_var.get(),
            })
        except ValueError as ex:
            messagebox.showerror("Lỗi", str(ex))
            return

        self._plos_training = True
        self._plos_start_btn.configure(state="disabled")
        self._plos_stop_btn.configure(state="normal")
        self._plos_status_lbl.configure(text="🔄 Đang train...", text_color=WARNING)
        self._plos_start_time = time.time()
        self._plos_current_epochs = payload["epochs"]
        self._plos_progressbar.set(0)
        self._plos_epoch_lbl.configure(text=f"0 / {payload['epochs']}")
        self._plos_pct_lbl.configure(text="0%")
        self._plos_acc_lbl.configure(text="Val Acc: —" if payload["use_validation"] else "Val Acc: N/A")
        self._plos_elapsed_lbl.configure(text="")

        self._plos_log_write(f"\n{'='*60}\n", "dim")
        self._plos_log_write(f"  PLOS ONE 2024 — MobileNetV2 (Transfer Learning)\n", "info")
        self._plos_log_write(f"  Dataset  : {payload['data_path']}\n", "info")
        if payload["raw_data_path"] != payload["data_path"]:
            self._plos_log_write(f"  Input    : {payload['raw_data_path']} -> auto doi ve dataset root\n", "dim")
        self._plos_log_write(f"  ImgSz    : {payload['imgsz']}  Batch: {payload['batch']}  Epochs: {payload['epochs']}\n", "info")
        self._plos_log_write(f"  LR       : {payload['lr']:.5f}  Optimizer: {payload['optimizer']}\n", "info")
        self._plos_log_write(f"  Freeze   : {payload['freeze']}  Early Stop: {payload['patience']}\n", "info")
        self._plos_log_write(f"  Device   : {payload['device'].upper()}  Workers: {payload['workers']}\n", "info")
        self._plos_log_write(f"  AMP      : {payload['amp']}  Cosine LR: {payload['cos_lr']}\n", "info")
        self._plos_log_write(
            f"  Validation: {'Dung val/' if payload['use_validation'] else 'Bo qua val/ vi khong co anh hop le; chi train tren train/'}\n",
            "info",
        )
        if payload["weights_path"]:
            self._plos_log_write(f"  Weights  : {payload['weights_path']} (local)\n", "info")
        else:
            self._plos_log_write(f"  Weights  : ImageNet (online download)\n", "info")
        self._plos_log_write(f"{'='*60}\n\n", "dim")
        threading.Thread(target=self._run_plos, args=(payload["script"], payload["epochs"]), daemon=True).start()

    def _run_plos(self, script: str, total_epochs: int):
        retcode, ex = stream_inline_job(
            script,
            str(PYTHON_EXE),
            str(ROOT_DIR),
            lambda line: self._plos_parse_line(line, total_epochs),
            lambda: self._plos_training,
            on_process_started=lambda proc: setattr(self, "_plos_process", proc),
            force_utf8=True,
        )
        if ex is not None:
            self.after(0, self._plos_log_write, f"\n[ERROR] {ex}\n", "err")
        self.after(0, self._on_plos_done, retcode)

    def _plos_parse_line(self, line: str, total_epochs: int):
        stripped = line.rstrip()
        tag = detect_stream_tag(line)
        self.after(0, self._plos_log_write, stripped + "\n", tag)
        progress = parse_epoch_progress(line, self._plos_start_time)
        if progress:
            self.after(0, self._plos_update_progress,
                       progress["cur"], progress["tot"], progress["pct"], progress["acc_str"],
                       self._fmt_time(progress["elapsed"]), self._fmt_time(progress["eta_s"]))

    def _plos_update_progress(self, cur, tot, pct, acc_str, elapsed_str, eta):
        self._plos_progressbar.set(pct / 100)
        self._plos_prog_lbl.configure(text=f"Epoch {cur} / {tot}  ({pct}%)")
        self._plos_epoch_lbl.configure(text=f"{cur} / {tot}")
        self._plos_pct_lbl.configure(text=f"{pct}%")
        if acc_str:
            self._plos_acc_lbl.configure(text=f"Val Acc: {acc_str}")
        self._plos_elapsed_lbl.configure(text=f"⏱ {elapsed_str}  |  ETA: {eta}")

    def _on_plos_done(self, retcode: int):
        self._plos_training = False
        self._plos_start_btn.configure(state="normal")
        self._plos_stop_btn.configure(state="disabled")
        if retcode == 0:
            self._plos_progressbar.set(1.0)
            self._plos_pct_lbl.configure(text="100%")
            self._plos_status_lbl.configure(text="✓ Hoàn thành!", text_color=SUCCESS)
            self._plos_log_write("\n✓ MobileNetV2 training hoàn thành!\n", "ok")
            elapsed = self._fmt_time(time.time() - self._plos_start_time)
            self._plos_log_write(f"⏱ Tổng thời gian: {elapsed}\n", "info")
            messagebox.showinfo("Xong!", f"PLOS ONE 2024 MobileNetV2 hoàn thành!\nModel lưu tại:\n{self._plos_out_var.get()}")
        else:
            self._plos_status_lbl.configure(text="✗ Lỗi / Đã dừng", text_color=DANGER)
            self._plos_log_write(f"\n✗ Kết thúc bất thường (code {retcode})\n", "err")

    def _stop_plos(self):
        if self._plos_process and self._plos_process.poll() is None:
            self._plos_training = False
            self._plos_process.terminate()
            self._plos_log_write("\n⏹ Đã gửi lệnh dừng...\n", "warn")
            self._plos_status_lbl.configure(text="⏹ Đang dừng...", text_color=WARNING)
