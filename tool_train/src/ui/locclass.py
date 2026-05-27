"""
locclass.py â€” Lá»c class Dataset YOLO
Giao diện Tkinter dark-theme.
Cho phÃ©p chá»n thÆ° má»¥c dataset, Ä‘á»c data.yaml, chá»n class muá»‘n giá»¯,
remap class ID và copy ra dataset mới.
"""
import os
import shutil
import threading
import traceback
from pathlib import Path
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox
import tkinter.scrolledtext as _st

from ui_theme import ACCENT, ACCENT2, BG, BG2, BG3, BG4, DANGER, INFO, SUCCESS, TEXT, TEXT_DIM, WARNING, apply_ttk_theme

# ─── Màu sắc ─────────────────────────────────────────────────────────────────

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff",
            ".JPG", ".JPEG", ".PNG"}


# â”€â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _styled_btn(parent, text, command, color=ACCENT, fg=TEXT, **kw):
    return tk.Button(parent, text=text, command=command,
                     bg=color, fg=fg, relief="flat", cursor="hand2",
                     font=("Segoe UI", 9, "bold"), padx=12, pady=4, **kw)


def _section(parent, title):
    """Card section vá»›i tiÃªu Ä‘á»."""
    frame = tk.Frame(parent, bg=BG2, bd=0, relief="flat")
    frame.pack(fill="x", padx=10, pady=(6, 0))
    tk.Label(frame, text=title, font=("Segoe UI", 9, "bold"),
             bg=BG2, fg=ACCENT2, anchor="w").pack(fill="x", padx=10, pady=(8, 4))
    inner = tk.Frame(frame, bg=BG2)
    inner.pack(fill="x", padx=10, pady=(0, 8))
    return inner


def _path_row(parent, label_text, var, browse_cmd):
    row = tk.Frame(parent, bg=BG2)
    row.pack(fill="x", pady=3)
    tk.Label(row, text=label_text, font=("Segoe UI", 9), bg=BG2,
             fg=TEXT_DIM, width=12, anchor="w").pack(side="left")
    entry = tk.Entry(row, textvariable=var, bg=BG4, fg=TEXT, insertbackground=TEXT,
                     relief="flat", font=("Cascadia Code", 9), bd=4)
    entry.pack(side="left", fill="x", expand=True, padx=(4, 4))
    tk.Button(row, text="📂", bg=BG3, fg=ACCENT2, relief="flat",
              cursor="hand2", font=("Segoe UI", 9), padx=8,
              command=browse_cmd).pack(side="left")
    return entry


# â”€â”€â”€ App â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class LocClassApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ðŸ—‚ Lá»c Class Dataset YOLO")
        self.geometry("900x680")
        self.minsize(740, 540)
        self.configure(bg=BG)
        self._running = False
        self._class_vars: list = []  # list of (BooleanVar, name, orig_id)
        self._build_ui()

    # â”€â”€â”€ BUILD UI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _build_ui(self):
        apply_ttk_theme(ttk.Style(self))
        # â”€â”€ Header â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        hdr = tk.Frame(self, bg=ACCENT, height=48)
        hdr.pack(fill="x")
        tk.Label(hdr, text="ðŸ—‚  Lá»c Class Dataset YOLO",
                 font=("Segoe UI", 13, "bold"), bg=ACCENT, fg=TEXT,
                 padx=16).pack(side="left", pady=8)
        tk.Label(hdr, text="Giữ lại class cần thiết & remap ID → dataset mới",
                 font=("Segoe UI", 8), bg=ACCENT, fg="#ddd6fe").pack(side="left")

        # â”€â”€ Body: left (controls) + right (log) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=0, pady=0)

        paned = tk.PanedWindow(body, orient="horizontal", bg=BG,
                               sashwidth=6, sashrelief="flat")
        paned.pack(fill="both", expand=True, padx=4, pady=4)

        left  = tk.Frame(paned, bg=BG, width=390)
        right = tk.Frame(paned, bg=BG)
        paned.add(left,  minsize=300)
        paned.add(right, minsize=300)

        self._build_left(left)
        self._build_right(right)

        # â”€â”€ Footer status â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        ftr = tk.Frame(self, bg=BG3, height=28)
        ftr.pack(fill="x", side="bottom")
        self._status_lbl = tk.Label(ftr, text="⏹ Sẵn sàng",
                                    font=("Segoe UI", 8), bg=BG3, fg=TEXT_DIM,
                                    anchor="w", padx=10)
        self._status_lbl.pack(side="left", fill="y")

    def _build_left(self, parent):
        # Scrollable inner frame
        canvas = tk.Canvas(parent, bg=BG, highlightthickness=0)
        scroll = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(canvas, bg=BG)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_resize(e):
            canvas.itemconfig(win_id, width=e.width)
        canvas.bind("<Configure>", _on_resize)
        inner.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))

        # ── Thư mục ──────────────────────────────────────────────────────────
        sec1 = _section(inner, "ðŸ“‚  ÄÆ°á»ng dáº«n")
        self._src_var = tk.StringVar()
        self._dst_var = tk.StringVar()
        _path_row(sec1, "Nguồn (src):", self._src_var, self._browse_src)
        _path_row(sec1, "Đích (dst):",  self._dst_var, self._browse_dst)
        tk.Button(sec1, text="ðŸ”„  Äá»c data.yaml (tá»± Ä‘á»™ng phÃ¡t hiá»‡n class)",
                  bg=BG3, fg=ACCENT2, relief="flat", cursor="hand2",
                  font=("Segoe UI", 9), padx=8, pady=3,
                  command=self._load_yaml).pack(fill="x", pady=(6, 0))

        # â”€â”€ Chá»n class â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        sec2 = _section(inner, "ðŸ·  Chá»n class muá»‘n giá»¯")
        self._class_frame = tk.Frame(sec2, bg=BG2)
        self._class_frame.pack(fill="x")
        self._class_hint_lbl = tk.Label(
            sec2, text="(Chá»n thÆ° má»¥c nguá»“n rá»“i nháº¥n 'Äá»c data.yaml')",
            font=("Segoe UI", 8, "italic"), bg=BG2, fg=TEXT_DIM)
        self._class_hint_lbl.pack(anchor="w", pady=(4, 0))
        btn_row = tk.Frame(sec2, bg=BG2)
        btn_row.pack(fill="x", pady=(6, 0))
        tk.Button(btn_row, text="âœ” Chá»n táº¥t cáº£", bg=BG3, fg=SUCCESS, relief="flat",
                  cursor="hand2", font=("Segoe UI", 8), padx=6,
                  command=self._select_all).pack(side="left", padx=(0, 4))
        tk.Button(btn_row, text="âœ˜ Bá» háº¿t", bg=BG3, fg=DANGER, relief="flat",
                  cursor="hand2", font=("Segoe UI", 8), padx=6,
                  command=self._deselect_all).pack(side="left")

        # ── Thêm class thủ công ───────────────────────────────────────────────
        sec3 = _section(inner, "âœ  ThÃªm class thá»§ cÃ´ng (náº¿u khÃ´ng cÃ³ data.yaml)")
        man_row = tk.Frame(sec3, bg=BG2)
        man_row.pack(fill="x")
        self._manual_entry = tk.Entry(
            man_row, bg=BG4, fg=TEXT, insertbackground=TEXT,
            relief="flat", font=("Cascadia Code", 9), bd=4)
        self._manual_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Label(man_row, text="tên, cách dấu phẩy",
                 font=("Segoe UI", 8), bg=BG2, fg=TEXT_DIM).pack(side="left")
        tk.Button(sec3, text="âž•  ThÃªm vÃ o danh sÃ¡ch",
                  bg=BG3, fg=ACCENT2, relief="flat", cursor="hand2",
                  font=("Segoe UI", 9), padx=8, pady=3,
                  command=self._add_manual_classes).pack(fill="x", pady=(6, 0))

        # â”€â”€ TÃ¹y chá»n â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        sec4 = _section(inner, "âš™  TÃ¹y chá»n")
        self._remap_var       = tk.BooleanVar(value=True)
        self._copy_no_lbl_var = tk.BooleanVar(value=False)
        self._auto_ext_var    = tk.BooleanVar(value=True)
        self._img_ext_var     = tk.StringVar(value=".jpg")

        tk.Checkbutton(sec4, text="Remap class ID (0, 1, 2â€¦ theo thá»© tá»± chá»n)",
                       variable=self._remap_var, bg=BG2, fg=TEXT,
                       selectcolor=BG3, activebackground=BG2,
                       font=("Segoe UI", 9)).pack(anchor="w")
        tk.Checkbutton(sec4, text="Copy ảnh không có label (background images)",
                       variable=self._copy_no_lbl_var, bg=BG2, fg=TEXT,
                       selectcolor=BG3, activebackground=BG2,
                       font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 0))
        tk.Checkbutton(sec4, text="Tá»± Ä‘á»™ng tÃ¬m má»i Ä‘á»‹nh dáº¡ng áº£nh (jpg/png/bmpâ€¦)",
                       variable=self._auto_ext_var, bg=BG2, fg=TEXT,
                       selectcolor=BG3, activebackground=BG2,
                       font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 0))

        ext_row = tk.Frame(sec4, bg=BG2)
        ext_row.pack(fill="x", pady=(4, 0))
        tk.Label(ext_row, text="Äá»‹nh dáº¡ng (náº¿u táº¯t auto):",
                 font=("Segoe UI", 8), bg=BG2, fg=TEXT_DIM).pack(side="left")
        for ext in [".jpg", ".png", ".jpeg", ".bmp", ".webp"]:
            tk.Radiobutton(ext_row, text=ext, variable=self._img_ext_var, value=ext,
                           bg=BG2, fg=TEXT, selectcolor=BG3, activebackground=BG2,
                           font=("Segoe UI", 8)).pack(side="left", padx=3)

        # â”€â”€ Run button â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        btn_frame = tk.Frame(inner, bg=BG)
        btn_frame.pack(fill="x", padx=10, pady=10)
        self._run_btn = _styled_btn(btn_frame, "â–¶  Cháº¡y lá»c Dataset",
                                    self._on_run, color=ACCENT)
        self._run_btn.pack(fill="x", ipady=6)

    def _build_right(self, parent):
        hdr = tk.Frame(parent, bg=BG3)
        hdr.pack(fill="x")
        tk.Label(hdr, text="ðŸ“ Log",
                 font=("Segoe UI", 9, "bold"), bg=BG3, fg=TEXT_DIM,
                 padx=8).pack(side="left", pady=4)
        tk.Button(hdr, text="🗑 Xóa log", bg=BG3, fg=TEXT_DIM, relief="flat",
                  cursor="hand2", font=("Segoe UI", 8), padx=8,
                  command=self._clear_log).pack(side="right", pady=2, padx=4)

        self._log_box = _st.ScrolledText(
            parent, bg=BG4, fg="#d4d4d4", insertbackground=TEXT,
            relief="flat", font=("Cascadia Code", 9), wrap="word",
            state="disabled")
        self._log_box.pack(fill="both", expand=True, padx=4, pady=4)
        self._log_box.tag_config("ok",   foreground=SUCCESS)
        self._log_box.tag_config("warn", foreground=WARNING)
        self._log_box.tag_config("err",  foreground=DANGER)
        self._log_box.tag_config("info", foreground=INFO)
        self._log_box.tag_config("hdr",  foreground=ACCENT2)

        # Progress bar
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TProgressbar", troughcolor=BG3,
                        background=ACCENT, thickness=6)
        self._progress = ttk.Progressbar(parent, style="TProgressbar",
                                         mode="determinate", maximum=100, value=0)
        self._progress.pack(fill="x", padx=4, pady=(0, 4))

    # â”€â”€â”€ LOG â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _log(self, text, tag=""):
        def _do():
            self._log_box.configure(state="normal")
            self._log_box.insert("end", text + "\n", tag)
            self._log_box.see("end")
            self._log_box.configure(state="disabled")
        self.after(0, _do)

    def _clear_log(self):
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")

    def _set_status(self, text, color=TEXT_DIM):
        self.after(0, lambda: self._status_lbl.configure(text=text, fg=color))

    def _set_progress(self, val):
        self.after(0, lambda: self._progress.configure(value=val))

    # â”€â”€â”€ BROWSE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _browse_src(self):
        d = filedialog.askdirectory(title="Chá»n thÆ° má»¥c dataset nguá»“n")
        if d:
            self._src_var.set(d)
            self._load_yaml()

    def _browse_dst(self):
        d = filedialog.askdirectory(title="Chá»n thÆ° má»¥c Ä‘Ã­ch (output)")
        if d:
            self._dst_var.set(d)

    # â”€â”€â”€ LOAD YAML â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _load_yaml(self):
        src = self._src_var.get().strip()
        if not src or not Path(src).is_dir():
            messagebox.showwarning("âš ", "Chá»n thÆ° má»¥c nguá»“n trÆ°á»›c.")
            return
        yaml_candidates = (list(Path(src).glob("data.yaml"))
                           + list(Path(src).rglob("data.yaml")))
        if not yaml_candidates:
            self._log(f"[warn] Không tìm thấy data.yaml trong {src}", "warn")
            self._log("[info] Bạn có thể thêm class thủ công bên dưới.", "info")
            return
        yaml_path = yaml_candidates[0]
        try:
            classes = self._parse_yaml_names(yaml_path)
            self._populate_class_checkboxes(classes)
            self._log(f"[âœ”] Äá»c data.yaml: {yaml_path}", "ok")
            self._log(f"[info] {len(classes)} class: {', '.join(classes)}", "info")
            self._class_hint_lbl.configure(text=f"Từ: {yaml_path.name}")
        except Exception as ex:
            self._log(f"[âœ—] Lá»—i Ä‘á»c data.yaml: {ex}", "err")

    def _parse_yaml_names(self, yaml_path: Path) -> list:
        text = yaml_path.read_text(encoding="utf-8")
        names: list = []
        in_names = False
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("names:"):
                after = stripped[len("names:"):].strip()
                if after.startswith("["):
                    inner = after.strip("[]")
                    names = [x.strip().strip("'\"") for x in inner.split(",") if x.strip()]
                    break
                in_names = True
                continue
            if in_names:
                if stripped.startswith("-"):
                    name = stripped.lstrip("- ").strip().strip("'\"")
                    if name:
                        names.append(name)
                elif stripped and not stripped.startswith("#") and ":" in stripped:
                    in_names = False
        return names

    def _populate_class_checkboxes(self, classes: list):
        for w in self._class_frame.winfo_children():
            w.destroy()
        self._class_vars.clear()
        for i, name in enumerate(classes):
            var = tk.BooleanVar(value=True)
            row = tk.Frame(self._class_frame, bg=BG2)
            row.pack(fill="x", pady=1)
            tk.Checkbutton(row, text=f"[{i}]  {name}",
                           variable=var, bg=BG2, fg=TEXT,
                           selectcolor=BG3, activebackground=BG2,
                           font=("Cascadia Code", 9)).pack(side="left")
            self._class_vars.append((var, name, i))

    def _select_all(self):
        for var, _, _ in self._class_vars:
            var.set(True)

    def _deselect_all(self):
        for var, _, _ in self._class_vars:
            var.set(False)

    def _add_manual_classes(self):
        raw = self._manual_entry.get().strip()
        if not raw:
            return
        names = [n.strip() for n in raw.split(",") if n.strip()]
        start_id = max((oid for _, _, oid in self._class_vars), default=-1) + 1
        for i, name in enumerate(names):
            if any(n == name for _, n, _ in self._class_vars):
                self._log(f"[warn] Class '{name}' Ä‘Ã£ tá»“n táº¡i, bá» qua.", "warn")
                continue
            var = tk.BooleanVar(value=True)
            row = tk.Frame(self._class_frame, bg=BG2)
            row.pack(fill="x", pady=1)
            orig_id = start_id + i
            tk.Checkbutton(row, text=f"[{orig_id}]  {name}",
                           variable=var, bg=BG2, fg=TEXT,
                           selectcolor=BG3, activebackground=BG2,
                           font=("Cascadia Code", 9)).pack(side="left")
            self._class_vars.append((var, name, orig_id))
        self._manual_entry.delete(0, "end")
        self._class_hint_lbl.configure(
            text=f"{len(self._class_vars)} class trong danh sÃ¡ch")

    # â”€â”€â”€ RUN â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _on_run(self):
        if self._running:
            messagebox.showinfo("â„¹", "Äang cháº¡y, hÃ£y Ä‘á»£i.")
            return
        src = self._src_var.get().strip()
        dst = self._dst_var.get().strip()
        if not src or not Path(src).is_dir():
            messagebox.showerror("âœ— Lá»—i", "Chá»n thÆ° má»¥c nguá»“n há»£p lá»‡.")
            return
        if not dst:
            messagebox.showerror("âœ— Lá»—i", "Chá»n thÆ° má»¥c Ä‘Ã­ch.")
            return
        keep = [(name, orig_id) for var, name, orig_id in self._class_vars if var.get()]
        if not keep:
            messagebox.showerror("âœ— Lá»—i", "Chá»n Ã­t nháº¥t 1 class.")
            return

        self._running = True
        self._run_btn.configure(state="disabled", text="⏳ Đang chạy...")
        self._set_status("⏳ Đang lọc...", WARNING)
        self._set_progress(0)

        threading.Thread(target=self._filter_thread,
                         args=(src, dst, keep), daemon=True).start()

    def _filter_thread(self, src: str, dst: str, keep: list):
        try:
            keep_ids = {orig_id for _, orig_id in keep}
            remap    = self._remap_var.get()
            copy_no_lbl = self._copy_no_lbl_var.get()
            auto_ext    = self._auto_ext_var.get()
            preferred_ext = self._img_ext_var.get()

            # remap: old_id â†’ new_id
            id_map: dict = {}
            if remap:
                for new_id, (_, old_id) in enumerate(
                        sorted(keep, key=lambda x: x[1])):
                    id_map[old_id] = new_id
            else:
                id_map = {old_id: old_id for _, old_id in keep}

            keep_names = [name for name, _ in keep]
            self._log("â•" * 60, "hdr")
            self._log("  Báº®T Äáº¦U Lá»ŒC DATASET", "hdr")
            self._log(f"  Nguồn : {src}", "info")
            self._log(f"  Đích   : {dst}", "info")
            self._log(f"  Giữ    : {keep_names}", "info")
            self._log(f"  Remap  : {id_map}", "info")
            self._log("â•" * 60, "hdr")

            splits = ["train", "valid", "test"]
            existing_splits = [s for s in splits if (Path(src) / s).is_dir()]
            if not existing_splits:
                existing_splits = [d.name for d in Path(src).iterdir()
                                   if d.is_dir()]
            if not existing_splits:
                self._log("[✗] Không tìm thấy thư mục split nào.", "err")
                return

            total_labels = sum(
                len(list((Path(src) / sp / "labels").glob("*.txt")))
                for sp in existing_splits
                if (Path(src) / sp / "labels").is_dir()
            )
            processed = 0
            stats = {sp: {"kept": 0, "skipped": 0, "no_ann": 0}
                     for sp in existing_splits}

            for sp in existing_splits:
                img_dir = Path(src) / sp / "images"
                lbl_dir = Path(src) / sp / "labels"
                out_img = Path(dst) / sp / "images"
                out_lbl = Path(dst) / sp / "labels"
                out_img.mkdir(parents=True, exist_ok=True)
                out_lbl.mkdir(parents=True, exist_ok=True)

                self._log(f"\n[Split: {sp}]", "hdr")

                label_files = list(lbl_dir.glob("*.txt")) if lbl_dir.is_dir() else []

                for lbl_file in label_files:
                    img_file = None
                    if auto_ext:
                        for ext in IMG_EXTS:
                            cand = img_dir / (lbl_file.stem + ext)
                            if cand.exists():
                                img_file = cand
                                break
                    else:
                        cand = img_dir / (lbl_file.stem + preferred_ext)
                        if cand.exists():
                            img_file = cand

                    if img_file is None:
                        stats[sp]["skipped"] += 1
                        processed += 1
                        if total_labels:
                            self._set_progress(
                                int(processed / total_labels * 100))
                        continue

                    try:
                        lines = lbl_file.read_text(
                            encoding="utf-8").splitlines()
                    except Exception:
                        stats[sp]["skipped"] += 1
                        processed += 1
                        continue

                    new_lines = []
                    for line in lines:
                        parts = line.strip().split()
                        if not parts:
                            continue
                        try:
                            cls_id = int(parts[0])
                        except ValueError:
                            continue
                        if cls_id in keep_ids:
                            new_lines.append(
                                f"{id_map[cls_id]} " + " ".join(parts[1:]))

                    if not new_lines:
                        if copy_no_lbl:
                            shutil.copy2(img_file, out_img / img_file.name)
                            (out_lbl / lbl_file.name).write_text(
                                "", encoding="utf-8")
                            stats[sp]["no_ann"] += 1
                        else:
                            stats[sp]["skipped"] += 1
                    else:
                        shutil.copy2(img_file, out_img / img_file.name)
                        (out_lbl / lbl_file.name).write_text(
                            "\n".join(new_lines) + "\n", encoding="utf-8")
                        stats[sp]["kept"] += 1

                    processed += 1
                    if total_labels:
                        self._set_progress(
                            int(processed / total_labels * 100))

                self._log(
                    f"  âœ” kept={stats[sp]['kept']}  "
                    f"skip={stats[sp]['skipped']}  "
                    f"no_ann={stats[sp]['no_ann']}", "ok")

            self._write_data_yaml(dst, keep, existing_splits)

            total_kept = sum(s["kept"] for s in stats.values())
            total_skip = sum(s["skipped"] for s in stats.values())
            self._log("\n" + "â•" * 60, "hdr")
            self._log(f"  ✅ HOÀN TẤT  |  kept={total_kept}  "
                      f"skipped={total_skip}", "ok")
            self._log(f"  ðŸ“ LÆ°u táº¡i: {dst}", "ok")
            self._log("â•" * 60, "hdr")
            self._set_status(
                f"✔ Xong — {total_kept} ảnh đã giữ lại", SUCCESS)
            self._set_progress(100)

        except Exception:
            err = traceback.format_exc()
            self._log(f"[✗] Lỗi:\n{err}", "err")
            self._set_status("âœ— Lá»—i khi lá»c", DANGER)
        finally:
            self._running = False
            self.after(0, self._run_btn.configure,
                       {"state": "normal", "text": "â–¶  Cháº¡y lá»c Dataset"})

    def _write_data_yaml(self, dst: str, keep: list, splits: list):
        sorted_keep = sorted(keep, key=lambda x: x[1])
        names = [name for name, _ in sorted_keep]
        lines = [
            f"path: {dst}",
            f"nc: {len(names)}",
            f"names: {names}",
            "",
        ]
        for sp in splits:
            lines.append(f"{sp}: {sp}/images")
        yaml_out = Path(dst) / "data.yaml"
        yaml_out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self._log(f"[âœ”] ÄÃ£ ghi data.yaml â†’ {yaml_out}", "ok")


# â”€â”€â”€ Entry â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if __name__ == "__main__":
    app = LocClassApp()
    app.mainloop()




