"""
YOLOv8 Inference Tester
Hỗ trợ: Detection (.pt / .onnx) & Instance Segmentation (.pt / .onnx)
Input:   Ảnh đơn | Video | Webcam
GPU: RTX 4060 8GB | CPU: i9-14900HX
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import sys
import os
import time
import io
import warnings
from pathlib import Path
import customtkinter as ctk

SRC_DIR = Path(__file__).resolve().parents[2]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from bll.app_context import RUNS_DIR, TOOL_TRAIN_DIR
from bll.test.artifact_service import find_latest_eval_json, load_saved_eval_artifacts
from bll.test.history_service import (
    cmp_history_from_results_csv,
    make_paper_benchmark_info,
    paper_find_history_data,
)
from bll.test.inference_service import predict_dynamic_conf
from bll.test.registry_service import (
    load_registry_data as bll_load_registry_data,
    move_selected_registry_items,
    save_registry_data as bll_save_registry_data,
)
from bll.test.segment_service import run_segment_preview
from dal.jsonb.config_store import COMPARE_CONFIG_PATH, INPUT_CONFIG_PATH, TESTER_CONFIG_PATH
from dal.jsonb.tester_repository import (
    load_compare_registry,
    load_input_registry,
    load_tester_config,
    save_compare_registry,
    save_input_registry,
    save_tester_config,
)

from ui.ui_theme import (
    ACCENT,
    ACCENT2,
    ACCENT3,
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
    apply_entry_theme,
    build_app_taskbar,
    build_dashboard_banner,
    build_metric_strip,
    build_page_body,
    build_tabview,
    apply_textbox_theme,
    apply_ttk_theme,
    patch_customtkinter_text,
    silence_console_output,
    setup_ctk,
)

warnings.filterwarnings("ignore", category=FutureWarning, module=r"google\.generativeai")
silence_console_output()
import google.generativeai as genai

setup_ctk(ctk)

_ORIG_TK_BUTTON = tk.Button


def _button_hover_color(base_color: str) -> str:
    mapping = {
        ACCENT: ACCENT2,
        SUCCESS: "#3f9b45",
        DANGER: "#e06262",
        WARNING: "#d4b13d",
        INFO: "#38bdf8",
        BG2: ACCENT,
        BG3: ACCENT,
        BG4: ACCENT,
    }
    return mapping.get(base_color, ACCENT3)


def _ctk_button_factory(master=None, cnf=None, **kwargs):
    opts = {}
    if cnf:
        opts.update(cnf)
    opts.update(kwargs)
    bg = str(opts.pop("bg", opts.pop("background", BG3)))
    fg = str(opts.pop("fg", opts.pop("foreground", TEXT)))
    text = opts.pop("text", "")
    command = opts.pop("command", None)
    font = opts.pop("font", ("Segoe UI", 10, "bold"))
    state = opts.pop("state", "normal")
    width = opts.pop("width", 0)
    cursor = opts.pop("cursor", "hand2")
    opts.pop("relief", None)
    opts.pop("activebackground", None)
    opts.pop("activeforeground", None)
    opts.pop("bd", None)
    opts.pop("highlightthickness", None)
    opts.pop("padx", None)
    pady = opts.pop("pady", 0)

    fg_color = bg if bg not in {"SystemButtonFace", ""} else BG3
    border_width = 1 if fg_color in {BG2, BG3, BG4} else 0
    height = 36
    try:
        height = max(34, 22 + int(pady) * 2)
    except Exception:
        pass

    button = ctk.CTkButton(
        master,
        text=text,
        command=command,
        font=font,
        fg_color=fg_color,
        hover_color=_button_hover_color(fg_color),
        text_color=fg,
        border_width=border_width,
        border_color=BORDER,
        corner_radius=14,
        state=state,
        width=width if isinstance(width, (int, float)) and width > 0 else 0,
        height=height,
    )
    try:
        button.configure(cursor=cursor)
    except Exception:
        pass

    def _apply(fg_color=None, text_color=None):
        kwargs = {}
        if fg_color is not None:
            kwargs["fg_color"] = fg_color
        if text_color is not None:
            kwargs["text_color"] = text_color
        if kwargs:
            try:
                button.configure(**kwargs)
            except Exception:
                pass

    hover_fg = _button_hover_color(fg_color)
    button.bind("<Enter>", lambda _e: _apply(hover_fg, "white" if fg_color != BG3 else TEXT), add="+")
    button.bind("<Leave>", lambda _e: _apply(fg_color, fg), add="+")
    button.bind("<ButtonPress-1>", lambda _e: _apply(ACCENT3, "white"), add="+")
    button.bind("<ButtonRelease-1>", lambda _e: _apply(hover_fg, "white" if fg_color != BG3 else TEXT), add="+")
    return button


tk.Button = _ctk_button_factory

# ─── Đường dẫn mặc định ──────────────────────────────────────────────────────
ROOT_DIR      = TOOL_TRAIN_DIR
EVAL_BASE_DIR = Path(r"D:\DACS\SSBBKH\danh_gia-so_sanh\danh_gia_model")
PYTHON_EXE = Path(sys.executable)
JILSA_GREEN = "#4ade80"
PLOS_BLUE = "#60a5fa"
JILSA_BANNER_BG = "#0a1a10"
PLOS_BANNER_BG = "#0a0f1a"

# ─── Màu sắc (cùng palette với train.py) ─────────────────────────────────────

# ─── Màu nhãn lớp (detection box / mask overlay) ─────────────────────────────
CLASS_COLORS = [
    "#ef4444","#f97316","#eab308","#22c55e","#14b8a6",
    "#3b82f6","#8b5cf6","#ec4899","#06b6d4","#84cc16",
]

TASK_TYPES    = ["Detection", "Instance Segmentation", "Classification"]
INPUT_SOURCES = ["Ảnh (Image)", "Video", "Webcam"]

# ─── Chuẩn bài báo quốc tế (benchmark cố định) ───────────────────────────────
PAPER_BENCHMARKS = {
    "JILSA 2022\n(Custom CNN)": {
        "paper":        "Application of AI Algorithm in Image Processing for Cattle Disease Diagnosis",
        "architecture": "Custom CNN (3 Conv layers)",
        "classes":      3,
        "class_names":  "Viêm da nổi cục, Nấm da, Mụn cóc",
        "input_size":   "200×200",
        "params_m":     10.33,
        "gflops":       15.8,
        "optimizer":    "SGD with Momentum",
        "lr":           0.001,
        "batch_size":   64,
        "epochs":       50,
        "loss_fn":      "CrossEntropyLoss",
        "accuracy":     95.0,
        "map50":        None,
        "map50_95":     None,
        "train_split":  "90% Train / 10% Test",
        "test_images":  399,
        "augmentation": "Heavy (Rotation, Flip, Zoom, Shear, Brightness)",
    },
    "PLOS ONE 2024\n(MobileNetV2)": {
        "paper":        "Detection and multi-class classification of cattle diseases using integrated deep learning models",
        "architecture": "MobileNetV2 (Transfer Learning, ImageNet pre-trained)",
        "classes":      2,
        "class_names":  "Healthy, Lumpy",
        "input_size":   "224×224",
        "params_m":     3.5,
        "gflops":       0.4,
        "optimizer":    "RMSProp",
        "lr":           0.001,
        "batch_size":   32,
        "epochs":       None,
        "loss_fn":      "CrossEntropyLoss",
        "accuracy":     95.0,
        "map50":        None,
        "map50_95":     None,
        "train_split":  "70% Train / 15% Val / 15% Test",
        "test_images":  230,
        "augmentation": "Light (Rotation, Flip, Zoom)",
    },
}


# ─── Pre-install + cache-invalidate helper ───────────────────────────────────
def _ensure_packages(*packages: str):
    """
    Cài các package còn thiếu vào ĐÚNG venv hiện tại bằng pip,
    sau đó gọi importlib.invalidate_caches() để Python thấy ngay
    mà không cần restart.
    """
    import importlib, importlib.util, subprocess as _sp
    to_install = []
    for pkg in packages:
        imp_name = pkg.split("-")[0].replace("-", "_")
        if importlib.util.find_spec(imp_name) is None:
            to_install.append(pkg)
    if to_install:
        _sp.run(
            [str(PYTHON_EXE), "-m", "pip", "install", *to_install, "-q"],
            check=False,
        )
        importlib.invalidate_caches()


# ─── Lazy-import helpers (tránh crash khi chưa cài) ──────────────────────────
def _import_cv2():
    import cv2
    return cv2

def _import_pil():
    from PIL import Image, ImageTk, ImageDraw, ImageFont
    return Image, ImageTk, ImageDraw, ImageFont

def _import_numpy():
    import numpy as np
    return np

def _import_yolo():
    from ultralytics import YOLO
    return YOLO


# ─────────────────────────────────────────────────────────────────────────────
class _CanvasImage:
    """Hiển thị PIL.Image.Image trên tk.Canvas, scale giữ tỉ lệ."""
    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self._img_id = None
        self._tk_img = None

    def show(self, pil_img):
        Image, ImageTk, _, _ = _import_pil()
        cw = self.canvas.winfo_width()  or 640
        ch = self.canvas.winfo_height() or 480
        # fit-to-canvas: vừa thu vừa phóng to giữ tỷ lệ
        iw, ih = pil_img.size
        scale = min(cw / iw, ch / ih)
        nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
        img = pil_img.resize((nw, nh), Image.LANCZOS)
        self._tk_img = ImageTk.PhotoImage(img)
        cx, cy = cw // 2, ch // 2
        if self._img_id:
            self.canvas.itemconfigure(self._img_id, image=self._tk_img)
            self.canvas.coords(self._img_id, cx, cy)
        else:
            self._img_id = self.canvas.create_image(cx, cy, anchor="center",
                                                     image=self._tk_img)


# ─────────────────────────────────────────────────────────────────────────────
class TesterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Con Bò Cười - Đánh giá mô hình")
        self.geometry("1600x980")
        self.minsize(1280, 820)
        self.configure(fg_color=BG)
        self.resizable(True, True)

        # State
        self._model          = None
        self._model_path     = tk.StringVar()
        self._task_var       = tk.StringVar(value=TASK_TYPES[0])
        self._source_var     = tk.StringVar(value=INPUT_SOURCES[0])
        self._input_path     = tk.StringVar()
        self._cam_idx_var    = tk.IntVar(value=0)
        self._conf_var       = tk.DoubleVar(value=0.50)
        self._iou_var        = tk.DoubleVar(value=0.50)
        self._dynamic_conf_var = tk.BooleanVar(value=False)  # Auto giảm conf
        self._imgsz_var      = tk.IntVar(value=640)
        self._save_var       = tk.BooleanVar(value=False)
        self._half_var       = tk.BooleanVar(value=False)
        self._device_var     = tk.StringVar(value="0")

        self._running        = False
        self._stop_flag      = False
        self._frame_queue    = queue.Queue(maxsize=2)
        self._fps_counter    = []
        self._opacity_var    = tk.IntVar(value=75)    # 0-100
        self._last_result    = None   # cache for slider re-render
        self._last_source    = None   # cache for re-inference
        self._debounce_id    = None   # slider debounce
        self._gemini_key_var = tk.StringVar(value="")
        self._class_row_widgets: dict = {}  # cls_id → (row, badge, name_lbl, conf_lbl)
        self._last_diagnosis: list = []     # cache for LLM

        # ── Comparison tab state ──
        _MAX_CMP = 6
        self._cmp_slot_labels       = list("ABCDEF")
        self._cmp_slot_colors       = ["#22c55e", "#38bdf8", "#f59e0b", "#a855f7", "#ec4899", "#14b8a6"]
        self._cmp_enabled_slots     = 0   # 0 until user picks from registry
        self._cmp_model: list       = [None]  * _MAX_CMP
        self._cmp_model_type: list  = ["yolo"] * _MAX_CMP
        self._cmp_pth_class_names: list = [[] for _ in range(_MAX_CMP)]
        self._cmp_path_var: list    = [tk.StringVar() for _ in range(_MAX_CMP)]
        self._cmp_dataset_var: list = [tk.StringVar() for _ in range(_MAX_CMP)]
        self._cmp_alias_var: list   = [tk.StringVar(value=f"Model {l}") for l in "ABCDEF"]
        self._cmp_task_var: list    = [tk.StringVar(value=TASK_TYPES[0]) for _ in range(_MAX_CMP)]
        self._cmp_info_lbl: list    = [None] * _MAX_CMP
        self._cmp_canvas_img: list  = [None] * _MAX_CMP
        self._cmp_summary_frame: list = [None] * _MAX_CMP
        self._cmp_summary_chart: list = [None] * _MAX_CMP
        self._cmp_summary_chart_img: list = [None] * _MAX_CMP
        self._cmp_history_data: list = [None] * _MAX_CMP
        self._cmp_eval_summary: list = [{} for _ in range(_MAX_CMP)]
        # registry (thong_so.json)
        self._cmp_registry: list    = []   # list of model dicts
        self._cmp_check_vars: list  = []   # BooleanVar per registry entry
        self._cmp_list_inner        = None # set during _build_comparison_tab
        self._cmp_canvas_area       = None # set during _build_comparison_tab
        self._cmp_sel_count_lbl     = None # selection count label
        self._cmp_source_var        = tk.StringVar(value=INPUT_SOURCES[0])
        self._cmp_input_var         = tk.StringVar()
        self._cmp_cam_var           = tk.IntVar(value=0)
        self._cmp_conf_var          = tk.DoubleVar(value=0.50)
        self._cmp_iou_var           = tk.DoubleVar(value=0.50)
        # Per-slot conf/iou cho YOLO (được tạo mới khi rebuild canvas)
        self._cmp_conf_slot: list   = [tk.DoubleVar(value=0.50) for _ in range(6)]
        self._cmp_iou_slot:  list   = [tk.DoubleVar(value=0.45) for _ in range(6)]
        self._cmp_device_var        = tk.StringVar(value="0")
        self._cmp_imgsz_var         = tk.IntVar(value=640)
        self._cmp_running           = False
        self._cmp_stop_flag         = False
        self._cmp_metrics: list     = [{} for _ in range(6)]
        self._cmp_fps_lbl: list     = [None] * 6
        self._cmp_det_lbl: list     = [None] * 6
        self._cmp_ms_lbl: list      = [None] * 6
        # Per-slot native imgsz (auto-detected from ONNX model, fallback to global)
        self._cmp_imgsz_slot: list  = [None] * 6
        self._cmp_frame_queue       = queue.Queue(maxsize=2)

        # ── Compare History tab state ──
        self._cmphistory_rows:       list = []
        self._cmphistory_row_frames: list = []
        self._cmphistory_selected:   int  = -1
        self._cmphistory_detail_win        = None
        self._cmphistory_table_inner       = None
        self._cmphistory_sort_key:   str  = "timestamp"
        self._cmphistory_sort_rev:   bool = True
        self._cmphistory_summary_lbl       = None

        # ── Eval tab state (Val) ──
        self._eval_model_dir        = tk.StringVar()
        self._eval_data_path        = tk.StringVar()
        self._eval_output_dir       = tk.StringVar()
        self._eval_task_var         = tk.StringVar(value=TASK_TYPES[0])
        self._eval_device_var       = tk.StringVar(value="0")
        self._eval_imgsz_var        = tk.IntVar(value=640)
        self._eval_split_var        = tk.StringVar(value="val")
        self._eval_conf_var         = tk.DoubleVar(value=0.25)
        self._eval_iou_var          = tk.DoubleVar(value=0.45)
        self._eval_half_var         = tk.BooleanVar(value=False)
        self._eval_limit_var        = tk.IntVar(value=0)
        self._eval_limit_mode_var   = tk.StringVar(value="random")
        self._eval_class_filter_var = tk.StringVar(value="")
        self._eval_running          = False
        self._eval_results          : dict = {}
        self._eval_chart_pil_img    = None
        self._batch_chart_pil_img   = None

        # ── Batch Predict tab state ──
        self._batch_model_dir       = tk.StringVar()
        self._batch_data_path       = tk.StringVar()
        self._batch_output_dir      = tk.StringVar()
        self._batch_task_var        = tk.StringVar(value=TASK_TYPES[0])
        self._batch_device_var      = tk.StringVar(value="0")
        self._batch_imgsz_var       = tk.IntVar(value=640)
        self._batch_conf_var        = tk.DoubleVar(value=0.25)
        self._batch_iou_var         = tk.DoubleVar(value=0.45)
        self._batch_half_var        = tk.BooleanVar(value=False)
        self._batch_running         = False
        # split / limit
        self._batch_img_total       = tk.IntVar(value=0)
        self._batch_split_enable    = tk.BooleanVar(value=False)
        self._batch_split_n         = tk.IntVar(value=50)
        self._batch_split_mode      = tk.StringVar(value="random")

        # ── Unified eval+batch mode selector ──
        self._run_mode_var          = tk.StringVar(value="val")

        # ── Benchmark comparison state ──
        self._bench_table_frame     = None   # set during _build_eval_batch_merged_tab
        self._bench_canvas          = None   # set during _build_eval_batch_merged_tab
        self._bench_tk_img          = None   # prevent GC
        self._bench_pil_img         = None
        self._bench_reference_var   = tk.StringVar(value="JILSA 2022")
        self._bench_cached_models   = {}
        self._bench_latest_yolo_model = None
        self._eval_model_kind_var   = tk.StringVar(value="YOLO")
        self._eval_registry_label_var = tk.StringVar(value="")
        self._eval_registry_options: list[dict] = []
        self._eval_registry_cb = None
        self._eval_mode_panels      = {}
        self._eval_chart_caption_lbl = None
        self._bench_chart_caption_lbl = None
        self._jilsa_chart_caption_lbl = None
        self._plos_chart_caption_lbl = None
        self._jilsa_chart_pil_img   = None
        self._plos_chart_pil_img    = None
        self._paper_chart_state = {"jilsa": {}, "plos": {}}
        self._paper_chart_mode_var = {
            "jilsa": tk.StringVar(value="summary"),
            "plos": tk.StringVar(value="summary"),
        }
        self._paper_chart_mode_buttons = {"jilsa": {}, "plos": {}}

        # ── PyTorch .pth eval tab state ──
        self._pth_model_path        = tk.StringVar()
        self._pth_arch_var          = tk.StringVar(value="JILSA 2022 (CustomCNN)")
        self._pth_data_var          = tk.StringVar()
        self._pth_val_folder_var    = tk.StringVar(value="test")
        self._pth_imgsz_var         = tk.IntVar(value=224)
        self._pth_batch_var         = tk.IntVar(value=32)
        self._pth_workers_var       = tk.IntVar(value=0)
        self._pth_device_var        = tk.StringVar(value="cuda")
        self._pth_out_var           = tk.StringVar(value=str(EVAL_BASE_DIR / "jilsa"))
        self._pth_running           = False
        self._pth_process           = None
        self._pth_start_time        = 0.0
        self._pth_in_report         = False

        # ── JILSA 2022 eval tab state ──
        self._jilsa_model_var   = tk.StringVar()
        self._jilsa_data_var    = tk.StringVar()
        self._jilsa_valfolder_var = tk.StringVar(value="test")
        self._jilsa_imgsz_var   = tk.IntVar(value=200)
        self._jilsa_batch_var   = tk.IntVar(value=32)
        self._jilsa_limit_var   = tk.IntVar(value=0)   # 0 = không giới hạn
        self._jilsa_device_var  = tk.StringVar(value="cuda")
        self._jilsa_out_var     = tk.StringVar(value=str(EVAL_BASE_DIR / "jilsa"))
        self._jilsa_running     = False
        self._jilsa_process     = None

        # ── PLOS ONE 2024 eval tab state ──
        self._plos_model_var    = tk.StringVar()
        self._plos_data_var     = tk.StringVar()
        self._plos_valfolder_var = tk.StringVar(value="test")
        self._plos_imgsz_var    = tk.IntVar(value=224)
        self._plos_batch_var    = tk.IntVar(value=32)
        self._plos_limit_var    = tk.IntVar(value=0)    # 0 = không giới hạn
        self._plos_device_var   = tk.StringVar(value="cuda")
        self._plos_out_var      = tk.StringVar(value=str(EVAL_BASE_DIR / "plos"))
        self._plos_running      = False
        self._plos_process      = None

        # ── History tab state ──
        self._hist_rows:       list  = []   # list of (json_path, data_dict)
        self._hist_row_frames: list  = []   # tk.Frame refs per row (for highlight)
        self._hist_selected:   int   = -1   # index of currently selected row
        self._hist_detail_win          = None
        self._hist_table_inner         = None
        self._hist_sort_key:   str   = "timestamp"
        self._hist_sort_rev:   bool  = True

        # .pth inference state (Tab 1 — in-memory classification)
        self._is_pth             = False
        self._pth_infer_sd       = None    # state_dict (OrderedDict) loaded from .pth
        self._pth_infer_arch     = ""      # "JILSA 2022 (CustomCNN)" / "PLOS ONE 2024 (MobileNetV2)"
        self._pth_infer_nc       = 0       # num_classes detected from state_dict
        self._pth_infer_class_names: list = []   # mapped class names (auto-detect or manual)
        self._pth_class_names_var = tk.StringVar(value="")  # bound to editable UI entry

        self._build_ui()
        self._apply_ui_polish()
        self._load_saved_config()
        self._check_deps()

    def _build_scrollable_left(self, paned, *, width=320, minsize=280, padx=12, pady=10):
        container = ctk.CTkFrame(paned, fg_color=BG2, corner_radius=24, border_width=1, border_color=BORDER, width=width)
        inner = ctk.CTkScrollableFrame(
            container,
            fg_color=BG2,
            corner_radius=18,
            scrollbar_button_color=ACCENT,
            scrollbar_button_hover_color=ACCENT2,
        )
        inner.pack(fill="both", expand=True, padx=8, pady=8)
        return container, inner, minsize

    # ─────────────────────────────────────────────────────────────────────────
    # BUILD UI
    # ─────────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        host = ctk.CTkFrame(self, fg_color="transparent")
        host.pack(fill="both", expand=True)

        hdr, self._status_lbl = build_app_taskbar(
            ctk,
            host,
            title="Con Bò Cười - Đánh giá mô hình",
            subtitle="Kiểm thử nhanh, benchmark, so sánh và lịch sử đánh giá trong cùng một không gian kỹ thuật.",
            status_text="Chưa chạy",
            status_color=ACCENT,
        )
        hdr.pack(fill="x", padx=18, pady=(18, 0))

        metrics = build_metric_strip(
            ctk,
            host,
            [
                {"title": "Chế độ", "value": "4", "hint": "So sánh, Đánh giá, Lịch sử, Lịch sử so sánh", "accent": ACCENT},
                {"title": "Bề mặt", "value": "Giàu dữ liệu", "hint": "Biểu đồ, bảng, confusion matrix", "accent": SUCCESS},
                {"title": "Phạm vi", "value": "Vỏ UI", "hint": "Logic đánh giá được giữ nguyên", "accent": WARNING},
            ],
            columns=3,
        )
        metrics.pack(fill="x", padx=18, pady=(14, 8))

        # ── Notebook tabs ──
        style = ttk.Style(self)
        apply_ttk_theme(style)
        style.configure("Tester.TNotebook", background=BG, borderwidth=0)
        style.configure("Tester.TNotebook.Tab",
                        background=BG3, foreground=TEXT_DIM,
                        padding=[16, 8], font=("Segoe UI", 9, "bold"))
        style.map("Tester.TNotebook.Tab",
                  background=[("selected", ACCENT), ("active", ACCENT3)],
                  foreground=[("selected", "white"), ("active", TEXT)])

        nb = build_tabview(ctk, host)
        nb.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        nb.add("So sánh")
        nb.add("Đánh giá")
        nb.add("Lịch sử đánh giá")
        nb.add("Lịch sử so sánh")

        tab_compare = nb.tab("So sánh")
        self._build_comparison_tab(self._make_tab_shell(tab_compare))

        tab_eval = nb.tab("Đánh giá")
        self._build_eval_unified_tab(self._make_tab_shell(tab_eval))

        tab_hist = nb.tab("Lịch sử đánh giá")
        self._build_history_tab(self._make_tab_shell(tab_hist))

        tab_cmp_hist = nb.tab("Lịch sử so sánh")
        self._build_cmp_history_tab(self._make_tab_shell(tab_cmp_hist))

    def _make_tab_shell(self, parent):
        shell = build_page_body(ctk, parent, padx=6, pady=8)
        banner = build_dashboard_banner(
            ctk,
            shell,
            eyebrow="KHÔNG GIAN ĐÁNH GIÁ",
            title="Bảng điều khiển kỹ thuật tập trung cho validation và so sánh mô hình",
            description="Mỗi tab giữ nguyên logic inference và lịch sử hiện có, nhưng được đặt trong một lớp giao diện mạch lạc và dễ đọc hơn.",
            accent=ACCENT,
            compact=True,
        )
        banner.pack(fill="x", padx=8, pady=(8, 10))
        return shell

    def _set_chart_caption(self, key: str, text: str):
        lbl = getattr(self, f"_{key}_chart_caption_lbl", None)
        if lbl is None:
            return
        try:
            lbl.configure(text=f"Biểu đồ hiện tại: {text}")
        except Exception:
            pass

    def _fit_pil_to_canvas(self, canvas: tk.Canvas, pil_img, min_w: int = 320, min_h: int = 180):
        Image, ImageTk, _, _ = _import_pil()
        cw = max(canvas.winfo_width() or 0, min_w)
        ch = max(canvas.winfo_height() or 0, min_h)
        iw, ih = pil_img.size
        if iw <= 0 or ih <= 0:
            return ImageTk.PhotoImage(pil_img), pil_img
        scale = min(cw / iw, ch / ih)
        nw = max(1, int(iw * scale))
        nh = max(1, int(ih * scale))
        fitted = pil_img.resize((nw, nh), Image.LANCZOS if hasattr(Image, "LANCZOS") else Image.ANTIALIAS)
        return ImageTk.PhotoImage(fitted), fitted

    def _paint_pil_on_canvas(self, canvas: tk.Canvas, pil_img, *, min_w: int = 320, min_h: int = 180):
        tk_img, fitted = self._fit_pil_to_canvas(canvas, pil_img, min_w=min_w, min_h=min_h)
        cw = max(canvas.winfo_width() or 0, min_w)
        ch = max(canvas.winfo_height() or 0, min_h)
        canvas.delete("all")
        canvas.create_image(cw // 2, ch // 2, anchor="center", image=tk_img)
        canvas._pil_img = fitted
        canvas._tk_img = tk_img
        return tk_img, fitted

    def _save_chart_pil_image(self, pil_img, *, title: str, initialfile: str):
        from tkinter import filedialog as _fd
        if pil_img is None:
            messagebox.showinfo("Thông báo", "Chưa có biểu đồ để lưu. Hãy chạy tác vụ trước.")
            return
        save_path = _fd.asksaveasfilename(
            title=title,
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("All files", "*.*")],
            initialfile=initialfile,
        )
        if not save_path:
            return
        try:
            pil_img.save(save_path)
            messagebox.showinfo("Đã lưu", f"Biểu đồ đã được lưu tại:\n{save_path}")
        except Exception as ex:
            messagebox.showerror("Lỗi", f"Không thể lưu biểu đồ:\n{ex}")

    def _apply_button_hover(self, widget: tk.Button):
        try:
            base_bg = str(widget.cget("bg"))
        except Exception:
            base_bg = str(widget.cget("fg_color"))
        try:
            base_fg = str(widget.cget("fg"))
        except Exception:
            base_fg = str(widget.cget("text_color"))
        hover_bg = ACCENT if base_bg in {BG2, BG3, BG4} else ACCENT3
        hover_fg = "white" if hover_bg != BG3 else TEXT
        try:
            widget.configure(relief="flat", bd=0, activebackground=hover_bg, activeforeground=hover_fg, highlightthickness=0, cursor="hand2")
        except Exception:
            try:
                widget.configure(hover_color=hover_bg, cursor="hand2")
            except Exception:
                return

        def _on_enter(_event):
            try:
                widget.configure(bg=hover_bg, fg=hover_fg)
            except Exception:
                try:
                    widget.configure(fg_color=hover_bg, text_color=hover_fg)
                except Exception:
                    pass

        def _on_leave(_event):
            try:
                widget.configure(bg=base_bg, fg=base_fg)
            except Exception:
                try:
                    widget.configure(fg_color=base_bg, text_color=base_fg)
                except Exception:
                    pass

        widget.bind("<Enter>", _on_enter, add="+")
        widget.bind("<Leave>", _on_leave, add="+")

    def _apply_ui_polish(self):
        def _walk(node):
            for child in node.winfo_children():
                if child.__class__.__name__ in {"Button", "CTkButton"}:
                    self._apply_button_hover(child)
                elif isinstance(child, tk.Entry):
                    try:
                        apply_entry_theme(child)
                    except Exception:
                        pass
                elif isinstance(child, tk.Text):
                    try:
                        apply_textbox_theme(child, dark=True)
                    except Exception:
                        pass
                _walk(child)
        _walk(self)

    # ── helper widgets ────────────────────────────────────────────────────────
    def _sec(self, parent, text):
        tk.Label(parent, text=text, font=("Segoe UI", 9, "bold"),
                 bg=BG2, fg=ACCENT2).pack(anchor="w", pady=(10, 2))

    def _row(self, parent, label, widget_factory):
        f = tk.Frame(parent, bg=BG2)
        f.pack(fill="x", pady=2)
        tk.Label(f, text=label, width=16, anchor="w",
                 font=("Segoe UI", 9), bg=BG2, fg=TEXT).pack(side="left")
        w = widget_factory(f)
        w.pack(side="left", fill="x", expand=True)
        return w

    def _spin(self, parent, var, from_, to, increment=1, width=8):
        return tk.Spinbox(parent, textvariable=var, from_=from_, to=to,
                          increment=increment, width=width,
                          bg=BG3, fg=TEXT, buttonbackground=BG3,
                          insertbackground=TEXT, relief="flat",
                          font=("Segoe UI", 9))

    # ── LEFT PANEL ────────────────────────────────────────────────────────────
    def _build_left(self, parent):
        sec  = lambda t: self._sec(parent, t)
        row  = lambda l, f: self._row(parent, l, f)
        spin = self._spin

        # ── Model ──
        sec("🤖 Model")
        f_model = tk.Frame(parent, bg=BG2)
        f_model.pack(fill="x", pady=2)
        model_entry = tk.Entry(f_model, textvariable=self._model_path, font=("Segoe UI", 8))
        apply_entry_theme(model_entry)
        model_entry.pack(side="left", fill="x", expand=True, padx=(0, 2))
        tk.Button(f_model, text="...", command=self._browse_model,
                  bg=BG3, fg=TEXT, relief="flat", padx=4, cursor="hand2").pack(side="left")

        self._load_btn = tk.Button(parent, text="⬆  Tải model",
                                   font=("Segoe UI", 9, "bold"),
                                   bg=ACCENT, fg="white", relief="flat",
                                   cursor="hand2", pady=5,
                                   command=self._load_model)
        self._load_btn.pack(fill="x", pady=(4, 2))
        self._model_info_lbl = tk.Label(parent, text="", font=("Segoe UI", 8),
                                        bg=BG2, fg=TEXT_DIM, justify="left", wraplength=260)
        self._model_info_lbl.pack(anchor="w")

        # ── Task ──
        sec("🎯 Loại Task")
        self._task_cb = ttk.Combobox(parent, textvariable=self._task_var,
                                     values=TASK_TYPES, state="readonly",
                                     font=("Segoe UI", 9))
        self._task_cb.pack(fill="x", pady=2)
        self._task_cb.bind("<<ComboboxSelected>>", self._on_task_changed)

        # ── Input ──
        sec("📥 Nguồn đầu vào")
        src_cb = ttk.Combobox(parent, textvariable=self._source_var,
                               values=INPUT_SOURCES, state="readonly",
                               font=("Segoe UI", 9))
        src_cb.pack(fill="x", pady=2)
        src_cb.bind("<<ComboboxSelected>>", self._on_source_changed)

        # Input path row (ảnh / video)
        self._input_frame = tk.Frame(parent, bg=BG2)
        self._input_frame.pack(fill="x", pady=2)
        self._input_entry = tk.Entry(
            self._input_frame,
            textvariable=self._input_path,
            font=("Segoe UI", 8),
        )
        apply_entry_theme(self._input_entry)
        self._input_entry.pack(side="left", fill="x", expand=True, padx=(0, 2))
        self._input_browse_btn = tk.Button(self._input_frame, text="...",
                                           command=self._browse_input,
                                           bg=BG3, fg=TEXT, relief="flat",
                                           padx=4, cursor="hand2")
        self._input_browse_btn.pack(side="left")

        # Webcam row (ẩn mặc định)
        self._cam_frame = tk.Frame(parent, bg=BG2)
        tk.Label(self._cam_frame, text="Cam index", width=10, anchor="w",
                 font=("Segoe UI", 9), bg=BG2, fg=TEXT).pack(side="left")
        spin(self._cam_frame, self._cam_idx_var, 0, 10).pack(side="left")

        # ── Params ── (Confidence & IOU điều chỉnh bằng slider bên phải)
        sec("⚙ Tham số suy luận")
        row("Img size",   lambda p: spin(p, self._imgsz_var, 320, 1280, 32))
        row("Device",     lambda p: ttk.Combobox(p, textvariable=self._device_var,
                          values=["0","cpu"], state="readonly",
                          font=("Segoe UI", 9), width=6))

        f_checks = tk.Frame(parent, bg=BG2)
        f_checks.pack(fill="x", pady=4)
        tk.Checkbutton(f_checks, text="Half (FP16)", variable=self._half_var,
                       bg=BG2, fg=TEXT, selectcolor=BG3,
                       activebackground=BG2, font=("Segoe UI", 9)).pack(side="left")
        tk.Checkbutton(f_checks, text="Lưu kết quả", variable=self._save_var,
                       bg=BG2, fg=TEXT, selectcolor=BG3,
                       activebackground=BG2, font=("Segoe UI", 9)).pack(side="left", padx=8)

        # ── Dynamic Auto Conf toggle ──────────────────────────────────────
        dyn_frame = tk.Frame(parent, bg=BG3, padx=8, pady=6,
                             relief="flat", bd=0)
        dyn_frame.pack(fill="x", pady=(4, 2))

        dyn_icon_lbl = tk.Label(dyn_frame, text="🎯",
                                font=("Segoe UI Emoji", 10),
                                bg=BG3, fg=TEXT)
        dyn_icon_lbl.pack(side="left")

        dyn_text_lbl = tk.Label(dyn_frame,
                                text=" Dynamic Auto Conf",
                                font=("Segoe UI", 9, "bold"),
                                bg=BG3, fg=TEXT_DIM)
        dyn_text_lbl.pack(side="left", fill="x", expand=True)

        # Toggle button (ON/OFF)
        self._dyn_btn = tk.Button(
            dyn_frame, text="OFF",
            font=("Segoe UI", 8, "bold"),
            bg=BG2, fg=TEXT_DIM,
            activebackground=BG2, relief="flat",
            padx=10, pady=2, cursor="hand2",
            command=self._toggle_dynamic_conf,
        )
        self._dyn_btn.pack(side="right")

        # ── Buttons ──
        btn_frame = tk.Frame(parent, bg=BG2)
        btn_frame.pack(fill="x", pady=(14, 4))

        self._run_btn = tk.Button(btn_frame, text="▶  Chạy Inference",
                                  font=("Segoe UI", 10, "bold"),
                                  bg=SUCCESS, fg="white", relief="flat",
                                  cursor="hand2", pady=8,
                                  command=self._run_inference,
                                  state="disabled")
        self._run_btn.pack(fill="x", pady=2)

        self._stop_btn = tk.Button(btn_frame, text="⏹  Dừng",
                                   font=("Segoe UI", 10, "bold"),
                                   bg=DANGER, fg="white", relief="flat",
                                   cursor="hand2", pady=8,
                                   command=self._stop_inference,
                                   state="disabled")
        self._stop_btn.pack(fill="x", pady=2)

        tk.Button(btn_frame, text="💾  Lưu ảnh hiện tại",
                  font=("Segoe UI", 9),
                  bg=BG3, fg=TEXT_DIM, relief="flat",
                  cursor="hand2", pady=6,
                  command=self._save_current_frame).pack(fill="x", pady=2)

        tk.Button(btn_frame, text="⚙  Lưu & Xem cấu hình",
                  font=("Segoe UI", 9),
                  bg=BG3, fg=TEXT_DIM, relief="flat",
                  cursor="hand2", pady=6,
                  command=self._save_and_show_config).pack(fill="x", pady=2)

        # stats
        self._stats_lbl = tk.Label(parent, text="", font=("Segoe UI", 8),
                                   bg=BG2, fg=TEXT_DIM, justify="left")
        self._stats_lbl.pack(anchor="w", pady=(6, 0))

        # ── Gemini API Key ──
        self._sec(parent, "🔑 Gemini API Key")
        gemini_entry = tk.Entry(
            parent,
            textvariable=self._gemini_key_var,
            font=("Segoe UI", 8),
            show="•",
        )
        apply_entry_theme(gemini_entry)
        gemini_entry.pack(fill="x", pady=2)
    # ── RIGHT PANEL ────────────────────────────────────────────────────────────
    def _build_right(self, parent):
        from tkinter import scrolledtext as _st

        # Horizontal split: canvas (left) | side panel (right)
        r_paned = tk.PanedWindow(parent, orient="horizontal", bg=BG,
                                 sashwidth=4, sashrelief="flat")
        r_paned.pack(fill="both", expand=True)

        canvas_wrap = tk.Frame(r_paned, bg=BG)
        side        = tk.Frame(r_paned, bg=BG2, padx=10, pady=6, width=300)
        r_paned.add(canvas_wrap, minsize=400)
        r_paned.add(side,        minsize=260)

        # ── Canvas area ──
        badge = tk.Frame(canvas_wrap, bg=BG3, padx=10, pady=5)
        badge.pack(fill="x", padx=4, pady=(4, 0))
        self._fps_lbl = tk.Label(badge, text="FPS: —",
                                 font=("Segoe UI", 9), bg=BG3, fg=TEXT_DIM)
        self._fps_lbl.pack(side="left")
        self._task_badge = tk.Label(badge, text="Detection",
                                    font=("Segoe UI", 9, "bold"),
                                    bg=ACCENT, fg="white", padx=6, pady=1)
        self._task_badge.pack(side="right", padx=(6, 0))
        self._detect_count_lbl = tk.Label(badge, text="0 objects detected",
                                          font=("Segoe UI", 10, "bold"),
                                          bg=BG3, fg=TEXT)
        self._detect_count_lbl.pack(side="right")

        self._canvas = tk.Canvas(canvas_wrap, bg=BG4,
                                 highlightthickness=0, cursor="crosshair")
        self._canvas.pack(fill="both", expand=True, padx=4, pady=(2, 4))
        self._canvas_img = _CanvasImage(self._canvas)
        self._canvas.bind("<Configure>", self._on_canvas_resize)
        self._placeholder_visible = True
        self._draw_placeholder()

        # ── Side panel: sliders ──
        self._conf_pct_var = tk.IntVar(value=int(self._conf_var.get() * 100))
        self._iou_pct_var  = tk.IntVar(value=int(self._iou_var.get() * 100))

        def _make_slider(label_text, int_var, on_change_fn):
            tk.Frame(side, bg=BG3, height=1).pack(fill="x", pady=(10, 0))
            row = tk.Frame(side, bg=BG2)
            row.pack(fill="x", pady=(6, 0))
            tk.Label(row, text=label_text, font=("Segoe UI", 9, "bold"),
                     bg=BG2, fg=TEXT, anchor="w").pack(side="left", fill="x", expand=True)
            val_lbl = tk.Label(row, text=f"{int_var.get()}%",
                               font=("Segoe UI", 9, "bold"),
                               bg=BG2, fg=ACCENT2, width=6, anchor="e")
            val_lbl.pack(side="right")

            row2 = tk.Frame(side, bg=BG2)
            row2.pack(fill="x")
            tk.Label(row2, text="0%", font=("Segoe UI", 7),
                     bg=BG2, fg=TEXT_DIM).pack(side="left")
            sc = tk.Scale(row2, variable=int_var, from_=0, to=100,
                          orient="horizontal", showvalue=False,
                          bg=BG2, troughcolor=BG3, activebackground=ACCENT2,
                          highlightthickness=0, cursor="hand2",
                          sliderlength=14, sliderrelief="flat", width=10,
                          command=lambda _: None)
            sc.pack(side="left", fill="x", expand=True)
            tk.Label(row2, text="100%", font=("Segoe UI", 7),
                     bg=BG2, fg=TEXT_DIM).pack(side="right")

            def _on_write(*_):
                val_lbl.configure(text=f"{int_var.get()}%")
                on_change_fn()
            int_var.trace_add("write", _on_write)

        def _sync_conf():
            self._conf_var.set(self._conf_pct_var.get() / 100)
            self._schedule_filter_render()

        def _sync_iou():
            self._iou_var.set(self._iou_pct_var.get() / 100)
            self._schedule_filter_render()

        def _sync_opacity():
            self._schedule_filter_render()

        _make_slider("Confidence  (hiển thị):", self._conf_pct_var, _sync_conf)
        _make_slider("IOU  (hiển thị):",         self._iou_pct_var,  _sync_iou)
        _make_slider("Opacity mask:",             self._opacity_var,  _sync_opacity)

        # ── Chẩn đoán panel ──
        tk.Frame(side, bg=BG3, height=1).pack(fill="x", pady=(12, 0))
        diag_hdr = tk.Frame(side, bg=BG2)
        diag_hdr.pack(fill="x", pady=(6, 2))
        tk.Label(diag_hdr, text="🩺  Kết quả chẩn đoán",
                 font=("Segoe UI", 9, "bold"), bg=BG2, fg=ACCENT2).pack(side="left")
        self._diag_count_lbl = tk.Label(diag_hdr, text="—",
                 font=("Segoe UI", 8, "bold"), bg=BG2, fg=TEXT_DIM)
        self._diag_count_lbl.pack(side="right")

        # Editable class names entry (shown when .pth loaded)
        self._pth_cls_name_frame = tk.Frame(side, bg=BG2)
        # packed/unpacked dynamically in _on_pth_model_loaded / _on_model_loaded
        f_cne = tk.Frame(self._pth_cls_name_frame, bg=BG2)
        f_cne.pack(fill="x", pady=(2, 0))
        tk.Label(f_cne, text="Tên class (phẩy):",
                 font=("Segoe UI", 8), bg=BG2, fg=TEXT_DIM).pack(side="left")
        self._pth_cls_apply_btn = tk.Button(
            f_cne, text="Áp dụng",
            font=("Segoe UI", 8), bg=ACCENT, fg="white",
            relief="flat", padx=6, cursor="hand2",
            command=self._apply_pth_class_names)
        self._pth_cls_apply_btn.pack(side="right")
        self._pth_cls_name_entry = tk.Entry(
            self._pth_cls_name_frame,
            textvariable=self._pth_class_names_var,
            font=("Segoe UI", 8),
        )
        apply_entry_theme(self._pth_cls_name_entry)
        self._pth_cls_name_entry.pack(fill="x", pady=(2, 2))
        self._pth_cls_name_entry.bind("<Return>", lambda _: self._apply_pth_class_names())
        tk.Label(self._pth_cls_name_frame,
                 text="  ↳ ImageFolder xếp theo A–Z  (ví dụ: Viêm_Da_Nổi_Cục, Nấm_Da, Mụn_Cóc)",
                 font=("Segoe UI", 7, "italic"), bg=BG2, fg=TEXT_DIM).pack(anchor="w")

        # Scrollable class list
        self._cls_wrap = tk.Frame(side, bg=BG4, height=120)
        self._cls_wrap.pack(fill="x", pady=(2, 4))
        self._cls_wrap.pack_propagate(False)
        cls_cv = tk.Canvas(self._cls_wrap, bg=BG4, highlightthickness=0)
        cls_sb = tk.Scrollbar(self._cls_wrap, orient="vertical", command=cls_cv.yview)
        cls_cv.configure(yscrollcommand=cls_sb.set)
        cls_sb.pack(side="right", fill="y")
        cls_cv.pack(side="left", fill="both", expand=True)
        self._cls_inner = tk.Frame(cls_cv, bg=BG4)
        self._cls_win_id = cls_cv.create_window((0, 0), window=self._cls_inner, anchor="nw")
        cls_cv.bind("<Configure>", lambda e: cls_cv.itemconfigure(self._cls_win_id, width=e.width))
        self._cls_inner.bind("<Configure>", lambda e: cls_cv.configure(scrollregion=cls_cv.bbox("all")))
        self._cls_no_model_lbl = tk.Label(
            self._cls_inner, text="(Chưa tải model)",
            font=("Segoe UI", 8), bg=BG4, fg=TEXT_DIM)
        self._cls_no_model_lbl.pack(pady=8)

        # ── Kết quả dự đoán .pth (ẩn cho đến khi inference chạy) ──────────
        self._pth_pred_frame = tk.Frame(side, bg=BG2)
        # không pack ngay — sẽ hiện qua _show_pth_result()
        pred_title_row = tk.Frame(self._pth_pred_frame, bg=BG2)
        pred_title_row.pack(fill="x", pady=(4, 2))
        tk.Label(pred_title_row, text="📊  Xác suất dự đoán",
                 font=("Segoe UI", 9, "bold"), bg=BG2, fg=ACCENT2).pack(side="left")
        self._pth_pred_time_lbl = tk.Label(pred_title_row, text="",
                 font=("Segoe UI", 8), bg=BG2, fg=TEXT_DIM)
        self._pth_pred_time_lbl.pack(side="right")
        # top-1 badge
        self._pth_top1_frame = tk.Frame(self._pth_pred_frame, bg=BG3, padx=8, pady=6)
        self._pth_top1_frame.pack(fill="x", pady=(0, 4))
        self._pth_top1_icon  = tk.Label(self._pth_top1_frame, text="🏆",
                 font=("Segoe UI", 16), bg=BG3)
        self._pth_top1_icon.pack(side="left")
        _t1_right = tk.Frame(self._pth_top1_frame, bg=BG3)
        _t1_right.pack(side="left", padx=(8, 0))
        self._pth_top1_name = tk.Label(_t1_right, text="—",
                 font=("Segoe UI", 11, "bold"), bg=BG3, fg=SUCCESS)
        self._pth_top1_name.pack(anchor="w")
        self._pth_top1_conf = tk.Label(_t1_right, text="—",
                 font=("Segoe UI", 9), bg=BG3, fg=TEXT_DIM)
        self._pth_top1_conf.pack(anchor="w")
        # progress bars for each class
        self._pth_bar_frame = tk.Frame(self._pth_pred_frame, bg=BG2)
        self._pth_bar_frame.pack(fill="x", pady=(0, 4))
        self._pth_bar_rows: list = []   # list of (lbl_name, bar_canvas, lbl_pct) tuples

        # LLM section
        tk.Frame(side, bg=BG3, height=1).pack(fill="x", pady=(8, 0))
        llm_hdr = tk.Frame(side, bg=BG2)
        llm_hdr.pack(fill="x", pady=(4, 2))
        tk.Label(llm_hdr, text="🤖  Phân tích Gemini AI",
                 font=("Segoe UI", 9, "bold"), bg=BG2, fg=ACCENT2).pack(side="left")
        self._gemini_btn = tk.Button(
            llm_hdr, text="▶ Phân tích",
            font=("Segoe UI", 8, "bold"),
            bg=ACCENT, fg="white", relief="flat", padx=8, cursor="hand2",
            command=self._call_gemini)
        self._gemini_btn.pack(side="right")

        self._llm_box = _st.ScrolledText(
            side,
            relief="flat",
            font=("Segoe UI", 8),
            wrap="word",
            state="disabled",
            height=8,
        )
        apply_textbox_theme(self._llm_box, dark=True)
        self._llm_box.pack(fill="both", expand=True, pady=(0, 4))

        # ── Debug log (small, bottom) ──
        self._log_box = _st.ScrolledText(
            side,
            relief="flat",
            font=("Cascadia Code", 7),
            height=3,
            state="disabled",
            wrap="word",
        )
        apply_textbox_theme(self._log_box, dark=True)
        self._log_box.pack(fill="x", pady=(0, 2))
        self._log_box.tag_config("ok",   foreground="#22c55e")
        self._log_box.tag_config("warn", foreground="#f59e0b")
        self._log_box.tag_config("err",  foreground="#ef4444")
        self._log_box.tag_config("info", foreground="#38bdf8")

    # ─────────────────────────────────────────────────────────────────────────
    # DYNAMIC CONF TOGGLE
    # ─────────────────────────────────────────────────────────────────────────
    def _toggle_dynamic_conf(self):
        is_on = not self._dynamic_conf_var.get()
        self._dynamic_conf_var.set(is_on)
        if is_on:
            self._dyn_btn.configure(
                text="ON ",
                bg=WARNING, fg="#1a1a2e",
                activebackground=WARNING,
            )
        else:
            self._dyn_btn.configure(
                text="OFF",
                bg=BG2, fg=TEXT_DIM,
                activebackground=BG2,
            )

    # ─────────────────────────────────────────────────────────────────────────
    # LOG HELPER
    # ─────────────────────────────────────────────────────────────────────────
    def _log(self, text: str, tag: str = ""):
        def _write():
            self._log_box.configure(state="normal")
            if tag:
                self._log_box.insert("end", text + "\n", tag)
            else:
                self._log_box.insert("end", text + "\n")
            self._log_box.configure(state="disabled")
            self._log_box.see("end")
        self.after(0, _write)

    # ─────────────────────────────────────────────────────────────────────────
    # PLACEHOLDER
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_placeholder(self):
        self._canvas.delete("placeholder")
        w = self._canvas.winfo_width()  or 640
        h = self._canvas.winfo_height() or 480
        cx, cy = w // 2, h // 2
        self._canvas.create_text(cx, cy - 20, text="🖼",
                                  font=("Segoe UI Emoji", 40),
                                  fill=TEXT_DIM, tags="placeholder")
        self._canvas.create_text(cx, cy + 34,
                                  text="Tải model → Chọn nguồn → Chạy Inference",
                                  font=("Segoe UI", 13), fill=TEXT_DIM,
                                  tags="placeholder")

    def _on_canvas_resize(self, _event):
        if self._placeholder_visible:
            self._draw_placeholder()

    def _get_canvas_pil_image(self, canvas: tk.Canvas):
        pil_img = getattr(canvas, "_pil_img", None)
        if pil_img is not None:
            return pil_img
        tk_img = getattr(canvas, "_tk_img", None)
        if tk_img is None:
            return None
        try:
            from PIL import ImageTk as _ITK
            return _ITK.getimage(tk_img).convert("RGB")
        except Exception:
            return None

    def _open_chart_fullscreen(self, canvas: tk.Canvas, title: str):
        pil_img = self._get_canvas_pil_image(canvas)
        if pil_img is None:
            messagebox.showinfo("Thông báo", "Chưa có biểu đồ để mở toàn màn hình.")
            return

        win = tk.Toplevel(self)
        win.title(title)
        win.configure(bg=BG)
        try:
            win.state("zoomed")
        except Exception:
            pass
        try:
            win.attributes("-fullscreen", True)
        except Exception:
            pass

        hdr = tk.Frame(win, bg=BG3, padx=10, pady=8)
        hdr.pack(fill="x")
        tk.Label(
            hdr, text=f"{title}  ·  ESC để thoát",
            font=("Segoe UI", 10, "bold"), bg=BG3, fg=ACCENT2
        ).pack(side="left")
        tk.Button(
            hdr, text="Thu nhỏ", font=("Segoe UI", 8),
            bg=BG2, fg=TEXT, relief="flat", cursor="hand2",
            command=lambda: win.attributes("-fullscreen", False),
        ).pack(side="right", padx=4)
        tk.Button(
            hdr, text="Đóng", font=("Segoe UI", 8),
            bg=BG2, fg=TEXT, relief="flat", cursor="hand2",
            command=win.destroy,
        ).pack(side="right", padx=4)

        view = tk.Canvas(win, bg=BG4, highlightthickness=0)
        view.pack(fill="both", expand=True, padx=8, pady=8)
        viewer = _CanvasImage(view)

        def _redraw(_event=None):
            viewer.show(pil_img)
            view._pil_img = pil_img
            view._tk_img = viewer._tk_img

        view.bind("<Configure>", _redraw)
        win.bind("<Escape>", lambda _e: win.destroy())
        win.after(50, _redraw)

    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS UI
    # ─────────────────────────────────────────────────────────────────────────
    def _on_source_changed(self, _event=None):
        src = self._source_var.get()
        if src == "Webcam":
            self._input_frame.pack_forget()
            self._cam_frame.pack(fill="x", pady=2,
                                  after=self._task_cb)
        else:
            self._cam_frame.pack_forget()
            self._input_frame.pack(fill="x", pady=2)

    def _on_task_changed(self, _event=None):
        task = self._task_var.get()
        self._task_badge.configure(text=task)

    def _browse_model(self):
        f = filedialog.askopenfilename(
            title="Chọn file model",
            filetypes=[("All models", "*.pt *.pth *.onnx"),
                       ("YOLO (.pt/.onnx)", "*.pt *.onnx"),
                       ("PyTorch (.pth)", "*.pth"),
                       ("All files", "*.*")],
            initialdir=str(RUNS_DIR),
        )
        if f:
            self._model_path.set(f)

    def _browse_input(self):
        src = self._source_var.get()
        if src == "Ảnh (Image)":
            f = filedialog.askopenfilename(
                title="Chọn ảnh",
                filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.webp"),
                            ("All files", "*.*")],
            )
        else:
            f = filedialog.askopenfilename(
                title="Chọn video",
                filetypes=[("Videos", "*.mp4 *.avi *.mov *.mkv *.webm"),
                            ("All files", "*.*")],
            )
        if f:
            self._input_path.set(f)

    def _set_status(self, text: str, color: str = "white"):
        try:
            self._status_lbl.configure(text=text, fg_color=color, text_color="white")
        except Exception:
            self._status_lbl.configure(text=text, bg=color, fg="white")

    def _set_model_info(self, text: str, color: str = TEXT_DIM):
        lbl = getattr(self, "_model_info_lbl", None)
        if lbl is not None:
            try:
                lbl.configure(text=text, fg=color)
                return
            except Exception:
                try:
                    lbl.configure(text=text, text_color=color)
                    return
                except Exception:
                    pass
        self._set_status(text[:48], color)

    # ─────────────────────────────────────────────────────────────────────────
    # DEP CHECK  (chạy nền, tự cài nếu thiếu)
    # ─────────────────────────────────────────────────────────────────────────
    def _check_deps(self):
        self._set_model_info("⏳ Kiểm tra thư viện...", WARNING)
        threading.Thread(target=self._check_deps_thread, daemon=True).start()

    def _check_deps_thread(self):
        # Đảm bảo tất cả deps cần thiết đều có trong venv này
        _ensure_packages(
            "ultralytics",
            "opencv-python",
            "pillow",
            "onnx",
            "onnxslim",
            "onnxruntime-gpu",
        )
        import importlib
        missing = []
        for pkg, imp in [("ultralytics", "ultralytics"),
                         ("opencv-python", "cv2"),
                         ("pillow", "PIL")]:
            try:
                importlib.import_module(imp)
            except ImportError:
                missing.append(pkg)

        if missing:
            msg = (f"Thiếu thư viện: {', '.join(missing)}\n"
                   f"Chạy: pip install {' '.join(missing)}")
            self.after(0, self._set_model_info, msg, DANGER)
        else:
            self.after(0, self._set_model_info, "✔ Tất cả thư viện sẵn sàng.", SUCCESS)

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDER HELPERS
    # ─────────────────────────────────────────────────────────────────────────
    def _schedule_filter_render(self):
        """Debounce: chờ 300ms sau lần cuối thay đổi slider rồi re-render."""
        if self._debounce_id is not None:
            try:
                self.after_cancel(self._debounce_id)
            except Exception:
                pass
        self._debounce_id = self.after(300, self._filter_render)

    def _filter_render(self):
        """Re-render ảnh và JSON từ _last_result với ngưỡng conf/opacity hiện tại."""
        if self._last_result is None:
            return
        import traceback
        cv2   = _import_cv2()
        Image, _, _, _ = _import_pil()
        np    = _import_numpy()
        is_seg      = self._task_var.get() == "Instance Segmentation"
        conf_thresh = self._conf_var.get()
        opacity     = self._opacity_var.get()
        r = self._last_result
        if r.boxes is not None:
            n_pass  = sum(1 for b in r.boxes if float(b.conf[0]) >= conf_thresh)
            n_total = len(r.boxes)
            self._log(f"[filter] conf={conf_thresh:.0%}  {n_pass}/{n_total} boxes hiển thị", "info")
            self._set_status(f"🔍 conf={conf_thresh:.0%} | {n_pass}/{n_total} objects", WARNING)
        try:
            annotated = self._draw_result(
                r, cv2, Image, np, is_seg, conf_thresh, opacity)
            self._show_image(annotated)
            self._update_diagnosis(r, conf_thresh)
        except Exception:
            self._log(f"[re-render lỗi]\n{traceback.format_exc()}", "err")

    # ─────────────────────────────────────────────────────────────────────────
    # JSON HELPERS
    # ─────────────────────────────────────────────────────────────────────────
    def _build_predictions_json(self, result, conf_thresh: float) -> str:
        import json, uuid
        names      = result.names if hasattr(result, "names") and result.names else {}
        has_masks  = result.masks is not None
        preds      = []

        if result.boxes is None:
            return json.dumps({"predictions": []}, indent=2, ensure_ascii=False)

        for i, box in enumerate(result.boxes):
            conf = float(box.conf[0])
            if conf < conf_thresh:
                continue
            cls_id = int(box.cls[0])
            name   = names.get(cls_id, f"cls{cls_id}")
            xywh   = box.xywh[0].tolist()
            cx, cy, w, h = xywh[0], xywh[1], xywh[2], xywh[3]
            pred = {
                "x":           round(cx, 1),
                "y":           round(cy, 1),
                "width":       round(w,  1),
                "height":      round(h,  1),
                "confidence":  round(conf, 3),
                "class":       name,
                "class_id":    cls_id,
                "detection_id": str(uuid.uuid4()),
            }
            if has_masks and result.masks.xy is not None and i < len(result.masks.xy):
                poly = result.masks.xy[i]
                if len(poly) >= 3:
                    pred["points"] = [
                        {"x": round(float(p[0]), 1), "y": round(float(p[1]), 1)}
                        for p in poly
                    ]
            preds.append(pred)

        return json.dumps({"predictions": preds}, indent=2, ensure_ascii=False)

    def _update_json(self, result, conf_thresh: float = 0.0):
        json_str = self._build_predictions_json(result, conf_thresh)
        self._json_box.configure(state="normal")
        self._json_box.delete("1.0", "end")
        self._json_box.insert("end", json_str)
        self._json_box.configure(state="disabled")
        # Update count badge
        n = 0
        if result.boxes is not None:
            n = sum(1 for b in result.boxes if float(b.conf[0]) >= conf_thresh)
        self._detect_count_lbl.configure(text=f"{n} objects detected")

    def _copy_json(self):
        txt = self._json_box.get("1.0", "end").strip()
        if txt:
            self.clipboard_clear()
            self.clipboard_append(txt)

    # ─────────────────────────────────────────────────────────────────────────
    # DIAGNOSIS + LLM
    # ─────────────────────────────────────────────────────────────────────────
    def _populate_class_list(self):
        """Tạo hàng class trong panel chẩn đoán sau khi model được tải."""
        for w in self._cls_inner.winfo_children():
            w.destroy()
        self._class_row_widgets.clear()
        if self._model is None or not hasattr(self._model, "names"):
            tk.Label(self._cls_inner, text="(Chưa tải model)",
                     font=("Segoe UI", 8), bg=BG4, fg=TEXT_DIM).pack(pady=8)
            return
        for cls_id, cls_name in sorted(self._model.names.items()):
            row = tk.Frame(self._cls_inner, bg=BG4)
            row.pack(fill="x", padx=4, pady=1)
            badge    = tk.Label(row, text="❓", font=("Segoe UI", 10),
                                bg=BG4, fg=TEXT_DIM, width=2)
            badge.pack(side="left")
            name_lbl = tk.Label(row, text=cls_name, font=("Segoe UI", 9),
                                bg=BG4, fg=TEXT_DIM, anchor="w")
            name_lbl.pack(side="left", fill="x", expand=True)
            conf_lbl = tk.Label(row, text="—", font=("Cascadia Code", 8),
                                bg=BG4, fg=TEXT_DIM, width=7, anchor="e")
            conf_lbl.pack(side="right")
            self._class_row_widgets[cls_id] = (row, badge, name_lbl, conf_lbl)
        self._diag_count_lbl.configure(text="—", fg=TEXT_DIM)
        self._last_diagnosis = []

    def _update_diagnosis(self, result, conf_thresh: float = 0.0):
        """Cập nhật panel chẩn đoán: mỗi class True/False với confidence tốt nhất."""
        if result is None or result.boxes is None:
            return
        names = result.names if hasattr(result, "names") and result.names else {}
        best: dict = {}
        for box in result.boxes:
            conf   = float(box.conf[0])
            cls_id = int(box.cls[0])
            if conf >= conf_thresh:
                if cls_id not in best or conf > best[cls_id]:
                    best[cls_id] = conf
        n_det = len(best)
        n_cls = len(names)
        self._diag_count_lbl.configure(
            text=f"{n_det} / {n_cls} phát hiện",
            fg=SUCCESS if n_det > 0 else TEXT_DIM)
        self._detect_count_lbl.configure(text=f"{n_det} objects detected")
        for cls_id in self._class_row_widgets:
            _, badge, name_lbl, conf_lbl = self._class_row_widgets[cls_id]
            if cls_id in best:
                badge.configure(text="✅", fg="#22c55e")
                name_lbl.configure(fg=TEXT)
                conf_lbl.configure(text=f"{best[cls_id]:.0%}", fg=SUCCESS)
            else:
                badge.configure(text="❌", fg="#ef4444")
                name_lbl.configure(fg=TEXT_DIM)
                conf_lbl.configure(text="—", fg=TEXT_DIM)
        self._last_diagnosis = [
            {"class": names.get(cid, f"cls{cid}"), "confidence": round(c, 3)}
            for cid, c in sorted(best.items(), key=lambda x: -x[1])
        ]

    def _call_gemini(self):
        """Gọi Gemini API để phân tích kết quả chẩn đoán."""
        api_key = self._gemini_key_var.get().strip()
        if not api_key:
            messagebox.showwarning("Thiếu API Key",
                "Vui lòng nhập Gemini API Key trong phần '🔑 Gemini API Key' ở panel trái.")
            return
        if not self._last_diagnosis and self._last_result is None:
            messagebox.showinfo("ℹ", "Hãy chạy inference trước.")
            return
        all_classes = (
            list(self._model.names.values())
            if self._model and hasattr(self._model, "names") else []
        )
        detected_names = {d["class"] for d in self._last_diagnosis}
        not_detected   = [c for c in all_classes if c not in detected_names]
        self._gemini_btn.configure(state="disabled", text="⏳...")
        self._llm_box.configure(state="normal")
        self._llm_box.delete("1.0", "end")
        self._llm_box.insert("end", "⏳ Đang hỏi Gemini AI...\n")
        self._llm_box.configure(state="disabled")
        detected    = list(self._last_diagnosis)
        api_key_val = api_key

        def _do():
            try:
                _ensure_packages("google-generativeai")
                import google.generativeai as genai
                genai.configure(api_key=api_key_val)
                mdl  = genai.GenerativeModel("gemini-2.5-flash")
                resp = mdl.generate_content(self._build_gemini_prompt(detected, not_detected))
                self.after(0, self._show_llm_result, resp.text)
            except Exception:
                import traceback
                self.after(0, self._show_llm_result,
                           f"❌ Lỗi kết nối Gemini:\n{traceback.format_exc()}")

        threading.Thread(target=_do, daemon=True).start()

    def _build_gemini_prompt(self, detected: list, not_detected: list) -> str:
        lines_det = "\n".join(
            f"  - {d['class']} (confidence: {d['confidence']:.0%})" for d in detected
        ) or "  (không có)"
        lines_not = "\n".join(f"  - {c}" for c in not_detected) or "  (không có)"
        return (
            "Bạn là bác sĩ thú y chuyên về bệnh ở bò. "
            "Hệ thống AI thị giác (YOLOv8 Instance Segmentation) "
            "đã phân tích ảnh và cho kết quả:\n\n"
            f"✅ Phát hiện:\n{lines_det}\n\n"
            f"❌ Không phát hiện:\n{lines_not}\n\n"
            "Dựa vào kết quả trên, hãy:\n"
            "1. Nhận xét tình trạng sức khỏe con bò\n"
            "2. Mô tả ngắn gọn từng bệnh được phát hiện (triệu chứng, mức độ nguy hiểm)\n"
            "3. Đề xuất hướng xử lý / điều trị\n"
            "Trả lời bằng tiếng Việt, ngắn gọn và chuyên nghiệp."
        )

    def _show_llm_result(self, text: str):
        self._llm_box.configure(state="normal")
        self._llm_box.delete("1.0", "end")
        self._llm_box.insert("end", text)
        self._llm_box.configure(state="disabled")
        self._gemini_btn.configure(state="normal", text="▶ Phân tích")

    # ─────────────────────────────────────────────────────────────────────────
    # LOAD MODEL
    # ─────────────────────────────────────────────────────────────────────────
    def _load_model(self):
        path = self._model_path.get().strip()
        if not path or not Path(path).exists():
            messagebox.showerror("Lỗi", "Vui lòng chọn file model hợp lệ (.pt, .onnx, hoặc .pth).")
            return

        self._load_btn.configure(state="disabled", text="⏳ Đang tải...")
        self._set_status("⏳ Đang tải model...", WARNING)
        suffix = Path(path).suffix.lower()

        # ── .pth: PyTorch state_dict (classification only) ─────────────────
        if suffix == ".pth":
            def _do_pth():
                try:
                    import torch
                    try:
                        _ckpt = torch.load(path, map_location="cpu", weights_only=True)
                    except Exception:
                        _ckpt = torch.load(path, map_location="cpu", weights_only=False)
                    # Support both new checkpoint {model_weights, class_names} and old state_dict
                    _saved_names = []
                    if isinstance(_ckpt, dict) and "model_weights" in _ckpt:
                        _saved_names = list(_ckpt.get("class_names", []))
                        sd = _ckpt["model_weights"]
                    else:
                        sd = _ckpt
                    use_mnv2 = "features.0.0.weight" in sd
                    arch = "PLOS ONE 2024 (MobileNetV2)" if use_mnv2 else "JILSA 2022 (CustomCNN)"
                    nc = 0
                    if "classifier.4.weight" in sd:
                        nc = sd["classifier.4.weight"].shape[0]
                    elif "classifier.1.weight" in sd:
                        nc = sd["classifier.1.weight"].shape[0]
                    params = sum(v.numel() for v in sd.values()
                                 if hasattr(v, "numel") and callable(v.numel))
                    info = (f"✔ Loaded: {Path(path).name} [.PTH]\n"
                            f"Arch: {arch}  |  {nc} classes\n"
                            f"Params: {params/1e6:.2f}M  |  Task: Classification")
                    self.after(0, self._on_pth_model_loaded, sd, arch, nc, info, _saved_names)
                except Exception as ex:
                    self.after(0, self._on_model_error, str(ex))
            threading.Thread(target=_do_pth, daemon=True).start()
            return

        # ── YOLO .pt / .onnx ─────────────────────────────────────────────
        def _do():
            try:
                if suffix == ".onnx":
                    _ensure_packages("onnx", "onnxslim", "onnxruntime-gpu")
                _ensure_packages("ultralytics")
                import importlib
                importlib.invalidate_caches()
                try:
                    import onnxruntime as _ort
                    _ort.set_default_logger_severity(3)
                except Exception:
                    pass
                YOLO = _import_yolo()
                task_map = {"Detection": "detect", "Instance Segmentation": "segment"}
                task = task_map.get(self._task_var.get(), "detect")
                self._model = YOLO(path, task=task)
                import numpy as _np
                _device  = self._device_var.get()
                _imgsz   = self._imgsz_var.get()
                _dummy   = _np.zeros((_imgsz, _imgsz, 3), dtype=_np.uint8)
                self._model.predict(source=_dummy, imgsz=_imgsz, device=_device, verbose=False)
                cls_names = list(self._model.names.values()) if hasattr(self._model, "names") else []
                info = (f"✔ Loaded: {Path(path).name} [{suffix.upper()}]\n"
                        f"Task: {self._task_var.get()}\n"
                        f"Classes ({len(cls_names)}): {', '.join(cls_names[:6])}"
                        f"{'...' if len(cls_names) > 6 else ''}")
                self.after(0, self._on_model_loaded, info)
            except Exception as ex:
                self.after(0, self._on_model_error, str(ex))
        threading.Thread(target=_do, daemon=True).start()

    # ──────────────────────────────────────────────────────────────────────────
    # .pth CLASS NAME HELPERS
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _detect_class_names_from_pth(pth_path: str, nc: int) -> list:
        """Try to auto-detect class names from files adjacent to the .pth."""
        import os, re
        pth_dir = Path(pth_path).parent

        # 1. classes.txt / class_names.txt / labels.txt in same folder or parent
        for search_dir in (pth_dir, pth_dir.parent):
            for fname in ("classes.txt", "class_names.txt", "labels.txt"):
                fp = search_dir / fname
                if fp.exists():
                    names = [l.strip() for l in fp.read_text(encoding="utf-8").splitlines() if l.strip()]
                    if len(names) == nc:
                        return names

        # 2. data.yaml in same folder, parent or grandparent
        for candidate in (pth_dir / "data.yaml", pth_dir.parent / "data.yaml",
                          pth_dir.parent.parent / "data.yaml", pth_dir / "dataset.yaml"):
            if candidate.exists():
                txt = candidate.read_text(encoding="utf-8")
                m = re.search(r"names\s*:\s*\[([^\]]+)\]", txt)
                if m:
                    names = [n.strip().strip("'\"")
                             for n in m.group(1).split(",") if n.strip()]
                    if len(names) == nc:
                        return names
                m2 = re.findall(r"^\s*-\s*(.+)$", txt, re.MULTILINE)
                if len(m2) == nc:
                    return [n.strip().strip("'\"") for n in m2]

        # 3. class_names.json next to pth
        fp_json = pth_dir / "class_names.json"
        if fp_json.exists():
            import json
            try:
                data = json.loads(fp_json.read_text(encoding="utf-8"))
                if isinstance(data, list) and len(data) == nc:
                    return [str(x) for x in data]
            except Exception:
                pass

        # 4. Smart defaults for known project models
        # ImageFolder sorts A–Z: Lumpy_Skin(0) Ringworm(1) Warts(2)
        if nc == 3:
            return ["Viêm da nổi cục", "Nấm da", "Mụn cóc"]
        # Healthy(0) Lumpy(1)
        if nc == 2:
            return ["Khỏe mạnh", "Viêm da nổi cục"]

        return []

    def _apply_pth_class_names(self):
        """Parse the class names entry field and update _pth_infer_class_names."""
        raw = self._pth_class_names_var.get()
        names = [n.strip() for n in raw.split(",") if n.strip()]
        nc = self._pth_infer_nc
        if not names:
            return
        if len(names) != nc:
            messagebox.showwarning(
                "Số class không khớp",
                f"Model có {nc} class nhưng bạn nhập {len(names)} tên.\n"
                f"Vui lòng nhập đúng {nc} tên cách nhau bởi dấu phẩy.")
            return
        self._pth_infer_class_names = names
        # refresh class panel
        for w in self._cls_inner.winfo_children():
            w.destroy()
        colors = ["#4ade80", "#38bdf8", "#f59e0b", "#f87171",
                  "#a78bfa", "#34d399", "#fb923c", "#e879f9"]
        for i, name in enumerate(names):
            tk.Label(self._cls_inner,
                     text=f"• {name}",
                     font=("Segoe UI", 8, "bold"), bg=BG4,
                     fg=colors[i % len(colors)]).pack(anchor="w", padx=4)
        self._diag_count_lbl.configure(
            text=f"{nc} classes  ✔", fg=SUCCESS)

    def _on_pth_model_loaded(self, sd, arch: str, nc: int, info: str, saved_class_names: list = None):
        """Store .pth state dict and update UI for classification inference."""
        self._is_pth         = True
        self._pth_infer_sd   = sd
        self._pth_infer_arch = arch
        self._pth_infer_nc   = nc
        self._model          = None

        # ── Resolve class names: checkpoint → file detection → smart default ──
        pth_path = self._model_path.get().strip()
        if saved_class_names:
            detected = saved_class_names
            src_tag  = "từ model"
        else:
            detected = self._detect_class_names_from_pth(pth_path, nc)
            src_tag  = "từ file" if detected else "mặc định"
        if detected:
            self._pth_infer_class_names = detected
        else:
            self._pth_infer_class_names = [f"Class_{i}" for i in range(nc)]
        self._pth_class_names_var.set(", ".join(self._pth_infer_class_names))

        self._set_model_info(info, "#4ade80")
        self._load_btn.configure(state="normal", text="⬆  Tải model")
        self._run_btn.configure(state="normal")
        self._set_status("✔ .pth sẵn sàng (Classification)", SUCCESS)
        self._task_var.set("Classification")
        self._task_badge.configure(text="Classification (.pth)")
        # show class name entry (insert BEFORE class list for correct layout)
        self._pth_cls_name_frame.pack(before=self._cls_wrap, fill="x", pady=(2, 0))
        # populate class list
        for w in self._cls_inner.winfo_children():
            w.destroy()
        self._cls_no_model_lbl = None
        colors = ["#4ade80", "#38bdf8", "#f59e0b", "#f87171",
                  "#a78bfa", "#34d399", "#fb923c", "#e879f9"]
        for i, name in enumerate(self._pth_infer_class_names):
            tk.Label(self._cls_inner,
                     text=f"• {name}",
                     font=("Segoe UI", 8, "bold"), bg=BG4,
                     fg=colors[i % len(colors)]).pack(anchor="w", padx=4)
        suffix = f"  ({src_tag})"
        self._diag_count_lbl.configure(text=f"{nc} classes{suffix}", fg=SUCCESS if detected else TEXT_DIM)
        self._pth_arch_var.set(arch)

    def _on_model_loaded(self, info: str):
        self._is_pth = False
        self._pth_infer_sd = None
        self._pth_infer_class_names = []
        self._set_model_info(info, SUCCESS)
        self._load_btn.configure(state="normal", text="⬆  Tải model")
        self._run_btn.configure(state="normal")
        self._set_status("✔ Model sẵn sàng", SUCCESS)
        self._task_badge.configure(text=self._task_var.get())
        self._pth_cls_name_frame.pack_forget()  # hide class name editor for YOLO models
        self._pth_pred_frame.pack_forget()      # hide prediction panel for YOLO models
        self._populate_class_list()

    def _on_model_error(self, err: str):
        self._set_model_info(f"✗ Lỗi: {err[:150]}", DANGER)
        self._load_btn.configure(state="normal", text="⬆  Tải model")
        self._set_status("✗ Lỗi tải model", DANGER)

    # ─────────────────────────────────────────────────────────────────────────
    # RUN INFERENCE
    # ─────────────────────────────────────────────────────────────────────────
    def _run_inference(self):
        # ── .pth classification model ──────────────────────────────────────
        if self._is_pth:
            if self._pth_infer_sd is None:
                messagebox.showwarning("Chưa tải model", "Hãy tải lại model .pth.")
                return
            src = self._source_var.get()
            if src == "Webcam":
                source = self._cam_idx_var.get()
            else:
                path_in = self._input_path.get().strip()
                if not path_in or not Path(path_in).exists():
                    messagebox.showerror("Lỗi", "Vui lòng chọn file ảnh/video hợp lệ.")
                    return
                source = path_in
            self._running   = True
            self._stop_flag = False
            self._run_btn.configure(state="disabled")
            self._stop_btn.configure(state="normal")
            self._placeholder_visible = False
            self._canvas.delete("placeholder")
            self._set_status("🔄 Đang phân loại (.pth)...", WARNING)
            threading.Thread(target=self._pth_infer_thread,
                             args=(source, src), daemon=True).start()
            return

        # ── YOLO model ─────────────────────────────────────────────────────
        if self._model is None:
            messagebox.showwarning("Chưa tải model", "Hãy tải model trước khi chạy.")
            return

        src = self._source_var.get()

        if src == "Webcam":
            source = self._cam_idx_var.get()
        else:
            path = self._input_path.get().strip()
            if not path or not Path(path).exists():
                messagebox.showerror("Lỗi", "Vui lòng chọn file ảnh/video hợp lệ.")
                return
            source = path

        self._running   = True
        self._stop_flag = False
        self._run_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._fps_counter.clear()
        self._placeholder_visible = False
        self._canvas.delete("placeholder")
        self._set_status("🔄 Đang xử lý...", WARNING)

        mode = "image" if src == "Ảnh (Image)" else "stream"
        threading.Thread(
            target=self._inference_thread,
            args=(source, mode),
            daemon=True,
        ).start()

        if mode == "stream":
            self.after(30, self._poll_frame_queue)

    def _inference_thread(self, source, mode: str):
        try:
            cv2       = _import_cv2()
            Image, ImageTk, ImageDraw, ImageFont = _import_pil()
            np        = _import_numpy()

            conf    = self._conf_var.get()
            iou     = self._iou_var.get()
            imgsz   = self._imgsz_var.get()
            device  = self._device_var.get()
            half    = self._half_var.get() and device != "cpu"
            save    = self._save_var.get()
            is_seg  = self._task_var.get() == "Instance Segmentation"

            if mode == "image":
                use_dynamic = self._dynamic_conf_var.get()
                if use_dynamic:
                    self._log(f"[→] Dynamic Conf ON: start={conf:.0%}→min=5% step=5% | iou={iou:.2f} imgsz={imgsz} device={device}", "info")
                    r, final_conf = predict_dynamic_conf(
                        self._model, source,
                        start_conf=conf, min_conf=0.05, step=0.05,
                        iou=iou, imgsz=imgsz, device=device, half=half, save=save,
                    )
                    n_box  = len(r.boxes) if r.boxes is not None else 0
                    n_mask = len(r.masks) if r.masks is not None else 0
                    if final_conf > 0:
                        self._log(f"[✔] Tìm box tại conf={final_conf:.0%} | Boxes: {n_box}  Masks: {n_mask}", "ok")
                    else:
                        self._log(f"[⚠] Không phát hiện ở bất kỳ ngưỡng nào. Boxes: {n_box}  Masks: {n_mask}", "warn")
                    draw_conf = final_conf if final_conf > 0 else conf
                else:
                    self._log(f"[→] Fixed Conf: conf={conf:.0%} iou={iou:.2f} imgsz={imgsz} device={device}", "info")
                    results = self._model.predict(
                        source=source, conf=conf, iou=iou,
                        imgsz=imgsz, device=device, half=half,
                        save=save, verbose=False,
                    )
                    r = results[0]
                    n_box  = len(r.boxes) if r.boxes is not None else 0
                    n_mask = len(r.masks) if r.masks is not None else 0
                    self._log(f"[✔] Fixed conf={conf:.0%} | Boxes: {n_box}  Masks: {n_mask}", "ok")
                    draw_conf = conf
                # Lưu cache cho slider
                self._last_result = r
                self._last_source  = source
                try:
                    annotated = self._draw_result(
                        r, cv2, Image, np, is_seg, draw_conf, self._opacity_var.get())
                    self._log(f"[draw] OK — hiển thị ảnh {annotated.size}", "ok")
                    self.after(0, self._show_image, annotated)
                except Exception:
                    import traceback as _tb
                    self._log(f"[draw ERROR]\n{_tb.format_exc()}", "err")
                    # fallback: dùng result.plot()
                    try:
                        from PIL import Image as _PIL
                        plotted = r.plot() if hasattr(r, 'plot') else r.orig_img
                        ann2 = _PIL.fromarray(plotted[..., ::-1])
                        self._log("[draw fallback] dùng result.plot()", "warn")
                        self.after(0, self._show_image, ann2)
                    except Exception:
                        pass
                self.after(0, self._update_diagnosis, r, draw_conf)
                self.after(0, self._on_inference_done, 0)

            else:  # video / webcam
                cap_src = source if isinstance(source, int) else str(source)
                cap = cv2.VideoCapture(cap_src)
                if not cap.isOpened():
                    raise RuntimeError(f"Không mở được nguồn: {source}")

                while not self._stop_flag:
                    ok, frame_bgr = cap.read()
                    if not ok:
                        break

                    t0 = time.perf_counter()
                    results = self._model.predict(
                        source=frame_bgr, conf=conf, iou=iou,
                        imgsz=imgsz, device=device, half=half,
                        save=False, verbose=False,
                    )
                    dt = time.perf_counter() - t0
                    r  = results[0]
                    annotated = self._draw_result(
                        r, cv2, Image, np, is_seg,
                        conf, self._opacity_var.get())

                    # FPS rolling
                    now = time.perf_counter()
                    self._fps_counter.append(now)
                    self._fps_counter = [t for t in self._fps_counter if now - t <= 1.0]
                    fps = len(self._fps_counter)

                    try:
                        self._frame_queue.put_nowait((annotated, r, fps))
                    except queue.Full:
                        pass

                cap.release()
                self.after(0, self._on_inference_done, 0)

        except Exception as ex:
            import traceback
            tb = traceback.format_exc()
            self._log(f"[\u2717] {tb}", "err")
            self.after(0, self._on_inference_done, -1, tb)

    def _poll_frame_queue(self):
        if not self._running:
            return
        try:
            annotated, r, fps = self._frame_queue.get_nowait()
            self._show_image(annotated)
            conf_thresh = self._conf_var.get()
            self._update_diagnosis(r, conf_thresh)
            n = sum(1 for b in r.boxes if float(b.conf[0]) >= conf_thresh) \
                if r.boxes is not None else 0
            self._fps_lbl.configure(text=f"FPS: {fps}")
            self._detect_count_lbl.configure(text=f"{n} objects detected")
        except queue.Empty:
            pass
        self.after(30, self._poll_frame_queue)

    # ─────────────────────────────────────────────────────────────────────────
    # DRAW RESULT  — vẽ thủ công để hỗ trợ lọc conf + opacity mask
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_result(self, result, cv2, Image, np, is_seg: bool,
                     conf_thresh: float = 0.25, opacity: int = 75):
        """Trả về PIL.Image vẽ bbox + mask, lọc theo conf_thresh & opacity."""
        from PIL import ImageDraw as _D

        # ─ lấy và chuẩn hoá orig_img ─
        orig = result.orig_img
        if orig is None or orig.size == 0:
            blank = np.zeros((480, 640, 3), dtype=np.uint8)
            return Image.fromarray(blank)
        if orig.ndim == 4:
            orig = orig[0]
        if orig.ndim == 3 and orig.shape[0] in (1, 3, 4) and orig.shape[0] < orig.shape[1]:
            orig = np.transpose(orig, (1, 2, 0))     # CHW → HWC
        if orig.dtype != np.uint8:
            mx = orig.max()
            orig = (orig * (255.0 / mx if mx > 1.0 else 255.0)).clip(0, 255).astype(np.uint8)

        img_rgb = cv2.cvtColor(orig, cv2.COLOR_BGR2RGB)
        base    = Image.fromarray(img_rgb).convert("RGBA")
        names  = result.names if hasattr(result, "names") and result.names else {}
        alpha  = int(max(0, min(100, opacity)) / 100.0 * 255)

        def _get_name(cls_id: int) -> str:
            return names.get(cls_id, f"cls{cls_id}")

        # ─ lọc các box đạt ngưỡng ─  lưu cả index và box object để tránh re-index
        valid: list[tuple[int, object]] = []
        if result.boxes is not None:
            for i, box in enumerate(result.boxes):
                if float(box.conf[0]) >= conf_thresh:
                    valid.append((i, box))

        # ─ vẽ mask (polygon) cho seg ─
        if is_seg and result.masks is not None:
            polys = result.masks.xy          # list[(N,2)] toạ độ ảnh gốc
            for i, box in valid:
                if i >= len(polys):
                    continue
                poly = polys[i]
                if len(poly) < 3:
                    continue
                cls_id = int(box.cls[0])
                ch = CLASS_COLORS[cls_id % len(CLASS_COLORS)]
                r_c, g_c, b_c = int(ch[1:3],16), int(ch[3:5],16), int(ch[5:7],16)
                pts = [(float(x), float(y)) for x, y in poly]
                layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
                _D.Draw(layer).polygon(pts, fill=(r_c, g_c, b_c, alpha))
                base = Image.alpha_composite(base, layer)

        # ─ vẽ bbox + label ─
        draw = _D.Draw(base)
        for i, box in valid:
            cls_id = int(box.cls[0])
            conf   = float(box.conf[0])
            lbl    = f"{_get_name(cls_id)}  {conf:.0%}"
            ch     = CLASS_COLORS[cls_id % len(CLASS_COLORS)]
            r_c, g_c, b_c = int(ch[1:3],16), int(ch[3:5],16), int(ch[5:7],16)
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            for th in range(3):
                draw.rectangle([x1-th, y1-th, x2+th, y2+th],
                               outline=(r_c, g_c, b_c, 255))
            tw = len(lbl) * 6 + 8
            draw.rectangle([x1, y1-20, x1+tw, y1], fill=(r_c, g_c, b_c, 210))
            draw.text((x1+4, y1-18), lbl, fill=(255, 255, 255, 255))

        return base.convert("RGB")

    def _draw_cls_result(self, result, cv2, Image):
        """Render kết quả Classification: hiển thị top-3 class trên ảnh gốc."""
        from PIL import ImageDraw as _D
        import numpy as _np

        orig = result.orig_img
        if orig is None:
            orig = _np.zeros((224, 224, 3), dtype=_np.uint8)
        img_rgb = cv2.cvtColor(orig, cv2.COLOR_BGR2RGB)
        base = Image.fromarray(img_rgb).convert("RGBA")
        W, H = base.size

        names = result.names if hasattr(result, "names") and result.names else {}
        probs = result.probs  # Probs object

        if probs is None:
            return base.convert("RGB")

        top5_ids  = probs.top5          # list[int]
        top5_cfs  = probs.top5conf.tolist()  # list[float]

        # Background banner (semi-transparent)
        layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw  = _D.Draw(layer)
        banner_h = min(30 + len(top5_ids[:3]) * 28, H)
        draw.rectangle([0, 0, W, banner_h], fill=(0, 0, 0, 160))
        base = Image.alpha_composite(base, layer)

        draw2 = _D.Draw(base)
        colors = ["#22c55e", "#f59e0b", "#38bdf8"]  # top-1 green, top-2 amber, top-3 sky
        draw2.text((8, 6), "Classification Result", fill=(200, 200, 200, 230))
        for rank, (cls_id, conf) in enumerate(zip(top5_ids[:3], top5_cfs[:3])):
            cls_name = names.get(int(cls_id), str(cls_id))
            pct      = float(conf)
            color_hex = colors[rank]
            r_c = int(color_hex[1:3], 16)
            g_c = int(color_hex[3:5], 16)
            b_c = int(color_hex[5:7], 16)

            y = 26 + rank * 28
            # bar background
            bar_w = int((W - 16) * pct)
            draw2.rectangle([8, y, 8 + bar_w, y + 20], fill=(r_c, g_c, b_c, 90))
            label = f"#{rank+1}  {cls_name}  {pct:.1%}"
            draw2.text((12, y + 2), label, fill=(r_c, g_c, b_c, 255))

        return base.convert("RGB")

    # ─────────────────────────────────────────────────────────────────────────
    # .pth CLASSIFICATION INFERENCE (Tab 1)
    # ─────────────────────────────────────────────────────────────────────────
    def _pth_infer_thread(self, source, src_type: str):
        """Run in-memory PyTorch .pth classification and show on canvas."""
        try:
            import torch
            import torch.nn as nn
            import torch.nn.functional as F
            from torchvision import transforms, models as _tv_models
            Image, _, _, _ = _import_pil()
            cv2 = _import_cv2()

            nc      = self._pth_infer_nc
            arch    = self._pth_infer_arch
            imgsz   = self._imgsz_var.get()
            dev_str = self._device_var.get()
            device  = torch.device(
                "cuda" if dev_str != "cpu" and torch.cuda.is_available() else "cpu")

            # ── Build model ────────────────────────────────────────────────
            if "MobileNet" in arch:
                model = _tv_models.mobilenet_v2(weights=None)
                model.classifier = nn.Sequential(
                    nn.Dropout(p=0.2), nn.Linear(1280, 128),
                    nn.ReLU(inplace=True), nn.Dropout(p=0.2),
                    nn.Linear(128, nc))
            else:
                class _CCNN(nn.Module):
                    def __init__(self, _nc):
                        super().__init__()
                        self.features = nn.Sequential(
                            nn.Conv2d(3,   32, 3, padding=1), nn.BatchNorm2d(32),  nn.ReLU(True), nn.MaxPool2d(2),
                            nn.Conv2d(32,  64, 3, padding=1), nn.BatchNorm2d(64),  nn.ReLU(True), nn.MaxPool2d(2),
                            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(True), nn.MaxPool2d(2),
                            nn.Conv2d(128,256, 3, padding=1), nn.BatchNorm2d(256), nn.ReLU(True), nn.MaxPool2d(2),
                            nn.AdaptiveAvgPool2d((9, 9)),  # ép 9×9 cố định ≈ 10.6M params (JILSA 2022)
                        )
                        flat = 256 * 9 * 9  # = 20,736
                        self.classifier = nn.Sequential(
                            nn.Flatten(), nn.Linear(flat,512), nn.ReLU(True),
                            nn.Dropout(0.5), nn.Linear(512, _nc))
                    def forward(self, x): return self.classifier(self.features(x))
                model = _CCNN(nc)
            model.load_state_dict(self._pth_infer_sd)
            model = model.to(device)
            model.eval()

            tf = transforms.Compose([
                transforms.Resize((imgsz, imgsz)),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            ])
            # Use real class names: from stored list, fallback to generic
            stored = self._pth_infer_class_names
            if stored and len(stored) == nc:
                class_names = stored
            else:
                class_names = [f"Class_{i}" for i in range(nc)]

            def classify_pil(img_pil):
                t = tf(img_pil.convert("RGB")).unsqueeze(0).to(device)
                with torch.no_grad():
                    probs = F.softmax(model(t), dim=1)[0]
                k = min(5, nc)
                vals, idxs = torch.topk(probs, k)
                return [(class_names[i.item()], v.item()) for i, v in zip(idxs, vals)]

            if src_type == "Ảnh (Image)":
                t0 = time.time()
                img = Image.open(source).convert("RGB")
                preds = classify_pil(img)
                elapsed_ms = (time.time() - t0) * 1000
                result_img = self._draw_pth_cls_overlay(img, preds, elapsed_ms)
                top1 = preds[0] if preds else ("?", 0.0)
                self.after(0, self._show_image, result_img)
                self.after(0, self._show_pth_result, preds, elapsed_ms)
                self.after(0, self._fps_lbl.configure,
                           {"text": f"{elapsed_ms:.0f} ms  |  {top1[0]}: {top1[1]:.1%}"})
                self.after(0, self._detect_count_lbl.configure,
                           {"text": f"▶ {top1[0]}  {top1[1]:.1%}"})
                self.after(0, self._on_inference_done, 0)
            else:
                if src_type == "Webcam":
                    cap = cv2.VideoCapture(int(source))
                else:
                    cap = cv2.VideoCapture(source)
                if not cap.isOpened():
                    self.after(0, self._on_inference_done, -1,
                               "Không mở được nguồn video/webcam")
                    return
                try:
                    while not self._stop_flag:
                        ret, frame = cap.read()
                        if not ret:
                            break
                        t0 = time.time()
                        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        img_pil = Image.fromarray(img_rgb)
                        preds = classify_pil(img_pil)
                        elapsed_ms = (time.time() - t0) * 1000
                        result_img = self._draw_pth_cls_overlay(img_pil, preds, elapsed_ms)
                        self._fps_counter.append(time.time())
                        if len(self._fps_counter) > 30:
                            self._fps_counter = self._fps_counter[-30:]
                        fps = (len(self._fps_counter) /
                               max(self._fps_counter[-1] - self._fps_counter[0], 1e-6)
                               if len(self._fps_counter) > 1 else 0.0)
                        self._frame_queue.put(result_img)
                        top1 = preds[0] if preds else ("?", 0.0)
                        self.after(0, self._show_pth_result, preds, elapsed_ms)
                        self.after(0, self._fps_lbl.configure,
                                   {"text": f"FPS: {fps:.1f}  |  {elapsed_ms:.0f}ms"})
                        self.after(0, self._detect_count_lbl.configure,
                                   {"text": f"▶ {top1[0]}  {top1[1]:.1%}"})
                finally:
                    cap.release()
                self.after(0, self._on_inference_done, 0)
        except Exception:
            import traceback
            self.after(0, self._on_inference_done, -1, traceback.format_exc())

    # ─────────────────────────────────────────────────────────────────────────
    # PTH RESULT UI
    # ─────────────────────────────────────────────────────────────────────────
    def _rebuild_pth_bars(self, n: int):
        """Rebuild progress-bar rows for n classes (call when nc changes)."""
        for w in self._pth_bar_frame.winfo_children():
            w.destroy()
        self._pth_bar_rows.clear()
        COLORS = ["#22c55e", "#a78bfa", "#38bdf8", "#f59e0b", "#ef4444",
                  "#34d399", "#fb923c", "#e879f9", "#60a5fa", "#fbbf24"]
        for i in range(n):
            row = tk.Frame(self._pth_bar_frame, bg=BG2)
            row.pack(fill="x", padx=4, pady=1)
            lbl_name = tk.Label(row, text=f"Class {i}", width=18, anchor="w",
                                font=("Segoe UI", 8), bg=BG2, fg=TEXT)
            lbl_name.pack(side="left")
            bar_cv = tk.Canvas(row, bg=BG3, height=16,
                               highlightthickness=0, relief="flat")
            bar_cv.pack(side="left", fill="x", expand=True, padx=(2, 4))
            lbl_pct = tk.Label(row, text="0.0%", width=6, anchor="e",
                               font=("Segoe UI", 8, "bold"),
                               bg=BG2, fg=COLORS[i % len(COLORS)])
            lbl_pct.pack(side="left")
            self._pth_bar_rows.append((lbl_name, bar_cv, lbl_pct, COLORS[i % len(COLORS)]))

    def _show_pth_result(self, preds: list, elapsed_ms: float):
        """Update right-panel diagnosis result for .pth classification. Call on main thread."""
        COLORS = ["#22c55e", "#a78bfa", "#38bdf8", "#f59e0b", "#ef4444",
                  "#34d399", "#fb923c", "#e879f9", "#60a5fa", "#fbbf24"]

        # Show panel if hidden
        if not self._pth_pred_frame.winfo_ismapped():
            self._pth_pred_frame.pack(fill="x", pady=(4, 0),
                                      after=self._cls_wrap)

        nc = self._pth_infer_nc
        class_names = (self._pth_infer_class_names
                       if len(self._pth_infer_class_names) == nc
                       else [f"Class_{i}" for i in range(nc)])

        # Rebuild bars if count changed
        if len(self._pth_bar_rows) != nc:
            self._rebuild_pth_bars(nc)

        # Fill bar names
        for i, (lbl_name, bar_cv, lbl_pct, color) in enumerate(self._pth_bar_rows):
            lbl_name.configure(text=class_names[i] if i < len(class_names) else f"Class_{i}")

        # Build full prob dict (preds may be top-k, not all classes)
        prob_map = {name: 0.0 for name in class_names}
        for cls_name, conf in preds:
            if cls_name in prob_map:
                prob_map[cls_name] = conf

        top1_name = preds[0][0] if preds else "?"
        top1_conf = preds[0][1] if preds else 0.0

        # Update top-1 badge
        rank0_color = COLORS[0]
        self._pth_top1_name.configure(text=top1_name, fg=rank0_color)
        self._pth_top1_conf.configure(
            text=f"Độ tin cậy: {top1_conf:.1%}  ({top1_conf*100:.1f}/100)")
        self._pth_pred_time_lbl.configure(text=f"{elapsed_ms:.0f} ms")

        # Determine top-1 index for icon
        is_healthy = "kh" in top1_name.lower()  # "khỏe mạnh"
        self._pth_top1_icon.configure(
            text="✅" if top1_conf >= 0.8 else ("⚠️" if top1_conf >= 0.5 else "❓"))

        # Update bars
        self._pth_bar_frame.update_idletasks()
        for i, (lbl_name, bar_cv, lbl_pct, color) in enumerate(self._pth_bar_rows):
            name = class_names[i] if i < len(class_names) else f"Class_{i}"
            conf = prob_map.get(name, 0.0)
            bar_cv.delete("all")
            bar_cv.update_idletasks()
            w = bar_cv.winfo_width() or 100
            h = bar_cv.winfo_height() or 16
            bar_px = max(2, int(w * conf))
            rc, gc, bc = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
            # Background
            bar_cv.create_rectangle(0, 0, w, h, fill=BG3, outline="")
            # Filled bar
            alpha_fill = f"#{rc:02x}{gc:02x}{bc:02x}"
            bar_cv.create_rectangle(0, 0, bar_px, h, fill=alpha_fill, outline="")
            # Highlight top-1
            if name == top1_name:
                bar_cv.create_rectangle(0, 0, w, h,
                                        outline=color, width=2)
            lbl_pct.configure(text=f"{conf:.1%}", fg=color)

        # Update class list — highlight predicted class
        cls_items = [w for w in self._cls_inner.winfo_children()
                     if isinstance(w, tk.Label)]
        for i, lbl in enumerate(cls_items):
            name = class_names[i] if i < len(class_names) else ""
            color = COLORS[i % len(COLORS)]
            if name == top1_name:
                lbl.configure(
                    text=f"▶ {name}  {top1_conf:.0%}",
                    font=("Segoe UI", 9, "bold"), fg=rank0_color,
                    bg="#1a2e1a" if rank0_color == "#22c55e" else BG3)
            else:
                lbl.configure(
                    text=f"• {name}",
                    font=("Segoe UI", 8, "bold"), fg=color, bg=BG4)

        # Log to debug log box
        self._log(f"[PTH] {top1_name}  {top1_conf:.1%}  ({elapsed_ms:.0f}ms)", "ok")
        others = ", ".join(f"{n}: {c:.0%}" for n, c in preds[1:3]) if len(preds) > 1 else ""
        if others:
            self._log(f"       ↳ {others}", "info")

    def _draw_pth_cls_overlay(self, img_pil, preds: list, elapsed_ms: float):
        """Draw top-k classification result overlay on PIL image for .pth model."""
        from PIL import ImageDraw as _D, Image as _Img
        base = img_pil.convert("RGBA")
        W, H = base.size
        n = min(len(preds), 5)
        banner_h = min(28 + n * 30, H // 2)
        layer = _Img.new("RGBA", (W, H), (0, 0, 0, 0))
        _D.Draw(layer).rectangle([0, H - banner_h, W, H], fill=(10, 10, 30, 200))
        base = _Img.alpha_composite(base, layer)
        draw = _D.Draw(base)
        colors = ["#22c55e", "#a78bfa", "#38bdf8", "#f59e0b", "#ef4444"]
        draw.text((8, H - banner_h + 4),
                  f"🧠  PyTorch .pth  |  {elapsed_ms:.0f} ms",
                  fill=(180, 180, 180, 230))
        for rank, (cls_name, conf) in enumerate(preds[:5]):
            y = H - banner_h + 24 + rank * 28
            if y + 20 > H:
                break
            ch = colors[rank % len(colors)]
            rc, gc, bc = int(ch[1:3], 16), int(ch[3:5], 16), int(ch[5:7], 16)
            bar_w = max(4, int((W - 16) * conf))
            draw.rectangle([8, y, 8 + bar_w, y + 20], fill=(rc, gc, bc, 90))
            draw.text((12, y + 2),
                      f"#{rank+1}  {cls_name}  {conf:.1%}",
                      fill=(rc, gc, bc, 255))
        return base.convert("RGB")

    def _cmp_slot_name(self, slot: int) -> str:
        alias = self._cmp_alias_var[slot].get().strip() if slot < len(self._cmp_alias_var) else ""
        return alias if alias else f"Model {self._cmp_slot_labels[slot] if slot < len(self._cmp_slot_labels) else slot+1}"

    def _cmp_active_slots(self) -> range:
        return range(self._cmp_enabled_slots)

    def _cmp_enable_slot_c(self):
        pass  # no longer used – models are selected via registry checklist

    # ─────────────────────────────────────────────────────────────────────────
    # UPDATE UI
    # ─────────────────────────────────────────────────────────────────────────
    def _show_image(self, pil_img):
        self._canvas_img.show(pil_img)
        self._last_frame = pil_img

    def _on_inference_done(self, retcode: int, err: str = ""):
        self._running = False
        self._run_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        if retcode == 0:
            self._set_status("✔ Xong!", SUCCESS)
        else:
            self._set_status("✗ Lỗi", DANGER)
            if err:
                # Hiển thị traceback đầy đủ trong dialog (cuộn được)
                dlg = tk.Toplevel(self)
                dlg.title("Lỗi Inference")
                dlg.configure(bg=BG)
                dlg.geometry("680x340")
                from tkinter import scrolledtext as _st2
                tb_box = _st2.ScrolledText(
                    dlg, bg=BG4, fg="#ef4444", relief="flat",
                    font=("Cascadia Code", 8), wrap="word",
                )
                tb_box.pack(fill="both", expand=True, padx=8, pady=8)
                tb_box.insert("end", err)
                tb_box.configure(state="disabled")
                tk.Button(dlg, text="Đóng", command=dlg.destroy,
                          bg=DANGER, fg="white", relief="flat", padx=12, pady=4,
                          cursor="hand2").pack(pady=(0, 8))

    def _stop_inference(self):
        self._stop_flag = True
        self._set_status("⏹ Đang dừng...", WARNING)

    # ─────────────────────────────────────────────────────────────────────────
    # SAVE CURRENT FRAME
    # ─────────────────────────────────────────────────────────────────────────
    def _save_current_frame(self):
        if not hasattr(self, "_last_frame") or self._last_frame is None:
            messagebox.showinfo("Thông báo", "Chưa có frame nào để lưu.")
            return
        path = filedialog.asksaveasfilename(
            title="Lưu ảnh kết quả",
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("All", "*.*")],
            initialdir=str(RUNS_DIR),
        )
        if path:
            self._last_frame.save(path)
            messagebox.showinfo("Đã lưu", f"Ảnh đã lưu tại:\n{path}")

    def _save_and_show_config(self):
        cfg = {
            "model_path" : self._model_path.get(),
            "task"       : self._task_var.get(),
            "device"     : self._device_var.get(),
            "imgsz"      : self._imgsz_var.get(),
            "conf"       : round(self._conf_var.get(), 2),
            "iou"        : round(self._iou_var.get(), 2),
            "opacity_pct": self._opacity_var.get(),
            "half"       : self._half_var.get(),
            "save_result": self._save_var.get(),
        }
        save_tester_config(cfg)

        # Hiện dialog thông tin cấu hình hiện tại
        from tkinter import scrolledtext as _st
        dlg = tk.Toplevel(self)
        dlg.title("⚙ Cấu hình hiện tại")
        dlg.configure(bg=BG)
        dlg.geometry("400x320")
        dlg.resizable(False, False)
        tk.Label(dlg, text="Cấu hình đã lưu vào tester_config.json",
                 font=("Segoe UI", 9), bg=BG, fg=TEXT_DIM).pack(pady=(10, 4))
        txt = _st.ScrolledText(dlg, bg=BG3, fg=TEXT, font=("Cascadia Code", 9),
                               relief="flat", state="normal")
        txt.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        lines = [
            f"  Model      : {cfg['model_path']}",
            f"  Task       : {cfg['task']}",
            f"  Device     : {cfg['device']}",
            f"  Img size   : {cfg['imgsz']}",
            f"  Confidence : {cfg['conf']:.0%}  (slider lọc hiển thị)",
            f"  IOU        : {cfg['iou']:.0%}  (slider lọc hiển thị)",
            f"  Opacity    : {cfg['opacity_pct']}%",
            f"  Half FP16  : {cfg['half']}",
            f"  Lưu kết quả: {cfg['save_result']}",
        ]
        txt.insert("1.0", "\n".join(lines))
        txt.configure(state="disabled")
        tk.Button(dlg, text="Đóng", bg=ACCENT, fg="white", relief="flat",
                  padx=16, cursor="hand2", command=dlg.destroy).pack(pady=(0, 10))

    def _load_saved_config(self):
        cfg = load_tester_config()
        if not cfg:
            return

        self._model_path.set(cfg.get("model_path", self._model_path.get()))
        self._task_var.set(cfg.get("task", self._task_var.get()))
        self._device_var.set(str(cfg.get("device", self._device_var.get())))
        self._imgsz_var.set(cfg.get("imgsz", self._imgsz_var.get()))
        self._conf_var.set(cfg.get("conf", self._conf_var.get()))
        self._iou_var.set(cfg.get("iou", self._iou_var.get()))
        self._opacity_var.set(cfg.get("opacity_pct", self._opacity_var.get()))
        self._half_var.set(cfg.get("half", self._half_var.get()))
        self._save_var.set(cfg.get("save_result", self._save_var.get()))
        if hasattr(self, "_task_cb"):
            self._task_cb.set(self._task_var.get())

    # ─────────────────────────────────────────────────────────────────────────
    # SO SÁNH MODEL — BUILD UI
    # ─────────────────────────────────────────────────────────────────────────
    def _build_comparison_tab(self, parent: tk.Frame):
        """Tab 2: tick models from registry → load into dynamic side-by-side comparison."""

        paned = tk.PanedWindow(parent, orient="horizontal", bg=BG,
                               sashwidth=5, sashrelief="flat")
        paned.pack(fill="both", expand=True)

        # ── LEFT: Registry panel ────────────────────────────────────────────
        left_outer = tk.Frame(paned, bg=BG2, width=240)
        paned.add(left_outer, minsize=180)

        # header
        hdr_l = tk.Frame(left_outer, bg=ACCENT, pady=5)
        hdr_l.pack(fill="x")
        tk.Label(hdr_l, text="📋 Danh sách model",
                 font=("Segoe UI", 9, "bold"), bg=ACCENT, fg="white").pack(side="left", padx=8)
        tk.Button(hdr_l, text="🔄", bg=ACCENT, fg="white", relief="flat",
                  cursor="hand2", font=("Segoe UI", 10),
                  command=self._cmp_refresh_registry).pack(side="right", padx=4)

        # selection count badge
        self._cmp_sel_count_lbl = tk.Label(left_outer, text="Chưa chọn model nào",
                                           font=("Segoe UI", 7), bg=BG3, fg=TEXT_DIM,
                                           pady=3, anchor="center")
        self._cmp_sel_count_lbl.pack(fill="x")

        # scrollable checklist
        list_container = tk.Frame(left_outer, bg=BG2)
        list_container.pack(fill="both", expand=True)
        list_canvas = tk.Canvas(list_container, bg=BG2, highlightthickness=0)
        list_scroll = ttk.Scrollbar(list_container, orient="vertical", command=list_canvas.yview)
        list_canvas.configure(yscrollcommand=list_scroll.set)
        list_scroll.pack(side="right", fill="y")
        list_canvas.pack(side="left", fill="both", expand=True)

        self._cmp_list_inner = tk.Frame(list_canvas, bg=BG2)
        _win = list_canvas.create_window((0, 0), window=self._cmp_list_inner, anchor="nw")

        def _sync(*_):
            list_canvas.configure(scrollregion=list_canvas.bbox("all"))
            list_canvas.itemconfigure(_win, width=list_canvas.winfo_width())
        self._cmp_list_inner.bind("<Configure>", _sync)
        list_canvas.bind("<Configure>", _sync)

        def _mw(e): list_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        list_container.bind("<Enter>", lambda _: list_canvas.bind_all("<MouseWheel>", _mw))
        list_container.bind("<Leave>", lambda _: list_canvas.unbind_all("<MouseWheel>"))

        # bottom buttons
        bottom_l = tk.Frame(left_outer, bg=BG2, pady=4)
        bottom_l.pack(fill="x")
        op_row = tk.Frame(bottom_l, bg=BG2)
        op_row.pack(fill="x", padx=6, pady=(0, 4))
        tk.Button(op_row, text="⬆ Di chuyển lên", bg=BG3, fg=TEXT,
                  relief="flat", cursor="hand2", padx=6, pady=4,
                  font=("Segoe UI", 8),
                  command=lambda: self._cmp_move_selected_in_registry(True)).pack(side="left", fill="x", expand=True, padx=2)
        tk.Button(op_row, text="⬇ Di chuyển xuống", bg=BG3, fg=TEXT,
                  relief="flat", cursor="hand2", padx=6, pady=4,
                  font=("Segoe UI", 8),
                  command=lambda: self._cmp_move_selected_in_registry(False)).pack(side="left", fill="x", expand=True, padx=2)
        tk.Button(op_row, text="🗑 Xóa đã chọn", bg=DANGER, fg="white",
                  relief="flat", cursor="hand2", padx=6, pady=4,
                  font=("Segoe UI", 8),
                  command=self._cmp_delete_selected_in_registry).pack(side="left", fill="x", expand=True, padx=2)
        tk.Button(bottom_l, text="⬆ Tải model đã chọn", bg=ACCENT, fg="white",
                  relief="flat", cursor="hand2", padx=8, pady=5,
                  font=("Segoe UI", 8, "bold"),
                  command=self._cmp_load_selected_from_registry).pack(fill="x", padx=6, pady=2)
        tk.Button(bottom_l, text="➕ Thêm model mới", bg=BG3, fg=SUCCESS,
                  relief="flat", cursor="hand2", padx=8, pady=3,
                  font=("Segoe UI", 8),
                  command=self._cmp_add_model_to_registry).pack(fill="x", padx=6, pady=2)

        # ── RIGHT: Main area with vertical scroll ───────────────────────────
        right_outer = tk.Frame(paned, bg=BG)
        paned.add(right_outer, minsize=600)

        right_canvas = tk.Canvas(right_outer, bg=BG, highlightthickness=0)
        right_scroll = ttk.Scrollbar(right_outer, orient="vertical", command=right_canvas.yview)
        right_canvas.configure(yscrollcommand=right_scroll.set)
        right_scroll.pack(side="right", fill="y")
        right_canvas.pack(side="left", fill="both", expand=True)

        right = tk.Frame(right_canvas, bg=BG)
        _right_win = right_canvas.create_window((0, 0), window=right, anchor="nw")

        def _sync_right(*_):
            right_canvas.configure(scrollregion=right_canvas.bbox("all"))
            right_canvas.itemconfigure(_right_win, width=right_canvas.winfo_width())

        right.bind("<Configure>", _sync_right)
        right_canvas.bind("<Configure>", _sync_right)

        def _right_mw(e):
            right_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        right_outer.bind("<Enter>", lambda _: right_canvas.bind_all("<MouseWheel>", _right_mw))
        right_outer.bind("<Leave>", lambda _: right_canvas.unbind_all("<MouseWheel>"))

        # source & controls bar
        ctrl_bar = tk.Frame(right, bg=BG3, pady=5)
        ctrl_bar.pack(fill="x", padx=6, pady=(6, 0))

        tk.Label(ctrl_bar, text="🎯 Nguồn đầu vào & điều khiển",
                 font=("Segoe UI", 9, "bold"), bg=BG3, fg=WARNING).pack(anchor="w", padx=10, pady=(2, 3))

        params_row = tk.Frame(ctrl_bar, bg=BG3)
        params_row.pack(fill="x", padx=10, pady=(0, 4))

        tk.Label(params_row, text="Nguồn:", bg=BG3, fg=TEXT_DIM,
                 font=("Segoe UI", 8)).pack(side="left")
        self._cmp_src_cb = ttk.Combobox(params_row, textvariable=self._cmp_source_var,
                                         values=INPUT_SOURCES, state="readonly",
                                         width=14, font=("Segoe UI", 8))
        self._cmp_src_cb.pack(side="left", padx=(3, 8))
        self._cmp_src_cb.bind("<<ComboboxSelected>>", lambda _: self._cmp_on_source_changed())

        self._cmp_file_entry = tk.Entry(params_row, textvariable=self._cmp_input_var,
                                        font=("Segoe UI", 8), width=28)
        apply_entry_theme(self._cmp_file_entry)
        self._cmp_file_entry.pack(side="left", ipady=3)
        tk.Button(params_row, text="...", bg=BG2, fg=TEXT_DIM, relief="flat",
                  cursor="hand2", padx=4,
                  command=self._cmp_browse_input).pack(side="left", padx=(2, 10))

        tk.Label(params_row, text="Cam:", bg=BG3, fg=TEXT_DIM,
                 font=("Segoe UI", 8)).pack(side="left")
        self._cmp_cam_spin = tk.Spinbox(params_row, from_=0, to=9,
                                         textvariable=self._cmp_cam_var,
                                         bg=BG2, fg=TEXT, relief="flat", width=3,
                                         font=("Segoe UI", 8))
        self._cmp_cam_spin.pack(side="left", padx=(2, 10))

        tk.Label(params_row, text="Device:", bg=BG3, fg=TEXT_DIM,
                 font=("Segoe UI", 8)).pack(side="left")
        ttk.Combobox(params_row, textvariable=self._cmp_device_var,
                     values=["cpu", "0", "1"], state="readonly", width=5,
                     font=("Segoe UI", 8)).pack(side="left", padx=(2, 8))

        tk.Label(params_row, text="Imgsz:", bg=BG3, fg=TEXT_DIM,
                 font=("Segoe UI", 8)).pack(side="left")
        tk.Spinbox(params_row, from_=320, to=1280, increment=32,
                   textvariable=self._cmp_imgsz_var, bg=BG2, fg=TEXT, relief="flat",
                   width=5, font=("Segoe UI", 8)).pack(side="left", padx=(2, 12))

        self._cmp_start_btn = tk.Button(
            params_row, text="▶ Bắt đầu", bg=SUCCESS, fg="white", relief="flat",
            padx=10, pady=3, cursor="hand2", font=("Segoe UI", 9, "bold"),
            command=self._cmp_start)
        self._cmp_start_btn.pack(side="left", padx=3)
        self._cmp_stop_btn = tk.Button(
            params_row, text="⏹ Dừng", bg=DANGER, fg="white", relief="flat",
            padx=10, pady=3, cursor="hand2", font=("Segoe UI", 9, "bold"),
            state="disabled", command=self._cmp_stop)
        self._cmp_stop_btn.pack(side="left", padx=3)
        self._cmp_record_btn = tk.Button(
            params_row, text="📋 Ghi thông số", bg=INFO, fg="white", relief="flat",
            padx=8, pady=3, cursor="hand2", font=("Segoe UI", 8, "bold"),
            command=self._cmp_record_metrics)
        self._cmp_record_btn.pack(side="left", padx=3)
        tk.Button(params_row, text="🧩 Mô hình bổ sung", bg="#7c3aed", fg="white", relief="flat",
                  padx=8, pady=3, cursor="hand2", font=("Segoe UI", 8, "bold"),
                  command=self._cmp_open_aux_segment_popup).pack(side="left", padx=3)
        tk.Button(params_row, text="📊 Biểu đồ", bg=ACCENT2, fg="white", relief="flat",
                  padx=8, pady=3, cursor="hand2", font=("Segoe UI", 8, "bold"),
                  command=self._cmp_open_advanced_compare).pack(side="left", padx=3)
        tk.Button(params_row, text="💾 Lưu phiên", bg=SUCCESS, fg="white", relief="flat",
                  padx=8, pady=3, cursor="hand2", font=("Segoe UI", 8, "bold"),
                  command=self._cmp_quick_save).pack(side="left", padx=3)
        tk.Button(params_row, text="📤 Xuất báo cáo", bg=BG2, fg=TEXT, relief="flat",
                  padx=8, pady=3, cursor="hand2", font=("Segoe UI", 8),
                  command=self._cmp_save_report).pack(side="left", padx=3)
        tk.Button(params_row, text="🎲 Ảnh ngẫu nhiên", bg=WARNING, fg="white", relief="flat",
                  padx=8, pady=3, cursor="hand2", font=("Segoe UI", 8, "bold"),
                  command=self._cmp_eval_all_slots).pack(side="left", padx=3)

        # canvas area (dynamically rebuilt when models are selected)
        self._cmp_canvas_area = tk.Frame(right, bg=BG)
        self._cmp_canvas_area.pack(fill="both", expand=True, padx=6, pady=4)

        # placeholder
        self._cmp_canvas_placeholder = tk.Label(
            self._cmp_canvas_area,
            text="← Tick model trong danh sách rồi nhấn\n\"⬆ Tải model đã chọn\"",
            font=("Segoe UI", 12), bg=BG, fg=TEXT_DIM, justify="center")
        self._cmp_canvas_placeholder.pack(expand=True)

        # metrics table
        metrics_frame = tk.Frame(right, bg=BG2, pady=4)
        metrics_frame.pack(fill="x", padx=6, pady=(0, 6))
        tk.Label(metrics_frame, text="📊 Bảng so sánh thông số",
                 font=("Segoe UI", 9, "bold"), bg=BG2, fg=ACCENT2).pack(anchor="w", padx=6)
        self._cmp_metrics_tbl = tk.Frame(metrics_frame, bg=BG2)
        self._cmp_metrics_tbl.pack(fill="x", padx=6, pady=2)
        self._cmp_build_metrics_table()

        # load registry and restore general settings
        self._cmp_load_saved_models(silent=True)
        self._cmp_refresh_registry()
        self._cmp_on_source_changed()

    def _cmp_build_metrics_table(self):
        """Vẽ bảng so sánh metrics, gọi lại mỗi khi refresh."""
        for w in self._cmp_metrics_tbl.winfo_children():
            w.destroy()

        active_slots = list(self._cmp_active_slots())
        if not active_slots:
            tk.Label(self._cmp_metrics_tbl, text="Chưa có model nào được tải.",
                     font=("Segoe UI", 8), bg=BG2, fg=TEXT_DIM).pack(anchor="w", padx=6, pady=4)
            return

        headers = ["Thông số"] + [self._cmp_slot_name(slot) for slot in active_slots]
        col_widths = [22] + [24 for _ in active_slots]
        for c, (h, w) in enumerate(zip(headers, col_widths)):
            tk.Label(self._cmp_metrics_tbl, text=h, font=("Segoe UI", 8, "bold"),
                     bg=BG3, fg=ACCENT2, width=w, anchor="center",
                     relief="flat", pady=4).grid(row=0, column=c, padx=1, pady=1, sticky="nsew")

        active_task_kinds = {self._cmp_task_kind(slot) for slot in active_slots}
        rows = [
            ("Tên file", "model_name", "—", None),
            ("Task", "task_type", "—", None),
            ("Layers", "layers", "—", None),
            ("Parameters (M)", "params_m", "—", None),
            ("GFLOPs", "gflops", "—", None),
            ("Kích thước (MB)", "size_mb", "—", None),
            ("FPS trung bình", "avg_fps", "—", None),
            ("Inference (ms)", "avg_ms", "—", None),
            ("Tổng frames", "total_frames", "—", None),
            ("Accuracy", "accuracy", "—", {"classify"}),
            ("Macro F1", "macro_f1", "—", {"classify"}),
            ("Loss validation", "val_loss", "—", {"classify"}),
            ("Top-1 Val", "val_top1", "—", {"classify"}),
            ("Top-5 Val", "val_top5", "—", {"classify"}),
            ("Top-1 Class", "top1_class", "—", {"classify"}),
            ("Top-1 Confidence", "top1_conf", "—", {"classify"}),
            ("Top-3 Classes", "top3", "—", {"classify"}),
            ("mAP50", "val_map50", "—", {"detect", "segment"}),
            ("mAP50-95", "val_map50_95", "—", {"detect", "segment"}),
            ("Tổng objects", "total_dets", "—", {"detect", "segment"}),
        ]
        visible_rows = []
        for label, key, default, visible_for in rows:
            if visible_for is not None and not (active_task_kinds & visible_for):
                continue
            visible_rows.append((label, key, default))

        for r, (label, key, default) in enumerate(visible_rows, start=1):
            tk.Label(self._cmp_metrics_tbl, text=label, font=("Segoe UI", 8),
                     bg=BG2, fg=TEXT_DIM, width=col_widths[0], anchor="w",
                     padx=6).grid(row=r, column=0, padx=1, pady=1, sticky="nsew")
            for idx, slot in enumerate(active_slots, start=1):
                val = self._cmp_metrics[slot].get(key, default)
                color = self._cmp_slot_colors[slot]
                tk.Label(self._cmp_metrics_tbl, text=str(val),
                         font=("Cascadia Code", 8), bg=BG3, fg=color,
                         width=col_widths[idx], anchor="center",
                         relief="flat", pady=3).grid(
                            row=r, column=idx, padx=1, pady=1, sticky="nsew")
        for slot in active_slots:
            self._cmp_render_slot_summary(slot)

    def _cmp_task_kind(self, slot: int) -> str:
        task_text = str(self._cmp_metrics[slot].get("task_type", "")).lower()
        if "segment" in task_text:
            return "segment"
        if "detect" in task_text:
            return "detect"
        if "class" in task_text or "cnn" in task_text or "mobilenet" in task_text:
            return "classify"
        model_type = str(self._cmp_model_type[slot]).lower() if slot < len(self._cmp_model_type) else ""
        return "classify" if model_type == "pth" else "detect"

    def _cmp_set_info(self, slot: int, text: str, fg: str):
        """Safely update info label — no-op when label is None or destroyed."""
        lbl = self._cmp_info_lbl[slot]
        if lbl is None:
            return
        try:
            lbl.configure(text=text, fg=fg)
        except Exception:
            pass

    def _cmp_history_from_results_csv(self, run_dir: Path):
        return cmp_history_from_results_csv(run_dir)

    def _cmp_find_latest_eval_json(self, model_path: str):
        return find_latest_eval_json(model_path, EVAL_BASE_DIR, RUNS_DIR)

    def _cmp_apply_saved_eval_artifacts(self, slot: int):
        path = self._cmp_path_var[slot].get().strip()
        if not path:
            return
        model_type = self._cmp_model_type[slot]
        payload = load_saved_eval_artifacts(
            path,
            model_type,
            runs_dir=RUNS_DIR,
            eval_base_dir=EVAL_BASE_DIR,
            eval_run_dir_finder=self._eval_find_run_dir,
        )
        self._cmp_history_data[slot] = payload["history"]
        self._cmp_eval_summary[slot] = payload["summary"]
        self._cmp_metrics[slot].update(payload["metric_updates"])

    def _cmp_render_slot_summary(self, slot: int):
        frame = self._cmp_summary_frame[slot] if slot < len(self._cmp_summary_frame) else None
        if frame is None:
            return
        for w in frame.winfo_children():
            if w is not self._cmp_summary_chart[slot]:
                w.destroy()

        color = self._cmp_slot_colors[slot % len(self._cmp_slot_colors)]
        tk.Label(frame, text="Tóm tắt nhanh",
                 font=("Segoe UI", 8, "bold"), bg=BG2, fg=color).pack(anchor="w")

        metrics = self._cmp_metrics[slot] if slot < len(self._cmp_metrics) else {}
        summary = self._cmp_eval_summary[slot] if slot < len(self._cmp_eval_summary) else {}
        def _loss_text(value):
            parsed = self._safe_float_or_none(value)
            if parsed is None:
                return "—"
            return f"{parsed:.4f}"
        acc_text = (
            self._fmt_percent_or_na(metrics.get("accuracy"))
            or self._fmt_percent_or_na(summary.get("accuracy"))
            or metrics.get("top1_conf")
            or self._fmt_percent_or_na(metrics.get("val_map50"))
            or "—"
        )
        f1_text = (
            self._fmt_percent_or_na(metrics.get("macro_f1"))
            or self._fmt_percent_or_na(summary.get("macro_f1"))
            or self._fmt_percent_or_na(metrics.get("val_top1"))
            or "—"
        )
        params_text = "—"
        params_m = self._safe_float_or_none(metrics.get("params_m"))
        if params_m is not None:
            params_text = f"{params_m:.2f} M"
        gflops_text = "—"
        gflops_num = self._safe_float_or_none(
            metrics.get("gflops_num") if metrics.get("gflops_num") is not None else metrics.get("gflops")
        )
        if gflops_num is not None:
            gflops_text = f"{gflops_num:.2f}"
        elif metrics.get("gflops"):
            gflops_text = str(metrics.get("gflops"))
        speed_text = (
            f"{metrics.get('avg_fps', '—')} FPS"
            if metrics.get("avg_fps") not in (None, "", "—")
            else (f"{metrics.get('avg_ms', '—')} ms" if metrics.get("avg_ms") not in (None, "", "—") else "—")
        )
        loss_text = _loss_text(summary.get("val_loss"))
        if loss_text == "—":
            loss_text = _loss_text(metrics.get("val_loss"))
        cards = [
            ("Acc", acc_text, SUCCESS),
            ("F1 / Val", f"{f1_text} / {loss_text}", INFO),
            ("Params", params_text, WARNING),
            ("GFLOPs / Speed", f"{gflops_text} / {speed_text}", TEXT),
        ]
        cards_row = tk.Frame(frame, bg=BG2)
        cards_row.pack(fill="x", pady=(6, 0))
        for label, value, fg in cards:
            card = tk.Frame(cards_row, bg=BG3, padx=6, pady=4)
            card.pack(side="left", fill="x", expand=True, padx=2)
            tk.Label(card, text=label, font=("Segoe UI", 7, "bold"),
                     bg=BG3, fg=TEXT_DIM).pack(anchor="w")
            tk.Label(card, text=str(value), font=("Cascadia Code", 8, "bold"),
                     bg=BG3, fg=fg).pack(anchor="w", pady=(3, 0))

        chart = self._cmp_summary_chart[slot]
        chart.pack(fill="x", pady=(6, 0))
        self._cmp_draw_slot_chart(slot)

    def _cmp_draw_slot_chart(self, slot: int):
        chart = self._cmp_summary_chart[slot] if slot < len(self._cmp_summary_chart) else None
        if chart is None:
            return
        metrics = self._cmp_metrics[slot]
        history = self._cmp_history_data[slot] if slot < len(self._cmp_history_data) else []
        values = []
        labels = []

        def _pct(value):
            if isinstance(value, str) and value.endswith("%"):
                try:
                    return float(value.rstrip("%"))
                except Exception:
                    return None
            val = self._safe_float_or_none(value)
            if val is None:
                return None
            return val * 100.0 if val <= 1.0 else val

        def _fmt_chart_value(value, percent=False):
            if value is None:
                return "—"
            if percent:
                return f"{value:.1f}%"
            return f"{value:.4f}" if value < 10 else f"{value:.2f}"

        top1 = _pct(metrics.get("top1_conf_num") if metrics.get("top1_conf_num") is not None else metrics.get("top1_conf"))
        if top1 is not None:
            labels.append("Top1")
            values.append(min(top1, 100.0))
        macro_f1 = _pct(metrics.get("macro_f1"))
        if macro_f1 is not None:
            labels.append("F1")
            values.append(min(macro_f1, 100.0))
        avg_conf = _pct(metrics.get("avg_conf"))
        if avg_conf is not None:
            labels.append("Conf")
            values.append(min(avg_conf, 100.0))
        params_m = self._safe_float_or_none(metrics.get("params_m"))
        if params_m is not None:
            labels.append("Param")
            values.append(min(params_m, 100.0))
        gflops = self._safe_float_or_none(metrics.get("gflops_num") if metrics.get("gflops_num") is not None else metrics.get("gflops"))
        if gflops is not None:
            labels.append("GF")
            values.append(min(gflops, 100.0))
        fps = self._safe_float_or_none(metrics.get("avg_fps"))
        if fps is not None:
            labels.append("FPS")
            values.append(min(fps, 100.0))
        ms = self._safe_float_or_none(metrics.get("avg_ms"))
        if ms is not None and ms > 0:
            labels.append("ms")
            values.append(min(1000.0 / ms, 100.0))

        chart.delete("all")
        w = max(chart.winfo_width(), 260)
        h = max(chart.winfo_height(), 150)

        if history:
            chart.create_rectangle(0, 0, w, h, fill=BG3, outline="")
            plot_left = 14
            plot_right = w - 12
            plot_top = 18
            plot_bottom = h - 24
            chart.create_line(plot_left, plot_bottom, plot_right, plot_bottom, fill=BORDER, width=1)
            chart.create_line(plot_left, plot_top, plot_left, plot_bottom, fill=BORDER, width=1)

            series_specs = [
                ("train_loss", "#F59E0B", False, "Loss huấn luyện"),
                ("val_loss", "#EF4444", False, "Loss validation"),
                ("val_acc", "#10B981", True, "Val Acc"),
            ]
            drawn = 0
            legend_x = plot_left
            steps = max(len(history) - 1, 1)

            for key, color, is_percent, legend in series_specs:
                series = []
                for item in history:
                    raw = self._safe_float_or_none(item.get(key))
                    if raw is None:
                        continue
                    value = raw * 100.0 if is_percent and raw <= 1.0 else raw
                    series.append(value)
                if not series:
                    continue

                s_min = min(series)
                s_max = max(series)
                span = s_max - s_min
                points = []
                for idx, item in enumerate(history):
                    raw = self._safe_float_or_none(item.get(key))
                    if raw is None:
                        continue
                    value = raw * 100.0 if is_percent and raw <= 1.0 else raw
                    x = plot_left + ((plot_right - plot_left) * idx / steps)
                    if span <= 1e-9:
                        y = (plot_top + plot_bottom) / 2
                    else:
                        y = plot_bottom - ((value - s_min) / span) * (plot_bottom - plot_top)
                    points.append((x, y, value))

                if not points:
                    continue
                if len(points) > 1:
                    flat = []
                    for x, y, _v in points:
                        flat.extend((x, y))
                    chart.create_line(*flat, fill=color, width=2, smooth=True)
                for x, y, _v in points:
                    chart.create_oval(x - 2, y - 2, x + 2, y + 2, fill=color, outline="")

                last_x, last_y, last_value = points[-1]
                chart.create_text(
                    min(plot_right - 2, last_x + 24),
                    last_y - 6,
                    text=_fmt_chart_value(last_value, percent=is_percent),
                    fill=color,
                    font=("Cascadia Code", 7, "bold"),
                )
                chart.create_rectangle(legend_x, 4, legend_x + 10, 10, fill=color, outline="")
                chart.create_text(legend_x + 14, 7, text=legend, anchor="w", fill=TEXT_DIM, font=("Segoe UI", 7))
                legend_x += 72
                drawn += 1

            if drawn:
                last_epoch = history[-1].get("epoch") if history else None
                chart.create_text(plot_right, h - 9, text=f"Epoch {last_epoch or len(history)}", anchor="e",
                                  fill=TEXT_DIM, font=("Segoe UI", 7))
                return

        if not values:
            chart.create_text(w // 2, h // 2, text="Chạy 1 ảnh để xem metric nhanh",
                              fill=TEXT_DIM, font=("Segoe UI", 8))
            return

        pad_x = 12
        bar_gap = 10
        bar_w = max(24, int((w - pad_x * 2 - bar_gap * max(len(values) - 1, 0)) / max(len(values), 1)))
        max_v = max(values) or 1.0
        for idx, (label, val) in enumerate(zip(labels, values)):
            x0 = pad_x + idx * (bar_w + bar_gap)
            x1 = x0 + bar_w
            usable_h = h - 28
            y1 = h - 16
            y0 = y1 - (val / max_v) * usable_h
            chart.create_rectangle(x0, y0, x1, y1, fill=self._cmp_slot_colors[slot % len(self._cmp_slot_colors)], outline="")
            chart.create_text((x0 + x1) / 2, y0 - 8, text=f"{val:.0f}", fill=TEXT, font=("Cascadia Code", 7))
            chart.create_text((x0 + x1) / 2, h - 7, text=label, fill=TEXT_DIM, font=("Segoe UI", 7))

    # ─────────────────────────────────────────────────────────────────────────
    # SO SÁNH MODEL — REGISTRY (checklist)
    # ─────────────────────────────────────────────────────────────────────────
    def _cmp_refresh_registry(self):
        """Read thong_so.json and rebuild the checkbox list."""
        import json
        if self._cmp_list_inner is None:
            return
        tracked_paths = set(self._cmp_get_selected_registry_paths())
        for w in self._cmp_list_inner.winfo_children():
            w.destroy()
        self._cmp_registry.clear()
        self._cmp_check_vars.clear()

        data, groups, _top_level = self._cmp_load_registry_data()
        if data is None:
            tk.Label(self._cmp_list_inner,
                     text="(Chưa có danh sách)\nThêm model bên dưới.",
                     font=("Segoe UI", 8), bg=BG2, fg=TEXT_DIM,
                     justify="center").pack(padx=8, pady=8)
            self._cmp_update_sel_label()
            return

        TASK_COLOR = {"detect": "#22c55e", "classify": "#38bdf8", "segment": "#f59e0b"}
        if groups is None:
            groups = []
        for group in groups:
            g_name = group.get("name", "Nhóm")
            g_hdr = tk.Frame(self._cmp_list_inner, bg=BG3)
            g_hdr.pack(fill="x", pady=(6, 0))
            tk.Label(g_hdr, text=f"▸ {g_name}", font=("Segoe UI", 8, "bold"),
                     bg=BG3, fg=ACCENT2, padx=6, pady=3).pack(anchor="w")

            for model in group.get("models", []):
                if not model.get("duong_dan"):
                    continue
                var = tk.BooleanVar(value=model.get("duong_dan", "") in tracked_paths)
                self._cmp_registry.append(model)
                self._cmp_check_vars.append(var)

                row = tk.Frame(self._cmp_list_inner, bg=BG2)
                row.pack(fill="x", padx=4, pady=1)
                tk.Checkbutton(row, variable=var, bg=BG2, fg=TEXT,
                               activebackground=BG2, selectcolor=BG3,
                               relief="flat", cursor="hand2",
                               command=self._cmp_update_sel_label).pack(side="left")
                task = model.get("task", "detect")
                bc = TASK_COLOR.get(task, BG3)
                tk.Label(row, text=task[:3].upper(), font=("Segoe UI", 7, "bold"),
                         bg=bc, fg="white", padx=3, pady=1).pack(side="left", padx=2)
                model_type = model.get("model_type", "")
                if not model_type:
                    model_type = "pth" if str(model.get("duong_dan", "")).endswith(".pth") else "yolo"
                type_col = INFO if model_type == "pth" else SUCCESS
                tk.Label(row, text=model_type.upper(), font=("Segoe UI", 6),
                         bg=BG2, fg=type_col).pack(side="left", padx=(0, 2))
                name = model.get("ten") or Path(model.get("duong_dan", "")).stem
                lbl = tk.Label(row, text=name, font=("Segoe UI", 8),
                               bg=BG2, fg=TEXT, anchor="w",
                               cursor="hand2", wraplength=150)
                lbl.pack(side="left", padx=3, fill="x", expand=True)
                # right-click or double-click → detail popup
                _mi = model  # capture
                lbl.bind("<Double-Button-1>",
                         lambda e, m=_mi: self._cmp_show_model_detail(m))
                lbl.bind("<Button-3>",
                         lambda e, m=_mi: self._cmp_show_model_detail(m))
                # info button
                info_btn = tk.Label(row, text="ℹ", font=("Segoe UI", 9),
                                    bg=BG2, fg=ACCENT2, cursor="hand2", padx=4)
                info_btn.pack(side="right")
                info_btn.bind("<Button-1>",
                              lambda e, m=_mi: self._cmp_show_model_detail(m))
                # star button for best model
                star_var = tk.BooleanVar(value=model.get("star", False))
                star_btn = tk.Label(row, text="*" if star_var.get() else "o",
                                    font=("Segoe UI", 10, "bold"), bg=BG2, fg="#ffd700" if star_var.get() else TEXT_DIM,
                                    cursor="hand2", padx=2)
                star_btn.pack(side="right")
                star_btn.bind("<Button-1>", lambda e, sv=star_var, sb=star_btn, m=model: self._cmp_toggle_star(sv, sb, m))

        if not self._cmp_registry:
            tk.Label(self._cmp_list_inner,
                     text="Không có model hợp lệ\ntrong danh sách.",
                     font=("Segoe UI", 8), bg=BG2, fg=TEXT_DIM,
                     justify="center").pack(padx=8, pady=8)
        self._cmp_update_sel_label()
        self._eval_refresh_registry_models()

    def _cmp_show_model_detail(self, model: dict):
        """Popup hiển thị thông tin chi tiết model + các thao tác nhanh."""
        import json, shutil

        dlg = tk.Toplevel(self)
        dlg.title("Thông tin Model")
        dlg.configure(bg=BG2)
        dlg.resizable(False, False)
        dlg.grab_set()

        path_str = model.get("duong_dan", "")
        p = Path(path_str)

        # ── Banner ──────────────────────────────────────────────────────────
        hdr = tk.Frame(dlg, bg=BG3, padx=14, pady=10)
        hdr.pack(fill="x")
        name = model.get("ten") or p.stem
        tk.Label(hdr, text=f"📦  {name}",
                 font=("Segoe UI", 12, "bold"), bg=BG3, fg=ACCENT2).pack(anchor="w")
        task = model.get("task", "detect")
        mtype = model.get("model_type", "yolo")
        TASK_COLOR = {"detect": "#22c55e", "classify": "#38bdf8", "segment": "#f59e0b"}
        tk.Label(hdr, text=f"{task.upper()}  ·  {mtype.upper()}",
                 font=("Segoe UI", 8), bg=BG3,
                 fg=TASK_COLOR.get(task, TEXT_DIM)).pack(anchor="w")

        # ── Info grid ───────────────────────────────────────────────────────
        info_f = tk.Frame(dlg, bg=BG2, padx=14, pady=8)
        info_f.pack(fill="x")

        def row(label, value, value_fg=TEXT):
            r = tk.Frame(info_f, bg=BG2)
            r.pack(fill="x", pady=2)
            tk.Label(r, text=label, width=16, anchor="w",
                     font=("Segoe UI", 8, "bold"), bg=BG2, fg=TEXT_DIM).pack(side="left")
            tk.Label(r, text=str(value), anchor="w",
                     font=("Segoe UI", 8), bg=BG2, fg=value_fg,
                     wraplength=340).pack(side="left", fill="x", expand=True)

        # File existence status
        exists = p.exists() if path_str else False
        status_txt = "✔ Tồn tại" if exists else "✗ Không tìm thấy"
        status_clr = SUCCESS if exists else DANGER
        row("Trạng thái", status_txt, status_clr)

        # File size
        if exists:
            sz = p.stat().st_size
            sz_str = (f"{sz/1_048_576:.2f} MB" if sz >= 1_048_576
                      else f"{sz/1024:.1f} KB" if sz >= 1024
                      else f"{sz} bytes")
            row("Kích thước", sz_str, INFO)
        row("Loại task", task)
        row("Kiến trúc", mtype)
        if model.get("mo_ta"):
            row("Mô tả", model["mo_ta"])
        if model.get("layers"):
            row("Layers", model["layers"])
        if model.get("parameters"):
            p_val = model["parameters"]
            row("Parameters", f"{int(p_val):,}" if isinstance(p_val, (int, float)) else str(p_val))
        if model.get("gflops"):
            row("GFLOPs", model["gflops"])
        if model.get("duong_dan_dataset"):
            row("Dataset", model["duong_dan_dataset"], TEXT_DIM)

        # ── Path display + Copy ──────────────────────────────────────────────
        path_f = tk.Frame(dlg, bg=BG3, padx=14, pady=6)
        path_f.pack(fill="x")
        tk.Label(path_f, text="Đường dẫn:", font=("Segoe UI", 8, "bold"),
                 bg=BG3, fg=TEXT_DIM).pack(anchor="w")
        path_inner = tk.Frame(path_f, bg=BG3)
        path_inner.pack(fill="x", pady=(2, 0))
        path_entry = tk.Entry(path_inner, font=("Segoe UI", 8), width=50,
                              bg=BG4 if hasattr(self, '_BG4') else "#252538",
                              fg=TEXT, insertbackground=TEXT, relief="flat")
        path_entry.insert(0, path_str)
        path_entry.configure(state="readonly")
        path_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))

        def _copy_path():
            dlg.clipboard_clear()
            dlg.clipboard_append(path_str)
            copy_btn.configure(text="✔ Đã copy!", fg=SUCCESS)
            dlg.after(1500, lambda: copy_btn.configure(text="📋 Copy path", fg=TEXT))
        copy_btn = tk.Button(path_inner, text="📋 Copy path",
                             font=("Segoe UI", 8), bg=BG2, fg=TEXT,
                             relief="flat", cursor="hand2", padx=6, pady=2,
                             command=_copy_path)
        copy_btn.pack(side="left")

        def _open_folder():
            import subprocess as _sp
            folder = p.parent if p.is_file() else p
            if folder.exists():
                _sp.Popen(["explorer", str(folder.resolve())])
        tk.Button(path_inner, text="📂 Mở thư mục",
                  font=("Segoe UI", 8), bg=BG2, fg=TEXT_DIM,
                  relief="flat", cursor="hand2", padx=6, pady=2,
                  command=_open_folder).pack(side="left", padx=(4, 0))

        # ── Action buttons ───────────────────────────────────────────────────
        act_f = tk.Frame(dlg, bg=BG2, padx=14, pady=10)
        act_f.pack(fill="x")
        tk.Label(act_f, text="Thao tác nhanh:",
                 font=("Segoe UI", 8, "bold"), bg=BG2, fg=TEXT_DIM).pack(anchor="w", pady=(0, 6))
        btn_row = tk.Frame(act_f, bg=BG2)
        btn_row.pack(fill="x")

        def _save_json(data):
            save_compare_registry(data)
            self._cmp_refresh_registry()

        def _find_model_in_json():
            data = load_compare_registry()
            if not data:
                return None, None, None
            for gi, g in enumerate(data.get("groups", [])):
                for mi, m in enumerate(g.get("models", [])):
                    if m.get("duong_dan") == path_str or m.get("ten") == name:
                        return data, gi, mi
            return data, None, None

        # ── Rename ──
        def _rename():
            new_name = tk.simpledialog.askstring(
                "Đổi tên", f"Tên hiển thị hiện tại:\n{name}\n\nTên mới:",
                initialvalue=name, parent=dlg)
            if new_name and new_name.strip() and new_name.strip() != name:
                data, gi, mi = _find_model_in_json()
                if gi is not None:
                    data["groups"][gi]["models"][mi]["ten"] = new_name.strip()
                    _save_json(data)
                    dlg.destroy()

        tk.Button(btn_row, text="✏  Đổi tên",
                  font=("Segoe UI", 9), bg=BG3, fg=TEXT,
                  relief="flat", cursor="hand2", padx=10, pady=6,
                  command=_rename).pack(side="left", padx=(0, 4))

        # ── Relocate (di chuyển đường dẫn) ──
        def _relocate():
            new_path = filedialog.askopenfilename(
                title="Chọn file model mới",
                filetypes=[("Model files", "*.pt *.pth *.onnx"), ("All files", "*.*")],
                initialdir=str(p.parent) if p.parent.exists() else str(ROOT_DIR),
                parent=dlg)
            if new_path:
                new_path_fwd = new_path.replace("\\", "/")
                data, gi, mi = _find_model_in_json()
                if gi is not None:
                    data["groups"][gi]["models"][mi]["duong_dan"] = new_path_fwd
                    _save_json(data)
                    dlg.destroy()
                    messagebox.showinfo("✔", f"Đã cập nhật đường dẫn:\n{new_path_fwd}")

        tk.Button(btn_row, text="📁  Đổi đường dẫn",
                  font=("Segoe UI", 9), bg=BG3, fg=TEXT,
                  relief="flat", cursor="hand2", padx=10, pady=6,
                  command=_relocate).pack(side="left", padx=(0, 4))

        # ── Copy file đến thư mục khác ──
        def _copy_file():
            if not p.exists():
                messagebox.showwarning("⚠", "File không tồn tại, không thể copy.", parent=dlg)
                return
            dest_dir = filedialog.askdirectory(
                title="Chọn thư mục đích để copy model", parent=dlg)
            if dest_dir:
                dest_path = Path(dest_dir) / p.name
                try:
                    shutil.copy2(str(p), str(dest_path))
                    messagebox.showinfo("✔ Đã copy", f"Đã copy sang:\n{dest_path}", parent=dlg)
                except Exception as ex:
                    messagebox.showerror("Lỗi", str(ex), parent=dlg)

        tk.Button(btn_row, text="📄  Copy file",
                  font=("Segoe UI", 9), bg=BG3, fg=TEXT,
                  relief="flat", cursor="hand2", padx=10, pady=6,
                  command=_copy_file).pack(side="left", padx=(0, 4))

        # ── Remove from list ──
        def _remove():
            if not messagebox.askyesno("Xóa khỏi danh sách",
                                       f"Xóa '{name}' khỏi danh sách so sánh?\n"
                                       "(File model vẫn còn trên ổ đĩa)",
                                       parent=dlg):
                return
            data, gi, mi = _find_model_in_json()
            if gi is not None:
                data["groups"][gi]["models"].pop(mi)
                _save_json(data)
            dlg.destroy()

        tk.Button(btn_row, text="🗑  Xóa khỏi DS",
                  font=("Segoe UI", 9), bg=DANGER, fg="white",
                  relief="flat", cursor="hand2", padx=10, pady=6,
                  command=_remove).pack(side="left", padx=(0, 4))

        # ── Close ──
        tk.Button(act_f, text="✖  Đóng",
                  font=("Segoe UI", 9), bg=BG3, fg=TEXT_DIM,
                  relief="flat", cursor="hand2", padx=14, pady=6,
                  command=dlg.destroy).pack(anchor="e", pady=(8, 0))

        dlg.update_idletasks()
        # Center on parent
        pw, ph = self.winfo_width(), self.winfo_height()
        px, py = self.winfo_rootx(), self.winfo_rooty()
        dw, dh = dlg.winfo_width(), dlg.winfo_height()
        dlg.geometry(f"+{px + (pw-dw)//2}+{py + (ph-dh)//2}")

    def _cmp_update_sel_label(self):
        n = sum(1 for v in self._cmp_check_vars if v.get())
        if self._cmp_sel_count_lbl is None:
            return
        if n == 0:
            self._cmp_sel_count_lbl.configure(text="Chưa chọn model nào", fg=TEXT_DIM)
        elif n > 6:
            self._cmp_sel_count_lbl.configure(text=f"⚠ Chọn {n} model (tối đa 6)", fg=DANGER)
        else:
            self._cmp_sel_count_lbl.configure(text=f"✔ Đã chọn {n} model", fg=SUCCESS)

    def _cmp_toggle_star(self, star_var, star_btn, model):
        """Toggle star status for best model - allow multiple starred models."""
        import json
        # Load current data
        data, groups, top_level = self._cmp_load_registry_data()
        if not data or not groups:
            return

        # Find the model in groups and toggle its star status
        for group in groups:
            for m in group.get("models", []):
                if m == model:
                    # Toggle star for this model only
                    m["star"] = not m.get("star", False)
                    break

        # Save changes
        self._cmp_save_registry_data(data, groups, top_level)
        # Refresh to update all star buttons
        self._cmp_refresh_registry()

    def _cmp_get_selected_registry_paths(self):
        paths = []
        for i, v in enumerate(self._cmp_check_vars):
            if not v.get():
                continue
            model = self._cmp_registry[i]
            path = str(model.get("duong_dan", "")).replace("\\", "/")
            if path:
                paths.append(path)
            elif model.get("key"):
                paths.append(str(model["key"]))
        return paths

    def _cmp_load_registry_data(self):
        return bll_load_registry_data()

    def _cmp_save_registry_data(self, data, groups, top_level):
        bll_save_registry_data(data, groups, top_level)

    def _cmp_move_selected_in_registry(self, move_up: bool):
        selected = [i for i, v in enumerate(self._cmp_check_vars) if v.get()]
        if not selected:
            messagebox.showwarning("Chưa chọn", "Tick ít nhất 1 model để di chuyển.")
            return

        data, groups, top_level = self._cmp_load_registry_data()
        if data is None or not groups:
            messagebox.showwarning("Chưa có danh sách", "Không tìm thấy model để sắp xếp.")
            return

        changed, groups, flat = move_selected_registry_items(groups, selected, move_up)
        if not flat:
            messagebox.showwarning("Rỗng", "Danh sách model trống.")
            return

        if not changed:
            messagebox.showinfo("Không thay đổi", "Không thể di chuyển các model đã chọn lên/xuống thêm.")
            return

        self._cmp_save_registry_data(data, groups, top_level)
        self._cmp_refresh_registry()

    def _cmp_delete_selected_in_registry(self):
        selected = [i for i, v in enumerate(self._cmp_check_vars) if v.get()]
        if not selected:
            messagebox.showwarning("Chưa chọn", "Tick ít nhất 1 model để xóa.")
            return
        if not messagebox.askyesno("Xác nhận xóa", f"Xóa {len(selected)} model đã chọn khỏi danh sách?"):
            return

        data, groups, top_level = self._cmp_load_registry_data()
        if data is None or not groups:
            messagebox.showwarning("Chưa có danh sách", "Không tìm thấy model để xóa.")
            return

        flat = []
        for gi, group in enumerate(groups):
            for mi, model in enumerate(group.get("models", [])):
                if not model.get("duong_dan"):
                    continue
                flat.append((gi, mi, model))

        remaining = []
        for idx, (gi, mi, model) in enumerate(flat):
            if idx not in selected:
                remaining.append((gi, model))

        grouped = {}
        for gi, model in remaining:
            grouped.setdefault(gi, []).append(model)
        for gi, group in enumerate(groups):
            group["models"] = grouped.get(gi, [])

        self._cmp_save_registry_data(data, groups, top_level)
        self._cmp_refresh_registry()

    def _cmp_load_selected_from_registry(self):
        """Assign checked registry models to slots, rebuild canvas, then load."""
        selected = [(i, self._cmp_registry[i])
                    for i, v in enumerate(self._cmp_check_vars) if v.get()]
        if not selected:
            messagebox.showwarning("Chưa chọn", "Tick ít nhất 1 model để so sánh.")
            return
        if len(selected) > 6:
            messagebox.showwarning("Quá nhiều", "Chọn tối đa 6 model một lúc.")
            return

        n = len(selected)
        task_map = {"detect": "Detection", "segment": "Instance Segmentation",
                    "classify": "Classification"}
        for slot, (_, model) in enumerate(selected):
            self._cmp_model[slot]      = None
            self._cmp_model_type[slot] = "yolo"
            self._cmp_metrics[slot]    = {}
            self._cmp_imgsz_slot[slot] = None
            self._cmp_path_var[slot].set(model.get("duong_dan", ""))
            self._cmp_dataset_var[slot].set(model.get("duong_dan_dataset", ""))
            self._cmp_alias_var[slot].set(model.get("ten") or f"Model {slot+1}")
            self._cmp_task_var[slot].set(
                task_map.get(model.get("task", "detect"), "Detection"))
            self._cmp_pth_class_names[slot] = list(model.get("class_names", []))
            # pre-fill static metrics from registry
            m = self._cmp_metrics[slot]
            if model.get("parameters"):
                m["params_m"] = f"{model['parameters']/1e6:.4f}"
            if model.get("gflops") is not None:
                m["gflops"] = f"{float(model['gflops']):.3f}"
            if model.get("duong_dan"):
                try:
                    sz = Path(model["duong_dan"]).stat().st_size / (1024 * 1024)
                    m["size_mb"] = f"{sz:.2f}"
                    m["model_name"] = Path(model["duong_dan"]).name
                except Exception:
                    pass
            m.update({k: v for k, v in model.get("metrics", {}).items()
                      if not k.startswith("_")})

        self._cmp_enabled_slots = n
        self._cmp_rebuild_canvas_panels()
        for slot in range(n):
            self._cmp_load_model(slot)
        self._cmp_build_metrics_table()

    def _cmp_rebuild_canvas_panels(self):
        """Destroy and recreate canvas panels for current active slots."""
        if self._cmp_canvas_area is None:
            return
        for w in self._cmp_canvas_area.winfo_children():
            w.destroy()
        n = self._cmp_enabled_slots
        if n == 0:
            tk.Label(self._cmp_canvas_area,
                     text="← Tick model trong danh sách rồi nhấn\n\"⬆ Tải model đã chọn\"",
                     font=("Segoe UI", 12), bg=BG, fg=TEXT_DIM,
                     justify="center").pack(expand=True)
            return
        for slot in range(n):
            color = self._cmp_slot_colors[slot % len(self._cmp_slot_colors)]
            panel = tk.Frame(self._cmp_canvas_area, bg=BG3, bd=2, relief="flat")
            panel.pack(side="left", fill="both", expand=True, padx=3)

            hdr_f = tk.Frame(panel, bg=color, pady=3)
            hdr_f.pack(fill="x")

            alias_var = self._cmp_alias_var[slot]
            hdr_lbl = tk.Label(hdr_f, text=alias_var.get() or f"Model {slot+1}",
                               font=("Segoe UI", 9, "bold"), bg=color, fg="white")
            hdr_lbl.pack(side="left", padx=8)
            def _on_alias(*_, l=hdr_lbl, v=alias_var):
                try:
                    l.configure(text=v.get() or "—")
                except Exception:
                    pass
            alias_var.trace_add("write", _on_alias)

            fps_lbl = tk.Label(hdr_f, text="FPS: —", font=("Cascadia Code", 8), bg=color, fg="white")
            fps_lbl.pack(side="right", padx=5)
            ms_lbl  = tk.Label(hdr_f, text="ms: —",  font=("Cascadia Code", 8), bg=color, fg="white")
            ms_lbl.pack(side="right", padx=5)
            det_lbl = tk.Label(hdr_f, text="obj: 0",  font=("Cascadia Code", 8), bg=color, fg="white")
            det_lbl.pack(side="right", padx=5)
            self._cmp_fps_lbl[slot] = fps_lbl
            self._cmp_ms_lbl[slot]  = ms_lbl
            self._cmp_det_lbl[slot] = det_lbl
            self._cmp_info_lbl[slot] = None

            # ── Conf / IOU per-slot (chỉ hiện cho YOLO .pt, không phải .pth CNN) ──
            _is_yolo = self._cmp_model_type[slot] == "yolo"
            if _is_yolo:
                ci_row = tk.Frame(panel, bg=BG3, pady=2)
                ci_row.pack(fill="x", padx=4)
                for _lbl, _var, _default in [
                    ("Conf", self._cmp_conf_slot[slot], 0.50),
                    ("IOU",  self._cmp_iou_slot[slot],  0.45),
                ]:
                    tk.Label(ci_row, text=f"{_lbl}:", bg=BG3, fg=TEXT_DIM,
                             font=("Segoe UI", 7)).pack(side="left", padx=(6, 1))
                    tk.Spinbox(ci_row, from_=0.01, to=1.0, increment=0.05,
                               textvariable=_var, format="%.2f",
                               bg=BG2, fg=TEXT, relief="flat", width=5,
                               font=("Cascadia Code", 7)
                               ).pack(side="left", padx=(0, 4))

            canvas = tk.Canvas(panel, bg=BG4, highlightthickness=0)
            canvas.pack(fill="both", expand=True)
            self._cmp_canvas_img[slot] = _CanvasImage(canvas)

            summary = tk.Frame(panel, bg=BG2, padx=6, pady=6)
            summary.pack(fill="x")
            self._cmp_summary_frame[slot] = summary

            tk.Label(summary, text="Tóm tắt nhanh",
                     font=("Segoe UI", 8, "bold"), bg=BG2, fg=color).pack(anchor="w")
            chart = tk.Canvas(summary, bg=BG3, height=164, highlightthickness=0)
            chart.pack(fill="x", pady=(6, 0))
            self._cmp_summary_chart[slot] = chart
            self._cmp_summary_chart_img[slot] = None
            self._cmp_render_slot_summary(slot)

    def _cmp_add_model_to_registry(self):
        """Simple dialog: add a new model entry to thong_so.json."""
        import json
        dlg = tk.Toplevel(self)
        dlg.title("➕ Thêm model vào danh sách")
        dlg.configure(bg=BG2)
        dlg.resizable(False, False)
        dlg.grab_set()

        fields = {}
        labels_vars = [
            ("Tên hiển thị",   "ten",                tk.StringVar()),
            ("Đường dẫn model", "duong_dan",          tk.StringVar()),
            ("Dataset path",   "duong_dan_dataset",   tk.StringVar()),
        ]
        task_var = tk.StringVar(value="detect")

        tk.Label(dlg, text="Thêm model mới", font=("Segoe UI", 10, "bold"),
                 bg=BG2, fg=ACCENT2).pack(padx=14, pady=(10, 6), anchor="w")
        for (label, key, var) in labels_vars:
            fields[key] = var
            f = tk.Frame(dlg, bg=BG2)
            f.pack(fill="x", padx=14, pady=2)
            tk.Label(f, text=f"{label}:", bg=BG2, fg=TEXT_DIM,
                     font=("Segoe UI", 8), width=16, anchor="w").pack(side="left")
            ent = tk.Entry(f, textvariable=var, font=("Segoe UI", 9), width=36)
            apply_entry_theme(ent)
            ent.pack(side="left", ipady=3)
            if key == "duong_dan":
                def _browse(v=var):
                    p = filedialog.askopenfilename(
                        filetypes=[("Models", "*.pt *.onnx *.pth"), ("All", "*.*")])
                    if p:
                        v.set(p)
                        if not fields["ten"].get():
                            fields["ten"].set(Path(p).stem)
                tk.Button(f, text="...", bg=BG3, fg=TEXT_DIM, relief="flat",
                          padx=4, cursor="hand2", command=_browse).pack(side="left", padx=2)
            elif key == "duong_dan_dataset":
                def _bds(v=var):
                    p = filedialog.askdirectory()
                    if p:
                        v.set(p)
                tk.Button(f, text="📂", bg=BG3, fg=TEXT_DIM, relief="flat",
                          padx=4, cursor="hand2", command=_bds).pack(side="left", padx=2)

        f_task = tk.Frame(dlg, bg=BG2)
        f_task.pack(fill="x", padx=14, pady=2)
        tk.Label(f_task, text="Task:", bg=BG2, fg=TEXT_DIM,
                 font=("Segoe UI", 8), width=16, anchor="w").pack(side="left")
        ttk.Combobox(f_task, textvariable=task_var,
                     values=["detect", "classify", "segment"], state="readonly",
                     width=14, font=("Segoe UI", 8)).pack(side="left")

        def _save():
            path_val = fields["duong_dan"].get().strip()
            if not path_val:
                messagebox.showwarning("Thiếu thông tin", "Cần có đường dẫn model.", parent=dlg)
                return
            entry = {
                "key": f"m_{Path(path_val).stem[:20]}",
                "ten": fields["ten"].get().strip() or Path(path_val).stem,
                "duong_dan": path_val.replace("\\", "/"),
                "duong_dan_dataset": fields["duong_dan_dataset"].get().strip().replace("\\", "/"),
                "task": task_var.get(),
                "mo_ta": "",
                "layers": None, "parameters": None, "gflops": None,
            }
            if not COMPARE_CONFIG_PATH.exists():
                data = {"groups": [{"id": "default", "name": "Danh sách",
                                    "collapsed": False, "models": []}],
                        "cai_dat_chung": {"device": "0", "imgsz": 640,
                                          "conf": 0.5, "iou": 0.45, "half": False}}
            else:
                data = json.loads(COMPARE_CONFIG_PATH.read_text(encoding="utf-8"))
            if not data.get("groups"):
                data["groups"] = [{"id": "default", "name": "Danh sách",
                                   "collapsed": False, "models": []}]
            data["groups"][0].setdefault("models", []).append(entry)
            COMPARE_CONFIG_PATH.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            dlg.destroy()
            self._cmp_refresh_registry()

        btn_row = tk.Frame(dlg, bg=BG2)
        btn_row.pack(pady=10)
        tk.Button(btn_row, text="✔ Lưu", bg=SUCCESS, fg="white", relief="flat",
                  padx=12, pady=4, cursor="hand2", font=("Segoe UI", 9, "bold"),
                  command=_save).pack(side="left", padx=6)
        tk.Button(btn_row, text="✖ Hủy", bg=DANGER, fg="white", relief="flat",
                  padx=12, pady=4, cursor="hand2", font=("Segoe UI", 9),
                  command=dlg.destroy).pack(side="left", padx=6)

    # ─────────────────────────────────────────────────────────────────────────
    # SO SÁNH MODEL — HELPER / BROWSE
    # ─────────────────────────────────────────────────────────────────────────
    def _cmp_browse(self, slot: int):
        path = filedialog.askopenfilename(
            title=f"Chọn {self._cmp_slot_name(slot)}",
            filetypes=[("All models", "*.pt *.onnx *.pth"),
                       ("YOLO weights", "*.pt *.onnx"),
                       ("PyTorch CNN (.pth)", "*.pth"),
                       ("All", "*.*")],
            initialdir=str(ROOT_DIR),
        )
        if path:
            self._cmp_path_var[slot].set(path)

    def _cmp_browse_dataset(self, slot: int):
        choice = messagebox.askquestion(
            "Chọn dataset",
            "Chọn thư mục dataset?\n\nYes: thư mục dataset\nNo: file data.yaml",
            icon="question",
        )
        if choice == "yes":
            path = filedialog.askdirectory(title=f"Chọn dataset cho {self._cmp_slot_name(slot)}",
                                           initialdir=str(ROOT_DIR))
        else:
            path = filedialog.askopenfilename(
                title=f"Chọn data.yaml cho {self._cmp_slot_name(slot)}",
                filetypes=[("YAML", "*.yaml *.yml"), ("All files", "*.*")],
                initialdir=str(ROOT_DIR),
            )
        if path:
            self._cmp_dataset_var[slot].set(path.replace("\\", "/"))

    def _cmp_browse_input(self):
        src = self._cmp_source_var.get()
        if src == "Video":
            path = filedialog.askopenfilename(
                title="Chọn video", filetypes=[("Video", "*.mp4 *.avi *.mov *.mkv"), ("All", "*.*")])
        else:
            path = filedialog.askopenfilename(
                title="Chọn ảnh", filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp"), ("All", "*.*")])
        if path:
            self._cmp_input_var.set(path)

    def _cmp_on_source_changed(self):
        src = self._cmp_source_var.get()
        is_file = src in ("Ảnh (Image)", "Video")
        is_cam  = src == "Webcam"
        self._cmp_file_entry.configure(state="normal" if is_file else "disabled")
        self._cmp_cam_spin.configure(state="normal" if is_cam else "disabled")

    @staticmethod
    def _cmp_task_key(task_label: str) -> str:
        return {
            "Detection": "detect",
            "Instance Segmentation": "segment",
            "Classification": "classify",
        }.get(task_label, "detect")

    def _cmp_collect_saved_models(self):
        models = []
        for slot in self._cmp_active_slots():
            path = self._cmp_path_var[slot].get().strip().replace("\\", "/")
            alias = self._cmp_slot_name(slot)
            model_type = "pth" if Path(path).suffix.lower() == ".pth" else "yolo"
            entry = {
                "key": f"model_{self._cmp_slot_labels[slot].lower()}",
                "ten": alias,
                "duong_dan": path,
                "duong_dan_dataset": self._cmp_dataset_var[slot].get().strip().replace("\\", "/"),
                "task": self._cmp_task_key(self._cmp_task_var[slot].get()),
                "mo_ta": f"Slot {self._cmp_slot_labels[slot]} trong tab so sánh",
                "layers": self._cmp_metrics[slot].get("layers_raw"),
                "parameters": self._cmp_metrics[slot].get("parameters"),
                "gflops": self._cmp_metrics[slot].get("gflops_num"),
                "model_type": model_type,
            }
            metrics = {
                k: v for k, v in self._cmp_metrics[slot].items()
                if not k.startswith("_")
            }
            if metrics:
                entry["metrics"] = metrics
            class_names = self._cmp_pth_class_names[slot]
            if class_names:
                entry["class_names"] = class_names
            models.append(entry)

        general = {
            "device": self._cmp_device_var.get(),
            "imgsz": self._cmp_imgsz_var.get(),
            "conf": round(self._cmp_conf_var.get(), 3),
            "iou": round(self._cmp_iou_var.get(), 3),
            "half": False,
        }
        payload = {
            "groups": [{
                "id": "cmp_models",
                "name": "So sánh model",
                "collapsed": False,
                "models": models,
            }],
            "cai_dat_chung": general,
        }
        return payload, models, general

    def _cmp_save_models(self):
        import json

        payload, models, _general = self._cmp_collect_saved_models()
        try:
            COMPARE_CONFIG_PATH.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as ex:
            messagebox.showerror("Lỗi lưu file", f"Không thể ghi vào:\n{COMPARE_CONFIG_PATH}\n\n{ex}")
            return

        missing = [m["duong_dan"] for m in models if m["duong_dan"] and not Path(m["duong_dan"]).exists()]
        msg = f"Đã lưu {len(models)} model vào:\n{COMPARE_CONFIG_PATH}"
        if missing:
            msg += f"\n\nCó {len(missing)} đường dẫn chưa tồn tại."
        messagebox.showinfo("Đã lưu", msg)

    def _cmp_load_saved_models(self, silent: bool = False):
        """Restore only general settings (device/imgsz/conf/iou) from thong_so.json.
        Slot population is now handled by _cmp_load_selected_from_registry."""
        import json

        if not COMPARE_CONFIG_PATH.exists():
            return
        try:
            data = json.loads(COMPARE_CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            if not silent:
                messagebox.showwarning("JSON lỗi", f"Không đọc được:\n{COMPARE_CONFIG_PATH}")
            return

        if isinstance(data, dict):
            general = data.get("cai_dat_chung", {})
            if "device" in general:
                self._cmp_device_var.set(str(general["device"]))
            if "imgsz" in general:
                self._cmp_imgsz_var.set(general["imgsz"])
            if "conf" in general:
                self._cmp_conf_var.set(general["conf"])
            if "iou" in general:
                self._cmp_iou_var.set(general["iou"])

    def _cmp_show_json_preview(self):
        import json
        from tkinter import scrolledtext

        payload, _models, _general = self._cmp_collect_saved_models()
        win = tk.Toplevel(self)
        win.title("Preview — thong_so.json")
        win.geometry("700x560")
        win.configure(bg=BG)
        tk.Label(win, text="📋 Nội dung sẽ lưu vào thong_so.json",
                 font=("Segoe UI", 10, "bold"), bg=BG, fg=ACCENT2).pack(
                 padx=14, pady=(12, 4), anchor="w")
        txt = scrolledtext.ScrolledText(win, font=("Cascadia Code", 9), relief="flat")
        apply_textbox_theme(txt, dark=True)
        txt.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        txt.insert("end", json.dumps(payload, ensure_ascii=False, indent=2))
        txt.configure(state="disabled")

    def _cmp_show_ckpt_config(self, slot: int):
        path = self._cmp_path_var[slot].get().strip()
        if not path:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn model trước.")
            return
        if not Path(path).is_file():
            messagebox.showerror("Không tìm thấy", f"File không tồn tại:\n{path}")
            return
        self._cmp_set_info(slot, "⏳ Đang đọc cấu hình checkpoint...", WARNING)
        threading.Thread(
            target=self._cmp_read_ckpt,
            args=(slot, path, self._cmp_task_key(self._cmp_task_var[slot].get()), self._cmp_dataset_var[slot].get().strip()),
            daemon=True,
        ).start()

    def _cmp_read_ckpt(self, slot: int, path: str, task: str, dataset_path: str):
        try:
            import torch

            if path.lower().endswith(".pth"):
                try:
                    raw = torch.load(path, map_location="cpu", weights_only=True)
                except Exception:
                    raw = torch.load(path, map_location="cpu", weights_only=False)
                saved_names = []
                state_dict = raw.get("model_weights") if isinstance(raw, dict) and "model_weights" in raw else raw
                if isinstance(raw, dict):
                    saved_names = list(raw.get("class_names", []))
                params = sum(v.numel() for v in state_dict.values()
                             if hasattr(v, "numel") and callable(v.numel))
                is_mobilenet = any("features.0.0.weight" in k for k in state_dict.keys())
                arch = "MobileNetV2 (PLOS ONE 2024)" if is_mobilenet else "CustomCNN (JILSA 2022)"
                nc = 0
                for key in ("classifier.4.weight", "classifier.1.weight"):
                    if key in state_dict:
                        nc = state_dict[key].shape[0]
                        break
                sections = {
                    "🏗 Kiến trúc": {
                        "Architecture": arch,
                        "Parameters": f"{params:,} ({params / 1e6:.2f} M)",
                        "Num Classes": nc or "?",
                        "Input Size": "224 x 224",
                        "Class Names": ", ".join(saved_names) if saved_names else "(chưa có trong file)",
                    },
                    "📦 State Dict Keys": {
                        k: str(tuple(v.shape)) for k, v in state_dict.items() if hasattr(v, "shape")
                    },
                }
                self.after(0, self._cmp_open_ckpt_window, slot, path, sections, None)
                return

            from ultralytics import YOLO
            ckpt = torch.load(path, map_location="cpu", weights_only=False)
            sections = {}
            train_args = ckpt.get("train_args") or ckpt.get("args")
            data_yaml = dataset_path
            if train_args is not None:
                if hasattr(train_args, "__dict__"):
                    train_args = vars(train_args)
                sections["⚙ Train Args"] = train_args
                if isinstance(train_args, dict) and not data_yaml:
                    data_yaml = train_args.get("data")

            names = None
            for key in ("names", "model"):
                obj = ckpt.get(key)
                if obj is None:
                    continue
                if isinstance(obj, dict) and "names" in obj:
                    names = obj["names"]
                    break
                if hasattr(obj, "names"):
                    names = obj.names
                    break
            if names is not None:
                sections["🏷 Class Names"] = names

            meta = {}
            for key in ("epoch", "best_fitness", "date"):
                if ckpt.get(key) is not None:
                    meta[key] = ckpt.get(key)
            if meta:
                sections["📅 Checkpoint"] = meta

            model = YOLO(path, task=task)
            info = model.info(verbose=False)
            arch = {}
            if isinstance(info, (list, tuple)) and len(info) >= 4:
                arch["layers"] = int(info[0])
                arch["parameters"] = f"{int(info[1]):,} ({int(info[1]) / 1e6:.2f} M)"
                arch["GFLOPs"] = f"{float(info[3]):.3f}"
            if arch:
                sections["📐 Kiến trúc Model"] = arch

            if data_yaml and Path(str(data_yaml)).exists():
                try:
                    metrics = model.val(
                        data=str(data_yaml),
                        imgsz=self._cmp_imgsz_var.get(),
                        device=self._cmp_device_var.get(),
                        half=False,
                        verbose=False,
                    )
                    val_info = {}
                    if task == "segment":
                        val_info["mAP50-95 (Mask)"] = f"{metrics.seg.map:.4f}"
                        val_info["mAP50 (Mask)"] = f"{metrics.seg.map50:.4f}"
                        val_info["mAP50-95 (Box)"] = f"{metrics.box.map:.4f}"
                        val_info["mAP50 (Box)"] = f"{metrics.box.map50:.4f}"
                    elif task == "detect":
                        val_info["mAP50-95"] = f"{metrics.box.map:.4f}"
                        val_info["mAP50"] = f"{metrics.box.map50:.4f}"
                    elif task == "classify":
                        val_info["top1"] = f"{metrics.top1:.4f}"
                        val_info["top5"] = f"{metrics.top5:.4f}"
                    sections["📊 Validation"] = val_info
                except Exception as ex:
                    sections["📊 Validation"] = {"lỗi": str(ex)[:300]}
            else:
                sections["📊 Validation"] = {"Chú ý": "Chưa có dataset/data.yaml hợp lệ để chạy model.val()."}

            self.after(0, self._cmp_open_ckpt_window, slot, path, sections, None)
        except Exception as ex:
            self.after(0, self._cmp_open_ckpt_window, slot, path, {}, str(ex))

    def _cmp_open_ckpt_window(self, slot: int, path: str, sections: dict, error: str | None):
        from tkinter import scrolledtext

        win = tk.Toplevel(self)
        win.title(f"Cấu hình — {Path(path).name}")
        win.geometry("760x600")
        win.configure(bg=BG)
        tk.Label(win, text=f"🛠 Cấu hình model: {Path(path).name}",
                 font=("Segoe UI", 11, "bold"), bg=BG, fg=ACCENT2).pack(
                 padx=16, pady=(12, 4), anchor="w")
        tk.Label(win, text=path, font=("Segoe UI", 8), bg=BG, fg=TEXT_DIM).pack(
                 padx=16, anchor="w")
        txt = scrolledtext.ScrolledText(win, font=("Cascadia Code", 9), relief="flat", wrap="word")
        apply_textbox_theme(txt, dark=True)
        txt.pack(fill="both", expand=True, padx=16, pady=(8, 4))
        if error:
            txt.insert("end", f"❌ Lỗi khi đọc file:\n{error}\n")
        elif not sections:
            txt.insert("end", "⚠ Không tìm thấy thông tin cấu hình trong file này.\n")
        else:
            for title, data in sections.items():
                txt.insert("end", f"{'-' * 60}\n{title}\n{'-' * 60}\n")
                if isinstance(data, dict):
                    for key, value in data.items():
                        txt.insert("end", f"  {str(key):<30} {value}\n")
                else:
                    txt.insert("end", f"  {data}\n")
                txt.insert("end", "\n")
        txt.configure(state="disabled")

        def _copy():
            self.clipboard_clear()
            self.clipboard_append(txt.get("1.0", "end"))
            self._cmp_set_info(slot, "📋 Đã sao chép cấu hình model", INFO)

        bf = tk.Frame(win, bg=BG, pady=8)
        bf.pack(fill="x")
        tk.Button(bf, text="📋 Sao chép tất cả", font=("Segoe UI", 9),
                  bg=BG3, fg=TEXT, relief="flat", cursor="hand2", padx=12, pady=4,
                  command=_copy).pack(side="left", padx=16)
        tk.Button(bf, text="Đóng", font=("Segoe UI", 9),
                  bg=BG3, fg=TEXT_DIM, relief="flat", cursor="hand2", padx=12, pady=4,
                  command=win.destroy).pack(side="right", padx=16)

    def _cmp_eval_model(self, slot: int):
        path = self._cmp_path_var[slot].get().strip()
        if not path:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn model trước.")
            return
        if not Path(path).is_file():
            messagebox.showerror("Không tìm thấy", f"File không tồn tại:\n{path}")
            return
        self._cmp_set_info(slot, "⏳ Đang đánh giá model...", WARNING)
        threading.Thread(
            target=self._cmp_run_model_info,
            args=(slot, path, self._cmp_task_key(self._cmp_task_var[slot].get()), self._cmp_dataset_var[slot].get().strip()),
            daemon=True,
        ).start()

    def _cmp_eval_all_slots(self):
        """Chọn ngẫu nhiên 1 ảnh ngoài dataset rồi chạy so sánh nhanh trên ảnh đó."""
        import random

        active = list(self._cmp_active_slots())
        if not active:
            messagebox.showwarning("Chưa tải model", "Tải model trước khi so sánh.")
            return
        folder = filedialog.askdirectory(
            title="Chọn thư mục ảnh ngoài dataset để lấy ngẫu nhiên 1 ảnh",
            initialdir=str(ROOT_DIR),
        )
        if not folder:
            return
        img_exts = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
        candidates = [p for p in Path(folder).rglob("*") if p.is_file() and p.suffix.lower() in img_exts]
        if not candidates:
            messagebox.showwarning("Không có ảnh", f"Không tìm thấy ảnh hợp lệ trong:\n{folder}")
            return
        chosen = random.choice(candidates)
        self._cmp_source_var.set("Ảnh (Image)")
        self._cmp_on_source_changed()
        self._cmp_input_var.set(str(chosen))
        for slot in active:
            self._cmp_set_info(slot, f"🎲 Ảnh ngẫu nhiên: {chosen.name}", INFO)
        self._cmp_start()

    def _cmp_run_model_info(self, slot: int, path: str, task: str, dataset_path: str):
        try:
            if path.lower().endswith(".pth"):
                import torch as _t
                import torch.nn as _nn

                try:
                    raw = _t.load(path, map_location="cpu", weights_only=True)
                except Exception:
                    raw = _t.load(path, map_location="cpu", weights_only=False)
                saved_names = []
                if isinstance(raw, dict) and "model_weights" in raw:
                    saved_names = list(raw.get("class_names", []))
                    state_dict = raw["model_weights"]
                else:
                    state_dict = raw

                params = sum(v.numel() for v in state_dict.values()
                             if hasattr(v, "numel") and callable(v.numel))
                is_mobilenet = any("features.0.0.weight" in k for k in state_dict.keys())
                arch = "MobileNetV2 (PLOS ONE 2024)" if is_mobilenet else "CustomCNN (JILSA 2022)"
                nc = 0
                for key in ("classifier.4.weight", "classifier.1.weight"):
                    if key in state_dict:
                        nc = state_dict[key].shape[0]
                        break
                gflops = None
                try:
                    from torchvision import models as _tv_models
                    if is_mobilenet:
                        mdl = _tv_models.mobilenet_v2(weights=None)
                        mdl.classifier = _nn.Sequential(
                            _nn.Dropout(0.2), _nn.Linear(1280, 128),
                            _nn.ReLU(True), _nn.Dropout(0.2), _nn.Linear(128, max(nc, 2)),
                        )
                    else:
                        class _CustomCNN(_nn.Module):
                            def __init__(self, out_nc):
                                super().__init__()
                                self.features = _nn.Sequential(
                                    _nn.Conv2d(3, 32, 3, padding=1), _nn.BatchNorm2d(32), _nn.ReLU(True), _nn.MaxPool2d(2),
                                    _nn.Conv2d(32, 64, 3, padding=1), _nn.BatchNorm2d(64), _nn.ReLU(True), _nn.MaxPool2d(2),
                                    _nn.Conv2d(64, 128, 3, padding=1), _nn.BatchNorm2d(128), _nn.ReLU(True), _nn.MaxPool2d(2),
                                    _nn.Conv2d(128, 256, 3, padding=1), _nn.BatchNorm2d(256), _nn.ReLU(True), _nn.MaxPool2d(2),
                                    _nn.AdaptiveAvgPool2d((9, 9)),
                                )
                                self.classifier = _nn.Sequential(
                                    _nn.Flatten(), _nn.Linear(256 * 9 * 9, 512),
                                    _nn.ReLU(True), _nn.Dropout(0.5), _nn.Linear(512, out_nc),
                                )
                            def forward(self, x):
                                return self.classifier(self.features(x))

                        mdl = _CustomCNN(max(nc, 2))
                    mdl.load_state_dict(state_dict, strict=False)
                    mdl.eval()
                    dummy = _t.zeros(1, 3, 224, 224)
                    try:
                        from torch.utils.flop_counter import FlopCounterMode
                        with FlopCounterMode(mdl, display=False) as flop_mode:
                            mdl(dummy)
                        gflops = flop_mode.get_total_flops() / 1e9
                    except Exception:
                        try:
                            from thop import profile as _tpf
                            macs, _ = _tpf(mdl, inputs=(dummy,), verbose=False)
                            gflops = macs * 2 / 1e9
                        except Exception:
                            gflops = None
                except Exception:
                    gflops = None

                size_mb = Path(path).stat().st_size / (1024 * 1024)
                payload = {
                    "layers_raw": None,
                    "layers": "—",
                    "parameters": params,
                    "params_m": f"{params / 1e6:.4f}",
                    "gflops_num": gflops,
                    "gflops": f"{gflops:.3f}" if gflops is not None else "N/A (.pth)",
                    "size_mb_num": size_mb,
                    "size_mb": f"{size_mb:.2f}",
                    "model_name": Path(path).name,
                    "task_type": f"CNN ({arch})",
                    "summary": (
                        f"🧠 {Path(path).name}\n"
                        f"Arch: {arch} | Params: {params / 1e6:.2f} M | GFLOPs: "
                        f"{f'{gflops:.3f}' if gflops is not None else 'N/A'}\n"
                        f"Classes: {', '.join(saved_names) if saved_names else (str(nc) + ' classes' if nc else 'không rõ')}\n"
                        "Đây là file .pth thuần PyTorch, không chạy model.val() tự động."
                    ),
                    "color": INFO,
                }
                if saved_names:
                    payload["class_names"] = saved_names
                self.after(0, self._cmp_on_eval_done, slot, payload, None)
                return

            from ultralytics import YOLO
            import contextlib

            model = YOLO(path, task=task)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                info = model.info(verbose=True)
            layers = params = gflops = None
            if isinstance(info, (list, tuple)) and len(info) >= 4:
                layers = int(info[0])
                params = int(info[1])
                gflops = float(info[3])
            else:
                for line in buf.getvalue().splitlines():
                    if "layers" in line.lower() and "parameters" in line.lower():
                        import re
                        nums = [n.replace(",", "") for n in re.findall(r"[\d,]+\.?\d*", line)]
                        if len(nums) >= 3:
                            try:
                                layers = int(nums[0])
                                params = int(nums[1])
                                gflops = float(nums[-1])
                            except ValueError:
                                pass
                        break

            size_mb = Path(path).stat().st_size / (1024 * 1024)
            payload = {
                "layers_raw": layers,
                "layers": layers if layers is not None else "—",
                "parameters": params,
                "params_m": f"{params / 1e6:.4f}" if params is not None else "N/A",
                "gflops_num": gflops,
                "gflops": f"{gflops:.3f}" if gflops is not None else "N/A",
                "size_mb_num": size_mb,
                "size_mb": f"{size_mb:.2f}",
                "model_name": Path(path).name,
                "task_type": task,
                "color": SUCCESS,
            }

            summary_lines = [
                f"✔ {Path(path).name}",
                f"Layers: {layers if layers is not None else '—'} | Params: {payload['params_m']} M | GFLOPs: {payload['gflops']}",
                f"Size: {payload['size_mb']} MB",
            ]

            dataset = dataset_path
            if not dataset:
                try:
                    import torch
                    ckpt = torch.load(path, map_location="cpu", weights_only=False)
                    train_args = ckpt.get("train_args") or ckpt.get("args")
                    if hasattr(train_args, "__dict__"):
                        train_args = vars(train_args)
                    if isinstance(train_args, dict):
                        dataset = str(train_args.get("data") or "")
                except Exception:
                    dataset = ""

            if dataset and Path(dataset).exists():
                metrics = model.val(
                    data=dataset,
                    imgsz=self._cmp_imgsz_var.get(),
                    device=self._cmp_device_var.get(),
                    half=False,
                    verbose=False,
                )
                if task == "segment":
                    payload["val_map50_95"] = f"{metrics.seg.map:.4f}"
                    payload["val_map50"] = f"{metrics.seg.map50:.4f}"
                    payload["box_map50_95"] = f"{metrics.box.map:.4f}"
                    payload["box_map50"] = f"{metrics.box.map50:.4f}"
                    summary_lines.append(
                        f"Mask mAP50: {payload['val_map50']} | Mask mAP50-95: {payload['val_map50_95']}"
                    )
                elif task == "detect":
                    payload["val_map50_95"] = f"{metrics.box.map:.4f}"
                    payload["val_map50"] = f"{metrics.box.map50:.4f}"
                    summary_lines.append(
                        f"mAP50: {payload['val_map50']} | mAP50-95: {payload['val_map50_95']}"
                    )
                elif task == "classify":
                    payload["val_top1"] = f"{metrics.top1:.4f}"
                    payload["val_top5"] = f"{metrics.top5:.4f}"
                    summary_lines.append(
                        f"Top1: {payload['val_top1']} | Top5: {payload['val_top5']}"
                    )
            else:
                summary_lines.append("Chưa có dataset hợp lệ, chỉ đọc model.info().")

            payload["summary"] = "\n".join(summary_lines)
            self.after(0, self._cmp_on_eval_done, slot, payload, None)
        except Exception as ex:
            self.after(0, self._cmp_on_eval_done, slot, {}, str(ex))

    def _cmp_on_eval_done(self, slot: int, payload: dict, error: str | None):
        if error:
            self._cmp_set_info(slot, f"✗ {error[:180]}", DANGER)
            self._cmp_render_slot_summary(slot)
            return
        if payload.get("class_names"):
            self._cmp_pth_class_names[slot] = list(payload["class_names"])
        self._cmp_metrics[slot].update(payload)
        self._cmp_set_info(slot,
            payload.get("summary", "✔ Đánh giá xong."),
            payload.get("color", SUCCESS))
        self._cmp_build_metrics_table()
        self._cmp_render_slot_summary(slot)

    def _cmp_gather_advanced_models(self):
        models = []
        for slot in self._cmp_active_slots():
            path = self._cmp_path_var[slot].get().strip()
            alias = self._cmp_slot_name(slot)
            if not alias and not path:
                continue
            metrics = self._cmp_metrics[slot]
            size_mb = metrics.get("size_mb_num")
            if size_mb is None and path and Path(path).exists():
                try:
                    size_mb = Path(path).stat().st_size / (1024 * 1024)
                except Exception:
                    size_mb = 0.0
            models.append({
                "slot": self._cmp_slot_labels[slot],
                "name": alias or Path(path).name or f"Model {self._cmp_slot_labels[slot]}",
                "group": "So sánh",
                "task": self._cmp_task_key(self._cmp_task_var[slot].get()),
                "path": path,
                "size_mb": float(size_mb or 0),
                "stats": {
                    "layers": metrics.get("layers_raw"),
                    "parameters": metrics.get("parameters"),
                    "gflops": metrics.get("gflops_num"),
                },
            })
        return models

    def _cmp_open_advanced_compare(self):
        from tkinter import scrolledtext

        all_models = [m for m in self._cmp_gather_advanced_models() if m.get("name") or m.get("path")]
        if not all_models:
            messagebox.showinfo("Thông báo", "Chưa có model nào trong tab so sánh.")
            return

        win = tk.Toplevel(self)
        win.title("So Sánh Model — Biểu đồ nâng cao")
        win.geometry("1220x760")
        win.configure(bg=BG)

        top = tk.Frame(win, bg=BG2, pady=10)
        top.pack(fill="x")
        tk.Label(top, text="📊 So sánh model nâng cao",
                 font=("Segoe UI", 13, "bold"), bg=BG2, fg=ACCENT2).pack(side="left", padx=16)
        status_lbl = tk.Label(top, text="", font=("Segoe UI", 9), bg=BG2, fg=TEXT_DIM)
        status_lbl.pack(side="right", padx=16)

        left = tk.Frame(win, bg=BG2, width=260)
        left.pack(side="left", fill="y", padx=(10, 6), pady=(8, 10))
        right = tk.Frame(win, bg=BG, bd=0)
        right.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=(8, 10))

        tk.Label(left, text="Model tham gia", font=("Segoe UI", 10, "bold"),
                 bg=BG2, fg=TEXT).pack(anchor="w", padx=12, pady=(12, 6))
        check_vars = []
        for model in all_models:
            var = tk.BooleanVar(value=True)
            check_vars.append((model, var))
            tk.Checkbutton(
                left,
                text=f"[{model['slot']}] {model['name']}",
                variable=var,
                bg=BG2,
                fg=TEXT,
                activebackground=BG2,
                activeforeground=TEXT,
                selectcolor=BG3,
                font=("Segoe UI", 9),
            ).pack(anchor="w", padx=12, pady=2)

        tab_var = tk.StringVar(value="bar")
        modes = [
            ("📊 Bar", "bar"),
            ("🕸 Radar", "radar"),
            ("🫧 Scatter", "scatter"),
            ("📋 Table", "table"),
        ]
        tk.Label(left, text="Kiểu hiển thị", font=("Segoe UI", 10, "bold"),
                 bg=BG2, fg=TEXT).pack(anchor="w", padx=12, pady=(16, 6))
        for text, value in modes:
            tk.Radiobutton(
                left,
                text=text,
                value=value,
                variable=tab_var,
                bg=BG2,
                fg=TEXT,
                activebackground=BG2,
                activeforeground=TEXT,
                selectcolor=BG3,
                font=("Segoe UI", 9),
            ).pack(anchor="w", padx=12, pady=2)

        chart_frame = tk.Frame(right, bg=BG)
        chart_frame.pack(fill="both", expand=True)
        palette = self._cmp_slot_colors

        def _embed_fig(fig):
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            canvas = FigureCanvasTkAgg(fig, master=chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)

        def _draw_table(models):
            txt = scrolledtext.ScrolledText(chart_frame, font=("Cascadia Code", 9), relief="flat", wrap="none")
            apply_textbox_theme(txt, dark=True)
            txt.pack(fill="both", expand=True, padx=8, pady=8)
            cols = ["Model", "Task", "Params (M)", "GFLOPs", "Layers", "Size (MB)"]
            widths = [24, 12, 12, 10, 8, 10]
            hdr = "│".join(f" {c.ljust(w)} " for c, w in zip(cols, widths))
            sep = "┼".join("─" * (w + 2) for w in widths)
            txt.insert("end", f"┌{'┬'.join('─' * (w + 2) for w in widths)}┐\n")
            txt.insert("end", f"│{hdr}│\n")
            txt.insert("end", f"├{sep}┤\n")
            for model in models:
                stats = model["stats"]
                row_vals = [
                    model["name"],
                    model["task"],
                    f"{(stats.get('parameters') or 0) / 1e6:.3f}" if stats.get("parameters") else "—",
                    f"{stats.get('gflops'):.3f}" if stats.get("gflops") is not None else "—",
                    str(stats.get("layers") or "—"),
                    f"{model.get('size_mb', 0):.2f}" if model.get("size_mb") else "—",
                ]
                txt.insert("end", f"│{'│'.join(f' {str(v).ljust(w)} ' for v, w in zip(row_vals, widths))}│\n")
            txt.insert("end", f"└{'┴'.join('─' * (w + 2) for w in widths)}┘\n")
            txt.configure(state="disabled")

        def _draw_bar(models):
            import matplotlib.pyplot as plt

            metric_defs = [
                ("Params (M)", lambda m: (m["stats"].get("parameters") or 0) / 1e6),
                ("GFLOPs", lambda m: m["stats"].get("gflops") or 0),
                ("Layers", lambda m: m["stats"].get("layers") or 0),
                ("Size (MB)", lambda m: m.get("size_mb") or 0),
            ]
            active = [(label, fn) for label, fn in metric_defs if any(fn(m) > 0 for m in models)]
            if not active:
                _draw_table(models)
                return
            fig, axes = plt.subplots(2, 2, figsize=(10, 6.5))
            fig.patch.set_facecolor("#1e1e2e")
            axes = axes.flatten()
            for idx, (title, fn) in enumerate(active):
                ax = axes[idx]
                ax.set_facecolor("#252538")
                vals = [fn(m) for m in models]
                labels = [m["name"] for m in models]
                bars = ax.bar(range(len(models)), vals, color=[palette[i % len(palette)] for i in range(len(models))], alpha=0.88)
                ax.set_title(title, color="white", fontsize=10, fontweight="bold")
                ax.set_xticks(range(len(models)))
                ax.set_xticklabels(labels, rotation=12 if len(models) > 2 else 0,
                                   ha="right" if len(models) > 2 else "center",
                                   fontsize=8, color="white")
                ax.tick_params(axis="y", colors="white", labelsize=8)
                ax.grid(True, axis="y", alpha=0.2, color="#555577", linestyle="--")
                for bar, val in zip(bars, vals):
                    if val:
                        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() * 1.02,
                                f"{val:.2f}" if val < 1000 else f"{val:.0f}",
                                ha="center", va="bottom", fontsize=8, color="white")
            for idx in range(len(active), len(axes)):
                axes[idx].set_visible(False)
            plt.tight_layout()
            _embed_fig(fig)
            plt.close(fig)

        def _draw_radar(models):
            try:
                import numpy as np
                import matplotlib.pyplot as plt
            except ImportError:
                _draw_table(models)
                return
            metric_defs = [
                ("Params (M)", lambda m: (m["stats"].get("parameters") or 0) / 1e6, True),
                ("GFLOPs", lambda m: m["stats"].get("gflops") or 0, True),
                ("Size (MB)", lambda m: m.get("size_mb") or 0, True),
                ("Layers", lambda m: m["stats"].get("layers") or 0, False),
            ]
            active = [(label, fn, inv) for label, fn, inv in metric_defs if any(fn(m) > 0 for m in models)]
            if len(active) < 3:
                _draw_table(models)
                return
            fig, ax = plt.subplots(figsize=(7.5, 6.5), subplot_kw={"polar": True})
            fig.patch.set_facecolor("#1e1e2e")
            ax.set_facecolor("#252538")
            angles = np.linspace(0, 2 * np.pi, len(active), endpoint=False)
            for idx, model in enumerate(models):
                raw = np.array([fn(model) for _, fn, _ in active], dtype=float)
                maxv = np.array([max(fn(mm) for mm in models) or 1 for _, fn, _ in active], dtype=float)
                norm = raw / maxv
                for i, (_, _, inv) in enumerate(active):
                    if inv:
                        norm[i] = 1.0 - norm[i]
                vals = np.concatenate([norm, norm[:1]])
                ang = np.concatenate([angles, angles[:1]])
                color = palette[idx % len(palette)]
                ax.plot(ang, vals, "o-", linewidth=2, color=color, label=model["name"])
                ax.fill(ang, vals, alpha=0.12, color=color)
            ax.set_xticks(angles)
            ax.set_xticklabels([label for label, _, _ in active], color="white", fontsize=9)
            ax.set_yticks([0.25, 0.5, 0.75, 1.0])
            ax.set_yticklabels(["25%", "50%", "75%", "100%"], color="#888888", fontsize=7)
            ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.12), fontsize=8)
            plt.tight_layout()
            _embed_fig(fig)
            plt.close(fig)

        def _draw_scatter(models):
            try:
                import matplotlib.pyplot as plt
            except ImportError:
                _draw_table(models)
                return
            params_m = [(m["stats"].get("parameters") or 0) / 1e6 for m in models]
            gflops = [m["stats"].get("gflops") or 0 for m in models]
            sizes = [m.get("size_mb") or 0 for m in models]
            if not any(params_m) or not any(gflops):
                _draw_table(models)
                return
            fig, ax = plt.subplots(figsize=(9, 6))
            fig.patch.set_facecolor("#1e1e2e")
            ax.set_facecolor("#252538")
            max_size = max(sizes) or 1
            for idx, model in enumerate(models):
                size = max(100, (sizes[idx] / max_size) * 900)
                color = palette[idx % len(palette)]
                ax.scatter(gflops[idx], params_m[idx], s=size, color=color, alpha=0.8,
                           edgecolors="white", linewidth=1.2)
                ax.annotate(model["name"], (gflops[idx], params_m[idx]),
                            textcoords="offset points", xytext=(10, 5), fontsize=9, color="white")
            ax.set_xlabel("GFLOPs", color="white")
            ax.set_ylabel("Parameters (M)", color="white")
            ax.grid(True, alpha=0.18, color="#555577", linestyle="--")
            ax.tick_params(colors="white")
            plt.tight_layout()
            _embed_fig(fig)
            plt.close(fig)

        def update_chart():
            for widget in chart_frame.winfo_children():
                widget.destroy()
            selected = [model for model, var in check_vars if var.get()]
            if not selected:
                tk.Label(chart_frame, text="⚠ Chọn ít nhất 1 model.",
                         font=("Segoe UI", 11), bg=BG, fg=WARNING).pack(expand=True)
                status_lbl.configure(text="Chưa chọn model", fg=WARNING)
                return
            mode = tab_var.get()
            try:
                if mode == "bar":
                    _draw_bar(selected)
                elif mode == "radar":
                    _draw_radar(selected)
                elif mode == "scatter":
                    _draw_scatter(selected)
                else:
                    _draw_table(selected)
                status_lbl.configure(text=f"So sánh {len(selected)} model • {mode.upper()}", fg=SUCCESS)
            except Exception as ex:
                for widget in chart_frame.winfo_children():
                    widget.destroy()
                _draw_table(selected)
                status_lbl.configure(text=f"Lỗi vẽ biểu đồ: {ex}", fg=WARNING)

        bottom = tk.Frame(win, bg=BG2, pady=8)
        bottom.pack(fill="x", side="bottom")
        tk.Button(bottom, text="🔄 Cập nhật", font=("Segoe UI", 10, "bold"),
                  bg=ACCENT, fg="white", relief="flat", cursor="hand2",
                  padx=18, pady=7, command=update_chart).pack(side="left", padx=16)
        tk.Button(bottom, text="Đóng", font=("Segoe UI", 10),
                  bg=BG3, fg=TEXT_DIM, relief="flat", cursor="hand2",
                  padx=14, pady=7, command=win.destroy).pack(side="right", padx=16)
        update_chart()

    def _cmp_get_model_info(self, model, path: str, imgsz: int = 640) -> dict:
        """Trích xuất thông số với 3 tầng bảo vệ (Fix cho Python 3.14+)."""
        info = {"model_name": Path(path).name, "params_m": "—", "gflops": "—", "size_mb": "—"}

        # 1. Tính dung lượng file (luôn chạy được)
        try:
            info["size_mb"] = f"{Path(path).stat().st_size / (1024 * 1024):.2f}"
        except Exception:
            pass

        # ONNX → không đếm được params/GFLOPs
        if Path(path).suffix.lower() == ".onnx":
            info["params_m"] = "N/A (ONNX)"
            info["gflops"]   = "N/A (ONNX)"
            return info

        # 2. Lấy thông số cho file .pt — dùng _get_model_stats() helper
        try:
            params_m, gflops = self._get_model_stats(model, imgsz)
            info["params_m"] = f"{params_m:.4f}" if params_m is not None else "N/A"
            info["gflops"]   = f"{gflops:.3f}"   if gflops  is not None else "N/A"
        except Exception as e:
            print(f"[Debug] Lỗi lấy thông số model: {e}")
            self._log(f"[Lỗi đo info .pt] {e}", "err")

        return info

    # ─────────────────────────────────────────────────────────────────────────
    # SO SÁNH MODEL — LOAD MODEL
    # ─────────────────────────────────────────────────────────────────────────
    def _cmp_load_model(self, slot: int):
        path = self._cmp_path_var[slot].get().strip()
        if not path or not Path(path).exists():
            messagebox.showerror("Lỗi", f"Chọn file model hợp lệ cho {self._cmp_slot_name(slot)}.")
            return
        self._cmp_set_info(slot, "⏳ Đang tải...", WARNING)
        ext = Path(path).suffix.lower()

        def _do():
            try:
                if ext == ".pth":
                    # ── Load PyTorch CNN (.pth) ────────────────────────────
                    import torch, torch.nn as nn
                    try:
                        _ckpt = torch.load(path, map_location="cpu", weights_only=True)
                    except Exception:
                        _ckpt = torch.load(path, map_location="cpu", weights_only=False)
                    if isinstance(_ckpt, dict) and "model_weights" in _ckpt:
                        _sd = _ckpt["model_weights"]
                        _saved_names = list(_ckpt.get("class_names", []))
                    else:
                        _sd = _ckpt; _saved_names = []

                    # Auto-detect arch
                    _is_mobilenet = any("features.0.0.weight" in k for k in _sd.keys())
                    _arch_name = "MobileNetV2 (PLOS)" if _is_mobilenet else "CustomCNN (JILSA)"

                    # Infer num_classes — same logic as inference tab
                    _nc = 0
                    if "classifier.4.weight" in _sd:          # JILSA CustomCNN
                        _nc = _sd["classifier.4.weight"].shape[0]
                    elif "classifier.1.weight" in _sd:        # MobileNetV2 (PLOS)
                        _nc = _sd["classifier.1.weight"].shape[0]
                    elif "fc.weight" in _sd:                   # ResNet-style
                        _nc = _sd["fc.weight"].shape[0]
                    else:
                        # fallback: find last weight tensor with 2D shape
                        for _k in reversed(list(_sd.keys())):
                            _t = _sd[_k]
                            if hasattr(_t, "shape") and len(_t.shape) == 2:
                                _nc = _t.shape[0]; break
                    if _nc == 0:
                        _nc = len(_saved_names) if _saved_names else 3

                    # Build model — kiến trúc khớp đúng với bài báo
                    if _is_mobilenet:
                        from torchvision import models as _tv_models
                        _mdl = _tv_models.mobilenet_v2(weights=None)
                        # PLOS ONE 2024: 5-layer classifier head (giống train.py)
                        _mdl.classifier = nn.Sequential(
                            nn.Dropout(p=0.2),
                            nn.Linear(_mdl.last_channel, 128),
                            nn.ReLU(inplace=True),
                            nn.Dropout(p=0.2),
                            nn.Linear(128, _nc),
                        )
                    else:
                        class _CustomCNN(nn.Module):
                            def __init__(self, nc):
                                super().__init__()
                                self.features = nn.Sequential(
                                    nn.Conv2d(3, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(True), nn.MaxPool2d(2),
                                    nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(True), nn.MaxPool2d(2),
                                    nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(True), nn.MaxPool2d(2),
                                    nn.Conv2d(128, 256, 3, padding=1), nn.BatchNorm2d(256), nn.ReLU(True), nn.MaxPool2d(2),
                                    nn.AdaptiveAvgPool2d((9, 9)),
                                )
                                self.classifier = nn.Sequential(
                                    nn.Flatten(), nn.Linear(256*9*9, 512), nn.ReLU(True),
                                    nn.Dropout(0.5), nn.Linear(512, nc))
                            def forward(self, x): return self.classifier(self.features(x))
                        _mdl = _CustomCNN(_nc)

                    _mdl.load_state_dict(_sd, strict=False)
                    _mdl.eval()
                    _params = sum(p.numel() for p in _mdl.parameters())

                    # ── Đếm layers (Conv/Linear/BN) ──────────────────────
                    _layer_types = (nn.Conv2d, nn.Linear, nn.BatchNorm2d,
                                    nn.BatchNorm1d, nn.ConvTranspose2d)
                    _layer_count = sum(1 for m in _mdl.modules()
                                       if isinstance(m, _layer_types))

                    # ── GFLOPs qua thop ──────────────────────────────────
                    _gflops_str = "N/A (.pth)"; _gflops_num = None
                    try:
                        _ensure_packages("thop")
                        from thop import profile as _thop_profile
                        import torch as _torch_thop
                        _imgsz_thop = 224 if _is_mobilenet else 200
                        _dummy = _torch_thop.zeros(1, 3, _imgsz_thop, _imgsz_thop)
                        _macs, _ = _thop_profile(_mdl, inputs=(_dummy,), verbose=False)
                        _gflops_num = _macs * 2 / 1e9
                        _gflops_str = f"{_gflops_num:.3f}"
                    except Exception as _te:
                        pass

                    self._cmp_model[slot] = _mdl
                    self._cmp_model_type[slot] = "pth"
                    if _saved_names:
                        self._cmp_pth_class_names[slot] = _saved_names
                    else:
                        # smart default
                        _defaults = {3: ["Viêm da nổi cục", "Nấm da", "Mụn cóc"],
                                     2: ["Khỏe mạnh", "Viêm da nổi cục"]}
                        self._cmp_pth_class_names[slot] = _defaults.get(_nc, [f"Class {i}" for i in range(_nc)])

                    # Store info
                    _size_mb = f"{Path(path).stat().st_size / (1024*1024):.2f}"
                    info_d = {
                        "model_name": Path(path).name,
                        "params_m":   f"{_params/1e6:.4f}",
                        "gflops":     _gflops_str,
                        "size_mb":    _size_mb,
                        "size_mb_num": float(_size_mb),
                        "parameters": _params,
                        "gflops_num": _gflops_num,
                        "layers_raw": _layer_count,
                        "layers":     _layer_count,
                        "task_type":  f"CNN ({_arch_name})",
                    }
                    for k, v in info_d.items():
                        self._cmp_metrics[slot][k] = v

                    cls_str = ", ".join(self._cmp_pth_class_names[slot][:5])
                    _gflops_info = _gflops_str if _gflops_num is None else f"{_gflops_num:.3f} G"
                    self._cmp_apply_saved_eval_artifacts(slot)
                    txt = (f"✔ {Path(path).name}  [🧠 PyTorch CNN]\n"
                           f"Arch: {_arch_name}  |  Layers: {_layer_count}  |  Classes: {_nc}\n"
                           f"Params: {_params/1e6:.2f} M  |  GFLOPs: {_gflops_info}  |  Size: {_size_mb} MB\n"
                           f"Classes: {cls_str}")
                    self.after(0, self._cmp_set_info, slot, txt, INFO)
                    self.after(0, self._cmp_build_metrics_table)

                else:
                    # ── Load YOLO (.pt / .onnx) ────────────────────────────
                    if ext == ".onnx":
                        _ensure_packages("onnx", "onnxslim", "onnxruntime-gpu")
                    _ensure_packages("ultralytics")
                    import importlib; importlib.invalidate_caches()
                    try:
                        import onnxruntime as _ort; _ort.set_default_logger_severity(3)
                    except Exception:
                        pass
                    YOLO = _import_yolo()
                    task_map = {"Detection": "detect",
                                "Instance Segmentation": "segment",
                                "Classification": "classify"}
                    task = task_map.get(self._cmp_task_var[slot].get(), "detect")
                    mdl = YOLO(path, task=task)

                    # ── Auto-detect native imgsz from ONNX input shape ──
                    _native_imgsz = self._cmp_imgsz_var.get()  # fallback
                    if ext == ".onnx":
                        try:
                            import onnx as _onnx_mod
                            _onnx_proto = _onnx_mod.load(path)
                            _inp = _onnx_proto.graph.input[0]
                            _dims = _inp.type.tensor_type.shape.dim
                            # shape: [batch, C, H, W]
                            if len(_dims) >= 4:
                                _h = _dims[2].dim_value
                                _w = _dims[3].dim_value
                                if _h > 0 and _w > 0:
                                    _native_imgsz = max(_h, _w)
                        except Exception:
                            pass
                    self._cmp_imgsz_slot[slot] = _native_imgsz

                    # warm-up with correct imgsz
                    import numpy as _np
                    _dummy = _np.zeros((_native_imgsz, _native_imgsz, 3), dtype=_np.uint8)
                    mdl.predict(source=_dummy, imgsz=_native_imgsz,
                                device=self._cmp_device_var.get(), verbose=False)
                    self._cmp_model[slot] = mdl
                    self._cmp_model_type[slot] = "yolo"
                    info_d = self._cmp_get_model_info(mdl, path, imgsz=_native_imgsz)
                    # Store native imgsz so metrics table shows correct value
                    info_d["imgsz"] = _native_imgsz
                    # ── Parse layers/params/GFLOPs via stdout capture ─────
                    import io as _sio, sys as _ssys, re as _sre
                    raw_layers = raw_params = raw_gflops = None
                    try:
                        _buf2 = _sio.StringIO()
                        _old2 = _ssys.stdout; _ssys.stdout = _buf2
                        try:
                            raw_info = mdl.info(verbose=True)
                        finally:
                            _ssys.stdout = _old2
                        _out2 = _buf2.getvalue()
                        # Parse: "YOLOv8n summary: 225 layers, 3157200 parameters, ..."
                        _ml = _sre.search(r'(\d+)\s+layers', _out2)
                        if _ml:
                            raw_layers = int(_ml.group(1))
                        _mp = _sre.search(r'([\d,]+)\s+parameters', _out2)
                        if _mp:
                            raw_params = int(_mp.group(1).replace(',', ''))
                        _mg = _sre.search(r'([\d.]+)\s+GFLOPs', _out2)
                        if _mg:
                            raw_gflops = float(_mg.group(1))
                        # Fallback: try tuple return from mdl.info()
                        if isinstance(raw_info, (list, tuple)):
                            if raw_layers is None and len(raw_info) > 0 and raw_info[0]:
                                try: raw_layers = int(raw_info[0])
                                except Exception: pass
                            if raw_params is None and len(raw_info) > 1 and raw_info[1]:
                                try: raw_params = int(raw_info[1])
                                except Exception: pass
                            if raw_gflops is None and len(raw_info) >= 4 and raw_info[3]:
                                try: raw_gflops = float(raw_info[3])
                                except Exception: pass
                    except Exception:
                        pass
                    # Fallback: count layers directly from model
                    if raw_layers is None:
                        try:
                            raw_layers = len(list(mdl.model.model))
                        except Exception:
                            pass
                    info_d["layers_raw"] = raw_layers
                    info_d["layers"] = raw_layers if raw_layers is not None else "—"
                    info_d["parameters"] = raw_params
                    info_d["gflops_num"] = raw_gflops
                    try:
                        info_d["size_mb_num"] = Path(path).stat().st_size / (1024 * 1024)
                    except Exception:
                        info_d["size_mb_num"] = None
                    info_d["task_type"] = task
                    for k, v in info_d.items():
                        self._cmp_metrics[slot][k] = v
                    cls_names = list(mdl.names.values()) if hasattr(mdl, "names") else []
                    self._cmp_apply_saved_eval_artifacts(slot)
                    txt = (f"✔ {info_d['model_name']}\n"
                           f"Params: {info_d['params_m']} M  |  GFLOPs: {info_d['gflops']}\n"
                           f"Size: {info_d['size_mb']} MB  |  Classes: {len(cls_names)}\n"
                           f"{', '.join(cls_names[:5])}{'...' if len(cls_names) > 5 else ''}")
                    self.after(0, self._cmp_set_info, slot, txt, SUCCESS)
                    self.after(0, self._cmp_build_metrics_table)

            except Exception as ex:
                _emsg = f"✗ {str(ex)[:120]}"
                self.after(0, self._cmp_set_info, slot, _emsg, DANGER)
                self.after(0, messagebox.showerror, "Lỗi tải model",
                           f"Slot {self._cmp_slot_labels[slot]} — {Path(path).name}\n\n{ex}")

        threading.Thread(target=_do, daemon=True).start()

    # ─────────────────────────────────────────────────────────────────────────
    # SO SÁNH MODEL — RUN INFERENCE
    # ─────────────────────────────────────────────────────────────────────────
    def _cmp_start(self):
        active_slots = list(self._cmp_active_slots())
        missing = [self._cmp_slot_labels[slot] for slot in active_slots if self._cmp_model[slot] is None]
        if missing:
            messagebox.showwarning("Chưa tải model", f"Hãy tải Model {', '.join(missing)} trước.")
            return
        src = self._cmp_source_var.get()
        if src == "Webcam":
            source = self._cmp_cam_var.get()
        else:
            path = self._cmp_input_var.get().strip()
            if not path or not Path(path).exists():
                messagebox.showerror("Lỗi", "Chọn file ảnh/video hợp lệ.")
                return
            source = path

        self._cmp_running   = True
        self._cmp_stop_flag = False
        self._cmp_start_btn.configure(state="disabled")
        self._cmp_stop_btn.configure(state="normal")

        # init runtime metrics counters
        for slot in active_slots:
            self._cmp_metrics[slot].setdefault("model_name", Path(self._cmp_path_var[slot].get()).name)
            self._cmp_metrics[slot].update({
                "total_frames": 0, "total_dets": 0,
                "_sum_ms": 0.0, "_sum_fps": 0.0, "_n": 0,
            })

        mode = "image" if src == "Ảnh (Image)" else "stream"
        threading.Thread(
            target=self._cmp_inference_thread,
            args=(source, mode), daemon=True).start()

        if mode == "stream":
            self.after(30, self._cmp_poll_queue)

    def _cmp_stop(self):
        self._cmp_stop_flag = True
        self._cmp_start_btn.configure(state="normal")
        self._cmp_stop_btn.configure(state="disabled")

    def _cmp_inference_thread(self, source, mode: str):
        try:
            cv2 = _import_cv2()
            Image, _, ImageDraw, ImageFont = _import_pil()
            np  = _import_numpy()
            # conf/iou ở đây chỉ dùng làm fallback cho pth; YOLO dùng per-slot
            conf   = self._cmp_conf_var.get()
            iou    = self._cmp_iou_var.get()
            imgsz  = self._cmp_imgsz_var.get()
            device = self._cmp_device_var.get()
            active_slots = list(self._cmp_active_slots())
            is_seg = {
                s: self._cmp_task_var[s].get() == "Instance Segmentation"
                for s in active_slots
            }
            fps_counters = {s: [] for s in active_slots}

            # Pre-build torchvision transform for pth slots
            import importlib as _imp
            _torch = None; _transforms = None
            if "pth" in self._cmp_model_type:
                import torch as _torch
                from torchvision import transforms as _transforms

            _pth_tf = None
            if _transforms is not None:
                _pth_tf = _transforms.Compose([
                    _transforms.Resize((imgsz, imgsz)),
                    _transforms.ToTensor(),
                    _transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
                ])

            def _infer_pth(slot, frame_bgr):
                """Run PyTorch CNN inference on a BGR frame."""
                t0 = time.perf_counter()
                # BGR → PIL RGB
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(frame_rgb)
                tensor = _pth_tf(pil_img).unsqueeze(0)
                with _torch.no_grad():
                    logits = self._cmp_model[slot](tensor)
                    probs  = _torch.softmax(logits, dim=1)[0]
                ms = (time.perf_counter() - t0) * 1000
                top1_id = int(probs.argmax())
                top1_cf = float(probs[top1_id])
                names   = self._cmp_pth_class_names[slot]
                top1_nm = names[top1_id] if top1_id < len(names) else str(top1_id)

                # Top-k classification metrics
                _topk = min(5, len(names))
                _topk_probs, _topk_ids = _torch.topk(probs, _topk)
                _top3_str = ", ".join(
                    f"{names[int(i)] if int(i) < len(names) else str(int(i))}:{float(p):.0%}"
                    for i, p in zip(_topk_ids[:3], _topk_probs[:3]))
                _top5_str = ", ".join(
                    f"{names[int(i)] if int(i) < len(names) else str(int(i))}:{float(p):.0%}"
                    for i, p in zip(_topk_ids, _topk_probs))
                self._cmp_metrics[slot]["top1_class"] = top1_nm
                self._cmp_metrics[slot]["top1_conf"]  = f"{top1_cf:.2%}"
                self._cmp_metrics[slot]["top1_conf_num"] = top1_cf
                self._cmp_metrics[slot]["top3"]       = _top3_str
                self._cmp_metrics[slot]["val_top1"]   = f"{top1_cf:.2%}"
                self._cmp_metrics[slot]["val_top5"]   = f"{float(_topk_probs[:min(5,_topk)].sum()):.2%}"
                self._cmp_metrics[slot]["total_dets"] = 1

                # Draw result overlay on PIL image (convert to RGBA for semi-transparent rects)
                pil_img = pil_img.convert("RGBA")
                overlay = Image.new("RGBA", pil_img.size, (0, 0, 0, 0))
                draw = ImageDraw.Draw(overlay)
                try:
                    font_big  = ImageFont.truetype("arial.ttf", max(14, imgsz // 20))
                    font_small= ImageFont.truetype("arial.ttf", max(10, imgsz // 28))
                except Exception:
                    font_big = font_small = ImageFont.load_default()
                color = "#22c55e" if top1_cf >= 0.6 else ("#f59e0b" if top1_cf >= 0.4 else "#ef4444")
                label = f"{top1_nm}  {top1_cf:.1%}"
                draw.rectangle([0, 0, pil_img.width, 36], fill=(0, 0, 0, 160))
                draw.text((8, 6), label, font=font_big, fill=color)
                # Draw prob bars for all classes
                bar_y = 40
                for i, nm in enumerate(names):
                    p = float(probs[i]) if i < len(probs) else 0.0
                    bar_w = int((pil_img.width - 12) * p)
                    bg = (34, 197, 94, 200) if i == top1_id else (71, 85, 105, 180)
                    draw.rectangle([6, bar_y, 6 + bar_w, bar_y + 14], fill=bg)
                    draw.text((8, bar_y), f"{nm[:18]}: {p:.1%}", font=font_small, fill=(220, 220, 220, 255))
                    bar_y += 18
                    if bar_y > pil_img.height - 10:
                        break
                pil_img = Image.alpha_composite(pil_img, overlay).convert("RGB")

                # Return PIL Image (required by _CanvasImage.show)
                n_label = f"{top1_nm} {top1_cf:.0%}"
                return pil_img, None, ms, n_label, True

            def _infer_one(slot, frame_bgr):
                if self._cmp_model_type[slot] == "pth":
                    return _infer_pth(slot, frame_bgr)
                t0    = time.perf_counter()
                _conf = self._cmp_conf_slot[slot].get()
                _iou  = self._cmp_iou_slot[slot].get()
                # Use per-slot native imgsz (important for ONNX fixed-size models)
                _imgsz = self._cmp_imgsz_slot[slot] or imgsz
                results = self._cmp_model[slot].predict(
                    source=frame_bgr, conf=_conf, iou=_iou,
                    imgsz=_imgsz, device=device, verbose=False, save=False)
                ms = (time.perf_counter() - t0) * 1000
                r  = results[0]
                is_cls = self._cmp_task_var[slot].get() == "Classification"
                if is_cls:
                    ann = self._draw_cls_result(r, _import_cv2(), _import_pil()[0])
                    if r.probs is not None:
                        top1_id = int(r.probs.top1)
                        top1_cf = float(r.probs.top1conf)
                        names   = r.names if hasattr(r, "names") and r.names else {}
                        n_label = f"{names.get(top1_id, str(top1_id))} {top1_cf:.0%}"
                    else:
                        n_label = "—"
                    return ann, r, ms, n_label, True
                else:
                    ann = self._draw_result(r, cv2, Image, np, is_seg[slot], conf, 75)
                    n   = len(r.boxes) if r.boxes is not None else 0
                    return ann, r, ms, n, False

            if mode == "image":
                src_path  = str(source)
                frame_bgr = cv2.imread(src_path)
                if frame_bgr is None:
                    raise RuntimeError(f"Không đọc được ảnh: {src_path}")
                frames_data = {}
                for slot in active_slots:
                    result_tuple = _infer_one(slot, frame_bgr)
                    ann, r, ms, n_val, is_cls = result_tuple
                    frames_data[slot] = {
                        "image": ann,
                        "ms": ms,
                        "label": n_val,
                        "is_cls": is_cls,
                    }
                    self._cmp_metrics[slot]["total_frames"] = 1
                    self._cmp_metrics[slot]["avg_ms"]  = f"{ms:.1f}"
                    self._cmp_metrics[slot]["avg_fps"] = f"{1000/ms:.1f}" if ms > 0 else "—"
                    self._cmp_metrics[slot]["_sum_ms"] = ms
                    self._cmp_metrics[slot]["_n"]      = 1
                    if is_cls:
                        if self._cmp_model_type[slot] == "pth":
                            # metrics already stored inside _infer_pth — nothing to do
                            pass
                        elif r is not None and r.probs is not None:
                            names = r.names if hasattr(r, "names") and r.names else {}
                            top1_id = int(r.probs.top1)
                            top1_cf = float(r.probs.top1conf)
                            top5_ids = r.probs.top5
                            top5_cfs = r.probs.top5conf.tolist()
                            top3_str = ", ".join(
                                f"{names.get(int(i), str(i))}:{float(c):.0%}"
                                for i, c in zip(top5_ids[:3], top5_cfs[:3])
                            )
                            self._cmp_metrics[slot]["top1_class"] = names.get(top1_id, str(top1_id))
                            self._cmp_metrics[slot]["top1_conf"]  = f"{top1_cf:.2%}"
                            self._cmp_metrics[slot]["top1_conf_num"] = top1_cf
                            self._cmp_metrics[slot]["top3"]       = top3_str
                            self._cmp_metrics[slot]["total_dets"] = 1
                        else:
                            self._cmp_metrics[slot]["top1_class"] = "—"
                            self._cmp_metrics[slot]["top1_conf"]  = "—"
                            self._cmp_metrics[slot]["total_dets"] = 0
                    else:
                        self._cmp_metrics[slot]["total_dets"] = n_val
                        if r is not None and getattr(r, "boxes", None) is not None and len(r.boxes) > 0:
                            try:
                                avg_conf = float(r.boxes.conf.mean().item())
                                self._cmp_metrics[slot]["avg_conf"] = avg_conf
                            except Exception:
                                pass

                self.after(0, self._cmp_show_images, frames_data, True)
                self.after(0, self._cmp_build_metrics_table)
                self.after(0, self._cmp_on_done)

            else:  # stream / video
                cap_src = source if isinstance(source, int) else str(source)
                cap = cv2.VideoCapture(cap_src)
                if not cap.isOpened():
                    raise RuntimeError(f"Không mở được nguồn: {source}")

                while not self._cmp_stop_flag:
                    ok, frame_bgr = cap.read()
                    if not ok:
                        break
                    frame_payload = {}
                    for slot in active_slots:
                        ann, r, ms, n_val, is_cls = _infer_one(slot, frame_bgr)
                        frame_payload[slot] = {
                            "image": ann,
                            "ms": ms,
                            "label": n_val,
                            "is_cls": is_cls,
                        }
                        m = self._cmp_metrics[slot]
                        m["total_frames"] = m.get("total_frames", 0) + 1
                        m["total_dets"]   = m.get("total_dets", 0) + (0 if is_cls else n_val)
                        m["_sum_ms"]      = m.get("_sum_ms", 0.0) + ms
                        m["_n"]           = m.get("_n", 0) + 1
                        m["avg_ms"]       = f"{m['_sum_ms'] / m['_n']:.1f}"
                        now = time.perf_counter()
                        fps_counters[slot].append(now)
                        fps_counters[slot] = [t for t in fps_counters[slot] if now - t <= 1.0]
                        m["avg_fps"] = str(len(fps_counters[slot]))

                    try:
                        self._cmp_frame_queue.put_nowait(frame_payload)
                    except queue.Full:
                        pass

                cap.release()
                self.after(0, self._cmp_on_done)

        except Exception as ex:
            import traceback, sys
            _tb = traceback.format_exc()
            print("[CMP ERROR]", _tb, file=sys.stderr)
            self.after(0, lambda msg=_tb: messagebox.showerror("Lỗi so sánh", msg[:1200]))
            self.after(0, self._cmp_on_done)

    def _cmp_poll_queue(self):
        if not self._cmp_running:
            return
        try:
            payload = self._cmp_frame_queue.get_nowait()
            self._cmp_show_images(payload, False)
        except queue.Empty:
            pass
        self.after(30, self._cmp_poll_queue)

    def _cmp_show_images(self, payload: dict, image_mode: bool):
        for slot in self._cmp_active_slots():
            if slot not in payload:
                continue
            item = payload[slot]
            self._cmp_canvas_img[slot].show(item["image"])
            fps = "—" if image_mode else self._cmp_metrics[slot].get("avg_fps", "—")
            self._cmp_fps_lbl[slot].configure(text=f"FPS: {fps}")
            self._cmp_ms_lbl[slot].configure(text=f"ms: {item['ms']:.0f}")
            label = item["label"]
            self._cmp_det_lbl[slot].configure(
                text=f"cls: {label}" if item.get("is_cls") else f"obj: {label}"
            )
            self._cmp_render_slot_summary(slot)

    def _cmp_on_done(self):
        self._cmp_running = False
        self._cmp_start_btn.configure(state="normal")
        self._cmp_stop_btn.configure(state="disabled")

    def _cmp_open_aux_segment_popup(self):
        if self._cmp_source_var.get() != "Ảnh (Image)":
            messagebox.showwarning("Chưa đúng nguồn", "Mô hình bổ sung chỉ chạy với nguồn Ảnh (Image).")
            return
        image_path = self._cmp_input_var.get().strip()
        if not image_path or not Path(image_path).is_file():
            messagebox.showwarning("Chưa chọn ảnh", "Hãy chọn một ảnh ở page So sánh trước.")
            return

        win = tk.Toplevel(self)
        win.title("Mô hình bổ sung - YOLO Segment")
        win.configure(bg=BG2)
        win.geometry("980x680")
        win.minsize(820, 560)
        win.grab_set()

        left = tk.Frame(win, bg=BG2, padx=12, pady=12)
        left.pack(side="left", fill="y")
        right = tk.Frame(win, bg=BG, padx=10, pady=10)
        right.pack(side="left", fill="both", expand=True)

        tk.Label(left, text="🧩 YOLO Segment bổ sung", font=("Segoe UI", 11, "bold"),
                 bg=BG2, fg=ACCENT2).pack(anchor="w")
        tk.Label(left, text="Chạy riêng model segment trên ảnh đang chọn để minh họa\nhướng phát triển ngoài 2 model classification.",
                 font=("Segoe UI", 8), bg=BG2, fg=TEXT_DIM, justify="left").pack(anchor="w", pady=(4, 10))

        seg_model_var = tk.StringVar(value="")
        seg_imgsz_var = tk.IntVar(value=640)
        seg_conf_var = tk.DoubleVar(value=0.25)
        seg_device_var = tk.StringVar(value=self._cmp_device_var.get() or "0")
        status_var = tk.StringVar(value="Sẵn sàng chạy segment trên ảnh đang chọn.")
        info_var = tk.StringVar(value=f"Ảnh: {Path(image_path).name}")

        def _browse_segment_model():
            path = filedialog.askopenfilename(
                title="Chọn model YOLO Segment",
                filetypes=[("YOLO model", "*.pt"), ("All files", "*.*")],
                initialdir=str(TOOL_TRAIN_DIR),
                parent=win,
            )
            if path:
                seg_model_var.set(path)

        def _row(label, widget):
            f = tk.Frame(left, bg=BG2)
            f.pack(fill="x", pady=3)
            tk.Label(f, text=label, width=14, anchor="w", font=("Segoe UI", 8, "bold"),
                     bg=BG2, fg=TEXT).pack(side="left")
            widget.pack(side="left", fill="x", expand=True)

        model_row = tk.Frame(left, bg=BG2)
        model_entry = tk.Entry(model_row, textvariable=seg_model_var, font=("Segoe UI", 8))
        apply_entry_theme(model_entry)
        model_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(model_row, text="📄", bg=BG3, fg=TEXT, relief="flat",
                  command=_browse_segment_model).pack(side="left")
        _row("Model segment", model_row)

        imgsz_spin = tk.Spinbox(left, from_=320, to=1280, increment=32, textvariable=seg_imgsz_var,
                                bg=BG3, fg=TEXT, relief="flat", width=8, font=("Segoe UI", 8))
        _row("Imgsz", imgsz_spin)
        conf_spin = tk.Spinbox(left, from_=0.05, to=1.0, increment=0.05, textvariable=seg_conf_var,
                               bg=BG3, fg=TEXT, relief="flat", width=8, font=("Segoe UI", 8))
        _row("Conf", conf_spin)
        dev_cb = ttk.Combobox(left, textvariable=seg_device_var, values=["0", "1", "cpu"],
                              state="readonly", width=8, font=("Segoe UI", 8))
        _row("Device", dev_cb)

        tk.Label(left, textvariable=info_var, font=("Segoe UI", 8), bg=BG2, fg=INFO,
                 justify="left", wraplength=280).pack(anchor="w", pady=(8, 4))
        tk.Label(left, textvariable=status_var, font=("Segoe UI", 8), bg=BG2, fg=TEXT_DIM,
                 justify="left", wraplength=280).pack(anchor="w", pady=(0, 8))

        canvas = tk.Canvas(right, bg=BG4, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        viewer = _CanvasImage(canvas)
        try:
            Image, *_ = _import_pil()
            viewer.show(Image.open(image_path).convert("RGB"))
        except Exception:
            pass

        def _finish_segment(payload=None, error: str | None = None):
            if error:
                status_var.set(error)
                return
            if not payload:
                status_var.set("Không có dữ liệu trả về từ model segment.")
                return
            viewer.show(payload["image"])
            class_text = ", ".join(f"{k}:{v}" for k, v in payload["class_counts"].items()) or "Không có đối tượng"
            info_var.set(
                f"Model: {payload['model_name']}\n"
                f"Ảnh: {payload['image_name']}\n"
                f"Objects: {payload['total_objects']} | Masks: {payload['mask_count']}\n"
                f"Classes: {class_text}"
            )
            status_var.set(f"Xong trong {payload['infer_ms']:.1f} ms")

        def _run_segment_popup():
            model_path = seg_model_var.get().strip()
            if not model_path:
                messagebox.showwarning("Thiếu model", "Chọn model YOLO Segment trước.", parent=win)
                return
            status_var.set("⏳ Đang chạy mô hình segment bổ sung...")

            def _worker():
                try:
                    payload = run_segment_preview(
                        model_path,
                        image_path,
                        seg_imgsz_var.get(),
                        seg_conf_var.get(),
                        seg_device_var.get(),
                    )
                    self.after(0, _finish_segment, payload, None)
                except Exception as ex:
                    self.after(0, _finish_segment, None, str(ex))

            threading.Thread(target=_worker, daemon=True).start()

        btn_f = tk.Frame(left, bg=BG2)
        btn_f.pack(fill="x", pady=(6, 0))
        tk.Button(btn_f, text="▶ Chạy segment", bg=SUCCESS, fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), command=_run_segment_popup).pack(fill="x", pady=2)
        tk.Button(btn_f, text="✖ Đóng", bg=BG3, fg=TEXT, relief="flat",
                  font=("Segoe UI", 8), command=win.destroy).pack(fill="x", pady=2)

    # ─────────────────────────────────────────────────────────────────────────
    # SO SÁNH MODEL — RECORD / SAVE METRICS
    # ─────────────────────────────────────────────────────────────────────────
    def _cmp_record_metrics(self):
        """Chụp snapshot thông số hiện tại và cập nhật bảng."""
        for slot in self._cmp_active_slots():
            m = self._cmp_metrics[slot]
            n = m.get("_n", 0)
            if n > 0:
                m["avg_ms"]  = f"{m.get('_sum_ms', 0) / n:.1f}"
                fps = m.get("avg_fps", "—")
                m["avg_fps"] = fps
        self._cmp_build_metrics_table()
        messagebox.showinfo("✔ Đã ghi", "Thông số đã được cập nhật vào bảng.\n"
                            "Nhấn '💾 Lưu báo cáo' để xuất file.")

    def _cmp_save_report(self):
        """Lưu báo cáo so sánh ra JSON và CSV."""
        import json, csv

        active_slots = list(self._cmp_active_slots())
        if not any(self._cmp_metrics[s].get("model_name") for s in active_slots):
            messagebox.showinfo("Thông báo", "Hãy tải ít nhất một model và chạy inference trước.")
            return

        save_dir = filedialog.askdirectory(title="Chọn thư mục lưu báo cáo",
                                           initialdir=str(RUNS_DIR))
        if not save_dir:
            return

        import datetime
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base = Path(save_dir)

        # ── JSON ──
        report = {"timestamp": ts}
        for slot in active_slots:
            report[f"model_{self._cmp_slot_labels[slot]}"] = {
                k: v for k, v in self._cmp_metrics[slot].items() if not k.startswith("_")
            }
        json_path = base / f"cmp_report_{ts}.json"
        json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        # ── CSV ──
        csv_path = base / f"cmp_report_{ts}.csv"
        keys_order = ["model_name", "params_m", "gflops", "size_mb",
                      "avg_fps", "avg_ms", "total_frames", "total_dets"]
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Thông số"] + [self._cmp_slot_name(slot) for slot in active_slots])
            label_map = {
                "model_name":    "Tên file",
                "params_m":      "Parameters (M)",
                "gflops":        "GFLOPs",
                "size_mb":       "Kích thước (MB)",
                "avg_fps":       "FPS trung bình",
                "avg_ms":        "Inference (ms)",
                "total_frames":  "Tổng frames",
                "total_dets":    "Tổng objects",
            }
            for k in keys_order:
                row = [label_map.get(k, k)]
                for slot in active_slots:
                    row.append(self._cmp_metrics[slot].get(k, "—"))
                writer.writerow(row)
        messagebox.showinfo("✔ Đã lưu",
            f"Báo cáo đã lưu:\n• {json_path.name}\n• {csv_path.name}\n\nThư mục: {save_dir}")

        # ── Tự động lưu bản sao vào EVAL_BASE_DIR/compare để Lịch sử So sánh quét được ──
        try:
            cmp_dir = EVAL_BASE_DIR / "compare"
            cmp_dir.mkdir(parents=True, exist_ok=True)
            auto_json = cmp_dir / f"cmp_report_{ts}.json"
            if not auto_json.exists():
                auto_json.write_text(
                    json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
        # Làm mới tab Lịch sử So sánh
        self.after(300, self._cmphistory_refresh)

    def _cmp_quick_save(self):
        """Lưu phiên so sánh nhanh vào EVAL_BASE_DIR/compare không hỏi thư mục."""
        import json, datetime
        active_slots = list(self._cmp_active_slots())
        if not any(self._cmp_metrics[s].get("model_name") for s in active_slots):
            messagebox.showinfo("Thông báo",
                                "Hãy tải ít nhất một model và chạy inference trước.")
            return
        ts    = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report = {"timestamp": ts}
        for slot in active_slots:
            report[f"model_{self._cmp_slot_labels[slot]}"] = {
                k: v for k, v in self._cmp_metrics[slot].items()
                if not k.startswith("_")
            }
        try:
            cmp_dir = EVAL_BASE_DIR / "compare"
            cmp_dir.mkdir(parents=True, exist_ok=True)
            out_path = cmp_dir / f"cmp_report_{ts}.json"
            out_path.write_text(
                json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
            messagebox.showinfo("✔ Đã lưu phiên",
                                f"Phiên so sánh đã lưu:\n{out_path}")
            self.after(300, self._cmphistory_refresh)
        except Exception as ex:
            messagebox.showerror("Lỗi lưu phiên", str(ex))

    # ─────────────────────────────────────────────────────────────────────────
    # UNIFIED EVALUATION PAGE
    # ─────────────────────────────────────────────────────────────────────────
    def _build_eval_unified_tab(self, parent: tk.Frame):
        toolbar = tk.Frame(parent, bg=BG2, padx=12, pady=10)
        toolbar.pack(fill="x", padx=8, pady=(8, 0))
        tk.Label(toolbar, text="🧪  Đánh giá mô hình",
                 font=("Segoe UI", 11, "bold"), bg=BG2, fg=ACCENT2).pack(side="left")
        tk.Label(toolbar, text="Loại model:",
                 font=("Segoe UI", 9, "bold"), bg=BG2, fg=TEXT).pack(side="left", padx=(18, 6))
        mode_cb = ttk.Combobox(
            toolbar,
            textvariable=self._eval_model_kind_var,
            values=["YOLO", "CNN", "Netmobile"],
            state="readonly",
            width=14,
            font=("Segoe UI", 9),
        )
        mode_cb.pack(side="left")
        tk.Label(
            toolbar,
            text="Chọn là đổi giao diện đánh giá ngay, không cần mở tab khác.",
            font=("Segoe UI", 8, "italic"), bg=BG2, fg=TEXT_DIM
        ).pack(side="left", padx=(10, 0))
        tk.Label(toolbar, text="Model đã lưu:",
                 font=("Segoe UI", 9, "bold"), bg=BG2, fg=TEXT).pack(side="left", padx=(18, 6))
        self._eval_registry_cb = ttk.Combobox(
            toolbar,
            textvariable=self._eval_registry_label_var,
            values=[],
            state="readonly",
            width=42,
            font=("Segoe UI", 8),
        )
        self._eval_registry_cb.pack(side="left", padx=(0, 4))
        self._eval_registry_cb.bind("<<ComboboxSelected>>", self._on_eval_registry_model_selected)
        tk.Button(toolbar, text="↻", bg=BG3, fg=TEXT_DIM, relief="flat",
                  padx=6, cursor="hand2", font=("Segoe UI", 8),
                  command=self._eval_refresh_registry_models).pack(side="left")

        stack = tk.Frame(parent, bg=BG)
        stack.pack(fill="both", expand=True, padx=4, pady=8)

        yolo_frame = tk.Frame(stack, bg=BG)
        cnn_frame = tk.Frame(stack, bg=BG)
        netmobile_frame = tk.Frame(stack, bg=BG)
        for panel in (yolo_frame, cnn_frame, netmobile_frame):
            panel.place(relx=0, rely=0, relwidth=1, relheight=1)

        self._build_eval_batch_merged_tab(yolo_frame)
        self._build_jilsa_tab(cnn_frame)
        self._build_plos_tab(netmobile_frame)

        self._eval_mode_panels = {
            "YOLO": yolo_frame,
            "CNN": cnn_frame,
            "Netmobile": netmobile_frame,
        }
        mode_cb.bind("<<ComboboxSelected>>", self._on_eval_model_kind_changed)
        self._on_eval_model_kind_changed()
        self._eval_refresh_registry_models()

    def _on_eval_model_kind_changed(self, _event=None):
        selected = self._eval_model_kind_var.get().strip() or "YOLO"
        for name, panel in self._eval_mode_panels.items():
            if name == selected:
                panel.lift()
            else:
                panel.lower()

    def _eval_make_registry_label(self, model: dict) -> str:
        name = (model.get("ten") or Path(model.get("duong_dan", "")).stem or "Model").strip()
        task = str(model.get("task") or "").strip().lower() or "unknown"
        model_path = model.get("duong_dan", "")
        suffix = Path(model_path).suffix.lower() if model_path else ""
        kind = "PTH" if suffix == ".pth" else "YOLO"
        return f"{name} [{kind}/{task}]"

    def _eval_refresh_registry_models(self):
        cb = getattr(self, "_eval_registry_cb", None)
        if cb is None:
            return
        data, groups, _top_level = self._cmp_load_registry_data()
        options = []
        seen_paths = set()
        for group in groups or []:
            for model in group.get("models", []):
                path = str(model.get("duong_dan") or "").strip()
                if not path or path in seen_paths:
                    continue
                seen_paths.add(path)
                options.append(model)
        self._eval_registry_options = options
        labels = [self._eval_make_registry_label(model) for model in options]
        cb.configure(values=labels)
        current = self._eval_registry_label_var.get().strip()
        if current not in labels:
            self._eval_registry_label_var.set("")

    def _on_eval_registry_model_selected(self, _event=None):
        label = self._eval_registry_label_var.get().strip()
        if not label:
            return
        for model in self._eval_registry_options:
            if self._eval_make_registry_label(model) == label:
                self._eval_apply_registry_model(model)
                return

    def _eval_apply_registry_model(self, model: dict):
        model_path = str(model.get("duong_dan") or "").strip()
        dataset_path = str(model.get("duong_dan_dataset") or "").strip()
        task = str(model.get("task") or "").strip().lower()
        suffix = Path(model_path).suffix.lower() if model_path else ""
        lower_name = f"{model.get('ten', '')} {model_path}".lower()

        if suffix == ".pth":
            is_plos = "plos" in lower_name or "mobilenet" in lower_name or "netmobile" in lower_name
            self._eval_model_kind_var.set("Netmobile" if is_plos else "CNN")
            if is_plos:
                self._plos_model_var.set(model_path)
                if dataset_path:
                    self._plos_data_var.set(dataset_path)
            else:
                self._jilsa_model_var.set(model_path)
                if dataset_path:
                    self._jilsa_data_var.set(dataset_path)
        else:
            self._eval_model_kind_var.set("YOLO")
            self._eval_model_dir.set(model_path)
            if dataset_path:
                self._eval_data_path.set(dataset_path)
            task_map = {
                "detect": "Detection",
                "segment": "Instance Segmentation",
                "classify": "Classification",
            }
            if task in task_map:
                self._eval_task_var.set(task_map[task])

        self._on_eval_model_kind_changed()

    # ─────────────────────────────────────────────────────────────────────────
    # MERGED EVAL + BATCH TAB — BUILD UI (RadioButton mode selector)
    # ─────────────────────────────────────────────────────────────────────────
    def _build_eval_batch_merged_tab(self, parent: tk.Frame):
        """Tab gộp: RadioButton chọn mode (Val / Batch+Accuracy) + bảng so sánh bài báo."""
        from tkinter import scrolledtext as _st

        outer = tk.PanedWindow(parent, orient="vertical", bg=BG,
                               sashwidth=5, sashrelief="flat")
        outer.pack(fill="both", expand=True)

        top_frame   = tk.Frame(outer, bg=BG)
        bench_frame = tk.Frame(outer, bg=BG2, bd=0)
        outer.add(top_frame,   minsize=420)
        outer.add(bench_frame, minsize=240)

        # ── Main horizontal split ─────────────────────────────────────────
        paned = tk.PanedWindow(top_frame, orient="horizontal", bg=BG,
                               sashwidth=5, sashrelief="flat")
        paned.pack(fill="both", expand=True, padx=4, pady=4)

        # ── Left panel với scrollbar ───────────────────────────────────────
        left_container = tk.Frame(paned, bg=BG2, width=320)
        right = tk.Frame(paned, bg=BG)
        paned.add(left_container, minsize=295)
        paned.add(right,          minsize=500)

        left_canvas = tk.Canvas(left_container, bg=BG2, highlightthickness=0,
                                width=310)
        left_sb = tk.Scrollbar(left_container, orient="vertical",
                               command=left_canvas.yview)
        left_canvas.configure(yscrollcommand=left_sb.set)
        left_sb.pack(side="right", fill="y")
        left_canvas.pack(side="left", fill="both", expand=True)

        left = tk.Frame(left_canvas, bg=BG2, padx=10, pady=8)
        _left_win = left_canvas.create_window((0, 0), window=left, anchor="nw")

        def _left_configure(event=None):
            left_canvas.configure(scrollregion=left_canvas.bbox("all"))
            left_canvas.itemconfig(_left_win, width=left_canvas.winfo_width())
        left.bind("<Configure>", _left_configure)
        left_canvas.bind("<Configure>", _left_configure)

        def _on_mousewheel(event):
            left_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        left.bind_all("<MouseWheel>", _on_mousewheel)

        def sec(t): self._sec(left, t)

        # ── Chế độ đánh giá ───────────────────────────────────────────────
        mode_f = tk.LabelFrame(left, text=" 🎯 Chế độ đánh giá ",
                               font=("Segoe UI", 8, "bold"),
                               bg=BG2, fg=ACCENT2, bd=1, relief="groove", padx=6, pady=4)
        mode_f.pack(fill="x", pady=(0, 6))
        tk.Radiobutton(
            mode_f,
            text="🏅 Val chính thức (.pt)  — model.val() → mAP, P, R, F1",
            value="val", variable=self._run_mode_var,
            bg=BG2, fg=TEXT, selectcolor=BG3, activebackground=BG2,
            font=("Segoe UI", 8), command=self._on_run_mode_change,
        ).pack(anchor="w", pady=1)
        tk.Radiobutton(
            mode_f,
            text="🎯 Batch Accuracy  — predict từng ảnh → Accuracy từ tên folder",
            value="batch", variable=self._run_mode_var,
            bg=BG2, fg=TEXT, selectcolor=BG3, activebackground=BG2,
            font=("Segoe UI", 8), command=self._on_run_mode_change,
        ).pack(anchor="w", pady=1)
        tk.Label(
            mode_f,
            text="💡 Batch: mỗi sub-folder = 1 class, YOLO predict ảnh, tính accuracy",
            font=("Segoe UI", 7), bg=BG2, fg=TEXT_DIM,
            justify="left", wraplength=260,
        ).pack(anchor="w", pady=(2, 0))

        # ── Model (.pt) ────────────────────────────────────────────────────
        sec("🤖 Model YOLO (.pt)")
        f_mdir = tk.Frame(left, bg=BG2); f_mdir.pack(fill="x", pady=2)
        eval_model_entry = tk.Entry(f_mdir, textvariable=self._eval_model_dir, font=("Segoe UI", 8))
        apply_entry_theme(eval_model_entry)
        eval_model_entry.pack(side="left", fill="x", expand=True, padx=(0, 2))
        tk.Button(f_mdir, text="📄", bg=BG3, fg=TEXT, relief="flat", padx=3, cursor="hand2",
                  command=self._eval_browse_model_file).pack(side="left", padx=(0, 2))
        tk.Button(f_mdir, text="📁", bg=BG3, fg=TEXT, relief="flat", padx=3, cursor="hand2",
                  command=self._eval_browse_model_folder).pack(side="left", padx=(0, 2))
        tk.Button(f_mdir, text="🧾", bg=BG3, fg=TEXT, relief="flat", padx=3, cursor="hand2",
                  command=self._eval_show_model_config).pack(side="left")

        # ── Dataset / Nguồn ảnh ────────────────────────────────────────────
        sec("📂 Dataset / Nguồn ảnh")
        self._eval_data_hint_lbl = tk.Label(
            left, text="",
            font=("Segoe UI", 7), bg=BG2, fg=TEXT_DIM, justify="left", wraplength=270)
        self._eval_data_hint_lbl.pack(anchor="w")
        f_data = tk.Frame(left, bg=BG2); f_data.pack(fill="x", pady=2)
        eval_data_entry = tk.Entry(f_data, textvariable=self._eval_data_path, font=("Segoe UI", 8))
        apply_entry_theme(eval_data_entry)
        eval_data_entry.pack(side="left", fill="x", expand=True, padx=(0, 2))
        tk.Button(f_data, text="📄", bg=BG3, fg=TEXT, relief="flat", padx=3, cursor="hand2",
                  command=self._eval_browse_yaml).pack(side="left", padx=(0, 2))
        tk.Button(f_data, text="📁", bg=BG3, fg=TEXT, relief="flat", padx=3, cursor="hand2",
                  command=self._eval_browse_data_folder).pack(side="left", padx=(0, 2))
        tk.Button(f_data, text="🏷", bg=BG3, fg=TEXT, relief="flat", padx=6, cursor="hand2",
                  command=self._eval_open_input_registry).pack(side="left")

        # ── Task ───────────────────────────────────────────────────────────
        sec("🎯 Loại Task")
        ttk.Combobox(left, textvariable=self._eval_task_var, values=TASK_TYPES,
                     state="readonly", font=("Segoe UI", 9)).pack(fill="x", pady=2)
        self._eval_metrics_hint_lbl = tk.Label(
            left, text="", font=("Segoe UI", 8, "italic"),
            bg=BG2, fg=INFO, justify="left", wraplength=270)
        self._eval_metrics_hint_lbl.pack(anchor="w", pady=(0, 4))

        # ── Tham số chung ──────────────────────────────────────────────────
        sec("⚙ Tham số")
        self._row(left, "Img size",
                  lambda p: self._spin(p, self._eval_imgsz_var, 224, 1280, 32))
        self._row(left, "Device",
                  lambda p: ttk.Combobox(p, textvariable=self._eval_device_var,
                                         values=["0", "cpu"], state="readonly",
                                         font=("Segoe UI", 9), width=6))
        self._eval_conf_frame = tk.Frame(left, bg=BG2)
        self._eval_conf_frame.pack(fill="x")
        self._row(self._eval_conf_frame, "Conf",
                  lambda p: self._spin(p, self._eval_conf_var, 0.01, 1.0, 0.05, width=8))
        f_half = tk.Frame(left, bg=BG2); f_half.pack(fill="x", pady=2)
        tk.Checkbutton(f_half, text="Half FP16", variable=self._eval_half_var,
                       bg=BG2, fg=TEXT, selectcolor=BG3,
                       activebackground=BG2, font=("Segoe UI", 9)).pack(side="left")

        # ── Val-specific params ────────────────────────────────────────────
        self._val_specific_frame = tk.LabelFrame(
            left, text=" 📊 Val options ",
            font=("Segoe UI", 8, "bold"),
            bg=BG2, fg=TEXT_DIM, bd=1, relief="groove", padx=6, pady=4)
        self._row(self._val_specific_frame, "Split",
                  lambda p: ttk.Combobox(p, textvariable=self._eval_split_var,
                                         values=["val", "test", "train"], state="readonly",
                                         font=("Segoe UI", 9), width=6))
        self._row(self._val_specific_frame, "IOU",
                  lambda p: self._spin(p, self._eval_iou_var, 0.01, 1.0, 0.05, width=8))
        f_eval_limit = tk.Frame(self._val_specific_frame, bg=BG2)
        f_eval_limit.pack(fill="x", pady=(2, 0))
        tk.Label(f_eval_limit, text="Giới hạn ảnh", width=16, anchor="w",
                 font=("Segoe UI", 9), bg=BG2, fg=TEXT).pack(side="left")
        tk.Spinbox(
            f_eval_limit,
            textvariable=self._eval_limit_var,
            from_=0,
            to=99999,
            increment=10,
            width=8,
            bg=BG3,
            fg=SUCCESS,
            insertbackground=TEXT,
            relief="flat",
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(0, 4))
        tk.Label(f_eval_limit, text="0 = không giới hạn", bg=BG2, fg=TEXT_DIM,
                 font=("Segoe UI", 8)).pack(side="left")
        f_eval_mode = tk.Frame(self._val_specific_frame, bg=BG2)
        f_eval_mode.pack(fill="x", pady=(2, 0))
        tk.Label(f_eval_mode, text="Cách lấy mẫu", width=16, anchor="w",
                 font=("Segoe UI", 9), bg=BG2, fg=TEXT).pack(side="left")
        for value, label in [("random", "🎲 Ngẫu nhiên"), ("sequential", "📋 Tuần tự")]:
            tk.Radiobutton(
                f_eval_mode,
                text=label,
                value=value,
                variable=self._eval_limit_mode_var,
                bg=BG2,
                fg=TEXT,
                selectcolor=BG3,
                activebackground=BG2,
                font=("Segoe UI", 8),
            ).pack(side="left", padx=(0, 8))
        f_eval_filter = tk.Frame(self._val_specific_frame, bg=BG2)
        f_eval_filter.pack(fill="x", pady=(2, 0))
        tk.Label(f_eval_filter, text="Lọc theo class", width=16, anchor="w",
                 font=("Segoe UI", 9), bg=BG2, fg=TEXT).pack(side="left")
        eval_filter_entry = tk.Entry(
            f_eval_filter,
            textvariable=self._eval_class_filter_var,
            font=("Segoe UI", 8),
        )
        apply_entry_theme(eval_filter_entry)
        eval_filter_entry.pack(side="left", fill="x", expand=True)
        tk.Label(self._val_specific_frame,
                 text="💡 detect/seg + thư mục → tự tạo YAML tạm\n"
                      "💡 classify + folder class/ → tự dựng train/val/test tạm, hỗ trợ giới hạn ảnh và lọc class",
                 font=("Segoe UI", 7), bg=BG2, fg=TEXT_DIM,
                 justify="left", wraplength=260).pack(anchor="w", pady=(4, 0))
        # alias used internally by any task-change callbacks
        self._eval_det_params_frame = self._val_specific_frame

        # ── Batch-specific params ──────────────────────────────────────────
        self._batch_specific_frame = tk.LabelFrame(
            left, text=" 🖼 Batch options ",
            font=("Segoe UI", 8, "bold"),
            bg=BG2, fg=TEXT_DIM, bd=1, relief="groove", padx=6, pady=4)

        tk.Label(self._batch_specific_frame, text="💾 Thư mục lưu ảnh kết quả",
                 font=("Segoe UI", 8, "bold"), bg=BG2, fg=ACCENT2).pack(anchor="w")
        f_out = tk.Frame(self._batch_specific_frame, bg=BG2); f_out.pack(fill="x", pady=2)
        tk.Entry(f_out, textvariable=self._batch_output_dir, bg=BG3, fg=SUCCESS,
                 insertbackground=TEXT, relief="flat",
                 font=("Segoe UI", 8)).pack(side="left", fill="x", expand=True, padx=(0, 2))
        tk.Button(f_out, text="📁", bg=SUCCESS, fg="white", relief="flat", padx=6,
                  cursor="hand2", font=("Segoe UI", 9, "bold"),
                  command=lambda: self._browse_dir(
                      self._batch_output_dir, "Chọn thư mục lưu kết quả")).pack(side="left")

        f_cnt = tk.Frame(self._batch_specific_frame, bg=BG2); f_cnt.pack(fill="x", pady=(4, 0))
        self._batch_img_count_lbl = tk.Label(
            f_cnt, text="📊 Chưa đếm ảnh",
            font=("Segoe UI", 8, "italic"), bg=BG2, fg=TEXT_DIM)
        self._batch_img_count_lbl.pack(side="left")
        tk.Button(f_cnt, text="🔄", bg=BG3, fg=TEXT_DIM, relief="flat", padx=4,
                  cursor="hand2", font=("Segoe UI", 8),
                  command=self._unified_refresh_count).pack(side="right")

        f_lim = tk.Frame(self._batch_specific_frame, bg=BG2); f_lim.pack(fill="x", pady=(4, 0))
        tk.Checkbutton(f_lim, text="Giới hạn số ảnh",
                       variable=self._batch_split_enable,
                       bg=BG2, fg=TEXT, selectcolor=BG3, activebackground=BG2,
                       font=("Segoe UI", 8),
                       command=self._batch_on_split_toggle).pack(side="left")
        self._batch_split_n_spin = tk.Spinbox(
            f_lim, textvariable=self._batch_split_n,
            from_=1, to=99999, increment=10, width=7,
            bg=BG3, fg=SUCCESS, insertbackground=TEXT,
            relief="flat", font=("Segoe UI", 9), state="disabled")
        self._batch_split_n_spin.pack(side="left", padx=(6, 2))
        tk.Label(f_lim, text="ảnh", bg=BG2, fg=TEXT_DIM, font=("Segoe UI", 8)).pack(side="left")

        f_lim_mode = tk.Frame(self._batch_specific_frame, bg=BG2)
        f_lim_mode.pack(fill="x", pady=(2, 0))
        for mv, mt in [("random", "🎲 Ngẫu nhiên"), ("sequential", "📋 Tuần tự")]:
            tk.Radiobutton(f_lim_mode, text=mt, value=mv, variable=self._batch_split_mode,
                           bg=BG2, fg=TEXT, selectcolor=BG3, activebackground=BG2,
                           font=("Segoe UI", 8), state="disabled").pack(side="left", padx=(0, 8))
        self._batch_split_mode_radios = f_lim_mode.winfo_children()

        self._batch_split_info_lbl = tk.Label(
            self._batch_specific_frame, text="",
            font=("Segoe UI", 7, "italic"), bg=BG2, fg=WARNING, wraplength=260)
        self._batch_split_info_lbl.pack(anchor="w")

        self._batch_split_n.trace_add("write", lambda *_: self._batch_on_split_toggle())
        self._batch_split_enable.trace_add("write", lambda *_: self._batch_on_split_toggle())

        tk.Label(self._batch_specific_frame,
                 text="💡 Accuracy = GT (tên folder) == class dự đoán\n"
                      "   Chuẩn hóa: bỏ 'cow'/'cows', lowercase, trim",
                 font=("Segoe UI", 7), bg=BG2, fg=TEXT_DIM,
                 justify="left", wraplength=260).pack(anchor="w", pady=(4, 0))

        # Tạo frame rỗng để không lỗi khi _on_run_mode_change gọi pack_forget
        self._pth_eval_unified_frame = tk.Frame(left, bg=BG2)

        # ── Mode hint label ────────────────────────────────────────────────
        self._mode_hint_lbl = tk.Label(
            left, text="", font=("Segoe UI", 8, "italic"),
            bg=BG2, fg=INFO, justify="left", wraplength=270)
        self._mode_hint_lbl.pack(anchor="w", pady=(6, 2))

        # ── Run button ─────────────────────────────────────────────────────
        self._eval_run_btn = tk.Button(
            left, text="▶  Chạy",
            font=("Segoe UI", 10, "bold"),
            bg=SUCCESS, fg="white", relief="flat",
            cursor="hand2", pady=8,
            command=self._run_eval_dispatch)
        self._eval_run_btn.pack(fill="x", pady=(10, 2))
        self._eval_batch_btn = self._eval_run_btn  # alias for batch thread finally block

        tk.Button(left, text="💾  Xuất kết quả JSON",
                  font=("Segoe UI", 9),
                  bg=BG3, fg=TEXT_DIM, relief="flat",
                  cursor="hand2", pady=6,
                  command=self._eval_export).pack(fill="x", pady=2)
        tk.Button(left, text="💾  Lưu phiên (EVAL_BASE_DIR/yolo)",
                  font=("Segoe UI", 9, "bold"),
                  bg=SUCCESS, fg="white", relief="flat",
                  cursor="hand2", pady=6,
                  command=self._yolo_save_session).pack(fill="x", pady=(0, 2))

        self._eval_status_lbl = tk.Label(
            left, text="⏹ Chưa chạy",
            font=("Segoe UI", 8),
            bg=BG2, fg=TEXT_DIM, wraplength=270, justify="left")
        self._eval_status_lbl.pack(anchor="w", pady=(8, 0))
        self._batch_status_lbl = self._eval_status_lbl  # alias

        # ── Task change → cập nhật hint ────────────────────────────────────
        _METRICS_HINTS = {
            "Detection":
                "📊 Val: mAP@50 · mAP@50-95 · Precision · Recall · F1\n"
                "   Batch: Đếm objects theo class",
            "Instance Segmentation":
                "📊 Val: Box + Mask mAP@50-95\n"
                "   Batch: Đếm objects theo class",
            "Classification":
                "📊 Val: Top-1 / Top-5 Accuracy (model.val())\n"
                "   Batch: Accuracy từ tên folder (tên folder = ground-truth class)",
        }
        _DEFAULTS = {
            "Classification":        {"imgsz": 224, "conf": 0.40},
            "Detection":             {"imgsz": 640, "conf": 0.25},
            "Instance Segmentation": {"imgsz": 640, "conf": 0.25},
        }
        def _on_task_change(*_):
            task = self._eval_task_var.get()
            self._eval_metrics_hint_lbl.configure(text=_METRICS_HINTS.get(task, ""))
            d = _DEFAULTS.get(task, {})
            if "imgsz" in d: self._eval_imgsz_var.set(d["imgsz"])
            if "conf"  in d: self._eval_conf_var.set(d["conf"])
        self._eval_task_var.trace_add("write", _on_task_change)
        _on_task_change()

        # ── RIGHT: shared results panel ────────────────────────────────────
        r_paned = tk.PanedWindow(right, orient="vertical", bg=BG,
                                 sashwidth=4, sashrelief="flat")
        r_paned.pack(fill="both", expand=True)

        top_half = tk.Frame(r_paned, bg=BG)
        r_paned.add(top_half, minsize=280)

        top_split = tk.PanedWindow(top_half, orient="horizontal", bg=BG,
                                   sashwidth=4, sashrelief="flat")
        top_split.pack(fill="both", expand=True)

        metrics_panel = tk.Frame(top_split, bg=BG2, padx=10, pady=8)
        top_split.add(metrics_panel, minsize=220)
        tk.Label(metrics_panel, text="📋 Kết quả đánh giá",
                 font=("Segoe UI", 10, "bold"), bg=BG2, fg=ACCENT2).pack(anchor="w", pady=(0, 6))
        self._eval_summary_frame = tk.Frame(metrics_panel, bg=BG2)
        self._eval_summary_frame.pack(fill="x", pady=(0, 6))
        self._eval_metrics_frame = tk.Frame(metrics_panel, bg=BG2)
        self._eval_metrics_frame.pack(fill="both", expand=True)
        self._eval_draw_empty_metrics()

        chart_panel = tk.Frame(top_split, bg=BG3, padx=4, pady=4)
        top_split.add(chart_panel, minsize=260)
        chart_hdr = tk.Frame(chart_panel, bg=BG3); chart_hdr.pack(fill="x")
        tk.Label(chart_hdr, text="📈 Loss / Biểu đồ kết quả",
                 font=("Segoe UI", 9, "bold"), bg=BG3, fg=ACCENT2).pack(side="left")
        tk.Button(chart_hdr, text="🔄", bg=BG3, fg=TEXT_DIM, relief="flat",
                  cursor="hand2", padx=4, font=("Segoe UI", 8),
                  command=self._eval_refresh_chart).pack(side="right")
        tk.Button(chart_hdr, text="💾", bg=BG3, fg=TEXT_DIM, relief="flat",
                  cursor="hand2", padx=4, font=("Segoe UI", 8),
                  command=self._batch_save_chart).pack(side="right")
        tk.Button(chart_hdr, text="⛶", bg=BG3, fg=TEXT_DIM, relief="flat",
                  cursor="hand2", padx=4, font=("Segoe UI", 8),
                  command=lambda: self._open_chart_fullscreen(
                      self._eval_chart_canvas, "Biểu đồ đánh giá YOLO"
                  )).pack(side="right")
        self._eval_chart_canvas = tk.Canvas(chart_panel, bg=BG4, highlightthickness=0)
        self._eval_chart_canvas.pack(fill="both", expand=True, pady=(4, 0))
        self._eval_chart_canvas.bind(
            "<Double-Button-1>",
            lambda _e: self._open_chart_fullscreen(
                self._eval_chart_canvas, "Biểu đồ đánh giá YOLO"
            ),
        )
        self._eval_chart_caption_lbl = tk.Label(
            chart_panel,
            text="Biểu đồ hiện tại: Chưa có dữ liệu biểu đồ",
            font=("Segoe UI", 8, "italic"),
            bg=BG3,
            fg=TEXT_DIM,
            anchor="w",
            justify="left",
        )
        self._eval_chart_caption_lbl.pack(fill="x", pady=(4, 0))
        self._eval_chart_tk_img  = None
        self._batch_chart_canvas = self._eval_chart_canvas  # alias for _batch_draw_chart
        self._batch_chart_tk_img = None

        bot_half = tk.Frame(r_paned, bg=BG)
        r_paned.add(bot_half, minsize=120)
        log_hdr = tk.Frame(bot_half, bg=BG); log_hdr.pack(fill="x", pady=(0, 4))
        tk.Label(log_hdr, text="📝 Log",
                 font=("Segoe UI", 8, "bold"), bg=BG, fg=TEXT_DIM).pack(side="left", padx=6)
        tk.Button(log_hdr, text="🗑 Xóa log", bg=BG3, fg=TEXT_DIM, relief="flat",
                  cursor="hand2", padx=8, font=("Segoe UI", 8),
                  command=lambda: (
                      self._eval_log_box.configure(state="normal"),
                      self._eval_log_box.delete("1.0", "end"),
                      self._eval_log_box.configure(state="disabled"),
                  )).pack(side="right", padx=4)
        self._eval_log_box = _st.ScrolledText(
            bot_half,
            relief="flat",
            font=("Cascadia Code", 8),
            wrap="word",
            state="disabled",
            height=8,
        )
        apply_textbox_theme(self._eval_log_box, dark=True)
        self._eval_log_box.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        for tag, fg_c in [("ok", "#22c55e"), ("warn", "#f59e0b"),
                           ("err", "#ef4444"), ("info", "#38bdf8")]:
            self._eval_log_box.tag_config(tag, foreground=fg_c)
        self._batch_log_box = self._eval_log_box  # alias for _batch_log

        # ── Benchmark panel ────────────────────────────────────────────────
        hdr_b = tk.Frame(bench_frame, bg=BG3, pady=5)
        hdr_b.pack(fill="x")
        tk.Label(hdr_b, text="📚 So sánh với Bài Báo Quốc Tế",
                 font=("Segoe UI", 10, "bold"), bg=BG3, fg=ACCENT2).pack(side="left", padx=10)
        tk.Label(hdr_b, text="(cập nhật tự động sau mỗi lần chạy)",
                 font=("Segoe UI", 8, "italic"), bg=BG3, fg=TEXT_DIM).pack(side="left")
        tk.Label(hdr_b, text="So sánh với:", font=("Segoe UI", 8, "bold"),
                 bg=BG3, fg=TEXT).pack(side="left", padx=(12, 4))
        bench_ref_cb = ttk.Combobox(hdr_b, textvariable=self._bench_reference_var,
                                    values=["JILSA 2022", "PLOS ONE 2024"], width=16,
                                    state="readonly", font=("Segoe UI", 8))
        bench_ref_cb.pack(side="left")
        bench_ref_cb.bind(
            "<<ComboboxSelected>>",
            lambda _e: (self._bench_build_reference_table(), self._bench_draw_chart(None)),
        )
        tk.Button(hdr_b, text="💾 Lưu chart", bg=BG2, fg=ACCENT2, relief="flat",
                  cursor="hand2", padx=8, font=("Segoe UI", 8),
                  command=self._bench_save_chart).pack(side="right", padx=8)
        body_b = tk.Frame(bench_frame, bg=BG2)
        body_b.pack(fill="both", expand=True)

        # ── Left+Right split via PanedWindow (kéo sash để mở rộng bảng) ──
        _bench_paned = tk.PanedWindow(body_b, orient="horizontal", bg=BG3,
                                      sashwidth=5, sashrelief="flat",
                                      handlesize=6)
        _bench_paned.pack(fill="both", expand=True, padx=4, pady=4)

        # ── Left: scrollable table ──────────────────────────────────────
        tbl_outer = tk.Frame(_bench_paned, bg=BG2)
        _bench_paned.add(tbl_outer, minsize=200, width=360, stretch="never")

        _tbl_vsb = tk.Scrollbar(tbl_outer, orient="vertical", bg=BG3,
                                troughcolor=BG2, relief="flat", width=8)
        _tbl_vsb.pack(side="right", fill="y")
        _tbl_canvas = tk.Canvas(tbl_outer, bg=BG2, highlightthickness=0,
                                yscrollcommand=_tbl_vsb.set)
        _tbl_canvas.pack(side="left", fill="both", expand=True)
        _tbl_vsb.config(command=_tbl_canvas.yview)

        tbl_frame = tk.Frame(_tbl_canvas, bg=BG2)
        _tbl_win  = _tbl_canvas.create_window((0, 0), window=tbl_frame, anchor="nw")

        def _tbl_on_configure(e):
            _tbl_canvas.configure(scrollregion=_tbl_canvas.bbox("all"))
            _tbl_canvas.itemconfig(_tbl_win, width=_tbl_canvas.winfo_width())
        tbl_frame.bind("<Configure>", _tbl_on_configure)
        _tbl_canvas.bind("<Configure>",
            lambda e: _tbl_canvas.itemconfig(_tbl_win, width=e.width))

        def _tbl_mousewheel(e):
            _tbl_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        _tbl_canvas.bind_all("<MouseWheel>", _tbl_mousewheel)

        self._bench_table_frame = tbl_frame
        self._bench_build_reference_table()

        # ── Right: chart canvas ─────────────────────────────────────────
        chart_f = tk.Frame(_bench_paned, bg=BG4)
        _bench_paned.add(chart_f, minsize=200, stretch="always")
        self._bench_canvas = tk.Canvas(chart_f, bg=BG4, highlightthickness=0)
        self._bench_canvas.pack(fill="both", expand=True)
        self._bench_chart_caption_lbl = tk.Label(
            chart_f,
            text="Biểu đồ hiện tại: So sánh benchmark chưa được tạo",
            font=("Segoe UI", 8, "italic"),
            bg=BG4,
            fg=TEXT_DIM,
            anchor="w",
            justify="left",
        )
        self._bench_chart_caption_lbl.pack(fill="x", padx=8, pady=(4, 6))
        self._bench_canvas.create_text(
            200, 100,
            text="📊 Chạy để xem so sánh với bài báo",
            fill=TEXT_DIM, font=("Segoe UI", 9), justify="center")
        self._bench_tk_img = None

        # ── Initial mode display ───────────────────────────────────────────
        self._on_run_mode_change()

    def _auto_detect_eval_mode(self):
        """Tự nhận dạng loại model từ đuôi file và cập nhật badge — không override mode đã chọn."""
        path = self._eval_model_dir.get().strip()
        ext = Path(path).suffix.lower() if path else ""
        try:
            # Chỉ set default mode khi user chưa chọn gì (mode vẫn là mặc định)
            if self._run_mode_var.get() not in ("val", "batch"):
                self._run_mode_var.set("val")
            if ext == ".pt":
                self._eval_detected_type_lbl.configure(
                    text="  YOLO (.pt) — mAP, P, R, F1 / Batch Accuracy",
                    fg=SUCCESS)
                self._eval_detected_badge.configure(
                    text="🏅 YOLO", fg=SUCCESS)
                self._yolo_submode_frame.pack(fill="x", pady=(2, 0))
            elif ext:
                self._eval_detected_type_lbl.configure(
                    text=f"  {ext} không hỗ trợ ở màn này",
                    fg=WARNING)
                self._eval_detected_badge.configure(text="⚠", fg=WARNING)
                self._yolo_submode_frame.pack_forget()
            elif path == "":
                self._eval_detected_type_lbl.configure(
                    text="  (chưa chọn file)", fg=TEXT_DIM)
                self._eval_detected_badge.configure(text="", fg=TEXT_DIM)
                self._yolo_submode_frame.pack_forget()
        except Exception:
            pass
        self._on_run_mode_change()

    def _on_run_mode_change(self):
        """Toggle UI cho từng mode đánh giá YOLO."""
        try:
            mode = self._run_mode_var.get()
            self._pth_eval_unified_frame.pack_forget()
            if mode == "batch":
                self._val_specific_frame.pack_forget()
                self._batch_specific_frame.pack(fill="x", pady=(4, 2))
                self._eval_run_btn.configure(text="▶  Chạy Batch Accuracy", bg=WARNING)
                self._eval_data_hint_lbl.configure(
                    text="Batch: Thư mục gốc chứa sub-folder theo tên class"
                )
                self._mode_hint_lbl.configure(
                    text="💡 Mỗi sub-folder = 1 class GT\n"
                         "   Accuracy = predicted_class == folder_name"
                )
            else:  # "val"
                self._batch_specific_frame.pack_forget()
                self._val_specific_frame.pack(fill="x", pady=(4, 2))
                self._eval_run_btn.configure(text="▶  Chạy Đánh giá YOLO", bg=SUCCESS)
                self._eval_data_hint_lbl.configure(
                    text="Val: YAML (detect/seg) hoặc thư mục class/ (classify)"
                )
                self._mode_hint_lbl.configure(
                    text="💡 Dùng model.val() → mAP, P, R, F1\n"
                         "   Classification: tự tính Top-1/Top-5 Accuracy"
                )
        except Exception:
            pass  # widgets not yet built

    def _restore_eval_primary_button(self):
        btn = getattr(self, "_eval_run_btn", None)
        if btn is None:
            return
        try:
            btn.configure(state="normal")
        except Exception:
            return
        try:
            self._on_run_mode_change()
        except Exception:
            try:
                btn.configure(text="▶  Chạy Đánh giá YOLO", bg=SUCCESS)
            except Exception:
                pass

    def _run_eval_dispatch(self):
        """Dispatch theo mode được chọn (val hoặc batch accuracy)."""
        mode = self._run_mode_var.get()
        if mode == "batch":
            self._run_batch_accuracy()
        else:
            self._run_official_val()

    def _run_official_val(self):
        """Đánh giá chính thức dùng model.val() (gọi _eval_run)."""
        self._eval_run()

    def _run_batch_accuracy(self):
        """Batch Predict + Accuracy từ tên folder — không dùng messagebox popup."""
        if self._eval_running:
            messagebox.showinfo("⏳", "Đang chạy, vui lòng đợi.")
            return

        model_input = self._eval_model_dir.get().strip()
        data_path   = self._eval_data_path.get().strip()

        if not model_input or not data_path:
            messagebox.showerror("Thiếu thông tin",
                "Vui lòng chọn Model và Thư mục ảnh.")
            return
        if not Path(data_path).exists():
            messagebox.showerror("Lỗi", f"Đường dẫn không tồn tại:\n{data_path}")
            return

        # Resolve model path
        model_path = None
        p = Path(model_input)
        if p.is_file() and p.suffix.lower() in (".pt", ".onnx"):
            model_path = str(p)
        else:
            for cand in [p / "weights" / "best.pt", p / "weights" / "last.pt",
                         p / "best.pt", p / "last.pt"]:
                if cand.is_file():
                    model_path = str(cand); break
            if model_path is None:
                for ext in ("*.pt", "*.onnx"):
                    found = list(p.rglob(ext))
                    if found:
                        model_path = str(found[0]); break
        if model_path is None:
            messagebox.showerror("Không tìm thấy model",
                "Không tìm thấy file .pt/.onnx.\n"
                "Chọn trực tiếp file (nút 📄) hoặc thư mục weights/ (nút 📁).")
            return

        self._eval_running = True
        self._eval_run_btn.configure(state="disabled", text="⏳ Đang chạy...")
        self._eval_set_status("⏳ Batch + Accuracy đang chạy...", WARNING)
        self._eval_log_box.configure(state="normal")
        self._eval_log_box.delete("1.0", "end")
        self._eval_log_box.configure(state="disabled")

        threading.Thread(
            target=self._run_batch_accuracy_thread,
            args=(model_path, data_path),
            daemon=True,
        ).start()

    @staticmethod
    def _normalize_class_name(name: str) -> str:
        """Chuẩn hóa tên class để so sánh chính xác nhưng robust.
        Loại bỏ hậu tố 'cows'/'cow', chuẩn hóa separator, lowercase.
        Ví dụ: 'lumpyskin_cows' → 'lumpyskin', 'healthy cow' → 'healthy'.
        """
        name = name.lower().strip()
        name = name.replace("cows", "").replace("cow", "")
        name = name.replace("_", " ").replace("-", " ")
        return " ".join(name.split())  # collapse extra spaces

    def _eval_parse_class_filters(self) -> list[str]:
        raw = self._eval_class_filter_var.get().strip()
        if not raw:
            return []
        parts = raw.replace(";", ",").replace("|", ",").split(",")
        values = []
        for part in parts:
            norm = self._normalize_class_name(part)
            if norm and norm not in values:
                values.append(norm)
        return values

    @staticmethod
    def _eval_try_link_or_copy(src: Path, dst: Path):
        import shutil

        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            if dst.exists():
                return
            os.link(src, dst)
            return
        except Exception:
            pass
        shutil.copy2(src, dst)

    def _eval_prepare_classification_dataset(self, data_path: str, split: str) -> tuple[str, Path | None, dict]:
        import random as _rng
        import tempfile
        import shutil
        import subprocess as _sp
        from collections import defaultdict

        src_root = Path(data_path)
        if not src_root.is_dir():
            return data_path, None, {"mode": "direct"}

        split_dirs = {
            d.name.lower(): d for d in src_root.iterdir()
            if d.is_dir() and d.name.lower() in {"train", "val", "test"}
        }
        if split_dirs:
            source_split_dir = split_dirs.get(split.lower()) or split_dirs.get("val") or next(iter(split_dirs.values()))
            is_flat = False
        else:
            source_split_dir = src_root
            is_flat = True

        class_dirs = sorted([d for d in source_split_dir.iterdir() if d.is_dir()])
        if not class_dirs:
            raise FileNotFoundError(f"Không tìm thấy folder class trong: {source_split_dir}")

        wanted_classes = set(self._eval_parse_class_filters())
        if wanted_classes:
            filtered_dirs = [
                d for d in class_dirs
                if self._normalize_class_name(d.name) in wanted_classes
            ]
            if not filtered_dirs:
                raise FileNotFoundError(
                    "Không có class nào khớp bộ lọc: "
                    + ", ".join(sorted(wanted_classes))
                )
            class_dirs = filtered_dirs

        all_entries = []
        per_class_total = {}
        for class_dir in class_dirs:
            images = sorted([
                p for p in class_dir.rglob("*")
                if p.is_file() and p.suffix.lower() in {e.lower() for e in self._IMG_EXTS}
            ])
            if images:
                per_class_total[class_dir.name] = len(images)
                all_entries.extend((class_dir.name, img) for img in images)

        if not all_entries:
            raise FileNotFoundError(f"Không tìm thấy ảnh trong: {source_split_dir}")

        limit = max(0, int(self._eval_limit_var.get() or 0))
        mode = self._eval_limit_mode_var.get()
        filter_active = bool(wanted_classes)

        if is_flat and limit == 0 and not filter_active:
            temp_root = Path(tempfile.mkdtemp(prefix="_yolo_cls_eval_"))
            for split_name in ("train", "val", "test"):
                dst = temp_root / split_name
                ret = _sp.run(
                    ["cmd", "/c", "mklink", "/J", str(dst), str(source_split_dir.resolve())],
                    capture_output=True, text=True,
                )
                if ret.returncode != 0:
                    dst.mkdir(parents=True, exist_ok=True)
                    for class_dir in class_dirs:
                        linked = dst / class_dir.name
                        try:
                            linked.symlink_to(class_dir.resolve(), target_is_directory=True)
                        except Exception:
                            shutil.copytree(class_dir, linked, dirs_exist_ok=True)
            return str(temp_root), temp_root, {
                "mode": "linked-flat",
                "selected_images": len(all_entries),
                "total_images": len(all_entries),
                "classes": [d.name for d in class_dirs],
            }

        selected_entries = list(all_entries)
        if limit > 0 and len(selected_entries) > limit:
            if mode == "random":
                selected_entries = sorted(_rng.sample(selected_entries, limit), key=lambda item: str(item[1]))
            else:
                selected_entries = selected_entries[:limit]

        selected_map = defaultdict(list)
        for class_name, img_path in selected_entries:
            selected_map[class_name].append(img_path)

        temp_root = Path(tempfile.mkdtemp(prefix="_yolo_cls_eval_"))
        for split_name in ("train", "val", "test"):
            split_root = temp_root / split_name
            for class_name, img_paths in selected_map.items():
                class_root = split_root / class_name
                class_root.mkdir(parents=True, exist_ok=True)
                for idx, img_path in enumerate(img_paths, start=1):
                    target = class_root / f"{idx:06d}{img_path.suffix.lower()}"
                    self._eval_try_link_or_copy(img_path, target)

        return str(temp_root), temp_root, {
            "mode": "subset",
            "selected_images": len(selected_entries),
            "total_images": len(all_entries),
            "classes": sorted(selected_map.keys()),
            "per_class_total": per_class_total,
        }

    def _eval_collect_classification_metrics(
        self,
        model,
        prepared_data_path: str,
        split: str,
        imgsz: int,
        device: str,
        half: bool,
    ) -> dict:
        from collections import Counter

        split_root = Path(prepared_data_path) / split
        if not split_root.is_dir():
            split_root = Path(prepared_data_path)
        class_dirs = sorted([d for d in split_root.iterdir() if d.is_dir()])
        if not class_dirs:
            raise FileNotFoundError(f"Khong tim thay folder class trong: {split_root}")

        image_items = []
        for class_dir in class_dirs:
            for img_path in sorted(class_dir.rglob("*")):
                if img_path.is_file() and img_path.suffix.lower() in {e.lower() for e in self._IMG_EXTS}:
                    image_items.append((class_dir.name, img_path))
        if not image_items:
            raise FileNotFoundError(f"Khong tim thay anh de danh gia trong: {split_root}")

        dataset_classes = [d.name for d in class_dirs]
        norm_to_dataset = {self._normalize_class_name(name): name for name in dataset_classes}
        predicted_names = []

        batch_size = min(32, max(1, len(image_items)))
        for start in range(0, len(image_items), batch_size):
            batch_items = image_items[start:start + batch_size]
            sources = [str(path) for _, path in batch_items]
            results = model.predict(
                source=sources,
                imgsz=imgsz,
                device=device,
                half=half,
                verbose=False,
                stream=False,
            )
            for result in results:
                probs = getattr(result, "probs", None)
                if probs is None:
                    predicted_names.append("unknown")
                    continue
                top1 = getattr(probs, "top1", None)
                names = getattr(result, "names", {}) or getattr(model, "names", {}) or {}
                pred_name = names.get(int(top1), str(top1)) if top1 is not None else "unknown"
                predicted_names.append(str(pred_name))

        if len(predicted_names) != len(image_items):
            raise RuntimeError("So luong prediction khong khop voi so anh danh gia.")

        extra_pred_names = []
        for pred_name in predicted_names:
            pred_norm = self._normalize_class_name(pred_name)
            if pred_norm not in norm_to_dataset and pred_name not in extra_pred_names:
                extra_pred_names.append(pred_name)
        class_names = dataset_classes + extra_pred_names
        name_to_idx = {name: idx for idx, name in enumerate(class_names)}

        y_true = []
        y_pred = []
        for (true_name, _), pred_name in zip(image_items, predicted_names):
            pred_norm = self._normalize_class_name(pred_name)
            pred_label = norm_to_dataset.get(pred_norm, pred_name)
            y_true.append(name_to_idx[true_name])
            y_pred.append(name_to_idx[pred_label])

        try:
            from sklearn.metrics import confusion_matrix, precision_recall_fscore_support

            label_ids = list(range(len(class_names)))
            cm = confusion_matrix(y_true, y_pred, labels=label_ids)
            prec, rec, f1, support = precision_recall_fscore_support(
                y_true, y_pred, labels=label_ids, average=None, zero_division=0
            )
            macro_prec, macro_rec, macro_f1, _ = precision_recall_fscore_support(
                y_true, y_pred, labels=label_ids, average="macro", zero_division=0
            )
            weighted_prec, weighted_rec, weighted_f1, _ = precision_recall_fscore_support(
                y_true, y_pred, labels=label_ids, average="weighted", zero_division=0
            )
        except Exception:
            n_cls = len(class_names)
            cm = [[0 for _ in range(n_cls)] for _ in range(n_cls)]
            for gt_idx, pred_idx in zip(y_true, y_pred):
                cm[gt_idx][pred_idx] += 1
            prec, rec, f1, support = [], [], [], []
            for idx in range(n_cls):
                tp = cm[idx][idx]
                fp = sum(cm[row][idx] for row in range(n_cls) if row != idx)
                fn = sum(cm[idx][col] for col in range(n_cls) if col != idx)
                sup = sum(cm[idx])
                p_val = tp / (tp + fp) if (tp + fp) else 0.0
                r_val = tp / (tp + fn) if (tp + fn) else 0.0
                f1_val = 2 * p_val * r_val / (p_val + r_val) if (p_val + r_val) else 0.0
                prec.append(p_val)
                rec.append(r_val)
                f1.append(f1_val)
                support.append(sup)
            macro_prec = sum(prec) / max(len(prec), 1)
            macro_rec = sum(rec) / max(len(rec), 1)
            macro_f1 = sum(f1) / max(len(f1), 1)
            total_support = max(sum(support), 1)
            weighted_prec = sum(p * s for p, s in zip(prec, support)) / total_support
            weighted_rec = sum(r * s for r, s in zip(rec, support)) / total_support
            weighted_f1 = sum(fv * s for fv, s in zip(f1, support)) / total_support

        if hasattr(cm, "tolist"):
            cm_list = cm.tolist()
        else:
            cm_list = cm

        total = len(y_true)
        correct = sum(int(gt == pred) for gt, pred in zip(y_true, y_pred))
        per_class_metrics = []
        for idx, class_name in enumerate(class_names):
            sup = int(support[idx]) if idx < len(support) else sum(cm_list[idx])
            correct_cls = cm_list[idx][idx]
            acc_cls = correct_cls / sup if sup else 0.0
            per_class_metrics.append({
                "class_name": class_name,
                "support": sup,
                "correct": int(correct_cls),
                "accuracy": float(acc_cls),
                "precision": float(prec[idx]),
                "recall": float(rec[idx]),
                "f1": float(f1[idx]),
            })

        pred_counter = Counter(class_names[pred_idx] for pred_idx in y_pred)
        return {
            "class_names": class_names,
            "confusion_matrix": cm_list,
            "per_class_metrics": per_class_metrics,
            "overall_accuracy": correct / max(total, 1),
            "macro_precision": float(macro_prec),
            "macro_recall": float(macro_rec),
            "macro_f1": float(macro_f1),
            "weighted_precision": float(weighted_prec),
            "weighted_recall": float(weighted_rec),
            "weighted_f1": float(weighted_f1),
            "total_images": total,
            "prediction_distribution": dict(pred_counter),
        }

    def _eval_log_classification_metrics(self, analysis: dict):
        per_class = analysis.get("per_class_metrics") or []
        if not per_class:
            return
        self._eval_log("", "")
        self._eval_log("[REPORT] Per-class metrics", "info")
        self._eval_log("  " + "-" * 104, "info")
        self._eval_log(
            "  {0:<22} {1:>8} {2:>10} {3:>10} {4:>10} {5:>10}".format(
                "Class", "Support", "Precision", "Recall", "F1", "Acc"
            ),
            "info",
        )
        self._eval_log("  " + "-" * 104, "info")
        for item in per_class:
            self._eval_log(
                "  {0:<22} {1:>8} {2:>10.4f} {3:>10.4f} {4:>10.4f} {5:>10.4f}".format(
                    str(item["class_name"])[:22],
                    int(item["support"]),
                    float(item["precision"]),
                    float(item["recall"]),
                    float(item["f1"]),
                    float(item["accuracy"]),
                ),
                "dim",
            )
        self._eval_log("  " + "-" * 104, "info")
        self._eval_log(
            "  Macro: P={0:.4f}  R={1:.4f}  F1={2:.4f} | Weighted F1={3:.4f}".format(
                float(analysis.get("macro_precision", 0.0)),
                float(analysis.get("macro_recall", 0.0)),
                float(analysis.get("macro_f1", 0.0)),
                float(analysis.get("weighted_f1", 0.0)),
            ),
            "ok",
        )

    @staticmethod
    def _get_model_stats(model, imgsz: int = 640) -> tuple:
        """Trả về (params_m: float|None, gflops: float|None).

        - params_m: đếm trực tiếp qua numel() → luôn chính xác.
        - gflops: capture stdout từ model.model.info(verbose=True) rồi parse
          regex vì ultralytics mới trả về None thay vì tuple.
          Fallback thứ 2: dùng thop nếu có.
        """
        import io as _io, sys as _sys, re as _re

        params_m: float | None = None
        gflops:   float | None = None

        # ── Params: đếm numel() ───────────────────────────────────────────
        try:
            params_m = sum(p.numel() for p in model.model.parameters()) / 1e6
        except Exception:
            pass

        # ── GFLOPs tầng 1: capture stdout của model.model.info() ─────────
        try:
            buf      = _io.StringIO()
            old_out  = _sys.stdout
            _sys.stdout = buf
            try:
                model.model.info(imgsz=imgsz, verbose=True)
            finally:
                _sys.stdout = old_out
            out = buf.getvalue()
            m = _re.search(r"([\d.]+)\s+GFLOPs", out)
            if m:
                gflops = float(m.group(1))
        except Exception:
            pass

        # ── GFLOPs tầng 2: thop (nếu tầng 1 thất bại) ───────────────────
        if gflops is None:
            try:
                import torch as _torch
                from thop import profile as _thop_profile
                dummy = _torch.zeros(1, 3, imgsz, imgsz,
                                     device=next(model.model.parameters()).device)
                macs, _ = _thop_profile(model.model, inputs=(dummy,), verbose=False)
                gflops = macs * 2 / 1e9
            except Exception:
                pass

        return params_m, gflops

    @staticmethod
    def _build_pth_model_from_state_dict(state_dict: dict):
        import torch.nn as nn
        from torchvision import models as _tv_models

        use_mobilenet = any("features.0.0.weight" in k for k in state_dict.keys())
        num_classes = None
        for key, value in state_dict.items():
            if not hasattr(value, "shape"):
                continue
            if key.endswith("classifier.4.weight") and len(value.shape) >= 1:
                num_classes = int(value.shape[0])
                break
        if num_classes is None:
            for key, value in state_dict.items():
                if not hasattr(value, "shape"):
                    continue
                if key.endswith("classifier.1.weight") and len(value.shape) >= 1:
                    num_classes = int(value.shape[0])
                    break
        if num_classes is None:
            num_classes = 2

        if use_mobilenet:
            model = _tv_models.mobilenet_v2(weights=None)
            model.classifier = nn.Sequential(
                nn.Dropout(p=0.2),
                nn.Linear(model.last_channel, 128),
                nn.ReLU(inplace=True),
                nn.Dropout(p=0.2),
                nn.Linear(128, num_classes),
            )
            arch_name = "MobileNetV2 (PLOS ONE 2024)"
        else:
            class _CustomCNN(nn.Module):
                def __init__(self, nc):
                    super().__init__()
                    self.features = nn.Sequential(
                        nn.Conv2d(3, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(True), nn.MaxPool2d(2),
                        nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(True), nn.MaxPool2d(2),
                        nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(True), nn.MaxPool2d(2),
                        nn.Conv2d(128, 256, 3, padding=1), nn.BatchNorm2d(256), nn.ReLU(True), nn.MaxPool2d(2),
                        nn.AdaptiveAvgPool2d((9, 9)),
                    )
                    self.classifier = nn.Sequential(
                        nn.Flatten(),
                        nn.Linear(256 * 9 * 9, 512),
                        nn.ReLU(True),
                        nn.Dropout(0.5),
                        nn.Linear(512, nc),
                    )

                def forward(self, x):
                    return self.classifier(self.features(x))

            model = _CustomCNN(num_classes)
            arch_name = "CustomCNN (JILSA 2022)"

        model.load_state_dict(state_dict, strict=False)
        model.eval()
        return model, arch_name

    def _get_pth_checkpoint_stats(self, model_path: str, imgsz: int):
        import torch

        try:
            ckpt = torch.load(model_path, map_location="cpu", weights_only=True)
        except Exception:
            ckpt = torch.load(model_path, map_location="cpu", weights_only=False)
        state_dict = ckpt.get("model_weights") if isinstance(ckpt, dict) and "model_weights" in ckpt else ckpt
        if not isinstance(state_dict, dict):
            return {"params": None, "params_m": None, "gflops": None, "arch": None}

        model, arch_name = self._build_pth_model_from_state_dict(state_dict)
        params = sum(p.numel() for p in model.parameters())
        gflops = None
        try:
            _ensure_packages("thop")
            from thop import profile as _thop_profile
            dummy = torch.zeros(1, 3, imgsz, imgsz)
            macs, _ = _thop_profile(model, inputs=(dummy,), verbose=False)
            gflops = macs * 2 / 1e9
        except Exception:
            gflops = None
        return {
            "params": params,
            "params_m": (params / 1e6) if params is not None else None,
            "gflops": gflops,
            "arch": arch_name,
        }

    def _draw_pth_history_on_eval_canvas(self, history: list | None, summary_metrics: dict | None = None):
        history = history or []
        summary_metrics = summary_metrics or {}
        epochs = []
        series = {}

        def _push(name, value):
            if name not in series:
                series[name] = []
            series[name].append(value if value is not None else float("nan"))

        for idx, item in enumerate(history, start=1):
            epoch = self._safe_float_or_none(item.get("epoch") if isinstance(item, dict) else None)
            epochs.append(int(epoch or idx))
            if isinstance(item, dict):
                _push("train_loss", self._safe_float_or_none(item.get("train_loss")))
                _push("val_loss", self._safe_float_or_none(item.get("val_loss")))
                _push("val_acc", self._safe_float_or_none(item.get("val_acc")))

        if not epochs:
            epochs = [1]
            _push("val_loss", self._safe_float_or_none(summary_metrics.get("val_loss")))
            _push("accuracy", self._safe_float_or_none(summary_metrics.get("accuracy")))
            _push("macro_f1", self._safe_float_or_none(summary_metrics.get("macro_f1")))

        plot_cols = [name for name, vals in series.items() if any(v == v for v in vals)]
        if not plot_cols:
            self._eval_draw_no_chart()
            return
        self.after(0, self._eval_draw_chart, epochs, series, plot_cols)

    def _unified_refresh_count(self):
        """Đếm ảnh trong _eval_data_path và cập nhật _batch_img_count_lbl."""
        path = self._eval_data_path.get().strip()
        if not path or not Path(path).is_dir():
            try:
                self._batch_img_count_lbl.configure(
                    text="📊 (chưa chọn thư mục)", fg=TEXT_DIM)
            except Exception:
                pass
            self._batch_img_total.set(0)
            return
        imgs = [f for f in Path(path).rglob("*")
                if f.suffix.lower() in {e.lower() for e in self._IMG_EXTS}]
        n = len(imgs)
        self._batch_img_total.set(n)
        try:
            if n == 0:
                self._batch_img_count_lbl.configure(
                    text="⚠ Không tìm thấy ảnh", fg=WARNING)
            else:
                self._batch_img_count_lbl.configure(
                    text=f"📊 Tìm thấy  {n}  ảnh", fg=SUCCESS)
                if self._batch_split_n.get() > n:
                    self._batch_split_n.set(n)
                try:
                    self._batch_split_n_spin.configure(to=n)
                except Exception:
                    pass
        except Exception:
            pass
        self._batch_on_split_toggle()

    def _run_batch_accuracy_thread(self, model_path: str, data_path: str):
        """Thread: model.predict() + Accuracy từ tên folder (ground truth).

        Accuracy được tính bằng cách so sánh chính xác tên class từ tên thư mục
        (ground truth) với class dự đoán cao nhất của model, sau khi chuẩn hóa
        (bỏ hậu tố 'cow'/'cows', lowercase, collapse whitespace).
        """
        import traceback as _tb, random as _rng
        from collections import defaultdict

        task_map   = {"Detection":             "detect",
                      "Instance Segmentation": "segment",
                      "Classification":        "classify"}
        task_label = self._eval_task_var.get()
        task       = task_map.get(task_label, "classify")
        imgsz      = self._eval_imgsz_var.get()
        device     = self._eval_device_var.get()
        conf       = self._eval_conf_var.get()
        half       = self._eval_half_var.get()
        output_dir = self._batch_output_dir.get().strip()

        self._eval_log(f"[→] Model   : {model_path}", "info")
        self._eval_log(f"[→] Dataset : {data_path}", "info")
        self._eval_log(
            f"[→] Task={task}  imgsz={imgsz}  conf={conf}  device={device}", "info")

        # ── Thu thập ảnh ──────────────────────────────────────────────────
        dp = Path(data_path)
        if dp.is_file():
            all_imgs = [str(dp)]
        else:
            all_imgs = [str(f) for f in dp.rglob("*")
                        if f.suffix.lower() in {e.lower() for e in self._IMG_EXTS}]

        if not all_imgs:
            self._eval_log("[✗] Không tìm thấy ảnh trong thư mục.", "err")
            self._eval_set_status("✗ Không tìm thấy ảnh", DANGER)
            self._eval_running = False
            self.after(0, self._restore_eval_primary_button)
            return

        # Optional limit
        if self._batch_split_enable.get():
            limit  = min(self._batch_split_n.get(), len(all_imgs))
            source = (_rng.sample(all_imgs, limit)
                      if self._batch_split_mode.get() == "random"
                      else all_imgs[:limit])
        else:
            source = all_imgs

        n = len(source)
        self._eval_log(f"[→] Xử lý {n}/{len(all_imgs)} ảnh", "info")

        try:
            _ensure_packages("ultralytics")
            YOLO  = _import_yolo()
            model = YOLO(model_path, task=task)
            self._eval_log(f"[✔] Model tải xong: {Path(model_path).name}", "ok")

            # ── Auto-correct task từ model thực tế ───────────────────────
            _model_task = getattr(model, "task", None) or task
            if _model_task != task:
                self._eval_log(
                    f"[⚠] Task dropdown='{task}' nhưng model.task='{_model_task}'"
                    f" → dùng '{_model_task}' để đảm bảo kết quả đúng", "warn")
                task = _model_task
            self._eval_log(f"[→] Task thực tế: {task}", "info")

            # ── Thông số model để so sánh bài báo ─────────────────────────
            _params_m, _gflops = self._get_model_stats(model, imgsz)
            if _params_m is not None:
                self._eval_log(f"[ℹ] Params: {_params_m:.4f} M  |  GFLOPs: {_gflops if _gflops is not None else 'N/A'}", "info")

            predict_kwargs = dict(
                source=source, imgsz=imgsz, device=device,
                half=half, save=True, verbose=False,
            )
            if output_dir:
                predict_kwargs["project"] = output_dir
            if task != "classify":
                predict_kwargs["conf"]     = conf
                predict_kwargs["save_txt"] = True

            self._eval_log("[→] Đang chạy predict...", "info")
            results  = model.predict(**predict_kwargs)
            save_dir = Path(getattr(results[0], "save_dir", "") if results else "")
            self._eval_log(f"[✔] Predict xong — {len(results)} ảnh", "ok")

            # ══════════════════════════════════════════════════════════════
            # CLASSIFICATION — Accuracy từ tên folder (ground truth)
            # ══════════════════════════════════════════════════════════════
            if task == "classify":
                # ── Pre-check: kiểm tra cấu trúc thư mục ─────────────────
                gt_folders = {Path(p).parent.name.strip() for p in source}
                model_cls_norms = {self._normalize_class_name(v)
                                   for v in model.names.values()}
                gt_norms   = {self._normalize_class_name(g) for g in gt_folders
                              if g}  # bỏ rỗng
                no_subfolder = "" in gt_folders or len(gt_folders) == 1 and \
                               next(iter(gt_folders)) == Path(data_path).name
                if not gt_norms:
                    self._eval_log(
                        "⚠  KHÔNG THỂ ĐO ACCURACY: ảnh không được đặt trong thư mục"
                        " con đặt tên theo class.\n"
                        "   Cấu trúc cần có:\n"
                        "     test_folder/\n"
                        "       TênClass1/  ← tên thư mục = ground truth\n"
                        "         img1.jpg\n"
                        "       TênClass2/\n"
                        "         img2.jpg", "warn")
                else:
                    unmatched = gt_norms - model_cls_norms
                    if unmatched:
                        self._eval_log(
                            f"⚠  Tên folder GT không khớp model.names:", "warn")
                        for u in sorted(unmatched):
                            self._eval_log(f"     '{u}' không có trong {sorted(model_cls_norms)}", "warn")
                    self._eval_log(
                        f"[✔] Class GT: {sorted(gt_folders - {''})} | Model names: {list(model.names.values())}", "info")

                self._eval_log("", "")
                self._eval_log(
                    f"  {'#':>4}  {'Ảnh':<28}  {'GT (folder)':<20}  {'Dự đoán':<20}"
                    f"  Top1    OK?", "info")
                self._eval_log("  " + "─" * 90, "info")

                correct   = total_acc = 0
                cls_stats: dict = defaultdict(lambda: {"correct": 0, "total": 0})
                mismatches: list = []

                # NOTE: ultralytics trả r.path = "image0.jpg" khi source là list
                # → phải dùng source[i] để lấy path gốc
                for idx, (r, orig_path) in enumerate(zip(results, source), 1):
                    if r.probs is None:
                        self._eval_log(
                            f"  {idx:>4}  {Path(orig_path).name:<28}  r.probs=None (wrong task?)", "warn")
                        continue
                    pred_id   = int(r.probs.top1)
                    pred_name = str(r.names.get(pred_id, f"cls{pred_id}")).strip()
                    true_name = Path(orig_path).parent.name.strip()
                    top1_conf = (float(r.probs.top1conf)
                                 if hasattr(r.probs, "top1conf") else 0.0)
                    img_name  = Path(orig_path).name

                    # ── So sánh: ưu tiên exact (lowercase), fallback normalize ──
                    pred_lower = pred_name.lower()
                    true_lower = true_name.lower()
                    is_correct = (pred_lower == true_lower)
                    if not is_correct:
                        pred_norm = self._normalize_class_name(pred_lower)
                        true_norm = self._normalize_class_name(true_lower)
                        is_correct = (pred_norm == true_norm)

                    total_acc += 1
                    cls_stats[true_lower]["total"] += 1
                    if is_correct:
                        correct += 1
                        cls_stats[true_lower]["correct"] += 1
                        flag = "✅"
                    else:
                        mismatches.append((true_name, pred_name, img_name))
                        flag = "❌"

                    self._eval_log(
                        f"  {idx:>4}  {img_name:<28}  {true_name:<20}"
                        f"  {pred_name:<20}  {top1_conf:5.1%}   {flag}",
                        "ok" if is_correct else "err")

                accuracy = (correct / total_acc * 100) if total_acc > 0 else 0.0
                self._eval_log("═" * 92, "ok")
                if total_acc == 0:
                    self._eval_log(
                        "  ⚠ KHÔNG ĐO ĐƯỢC ACCURACY: r.probs=None cho tất cả ảnh.", "err")
                    self._eval_log(
                        "  → Kiểm tra lại Task (cần chọn 'Classification')", "err")
                    self._eval_log(
                        "  → Và model phải là YOLO Classification (.pt-classify)", "err")
                else:
                    self._eval_log(
                        f"  🎯 ACCURACY: {accuracy:.2f}%  ({correct}/{total_acc})", "ok")
                self._eval_log("─" * 92, "info")

                for cls_name, stat in sorted(cls_stats.items()):
                    cls_acc = ((stat["correct"] / stat["total"] * 100)
                               if stat["total"] > 0 else 0.0)
                    bar = "█" * int(cls_acc / 5) + "░" * (20 - int(cls_acc / 5))
                    self._eval_log(
                        f"    GT [{cls_name:<18}]  [{bar}]  {cls_acc:.2f}%"
                        f"  ({stat['correct']}/{stat['total']})", "info")

                if mismatches:
                    self._eval_log(
                        f"  ⚠  {len(mismatches)} ảnh dự đoán SAI:", "warn")
                    for t, p_name, img in mismatches[:15]:
                        self._eval_log(
                            f"     GT={t:<18}  Pred={p_name:<18}  {img}", "warn")
                    if len(mismatches) > 15:
                        self._eval_log(
                            f"     ... và {len(mismatches) - 15} ảnh sai khác", "warn")

                self._eval_log("═" * 92, "ok")

                result = {
                    "model":     Path(model_path).name,
                    "task":      task_label,
                    "mode":      "Batch Predict + Accuracy (folder GT · normalized)",
                    "ảnh xử lý": str(total_acc),
                    "Accuracy":  f"{accuracy:.2f}%  ({correct}/{total_acc})",
                    "Sai":       str(len(mismatches)),
                    "lưu tại":   str(save_dir),
                }
                for cls_name, stat in sorted(cls_stats.items()):
                    cls_acc = ((stat["correct"] / stat["total"] * 100)
                               if stat["total"] > 0 else 0.0)
                    result[f"  GT:{cls_name}"] = (
                        f"{cls_acc:.1f}%  ({stat['correct']}/{stat['total']})")

                self._eval_set_status(
                    f"✔ Accuracy: {accuracy:.2f}% | {correct}/{total_acc}", SUCCESS)
                self.after(0, self._eval_show_results, result)
                self._eval_results = result

                # ── Benchmark comparison ───────────────────────────────────
                if self._bench_canvas is not None:
                    _bench_info = {
                        "architecture": f"YOLOv8 ({task_label})",
                        "classes":      (len(model.names)
                                         if hasattr(model, "names") else "—"),
                        "input_size":   f"{imgsz}×{imgsz}",
                        "params_m":     _params_m,
                        "gflops":       _gflops,
                        "optimizer":    "AdamW / SGD (YOLO default)",
                        "loss_fn":      "BCE + DFL / CrossEntropyLoss",
                        "accuracy":     accuracy,
                        "accuracy_str": f"{accuracy:.2f}%",
                        "map50":        None,
                        "map50_95":     None,
                        "test_images":  total_acc,
                        "augmentation": "Mosaic, Flip, HSV (YOLO default)",
                    }
                    self.after(500, self._draw_benchmark_comparison, _bench_info)

            # ══════════════════════════════════════════════════════════════
            # DETECTION / SEGMENTATION — đếm objects + Accuracy từ folder GT
            # ══════════════════════════════════════════════════════════════
            else:
                cls_counts: dict = defaultdict(int)
                correct_det = total_det_acc = 0
                cls_stats_det: dict = defaultdict(lambda: {"correct": 0, "total": 0})

                for r, orig_path in zip(results, source):
                    names_map   = r.names if hasattr(r, "names") else {}
                    gt_folder   = Path(orig_path).parent.name.strip().lower()
                    gt_norm     = self._normalize_class_name(gt_folder)
                    # Có GT hợp lệ (không phải thư mục gốc dataset)
                    has_valid_gt = (gt_folder != ""
                                    and gt_folder != Path(data_path).name.lower())

                    if r.boxes is not None and len(r.boxes) > 0:
                        for box in r.boxes:
                            cid = int(box.cls[0])
                            cls_counts[names_map.get(cid, f"cls{cid}")] += 1

                        if has_valid_gt:
                            # Correct nếu ít nhất 1 box khớp tên folder GT
                            pred_norms = {
                                self._normalize_class_name(names_map.get(int(b.cls[0]), ""))
                                for b in r.boxes
                            }
                            is_correct = gt_norm in pred_norms
                            total_det_acc += 1
                            cls_stats_det[gt_folder]["total"] += 1
                            if is_correct:
                                correct_det += 1
                                cls_stats_det[gt_folder]["correct"] += 1
                    elif has_valid_gt:
                        total_det_acc += 1
                        cls_stats_det[gt_folder]["total"] += 1

                total_dets = sum(cls_counts.values())
                self._eval_log("═" * 65, "ok")
                self._eval_log(
                    f"  TỔNG KẾT QUẢ {task_label.upper()}: "
                    f"{total_dets} objects / {n} ảnh", "ok")
                self._eval_log("═" * 65, "ok")
                for cls_name, cnt in sorted(cls_counts.items(), key=lambda x: -x[1]):
                    pct = cnt / total_dets * 100 if total_dets > 0 else 0.0
                    self._eval_log(
                        f"  {cls_name:<22}  {cnt:>5}  ({pct:.1f}%)", "info")

                result = {
                    "model":        Path(model_path).name,
                    "task":         task_label,
                    "mode":         f"Batch Predict ({task_label})",
                    "ảnh xử lý":   str(n),
                    "conf":         f"{conf:.2f}",
                    "tổng objects": str(total_dets),
                    "lưu tại":      str(save_dir),
                }
                if total_det_acc > 0:
                    det_acc = correct_det / total_det_acc * 100
                    result["Accuracy (folder GT)"] = (
                        f"{det_acc:.2f}%  ({correct_det}/{total_det_acc})")
                    self._eval_log("─" * 65, "ok")
                    self._eval_log(
                        f"  🎯 ACCURACY (folder GT): {det_acc:.2f}%"
                        f"  ({correct_det}/{total_det_acc})", "ok")
                    for cls_name, stat in sorted(cls_stats_det.items()):
                        cls_acc = (stat["correct"] / stat["total"] * 100
                                   if stat["total"] > 0 else 0.0)
                        result[f"  GT:{cls_name}"] = (
                            f"{cls_acc:.1f}%  ({stat['correct']}/{stat['total']})")
                        self._eval_log(
                            f"    [{cls_name:<18}]  {cls_acc:.1f}%"
                            f"  ({stat['correct']}/{stat['total']})", "info")
                    self._eval_set_status(
                        f"✔ Accuracy: {det_acc:.2f}% | {total_dets} objects", SUCCESS)
                else:
                    self._eval_set_status(
                        f"✔ {task_label}: {total_dets} objects / {n} ảnh", SUCCESS)

                for cls_name, cnt in sorted(cls_counts.items(),
                                             key=lambda x: -x[1])[:10]:
                    pct = cnt / total_dets * 100 if total_dets > 0 else 0.0
                    result[f"  {cls_name}"] = f"{cnt}  ({pct:.1f}%)"
                self.after(0, self._eval_show_results, result)
                self._eval_results = result

            self._eval_log(f"\n[✔] Kết quả lưu tại: {save_dir}", "ok")

        except Exception:
            err = _tb.format_exc()
            self._eval_log(f"[✗] Lỗi:\n{err}", "err")
            self._eval_set_status("✗ Lỗi batch predict", DANGER)
        finally:
            self._eval_running = False
            self.after(0, self._restore_eval_primary_button)

    def _bench_build_reference_table(self, your_model: dict | None = None):
        """Render bảng benchmark 3 phía: baseline bài báo, re-implement và YOLOv8."""
        for w in self._bench_table_frame.winfo_children():
            w.destroy()

        selected = self._bench_reference_var.get()
        if selected == "PLOS ONE 2024":
            paper = PAPER_BENCHMARKS["PLOS ONE 2024\n(MobileNetV2)"]
            paper_label = "Baseline"
            paper_color = "#14532d"
            paper_bg = "#bbf7d0"
        else:
            paper = PAPER_BENCHMARKS["JILSA 2022\n(Custom CNN)"]
            paper_label = "Baseline"
            paper_color = "#7c2d12"
            paper_bg = "#fed7aa"

        reimpl_model = self._bench_cached_models.get(selected) or {}
        if your_model is not None and your_model.get("_bench_name") == selected:
            reimpl_model = your_model
        yolo_model = self._bench_latest_yolo_model or {}
        if your_model is not None and not your_model.get("_bench_name"):
            yolo_model = your_model

        col_w = [16, 18, 20, 18]

        def _hdr_cell(row_f, text, width, bg_c, fg_c="#ffffff"):
            tk.Label(
                row_f, text=text, font=("Segoe UI", 8, "bold"),
                bg=bg_c, fg=fg_c, width=width, anchor="center",
                padx=3, pady=4, relief="flat"
            ).pack(side="left", padx=1)

        def _cell(row_f, text, width, bg_c, fg_c=TEXT):
            tk.Label(
                row_f, text=str(text), font=("Segoe UI", 8),
                bg=bg_c, fg=fg_c, width=width, anchor="w",
                padx=3, pady=3, wraplength=170
            ).pack(side="left", padx=1)

        def _na(v):
            if v is None:
                return "—"
            txt = str(v).strip()
            return txt if txt else "—"

        def _fmt_num(v, digits):
            v = self._safe_float_or_none(v)
            return f"{v:.{digits}f}" if v is not None else "—"

        hdr_f = tk.Frame(self._bench_table_frame, bg=BG3)
        hdr_f.pack(fill="x", pady=(0, 1))
        _hdr_cell(hdr_f, "Thông số", col_w[0], BG3, ACCENT2)
        _hdr_cell(hdr_f, paper_label, col_w[1], paper_color, "white")
        _hdr_cell(hdr_f, "Re-implement", col_w[2], ACCENT, "white")
        _hdr_cell(hdr_f, "YOLOv8", col_w[3], "#1d4ed8", "white")

        rows_data = [
            ("Kiến trúc", paper["architecture"], _na(reimpl_model.get("architecture")), _na(yolo_model.get("architecture"))),
            ("Số lớp", str(paper["classes"]), _na(reimpl_model.get("classes")), _na(yolo_model.get("classes"))),
            ("Input Size", paper["input_size"], _na(reimpl_model.get("input_size")), _na(yolo_model.get("input_size"))),
            ("Params (M)", f"{paper['params_m']:.2f}", _fmt_num(reimpl_model.get("params_m"), 2), _fmt_num(yolo_model.get("params_m"), 2)),
            ("GFLOPs", f"{paper['gflops']:.1f}", _fmt_num(reimpl_model.get("gflops"), 1), _fmt_num(yolo_model.get("gflops"), 1)),
            ("Optimizer", paper["optimizer"], _na(reimpl_model.get("optimizer")), _na(yolo_model.get("optimizer"))),
            ("Loss Function", paper["loss_fn"], _na(reimpl_model.get("loss_fn")), _na(yolo_model.get("loss_fn"))),
            ("Accuracy / mAP50", f"{paper['accuracy']}%", _na(reimpl_model.get("accuracy_str")), _na(yolo_model.get("accuracy_str"))),
            ("mAP50-95", "—", _na(reimpl_model.get("map50_95")), _na(yolo_model.get("map50_95"))),
            ("Loss validation", "—", _fmt_num(reimpl_model.get("val_loss"), 4), _fmt_num(yolo_model.get("val_loss"), 4)),
            ("Macro F1", "—", self._fmt_percent_or_na(reimpl_model.get("macro_f1")), self._fmt_percent_or_na(yolo_model.get("macro_f1"))),
            ("Ảnh test", str(paper["test_images"]), _na(reimpl_model.get("test_images")), _na(yolo_model.get("test_images"))),
            ("Augmentation", paper["augmentation"], _na(reimpl_model.get("augmentation")), _na(yolo_model.get("augmentation"))),
        ]

        for label, baseline_val, reimpl_val, yolo_val in rows_data:
            row_f = tk.Frame(self._bench_table_frame, bg=BG2)
            row_f.pack(fill="x", pady=0)
            _cell(row_f, label, col_w[0], BG2)
            _cell(row_f, baseline_val, col_w[1], paper_bg)
            _cell(row_f, reimpl_val, col_w[2], BG2)
            _cell(row_f, yolo_val, col_w[3], BG2)


    def _draw_benchmark_comparison(self, your_model: dict):
        """Vẽ matplotlib chart so sánh model với 2 bài báo vào _bench_canvas."""
        if your_model is not None and your_model.get("_bench_name"):
            self._bench_cached_models[your_model["_bench_name"]] = dict(your_model)
        elif your_model is not None:
            self._bench_latest_yolo_model = dict(your_model)
        self.after(0, self._bench_build_reference_table, your_model)
        self.after(50, self._bench_draw_chart, your_model)

    def _bench_draw_chart(self, your_model: dict):
        """Vẽ biểu đồ benchmark 3 phía vào _bench_canvas."""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import matplotlib.gridspec as gridspec
            from PIL import Image as _PIL, ImageTk as _ITK
            import io

            selected = self._bench_reference_var.get()
            if selected == "PLOS ONE 2024":
                paper = PAPER_BENCHMARKS["PLOS ONE 2024\n(MobileNetV2)"]
                paper_name = "PLOS ONE\n2024"
                paper_color = "#22c55e"
            else:
                paper = PAPER_BENCHMARKS["JILSA 2022\n(Custom CNN)"]
                paper_name = "JILSA\n2022"
                paper_color = "#f97316"

            c  = self._bench_canvas
            cw = max(c.winfo_width(), 560)
            ch = max(c.winfo_height(), 240)

            fig = plt.figure(figsize=(cw / 96, ch / 96), dpi=96)
            fig.patch.set_facecolor("#1e1e2e")

            BG_AX   = "#13131f"
            C_TICK  = "#9090b0"
            C_SPINE = "#333350"
            C_TITLE = "#c0c0e0"

            # 3 subplots: Params(M), GFLOPs, Accuracy/mAP50
            gs = gridspec.GridSpec(1, 3, figure=fig, wspace=0.45)

            reimpl_model = self._bench_cached_models.get(selected) or {}
            if your_model is not None and your_model.get("_bench_name") == selected:
                reimpl_model = your_model
            yolo_model = self._bench_latest_yolo_model or {}
            if your_model is not None and not your_model.get("_bench_name"):
                yolo_model = your_model

            names = [paper_name, "Re-impl", "YOLOv8"]
            colors = [paper_color, "#7c3aed", "#2563eb"]

            params_vals = [
                paper["params_m"],
                self._safe_float_or_none(reimpl_model.get("params_m")) or 0.0,
                self._safe_float_or_none(yolo_model.get("params_m")) or 0.0,
            ]
            gflops_vals = [
                paper["gflops"],
                self._safe_float_or_none(reimpl_model.get("gflops")) or 0.0,
                self._safe_float_or_none(yolo_model.get("gflops")) or 0.0,
            ]
            # Accuracy: prefer accuracy (%), else map50*100
            def _acc(d, key_acc="accuracy", key_map="map50"):
                v = self._safe_float_or_none(d.get(key_acc))
                if v is not None:
                    return float(v)
                v = self._safe_float_or_none(d.get(key_map))
                return float(v) * 100 if v is not None else 0.0

            acc_vals = [
                float(paper["accuracy"]),
                _acc(reimpl_model),
                _acc(yolo_model),
            ]
            acc_label = "Accuracy (%)"
            if reimpl_model.get("accuracy") is None and reimpl_model.get("map50") is not None:
                acc_label = "mAP50×100"

            chart_configs = [
                ("Params (M)",    params_vals, ".2f"),
                ("GFLOPs",        gflops_vals, ".1f"),
                (acc_label,       acc_vals,    ".1f"),
            ]

            for col, (title, vals, fmt) in enumerate(chart_configs):
                ax = fig.add_subplot(gs[0, col])
                ax.set_facecolor(BG_AX)
                for sp in ax.spines.values():
                    sp.set_color(C_SPINE)
                ax.tick_params(colors=C_TICK, labelsize=7)

                bars = ax.bar(names, vals, color=colors,
                              edgecolor="#111122", linewidth=0.5, width=0.55)
                ax.set_title(title, color=C_TITLE, fontsize=8, pad=6)
                ax.set_ylabel("", color=C_TICK, fontsize=7)
                ax.tick_params(axis="x", labelsize=6.5)
                ax.tick_params(axis="y", labelsize=6.5)

                # Value labels on bars
                for bar, val in zip(bars, vals):
                    if val > 0:
                        ax.text(bar.get_x() + bar.get_width() / 2,
                                bar.get_height() + max(vals) * 0.015,
                                format(val, fmt),
                                ha="center", va="bottom",
                                color=C_TITLE, fontsize=7)

                # Dashed reference line for paper benchmark
                ax.axhline(vals[0], color=paper_color, linewidth=0.7,
                           linestyle="--", alpha=0.5)

            plt.tight_layout(pad=1.1)
            buf = io.BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight",
                        facecolor=fig.get_facecolor())
            plt.close(fig)
            buf.seek(0)

            img = _PIL.open(buf).convert("RGB")
            tk_img, fitted = self._paint_pil_on_canvas(c, img, min_w=560, min_h=240)
            self._bench_tk_img = tk_img
            self._bench_pil_img = fitted
            self._set_chart_caption("bench", "So sánh benchmark: Params, GFLOPs và Accuracy hoặc mAP50")

        except ImportError as e:
            self.after(0, lambda: self._bench_canvas.itemconfigure(
                self._bench_canvas.create_text(
                    200, 100, text=f"⚠ Cần matplotlib + Pillow\n({e})",
                    fill=WARNING, font=("Segoe UI", 9), justify="center"),
                ))
        except Exception as ex:
            print(f"[bench chart error] {ex}")

    def _bench_save_chart(self):
        """Lưu biểu đồ benchmark bằng cùng pipeline ảnh đã render."""
        import datetime
        if self._bench_pil_img is None:
            messagebox.showinfo("Thông báo", "Chạy Đánh giá hoặc dự đoán theo lô trước.")
            return
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self._save_chart_pil_image(
            self._bench_pil_img,
            title="Lưu biểu đồ so sánh benchmark",
            initialfile=f"benchmark_comparison_{ts}.png",
        )

    # ─────────────────────────────────────────────────────────────────────────
    # ĐÁNH GIÁ MODEL (VAL) — BUILD UI
    # ─────────────────────────────────────────────────────────────────────────
    def _build_eval_tab(self, parent: tk.Frame):
        """Tab Đánh giá (Val): chạy model.val() → metrics + loss chart."""
        from tkinter import scrolledtext as _st

        paned = tk.PanedWindow(parent, orient="horizontal", bg=BG,
                               sashwidth=5, sashrelief="flat")
        paned.pack(fill="both", expand=True, padx=8, pady=8)

        left  = tk.Frame(paned, bg=BG2, padx=12, pady=10, width=320)
        right = tk.Frame(paned, bg=BG)
        paned.add(left,  minsize=290)
        paned.add(right, minsize=520)

        def sec(t): self._sec(left, t)

        # ── Model ──────────────────────────────────────────────────────────
        sec("🤖 Model (.pt / .onnx)")
        tk.Label(left, text="Chọn file .pt/.onnx hoặc thư mục chứa weights/",
                 font=("Segoe UI", 7), bg=BG2, fg=TEXT_DIM).pack(anchor="w")
        f_mdir = tk.Frame(left, bg=BG2); f_mdir.pack(fill="x", pady=2)
        tk.Entry(f_mdir, textvariable=self._eval_model_dir, bg=BG3, fg=TEXT,
                 insertbackground=TEXT, relief="flat",
                 font=("Segoe UI", 8)).pack(side="left", fill="x", expand=True, padx=(0, 2))
        tk.Button(f_mdir, text="📄", bg=BG3, fg=TEXT, relief="flat", padx=3, cursor="hand2",
                  command=self._eval_browse_model_file).pack(side="left", padx=(0, 2))
        tk.Button(f_mdir, text="📁", bg=BG3, fg=TEXT, relief="flat", padx=3, cursor="hand2",
                  command=self._eval_browse_model_folder).pack(side="left")

        # ── Dataset ────────────────────────────────────────────────────────
        sec("📂 Dataset")
        tk.Label(left, text="YAML cho detect/seg  ·  thư mục cho classify",
                 font=("Segoe UI", 7), bg=BG2, fg=TEXT_DIM).pack(anchor="w")
        f_data = tk.Frame(left, bg=BG2); f_data.pack(fill="x", pady=2)
        tk.Entry(f_data, textvariable=self._eval_data_path, bg=BG3, fg=TEXT,
                 insertbackground=TEXT, relief="flat",
                 font=("Segoe UI", 8)).pack(side="left", fill="x", expand=True, padx=(0, 2))
        tk.Button(f_data, text="📄", bg=BG3, fg=TEXT, relief="flat", padx=3, cursor="hand2",
                  command=self._eval_browse_yaml).pack(side="left", padx=(0, 2))
        tk.Button(f_data, text="📁", bg=BG3, fg=TEXT, relief="flat", padx=3, cursor="hand2",
                  command=self._eval_browse_data_folder).pack(side="left")

        # ── Output dir ─────────────────────────────────────────────────────
        sec("💾 Thư mục lưu kết quả Val")
        tk.Label(left, text="Để trống → tự lưu vào runs/ mặc định của YOLO",
                 font=("Segoe UI", 7), bg=BG2, fg=TEXT_DIM).pack(anchor="w")
        f_out = tk.Frame(left, bg=BG2); f_out.pack(fill="x", pady=2)
        tk.Entry(f_out, textvariable=self._eval_output_dir, bg=BG3, fg=SUCCESS,
                 insertbackground=TEXT, relief="flat",
                 font=("Segoe UI", 8)).pack(side="left", fill="x", expand=True, padx=(0, 2))
        tk.Button(f_out, text="📁", bg=SUCCESS, fg="white", relief="flat", padx=6,
                  cursor="hand2", font=("Segoe UI", 9, "bold"),
                  activebackground="#16a34a",
                  command=lambda: self._browse_dir(
                      self._eval_output_dir, "Chọn thư mục lưu kết quả Val")).pack(side="left")

        # ── Task ───────────────────────────────────────────────────────────
        sec("🎯 Loại Task")
        ttk.Combobox(left, textvariable=self._eval_task_var, values=TASK_TYPES,
                     state="readonly", font=("Segoe UI", 9)).pack(fill="x", pady=2)

        # Dynamic metrics hint
        self._eval_metrics_hint_lbl = tk.Label(
            left, text="", font=("Segoe UI", 8, "italic"),
            bg=BG2, fg=INFO, justify="left", wraplength=270)
        self._eval_metrics_hint_lbl.pack(anchor="w", pady=(2, 4))

        # ── Tham số ────────────────────────────────────────────────────────
        sec("⚙ Tham số đánh giá")
        self._row(left, "Img size", lambda p: self._spin(p, self._eval_imgsz_var, 320, 1280, 32))
        self._row(left, "Device",
                  lambda p: ttk.Combobox(p, textvariable=self._eval_device_var,
                                         values=["0", "cpu"], state="readonly",
                                         font=("Segoe UI", 9), width=6))

        # Det/Seg-only params: Split + IOU — ẩn khi Classification
        # Conf — luôn hiển thị (có thể điều chỉnh cho cả Classification)
        self._eval_conf_frame = tk.Frame(left, bg=BG2)
        self._eval_conf_frame.pack(fill="x")
        self._row(self._eval_conf_frame, "Conf",
                  lambda p: self._spin(p, self._eval_conf_var, 0.01, 1.0, 0.05, width=8))

        self._eval_det_params_frame = tk.Frame(left, bg=BG2)
        self._eval_det_params_frame.pack(fill="x")
        self._row(self._eval_det_params_frame, "Split",
                  lambda p: ttk.Combobox(p, textvariable=self._eval_split_var,
                                         values=["val", "test", "train"], state="readonly",
                                         font=("Segoe UI", 9), width=6))
        self._row(self._eval_det_params_frame, "IOU",
                  lambda p: self._spin(p, self._eval_iou_var,  0.01, 1.0, 0.05, width=8))

        f_half = tk.Frame(left, bg=BG2); f_half.pack(fill="x", pady=4)
        tk.Checkbutton(f_half, text="Half FP16 (val/predict)", variable=self._eval_half_var,
                       bg=BG2, fg=TEXT, selectcolor=BG3,
                       activebackground=BG2, font=("Segoe UI", 9)).pack(side="left")

        self._eval_mode_hint = tk.Label(
            left,
            text="💡 detect/seg + thư mục → sẽ tự tạo YAML tạm\n"
                 "   (cần file .txt nhãn cùng thư mục với ảnh)",
            font=("Segoe UI", 7), bg=BG2, fg=TEXT_DIM,
            justify="left", wraplength=270)
        self._eval_mode_hint.pack(anchor="w", pady=(4, 0))

        # ── Nút chạy + xuất ────────────────────────────────────────────────
        self._eval_run_btn = tk.Button(
            left, text="▶  Chạy Đánh giá (Val)",
            font=("Segoe UI", 10, "bold"),
            bg=SUCCESS, fg="white", relief="flat",
            cursor="hand2", pady=8,
            command=self._eval_run)
        self._eval_run_btn.pack(fill="x", pady=(14, 2))

        tk.Button(left, text="💾  Xuất kết quả JSON",
                  font=("Segoe UI", 9),
                  bg=BG3, fg=TEXT_DIM, relief="flat",
                  cursor="hand2", pady=6,
                  command=self._eval_export).pack(fill="x", pady=2)
        tk.Button(left, text="💾  Lưu phiên (EVAL_BASE_DIR/yolo)",
                  font=("Segoe UI", 9, "bold"),
                  bg=SUCCESS, fg="white", relief="flat",
                  cursor="hand2", pady=6,
                  command=self._yolo_save_session).pack(fill="x", pady=(0, 2))

        self._eval_status_lbl = tk.Label(left, text="⏹ Chưa chạy",
                                          font=("Segoe UI", 8),
                                          bg=BG2, fg=TEXT_DIM, wraplength=270, justify="left")
        self._eval_status_lbl.pack(anchor="w", pady=(8, 0))

        # ── Task change → cập nhật hint + ẩn/hiện tham số ─────────────────
        _METRICS_HINTS = {
            "Detection":
                "📊 Thang đo: mAP@50 · mAP@50-95 · Precision · Recall · F1",
            "Instance Segmentation":
                "📊 Thang đo: Box mAP@50-95 + Mask mAP@50-95\n"
                "   (2 luồng riêng: bounding-box & pixel mask)",
            "Classification":
                "📊 Thang đo: Top-1 Accuracy · Top-5 Accuracy\n"
                "   · Mean Per-Class Accuracy (top1p)",
        }
        # Thông số mặc định theo task
        _EVAL_DEFAULTS = {
            "Classification":        {"imgsz": 224, "conf": 0.40},
            "Detection":             {"imgsz": 640, "conf": 0.25},
            "Instance Segmentation": {"imgsz": 640, "conf": 0.25},
        }
        def _on_eval_task_change(*_):
            task = self._eval_task_var.get()
            self._eval_metrics_hint_lbl.configure(text=_METRICS_HINTS.get(task, ""))
            # Split + IOU không dùng cho Classification; Conf luôn hiện
            if task == "Classification":
                self._eval_det_params_frame.pack_forget()
            else:
                self._eval_det_params_frame.pack(fill="x", after=self._eval_conf_frame)
            d = _EVAL_DEFAULTS.get(task, {})
            if "imgsz" in d: self._eval_imgsz_var.set(d["imgsz"])
            if "conf"  in d: self._eval_conf_var.set(d["conf"])
        self._eval_task_var.trace_add("write", _on_eval_task_change)
        _on_eval_task_change()

        # ── RIGHT: results ─────────────────────────────────────────────────
        r_paned = tk.PanedWindow(right, orient="vertical", bg=BG,
                                 sashwidth=4, sashrelief="flat")
        r_paned.pack(fill="both", expand=True)

        top_half = tk.Frame(r_paned, bg=BG)
        r_paned.add(top_half, minsize=280)

        top_split = tk.PanedWindow(top_half, orient="horizontal", bg=BG,
                                   sashwidth=4, sashrelief="flat")
        top_split.pack(fill="both", expand=True)

        metrics_panel = tk.Frame(top_split, bg=BG2, padx=10, pady=8)
        top_split.add(metrics_panel, minsize=220)

        tk.Label(metrics_panel, text="📋 Kết quả đánh giá",
                 font=("Segoe UI", 10, "bold"), bg=BG2, fg=ACCENT2).pack(anchor="w", pady=(0, 6))

        self._eval_metrics_frame = tk.Frame(metrics_panel, bg=BG2)
        self._eval_metrics_frame.pack(fill="both", expand=True)
        self._eval_draw_empty_metrics()

        chart_panel = tk.Frame(top_split, bg=BG3, padx=4, pady=4)
        top_split.add(chart_panel, minsize=260)

        chart_hdr = tk.Frame(chart_panel, bg=BG3); chart_hdr.pack(fill="x")
        tk.Label(chart_hdr, text="📈 Loss / Metrics theo epoch",
                 font=("Segoe UI", 9, "bold"), bg=BG3, fg=ACCENT2).pack(side="left")
        tk.Button(chart_hdr, text="🔄", bg=BG3, fg=TEXT_DIM, relief="flat",
                  cursor="hand2", padx=4, font=("Segoe UI", 8),
                  command=self._eval_refresh_chart).pack(side="right")

        self._eval_chart_canvas = tk.Canvas(chart_panel, bg=BG4, highlightthickness=0)
        self._eval_chart_canvas.pack(fill="both", expand=True, pady=(4, 0))
        self._eval_chart_tk_img  = None
        self._batch_chart_tk_img = None

        bot_half = tk.Frame(r_paned, bg=BG)
        r_paned.add(bot_half, minsize=120)

        tk.Label(bot_half, text="📝 Log đánh giá",
                 font=("Segoe UI", 8, "bold"), bg=BG, fg=TEXT_DIM).pack(anchor="w", padx=6)
        self._eval_log_box = _st.ScrolledText(
            bot_half, bg=BG4, fg="#d4d4d4", insertbackground="white",
            relief="flat", font=("Cascadia Code", 8),
            wrap="word", state="disabled", height=8,
        )
        self._eval_log_box.pack(fill="both", expand=True, padx=4, pady=(2, 4))
        self._eval_log_box.tag_config("ok",   foreground="#22c55e")
        self._eval_log_box.tag_config("warn", foreground="#f59e0b")
        self._eval_log_box.tag_config("err",  foreground="#ef4444")
        self._eval_log_box.tag_config("info", foreground="#38bdf8")
        self._eval_log_box.tag_config("dim",  foreground="#94a3b8")

    # BATCH PREDICT — BUILD UI
    # ─────────────────────────────────────────────────────────────────────────
    def _build_batch_tab(self, parent: tk.Frame):
        """Tab Batch Predict: chạy model.predict() hàng loạt trên thư mục ảnh."""
        from tkinter import scrolledtext as _st

        paned = tk.PanedWindow(parent, orient="horizontal", bg=BG,
                               sashwidth=5, sashrelief="flat")
        paned.pack(fill="both", expand=True, padx=8, pady=8)

        left  = tk.Frame(paned, bg=BG2, padx=12, pady=10, width=320)
        right = tk.Frame(paned, bg=BG)
        paned.add(left,  minsize=290)
        paned.add(right, minsize=520)

        def sec(t): self._sec(left, t)

        # ── Model ──────────────────────────────────────────────────────────
        sec("🤖 Model (.pt / .onnx)")
        tk.Label(left, text="Chọn file .pt/.onnx hoặc thư mục chứa weights/",
                 font=("Segoe UI", 7), bg=BG2, fg=TEXT_DIM).pack(anchor="w")
        f_mdir = tk.Frame(left, bg=BG2); f_mdir.pack(fill="x", pady=2)
        tk.Entry(f_mdir, textvariable=self._batch_model_dir, bg=BG3, fg=TEXT,
                 insertbackground=TEXT, relief="flat",
                 font=("Segoe UI", 8)).pack(side="left", fill="x", expand=True, padx=(0, 2))
        tk.Button(f_mdir, text="📄", bg=BG3, fg=TEXT, relief="flat", padx=3, cursor="hand2",
                  command=lambda: self._browse_file(
                      self._batch_model_dir, "Chọn file model",
                      [("YOLO model", "*.pt *.onnx"), ("All files", "*.*")]
                  )).pack(side="left", padx=(0, 2))
        tk.Button(f_mdir, text="📁", bg=BG3, fg=TEXT, relief="flat", padx=3, cursor="hand2",
                  command=lambda: self._browse_dir(
                      self._batch_model_dir, "Chọn thư mục model")
                  ).pack(side="left")

        # ── Nguồn ảnh ──────────────────────────────────────────────────────
        sec("📂 Nguồn ảnh (thư mục / file ảnh)")
        tk.Label(left, text="Thư mục ảnh, file ảnh đơn, hoặc video để predict",
                 font=("Segoe UI", 7), bg=BG2, fg=TEXT_DIM).pack(anchor="w")
        f_data = tk.Frame(left, bg=BG2); f_data.pack(fill="x", pady=2)
        tk.Entry(f_data, textvariable=self._batch_data_path, bg=BG3, fg=TEXT,
                 insertbackground=TEXT, relief="flat",
                 font=("Segoe UI", 8)).pack(side="left", fill="x", expand=True, padx=(0, 2))
        tk.Button(f_data, text="📄", bg=BG3, fg=TEXT, relief="flat", padx=3, cursor="hand2",
                  command=lambda: self._browse_file(
                      self._batch_data_path, "Chọn ảnh/video",
                      [("Images & Video", "*.jpg *.jpeg *.png *.bmp *.mp4 *.avi"),
                       ("All files", "*.*")]
                  )).pack(side="left", padx=(0, 2))
        tk.Button(f_data, text="📁", bg=BG3, fg=TEXT, relief="flat", padx=3, cursor="hand2",
                  command=self._batch_browse_data_folder).pack(side="left")

        # ── Image count + refresh ──────────────────────────────────────────
        f_count = tk.Frame(left, bg=BG2); f_count.pack(fill="x", pady=(2, 0))
        self._batch_img_count_lbl = tk.Label(
            f_count, text="📊 Chưa chọn thư mục",
            font=("Segoe UI", 8, "italic"), bg=BG2, fg=TEXT_DIM)
        self._batch_img_count_lbl.pack(side="left")
        tk.Button(f_count, text="🔄", bg=BG3, fg=TEXT_DIM, relief="flat", padx=4,
                  cursor="hand2", font=("Segoe UI", 8),
                  command=self._batch_refresh_count).pack(side="right")

        # ── Split / giới hạn số ảnh test ──────────────────────────────────
        self._batch_split_frame = tk.LabelFrame(
            left, text=" 🎲 Giới hạn số ảnh test ",
            font=("Segoe UI", 8, "bold"),
            bg=BG2, fg=ACCENT2, bd=1, relief="groove", padx=6, pady=4)
        self._batch_split_frame.pack(fill="x", pady=(4, 2))

        f_split_top = tk.Frame(self._batch_split_frame, bg=BG2)
        f_split_top.pack(fill="x")
        tk.Checkbutton(
            f_split_top, text="Bật giới hạn",
            variable=self._batch_split_enable,
            bg=BG2, fg=TEXT, selectcolor=BG3, activebackground=BG2,
            font=("Segoe UI", 9),
            command=self._batch_on_split_toggle
        ).pack(side="left")

        self._batch_split_n_spin = tk.Spinbox(
            f_split_top, textvariable=self._batch_split_n,
            from_=1, to=99999, increment=10, width=7,
            bg=BG3, fg=SUCCESS, insertbackground=TEXT,
            relief="flat", font=("Segoe UI", 9),
            state="disabled")
        self._batch_split_n_spin.pack(side="left", padx=(6, 2))
        tk.Label(f_split_top, text="ảnh", bg=BG2, fg=TEXT_DIM,
                 font=("Segoe UI", 8)).pack(side="left")

        f_split_mode = tk.Frame(self._batch_split_frame, bg=BG2)
        f_split_mode.pack(fill="x", pady=(4, 0))
        for mode_val, mode_txt in [("random", "🎲 Ngẫu nhiên"), ("sequential", "📋 Tuần tự")]:
            tk.Radiobutton(
                f_split_mode, text=mode_txt, value=mode_val,
                variable=self._batch_split_mode,
                bg=BG2, fg=TEXT, selectcolor=BG3, activebackground=BG2,
                font=("Segoe UI", 8), state="disabled",
            ).pack(side="left", padx=(0, 10))
        self._batch_split_mode_radios = f_split_mode.winfo_children()

        self._batch_split_info_lbl = tk.Label(
            self._batch_split_frame, text="",
            font=("Segoe UI", 7, "italic"), bg=BG2, fg=WARNING, wraplength=260)
        self._batch_split_info_lbl.pack(anchor="w")

        # Trace split_n changes → update info label
        self._batch_split_n.trace_add("write",
            lambda *_: self._batch_on_split_toggle())
        self._batch_split_enable.trace_add("write",
            lambda *_: self._batch_on_split_toggle())

        # ── Output dir ─────────────────────────────────────────────────────
        sec("💾 Thư mục lưu ảnh kết quả")
        tk.Label(left, text="Để trống → tự lưu vào runs/ mặc định của YOLO",
                 font=("Segoe UI", 7), bg=BG2, fg=TEXT_DIM).pack(anchor="w")
        f_out = tk.Frame(left, bg=BG2); f_out.pack(fill="x", pady=2)
        tk.Entry(f_out, textvariable=self._batch_output_dir, bg=BG3, fg=SUCCESS,
                 insertbackground=TEXT, relief="flat",
                 font=("Segoe UI", 8)).pack(side="left", fill="x", expand=True, padx=(0, 2))
        tk.Button(f_out, text="📁", bg=SUCCESS, fg="white", relief="flat", padx=6,
                  cursor="hand2", font=("Segoe UI", 9, "bold"),
                  activebackground="#16a34a",
                  command=lambda: self._browse_dir(
                      self._batch_output_dir, "Chọn thư mục lưu ảnh kết quả")
                  ).pack(side="left")

        # ── Task ───────────────────────────────────────────────────────────
        sec("🎯 Loại Task")
        ttk.Combobox(left, textvariable=self._batch_task_var, values=TASK_TYPES,
                     state="readonly", font=("Segoe UI", 9)).pack(fill="x", pady=2)

        # Dynamic hint (đầu ra của mỗi task)
        self._batch_hint_lbl = tk.Label(
            left, text="", font=("Segoe UI", 8, "italic"),
            bg=BG2, fg=INFO, justify="left", wraplength=270)
        self._batch_hint_lbl.pack(anchor="w", pady=(2, 4))

        # ── Tham số ────────────────────────────────────────────────────────
        sec("⚙ Tham số predict")
        self._row(left, "Img size", lambda p: self._spin(p, self._batch_imgsz_var, 32, 1280, 32))
        self._row(left, "Device",
                  lambda p: ttk.Combobox(p, textvariable=self._batch_device_var,
                                         values=["0", "cpu"], state="readonly",
                                         font=("Segoe UI", 9), width=6))

        # Conf — luôn hiển thị (dùng cho cả Classification)
        self._batch_conf_frame = tk.Frame(left, bg=BG2)
        self._batch_conf_frame.pack(fill="x")
        self._row(self._batch_conf_frame, "Conf",
                  lambda p: self._spin(p, self._batch_conf_var, 0.01, 1.0, 0.05, width=8))

        # IOU — chỉ hiển thị khi Detection / Segmentation
        self._batch_det_params_frame = tk.Frame(left, bg=BG2)
        self._batch_det_params_frame.pack(fill="x")
        self._row(self._batch_det_params_frame, "IOU",
                  lambda p: self._spin(p, self._batch_iou_var, 0.01, 1.0, 0.05, width=8))

        f_half = tk.Frame(left, bg=BG2); f_half.pack(fill="x", pady=4)
        tk.Checkbutton(f_half, text="Half FP16", variable=self._batch_half_var,
                       bg=BG2, fg=TEXT, selectcolor=BG3,
                       activebackground=BG2, font=("Segoe UI", 9)).pack(side="left")

        # ── Task change → hint + ẩn/hiện Conf/IOU ─────────────────────────
        _BATCH_HINTS = {
            "Detection":
                "🖼 Kết quả: ảnh bounding-box + .txt nhãn box\n"
                "   · Thống kê số object theo class",
            "Instance Segmentation":
                "🖼 Kết quả: ảnh mask overlay + .txt nhãn\n"
                "   · Thống kê số object theo class",
            "Classification":
                "🖼 Kết quả: ảnh phân loại theo Top-1 class\n"
                "   · Thống kê tỉ lệ mỗi class (%)",
        }
        # Thông số mặc định theo task
        _BATCH_DEFAULTS = {
            "Classification":        {"imgsz": 224, "conf": 0.40},
            "Detection":             {"imgsz": 640, "conf": 0.25},
            "Instance Segmentation": {"imgsz": 640, "conf": 0.25},
        }
        def _on_batch_task_change(*_):
            task = self._batch_task_var.get()
            self._batch_hint_lbl.configure(text=_BATCH_HINTS.get(task, ""))
            # IOU không dùng cho Classification → ẩn; Conf luôn hiện
            if task == "Classification":
                self._batch_det_params_frame.pack_forget()
            else:
                self._batch_det_params_frame.pack(fill="x", after=self._batch_conf_frame)
            d = _BATCH_DEFAULTS.get(task, {})
            if "imgsz" in d: self._batch_imgsz_var.set(d["imgsz"])
            if "conf"  in d: self._batch_conf_var.set(d["conf"])
        self._batch_task_var.trace_add("write", _on_batch_task_change)
        _on_batch_task_change()

        # ── Nút chạy ───────────────────────────────────────────────────────
        self._eval_batch_btn = tk.Button(
            left, text="▶  Chạy dự đoán theo lô",
            font=("Segoe UI", 10, "bold"),
            bg=INFO, fg="white", relief="flat",
            cursor="hand2", pady=8,
            command=self._eval_batch_run)
        self._eval_batch_btn.pack(fill="x", pady=(14, 2))

        tk.Label(left,
                 text="Chạy predict hàng loạt, lưu ảnh kết quả.\nKhông cần file nhãn.",
                 font=("Segoe UI", 7), bg=BG2, fg=TEXT_DIM,
                 justify="left", wraplength=270).pack(anchor="w")

        self._batch_status_lbl = tk.Label(left, text="⏹ Chưa chạy",
                                           font=("Segoe UI", 8),
                                           bg=BG2, fg=TEXT_DIM, wraplength=270, justify="left")
        self._batch_status_lbl.pack(anchor="w", pady=(8, 0))

        # ── RIGHT: log + chart (paned) ─────────────────────────────────────
        r_paned = tk.PanedWindow(right, orient="vertical", bg=BG,
                                 sashwidth=5, sashrelief="flat")
        r_paned.pack(fill="both", expand=True, padx=4, pady=4)

        log_frame   = tk.Frame(r_paned, bg=BG)
        chart_frame = tk.Frame(r_paned, bg=BG4)
        r_paned.add(log_frame,   minsize=140)
        r_paned.add(chart_frame, minsize=180)

        log_hdr = tk.Frame(log_frame, bg=BG); log_hdr.pack(fill="x", pady=(0, 4))
        tk.Label(log_hdr, text="📝 Nhật ký dự đoán theo lô",
                 font=("Segoe UI", 9, "bold"), bg=BG, fg=TEXT_DIM).pack(side="left", padx=6)
        tk.Button(log_hdr, text="💾 Lưu chart", bg=BG3, fg=ACCENT2, relief="flat",
                  cursor="hand2", padx=8, font=("Segoe UI", 8),
                  command=self._batch_save_chart).pack(side="right", padx=4)
        tk.Button(log_hdr, text="🗑 Xóa log", bg=BG3, fg=TEXT_DIM, relief="flat",
                  cursor="hand2", padx=8, font=("Segoe UI", 8),
                  command=lambda: (
                      self._batch_log_box.configure(state="normal"),
                      self._batch_log_box.delete("1.0", "end"),
                      self._batch_log_box.configure(state="disabled")
                  )).pack(side="right", padx=4)

        self._batch_log_box = _st.ScrolledText(
            log_frame, bg=BG4, fg="#d4d4d4", insertbackground="white",
            relief="flat", font=("Cascadia Code", 9),
            wrap="word", state="disabled",
        )
        self._batch_log_box.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self._batch_log_box.tag_config("ok",   foreground="#22c55e")
        self._batch_log_box.tag_config("warn", foreground="#f59e0b")
        self._batch_log_box.tag_config("err",  foreground="#ef4444")
        self._batch_log_box.tag_config("info", foreground="#38bdf8")

        # Chart canvas
        chart_hdr = tk.Frame(chart_frame, bg=BG3); chart_hdr.pack(fill="x")
        tk.Label(chart_hdr, text="📊 Biểu đồ kết quả",
                 font=("Segoe UI", 8, "bold"), bg=BG3, fg=TEXT_DIM).pack(side="left", padx=6, pady=3)
        self._batch_chart_canvas = tk.Canvas(
            chart_frame, bg=BG4, highlightthickness=0)
        self._batch_chart_canvas.pack(fill="both", expand=True)
        self._batch_chart_canvas.create_text(
            200, 100, text="📊 Chạy dự đoán theo lô để xem biểu đồ",
            fill=TEXT_DIM, font=("Segoe UI", 9))

    def _eval_draw_empty_metrics(self):
        self._eval_render_summary_cards({})
        for w in self._eval_metrics_frame.winfo_children():
            w.destroy()
        rows = [
            ("Model",           "—"),
            ("Task",            "—"),
            ("Dataset",         "—"),
            ("Split",           "—"),
        ]
        self._eval_render_metrics_rows(rows)

    def _eval_render_summary_cards(self, result: dict):
        if not hasattr(self, "_eval_summary_frame") or self._eval_summary_frame is None:
            return
        for w in self._eval_summary_frame.winfo_children():
            w.destroy()

        def _pick(*keys):
            for key in keys:
                value = result.get(key)
                if value not in (None, "", "—"):
                    return value
            return "—"

        task = str(result.get("task", self._eval_task_var.get() if hasattr(self, "_eval_task_var") else "")).lower()
        cards = [
            ("Params", _pick("Params (M)"), WARNING),
            ("GFLOPs", _pick("GFLOPs"), INFO),
        ]
        if "class" in task:
            cards = [
                ("Top-1", _pick("Top-1 Accuracy"), SUCCESS),
                ("Macro F1", _pick("Macro F1-Score"), ACCENT2),
                ("Precision", _pick("Macro Precision"), INFO),
                ("Recall", _pick("Macro Recall"), WARNING),
            ] + cards
        elif "segment" in task:
            cards = [
                ("Box mAP50", _pick("Box mAP@50"), SUCCESS),
                ("Mask mAP50", _pick("Mask mAP@50"), ACCENT2),
                ("Box F1", _pick("Box F1"), INFO),
                ("Mask F1", _pick("Mask F1"), WARNING),
            ] + cards
        else:
            cards = [
                ("mAP50", _pick("mAP@50"), SUCCESS),
                ("mAP50-95", _pick("mAP@50-95"), ACCENT2),
                ("Precision", _pick("Precision"), INFO),
                ("Recall / F1", f"{_pick('Recall')} / {_pick('F1 Score')}", WARNING),
            ] + cards

        for label, value, fg in cards[:6]:
            card = tk.Frame(self._eval_summary_frame, bg=BG3, padx=8, pady=6)
            card.pack(side="left", fill="x", expand=True, padx=2)
            tk.Label(card, text=label, font=("Segoe UI", 7, "bold"),
                     bg=BG3, fg=TEXT_DIM).pack(anchor="w")
            tk.Label(card, text=str(value), font=("Cascadia Code", 8, "bold"),
                     bg=BG3, fg=fg, wraplength=140, justify="left").pack(anchor="w", pady=(4, 0))

    def _eval_render_metrics_rows(self, rows: list[tuple[str, str]]):
        for w in self._eval_metrics_frame.winfo_children():
            w.destroy()
        for i, (label, value) in enumerate(rows):
            bg = BG3 if i % 2 == 0 else BG2
            row_f = tk.Frame(self._eval_metrics_frame, bg=bg)
            row_f.pack(fill="x", pady=1)
            # Label column — bright white for readability
            tk.Label(row_f, text=label, font=("Segoe UI", 8, "bold"),
                     bg=bg, fg=ACCENT2, width=22, anchor="w", padx=6,
                     pady=4).pack(side="left")
            # Value column — color by content
            sv = str(value)
            if sv in ("—", "", "None"):
                fg = TEXT_DIM
            elif any(v in label for v in ["✅", "mAP", "Accuracy", "Top-1", "Top-5", "F1"]):
                fg = ACCENT2          # highlight key metrics
            elif any(v in label for v in ["Precision", "Recall"]):
                fg = INFO
            elif any(v in sv for v in ["Lỗi", "lỗi", "✗", "⚠"]):
                fg = DANGER
            elif any(v in sv for v in ["✔", "✅"]):
                fg = SUCCESS
            else:
                fg = "#dbeafe"
            tk.Label(row_f, text=sv, font=("Cascadia Code", 9),
                     bg=bg, fg=fg, anchor="w", padx=6, pady=4,
                     wraplength=260).pack(side="left", fill="x", expand=True)

    # ─────────────────────────────────────────────────────────────────────────
    # ĐÁNH GIÁ MODEL — BROWSE HELPERS
    # ─────────────────────────────────────────────────────────────────────────
    # ─────────────────────────────────────────────────────────────────────────
    # ĐÁNH GIÁ MODEL — BATCH PREDICT
    # ─────────────────────────────────────────────────────────────────────────
    # ─────────────────────────────────────────────────────────────────────────
    # BATCH PREDICT — RUN
    # ─────────────────────────────────────────────────────────────────────────
    def _eval_batch_run(self):
        """Batch Predict với tuỳ chọn tính Accuracy (so sánh ground-truth từ tên thư mục)."""
        if self._batch_running:
            messagebox.showinfo("⏳", "Đang chạy, vui lòng đợi.")
            return

        model_input = self._batch_model_dir.get().strip()
        data_path   = self._batch_data_path.get().strip()

        if not model_input or not data_path:
            messagebox.showerror("Thiếu thông tin", "Vui lòng chọn Model và Thư mục dataset.")
            return
        if not Path(data_path).exists():
            messagebox.showerror("Lỗi", f"Đường dẫn không tồn tại:\n{data_path}")
            return

        # Resolve model path (file trực tiếp hoặc thư mục chứa weights)
        model_path = None
        p = Path(model_input)
        if p.is_file() and p.suffix.lower() in (".pt", ".onnx"):
            model_path = str(p)
        else:
            for cand in [p/"weights"/"best.pt", p/"weights"/"last.pt",
                         p/"best.pt", p/"last.pt"]:
                if cand.is_file():
                    model_path = str(cand); break
            if model_path is None:
                for ext in ("*.pt", "*.onnx"):
                    found = list(p.rglob(ext))
                    if found:
                        model_path = str(found[0]); break
        if model_path is None:
            messagebox.showerror("Không tìm thấy model",
                "Không tìm thấy file .pt/.onnx.\n"
                "Chọn trực tiếp file (nút 📄) hoặc thư mục weights/ (nút 📁).")
            return

        # Hỏi chế độ: Predict + Accuracy hay chỉ Predict
        calc_accuracy = messagebox.askyesno(
            "Chọn chế độ dự đoán theo lô",
            "Bạn muốn:\n\n"
            "【Yes】  Predict + Tính Accuracy\n"
            "         (so sánh kết quả với tên thư mục chứa ảnh — ground truth)\n\n"
            "【No】   Chỉ Predict và lưu ảnh kết quả"
        )

        self._batch_running = True
        self._eval_batch_btn.configure(state="disabled", text="⏳ Đang chạy...")
        self._batch_set_status("⏳ Batch predict đang chạy...", WARNING)
        self._batch_log_box.configure(state="normal")
        self._batch_log_box.delete("1.0", "end")
        self._batch_log_box.configure(state="disabled")

        threading.Thread(
            target=self._batch_predict_thread,
            args=(model_path, data_path, calc_accuracy),
            daemon=True,
        ).start()

    def _batch_predict_thread(self, model_path: str, data_path: str, calc_accuracy: bool):
        """Thread chính của Batch Predict. calc_accuracy=True → so GT từ tên thư mục."""
        import traceback as _tb, shutil, random as _rng
        from collections import defaultdict
        from datetime import datetime

        task_map = {"Detection": "detect", "Instance Segmentation": "segment",
                    "Classification": "classify"}
        task_label   = self._batch_task_var.get()
        task         = task_map.get(task_label, "detect")
        device       = self._batch_device_var.get()
        imgsz        = self._batch_imgsz_var.get()
        conf         = self._batch_conf_var.get()
        iou          = self._batch_iou_var.get()
        half         = self._batch_half_var.get()
        output_dir   = self._batch_output_dir.get().strip() or None

        # ── Tên thư mục kết quả theo quy chuẩn thời gian_Ngày_Loạitest ──
        task_short = {"detect": "Detection", "segment": "Segmentation",
                      "classify": "Classification"}.get(task, task_label)
        run_name = datetime.now().strftime(f"%H%M%S_%Y%m%d") + f"_{task_short}"
        mode_txt = "Predict+Accuracy" if calc_accuracy else "Predict"

        self._batch_log("─" * 65, "info")
        self._batch_log(f"  RUN  : {run_name}", "ok")
        self._batch_log(f"  Model: {Path(model_path).name}", "info")
        self._batch_log(f"  Src  : {data_path}", "info")
        self._batch_log(f"  Mode : {mode_txt}  |  Task: {task_label}", "info")
        if task != "classify":
            self._batch_log(f"  Conf={conf}  IOU={iou}  Half={half}", "info")
        if output_dir:
            self._batch_log(f"  Dest : {output_dir}/{run_name}", "info")
        self._batch_log("─" * 65, "info")

        # ── Thu thập ảnh (luôn rglob để hỗ trợ cấu trúc thư mục lồng nhau) ─
        source: object = data_path
        if Path(data_path).is_dir():
            all_imgs = sorted(str(f) for f in Path(data_path).rglob("*")
                              if f.suffix.lower() in {ext.lower() for ext in self._IMG_EXTS})
            total_found = len(all_imgs)
            if total_found == 0:
                self._batch_log(f"[✗] Không tìm thấy ảnh trong: {data_path}", "err")
                self._batch_set_status("✗ Không tìm thấy ảnh", DANGER)
                return
            self._batch_log(f"[info] Tìm thấy {total_found} ảnh", "info")

            if self._batch_split_enable.get():
                split_n    = min(self._batch_split_n.get(), total_found)
                split_mode = self._batch_split_mode.get()
                if split_n < total_found:
                    source = (_rng.sample(all_imgs, split_n)
                              if split_mode == "random" else all_imgs[:split_n])
                    self._batch_log(
                        f"[Split/{split_mode}] {split_n}/{total_found} ảnh được chọn", "warn")
                else:
                    source = all_imgs
                    self._batch_log(f"[Split] {total_found} ảnh (tất cả)", "info")
            else:
                source = all_imgs

        try:
            _ensure_packages("ultralytics")
            YOLO   = _import_yolo()
            model  = YOLO(model_path, task=task)
            self._batch_log(f"[✔] Model tải xong: {Path(model_path).name}", "ok")
            self._batch_log("[→] Đang chạy predict...", "info")

            # ── Thu thập thông số model để so sánh bài báo ─────────────────
            _model_params_m, _model_gflops = self._get_model_stats(model, imgsz)
            if _model_params_m is not None:
                self._batch_log(f"[ℹ] Params: {_model_params_m:.4f} M  |  GFLOPs: {_model_gflops if _model_gflops is not None else 'N/A'}", "info")

            predict_kwargs = dict(
                source=source, imgsz=imgsz, device=device, half=half,
                save=True, save_txt=(task != "classify"), verbose=False,
                name=run_name,
            )
            if task != "classify":
                predict_kwargs["conf"] = conf
                predict_kwargs["iou"]  = iou
            if output_dir:
                predict_kwargs["project"] = output_dir

            results  = model.predict(**predict_kwargs)
            n        = len(results)
            save_dir = Path(getattr(results[0], "save_dir", "") if results else "")

            self._batch_log(f"[✔] Predict xong — {n} ảnh", "ok")

            # ══════════════════════════════════════════════════════════════
            # CLASSIFICATION — log chi tiết từng ảnh + tách class folder
            # ══════════════════════════════════════════════════════════════
            if task == "classify":
                cls_counts: dict = defaultdict(int)
                # map: class_name → [(tên file output, Path ảnh gốc)]
                cls_files: dict  = defaultdict(list)  # (fname_output, Path_src)
                # ảnh bị lọc vào non_disease
                non_disease_files: list = []   # list of (fname_output, Path_src)
                # ngưỡng lọc: 2 class thấp hơn đều > NON_DIS_THR → không chắc → non_disease
                NON_DIS_THR = 0.20

                self._batch_log("", "")
                self._batch_log(
                    f"  #    {'Ảnh':<34} {'Dự đoán':<18} {'Top1':>6}  {'Top2':>6}  {'Top3':>6}  {'Flag'}", "info")
                self._batch_log("  " + "─" * 78, "info")

                for idx, r in enumerate(results, 1):
                    img_name = Path(r.path).name
                    if r.probs is None:
                        self._batch_log(
                            f"  {idx:>4}  {img_name:<34} {'—':<18} {'—':>6}  {'—':>6}  {'—':>6}  ⚠ no probs", "warn")
                        continue

                    probs_data  = r.probs.data          # tensor tất cả class
                    num_classes = len(probs_data)

                    pred_id   = int(r.probs.top1)
                    pred_name = r.names.get(pred_id, f"cls{pred_id}")
                    top1_conf = float(r.probs.top1conf) if hasattr(r.probs, "top1conf") else float(probs_data[pred_id])

                    # Lấy top2, top3 conf
                    sorted_confs = sorted(float(v) for v in probs_data)[::-1]
                    top2_conf = sorted_confs[1] if num_classes >= 2 else 0.0
                    top3_conf = sorted_confs[2] if num_classes >= 3 else 0.0

                    # ── Thuật toán lọc non_disease ─────────────────────────
                    # Nếu top2 > NON_DIS_THR VÀ top3 > NON_DIS_THR
                    # → model không tự tin, ảnh không rõ bệnh → non_disease
                    is_non_disease = (num_classes >= 3
                                      and top2_conf > NON_DIS_THR
                                      and top3_conf > NON_DIS_THR)

                    entry = (Path(r.path).name, Path(r.path))

                    if is_non_disease:
                        non_disease_files.append(entry)
                        flag = "⚠ non_disease"
                        tag  = "warn"
                    else:
                        cls_counts[pred_name] += 1
                        cls_files[pred_name].append(entry)
                        flag = "✔"
                        tag  = "ok" if top1_conf >= 0.8 else ("warn" if top1_conf >= 0.5 else "err")

                    self._batch_log(
                        f"  {idx:>4}  {img_name:<34} {pred_name:<18} "
                        f"{top1_conf:>6.3f}  {top2_conf:>6.3f}  {top3_conf:>6.3f}  {flag}", tag)

                n_valid      = sum(cls_counts.values())
                n_nondisease = len(non_disease_files)

                # ── Tạo subfolder labeled/ và raw/ theo class ────────────
                if save_dir and save_dir.exists():
                    labeled_root = save_dir / "labeled"
                    raw_root     = save_dir / "raw"
                    labeled_root.mkdir(exist_ok=True)
                    raw_root.mkdir(exist_ok=True)
                    created_dirs = []

                    # Class folders (bệnh rõ ràng)
                    all_cls_entries = dict(cls_files)
                    if non_disease_files:
                        all_cls_entries["non_disease"] = non_disease_files

                    for cls_name, entries in all_cls_entries.items():
                        lbl_dir = labeled_root / cls_name
                        raw_dir = raw_root     / cls_name
                        lbl_dir.mkdir(exist_ok=True)
                        raw_dir.mkdir(exist_ok=True)
                        moved_lbl = moved_raw = 0
                        for fname_out, src_path in entries:
                            lbl_src = save_dir / fname_out
                            if lbl_src.exists():
                                try:
                                    shutil.move(str(lbl_src), str(lbl_dir / fname_out))
                                    moved_lbl += 1
                                except Exception:
                                    pass
                            if src_path.exists():
                                try:
                                    shutil.copy2(str(src_path), str(raw_dir / src_path.name))
                                    moved_raw += 1
                                except Exception:
                                    pass
                        prefix = "⚠" if cls_name == "non_disease" else "✔"
                        created_dirs.append(
                            f"{prefix} {cls_name}/  labeled={moved_lbl}  raw={moved_raw}")

                    self._batch_log("", "")
                    self._batch_log("[✔] Thư mục kết quả:", "ok")
                    self._batch_log(f"    📂 labeled/  ← ảnh có nhãn (YOLO output)", "info")
                    self._batch_log(f"    📂 raw/      ← ảnh gốc (data thô)", "info")
                    for d in created_dirs:
                        self._batch_log(f"       ├─ {d}",
                                        "warn" if "non_disease" in d else "ok")

                # ── Summary per-class (chỉ ảnh hợp lệ) ───────────────────
                self._batch_log("", "")
                self._batch_log("═" * 70, "ok")
                self._batch_log(
                    f"  TỔNG KẾT QUẢ PHÂN LOẠI  ({n} ảnh tổng  |  "
                    f"{n_valid} hợp lệ  |  {n_nondisease} non_disease)", "ok")
                self._batch_log("═" * 70, "ok")
                for cls_name, cnt in sorted(cls_counts.items(), key=lambda x: -x[1]):
                    pct     = cnt / n_valid * 100 if n_valid > 0 else 0.0
                    bar_len = int(pct / 5)
                    bar     = "█" * bar_len + "░" * (20 - bar_len)
                    self._batch_log(
                        f"  {cls_name:<22} [{bar}]  {cnt:>4} ảnh  ({pct:5.1f}%)", "info")
                if n_nondisease:
                    pct_nd = n_nondisease / n * 100 if n > 0 else 0.0
                    self._batch_log(
                        f"  {'non_disease':<22} {'░'*20}  {n_nondisease:>4} ảnh  ({pct_nd:5.1f}%)  [đã loại]", "warn")
                self._batch_log("─" * 70, "info")
                self._batch_log(
                    f"  ℹ️  Ngưỡng non_disease: top2 > {NON_DIS_THR} AND top3 > {NON_DIS_THR}", "warn")
                self._batch_log("─" * 70, "info")

                # ── ACCURACY (tính trên ảnh hợp lệ, loại non_disease) ────
                acc_stats: dict = {}
                accuracy: float | None = None
                if calc_accuracy:
                    correct = total_acc = 0
                    acc_stats = defaultdict(lambda: {"correct": 0, "total": 0})
                    # mismatches: list of (true, pred, img_name) để debug
                    mismatches: list[tuple[str, str, str]] = []

                    self._batch_log("─" * 70, "info")
                    self._batch_log(
                        f"  {'#':>4}  {'Ảnh':<30}  {'GT':<18}  {'Dự đoán':<18}  Top1    OK?",
                        "info")
                    self._batch_log("─" * 70, "info")

                    # NOTE: ultralytics trả r.path = "image0.jpg" khi source là list
                    # → dùng source[i] để lấy path gốc
                    for idx, (r, orig_path) in enumerate(zip(results, source), 1):
                        if r.probs is None:
                            continue

                        pred_id   = int(r.probs.top1)
                        pred_name = r.names.get(pred_id, f"cls{pred_id}").lower().strip()
                        true_name = Path(orig_path).parent.name.lower().strip()
                        top1_conf = float(r.probs.top1conf)
                        img_name  = Path(orig_path).name

                        # ── So sánh chuẩn hóa (bỏ 'cow'/'cows', normalize sep) ──
                        pred_norm  = self._normalize_class_name(pred_name)
                        true_norm  = self._normalize_class_name(true_name)
                        is_correct = (pred_norm == true_norm)

                        total_acc += 1
                        acc_stats[true_name]["total"] += 1
                        if is_correct:
                            correct += 1
                            acc_stats[true_name]["correct"] += 1
                            flag = "✅"
                        else:
                            mismatches.append((true_name, pred_name, img_name))
                            flag = "❌"

                        self._batch_log(
                            f"  {idx:>4}  {img_name:<30}  {true_name:<18}"
                            f"  {pred_name:<18}  {top1_conf:5.1%}   {flag}",
                            "ok" if is_correct else "err")

                    accuracy = (correct / total_acc * 100) if total_acc > 0 else 0.0
                    self._batch_log("═" * 70, "ok")
                    self._batch_log(
                        f"  🎯 ACCURACY: {accuracy:.2f}%  ({correct}/{total_acc})  "
                        f"| loại non_disease = {n_nondisease}", "ok")
                    self._batch_log("─" * 70, "info")
                    for cls_name, stat in sorted(acc_stats.items()):
                        cls_acc = (stat["correct"] / stat["total"] * 100) \
                                   if stat["total"] > 0 else 0.0
                        bar_len  = int(cls_acc / 5)
                        self._batch_log(
                            f"    GT [{cls_name:<18}]  {'█'*bar_len:<20}  {cls_acc:6.2f}%"
                            f"  ({stat['correct']:>3}/{stat['total']:>3})", "info")
                    if mismatches:
                        self._batch_log("─" * 70, "warn")
                        self._batch_log(
                            f"  ⚠  {len(mismatches)} ảnh dự đoán SAI — kiểm tra tên folder vs model.names:", "warn")
                        for true_n, pred_n, img_n in mismatches[:20]:
                            self._batch_log(
                                f"     GT={true_n:<18}  Pred={pred_n:<18}  {img_n}", "warn")
                        if len(mismatches) > 20:
                            self._batch_log(
                                f"     ... và {len(mismatches)-20} ảnh sai khác (truncated)", "warn")
                    self._batch_log("═" * 70, "ok")
                    batch_result = {
                        "model":             Path(model_path).name,
                        "task":              task_label,
                        "run":               run_name,
                        "ảnh tổng":          str(n),
                        "ảnh hợp lệ":        str(n_valid),
                        "non_disease":       str(n_nondisease),
                        "mode":              "Classify + Accuracy (exact match)",
                        f"Accuracy (valid {total_acc})": f"{accuracy:.2f}%  ({correct}/{total_acc})",
                        "sai":               str(len(mismatches)),
                        "lưu tại":           str(save_dir),
                    }
                    for cls_name, stat in sorted(acc_stats.items()):
                        cls_acc = (stat["correct"] / stat["total"] * 100) \
                                   if stat["total"] > 0 else 0.0
                        batch_result[f"  GT:{cls_name}"] = \
                            f"{cls_acc:.1f}%  ({stat['correct']}/{stat['total']})"
                    self._batch_set_status(
                        f"✔ Accuracy: {accuracy:.2f}% | valid={n_valid} non_dis={n_nondisease}", SUCCESS)
                else:
                    batch_result = {
                        "model":       Path(model_path).name,
                        "task":        task_label,
                        "run":         run_name,
                        "ảnh tổng":    str(n),
                        "ảnh hợp lệ":  str(n_valid),
                        "non_disease": str(n_nondisease),
                        "mode":        "Classify (không tính Accuracy)",
                        "lưu tại":     str(save_dir),
                    }
                    for cls_name, cnt in sorted(cls_counts.items(), key=lambda x: -x[1]):
                        pct = cnt / n_valid * 100 if n_valid > 0 else 0.0
                        batch_result[f"  {cls_name}"] = f"{cnt} ảnh  ({pct:.1f}%)"
                    batch_result["  non_disease"] = f"{n_nondisease} ảnh (đã loại)"
                    self._batch_set_status(
                        f"✔ Phân loại xong — valid={n_valid}  non_dis={n_nondisease}", SUCCESS)
                chart_data = {
                    "type": "classification",
                    "cls_counts": dict(cls_counts),
                    "n_valid": n_valid,
                    "n_nondisease": n_nondisease,
                    "n_total": n,
                    "acc_stats": {k: dict(v) for k, v in acc_stats.items()} if calc_accuracy else {},
                    "accuracy": accuracy if calc_accuracy else None,
                }

            # ══════════════════════════════════════════════════════════════
            # DETECT / SEGMENT — thống kê object theo class
            # ══════════════════════════════════════════════════════════════
            else:
                cls_counts: dict = defaultdict(int)
                for r in results:
                    if r.boxes is not None:
                        names_map = r.names if hasattr(r, "names") else {}
                        for box in r.boxes:
                            cls_counts[names_map.get(int(box.cls[0]), f"cls{int(box.cls[0])}")] += 1

                total_dets = sum(cls_counts.values())
                self._batch_log("", "")
                self._batch_log("═" * 65, "ok")
                self._batch_log(f"  TỔNG KẾT QUẢ {task_label.upper()}  ({n} ảnh  |  {total_dets} objects)", "ok")
                self._batch_log("═" * 65, "ok")
                for cls_name, cnt in sorted(cls_counts.items(), key=lambda x: -x[1]):
                    pct     = cnt / total_dets * 100 if total_dets > 0 else 0.0
                    bar_len = int(pct / 5)
                    bar     = "█" * bar_len + "░" * (20 - bar_len)
                    self._batch_log(
                        f"  {cls_name:<22} [{bar}]  {cnt:>5}  ({pct:5.1f}%)", "info")
                if cls_counts:
                    top_cls = max(cls_counts, key=cls_counts.get)
                    self._batch_log("─" * 65, "info")
                    self._batch_log(
                        f"  → Chiếm ưu thế: \"{top_cls}\"  {cls_counts[top_cls]}/{total_dets} objects", "ok")
                self._batch_log("═" * 65, "ok")

                count_label = "tổng detected objects"
                batch_result = {
                    "model": Path(model_path).name, "task": task_label,
                    "run": run_name, "ảnh xử lý": str(n),
                    "conf": f"{conf:.2f}", "iou": f"{iou:.2f}",
                    count_label: str(total_dets), "lưu tại": str(save_dir),
                }
                for cls_name, cnt in sorted(cls_counts.items(), key=lambda x: -x[1])[:10]:
                    pct = cnt / total_dets * 100 if total_dets > 0 else 0.0
                    batch_result[f"  {cls_name}"] = f"{cnt}  ({pct:.1f}%)"
                self._batch_set_status(f"✔ {task_label} xong — {n} ảnh", SUCCESS)
                chart_data = {
                    "type": "detection",
                    "task": task_label,
                    "cls_counts": dict(cls_counts),
                    "total": total_dets,
                }

            self._batch_log(f"\n[✔] Kết quả lưu tại: {save_dir}", "ok")
            self._eval_results = batch_result
            self.after(0, self._eval_show_results, batch_result)
            self.after(200, self._batch_draw_chart, chart_data)

            # ── So sánh với bài báo (hậu kì) ────────────────────────────────
            if self._bench_canvas is not None:
                _accuracy_val = None
                if calc_accuracy:
                    try:
                        for k, v in batch_result.items():
                            if "Accuracy" in k and "%" in str(v):
                                _accuracy_val = float(str(v).split("%")[0].strip())
                                break
                    except Exception:
                        pass
                _test_count = n if "n" in dir() else None
                _bench_info = {
                    "architecture": f"YOLOv8 ({task_label})",
                    "classes":      len(model.names) if hasattr(model, "names") else "—",
                    "input_size":   f"{imgsz}×{imgsz}",
                    "params_m":     _model_params_m,
                    "gflops":       _model_gflops,
                    "optimizer":    "AdamW / SGD (YOLO default)",
                    "loss_fn":      "BCE + DFL / CrossEntropyLoss",
                    "accuracy":     _accuracy_val,
                    "accuracy_str": (f"{_accuracy_val:.2f}%" if _accuracy_val is not None else "—"),
                    "map50":        None,
                    "map50_95":     None,
                    "test_images":  _test_count,
                    "augmentation": "Mosaic, Flip, HSV (YOLO default)",
                }
                self.after(500, self._draw_benchmark_comparison, _bench_info)

        except Exception:
            err = _tb.format_exc()
            self._batch_log(f"[✗] Lỗi:\n{err}", "err")
            self._batch_set_status("✗ Lỗi khi batch predict", DANGER)
        finally:
            self._batch_running = False
            self.after(0, self._restore_eval_primary_button)

    # ─────────────────────────────────────────────────────────────────────────
    # BATCH PREDICT — BIỂU ĐỒ
    # ─────────────────────────────────────────────────────────────────────────

    def _batch_draw_no_chart(self, msg="📊 Không có dữ liệu biểu đồ"):
        def _draw():
            c = self._batch_chart_canvas
            c.delete("all")
            w = max(c.winfo_width(), 300)
            h = max(c.winfo_height(), 160)
            c.create_text(w // 2, h // 2, text=msg,
                          fill=TEXT_DIM, font=("Segoe UI", 9), justify="center")
            self._set_chart_caption("eval", "Chưa có dữ liệu biểu đồ batch")
        self.after(0, _draw)

    def _batch_draw_chart(self, chart_data: dict):
        """Vẽ biểu đồ matplotlib vào _batch_chart_canvas."""
        if not chart_data:
            self._batch_draw_no_chart()
            return
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import matplotlib.gridspec as gridspec
            from PIL import Image as _PIL, ImageTk as _ITK
            import io, math

            BG_FIG   = "#1e1e2e"
            BG_AX    = "#13131f"
            C_TICK   = "#9090b0"
            C_SPINE  = "#333350"
            C_TITLE  = "#c0c0e0"
            PALETTE  = ["#22c55e", "#ef4444", "#38bdf8", "#f59e0b",
                        "#a78bfa", "#fb923c", "#34d399", "#f472b6",
                        "#60a5fa", "#f87171", "#4ade80", "#fbbf24"]

            c  = self._batch_chart_canvas
            cw = max(c.winfo_width(),  500)
            ch = max(c.winfo_height(), 220)

            chart_type = chart_data.get("type", "")

            if chart_type == "classification":
                cls_counts   = chart_data.get("cls_counts", {})
                n_nondisease = chart_data.get("n_nondisease", 0)
                n_valid      = chart_data.get("n_valid", 0)
                acc_stats    = chart_data.get("acc_stats", {})
                accuracy     = chart_data.get("accuracy")

                has_acc = bool(acc_stats)
                ncols   = 3 if has_acc else 2
                fig     = plt.figure(figsize=(cw / 96, ch / 96), dpi=96)
                fig.patch.set_facecolor(BG_FIG)
                gs = gridspec.GridSpec(1, ncols, figure=fig, wspace=0.4)

                # ─── (1) Pie chart class distribution (valid only) ──────
                ax1 = fig.add_subplot(gs[0, 0])
                ax1.set_facecolor(BG_AX)
                ax1.tick_params(colors=C_TICK)
                for sp in ax1.spines.values():
                    sp.set_color(C_SPINE)
                if cls_counts:
                    labels = list(cls_counts.keys())
                    sizes  = [cls_counts[l] for l in labels]
                    colors = [PALETTE[i % len(PALETTE)] for i in range(len(labels))]
                    wedge_props = {"linewidth": 0.5, "edgecolor": BG_FIG}
                    ax1.pie(sizes, labels=labels, colors=colors,
                            autopct="%1.1f%%", startangle=90,
                            wedgeprops=wedge_props,
                            textprops={"color": C_TITLE, "fontsize": 7})
                    ax1.set_title(f"Phân bố class\n(valid={n_valid})",
                                  color=C_TITLE, fontsize=8, pad=4)
                else:
                    ax1.text(0.5, 0.5, "Không có dữ liệu", ha="center",
                             va="center", color=C_TICK, transform=ax1.transAxes)

                # ─── (2) Bar chart: valid vs non_disease ────────────────
                ax2 = fig.add_subplot(gs[0, 1])
                ax2.set_facecolor(BG_AX)
                ax2.tick_params(colors=C_TICK, labelsize=7)
                for sp in ax2.spines.values():
                    sp.set_color(C_SPINE)

                all_counts = list(cls_counts.items())
                if n_nondisease:
                    all_counts.append(("non_disease", n_nondisease))
                if all_counts:
                    bar_labels = [x[0] for x in all_counts]
                    bar_vals   = [x[1] for x in all_counts]
                    bar_colors = [PALETTE[i % len(PALETTE)] for i in range(len(bar_labels))]
                    bars = ax2.bar(range(len(bar_labels)), bar_vals,
                                   color=bar_colors, edgecolor=BG_FIG, linewidth=0.4)
                    ax2.set_xticks(range(len(bar_labels)))
                    ax2.set_xticklabels(bar_labels, rotation=30, ha="right", fontsize=6)
                    ax2.set_ylabel("Số ảnh", color=C_TICK, fontsize=7)
                    ax2.set_title("Số lượng ảnh mỗi class",
                                  color=C_TITLE, fontsize=8, pad=4)
                    for bar, val in zip(bars, bar_vals):
                        ax2.text(bar.get_x() + bar.get_width() / 2,
                                 bar.get_height() + max(bar_vals) * 0.01,
                                 str(val), ha="center", va="bottom",
                                 color=C_TICK, fontsize=6)

                # ─── (3) Accuracy per class bar (if calc_accuracy) ──────
                if has_acc:
                    ax3 = fig.add_subplot(gs[0, 2])
                    ax3.set_facecolor(BG_AX)
                    ax3.tick_params(colors=C_TICK, labelsize=7)
                    for sp in ax3.spines.values():
                        sp.set_color(C_SPINE)

                    cls_names = sorted(acc_stats.keys())
                    accs = []
                    for cn in cls_names:
                        stat = acc_stats[cn]
                        t = stat["total"] if isinstance(stat, dict) else 0
                        cr = stat["correct"] if isinstance(stat, dict) else 0
                        accs.append(cr / t * 100 if t > 0 else 0.0)
                    acc_colors = [PALETTE[i % len(PALETTE)] for i in range(len(cls_names))]
                    bars3 = ax3.bar(range(len(cls_names)), accs,
                                    color=acc_colors, edgecolor=BG_FIG, linewidth=0.4)
                    ax3.set_ylim(0, 110)
                    ax3.axhline(accuracy or 0, color="#f59e0b", linewidth=1,
                                linestyle="--", label=f"Overall {accuracy:.1f}%")
                    ax3.set_xticks(range(len(cls_names)))
                    ax3.set_xticklabels(cls_names, rotation=30, ha="right", fontsize=6)
                    ax3.set_ylabel("Accuracy (%)", color=C_TICK, fontsize=7)
                    ax3.set_title(f"Accuracy per class\n(Overall {accuracy:.1f}%)" if accuracy is not None
                                  else "Accuracy per class",
                                  color=C_TITLE, fontsize=8, pad=4)
                    ax3.legend(fontsize=6, facecolor=BG_FIG, labelcolor=C_TITLE, framealpha=0.5)
                    for bar, val in zip(bars3, accs):
                        ax3.text(bar.get_x() + bar.get_width() / 2,
                                 val + 1.5, f"{val:.1f}%",
                                 ha="center", va="bottom", color=C_TICK, fontsize=6)

            elif chart_type == "detection":
                cls_counts = chart_data.get("cls_counts", {})
                total_dets = chart_data.get("total", 0)
                task_label = chart_data.get("task", "Detection")

                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(cw / 96, ch / 96), dpi=96)
                fig.patch.set_facecolor(BG_FIG)
                for ax in (ax1, ax2):
                    ax.set_facecolor(BG_AX)
                    ax.tick_params(colors=C_TICK, labelsize=7)
                    for sp in ax.spines.values():
                        sp.set_color(C_SPINE)

                # Pie
                if cls_counts:
                    labels = list(cls_counts.keys())
                    sizes  = [cls_counts[l] for l in labels]
                    colors = [PALETTE[i % len(PALETTE)] for i in range(len(labels))]
                    ax1.pie(sizes, labels=labels, colors=colors,
                            autopct="%1.1f%%", startangle=90,
                            wedgeprops={"linewidth": 0.5, "edgecolor": BG_FIG},
                            textprops={"color": C_TITLE, "fontsize": 7})
                ax1.set_title(f"Phân bố {task_label}\n(tổng={total_dets})",
                              color=C_TITLE, fontsize=8, pad=4)

                # Bar
                if cls_counts:
                    sorted_cls = sorted(cls_counts.items(), key=lambda x: -x[1])[:12]
                    bl = [x[0] for x in sorted_cls]
                    bv = [x[1] for x in sorted_cls]
                    bc = [PALETTE[i % len(PALETTE)] for i in range(len(bl))]
                    bars = ax2.barh(range(len(bl)), bv, color=bc,
                                   edgecolor=BG_FIG, linewidth=0.4)
                    ax2.set_yticks(range(len(bl)))
                    ax2.set_yticklabels(bl, fontsize=7)
                    ax2.set_xlabel("Số objects", color=C_TICK, fontsize=7)
                    ax2.set_title("Objects mỗi class",
                                  color=C_TITLE, fontsize=8, pad=4)
                    for bar, val in zip(bars, bv):
                        ax2.text(bar.get_width() + max(bv) * 0.01,
                                 bar.get_y() + bar.get_height() / 2,
                                 str(val), va="center", color=C_TICK, fontsize=6)
            else:
                self._batch_draw_no_chart()
                return

            plt.tight_layout(pad=1.2)
            buf = io.BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight",
                        facecolor=fig.get_facecolor())
            plt.close(fig)
            buf.seek(0)

            img = _PIL.open(buf).convert("RGB")
            tk_img, fitted = self._paint_pil_on_canvas(c, img, min_w=500, min_h=220)
            self._batch_chart_tk_img = tk_img
            self._batch_chart_pil_img = fitted
            if chart_type == "classification":
                self._set_chart_caption("eval", "Biểu đồ batch classification: phân bố class và accuracy")
            elif chart_type == "detection":
                self._set_chart_caption("eval", "Biểu đồ batch YOLO: phân bố object theo class")
            self._batch_log("[✔] Biểu đồ đã được vẽ", "ok")

        except ImportError as e:
            self._batch_draw_no_chart(f"⚠ Cần cài matplotlib + Pillow\n({e})")
        except Exception as ex:
            self._batch_log(f"[warn] Lỗi vẽ biểu đồ: {ex}", "warn")
            self._batch_draw_no_chart(f"⚠ Lỗi vẽ biểu đồ:\n{ex}")

    def _batch_save_chart(self):
        """Lưu biểu đồ batch predict thành file PNG."""
        import datetime
        if self._batch_chart_pil_img is None:
            messagebox.showinfo("Thông báo", "Chưa có biểu đồ để lưu. Hãy chạy dự đoán theo lô trước.")
            return
        self._save_chart_pil_image(
            self._batch_chart_pil_img,
            title="Lưu biểu đồ dự đoán theo lô",
            initialfile=f"batch_chart_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
        )

    def _eval_browse_model_file(self):
        f = filedialog.askopenfilename(
            title="Chọn file model YOLO (.pt)",
            filetypes=[("YOLO model", "*.pt"),
                       ("All files", "*.*")],
            initialdir=str(ROOT_DIR),
        )
        if f:
            self._eval_model_dir.set(f)

    def _eval_browse_model_folder(self):
        d = filedialog.askdirectory(title="Chọn thư mục model (chứa weights/)",
                                    initialdir=str(ROOT_DIR))
        if d:
            self._eval_model_dir.set(d)

    def _eval_browse_yaml(self):
        f = filedialog.askopenfilename(
            title="Chọn data.yaml",
            filetypes=[("YAML", "*.yaml *.yml"), ("All", "*.*")],
            initialdir=str(ROOT_DIR),
        )
        if f:
            self._eval_data_path.set(f)
            self._unified_refresh_count()

    def _eval_show_model_config(self):
        path = self._eval_model_dir.get().strip()
        if not path:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn file model .pt để xem cấu hình.")
            return
        if Path(path).is_dir():
            candidates = ["best.pt", "last.pt"]
            found = next((Path(path) / c for c in candidates if (Path(path) / c).is_file()), None)
            if found is None:
                messagebox.showerror("Không tìm thấy", "Thư mục không chứa file .pt hợp lệ (best.pt/last.pt).")
                return
            path = str(found)
        if not Path(path).is_file():
            messagebox.showerror("Không tìm thấy", f"File không tồn tại:\n{path}")
            return
        threading.Thread(target=self._eval_read_model_config, args=(path,), daemon=True).start()

    def _eval_read_model_config(self, path: str):
        try:
            import torch
            from ultralytics import YOLO
            sections = {}
            ckpt = None
            try:
                ckpt = torch.load(path, map_location="cpu", weights_only=False)
            except Exception:
                ckpt = torch.load(path, map_location="cpu", weights_only=True)

            train_args = None
            if isinstance(ckpt, dict):
                train_args = ckpt.get("train_args") or ckpt.get("args")
                if isinstance(train_args, dict) or hasattr(train_args, "__dict__"):
                    if not isinstance(train_args, dict):
                        train_args = vars(train_args)
                    keys = [
                        "task", "data", "model", "epochs", "batch", "imgsz",
                        "lr0", "optimizer", "weight_decay", "dropout",
                        "label_smoothing", "cos_lr", "patience", "mosaic",
                        "mixup", "degrees", "hsv_s", "hsv_v", "amp",
                        "cache", "device", "project", "name",
                    ]
                    filtered = {k: train_args[k] for k in keys if k in train_args}
                    if filtered:
                        sections["⚙ Train Args"] = filtered
                    else:
                        sections["⚙ Train Args"] = {k: train_args.get(k) for k in sorted(train_args)}
                names = None
                for key in ("names", "model"):
                    obj = ckpt.get(key)
                    if obj is None:
                        continue
                    if isinstance(obj, dict) and "names" in obj:
                        names = obj["names"]
                        break
                    if hasattr(obj, "names"):
                        names = obj.names
                        break
                if names is not None:
                    sections["🏷 Class Names"] = names
                meta = {}
                for key in ("epoch", "best_fitness", "date", "mAP", "model"):
                    if ckpt.get(key) is not None:
                        meta[key] = ckpt.get(key)
                if meta:
                    sections["📅 Checkpoint"] = meta

            try:
                model = YOLO(path)
                info = model.info(verbose=False)
                arch = {}
                if isinstance(info, (list, tuple)) and len(info) >= 4:
                    arch["layers"] = int(info[0])
                    arch["parameters"] = f"{int(info[1]):,} ({int(info[1]) / 1e6:.2f} M)"
                    arch["GFLOPs"] = f"{float(info[3]):.3f}"
                if arch:
                    sections["📐 Model Info"] = arch
            except Exception:
                pass

            self.after(0, self._eval_open_model_config_window, path, sections, None)
        except Exception as ex:
            self.after(0, self._eval_open_model_config_window, path, {}, str(ex))

    def _eval_open_model_config_window(self, path: str, sections: dict, error: str | None):
        from tkinter import scrolledtext

        win = tk.Toplevel(self)
        win.title(f"Cấu hình model — {Path(path).name}")
        win.geometry("760x560")
        win.configure(bg=BG)
        tk.Label(win, text=f"🧾 Cấu hình model: {Path(path).name}",
                 font=("Segoe UI", 11, "bold"), bg=BG, fg=ACCENT2).pack(
                 padx=16, pady=(12, 4), anchor="w")
        tk.Label(win, text=path, font=("Segoe UI", 8), bg=BG, fg=TEXT_DIM).pack(
                 padx=16, anchor="w")
        txt = scrolledtext.ScrolledText(win, font=("Cascadia Code", 9), relief="flat", wrap="word")
        apply_textbox_theme(txt, dark=True)
        txt.pack(fill="both", expand=True, padx=16, pady=(8, 4))
        if error:
            txt.insert("end", f"❌ Lỗi khi đọc file:\n{error}\n")
        elif not sections:
            txt.insert("end", "⚠ Không tìm thấy thông tin cấu hình trong file này.\n")
        else:
            for title, data in sections.items():
                txt.insert("end", f"{'-' * 60}\n{title}\n{'-' * 60}\n")
                if isinstance(data, dict):
                    for key, value in data.items():
                        txt.insert("end", f"  {str(key):<28} {value}\n")
                elif isinstance(data, (list, tuple)):
                    for item in data:
                        txt.insert("end", f"  - {item}\n")
                else:
                    txt.insert("end", f"  {data}\n")
                txt.insert("end", "\n")
        txt.configure(state="disabled")

        def _copy():
            self.clipboard_clear()
            self.clipboard_append(txt.get("1.0", "end"))
            messagebox.showinfo("Sao chép", "Đã sao chép cấu hình vào bộ nhớ tạm.")

        bf = tk.Frame(win, bg=BG, pady=8)
        bf.pack(fill="x")
        tk.Button(bf, text="📋 Sao chép tất cả", font=("Segoe UI", 9),
                  bg=BG3, fg=TEXT, relief="flat", cursor="hand2", padx=12, pady=4,
                  command=_copy).pack(side="left", padx=16)
        tk.Button(bf, text="Đóng", font=("Segoe UI", 9),
                  bg=BG3, fg=TEXT_DIM, relief="flat", cursor="hand2", padx=12, pady=4,
                  command=win.destroy).pack(side="right", padx=16)

    def _eval_browse_data_folder(self):
        d = filedialog.askdirectory(title="Chọn thư mục dataset (Classification)",
                                    initialdir=str(ROOT_DIR))
        if d:
            self._eval_data_path.set(d)
            self._unified_refresh_count()

    def _input_load_entries(self):
        data = load_input_registry()
        if isinstance(data, dict) and isinstance(data.get("entries"), list):
            return data
        return {"entries": []}

    def _input_save_entries(self, data):
        try:
            save_input_registry(data)
        except Exception as ex:
            messagebox.showerror("Lỗi", f"Không thể lưu input.json:\n{ex}")

    def _eval_open_input_registry(self):
        import json
        dlg = tk.Toplevel(self)
        dlg.title("🏷 Quản lý đường dẫn YOLO Eval")
        dlg.configure(bg=BG2)
        dlg.resizable(False, False)
        dlg.grab_set()

        tk.Label(dlg, text="Quản lý danh sách đường dẫn dataset",
                 font=("Segoe UI", 10, "bold"), bg=BG2, fg=ACCENT2).pack(anchor="w", padx=14, pady=(10, 6))

        list_frame = tk.Frame(dlg, bg=BG2)
        list_frame.pack(fill="both", expand=True, padx=14, pady=(0, 6))
        listbox = tk.Listbox(list_frame, width=80, height=10, activestyle="none",
                             bg=BG3, fg=TEXT, selectbackground=ACCENT2, selectforeground="white",
                             font=("Segoe UI", 8))
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
        scrollbar.pack(side="right", fill="y")
        listbox.configure(yscrollcommand=scrollbar.set)

        def refresh_list():
            nonlocal data
            listbox.delete(0, "end")
            data = self._input_load_entries()
            for entry in data.get("entries", []):
                label = entry.get("name", "<Không tên>")
                path = entry.get("path", "")
                listbox.insert("end", f"{label} — {path}")
            return data

        data = refresh_list()

        def _select_entry():
            sel = listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            entry = data.get("entries", [])[idx]
            self._eval_data_path.set(entry.get("path", ""))
            self._unified_refresh_count()
            dlg.destroy()

        def _edit_entry():
            sel = listbox.curselection()
            if not sel:
                messagebox.showwarning("Chưa chọn", "Chọn một đường dẫn để sửa.", parent=dlg)
                return
            idx = sel[0]
            entry = data.get("entries", [])[idx]
            _open_editor(entry, idx)

        def _remove_entry():
            sel = listbox.curselection()
            if not sel:
                messagebox.showwarning("Chưa chọn", "Chọn một đường dẫn để xóa.", parent=dlg)
                return
            idx = sel[0]
            if not messagebox.askyesno("Xóa", "Xóa đường dẫn đã chọn khỏi input.json?", parent=dlg):
                return
            entries = data.get("entries", [])
            entries.pop(idx)
            self._input_save_entries({"entries": entries})
            refresh_list()

        def _open_editor(entry=None, index=None):
            edit_dlg = tk.Toplevel(dlg)
            edit_dlg.title("Thêm/Sửa đường dẫn")
            edit_dlg.configure(bg=BG2)
            edit_dlg.resizable(False, False)
            edit_dlg.grab_set()

            name_var = tk.StringVar(value=entry.get("name", "") if entry else "")
            path_var = tk.StringVar(value=entry.get("path", "") if entry else "")

            form = tk.Frame(edit_dlg, bg=BG2)
            form.pack(fill="x", padx=14, pady=10)
            tk.Label(form, text="Tên:", bg=BG2, fg=TEXT_DIM,
                     font=("Segoe UI", 8), width=12, anchor="w").grid(row=0, column=0, pady=4)
            ent_name = tk.Entry(form, textvariable=name_var, font=("Segoe UI", 9), width=44)
            apply_entry_theme(ent_name)
            ent_name.grid(row=0, column=1, pady=4, sticky="w")

            tk.Label(form, text="Đường dẫn:", bg=BG2, fg=TEXT_DIM,
                     font=("Segoe UI", 8), width=12, anchor="w").grid(row=1, column=0, pady=4)
            ent_path = tk.Entry(form, textvariable=path_var, font=("Segoe UI", 9), width=34)
            apply_entry_theme(ent_path)
            ent_path.grid(row=1, column=1, pady=4, sticky="w")
            tk.Button(form, text="📁", bg=BG3, fg=TEXT, relief="flat", padx=4,
                      cursor="hand2", command=lambda: _browse_path(path_var)).grid(row=1, column=2, padx=(4, 0))

            def _browse_path(var):
                choice = messagebox.askquestion(
                    "Chọn kiểu đường dẫn",
                    "Chọn thư mục dataset?\nYes: thư mục, No: file YAML",
                    parent=edit_dlg,
                )
                if choice == "yes":
                    p = filedialog.askdirectory(title="Chọn thư mục dataset", initialdir=str(ROOT_DIR))
                else:
                    p = filedialog.askopenfilename(
                        title="Chọn data.yaml",
                        filetypes=[("YAML", "*.yaml *.yml"), ("All", "*.*")],
                        initialdir=str(ROOT_DIR),
                    )
                if p:
                    var.set(p)

            def _save_entry():
                name = name_var.get().strip() or "Không tên"
                path = path_var.get().strip()
                if not path:
                    messagebox.showwarning("Thiếu dữ liệu", "Cần nhập đường dẫn.", parent=edit_dlg)
                    return
                entries = data.get("entries", [])
                if index is None:
                    entries.append({"name": name, "path": path})
                else:
                    entries[index] = {"name": name, "path": path}
                self._input_save_entries({"entries": entries})
                refresh_list()
                edit_dlg.destroy()

            btn_row = tk.Frame(edit_dlg, bg=BG2)
            btn_row.pack(fill="x", padx=14, pady=(0, 10))
            tk.Button(btn_row, text="✔ Lưu", bg=SUCCESS, fg="white", relief="flat",
                      padx=10, pady=4, cursor="hand2", command=_save_entry).pack(side="left", padx=(0, 4))
            tk.Button(btn_row, text="✖ Hủy", bg=DANGER, fg="white", relief="flat",
                      padx=10, pady=4, cursor="hand2", command=edit_dlg.destroy).pack(side="left")
            edit_dlg.update_idletasks()
            x = dlg.winfo_rootx() + (dlg.winfo_width() - edit_dlg.winfo_width()) // 2
            y = dlg.winfo_rooty() + (dlg.winfo_height() - edit_dlg.winfo_height()) // 2
            edit_dlg.geometry(f"+{x}+{y}")

        btn_row = tk.Frame(dlg, bg=BG2)
        btn_row.pack(fill="x", padx=14, pady=(0, 10))
        tk.Button(btn_row, text="📥 Load", bg=SUCCESS, fg="white", relief="flat",
                  padx=10, pady=4, cursor="hand2", command=_select_entry).pack(side="left")
        tk.Button(btn_row, text="➕ Thêm", bg=ACCENT, fg="white", relief="flat",
                  padx=10, pady=4, cursor="hand2", command=lambda: _open_editor(None, None)).pack(side="left", padx=4)
        tk.Button(btn_row, text="✏ Sửa", bg=BG3, fg=TEXT, relief="flat",
                  padx=10, pady=4, cursor="hand2", command=_edit_entry).pack(side="left", padx=4)
        tk.Button(btn_row, text="🗑 Xóa", bg=DANGER, fg="white", relief="flat",
                  padx=10, pady=4, cursor="hand2", command=_remove_entry).pack(side="left", padx=4)
        tk.Button(btn_row, text="✖ Đóng", bg=BG3, fg=TEXT_DIM, relief="flat",
                  padx=10, pady=4, cursor="hand2", command=dlg.destroy).pack(side="right")

        dlg.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dlg.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dlg.winfo_height()) // 2
        dlg.geometry(f"+{x}+{y}")

    # ─────────────────────────────────────────────────────────────────────────
    # ĐÁNH GIÁ MODEL — LOG HELPER
    # ─────────────────────────────────────────────────────────────────────────
    def _eval_log(self, text: str, tag: str = ""):
        def _write():
            self._eval_log_box.configure(state="normal")
            if tag:
                self._eval_log_box.insert("end", text + "\n", tag)
            else:
                self._eval_log_box.insert("end", text + "\n")
            self._eval_log_box.configure(state="disabled")
            self._eval_log_box.see("end")
        self.after(0, _write)

    def _eval_set_status(self, text: str, color: str = ""):
        fg = color or TEXT_DIM
        self.after(0, self._eval_status_lbl.configure, {"text": text, "fg": fg})

    # ─────────────────────────────────────────────────────────────────────────
    # BATCH PREDICT — LOG HELPER
    # ─────────────────────────────────────────────────────────────────────────
    def _batch_log(self, text: str, tag: str = ""):
        def _write():
            self._batch_log_box.configure(state="normal")
            if tag:
                self._batch_log_box.insert("end", text + "\n", tag)
            else:
                self._batch_log_box.insert("end", text + "\n")
            self._batch_log_box.configure(state="disabled")
            self._batch_log_box.see("end")
        self.after(0, _write)

    def _batch_set_status(self, text: str, color: str = ""):
        fg = color or TEXT_DIM
        self.after(0, self._batch_status_lbl.configure, {"text": text, "fg": fg})

    # ─────────────────────────────────────────────────────────────────────────
    # GENERIC BROWSE HELPERS
    # ─────────────────────────────────────────────────────────────────────────
    def _browse_file(self, var: tk.StringVar, title: str, filetypes: list):
        f = filedialog.askopenfilename(
            title=title, filetypes=filetypes, initialdir=str(ROOT_DIR))
        if f:
            var.set(f)

    def _browse_dir(self, var: tk.StringVar, title: str):
        d = filedialog.askdirectory(title=title, initialdir=str(ROOT_DIR))
        if d:
            var.set(d)

    # ── Batch data-folder browse (+ auto count) ───────────────────────────
    _IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif",
                 ".tiff", ".tif", ".webp", ".JPG", ".JPEG", ".PNG"}

    def _batch_browse_data_folder(self):
        d = filedialog.askdirectory(title="Chọn thư mục ảnh", initialdir=str(ROOT_DIR))
        if d:
            self._batch_data_path.set(d)
            self._batch_refresh_count()

    def _batch_refresh_count(self):
        """Đếm ảnh trong thư mục đang chọn và cập nhật UI."""
        path = self._batch_data_path.get().strip()
        if not path or not Path(path).is_dir():
            self._batch_img_count_lbl.configure(
                text="📊 (chưa chọn thư mục)", fg=TEXT_DIM)
            self._batch_img_total.set(0)
            self._batch_split_info_lbl.configure(text="")
            return
        imgs = [f for f in Path(path).rglob("*")
                if f.suffix in self._IMG_EXTS]
        n = len(imgs)
        self._batch_img_total.set(n)
        if n == 0:
            self._batch_img_count_lbl.configure(
                text="⚠ Không tìm thấy ảnh trong thư mục", fg=WARNING)
        else:
            self._batch_img_count_lbl.configure(
                text=f"📊 Tìm thấy  {n}  ảnh", fg=SUCCESS)
            # Clamp split_n to n
            if self._batch_split_n.get() > n:
                self._batch_split_n.set(n)
            try:
                self._batch_split_n_spin.configure(to=n)
            except Exception:
                pass
        self._batch_on_split_toggle()  # refresh info label

    def _batch_on_split_toggle(self):
        """Bật/tắt spinbox và radio khi toggle split checkbutton."""
        enabled = self._batch_split_enable.get()
        spin_state = "normal" if enabled else "disabled"
        try:
            self._batch_split_n_spin.configure(state=spin_state)
            for rb in self._batch_split_mode_radios:
                rb.configure(state=spin_state)
        except Exception:
            pass
        total = self._batch_img_total.get()
        if enabled and total > 0:
            n = min(self._batch_split_n.get(), total)
            pct = n / total * 100
            self._batch_split_info_lbl.configure(
                text=f"Sẽ dùng {n}/{total} ảnh ({pct:.0f}%)")
        else:
            self._batch_split_info_lbl.configure(text="")

    # ─────────────────────────────────────────────────────────────────────────
    # ĐÁNH GIÁ MODEL — RUN
    # ─────────────────────────────────────────────────────────────────────────
    def _eval_run(self):
        if self._eval_running:
            messagebox.showinfo("⏳", "Đánh giá đang chạy, vui lòng đợi.")
            return

        model_input = self._eval_model_dir.get().strip()
        data_path   = self._eval_data_path.get().strip()

        if not model_input or not data_path:
            messagebox.showerror("Thiếu thông tin", "Vui lòng chọn Model và Dataset.")
            return
        if not Path(data_path).exists():
            messagebox.showerror("Không tìm thấy dataset",
                f"Đường dẫn không tồn tại:\n{data_path}")
            return

        # Resolve model path
        model_path = None
        p = Path(model_input)
        if p.is_file() and p.suffix.lower() == ".pt":
            model_path = str(p)
        else:
            for cand in [p/"weights"/"best.pt", p/"weights"/"last.pt",
                         p/"best.pt", p/"last.pt"]:
                if cand.is_file():
                    model_path = str(cand); break
            if model_path is None:
                found = list(p.rglob("*.pt"))
                if found:
                    model_path = str(found[0])
        if model_path is None:
            messagebox.showerror("Không tìm thấy model",
                "Không tìm thấy file .pt.\n"
                "Chọn trực tiếp file (nút 📄) hoặc thư mục weights/ (nút 📁).")
            return

        self._eval_running = True
        self._eval_run_btn.configure(state="disabled", text="⏳ Đang đánh giá...")
        self._eval_set_status("⏳ Đang chạy đánh giá...", WARNING)
        self._eval_log_box.configure(state="normal")
        self._eval_log_box.delete("1.0", "end")
        self._eval_log_box.configure(state="disabled")

        threading.Thread(
            target=self._eval_thread,
            args=(model_path, data_path),
            daemon=True,
        ).start()

    def _eval_thread(self, model_path: str, data_path: str):
        import io, sys, tempfile, traceback as _tb, subprocess as _sp

        task_map = {"Detection": "detect",
                    "Instance Segmentation": "segment",
                    "Classification": "classify"}
        task_label = self._eval_task_var.get()
        task       = task_map.get(task_label, "detect")
        device     = self._eval_device_var.get()
        imgsz      = self._eval_imgsz_var.get()
        split      = self._eval_split_var.get()
        conf       = self._eval_conf_var.get()
        iou        = self._eval_iou_var.get()
        half       = self._eval_half_var.get()

        self._eval_log(f"[→] Model   : {model_path}", "info")
        self._eval_log(f"[→] Dataset : {data_path}", "info")
        self._eval_log(
            f"[→] Task={task}  split={split}  imgsz={imgsz}"
            f"  conf={conf}  iou={iou}  device={device}", "info")

        # ── Classification: wrap flat class folder into train/val/test structure ──
        _cls_tmp_dir = None
        if task == "classify" and Path(data_path).is_dir():
            _subdirs = {d.name.lower() for d in Path(data_path).iterdir() if d.is_dir()}
            if not _subdirs.intersection({"train", "val", "test"}):
                # Flat ImageFolder (class subfolders directly) — wrap with junction
                _cls_tmp_dir = Path(tempfile.mkdtemp(prefix="_yolo_cls_eval_"))
                _junction_target = str(Path(data_path).resolve())
                _junction_dst    = str(_cls_tmp_dir / split)
                _ret = _sp.run(
                    ["cmd", "/c", "mklink", "/J", _junction_dst, _junction_target],
                    capture_output=True, text=True)
                if _ret.returncode == 0:
                    self._eval_log(
                        f"[info] Flat class folder → tạo junction '{split}/' tạm thời.", "info")
                    data_path = str(_cls_tmp_dir)
                else:
                    # Junction failed (e.g. already exists) — try copy approach fallback
                    import shutil
                    (_cls_tmp_dir / split).mkdir(parents=True, exist_ok=True)
                    for _cf in Path(_junction_target).iterdir():
                        if _cf.is_dir():
                            (_cls_tmp_dir / split / _cf.name).symlink_to(_cf.resolve())
                    self._eval_log(
                        f"[info] Flat class folder → tạo symlink '{split}/' tạm thời.", "info")
                    data_path = str(_cls_tmp_dir)

        # ── Tự động tạo YAML tạm nếu detect/segment + folder ──────────────
        temp_yaml_path = None
        if task in ("detect", "segment") and Path(data_path).is_dir():
            self._eval_log("[info] Phát hiện thư mục ảnh cho detect/segment.", "info")
            self._eval_log("[info] Đang tạo YAML tạm...", "info")
            _ensure_packages("ultralytics")
            YOLO_pre = _import_yolo()
            try:
                _tmp_mdl = YOLO_pre(model_path, task=task)
                nc    = len(_tmp_mdl.names)
                names = list(_tmp_mdl.names.values())
            except Exception:
                nc    = 80
                names = [f"class{i}" for i in range(nc)]
            abs_data = str(Path(data_path).resolve()).replace("\\", "/")
            yaml_content = (
                f"path: {abs_data}\ntrain: .\nval: .\ntest: .\n"
                f"nc: {nc}\nnames: {names}\n"
            )
            temp_yaml_path = Path(tempfile.gettempdir()) / "_yolo_eval_temp.yaml"
            temp_yaml_path.write_text(yaml_content, encoding="utf-8")
            self._eval_log(f"[info] YAML tạm: {temp_yaml_path}", "info")
            self._eval_log("[warn] Đảm bảo thư mục có file .txt nhãn cho mỗi ảnh!", "warn")
            data_path = str(temp_yaml_path)

        try:
            _ensure_packages("ultralytics")
            YOLO = _import_yolo()
            model = YOLO(model_path, task=task)
            self._eval_log(f"[✔] Model: {Path(model_path).name}", "ok")

            buf = io.StringIO(); old_out = sys.stdout; sys.stdout = buf
            try:
                metrics = model.val(
                    data=data_path,
                    imgsz=imgsz,
                    device=device,
                    split=split,
                    conf=conf,
                    iou=iou,
                    half=half,
                    verbose=True,
                )
            finally:
                sys.stdout = old_out
                if temp_yaml_path and temp_yaml_path.exists():
                    try: temp_yaml_path.unlink()
                    except Exception: pass

            for line in buf.getvalue().splitlines()[-40:]:
                self._eval_log(line)

            self._eval_results = self._eval_parse_metrics(
                metrics, task_label, model_path, data_path, split)
            if _params_m is not None:
                self._eval_results["Params (M)"] = f"{_params_m:.4f}"
            if _gflops is not None:
                self._eval_results["GFLOPs"] = f"{_gflops:.3f}"
            self.after(0, self._eval_show_results, self._eval_results)
            # Ưu tiên confusion matrix cho classification, fallback results.csv chart cho YOLO
            if task == "classify" and self._eval_results.get("_confusion_matrix"):
                self.after(
                    200,
                    self._eval_draw_confusion_matrix,
                    self._eval_results.get("_class_names", []),
                    self._eval_results.get("_confusion_matrix", []),
                    "Confusion Matrix - Classification",
                )
            else:
                run_dir = self._eval_find_run_dir(model_path)
                if run_dir:
                    self.after(200, self._eval_plot_loss, run_dir)
            self._eval_set_status("✔ Đánh giá xong!", SUCCESS)

            # ── So sánh với bài báo (hậu kì) ─────────────────────────────
            if self._bench_canvas is not None:
                _r = self._eval_results
                _map50    = _r.get("mAP50") or _r.get("mAP@50") or None
                _map50_95 = _r.get("mAP50-95") or _r.get("mAP@50-95") or None
                _prec     = _r.get("Precision") or None
                _recall   = _r.get("Recall") or None
                _accuracy = (_r.get("Top-1 Accuracy") or _r.get("Top-1 Acc")
                              or _r.get("Accuracy") or None)
                # convert string: may be "0.7083  (70.83%)" or "0.92" → float
                def _f(v):
                    if v is None: return None
                    import re as _re
                    try:
                        # Extract first float-like number from string
                        m = _re.search(r'[\d.]+', str(v))
                        return float(m.group()) if m else None
                    except Exception: return None
                _map50    = _f(_map50)
                _map50_95 = _f(_map50_95)
                _accuracy = _f(_accuracy)
                _params_m, _gflops = self._get_model_stats(model, imgsz)
                # accuracy string for table
                if _accuracy is not None:
                    _acc_str = f"{_accuracy * 100:.2f}%" if _accuracy <= 1.0 else f"{_accuracy:.2f}%"
                elif _map50 is not None:
                    _acc_str = f"mAP50={_map50:.4f}"
                else:
                    _acc_str = "—"
                _bench_info = {
                    "architecture": f"YOLOv8 ({task_label})",
                    "classes":      len(model.names) if hasattr(model, "names") else "—",
                    "input_size":   f"{imgsz}×{imgsz}",
                    "params_m":     _params_m,
                    "gflops":       _gflops,
                    "optimizer":    "AdamW / SGD (YOLO default)",
                    "loss_fn":      "BCE + DFL / CrossEntropyLoss",
                    "accuracy":     (_accuracy * 100 if _accuracy and _accuracy <= 1.0 else _accuracy),
                    "accuracy_str": _acc_str,
                    "map50":        _map50,
                    "map50_95":     f"{_map50_95:.4f}" if _map50_95 is not None else None,
                    "test_images":  "—",
                    "augmentation": "Mosaic, Flip, HSV (YOLO default)",
                }
                self.after(500, self._draw_benchmark_comparison, _bench_info)

        except Exception:
            err = _tb.format_exc()
            self._eval_log(f"[✗] Lỗi:\n{err}", "err")
            self._eval_set_status("✗ Lỗi khi đánh giá", DANGER)
        finally:
            # Clean up temp classification wrapper dir
            if _cls_tmp_dir is not None:
                try:
                    import shutil as _shu
                    # Remove junction first (rmtree would follow the junction)
                    _junc = _cls_tmp_dir / split
                    if _junc.exists():
                        _sp.run(["cmd", "/c", "rd", str(_junc)],
                                capture_output=True)  # rd removes junction only
                    _shu.rmtree(_cls_tmp_dir, ignore_errors=True)
                except Exception:
                    pass
            self._eval_running = False
            self.after(0, self._restore_eval_primary_button)

    def _eval_parse_metrics(self, metrics, task_label: str,
                             model_path: str, data_path: str, split: str,
                             extra: dict | None = None) -> dict:
        """Trích xuất metrics từ kết quả model.val() tuỳ theo task."""
        result: dict = {
            "model":   Path(model_path).name,
            "task":    task_label,
            "dataset": Path(data_path).name,
            "split":   split,
        }
        try:
            if task_label == "Classification":
                # ultralytics >= 8.x: top1/top5 as float attr
                top1 = getattr(metrics, "top1", None)
                top5 = getattr(metrics, "top5", None)
                # Fallback: results_dict (newer ultralytics versions)
                if top1 is None:
                    try:
                        rd = getattr(metrics, "results_dict", {}) or {}
                        top1 = rd.get("metrics/accuracy_top1") or rd.get("top1")
                        top5 = rd.get("metrics/accuracy_top5") or rd.get("top5")
                    except Exception:
                        pass
                # Fallback: speed/fitness attrs sometimes wrap it
                if top1 is None:
                    try:
                        top1 = float(getattr(metrics, "fitness", None) or 0) or None
                    except Exception:
                        pass
                result["Top-1 Accuracy"] = self._fmt(top1)
                result["Top-5 Accuracy"] = self._fmt(top5)

                # Per-class accuracy (top1p) nếu ultralytics trả về
                top1p = getattr(metrics, "top1p", None)
                if top1p is None:
                    try:
                        rd = getattr(metrics, "results_dict", {}) or {}
                        top1p = rd.get("metrics/accuracy_top1p")
                    except Exception:
                        pass
                if top1p is not None:
                    try:
                        import numpy as _np
                        arr = _np.array(top1p).flatten()
                        result["Mean Per-Class Acc"] = self._fmt(float(_np.mean(arr)))
                        result["Min Per-Class Acc"]  = self._fmt(float(_np.min(arr)))
                    except Exception:
                        pass
                if extra:
                    result["Macro Precision"] = self._fmt(extra.get("macro_precision"))
                    result["Macro Recall"] = self._fmt(extra.get("macro_recall"))
                    result["Macro F1-Score"] = self._fmt(extra.get("macro_f1"))
                    result["Weighted F1-Score"] = self._fmt(extra.get("weighted_f1"))
                    result["Total Images"] = extra.get("total_images", "—")
                    per_class = extra.get("per_class_metrics") or []
                    if per_class:
                        worst = min(per_class, key=lambda item: float(item.get("f1", 0.0)))
                        best = max(per_class, key=lambda item: float(item.get("f1", 0.0)))
                        result["Best Class F1"] = (
                            f"{best['class_name']}: {float(best['f1']):.4f}"
                        )
                        result["Worst Class F1"] = (
                            f"{worst['class_name']}: {float(worst['f1']):.4f}"
                        )
                        for item in per_class:
                            result[f"Class: {item['class_name']}"] = (
                                f"P={float(item['precision']):.4f} | "
                                f"R={float(item['recall']):.4f} | "
                                f"F1={float(item['f1']):.4f} | "
                                f"Acc={float(item['accuracy']):.4f} | "
                                f"Support={int(item['support'])}"
                            )
                    result["_per_class_metrics"] = per_class
                    result["_confusion_matrix"] = extra.get("confusion_matrix", [])
                    result["_class_names"] = extra.get("class_names", [])
                    result["_prediction_distribution"] = extra.get("prediction_distribution", {})

            elif task_label == "Detection":
                box = getattr(metrics, "box", metrics)
                mp  = getattr(box, "mp", None)
                mr  = getattr(box, "mr", None)
                result["mAP@50"]    = self._fmt(getattr(box, "map50", None))
                result["mAP@50-95"] = self._fmt(getattr(box, "map",   None))
                result["Precision"] = self._fmt(mp)
                result["Recall"]    = self._fmt(mr)
                # F1 = 2PR/(P+R) — ultralytics không có .f1 scalar
                if mp is not None and mr is not None:
                    try:
                        p_val = float(mp); r_val = float(mr)
                        f1 = 2 * p_val * r_val / (p_val + r_val) if (p_val + r_val) > 0 else 0.0
                        result["F1 Score"] = self._fmt(f1)
                    except Exception:
                        result["F1 Score"] = "—"
                # Per-class mAP (maps array)
                maps  = getattr(box, "maps", None)
                names = getattr(metrics, "names", {})
                if maps is not None and names:
                    try:
                        import numpy as _np
                        arr = _np.array(maps).flatten()
                        for i, v in enumerate(arr[:10]):
                            cls_name = names.get(i, f"cls{i}")
                            result[f"  mAP {cls_name}"] = self._fmt(float(v))
                    except Exception:
                        pass

            elif task_label == "Instance Segmentation":
                box  = getattr(metrics, "box", metrics)
                mask = (getattr(metrics, "seg",   None) or
                        getattr(metrics, "mask",  None) or
                        getattr(metrics, "masks", None))
                mp_b = getattr(box, "mp", None)
                mr_b = getattr(box, "mr", None)
                result["Box mAP@50"]    = self._fmt(getattr(box, "map50", None))
                result["Box mAP@50-95"] = self._fmt(getattr(box, "map",   None))
                result["Box Precision"] = self._fmt(mp_b)
                result["Box Recall"]    = self._fmt(mr_b)
                if mp_b is not None and mr_b is not None:
                    try:
                        p_val = float(mp_b); r_val = float(mr_b)
                        f1 = 2 * p_val * r_val / (p_val + r_val) if (p_val + r_val) > 0 else 0.0
                        result["Box F1"] = self._fmt(f1)
                    except Exception:
                        result["Box F1"] = "—"
                if mask is not None:
                    mp_m = getattr(mask, "mp", None)
                    mr_m = getattr(mask, "mr", None)
                    result["Mask mAP@50"]    = self._fmt(getattr(mask, "map50", None))
                    result["Mask mAP@50-95"] = self._fmt(getattr(mask, "map",   None))
                    result["Mask Precision"] = self._fmt(mp_m)
                    result["Mask Recall"]    = self._fmt(mr_m)
                    if mp_m is not None and mr_m is not None:
                        try:
                            p_val = float(mp_m); r_val = float(mr_m)
                            f1 = 2*p_val*r_val/(p_val+r_val) if (p_val+r_val) > 0 else 0.0
                            result["Mask F1"] = self._fmt(f1)
                        except Exception:
                            result["Mask F1"] = "—"
                else:
                    result["Mask mAP@50"] = "— (không tìm thấy seg metrics)"

        except Exception as ex:
            result["parse_error"] = str(ex)
            self._eval_log(f"[warn] parse_metrics lỗi: {ex}", "warn")

        return result

    @staticmethod
    def _fmt(val) -> str:
        if val is None:
            return "—"
        try:
            import numpy as _np
            if hasattr(val, '__len__'):
                val = float(_np.mean(val))
            return f"{float(val):.4f}  ({float(val)*100:.2f}%)"
        except Exception:
            return str(val)

    def _eval_show_results(self, result: dict):
        """Cập nhật bảng metrics trên UI."""
        label_map = {
            "model":                  "🤖 Model",
            "task":                   "🎯 Task",
            "dataset":                "📂 Dataset",
            "split":                  "🔀 Split",
            "conf":                   "⚙ Conf",
            "iou":                    "⚙ IOU",
            "Params (M)":             "🧮 Params (M)",
            "GFLOPs":                 "⚡ GFLOPs",
            "FPS":                    "🎞 FPS",
            "Inference (ms)":         "⏱ Inference (ms)",
            "Layers":                 "🧱 Layers",
            # Classification
            "Top-1 Accuracy":         "✅ Top-1 Accuracy",
            "Top-5 Accuracy":         "✅ Top-5 Accuracy",
            "Mean Per-Class Acc":     "📊 Mean Per-Class Acc",
            "Min Per-Class Acc":      "📉 Min Per-Class Acc",
            "Macro Precision":        "🎯 Macro Precision",
            "Macro Recall":           "📡 Macro Recall",
            "Macro F1-Score":         "⚖ Macro F1-Score",
            "Weighted F1-Score":      "⚖ Weighted F1-Score",
            "Best Class F1":          "🏆 Best Class F1",
            "Worst Class F1":         "🧪 Worst Class F1",
            "Total Images":           "🖼 Total Images",
            # Detection
            "mAP@50":                 "✅ mAP@50",
            "mAP@50-95":              "✅ mAP@50-95",
            "Precision":              "🎯 Precision",
            "Recall":                 "📡 Recall",
            "F1 Score":               "⚖ F1 Score",
            # Segmentation
            "Box mAP@50":             "✅ Box mAP@50",
            "Box mAP@50-95":          "✅ Box mAP@50-95",
            "Box Precision":          "🎯 Box Precision",
            "Box Recall":             "📡 Box Recall",
            "Box F1":                 "⚖ Box F1",
            "Mask mAP@50":            "✅ Mask mAP@50",
            "Mask mAP@50-95":         "✅ Mask mAP@50-95",
            "Mask Precision":         "🎯 Mask Precision",
            "Mask Recall":            "📡 Mask Recall",
            "Mask F1":                "⚖ Mask F1",
            # Batch predict
            "mode":                     "🔧 Chế độ",
            "ảnh xử lý":                "🖼 Ảnh xử lý",
            "Accuracy":                 "🎯 Accuracy (Batch)",
            "Accuracy (folder GT)":     "🎯 Accuracy (folder GT)",
            "Sai":                      "❌ Sai",
            "tổng phân loại":           "📊 Tổng phân loại",
            "tổng objects":             "📦 Tổng objects",
            "tổng detected objects":    "📦 Tổng objects",
            "lưu tại":                  "💾 Lưu tại",
            "parse_error":              "⚠ Parse Error",
        }
        self._eval_render_summary_cards(result)
        # Skip internal/debug keys (starting with _)
        rows = [(label_map.get(k, k), v) for k, v in result.items()
                if not k.startswith("_")]
        self._eval_render_metrics_rows(rows)

    def _eval_find_run_dir(self, model_path: str) -> Path | None:
        """Tìm thư mục run chứa results.csv gần nhất với model_path."""
        p = Path(model_path)
        # Case 1: <run_dir>/weights/best.pt  →  <run_dir>
        if p.is_file() and p.parent.name == "weights":
            run_dir = p.parent.parent
            if (run_dir / "results.csv").exists():
                return run_dir
        # Case 2: file nằm ngay trong run_dir
        if p.is_file() and (p.parent / "results.csv").exists():
            return p.parent
        # Case 3: thư mục được chọn
        if p.is_dir() and (p / "results.csv").exists():
            return p
        # Case 4: tìm trong RUNS_DIR
        csv_candidates = list(RUNS_DIR.rglob("results.csv"))
        if csv_candidates:
            return max(csv_candidates, key=lambda x: x.stat().st_mtime).parent
        return None

    def _eval_refresh_chart(self):
        """Nút refresh: vẽ lại chart từ model/thư mục hiện tại."""
        model_input = self._eval_model_dir.get().strip()
        if not model_input:
            messagebox.showinfo("ℹ", "Chọn model trước.")
            return
        p = Path(model_input)
        # Nếu là file → dùng path file; nếu là thư mục → tự ghép weights/best.pt
        model_path = str(p) if p.is_file() else str(p / "weights" / "best.pt")
        run_dir = self._eval_find_run_dir(model_path)
        if run_dir is None and p.is_dir():
            run_dir = p  # thử thư mục trực tiếp
        if run_dir is None:
            self._eval_draw_no_chart()
            return
        self._eval_plot_loss(run_dir)

    def _eval_plot_loss(self, run_dir: Path):
        """Đọc results.csv và vẽ chart vào canvas."""
        csv_path = run_dir / "results.csv"
        if not csv_path.exists():
            self._eval_log(f"[info] Không tìm thấy results.csv tại {run_dir}", "warn")
            self._eval_draw_no_chart()
            return
        try:
            import csv, math
            rows = []
            with open(csv_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rows.append(row)
            if not rows:
                self._eval_draw_no_chart()
                return

            headers = [h.strip() for h in rows[0].keys()]

            # Chọn cột cần vẽ
            loss_cols = [h for h in headers if "loss" in h.lower()]
            metric_cols = [h for h in headers if any(k in h.lower()
                for k in ["map", "accuracy", "precision", "recall"])]
            plot_cols = (loss_cols + metric_cols)[:8]  # max 8 series

            if not plot_cols:
                self._eval_log("[warn] results.csv không có cột loss/metric để vẽ", "warn")
                self._eval_draw_no_chart()
                return

            epochs = []
            series: dict[str, list[float]] = {c: [] for c in plot_cols}
            for row in rows:
                try:
                    ep_val = row.get("epoch") or row.get(" epoch") or row.get("Epoch") or str(len(epochs))
                    epochs.append(int(float(ep_val.strip())))
                    for c in plot_cols:
                        val = row.get(c, "").strip()
                        series[c].append(float(val) if val else float("nan"))
                except Exception:
                    continue

            self.after(0, self._eval_draw_chart, epochs, series, plot_cols)

        except Exception as ex:
            self._eval_log(f"[warn] Không đọc được results.csv: {ex}", "warn")
            self._eval_draw_no_chart()

    def _eval_draw_no_chart(self):
        def _draw():
            c = self._eval_chart_canvas
            c.delete("all")
            c._pil_img = None
            w = c.winfo_width()  or 400
            h = c.winfo_height() or 200
            c.create_text(w//2, h//2, text="📊 Không có dữ liệu loss\n(results.csv không tìm thấy)",
                          fill=TEXT_DIM, font=("Segoe UI", 10), justify="center")
            self._set_chart_caption("eval", "Chưa có dữ liệu biểu đồ")
        self.after(0, _draw)

    def _eval_draw_confusion_matrix(self, class_names: list, matrix: list, title: str = "Confusion Matrix"):
        if not matrix:
            self._eval_draw_no_chart()
            return
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import numpy as np
            from PIL import Image as _PIL, ImageTk as _ITK
            import io

            c = self._eval_chart_canvas
            cw = max(c.winfo_width(), 400)
            ch = max(c.winfo_height(), 220)
            cm = np.array(matrix, dtype=float)
            if cm.ndim != 2 or cm.shape[0] == 0 or cm.shape[1] == 0:
                self._eval_draw_no_chart()
                return
            if not class_names:
                class_names = [f"Class {idx + 1}" for idx in range(cm.shape[0])]
            elif len(class_names) < cm.shape[0]:
                class_names = list(class_names) + [
                    f"Class {idx + 1}" for idx in range(len(class_names), cm.shape[0])
                ]
            else:
                class_names = list(class_names[:cm.shape[0]])
            drop_names = {"background", "bg", "unknown", "none", "__background__"}
            keep_indices = []
            for idx, name in enumerate(class_names):
                norm_name = str(name).strip().lower()
                row_sum = float(cm[idx, :].sum()) if idx < cm.shape[0] else 0.0
                col_sum = float(cm[:, idx].sum()) if idx < cm.shape[1] else 0.0
                if norm_name in drop_names and (row_sum + col_sum) <= 0.0:
                    continue
                keep_indices.append(idx)
            if keep_indices and len(keep_indices) != len(class_names):
                cm = cm[np.ix_(keep_indices, keep_indices)]
                class_names = [class_names[idx] for idx in keep_indices]
            support = cm.sum(axis=1, keepdims=True)
            norm_cm = np.divide(cm, support, out=np.zeros_like(cm), where=support > 0)

            fig, ax = plt.subplots(figsize=(cw / 96, ch / 96), dpi=96)
            fig.patch.set_facecolor("#1e1e2e")
            ax.set_facecolor("#13131f")
            im = ax.imshow(norm_cm, cmap="YlGn", vmin=0.0, vmax=1.0)
            cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            cbar.ax.yaxis.set_tick_params(color="#c0c0e0")
            plt.setp(plt.getp(cbar.ax.axes, "yticklabels"), color="#c0c0e0", fontsize=7)

            tick_names = [name[:16] for name in class_names]
            ax.set_xticks(range(len(class_names)))
            ax.set_yticks(range(len(class_names)))
            ax.set_xticklabels(tick_names, rotation=35, ha="right", fontsize=7, color="#c0c0e0")
            ax.set_yticklabels(tick_names, fontsize=7, color="#c0c0e0")
            ax.set_xlabel("Dự đoán", color="#c0c0e0", fontsize=8)
            ax.set_ylabel("Nhãn thật", color="#c0c0e0", fontsize=8)
            ax.set_title(title, color="#f8fafc", fontsize=10, pad=8)

            for row_idx in range(len(class_names)):
                for col_idx in range(len(class_names)):
                    cell_total = int(cm[row_idx, col_idx])
                    if cell_total <= 0:
                        continue
                    ax.text(
                        col_idx,
                        row_idx,
                        f"{cell_total}\n{norm_cm[row_idx, col_idx]:.2f}",
                        ha="center",
                        va="center",
                        fontsize=6,
                        color="#08130d" if norm_cm[row_idx, col_idx] >= 0.45 else "#f8fafc",
                    )

            plt.tight_layout(pad=1.1)
            buf = io.BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
            plt.close(fig)
            buf.seek(0)
            img = _PIL.open(buf).convert("RGB")
            tk_img, fitted = self._paint_pil_on_canvas(c, img, min_w=400, min_h=220)
            self._eval_chart_tk_img = tk_img
            self._eval_chart_pil_img = fitted
            self._set_chart_caption("eval", "Confusion Matrix chuẩn hóa cho Classification")
            self._eval_log("[✔] Confusion Matrix vẽ OK", "ok")
        except Exception as ex:
            self._eval_log(f"[warn] Không vẽ được confusion matrix: {ex}", "warn")
            self._eval_draw_no_chart()

    def _eval_draw_chart(self, epochs: list, series: dict, cols: list):
        """Vẽ chart matplotlib vào canvas hoặc fallback vẽ tkinter thuần."""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from PIL import Image as _PIL, ImageTk as _ITK
            import io, math

            palette = ["#22c55e", "#ef4444", "#38bdf8", "#f59e0b",
                       "#a78bfa", "#fb923c", "#34d399", "#f472b6"]

            n_loss   = sum(1 for c in cols if "loss" in c.lower())
            n_metric = len(cols) - n_loss
            n_plots  = (1 if n_loss else 0) + (1 if n_metric else 0)
            if n_plots == 0:
                n_plots = 1

            c = self._eval_chart_canvas
            cw = max(c.winfo_width(),  400)
            ch = max(c.winfo_height(), 220)

            fig, axes = plt.subplots(1, n_plots, figsize=(cw / 96, ch / 96), dpi=96)
            if n_plots == 1:
                axes = [axes]
            fig.patch.set_facecolor("#1e1e2e")
            for ax in axes:
                ax.set_facecolor("#13131f")
                ax.tick_params(colors="#9090b0", labelsize=7)
                ax.spines[:].set_color("#333350")

            ax_loss   = axes[0]
            ax_metric = axes[-1]

            ci = 0
            for col in cols:
                vals = series[col]
                if any(not math.isnan(v) for v in vals):
                    color = palette[ci % len(palette)]
                    label = col.strip().replace("train/", "").replace("val/", "val_")
                    ax = ax_loss if "loss" in col.lower() else ax_metric
                    ax.plot(epochs[:len(vals)], vals, color=color, linewidth=1.4,
                            label=label, marker=".", markersize=3)
                    ci += 1

            ax_loss.set_title("Loss", color="#c0c0e0", fontsize=8, pad=4)
            ax_loss.legend(fontsize=6, facecolor="#1e1e2e", labelcolor="#c0c0e0",
                           framealpha=0.6)
            ax_loss.set_xlabel("Epoch", color="#9090b0", fontsize=7)

            if n_loss > 0 and n_metric > 0:
                ax_metric.set_title("Metrics", color="#c0c0e0", fontsize=8, pad=4)
                ax_metric.legend(fontsize=6, facecolor="#1e1e2e", labelcolor="#c0c0e0",
                                 framealpha=0.6)
                ax_metric.set_xlabel("Epoch", color="#9090b0", fontsize=7)

            plt.tight_layout(pad=1.2)
            buf = io.BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight",
                        facecolor=fig.get_facecolor())
            plt.close(fig)
            buf.seek(0)
            img = _PIL.open(buf).convert("RGB")
            tk_img, fitted = self._paint_pil_on_canvas(c, img, min_w=400, min_h=220)
            self._eval_chart_tk_img = tk_img  # prevent GC
            self._eval_chart_pil_img = fitted
            self._set_chart_caption("eval", "Đường Loss và Metrics theo Epoch")
            self._eval_log(f"[✔] Chart vẽ OK ({len(cols)} series, {len(epochs)} epochs)", "ok")

        except ImportError:
            self._eval_draw_chart_plain(epochs, series, cols)
        except Exception as ex:
            self._eval_log(f"[warn] matplotlib lỗi: {ex}", "warn")
            self._eval_draw_chart_plain(epochs, series, cols)

    def _eval_draw_chart_plain(self, epochs: list, series: dict, cols: list):
        """Fallback: vẽ chart đơn giản bằng tkinter Canvas thuần."""
        import math
        c = self._eval_chart_canvas
        c.delete("all")
        self._set_chart_caption("eval", "Đường Loss và Metrics theo Epoch")
        cw = max(c.winfo_width(),  400)
        ch = max(c.winfo_height(), 220)
        PAD_L, PAD_R, PAD_T, PAD_B = 50, 20, 20, 40
        plot_w = cw - PAD_L - PAD_R
        plot_h = ch - PAD_T - PAD_B

        palette = ["#22c55e", "#ef4444", "#38bdf8", "#f59e0b",
                   "#a78bfa", "#fb923c", "#34d399", "#f472b6"]

        # find global y range
        all_vals = [v for col in cols for v in series[col] if not math.isnan(v)]
        if not all_vals or len(epochs) < 2:
            c.create_text(cw//2, ch//2, text="Không đủ dữ liệu để vẽ",
                          fill=TEXT_DIM, font=("Segoe UI", 9))
            return

        y_min, y_max = min(all_vals), max(all_vals)
        if y_max == y_min:
            y_max = y_min + 1.0
        x_min, x_max = epochs[0], epochs[-1]
        if x_max == x_min:
            x_max = x_min + 1

        def _px(ep, val):
            px = PAD_L + (ep - x_min) / (x_max - x_min) * plot_w
            py = PAD_T + plot_h - (val - y_min) / (y_max - y_min) * plot_h
            return px, py

        # grid lines
        c.create_rectangle(PAD_L, PAD_T, PAD_L + plot_w, PAD_T + plot_h,
                            outline="#333350", fill="#13131f")
        for i in range(5):
            y_val = y_min + i * (y_max - y_min) / 4
            _, py = _px(x_min, y_val)
            c.create_line(PAD_L, py, PAD_L + plot_w, py, fill="#2a2a40", dash=(3, 4))
            c.create_text(PAD_L - 4, py, text=f"{y_val:.3f}", anchor="e",
                          fill="#6060a0", font=("Cascadia Code", 6))

        # series
        for ci, col in enumerate(cols):
            color = palette[ci % len(palette)]
            vals  = series[col]
            pts   = []
            for ep, val in zip(epochs[:len(vals)], vals):
                if not math.isnan(val):
                    pts.append(_px(ep, val))
            if len(pts) >= 2:
                flat = [v for pt in pts for v in pt]
                c.create_line(*flat, fill=color, width=1, smooth=True)
            # legend dot
            lx = PAD_L + (ci % 4) * 100
            ly = PAD_T + plot_h + 12 + (ci // 4) * 14
            c.create_oval(lx - 4, ly - 4, lx + 4, ly + 4, fill=color, outline="")
            c.create_text(lx + 6, ly, text=col.strip()[:18], anchor="w",
                          fill="#a0a0c0", font=("Cascadia Code", 6))

        c.create_text(PAD_L + plot_w//2, ch - 6, text="Epoch",
                      fill="#6060a0", font=("Segoe UI", 7))

    # ─────────────────────────────────────────────────────────────────────────
    # ĐÁNH GIÁ MODEL — EXPORT
    # ─────────────────────────────────────────────────────────────────────────
    def _eval_export(self):
        import json, datetime
        if not self._eval_results:
            messagebox.showinfo("Thông báo", "Chưa có kết quả để xuất. Hãy chạy đánh giá trước.")
            return
        save_path = filedialog.asksaveasfilename(
            title="Lưu kết quả đánh giá",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("All", "*.*")],
            initialdir=str(RUNS_DIR),
            initialfile=f"eval_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )
        if not save_path:
            return
        out = {"timestamp": datetime.datetime.now().isoformat(), **self._eval_results}
        Path(save_path).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        messagebox.showinfo("✔ Đã lưu", f"Kết quả đã lưu:\n{save_path}")

    def _yolo_save_session(self):
        """Lưu nhanh kết quả đánh giá YOLO vào EVAL_BASE_DIR/yolo không hỏi thư mục."""
        import json, datetime
        if not self._eval_results:
            messagebox.showinfo("Thông báo", "Chưa có kết quả. Hãy chạy đánh giá YOLO trước.")
            return
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        # Build record — thêm các trường định danh
        record = {
            "paper":      "YOLO Evaluation",
            "timestamp":  datetime.datetime.now().isoformat(),
            "model":      self._eval_model_dir.get().strip(),
            "eval_dir":   self._eval_data_path.get().strip(),
            "task":       self._eval_task_var.get(),
            "device":     self._eval_device_var.get(),
            "img_size":   self._eval_imgsz_var.get(),
        }
        record.update({k: v for k, v in self._eval_results.items()
                        if not k.startswith("_")})
        try:
            yolo_dir = EVAL_BASE_DIR / "yolo"
            yolo_dir.mkdir(parents=True, exist_ok=True)
            # Dùng prefix "eval_" để Tab 6 (Lịch sử Đánh giá) quét được
            out_path = yolo_dir / f"eval_yolo_{ts}.json"
            out_path.write_text(
                json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
            messagebox.showinfo("✔ Đã lưu phiên",
                                f"Phiên đánh giá YOLO đã lưu:\n{out_path}")
            self.after(300, self._hist_refresh)
        except Exception as ex:
            messagebox.showerror("Lỗi lưu phiên", str(ex))

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4: PyTorch .pth Evaluator (JILSA CustomCNN / PLOS MobileNetV2)
    # ══════════════════════════════════════════════════════════════════════════
    def _build_pth_eval_tab(self, parent: tk.Frame):
        from tkinter import scrolledtext as _st

        banner = tk.Frame(parent, bg="#0d1a12", padx=12, pady=10)
        banner.pack(fill="x", padx=8, pady=(8, 0))
        tk.Label(banner, text="🧠  Đánh giá model PyTorch (.pth) — Classification",
                 font=("Segoe UI", 11, "bold"), bg="#0d1a12", fg="#4ade80").pack(anchor="w")
        tk.Label(banner,
                 text="Hỗ trợ: JILSA 2022 Custom CNN · PLOS ONE 2024 MobileNetV2\n"
                      "Dataset cần có cấu trúc thư mục con theo tên class (giống ImageFolder).",
                 font=("Segoe UI", 8), bg="#0d1a12", fg=TEXT_DIM, justify="left").pack(anchor="w", pady=(2, 0))

        paned = tk.PanedWindow(parent, orient="horizontal", bg=BG, sashwidth=5)
        paned.pack(fill="both", expand=True, padx=8, pady=8)
        left  = tk.Frame(paned, bg=BG2, padx=12, pady=10, width=320)
        right = tk.Frame(paned, bg=BG)
        paned.add(left, minsize=280)
        paned.add(right, minsize=420)

        def sec(t):
            tk.Label(left, text=t, font=("Segoe UI", 9, "bold"),
                     bg=BG2, fg="#4ade80").pack(anchor="w", pady=(10, 2))

        # ── Model file ──
        sec("🤖 File model (.pth)")
        f_m = tk.Frame(left, bg=BG2); f_m.pack(fill="x", pady=2)
        tk.Entry(f_m, textvariable=self._pth_model_path, bg=BG3, fg=TEXT,
                 insertbackground=TEXT, relief="flat",
                 font=("Segoe UI", 8)).pack(side="left", fill="x", expand=True, padx=(0, 2))
        tk.Button(f_m, text="...", command=self._pth_browse_model,
                  bg=BG3, fg=TEXT, relief="flat", padx=4, cursor="hand2").pack(side="left")

        # ── Architecture ──
        sec("🏗 Kiến trúc model")
        ttk.Combobox(left, textvariable=self._pth_arch_var,
                     values=["JILSA 2022 (CustomCNN)", "PLOS ONE 2024 (MobileNetV2)"],
                     state="readonly", font=("Segoe UI", 9)).pack(fill="x", pady=2)

        # ── Dataset ──
        sec("📁 Dataset folder (có thư mục con theo class)")
        f_d = tk.Frame(left, bg=BG2); f_d.pack(fill="x", pady=2)
        tk.Entry(f_d, textvariable=self._pth_data_var, bg=BG3, fg=TEXT,
                 insertbackground=TEXT, relief="flat",
                 font=("Segoe UI", 8)).pack(side="left", fill="x", expand=True, padx=(0, 2))
        tk.Button(f_d, text="...", command=self._pth_browse_data,
                  bg=BG3, fg=TEXT, relief="flat", padx=4, cursor="hand2").pack(side="left")

        # Val subfolder selector
        f_vf = tk.Frame(left, bg=BG2); f_vf.pack(fill="x", pady=2)
        tk.Label(f_vf, text="Val folder", width=14, anchor="w",
                 font=("Segoe UI", 9), bg=BG2, fg=TEXT).pack(side="left")
        ttk.Combobox(f_vf, textvariable=self._pth_val_folder_var,
                     values=["test", "val", "valid"],
                     state="normal", font=("Segoe UI", 9), width=10).pack(side="left")
        tk.Label(left,
                 text="  ↳ Nếu dataset có train/test (hoặc val/valid), chọn đúng tên sub-folder.",
                 font=("Segoe UI", 7, "italic"), bg=BG2, fg=WARNING,
                 wraplength=260, justify="left").pack(anchor="w", pady=(0, 4))

        # ── Params ──
        sec("⚙ Tham số đánh giá")

        def srow(lbl, var, frm, to, inc=1, fmt=None):
            fr = tk.Frame(left, bg=BG2); fr.pack(fill="x", pady=2)
            tk.Label(fr, text=lbl, width=14, anchor="w",
                     font=("Segoe UI", 9), bg=BG2, fg=TEXT).pack(side="left")
            kw = dict(textvariable=var, from_=frm, to=to, increment=inc,
                      width=8, bg=BG3, fg=TEXT, buttonbackground=BG3,
                      insertbackground=TEXT, relief="flat", font=("Segoe UI", 9))
            if fmt: kw["format"] = fmt
            tk.Spinbox(fr, **kw).pack(side="left")

        srow("Img Size",   self._pth_imgsz_var,  32, 640, 8)
        srow("Batch Size", self._pth_batch_var,   1, 256)
        srow("Workers",    self._pth_workers_var, 0,  16)

        f_dev = tk.Frame(left, bg=BG2); f_dev.pack(fill="x", pady=2)
        tk.Label(f_dev, text="Device", width=14, anchor="w",
                 font=("Segoe UI", 9), bg=BG2, fg=TEXT).pack(side="left")
        ttk.Combobox(f_dev, textvariable=self._pth_device_var,
                     values=["cuda", "cpu"], state="readonly",
                     font=("Segoe UI", 9), width=8).pack(side="left")

        # ── Output dir ──
        sec("💾 Folder lưu kết quả")
        f_out = tk.Frame(left, bg=BG2); f_out.pack(fill="x", pady=2)
        tk.Entry(f_out, textvariable=self._pth_out_var, bg=BG3, fg=TEXT,
                 insertbackground=TEXT, relief="flat",
                 font=("Segoe UI", 8)).pack(side="left", fill="x", expand=True, padx=(0, 2))
        tk.Button(f_out, text="...", command=self._pth_browse_out,
                  bg=BG3, fg=TEXT, relief="flat", padx=4, cursor="hand2").pack(side="left")
        tk.Label(left, text="  ↳ Lưu results.json + confusion_matrix.png vào đây.",
                 font=("Segoe UI", 7, "italic"), bg=BG2, fg=TEXT_DIM,
                 wraplength=260, justify="left").pack(anchor="w", pady=(0, 4))

        # ── Buttons ──
        btn_f = tk.Frame(left, bg=BG2); btn_f.pack(fill="x", pady=(16, 4))
        self._pth_run_btn = tk.Button(
            btn_f, text="▶  Bắt đầu Đánh giá",
            font=("Segoe UI", 10, "bold"),
            bg="#16a34a", fg="white", relief="flat", cursor="hand2", pady=8,
            command=self._start_pth_eval,
        )
        self._pth_run_btn.pack(fill="x", pady=2)
        self._pth_stop_btn = tk.Button(
            btn_f, text="⏹  Dừng lại",
            font=("Segoe UI", 10, "bold"),
            bg=DANGER, fg="white", relief="flat", cursor="hand2", pady=8,
            command=self._stop_pth_eval, state="disabled",
        )
        self._pth_stop_btn.pack(fill="x", pady=2)
        tk.Button(btn_f, text="🗑  Xóa Log",
                  font=("Segoe UI", 9), bg=BG3, fg=TEXT_DIM,
                  relief="flat", cursor="hand2", pady=6,
                  command=self._pth_clear_log).pack(fill="x", pady=2)
        self._pth_open_btn = tk.Button(
            btn_f, text="📂  Mở thư mục kết quả",
            font=("Segoe UI", 9), bg=BG3, fg=SUCCESS,
            relief="flat", cursor="hand2", pady=6,
            command=self._pth_open_output, state="disabled")
        self._pth_open_btn.pack(fill="x", pady=2)
        self._pth_status_lbl = tk.Label(left, text="⏹ Chưa chạy",
            font=("Segoe UI", 9, "bold"), bg=BG2, fg=TEXT_DIM)
        self._pth_status_lbl.pack(anchor="w", pady=(8, 0))

        # ── RIGHT — progress + log ──
        # Accuracy summary box
        sum_f = tk.Frame(right, bg=BG3, padx=16, pady=8)
        sum_f.pack(fill="x", padx=8, pady=(4, 4))
        tk.Label(sum_f, text="KẾT QUẢ", font=("Segoe UI", 8, "bold"),
                 bg=BG3, fg=TEXT_DIM).pack(side="left")
        self._pth_acc_lbl = tk.Label(sum_f, text="Accuracy: —",
                                     font=("Segoe UI", 20, "bold"),
                                     bg=BG3, fg="#4ade80")
        self._pth_acc_lbl.pack(side="left", padx=16)
        self._pth_elapsed_lbl = tk.Label(sum_f, text="",
                                         font=("Segoe UI", 9), bg=BG3, fg=TEXT_DIM)
        self._pth_elapsed_lbl.pack(side="right")

        # Progress bar
        prog_f = tk.Frame(right, bg=BG, pady=4); prog_f.pack(fill="x", padx=8)
        self._pth_prog_lbl = tk.Label(prog_f, text="—",
                                      font=("Segoe UI", 9, "bold"), bg=BG, fg=ACCENT2)
        self._pth_prog_lbl.pack(side="left", padx=6)
        _sty = ttk.Style()
        _sty.configure("pth.Horizontal.TProgressbar",
                        troughcolor=BG3, background="#16a34a", thickness=12)
        self._pth_progressbar = ttk.Progressbar(
            right, style="pth.Horizontal.TProgressbar",
            mode="indeterminate")
        self._pth_progressbar.pack(fill="x", padx=8, pady=(0, 6))

        # Log
        log_f = tk.Frame(right, bg=BG)
        log_f.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        tk.Label(log_f, text="📋 Log đánh giá",
                 font=("Segoe UI", 9, "bold"), bg=BG, fg="#4ade80").pack(anchor="w")
        self._pth_log = _st.ScrolledText(
            log_f, bg="#0d0d1a", fg="#d4d4d4",
            insertbackground="white", relief="flat",
            font=("Cascadia Code", 8), wrap="word", state="disabled")
        self._pth_log.pack(fill="both", expand=True, pady=(4, 0))
        for tag, clr in [("ok", SUCCESS), ("warn", WARNING), ("err", DANGER),
                         ("info", INFO), ("dim", TEXT_DIM), ("best", "#fbbf24"),
                         ("cls", ACCENT2)]:
            self._pth_log.tag_config(tag, foreground=clr)

    # ─────────────────────────────────────────────────────────────────────────
    # .pth EVAL — UNIFIED (Tab 3 route)
    # ─────────────────────────────────────────────────────────────────────────
    def _run_pth_eval_unified(self):
        """Đánh giá .pth từ Tab 3 — dùng _eval_model_dir và _eval_data_path."""
        import threading as _th

        model_path = self._eval_model_dir.get().strip()
        if not model_path or not Path(model_path).exists():
            messagebox.showerror("Lỗi", "Chọn file .pth hợp lệ trong ô Model.")
            return
        if not model_path.lower().endswith(".pth"):
            messagebox.showerror(
                "Lỗi", "Chế độ .pth chỉ hỗ trợ file .pth (PyTorch state_dict).")
            return
        data_root = self._eval_data_path.get().strip()
        if not data_root or not Path(data_root).is_dir():
            messagebox.showerror("Lỗi", "Chọn thư mục dataset hợp lệ.")
            return

        val_folder = self._pth_val_folder_var.get().strip()
        dp = Path(data_root)
        eval_path = str(dp / val_folder) if (dp / val_folder).is_dir() else data_root

        arch    = self._pth_arch_var.get()
        imgsz   = self._pth_imgsz_var.get()
        batch   = self._pth_batch_var.get()
        workers = self._pth_workers_var.get()
        device  = self._eval_device_var.get()
        out_dir = self._pth_out_var.get().strip() or str(RUNS_DIR / "pth_eval")
        # use_mobilenet and arch are auto-detected inside the eval script from state dict keys

        model_path_fwd = model_path.replace("\\", "/")
        out_dir_fwd    = out_dir.replace("\\", "/")
        eval_path_fwd  = eval_path.replace("\\", "/")

        # ── UI state ──────────────────────────────────────────────────────
        self._eval_running = True
        self._eval_run_btn.configure(state="disabled", text="⏳ Đang đánh giá .pth...")
        self._eval_status_lbl.configure(text="🔄 Đang đánh giá .pth...", fg=WARNING)

        def _elog(txt, tag=""):
            def _w():
                self._eval_log_box.configure(state="normal")
                if tag:
                    self._eval_log_box.insert("end", txt, tag)
                else:
                    self._eval_log_box.insert("end", txt)
                self._eval_log_box.configure(state="disabled")
                self._eval_log_box.see("end")
            self.after(0, _w)

        _elog(f"\n{'='*60}\n")
        _elog(f"  PyTorch .pth Evaluator  (Tab 3 unified)\n", "info")
        _elog(f"  Model  : {model_path}\n", "info")
        _elog(f"  Arch   : (tự nhận dạng từ file)\n", "info")
        _elog(f"  Data   : {eval_path}\n", "info")
        _elog(f"  ImgSz  : {imgsz}  Batch: {batch}  Device: {device.upper()}\n", "info")
        _elog(f"{'='*60}\n\n")

        script = f"""
import sys, os, json, time as _time
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
from pathlib import Path
from collections import defaultdict
try:
    from sklearn.metrics import (classification_report,
                                  precision_recall_fscore_support, confusion_matrix)
    HAS_SK = True
except ImportError:
    HAS_SK = False

DEVICE = torch.device("{device}" if "{device}" == "cpu" or not torch.cuda.is_available() else "cuda")
print(f"[INFO] Device: {{DEVICE}}", flush=True)
if DEVICE.type == "cuda":
    print(f"[INFO] GPU: {{torch.cuda.get_device_name(0)}}", flush=True)

tf = transforms.Compose([
    transforms.Resize(({imgsz}, {imgsz})),
    transforms.ToTensor(),
    transforms.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225]),
])

eval_dir = "{eval_path_fwd}"
ds = datasets.ImageFolder(eval_dir, transform=tf)
num_classes = len(ds.classes)
print(f"[INFO] Classes ({{num_classes}}): {{ds.classes}}", flush=True)
print(f"[INFO] Tổng ảnh: {{len(ds)}}", flush=True)

loader = DataLoader(ds, batch_size={batch}, shuffle=False,
                    num_workers={workers}, pin_memory=(DEVICE.type=="cuda"))

class CustomCNN(nn.Module):
    def __init__(self, nc):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3,   32, 3, padding=1), nn.BatchNorm2d(32),  nn.ReLU(True), nn.MaxPool2d(2),
            nn.Conv2d(32,  64, 3, padding=1), nn.BatchNorm2d(64),  nn.ReLU(True), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(True), nn.MaxPool2d(2),
            nn.Conv2d(128,256, 3, padding=1), nn.BatchNorm2d(256), nn.ReLU(True), nn.MaxPool2d(2),
            nn.AdaptiveAvgPool2d((9, 9)),  # ép 9×9 cố định ≈ 10.6M params (JILSA 2022)
        )
        flat = 256 * 9 * 9  # = 20,736
        self.classifier = nn.Sequential(
            nn.Flatten(), nn.Linear(flat,512), nn.ReLU(True), nn.Dropout(0.5), nn.Linear(512,nc)
        )
    def forward(self, x): return self.classifier(self.features(x))

model_file = "{model_path_fwd}"
try:
    _ckpt = torch.load(model_file, map_location="cpu", weights_only=True)
except Exception:
    _ckpt = torch.load(model_file, map_location="cpu", weights_only=False)
if isinstance(_ckpt, dict) and "model_weights" in _ckpt:
    _state = _ckpt["model_weights"]
else:
    _state = _ckpt

# Auto-detect kiến trúc từ state dict keys
USE_MOBILENET = any("features.0.0.weight" in k for k in _state.keys())
print(f"[INFO] Arch tự nhận dạng: {{('MobileNetV2' if USE_MOBILENET else 'CustomCNN (JILSA)') }}", flush=True)

for _k in list(_state.keys()):
    if "classifier.4.weight" in _k:
        _nc = _state[_k].shape[0]
        if _nc != num_classes:
            print(f"[WARN] Eval folder: {{num_classes}} cls — Weights: {{_nc}} cls → dùng {{_nc}}.", flush=True)
            num_classes = _nc
        break

if USE_MOBILENET:
    model = models.mobilenet_v2(weights=None)
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.2), nn.Linear(1280, 128),
        nn.ReLU(inplace=True), nn.Dropout(p=0.2), nn.Linear(128, num_classes))
else:
    model = CustomCNN(num_classes)
model.load_state_dict(_state)
model.to(DEVICE); model.eval()
total_p = sum(p.numel() for p in model.parameters())
print(f"[INFO] Params: {{total_p:,}} ({{total_p/1e6:.2f}} M)", flush=True)
print("[INFO] Weights tải thành công!", flush=True)

all_preds, all_labels = [], []
n_done = 0; n_total = len(ds)
t_start = _time.time()
with torch.no_grad():
    for imgs, lbls in loader:
        t0 = _time.time()
        _, preds = torch.max(model(imgs.to(DEVICE)), 1)
        all_preds.extend(preds.cpu().tolist())
        all_labels.extend(lbls.tolist())
        n_done += len(lbls)
        ms = (_time.time() - t0) * 1000
        print(f"[PROG] {{n_done}}/{{n_total}} ({ms/len(lbls):.1f}ms/img)", flush=True)

infer_sec = _time.time() - t_start
fps = n_total / max(infer_sec, 1e-6)
print(f"[INFO] Inference time: {{infer_sec:.2f}}s | FPS: {{fps:.1f}}", flush=True)

correct = sum(p==l for p,l in zip(all_preds, all_labels))
acc = correct / max(len(all_labels), 1)
print(f"[RESULT] Overall Accuracy = {{acc:.4f}} ({{correct}}/{{len(all_labels)}})", flush=True)

cls_correct = defaultdict(int); cls_total = defaultdict(int)
for p, l in zip(all_preds, all_labels):
    cls_total[l] += 1
    if p == l: cls_correct[l] += 1

if HAS_SK:
    prec, rec, f1, _ = precision_recall_fscore_support(
        all_labels, all_preds, average=None, zero_division=0)
    for ci, cname in enumerate(ds.classes):
        tot = cls_total[ci]; cor = cls_correct[ci]; cac = cor/tot if tot>0 else 0.0
        print(f"[CLASS] {{cname}}: Acc={{cac:.4f}} P={{prec[ci]:.4f}} R={{rec[ci]:.4f}} F1={{f1[ci]:.4f}} ({{cor}}/{{tot}})", flush=True)
    rpt = classification_report(all_labels, all_preds, target_names=ds.classes, digits=4)
    print("[REPORT]", flush=True)
    for line in rpt.splitlines():
        print(f"  {{line}}", flush=True)
else:
    for ci, cname in enumerate(ds.classes):
        tot = cls_total[ci]; cor = cls_correct[ci]; cac = cor/tot if tot>0 else 0.0
        print(f"[CLASS] {{cname}}: Acc={{cac:.4f}} ({{cor}}/{{tot}})", flush=True)

import datetime
out_dir = Path("{out_dir_fwd}")
arch_name = "MobileNetV2 (PLOS ONE 2024)" if USE_MOBILENET else "CustomCNN (JILSA 2022)"
out_dir.mkdir(parents=True, exist_ok=True)
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
results = {{
    "timestamp": datetime.datetime.now().isoformat(),
    "model": "{model_path_fwd}", "arch": arch_name,
    "eval_dir": eval_dir, "img_size": {imgsz}, "device": str(DEVICE),
    "total_imgs": n_total, "accuracy": round(acc, 6),
    "correct": correct, "fps": round(fps, 2), "infer_sec": round(infer_sec, 3),
    "params": total_p,
    "classes": {{
        cname: {{
            "accuracy": round(cls_correct[ci]/max(cls_total[ci],1), 6),
            "correct": cls_correct[ci], "total": cls_total[ci],
            **({{ "precision": round(float(prec[ci]),6),
                 "recall":    round(float(rec[ci]),6),
                 "f1":        round(float(f1[ci]),6)}} if HAS_SK else {{}})
        }} for ci, cname in enumerate(ds.classes)
    }},
}}
json_path = out_dir / f"eval_{{ts}}.json"
json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[SAVED] JSON: {{json_path}}", flush=True)

if HAS_SK:
    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt; import numpy as np
        cm = confusion_matrix(all_labels, all_preds)
        fig, ax = plt.subplots(figsize=(max(5, num_classes*1.4), max(4, num_classes*1.2)))
        fig.patch.set_facecolor("#1e1e2e"); ax.set_facecolor("#252538")
        im = ax.imshow(cm, interpolation="nearest", cmap="Blues")
        plt.colorbar(im, ax=ax)
        ax.set_xticks(range(num_classes)); ax.set_yticks(range(num_classes))
        ax.set_xticklabels(ds.classes, rotation=40, ha="right", fontsize=9, color="white")
        ax.set_yticklabels(ds.classes, fontsize=9, color="white")
        ax.tick_params(colors="white")
        thresh = cm.max() / 2.0
        for i in range(num_classes):
            for j in range(num_classes):
                ax.text(j, i, str(cm[i,j]), ha="center", va="center", fontsize=10,
                        fontweight="bold", color="white" if cm[i,j] < thresh else "#1e1e2e")
        ax.set_xlabel("Dự đoán", color="white", fontsize=11)
        ax.set_ylabel("Nhãn thật", color="white", fontsize=11)
        ax.set_title(f"Confusion Matrix — Acc={{acc:.4f}}", color="white", fontsize=12, fontweight="bold")
        plt.tight_layout()
        cm_path = out_dir / f"confusion_matrix_{{ts}}.png"
        fig.savefig(str(cm_path), dpi=120, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        print(f"[SAVED] Confusion Matrix: {{cm_path}}", flush=True)
    except Exception as _cm_e:
        print(f"[WARN] Không vẽ được confusion matrix: {{_cm_e}}", flush=True)

print("[DONE] Đánh giá hoàn thành!", flush=True)
"""

        def _run():
            import subprocess, os as _os
            pth_stats = None
            try:
                try:
                    pth_stats = self._get_pth_checkpoint_stats(model_path, imgsz)
                except Exception:
                    pth_stats = None
                _env = {**_os.environ, "PYTHONUTF8": "1"}
                proc = subprocess.Popen(
                    [str(PYTHON_EXE), "-c", script],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1, encoding="utf-8", errors="replace",
                    cwd=str(RUNS_DIR), env=_env,
                )
                _in_report = False
                saved_json_path = ""
                for line in proc.stdout:
                    s = line.rstrip()
                    if "[PROG]" in line:
                        continue
                    tag = ""
                    if "[RESULT]" in line:  tag = "ok"
                    elif "[CLASS]" in line:  tag = "info"
                    elif "[SAVED]" in line:  tag = "ok"
                    elif "[DONE]" in line:   tag = "ok"
                    elif "[REPORT]" in line or (_in_report and s.startswith("  ")):
                        tag = "dim"
                    elif "[WARN]" in line:   tag = "warn"
                    elif "[ERROR]" in line or "Traceback" in line or "Error" in line:
                        tag = "err"
                    elif "[INFO]" in line:   tag = "info"
                    if "[REPORT]" in line:   _in_report = True
                    elif s and not s.startswith("  "): _in_report = False
                    if s.startswith("[SAVED] JSON:"):
                        saved_json_path = s.split(":", 1)[1].strip()
                    _elog(s + "\n", tag)
                    if "[RESULT]" in line and "Accuracy" in line:
                        try:
                            acc_val = float(line.split("=")[1].split("(")[0].strip())
                            self.after(0, self._update_pth_unified_metrics,
                                       acc_val * 100, arch)
                        except Exception:
                            pass
                proc.wait()
                retcode = proc.returncode
            except Exception as ex:
                _elog(f"\n[ERROR] {ex}\n", "err")
                retcode = -1
                saved_json_path = ""

            def _done():
                self._eval_running = False
                self._eval_run_btn.configure(
                    state="normal", text="▶  Đánh giá PyTorch .pth")
                if retcode == 0:
                    result_payload = None
                    if saved_json_path and Path(saved_json_path).exists():
                        try:
                            import json as _json
                            result_payload = _json.loads(Path(saved_json_path).read_text(encoding="utf-8"))
                        except Exception:
                            result_payload = None
                    if result_payload:
                        if pth_stats:
                            result_payload.setdefault("params", pth_stats.get("params"))
                            result_payload.setdefault("gflops", pth_stats.get("gflops"))
                            result_payload.setdefault("arch", pth_stats.get("arch"))
                        self._update_pth_unified_metrics_from_payload(result_payload)
                        arch_name = str(result_payload.get("arch", arch) or arch)
                        which = None
                        arch_lower = arch_name.lower()
                        if "jilsa" in arch_lower or "customcnn" in arch_lower:
                            which = "jilsa"
                        elif "plos" in arch_lower or "mobilenet" in arch_lower:
                            which = "plos"
                        cls_map = result_payload.get("classes") or {}
                        cls_data = []
                        for cname, info in cls_map.items():
                            if not isinstance(info, dict):
                                continue
                            cls_data.append({
                                "name": cname,
                                "acc": self._safe_float_or_none(info.get("accuracy")) or 0.0,
                                "correct": int(info.get("correct", 0) or 0),
                                "total": int(info.get("total", 0) or 0),
                                "p": self._safe_float_or_none(info.get("precision")) or 0.0,
                                "r": self._safe_float_or_none(info.get("recall")) or 0.0,
                                "f1": self._safe_float_or_none(info.get("f1")) or 0.0,
                            })
                        acc_norm = self._safe_float_or_none(result_payload.get("accuracy"))
                        f1_vals = [d.get("f1") for d in cls_data if d.get("f1") is not None]
                        macro_f1 = sum(f1_vals) / len(f1_vals) if f1_vals else None
                        summary_metrics = {
                            "val_loss": None,
                            "accuracy": acc_norm,
                            "macro_precision": (sum(d.get("p", 0.0) for d in cls_data) / len(cls_data)) if cls_data else None,
                            "macro_recall": (sum(d.get("r", 0.0) for d in cls_data) / len(cls_data)) if cls_data else None,
                            "macro_f1": macro_f1,
                        }
                        if which and cls_data:
                            history_data = self._paper_find_history_data(which, model_path)
                            self._draw_pth_history_on_eval_canvas(history_data, summary_metrics)
                            self._paper_render_chart(
                                which,
                                cls_data,
                                acc_norm,
                                macro_f1,
                                summary_metrics,
                                history_data,
                                result_payload.get("confusion_matrix") or [],
                                list(cls_map.keys()),
                            )
                            total_images = result_payload.get("total_imgs")
                            bench_info = self._paper_make_benchmark_info(which, model_path, imgsz, total_images, {
                                **summary_metrics,
                                "params": result_payload.get("params") or (pth_stats or {}).get("params"),
                                "gflops": result_payload.get("gflops") or (pth_stats or {}).get("gflops"),
                                "classes": cls_map,
                            })
                            self._bench_reference_var.set("JILSA 2022" if which == "jilsa" else "PLOS ONE 2024")
                            self._draw_benchmark_comparison(bench_info)
                    self._eval_status_lbl.configure(
                        text="✔ Đánh giá .pth hoàn thành!", fg=SUCCESS)
                else:
                    self._eval_status_lbl.configure(
                        text="✗ Lỗi / Dừng", fg=DANGER)
            self.after(0, _done)

        _th.Thread(target=_run, daemon=True).start()

    def _update_pth_unified_metrics(self, acc_pct: float, arch: str):
        """Update the shared metrics panel with .pth eval accuracy."""
        for w in self._eval_metrics_frame.winfo_children():
            w.destroy()
        tk.Label(self._eval_metrics_frame, text="PyTorch .pth",
                 font=("Segoe UI", 8, "bold"), bg=BG2, fg=TEXT_DIM).pack(anchor="w")
        tk.Label(self._eval_metrics_frame, text="Accuracy",
                 font=("Segoe UI", 9), bg=BG2, fg=TEXT).pack(anchor="w", pady=(4, 0))
        tk.Label(self._eval_metrics_frame, text=f"{acc_pct:.2f}%",
                 font=("Segoe UI", 22, "bold"), bg=BG2, fg=SUCCESS).pack(anchor="w")
        tk.Label(self._eval_metrics_frame, text=arch,
                 font=("Segoe UI", 8), bg=BG2, fg=TEXT_DIM,
                 wraplength=200).pack(anchor="w", pady=(4, 0))

    def _update_pth_unified_metrics_from_payload(self, payload: dict):
        classes = payload.get("classes") or {}
        f1_vals = []
        for info in classes.values():
            if not isinstance(info, dict):
                continue
            f1_val = self._safe_float_or_none(info.get("f1"))
            if f1_val is not None:
                f1_vals.append(f1_val)
        macro_f1 = (sum(f1_vals) / len(f1_vals)) if f1_vals else None
        acc_pct = (self._safe_float_or_none(payload.get("accuracy")) or 0.0) * 100.0

        for w in self._eval_metrics_frame.winfo_children():
            w.destroy()
        tk.Label(self._eval_metrics_frame, text="PyTorch .pth",
                 font=("Segoe UI", 8, "bold"), bg=BG2, fg=TEXT_DIM).pack(anchor="w")
        cards = [
            ("Accuracy", f"{acc_pct:.2f}%", SUCCESS),
            ("Macro F1", self._fmt_percent_or_na(macro_f1), ACCENT2),
            ("Images", str(payload.get("total_imgs") or "—"), TEXT),
            ("Params (M)", f"{(self._safe_float_or_none(payload.get('params')) or 0.0) / 1e6:.3f}" if self._safe_float_or_none(payload.get("params")) is not None else "—", INFO),
            ("GFLOPs", f"{self._safe_float_or_none(payload.get('gflops')):.3f}" if self._safe_float_or_none(payload.get("gflops")) is not None else "—", WARNING),
        ]
        for label, value, color in cards:
            tk.Label(self._eval_metrics_frame, text=label,
                     font=("Segoe UI", 9), bg=BG2, fg=TEXT).pack(anchor="w", pady=(4, 0))
            tk.Label(self._eval_metrics_frame, text=value,
                     font=("Segoe UI", 16, "bold"), bg=BG2, fg=color).pack(anchor="w")
        tk.Label(self._eval_metrics_frame, text=str(payload.get("arch") or "—"),
                 font=("Segoe UI", 8), bg=BG2, fg=TEXT_DIM,
                 wraplength=200).pack(anchor="w", pady=(6, 0))

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 4 (legacy): .pth Evaluator standalone UI
    # ─────────────────────────────────────────────────────────────────────────
        d = filedialog.askdirectory(title="Chọn folder lưu kết quả")
        if d: self._pth_out_var.set(d)

    def _pth_open_output(self):
        import subprocess as _sp, os as _os
        out = self._pth_out_var.get().strip()
        if out and Path(out).is_dir():
            _sp.Popen(["explorer", out])
        else:
            messagebox.showinfo("Thư mục", f"Thư mục không tồn tại:\n{out}")

    def _pth_browse_model(self):
        f = filedialog.askopenfilename(
            title="Chọn file model (.pth)",
            filetypes=[("PyTorch weights", "*.pth"), ("All files", "*.*")],
            initialdir=str(RUNS_DIR),
        )
        if f: self._pth_model_path.set(f)

    def _pth_browse_data(self):
        d = filedialog.askdirectory(title="Chọn dataset folder")
        if d: self._pth_data_var.set(d)

    def _pth_log_write(self, text: str, tag: str = ""):
        self._pth_log.configure(state="normal")
        if tag: self._pth_log.insert("end", text, tag)
        else:   self._pth_log.insert("end", text)
        self._pth_log.configure(state="disabled")
        self._pth_log.see("end")

    def _pth_clear_log(self):
        self._pth_log.configure(state="normal")
        self._pth_log.delete("1.0", "end")
        self._pth_log.configure(state="disabled")

    # ── Start eval ────────────────────────────────────────────────────────────
    def _start_pth_eval(self):
        model_path = self._pth_model_path.get().strip()
        if not model_path or not Path(model_path).exists():
            messagebox.showerror("Lỗi", "Vui lòng chọn file model .pth hợp lệ.")
            return
        data_root = self._pth_data_var.get().strip()
        val_folder = self._pth_val_folder_var.get().strip()
        if not data_root or not Path(data_root).is_dir():
            messagebox.showerror("Lỗi", "Vui lòng chọn dataset folder hợp lệ.")
            return
        # Check whether the val subfolder exists vs the root itself has class dirs
        data_path_obj = Path(data_root)
        if (data_path_obj / val_folder).is_dir():
            eval_path = str(data_path_obj / val_folder)
        else:
            # Assume data_root itself is the eval folder (already contains class subfolders)
            eval_path = data_root

        arch    = self._pth_arch_var.get()
        imgsz   = self._pth_imgsz_var.get()
        batch   = self._pth_batch_var.get()
        workers = self._pth_workers_var.get()
        device  = self._pth_device_var.get()

        self._pth_running = True
        self._pth_run_btn.configure(state="disabled")
        self._pth_stop_btn.configure(state="normal")
        self._pth_status_lbl.configure(text="🔄 Đang đánh giá...", fg=WARNING)
        self._pth_start_time = time.time()
        self._pth_progressbar.configure(mode="indeterminate")
        self._pth_progressbar.start(15)
        self._pth_acc_lbl.configure(text="Accuracy: —")
        self._pth_elapsed_lbl.configure(text="")

        self._pth_log_write(f"\n{'='*60}\n", "dim")
        self._pth_log_write(f"  PyTorch .pth Evaluator\n", "info")
        self._pth_log_write(f"  Model  : {model_path}\n", "info")
        self._pth_log_write(f"  Arch   : {arch}\n", "info")
        self._pth_log_write(f"  Data   : {eval_path}\n", "info")
        self._pth_log_write(f"  ImgSz  : {imgsz}  Batch: {batch}  Device: {device.upper()}\n", "info")
        self._pth_log_write(f"{'='*60}\n\n", "dim")

        use_mobilenet = "MobileNet" in arch
        out_dir = self._pth_out_var.get().strip() or str(RUNS_DIR / "pth_eval")
        model_path_fwd = model_path.replace("\\", "/")
        out_dir_fwd    = out_dir.replace("\\", "/")
        eval_path_fwd  = eval_path.replace("\\", "/")

        script = f"""
import sys, os, json, time as _time
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
from pathlib import Path
from collections import defaultdict
try:
    from sklearn.metrics import (classification_report, accuracy_score,
                                  precision_recall_fscore_support, confusion_matrix)
    HAS_SK = True
except ImportError:
    HAS_SK = False

DEVICE = torch.device("{device}" if "{device}" == "cpu" or not torch.cuda.is_available() else "cuda")
print(f"[INFO] Device: {{DEVICE}}", flush=True)
if DEVICE.type == "cuda":
    print(f"[INFO] GPU: {{torch.cuda.get_device_name(0)}}", flush=True)

tf = transforms.Compose([
    transforms.Resize(({imgsz}, {imgsz})),
    transforms.ToTensor(),
    transforms.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225]),
])

eval_dir = "{eval_path_fwd}"
ds = datasets.ImageFolder(eval_dir, transform=tf)
num_classes = len(ds.classes)
print(f"[INFO] Classes ({{num_classes}}): {{ds.classes}}", flush=True)
print(f"[INFO] Tổng ảnh: {{len(ds)}}", flush=True)

loader = DataLoader(ds, batch_size={batch}, shuffle=False,
                    num_workers={workers}, pin_memory=(DEVICE.type=="cuda"))

# ── Define CustomCNN (JILSA 2022) ────────────────────────────────────────────
class CustomCNN(nn.Module):
    def __init__(self, nc):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3,   32, 3, padding=1), nn.BatchNorm2d(32),  nn.ReLU(True), nn.MaxPool2d(2),
            nn.Conv2d(32,  64, 3, padding=1), nn.BatchNorm2d(64),  nn.ReLU(True), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(True), nn.MaxPool2d(2),
            nn.Conv2d(128,256, 3, padding=1), nn.BatchNorm2d(256), nn.ReLU(True), nn.MaxPool2d(2),
            nn.AdaptiveAvgPool2d((9, 9)),  # ép 9×9 cố định ≈ 10.6M params (JILSA 2022)
        )
        flat = 256 * 9 * 9  # = 20,736
        self.classifier = nn.Sequential(
            nn.Flatten(), nn.Linear(flat,512), nn.ReLU(True), nn.Dropout(0.5), nn.Linear(512,nc)
        )
    def forward(self, x): return self.classifier(self.features(x))

# ── Load state dict trước (để infer num_classes + arch) ───────────────────────
model_file = "{model_path_fwd}"
try:
    _ckpt = torch.load(model_file, map_location="cpu", weights_only=True)
except Exception:
    _ckpt = torch.load(model_file, map_location="cpu", weights_only=False)
if isinstance(_ckpt, dict) and "model_weights" in _ckpt:
    _state = _ckpt["model_weights"]
else:
    _state = _ckpt

# Auto-detect kiến trúc từ state dict keys
USE_MOBILENET = any("features.0.0.weight" in k for k in _state.keys())
print(f"[INFO] Arch tự nhận dạng: {{('MobileNetV2' if USE_MOBILENET else 'CustomCNN (JILSA)') }}", flush=True)

# Infer num_classes từ state_dict (ưu tiên hơn số class trong eval folder)
for _k in list(_state.keys()):
    if "classifier.4.weight" in _k:
        _nc = _state[_k].shape[0]
        if _nc != num_classes:
            print(f"[WARN] Eval folder: {{num_classes}} cls — Model weights: {{_nc}} cls → dùng {{_nc}}.", flush=True)
            num_classes = _nc
        break

# ── Build model với đúng kiến trúc ────────────────────────────────────────────
if USE_MOBILENET:
    model = models.mobilenet_v2(weights=None)
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.2),
        nn.Linear(1280, 128),
        nn.ReLU(inplace=True),
        nn.Dropout(p=0.2),
        nn.Linear(128, num_classes),
    )
else:
    model = CustomCNN(num_classes)
model.load_state_dict(_state)
model.to(DEVICE)
model.eval()
total_p = sum(p.numel() for p in model.parameters())
print(f"[INFO] Params: {{total_p:,}} ({{total_p/1e6:.2f}} M)", flush=True)
print("[INFO] Weights tải thành công!", flush=True)

# ── Inference ─────────────────────────────────────────────────────────────────
all_preds, all_labels = [], []
n_done = 0
n_total = len(ds)
t_infer_start = _time.time()

with torch.no_grad():
    for imgs, lbls in loader:
        t0 = _time.time()
        outputs = model(imgs.to(DEVICE))
        _, preds = torch.max(outputs, 1)
        all_preds.extend(preds.cpu().tolist())
        all_labels.extend(lbls.tolist())
        n_done += len(lbls)
        ms = (_time.time() - t0) * 1000
        print(f"[PROG] {{n_done}}/{{n_total}} ({ms/len(lbls):.1f}ms/img)", flush=True)

infer_sec = _time.time() - t_infer_start
fps = n_total / max(infer_sec, 1e-6)
print(f"[INFO] Inference time: {{infer_sec:.2f}}s | FPS: {{fps:.1f}}", flush=True)

# ── Overall Accuracy ──────────────────────────────────────────────────────────
correct = sum(p==l for p,l in zip(all_preds, all_labels))
acc = correct / max(len(all_labels), 1)
print(f"[RESULT] Overall Accuracy = {{acc:.4f}} ({{correct}}/{{len(all_labels)}})", flush=True)

# ── Per-class metrics ─────────────────────────────────────────────────────────
cls_correct = defaultdict(int)
cls_total   = defaultdict(int)
for p, l in zip(all_preds, all_labels):
    cls_total[l] += 1
    if p == l: cls_correct[l] += 1

if HAS_SK:
    prec, rec, f1, sup = precision_recall_fscore_support(
        all_labels, all_preds, average=None, zero_division=0)
    for ci, cname in enumerate(ds.classes):
        tot = cls_total[ci]; cor = cls_correct[ci]
        cac = cor/tot if tot>0 else 0.0
        print(f"[CLASS] {{cname}}: Acc={{cac:.4f}} P={{prec[ci]:.4f}} R={{rec[ci]:.4f}} F1={{f1[ci]:.4f}} ({{cor}}/{{tot}})", flush=True)
else:
    for ci, cname in enumerate(ds.classes):
        tot = cls_total[ci]; cor = cls_correct[ci]
        cac = cor/tot if tot>0 else 0.0
        print(f"[CLASS] {{cname}}: Acc={{cac:.4f}} ({{cor}}/{{tot}})", flush=True)

# ── Classification report ─────────────────────────────────────────────────────
if HAS_SK:
    rpt = classification_report(all_labels, all_preds,
                                 target_names=ds.classes, digits=4)
    print("[REPORT]", flush=True)
    for line in rpt.splitlines():
        print(f"  {{line}}", flush=True)

# ── Save JSON results ──────────────────────────────────────────────────────────
import datetime
out_dir = Path("{out_dir_fwd}")
out_dir.mkdir(parents=True, exist_ok=True)
arch_name = "MobileNetV2 (PLOS ONE 2024)" if USE_MOBILENET else "CustomCNN (JILSA 2022)"
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
results = {{
    "timestamp":  datetime.datetime.now().isoformat(),
    "model":      "{model_path_fwd}",
    "arch":       arch_name,
    "eval_dir":   eval_dir,
    "img_size":   {imgsz},
    "device":     str(DEVICE),
    "total_imgs": n_total,
    "accuracy":   round(acc, 6),
    "correct":    correct,
    "fps":        round(fps, 2),
    "infer_sec":  round(infer_sec, 3),
    "params":     total_p,
    "classes": {{
        cname: {{
            "accuracy":  round(cls_correct[ci]/max(cls_total[ci],1), 6),
            "correct":   cls_correct[ci],
            "total":     cls_total[ci],
            **({{
                "precision": round(float(prec[ci]), 6),
                "recall":    round(float(rec[ci]),  6),
                "f1":        round(float(f1[ci]),   6),
            }} if HAS_SK else {{}})
        }}
        for ci, cname in enumerate(ds.classes)
    }},
}}
json_path = out_dir / f"eval_{{ts}}.json"
json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[SAVED] JSON: {{json_path}}", flush=True)

# ── Confusion Matrix ──────────────────────────────────────────────────────────
if HAS_SK:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        cm = confusion_matrix(all_labels, all_preds)
        fig, ax = plt.subplots(figsize=(max(5, num_classes*1.4), max(4, num_classes*1.2)))
        fig.patch.set_facecolor("#1e1e2e")
        ax.set_facecolor("#252538")
        im = ax.imshow(cm, interpolation="nearest", cmap="Blues")
        plt.colorbar(im, ax=ax)
        ax.set_xticks(range(num_classes))
        ax.set_yticks(range(num_classes))
        ax.set_xticklabels(ds.classes, rotation=40, ha="right", fontsize=9, color="white")
        ax.set_yticklabels(ds.classes, fontsize=9, color="white")
        ax.tick_params(colors="white")
        thresh = cm.max() / 2.0
        for i in range(num_classes):
            for j in range(num_classes):
                ax.text(j, i, str(cm[i, j]),
                        ha="center", va="center", fontsize=10, fontweight="bold",
                        color="white" if cm[i, j] < thresh else "#1e1e2e")
        ax.set_xlabel("Dự đoán", color="white", fontsize=11)
        ax.set_ylabel("Nhãn thật", color="white", fontsize=11)
        ax.set_title(f"Confusion Matrix — Acc={{acc:.4f}}", color="white",
                     fontsize=12, fontweight="bold")
        plt.tight_layout()
        cm_path = out_dir / f"confusion_matrix_{{ts}}.png"
        fig.savefig(str(cm_path), dpi=120, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        plt.close(fig)
        print(f"[SAVED] Confusion Matrix: {{cm_path}}", flush=True)
    except Exception as _cm_e:
        print(f"[WARN] Không vẽ được confusion matrix: {{_cm_e}}", flush=True)

print("[DONE] Đánh giá hoàn thành!", flush=True)
"""
        import threading as _th
        _th.Thread(target=self._run_pth_eval, args=(script,), daemon=True).start()

    def _run_pth_eval(self, script: str):
        import subprocess, os as _os
        try:
            _env = {**_os.environ, "PYTHONUTF8": "1"}
            self._pth_process = subprocess.Popen(
                [str(PYTHON_EXE), "-c", script],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, encoding="utf-8", errors="replace",
                cwd=str(RUNS_DIR), env=_env,
            )
            for line in self._pth_process.stdout:
                if not self._pth_running: break
                self._parse_pth_line(line)
            self._pth_process.wait()
            retcode = self._pth_process.returncode
        except Exception as ex:
            self.after(0, self._pth_log_write, f"\n[ERROR] {ex}\n", "err")
            retcode = -1
        finally:
            self._pth_process = None
            self.after(0, self._on_pth_eval_done, retcode)

    def _parse_pth_line(self, line: str):
        s = line.rstrip()
        tag = ""
        if "[RESULT]" in line:    tag = "best"
        elif "[CLASS]" in line:   tag = "cls"
        elif "[SAVED]" in line:   tag = "ok"
        elif "[DONE]" in line:    tag = "ok"
        elif "[REPORT]" in line or (s.startswith("  ") and self._pth_in_report):
            tag = "dim"
        elif "[WARN]" in line or "WARNING" in line: tag = "warn"
        elif "[ERROR]" in line or "Error" in line or "Traceback" in line: tag = "err"
        elif "[INFO]" in line:    tag = "info"
        elif "[PROG]" in line:
            try:
                body = line.split("[PROG]")[1].strip()
                frac = body.split("(")[0].strip()
                parts = frac.split("/")
                done, total = int(parts[0]), int(parts[1])
                pct = int(done / total * 100) if total > 0 else 0
                elapsed = time.time() - self._pth_start_time
                self.after(0, self._pth_prog_lbl.configure,
                           {"text": f"{done}/{total} ({pct}%)  {body.split('(')[1].rstrip(')') if '(' in body else ''}"})
                self.after(0, self._pth_elapsed_lbl.configure,
                           {"text": f"⏱ {self._fmt_time(elapsed)}"})
            except Exception:
                pass
            return
        # Track report section for indented lines
        if "[REPORT]" in line:
            self._pth_in_report = True
        elif line.strip() and not line.startswith("  "):
            self._pth_in_report = False
        self.after(0, self._pth_log_write, s + "\n", tag)

        if "[RESULT]" in line and "Accuracy" in line:
            try:
                acc_str = line.split("=")[1].split("(")[0].strip()
                acc_pct = float(acc_str) * 100
                self.after(0, self._pth_acc_lbl.configure,
                           {"text": f"Accuracy: {acc_pct:.2f}%"})
            except Exception:
                pass

    def _on_pth_eval_done(self, retcode: int):
        self._pth_running = False
        self._pth_in_report = False
        self._pth_run_btn.configure(state="normal")
        self._pth_stop_btn.configure(state="disabled")
        self._pth_progressbar.stop()
        self._pth_progressbar.configure(mode="determinate", value=100)
        elapsed = time.time() - self._pth_start_time
        self._pth_elapsed_lbl.configure(text=f"⏱ {self._fmt_time(elapsed)}")
        if retcode == 0:
            self._pth_status_lbl.configure(text="✔ Hoàn thành!", fg=SUCCESS)
            self._pth_log_write(f"\n✔ Đánh giá hoàn thành!  Tổng: {self._fmt_time(elapsed)}\n", "ok")
            self._pth_open_btn.configure(state="normal")
        else:
            self._pth_status_lbl.configure(text="✗ Lỗi / Đã dừng", fg=DANGER)
            self._pth_log_write(f"\n✗ Kết thúc bất thường (code {retcode})\n", "err")

    def _stop_pth_eval(self):
        if self._pth_process and self._pth_process.poll() is None:
            self._pth_running = False
            self._pth_process.terminate()
            self._pth_log_write("\n⏹ Đã gửi lệnh dừng...\n", "warn")
            self._pth_status_lbl.configure(text="⏹ Đang dừng...", fg=WARNING)

    def _fmt_time(self, seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h: return f"{h}h {m:02d}m {s:02d}s"
        if m: return f"{m}m {s:02d}s"
        return f"{s}s"


    # ═════════════════════════════════════════════════════════════════════════
    # TAB JILSA 2022 — Custom CNN Evaluation
    # ═════════════════════════════════════════════════════════════════════════
    def _build_jilsa_tab(self, parent: tk.Frame):
        from tkinter import scrolledtext as _st

        banner = tk.Frame(parent, bg=JILSA_BANNER_BG, padx=14, pady=10)
        banner.pack(fill="x", padx=8, pady=(8, 0))
        tk.Label(banner, text="🧠  JILSA 2022 — Custom CNN Evaluation",
                 font=("Segoe UI", 12, "bold"), bg=JILSA_BANNER_BG, fg=JILSA_GREEN).pack(anchor="w")
        tk.Label(banner,
                 text="Alzubaidi et al. 2022  ·  Loss: CrossEntropyLoss  ·  "
                      "Metric chính: Top-1 Accuracy + Confusion Matrix\n"
                      "Test set: ~10% (không có Val riêng)  ·  Input: 200×200  ·  "
                      "Arch: CustomCNN (~11M params)",
                 font=("Segoe UI", 8), bg=JILSA_BANNER_BG, fg=TEXT_DIM,
                 justify="left").pack(anchor="w", pady=(2, 0))

        paned = tk.PanedWindow(parent, orient="horizontal", bg=BG, sashwidth=5)
        paned.pack(fill="both", expand=True, padx=8, pady=8)

        left  = tk.Frame(paned, bg=BG2, padx=12, pady=10, width=310)
        right = tk.Frame(paned, bg=BG)
        paned.add(left,  minsize=280)
        paned.add(right, minsize=440)

        def sec(t):
            tk.Label(left, text=t, font=("Segoe UI", 9, "bold"),
                     bg=BG2, fg=JILSA_GREEN).pack(anchor="w", pady=(10, 2))

        sec("🤖 File model (.pth — CustomCNN)")
        f_m = tk.Frame(left, bg=BG2); f_m.pack(fill="x", pady=2)
        ent_m = tk.Entry(f_m, textvariable=self._jilsa_model_var, font=("Segoe UI", 8))
        apply_entry_theme(ent_m)
        ent_m.pack(side="left", fill="x", expand=True, padx=(0, 2))
        tk.Button(f_m, text="...", bg=BG3, fg=TEXT, relief="flat", padx=4, cursor="hand2",
                  command=lambda: self._browse_file(
                      self._jilsa_model_var, "Chọn file .pth",
                      [("PyTorch weights", "*.pth"), ("All", "*.*")])
                  ).pack(side="left")

        sec("📁 Dataset folder (ImageFolder cấu trúc)")
        tk.Label(left, text="Mỗi class là 1 sub-folder con: dataset/class_name/img.jpg",
                 font=("Segoe UI", 7), bg=BG2, fg=TEXT_DIM, wraplength=265).pack(anchor="w")
        f_d = tk.Frame(left, bg=BG2); f_d.pack(fill="x", pady=2)
        ent_d = tk.Entry(f_d, textvariable=self._jilsa_data_var, font=("Segoe UI", 8))
        apply_entry_theme(ent_d)
        ent_d.pack(side="left", fill="x", expand=True, padx=(0, 2))
        tk.Button(f_d, text="📁", bg=BG3, fg=TEXT, relief="flat", padx=4, cursor="hand2",
                  command=lambda: self._browse_dir(
                      self._jilsa_data_var, "Chọn dataset folder")
                  ).pack(side="left")

        tk.Label(left, text="⚙ Class names: tự động đọc từ model",
                 font=("Segoe UI", 7, "italic"), bg=BG2, fg=TEXT_DIM).pack(anchor="w", pady=(6,4))
        for lbl, var, frm, to, inc in [
            ("Batch",    self._jilsa_batch_var,   1, 256, 1),
        ]:
            fr = tk.Frame(left, bg=BG2); fr.pack(fill="x", pady=2)
            tk.Label(fr, text=lbl, width=14, anchor="w",
                     font=("Segoe UI", 9), bg=BG2, fg=TEXT).pack(side="left")
            tk.Spinbox(fr, textvariable=var, from_=frm, to=to, increment=inc,
                       width=8, bg=BG3, fg=TEXT, buttonbackground=BG3,
                       insertbackground=TEXT, relief="flat",
                       font=("Segoe UI", 9)).pack(side="left")
        # ─ Image limit per class
        f_lim = tk.Frame(left, bg=BG2); f_lim.pack(fill="x", pady=2)
        tk.Label(f_lim, text="Giới hạn ảnh", width=14, anchor="w",
                 font=("Segoe UI", 9), bg=BG2, fg=TEXT).pack(side="left")
        tk.Spinbox(f_lim, textvariable=self._jilsa_limit_var, from_=0, to=99999, increment=10,
                   width=8, bg=BG3, fg=TEXT, buttonbackground=BG3,
                   insertbackground=TEXT, relief="flat",
                   font=("Segoe UI", 9)).pack(side="left")
        tk.Label(f_lim, text=" ảnh/class  (0 = không giới hạn)",
                 font=("Segoe UI", 7, "italic"), bg=BG2, fg=WARNING).pack(side="left", padx=4)
        f_dev = tk.Frame(left, bg=BG2); f_dev.pack(fill="x", pady=2)
        tk.Label(f_dev, text="Device", width=14, anchor="w",
                 font=("Segoe UI", 9), bg=BG2, fg=TEXT).pack(side="left")
        ttk.Combobox(f_dev, textvariable=self._jilsa_device_var,
                     values=["cuda", "cpu"], state="readonly",
                     font=("Segoe UI", 9), width=8).pack(side="left")

        sec("💾 Folder lưu kết quả")
        f_out = tk.Frame(left, bg=BG2); f_out.pack(fill="x", pady=2)
        ent_out = tk.Entry(f_out, textvariable=self._jilsa_out_var, font=("Segoe UI", 8))
        apply_entry_theme(ent_out)
        ent_out.pack(side="left", fill="x", expand=True, padx=(0, 2))
        tk.Button(f_out, text="📁", bg=BG3, fg=TEXT, relief="flat", padx=4, cursor="hand2",
                  command=lambda: self._browse_dir(
                      self._jilsa_out_var, "Chọn folder lưu kết quả")
                  ).pack(side="left")

        btn_f = tk.Frame(left, bg=BG2); btn_f.pack(fill="x", pady=(14, 4))
        self._jilsa_run_btn = tk.Button(
            btn_f, text="▶  Bắt đầu Đánh giá",
            font=("Segoe UI", 10, "bold"),
            bg="#16a34a", fg="white", relief="flat", cursor="hand2", pady=8,
            command=self._start_jilsa_eval)
        self._jilsa_run_btn.pack(fill="x", pady=2)
        self._jilsa_stop_btn = tk.Button(
            btn_f, text="⏹  Dừng",
            font=("Segoe UI", 9, "bold"), bg=DANGER, fg="white",
            relief="flat", cursor="hand2", pady=6, state="disabled",
            command=lambda: self._stop_paper_eval("jilsa"))
        self._jilsa_stop_btn.pack(fill="x", pady=2)
        tk.Button(btn_f, text="🗑  Xóa Log",
                  font=("Segoe UI", 9), bg=BG3, fg=TEXT_DIM,
                  relief="flat", cursor="hand2", pady=5,
                  command=lambda: self._paper_log_clear("jilsa")).pack(fill="x", pady=2)
        self._jilsa_open_btn = tk.Button(
            btn_f, text="📂  Mở thư mục kết quả",
            font=("Segoe UI", 9), bg=BG3, fg=SUCCESS,
            relief="flat", cursor="hand2", pady=6, state="disabled",
            command=lambda: self._paper_open_output(self._jilsa_out_var))
        self._jilsa_open_btn.pack(fill="x", pady=2)
        self._jilsa_status_lbl = tk.Label(left, text="⏹ Chưa chạy",
            font=("Segoe UI", 9, "bold"), bg=BG2, fg=TEXT_DIM)
        self._jilsa_status_lbl.pack(anchor="w", pady=(8, 0))

        # ── Right ──
        sum_f = tk.Frame(right, bg=JILSA_BANNER_BG, padx=16, pady=8)
        sum_f.pack(fill="x", padx=8, pady=(4, 4))
        tk.Label(sum_f, text="KẾT QUẢ", font=("Segoe UI", 8, "bold"),
                 bg=JILSA_BANNER_BG, fg=TEXT_DIM).pack(side="left")
        self._jilsa_acc_lbl = tk.Label(sum_f, text="Accuracy: —",
            font=("Segoe UI", 20, "bold"), bg=JILSA_BANNER_BG, fg=JILSA_GREEN)
        self._jilsa_acc_lbl.pack(side="left", padx=16)
        self._jilsa_f1_lbl = tk.Label(sum_f, text="",
            font=("Segoe UI", 10), bg=JILSA_BANNER_BG, fg=INFO)
        self._jilsa_f1_lbl.pack(side="left", padx=8)
        self._jilsa_elapsed_lbl = tk.Label(sum_f, text="",
            font=("Segoe UI", 9), bg=JILSA_BANNER_BG, fg=TEXT_DIM)
        self._jilsa_elapsed_lbl.pack(side="right")

        right_paned = tk.PanedWindow(right, orient="vertical", bg=BG,
                                     sashwidth=4, sashrelief="flat")
        right_paned.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        upper = tk.Frame(right_paned, bg=BG)
        lower = tk.Frame(right_paned, bg=BG)
        right_paned.add(upper, minsize=420)
        right_paned.add(lower, minsize=110)

        metrics_frame = tk.Frame(upper, bg=BG3, padx=8, pady=8)
        metrics_frame.pack(fill="x", pady=(0, 4))
        tk.Label(metrics_frame, text="Val Metrics",
                 font=("Segoe UI", 8, "bold"), bg=BG3, fg=JILSA_GREEN).pack(anchor="w", padx=2)
        self._jilsa_metrics_frame = tk.Frame(metrics_frame, bg=BG3)
        self._jilsa_metrics_frame.pack(fill="x", pady=(6, 0))

        cls_frame = tk.Frame(upper, bg=BG2)
        cls_frame.pack(fill="x", pady=(0, 4))
        tk.Label(cls_frame, text="📊 Kết quả từng class",
                 font=("Segoe UI", 8, "bold"), bg=BG2, fg=JILSA_GREEN).pack(anchor="w", padx=6)
        self._jilsa_cls_tbl = tk.Frame(cls_frame, bg=BG2)
        self._jilsa_cls_tbl.pack(fill="x", padx=6, pady=2)
        tk.Label(self._jilsa_cls_tbl, text="(chưa chạy)",
                 font=("Segoe UI", 8), bg=BG2, fg=TEXT_DIM).pack(anchor="w", pady=2)

        # ── Chart panel ──
        chart_wrap = tk.Frame(upper, bg=BG3, padx=4, pady=4)
        chart_wrap.pack(fill="both", expand=True, pady=(2, 0))
        chart_hdr_f = tk.Frame(chart_wrap, bg=BG3)
        chart_hdr_f.pack(fill="x")
        tk.Label(chart_hdr_f, text="📈 Biểu đồ đánh giá tổng hợp",
                 font=("Segoe UI", 8, "bold"), bg=BG3, fg=JILSA_GREEN).pack(side="left", padx=6, pady=3)
        tk.Button(chart_hdr_f, text="💾 Lưu biểu đồ",
                  font=("Segoe UI", 8), bg=BG3, fg=TEXT_DIM, relief="flat",
                  cursor="hand2", padx=6, pady=2,
                  command=lambda: self._paper_save_chart("jilsa")).pack(side="right", padx=4)
        tk.Button(chart_hdr_f, text="⛶ Toàn màn hình",
                  font=("Segoe UI", 8), bg=BG3, fg=TEXT_DIM, relief="flat",
                  cursor="hand2", padx=6, pady=2,
                  command=lambda: self._open_chart_fullscreen(
                      self._jilsa_chart_canvas, "Biểu đồ đánh giá JILSA"
                  )).pack(side="right", padx=4)
        chart_mode_f = tk.Frame(chart_wrap, bg=BG3)
        chart_mode_f.pack(fill="x", pady=(2, 0))
        for mode, label in [
            ("summary", "Metrics"),
            ("history", "History"),
            ("cm", "Ma trận nhầm lẫn"),
            ("class", "Từng class"),
        ]:
            btn = tk.Button(
                chart_mode_f,
                text=label,
                font=("Segoe UI", 8),
                bg=BG2,
                fg=TEXT,
                relief="flat",
                cursor="hand2",
                padx=8,
                pady=3,
                command=lambda m=mode: self._paper_show_chart("jilsa", m),
            )
            btn.pack(side="left", padx=(4, 2))
            self._paper_chart_mode_buttons["jilsa"][mode] = btn
        self._jilsa_chart_canvas = tk.Canvas(chart_wrap, bg=JILSA_BANNER_BG, height=340,
                                             highlightthickness=0)
        self._jilsa_chart_canvas.pack(fill="both", expand=True, pady=(4, 0))
        self._jilsa_chart_canvas.bind(
            "<Double-Button-1>",
            lambda _e: self._open_chart_fullscreen(
                self._jilsa_chart_canvas, "Biểu đồ đánh giá JILSA"
            ),
        )
        self._jilsa_chart_caption_lbl = tk.Label(
            chart_wrap,
            text="Biểu đồ hiện tại: Chưa có dữ liệu biểu đồ",
            font=("Segoe UI", 8, "italic"),
            bg=BG3,
            fg=TEXT_DIM,
            anchor="w",
            justify="left",
        )
        self._jilsa_chart_caption_lbl.pack(fill="x", pady=(4, 0))
        self._jilsa_chart_tk_img = None

        log_f = tk.Frame(lower, bg=BG)
        log_f.pack(fill="both", expand=True)
        tk.Label(log_f, text="📋 Log đánh giá",
                 font=("Segoe UI", 9, "bold"), bg=BG, fg=JILSA_GREEN).pack(anchor="w")
        self._jilsa_log = _st.ScrolledText(
            log_f, bg="#070d08", fg="#d4d4d4",
            insertbackground="white", relief="flat",
            font=("Cascadia Code", 8), wrap="word", state="disabled")
        self._jilsa_log.pack(fill="both", expand=True, pady=(4, 0))
        for tag, clr in [("ok", SUCCESS), ("warn", WARNING), ("err", DANGER),
                         ("info", INFO), ("dim", TEXT_DIM),
                         ("acc", JILSA_GREEN), ("cls", ACCENT2)]:
            self._jilsa_log.tag_config(tag, foreground=clr)

    # ═════════════════════════════════════════════════════════════════════════
    # TAB PLOS ONE 2024 — MobileNetV2 Evaluation
    # ═════════════════════════════════════════════════════════════════════════
    def _build_plos_tab(self, parent: tk.Frame):
        from tkinter import scrolledtext as _st

        banner = tk.Frame(parent, bg=PLOS_BANNER_BG, padx=14, pady=10)
        banner.pack(fill="x", padx=8, pady=(8, 0))
        tk.Label(banner, text="📱  PLOS ONE 2024 — MobileNetV2 Evaluation",
                 font=("Segoe UI", 12, "bold"), bg=PLOS_BANNER_BG, fg=PLOS_BLUE).pack(anchor="w")
        tk.Label(banner,
                 text="PLOS ONE 2024  ·  Loss: CrossEntropyLoss  ·  "
                      "Metric: Accuracy + Precision + Recall + F1 + Confusion Matrix\n"
                      "Test set: 15%  ·  Input: 224×224  ·  Arch: MobileNetV2 (~4.3M params)",
                 font=("Segoe UI", 8), bg=PLOS_BANNER_BG, fg=TEXT_DIM,
                 justify="left").pack(anchor="w", pady=(2, 0))

        paned = tk.PanedWindow(parent, orient="horizontal", bg=BG, sashwidth=5)
        paned.pack(fill="both", expand=True, padx=8, pady=8)

        left  = tk.Frame(paned, bg=BG2, padx=12, pady=10, width=310)
        right = tk.Frame(paned, bg=BG)
        paned.add(left,  minsize=280)
        paned.add(right, minsize=440)

        def sec(t):
            tk.Label(left, text=t, font=("Segoe UI", 9, "bold"),
                     bg=BG2, fg=PLOS_BLUE).pack(anchor="w", pady=(10, 2))

        sec("🤖 File model (.pth — MobileNetV2)")
        f_m = tk.Frame(left, bg=BG2); f_m.pack(fill="x", pady=2)
        ent_m = tk.Entry(f_m, textvariable=self._plos_model_var, font=("Segoe UI", 8))
        apply_entry_theme(ent_m)
        ent_m.pack(side="left", fill="x", expand=True, padx=(0, 2))
        tk.Button(f_m, text="...", bg=BG3, fg=TEXT, relief="flat", padx=4, cursor="hand2",
                  command=lambda: self._browse_file(
                      self._plos_model_var, "Chọn file .pth",
                      [("PyTorch weights", "*.pth"), ("All", "*.*")])
                  ).pack(side="left")

        sec("📁 Dataset folder (ImageFolder cấu trúc)")
        tk.Label(left, text="Mỗi class là 1 sub-folder con: dataset/class_name/img.jpg",
                 font=("Segoe UI", 7), bg=BG2, fg=TEXT_DIM, wraplength=265).pack(anchor="w")
        f_d = tk.Frame(left, bg=BG2); f_d.pack(fill="x", pady=2)
        ent_d = tk.Entry(f_d, textvariable=self._plos_data_var, font=("Segoe UI", 8))
        apply_entry_theme(ent_d)
        ent_d.pack(side="left", fill="x", expand=True, padx=(0, 2))
        tk.Button(f_d, text="📁", bg=BG3, fg=TEXT, relief="flat", padx=4, cursor="hand2",
                  command=lambda: self._browse_dir(
                      self._plos_data_var, "Chọn dataset folder")
                  ).pack(side="left")

        tk.Label(left, text="⚙ Class names: tự động đọc từ model",
                 font=("Segoe UI", 7, "italic"), bg=BG2, fg=TEXT_DIM).pack(anchor="w", pady=(6,4))
        for lbl, var, frm, to, inc in [
            ("Batch",    self._plos_batch_var,   1, 256, 1),
        ]:
            fr = tk.Frame(left, bg=BG2); fr.pack(fill="x", pady=2)
            tk.Label(fr, text=lbl, width=14, anchor="w",
                     font=("Segoe UI", 9), bg=BG2, fg=TEXT).pack(side="left")
            tk.Spinbox(fr, textvariable=var, from_=frm, to=to, increment=inc,
                       width=8, bg=BG3, fg=TEXT, buttonbackground=BG3,
                       insertbackground=TEXT, relief="flat",
                       font=("Segoe UI", 9)).pack(side="left")
        # ─ Image limit per class
        f_lim = tk.Frame(left, bg=BG2); f_lim.pack(fill="x", pady=2)
        tk.Label(f_lim, text="Giới hạn ảnh", width=14, anchor="w",
                 font=("Segoe UI", 9), bg=BG2, fg=TEXT).pack(side="left")
        tk.Spinbox(f_lim, textvariable=self._plos_limit_var, from_=0, to=99999, increment=10,
                   width=8, bg=BG3, fg=TEXT, buttonbackground=BG3,
                   insertbackground=TEXT, relief="flat",
                   font=("Segoe UI", 9)).pack(side="left")
        tk.Label(f_lim, text=" ảnh/class  (0 = không giới hạn)",
                 font=("Segoe UI", 7, "italic"), bg=BG2, fg=WARNING).pack(side="left", padx=4)
        f_dev = tk.Frame(left, bg=BG2); f_dev.pack(fill="x", pady=2)
        tk.Label(f_dev, text="Device", width=14, anchor="w",
                 font=("Segoe UI", 9), bg=BG2, fg=TEXT).pack(side="left")
        ttk.Combobox(f_dev, textvariable=self._plos_device_var,
                     values=["cuda", "cpu"], state="readonly",
                     font=("Segoe UI", 9), width=8).pack(side="left")

        sec("💾 Folder lưu kết quả")
        f_out = tk.Frame(left, bg=BG2); f_out.pack(fill="x", pady=2)
        ent_out = tk.Entry(f_out, textvariable=self._plos_out_var, font=("Segoe UI", 8))
        apply_entry_theme(ent_out)
        ent_out.pack(side="left", fill="x", expand=True, padx=(0, 2))
        tk.Button(f_out, text="📁", bg=BG3, fg=TEXT, relief="flat", padx=4, cursor="hand2",
                  command=lambda: self._browse_dir(
                      self._plos_out_var, "Chọn folder lưu kết quả")
                  ).pack(side="left")

        btn_f = tk.Frame(left, bg=BG2); btn_f.pack(fill="x", pady=(14, 4))
        self._plos_run_btn = tk.Button(
            btn_f, text="▶  Bắt đầu Đánh giá",
            font=("Segoe UI", 10, "bold"),
            bg="#1d4ed8", fg="white", relief="flat", cursor="hand2", pady=8,
            command=self._start_plos_eval)
        self._plos_run_btn.pack(fill="x", pady=2)
        self._plos_stop_btn = tk.Button(
            btn_f, text="⏹  Dừng",
            font=("Segoe UI", 9, "bold"), bg=DANGER, fg="white",
            relief="flat", cursor="hand2", pady=6, state="disabled",
            command=lambda: self._stop_paper_eval("plos"))
        self._plos_stop_btn.pack(fill="x", pady=2)
        tk.Button(btn_f, text="🗑  Xóa Log",
                  font=("Segoe UI", 9), bg=BG3, fg=TEXT_DIM,
                  relief="flat", cursor="hand2", pady=5,
                  command=lambda: self._paper_log_clear("plos")).pack(fill="x", pady=2)
        self._plos_open_btn = tk.Button(
            btn_f, text="📂  Mở thư mục kết quả",
            font=("Segoe UI", 9), bg=BG3, fg=SUCCESS,
            relief="flat", cursor="hand2", pady=6, state="disabled",
            command=lambda: self._paper_open_output(self._plos_out_var))
        self._plos_open_btn.pack(fill="x", pady=2)
        self._plos_status_lbl = tk.Label(left, text="⏹ Chưa chạy",
            font=("Segoe UI", 9, "bold"), bg=BG2, fg=TEXT_DIM)
        self._plos_status_lbl.pack(anchor="w", pady=(8, 0))

        # ── Right ──
        sum_f = tk.Frame(right, bg=PLOS_BANNER_BG, padx=16, pady=8)
        sum_f.pack(fill="x", padx=8, pady=(4, 4))
        tk.Label(sum_f, text="KẾT QUẢ", font=("Segoe UI", 8, "bold"),
                 bg=PLOS_BANNER_BG, fg=TEXT_DIM).pack(side="left")
        self._plos_acc_lbl = tk.Label(sum_f, text="Accuracy: —",
            font=("Segoe UI", 20, "bold"), bg=PLOS_BANNER_BG, fg=PLOS_BLUE)
        self._plos_acc_lbl.pack(side="left", padx=16)
        self._plos_f1_lbl = tk.Label(sum_f, text="",
            font=("Segoe UI", 10), bg=PLOS_BANNER_BG, fg=INFO)
        self._plos_f1_lbl.pack(side="left", padx=8)
        self._plos_elapsed_lbl = tk.Label(sum_f, text="",
            font=("Segoe UI", 9), bg=PLOS_BANNER_BG, fg=TEXT_DIM)
        self._plos_elapsed_lbl.pack(side="right")

        right_paned = tk.PanedWindow(right, orient="vertical", bg=BG,
                                     sashwidth=4, sashrelief="flat")
        right_paned.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        upper = tk.Frame(right_paned, bg=BG)
        lower = tk.Frame(right_paned, bg=BG)
        right_paned.add(upper, minsize=420)
        right_paned.add(lower, minsize=110)

        metrics_frame = tk.Frame(upper, bg=BG3, padx=8, pady=8)
        metrics_frame.pack(fill="x", pady=(0, 4))
        tk.Label(metrics_frame, text="Val Metrics",
                 font=("Segoe UI", 8, "bold"), bg=BG3, fg=PLOS_BLUE).pack(anchor="w", padx=2)
        self._plos_metrics_frame = tk.Frame(metrics_frame, bg=BG3)
        self._plos_metrics_frame.pack(fill="x", pady=(6, 0))

        cls_frame = tk.Frame(upper, bg=BG2)
        cls_frame.pack(fill="x", pady=(0, 4))
        tk.Label(cls_frame, text="📊 Kết quả từng class (Precision · Recall · F1)",
                 font=("Segoe UI", 8, "bold"), bg=BG2, fg=PLOS_BLUE).pack(anchor="w", padx=6)
        self._plos_cls_tbl = tk.Frame(cls_frame, bg=BG2)
        self._plos_cls_tbl.pack(fill="x", padx=6, pady=2)
        tk.Label(self._plos_cls_tbl, text="(chưa chạy)",
                 font=("Segoe UI", 8), bg=BG2, fg=TEXT_DIM).pack(anchor="w", pady=2)

        # ── Chart panel ──
        chart_wrap = tk.Frame(upper, bg=BG3, padx=4, pady=4)
        chart_wrap.pack(fill="both", expand=True, pady=(2, 0))
        chart_hdr_f = tk.Frame(chart_wrap, bg=BG3)
        chart_hdr_f.pack(fill="x")
        tk.Label(chart_hdr_f, text="📈 Biểu đồ đánh giá tổng hợp",
                 font=("Segoe UI", 8, "bold"), bg=BG3, fg=PLOS_BLUE).pack(side="left", padx=6, pady=3)
        tk.Button(chart_hdr_f, text="💾 Lưu biểu đồ",
                  font=("Segoe UI", 8), bg=BG3, fg=TEXT_DIM, relief="flat",
                  cursor="hand2", padx=6, pady=2,
                  command=lambda: self._paper_save_chart("plos")).pack(side="right", padx=4)
        tk.Button(chart_hdr_f, text="⛶ Toàn màn hình",
                  font=("Segoe UI", 8), bg=BG3, fg=TEXT_DIM, relief="flat",
                  cursor="hand2", padx=6, pady=2,
                  command=lambda: self._open_chart_fullscreen(
                      self._plos_chart_canvas, "Biểu đồ đánh giá PLOS"
                  )).pack(side="right", padx=4)
        chart_mode_f = tk.Frame(chart_wrap, bg=BG3)
        chart_mode_f.pack(fill="x", pady=(2, 0))
        for mode, label in [
            ("summary", "Metrics"),
            ("history", "History"),
            ("cm", "Ma trận nhầm lẫn"),
            ("class", "Từng class"),
        ]:
            btn = tk.Button(
                chart_mode_f,
                text=label,
                font=("Segoe UI", 8),
                bg=BG2,
                fg=TEXT,
                relief="flat",
                cursor="hand2",
                padx=8,
                pady=3,
                command=lambda m=mode: self._paper_show_chart("plos", m),
            )
            btn.pack(side="left", padx=(4, 2))
            self._paper_chart_mode_buttons["plos"][mode] = btn
        self._plos_chart_canvas = tk.Canvas(chart_wrap, bg=PLOS_BANNER_BG, height=340,
                                            highlightthickness=0)
        self._plos_chart_canvas.pack(fill="both", expand=True, pady=(4, 0))
        self._plos_chart_canvas.bind(
            "<Double-Button-1>",
            lambda _e: self._open_chart_fullscreen(
                self._plos_chart_canvas, "Biểu đồ đánh giá PLOS"
            ),
        )
        self._plos_chart_caption_lbl = tk.Label(
            chart_wrap,
            text="Biểu đồ hiện tại: Chưa có dữ liệu biểu đồ",
            font=("Segoe UI", 8, "italic"),
            bg=BG3,
            fg=TEXT_DIM,
            anchor="w",
            justify="left",
        )
        self._plos_chart_caption_lbl.pack(fill="x", pady=(4, 0))
        self._plos_chart_tk_img = None

        log_f = tk.Frame(lower, bg=BG)
        log_f.pack(fill="both", expand=True)
        tk.Label(log_f, text="📋 Log đánh giá",
                 font=("Segoe UI", 9, "bold"), bg=BG, fg=PLOS_BLUE).pack(anchor="w")
        self._plos_log = _st.ScrolledText(
            log_f, bg="#07090d", fg="#d4d4d4",
            insertbackground="white", relief="flat",
            font=("Cascadia Code", 8), wrap="word", state="disabled")
        self._plos_log.pack(fill="both", expand=True, pady=(4, 0))
        for tag, clr in [("ok", SUCCESS), ("warn", WARNING), ("err", DANGER),
                         ("info", INFO), ("dim", TEXT_DIM),
                         ("acc", PLOS_BLUE), ("cls", ACCENT2)]:
            self._plos_log.tag_config(tag, foreground=clr)

    # ═════════════════════════════════════════════════════════════════════════
    # PAPER EVAL — SHARED BACKEND
    # ═════════════════════════════════════════════════════════════════════════
    def _paper_log_write(self, which: str, text: str, tag: str = ""):
        log = self._jilsa_log if which == "jilsa" else self._plos_log
        def _w():
            log.configure(state="normal")
            if tag:
                log.insert("end", text, tag)
            else:
                log.insert("end", text)
            log.configure(state="disabled")
            log.see("end")
        self.after(0, _w)

    def _paper_log_clear(self, which: str):
        log = self._jilsa_log if which == "jilsa" else self._plos_log
        log.configure(state="normal")
        log.delete("1.0", "end")
        log.configure(state="disabled")

    def _paper_open_output(self, out_var: tk.StringVar):
        import subprocess as _sp
        p = out_var.get().strip()
        if p and Path(p).exists():
            _sp.Popen(["explorer", str(Path(p).resolve())])
        else:
            messagebox.showinfo("ℹ", "Thư mục chưa tồn tại.")

    def _stop_paper_eval(self, which: str):
        proc = self._jilsa_process if which == "jilsa" else self._plos_process
        if proc and proc.poll() is None:
            proc.terminate()
            self._paper_log_write(which, "\n⏹ Đã gửi lệnh dừng...\n", "warn")
            lbl = self._jilsa_status_lbl if which == "jilsa" else self._plos_status_lbl
            lbl.configure(text="⏹ Đang dừng...", fg=WARNING)

    def _start_jilsa_eval(self):
        self._start_paper_eval("jilsa")

    def _start_plos_eval(self):
        self._start_paper_eval("plos")

    def _start_paper_eval(self, which: str):
        import threading as _th, time as _t, os as _os

        if which == "jilsa":
            if self._jilsa_running:
                messagebox.showinfo("⏳", "Đánh giá JILSA đang chạy.")
                return
            model_path  = self._jilsa_model_var.get().strip()
            data_root   = self._jilsa_data_var.get().strip()
            imgsz       = self._jilsa_imgsz_var.get()
            batch       = self._jilsa_batch_var.get()
            img_limit   = self._jilsa_limit_var.get()
            device_str  = self._jilsa_device_var.get()
            _model_stem = Path(model_path).stem.lower()
            _sub = "jilsa" if "jilsa" in _model_stem else ("plos" if "lumpy" in _model_stem else "jilsa")
            out_dir     = self._jilsa_out_var.get().strip() or str(EVAL_BASE_DIR / _sub)
            run_btn     = self._jilsa_run_btn
            stop_btn    = self._jilsa_stop_btn
            open_btn    = self._jilsa_open_btn
            status_lbl  = self._jilsa_status_lbl
            acc_lbl     = self._jilsa_acc_lbl
            f1_lbl      = self._jilsa_f1_lbl
            elapsed_lbl = self._jilsa_elapsed_lbl
            metrics_fr  = self._jilsa_metrics_frame
            cls_tbl     = self._jilsa_cls_tbl
            paper_name  = "JILSA 2022 (CustomCNN)"
            is_mobilenet = False
        else:
            if self._plos_running:
                messagebox.showinfo("⏳", "Đánh giá PLOS ONE đang chạy.")
                return
            model_path  = self._plos_model_var.get().strip()
            data_root   = self._plos_data_var.get().strip()
            imgsz       = self._plos_imgsz_var.get()
            batch       = self._plos_batch_var.get()
            img_limit   = self._plos_limit_var.get()
            device_str  = self._plos_device_var.get()
            _model_stem = Path(model_path).stem.lower()
            _sub = "plos" if "lumpy" in _model_stem else ("jilsa" if "jilsa" in _model_stem else "plos")
            out_dir     = self._plos_out_var.get().strip() or str(EVAL_BASE_DIR / _sub)
            run_btn     = self._plos_run_btn
            stop_btn    = self._plos_stop_btn
            open_btn    = self._plos_open_btn
            status_lbl  = self._plos_status_lbl
            acc_lbl     = self._plos_acc_lbl
            f1_lbl      = self._plos_f1_lbl
            elapsed_lbl = self._plos_elapsed_lbl
            metrics_fr  = self._plos_metrics_frame
            cls_tbl     = self._plos_cls_tbl
            paper_name  = "PLOS ONE 2024 (MobileNetV2)"
            is_mobilenet = True

        if not model_path or not Path(model_path).exists():
            messagebox.showerror("Lỗi", "Chọn file .pth hợp lệ.")
            return
        if not data_root or not Path(data_root).exists():
            messagebox.showerror("Lỗi", "Chọn dataset folder hợp lệ.")
            return

        mp  = model_path.replace("\\", "/")
        ep  = data_root.replace("\\", "/")
        odp = out_dir.replace("\\", "/")

        if which == "jilsa":
            self._jilsa_running = True
        else:
            self._plos_running = True
        run_btn.configure(state="disabled", text="⏳ Đang đánh giá...")
        stop_btn.configure(state="normal")
        status_lbl.configure(text="🔄 Đang đánh giá...", fg=WARNING)
        acc_lbl.configure(text="Accuracy: —")
        f1_lbl.configure(text="")
        elapsed_lbl.configure(text="")
        for w in metrics_fr.winfo_children():
            w.destroy()
        for w in cls_tbl.winfo_children():
            w.destroy()
        self._paper_log_clear(which)
        self._paper_log_write(which, f"{'='*60}\n  {paper_name}\n{'='*60}\n", "acc")
        self._paper_log_write(which, f"Model : {model_path}\n", "info")
        self._paper_log_write(which, f"Data  : {data_root}\n", "info")
        self._paper_log_write(which, f"ImgSz={imgsz}  Batch={batch}  Device={device_str}"
                              + (f"  Giới hạn={img_limit} ảnh\n\n" if img_limit > 0 else "  Giới hạn=Không\n\n"),
                              "info")

        # ── Đọc checkpoint để lấy num_classes + class names ngay bây giờ ──
        try:
            import torch as _torch
            _ckpt_pre = _torch.load(model_path, map_location="cpu", weights_only=True)
        except Exception:
            try:
                _ckpt_pre = _torch.load(model_path, map_location="cpu", weights_only=False)
            except Exception as _e:
                messagebox.showerror("Lỗi load model", f"Không đọc được file .pth:\n{_e}")
                return
        _state_pre = _ckpt_pre.get("model_weights", _ckpt_pre) if isinstance(_ckpt_pre, dict) else _ckpt_pre
        # Detect num_classes from last Linear layer weight (same logic as _cmp_load_model)
        ckpt_num_classes = 0
        if "classifier.4.weight" in _state_pre:          # JILSA CustomCNN
            ckpt_num_classes = int(_state_pre["classifier.4.weight"].shape[0])
        elif "classifier.1.weight" in _state_pre:        # MobileNetV2 2-layer head (old)
            # Check if this is the hidden layer (shape[0]==128) or final layer
            _w1 = _state_pre["classifier.1.weight"]
            if _w1.shape[0] == 128 and "classifier.4.weight" not in _state_pre:
                # 5-layer head: last layer is classifier.4
                # classifier.4 not found but classifier.1 is 128→1280 → need classifier.4
                # Try classifier.4 explicitly (already checked), fallback: scan
                _weight_keys = [k for k in _state_pre if k.endswith(".weight")]
                _last_w = _state_pre[_weight_keys[-1]] if _weight_keys else None
                ckpt_num_classes = int(_last_w.shape[0]) if _last_w is not None and len(_last_w.shape) >= 1 else 0
            else:
                ckpt_num_classes = int(_w1.shape[0])
        if ckpt_num_classes == 0:
            # Generic fallback: last weight tensor (sorted by key)
            _weight_keys = [k for k in _state_pre if k.endswith(".weight")]
            if _weight_keys:
                _last_w = _state_pre[_weight_keys[-1]]
                ckpt_num_classes = int(_last_w.shape[0]) if len(_last_w.shape) >= 1 else 2
            else:
                ckpt_num_classes = 2  # ultimate fallback
        ckpt_classes = (_ckpt_pre.get("class_names") or _ckpt_pre.get("classes") or []) \
            if isinstance(_ckpt_pre, dict) else []

        # Auto-detect class names: checkpoint → fallback class_0..n
        if ckpt_classes and len(ckpt_classes) == ckpt_num_classes:
            resolved_classes = list(ckpt_classes)
            cls_source = "checkpoint (class_names)"
        else:
            resolved_classes = [f"class_{i}" for i in range(ckpt_num_classes)]
            cls_source = "fallback (không có trong file .pth)"

        self._paper_log_write(which, f"Classes ({ckpt_num_classes}, nguồn={cls_source}): {', '.join(resolved_classes)}\n", "info")

        # Build the evaluation script — architecture khớp đúng với bài báo
        if is_mobilenet:
            # PLOS ONE 2024: MobileNetV2 — 5-layer classifier head (khớp với train.py)
            model_build_code = """
# PLOS ONE 2024 — MobileNetV2 (Transfer Learning)
# Kiến trúc classifier head khớp đúng train.py:
#   Dropout(0.2) → Linear(1280,128) → ReLU → Dropout(0.2) → Linear(128, num_classes)
model = models.mobilenet_v2(weights=None)
model.classifier = nn.Sequential(
    nn.Dropout(p=0.2),
    nn.Linear(model.last_channel, 128),
    nn.ReLU(inplace=True),
    nn.Dropout(p=0.2),
    nn.Linear(128, num_classes),
)
"""
        else:
            # JILSA 2022: Custom CNN — 4 conv blocks + AdaptiveAvgPool2d + FC classifier
            model_build_code = """
# JILSA 2022 — Custom CNN (tái hiện đúng kiến trúc bài báo)
class CustomCNN(nn.Module):
    def __init__(self, num_classes=3):
        super(CustomCNN, self).__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(True), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(True), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(True), nn.MaxPool2d(2),
            nn.Conv2d(128, 256, 3, padding=1), nn.BatchNorm2d(256), nn.ReLU(True), nn.MaxPool2d(2),
            nn.AdaptiveAvgPool2d((9, 9)))
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(256 * 9 * 9, 512),
            nn.ReLU(True),
            nn.Dropout(0.5),
            nn.Linear(512, num_classes))
    def forward(self, x):
        return self.classifier(self.features(x))
model = CustomCNN(num_classes=num_classes)
"""

        script = f"""
import sys, json, time as _time, datetime, os
from pathlib import Path
from collections import defaultdict
import torch, torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models

DEVICE = torch.device("cpu") if "{device_str}" == "cpu" or not torch.cuda.is_available() else torch.device("cuda")
print(f"[INFO] Device: {{DEVICE}}", flush=True)
if DEVICE.type == "cuda":
    print(f"[INFO] GPU: {{torch.cuda.get_device_name(0)}}", flush=True)

tf = transforms.Compose([
    transforms.Resize(({imgsz}, {imgsz})),
    transforms.ToTensor(),
    transforms.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225]),
])

import random as _rnd
from torch.utils.data import Dataset as _Dataset, Subset as _Sub
from PIL import Image as _PILImage

_eval_root = Path("{ep}")
_EXTS = {{'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tif', '.tiff'}}

# ── num_classes và class list đã được xác định từ checkpoint trước khi chạy ──
num_classes = {ckpt_num_classes}
_cls_list   = {resolved_classes!r}
_cls2idx    = {{c: i for i, c in enumerate(_cls_list)}}
print(f"[INFO] num_classes: {{num_classes}}  |  classes: {{', '.join(_cls_list)}}", flush=True)

# ── Load checkpoint ───────────────────────────────────────────────────
try:
    _ckpt = torch.load("{mp}", map_location="cpu", weights_only=True)
except Exception:
    _ckpt = torch.load("{mp}", map_location="cpu", weights_only=False)
_state = _ckpt.get("model_weights", _ckpt) if isinstance(_ckpt, dict) else _ckpt

# ── Auto-detect: subfolder-per-class  OR  flat folder ────────────────
# Sort theo tên folder (giống datasets.ImageFolder của PyTorch — sorted(os.listdir()))
_subdirs = sorted([d for d in _eval_root.iterdir()
                   if d.is_dir() and not d.name.startswith('.')],
                  key=lambda d: d.name)
_flat_imgs = sorted([f for f in _eval_root.iterdir() if f.suffix.lower() in _EXTS])

_use_subfolder = len(_subdirs) > 0 and len(_flat_imgs) == 0

if _use_subfolder:
    # ── MODE 1: subfolder-per-class (ImageFolder style) ──────────────
    print(f"[INFO] Chế độ: Subfolder-per-class ({{len(_subdirs)}} class folders)", flush=True)
    # Use subfolder names as class labels (override injected _cls_list if sizes match)
    _folder_classes = [d.name for d in _subdirs]
    if len(_folder_classes) == num_classes:
        _cls_list  = _folder_classes
        _cls2idx   = {{c: i for i, c in enumerate(_cls_list)}}
        print(f"[INFO] Class names từ sub-folder (A-Z như ImageFolder):", flush=True)
        for _i, _cn in enumerate(_cls_list):
            print(f"[INFO]   index {{_i}} → {{_cn}}", flush=True)
        print(f"[WARN] Đảm bảo thứ tự A-Z này khớp với lúc train!", flush=True)
    else:
        print(f"[WARN] Số sub-folder ({{len(_folder_classes)}}) ≠ num_classes ({{num_classes}}). Dùng tên folder.", flush=True)
        _cls_list  = _folder_classes
        _cls2idx   = {{c: i for i, c in enumerate(_cls_list)}}
        for _i, _cn in enumerate(_cls_list):
            print(f"[INFO]   index {{_i}} → {{_cn}}", flush=True)
    # Collect (path, label) pairs from subfolders
    _samples_sf: list = []
    for _d in _subdirs:
        _lbl = _cls2idx.get(_d.name, -1)
        for _f in sorted(_d.iterdir()):
            if _f.suffix.lower() in _EXTS:
                _samples_sf.append((_f, _lbl))
    _all_imgs = [s[0] for s in _samples_sf]
    _sf_labels = [s[1] for s in _samples_sf]
    print(f"[INFO] Tổng ảnh tìm thấy: {{len(_all_imgs)}}", flush=True)
    for _cn, _ci in _cls2idx.items():
        _cnt = sum(1 for l in _sf_labels if l == _ci)
        print(f"[INFO]   {{_cn}}: {{_cnt}} ảnh", flush=True)
else:
    # ── MODE 2: flat folder — match class name trong filename ─────────
    print(f"[INFO] Chế độ: Flat folder", flush=True)
    _all_imgs = _flat_imgs
    _sf_labels = None

if not _all_imgs:
    print(f"[ERROR] Không tìm thấy ảnh trong: {{_eval_root}}", flush=True)
    print(f"[ERROR] Hãy kiểm tra: đường dẫn đúng chưa? folder có ảnh không?", flush=True)
    sys.exit(1)
print(f"[INFO] Tổng ảnh tìm thấy: {{len(_all_imgs)}}", flush=True)

# ── Giới hạn tổng số ảnh ─────────────────────────────────────────────
_img_limit = {img_limit}
if _img_limit > 0 and len(_all_imgs) > _img_limit:
    _rnd.shuffle(_all_imgs)
    _all_imgs = sorted(_all_imgs[:_img_limit])
    if _sf_labels is not None:
        _sf_labels = [_sf_labels[_all_imgs.index(f)] for f in _all_imgs]
    print(f"[INFO] Giới hạn {{_img_limit}} ảnh → còn {{len(_all_imgs)}} ảnh", flush=True)

# ── Dataset wrapper ───────────────────────────────────────────────────
class _FlatDS(_Dataset):
    def __init__(self, files, labels, tf):
        self.files = files
        self.samples = list(zip([str(f) for f in files], labels))
        self.tf = tf
    def __len__(self): return len(self.samples)
    def __getitem__(self, i):
        path, lbl = self.samples[i]
        img = _PILImage.open(path).convert('RGB')
        return self.tf(img), lbl

if _sf_labels is not None:
    # Subfolder mode: labels already known
    _labels_list = _sf_labels
else:
    # Flat mode: detect label from filename
    _cls_lower = {{c.lower(): i for c, i in _cls2idx.items()}}
    def _detect_label(fname: str) -> int:
        stem = Path(fname).stem.lower()
        prefix = stem.split('_')[0]
        if prefix in _cls_lower:
            return _cls_lower[prefix]
        _hits = [(len(c), idx) for c, idx in _cls_lower.items() if c in stem]
        if _hits:
            return sorted(_hits, reverse=True)[0][1]
        return -1
    _labels_list = [_detect_label(f.name) for f in _all_imgs]

_ds_full = _FlatDS(_all_imgs, _labels_list, tf)
_valid_idx = [i for i, (_, lbl) in enumerate(_ds_full.samples) if lbl >= 0]
_skipped = len(_all_imgs) - len(_valid_idx)
if _skipped > 0:
    _bad_names = [Path(_ds_full.samples[i][0]).name
                  for i in range(len(_ds_full.samples)) if _ds_full.samples[i][1] < 0][:5]
    print(f"[WARN] Bỏ {{_skipped}} ảnh không nhận ra class. VD: {{', '.join(_bad_names)}}", flush=True)
    print(f"[WARN] Class list: {{', '.join(_cls_list)}}", flush=True)
ds = _Sub(_ds_full, _valid_idx)
ds.classes = _cls_list
print(f"[INFO] Tổng ảnh sử dụng: {{len(ds)}}", flush=True)

loader = DataLoader(ds, batch_size={batch}, shuffle=False, num_workers=0,
                    pin_memory=(DEVICE.type=="cuda"))

{model_build_code}
_load_result = model.load_state_dict(_state, strict=False)
if _load_result.missing_keys:
    print(f"[WARN] Missing keys ({{len(_load_result.missing_keys)}}): {{_load_result.missing_keys[:5]}}", flush=True)
if _load_result.unexpected_keys:
    print(f"[WARN] Unexpected keys ({{len(_load_result.unexpected_keys)}}): {{_load_result.unexpected_keys[:5]}}", flush=True)
if not _load_result.missing_keys and not _load_result.unexpected_keys:
    print("[INFO] Weights loaded: OK (strict match)", flush=True)
model.to(DEVICE); model.eval()
total_params = sum(p.numel() for p in model.parameters())
print(f"[INFO] Params: {{total_params:,}} ({{total_params/1e6:.2f}} M)", flush=True)
criterion = nn.CrossEntropyLoss()

all_preds, all_labels = [], []
loss_sum = 0.0
n_done = 0; n_total = len(ds)
t0 = _time.time()
with torch.no_grad():
    for imgs, lbls in loader:
        imgs = imgs.to(DEVICE)
        lbls_dev = lbls.to(DEVICE)
        logits = model(imgs)
        loss = criterion(logits, lbls_dev)
        loss_sum += float(loss.item()) * int(lbls_dev.size(0))
        _, preds = torch.max(logits, 1)
        all_preds.extend(preds.cpu().tolist())
        all_labels.extend(lbls.tolist())
        n_done += len(lbls)
        print(f"[PROG] {{n_done}}/{{n_total}}", flush=True)

infer_sec = _time.time() - t0
fps = n_total / max(infer_sec, 1e-6)
correct = sum(p==l for p,l in zip(all_preds, all_labels))
acc = correct / max(len(all_labels), 1)
val_loss = loss_sum / max(len(all_labels), 1)
print(f"[RESULT] Accuracy={{acc:.6f}} ValLoss={{val_loss:.6f}} ({{correct}}/{{len(all_labels)}}) FPS={{fps:.1f}} t={{infer_sec:.2f}}s", flush=True)

cls_correct = defaultdict(int); cls_total = defaultdict(int)
for p,l in zip(all_preds, all_labels):
    cls_total[l]+=1
    if p==l: cls_correct[l]+=1

macro_precision = None; macro_recall = None; macro_f1 = None; cm_arr = None
if not all_labels:
    print("[ERROR] Không có ảnh nào được đánh giá. Kiểm tra tên file — tên phải chứa tên class.", flush=True)
    print(f"[ERROR] Class list: {{', '.join(ds.classes)}}", flush=True)
    sys.exit(1)
try:
    from sklearn.metrics import (classification_report,
        precision_recall_fscore_support, confusion_matrix)
    prec, rec, f1, _ = precision_recall_fscore_support(
        all_labels, all_preds, average=None, zero_division=0)
    macro_precision = float(prec.mean())
    macro_recall = float(rec.mean())
    macro_f1 = float(f1.mean())
    print(f"[RESULT] Macro-P={{macro_precision:.6f}} Macro-R={{macro_recall:.6f}} Macro-F1={{macro_f1:.6f}}", flush=True)
    for ci, cname in enumerate(ds.classes):
        tot=cls_total[ci]; cor=cls_correct[ci]; cacc=cor/max(tot,1)
        print(f"[CLASS] {{cname}}: Acc={{cacc:.4f}} P={{prec[ci]:.4f}} R={{rec[ci]:.4f}} F1={{f1[ci]:.4f}} ({{cor}}/{{tot}})", flush=True)
    rpt = classification_report(all_labels, all_preds, target_names=ds.classes, digits=4)
    print("[REPORT]", flush=True)
    for line in rpt.splitlines():
        print(f"  {{line}}", flush=True)
    cm_arr = confusion_matrix(all_labels, all_preds).tolist()
except ImportError:
    print("[WARN] sklearn không khả dụng — bỏ qua P/R/F1.", flush=True)
    for ci, cname in enumerate(ds.classes):
        tot=cls_total[ci]; cor=cls_correct[ci]
        print(f"[CLASS] {{cname}}: Acc={{cor/max(tot,1):.4f}} ({{cor}}/{{tot}})", flush=True)

out_dir = Path("{odp}"); out_dir.mkdir(parents=True, exist_ok=True)
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
results = {{
    "paper": "{paper_name}", "timestamp": datetime.datetime.now().isoformat(),
    "model": "{mp}", "eval_dir": "{ep}",
    "img_size": {imgsz}, "batch": {batch}, "device": str(DEVICE),
    "total_imgs": n_total, "accuracy": round(acc, 6), "correct": correct,
    "val_loss": round(val_loss, 6),
    "macro_precision": round(macro_precision, 6) if macro_precision is not None else None,
    "macro_recall": round(macro_recall, 6) if macro_recall is not None else None,
    "macro_f1": round(macro_f1, 6) if macro_f1 is not None else None,
    "fps": round(fps, 2), "infer_sec": round(infer_sec, 3), "params": total_params,
    "classes": {{
        cname: {{"total": cls_total[ci], "correct": cls_correct[ci],
                 "accuracy": round(cls_correct[ci]/max(cls_total[ci],1),6)}}
        for ci, cname in enumerate(ds.classes)
    }},
    "confusion_matrix": cm_arr,
}}
json_path = out_dir / f"eval_{{ts}}.json"
json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[SAVED] {{json_path}}", flush=True)

if cm_arr is not None:
    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt, numpy as np
        cm = np.array(cm_arr)
        fig, ax = plt.subplots(figsize=(max(5,num_classes*1.4), max(4,num_classes*1.2)))
        fig.patch.set_facecolor("#1e1e2e"); ax.set_facecolor("#252538")
        im = ax.imshow(cm, interpolation="nearest", cmap="Blues")
        plt.colorbar(im, ax=ax)
        ax.set_xticks(range(num_classes)); ax.set_yticks(range(num_classes))
        ax.set_xticklabels(ds.classes, rotation=35, ha="right", fontsize=9, color="white")
        ax.set_yticklabels(ds.classes, fontsize=9, color="white"); ax.tick_params(colors="white")
        thresh = cm.max()/2.0
        for i in range(num_classes):
            for j in range(num_classes):
                ax.text(j,i,str(cm[i,j]),ha="center",va="center",fontsize=11,fontweight="bold",
                        color="white" if cm[i,j]<thresh else "#1e1e2e")
        ax.set_xlabel("Dự đoán",color="white",fontsize=11); ax.set_ylabel("Nhãn thật",color="white",fontsize=11)
        ax.set_title(f"Confusion Matrix — {paper_name}\\nAcc={{acc:.4f}}",color="white",fontsize=11,fontweight="bold")
        plt.tight_layout()
        cm_path = out_dir / f"confusion_matrix_{{ts}}.png"
        fig.savefig(str(cm_path), dpi=130, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        print(f"[SAVED] {{cm_path}}", flush=True)
    except Exception as _e:
        print(f"[WARN] confusion matrix error: {{_e}}", flush=True)

print("[DONE] Đánh giá hoàn thành!", flush=True)
"""

        def _run():
            import subprocess
            env = {**_os.environ, "PYTHONUTF8": "1"}
            t_start = _t.time()
            pth_stats = None
            try:
                try:
                    pth_stats = self._get_pth_checkpoint_stats(model_path, imgsz)
                    if pth_stats and (pth_stats.get("params_m") is not None or pth_stats.get("gflops") is not None):
                        params_text = f"{pth_stats['params_m']:.3f} M" if pth_stats.get("params_m") is not None else "—"
                        gflops_text = f"{pth_stats['gflops']:.3f}" if pth_stats.get("gflops") is not None else "—"
                        stats_msg = (
                            f"[INFO] Params: {params_text}  |  GFLOPs: {gflops_text}\n"
                        )
                        self._paper_log_write(which, stats_msg, "info")
                except Exception:
                    pth_stats = None
                proc = subprocess.Popen(
                    [str(PYTHON_EXE), "-c", script],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1, encoding="utf-8", errors="replace",
                    cwd=str(ROOT_DIR), env=env,
                )
                if which == "jilsa":
                    self._jilsa_process = proc
                else:
                    self._plos_process = proc

                acc_val = None; f1_val = None; cls_data = []
                val_loss = None; macro_p = None; macro_r = None
                saved_json_path = ""
                for line in proc.stdout:
                    s = line.rstrip()
                    if "[PROG]" in s:
                        try:
                            parts = s.split("]")[1].strip().split("/")
                            done, total = int(parts[0]), int(parts[1])
                            pct = done / max(total, 1) * 100
                            self.after(0, elapsed_lbl.configure,
                                       {"text": f"{pct:.0f}%  {self._fmt_time(_t.time()-t_start)}"})
                        except Exception:
                            pass
                        continue
                    tag = ""
                    if "[RESULT]" in s:
                        tag = "acc"
                        for tok in s.split():
                            if tok.startswith("Accuracy="):
                                try: acc_val = float(tok.split("=")[1])
                                except Exception: pass
                            elif tok.startswith("ValLoss="):
                                try: val_loss = float(tok.split("=")[1])
                                except Exception: pass
                            elif tok.startswith("Macro-P="):
                                try: macro_p = float(tok.split("=")[1])
                                except Exception: pass
                            elif tok.startswith("Macro-R="):
                                try: macro_r = float(tok.split("=")[1])
                                except Exception: pass
                            elif tok.startswith("Macro-F1="):
                                try: f1_val = float(tok.split("=")[1])
                                except Exception: pass
                    elif "[CLASS]" in s:
                        tag = "cls"
                        try:
                            rest = s.split("] ", 1)[1]
                            cname, stats = rest.split(": ", 1)
                            d = {"name": cname.strip()}
                            for tok in stats.split():
                                if "=" in tok:
                                    k, v = tok.split("=", 1)
                                    try: d[k.lower()] = float(v)
                                    except Exception: pass
                            if "(" in stats:
                                frac = stats.split("(")[1].rstrip(")")
                                cor, tot = frac.split("/")
                                d["correct"] = int(cor); d["total"] = int(tot)
                            cls_data.append(d)
                        except Exception:
                            pass
                    elif s.startswith("[SAVED] ") and s.lower().endswith(".json"):
                        saved_json_path = s.split("] ", 1)[1].strip()
                        tag = "ok"
                    elif "[SAVED]" in s or "[DONE]" in s: tag = "ok"
                    elif "[WARN]" in s: tag = "warn"
                    elif "Traceback" in s or "Error" in s or "[ERROR]" in s: tag = "err"
                    elif "[INFO]" in s or "[REPORT]" in s: tag = "info"
                    elif s.startswith("  "): tag = "dim"
                    self._paper_log_write(which, s + "\n", tag)

                proc.wait()
                retcode = proc.returncode
            except Exception as ex:
                self._paper_log_write(which, f"\n[ERROR] {ex}\n", "err")
                retcode = -1

            def _done():
                elapsed = self._fmt_time(_t.time() - t_start)
                if which == "jilsa":
                    self._jilsa_running = False
                else:
                    self._plos_running = False
                run_btn.configure(state="normal", text="▶  Bắt đầu Đánh giá")
                stop_btn.configure(state="disabled")
                elapsed_lbl.configure(text=f"⏱ {elapsed}")
                if acc_val is not None:
                    acc_lbl.configure(text=f"Accuracy: {acc_val*100:.2f}%")
                if f1_val is not None:
                    f1_lbl.configure(text=f"Macro-F1: {f1_val*100:.2f}%")
                accent = JILSA_GREEN if which == "jilsa" else PLOS_BLUE
                if any(v is not None for v in (val_loss, acc_val, macro_p, macro_r, f1_val)):
                    summary_metrics = {
                        "val_loss": val_loss,
                        "accuracy": acc_val,
                        "macro_precision": macro_p,
                        "macro_recall": macro_r,
                        "macro_f1": f1_val,
                    }
                    self._paper_render_metrics(metrics_fr, summary_metrics, accent)
                else:
                    summary_metrics = None
                if cls_data:
                    self._paper_render_cls_table(cls_tbl, cls_data)
                    history_data = self._paper_find_history_data(which, model_path)
                    self._draw_pth_history_on_eval_canvas(history_data, summary_metrics)
                    cm_payload = []
                    cm_names = [d.get("name", f"Class {i + 1}") for i, d in enumerate(cls_data)]
                    if saved_json_path and Path(saved_json_path).exists():
                        try:
                            import json as _json
                            chart_payload = _json.loads(Path(saved_json_path).read_text(encoding="utf-8"))
                            cm_payload = chart_payload.get("confusion_matrix") or []
                            cls_map_payload = chart_payload.get("classes") or {}
                            if cls_map_payload:
                                cm_names = list(cls_map_payload.keys())
                        except Exception:
                            pass
                    self._paper_render_chart(
                        which,
                        cls_data,
                        acc_val,
                        f1_val,
                        summary_metrics,
                        history_data,
                        cm_payload,
                        cm_names,
                    )
                if retcode == 0:
                    status_lbl.configure(text="✔ Đánh giá xong!", fg=SUCCESS)
                    bench_metrics = None
                    if saved_json_path and Path(saved_json_path).exists():
                        try:
                            import json as _json
                            bench_metrics = _json.loads(Path(saved_json_path).read_text(encoding="utf-8"))
                        except Exception:
                            bench_metrics = None
                    if bench_metrics is None:
                        bench_metrics = {
                            "accuracy": acc_val,
                            "macro_f1": f1_val,
                            "val_loss": val_loss,
                            "classes": {d.get("name", f"c{i}"): d for i, d in enumerate(cls_data)},
                            "gflops": (pth_stats or {}).get("gflops"),
                        }
                    if pth_stats:
                        if bench_metrics.get("params") is None:
                            bench_metrics["params"] = pth_stats.get("params")
                        if bench_metrics.get("gflops") is None:
                            bench_metrics["gflops"] = pth_stats.get("gflops")
                    total_images = sum(int(d.get("total", 0) or 0) for d in cls_data) if cls_data else None
                    bench_info = self._paper_make_benchmark_info(
                        which, model_path, imgsz, total_images, bench_metrics
                    )
                    self._bench_reference_var.set("JILSA 2022" if which == "jilsa" else "PLOS ONE 2024")
                    self._draw_benchmark_comparison(bench_info)
                    open_btn.configure(state="normal")
                    self.after(500, self._hist_refresh)  # cập nhật tab Lịch sử
                else:
                    status_lbl.configure(text="✗ Lỗi / Đã dừng", fg=DANGER)
            self.after(0, _done)

        _th.Thread(target=_run, daemon=True).start()

    def _paper_render_cls_table(self, tbl_frame: tk.Frame, cls_data: list):
        for w in tbl_frame.winfo_children():
            w.destroy()
        has_prf = any("p" in d for d in cls_data)
        hdrs   = ["Class", "Accuracy", "Correct/Total"] + (["Precision","Recall","F1"] if has_prf else [])
        widths = [20, 10, 13] + ([9, 9, 9] if has_prf else [])
        for c, (h, w) in enumerate(zip(hdrs, widths)):
            tk.Label(tbl_frame, text=h, font=("Segoe UI", 8, "bold"),
                     bg=BG3, fg=ACCENT2, width=w, anchor="center",
                     pady=3, padx=4).grid(row=0, column=c, padx=1, pady=1, sticky="ew")
        for r, d in enumerate(cls_data, start=1):
            bg  = BG3 if r % 2 == 0 else BG2
            av  = d.get("acc", 0.0)
            fga = SUCCESS if av >= 0.9 else (WARNING if av >= 0.7 else DANGER)
            vals = [d.get("name","—"), f"{av*100:.2f}%",
                    f"{d.get('correct','?')}/{d.get('total','?')}"]
            if has_prf:
                vals += [f"{d.get('p',0.0):.4f}", f"{d.get('r',0.0):.4f}", f"{d.get('f1',0.0):.4f}"]
            for c, (val, w) in enumerate(zip(vals, widths)):
                fg = fga if c == 1 else ("white" if c == 0 else TEXT)
                tk.Label(tbl_frame, text=str(val), font=("Cascadia Code", 8),
                         bg=bg, fg=fg, width=w, anchor="center",
                         pady=2, padx=3).grid(row=r, column=c, padx=1, pady=1, sticky="ew")

    def _paper_render_metrics(self, frame: tk.Frame, metrics: dict, accent: str):
        for w in frame.winfo_children():
            w.destroy()
        cards = [
            ("Loss validation", metrics.get("val_loss")),
            ("Accuracy", metrics.get("accuracy")),
            ("Macro P", metrics.get("macro_precision")),
            ("Macro R", metrics.get("macro_recall")),
            ("Macro F1", metrics.get("macro_f1")),
        ]
        for idx, (label, value) in enumerate(cards):
            card = tk.Frame(frame, bg=BG2, padx=8, pady=6)
            card.grid(row=0, column=idx, padx=3, sticky="nsew")
            frame.grid_columnconfigure(idx, weight=1)
            tk.Label(card, text=label, font=("Segoe UI", 7, "bold"),
                     bg=BG2, fg=TEXT_DIM).pack(anchor="w")
            if value is None:
                text = "—"
            elif label == "Loss validation":
                text = f"{float(value):.4f}"
            else:
                text = f"{float(value) * 100:.2f}%"
            fg = accent if label in ("Accuracy", "Macro F1") and value is not None else TEXT
            tk.Label(card, text=text, font=("Cascadia Code", 9, "bold"),
                     bg=BG2, fg=fg).pack(anchor="w", pady=(4, 0))

    def _paper_make_benchmark_info(self, which: str, model_path: str, imgsz: int,
                                   total_images, metrics: dict):
        return make_paper_benchmark_info(which, imgsz, total_images, metrics)

    def _safe_float_or_none(self, value):
        if value is None:
            return None
        try:
            text = str(value).strip()
            if not text or text.lower() in {"none", "n/a", "na", "-", "—", "nan"}:
                return None
            return float(text)
        except Exception:
            return None

    def _fmt_percent_or_na(self, value):
        val = self._safe_float_or_none(value)
        if val is None:
            return "—"
        if val <= 1.0:
            val *= 100.0
        return f"{val:.2f}%"

    def _paper_history_candidates(self, which: str, model_path: str):
        from bll.test.history_service import paper_history_candidates

        return paper_history_candidates(which, model_path, RUNS_DIR)

    def _paper_find_history_data(self, which: str, model_path: str):
        return paper_find_history_data(which, model_path, RUNS_DIR)

    def _paper_sync_chart_mode_buttons(self, which: str):
        current = self._paper_chart_mode_var[which].get().strip() or "summary"
        accent = "#4ade80" if which == "jilsa" else "#60a5fa"
        for mode, btn in self._paper_chart_mode_buttons.get(which, {}).items():
            try:
                if mode == current:
                    btn.configure(bg=accent, fg="white")
                else:
                    btn.configure(bg=BG2, fg=TEXT)
            except Exception:
                pass

    def _paper_render_chart(self, which: str, cls_data: list,
                            acc_val: float | None, f1_val: float | None,
                            metrics: dict | None = None,
                            history: list | None = None,
                            confusion_matrix: list | None = None,
                            class_names: list | None = None):
        self._paper_chart_state[which] = {
            "cls_data": cls_data or [],
            "acc_val": acc_val,
            "f1_val": f1_val,
            "metrics": metrics or {},
            "history": history or [],
            "confusion_matrix": confusion_matrix or [],
            "class_names": list(class_names or []),
        }
        state = self._paper_chart_state[which]
        default_mode = "cm" if state["confusion_matrix"] else ("history" if state["history"] else "class")
        current = self._paper_chart_mode_var[which].get().strip()
        if current not in {"summary", "history", "cm", "class"}:
            current = default_mode
        if current == "cm" and not state["confusion_matrix"]:
            current = default_mode
        if current == "history" and not state["history"]:
            current = default_mode
        self._paper_show_chart(which, current)

    def _paper_show_chart(self, which: str, mode: str | None = None):
        state = self._paper_chart_state.get(which) or {}
        cls_data = state.get("cls_data") or []
        metrics_payload = state.get("metrics") or {}
        history_payload = state.get("history") or []
        cm_payload = state.get("confusion_matrix") or []
        cm_names = list(state.get("class_names") or [d.get("name", f"Class {i + 1}") for i, d in enumerate(cls_data)])
        acc_val = state.get("acc_val")
        f1_val = state.get("f1_val")
        canvas = self._jilsa_chart_canvas if which == "jilsa" else self._plos_chart_canvas
        accent = "#4ade80" if which == "jilsa" else "#60a5fa"

        available_modes = {"summary", "class"}
        if history_payload:
            available_modes.add("history")
        if cm_payload:
            available_modes.add("cm")
        if mode not in available_modes:
            mode = "cm" if "cm" in available_modes else ("history" if "history" in available_modes else "class")
        self._paper_chart_mode_var[which].set(mode)
        self._paper_sync_chart_mode_buttons(which)

        def _draw():
            try:
                import matplotlib
                matplotlib.use("Agg")
                import matplotlib.pyplot as plt
                import numpy as np
                from PIL import Image as _PIL
                import io

                cw = max(canvas.winfo_width(), 860)
                ch = max(canvas.winfo_height(), 360)
                fig, ax = plt.subplots(figsize=(cw / 96, ch / 96), dpi=96)
                fig.patch.set_facecolor("#1e1e2e")
                ax.set_facecolor("#13131f")
                ax.tick_params(colors="#9090b0", labelsize=8)
                ax.spines[:].set_color("#333350")

                caption = "Biểu đồ đánh giá"
                if mode == "summary":
                    summary_labels = []
                    summary_values = []
                    summary_colors = []
                    for key, label, color in [
                        ("val_loss", "Loss validation", "#f87171"),
                        ("accuracy", "Acc", accent),
                        ("macro_precision", "Macro P", "#f59e0b"),
                        ("macro_recall", "Macro R", "#38bdf8"),
                        ("macro_f1", "Macro F1", "#a78bfa"),
                    ]:
                        val = metrics_payload.get(key)
                        if val is None:
                            continue
                        summary_labels.append(label)
                        summary_values.append(float(val) if key == "val_loss" else float(val) * 100.0)
                        summary_colors.append(color)
                    if summary_labels:
                        bars = ax.bar(range(len(summary_labels)), summary_values, color=summary_colors, alpha=0.92, width=0.62)
                        ax.set_xticks(range(len(summary_labels)))
                        ax.set_xticklabels(summary_labels, fontsize=9, color="#c0c0e0")
                        ax.set_title("Chỉ số validation", color="#c0c0e0", fontsize=12, pad=8)
                        top_max = max(summary_values) if summary_values else 0.0
                        for idx, bar in enumerate(bars):
                            val = summary_values[idx]
                            txt = f"{val:.4f}" if summary_labels[idx] == "Loss validation" else f"{val:.2f}%"
                            ax.text(
                                bar.get_x() + bar.get_width() / 2,
                                bar.get_height() + (top_max * 0.03 if top_max > 0 else 0.05),
                                txt, ha="center", va="bottom", fontsize=8, color="#e2e8f0"
                            )
                    else:
                        ax.text(0.5, 0.5, "Chưa có validation metrics", ha="center", va="center",
                                color="#9090b0", fontsize=10, transform=ax.transAxes)
                        ax.set_xticks([])
                        ax.set_yticks([])
                    caption = "Các chỉ số validation tổng hợp"

                elif mode == "history":
                    epochs = [int(item.get("epoch", 0) or 0) for item in history_payload]
                    train_loss = [self._safe_float_or_none(item.get("train_loss")) for item in history_payload]
                    val_loss_hist = [self._safe_float_or_none(item.get("val_loss")) for item in history_payload]
                    val_acc = [
                        (self._safe_float_or_none(item.get("val_acc")) * 100.0)
                        if self._safe_float_or_none(item.get("val_acc")) is not None
                        else None
                        for item in history_payload
                    ]
                    ax.plot(
                        epochs,
                        [v if v is not None else float("nan") for v in train_loss],
                        color="#f97316", linewidth=1.8, marker=".", markersize=4, label="Loss huấn luyện"
                    )
                    if any(v is not None for v in val_loss_hist):
                        ax.plot(
                            epochs,
                            [v if v is not None else float("nan") for v in val_loss_hist],
                            color="#ef4444", linewidth=1.8, marker=".", markersize=4, label="Loss validation"
                        )
                    ax2 = ax.twinx()
                    ax2.set_facecolor("none")
                    ax2.tick_params(colors="#9090b0", labelsize=8)
                    ax2.spines[:].set_color("#333350")
                    if any(v is not None for v in val_acc):
                        ax2.plot(
                            epochs,
                            [v if v is not None else float("nan") for v in val_acc],
                            color=accent, linewidth=1.8, marker=".", markersize=4, label="Val Acc"
                        )
                    ax.set_title("Training History", color="#c0c0e0", fontsize=12, pad=8)
                    ax.set_xlabel("Epoch", color="#9090b0", fontsize=8)
                    ax.set_ylabel("Loss", color="#9090b0", fontsize=8)
                    ax2.set_ylabel("Val Acc (%)", color="#9090b0", fontsize=8)
                    l1, lb1 = ax.get_legend_handles_labels()
                    l2, lb2 = ax2.get_legend_handles_labels()
                    ax.legend(l1 + l2, lb1 + lb2, fontsize=7, facecolor="#1e1e2e",
                              labelcolor="#c0c0e0", framealpha=0.6, loc="upper right")
                    caption = "Đường Loss và Accuracy theo từng epoch"

                elif mode == "cm":
                    cm = np.array(cm_payload, dtype=float)
                    if cm.ndim != 2 or not cm.shape[0] or not cm.shape[1]:
                        raise ValueError("Không có dữ liệu confusion matrix")
                    names = list(cm_names[:cm.shape[0]]) if cm_names else [f"Class {i+1}" for i in range(cm.shape[0])]
                    support = cm.sum(axis=1, keepdims=True)
                    norm_cm = np.divide(cm, support, out=np.zeros_like(cm), where=support > 0)
                    im = ax.imshow(norm_cm, cmap="YlGn", vmin=0.0, vmax=1.0)
                    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
                    ax.set_xticks(range(len(names)))
                    ax.set_yticks(range(len(names)))
                    ax.set_xticklabels([name[:18] for name in names], rotation=30, ha="right", fontsize=9, color="#c0c0e0")
                    ax.set_yticklabels([name[:18] for name in names], fontsize=9, color="#c0c0e0")
                    ax.set_xlabel("Dự đoán", color="#9090b0", fontsize=8)
                    ax.set_ylabel("Nhãn thật", color="#9090b0", fontsize=8)
                    ax.set_title("Confusion Matrix", color="#c0c0e0", fontsize=12, pad=8)
                    for ri in range(len(names)):
                        for ci in range(len(names)):
                            cell_total = int(cm[ri, ci])
                            if cell_total <= 0:
                                continue
                            ax.text(
                                ci, ri, f"{cell_total}\n{norm_cm[ri, ci]:.2f}",
                                ha="center", va="center", fontsize=8,
                                color="#08130d" if norm_cm[ri, ci] >= 0.45 else "#f8fafc"
                            )
                    caption = "Ma trận nhầm lẫn chuẩn hóa của mô hình classification"

                else:
                    has_prf = any("p" in d for d in cls_data)
                    names = [d.get("name", f"cls{i}") for i, d in enumerate(cls_data)]
                    acc_vals = [d.get("acc", 0.0) * 100 for d in cls_data]
                    x = range(len(names))
                    if has_prf:
                        width = 0.18
                        offsets = [-1.5, -0.5, 0.5, 1.5]
                        keys = ["acc", "p", "r", "f1"]
                        labels = ["Accuracy", "Precision", "Recall", "F1"]
                        series = [
                            acc_vals,
                            [d.get("p", 0.0) * 100 for d in cls_data],
                            [d.get("r", 0.0) * 100 for d in cls_data],
                            [d.get("f1", 0.0) * 100 for d in cls_data],
                        ]
                        palette = {"acc": accent, "p": "#f59e0b", "r": "#38bdf8", "f1": "#a78bfa"}
                        for idx, (key, lbl, vals_s) in enumerate(zip(keys, labels, series)):
                            xs = [xi + offsets[idx] * width for xi in x]
                            ax.bar(xs, vals_s, width=width, color=palette[key], alpha=0.88, label=lbl)
                        ax.legend(fontsize=7, facecolor="#1e1e2e", labelcolor="#c0c0e0", framealpha=0.6, loc="lower right")
                    else:
                        ax.bar(list(x), acc_vals, color=accent, alpha=0.88, width=0.55)
                    ax.set_xticks(list(x))
                    ax.set_xticklabels(names, rotation=20, ha="right", fontsize=9, color="#c0c0e0")
                    ax.set_ylabel("%", color="#9090b0", fontsize=8)
                    ax.set_ylim(0, 110)
                    ax.set_xlim(-0.6, len(names) - 0.4 if names else 0.4)
                    for xi, av in zip(x, acc_vals):
                        ax.text(xi, av + 1.4, f"{av:.1f}", ha="center", va="bottom", fontsize=8, color="#e2e8f0")
                    title_parts = []
                    if acc_val is not None:
                        title_parts.append(f"Acc {acc_val * 100:.2f}%")
                    if f1_val is not None:
                        title_parts.append(f"Macro-F1 {f1_val * 100:.2f}%")
                    ax.set_title("  ·  ".join(title_parts) if title_parts else "Per-class results",
                                 color="#c0c0e0", fontsize=12, pad=8)
                    caption = "Biểu đồ kết quả trên từng class"

                plt.tight_layout(pad=1.0)
                buf = io.BytesIO()
                fig.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
                plt.close(fig)
                buf.seek(0)
                img = _PIL.open(buf).convert("RGB")
                tk_img, fitted = self._paint_pil_on_canvas(canvas, img, min_w=860, min_h=360)
                if which == "jilsa":
                    self._jilsa_chart_tk_img = tk_img
                    self._jilsa_chart_pil_img = fitted
                else:
                    self._plos_chart_tk_img = tk_img
                    self._plos_chart_pil_img = fitted
                self._set_chart_caption(which, caption)
            except ImportError:
                self._paper_draw_chart_plain(canvas, cls_data, accent)
            except Exception as ex:
                canvas.delete("all")
                canvas.create_text(
                    8, canvas.winfo_height() // 2 or 90,
                    text=f"⚠ Không vẽ được biểu đồ: {ex}",
                    fill=WARNING, font=("Segoe UI", 8), anchor="w")
                self._set_chart_caption(which, f"Lỗi vẽ biểu đồ: {ex}")

        self.after(40, _draw)

    def _paper_draw_chart_plain(self, canvas: tk.Canvas, cls_data: list, accent: str):
        """Fallback: vẽ bar chart tkinter thuần (không cần matplotlib)."""
        canvas.delete("all")
        cw = max(canvas.winfo_width(),  480)
        ch = max(canvas.winfo_height(), 180)
        PAD_L, PAD_R, PAD_T, PAD_B = 34, 12, 20, 36
        plot_w = cw - PAD_L - PAD_R
        plot_h = ch - PAD_T - PAD_B
        names    = [d.get("name", f"cls{i}") for i, d in enumerate(cls_data)]
        acc_vals = [d.get("acc", 0.0) * 100 for d in cls_data]
        n = max(len(names), 1)
        bar_w = plot_w / n * 0.6
        gap   = plot_w / n

        canvas.create_rectangle(PAD_L, PAD_T, PAD_L + plot_w, PAD_T + plot_h,
                                 outline="#333350", fill="#13131f")

        for i, (name, av) in enumerate(zip(names, acc_vals)):
            x0 = PAD_L + i * gap + (gap - bar_w) / 2
            y_top = PAD_T + plot_h * (1 - av / 100)
            clr = "#22c55e" if av >= 90 else ("#f59e0b" if av >= 70 else "#ef4444")
            canvas.create_rectangle(x0, y_top, x0 + bar_w, PAD_T + plot_h,
                                    fill=clr, outline="", width=0)
            canvas.create_text(x0 + bar_w / 2, y_top - 4,
                               text=f"{av:.1f}", fill="#e2e8f0",
                               font=("Segoe UI", 6), anchor="s")
            canvas.create_text(x0 + bar_w / 2, PAD_T + plot_h + 4,
                               text=name[:10], fill="#9090b0",
                               font=("Segoe UI", 6), anchor="n",
                               angle=30 if n > 6 else 0)

        # Y-axis labels
        for tick in [0, 25, 50, 75, 100]:
            y = PAD_T + plot_h * (1 - tick / 100)
            canvas.create_line(PAD_L - 3, y, PAD_L, y, fill="#555570")
            canvas.create_text(PAD_L - 5, y, text=f"{tick}",
                               fill="#9090b0", font=("Segoe UI", 6), anchor="e")

    def _paper_save_chart(self, which: str):
        """Lưu biểu đồ JILSA / PLOS từ ảnh PIL đã render."""
        import datetime

        pil_img = self._jilsa_chart_pil_img if which == "jilsa" else self._plos_chart_pil_img
        if pil_img is None:
            messagebox.showinfo("Thông báo", "Chưa có biểu đồ để lưu.\nHãy chạy đánh giá trước.")
            return

        paper_label = "JILSA2022" if which == "jilsa" else "PLOSONE2024"
        self._save_chart_pil_image(
            pil_img,
            title=f"Lưu biểu đồ {paper_label}",
            initialfile=f"chart_{paper_label}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
        )

    # ─────────────────────────────────────────────────────────────────────────
    # LỊCH SỬ ĐÁNH GIÁ — Tab 6
    # ─────────────────────────────────────────────────────────────────────────
    def _build_history_tab(self, parent: tk.Frame):
        """Xây dựng tab Lịch sử Đánh giá."""
        HIST_BG  = BG
        HIST_BG2 = BG2
        HIST_BG3 = BG3

        # ── Toolbar ────────────────────────────────────────────────────────
        toolbar = tk.Frame(parent, bg=HIST_BG3, pady=4)
        toolbar.pack(fill="x", padx=4, pady=(4, 0))

        tk.Label(toolbar, text="📋 Lịch sử Đánh giá Mô hình",
                 font=("Segoe UI", 11, "bold"), bg=HIST_BG3, fg=TEXT).pack(side="left", padx=10)

        tk.Button(toolbar, text="🔄 Làm mới", font=("Segoe UI", 8, "bold"),
                  bg=ACCENT, fg="white", relief="flat", padx=10, cursor="hand2",
                  command=self._hist_refresh).pack(side="right", padx=4)
        tk.Button(toolbar, text="🗑 Xóa đã chọn", font=("Segoe UI", 8),
                  bg=DANGER, fg="white", relief="flat", padx=10, cursor="hand2",
                  command=self._hist_delete_selected).pack(side="right", padx=4)
        tk.Button(toolbar, text="📂 Mở thư mục", font=("Segoe UI", 8),
                  bg=BG3, fg=TEXT, relief="flat", padx=10, cursor="hand2",
                  command=lambda: self._open_folder(str(RUNS_DIR))).pack(side="right", padx=4)

        # ── Tóm tắt counts ─────────────────────────────────────────────────
        self._hist_summary_lbl = tk.Label(parent, text="",
                                          font=("Segoe UI", 8), bg=HIST_BG, fg=TEXT_DIM)
        self._hist_summary_lbl.pack(anchor="w", padx=10, pady=(4, 0))

        # ── Table header ───────────────────────────────────────────────────
        HDR_COLS = [
            ("STT",            4),
            ("Thời gian",     17),
            ("Mô hình",       20),
            ("Bài báo",       14),
            ("Accuracy",       9),
            ("Macro-F1",       9),
            ("Tổng ảnh",       9),
            ("FPS",            6),
            ("Device",         6),
        ]
        hdr_frame = tk.Frame(parent, bg=BG3)
        hdr_frame.pack(fill="x", padx=4, pady=(4, 0))
        for col, (text, width) in enumerate(HDR_COLS):
            lbl = tk.Label(hdr_frame, text=text,
                           font=("Segoe UI", 8, "bold"),
                           bg=BG3, fg=ACCENT2, width=width, anchor="center",
                           pady=5, cursor="hand2")
            lbl.grid(row=0, column=col, padx=1, sticky="nsew")
            lbl.bind("<Button-1>", lambda e, k=text: self._hist_sort_by(k))
        self._hist_hdr_cols = HDR_COLS

        # ── Scrollable table body ───────────────────────────────────────────
        table_wrapper = tk.Frame(parent, bg=HIST_BG)
        table_wrapper.pack(fill="both", expand=True, padx=4, pady=4)

        vsb = tk.Scrollbar(table_wrapper, orient="vertical", bg=HIST_BG3)
        vsb.pack(side="right", fill="y")
        hsb = tk.Scrollbar(table_wrapper, orient="horizontal", bg=HIST_BG3)
        hsb.pack(side="bottom", fill="x")

        self._hist_canvas_scroll = tk.Canvas(table_wrapper, bg=HIST_BG,
                                             highlightthickness=0,
                                             yscrollcommand=vsb.set,
                                             xscrollcommand=hsb.set)
        self._hist_canvas_scroll.pack(fill="both", expand=True)
        vsb.config(command=self._hist_canvas_scroll.yview)
        hsb.config(command=self._hist_canvas_scroll.xview)

        self._hist_table_inner = tk.Frame(self._hist_canvas_scroll, bg=HIST_BG)
        _win = self._hist_canvas_scroll.create_window(
            (0, 0), window=self._hist_table_inner, anchor="nw")

        def _on_frame_config(e):
            self._hist_canvas_scroll.configure(
                scrollregion=self._hist_canvas_scroll.bbox("all"))
        def _on_canvas_config(e):
            self._hist_canvas_scroll.itemconfig(_win, width=e.width)

        self._hist_table_inner.bind("<Configure>", _on_frame_config)
        self._hist_canvas_scroll.bind("<Configure>", _on_canvas_config)
        self._hist_canvas_scroll.bind("<MouseWheel>",
            lambda e: self._hist_canvas_scroll.yview_scroll(-1*(e.delta//120), "units"))

        # Tải ngay khi build xong
        self.after(200, self._hist_refresh)

    def _hist_refresh(self):
        """Quét tất cả file eval_*.json trong EVAL_BASE_DIR và RUNS_DIR (bao gồm sub-folder) và vẽ lại bảng."""
        import json
        self._hist_rows.clear()

        # Tổng hợp các thư mục cần quét
        _base_dirs = [EVAL_BASE_DIR, RUNS_DIR]
        search_dirs = []
        for _base in _base_dirs:
            if _base.exists():
                search_dirs.append(_base)
                for _d in _base.iterdir():
                    if _d.is_dir():
                        search_dirs.append(_d)

        all_files = []
        for d in search_dirs:
            if d.exists():
                all_files.extend(sorted(d.glob("eval_*.json")))

        # Deduplicate
        seen = set()
        for p in all_files:
            if p not in seen:
                seen.add(p)
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    data["_json_path"] = str(p)
                    self._hist_rows.append(data)
                except Exception:
                    pass

        # Sort
        key_map = {
            "Thời gian":  "timestamp",
            "Accuracy":   "accuracy",
            "Macro-F1":   "macro_f1",
            "Tổng ảnh":  "total_imgs",
            "FPS":        "fps",
        }
        sort_k = key_map.get(self._hist_sort_key, self._hist_sort_key)
        try:
            self._hist_rows.sort(
                key=lambda d: (d.get(sort_k) or 0),
                reverse=self._hist_sort_rev)
        except Exception:
            pass

        self._hist_draw_table()

        total = len(self._hist_rows)
        papers = {}
        for d in self._hist_rows:
            p = d.get("paper", "Unknown")
            papers[p] = papers.get(p, 0) + 1
        summary = f"Tổng: {total} phiên  |  " + "  ·  ".join(
            f"{p}: {n}" for p, n in papers.items())
        try:
            self._hist_summary_lbl.configure(text=summary)
        except Exception:
            pass

    def _hist_sort_by(self, col_text: str):
        if self._hist_sort_key == col_text:
            self._hist_sort_rev = not self._hist_sort_rev
        else:
            self._hist_sort_key = col_text
            self._hist_sort_rev = True
        self._hist_refresh()

    def _hist_draw_table(self):
        if self._hist_table_inner is None:
            return
        for w in self._hist_table_inner.winfo_children():
            w.destroy()
        self._hist_row_frames.clear()

        if not self._hist_rows:
            tk.Label(self._hist_table_inner,
                     text="Chưa có phiên đánh giá nào.\n"
                          "Chạy đánh giá ở tab JILSA 2022 hoặc PLOS ONE 2024 để tạo dữ liệu.",
                     font=("Segoe UI", 10), bg=BG, fg=TEXT_DIM,
                     justify="center").pack(pady=40)
            return

        HDR_COLS = self._hist_hdr_cols
        widths = [w for _, w in HDR_COLS]
        self._hist_selected = -1

        for idx, d in enumerate(self._hist_rows):
            is_jilsa = "JILSA" in d.get("paper", "")
            row_bg   = BG3 if idx % 2 == 0 else BG2
            accent_c = "#4ade80" if is_jilsa else "#60a5fa"

            row_frame = tk.Frame(self._hist_table_inner, bg=row_bg, cursor="hand2")
            row_frame.pack(fill="x", pady=1)
            self._hist_row_frames.append(row_frame)

            ts_raw = d.get("timestamp", "")
            try:
                import datetime as _dt
                ts_disp = _dt.datetime.fromisoformat(ts_raw).strftime("%d/%m/%Y %H:%M:%S")
            except Exception:
                ts_disp = ts_raw[:19]

            model_name = Path(d.get("model", "")).name
            acc  = d.get("accuracy")
            f1   = d.get("macro_f1")
            n    = d.get("total_imgs", "—")
            fps  = d.get("fps", "—")
            dev  = d.get("device", "—")

            acc_str = f"{acc*100:.2f}%" if acc is not None else "—"
            f1_str  = f"{f1*100:.2f}%"  if f1  is not None else "—"
            acc_fg  = SUCCESS if (acc or 0) >= 0.9 else (WARNING if (acc or 0) >= 0.7 else DANGER)
            f1_fg   = SUCCESS if (f1  or 0) >= 0.9 else (WARNING if (f1  or 0) >= 0.7 else DANGER)

            values = [
                (f"{idx+1}",                  TEXT_DIM, "center"),
                (ts_disp,                      TEXT,     "center"),
                (model_name[:22],              accent_c, "w"),
                (d.get("paper","")[:16],       TEXT_DIM, "center"),
                (acc_str,                      acc_fg,   "center"),
                (f1_str,                       f1_fg,    "center"),
                (str(n),                       TEXT,     "center"),
                (f"{fps:.1f}" if isinstance(fps, float) else str(fps), TEXT, "center"),
                (str(dev)[:6],                 TEXT_DIM, "center"),
            ]

            for col, ((val, fg, anc), w) in enumerate(zip(values, widths)):
                lbl = tk.Label(row_frame, text=val,
                               font=("Cascadia Code", 8),
                               bg=row_bg, fg=fg, width=w,
                               anchor=anc, pady=5, padx=4)
                lbl.grid(row=0, column=col, padx=1, sticky="nsew")
                lbl.bind("<Button-1>",
                         lambda e, i=idx: self._hist_on_row_click(i))
                lbl.bind("<Double-Button-1>",
                         lambda e, i=idx: self._hist_show_detail(i))
                lbl.bind("<Enter>",
                         lambda e, f=row_frame, c=row_bg: f.configure(bg=ACCENT3) or
                         [ch.configure(bg=ACCENT3) for ch in f.winfo_children()])
                lbl.bind("<Leave>",
                         lambda e, f=row_frame, c=row_bg, i=idx: (
                             f.configure(bg=(ACCENT if self._hist_selected == i else c)) or
                             [ch.configure(bg=(ACCENT if self._hist_selected == i else c))
                              for ch in f.winfo_children()]))

            row_frame.bind("<Double-Button-1>",
                           lambda e, i=idx: self._hist_show_detail(i))

    def _hist_on_row_click(self, idx: int):
        """Highlight row và hiện mini-preview ở bottom."""
        old = self._hist_selected
        self._hist_selected = idx
        # Deselect old
        if old >= 0 and old < len(self._hist_row_frames):
            bg = BG3 if old % 2 == 0 else BG2
            f  = self._hist_row_frames[old]
            try:
                f.configure(bg=bg)
                for ch in f.winfo_children():
                    ch.configure(bg=bg)
            except Exception:
                pass
        # Highlight new
        if idx < len(self._hist_row_frames):
            f = self._hist_row_frames[idx]
            try:
                f.configure(bg=ACCENT)
                for ch in f.winfo_children():
                    ch.configure(bg=ACCENT)
            except Exception:
                pass
        # Auto-open detail
        self._hist_show_detail(idx)

    def _hist_delete_selected(self):
        if self._hist_selected < 0 or self._hist_selected >= len(self._hist_rows):
            messagebox.showinfo("Chưa chọn", "Click vào 1 dòng để chọn trước khi xóa.")
            return
        d   = self._hist_rows[self._hist_selected]
        pth = d.get("_json_path", "")
        if not pth:
            return
        if not messagebox.askyesno("Xác nhận xóa",
                                   f"Xóa phiên đánh giá:\n{Path(pth).name}?"):
            return
        try:
            Path(pth).unlink(missing_ok=True)
            # Cũng xóa confusion matrix PNG cùng tên
            cm_png = Path(pth).parent / Path(pth).stem.replace("eval_", "confusion_matrix_") + ".png"
            cm_png2 = Path(str(pth).replace("eval_", "confusion_matrix_").replace(".json", ".png"))
            for f in [cm_png, cm_png2]:
                if f.exists():
                    f.unlink(missing_ok=True)
        except Exception as ex:
            messagebox.showerror("Lỗi", str(ex))
            return
        self._hist_refresh()

    def _hist_show_detail(self, idx: int):
        """Mở cửa sổ chi tiết phiên đánh giá."""
        if idx < 0 or idx >= len(self._hist_rows):
            return
        d = self._hist_rows[idx]

        # Đóng cửa sổ cũ nếu còn mở
        if self._hist_detail_win is not None:
            try:
                self._hist_detail_win.destroy()
            except Exception:
                pass

        win = tk.Toplevel(self)
        self._hist_detail_win = win
        is_jilsa = "JILSA" in d.get("paper", "")
        accent   = "#4ade80" if is_jilsa else "#60a5fa"

        win.title(f"Chi tiết đánh giá — {d.get('paper','')}")
        win.configure(bg=BG)
        win.geometry("1000x680")
        win.resizable(True, True)

        # ── Header ─────────────────────────────────────────────────────────
        hdr = tk.Frame(win, bg=accent, pady=6)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"📊 {d.get('paper','')}",
                 font=("Segoe UI", 12, "bold"), bg=accent, fg="white").pack(side="left", padx=12)

        ts_raw = d.get("timestamp", "")
        try:
            import datetime as _dt
            ts_disp = _dt.datetime.fromisoformat(ts_raw).strftime("%d/%m/%Y %H:%M:%S")
        except Exception:
            ts_disp = ts_raw

        tk.Label(hdr, text=ts_disp, font=("Segoe UI", 9), bg=accent, fg="white").pack(side="right", padx=12)

        # ── Main paned layout ───────────────────────────────────────────────
        paned = tk.PanedWindow(win, orient="horizontal", bg=BG, sashwidth=5)
        paned.pack(fill="both", expand=True, padx=6, pady=6)

        left_panel = tk.Frame(paned, bg=BG2, width=320)
        right_panel = tk.Frame(paned, bg=BG)
        paned.add(left_panel,  minsize=280)
        paned.add(right_panel, minsize=400)

        # ── LEFT: Thông số tổng quan ────────────────────────────────────────
        tk.Label(left_panel, text="⚙ Thông số phiên đánh giá",
                 font=("Segoe UI", 9, "bold"), bg=BG2, fg=accent).pack(anchor="w", padx=8, pady=(8, 4))

        acc  = d.get("accuracy")
        f1   = d.get("macro_f1")
        n    = d.get("total_imgs", "—")
        fps  = d.get("fps", "—")
        dev  = d.get("device", "—")
        t    = d.get("infer_sec", "—")
        params = d.get("params", None)

        info_rows = [
            ("Mô hình",        Path(d.get("model","")).name),
            ("Dataset",        Path(d.get("eval_dir","")).name),
            ("Img Size",       f"{d.get('img_size','—')} px"),
            ("Batch Size",     str(d.get("batch","—"))),
            ("Device",         str(dev)),
            ("Tổng ảnh",      str(n)),
            ("Thời gian inf.", f"{t:.2f}s" if isinstance(t, float) else str(t)),
            ("FPS",            f"{fps:.1f}" if isinstance(fps, float) else str(fps)),
            ("Parameters",     f"{params/1e6:.2f} M" if params else "—"),
            ("─────────",       "─────────────"),
            ("Accuracy",       f"{acc*100:.4f}%" if acc is not None else "—"),
            ("Macro-F1",       f"{f1*100:.4f}%"  if f1  is not None else "—"),
            ("Correct / Total",f"{d.get('correct','—')} / {n}"),
        ]
        for key, val in info_rows:
            fr = tk.Frame(left_panel, bg=BG2)
            fr.pack(fill="x", padx=8, pady=1)
            tk.Label(fr, text=key, font=("Segoe UI", 8), bg=BG2,
                     fg=TEXT_DIM, width=16, anchor="w").pack(side="left")
            is_acc_row = key in ("Accuracy", "Macro-F1")
            v_fg = (SUCCESS if (acc or 0) >= 0.9 else (WARNING if (acc or 0) >= 0.7 else DANGER)) if is_acc_row else TEXT
            tk.Label(fr, text=val, font=("Cascadia Code", 8), bg=BG2,
                     fg=v_fg, anchor="w").pack(side="left", padx=4)

        # Per-class table
        tk.Label(left_panel, text="📌 Chi tiết từng class",
                 font=("Segoe UI", 9, "bold"), bg=BG2, fg=accent).pack(anchor="w", padx=8, pady=(12, 4))

        cls_dict = d.get("classes", {})
        if cls_dict:
            hdr_f = tk.Frame(left_panel, bg=BG3)
            hdr_f.pack(fill="x", padx=8)
            for col_txt, w in [("Class", 18), ("Acc%", 7), ("OK/Total", 10)]:
                tk.Label(hdr_f, text=col_txt, font=("Segoe UI", 7, "bold"),
                         bg=BG3, fg=ACCENT2, width=w, anchor="center", pady=3).pack(side="left", padx=1)

            for ci, (cname, cinfo) in enumerate(cls_dict.items()):
                c_acc = cinfo.get("accuracy", 0.0)
                c_cor = cinfo.get("correct", "?")
                c_tot = cinfo.get("total", "?")
                c_fg  = SUCCESS if c_acc >= 0.9 else (WARNING if c_acc >= 0.7 else DANGER)
                row_bg = BG3 if ci % 2 == 0 else BG2
                fr = tk.Frame(left_panel, bg=row_bg)
                fr.pack(fill="x", padx=8, pady=1)
                for val, w in [(cname[:18], 18), (f"{c_acc*100:.1f}%", 7), (f"{c_cor}/{c_tot}", 10)]:
                    tk.Label(fr, text=val, font=("Cascadia Code", 7),
                             bg=row_bg, fg=c_fg if val == f"{c_acc*100:.1f}%" else TEXT,
                             width=w, anchor="center", pady=2).pack(side="left", padx=1)

        # Buttons
        btn_f = tk.Frame(left_panel, bg=BG2)
        btn_f.pack(fill="x", padx=8, pady=8)
        json_p = d.get("_json_path", "")
        tk.Button(btn_f, text="📂 Mở thư mục",
                  font=("Segoe UI", 8), bg=BG3, fg=TEXT, relief="flat", cursor="hand2",
                  command=lambda: self._open_folder(str(Path(json_p).parent)) if json_p else None
                  ).pack(side="left", padx=4)
        tk.Button(btn_f, text="📄 Xem JSON",
                  font=("Segoe UI", 8), bg=BG3, fg=TEXT, relief="flat", cursor="hand2",
                  command=lambda: self._hist_open_json(json_p)
                  ).pack(side="left", padx=4)

        # ── RIGHT: Tabs biểu đồ ────────────────────────────────────────────
        right_nb_style = ttk.Style(win)
        right_nb_style.configure("Detail.TNotebook", background=BG, borderwidth=0)
        right_nb_style.configure("Detail.TNotebook.Tab",
                                 background=BG3, foreground=TEXT_DIM,
                                 padding=[12, 5], font=("Segoe UI", 8, "bold"))
        right_nb_style.map("Detail.TNotebook.Tab",
                           background=[("selected", accent)],
                           foreground=[("selected", "white")])

        right_nb = ttk.Notebook(right_panel, style="Detail.TNotebook")
        right_nb.pack(fill="both", expand=True)

        # ── Chart tab: Confusion Matrix ──
        tab_cm = tk.Frame(right_nb, bg=BG)
        right_nb.add(tab_cm, text=" 🟦 Confusion Matrix ")
        cm_canvas = tk.Canvas(tab_cm, bg=BG, highlightthickness=0)
        cm_canvas.pack(fill="both", expand=True)

        # ── Chart tab: Per-class bars ──
        tab_bar = tk.Frame(right_nb, bg=BG)
        right_nb.add(tab_bar, text=" 📊 Per-class Chart ")
        bar_canvas = tk.Canvas(tab_bar, bg=BG, highlightthickness=0)
        bar_canvas.pack(fill="both", expand=True)

        # ── Chart tab: Pie ──
        tab_pie = tk.Frame(right_nb, bg=BG)
        right_nb.add(tab_pie, text=" 🥧 Phân bố Class ")
        pie_canvas = tk.Canvas(tab_pie, bg=BG, highlightthickness=0)
        pie_canvas.pack(fill="both", expand=True)

        # Lưu tham chiếu để render sau khi window đã có kích thước
        win._cm_canvas  = cm_canvas
        win._bar_canvas = bar_canvas
        win._pie_canvas = pie_canvas
        win._data       = d
        win._accent     = accent

        def _render_all():
            self._hist_render_cm(win._cm_canvas,  win._data, win._accent)
            self._hist_render_bar(win._bar_canvas, win._data, win._accent)
            self._hist_render_pie(win._pie_canvas, win._data, win._accent)

        win.after(300, _render_all)

    def _hist_render_cm(self, canvas: tk.Canvas, d: dict, accent: str):
        """Vẽ confusion matrix lên canvas."""
        cm_arr = d.get("confusion_matrix")
        cls_dict = d.get("classes", {})
        class_names = list(cls_dict.keys())

        # Thử load file PNG đã lưu trước
        json_p = d.get("_json_path", "")
        if json_p:
            ts = Path(json_p).stem.replace("eval_", "")
            cm_img_path = Path(json_p).parent / f"confusion_matrix_{ts}.png"
            if cm_img_path.exists():
                try:
                    from PIL import Image as _PIL, ImageTk as _ITK
                    cw = max(canvas.winfo_width(), 400)
                    ch = max(canvas.winfo_height(), 320)
                    img = _PIL.open(str(cm_img_path)).convert("RGB")
                    img = img.resize((cw, ch), _PIL.LANCZOS if hasattr(_PIL, "LANCZOS") else _PIL.ANTIALIAS)
                    tk_img = _ITK.PhotoImage(img)
                    canvas._tk_img = tk_img  # prevent GC
                    canvas.delete("all")
                    canvas.create_image(0, 0, anchor="nw", image=tk_img)
                    return
                except Exception:
                    pass

        if not cm_arr or not class_names:
            canvas.create_text(10, 40, text="Không có dữ liệu confusion matrix.",
                               fill=TEXT_DIM, font=("Segoe UI", 9), anchor="w")
            return

        try:
            import matplotlib; matplotlib.use("Agg")
            import matplotlib.pyplot as plt, numpy as np
            from PIL import Image as _PIL, ImageTk as _ITK
            import io

            cm = np.array(cm_arr)
            n  = len(class_names)
            cw = max(canvas.winfo_width(), 400)
            ch = max(canvas.winfo_height(), 320)

            fig, ax = plt.subplots(figsize=(cw/96, ch/96), dpi=96)
            fig.patch.set_facecolor("#1e1e2e"); ax.set_facecolor("#252538")
            im = ax.imshow(cm, interpolation="nearest", cmap="Blues")
            plt.colorbar(im, ax=ax)
            ax.set_xticks(range(n)); ax.set_yticks(range(n))
            ax.set_xticklabels(class_names, rotation=35, ha="right", fontsize=9, color="white")
            ax.set_yticklabels(class_names, fontsize=9, color="white")
            ax.tick_params(colors="white")
            thresh = cm.max() / 2.0
            for i in range(n):
                for j in range(n):
                    ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                            fontsize=11, fontweight="bold",
                            color="white" if cm[i, j] < thresh else "#1e1e2e")
            acc = d.get("accuracy"); f1 = d.get("macro_f1")
            title = f"Confusion Matrix — {d.get('paper','')}"
            if acc: title += f"\nAcc {acc*100:.2f}%"
            if f1:  title += f"  |  Macro-F1 {f1*100:.2f}%"
            ax.set_xlabel("Dự đoán", color="white", fontsize=10)
            ax.set_ylabel("Nhãn thật", color="white", fontsize=10)
            ax.set_title(title, color="white", fontsize=9, fontweight="bold")
            plt.tight_layout()

            buf = io.BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
            plt.close(fig); buf.seek(0)
            img = _PIL.open(buf).convert("RGB")
            img = img.resize((cw, ch), _PIL.LANCZOS if hasattr(_PIL, "LANCZOS") else _PIL.ANTIALIAS)
            tk_img = _ITK.PhotoImage(img)
            canvas._tk_img = tk_img
            canvas._pil_img = img
            canvas.delete("all")
            canvas.create_image(0, 0, anchor="nw", image=tk_img)
        except Exception as ex:
            canvas.create_text(10, 40, text=f"⚠ {ex}", fill=WARNING,
                               font=("Segoe UI", 8), anchor="w")

    def _hist_render_bar(self, canvas: tk.Canvas, d: dict, accent: str):
        """Vẽ grouped bar chart per-class Accuracy / F1."""
        cls_dict = d.get("classes", {})
        if not cls_dict:
            canvas.create_text(10, 40, text="Không có dữ liệu per-class.",
                               fill=TEXT_DIM, font=("Segoe UI", 9), anchor="w")
            return
        try:
            import matplotlib; matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from PIL import Image as _PIL, ImageTk as _ITK
            import io

            names    = list(cls_dict.keys())
            acc_vals = [cls_dict[c].get("accuracy", 0.0) * 100 for c in names]
            n        = len(names)
            cw = max(canvas.winfo_width(), 400)
            ch = max(canvas.winfo_height(), 280)

            fig, ax = plt.subplots(figsize=(cw/96, ch/96), dpi=96)
            fig.patch.set_facecolor("#1e1e2e"); ax.set_facecolor("#13131f")
            ax.tick_params(colors="#9090b0", labelsize=8)
            ax.spines[:].set_color("#333350")

            bars = ax.bar(range(n), acc_vals, color=accent, alpha=0.85, width=0.55)
            for xi, av in enumerate(acc_vals):
                ax.text(xi, av + 1.5, f"{av:.1f}%", ha="center", va="bottom",
                        fontsize=8, color="#e2e8f0")

            ax.axhline(y=90, color="#22c55e", linewidth=0.8, linestyle="--", alpha=0.6, label="90%")
            ax.axhline(y=70, color="#f59e0b", linewidth=0.8, linestyle="--", alpha=0.6, label="70%")

            ax.set_xticks(range(n))
            ax.set_xticklabels(names, rotation=30, ha="right", fontsize=8, color="#c0c0e0")
            ax.set_ylabel("Accuracy (%)", color="#9090b0", fontsize=8)
            ax.set_ylim(0, 115)
            acc_g = d.get("accuracy"); f1_g = d.get("macro_f1")
            title = "Per-class Accuracy"
            if acc_g: title += f"  |  Overall {acc_g*100:.2f}%"
            if f1_g:  title += f"  |  Macro-F1 {f1_g*100:.2f}%"
            ax.set_title(title, color="#c0c0e0", fontsize=9, pad=4)
            ax.legend(fontsize=7, facecolor="#1e1e2e", labelcolor="#c0c0e0",
                      framealpha=0.5, loc="lower right")
            plt.tight_layout(pad=1.0)

            buf = io.BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
            plt.close(fig); buf.seek(0)
            img = _PIL.open(buf).convert("RGB")
            img = img.resize((cw, ch), _PIL.LANCZOS if hasattr(_PIL, "LANCZOS") else _PIL.ANTIALIAS)
            tk_img = _ITK.PhotoImage(img)
            canvas._tk_img = tk_img
            canvas.delete("all")
            canvas.create_image(0, 0, anchor="nw", image=tk_img)
        except Exception as ex:
            canvas.create_text(10, 40, text=f"⚠ {ex}", fill=WARNING,
                               font=("Segoe UI", 8), anchor="w")

    def _hist_render_pie(self, canvas: tk.Canvas, d: dict, accent: str):
        """Vẽ pie chart phân bố số lượng ảnh mỗi class."""
        cls_dict = d.get("classes", {})
        if not cls_dict:
            canvas.create_text(10, 40, text="Không có dữ liệu.",
                               fill=TEXT_DIM, font=("Segoe UI", 9), anchor="w")
            return
        try:
            import matplotlib; matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from PIL import Image as _PIL, ImageTk as _ITK
            import io

            names  = list(cls_dict.keys())
            totals = [cls_dict[c].get("total", 0) for c in names]
            cw = max(canvas.winfo_width(), 400)
            ch = max(canvas.winfo_height(), 280)

            palette = ["#7c3aed", "#2563eb", "#059669", "#d97706",
                       "#dc2626", "#0891b2", "#7c3aed", "#be185d"]
            colors = [palette[i % len(palette)] for i in range(len(names))]

            fig, axes = plt.subplots(1, 2, figsize=(cw/96, ch/96), dpi=96)
            fig.patch.set_facecolor("#1e1e2e")

            # Left: Pie — số lượng ảnh
            ax1 = axes[0]; ax1.set_facecolor("#1e1e2e")
            wedges, texts, autotexts = ax1.pie(
                totals, labels=names, autopct="%1.1f%%",
                colors=colors, startangle=90,
                textprops={"color": "white", "fontsize": 8},
                pctdistance=0.8)
            for at in autotexts:
                at.set_fontsize(8); at.set_color("#e2e8f0")
            ax1.set_title("Phân bố số lượng ảnh", color="#c0c0e0", fontsize=9)

            # Right: Bar — correct vs total per class
            ax2 = axes[1]; ax2.set_facecolor("#13131f")
            ax2.tick_params(colors="#9090b0", labelsize=7)
            ax2.spines[:].set_color("#333350")
            x = range(len(names))
            corrects = [cls_dict[c].get("correct", 0) for c in names]
            ax2.bar(x, totals,    color="#334155", width=0.55, label="Tổng")
            ax2.bar(x, corrects,  color=accent,    width=0.55, alpha=0.9, label="Đúng")
            ax2.set_xticks(list(x))
            ax2.set_xticklabels(names, rotation=30, ha="right", fontsize=7, color="#c0c0e0")
            ax2.set_ylabel("Số ảnh", color="#9090b0", fontsize=7)
            ax2.set_title("Đúng vs Tổng", color="#c0c0e0", fontsize=9)
            ax2.legend(fontsize=7, facecolor="#1e1e2e", labelcolor="#c0c0e0", framealpha=0.5)

            plt.tight_layout(pad=1.0)
            buf = io.BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
            plt.close(fig); buf.seek(0)
            img = _PIL.open(buf).convert("RGB")
            img = img.resize((cw, ch), _PIL.LANCZOS if hasattr(_PIL, "LANCZOS") else _PIL.ANTIALIAS)
            tk_img = _ITK.PhotoImage(img)
            canvas._tk_img = tk_img
            canvas.delete("all")
            canvas.create_image(0, 0, anchor="nw", image=tk_img)
        except Exception as ex:
            canvas.create_text(10, 40, text=f"⚠ {ex}", fill=WARNING,
                               font=("Segoe UI", 8), anchor="w")

    def _hist_open_json(self, json_path: str):
        """Mở file JSON trong cửa sổ text đơn giản."""
        if not json_path or not Path(json_path).exists():
            messagebox.showerror("Lỗi", "File không tồn tại.")
            return
        win = tk.Toplevel(self)
        win.title(f"JSON — {Path(json_path).name}")
        win.configure(bg=BG)
        win.geometry("700x500")
        txt = tk.Text(win, bg=BG3, fg=TEXT, font=("Cascadia Code", 9),
                      wrap="none", relief="flat")
        vsb = tk.Scrollbar(win, command=txt.yview)
        hsb = tk.Scrollbar(win, orient="horizontal", command=txt.xview)
        txt.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        hsb.pack(side="bottom", fill="x")
        vsb.pack(side="right",  fill="y")
        txt.pack(fill="both", expand=True)
        try:
            content = Path(json_path).read_text(encoding="utf-8")
            txt.insert("1.0", content)
        except Exception as ex:
            txt.insert("1.0", f"Lỗi đọc file: {ex}")
        txt.configure(state="disabled")

    # ─────────────────────────────────────────────────────────────────────────
    # LỊCH SỬ SO SÁNH — Tab 7
    # ─────────────────────────────────────────────────────────────────────────
    def _build_cmp_history_tab(self, parent: tk.Frame):
        """Tab lịch sử các phiên so sánh model (cmp_report_*.json)."""

        # ── Toolbar ──────────────────────────────────────────────────────────
        toolbar = tk.Frame(parent, bg=BG3, pady=4)
        toolbar.pack(fill="x", padx=4, pady=(4, 0))

        tk.Label(toolbar, text="🔀 Lịch sử So sánh Model",
                 font=("Segoe UI", 11, "bold"), bg=BG3, fg=TEXT).pack(side="left", padx=10)

        tk.Button(toolbar, text="🔄 Làm mới", font=("Segoe UI", 8, "bold"),
                  bg=ACCENT, fg="white", relief="flat", padx=10, cursor="hand2",
                  command=self._cmphistory_refresh).pack(side="right", padx=4)
        tk.Button(toolbar, text="🗑 Xóa đã chọn", font=("Segoe UI", 8),
                  bg=DANGER, fg="white", relief="flat", padx=10, cursor="hand2",
                  command=self._cmphistory_delete_selected).pack(side="right", padx=4)
        tk.Button(toolbar, text="📂 Mở thư mục", font=("Segoe UI", 8),
                  bg=BG3, fg=TEXT, relief="flat", padx=10, cursor="hand2",
                  command=lambda: self._open_folder(str(EVAL_BASE_DIR / "compare"))
                  ).pack(side="right", padx=4)

        # ── Summary label ─────────────────────────────────────────────────────
        self._cmphistory_summary_lbl = tk.Label(parent, text="",
                                                font=("Segoe UI", 8), bg=BG, fg=TEXT_DIM)
        self._cmphistory_summary_lbl.pack(anchor="w", padx=10, pady=(4, 0))

        # ── Header ───────────────────────────────────────────────────────────
        HDR_COLS = [
            ("STT",         4),
            ("Thời gian",  17),
            ("Số model",    8),
            ("Model (tóm tắt)", 38),
            ("FPS TB",      8),
            ("GFLOPs TB",   9),
            ("Params TB",   9),
        ]
        self._cmphistory_hdr_cols = HDR_COLS

        hdr_frame = tk.Frame(parent, bg=BG3)
        hdr_frame.pack(fill="x", padx=4, pady=(4, 0))
        for col, (text, width) in enumerate(HDR_COLS):
            lbl = tk.Label(hdr_frame, text=text,
                           font=("Segoe UI", 8, "bold"),
                           bg=BG3, fg=ACCENT2, width=width, anchor="center",
                           pady=5, cursor="hand2")
            lbl.grid(row=0, column=col, padx=1, sticky="nsew")
            lbl.bind("<Button-1>", lambda e, k=text: self._cmphistory_sort_by(k))

        # ── Scrollable table body ─────────────────────────────────────────────
        table_wrapper = tk.Frame(parent, bg=BG)
        table_wrapper.pack(fill="both", expand=True, padx=4, pady=4)

        vsb = tk.Scrollbar(table_wrapper, orient="vertical",   bg=BG3)
        vsb.pack(side="right",  fill="y")
        hsb = tk.Scrollbar(table_wrapper, orient="horizontal", bg=BG3)
        hsb.pack(side="bottom", fill="x")

        self._cmphistory_canvas_scroll = tk.Canvas(table_wrapper, bg=BG,
                                                   highlightthickness=0,
                                                   yscrollcommand=vsb.set,
                                                   xscrollcommand=hsb.set)
        self._cmphistory_canvas_scroll.pack(fill="both", expand=True)
        vsb.config(command=self._cmphistory_canvas_scroll.yview)
        hsb.config(command=self._cmphistory_canvas_scroll.xview)

        self._cmphistory_table_inner = tk.Frame(self._cmphistory_canvas_scroll, bg=BG)
        _win = self._cmphistory_canvas_scroll.create_window(
            (0, 0), window=self._cmphistory_table_inner, anchor="nw")

        def _on_frame_config(e):
            self._cmphistory_canvas_scroll.configure(
                scrollregion=self._cmphistory_canvas_scroll.bbox("all"))
        def _on_canvas_config(e):
            self._cmphistory_canvas_scroll.itemconfig(_win, width=e.width)

        self._cmphistory_table_inner.bind("<Configure>", _on_frame_config)
        self._cmphistory_canvas_scroll.bind("<Configure>", _on_canvas_config)
        self._cmphistory_canvas_scroll.bind(
            "<MouseWheel>",
            lambda e: self._cmphistory_canvas_scroll.yview_scroll(-1*(e.delta//120), "units"))

        self.after(250, self._cmphistory_refresh)

    def _cmphistory_refresh(self):
        """Quét cmp_report_*.json trong EVAL_BASE_DIR/compare và RUNS_DIR."""
        import json
        self._cmphistory_rows.clear()

        search_dirs = []
        for base in [EVAL_BASE_DIR / "compare", RUNS_DIR]:
            if base.exists():
                search_dirs.append(base)
                for d in base.iterdir():
                    if d.is_dir():
                        search_dirs.append(d)

        seen = set()
        for d in search_dirs:
            for p in sorted(d.glob("cmp_report_*.json")):
                if p not in seen:
                    seen.add(p)
                    try:
                        data = json.loads(p.read_text(encoding="utf-8"))
                        data["_json_path"] = str(p)
                        self._cmphistory_rows.append(data)
                    except Exception:
                        pass

        # Sort
        key_map = {
            "Thời gian": "timestamp",
            "Số model":  "_n_models",
            "FPS TB":    "_fps_avg",
            "GFLOPs TB": "_gflops_avg",
        }
        # Pre-compute derived fields
        for row in self._cmphistory_rows:
            models_list = [v for k, v in row.items()
                           if k.startswith("model_") and isinstance(v, dict)]
            row["_n_models"] = len(models_list)
            fps_vals    = []
            for m in models_list:
                f = m.get("avg_fps")
                if f in (None, "—"):
                    continue
                try:
                    fps_vals.append(float(str(f)))
                except (ValueError, TypeError):
                    pass
            gflop_vals  = []
            for m in models_list:
                g = m.get("gflops")
                if g in (None, "—"):
                    continue
                try:
                    gflop_vals.append(float(str(g)))
                except (ValueError, TypeError):
                    pass
            row["_fps_avg"]   = sum(fps_vals)   / len(fps_vals)   if fps_vals   else 0
            row["_gflops_avg"]= sum(gflop_vals) / len(gflop_vals) if gflop_vals else 0
            row["_models_list"] = models_list

        sort_k = key_map.get(self._cmphistory_sort_key, self._cmphistory_sort_key)
        try:
            self._cmphistory_rows.sort(
                key=lambda r: (r.get(sort_k) or 0),
                reverse=self._cmphistory_sort_rev)
        except Exception:
            pass

        self._cmphistory_draw_table()

        total = len(self._cmphistory_rows)
        try:
            self._cmphistory_summary_lbl.configure(
                text=f"Tổng: {total} phiên so sánh")
        except Exception:
            pass

    def _cmphistory_sort_by(self, col_text: str):
        if self._cmphistory_sort_key == col_text:
            self._cmphistory_sort_rev = not self._cmphistory_sort_rev
        else:
            self._cmphistory_sort_key = col_text
            self._cmphistory_sort_rev = True
        self._cmphistory_refresh()

    def _cmphistory_draw_table(self):
        if self._cmphistory_table_inner is None:
            return
        for w in self._cmphistory_table_inner.winfo_children():
            w.destroy()
        self._cmphistory_row_frames.clear()

        if not self._cmphistory_rows:
            tk.Label(self._cmphistory_table_inner,
                     text="Chưa có phiên so sánh nào.\n"
                          "Nhấn '💾 Lưu báo cáo' trong tab So sánh Model để tạo dữ liệu.",
                     font=("Segoe UI", 10), bg=BG, fg=TEXT_DIM,
                     justify="center").pack(pady=40)
            return

        HDR_COLS = self._cmphistory_hdr_cols
        widths = [w for _, w in HDR_COLS]
        self._cmphistory_selected = -1

        for idx, row in enumerate(self._cmphistory_rows):
            row_bg = BG3 if idx % 2 == 0 else BG2

            ts_raw = row.get("timestamp", "")
            try:
                import datetime as _dt
                ts_disp = _dt.datetime.strptime(ts_raw, "%Y%m%d_%H%M%S").strftime("%d/%m/%Y %H:%M:%S")
            except Exception:
                ts_disp = ts_raw

            models_list = row.get("_models_list", [])
            n_models    = row.get("_n_models", 0)
            fps_avg     = row.get("_fps_avg", 0)
            gflops_avg  = row.get("_gflops_avg", 0)

            # Tóm tắt tên các model
            names = [m.get("model_name", "?") for m in models_list]
            summary = "  ·  ".join(n[:16] for n in names[:4])
            if n_models > 4:
                summary += f"  (+{n_models-4})"

            fps_str    = f"{fps_avg:.1f}" if fps_avg else "—"
            gflops_str = f"{gflops_avg:.2f}" if gflops_avg else "—"

            # Tính params trung bình
            p_vals = []
            for m in models_list:
                try:
                    p_vals.append(float(m.get("params_m") or 0))
                except Exception:
                    pass
            params_str = f"{sum(p_vals)/len(p_vals):.2f} M" if p_vals else "—"

            values = [
                (f"{idx+1}",   TEXT_DIM, "center"),
                (ts_disp,      TEXT,     "center"),
                (str(n_models),ACCENT2,  "center"),
                (summary,      TEXT,     "w"),
                (fps_str,      SUCCESS if fps_avg > 20 else WARNING, "center"),
                (gflops_str,   INFO,     "center"),
                (params_str,   TEXT_DIM, "center"),
            ]

            row_frame = tk.Frame(self._cmphistory_table_inner, bg=row_bg, cursor="hand2")
            row_frame.pack(fill="x", pady=1)
            self._cmphistory_row_frames.append(row_frame)

            for col, ((val, fg, anc), w) in enumerate(zip(values, widths)):
                lbl = tk.Label(row_frame, text=val,
                               font=("Cascadia Code", 8),
                               bg=row_bg, fg=fg, width=w,
                               anchor=anc, pady=5, padx=4)
                lbl.grid(row=0, column=col, padx=1, sticky="nsew")
                lbl.bind("<Button-1>",
                         lambda e, i=idx: self._cmphistory_on_row_click(i))
                lbl.bind("<Double-Button-1>",
                         lambda e, i=idx: self._cmphistory_show_detail(i))
                lbl.bind("<Enter>",
                         lambda e, f=row_frame, c=row_bg: [
                             f.configure(bg=ACCENT3)] +
                             [ch.configure(bg=ACCENT3) for ch in f.winfo_children()])
                lbl.bind("<Leave>",
                         lambda e, f=row_frame, c=row_bg, i=idx: [
                             f.configure(bg=ACCENT if self._cmphistory_selected == i else c)] +
                             [ch.configure(bg=ACCENT if self._cmphistory_selected == i else c)
                              for ch in f.winfo_children()])

    def _cmphistory_on_row_click(self, idx: int):
        old = self._cmphistory_selected
        self._cmphistory_selected = idx
        if old >= 0 and old < len(self._cmphistory_row_frames):
            bg = BG3 if old % 2 == 0 else BG2
            f  = self._cmphistory_row_frames[old]
            try:
                f.configure(bg=bg)
                for ch in f.winfo_children(): ch.configure(bg=bg)
            except Exception: pass
        if idx < len(self._cmphistory_row_frames):
            f = self._cmphistory_row_frames[idx]
            try:
                f.configure(bg=ACCENT)
                for ch in f.winfo_children(): ch.configure(bg=ACCENT)
            except Exception: pass
        self._cmphistory_show_detail(idx)

    def _cmphistory_delete_selected(self):
        if self._cmphistory_selected < 0 or self._cmphistory_selected >= len(self._cmphistory_rows):
            messagebox.showinfo("Chưa chọn", "Click vào 1 dòng để chọn trước khi xóa.")
            return
        row  = self._cmphistory_rows[self._cmphistory_selected]
        pth  = row.get("_json_path", "")
        if not pth:
            return
        if not messagebox.askyesno("Xác nhận xóa", f"Xóa phiên so sánh:\n{Path(pth).name}?"):
            return
        try:
            Path(pth).unlink(missing_ok=True)
            csv_p = Path(str(pth).replace("cmp_report_", "cmp_report_").replace(".json", "")) \
                    .parent / (Path(pth).stem + ".csv")  # same stem, .csv
            if csv_p.exists():
                csv_p.unlink(missing_ok=True)
        except Exception as ex:
            messagebox.showerror("Lỗi", str(ex)); return
        self._cmphistory_refresh()

    def _cmphistory_show_detail(self, idx: int):
        """Cửa sổ chi tiết 1 phiên so sánh với bảng + biểu đồ grouped bar."""
        if idx < 0 or idx >= len(self._cmphistory_rows):
            return
        row = self._cmphistory_rows[idx]
        models_list = row.get("_models_list", [])
        if not models_list:
            messagebox.showinfo("Không có dữ liệu", "Phiên này không có dữ liệu model.")
            return

        if self._cmphistory_detail_win is not None:
            try: self._cmphistory_detail_win.destroy()
            except Exception: pass

        win = tk.Toplevel(self)
        self._cmphistory_detail_win = win
        win.title(f"Chi tiết so sánh — {row.get('timestamp','')}")
        win.configure(bg=BG)
        win.geometry("1020x680")
        win.resizable(True, True)

        # ── Header ───────────────────────────────────────────────────────────
        hdr = tk.Frame(win, bg=ACCENT, pady=6)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"🔀 So sánh {len(models_list)} model",
                 font=("Segoe UI", 12, "bold"), bg=ACCENT, fg="white").pack(side="left", padx=12)

        ts_raw = row.get("timestamp", "")
        try:
            import datetime as _dt
            ts_disp = _dt.datetime.strptime(ts_raw, "%Y%m%d_%H%M%S").strftime("%d/%m/%Y %H:%M:%S")
        except Exception:
            ts_disp = ts_raw
        tk.Label(hdr, text=ts_disp, font=("Segoe UI", 9), bg=ACCENT, fg="white").pack(side="right", padx=12)

        # ── Paned layout ──────────────────────────────────────────────────────
        paned = tk.PanedWindow(win, orient="horizontal", bg=BG, sashwidth=5)
        paned.pack(fill="both", expand=True, padx=6, pady=6)

        left_panel  = tk.Frame(paned, bg=BG2, width=340)
        right_panel = tk.Frame(paned, bg=BG)
        paned.add(left_panel,  minsize=300)
        paned.add(right_panel, minsize=420)

        # ── LEFT: bảng metrics từng model ────────────────────────────────────
        tk.Label(left_panel, text="📋 Thông số từng model",
                 font=("Segoe UI", 9, "bold"), bg=BG2, fg=ACCENT2).pack(anchor="w", padx=8, pady=(8,4))

        METRIC_KEYS = [
            ("Tên file",     "model_name",  False),
            ("Params (M)",   "params_m",    False),
            ("GFLOPs",       "gflops",      False),
            ("Size (MB)",    "size_mb",     False),
            ("FPS TB",       "avg_fps",     True),
            ("Inf (ms)",     "avg_ms",      False),
            ("Tổng frames",  "total_frames",False),
            ("Tổng obj",     "total_dets",  False),
            ("Top-1",        "val_top1",    False),
        ]
        slot_colors = self._cmp_slot_colors

        # Header row
        hdr_f = tk.Frame(left_panel, bg=BG3)
        hdr_f.pack(fill="x", padx=8, pady=(0,2))
        tk.Label(hdr_f, text="Thông số", font=("Segoe UI", 7, "bold"),
                 bg=BG3, fg=ACCENT2, width=14, anchor="w", pady=3).pack(side="left", padx=1)
        for i, m in enumerate(models_list):
            c = slot_colors[i % len(slot_colors)]
            nm = Path(m.get("model_name", f"M{i+1}")).stem[:10]
            tk.Label(hdr_f, text=nm, font=("Segoe UI", 7, "bold"),
                     bg=c, fg="white", width=9, anchor="center", pady=3
                     ).pack(side="left", padx=1)

        # Data rows
        for ri, (label, key, highlight) in enumerate(METRIC_KEYS):
            row_bg = BG3 if ri % 2 == 0 else BG2
            fr = tk.Frame(left_panel, bg=row_bg)
            fr.pack(fill="x", padx=8, pady=1)
            tk.Label(fr, text=label, font=("Segoe UI", 7), bg=row_bg,
                     fg=TEXT_DIM, width=14, anchor="w", pady=3).pack(side="left", padx=1)
            for i, m in enumerate(models_list):
                val = m.get(key, "—")
                if val is None: val = "—"
                if highlight and val != "—":
                    try:
                        _v = float(str(val))
                        fg = SUCCESS if _v >= 20 else WARNING
                    except Exception:
                        fg = TEXT
                else:
                    fg = TEXT
                tk.Label(fr, text=str(val)[:10], font=("Cascadia Code", 7),
                         bg=row_bg, fg=fg, width=9, anchor="center", pady=2
                         ).pack(side="left", padx=1)

        # Open JSON button
        json_p = row.get("_json_path", "")
        btn_f = tk.Frame(left_panel, bg=BG2)
        btn_f.pack(fill="x", padx=8, pady=8)
        tk.Button(btn_f, text="📂 Mở thư mục",
                  font=("Segoe UI", 8), bg=BG3, fg=TEXT, relief="flat", cursor="hand2",
                  command=lambda: self._open_folder(str(Path(json_p).parent)) if json_p else None
                  ).pack(side="left", padx=4)
        tk.Button(btn_f, text="📄 Xem JSON",
                  font=("Segoe UI", 8), bg=BG3, fg=TEXT, relief="flat", cursor="hand2",
                  command=lambda: self._hist_open_json(json_p)
                  ).pack(side="left", padx=4)

        # ── RIGHT: Grouped bar charts ─────────────────────────────────────────
        s = ttk.Style(win)
        s.configure("CmpDet.TNotebook", background=BG, borderwidth=0)
        s.configure("CmpDet.TNotebook.Tab",
                    background=BG3, foreground=TEXT_DIM,
                    padding=[10, 4], font=("Segoe UI", 8, "bold"))
        s.map("CmpDet.TNotebook.Tab",
              background=[("selected", ACCENT)],
              foreground=[("selected", "white")])

        right_nb = ttk.Notebook(right_panel, style="CmpDet.TNotebook")
        right_nb.pack(fill="both", expand=True)

        chart_defs = [
            ("  📊 FPS / Inf  ",    ["avg_fps", "avg_ms"],   ["FPS trung bình", "Inference (ms)"]),
            ("  🧮 Size / Params ", ["size_mb",  "params_m"], ["Size (MB)",      "Params (M)"]),
            ("  ⚡ GFLOPs       ",  ["gflops"],               ["GFLOPs"]),
        ]
        for tab_txt, keys, labels in chart_defs:
            tab_f  = tk.Frame(right_nb, bg=BG)
            right_nb.add(tab_f, text=tab_txt)
            c = tk.Canvas(tab_f, bg=BG, highlightthickness=0)
            c.pack(fill="both", expand=True)
            c._keys   = keys
            c._labels = labels

        def _render_charts():
            for ti in range(right_nb.index("end")):
                tab_frame = right_nb.nametowidget(right_nb.tabs()[ti])
                cv = tab_frame.winfo_children()[0] if tab_frame.winfo_children() else None
                if cv is None: continue
                self._cmphistory_render_bars(cv, models_list, cv._keys, cv._labels)

        win.after(300, _render_charts)

    def _cmphistory_render_bars(self, canvas: tk.Canvas, models_list: list,
                                keys: list, labels: list):
        """Vẽ grouped bar chart so sánh nhiều model theo các metrics."""
        try:
            import matplotlib; matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import numpy as np
            from PIL import Image as _PIL, ImageTk as _ITK
            import io

            cw = max(canvas.winfo_width(), 400)
            ch = max(canvas.winfo_height(), 300)
            n_keys   = len(keys)
            n_models = len(models_list)
            names    = [Path(m.get("model_name", f"M{i+1}")).stem[:14]
                        for i, m in enumerate(models_list)]
            palette  = self._cmp_slot_colors

            fig, axes = plt.subplots(1, n_keys, figsize=(cw/96, ch/96), dpi=96,
                                     squeeze=False)
            fig.patch.set_facecolor("#1e1e2e")

            for ki, (key, label) in enumerate(zip(keys, labels)):
                ax = axes[0][ki]
                ax.set_facecolor("#13131f")
                ax.tick_params(colors="#9090b0", labelsize=7)
                ax.spines[:].set_color("#333350")

                vals = []
                for m in models_list:
                    try:
                        vals.append(float(str(m.get(key, 0) or 0)))
                    except Exception:
                        vals.append(0.0)

                x = np.arange(n_models)
                colors = [palette[i % len(palette)] for i in range(n_models)]
                bars = ax.bar(x, vals, color=colors, width=0.55, alpha=0.85)
                for bi, v in enumerate(vals):
                    ax.text(bi, v + max(vals) * 0.02,
                            f"{v:.1f}" if v >= 10 else f"{v:.2f}",
                            ha="center", va="bottom", fontsize=7, color="#e2e8f0")
                ax.set_xticks(x)
                ax.set_xticklabels(names, rotation=30, ha="right", fontsize=7, color="#c0c0e0")
                ax.set_title(label, color="#c0c0e0", fontsize=8, pad=4)
                ax.set_ylabel(label, color="#9090b0", fontsize=7)

            plt.tight_layout(pad=1.2)
            buf = io.BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
            plt.close(fig); buf.seek(0)
            img = _PIL.open(buf).convert("RGB")
            img = img.resize((cw, ch), _PIL.LANCZOS if hasattr(_PIL, "LANCZOS") else _PIL.ANTIALIAS)
            tk_img = _ITK.PhotoImage(img)
            canvas._tk_img = tk_img
            canvas.delete("all")
            canvas.create_image(0, 0, anchor="nw", image=tk_img)
        except Exception as ex:
            canvas.create_text(10, 40, text=f"⚠ {ex}", fill=WARNING,
                               font=("Segoe UI", 8), anchor="w")


# ─────────────────────────────────────────────────────────────────────────────
    def _eval_thread(self, model_path: str, data_path: str):
        import io
        import sys
        import tempfile
        import traceback as _tb
        import subprocess as _sp

        task_map = {
            "Detection": "detect",
            "Instance Segmentation": "segment",
            "Classification": "classify",
        }
        task_label = self._eval_task_var.get()
        task = task_map.get(task_label, "detect")
        device = self._eval_device_var.get()
        imgsz = self._eval_imgsz_var.get()
        split = self._eval_split_var.get()
        conf = self._eval_conf_var.get()
        iou = self._eval_iou_var.get()
        half = self._eval_half_var.get()
        limit = max(0, int(self._eval_limit_var.get() or 0))
        limit_mode = self._eval_limit_mode_var.get()
        class_filters = self._eval_parse_class_filters()
        display_data_path = data_path

        self._eval_log(f"[→] Model   : {model_path}", "info")
        self._eval_log(f"[→] Dataset : {data_path}", "info")
        self._eval_log(
            f"[→] Task={task}  split={split}  imgsz={imgsz}"
            f"  conf={conf}  iou={iou}  device={device}",
            "info",
        )
        if task == "classify":
            self._eval_log(
                f"[→] Limit={limit or 'không'}  mode={limit_mode}"
                f"  class_filter={', '.join(class_filters) if class_filters else 'tất cả'}",
                "info",
            )

        cls_tmp_dir = None
        if task == "classify" and Path(data_path).is_dir():
            data_path, cls_tmp_dir, prep_info = self._eval_prepare_classification_dataset(data_path, split)
            if prep_info.get("mode") == "linked-flat":
                self._eval_log(
                    "[info] Flat class folder → tạo train/val/test tạm bằng junction/symlink.",
                    "info",
                )
            elif prep_info.get("mode") == "subset":
                self._eval_log(
                    f"[info] Classification subset: {prep_info.get('selected_images', 0)}/"
                    f"{prep_info.get('total_images', 0)} ảnh  |  classes={', '.join(prep_info.get('classes', []))}",
                    "info",
                )
            if prep_info.get("per_class_total"):
                for cls_name, total_imgs in sorted(prep_info["per_class_total"].items()):
                    self._eval_log(f"     - {cls_name}: {total_imgs} ảnh nguồn", "dim")

        temp_yaml_path = None
        if task in ("detect", "segment") and Path(data_path).is_dir():
            self._eval_log("[info] Phát hiện thư mục ảnh cho detect/segment.", "info")
            self._eval_log("[info] Đang tạo YAML tạm...", "info")
            _ensure_packages("ultralytics")
            YOLO_pre = _import_yolo()
            try:
                tmp_model = YOLO_pre(model_path, task=task)
                nc = len(tmp_model.names)
                names = list(tmp_model.names.values())
            except Exception:
                nc = 80
                names = [f"class{i}" for i in range(nc)]
            abs_data = str(Path(data_path).resolve()).replace("\\", "/")
            yaml_content = (
                f"path: {abs_data}\ntrain: .\nval: .\ntest: .\n"
                f"nc: {nc}\nnames: {names}\n"
            )
            temp_yaml_path = Path(tempfile.gettempdir()) / "_yolo_eval_temp.yaml"
            temp_yaml_path.write_text(yaml_content, encoding="utf-8")
            self._eval_log(f"[info] YAML tạm: {temp_yaml_path}", "info")
            self._eval_log("[warn] Đảm bảo thư mục có file .txt nhãn cho mỗi ảnh!", "warn")
            data_path = str(temp_yaml_path)

        try:
            _ensure_packages("ultralytics")
            YOLO = _import_yolo()
            model = YOLO(model_path, task=task)
            self._eval_log(f"[✔] Model: {Path(model_path).name}", "ok")
            cls_analysis = None

            buf = io.StringIO()
            old_out = sys.stdout
            sys.stdout = buf
            try:
                metrics = model.val(
                    data=data_path,
                    imgsz=imgsz,
                    device=device,
                    split=split,
                    conf=conf,
                    iou=iou,
                    half=half,
                    verbose=True,
                )
            finally:
                sys.stdout = old_out
                if temp_yaml_path and temp_yaml_path.exists():
                    try:
                        temp_yaml_path.unlink()
                    except Exception:
                        pass

            for line in buf.getvalue().splitlines()[-40:]:
                self._eval_log(line)

            if task == "classify":
                cls_analysis = self._eval_collect_classification_metrics(
                    model=model,
                    prepared_data_path=data_path,
                    split=split,
                    imgsz=imgsz,
                    device=device,
                    half=half,
                )
                self._eval_log_classification_metrics(cls_analysis)

            self._eval_results = self._eval_parse_metrics(
                metrics, task_label, model_path, display_data_path, split, extra=cls_analysis
            )
            self.after(0, self._eval_show_results, self._eval_results)
            if cls_analysis and cls_analysis.get("confusion_matrix"):
                self.after(
                    200,
                    self._eval_draw_confusion_matrix,
                    cls_analysis.get("class_names", []),
                    cls_analysis.get("confusion_matrix", []),
                    f"Confusion Matrix - {Path(model_path).name}",
                )
            else:
                run_dir = self._eval_find_run_dir(model_path)
                if run_dir:
                    self.after(200, self._eval_plot_loss, run_dir)
            self._eval_set_status("✔ Đánh giá xong!", SUCCESS)

            if self._bench_canvas is not None:
                result = self._eval_results
                map50 = result.get("mAP50") or result.get("mAP@50") or None
                map50_95 = result.get("mAP50-95") or result.get("mAP@50-95") or None
                accuracy = result.get("Top-1 Accuracy") or result.get("Top-1 Acc") or result.get("Accuracy") or None

                def _f(value):
                    if value is None:
                        return None
                    import re as _re

                    try:
                        match = _re.search(r"[\d.]+", str(value))
                        return float(match.group()) if match else None
                    except Exception:
                        return None

                map50 = _f(map50)
                map50_95 = _f(map50_95)
                accuracy = _f(accuracy)
                params_m, gflops = self._get_model_stats(model, imgsz)
                if accuracy is not None:
                    acc_str = f"{accuracy * 100:.2f}%" if accuracy <= 1.0 else f"{accuracy:.2f}%"
                elif map50 is not None:
                    acc_str = f"mAP50={map50:.4f}"
                else:
                    acc_str = "—"
                bench_info = {
                    "architecture": f"YOLOv8 ({task_label})",
                    "classes": len(model.names) if hasattr(model, "names") else "—",
                    "input_size": f"{imgsz}×{imgsz}",
                    "params_m": params_m,
                    "gflops": gflops,
                    "optimizer": "AdamW / SGD (YOLO default)",
                    "loss_fn": "BCE + DFL / CrossEntropyLoss",
                    "accuracy": (accuracy * 100 if accuracy and accuracy <= 1.0 else accuracy),
                    "accuracy_str": acc_str,
                    "map50": map50,
                    "map50_95": f"{map50_95:.4f}" if map50_95 is not None else None,
                    "test_images": "—",
                    "augmentation": "Mosaic, Flip, HSV (YOLO default)",
                }
                self.after(500, self._draw_benchmark_comparison, bench_info)

        except Exception:
            err = _tb.format_exc()
            self._eval_log(f"[✗] Lỗi:\n{err}", "err")
            self._eval_set_status("✗ Lỗi khi đánh giá", DANGER)
        finally:
            if cls_tmp_dir is not None:
                try:
                    import shutil as _shu

                    for split_name in ("train", "val", "test"):
                        link_dir = cls_tmp_dir / split_name
                        if link_dir.exists():
                            _sp.run(["cmd", "/c", "rd", str(link_dir)], capture_output=True)
                    _shu.rmtree(cls_tmp_dir, ignore_errors=True)
                except Exception:
                    pass
            self._eval_running = False
            self.after(0, self._restore_eval_primary_button)

if __name__ == "__main__":
    app = TesterApp()
    app.mainloop()

