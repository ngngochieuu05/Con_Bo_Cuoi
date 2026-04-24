from __future__ import annotations

import base64
import io
import json
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Tuple


def _maybe_reexec_into_local_venv() -> None:
    """
    This repo expects dependencies installed in a local `.venv`.

    If the user runs `python tool_fix_image.py` without activating the venv,
    imports like `cv2` can fail. When a local `.venv` exists and we're not
    currently inside any venv, re-exec the script using `.venv`'s interpreter.
    """

    if os.environ.get("CON_BO_CUOI_REEXEC") == "1":
        return

    # Already inside a venv -> don't override user intent.
    if getattr(sys, "base_prefix", sys.prefix) != sys.prefix:
        return

    repo_root = Path(__file__).resolve().parent

    # Windows venv layout (this project is primarily Windows).
    venv_python = repo_root / ".venv" / "Scripts" / "python.exe"

    # Cross-platform fallback for completeness.
    if not venv_python.exists():
        venv_python = repo_root / ".venv" / "bin" / "python"

    if not venv_python.exists():
        return

    try:
        if Path(sys.executable).resolve() == venv_python.resolve():
            return
    except Exception:
        # If resolving fails, fall back to re-exec attempt.
        pass

    env = os.environ.copy()
    env["CON_BO_CUOI_REEXEC"] = "1"

    completed = subprocess.run(
        [str(venv_python), str(Path(__file__).resolve()), *sys.argv[1:]],
        env=env,
    )
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    _maybe_reexec_into_local_venv()


try:
    import cv2
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Missing dependency `cv2`.\n"
        "You are likely running the script outside the repo's virtualenv.\n"
        "Run one of:\n"
        "  .\\.venv\\Scripts\\python.exe .\\tool_fix_image.py\n"
        "Or activate the venv (PowerShell) then rerun:\n"
        "  .\\.venv\\Scripts\\Activate.ps1\n"
        "  python .\\tool_fix_image.py\n"
        "Or install deps:\n"
        "  pip install -r webapp_system/requirements.txt\n"
    ) from exc

try:
    import flet as ft
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Missing dependency `flet`.\n"
        "Install deps:\n"
        "  pip install -r webapp_system/requirements.txt\n"
    ) from exc

try:
    import numpy as np
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Missing dependency `numpy`.\n"
        "Install deps:\n"
        "  pip install -r webapp_system/requirements.txt\n"
    ) from exc

try:
    from PIL import Image
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Missing dependency `Pillow` (PIL).\n"
        "Install deps:\n"
        "  pip install -r webapp_system/requirements.txt\n"
    ) from exc


SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
EMPTY_PREVIEW_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    "/w8AAgMBgJ/gX1cAAAAASUVORK5CYII="
)


# =========================================================
# CONFIG
# =========================================================

@dataclass
class ProcessConfig:
    enable_resize: bool = True
    target_size: int = 1024
    resize_mode: str = "Letterbox"  # Letterbox | Stretch | CenterCrop
    stride: int = 32
    pad_color: int = 114

    gamma: float = 1.0
    auto_contrast: float = 0.0
    white_balance: float = 0.0

    clahe_clip: float = 1.2
    clahe_tile: int = 8

    denoise_method: str = "Bilateral"  # None | Bilateral | NLMeans
    bilateral_d: int = 5
    bilateral_sigma_color: int = 30
    bilateral_sigma_space: int = 30

    nlmeans_h: int = 5
    nlmeans_h_color: int = 5

    sharpen_amount: float = 0.20
    sharpen_radius: float = 1.0

    saturation: float = 1.0


@dataclass
class BatchTask:
    task_id: int
    input_dir: Path
    output_dir: Path
    cfg: ProcessConfig
    total_files: int
    processed_count: int = 0
    skipped_count: int = 0
    status: str = "Queued"
    current_file: str = ""
    error: Optional[str] = None
    pause_requested: bool = False
    hard_stop_requested: bool = False
    delete_requested: bool = False
    last_ui_update: float = 0.0
    card: Optional[ft.Control] = None
    title_text: Optional[ft.Text] = None
    status_text: Optional[ft.Text] = None
    detail_text: Optional[ft.Text] = None
    progress_bar: Optional[ft.ProgressBar] = None
    pause_button: Optional[ft.OutlinedButton] = None
    stop_button: Optional[ft.OutlinedButton] = None
    resume_button: Optional[ft.OutlinedButton] = None
    delete_button: Optional[ft.OutlinedButton] = None


PRESETS: dict[str, ProcessConfig] = {
    "safe": ProcessConfig(
        enable_resize=True,
        target_size=1024,
        resize_mode="Letterbox",
        stride=32,
        pad_color=114,
        gamma=1.0,
        auto_contrast=0.0,
        white_balance=0.0,
        clahe_clip=1.2,
        clahe_tile=8,
        denoise_method="Bilateral",
        bilateral_d=5,
        bilateral_sigma_color=30,
        bilateral_sigma_space=30,
        nlmeans_h=5,
        nlmeans_h_color=5,
        sharpen_amount=0.20,
        sharpen_radius=1.0,
        saturation=1.0,
    ),
    "more_clear": ProcessConfig(
        enable_resize=True,
        target_size=1024,
        resize_mode="Letterbox",
        stride=32,
        pad_color=114,
        gamma=0.95,
        auto_contrast=1.0,
        white_balance=0.25,
        clahe_clip=1.6,
        clahe_tile=8,
        denoise_method="Bilateral",
        bilateral_d=5,
        bilateral_sigma_color=35,
        bilateral_sigma_space=35,
        nlmeans_h=5,
        nlmeans_h_color=5,
        sharpen_amount=0.35,
        sharpen_radius=1.2,
        saturation=1.0,
    ),
    "dark_image": ProcessConfig(
        enable_resize=True,
        target_size=1024,
        resize_mode="Letterbox",
        stride=32,
        pad_color=114,
        gamma=0.80,
        auto_contrast=1.2,
        white_balance=0.20,
        clahe_clip=1.5,
        clahe_tile=8,
        denoise_method="Bilateral",
        bilateral_d=5,
        bilateral_sigma_color=30,
        bilateral_sigma_space=30,
        nlmeans_h=5,
        nlmeans_h_color=5,
        sharpen_amount=0.30,
        sharpen_radius=1.1,
        saturation=1.0,
    ),
    "high_noise": ProcessConfig(
        enable_resize=True,
        target_size=1024,
        resize_mode="Letterbox",
        stride=32,
        pad_color=114,
        gamma=1.0,
        auto_contrast=0.4,
        white_balance=0.15,
        clahe_clip=1.0,
        clahe_tile=8,
        denoise_method="NLMeans",
        bilateral_d=5,
        bilateral_sigma_color=30,
        bilateral_sigma_space=30,
        nlmeans_h=6,
        nlmeans_h_color=6,
        sharpen_amount=0.15,
        sharpen_radius=1.0,
        saturation=1.0,
    ),
    "roboflow_640": ProcessConfig(
        enable_resize=True,
        target_size=640,
        resize_mode="Letterbox",
        stride=32,
        pad_color=114,
        gamma=1.0,
        auto_contrast=0.6,
        white_balance=0.15,
        clahe_clip=1.0,
        clahe_tile=8,
        denoise_method="Bilateral",
        bilateral_d=5,
        bilateral_sigma_color=25,
        bilateral_sigma_space=25,
        nlmeans_h=5,
        nlmeans_h_color=5,
        sharpen_amount=0.15,
        sharpen_radius=1.0,
        saturation=1.0,
    ),
    "natural": ProcessConfig(
        enable_resize=False,
        target_size=1024,
        resize_mode="Letterbox",
        stride=32,
        pad_color=114,
        gamma=1.0,
        auto_contrast=0.0,
        white_balance=0.0,
        clahe_clip=0.0,
        clahe_tile=8,
        denoise_method="None",
        bilateral_d=0,
        bilateral_sigma_color=0,
        bilateral_sigma_space=0,
        nlmeans_h=0,
        nlmeans_h_color=0,
        sharpen_amount=0.0,
        sharpen_radius=1.0,
        saturation=1.0,
    ),
}


# =========================================================
# IMAGE PROCESSING
# =========================================================

def resize_keep_ratio_with_padding(
    img: np.ndarray,
    target_size: int,
    enable_resize: bool = True,
    pad_color: Tuple[int, int, int] = (114, 114, 114),
) -> np.ndarray:
    if not enable_resize or target_size <= 0:
        return img

    h, w = img.shape[:2]

    if h <= 0 or w <= 0:
        return img

    scale = min(target_size / w, target_size / h)

    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))

    interpolation = cv2.INTER_AREA
    if scale > 1.0:
        interpolation = cv2.INTER_LANCZOS4 if scale >= 1.5 else cv2.INTER_CUBIC

    resized = cv2.resize(
        img,
        (new_w, new_h),
        interpolation=interpolation,
    )

    canvas = np.full(
        (target_size, target_size, 3),
        pad_color,
        dtype=np.uint8,
    )

    x_offset = (target_size - new_w) // 2
    y_offset = (target_size - new_h) // 2

    canvas[
        y_offset:y_offset + new_h,
        x_offset:x_offset + new_w,
    ] = resized

    return canvas


def resize_for_training(img: np.ndarray, cfg: ProcessConfig) -> np.ndarray:
    if not cfg.enable_resize or cfg.target_size <= 0:
        return img

    target_size = int(cfg.target_size)
    mode = str(cfg.resize_mode or "Letterbox")

    if mode == "Stretch":
        return cv2.resize(img, (target_size, target_size), interpolation=cv2.INTER_AREA)

    if mode == "CenterCrop":
        h, w = img.shape[:2]
        side = min(h, w)
        y1 = max(0, (h - side) // 2)
        x1 = max(0, (w - side) // 2)
        cropped = img[y1:y1 + side, x1:x1 + side]
        return cv2.resize(cropped, (target_size, target_size), interpolation=cv2.INTER_AREA)

    rounded_size = target_size
    if cfg.stride > 1:
        rounded_size = int(np.ceil(target_size / cfg.stride) * cfg.stride)

    pad = int(np.clip(cfg.pad_color, 0, 255))
    return resize_keep_ratio_with_padding(
        img,
        target_size=rounded_size,
        enable_resize=True,
        pad_color=(pad, pad, pad),
    )


def apply_auto_contrast(img: np.ndarray, clip_percent: float) -> np.ndarray:
    if clip_percent <= 0:
        return img

    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    low = np.percentile(l_channel, float(clip_percent))
    high = np.percentile(l_channel, 100.0 - float(clip_percent))

    if high <= low:
        return img

    stretched = (l_channel.astype(np.float32) - low) * (255.0 / (high - low))
    stretched = np.clip(stretched, 0, 255).astype(np.uint8)
    return cv2.cvtColor(cv2.merge((stretched, a_channel, b_channel)), cv2.COLOR_LAB2BGR)


def apply_gray_world_white_balance(img: np.ndarray, amount: float) -> np.ndarray:
    if amount <= 0:
        return img

    amount = float(np.clip(amount, 0.0, 1.0))
    work = img.astype(np.float32)
    means = work.reshape(-1, 3).mean(axis=0)
    gray = float(means.mean())
    gains = gray / np.maximum(means, 1.0)
    balanced = np.clip(work * gains, 0, 255).astype(np.uint8)
    return cv2.addWeighted(img, 1.0 - amount, balanced, amount, 0)


def apply_gamma(img: np.ndarray, gamma: float) -> np.ndarray:
    if abs(gamma - 1.0) < 1e-6:
        return img

    gamma = max(float(gamma), 0.01)
    inv_gamma = 1.0 / gamma

    table = np.array(
        [((i / 255.0) ** inv_gamma) * 255 for i in range(256)]
    ).astype("uint8")

    return cv2.LUT(img, table)


def apply_clahe_lab(
    img: np.ndarray,
    clip_limit: float,
    tile_grid_size: int,
) -> np.ndarray:
    if clip_limit <= 0:
        return img

    tile_grid_size = max(2, int(tile_grid_size))

    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    clahe = cv2.createCLAHE(
        clipLimit=float(clip_limit),
        tileGridSize=(tile_grid_size, tile_grid_size),
    )

    l_enhanced = clahe.apply(l_channel)

    lab_enhanced = cv2.merge(
        (l_enhanced, a_channel, b_channel)
    )

    return cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)


def apply_bilateral_denoise(
    img: np.ndarray,
    d: int,
    sigma_color: int,
    sigma_space: int,
) -> np.ndarray:
    if d <= 0:
        return img

    d = int(d)

    if d % 2 == 0:
        d += 1

    return cv2.bilateralFilter(
        img,
        d=d,
        sigmaColor=int(sigma_color),
        sigmaSpace=int(sigma_space),
    )


def apply_nlmeans_denoise(
    img: np.ndarray,
    h: int,
    h_color: int,
) -> np.ndarray:
    if h <= 0 and h_color <= 0:
        return img

    return cv2.fastNlMeansDenoisingColored(
        img,
        None,
        h=max(0, int(h)),
        hColor=max(0, int(h_color)),
        templateWindowSize=7,
        searchWindowSize=21,
    )


def apply_unsharp_mask(
    img: np.ndarray,
    amount: float,
    radius: float,
) -> np.ndarray:
    if amount <= 0:
        return img

    radius = max(0.1, float(radius))

    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    blur = cv2.GaussianBlur(
        l_channel,
        (0, 0),
        radius,
    )

    sharpened_l = cv2.addWeighted(
        l_channel,
        1.0 + amount,
        blur,
        -amount,
        0,
    )

    sharpened_lab = cv2.merge(
        (
            np.clip(sharpened_l, 0, 255).astype(np.uint8),
            a_channel,
            b_channel,
        )
    )

    return cv2.cvtColor(sharpened_lab, cv2.COLOR_LAB2BGR)


def apply_detail_enhance(
    img: np.ndarray,
    sharpen_amount: float,
) -> np.ndarray:
    if sharpen_amount <= 0.10:
        return img

    strength = min(1.0, max(0.0, sharpen_amount * 2.0))

    return cv2.detailEnhance(
        img,
        sigma_s=10 + strength * 70,
        sigma_r=min(0.35, 0.12 + strength * 0.12),
    )


def apply_saturation(
    img: np.ndarray,
    saturation: float,
) -> np.ndarray:
    if abs(saturation - 1.0) < 1e-6:
        return img

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)

    hsv[:, :, 1] *= float(saturation)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)

    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)


def preprocess_cv2(
    img: np.ndarray,
    cfg: ProcessConfig,
) -> np.ndarray:
    out = img.copy()

    out = resize_for_training(out, cfg)

    out = apply_gray_world_white_balance(out, cfg.white_balance)

    out = apply_auto_contrast(out, cfg.auto_contrast)

    out = apply_gamma(out, cfg.gamma)

    out = apply_clahe_lab(
        out,
        clip_limit=cfg.clahe_clip,
        tile_grid_size=cfg.clahe_tile,
    )

    if cfg.denoise_method == "Bilateral":
        out = apply_bilateral_denoise(
            out,
            d=cfg.bilateral_d,
            sigma_color=cfg.bilateral_sigma_color,
            sigma_space=cfg.bilateral_sigma_space,
        )

    elif cfg.denoise_method == "NLMeans":
        out = apply_nlmeans_denoise(
            out,
            h=cfg.nlmeans_h,
            h_color=cfg.nlmeans_h_color,
        )

    out = apply_detail_enhance(
        out,
        sharpen_amount=cfg.sharpen_amount,
    )

    out = apply_saturation(
        out,
        saturation=cfg.saturation,
    )

    out = apply_unsharp_mask(
        out,
        amount=cfg.sharpen_amount,
        radius=cfg.sharpen_radius,
    )

    return out


def cv2_to_base64_png(
    img_bgr: np.ndarray,
    max_w: int = 850,
    max_h: int = 650,
) -> str:
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    pil_img = Image.fromarray(rgb)

    w, h = pil_img.size

    scale = min(
        max_w / w,
        max_h / h,
        1.0,
    )

    if scale < 1.0:
        pil_img = pil_img.resize(
            (
                max(1, int(w * scale)),
                max(1, int(h * scale)),
            ),
            Image.Resampling.LANCZOS,
        )

    buffer = io.BytesIO()

    pil_img.save(
        buffer,
        format="PNG",
    )

    return base64.b64encode(
        buffer.getvalue()
    ).decode("utf-8")


def read_image_bgr(path: Path) -> Optional[np.ndarray]:
    try:
        raw = path.read_bytes()
    except OSError:
        return None

    if not raw:
        return None

    array = np.frombuffer(raw, dtype=np.uint8)
    img = cv2.imdecode(array, cv2.IMREAD_COLOR)

    if img is None:
        return None

    if len(img.shape) == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    return img


def save_image(path: Path, img_bgr: np.ndarray) -> bool:
    suffix = path.suffix.lower() or ".png"

    if suffix == ".jpg":
        suffix = ".jpeg"

    if suffix not in SUPPORTED_EXTS:
        suffix = ".png"
        path = path.with_suffix(".png")

    ok, encoded = cv2.imencode(suffix, img_bgr)

    if not ok:
        return False

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encoded.tobytes())
        return True
    except OSError:
        return False


# =========================================================
# FLET APP
# =========================================================

class CowSkinPreprocessApp:
    def __init__(self, page: ft.Page):
        self.page = page

        self.cfg = ProcessConfig()

        self.current_path: Optional[Path] = None
        self.original_img: Optional[np.ndarray] = None
        self.processed_img: Optional[np.ndarray] = None

        self.batch_input_dir: Optional[Path] = None
        self.batch_output_dir: Optional[Path] = None
        self.batch_tasks: list[BatchTask] = []
        self.batch_task_lock = threading.Lock()
        self.next_batch_task_id = 1
        self.show_param_help = False
        self.help_text_controls: list[ft.Text] = []
        self.main_tabs: Optional[ft.Tabs] = None
        self.preview_placeholder: Optional[ft.Control] = None
        self.preview_workspace: Optional[ft.Control] = None
        self.refresh_preview_button: Optional[ft.OutlinedButton] = None
        self.save_image_button: Optional[ft.OutlinedButton] = None

        self.file_picker_open = ft.FilePicker(
            on_result=self.on_open_file_result,
        )

        self.file_picker_save = ft.FilePicker(
            on_result=self.on_save_file_result,
        )

        self.file_picker_batch_input = ft.FilePicker(
            on_result=self.on_batch_input_result,
        )

        self.file_picker_batch_output = ft.FilePicker(
            on_result=self.on_batch_output_result,
        )

        self.page.overlay.append(self.file_picker_open)
        self.page.overlay.append(self.file_picker_save)
        self.page.overlay.append(self.file_picker_batch_input)
        self.page.overlay.append(self.file_picker_batch_output)

        self.instant_switch = ft.Switch(
            label="Apply tuc thi",
            value=True,
        )

        self.status_text = ft.Text(
            value="San sang.",
            size=12,
            color=ft.Colors.GREY_700,
        )

        self.batch_input_text = ft.Text(
            value="Input: chua chon",
            size=12,
            color=ft.Colors.GREY_700,
        )

        self.batch_output_text = ft.Text(
            value="Output: chua chon",
            size=12,
            color=ft.Colors.GREY_700,
        )

        self.batch_queue_text = ft.Text(
            value="Chua co batch task.",
            size=12,
            color=ft.Colors.GREY_700,
        )

        self.batch_tasks_column = ft.Column(
            spacing=10,
            controls=[],
        )

        self.original_preview = ft.Image(
            src_base64=EMPTY_PREVIEW_BASE64,
            fit=ft.ImageFit.CONTAIN,
            expand=True,
        )

        self.processed_preview = ft.Image(
            src_base64=EMPTY_PREVIEW_BASE64,
            fit=ft.ImageFit.CONTAIN,
            expand=True,
        )

        self.original_info = ft.Text(
            value="Chua mo anh.",
            size=12,
            color=ft.Colors.GREY_700,
        )

        self.processed_info = ft.Text(
            value="Chua xu ly.",
            size=12,
            color=ft.Colors.GREY_700,
        )

        self.enable_resize = ft.Switch(
            label="Resize + padding vuong",
            value=self.cfg.enable_resize,
            on_change=self.on_control_change,
        )

        self.enable_resize_help = self.make_help_text(
            "Bat de dua anh ve kich thuoc vuong cho model. Neu anh goc nho, viec upscale se co the lam lo them."
        )

        self.resize_mode = ft.Dropdown(
            label="Resize Mode",
            value=self.cfg.resize_mode,
            options=[
                ft.DropdownOption("Letterbox"),
                ft.DropdownOption("Stretch"),
                ft.DropdownOption("CenterCrop"),
            ],
            on_change=self.on_control_change,
        )
        self.resize_mode_help = self.make_help_text(
            "Letterbox nhu Ultralytics/YOLO: giu ti le va them padding. Stretch co the meo anh. CenterCrop cat giua anh."
        )

        self.target_size = self.make_slider(
            label="Output size",
            min_value=512,
            max_value=1536,
            value=self.cfg.target_size,
            step=128,
            help_text="Kich thuoc anh dau ra. Cang lon thi nhin to hon, nhung khong tao them chi tiet that; thu 640 neu anh goc qua mo.",
        )

        self.stride = self.make_slider(
            label="Stride padding | YOLO 32",
            min_value=1,
            max_value=64,
            value=self.cfg.stride,
            step=1,
            help_text="Lam tron kich thuoc letterbox theo boi so stride. YOLO thuong dung 32; dat 1 de tat lam tron.",
        )

        self.pad_color = self.make_slider(
            label="Pad color | YOLO 114",
            min_value=0,
            max_value=255,
            value=self.cfg.pad_color,
            step=1,
            help_text="Mau nen padding khi letterbox. Ultralytics thuong dung xam 114 de model on dinh hon nen den/trang.",
        )

        self.gamma = self.make_slider(
            label="Gamma | <1 sang hon",
            min_value=0.5,
            max_value=1.8,
            value=self.cfg.gamma,
            step=0.05,
            help_text="Dieu chinh do sang tong the. < 1 lam anh sang hon, > 1 lam anh toi hon. Nen chinh nhe de tranh bay chi tiet.",
        )

        self.auto_contrast = self.make_slider(
            label="Auto contrast | percentile",
            min_value=0.0,
            max_value=3.0,
            value=self.cfg.auto_contrast,
            step=0.1,
            help_text="Keo lai kenh sang theo percentile nhu normalize nhe. Tang qua cao co the mat chi tiet sang/toi.",
        )

        self.white_balance = self.make_slider(
            label="White balance | gray-world",
            min_value=0.0,
            max_value=1.0,
            value=self.cfg.white_balance,
            step=0.05,
            help_text="Giam lech mau do anh chup ngoai chuong. Nen dung nhe de khong lam sai mau vet benh.",
        )

        self.clahe_clip = self.make_slider(
            label="CLAHE Clip | 0 la tat",
            min_value=0.0,
            max_value=4.0,
            value=self.cfg.clahe_clip,
            step=0.1,
            help_text="Tang tuong phan cuc bo de lo ro dom/vet. Qua cao se lam anh bi gat, noi hat va nhin gia.",
        )

        self.clahe_tile = self.make_slider(
            label="CLAHE Tile",
            min_value=2,
            max_value=16,
            value=self.cfg.clahe_tile,
            step=1,
            help_text="Kich thuoc o khi CLAHE chia anh. Tile nho tac dong manh hon, tile lon mem hon.",
        )

        self.denoise_method = ft.Dropdown(
            label="Denoise Method",
            value=self.cfg.denoise_method,
            options=[
                ft.DropdownOption("None"),
                ft.DropdownOption("Bilateral"),
                ft.DropdownOption("NLMeans"),
            ],
            on_change=self.on_control_change,
        )
        self.denoise_method_help = self.make_help_text(
            "None giu nguyen chi tiet. Bilateral giu bien tot, hop voi anh da. NLMeans khu nhieu manh hon nhung de lam mem anh."
        )

        self.bilateral_d = self.make_slider(
            label="Bilateral d | nen 3-7",
            min_value=0,
            max_value=15,
            value=self.cfg.bilateral_d,
            step=1,
            help_text="Kich thuoc vung loc cua Bilateral. Tang len se lam min hon nhung de mat chi tiet nho.",
        )

        self.bilateral_sigma_color = self.make_slider(
            label="Bilateral sigmaColor",
            min_value=0,
            max_value=100,
            value=self.cfg.bilateral_sigma_color,
            step=5,
            help_text="Muc do tron theo khac biet mau. Cao hon se hoa tron cac diem/hat co mau gan nhau.",
        )

        self.bilateral_sigma_space = self.make_slider(
            label="Bilateral sigmaSpace",
            min_value=0,
            max_value=100,
            value=self.cfg.bilateral_sigma_space,
            step=5,
            help_text="Pham vi khong gian cua Bilateral. Cao hon se tac dong len vung rong hon quanh moi diem anh.",
        )

        self.nlmeans_h = self.make_slider(
            label="NLMeans h | nen 3-8",
            min_value=0,
            max_value=20,
            value=self.cfg.nlmeans_h,
            step=1,
            help_text="Do manh khu nhieu cua NLMeans tren kenh sang. Cao qua se lam mat texture va nhin bet.",
        )

        self.nlmeans_h_color = self.make_slider(
            label="NLMeans hColor | nen 3-8",
            min_value=0,
            max_value=20,
            value=self.cfg.nlmeans_h_color,
            step=1,
            help_text="Do manh khu nhieu tren kenh mau. Tang cao de giam loang mau, nhung co the lam da bi be mat.",
        )

        self.sharpen_amount = self.make_slider(
            label="Sharpen Amount | nen 0.10-0.30",
            min_value=0.0,
            max_value=1.0,
            value=self.cfg.sharpen_amount,
            step=0.05,
            help_text="Do manh lam ro bien va texture. Qua cao se tao vien trang/den va lam anh nhin gia.",
        )

        self.sharpen_radius = self.make_slider(
            label="Sharpen Radius",
            min_value=0.3,
            max_value=3.0,
            value=self.cfg.sharpen_radius,
            step=0.1,
            help_text="Ban kinh blur dung trong sharpen. Radius nho danh vao chi tiet min, radius lon danh vao bien lon hon.",
        )

        self.saturation = self.make_slider(
            label="Saturation | 1.0 giu nguyen",
            min_value=0.5,
            max_value=1.5,
            value=self.cfg.saturation,
            step=0.05,
            help_text="Do dam mau. De gan 1.0 cho anh phan tich; tang qua cao de lam mau sai va nhieu hon.",
        )

    # -----------------------------------------------------
    # UI setup
    # -----------------------------------------------------

    def setup(self):
        self.page.title = "Cow Skin Lesion Preprocess Tool"

        self.page.padding = 16
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.theme = ft.Theme(
            color_scheme_seed=ft.Colors.GREEN,
        )

        # Flet 0.28.x: dung page.window.*, khong dung page.window_width.
        try:
            self.page.window.width = 1450
            self.page.window.height = 900
            self.page.window.min_width = 1180
            self.page.window.min_height = 720
        except Exception:
            pass

        self.page.add(
            ft.Column(
                expand=True,
                controls=[
                    self.build_header(),
                    ft.Row(
                        expand=True,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                        controls=[
                            self.build_left_panel(),
                            self.build_preview_panel(),
                        ],
                    ),
                ],
            )
        )

        self.update_status(
            "Da khoi dong. Mo anh roi chon Quick Setting hoac chinh slider."
        )

    def build_header(self) -> ft.Control:
        self.save_image_button = ft.OutlinedButton(
            text="Luu anh",
            icon=ft.Icons.SAVE,
            disabled=True,
            on_click=self.open_save_dialog,
        )
        self.header_status_card = ft.Container(
            visible=False,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=12,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.GREY_200),
            content=ft.Column(
                spacing=2,
                controls=[
                    ft.Text(
                        "Trang thai",
                        size=11,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.GREEN_800,
                    ),
                    self.status_text,
                ],
            ),
        )
        return ft.Container(
            padding=16,
            border_radius=18,
            bgcolor=ft.Colors.GREEN_50,
            content=ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.IMAGE_SEARCH,
                        size=32,
                        color=ft.Colors.GREEN_700,
                    ),
                    ft.Column(
                        expand=True,
                        spacing=8,
                        controls=[
                            ft.Text(
                                "Cow Skin Lesion Preprocess Tool",
                                size=24,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                "Flet desktop app xu ly anh da bo truoc khi ve polygon instance segmentation tren Roboflow.",
                                size=13,
                                color=ft.Colors.GREY_700,
                            ),
                        ],
                    ),
                    self.header_status_card,
                    self.instant_switch,
                    ft.FilledButton(
                        text="Mo anh",
                        icon=ft.Icons.FOLDER_OPEN,
                        on_click=self.open_image_dialog,
                    ),
                    self.save_image_button,
                ],
            ),
        )

    def build_left_panel(self) -> ft.Control:
        return ft.Container(
            width=430,
            padding=12,
            border_radius=18,
            bgcolor=ft.Colors.GREY_50,
            content=ft.Column(
                scroll=ft.ScrollMode.AUTO,
                spacing=12,
                controls=[
                    self.build_quick_settings(),
                    self.build_controls(),
                ],
            ),
        )

    def build_quick_settings(self) -> ft.Control:
        return ft.Container(
            padding=12,
            border_radius=16,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(
                1,
                ft.Colors.GREY_200,
            ),
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.FLASH_ON,
                                color=ft.Colors.GREEN_700,
                            ),
                            ft.Text(
                                "Quick Settings",
                                size=18,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ],
                    ),
                    ft.Text(
                        "Bam preset de thiet lap thong so tuc thi.",
                        size=12,
                        color=ft.Colors.GREY_700,
                    ),
                    ft.Row(
                        wrap=True,
                        spacing=8,
                        run_spacing=8,
                        controls=[
                            ft.FilledTonalButton(
                                text="An toan",
                                icon=ft.Icons.CHECK_CIRCLE,
                                on_click=lambda e: self.apply_preset("safe"),
                            ),
                            ft.FilledTonalButton(
                                text="Ro hon",
                                icon=ft.Icons.AUTO_FIX_HIGH,
                                on_click=lambda e: self.apply_preset("more_clear"),
                            ),
                            ft.FilledTonalButton(
                                text="Anh toi",
                                icon=ft.Icons.WB_SUNNY,
                                on_click=lambda e: self.apply_preset("dark_image"),
                            ),
                            ft.FilledTonalButton(
                                text="Nhieu cao",
                                icon=ft.Icons.GRAIN,
                                on_click=lambda e: self.apply_preset("high_noise"),
                            ),
                            ft.FilledTonalButton(
                                text="RF 640",
                                icon=ft.Icons.CROP,
                                on_click=lambda e: self.apply_preset("roboflow_640"),
                            ),
                            ft.FilledTonalButton(
                                text="Reset",
                                icon=ft.Icons.RESTART_ALT,
                                on_click=lambda e: self.apply_preset("natural"),
                            ),
                        ],
                    ),
                    ft.Divider(),
                    ft.Row(
                        controls=[
                            ft.OutlinedButton(
                                text="Copy config",
                                icon=ft.Icons.CONTENT_COPY,
                                expand=True,
                                on_click=self.copy_config,
                            ),
                            ft.OutlinedButton(
                                text="Luu config",
                                icon=ft.Icons.DOWNLOAD,
                                expand=True,
                                on_click=self.save_config_json,
                            ),
                        ],
                    ),
                ],
            ),
        )

    def build_controls(self) -> ft.Control:
        return ft.Container(
            padding=12,
            border_radius=16,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(
                1,
                ft.Colors.GREY_200,
            ),
            content=ft.ExpansionTile(
                initially_expanded=True,
                tile_padding=ft.padding.only(left=0, right=4),
                controls_padding=ft.padding.only(top=8),
                title=ft.Text(
                    "Thong so xu ly",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                ),
                subtitle=ft.Text(
                    "An/hien panel tham so de tap trung vao preview.",
                    size=12,
                    color=ft.Colors.GREY_700,
                ),
                controls=[
                    ft.TextButton(
                        text="Hien chu thich" if not self.show_param_help else "An chu thich",
                        icon=ft.Icons.HELP_OUTLINE,
                        on_click=self.toggle_param_help,
                    ),
                    self.enable_resize,
                    self.enable_resize_help,
                    self.resize_mode,
                    self.resize_mode_help,
                    self.target_size,
                    self.stride,
                    self.pad_color,
                    self.gamma,
                    self.auto_contrast,
                    self.white_balance,
                    self.clahe_clip,
                    self.clahe_tile,
                    self.denoise_method,
                    self.denoise_method_help,
                    self.bilateral_d,
                    self.bilateral_sigma_color,
                    self.bilateral_sigma_space,
                    self.nlmeans_h,
                    self.nlmeans_h_color,
                    self.sharpen_amount,
                    self.sharpen_radius,
                    self.saturation,
                    ft.Container(
                        padding=10,
                        border_radius=12,
                        bgcolor=ft.Colors.AMBER_50,
                        content=ft.Text(
                            "Meo: neu long bi gai hoac da nhin gia, giam CLAHE Clip va Sharpen Amount.",
                            size=12,
                            color=ft.Colors.BROWN_700,
                        ),
                    ),
                ],
            ),
        )

    def build_batch_controls(self) -> ft.Control:
        return ft.Container(
            padding=12,
            border_radius=16,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(
                1,
                ft.Colors.GREY_200,
            ),
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.FOLDER_COPY,
                                color=ft.Colors.GREEN_700,
                            ),
                            ft.Text(
                                "Batch xu ly thu muc",
                                size=18,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ],
                    ),
                    ft.Text(
                        "Dung thong so hien tai de xu ly toan bo anh trong mot thu muc.",
                        size=12,
                        color=ft.Colors.GREY_700,
                    ),
                    ft.Container(
                        padding=12,
                        border_radius=12,
                        bgcolor=ft.Colors.GREEN_50,
                        content=ft.Column(
                            spacing=6,
                            controls=[
                                self.batch_input_text,
                                self.batch_output_text,
                            ],
                        ),
                    ),
                    ft.Row(
                        controls=[
                            ft.OutlinedButton(
                                text="Input",
                                icon=ft.Icons.FOLDER_OPEN,
                                expand=True,
                                on_click=lambda e: self.file_picker_batch_input.get_directory_path(),
                            ),
                            ft.OutlinedButton(
                                text="Output",
                                icon=ft.Icons.CREATE_NEW_FOLDER,
                                expand=True,
                                on_click=lambda e: self.file_picker_batch_output.get_directory_path(),
                            ),
                        ],
                    ),
                    ft.FilledButton(
                        text="Chay batch",
                        icon=ft.Icons.PLAY_ARROW,
                        on_click=self.run_batch,
                    ),
                    ft.Divider(),
                    ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.TASK_ALT,
                                color=ft.Colors.GREEN_700,
                            ),
                            ft.Text(
                                "Danh sach tien trinh",
                                size=16,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ],
                    ),
                    self.batch_queue_text,
                    ft.Container(
                        border_radius=14,
                        bgcolor=ft.Colors.GREY_50,
                        padding=12,
                        content=self.batch_tasks_column,
                    ),
                ],
            ),
        )

    def build_preview_panel(self) -> ft.Control:
        self.main_tabs = ft.Tabs(
            expand=True,
            animation_duration=250,
            indicator_color=ft.Colors.GREEN_700,
            label_color=ft.Colors.GREEN_900,
            unselected_label_color=ft.Colors.GREY_700,
            tabs=[
                ft.Tab(
                    text="Xu ly anh",
                    icon=ft.Icons.IMAGE_OUTLINED,
                    content=self.build_workbench_tab(),
                ),
                ft.Tab(
                    text="Tien trinh",
                    icon=ft.Icons.PENDING_ACTIONS,
                    content=self.build_processes_tab(),
                ),
            ],
        )
        return ft.Container(
            expand=True,
            padding=12,
            border_radius=18,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(
                1,
                ft.Colors.GREY_200,
            ),
            content=self.main_tabs,
        )

    def build_workbench_tab(self) -> ft.Control:
        self.refresh_preview_button = ft.OutlinedButton(
            text="Cap nhat preview",
            icon=ft.Icons.REFRESH,
            disabled=True,
            on_click=lambda e: self.update_preview(),
        )
        self.preview_placeholder = self.build_preview_empty_state()
        self.preview_workspace = ft.Column(
            expand=True,
            visible=False,
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(
                            "Preview Before / After",
                            size=20,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Container(expand=True),
                        self.refresh_preview_button,
                    ],
                ),
                ft.Row(
                    expand=True,
                    controls=[
                        self.preview_card(
                            title="Anh goc",
                            image=self.original_preview,
                            info=self.original_info,
                        ),
                        self.preview_card(
                            title="Anh processed",
                            image=self.processed_preview,
                            info=self.processed_info,
                        ),
                    ],
                ),
            ],
        )
        return ft.Column(
            expand=True,
            controls=[
                self.preview_placeholder,
                self.preview_workspace,
            ],
        )

    def build_processes_tab(self) -> ft.Control:
        return ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=12,
            controls=[
                ft.Container(
                    padding=16,
                    border_radius=16,
                    bgcolor=ft.Colors.GREY_50,
                    content=ft.Column(
                        spacing=4,
                        controls=[
                            ft.Text(
                                "Hang doi xu ly",
                                size=20,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                "Theo doi task dang chay, tam dung, dung han, tiep tuc hoac xoa tien trinh.",
                                size=12,
                                color=ft.Colors.GREY_700,
                            ),
                        ],
                    ),
                ),
                self.build_batch_controls(),
            ],
        )

    def build_preview_empty_state(self) -> ft.Control:
        return ft.Container(
            expand=True,
            alignment=ft.alignment.center,
            border_radius=18,
            bgcolor=ft.Colors.GREY_50,
            border=ft.border.all(1, ft.Colors.GREY_200),
            padding=32,
            content=ft.Column(
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=14,
                controls=[
                    ft.Icon(
                        ft.Icons.ADD_PHOTO_ALTERNATE_OUTLINED,
                        size=48,
                        color=ft.Colors.GREEN_700,
                    ),
                    ft.Text(
                        "Chua co preview",
                        size=22,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Text(
                        'Nhan "Mo anh" de hien Preview Before / After.',
                        size=13,
                        color=ft.Colors.GREY_700,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.FilledButton(
                        text="Mo anh",
                        icon=ft.Icons.FOLDER_OPEN,
                        on_click=self.open_image_dialog,
                    ),
                ],
            ),
        )

    def preview_card(
        self,
        title: str,
        image: ft.Image,
        info: ft.Text,
    ) -> ft.Control:
        return ft.Container(
            expand=True,
            padding=12,
            border_radius=16,
            bgcolor=ft.Colors.GREY_50,
            border=ft.border.all(
                1,
                ft.Colors.GREY_200,
            ),
            content=ft.Column(
                expand=True,
                controls=[
                    ft.Text(
                        title,
                        size=16,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Container(
                        expand=True,
                        alignment=ft.alignment.center,
                        border_radius=14,
                        bgcolor=ft.Colors.WHITE,
                        border=ft.border.all(
                            1,
                            ft.Colors.GREY_200,
                        ),
                        content=image,
                    ),
                    info,
                ],
            ),
        )

    def make_help_text(self, text: str) -> ft.Text:
        help_text = ft.Text(
            value=text,
            size=11,
            color=ft.Colors.BLUE_GREY_600,
            italic=True,
            visible=self.show_param_help,
        )
        self.help_text_controls.append(help_text)
        return help_text

    def toggle_param_help(self, e):
        self.show_param_help = not self.show_param_help
        for help_text in self.help_text_controls:
            help_text.visible = self.show_param_help
        e.control.text = "An chu thich" if self.show_param_help else "Hien chu thich"
        self.page.update()

    def make_slider(
        self,
        label: str,
        min_value: float,
        max_value: float,
        value: float,
        step: float,
        help_text: Optional[str] = None,
    ) -> ft.Control:
        value_text = ft.Text(
            value=self.format_value(value, step),
            size=12,
            color=ft.Colors.GREY_700,
        )

        slider = ft.Slider(
            min=min_value,
            max=max_value,
            divisions=int(round((max_value - min_value) / step)),
            value=value,
            label="{value}",
        )

        def on_change(e):
            current_value = float(e.control.value)
            value_text.value = self.format_value(current_value, step)
            self.page.update()
            self.on_control_change(e)

        slider.on_change = on_change

        slider._custom_step = step

        controls: list[ft.Control] = [
            ft.Row(
                controls=[
                    ft.Text(
                        label,
                        size=12,
                        expand=True,
                    ),
                    value_text,
                ],
            ),
            slider,
        ]

        if help_text:
            controls.append(self.make_help_text(help_text))

        return ft.Column(
            spacing=0,
            controls=controls,
        )

    # -----------------------------------------------------
    # Helpers
    # -----------------------------------------------------

    @staticmethod
    def format_value(value: float, step: float) -> str:
        if step >= 1:
            return str(int(round(value)))

        return f"{value:.2f}"

    @staticmethod
    def get_slider_value(control: ft.Control) -> float:
        if isinstance(control, ft.Column):
            slider = control.controls[1]
            return float(slider.value)

        raise TypeError("Invalid slider control.")

    @staticmethod
    def set_slider_value(control: ft.Control, value: float):
        if not isinstance(control, ft.Column):
            return

        slider = control.controls[1]
        value_text = control.controls[0].controls[1]

        step = getattr(slider, "_custom_step", 0.01)

        slider.value = value
        value_text.value = CowSkinPreprocessApp.format_value(
            value,
            step,
        )

    def get_config_from_controls(self) -> ProcessConfig:
        return ProcessConfig(
            enable_resize=bool(self.enable_resize.value),
            target_size=int(round(self.get_slider_value(self.target_size))),
            resize_mode=str(self.resize_mode.value),
            stride=int(round(self.get_slider_value(self.stride))),
            pad_color=int(round(self.get_slider_value(self.pad_color))),
            gamma=float(self.get_slider_value(self.gamma)),
            auto_contrast=float(self.get_slider_value(self.auto_contrast)),
            white_balance=float(self.get_slider_value(self.white_balance)),
            clahe_clip=float(self.get_slider_value(self.clahe_clip)),
            clahe_tile=int(round(self.get_slider_value(self.clahe_tile))),
            denoise_method=str(self.denoise_method.value),
            bilateral_d=int(round(self.get_slider_value(self.bilateral_d))),
            bilateral_sigma_color=int(round(self.get_slider_value(self.bilateral_sigma_color))),
            bilateral_sigma_space=int(round(self.get_slider_value(self.bilateral_sigma_space))),
            nlmeans_h=int(round(self.get_slider_value(self.nlmeans_h))),
            nlmeans_h_color=int(round(self.get_slider_value(self.nlmeans_h_color))),
            sharpen_amount=float(self.get_slider_value(self.sharpen_amount)),
            sharpen_radius=float(self.get_slider_value(self.sharpen_radius)),
            saturation=float(self.get_slider_value(self.saturation)),
        )

    def apply_config_to_controls(self, cfg: ProcessConfig):
        self.enable_resize.value = cfg.enable_resize
        self.resize_mode.value = cfg.resize_mode

        self.set_slider_value(self.target_size, cfg.target_size)
        self.set_slider_value(self.stride, cfg.stride)
        self.set_slider_value(self.pad_color, cfg.pad_color)
        self.set_slider_value(self.gamma, cfg.gamma)
        self.set_slider_value(self.auto_contrast, cfg.auto_contrast)
        self.set_slider_value(self.white_balance, cfg.white_balance)
        self.set_slider_value(self.clahe_clip, cfg.clahe_clip)
        self.set_slider_value(self.clahe_tile, cfg.clahe_tile)

        self.denoise_method.value = cfg.denoise_method

        self.set_slider_value(self.bilateral_d, cfg.bilateral_d)
        self.set_slider_value(self.bilateral_sigma_color, cfg.bilateral_sigma_color)
        self.set_slider_value(self.bilateral_sigma_space, cfg.bilateral_sigma_space)

        self.set_slider_value(self.nlmeans_h, cfg.nlmeans_h)
        self.set_slider_value(self.nlmeans_h_color, cfg.nlmeans_h_color)

        self.set_slider_value(self.sharpen_amount, cfg.sharpen_amount)
        self.set_slider_value(self.sharpen_radius, cfg.sharpen_radius)
        self.set_slider_value(self.saturation, cfg.saturation)

        self.page.update()

    def update_status(self, text: str):
        self.status_text.value = text
        self.page.update()

    def show_snack(self, text: str):
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(text)
        )

        self.page.snack_bar.open = True

        self.page.update()

    def refresh_page(self):
        try:
            self.page.update()
        except Exception:
            pass

    def set_preview_state(self, visible: bool):
        if self.preview_placeholder is not None:
            self.preview_placeholder.visible = not visible
        if self.preview_workspace is not None:
            self.preview_workspace.visible = visible
        if self.refresh_preview_button is not None:
            self.refresh_preview_button.disabled = not visible
        if self.save_image_button is not None:
            self.save_image_button.disabled = self.processed_img is None
        self.refresh_page()

    def set_active_tab(self, index: int):
        if self.main_tabs is None:
            return
        self.main_tabs.selected_index = index
        self.refresh_page()

    def find_batch_task(self, task_id: int) -> Optional[BatchTask]:
        with self.batch_task_lock:
            return next((item for item in self.batch_tasks if item.task_id == task_id), None)

    def remove_batch_task(self, task_id: int):
        with self.batch_task_lock:
            task = next((item for item in self.batch_tasks if item.task_id == task_id), None)
            if task is None:
                return
            self.batch_tasks = [item for item in self.batch_tasks if item.task_id != task_id]
            if task.card in self.batch_tasks_column.controls:
                self.batch_tasks_column.controls.remove(task.card)
        self.refresh_batch_queue_label()
        self.refresh_page()

    def refresh_batch_queue_label(self):
        total = len(self.batch_tasks)
        running = sum(1 for task in self.batch_tasks if task.status == "Running")
        queued = sum(1 for task in self.batch_tasks if task.status == "Queued")
        paused = sum(1 for task in self.batch_tasks if task.status == "Paused")
        stopping = sum(1 for task in self.batch_tasks if task.status == "Stopping")
        done = sum(1 for task in self.batch_tasks if task.status == "Done")
        cancelled = sum(1 for task in self.batch_tasks if task.status == "Cancelled")
        error = sum(1 for task in self.batch_tasks if task.status == "Error")

        if total == 0:
            self.batch_queue_text.value = "Chua co batch task."
            return

        self.batch_queue_text.value = (
            f"Tong task: {total} | Running: {running} | Queued: {queued} | "
            f"Paused: {paused} | Stopping: {stopping} | Done: {done} | "
            f"Cancelled: {cancelled} | Error: {error}"
        )

    def create_batch_task_card(self, task: BatchTask) -> ft.Control:
        task.title_text = ft.Text(
            value=f"Task #{task.task_id} | {task.input_dir.name}",
            size=14,
            weight=ft.FontWeight.BOLD,
        )
        task.status_text = ft.Text(
            value="Queued",
            size=12,
            color=ft.Colors.GREY_700,
        )
        task.detail_text = ft.Text(
            value=f"0/{task.total_files} anh | Output: {task.output_dir}",
            size=11,
            color=ft.Colors.GREY_600,
        )
        task.progress_bar = ft.ProgressBar(
            value=0 if task.total_files > 0 else None,
            bar_height=10,
            color=ft.Colors.GREEN_700,
            bgcolor=ft.Colors.GREEN_100,
        )
        task.pause_button = ft.OutlinedButton(
            text="Dung",
            icon=ft.Icons.PAUSE_CIRCLE_OUTLINE,
            on_click=lambda e, task_id=task.task_id: self.pause_batch_task(task_id),
        )
        task.stop_button = ft.OutlinedButton(
            text="Dung han",
            icon=ft.Icons.STOP_CIRCLE_OUTLINED,
            on_click=lambda e, task_id=task.task_id: self.stop_batch_task(task_id),
        )
        task.resume_button = ft.OutlinedButton(
            text="Tiep tuc",
            icon=ft.Icons.PLAY_CIRCLE_OUTLINE,
            on_click=lambda e, task_id=task.task_id: self.resume_batch_task(task_id),
        )
        task.delete_button = ft.OutlinedButton(
            text="Xoa",
            icon=ft.Icons.DELETE_OUTLINE,
            on_click=lambda e, task_id=task.task_id: self.delete_batch_task(task_id),
        )
        task.card = ft.Container(
            padding=12,
            border_radius=14,
            bgcolor=ft.Colors.GREEN_50,
            border=ft.border.all(1, ft.Colors.GREEN_100),
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        controls=[
                            task.title_text,
                            ft.Container(expand=True),
                            task.status_text,
                        ],
                    ),
                    task.progress_bar,
                    task.detail_text,
                    ft.Row(
                        wrap=True,
                        spacing=8,
                        run_spacing=8,
                        controls=[
                            task.pause_button,
                            task.stop_button,
                            task.resume_button,
                            task.delete_button,
                        ],
                    ),
                ],
            ),
        )
        self.update_batch_task_ui(task, force=True)
        return task.card

    def update_batch_task_ui(self, task: BatchTask, force: bool = False):
        if task.progress_bar is None or task.status_text is None or task.detail_text is None:
            return

        if not force:
            now = time.monotonic()
            if now - task.last_ui_update < 0.1:
                return
            task.last_ui_update = now

        done = task.processed_count + task.skipped_count
        if task.total_files > 0:
            task.progress_bar.value = min(1.0, done / task.total_files)
        else:
            task.progress_bar.value = None

        status_color = ft.Colors.GREY_700
        card_color = ft.Colors.GREEN_50
        border_color = ft.Colors.GREEN_100

        if task.status == "Running":
            status_color = ft.Colors.BLUE_700
            card_color = ft.Colors.BLUE_50
            border_color = ft.Colors.BLUE_100
        elif task.status == "Paused":
            status_color = ft.Colors.AMBER_800
            card_color = ft.Colors.AMBER_50
            border_color = ft.Colors.AMBER_100
        elif task.status == "Stopping":
            status_color = ft.Colors.RED_700
            card_color = ft.Colors.RED_50
            border_color = ft.Colors.RED_100
        elif task.status == "Done":
            status_color = ft.Colors.GREEN_700
        elif task.status in {"Error", "Cancelled"}:
            status_color = ft.Colors.RED_700
            card_color = ft.Colors.RED_50
            border_color = ft.Colors.RED_100

        task.status_text.value = task.status
        task.status_text.color = status_color

        if task.card is not None:
            task.card.bgcolor = card_color
            task.card.border = ft.border.all(1, border_color)

        current_file = f" | File: {task.current_file}" if task.current_file else ""
        error_text = f" | Error: {task.error}" if task.error else ""
        task.detail_text.value = (
            f"{done}/{task.total_files} anh | OK: {task.processed_count} | Loi: {task.skipped_count}"
            f"{current_file}{error_text}"
        )

        if task.pause_button is not None:
            task.pause_button.disabled = task.status not in {"Queued", "Running"}
        if task.stop_button is not None:
            task.stop_button.disabled = task.status not in {"Queued", "Running", "Paused"}
            task.stop_button.text = "Dang dung han" if task.status == "Stopping" else "Dung han"
        if task.resume_button is not None:
            task.resume_button.disabled = task.status != "Paused"
        if task.delete_button is not None:
            task.delete_button.disabled = task.delete_requested
            task.delete_button.text = "Dang xoa" if task.delete_requested else "Xoa"

        self.refresh_batch_queue_label()
        self.refresh_page()

    def add_batch_task(self, task: BatchTask):
        with self.batch_task_lock:
            self.batch_tasks.insert(0, task)
            card = self.create_batch_task_card(task)
            self.batch_tasks_column.controls.insert(0, card)
            self.refresh_batch_queue_label()
        self.refresh_page()

    def pause_batch_task(self, task_id: int):
        task = self.find_batch_task(task_id)
        if task is None:
            return
        if task.status not in {"Queued", "Running"}:
            return
        task.pause_requested = True
        task.status = "Paused"
        self.update_batch_task_ui(task, force=True)
        self.update_status(f"Da tam dung Task #{task.task_id}.")

    def stop_batch_task(self, task_id: int):
        task = self.find_batch_task(task_id)
        if task is None:
            return
        if task.status not in {"Queued", "Running", "Paused"}:
            return
        task.pause_requested = False
        task.hard_stop_requested = True
        task.status = "Stopping"
        self.update_batch_task_ui(task, force=True)
        self.update_status(f"Dang dung han Task #{task.task_id}.")

    def resume_batch_task(self, task_id: int):
        task = self.find_batch_task(task_id)
        if task is None:
            return
        if task.status != "Paused":
            return
        task.pause_requested = False
        task.status = "Running"
        self.update_batch_task_ui(task, force=True)
        self.update_status(f"Da tiep tuc Task #{task.task_id}.")

    def delete_batch_task(self, task_id: int):
        task = self.find_batch_task(task_id)
        if task is None:
            return
        if task.status in {"Queued", "Running", "Paused", "Stopping"}:
            task.delete_requested = True
            task.pause_requested = False
            task.hard_stop_requested = True
            task.status = "Stopping"
            self.update_batch_task_ui(task, force=True)
            self.update_status(f"Task #{task.task_id} se bi xoa sau khi dung.")
            return
        self.remove_batch_task(task_id)
        self.update_status(f"Da xoa Task #{task_id} khoi danh sach.")
        self.show_snack(f"Da xoa Task #{task_id}.")

    def process_batch_task(self, task: BatchTask):
        if task.hard_stop_requested:
            task.status = "Cancelled"
        else:
            task.status = "Paused" if task.pause_requested else "Running"
        self.update_batch_task_ui(task, force=True)
        if task.status == "Running":
            self.update_status(f"Task #{task.task_id} dang xu ly {task.total_files} anh...")

        files = [
            src for src in task.input_dir.rglob("*")
            if src.suffix.lower() in SUPPORTED_EXTS
        ]

        for src in files:
            while task.pause_requested and not task.hard_stop_requested:
                if task.status != "Paused":
                    task.status = "Paused"
                    self.update_batch_task_ui(task, force=True)
                time.sleep(0.2)

            if task.hard_stop_requested:
                task.status = "Cancelled"
                break

            if task.status != "Running":
                task.status = "Running"
                self.update_batch_task_ui(task, force=True)

            task.current_file = src.name
            img = read_image_bgr(src)

            if img is None:
                task.skipped_count += 1
                if task.error is None:
                    task.error = f"Cannot read image: {src.name}"
                self.update_batch_task_ui(task)
                continue

            try:
                processed = preprocess_cv2(img, task.cfg)
                output_name = f"{src.stem}_preprocessed.png"
                ok = save_image(task.output_dir / output_name, processed)

                if ok:
                    task.processed_count += 1
                else:
                    task.skipped_count += 1
                    if task.error is None:
                        task.error = f"Cannot save image: {src.name}"
            except Exception as exc:
                task.skipped_count += 1
                if task.error is None:
                    task.error = f"{src.name}: {exc}"

            self.update_batch_task_ui(task)

        if task.hard_stop_requested:
            task.status = "Cancelled"
        elif task.error and task.processed_count == 0:
            task.status = "Error"
        else:
            task.status = "Done"

        task.current_file = ""
        self.update_batch_task_ui(task, force=True)

        if task.delete_requested:
            self.remove_batch_task(task.task_id)
            self.update_status(f"Da xoa Task #{task.task_id} khoi danh sach.")
            self.show_snack(f"Da xoa Task #{task.task_id}.")
            return

        summary = (
            f"Task #{task.task_id} xong | OK: {task.processed_count} | Loi: {task.skipped_count}"
        )
        if task.status == "Cancelled":
            summary = (
                f"Task #{task.task_id} da dung | OK: {task.processed_count} | Loi: {task.skipped_count}"
            )
        elif task.error:
            summary += f" | Loi dau tien: {task.error}"

        self.update_status(summary)
        self.show_snack(summary)

    # -----------------------------------------------------
    # Events
    # -----------------------------------------------------

    def on_control_change(self, e):
        self.cfg = self.get_config_from_controls()

        if self.instant_switch.value:
            self.update_preview()

    def apply_preset(self, key: str):
        cfg = PRESETS[key]

        self.cfg = ProcessConfig(**asdict(cfg))

        self.apply_config_to_controls(self.cfg)

        self.update_preview()

        self.update_status(f"Da ap dung Quick Setting: {key}")

    def open_image_dialog(self, e):
        self.file_picker_open.pick_files(
            allow_multiple=False,
            allowed_extensions=[
                "jpg",
                "jpeg",
                "png",
                "bmp",
                "webp",
            ],
        )

    def on_open_file_result(self, e: ft.FilePickerResultEvent):
        if not e.files:
            return

        file_path = Path(e.files[0].path)

        if file_path.suffix.lower() not in SUPPORTED_EXTS:
            self.show_snack("File khong hop le. Hay chon anh jpg/jpeg/png/bmp/webp.")
            return

        img = read_image_bgr(file_path)

        if img is None:
            self.show_snack("Khong doc duoc anh.")
            return

        self.current_path = file_path
        self.original_img = img
        self.processed_img = None

        self.original_preview.src_base64 = cv2_to_base64_png(img)
        self.original_info.value = (
            f"{file_path.name} | "
            f"{img.shape[1]} x {img.shape[0]}"
        )
        self.processed_preview.src_base64 = EMPTY_PREVIEW_BASE64
        self.processed_info.value = "Dang tao preview..."

        if self.header_status_card is not None:
            self.header_status_card.visible = True

        self.set_preview_state(True)
        self.set_active_tab(0)
        self.update_preview()
        self.update_status(f"Da mo anh: {file_path.name}")

    def update_preview(self):
        if self.original_img is None:
            self.set_preview_state(False)
            return

        try:
            self.cfg = self.get_config_from_controls()

            self.processed_img = preprocess_cv2(
                self.original_img,
                self.cfg,
            )

            self.processed_preview.src_base64 = cv2_to_base64_png(
                self.processed_img
            )

            h, w = self.processed_img.shape[:2]

            self.processed_info.value = (
                f"Output {w} x {h} | "
                f"{self.cfg.resize_mode} | "
                f"AC {self.cfg.auto_contrast:.1f} | "
                f"CLAHE {self.cfg.clahe_clip:.1f} | "
                f"Denoise {self.cfg.denoise_method} | "
                f"Sharpen {self.cfg.sharpen_amount:.2f}"
            )
            if self.save_image_button is not None:
                self.save_image_button.disabled = False
            self.set_preview_state(True)

        except Exception as exc:
            self.processed_img = None
            self.processed_preview.src_base64 = EMPTY_PREVIEW_BASE64
            self.processed_info.value = "Chua xu ly."
            if self.save_image_button is not None:
                self.save_image_button.disabled = True
            self.refresh_page()
            self.show_snack(f"Loi xu ly anh: {exc}")

    def open_save_dialog(self, e):
        if self.processed_img is None:
            self.show_snack("Chua co anh processed de luu.")
            return

        default_name = "processed_image.png"

        if self.current_path:
            default_name = f"{self.current_path.stem}_preprocessed.png"

        self.file_picker_save.save_file(
            dialog_title="Luu anh processed",
            file_name=default_name,
            allowed_extensions=[
                "png",
                "jpg",
                "jpeg",
            ],
        )

    def on_save_file_result(self, e: ft.FilePickerResultEvent):
        if not e.path:
            return

        if self.processed_img is None:
            return

        output_path = Path(e.path)

        if output_path.suffix == "":
            output_path = output_path.with_suffix(".png")

        ok = save_image(output_path, self.processed_img)

        if ok:
            self.show_snack(f"Da luu anh: {output_path}")
        else:
            self.show_snack("Khong luu duoc anh.")

    def on_batch_input_result(self, e: ft.FilePickerResultEvent):
        if not e.path:
            return

        self.batch_input_dir = Path(e.path)
        self.batch_input_text.value = f"Input: {self.batch_input_dir}"

        self.update_status(f"Batch input: {self.batch_input_dir}")

    def on_batch_output_result(self, e: ft.FilePickerResultEvent):
        if not e.path:
            return

        self.batch_output_dir = Path(e.path)
        self.batch_output_text.value = f"Output: {self.batch_output_dir}"

        self.update_status(f"Batch output: {self.batch_output_dir}")

    def run_batch(self, e):
        if self.batch_input_dir is None:
            self.show_snack("Hay chon thu muc input truoc.")
            return

        if self.batch_output_dir is None:
            self.show_snack("Hay chon thu muc output truoc.")
            return

        cfg = self.get_config_from_controls()

        input_dir = self.batch_input_dir
        output_dir = self.batch_output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        files = [
            src for src in input_dir.rglob("*")
            if src.suffix.lower() in SUPPORTED_EXTS
        ]

        if not files:
            self.show_snack("Folder input khong co anh hop le.")
            return

        task = BatchTask(
            task_id=self.next_batch_task_id,
            input_dir=input_dir,
            output_dir=output_dir,
            cfg=ProcessConfig(**asdict(cfg)),
            total_files=len(files),
        )
        self.next_batch_task_id += 1

        self.add_batch_task(task)
        self.set_active_tab(1)
        self.update_status(
            f"Da tao Task #{task.task_id} | {task.total_files} anh | preview van hoat dong doc lap."
        )
        self.show_snack(f"Da them Task #{task.task_id} vao batch queue.")
        threading.Thread(
            target=self.process_batch_task,
            args=(task,),
            daemon=True,
        ).start()

    def copy_config(self, e):
        cfg = self.get_config_from_controls()

        text = json.dumps(
            asdict(cfg),
            ensure_ascii=False,
            indent=2,
        )

        self.page.set_clipboard(text)

        self.show_snack("Da copy config JSON vao clipboard.")

    def save_config_json(self, e):
        cfg = self.get_config_from_controls()

        output_path = Path.cwd() / "cow_skin_preprocess_config.json"

        output_path.write_text(
            json.dumps(
                asdict(cfg),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        self.show_snack(f"Da luu config tai: {output_path}")


def main(page: ft.Page):
    app = CowSkinPreprocessApp(page)
    app.setup()


if __name__ == "__main__":
    ft.app(target=main)

