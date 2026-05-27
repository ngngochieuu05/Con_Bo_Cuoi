"""tools.py — Tiện ích dataset: copy + đổi tên ảnh an toàn."""
from __future__ import annotations

import sys
import threading
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, messagebox

SRC_DIR = Path(__file__).resolve().parents[2]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from bll.tools.augment_service import (
    AUGMENT_PIPELINES,
    augment_dataset_albumentations,
    count_dataset_images,
)
from bll.tools.copy_service import copy_dataset_safe
from bll.tools.split_service import read_split_ratio, run_split_dataset

from ui.ui_theme import (
    ACCENT,
    BG,
    BG2,
    BG3,
    BG4,
    BORDER,
    DANGER,
    INFO,
    SUCCESS,
    TEXT,
    TEXT_DIM,
    WARNING,
    build_app_taskbar,
    build_dashboard_banner,
    build_empty_state,
    build_metric_strip,
    build_page_body,
    build_tabview,
    silence_console_output,
    setup_ctk,
)

# ── theme ──────────────────────────────────────────────────────────────────────
PRIMARY = ACCENT

setup_ctk(ctk)
silence_console_output()



# ══════════════════════════════════════════════════════════════════════════════
#  GUI
# ══════════════════════════════════════════════════════════════════════════════

class ToolsApp(ctk.CTk):
    """Tiện ích dataset — copy + đổi tên ảnh an toàn."""

    def __init__(self):
        super().__init__()
        self.title("Con Bò Cười - Công cụ dữ liệu")
        self.geometry("1380x900")
        self.minsize(1100, 720)
        self.configure(fg_color=BG)
        self._running = False
        self._augment_running = False
        self._stop_requested = False
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        host = ctk.CTkFrame(self, fg_color="transparent")
        host.pack(fill="both", expand=True)

        hdr, _ = build_app_taskbar(
            ctk,
            host,
            title="Con Bò Cười - Công cụ dữ liệu",
            subtitle="Tiện ích tiền xử lý dataset, chia tỉ lệ và augment ảnh theo một giao diện đồng bộ.",
            status_text=None,
        )
        hdr.pack(fill="x", padx=18, pady=(18, 0))

        metrics = build_metric_strip(
            ctk,
            host,
            [
                {"title": "Pipelines", "value": "3", "hint": "Copy, Split, Augment", "accent": ACCENT},
                {"title": "Safety", "value": "Non-destructive", "hint": "Copy-first workflow", "accent": SUCCESS},
                {"title": "Augment", "value": "Albumentations", "hint": "Batch image synthesis", "accent": WARNING},
            ],
            columns=3,
        )
        metrics.pack(fill="x", padx=18, pady=(14, 8))

        self._tabview = build_tabview(ctk, host)
        self._tabview.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        self._tabview.add("Sao chép dữ liệu")
        self._tabview.add("Chia tỉ lệ")
        self._tabview.add("Tăng cường ảnh")

        self._build_copy_tab(build_page_body(ctk, self._tabview.tab("Sao chép dữ liệu"), padx=6, pady=8))
        self._build_split_tab(build_page_body(ctk, self._tabview.tab("Chia tỉ lệ"), padx=6, pady=8))
        self._build_augment_tab(build_page_body(ctk, self._tabview.tab("Tăng cường ảnh"), padx=6, pady=8))

    def _build_copy_tab(self, parent):
        banner = build_dashboard_banner(
            ctk,
            parent,
            eyebrow="SAO CHÉP DỮ LIỆU",
            title="Luồng sao chép và đổi tên dữ liệu an toàn",
            description="Chọn thư mục nguồn, quyết định có thêm tiền tố tên lớp hay không, sau đó chạy sao chép có kiểm soát với tiến trình và log rõ ràng.",
            accent=ACCENT,
            compact=True,
        )
        banner.pack(fill="x", padx=12, pady=(8, 10))

        self._build_folder_row(parent, "📂 Thư mục nguồn *", is_source=True)
        self._build_folder_row(parent, "📁 Thư mục đích  (để trống = tự tạo)", is_source=False)

        opt_row = ctk.CTkFrame(parent, fg_color="transparent")
        opt_row.pack(fill="x", padx=20, pady=(6, 0))

        self._prefix_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            opt_row,
            text="Thêm tên class vào đầu tên file  (khuyến nghị)",
            variable=self._prefix_var,
            font=("Segoe UI", 12),
            text_color=TEXT,
            fg_color=PRIMARY,
            hover_color="#e11d48",
            checkmark_color="white",
            border_color=BORDER,
        ).pack(side="left")

        btn_row = ctk.CTkFrame(parent, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(14, 8))

        self._run_btn = ctk.CTkButton(
            btn_row, text="▶ Chạy",
            corner_radius=999, height=40,
            fg_color=PRIMARY, hover_color="#e11d48",
            text_color="white", font=("Segoe UI", 13, "bold"),
            command=self._on_run,
        )
        self._run_btn.pack(side="left", padx=(0, 10))

        self._stop_btn = ctk.CTkButton(
            btn_row, text="■ Dừng",
            corner_radius=999, height=40,
            fg_color=DANGER, hover_color="#cc0000",
            text_color="white", font=("Segoe UI", 13, "bold"),
            state="disabled",
            command=self._on_stop,
        )
        self._stop_btn.pack(side="left", padx=(0, 20))

        self._status_lbl = ctk.CTkLabel(
            btn_row, text="Sẵn sàng.", font=("Segoe UI", 12), text_color=TEXT_DIM,
        )
        self._status_lbl.pack(side="left")

        self._clear_btn = ctk.CTkButton(
            btn_row, text="🗑 Xóa log",
            corner_radius=999, height=34,
            fg_color=BG3, hover_color=BORDER,
            text_color=TEXT_DIM, font=("Segoe UI", 11),
            command=self._clear_log,
        )
        self._clear_btn.pack(side="right")

        self._progress = ctk.CTkProgressBar(parent, fg_color=BG3, progress_color=PRIMARY)
        self._progress.set(0)
        self._progress.pack(fill="x", padx=20, pady=(0, 8))

        log_lbl = ctk.CTkLabel(parent, text="Log:", font=("Segoe UI", 11, "bold"),
                               text_color=TEXT_DIM)
        log_lbl.pack(anchor="w", padx=22, pady=(0, 2))

        self._log_box = ctk.CTkTextbox(
            parent, font=("Consolas", 11),
            fg_color="#1e1e2e", text_color="#e2e8f0",
            corner_radius=10, border_width=1, border_color=BORDER,
            activate_scrollbars=True,
        )
        self._log_box.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        self._log_box.configure(state="disabled")

    def _build_split_tab(self, parent):
        banner = build_dashboard_banner(
            ctk,
            parent,
            eyebrow="PHÂN TÍCH TỈ LỆ",
            title="Kiểm tra nhanh tỉ lệ train/val/test hiện có",
            description="Đọc cấu trúc dataset hoặc đường dẫn liên kết và hiển thị tỉ lệ chia hiện tại trước khi chạy bất kỳ thao tác ghi nào.",
            accent=INFO,
            compact=True,
        )
        banner.pack(fill="x", padx=12, pady=(8, 10))

        self._split_src_var = ctk.StringVar()

        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(20, 0))

        ctk.CTkLabel(row, text="📂 Dataset root hoặc đường dẫn liên kết:",
                     font=("Segoe UI", 12, "bold"), text_color=TEXT,
                     width=260, anchor="w").pack(side="left")

        entry = ctk.CTkEntry(row, textvariable=self._split_src_var,
                             font=("Segoe UI", 11), fg_color=BG3,
                             border_color=BORDER, text_color=TEXT,
                             placeholder_text="Nhập đường dẫn hoặc dán link dataset…")
        entry.pack(side="left", fill="x", expand=True, padx=(8, 6))
        ctk.CTkButton(row, text="📂", width=36, height=32,
                      fg_color=BG3, hover_color=BORDER, text_color=TEXT,
                      corner_radius=8,
                      command=self._browse_split_source).pack(side="left")

        btn_row = ctk.CTkFrame(parent, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(12, 8))

        ctk.CTkButton(
            btn_row, text="📊 Đọc tỉ lệ split",
            corner_radius=999, height=40,
            fg_color=INFO, hover_color="#38bdf8",
            text_color="white", font=("Segoe UI", 13, "bold"),
            command=self._on_read_split,
        ).pack(side="left")

        self._split_result_box = ctk.CTkTextbox(
            parent, font=("Consolas", 11),
            fg_color="#1e1e2e", text_color="#e2e8f0",
            corner_radius=10, border_width=1, border_color=BORDER,
            activate_scrollbars=True,
            height=220,
        )
        self._split_result_box.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        self._split_result_box.configure(state="disabled")

        hint = build_empty_state(
            ctk,
            parent,
            title="Gợi ý",
            description="Dùng tab này để kiểm tra nhanh tỉ lệ dataset. Luồng split đầy đủ vẫn đang có sẵn trong mã nguồn và có thể đưa lên giao diện sau mà không phải đổi logic nghiệp vụ.",
            accent=INFO,
        )
        hint.pack(fill="x", padx=20, pady=(0, 16))

    def _build_dataset_split_tab(self, parent):
        self._split_src_var = ctk.StringVar(value=r"D:\DACS\Dataset\desease\so_sanh\2.lumpy\classification")
        self._split_dst_var = ctk.StringVar(value="")
        self._split_train_var = ctk.DoubleVar(value=0.70)
        self._split_val_var = ctk.DoubleVar(value=0.15)
        self._split_test_var = ctk.DoubleVar(value=0.15)
        self._split_seed_var = ctk.IntVar(value=42)
        self._split_move_var = ctk.BooleanVar(value=False)
        self._split_yaml_var = ctk.BooleanVar(value=True)
        self._split_sum_var = ctk.StringVar(value="Tong: 1.00")
        self._split_status_var = ctk.StringVar(value="Sẵn sàng.")
        self._split_stats_var = ctk.StringVar(value="Class  |  Total  |  Train  |  Val  |  Test")

        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=8, pady=8)

        hero = ctk.CTkFrame(scroll, fg_color=BG3, corner_radius=14, border_width=1, border_color=BORDER)
        hero.pack(fill="x", padx=12, pady=(8, 10))
        ctk.CTkLabel(hero, text="Split Dataset train / val / test", font=("Segoe UI", 18, "bold"), text_color=TEXT).pack(anchor="w", padx=14, pady=(12, 4))
        ctk.CTkLabel(hero, text="Tach dataset classification theo ty le co dinh, giu cau truc class va co the tao data.yaml ngay sau khi split.", font=("Segoe UI", 12), text_color=TEXT_DIM, justify="left", wraplength=860).pack(anchor="w", padx=14, pady=(0, 12))

        self._build_aug_path_row(scroll, "📂 Thư mục nguồn *", self._split_src_var, self._browse_split_source)
        self._build_aug_path_row(scroll, "📁 Thư mục đích", self._split_dst_var, self._browse_split_dest)

        ratio_card = ctk.CTkFrame(scroll, fg_color=BG3, corner_radius=14, border_width=1, border_color=BORDER)
        ratio_card.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkLabel(ratio_card, text="Tỷ lệ split", font=("Segoe UI", 14, "bold"), text_color=TEXT).pack(anchor="w", padx=14, pady=(10, 8))
        ratio_row = ctk.CTkFrame(ratio_card, fg_color="transparent")
        ratio_row.pack(fill="x", padx=12, pady=(0, 6))
        self._build_aug_numeric(ratio_row, "Train", self._split_train_var, 0.0, 1.0)
        self._build_aug_numeric(ratio_row, "Val", self._split_val_var, 0.0, 1.0)
        self._build_aug_numeric(ratio_row, "Test", self._split_test_var, 0.0, 1.0)
        self._build_aug_numeric(ratio_row, "Seed", self._split_seed_var, 0, 99999)
        ctk.CTkLabel(ratio_card, textvariable=self._split_sum_var, font=("Segoe UI", 12, "bold"), text_color=SUCCESS).pack(anchor="w", padx=14, pady=(0, 10))
        for var in (self._split_train_var, self._split_val_var, self._split_test_var):
            var.trace_add("write", self._update_split_sum)
        self._update_split_sum()

        opt_card = ctk.CTkFrame(scroll, fg_color=BG3, corner_radius=14, border_width=1, border_color=BORDER)
        opt_card.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkLabel(opt_card, text="Tùy chọn", font=("Segoe UI", 14, "bold"), text_color=TEXT).pack(anchor="w", padx=14, pady=(10, 8))
        ctk.CTkCheckBox(opt_card, text="Move thay vì Copy", variable=self._split_move_var, font=("Segoe UI", 12), text_color=TEXT, fg_color=PRIMARY, hover_color="#e11d48", checkmark_color="white", border_color=BORDER).pack(anchor="w", padx=14, pady=4)
        ctk.CTkCheckBox(opt_card, text="Tự tạo data.yaml", variable=self._split_yaml_var, font=("Segoe UI", 12), text_color=TEXT, fg_color=PRIMARY, hover_color="#e11d48", checkmark_color="white", border_color=BORDER).pack(anchor="w", padx=14, pady=(0, 10))

        btn_row = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(4, 8))
        self._split_run_btn = ctk.CTkButton(btn_row, text="✂ Chạy split", corner_radius=999, height=40, fg_color=INFO, hover_color="#38bdf8", text_color="white", font=("Segoe UI", 13, "bold"), command=self._start_split)
        self._split_run_btn.pack(side="left")
        ctk.CTkButton(btn_row, text="🗑 Xóa log", corner_radius=999, height=36, fg_color=BG3, hover_color=BORDER, text_color=TEXT_DIM, font=("Segoe UI", 11), command=self._clear_split_log).pack(side="left", padx=(10, 0))
        ctk.CTkLabel(btn_row, textvariable=self._split_status_var, font=("Segoe UI", 12), text_color=TEXT_DIM).pack(side="left", padx=18)

        self._split_progress = ctk.CTkProgressBar(scroll, fg_color=BG3, progress_color=INFO)
        self._split_progress.set(0)
        self._split_progress.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(scroll, textvariable=self._split_stats_var, font=("Consolas", 11, "bold"), text_color=INFO, justify="left").pack(anchor="w", padx=16, pady=(0, 6))

        self._split_result_box = ctk.CTkTextbox(scroll, font=("Consolas", 11), fg_color="#1e1e2e", text_color="#e2e8f0", corner_radius=10, border_width=1, border_color=BORDER, activate_scrollbars=True, height=260)
        self._split_result_box.pack(fill="both", expand=True, padx=12, pady=(0, 16))
        self._split_result_box.configure(state="disabled")

    def _build_split_tab(self, parent):
        self._build_dataset_split_tab(parent)

    def _update_split_sum(self, *_args):
        total = round(float(self._split_train_var.get()) + float(self._split_val_var.get()) + float(self._split_test_var.get()), 2)
        self._split_sum_var.set(f"Tong: {total:.2f}")

    def _write_split_log(self, text: str):
        self._split_result_box.configure(state="normal")
        self._split_result_box.insert("end", text)
        self._split_result_box.configure(state="disabled")
        self._split_result_box.see("end")

    def _clear_split_log(self):
        self._split_result_box.configure(state="normal")
        self._split_result_box.delete("0.0", "end")
        self._split_result_box.configure(state="disabled")
        self._split_progress.set(0)
        self._split_stats_var.set("Class  |  Total  |  Train  |  Val  |  Test")
        self._split_status_var.set("Sẵn sàng.")

    def _browse_split_source(self):
        d = filedialog.askdirectory(title="Chọn thư mục nguồn để split")
        if d:
            self._split_src_var.set(d)

    def _browse_split_dest(self):
        d = filedialog.askdirectory(title="Chọn thư mục đích sau khi split")
        if d:
            self._split_dst_var.set(d)

    def _start_split(self):
        src = self._split_src_var.get().strip()
        if not src:
            messagebox.showerror("Lỗi", "Chưa chọn thư mục nguồn.")
            return
        src_path = Path(src)
        if not src_path.is_dir():
            messagebox.showerror("Lỗi", f"Thư mục không tồn tại:\n{src}")
            return

        total_ratio = round(float(self._split_train_var.get()) + float(self._split_val_var.get()) + float(self._split_test_var.get()), 2)
        if abs(total_ratio - 1.0) >= 0.01:
            messagebox.showerror("Lỗi", f"Tổng tỷ lệ phải bằng 1.0, hiện tại = {total_ratio:.2f}")
            return

        dst = self._split_dst_var.get().strip()
        self._clear_split_log()
        self._split_run_btn.configure(state="disabled")
        self._split_status_var.set("Đang split...")
        self._write_split_log("=" * 60 + "\n")
        self._write_split_log(f"  Source : {src}\n")
        self._write_split_log(f"  Output : {dst or '(auto: source_split)'}\n")
        self._write_split_log(f"  Ratio  : Train {float(self._split_train_var.get()):.0%} / Val {float(self._split_val_var.get()):.0%} / Test {float(self._split_test_var.get()):.0%}\n")
        self._write_split_log(f"  Seed   : {int(self._split_seed_var.get())}  |  Move: {bool(self._split_move_var.get())}  |  Gen YAML: {bool(self._split_yaml_var.get())}\n")
        self._write_split_log("=" * 60 + "\n\n")

        threading.Thread(
            target=self._run_split_worker,
            args=(
                src,
                dst,
                float(self._split_train_var.get()),
                float(self._split_val_var.get()),
                float(self._split_test_var.get()),
                int(self._split_seed_var.get()),
                bool(self._split_move_var.get()),
                bool(self._split_yaml_var.get()),
            ),
            daemon=True,
        ).start()

    def _run_split_worker(self, src, dst, train_r, val_r, test_r, seed, move, gen_yaml):
        try:
            result = run_split_dataset(
                src,
                dst,
                train_r,
                val_r,
                test_r,
                seed,
                move,
                gen_yaml,
                progress_callback=lambda value: self.after(0, self._split_progress.set, value),
                log_callback=lambda line: self.after(0, self._write_split_log, line + "\n"),
            )
            self.after(
                0,
                self._finish_split,
                True,
                None,
                result["total_imgs"],
                result["out_path"],
                result["yaml_path"],
                result["summary_rows"],
            )
        except Exception as exc:
            self.after(0, self._finish_split, False, str(exc), None, None, None, None)

    def _finish_split(self, success: bool, error_message=None, total_imgs=None, out_path=None, yaml_path=None, summary_rows=None):
        self._split_run_btn.configure(state="normal")
        if not success:
            self._split_status_var.set("Lỗi.")
            if error_message:
                self._write_split_log(f"[ERROR] {error_message}\n")
                messagebox.showerror("Lỗi split", error_message)
            return

        self._split_progress.set(1)
        rows = summary_rows or []
        self._split_stats_var.set("\n".join(["Class                 | Total | Train | Val | Test"] + rows[:6]))
        self._split_status_var.set("Hoàn thành.")
        self._write_split_log("\n" + "=" * 60 + "\n")
        self._write_split_log(f"Hoan thanh: {total_imgs} anh\n")
        self._write_split_log(f"Output: {Path(out_path).resolve()}\n")
        if yaml_path:
            self._write_split_log(f"data.yaml: {Path(yaml_path).resolve()}\n")
        messagebox.showinfo("Xong!", f"Split thành công.\nOutput: {Path(out_path).resolve()}")

    def _build_augment_tab(self, parent):
        self._aug_src_var = ctk.StringVar()
        self._aug_dst_var = ctk.StringVar()
        self._aug_keep_original_var = ctk.BooleanVar(value=True)
        self._aug_width_var = ctk.IntVar(value=224)
        self._aug_height_var = ctk.IntVar(value=224)
        self._aug_pipeline_multiplier_vars = {}
        self._aug_option_vars = {
            "rotate": ctk.BooleanVar(value=True),
            "zoom": ctk.BooleanVar(value=True),
            "hflip": ctk.BooleanVar(value=True),
            "vflip": ctk.BooleanVar(value=True),
            "brightness": ctk.BooleanVar(value=True),
            "contrast": ctk.BooleanVar(value=True),
            "hsv": ctk.BooleanVar(value=True),
            "noise": ctk.BooleanVar(value=True),
            "dropout": ctk.BooleanVar(value=True),
        }
        for key in AUGMENT_PIPELINES:
            self._aug_pipeline_multiplier_vars[key] = ctk.IntVar(value=4)
        self._aug_estimate_var = ctk.StringVar(value="Chon thu muc nguon de uoc tinh so anh.")

        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=6, pady=6)

        banner = build_dashboard_banner(
            ctk,
            scroll,
            eyebrow="TĂNG CƯỜNG ẢNH",
            title="Tạo ảnh hàng loạt với điều khiển theo từng pipeline",
            description="Tinh chỉnh resize, chế độ giữ ảnh gốc và hệ số nhân của từng pipeline. Giao diện hiển thị ước tính đầu ra trước khi bắt đầu chạy augment.",
            accent=WARNING,
            compact=True,
        )
        banner.pack(fill="x", padx=12, pady=(6, 10))

        self._build_aug_path_row(scroll, "📂 Thư mục nguồn *", self._aug_src_var, self._browse_aug_source)
        self._build_aug_path_row(scroll, "📁 Thư mục đích *", self._aug_dst_var, self._browse_aug_dest)

        basic_card = ctk.CTkFrame(scroll, fg_color=BG3, corner_radius=14, border_width=1, border_color=BORDER)
        basic_card.pack(fill="x", padx=12, pady=(8, 10))
        ctk.CTkLabel(basic_card, text="Cấu hình cơ bản", font=("Segoe UI", 14, "bold"), text_color=TEXT).pack(anchor="w", padx=14, pady=(10, 8))
        row = ctk.CTkFrame(basic_card, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(0, 10))
        self._build_aug_numeric(row, "Resize W", self._aug_width_var, 32, 2048)
        self._build_aug_numeric(row, "Resize H", self._aug_height_var, 32, 2048)
        ctk.CTkCheckBox(
            row,
            text="Giữ ảnh gốc",
            variable=self._aug_keep_original_var,
            font=("Segoe UI", 12),
            text_color=TEXT,
            fg_color=PRIMARY,
            hover_color="#e11d48",
            checkmark_color="white",
            border_color=BORDER,
            command=self._update_aug_estimate,
        ).pack(side="left", padx=(18, 0), pady=8)
        hint = ctk.CTkFrame(scroll, fg_color=BG3, corner_radius=14, border_width=1, border_color=BORDER)
        hint.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkLabel(
            hint,
            text="Pipeline đang dùng",
            font=("Segoe UI", 14, "bold"),
            text_color=TEXT,
        ).pack(anchor="w", padx=14, pady=(10, 6))
        ctk.CTkLabel(
            hint,
            text="Moi pipeline tao ra mot nhom anh rieng. So luong anh nhan ban se cap nhat ngay khi tick hoac bo tick.",
            font=("Segoe UI", 12),
            text_color=TEXT_DIM,
            justify="left",
            wraplength=860,
        ).pack(anchor="w", padx=14, pady=(0, 10))

        pipeline_grid = ctk.CTkFrame(hint, fg_color="transparent")
        pipeline_grid.pack(fill="x", padx=12, pady=(0, 10))
        for idx, (key, meta) in enumerate(AUGMENT_PIPELINES.items()):
            item = ctk.CTkFrame(pipeline_grid, fg_color=BG2, corner_radius=10, border_width=1, border_color=BORDER)
            item.grid(row=idx // 2, column=idx % 2, padx=8, pady=6, sticky="ew")
            pipeline_grid.grid_columnconfigure(idx % 2, weight=1)
            ctk.CTkCheckBox(
                item,
                text=f"{meta['label']} - {meta['note']}",
                variable=self._aug_option_vars[key],
                font=("Segoe UI", 12),
                text_color=TEXT,
                fg_color=PRIMARY,
                hover_color="#e11d48",
                checkmark_color="white",
                border_color=BORDER,
                command=self._update_aug_estimate,
            ).pack(side="left", fill="x", expand=True, padx=(10, 8), pady=8)
            ctk.CTkLabel(
                item,
                text="Lan:",
                font=("Segoe UI", 11, "bold"),
                text_color=TEXT_DIM,
            ).pack(side="left", padx=(0, 4))
            ctk.CTkEntry(
                item,
                textvariable=self._aug_pipeline_multiplier_vars[key],
                width=56,
                font=("Segoe UI", 11),
                fg_color=BG3,
                border_color=BORDER,
                text_color=TEXT,
            ).pack(side="left", padx=(0, 10), pady=8)

        estimate_card = ctk.CTkFrame(scroll, fg_color=BG3, corner_radius=14, border_width=1, border_color=BORDER)
        estimate_card.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkLabel(
            estimate_card,
            text="Uoc tinh dau ra",
            font=("Segoe UI", 14, "bold"),
            text_color=TEXT,
        ).pack(anchor="w", padx=14, pady=(10, 6))
        ctk.CTkLabel(
            estimate_card,
            textvariable=self._aug_estimate_var,
            font=("Segoe UI", 12),
            text_color=TEXT_DIM,
            justify="left",
            wraplength=860,
        ).pack(anchor="w", padx=14, pady=(0, 10))

        btn_row = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(8, 8))
        self._aug_run_btn = ctk.CTkButton(
            btn_row,
            text="▶ Chạy augment",
            corner_radius=999,
            height=40,
            fg_color=PRIMARY,
            hover_color="#e11d48",
            text_color="white",
            font=("Segoe UI", 13, "bold"),
            command=self._on_augment_run,
        )
        self._aug_run_btn.pack(side="left")
        self._aug_stop_btn = ctk.CTkButton(
            btn_row,
            text="■ Dừng",
            corner_radius=999,
            height=40,
            fg_color=DANGER,
            hover_color="#cc0000",
            text_color="white",
            font=("Segoe UI", 13, "bold"),
            state="disabled",
            command=self._on_augment_stop,
        )
        self._aug_stop_btn.pack(side="left", padx=(10, 18))
        self._aug_status_lbl = ctk.CTkLabel(btn_row, text="Sẵn sàng.", font=("Segoe UI", 12), text_color=TEXT_DIM)
        self._aug_status_lbl.pack(side="left")
        ctk.CTkButton(
            btn_row,
            text="🗑 Xóa log",
            corner_radius=999,
            height=34,
            fg_color=BG3,
            hover_color=BORDER,
            text_color=TEXT_DIM,
            font=("Segoe UI", 11),
            command=self._clear_aug_log,
        ).pack(side="right")

        self._aug_progress = ctk.CTkProgressBar(scroll, fg_color=BG3, progress_color=PRIMARY)
        self._aug_progress.set(0)
        self._aug_progress.pack(fill="x", padx=12, pady=(0, 8))

        self._aug_log_box = ctk.CTkTextbox(
            scroll,
            font=("Consolas", 11),
            fg_color="#1e1e2e",
            text_color="#e2e8f0",
            corner_radius=10,
            border_width=1,
            border_color=BORDER,
            activate_scrollbars=True,
            height=240,
        )
        self._aug_log_box.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self._aug_log_box.configure(state="disabled")
        for variable in (
            self._aug_src_var,
            self._aug_keep_original_var,
            self._aug_width_var,
            self._aug_height_var,
        ):
            variable.trace_add("write", self._on_aug_setting_changed)
        for variable in self._aug_pipeline_multiplier_vars.values():
            variable.trace_add("write", self._on_aug_setting_changed)
        self._update_aug_estimate()

    def _build_folder_row(self, parent, label: str, is_source: bool):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(12, 0))

        ctk.CTkLabel(row, text=label, font=("Segoe UI", 12, "bold"),
                     text_color=TEXT, width=260, anchor="w").pack(side="left")

        if is_source:
            self._src_var = ctk.StringVar()
            entry = ctk.CTkEntry(row, textvariable=self._src_var,
                                 font=("Segoe UI", 11), fg_color=BG3,
                                 border_color=BORDER, text_color=TEXT,
                                 placeholder_text="Chọn hoặc nhập đường dẫn…")
            entry.pack(side="left", fill="x", expand=True, padx=(8, 6))
            ctk.CTkButton(row, text="📂", width=36, height=32,
                          fg_color=BG3, hover_color=BORDER, text_color=TEXT,
                          corner_radius=8,
                          command=self._browse_source).pack(side="left")
        else:
            self._dst_var = ctk.StringVar()
            entry = ctk.CTkEntry(row, textvariable=self._dst_var,
                                 font=("Segoe UI", 11), fg_color=BG3,
                                 border_color=BORDER, text_color=TEXT,
                                 placeholder_text="Để trống → tự tạo <nguồn>_copied_safe")
            entry.pack(side="left", fill="x", expand=True, padx=(8, 6))
            ctk.CTkButton(row, text="📁", width=36, height=32,
                          fg_color=BG3, hover_color=BORDER, text_color=TEXT,
                          corner_radius=8,
                          command=self._browse_dest).pack(side="left")

    def _build_aug_path_row(self, parent, label: str, text_var, browse_command):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(6, 0))
        ctk.CTkLabel(row, text=label, font=("Segoe UI", 12, "bold"),
                     text_color=TEXT, width=180, anchor="w").pack(side="left")
        ctk.CTkEntry(
            row,
            textvariable=text_var,
            font=("Segoe UI", 11),
            fg_color=BG3,
            border_color=BORDER,
            text_color=TEXT,
            placeholder_text="Chon thu muc...",
        ).pack(side="left", fill="x", expand=True, padx=(8, 6))
        ctk.CTkButton(
            row,
            text="📂",
            width=36,
            height=32,
            fg_color=BG3,
            hover_color=BORDER,
            text_color=TEXT,
            corner_radius=8,
            command=browse_command,
        ).pack(side="left")

    def _build_aug_numeric(self, parent, label: str, variable, from_: float, to: float):
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.pack(side="left", padx=(0, 14), pady=4)
        ctk.CTkLabel(box, text=label, font=("Segoe UI", 11, "bold"), text_color=TEXT).pack(anchor="w")
        ctk.CTkEntry(
            box,
            textvariable=variable,
            width=86,
            font=("Segoe UI", 11),
            fg_color=BG2,
            border_color=BORDER,
            text_color=TEXT,
        ).pack(anchor="w", pady=(4, 0))

    # ── Browse ────────────────────────────────────────────────────────────────

    def _browse_source(self):
        d = filedialog.askdirectory(title="Chọn thư mục nguồn")
        if d:
            self._src_var.set(d)

    def _browse_dest(self):
        d = filedialog.askdirectory(title="Chọn thư mục đích")
        if d:
            self._dst_var.set(d)
    def _browse_split_source(self):
        d = filedialog.askdirectory(title="Chọn thư mục dataset split")
        if d:
            self._split_src_var.set(d)

    def _browse_aug_source(self):
        d = filedialog.askdirectory(title="Chọn thư mục dataset nguồn để augment")
        if d:
            self._aug_src_var.set(d)

    def _browse_aug_dest(self):
        d = filedialog.askdirectory(title="Chọn thư mục đích để lưu dataset augment")
        if d:
            self._aug_dst_var.set(d)

    def _on_read_split(self):
        src = self._split_src_var.get().strip()
        if not src:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập đường dẫn dataset hoặc chọn thư mục.")
            return

        root = Path(src)
        if not root.exists():
            messagebox.showerror("Không tìm thấy", f"Đường dẫn không tồn tại:\n{src}")
            return

        try:
            report = read_split_ratio(root)
            self._render_split_result(report)
        except Exception as exc:
            messagebox.showerror("Lỗi đọc split", str(exc))

    def _render_split_result(self, report: dict):
        self._split_result_box.configure(state="normal")
        self._split_result_box.delete("0.0", "end")

        self._split_result_box.insert("end", f"Dataset root: {report['source']}\n")
        self._split_result_box.insert("end", f"Ghi chú: {report['note']}\n\n")

        total = report["total"]
        if total == 0:
            self._split_result_box.insert("end", "Không có ảnh nào được tìm thấy trong thư mục dataset.\n")
        else:
            for split_name, count in sorted(report["counts"].items()):
                percent = count / total * 100 if total else 0.0
                self._split_result_box.insert(
                    "end",
                    f"  - {split_name}: {count} ảnh  ({percent:.2f}%)\n"
                )
            self._split_result_box.insert("end", f"\nTổng ảnh: {total}\n")

        self._split_result_box.configure(state="disabled")
    # ── Log helpers ───────────────────────────────────────────────────────────

    def _on_aug_setting_changed(self, *_args):
        self._update_aug_estimate()

    def _get_aug_options(self) -> dict:
        return {key: bool(variable.get()) for key, variable in self._aug_option_vars.items()}

    def _get_aug_pipeline_multipliers(self) -> dict:
        multipliers = {}
        for key, variable in self._aug_pipeline_multiplier_vars.items():
            try:
                multipliers[key] = max(1, int(variable.get()))
            except (TypeError, ValueError):
                multipliers[key] = 1
        return multipliers

    def _update_aug_estimate(self):
        src = self._aug_src_var.get().strip()
        if not src:
            self._aug_estimate_var.set("Chon thu muc nguon de uoc tinh so anh.")
            return

        source = Path(src)
        if not source.is_dir():
            self._aug_estimate_var.set("Thu muc nguon khong hop le.")
            return

        try:
            original_count = count_dataset_images(source)
            keep_original = bool(self._aug_keep_original_var.get())
            options = self._get_aug_options()
            multipliers = self._get_aug_pipeline_multipliers()
            enabled_keys = [key for key, enabled in options.items() if enabled]
            enabled_count = len(enabled_keys)
            augment_per_image = sum(multipliers[key] for key in enabled_keys)
            copied_count = original_count if keep_original else 0
            augmented_count = original_count * augment_per_image
            total_created = copied_count + augmented_count
            pipeline_parts = [
                f"{AUGMENT_PIPELINES[key]['label']} x{multipliers[key]}"
                for key in enabled_keys
            ]
            pipeline_text = ", ".join(pipeline_parts) if pipeline_parts else "Khong bat pipeline nao"
            self._aug_estimate_var.set(
                f"So anh goc: {original_count} | Pipeline dang bat: {enabled_count} | Tong ban augment / anh: {augment_per_image}\n"
                f"Anh augment du kien: {augmented_count} | Giu goc: {copied_count} | Tong du kien: {total_created}\n"
                f"Pipeline bat: {pipeline_text}"
            )
        except Exception as exc:
            self._aug_estimate_var.set(f"Khong the uoc tinh: {exc}")

    def _log(self, msg: str):
        self._log_box.configure(state="normal")
        self._log_box.insert("end", msg + "\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _clear_log(self):
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")

    def _aug_log(self, msg: str):
        self._aug_log_box.configure(state="normal")
        self._aug_log_box.insert("end", msg + "\n")
        self._aug_log_box.see("end")
        self._aug_log_box.configure(state="disabled")

    def _clear_aug_log(self):
        self._aug_log_box.configure(state="normal")
        self._aug_log_box.delete("1.0", "end")
        self._aug_log_box.configure(state="disabled")

    # ── Run / Stop ────────────────────────────────────────────────────────────

    def _on_run(self):
        src = self._src_var.get().strip()
        if not src:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng chọn thư mục nguồn.")
            return
        if not Path(src).is_dir():
            messagebox.showerror("Không tìm thấy", f"Thư mục nguồn không tồn tại:\n{src}")
            return

        dst = self._dst_var.get().strip() or None
        prefix = self._prefix_var.get()

        self._running = True
        self._run_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._status_lbl.configure(text="⏳ Đang chạy…", text_color="#f59e0b")
        self._progress.set(0)
        self._progress.start()

        def _worker():
            try:
                result = copy_dataset_safe(
                    source_dir=src,
                    output_dir=dst,
                    add_class_prefix=prefix,
                    log_callback=lambda m: self.after(0, self._log, m),
                )
                self.after(0, self._on_done, result)
            except Exception as exc:
                self.after(0, self._on_error, str(exc))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_augment_run(self):
        if self._augment_running:
            messagebox.showinfo("Đang chạy", "Tiến trình augment đang chạy.")
            return
        src = self._aug_src_var.get().strip()
        dst = self._aug_dst_var.get().strip()
        if not src or not dst:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng chọn thư mục nguồn và thư mục đích.")
            return
        if not Path(src).is_dir():
            messagebox.showerror("Không tìm thấy", f"Thư mục nguồn không tồn tại:\n{src}")
            return
        if Path(src).resolve() == Path(dst).resolve():
            messagebox.showerror("Sai thư mục", "Thư mục đích phải khác thư mục nguồn.")
            return

        width = max(32, int(self._aug_width_var.get()))
        height = max(32, int(self._aug_height_var.get()))
        aug_options = self._get_aug_options()
        pipeline_multipliers = self._get_aug_pipeline_multipliers()
        if not any(aug_options.values()):
            messagebox.showwarning("Thieu pipeline", "Vui long chon it nhat 1 pipeline augment.")
            return

        self._stop_requested = False
        self._augment_running = True
        self._aug_run_btn.configure(state="disabled")
        self._aug_stop_btn.configure(state="normal")
        self._aug_status_lbl.configure(text="⏳ Đang augment…", text_color=WARNING)
        self._aug_progress.set(0)
        self._aug_progress.start()
        self._clear_aug_log()
        self._aug_log("[INFO] Bat dau augment dataset bang Albumentations")

        def _worker():
            try:
                result = augment_dataset_albumentations(
                    source_dir=src,
                    output_dir=dst,
                    multiplier=4,
                    keep_original=bool(self._aug_keep_original_var.get()),
                    image_width=width,
                    image_height=height,
                    options=aug_options,
                    pipeline_multipliers=pipeline_multipliers,
                    log_callback=lambda m: self.after(0, self._aug_log, m),
                    should_stop=lambda: self._stop_requested,
                )
                self.after(0, self._on_augment_done, result)
            except Exception as exc:
                self.after(0, self._on_augment_error, str(exc))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_augment_stop(self):
        self._stop_requested = True
        self._aug_status_lbl.configure(text="⚠ Đã yêu cầu dừng…", text_color=DANGER)

    def _on_augment_done(self, result: dict):
        self._aug_progress.stop()
        self._aug_progress.set(1)
        self._augment_running = False
        self._aug_run_btn.configure(state="normal")
        self._aug_stop_btn.configure(state="disabled")
        if result.get("stopped"):
            status = "⚠ Đã dừng"
            color = WARNING
        else:
            status = f"✅ Xong! Tao {result['total_created']} anh"
            color = SUCCESS
        self._aug_status_lbl.configure(text=status, text_color=color)
        self._aug_log("")
        self._aug_log("=" * 64)
        self._aug_log(f"Original images : {result['original_images']}")
        self._aug_log(f"Copied originals: {result['copied']}")
        self._aug_log(f"Augmented images: {result['augmented']}")
        self._aug_log(f"Skipped         : {result['skipped']}")
        self._aug_log(f"Output          : {result['output_dir']}")
        self._aug_log("=" * 64)

    def _on_augment_error(self, msg: str):
        self._aug_progress.stop()
        self._aug_progress.set(0)
        self._augment_running = False
        self._aug_run_btn.configure(state="normal")
        self._aug_stop_btn.configure(state="disabled")
        self._aug_status_lbl.configure(text="✗ Lỗi!", text_color=DANGER)
        self._aug_log(f"[ERROR] {msg}")
        messagebox.showerror("Lỗi augment", msg)

    def _on_stop(self):
        # Worker là thread daemon — không thể kill giữa chừng khi đang chạy IO file
        # Đặt cờ, worker sẽ dừng ở vòng lặp tiếp theo (nếu hỗ trợ)
        self._running = False
        self._status_lbl.configure(text="⚠ Đã yêu cầu dừng…", text_color=DANGER)

    def _on_done(self, result: dict):
        self._progress.stop()
        self._progress.set(1)
        self._running = False
        self._run_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self._status_lbl.configure(
            text=f"✅ Xong! {result['copied']} ảnh đã copy.", text_color=SUCCESS
        )

    def _on_error(self, msg: str):
        self._progress.stop()
        self._progress.set(0)
        self._running = False
        self._run_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self._status_lbl.configure(text="✗ Lỗi!", text_color=DANGER)
        self._log(f"\n✗ LỖI: {msg}")
        messagebox.showerror("Lỗi", msg)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = ToolsApp()
    app.mainloop()
