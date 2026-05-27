import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
import os
import time
from pathlib import Path

import customtkinter as ctk

from bll.train.classification_train_service import prepare_jilsa_training
from bll.train.session_service import detect_stream_tag, parse_epoch_progress, stream_inline_job
from ui.ui_theme import (
    ACCENT, ACCENT2, BG, BG2, BG3, BG4, BORDER,
    DANGER, SUCCESS, TEXT, TEXT_DIM, TEXT_MUTED, WARNING,
    UI_FONT, INPUT_BG,
    build_section_label, build_ctk_spinbox,
    build_epoch_header_ctk, build_log_textbox,
)
from bll.train.common import OUTPUT_DIR, PYTHON_EXE, ROOT_DIR


class CNNJilsaTrainerMixin:
    def _build_jilsa_tab(self, parent):
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
                                      scrollbar_button_color=ACCENT,
                                      scrollbar_button_hover_color=ACCENT2)
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
        build_section_label(ctk, left, "📂 Dataset (có train/ và val/ hoặc test/)")

        f_data = ctk.CTkFrame(left, fg_color="transparent")
        f_data.pack(fill="x", pady=2)
        self._jilsa_data_var = tk.StringVar(
            value=r"D:\DACS\Dataset\desease\so_sanh\1.jilsa2022\class")
        ctk.CTkEntry(f_data, textvariable=self._jilsa_data_var,
                     font=(UI_FONT, 10), fg_color=INPUT_BG,
                     border_color=BORDER, text_color=TEXT).pack(
            side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(f_data, text="📂", width=32, height=28,
                      font=(UI_FONT, 11), fg_color=BG3, hover_color=BG4,
                      text_color=TEXT, corner_radius=6,
                      command=self._jilsa_browse_data).pack(side="left")

        # Val folder row
        fv = ctk.CTkFrame(left, fg_color="transparent")
        fv.pack(fill="x", pady=2)
        ctk.CTkLabel(fv, text="Folder Val", font=(UI_FONT, 11), text_color=TEXT_DIM,
                     width=110, anchor="w").pack(side="left")
        self._jilsa_val_folder_var = tk.StringVar(value="test")
        ctk.CTkComboBox(fv, variable=self._jilsa_val_folder_var,
                        values=["val", "test", "valid"], state="readonly",
                        font=(UI_FONT, 11), width=100,
                        fg_color=INPUT_BG, border_color=BORDER,
                        button_color=BG3, button_hover_color=ACCENT,
                        text_color=TEXT, dropdown_fg_color=BG3,
                        dropdown_text_color=TEXT).pack(side="left")

        # ── LEFT: Hyperparameters ─────────────────────────────────────────────
        build_section_label(ctk, left, "⚙ Hyperparameters — JILSA 2022")

        self._jilsa_imgsz_var    = tk.IntVar(value=200)
        self._jilsa_batch_var    = tk.IntVar(value=64)
        self._jilsa_epochs_var   = tk.IntVar(value=50)
        self._jilsa_lr_var       = tk.DoubleVar(value=0.001)
        self._jilsa_patience_var = tk.IntVar(value=10)
        self._jilsa_workers_var  = tk.IntVar(value=0)
        self._jilsa_amp_var      = tk.BooleanVar(value=True)
        self._jilsa_cos_lr_var   = tk.BooleanVar(value=True)

        _spin_row("Img Size",        self._jilsa_imgsz_var,     32, 640, 8)
        _spin_row("Batch Size",      self._jilsa_batch_var,      1, 256)
        _spin_row("Epochs",          self._jilsa_epochs_var,     1, 500)
        _spin_row("LR (Adam)",       self._jilsa_lr_var,    0.0001, 0.1, 0.0001)
        _spin_row("Early Stop Pat.", self._jilsa_patience_var,   0,  50)
        _spin_row("Workers",         self._jilsa_workers_var,    0,  16)

        # Device row
        fd = ctk.CTkFrame(left, fg_color="transparent")
        fd.pack(fill="x", pady=2)
        ctk.CTkLabel(fd, text="Device", font=(UI_FONT, 11), text_color=TEXT_DIM,
                     width=130, anchor="w").pack(side="left")
        self._jilsa_device_var = tk.StringVar(value="cuda")
        ctk.CTkComboBox(fd, variable=self._jilsa_device_var,
                        values=["cuda", "cpu"], state="readonly",
                        font=(UI_FONT, 11), width=100,
                        fg_color=INPUT_BG, border_color=BORDER,
                        button_color=BG3, button_hover_color=ACCENT,
                        text_color=TEXT, dropdown_fg_color=BG3,
                        dropdown_text_color=TEXT).pack(side="left")

        # Checkboxes
        chk_row = ctk.CTkFrame(left, fg_color="transparent")
        chk_row.pack(fill="x", pady=(6, 2))
        ctk.CTkCheckBox(chk_row, text="AMP", variable=self._jilsa_amp_var,
                        font=(UI_FONT, 11), text_color=TEXT_DIM,
                        fg_color=ACCENT, hover_color=ACCENT2,
                        border_color=BORDER, checkmark_color="white").pack(side="left")
        ctk.CTkCheckBox(chk_row, text="Cosine LR", variable=self._jilsa_cos_lr_var,
                        font=(UI_FONT, 11), text_color=TEXT_DIM,
                        fg_color=ACCENT, hover_color=ACCENT2,
                        border_color=BORDER, checkmark_color="white").pack(side="left", padx=(10, 0))

        # ── Output dir ────────────────────────────────────────────────────────
        build_section_label(ctk, left, "💾 Lưu kết quả (.pth)")
        f_out = ctk.CTkFrame(left, fg_color="transparent")
        f_out.pack(fill="x", pady=2)
        self._jilsa_out_var = tk.StringVar(value=str(OUTPUT_DIR / "jilsa_cnn"))
        ctk.CTkEntry(f_out, textvariable=self._jilsa_out_var,
                     font=(UI_FONT, 10), fg_color=INPUT_BG,
                     border_color=BORDER, text_color=TEXT).pack(
            side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(f_out, text="📁", width=32, height=28,
                      font=(UI_FONT, 11), fg_color=BG3, hover_color=BG4,
                      text_color=TEXT, corner_radius=6,
                      command=self._jilsa_browse_output).pack(side="left")

        # ── Action buttons ────────────────────────────────────────────────────
        ctk.CTkFrame(left, fg_color=BORDER, height=1).pack(fill="x", pady=(12, 8))

        self._jilsa_start_btn = ctk.CTkButton(
            left, text="▶  Bắt đầu Train CNN",
            font=(UI_FONT, 13, "bold"), height=42,
            fg_color=ACCENT, hover_color=ACCENT2,
            text_color="white", corner_radius=8,
            command=self._start_jilsa,
        )
        self._jilsa_start_btn.pack(fill="x", pady=(0, 4))

        self._jilsa_stop_btn = ctk.CTkButton(
            left, text="⏹  Dừng lại",
            font=(UI_FONT, 13, "bold"), height=38,
            fg_color=DANGER, hover_color="#cc3333",
            text_color="white", corner_radius=8,
            command=self._stop_jilsa, state="disabled",
        )
        self._jilsa_stop_btn.pack(fill="x", pady=(0, 4))

        ctk.CTkButton(
            left, text="🗑  Xóa Log",
            font=(UI_FONT, 11), height=32,
            fg_color=BG3, hover_color=BG4,
            text_color=TEXT_DIM, corner_radius=8,
            command=self._jilsa_clear_log,
        ).pack(fill="x", pady=(0, 4))

        self._jilsa_status_lbl = ctk.CTkLabel(
            left, text="⏹ Chưa chạy",
            font=(UI_FONT, 11, "bold"), text_color=TEXT_DIM,
        )
        self._jilsa_status_lbl.pack(anchor="w", pady=(6, 0))

        # ── RIGHT: Epoch counter + progress + log ─────────────────────────────
        (self._jilsa_epoch_lbl,
         self._jilsa_pct_lbl,
         self._jilsa_elapsed_lbl,
         self._jilsa_acc_lbl,
         self._jilsa_prog_lbl,
         self._jilsa_progressbar) = build_epoch_header_ctk(
            ctk, right,
            epoch_lbl_attr="_jilsa_epoch_lbl",
            pct_lbl_attr="_jilsa_pct_lbl",
            elapsed_lbl_attr="_jilsa_elapsed_lbl",
            acc_lbl_attr="_jilsa_acc_lbl",
            prog_lbl_attr="_jilsa_prog_lbl",
            accent_color=ACCENT2,
        )

        self._jilsa_log = build_log_textbox(
            ctk, right,
            title="📋 JILSA 2022 Custom CNN Log",
            accent_color=ACCENT2,
            tags=[("best", "#fbbf24")],
        )

    # ── JILSA helpers ─────────────────────────────────────────────────────────
    def _jilsa_browse_data(self):
        d = filedialog.askdirectory(title="Chọn dataset folder (có train/ val/)")
        if d: self._jilsa_data_var.set(d)

    def _jilsa_browse_output(self):
        d = filedialog.askdirectory(title="Chọn folder lưu model .pth")
        if d: self._jilsa_out_var.set(d)

    def _jilsa_log_write(self, text: str, tag: str = ""):
        self._jilsa_log.configure(state="normal")
        if tag: self._jilsa_log.insert("end", text, tag)
        else:   self._jilsa_log.insert("end", text)
        self._jilsa_log.configure(state="disabled")
        self._jilsa_log.see("end")

    def _jilsa_clear_log(self):
        self._jilsa_log.configure(state="normal")
        self._jilsa_log.delete("1.0", "end")
        self._jilsa_log.configure(state="disabled")

    # ── JILSA training (unchanged logic) ──────────────────────────────────────
    def _start_jilsa(self):
        try:
            payload = prepare_jilsa_training({
                "data_path": self._jilsa_data_var.get(),
                "val_folder": self._jilsa_val_folder_var.get(),
                "imgsz": self._jilsa_imgsz_var.get(),
                "batch": self._jilsa_batch_var.get(),
                "epochs": self._jilsa_epochs_var.get(),
                "lr": self._jilsa_lr_var.get(),
                "patience": self._jilsa_patience_var.get(),
                "workers": self._jilsa_workers_var.get(),
                "device": self._jilsa_device_var.get(),
                "out_dir": self._jilsa_out_var.get(),
                "amp": self._jilsa_amp_var.get(),
                "cos_lr": self._jilsa_cos_lr_var.get(),
            })
        except ValueError as ex:
            messagebox.showerror("Lỗi", str(ex))
            return

        self._jilsa_training = True
        self._jilsa_start_btn.configure(state="disabled")
        self._jilsa_stop_btn.configure(state="normal")
        self._jilsa_status_lbl.configure(text="🔄 Đang train...", text_color=WARNING)
        self._jilsa_start_time = time.time()
        self._jilsa_current_epochs = payload["epochs"]
        self._jilsa_progressbar.set(0)
        self._jilsa_epoch_lbl.configure(text=f"0 / {payload['epochs']}")
        self._jilsa_pct_lbl.configure(text="0%")
        self._jilsa_acc_lbl.configure(text="Val Acc: —" if payload["use_validation"] else "Val Acc: N/A")
        self._jilsa_elapsed_lbl.configure(text="")

        self._jilsa_log_write(f"\n{'='*60}\n", "dim")
        self._jilsa_log_write(f"  JILSA 2022 — Custom CNN (PyTorch)\n", "info")
        self._jilsa_log_write(f"  Dataset  : {payload['data_path']}\n", "info")
        if payload["raw_data_path"] != payload["data_path"]:
            self._jilsa_log_write(f"  Input    : {payload['raw_data_path']} -> auto doi ve dataset root\n", "dim")
        self._jilsa_log_write(f"  ImgSz    : {payload['imgsz']}  Batch: {payload['batch']}  Epochs: {payload['epochs']}\n", "info")
        self._jilsa_log_write(f"  LR (Adam): {payload['lr']:.4f}  Early Stop: {payload['patience']}\n", "info")
        self._jilsa_log_write(f"  Device   : {payload['device'].upper()}  Workers: {payload['workers']}\n", "info")
        self._jilsa_log_write(f"  AMP      : {payload['amp']}  Cosine LR: {payload['cos_lr']}\n", "info")
        self._jilsa_log_write(
            f"  Validation: {'Dung ' + payload['val_folder'] + '/' if payload['use_validation'] else 'Bo qua ' + payload['val_folder'] + '/ vi khong co anh hop le; chi train tren train/'}\n",
            "info",
        )
        self._jilsa_log_write(f"{'='*60}\n\n", "dim")
        threading.Thread(target=self._run_jilsa, args=(payload["script"], payload["epochs"]), daemon=True).start()

    def _run_jilsa(self, script: str, total_epochs: int):
        retcode, ex = stream_inline_job(
            script,
            str(PYTHON_EXE),
            str(ROOT_DIR),
            lambda line: self._jilsa_parse_line(line, total_epochs),
            lambda: self._jilsa_training,
            on_process_started=lambda proc: setattr(self, "_jilsa_process", proc),
            unbuffered=True,
            force_utf8=True,
        )
        if ex is not None:
            self.after(0, self._jilsa_log_write, f"\n[ERROR] {ex}\n", "err")
        self.after(0, self._on_jilsa_done, retcode)

    def _jilsa_parse_line(self, line: str, total_epochs: int):
        stripped = line.rstrip()
        tag = detect_stream_tag(line)
        self.after(0, self._jilsa_log_write, stripped + "\n", tag)
        progress = parse_epoch_progress(line, self._jilsa_start_time)
        if progress:
            self.after(0, self._jilsa_update_progress,
                       progress["cur"], progress["tot"], progress["pct"], progress["acc_str"],
                       self._fmt_time(progress["elapsed"]), self._fmt_time(progress["eta_s"]))

    def _jilsa_update_progress(self, cur, tot, pct, acc_str, elapsed_str, eta):
        self._jilsa_progressbar.set(pct / 100)
        self._jilsa_prog_lbl.configure(text=f"Epoch {cur} / {tot}  ({pct}%)")
        self._jilsa_epoch_lbl.configure(text=f"{cur} / {tot}")
        self._jilsa_pct_lbl.configure(text=f"{pct}%")
        if acc_str:
            self._jilsa_acc_lbl.configure(text=f"Val Acc: {acc_str}")
        self._jilsa_elapsed_lbl.configure(text=f"⏱ {elapsed_str}  |  ETA: {eta}")

    def _on_jilsa_done(self, retcode: int):
        self._jilsa_training = False
        self._jilsa_start_btn.configure(state="normal")
        self._jilsa_stop_btn.configure(state="disabled")
        if retcode == 0:
            self._jilsa_progressbar.set(1.0)
            self._jilsa_pct_lbl.configure(text="100%")
            self._jilsa_status_lbl.configure(text="✓ Hoàn thành!", text_color=SUCCESS)
            self._jilsa_log_write("\n✓ JILSA CNN training hoàn thành!\n", "ok")
            elapsed = self._fmt_time(time.time() - self._jilsa_start_time)
            self._jilsa_log_write(f"⏱ Tổng thời gian: {elapsed}\n", "info")
            messagebox.showinfo("Xong!", f"JILSA 2022 Custom CNN hoàn thành!\nModel lưu tại:\n{self._jilsa_out_var.get()}")
        else:
            self._jilsa_status_lbl.configure(text="✗ Lỗi / Đã dừng", text_color=DANGER)
            self._jilsa_log_write(f"\n✗ Kết thúc bất thường (code {retcode})\n", "err")

    def _stop_jilsa(self):
        if self._jilsa_process and self._jilsa_process.poll() is None:
            self._jilsa_training = False
            self._jilsa_process.terminate()
            self._jilsa_log_write("\n⏹ Đã gửi lệnh dừng...\n", "warn")
            self._jilsa_status_lbl.configure(text="⏹ Đang dừng...", text_color=WARNING)
