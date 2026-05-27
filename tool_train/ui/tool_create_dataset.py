"""
=============================================================================
ðŸ® YOLOv8 CATTLE DETECTION + BATCH DATASET CREATOR
- Realtime: Camera / Video / Single Image
- Batch: Chá»n nhiá»u áº£nh hoáº·c folder â†’ tá»± Ä‘á»™ng táº¡o dataset chuáº©n YOLO
  (images + labels + images_with_boxes)
- Tùy chỉnh: Confidence, IOU, Device
=============================================================================
"""

import os
import sys
from pathlib import Path

# Tự động tìm TCL/TK theo Python đang chạy (không hardcode version)
_tcl_base = Path(sys.base_prefix) / "tcl"
_tcl_dir  = next((_tcl_base / d for d in ["tcl8.6", "tcl9.0"] if (_tcl_base / d).exists()), None)
_tk_dir   = next((_tcl_base / d for d in ["tk8.6",  "tk9.0"]  if (_tcl_base / d).exists()), None)
if _tcl_dir:
    os.environ.setdefault("TCL_LIBRARY", str(_tcl_dir))
if _tk_dir:
    os.environ.setdefault("TK_LIBRARY", str(_tk_dir))

import customtkinter as ctk
import cv2
from PIL import Image, ImageTk
from ultralytics import YOLO
import threading
import numpy as np
from tkinter import filedialog, messagebox
import time
import torch
import random
import shutil
from ui_theme import ACCENT, ACCENT2, BG, BG2, BG3, BG4, BORDER, DANGER, SIDEBAR, SUCCESS, TEXT, TEXT_DARK, TEXT_DIM, WARNING, patch_customtkinter_text, patch_tk_text
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from sklearn.metrics import roc_curve, auc, accuracy_score
    HAS_METRICS = True
except ImportError:
    HAS_METRICS = False

# Cấu hình màu sắc hiển thị (BGR)
COLOR_MAP = {
    0: (0, 255, 0),
    1: (203, 192, 255),
    2: (255, 255, 0),
    3: (42, 42, 165),
}
DEFAULT_COLOR = (0, 200, 255)


class CattleApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        patch_tk_text()
        patch_customtkinter_text(ctk)
        self.title("Cattle YOLOv8 - Detector & Dataset Creator")
        self.geometry("1500x900")
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=BG)

        # Biến chính
        self.model = None
        self.model_path = ctk.StringVar(value="models/Train_Cattle/runs/detect/train/weights/best.pt")
        self.is_running = False
        self._cap = None
        self._detect_thread = None
        self.input_mode = ctk.StringVar(value="camera")
        self.source_path = ctk.StringVar(value="")
        self.camera_index = ctk.StringVar(value="0") # String cho an toan hon IntVar

        # Tham số detection
        self.conf_threshold = ctk.DoubleVar(value=0.50)
        self.iou_threshold = ctk.DoubleVar(value=0.45)
        self.use_tta = ctk.BooleanVar(value=False)
        self.imgsz = ctk.IntVar(value=640)
        self.device = ctk.StringVar(value="0" if torch.cuda.is_available() else "cpu")
        self.max_det = ctk.IntVar(value=300)
        self.show_conf = ctk.BooleanVar(value=True)
        self.show_boxes = ctk.BooleanVar(value=True)

        # Biáº¿n Ä‘iá»u hÆ°á»›ng
        self.active_page = ctk.StringVar(value="test") # "test" hoặc "dataset"

        # Biáº¿n class filtering (Äá»‚ Lá»ŒC Lá»šP BÃ’ Náº°M, Äá»¨NG, Ä‚N...)
        self.all_classes = {} # {id: name}
        self.selected_classes = {} # {id: BooleanVar} cho viá»‡c tick chá»n
        self.class_name_vars = {} # {id: StringVar} cho việc đổi tên class
        self.filter_enabled = ctk.BooleanVar(value=False)

        # Biến cho trang Test (Mới)
        self.test_input_files: list[str] = []
        self.test_label_folder = ctk.StringVar(value="")
        self.test_is_perf_running = False
        self.latest_metrics = {} # Lưu trữ kết quả ACC, ROC, AUC
        
        # Biến batch processing (Cho trang Dataset Creator)
        self.batch_input_files: list[str] = []
        self.batch_input_videos: list[str] = []
        self.batch_output_folder = ctk.StringVar(value="")
        self.export_format = ctk.StringVar(value="roboflow") # "roboflow", "simple", "class_folders"
        self.filter_in_dataset = ctk.BooleanVar(value=True) # Chá»‰ xuáº¥t cÃ¡c class Ä‘Æ°á»£c chá»n

        # Biến xử lý video
        self.frame_interval = ctk.IntVar(value=10)   # Trích frame mỗi N frame
        self.video_split_mode = ctk.StringVar(value="primary")  # "primary" = class conf cao nhất, "all" = tất cả class
        self.save_video_no_detect = ctk.BooleanVar(value=False)  # Lưu frame không detect vào folder "no_detect"
        
        # Biáº¿n Ä‘iá»u khiá»ƒn tiáº¿n trÃ¬nh
        self.batch_is_paused = False
        self.batch_is_stopped = False

        self.setup_ui()

    # ------------------------------------------------------------------ UI --

    def setup_ui(self):
        # Cấu hình grid chính
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # â”€â”€ SIDEBAR â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0, fg_color=SIDEBAR, border_width=1, border_color=BORDER)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(10, weight=1) # Spacer

        logo_label = ctk.CTkLabel(self.sidebar, text="Cattle Tool", font=("Segoe UI", 24, "bold"), text_color=ACCENT)
        logo_label.pack(pady=(20, 20))

        # Nút chuyển trang
        self.btn_test_page = ctk.CTkButton(
            self.sidebar, text="Test Model", height=40, font=("Roboto", 14),
            fg_color=ACCENT, hover_color=ACCENT2, text_color="white", command=lambda: self.show_page("test")
        )
        self.btn_test_page.pack(fill="x", padx=20, pady=5)

        self.btn_dataset_page = ctk.CTkButton(
            self.sidebar, text="Dataset Creator", height=40, font=("Roboto", 14),
            fg_color=BG3, hover_color=BG4, text_color=TEXT, command=lambda: self.show_page("dataset")
        )
        self.btn_dataset_page.pack(fill="x", padx=20, pady=5)

        # Lá»c Class Section (Sidebar luÃ´n hiá»‡n Ä‘á»ƒ dá»… quáº£n lÃ½)
        self.add_sidebar_section("QUAN LY CLASS")
        
        # NÃºt thÃªm class tay
        ctk.CTkButton(self.sidebar, text="Them Class Tay", height=34, fg_color=ACCENT, hover_color=ACCENT2, text_color="white",
                       command=self.add_manual_class).pack(fill="x", padx=20, pady=5)

        self.filter_toggle = ctk.CTkCheckBox(self.sidebar, text="Bật lọc (khi Test)", variable=self.filter_enabled)
        self.filter_toggle.pack(anchor="w", padx=30, pady=5)
        
        # Scrollable area cho class list
        self.class_scroll = ctk.CTkScrollableFrame(self.sidebar, height=350, fg_color=BG2, border_width=1, border_color=BORDER)
        self.class_scroll.pack(fill="both", padx=10, pady=5)
        self.class_label = ctk.CTkLabel(self.class_scroll, text="Chưa có class...", text_color="grey")
        self.class_label.pack(pady=10)

        # â”€â”€ MAIN CONTENT â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self.main_container = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")
        self.main_container.grid(row=0, column=1, padx=15, pady=15, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        # --- TRANG 1: TEST MODEL ---
        self.test_page = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.test_page.grid(row=0, column=0, sticky="nsew")
        self.setup_test_page()

        # --- TRANG 2: DATASET CREATOR ---
        self.dataset_page = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.setup_dataset_page()

        self.show_page("test")

    def add_sidebar_section(self, text: str):
        ctk.CTkLabel(self.sidebar, text=text, font=("Segoe UI", 14, "bold"), text_color=ACCENT).pack(anchor="w", padx=20, pady=(20, 5))

    def show_page(self, page_name: str):
        self.active_page.set(page_name)
        if page_name == "test":
            self.dataset_page.grid_forget()
            self.test_page.grid(row=0, column=0, sticky="nsew")
            self.btn_test_page.configure(fg_color=ACCENT, hover_color=ACCENT2, text_color="white")
            self.btn_dataset_page.configure(fg_color=BG3, hover_color=BG4, text_color=TEXT)
        else:
            self.test_page.grid_forget()
            self.dataset_page.grid(row=0, column=0, sticky="nsew")
            self.btn_test_page.configure(fg_color=BG3, hover_color=BG4, text_color=TEXT)
            self.btn_dataset_page.configure(fg_color=ACCENT, hover_color=ACCENT2, text_color="white")

    def setup_test_page(self):
        self.test_page.grid_columnconfigure(0, weight=3)
        self.test_page.grid_columnconfigure(1, weight=1)
        self.test_page.grid_rowconfigure(0, weight=1)

        disp_frame = ctk.CTkFrame(self.test_page, fg_color=BG3, corner_radius=18, border_width=1, border_color=BORDER)
        disp_frame.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="nsew")
        self.display_frame = disp_frame 
        
        self.video_label = ctk.CTkLabel(disp_frame, text="Chon input va START de test model", text_color=TEXT_DIM, font=("Segoe UI", 14, "bold"))
        self.video_label.pack(expand=True)

        ctrl = ctk.CTkScrollableFrame(self.test_page, fg_color=BG2, corner_radius=18, border_width=1, border_color=BORDER)
        ctrl.grid(row=0, column=1, padx=0, pady=0, sticky="nsew")

        self.add_section_title(ctrl, "MODEL")
        m_frame = ctk.CTkFrame(ctrl)
        m_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkEntry(m_frame, textvariable=self.model_path).pack(side="left", expand=True, fill="x")
        ctk.CTkButton(m_frame, text="...", width=40, command=self.browse_model).pack(side="left", padx=5)
        ctk.CTkButton(ctrl, text="Load Model", fg_color=ACCENT, hover_color=ACCENT2, text_color="white", command=self.load_model).pack(fill="x", padx=10, pady=5)
        self.model_status = ctk.CTkLabel(ctrl, text="Chưa load", text_color="orange")
        self.model_status.pack(anchor="w", padx=10)

        # --- SOURCE (TEST) ---
        self.add_section_title(ctrl, "SOURCE (TEST)")
        
        # 1. Chon che do
        mode_frame = ctk.CTkFrame(ctrl)
        mode_frame.pack(fill="x", padx=10, pady=5)
        for mode, label in [("camera", "Camera"), ("video", "Video"), ("folder", "Folder/Images")]:
            ctk.CTkRadioButton(mode_frame, text=label, variable=self.input_mode, value=mode, command=self.update_test_ui_visibility).pack(side="left", padx=5)

        # Container cho cac phan thay doi de giu thu tu
        self.test_source_container = ctk.CTkFrame(ctrl, fg_color="transparent")
        self.test_source_container.pack(fill="x", pady=0)

        # 2. SOURCE BAR (Entry + Browse + Load)
        self.test_source_bar = ctk.CTkFrame(self.test_source_container, fg_color="transparent")
        # Pack se duoc goi trong update_test_ui_visibility ben trong container nay
        
        self.test_path_entry = ctk.CTkEntry(self.test_source_bar, textvariable=self.source_path, placeholder_text="Duong dan...")
        self.test_path_entry.pack(side="left", expand=True, fill="x", padx=(10, 5))
        self.test_browse_btn = ctk.CTkButton(self.test_source_bar, text="...", width=40, command=self.smart_browse_test_dynamic)
        self.test_browse_btn.pack(side="left", padx=5)
        
        self.load_input_btn = ctk.CTkButton(self.test_source_bar, text="LOAD DATA", width=80, fg_color="#3b82f6", command=self.action_load_data)
        self.load_input_btn.pack(side="left", padx=(0, 10))

        # 3. Extra controls inside container
        self.test_cam_frame = ctk.CTkFrame(self.test_source_container, fg_color="transparent")
        ctk.CTkLabel(self.test_cam_frame, text="Cam Index:").pack(side="left", padx=(10, 5))
        ctk.CTkEntry(self.test_cam_frame, textvariable=self.camera_index, width=50).pack(side="left")

        self.test_drop_container = ctk.CTkFrame(self.test_source_container, fg_color="transparent")
        self.test_drop_frame = ctk.CTkFrame(self.test_drop_container, height=100, border_color="#10B981", border_width=2, fg_color="#111827")
        self.test_drop_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(self.test_drop_frame, text="KEO THA ANH VAO DAY", font=("Roboto", 11, "bold"), fg_color="transparent").pack(pady=(10, 5))
        
        f_btn_frame = ctk.CTkFrame(self.test_drop_frame, fg_color="transparent")
        f_btn_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(f_btn_frame, text="Files", command=self.browse_test_files, height=30, width=80).pack(side="left", expand=True, padx=2)
        ctk.CTkButton(f_btn_frame, text="Folder", command=self.browse_test_folder, height=30, width=80).pack(side="left", expand=True, padx=2)

        self.test_count_label = ctk.CTkLabel(self.test_drop_container, text="0 anh da chon", text_color="#10B981")
        self.test_count_label.pack(anchor="w", padx=10)

        # Labels folder
        self.add_section_title(ctrl, "GROUND TRUTH (LABELS)")
        ctk.CTkButton(ctrl, text="Chon Thu Muc Labels (.txt)", command=self.browse_test_labels).pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(ctrl, textvariable=self.test_label_folder, text_color="grey", font=("Roboto", 10), wraplength=200).pack(padx=10)

        # Params
        self.add_section_title(ctrl, "PARAMS")
        ctk.CTkLabel(ctrl, text="Confidence").pack(anchor="w", padx=10)
        ctk.CTkSlider(ctrl, from_=0.05, to=0.99, variable=self.conf_threshold, command=self.update_labels).pack(fill="x", padx=10)
        self.conf_label = ctk.CTkLabel(ctrl, text="0.50")
        self.conf_label.pack(anchor="w", padx=10)

        ctk.CTkLabel(ctrl, text="IOU Threshold").pack(anchor="w", padx=10)
        ctk.CTkSlider(ctrl, from_=0.05, to=0.99, variable=self.iou_threshold, command=self.update_labels).pack(fill="x", padx=10)
        self.iou_label = ctk.CTkLabel(ctrl, text="0.45")
        self.iou_label.pack(anchor="w", padx=10)

        ctk.CTkCheckBox(ctrl, text="Bat TTA (augment)", variable=self.use_tta).pack(anchor="w", padx=10, pady=(8, 2))
        imgsz_row = ctk.CTkFrame(ctrl, fg_color="transparent")
        imgsz_row.pack(fill="x", padx=10, pady=(0, 5))
        ctk.CTkLabel(imgsz_row, text="imgsz:").pack(side="left")
        ctk.CTkEntry(imgsz_row, textvariable=self.imgsz, width=80).pack(side="left", padx=5)

        ctk.CTkCheckBox(ctrl, text="Hien Boxes", variable=self.show_boxes).pack(anchor="w", padx=10, pady=5)
        self.stats_label = ctk.CTkLabel(ctrl, text="Detections: 0")
        self.stats_label.pack(pady=5)

        # Core Controls
        self.add_section_title(ctrl, "CONTROLS")
        self.start_btn = ctk.CTkButton(ctrl, text="CHAY REALTIME (CAM/VIDEO)", fg_color="#059669", command=self.start_detection)
        self.start_btn.pack(fill="x", padx=10, pady=5)
        self.stop_btn = ctk.CTkButton(ctrl, text="STOP", fg_color="#DC2626", command=self.stop_detection, state="disabled")
        self.stop_btn.pack(fill="x", padx=10, pady=5)

        # Performance Metrics Section
        self.add_section_title(ctrl, "PERFORMANCE & METRICS")
        self.perf_progress = ctk.CTkProgressBar(ctrl)
        self.perf_progress.pack(fill="x", padx=10, pady=5)
        self.perf_progress.set(0)
        self.perf_status = ctk.CTkLabel(ctrl, text="Chua test", text_color="grey", font=("Roboto", 12, "bold"))
        self.perf_status.pack(pady=2)

        if HAS_METRICS:
            ctk.CTkButton(ctrl, text="CHAY DANH GIA MODEL", fg_color="#D97706", command=self.run_performance_test).pack(fill="x", padx=10, pady=5)
            ctk.CTkButton(ctrl, text="XEM BIEU DO (ROC/AUC/ACC)", fg_color="#3b82f6", command=self.show_metrics_charts).pack(fill="x", padx=10, pady=5)
        else:
            ctk.CTkLabel(ctrl, text="âš  Cai scikit-learn de dung tinh nang nay", text_color="orange", font=("Roboto", 11)).pack(padx=10, pady=5)
        
        self.update_test_ui_visibility()

    def setup_dataset_page(self):
        self.dataset_page.grid_columnconfigure(0, weight=1)
        self.dataset_page.grid_rowconfigure(0, weight=1)

        container = ctk.CTkScrollableFrame(self.dataset_page, fg_color=BG2, corner_radius=18, border_width=1, border_color=BORDER)
        container.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")

        # --- MODEL ---
        self.add_section_title(container, "MODEL & PARAMS")
        m_frame = ctk.CTkFrame(container)
        m_frame.pack(fill="x", padx=15, pady=5)
        
        top_m = ctk.CTkFrame(m_frame, fg_color="transparent")
        top_m.pack(fill="x", padx=10, pady=5)
        ctk.CTkEntry(top_m, textvariable=self.model_path, placeholder_text="Chon model .pt").pack(side="left", expand=True, fill="x")
        ctk.CTkButton(top_m, text="...", width=40, command=self.browse_model).pack(side="left", padx=5)
        
        bot_m = ctk.CTkFrame(m_frame, fg_color="transparent")
        bot_m.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(bot_m, text="Load Model", fg_color=ACCENT, hover_color=ACCENT2, text_color="white", command=self.load_model).pack(side="left", expand=True, padx=(0, 10))
        self.model_status_ds = ctk.CTkLabel(bot_m, text="Chua load", text_color="orange")
        self.model_status_ds.pack(side="left")

        ctk.CTkLabel(container, text="Confidence:").pack(anchor="w", padx=20, pady=(10, 0))
        ctk.CTkSlider(container, from_=0.05, to=0.99, variable=self.conf_threshold, command=self.update_labels).pack(fill="x", padx=20)
        self.conf_label_ds = ctk.CTkLabel(container, text="0.50")
        self.conf_label_ds.pack(anchor="w", padx=20)

        ctk.CTkLabel(container, text="IOU Threshold:").pack(anchor="w", padx=20, pady=(10, 0))
        ctk.CTkSlider(container, from_=0.05, to=0.99, variable=self.iou_threshold, command=self.update_labels).pack(fill="x", padx=20)
        self.iou_label_ds = ctk.CTkLabel(container, text="0.45")
        self.iou_label_ds.pack(anchor="w", padx=20)

        ctk.CTkCheckBox(container, text="Bat TTA (augment)", variable=self.use_tta).pack(anchor="w", padx=20, pady=(10, 2))
        imgsz_row_ds = ctk.CTkFrame(container, fg_color="transparent")
        imgsz_row_ds.pack(fill="x", padx=20, pady=(0, 6))
        ctk.CTkLabel(imgsz_row_ds, text="imgsz:").pack(side="left")
        ctk.CTkEntry(imgsz_row_ds, textvariable=self.imgsz, width=100).pack(side="left", padx=6)

        # --- SOURCE ---
        self.add_section_title(container, "CHON DU LIEU DAU VAO")
        
        # O text hien thi source
        self.dataset_source_entry = ctk.CTkEntry(container, placeholder_text="Chua chon du lieu")
        self.dataset_source_entry.pack(fill="x", padx=15, pady=(0, 5))

        self.drop_frame = ctk.CTkFrame(container, height=180, border_color="#10B981", border_width=2, fg_color="#111827")
        self.drop_frame.pack(fill="x", padx=15, pady=5)
        self.drop_frame.pack_propagate(False)
        
        ctk.CTkLabel(self.drop_frame, text="KEO THA ANH/FOLDER VAO DAY", font=("Roboto", 18, "bold"), fg_color="transparent").pack(pady=(30, 10))
        
        btn_row = ctk.CTkFrame(self.drop_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=40, pady=10)
        ctk.CTkButton(btn_row, text="Chon nhieu File", height=45, command=self.browse_batch_files).pack(side="left", expand=True, padx=10)
        ctk.CTkButton(btn_row, text="Chon Folder", height=45, command=self.browse_batch_folder).pack(side="left", expand=True, padx=10)

        self.batch_count_label = ctk.CTkLabel(container, text="0 anh da chon", text_color="#10B981")
        self.batch_count_label.pack(anchor="w", padx=15)

        # --- VIDEO INPUT ---
        self.add_section_title(container, "VIDEO DAU VAO (TACH FRAME THEO CLASS)")

        self.video_source_entry = ctk.CTkEntry(container, placeholder_text="Chua chon video")
        self.video_source_entry.pack(fill="x", padx=15, pady=(0, 5))

        vid_btn_row = ctk.CTkFrame(container, fg_color="transparent")
        vid_btn_row.pack(fill="x", padx=15, pady=5)
        ctk.CTkButton(vid_btn_row, text="Chon Video(s)", height=40, fg_color="#7C3AED",
                      command=self.browse_batch_videos).pack(side="left", expand=True, padx=(0, 5))
        ctk.CTkButton(vid_btn_row, text="Chon Folder Video", height=40, fg_color="#5B21B6",
                      command=self.browse_batch_video_folder).pack(side="left", expand=True, padx=(5, 0))
        ctk.CTkButton(vid_btn_row, text="Xoa DS Video", height=40, width=110, fg_color="#374151",
                      command=self.clear_batch_videos).pack(side="left", padx=(5, 0))

        self.video_count_label = ctk.CTkLabel(container, text="0 video da chon", text_color="#A78BFA")
        self.video_count_label.pack(anchor="w", padx=15)

        # Frame sampling controls
        vid_opt_frame = ctk.CTkFrame(container, fg_color="#111827", corner_radius=8)
        vid_opt_frame.pack(fill="x", padx=15, pady=8)

        fi_row = ctk.CTkFrame(vid_opt_frame, fg_color="transparent")
        fi_row.pack(fill="x", padx=10, pady=(8, 4))
        ctk.CTkLabel(fi_row, text="Trich frame moi N frame:", font=("Roboto", 12)).pack(side="left", padx=(0, 10))
        self.frame_interval_entry = ctk.CTkEntry(fi_row, textvariable=self.frame_interval, width=60)
        self.frame_interval_entry.pack(side="left")
        ctk.CTkLabel(fi_row, text="(1 = moi frame, 10 = cu 10 frame lay 1)", text_color="grey",
                     font=("Roboto", 11)).pack(side="left", padx=10)

        split_row = ctk.CTkFrame(vid_opt_frame, fg_color="transparent")
        split_row.pack(fill="x", padx=10, pady=4)
        ctk.CTkLabel(split_row, text="Che do chia class:", font=("Roboto", 12)).pack(side="left", padx=(0, 10))
        ctk.CTkRadioButton(split_row, text="Class chinh (conf cao nhat)",
                           variable=self.video_split_mode, value="primary").pack(side="left", padx=5)
        ctk.CTkRadioButton(split_row, text="Tat ca class phat hien",
                           variable=self.video_split_mode, value="all").pack(side="left", padx=5)

        ctk.CTkCheckBox(vid_opt_frame, text="Luu frame khong detect vao folder 'no_detect'",
                        variable=self.save_video_no_detect).pack(anchor="w", padx=10, pady=(4, 8))

        # Video progress
        self.video_progress_bar = ctk.CTkProgressBar(container)
        self.video_progress_bar.pack(fill="x", padx=15, pady=(5, 0))
        self.video_progress_bar.set(0)
        self.video_progress_label = ctk.CTkLabel(container, text="Video: chua xu ly", text_color="grey",
                                                  font=("Roboto", 11))
        self.video_progress_label.pack(anchor="w", padx=15)

        # --- DESTINATION ---
        self.add_section_title(container, "DICH DEN")
        ctk.CTkButton(container, text="Chon Thu Muc Luu Dataset", command=self.browse_batch_output).pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(container, textvariable=self.batch_output_folder, text_color="grey", wraplength=600).pack(padx=15)

        # --- EXPORT ---
        self.add_section_title(container, "TUY CHON XUAT")
        o_frame = ctk.CTkFrame(container)
        o_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(o_frame, text="Format:").pack(side="left", padx=10)
        ctk.CTkRadioButton(o_frame, text="Roboflow", variable=self.export_format, value="roboflow").pack(side="left", padx=10)
        ctk.CTkRadioButton(o_frame, text="YOLO", variable=self.export_format, value="simple").pack(side="left", padx=10)
        ctk.CTkRadioButton(o_frame, text="Loc theo Class", variable=self.export_format, value="class_folders").pack(side="left", padx=10)
        self.ds_filter_cb = ctk.CTkCheckBox(container, text="Chi xuat cac class duoc chon o Sidebar", variable=self.filter_in_dataset)
        self.ds_filter_cb.pack(anchor="w", padx=15)

        # --- PROGRESS ---
        self.add_section_title(container, "TIEN TRINH")
        self.batch_progress_bar = ctk.CTkProgressBar(container)
        self.batch_progress_bar.pack(fill="x", padx=15, pady=5)
        self.batch_status = ctk.CTkLabel(container, text="San sang", text_color="grey")
        self.batch_status.pack(anchor="w", padx=15)

        b_frame = ctk.CTkFrame(container, fg_color="transparent")
        b_frame.pack(fill="x", padx=10, pady=10)
        self.batch_start_btn = ctk.CTkButton(b_frame, text="BAT DAU", height=45, fg_color=ACCENT, hover_color=ACCENT2, text_color="white", command=self.start_batch_creation)
        self.batch_start_btn.pack(side="left", expand=True, padx=5)
        self.batch_pause_btn = ctk.CTkButton(b_frame, text="TAM DỪNG", height=45, fg_color=WARNING, hover_color="#d7ae38", text_color=TEXT_DARK, state="disabled", command=self.pause_batch_creation)
        self.batch_pause_btn.pack(side="left", expand=True, padx=5)
        self.batch_stop_btn = ctk.CTkButton(b_frame, text="DUNG HAN", height=45, fg_color=DANGER, hover_color="#f16a6a", text_color=TEXT_DARK, state="disabled", command=self.stop_batch_creation)
        self.batch_stop_btn.pack(side="left", expand=True, padx=5)

    def add_section_title(self, parent, text: str):
        ctk.CTkLabel(parent, text=text, font=("Segoe UI", 14, "bold"), text_color=ACCENT).pack(anchor="w", padx=10, pady=(15, 5))

    def update_labels(self, *_):
        c = f"{self.conf_threshold.get():.2f}"
        i = f"{self.iou_threshold.get():.2f}"
        self.conf_label.configure(text=c)
        if hasattr(self, 'iou_label'): self.iou_label.configure(text=i)
        if hasattr(self, 'conf_label_ds'): self.conf_label_ds.configure(text=c)
        if hasattr(self, 'iou_label_ds'): self.iou_label_ds.configure(text=i)

    def _safe_imgsz(self) -> int:
        try:
            value = int(self.imgsz.get())
            return value if value >= 32 else 640
        except Exception:
            return 640

    def _predict_with_current_settings(self, source, conf_override=None):
        return self.model.predict(
            source=source,
            conf=self.conf_threshold.get() if conf_override is None else conf_override,
            iou=self.iou_threshold.get(),
            max_det=self.max_det.get(),
            device=self.device.get(),
            imgsz=self._safe_imgsz(),
            augment=self.use_tta.get(),
            verbose=False
        )[0]

    # ---------------------------------------------------------- Model Handling
    def browse_model(self):
        path = filedialog.askopenfilename(filetypes=[("YOLO Model", "*.pt")])
        if path: self.model_path.set(path)

    def load_model(self):
        try:
            for lbl in [self.model_status, getattr(self, 'model_status_ds', None)]:
                if lbl: lbl.configure(text="⏳ Đang load...", text_color="orange")
            self.update()
            self.model = YOLO(self.model_path.get())
            self.all_classes = self.model.names
            self.update_class_list_ui()
            res = f"âœ… {os.path.basename(self.model_path.get())}"
            for lbl in [self.model_status, getattr(self, 'model_status_ds', None)]:
                if lbl: lbl.configure(text=res, text_color="#10B981")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Load model thất bại:\n{e}")

    def add_manual_class(self):
        nxt = max(self.class_name_vars.keys()) + 1 if self.class_name_vars else 0
        self._create_class_row(nxt, f"new_class_{nxt}")

    def update_class_list_ui(self):
        for w in self.class_scroll.winfo_children(): w.destroy()
        self.selected_classes, self.class_name_vars = {}, {}
        if not self.all_classes:
            ctk.CTkLabel(self.class_scroll, text="Chưa có class", text_color="grey").pack(pady=10)
            return
        for idx, name in self.all_classes.items(): self._create_class_row(idx, name)

    def update_test_ui_visibility(self):
        m = self.input_mode.get()
        # Hide all first
        self.test_source_bar.pack_forget()
        self.test_cam_frame.pack_forget()
        self.test_drop_container.pack_forget()
        
        if m == "folder":
            self.test_source_bar.pack(fill="x", pady=5)
            self.test_path_entry.configure(placeholder_text="Duong dan Folder/Multiple images")
            self.test_drop_container.pack(fill="x", pady=5)
            self.start_btn.configure(state="disabled")
        elif m == "video":
            self.test_source_bar.pack(fill="x", pady=5)
            self.test_path_entry.configure(placeholder_text="Chon video (.mp4, .avi, ...)")
            self.start_btn.configure(state="normal")
        else: # camera
            self.test_cam_frame.pack(fill="x", pady=10)
            self.start_btn.configure(state="normal")

    def action_load_data(self):
        m = self.input_mode.get()
        path = self.test_path_entry.get().strip()
        if not path and m != "camera":
            messagebox.showwarning("Loi", "Vui long chon hoac nhap duong dan truoc."); return

        if m == "video":
            if os.path.exists(path):
                self.source_path.set(path)
                messagebox.showinfo("Load", f"Video '{os.path.basename(path)}' da san sang.")
            else: messagebox.showerror("Loi", "File video khong ton tai.")
        elif m == "folder":
            if os.path.isdir(path):
                exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
                files = [os.path.join(path, f) for f in os.listdir(path) if os.path.splitext(f)[1].lower() in exts]
                if files:
                    self.test_input_files = files
                    self.test_count_label.configure(text=f"Da nap {len(files)} anh tu folder")
                    messagebox.showinfo("Load", f"Da nap {len(files)} anh thanh cong.")
                else: messagebox.showwarning("Load", "Folder khong co file anh hop le.")
            elif os.path.isfile(path):
                self.test_input_files = [path]
                self.test_count_label.configure(text="Da nap 1 file anh")
                messagebox.showinfo("Load", "Da nap file anh thanh cong.")
            else:
                # Neu test_input_files dang co (chon tu nut Files), thi thong bao
                if self.test_input_files:
                    messagebox.showinfo("Load", f"Dang co {len(self.test_input_files)} anh san sang.")
                else: messagebox.showerror("Loi", "Duong dan khong hop le.")

    def smart_browse_test_dynamic(self):
        m = self.input_mode.get()
        if m == "video": self.browse_source()
        elif m == "folder": 
            # Hoi xem muon chon file hay folder
            self.browse_test_folder()

    def _create_class_row(self, idx, name):
        row = ctk.CTkFrame(self.class_scroll, fg_color="transparent")
        row.pack(fill="x", pady=2)
        v_sel = ctk.BooleanVar(value=True); self.selected_classes[idx] = v_sel
        ctk.CTkCheckBox(row, text="", variable=v_sel, width=24).pack(side="left")
        ctk.CTkLabel(row, text=f"{idx}:", width=30, font=("Roboto", 11, "bold")).pack(side="left")
        v_name = ctk.StringVar(value=name); self.class_name_vars[idx] = v_name
        ctk.CTkEntry(row, textvariable=v_name, height=24).pack(side="left", expand=True, fill="x", padx=5)

    # ------------------------------------------------- Test Page Actions ---

    def browse_test_files(self):
        fs = filedialog.askopenfilenames(filetypes=[("Image Files", "*.jpg *.jpeg *.png *.bmp *.webp")])
        if fs: 
            self.test_input_files = list(fs)
            self.test_count_label.configure(text=f"Da chon {len(fs)} anh")
            self.test_path_entry.delete(0, "end")
            self.test_path_entry.insert(0, f"Selected {len(fs)} files...")

    def browse_test_folder(self):
        fd = filedialog.askdirectory()
        if fd:
            exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
            self.test_input_files = [os.path.join(fd, f) for f in os.listdir(fd) if os.path.splitext(f)[1].lower() in exts]
            self.test_count_label.configure(text=f"Da chon {len(self.test_input_files)} anh tu folder")
            self.test_path_entry.delete(0, "end")
            self.test_path_entry.insert(0, fd)

    def browse_test_labels(self):
        fd = filedialog.askdirectory(title="Chon thu muc chua file .txt (Labels)")
        if fd:
            self.test_label_folder.set(fd)
            # Count txt files for feedback
            cnt = len([f for f in os.listdir(fd) if f.lower().endswith(".txt")])
            messagebox.showinfo("Thong bao", f"Da chon thu muc: {os.path.basename(fd)}\nTim thay {cnt} file nhan (.txt)")

    def run_performance_test(self):
        if not HAS_METRICS:
            messagebox.showerror("Loi", "Thieu thu vien scikit-learn. Hay chay:\npip install scikit-learn"); return
        if not self.model: messagebox.showerror("Loi", "Chua load model!"); return
        if not self.test_input_files: messagebox.showerror("Loi", "Chua chon du lieu test (Anh/Folder)!"); return
        if not self.test_label_folder.get(): messagebox.showerror("Loi", "Chua chon thu muc Labels (.txt)!"); return

        self.test_is_perf_running = True
        self.perf_status.configure(text="Dang quet...", text_color="orange")
        self.perf_progress.set(0)

        def _perf_worker():
            y_true, y_scores = [], []
            correct_count = 0
            total = len(self.test_input_files)
            
            label_dir = self.test_label_folder.get()
            
            for idx, img_path in enumerate(self.test_input_files):
                img = cv2.imread(img_path)
                if img is None: continue
                
                results = self._predict_with_current_settings(source=img, conf_override=0.01)
                
                # Ground truth check
                img_name = os.path.basename(img_path)
                stem = os.path.splitext(img_name)[0]
                lbl_path = os.path.join(label_dir, stem + ".txt")
                
                if os.path.exists(lbl_path):
                    with open(lbl_path, "r") as f: gt_lines = [l.strip() for l in f.readlines() if l.strip()]
                    y_true.append(1 if len(gt_lines) > 0 else 0)
                else:
                    # Neu khong co file .txt -> Mac dinh la Background (0 object)
                    y_true.append(0)

                # Prediction score (max confidence found)
                max_conf = 0
                if len(results.boxes) > 0:
                    max_conf = float(results.boxes.conf.max())
                
                y_scores.append(max_conf)
                pred_bin = 1 if max_conf >= self.conf_threshold.get() else 0
                if pred_bin == y_true[-1]: correct_count += 1

                self.perf_progress.set((idx + 1) / total)
                self.perf_status.configure(text=f"Đang quét: {idx+1}/{total}")

            # Tính toán kết quả
            if len(y_true) > 0:
                acc = correct_count / len(y_true)
                try:
                    # roc_curve yêu cầu y_true có cả 2 class (0 và 1)
                    if len(set(y_true)) < 2:
                        raise ValueError("y_true chi co 1 class, khong tinh duoc ROC")
                    fpr, tpr, _ = roc_curve(y_true, y_scores)
                    roc_auc = auc(fpr, tpr)
                except ValueError as ve:
                    fpr, tpr = [0, 1], [0, 1]
                    roc_auc = 0.0
                    self.perf_status.configure(
                        text=f"ACC: {acc:.2f} | ROC N/A ({ve})", text_color="orange")

                self.latest_metrics = {
                    "acc": acc,
                    "roc_auc": roc_auc,
                    "fpr": fpr,
                    "tpr": tpr,
                    "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "total": len(y_true)
                }
                self.perf_status.configure(text=f"DONE | ACC: {acc:.2f} | AUC: {roc_auc:.2f}", text_color="#10B981")
                messagebox.showinfo("Hoan thanh", f"Da hoan thanh danh gia {len(y_true)} anh.\nACC: {acc:.2f}\nAUC: {roc_auc:.2f}")
            else:
                self.perf_status.configure(text="Khong tim thay nhan tuong ung", text_color="orange")
                img_sample = os.path.splitext(os.path.basename(self.test_input_files[0]))[0] + ".txt"
                messagebox.showwarning("Loi Khop Nhan",
                    f"Da nap {len(self.test_input_files)} anh, nhung khong tim thay file .txt nao tuong ung trong thu muc Labels.\n\n"
                    f"Yeu cau: Ten file anh va file nhan phai giong nhau.\n"
                    f"Vi du: Anh '{os.path.basename(self.test_input_files[0])}' thi Labels phai co file '{img_sample}'\n\n"
                    f"Vui long kiem tra lai ten file hoac thu muc Labels.")

        threading.Thread(target=_perf_worker, daemon=True).start()

    def show_metrics_charts(self):
        if not self.latest_metrics:
            messagebox.showinfo("ThÃ´ng bÃ¡o", "ChÆ°a cÃ³ dá»¯ liá»‡u Ä‘Ã¡nh giÃ¡. HÃ£y cháº¡y 'ÄÃNH GIÃ MODEL' trÆ°á»›c."); return
            
        view = ctk.CTkToplevel(self)
        view.title(f"Biểu đồ hiệu năng - {self.latest_metrics['time']}")
        view.geometry("900x700")

        # Vẽ biểu đồ bằng matplotlib
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.plot(self.latest_metrics['fpr'], self.latest_metrics['tpr'], color='darkorange', lw=2, 
                label=f"ROC curve (AUC = {self.latest_metrics['roc_auc']:.2f})")
        ax.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
        ax.set_xlim([0.0, 1.0]); ax.set_ylim([0.0, 1.05])
        ax.set_xlabel('False Positive Rate')
        ax.set_ylabel('True Positive Rate')
        ax.set_title(f"ROC Curve - Accuracy: {self.latest_metrics['acc']:.2%}\nTested on {self.latest_metrics['total']} images")
        ax.legend(loc="lower right")
        ax.grid(alpha=0.3)

        canvas = FigureCanvasTkAgg(fig, master=view)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=20)

        def save_chart():
            fd = filedialog.askdirectory(title="Chá»n nÆ¡i lÆ°u biá»ƒu Ä‘á»“")
            if fd:
                filepath = os.path.join(fd, f"metrics_{int(time.time())}.png")
                fig.savefig(filepath)
                messagebox.showinfo("LÆ°u xong", f"ÄÃ£ lÆ°u biá»ƒu Ä‘á»“ táº¡i:\n{filepath}")

        ctk.CTkButton(view, text="Luu Bieu Do Thanh Anh", command=save_chart).pack(pady=10)

    # ------------------------------------------------- Realtime detection ---
    def browse_source(self):
        m = self.input_mode.get()
        if m == "image": p = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg *.jpeg *.png *.bmp *.webp")])
        elif m == "video": p = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4 *.avi *.mov *.mkv")])
        else: p = ""
        if p: self.source_path.set(p)

    def start_detection(self):
        if not self.model: messagebox.showerror("Lỗi", "Chưa load model!"); return
        self.is_running = True
        self.start_btn.configure(state="disabled"); self.stop_btn.configure(state="normal")
        m = self.input_mode.get()
        if m == "camera": target = self._detect_camera
        elif m == "image": target = self._detect_image
        else: target = self._detect_video
        self._detect_thread = threading.Thread(target=target, daemon=True)
        self._detect_thread.start()

    def stop_detection(self):
        self.is_running = False
        self.start_btn.configure(state="normal"); self.stop_btn.configure(state="disabled")
        if self._cap: self._cap.release(); self._cap = None

    def _detect_camera(self):
        try: idx = int(self.camera_index.get())
        except: idx = 0
        self._cap = cv2.VideoCapture(idx)
        if not self._cap or not self._cap.isOpened():
            messagebox.showerror("Loi", f"Khong the mo Camera index {idx}. Vui long kiem tra ket noi."); self.stop_detection(); return
        while self.is_running and self._cap.isOpened():
            t0 = time.time(); ret, frame = self._cap.read()
            if not ret: break
            self._display_frame(self._run_inference(frame))
            self.stats_label.configure(text=f"FPS: {1/max(time.time()-t0, 1e-6):.1f}")
        self.stop_detection()

    def _detect_video(self):
        p = self.source_path.get()
        if not p: self.stop_detection(); return
        self._cap = cv2.VideoCapture(p)
        while self.is_running and self._cap.isOpened():
            t0 = time.time(); ret, frame = self._cap.read()
            if not ret: break
            self._display_frame(self._run_inference(frame))
            self.stats_label.configure(text=f"FPS: {1/max(time.time()-t0, 1e-6):.1f}")
        self.stop_detection()

    def _detect_image(self):
        p = self.source_path.get()
        if not p: self.stop_detection(); return
        f = cv2.imread(p)
        if f is not None: self._display_frame(self._run_inference(f))
        self.stop_detection()

    def _run_inference(self, frame) -> np.ndarray:
        results = self._predict_with_current_settings(source=frame)
        annotated = frame.copy()
        count = 0
        if self.show_boxes.get():
            for box in results.boxes:
                cls = int(box.cls)
                if self.filter_enabled.get() and (cls not in self.selected_classes or not self.selected_classes[cls].get()): continue
                count += 1
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                color = COLOR_MAP.get(cls, DEFAULT_COLOR)
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                lbl = f"{results.names[cls]} {float(box.conf):.2f}"
                cv2.putText(annotated, lbl, (x1, max(y1-6,0)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        self.stats_label.configure(text=f"Detections: {count}")
        return annotated

    def _display_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        dw, dh = self.display_frame.winfo_width() or 800, self.display_frame.winfo_height() or 600
        h, w = rgb.shape[:2]; sc = min(dw/w, dh/h)
        nw, nh = max(1, int(w*sc)), max(1, int(h * sc))
        
        pil_img = Image.fromarray(cv2.resize(rgb, (nw, nh)))
        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(nw, nh))
        self.video_label.configure(image=ctk_img, text="")
        self.video_label.image = ctk_img

    # ------------------------------------------------- Batch dataset --------
    def browse_batch_files(self):
        fs = filedialog.askopenfilenames(filetypes=[("Image Files", "*.jpg *.jpeg *.png *.bmp *.webp")])
        if fs: 
            self.batch_input_files = list(fs)
            self._update_batch_count("files")
            self.dataset_source_entry.delete(0, "end")
            self.dataset_source_entry.insert(0, f"Selected {len(fs)} files...")

    def browse_batch_folder(self):
        fd = filedialog.askdirectory()
        if fd:
            exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
            self.batch_input_files = [os.path.join(fd, f) for f in os.listdir(fd) if os.path.splitext(f)[1].lower() in exts]
            self._update_batch_count("folder")
            self.dataset_source_entry.delete(0, "end")
            self.dataset_source_entry.insert(0, fd)

    def browse_batch_videos(self):
        fs = filedialog.askopenfilenames(
            title="Chon file video",
            filetypes=[("Video Files", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm")]
        )
        if fs:
            self.batch_input_videos = list(fs)
            self._update_video_count()
            self.video_source_entry.delete(0, "end")
            self.video_source_entry.insert(0, f"Da chon {len(fs)} video")

    def browse_batch_video_folder(self):
        fd = filedialog.askdirectory(title="Chon thu muc chua video")
        if fd:
            exts = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"}
            self.batch_input_videos = [
                os.path.join(fd, f) for f in os.listdir(fd)
                if os.path.splitext(f)[1].lower() in exts
            ]
            self._update_video_count()
            self.video_source_entry.delete(0, "end")
            self.video_source_entry.insert(0, fd)
            messagebox.showinfo("Thong bao", f"Tim thay {len(self.batch_input_videos)} video trong folder.")

    def clear_batch_videos(self):
        self.batch_input_videos = []
        self._update_video_count()
        self.video_source_entry.delete(0, "end")
        self.video_source_entry.insert(0, "")

    def _update_video_count(self):
        c = len(self.batch_input_videos)
        self.video_count_label.configure(text=f"{c} video da chon", text_color="#A78BFA")

    def _update_batch_count(self, mode):
        c = len(self.batch_input_files)
        self.batch_count_label.configure(text=f"Da chon {c} anh", text_color="#10B981")

    def browse_batch_output(self):
        f = filedialog.askdirectory(); 
        if f: self.batch_output_folder.set(f)

    def pause_batch_creation(self):
        self.batch_is_paused = not self.batch_is_paused
        self.batch_pause_btn.configure(text="TIEP TUC" if self.batch_is_paused else "TAM DUNG")

    def stop_batch_creation(self):
        self.batch_is_stopped = True
        self.batch_is_paused = False

    def start_batch_creation(self):
        if not self.model:
            messagebox.showerror("Lỗi", "Chưa load model!"); return
        if not self.batch_input_files and not self.batch_input_videos:
            messagebox.showerror("Lá»—i", "ChÆ°a chá»n áº£nh hoáº·c video nÃ o!"); return
        if not self.batch_output_folder.get():
            messagebox.showerror("Lá»—i", "ChÆ°a chá»n thÆ° má»¥c lÆ°u output!"); return

        self.batch_is_stopped = False; self.batch_is_paused = False
        self.batch_start_btn.configure(state="disabled")
        self.batch_pause_btn.configure(state="normal", text="TAM DUNG")
        self.batch_stop_btn.configure(state="normal")
        
        fmt = self.export_format.get(); out = self.batch_output_folder.get()
        if fmt == "roboflow":
            for s in ["train", "valid"]:
                for sub in ["images", "labels"]: os.makedirs(os.path.join(out, s, sub), exist_ok=True)
        elif fmt == "simple":
            for sub in ["images", "labels"]: os.makedirs(os.path.join(out, sub), exist_ok=True)
        
        os.makedirs(os.path.join(out, "debug_boxes"), exist_ok=True)
        os.makedirs(os.path.join(out, "error"), exist_ok=True)

        def _get_valid_boxes(res):
            """Lá»c boxes theo class Ä‘Æ°á»£c chá»n."""
            valid = []
            for box in res.boxes:
                cls = int(box.cls)
                if self.filter_in_dataset.get() and (cls not in self.selected_classes or not self.selected_classes[cls].get()):
                    continue
                valid.append(box)
            return valid

        def _save_frame_to_class_folder(frame, valid_boxes, stem, out_dir):
            """Lưu frame vào thư mục class tương ứng (dùng cho class_folders format)."""
            mode = self.video_split_mode.get()
            if mode == "primary":
                # Chọn box có confidence cao nhất
                best = max(valid_boxes, key=lambda b: float(b.conf))
                cls = int(best.cls)
                cls_name = self.class_name_vars[cls].get() if cls in self.class_name_vars else f"class{cls}"
                cls_dir = os.path.join(out_dir, cls_name)
                os.makedirs(cls_dir, exist_ok=True)
                cv2.imwrite(os.path.join(cls_dir, f"{stem}.jpg"), frame)
            else:  # "all" - lưu vào tất cả class xuất hiện
                seen_classes = set()
                for box in valid_boxes:
                    cls = int(box.cls)
                    if cls in seen_classes:
                        continue
                    seen_classes.add(cls)
                    cls_name = self.class_name_vars[cls].get() if cls in self.class_name_vars else f"class{cls}"
                    cls_dir = os.path.join(out_dir, cls_name)
                    os.makedirs(cls_dir, exist_ok=True)
                    cv2.imwrite(os.path.join(cls_dir, f"{stem}.jpg"), frame)

        def _save_frame_yolo(frame, valid_boxes, stem, out_dir, subset=""):
            """Lưu frame + nhãn YOLO (dùng cho roboflow/simple format)."""
            base_img = os.path.join(out_dir, subset, "images") if subset else os.path.join(out_dir, "images")
            base_lbl = os.path.join(out_dir, subset, "labels") if subset else os.path.join(out_dir, "labels")
            cv2.imwrite(os.path.join(base_img, f"{stem}.jpg"), frame)
            h, w = frame.shape[:2]
            lines = []
            for b in valid_boxes:
                x1, y1, x2, y2 = b.xyxy[0].tolist()
                lines.append(f"{int(b.cls)} {(x1+x2)/2/w:.6f} {(y1+y2)/2/h:.6f} {(x2-x1)/w:.6f} {(y2-y1)/h:.6f}")
            with open(os.path.join(base_lbl, f"{stem}.txt"), "w") as lf:
                lf.write("\n".join(lines))

        def _save_debug(frame, valid_boxes, stem, out_dir):
            boxed = frame.copy()
            for b in valid_boxes:
                c = int(b.cls); x1, y1, x2, y2 = map(int, b.xyxy[0].tolist())
                color = COLOR_MAP.get(c, DEFAULT_COLOR)
                cv2.rectangle(boxed, (x1, y1), (x2, y2), color, 2)
                n = self.class_name_vars[c].get() if c in self.class_name_vars else f"class{c}"
                cv2.putText(boxed, f"{n} {float(b.conf):.2f}", (x1, max(y1-6, 0)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            cv2.imwrite(os.path.join(out_dir, "debug_boxes", f"{stem}.jpg"), boxed)

        def _worker():
            total_images = len(self.batch_input_files)
            total_videos = len(self.batch_input_videos)
            img_success, img_skipped = 0, 0

            # â”€â”€ Xá»¬ LÃ áº¢NH â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            if total_images > 0:
                self.batch_status.configure(text="Dang xu ly anh...", text_color="orange")
                files = list(self.batch_input_files); random.shuffle(files)

                for idx, img_path in enumerate(files):
                    while self.batch_is_paused: time.sleep(0.5)
                    if self.batch_is_stopped: break

                    img = cv2.imread(img_path)
                    if img is None: img_skipped += 1; continue

                    res = self._predict_with_current_settings(source=img)
                    valid = _get_valid_boxes(res)

                    img_name = os.path.basename(img_path)
                    stem = os.path.splitext(img_name)[0]

                    if not valid:
                        shutil.copy(img_path, os.path.join(out, "error", img_name))
                        img_skipped += 1
                    else:
                        if fmt == "class_folders":
                            _save_frame_to_class_folder(img, valid, stem, out)
                        else:
                            subset = "train" if (idx / total_images) < 0.8 and fmt == "roboflow" else \
                                     "valid" if fmt == "roboflow" else ""
                            _save_frame_yolo(img, valid, stem, out, subset)
                        _save_debug(img, valid, stem, out)
                        img_success += 1

                    self.batch_progress_bar.set((idx + 1) / total_images)
                    self.batch_status.configure(
                        text=f"Anh {idx+1}/{total_images} | âœ… {img_success} | â­ï¸ {img_skipped}")

            # â”€â”€ Xá»¬ LÃ VIDEO â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            if total_videos > 0 and not self.batch_is_stopped:
                frame_step = max(1, self.frame_interval.get())
                self.video_progress_label.configure(text="Bat dau xu ly video...", text_color="orange")

                for v_idx, video_path in enumerate(self.batch_input_videos):
                    if self.batch_is_stopped: break

                    video_stem = os.path.splitext(os.path.basename(video_path))[0]
                    cap = cv2.VideoCapture(video_path)
                    if not cap.isOpened():
                        self.video_progress_label.configure(
                            text=f"[{v_idx+1}/{total_videos}] Khong mo duoc: {os.path.basename(video_path)}",
                            text_color="red")
                        continue

                    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    frame_idx = 0
                    saved_frames = 0
                    skipped_frames = 0

                    while True:
                        while self.batch_is_paused: time.sleep(0.5)
                        if self.batch_is_stopped: break

                        ret, frame = cap.read()
                        if not ret: break

                        # Chỉ xử lý frame theo bước nhảy
                        if frame_idx % frame_step != 0:
                            frame_idx += 1
                            continue

                        res = self._predict_with_current_settings(source=frame)
                        valid = _get_valid_boxes(res)

                        frame_stem = f"{video_stem}_f{frame_idx:07d}"

                        if not valid:
                            if self.save_video_no_detect.get():
                                no_det_dir = os.path.join(out, "no_detect")
                                os.makedirs(no_det_dir, exist_ok=True)
                                cv2.imwrite(os.path.join(no_det_dir, f"{frame_stem}.jpg"), frame)
                            skipped_frames += 1
                        else:
                            if fmt == "class_folders":
                                _save_frame_to_class_folder(frame, valid, frame_stem, out)
                            else:
                                # Phân chia train/valid 80/20 dựa theo frame_idx
                                subset = "train" if (frame_idx % 10) < 8 and fmt == "roboflow" else \
                                         "valid" if fmt == "roboflow" else ""
                                _save_frame_yolo(frame, valid, frame_stem, out, subset)
                            _save_debug(frame, valid, frame_stem, out)
                            saved_frames += 1

                        frame_idx += 1

                        # Cập nhật tiến trình video
                        progress = frame_idx / max(total_frames, 1)
                        self.video_progress_bar.set(progress)
                        self.video_progress_label.configure(
                            text=f"Video [{v_idx+1}/{total_videos}] {os.path.basename(video_path)} "
                                 f"| Frame {frame_idx}/{total_frames} "
                                 f"| âœ… {saved_frames} | â­ï¸ {skipped_frames}")

                    cap.release()

                    # Tóm tắt sau mỗi video
                    self.batch_status.configure(
                        text=f"Video {v_idx+1}/{total_videos} xong | ðŸ–¼ {saved_frames} frame luu | â­ {skipped_frames} bo qua")

                self.video_progress_bar.set(1.0)
                if not self.batch_is_stopped:
                    self.video_progress_label.configure(
                        text=f"Da xu ly {total_videos} video xong!", text_color="#A78BFA")

            # â”€â”€ YAML cho YOLO formats â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            if fmt != "class_folders" and not self.batch_is_stopped:
                nc = max(self.class_name_vars.keys()) + 1 if self.class_name_vars else 0
                names = [self.class_name_vars.get(i, ctk.StringVar(value=f"class{i}")).get() for i in range(nc)]
                with open(os.path.join(out, "data.yaml"), "w") as yf:
                    yf.write(
                        f"path: {os.path.abspath(out).replace(chr(92), '/')}\n"
                        f"train: {'train/images' if fmt == 'roboflow' else 'images'}\n"
                        f"val: {'valid/images' if fmt == 'roboflow' else 'images'}\n"
                        f"nc: {nc}\nnames: {names}"
                    )

            self.batch_status.configure(
                text="Hoan thanh!" if not self.batch_is_stopped else "Da dung!",
                text_color="#10B981")
            self.batch_start_btn.configure(state="normal")
            self.batch_pause_btn.configure(state="disabled")
            self.batch_stop_btn.configure(state="disabled")
            if not self.batch_is_stopped:
                summary = []
                if total_images > 0:
                    summary.append(f"Anh: {img_success} luu / {img_skipped} bo qua")
                if total_videos > 0:
                    summary.append(f"Video: {total_videos} file da xu ly")
                messagebox.showinfo("Xong", "Da xu ly xong dataset!\n" + "\n".join(summary))

        threading.Thread(target=_worker, daemon=True).start()


if __name__ == "__main__":
    app = CattleApp()
    app.mainloop()





















