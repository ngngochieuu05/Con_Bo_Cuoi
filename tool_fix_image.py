from __future__ import annotations

import base64
import io
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
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


SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}

GEMINI_RESTORATION_PROMPT = """Use the attached input image as the only source of truth.
Restore and enhance the image according to this JSON specification.
Preserve the original subject identity, anatomical structure, disease/lesion details, texture, and composition.
Do not invent new objects, do not change the lesion meaning, do not remove medically relevant skin marks.
Return only the restored image.

{
  "task_meta": {
    "task_type": "photo_restoration",
    "target_quality": "high_definition_8k",
    "style_preset": "photo_realistic"
  },
  "restoration_requirements": {
    "damage_repair": {
      "actions": ["fill_scratches", "repair_tears", "fix_creases", "remove_dust_spots"],
      "reconstruction_method": "context_aware_infilling",
      "texture_goal": "realistic_material_matching"
    },
    "color_grading": {
      "goal": "restore_natural_vibrancy",
      "lighting": "balance_natural_illumination",
      "tone": "correct_fading_and_discoloration"
    }
  },
  "facial_enhancement": {
    "priority": "identity_preservation",
    "skin_texture": {
      "description": "smooth_but_textured",
      "details": "visible_pores_and_micro_details",
      "avoid": ["plastic_look", "waxy_skin", "oversmoothing"]
    },
    "features": {
      "eyes": "sharpen_and_clarify",
      "structure": "enhance_natural_definition"
    }
  },
  "post_processing": {"color": "auto_contrast"},
  "upscale": {"enabled": true, "factor": 4, "model": "ESRGAN_4x"}
}
"""
PRESET_LABELS: dict[str, str] = {
    "safe": "An toàn",
    "more_clear": "Rõ hơn",
    "dark_image": "Ảnh tối",
    "high_noise": "Nhiễu cao",
    "roboflow_640": "RF 640",
    "yolo_fast_640": "YOLO 640",
    "lesion_detail": "Chi tiết da",
    "restore_photo": "Khôi phục HD",
    "soft_natural": "Tự nhiên",
    "paper_scan": "Ảnh tài liệu",
    "natural": "Reset",
}



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
    preset_key: str = "custom"
    config_label: str = "Custom"
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

    "yolo_fast_640": ProcessConfig(
        enable_resize=True,
        target_size=640,
        resize_mode="Letterbox",
        stride=32,
        pad_color=114,
        gamma=1.0,
        auto_contrast=0.4,
        white_balance=0.10,
        clahe_clip=0.8,
        clahe_tile=8,
        denoise_method="Bilateral",
        bilateral_d=3,
        bilateral_sigma_color=20,
        bilateral_sigma_space=20,
        nlmeans_h=4,
        nlmeans_h_color=4,
        sharpen_amount=0.12,
        sharpen_radius=0.9,
        saturation=1.0,
    ),
    "lesion_detail": ProcessConfig(
        enable_resize=True,
        target_size=1024,
        resize_mode="Letterbox",
        stride=32,
        pad_color=114,
        gamma=0.92,
        auto_contrast=1.2,
        white_balance=0.20,
        clahe_clip=1.8,
        clahe_tile=6,
        denoise_method="Bilateral",
        bilateral_d=5,
        bilateral_sigma_color=28,
        bilateral_sigma_space=28,
        nlmeans_h=5,
        nlmeans_h_color=5,
        sharpen_amount=0.42,
        sharpen_radius=1.1,
        saturation=1.05,
    ),
    "restore_photo": ProcessConfig(
        enable_resize=True,
        target_size=1536,
        resize_mode="Giữ tỷ lệ + phản chiếu",
        stride=32,
        pad_color=114,
        gamma=0.96,
        auto_contrast=0.8,
        white_balance=0.30,
        clahe_clip=1.3,
        clahe_tile=8,
        denoise_method="NLMeans",
        bilateral_d=5,
        bilateral_sigma_color=30,
        bilateral_sigma_space=30,
        nlmeans_h=4,
        nlmeans_h_color=5,
        sharpen_amount=0.28,
        sharpen_radius=1.0,
        saturation=1.08,
    ),
    "soft_natural": ProcessConfig(
        enable_resize=True,
        target_size=1024,
        resize_mode="Giữ tỷ lệ + phản chiếu",
        stride=32,
        pad_color=114,
        gamma=1.0,
        auto_contrast=0.3,
        white_balance=0.20,
        clahe_clip=0.8,
        clahe_tile=10,
        denoise_method="Bilateral",
        bilateral_d=5,
        bilateral_sigma_color=22,
        bilateral_sigma_space=22,
        nlmeans_h=4,
        nlmeans_h_color=4,
        sharpen_amount=0.16,
        sharpen_radius=1.0,
        saturation=1.02,
    ),
    "paper_scan": ProcessConfig(
        enable_resize=True,
        target_size=1536,
        resize_mode="Giữ tỷ lệ + trắng",
        stride=32,
        pad_color=255,
        gamma=0.90,
        auto_contrast=1.5,
        white_balance=0.35,
        clahe_clip=1.2,
        clahe_tile=8,
        denoise_method="Bilateral",
        bilateral_d=3,
        bilateral_sigma_color=18,
        bilateral_sigma_space=18,
        nlmeans_h=3,
        nlmeans_h_color=3,
        sharpen_amount=0.34,
        sharpen_radius=0.9,
        saturation=0.95,
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
        denoise_method="Không",
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

    if mode in {"Stretch", "Kéo giãn"}:
        return cv2.resize(img, (target_size, target_size), interpolation=cv2.INTER_AREA)

    if mode in {"CenterCrop", "Cắt giữa"}:
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
    pad_color = (pad, pad, pad)
    if mode == "Giữ tỷ lệ + đen":
        pad_color = (0, 0, 0)
    elif mode == "Giữ tỷ lệ + trắng":
        pad_color = (255, 255, 255)

    out = resize_keep_ratio_with_padding(
        img,
        target_size=rounded_size,
        enable_resize=True,
        pad_color=pad_color,
    )

    if mode != "Giữ tỷ lệ + phản chiếu":
        return out

    blurred = cv2.resize(img, (rounded_size, rounded_size), interpolation=cv2.INTER_AREA)
    blurred = cv2.GaussianBlur(blurred, (0, 0), 18)
    mask = np.all(out == pad_color, axis=2)
    return np.where(mask[:, :, None], blurred, out).astype(np.uint8)


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


def cv2_to_png_bytes(img_bgr: np.ndarray) -> bytes:
    ok, encoded = cv2.imencode(".png", img_bgr)
    if not ok:
        raise RuntimeError("Không mã hoá được ảnh PNG.")
    return encoded.tobytes()


def bytes_to_bgr_image(raw: bytes) -> Optional[np.ndarray]:
    if not raw:
        return None
    array = np.frombuffer(raw, dtype=np.uint8)
    return cv2.imdecode(array, cv2.IMREAD_COLOR)


def format_gemini_http_error(code: int, detail: str) -> str:
    message = detail.strip()
    status = ""
    try:
        payload = json.loads(detail)
        error = payload.get("error", {})
        message = str(error.get("message") or message)
        status = str(error.get("status") or "")
    except json.JSONDecodeError:
        pass

    if code == 429 and status == "RESOURCE_EXHAUSTED":
        return (
            "Gemini API hết credit/quota billing (HTTP 429 RESOURCE_EXHAUSTED). "
            "Vào AI Studio > Projects > Billing để nạp/thêm credit, hoặc tắt AI On và dùng xử lý local."
        )
    if code == 400:
        return f"Gemini API từ chối request (HTTP 400): {message}"
    if code == 401 or code == 403:
        return f"Gemini API key không hợp lệ hoặc chưa có quyền (HTTP {code}): {message}"
    if code == 404:
        return f"Không tìm thấy Gemini model (HTTP 404). Kiểm tra tên model trong Setting: {message}"
    if code >= 500:
        return f"Gemini API đang lỗi phía server (HTTP {code}), thử lại sau: {message}"
    return f"Gemini API lỗi HTTP {code}: {message}"


def format_openai_http_error(code: int, detail: str) -> str:
    message = detail.strip()
    error_type = ""
    try:
        payload = json.loads(detail)
        error = payload.get("error", {})
        message = str(error.get("message") or message)
        error_type = str(error.get("type") or error.get("code") or "")
    except json.JSONDecodeError:
        pass

    if code == 429:
        return f"OpenAI API hết quota/rate limit (HTTP 429). Kiểm tra billing/quota hoặc thử lại sau: {message}"
    if code == 400:
        return f"OpenAI API từ chối request (HTTP 400): {message}"
    if code == 401 or code == 403:
        return f"OpenAI API key không hợp lệ hoặc chưa có quyền (HTTP {code}): {message}"
    if code == 404:
        return f"Không tìm thấy OpenAI model/endpoint (HTTP 404). Kiểm tra tên model trong Setting: {message}"
    if code >= 500:
        return f"OpenAI API đang lỗi phía server (HTTP {code}), thử lại sau: {message}"
    if error_type:
        return f"OpenAI API lỗi HTTP {code} ({error_type}): {message}"
    return f"OpenAI API lỗi HTTP {code}: {message}"


def build_multipart_form_data(fields: dict[str, str], files: dict[str, tuple[str, str, bytes]]) -> tuple[bytes, str]:
    boundary = f"----CowSkinAI{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        chunks.append(str(value).encode("utf-8"))
        chunks.append(b"\r\n")
    for name, (filename, content_type, data) in files.items():
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode("utf-8")
        )
        chunks.append(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        chunks.append(data)
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


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

    if suffix in {".tif", ".tiff"}:
        suffix = ".png"
        path = path.with_suffix(".png")
    elif suffix not in SUPPORTED_EXTS:
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
        self.active_preset_key = "safe"
        self.ai_api_logs: list[str] = []
        self.app_dir = Path(__file__).resolve().parent
        self.ai_api_log_file = self.app_dir / "ai_api_calls.log"
        self.gemini_request_in_flight = False
        self.gemini_settings_file = self.app_dir / ".gemini_settings.json"

        self.batch_input_dir: Optional[Path] = None
        self.batch_output_dir: Optional[Path] = None
        self.batch_output_manual = False
        self.review_input_dir: Optional[Path] = None
        self.review_output_dir: Optional[Path] = None
        self.review_files: list[Path] = []
        self.review_index = 0
        self.batch_tasks: list[BatchTask] = []
        self.batch_task_lock = threading.Lock()
        self.next_batch_task_id = 1
        self.show_param_help = False
        self.help_text_controls: list[ft.Text] = []
        self.main_tabs: Optional[ft.Tabs] = None
        self.preview_panel_body: Optional[ft.Container] = None
        self.review_tab_content: Optional[ft.Control] = None
        self.preview_placeholder: Optional[ft.Control] = None
        self.preview_workspace: Optional[ft.Control] = None
        self.refresh_preview_button: Optional[ft.OutlinedButton] = None
        self.save_image_button: Optional[ft.OutlinedButton] = None
        self.settings_button: Optional[ft.IconButton] = None
        self.ai_status_badge: Optional[ft.Container] = None
        self.ai_status_text: Optional[ft.Text] = None
        self.batch_config_status_text: Optional[ft.Text] = None

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

        self.file_picker_review_input = ft.FilePicker(
            on_result=self.on_review_input_result,
        )

        self.file_picker_review_output = ft.FilePicker(
            on_result=self.on_review_output_result,
        )

        self.page.overlay.append(self.file_picker_open)
        self.page.overlay.append(self.file_picker_save)
        self.page.overlay.append(self.file_picker_batch_input)
        self.page.overlay.append(self.file_picker_batch_output)
        self.page.overlay.append(self.file_picker_review_input)
        self.page.overlay.append(self.file_picker_review_output)

        self.instant_switch = ft.Switch(
            label="Áp dụng tức thì",
            value=True,
        )

        self.gemini_ai_switch = ft.Switch(
            label="Dùng AI phục hồi ảnh",
            value=False,
        )
        self.ai_provider_dropdown = ft.Dropdown(
            label="Nhà cung cấp AI",
            value="Gemini",
            options=[
                ft.DropdownOption("Gemini"),
                ft.DropdownOption("OpenAI"),
            ],
            on_change=self.on_ai_setting_change,
        )
        self.gemini_api_key_field = ft.TextField(
            label="Gemini API Key",
            password=True,
            can_reveal_password=True,
            hint_text="Dán API key từ Google AI Studio",
        )
        self.gemini_model_field = ft.TextField(
            label="Gemini image model",
            value="gemini-2.5-flash-image",
        )
        self.openai_api_key_field = ft.TextField(
            label="OpenAI API Key",
            password=True,
            can_reveal_password=True,
            hint_text="Dán API key từ OpenAI Platform",
        )
        self.openai_model_field = ft.TextField(
            label="OpenAI image model",
            value="gpt-image-1",
        )
        self.gemini_prompt_field = ft.TextField(
            label="Prompt phục hồi ảnh AI",
            value=GEMINI_RESTORATION_PROMPT,
            multiline=True,
            min_lines=6,
            max_lines=8,
        )

        self.ai_api_log_field = ft.TextField(
            label="Log gọi API ảnh - Rõ hơn",
            value="Chưa có log gọi AI.",
            multiline=True,
            min_lines=6,
            max_lines=8,
            read_only=True,
        )
        self.status_text = ft.Text(
            value="Sẵn sàng.",
            size=12,
            color=ft.Colors.GREY_700,
        )

        self.batch_input_text = ft.Text(
            value="Input: chưa chọn",
            size=12,
            color=ft.Colors.GREY_700,
        )

        self.batch_output_text = ft.Text(
            value="Output: chưa chọn",
            size=12,
            color=ft.Colors.GREY_700,
        )

        self.batch_queue_text = ft.Text(
            value="Chưa có batch task.",
            size=12,
            color=ft.Colors.GREY_700,
        )

        self.review_input_text = ft.Text(
            value="Nguồn: chưa chọn",
            size=12,
            color=ft.Colors.GREY_700,
        )
        self.review_output_text = ft.Text(
            value="Đích: chưa chọn",
            size=12,
            color=ft.Colors.GREY_700,
        )
        self.review_status_text = ft.Text(
            value="Chọn folder nguồn và folder đích để bắt đầu.",
            size=12,
            color=ft.Colors.GREY_700,
        )
        self.review_auto_save = ft.Switch(
            label="Tự lưu khi Next",
            value=True,
        )
        self.review_skip_done = ft.Checkbox(
            label="Bỏ qua ảnh đã có output hợp lệ",
            value=True,
        )
        self.review_scan_button: Optional[ft.FilledButton] = None
        self.review_save_button: Optional[ft.OutlinedButton] = None
        self.review_next_button: Optional[ft.FilledButton] = None
        self.review_prev_button: Optional[ft.IconButton] = None
        self.review_counter_next_button: Optional[ft.IconButton] = None
        self.review_counter_text: Optional[ft.Text] = None
        self.review_toolbar_counter_text: Optional[ft.Text] = None
        self.review_project_text: Optional[ft.Text] = None
        self.review_toolbar_file_text: Optional[ft.Text] = None
        self.review_more_button: Optional[ft.PopupMenuButton] = None
        self.review_train_checkbox: Optional[ft.Checkbox] = None
        self.review_valid_checkbox: Optional[ft.Checkbox] = None
        self.review_test_checkbox: Optional[ft.Checkbox] = None
        self.review_folder_details: Optional[ft.Control] = None
        self.review_intro_card: Optional[ft.Container] = None
        self.review_details_button: Optional[ft.TextButton] = None
        self.show_review_details = True

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
        self.review_original_preview = ft.Image(
            src_base64=EMPTY_PREVIEW_BASE64,
            fit=ft.ImageFit.CONTAIN,
            expand=True,
        )
        self.review_processed_preview = ft.Image(
            src_base64=EMPTY_PREVIEW_BASE64,
            fit=ft.ImageFit.CONTAIN,
            expand=True,
        )

        self.original_info = ft.Text(
            value="Chưa mở ảnh.",
            size=12,
            color=ft.Colors.GREY_700,
        )

        self.processed_info = ft.Text(
            value="Chưa xử lý.",
            size=12,
            color=ft.Colors.GREY_700,
        )

        self.review_original_info = ft.Text(
            value="Chưa chọn ảnh.",
            size=12,
            color=ft.Colors.GREY_700,
        )
        self.review_processed_info = ft.Text(
            value="Chưa xử lý.",
            size=12,
            color=ft.Colors.GREY_700,
        )

        self.enable_resize = ft.Switch(
            label="Resize + padding vuông",
            value=self.cfg.enable_resize,
            on_change=self.on_control_change,
        )

        self.enable_resize_help = self.make_help_text(
            "Bật để đưa ảnh về kích thước vuông cho model. Nếu ảnh gốc nhỏ, upscale có thể làm lộ nhòe."
        )

        self.resize_mode = ft.Dropdown(
            label="Chế độ resize",
            value=self.cfg.resize_mode,
            width=360,
            text_size=14,
            options=[
                ft.DropdownOption("Letterbox"),
                ft.DropdownOption("Giữ tỷ lệ + phản chiếu"),
                ft.DropdownOption("Giữ tỷ lệ + đen"),
                ft.DropdownOption("Giữ tỷ lệ + trắng"),
                ft.DropdownOption("Kéo giãn"),
                ft.DropdownOption("Cắt giữa"),
            ],
            on_change=self.on_control_change,
        )
        self.resize_mode_help = self.make_help_text(
            "Letterbox giữ tỷ lệ + padding chuẩn YOLO/Ultralytics. Phản chiếu giúp preview đỡ viền xám. Kéo giãn có thể làm méo ảnh."
        )

        self.target_size = self.make_slider(
            label="Kích thước đầu ra",
            min_value=512,
            max_value=1536,
            value=self.cfg.target_size,
            step=128,
            help_text="Kích thước ảnh đầu ra. Dùng 640 cho YOLO/RF, 1024-1536 cho khôi phục/preview.",
        )

        self.stride = self.make_slider(
            label="Stride padding | YOLO 32",
            min_value=1,
            max_value=64,
            value=self.cfg.stride,
            step=1,
            help_text="Làm tròn kích thước letterbox theo bội số stride. YOLO thường dùng 32; đặt 1 để tắt làm tròn.",
        )

        self.pad_color = self.make_slider(
            label="Màu padding | YOLO 114",
            min_value=0,
            max_value=255,
            value=self.cfg.pad_color,
            step=1,
            help_text="Màu nền padding khi letterbox. Ultralytics thường dùng xám 114 để model ổn định hơn nền đen/trắng.",
        )

        self.gamma = self.make_slider(
            label="Gamma | <1 sáng hơn",
            min_value=0.5,
            max_value=1.8,
            value=self.cfg.gamma,
            step=0.05,
            help_text="Điều chỉnh độ sáng tổng thể. < 1 làm ảnh sáng hơn, > 1 làm ảnh tối hơn.",
        )

        self.auto_contrast = self.make_slider(
            label="Tự cân tương phản",
            min_value=0.0,
            max_value=3.0,
            value=self.cfg.auto_contrast,
            step=0.1,
            help_text="Kéo lại kênh sáng theo percentile. Tăng quá cao có thể mất chi tiết sáng/tối.",
        )

        self.white_balance = self.make_slider(
            label="Cân bằng trắng",
            min_value=0.0,
            max_value=1.0,
            value=self.cfg.white_balance,
            step=0.05,
            help_text="Giảm lệch màu do ánh sáng chuồng/trời. Nên dùng nhẹ để không sai màu vết bệnh.",
        )

        self.clahe_clip = self.make_slider(
            label="CLAHE Clip | 0 là tắt",
            min_value=0.0,
            max_value=4.0,
            value=self.cfg.clahe_clip,
            step=0.1,
            help_text="Tăng tương phản cục bộ để lộ rõ đốm/vết. Quá cao sẽ gắt, nổi hạt và nhìn giả.",
        )

        self.clahe_tile = self.make_slider(
            label="Ô CLAHE",
            min_value=2,
            max_value=16,
            value=self.cfg.clahe_tile,
            step=1,
            help_text="Kích thước ô khi CLAHE chia ảnh. Ô nhỏ tác động mạnh hơn, ô lớn mềm hơn.",
        )

        self.denoise_method = ft.Dropdown(
            label="Khử nhiễu",
            value=self.cfg.denoise_method,
            width=360,
            text_size=14,
            options=[
                ft.DropdownOption("Không"),
                ft.DropdownOption("Bilateral"),
                ft.DropdownOption("NLMeans"),
            ],
            on_change=self.on_control_change,
        )
        self.denoise_method_help = self.make_help_text(
            "Không giữ nguyên chi tiết. Bilateral giữ biên tốt, hợp ảnh da. NLMeans khử nhiễu mạnh hơn nhưng dễ làm mềm ảnh."
        )

        self.bilateral_d = self.make_slider(
            label="Bilateral d | nên 3-7",
            min_value=0,
            max_value=15,
            value=self.cfg.bilateral_d,
            step=1,
            help_text="Kích thước vùng lọc Bilateral. Tăng lên sẽ mịn hơn nhưng dễ mất chi tiết nhỏ.",
        )

        self.bilateral_sigma_color = self.make_slider(
            label="Bilateral sigma màu",
            min_value=0,
            max_value=100,
            value=self.cfg.bilateral_sigma_color,
            step=5,
            help_text="Mức độ trộn theo khác biệt màu. Cao hơn sẽ hòa trộn các điểm/hạt có màu gần nhau.",
        )

        self.bilateral_sigma_space = self.make_slider(
            label="Bilateral sigma vùng",
            min_value=0,
            max_value=100,
            value=self.cfg.bilateral_sigma_space,
            step=5,
            help_text="Phạm vi không gian của Bilateral. Cao hơn sẽ tác động lên vùng rộng hơn quanh mỗi điểm ảnh.",
        )

        self.nlmeans_h = self.make_slider(
            label="NLMeans h | nên 3-8",
            min_value=0,
            max_value=20,
            value=self.cfg.nlmeans_h,
            step=1,
            help_text="Độ mạnh khử nhiễu của NLMeans trên kênh sáng. Cao quá sẽ làm mất texture và nhìn bẹt.",
        )

        self.nlmeans_h_color = self.make_slider(
            label="NLMeans hColor | nên 3-8",
            min_value=0,
            max_value=20,
            value=self.cfg.nlmeans_h_color,
            step=1,
            help_text="Độ mạnh khử nhiễu trên kênh màu. Tăng cao để giảm loang màu, nhưng có thể làm da bị bẹt mặt.",
        )

        self.sharpen_amount = self.make_slider(
            label="Sharpen Amount | nên 0.10-0.30",
            min_value=0.0,
            max_value=1.0,
            value=self.cfg.sharpen_amount,
            step=0.05,
            help_text="Độ mạnh làm rõ biên và texture. Quá cao sẽ tạo viền trắng/đen và làm ảnh nhìn giả.",
        )

        self.sharpen_radius = self.make_slider(
            label="Bán kính làm nét",
            min_value=0.3,
            max_value=3.0,
            value=self.cfg.sharpen_radius,
            step=0.1,
            help_text="Bán kính blur dùng trong sharpen. Radius nhỏ đánh vào chi tiết mịn, radius lớn đánh vào biên lớn hơn.",
        )

        self.saturation = self.make_slider(
            label="Độ bão hòa | 1.0 giữ nguyên",
            min_value=0.5,
            max_value=1.5,
            value=self.cfg.saturation,
            step=0.05,
            help_text="Độ đậm màu. Để gần 1.0 cho ảnh phân tích; tăng quá cao dễ làm màu sai và nhiễu hơn.",
        )

    # -----------------------------------------------------
    # UI setup
    # -----------------------------------------------------

    def load_gemini_settings(self):
        if not self.gemini_settings_file.exists():
            return
        try:
            data = json.loads(self.gemini_settings_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        self.gemini_ai_switch.value = bool(data.get("enabled", self.gemini_ai_switch.value))
        self.ai_provider_dropdown.value = str(data.get("provider", self.ai_provider_dropdown.value or "Gemini"))
        if self.ai_provider_dropdown.value not in {"Gemini", "OpenAI"}:
            self.ai_provider_dropdown.value = "Gemini"
        self.gemini_api_key_field.value = str(data.get("api_key", data.get("gemini_api_key", "")))
        self.openai_api_key_field.value = str(data.get("openai_api_key", ""))
        saved_model = str(data.get("model", data.get("gemini_model", self.gemini_model_field.value or "gemini-2.5-flash-image")))
        if saved_model == "gemini-2.5-flash-image-preview":
            saved_model = "gemini-2.5-flash-image"
        self.gemini_model_field.value = saved_model
        self.openai_model_field.value = str(data.get("openai_model", self.openai_model_field.value or "gpt-image-1"))
        self.gemini_prompt_field.value = str(
            data.get("prompt", self.gemini_prompt_field.value or GEMINI_RESTORATION_PROMPT)
        )
        self.update_ai_status_badge()

    def save_gemini_settings(self):
        data = {
            "enabled": bool(self.gemini_ai_switch.value),
            "provider": str(self.ai_provider_dropdown.value or "Gemini"),
            "api_key": str(self.gemini_api_key_field.value or ""),
            "gemini_api_key": str(self.gemini_api_key_field.value or ""),
            "model": str(self.gemini_model_field.value or ""),
            "gemini_model": str(self.gemini_model_field.value or ""),
            "openai_api_key": str(self.openai_api_key_field.value or ""),
            "openai_model": str(self.openai_model_field.value or ""),
            "prompt": str(self.gemini_prompt_field.value or ""),
        }
        self.gemini_settings_file.parent.mkdir(parents=True, exist_ok=True)
        self.gemini_settings_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.update_ai_status_badge()

    def close_settings_dialog(self, dialog):
        self.save_gemini_settings()
        self.page.close(dialog)
        self.show_snack("Đã lưu cấu hình Gemini.")

    def setup(self):
        self.page.title = "Cow Skin Lesion Preprocess Tool"

        self.page.padding = 16
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.theme = ft.Theme(
            color_scheme_seed=ft.Colors.GREEN,
        )

        # Flet 0.28.x: dùng page.window.*, không dùng page.window_width.
        try:
            self.page.window.width = 1450
            self.page.window.height = 900
            self.page.window.min_width = 1180
            self.page.window.min_height = 720
        except Exception:
            pass

        self.load_gemini_settings()

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
            "Đã khởi động. Mở ảnh rồi chọn Quick Setting hoặc chỉnh slider."
        )

    def build_header(self) -> ft.Control:
        self.save_image_button = ft.OutlinedButton(
            text="Lưu ảnh",
            icon=ft.Icons.SAVE,
            disabled=True,
            on_click=self.open_save_dialog,
        )
        self.settings_button = ft.IconButton(
            icon=ft.Icons.SETTINGS,
            tooltip="Cài đặt",
            icon_color=ft.Colors.GREEN_800,
            on_click=self.open_settings_dialog,
        )
        self.ai_status_text = ft.Text("AI Off", size=12, weight=ft.FontWeight.BOLD)
        self.ai_status_badge = ft.Container(
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=999,
            bgcolor=ft.Colors.GREY_200,
            border=ft.border.all(1, ft.Colors.GREY_300),
            content=self.ai_status_text,
        )
        self.update_ai_status_badge()
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
                        "Trạng thái",
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
                        ],
                    ),
                    self.header_status_card,
                    ft.FilledButton(
                        text="Mở ảnh",
                        icon=ft.Icons.FOLDER_OPEN,
                        on_click=self.open_image_dialog,
                    ),
                    self.save_image_button,
                    self.ai_status_badge,
                    self.settings_button,
                ],
            ),
        )

    def open_settings_dialog(self, e=None):
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Cài đặt xử lý ảnh", size=22, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                width=760,
                height=620,
                content=ft.Column(
                    scroll=ft.ScrollMode.AUTO,
                    spacing=14,
                    controls=[
                        ft.Container(
                            padding=14,
                            border_radius=14,
                            bgcolor=ft.Colors.GREEN_50,
                            border=ft.border.all(1, ft.Colors.GREEN_100),
                            content=ft.Column(
                                tight=True,
                                spacing=8,
                                controls=[
                                    ft.Text("Cấu hình chung", size=16, weight=ft.FontWeight.BOLD),
                                    self.instant_switch,
                                    ft.Text(
                                        "Bật để tự cập nhật preview khi thay đổi thanh trượt/preset.",
                                        size=12,
                                        color=ft.Colors.GREY_700,
                                    ),
                                ],
                            ),
                        ),
                        ft.Container(
                            padding=14,
                            border_radius=14,
                            bgcolor=ft.Colors.BLUE_50,
                            border=ft.border.all(1, ft.Colors.BLUE_100),
                            content=ft.Column(
                                tight=True,
                                spacing=12,
                                controls=[
                                    ft.Row(
                                        controls=[
                                            ft.Icon(ft.Icons.AUTO_FIX_HIGH, color=ft.Colors.BLUE_700),
                                            ft.Text("Cấu hình AI phục hồi ảnh", size=16, weight=ft.FontWeight.BOLD),
                                        ],
                                    ),
                                    self.gemini_ai_switch,
                                    self.ai_provider_dropdown,
                                    ft.Text("Gemini", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800),
                                    ft.Row(
                                        controls=[
                                            ft.Container(expand=True, content=self.gemini_api_key_field),
                                            ft.Container(expand=True, content=self.gemini_model_field),
                                        ],
                                    ),
                                    ft.Text("OpenAI / ChatGPT", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_800),
                                    ft.Row(
                                        controls=[
                                            ft.Container(expand=True, content=self.openai_api_key_field),
                                            ft.Container(expand=True, content=self.openai_model_field),
                                        ],
                                    ),
                                    ft.Container(
                                        height=220,
                                        content=self.gemini_prompt_field,
                                    ),
                                    ft.Text(
                                        "AI chỉ chạy với Quick Setting Rõ hơn. Chọn Gemini hoặc OpenAI, nhập API key tương ứng rồi Lưu cấu hình.",
                                        size=12,
                                        color=ft.Colors.GREY_700,
                                    ),
                                    self.ai_api_log_field,
                                ],
                            ),
                        ),
                    ],
                ),
            ),
            actions=[
                ft.TextButton("Đóng", on_click=lambda event: self.close_settings_dialog(dialog)),
                ft.FilledButton("Lưu cấu hình", on_click=lambda event: self.close_settings_dialog(dialog)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            inset_padding=ft.padding.symmetric(horizontal=40, vertical=24),
        )
        self.page.open(dialog)

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
                        "Bấm preset để thiết lập thông số tức thì.",
                        size=12,
                        color=ft.Colors.GREY_700,
                    ),
                    ft.Row(
                        wrap=True,
                        spacing=8,
                        run_spacing=8,
                        controls=[
                            ft.FilledTonalButton(
                                text="An toàn",
                                icon=ft.Icons.CHECK_CIRCLE,
                                on_click=lambda e: self.apply_preset("safe"),
                            ),
                            ft.FilledTonalButton(
                                text="Rõ hơn",
                                icon=ft.Icons.AUTO_FIX_HIGH,
                                on_click=lambda e: self.apply_preset("more_clear"),
                            ),
                            ft.FilledTonalButton(
                                text="Ảnh tối",
                                icon=ft.Icons.WB_SUNNY,
                                on_click=lambda e: self.apply_preset("dark_image"),
                            ),
                            ft.FilledTonalButton(
                                text="Nhiễu cao",
                                icon=ft.Icons.GRAIN,
                                on_click=lambda e: self.apply_preset("high_noise"),
                            ),
                            ft.FilledTonalButton(
                                text="RF 640",
                                icon=ft.Icons.CROP,
                                on_click=lambda e: self.apply_preset("roboflow_640"),
                            ),
                            ft.FilledTonalButton(
                                text="YOLO 640",
                                icon=ft.Icons.SPEED,
                                on_click=lambda e: self.apply_preset("yolo_fast_640"),
                            ),
                            ft.FilledTonalButton(
                                text="Chi tiết da",
                                icon=ft.Icons.TEXTURE,
                                on_click=lambda e: self.apply_preset("lesion_detail"),
                            ),
                            ft.FilledTonalButton(
                                text="Khôi phục HD",
                                icon=ft.Icons.HIGH_QUALITY,
                                on_click=lambda e: self.apply_preset("restore_photo"),
                            ),
                            ft.FilledTonalButton(
                                text="Tự nhiên",
                                icon=ft.Icons.TUNE,
                                on_click=lambda e: self.apply_preset("soft_natural"),
                            ),
                            ft.FilledTonalButton(
                                text="Ảnh tài liệu",
                                icon=ft.Icons.DOCUMENT_SCANNER,
                                on_click=lambda e: self.apply_preset("paper_scan"),
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
                                text="Lưu config",
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
                controls_padding=ft.padding.only(top=12, bottom=8),
                title=ft.Text(
                    "Thông số xử lý",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                ),
                subtitle=ft.Text(
                    "Ẩn/hiện panel tham số để tập trung vào preview.",
                    size=12,
                    color=ft.Colors.GREY_700,
                ),
                controls=[
                    ft.TextButton(
                        text="Hiện chú thích" if not self.show_param_help else "Ẩn chú thích",
                        icon=ft.Icons.HELP_OUTLINE,
                        on_click=self.toggle_param_help,
                    ),
                    self.enable_resize,
                    self.enable_resize_help,
                    self.spaced_dropdown(self.resize_mode),
                    self.resize_mode_help,
                    self.target_size,
                    self.stride,
                    self.pad_color,
                    self.gamma,
                    self.auto_contrast,
                    self.white_balance,
                    self.clahe_clip,
                    self.clahe_tile,
                    self.spaced_dropdown(self.denoise_method),
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
                            "Mẹo: nếu lông bị gai hoặc da nhìn giả, giảm CLAHE Clip và Sharpen Amount.",
                            size=12,
                            color=ft.Colors.BROWN_700,
                        ),
                    ),
                ],
            ),
        )

    def build_batch_controls(self) -> ft.Control:
        self.batch_config_status_text = ft.Text(
            self.get_config_display_name(),
            size=16,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.GREEN_900,
        )
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
                                "Batch xử lý thư mục",
                                size=18,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ],
                    ),
                    ft.Text(
                        "Dùng thông số hiện tại để xử lý toàn bộ ảnh trong một thư mục.",
                        size=12,
                        color=ft.Colors.GREY_700,
                    ),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(
                                width=560,
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
                            ft.Column(
                                width=140,
                                spacing=8,
                                controls=[
                                    ft.OutlinedButton(
                                        text="Mở nguồn",
                                        icon=ft.Icons.FOLDER_OPEN,
                                        on_click=self.open_batch_input_folder,
                                    ),
                                    ft.OutlinedButton(
                                        text="Mở đích",
                                        icon=ft.Icons.FOLDER_SPECIAL,
                                        on_click=self.open_batch_output_folder,
                                    ),
                                ],
                            ),
                            ft.Container(
                                width=300,
                                padding=12,
                                border_radius=12,
                                bgcolor=ft.Colors.ORANGE_50,
                                border=ft.border.all(1, ft.Colors.ORANGE_100),
                                content=ft.Column(
                                    spacing=4,
                                    controls=[
                                        ft.Text(
                                            "Cấu hình đang dùng",
                                            size=12,
                                            weight=ft.FontWeight.BOLD,
                                            color=ft.Colors.ORANGE_900,
                                        ),
                                        self.batch_config_status_text,
                                    ],
                                ),
                            ),
                        ],
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
                                "Danh sách tiến trình",
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
                    text="Preview Config",
                    icon=ft.Icons.IMAGE_OUTLINED,
                    content=self.build_workbench_tab(),
                ),
                ft.Tab(
                    text="Xử lý ảnh",
                    icon=ft.Icons.FOLDER_OPEN,
                    content=self.build_review_tab(),
                ),
                ft.Tab(
                    text="Tiến trình",
                    icon=ft.Icons.PENDING_ACTIONS,
                    content=self.build_processes_tab(),
                ),
            ],
        )
        self.preview_panel_body = ft.Container(
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
        return self.preview_panel_body

    def build_workbench_tab(self) -> ft.Control:
        self.refresh_preview_button = ft.OutlinedButton(
            text="Cập nhật preview",
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
                            title="Ảnh gốc",
                            image=self.original_preview,
                            info=self.original_info,
                        ),
                        self.preview_card(
                            title="Ảnh đã xử lý",
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

    def build_review_tab(self) -> ft.Control:
        self.review_prev_button = ft.IconButton(
            icon=ft.Icons.CHEVRON_LEFT,
            icon_size=22,
            disabled=True,
            on_click=self.prev_review_image,
        )
        self.review_next_button = ft.FilledButton(
            text="Next",
            icon=ft.Icons.CHEVRON_RIGHT,
            disabled=True,
            on_click=self.next_review_image,
        )
        self.review_counter_text = ft.Text(
            value="0 / 0",
            size=14,
            weight=ft.FontWeight.W_600,
            text_align=ft.TextAlign.CENTER,
        )
        self.review_toolbar_counter_text = ft.Text(
            value="0 / 0",
            size=16,
            weight=ft.FontWeight.W_600,
            text_align=ft.TextAlign.CENTER,
        )
        self.review_project_text = ft.Text(
            value="CHƯA CHỌN NGUỒN",
            size=11,
            color=ft.Colors.GREY_600,
            weight=ft.FontWeight.W_600,
        )
        self.review_toolbar_file_text = ft.Text(
            value="Chưa chọn ảnh",
            size=14,
            weight=ft.FontWeight.W_600,
            color=ft.Colors.GREY_800,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self.review_counter_next_button = ft.IconButton(
            icon=ft.Icons.CHEVRON_RIGHT,
            icon_size=22,
            disabled=True,
            on_click=self.next_review_image,
        )
        self.review_save_button = ft.OutlinedButton(
            text="Lưu tay",
            icon=ft.Icons.SAVE,
            disabled=True,
            on_click=self.save_review_current,
        )
        self.review_train_checkbox = ft.Checkbox(
            label="Train",
            value=True,
            data="train",
            active_color=ft.Colors.RED_600,
            check_color=ft.Colors.WHITE,
            shape=ft.CircleBorder(),
            visible=False,
            label_style=ft.TextStyle(color=ft.Colors.RED_700, weight=ft.FontWeight.BOLD),
            on_change=self.on_review_split_change,
        )
        self.review_valid_checkbox = ft.Checkbox(
            label="Valid",
            value=False,
            data="valid",
            active_color=ft.Colors.BLUE_600,
            check_color=ft.Colors.WHITE,
            shape=ft.CircleBorder(),
            visible=False,
            label_style=ft.TextStyle(color=ft.Colors.BLUE_700, weight=ft.FontWeight.BOLD),
            on_change=self.on_review_split_change,
        )
        self.review_test_checkbox = ft.Checkbox(
            label="Test",
            value=False,
            data="test",
            active_color=ft.Colors.ORANGE_600,
            check_color=ft.Colors.WHITE,
            shape=ft.CircleBorder(),
            visible=False,
            label_style=ft.TextStyle(color=ft.Colors.ORANGE_700, weight=ft.FontWeight.BOLD),
            on_change=self.on_review_split_change,
        )
        self.review_more_button = ft.PopupMenuButton(
            icon=ft.Icons.MORE_HORIZ,
            tooltip="Tác vụ ảnh",
            disabled=True,
            items=[
                ft.PopupMenuItem(
                    text="Copy image",
                    icon=ft.Icons.CONTENT_COPY,
                    on_click=self.copy_review_image,
                ),
                ft.PopupMenuItem(
                    text="Save as image",
                    icon=ft.Icons.SAVE_AS,
                    on_click=self.open_save_dialog,
                ),
                ft.PopupMenuItem(),
                ft.PopupMenuItem(
                    text="Remove from Project",
                    icon=ft.Icons.DELETE_OUTLINE,
                    on_click=self.remove_review_current,
                ),
            ],
        )
        self.review_scan_button = ft.FilledButton(
            text="Quét ảnh chưa xử lý",
            icon=ft.Icons.SEARCH,
            disabled=True,
            style=ft.ButtonStyle(
                bgcolor={
                    ft.ControlState.DEFAULT: ft.Colors.RED_600,
                    ft.ControlState.HOVERED: ft.Colors.RED_700,
                    ft.ControlState.DISABLED: ft.Colors.GREY_300,
                },
                color={
                    ft.ControlState.DEFAULT: ft.Colors.WHITE,
                    ft.ControlState.DISABLED: ft.Colors.GREY_600,
                },
            ),
            on_click=self.scan_review_folder,
        )
        self.review_details_button = ft.TextButton(
            text="Ẩn chi tiết nguồn/đích",
            icon=ft.Icons.EXPAND_LESS,
            on_click=self.toggle_review_details,
        )
        self.review_folder_details = ft.Container(
            visible=self.show_review_details,
            padding=ft.padding.symmetric(horizontal=14, vertical=12),
            border_radius=14,
            bgcolor=ft.Colors.BLUE_GREY_50,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=12, vertical=10),
                        border_radius=12,
                        bgcolor=ft.Colors.WHITE,
                        border=ft.border.all(1, ft.Colors.GREY_200),
                        content=ft.Column(
                            spacing=8,
                            controls=[
                                self.review_input_text,
                                self.review_output_text,
                            ],
                        ),
                    ),
                    ft.Row(
                        controls=[
                            ft.OutlinedButton(
                                text="Chọn folder nguồn",
                                icon=ft.Icons.FOLDER_OPEN,
                                expand=True,
                                on_click=lambda e: self.file_picker_review_input.get_directory_path(),
                            ),
                            ft.OutlinedButton(
                                text="Chọn folder đích",
                                icon=ft.Icons.CREATE_NEW_FOLDER,
                                expand=True,
                                on_click=lambda e: self.file_picker_review_output.get_directory_path(),
                            ),
                        ],
                    ),
                    ft.Row(
                        controls=[
                            self.review_scan_button,
                            self.review_auto_save,
                            self.review_skip_done,
                        ],
                    ),
                ],
            ),
        )
        self.review_intro_card = ft.Container(
            padding=16,
            border_radius=16,
            bgcolor=ft.Colors.GREEN_50,
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.IMAGE_SEARCH, color=ft.Colors.GREEN_700),
                            ft.Text("Duyệt và xử lý từng ảnh", size=20, weight=ft.FontWeight.BOLD),
                            ft.Container(expand=True),
                            self.review_details_button,
                        ],
                    ),
                    ft.Text(
                        "Chỉnh cấu hình cho từng ảnh ở panel trái, rồi Lưu tay hoặc Next theo chế độ tự lưu.",
                        size=12,
                        color=ft.Colors.GREY_700,
                    ),
                ],
            ),
        )
        self.review_tab_content = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=12,
            controls=[
                self.review_intro_card,
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=14, vertical=10),
                    border_radius=18,
                    bgcolor=ft.Colors.WHITE,
                    border=ft.border.all(1, ft.Colors.GREY_200),
                    content=ft.Column(
                        spacing=10,
                        controls=[
                            ft.Row(
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.IconButton(
                                        icon=ft.Icons.ARROW_BACK,
                                        tooltip="Quay lại thiết lập folder",
                                        on_click=self.show_review_setup,
                                    ),
                                    ft.Column(
                                        spacing=0,
                                        expand=True,
                                        controls=[
                                            ft.Row(
                                                spacing=6,
                                                controls=[
                                                    self.review_project_text,
                                                    ft.Icon(ft.Icons.CHEVRON_RIGHT, size=14, color=ft.Colors.GREY_500),
                                                    ft.Text("XỬ LÝ ẢNH", size=11, color=ft.Colors.GREEN_700, weight=ft.FontWeight.BOLD),
                                                ],
                                            ),
                                            self.review_toolbar_file_text,
                                        ],
                                    ),
                                    ft.Column(
                                        spacing=2,
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                        controls=[
                                            ft.Container(
                                                width=210,
                                                padding=ft.padding.symmetric(horizontal=8, vertical=2),
                                                border_radius=28,
                                                bgcolor=ft.Colors.GREY_50,
                                                border=ft.border.all(1, ft.Colors.GREY_200),
                                                content=ft.Row(
                                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                                    controls=[
                                                        self.review_prev_button,
                                                        self.review_toolbar_counter_text,
                                                        self.review_counter_next_button,
                                                    ],
                                                ),
                                            ),
                                            ft.Row(
                                                spacing=4,
                                                alignment=ft.MainAxisAlignment.CENTER,
                                                controls=[
                                                    self.review_train_checkbox,
                                                    self.review_valid_checkbox,
                                                    self.review_test_checkbox,
                                                ],
                                            ),
                                        ],
                                    ),
                                    self.review_next_button,
                                    self.review_more_button,
                                ],
                            ),
                            self.review_status_text,
                            self.review_folder_details,
                        ],
                    ),
                ),
                ft.Row(
                    expand=True,
                    controls=[
                        self.preview_card(
                            title="Ảnh nguồn",
                            image=self.review_original_preview,
                            info=self.review_original_info,
                        ),
                        self.preview_card(
                            title="Ảnh sau xử lý",
                            image=self.review_processed_preview,
                            info=self.review_processed_info,
                        ),
                    ],
                ),
            ],
        )
        return self.review_tab_content

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
                                "Hàng đợi xử lý",
                                size=20,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                "Theo dõi task đang chạy, tạm dừng, dừng hẳn, tiếp tục hoặc xóa tiến trình.",
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
                        "Chưa có preview",
                        size=22,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Text(
                        'Nhan "Mở ảnh" de hien Preview Before / After.',
                        size=13,
                        color=ft.Colors.GREY_700,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.FilledButton(
                        text="Mở ảnh",
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
                    info,
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
                ],
            ),
        )

    @staticmethod
    def spaced_dropdown(control: ft.Control) -> ft.Control:
        return ft.Container(
            padding=ft.padding.only(top=14, bottom=14),
            content=control,
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
        e.control.text = "Ẩn chú thích" if self.show_param_help else "Hiện chú thích"
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

    def append_ai_api_log(self, message: str):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {message}"
        print(line, flush=True)
        self.ai_api_logs.append(line)
        self.ai_api_logs = self.ai_api_logs[-120:]
        if hasattr(self, "ai_api_log_field") and self.ai_api_log_field is not None:
            self.ai_api_log_field.value = "\n".join(self.ai_api_logs[-40:])
        try:
            with self.ai_api_log_file.open("a", encoding="utf-8") as log_file:
                log_file.write(line + "\n")
        except OSError:
            pass
        try:
            self.refresh_page()
        except Exception:
            pass

    def get_ai_provider(self) -> str:
        provider = str(self.ai_provider_dropdown.value or "Gemini")
        return provider if provider in {"Gemini", "OpenAI"} else "Gemini"

    def should_use_gemini_ai(self) -> bool:
        provider = self.get_ai_provider()
        api_key = self.gemini_api_key_field.value if provider == "Gemini" else self.openai_api_key_field.value
        return bool(
            self.active_preset_key == "more_clear"
            and self.gemini_ai_switch.value
            and str(api_key or "").strip()
        )

    def enhance_with_ai(self, img_bgr: np.ndarray) -> np.ndarray:
        if self.get_ai_provider() == "OpenAI":
            return self.enhance_with_openai(img_bgr)
        return self.enhance_with_gemini(img_bgr)

    def enhance_with_gemini(self, img_bgr: np.ndarray) -> np.ndarray:
        if self.gemini_request_in_flight:
            raise RuntimeError("Gemini đang xử lý request trước đó, vui lòng chờ hoàn tất.")
        self.gemini_request_in_flight = True
        start_time = time.perf_counter()
        try:
            api_key = str(self.gemini_api_key_field.value or "").strip()
            model = str(self.gemini_model_field.value or "gemini-2.5-flash-image").strip()
            prompt = str(self.gemini_prompt_field.value or GEMINI_RESTORATION_PROMPT).strip()
            if not api_key:
                raise RuntimeError("Chưa nhập Gemini API key.")
            if not model:
                raise RuntimeError("Chưa nhập Gemini image model.")
            if not prompt:
                raise RuntimeError("Chưa nhập prompt Gemini.")

            h, w = img_bgr.shape[:2]
            self.append_ai_api_log(
                f"START Rõ hơn Gemini | model={model} | input={w}x{h} | prompt_chars={len(prompt)}"
            )
            image_bytes = cv2_to_png_bytes(img_bgr)
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            self.append_ai_api_log(
                f"REQUEST image/png bytes={len(image_bytes)} | base64_chars={len(image_b64)} | api_key=***{api_key[-4:] if len(api_key) >= 4 else '****'}"
            )
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": "image/png",
                                    "data": image_b64,
                                }
                            },
                        ]
                    }
                ],
                "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
            }
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            safe_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key=***"
            self.append_ai_api_log(f"POST {safe_url}")
            request = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                self.append_ai_api_log("WAITING Gemini response...")
                with urllib.request.urlopen(request, timeout=120) as response:
                    raw_response = response.read()
                    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                    self.append_ai_api_log(
                        f"RESPONSE HTTP {response.status} | bytes={len(raw_response)} | elapsed_ms={elapsed_ms}"
                    )
                    response_payload = json.loads(raw_response.decode("utf-8"))
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="ignore")[:1000]
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                friendly_error = format_gemini_http_error(exc.code, detail)
                self.append_ai_api_log(f"ERROR HTTP {exc.code} | elapsed_ms={elapsed_ms} | detail={detail}")
                self.append_ai_api_log(f"ERROR FRIENDLY | {friendly_error}")
                raise RuntimeError(friendly_error) from exc
            except urllib.error.URLError as exc:
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                self.append_ai_api_log(f"ERROR NETWORK | elapsed_ms={elapsed_ms} | reason={exc.reason}")
                raise RuntimeError(f"Không kết nối được Gemini API: {exc.reason}") from exc

            candidates = response_payload.get("candidates", [])
            self.append_ai_api_log(f"PARSE candidates={len(candidates)}")
            for candidate in candidates:
                content = candidate.get("content", {})
                for part in content.get("parts", []):
                    if "text" in part:
                        self.append_ai_api_log(f"TEXT part={str(part.get('text', ''))[:240]}")
                    inline_data = part.get("inline_data") or part.get("inlineData")
                    if not inline_data:
                        continue
                    data = inline_data.get("data")
                    if not data:
                        continue
                    result_bytes = base64.b64decode(data)
                    self.append_ai_api_log(
                        f"IMAGE part mime={inline_data.get('mime_type') or inline_data.get('mimeType')} | bytes={len(result_bytes)}"
                    )
                    result = bytes_to_bgr_image(result_bytes)
                    if result is not None:
                        out_h, out_w = result.shape[:2]
                        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                        self.append_ai_api_log(f"DONE output={out_w}x{out_h} | elapsed_ms={elapsed_ms}")
                        return result
            finish_reason = candidates[0].get("finishReason") if candidates else "NO_CANDIDATES"
            self.append_ai_api_log(f"ERROR Gemini không trả về ảnh kết quả | finish_reason={finish_reason}")
            raise RuntimeError("Gemini không trả về ảnh kết quả.")
        finally:
            self.gemini_request_in_flight = False

    def enhance_with_openai(self, img_bgr: np.ndarray) -> np.ndarray:
        if self.gemini_request_in_flight:
            raise RuntimeError("AI đang xử lý request trước đó, vui lòng chờ hoàn tất.")
        self.gemini_request_in_flight = True
        start_time = time.perf_counter()
        try:
            api_key = str(self.openai_api_key_field.value or "").strip()
            model = str(self.openai_model_field.value or "gpt-image-1").strip()
            prompt = str(self.gemini_prompt_field.value or GEMINI_RESTORATION_PROMPT).strip()
            if not api_key:
                raise RuntimeError("Chưa nhập OpenAI API key.")
            if not model:
                raise RuntimeError("Chưa nhập OpenAI image model.")
            if not prompt:
                raise RuntimeError("Chưa nhập prompt AI.")

            h, w = img_bgr.shape[:2]
            self.append_ai_api_log(
                f"START Rõ hơn OpenAI | model={model} | input={w}x{h} | prompt_chars={len(prompt)}"
            )
            image_bytes = cv2_to_png_bytes(img_bgr)
            self.append_ai_api_log(
                f"REQUEST image/png bytes={len(image_bytes)} | api_key=***{api_key[-4:] if len(api_key) >= 4 else '****'}"
            )
            body, content_type = build_multipart_form_data(
                fields={
                    "model": model,
                    "prompt": prompt,
                },
                files={
                    "image": ("input.png", "image/png", image_bytes),
                },
            )
            url = "https://api.openai.com/v1/images/edits"
            self.append_ai_api_log("POST https://api.openai.com/v1/images/edits")
            request = urllib.request.Request(
                url,
                data=body,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": content_type,
                },
                method="POST",
            )
            try:
                self.append_ai_api_log("WAITING OpenAI response...")
                with urllib.request.urlopen(request, timeout=180) as response:
                    raw_response = response.read()
                    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                    self.append_ai_api_log(
                        f"RESPONSE HTTP {response.status} | bytes={len(raw_response)} | elapsed_ms={elapsed_ms}"
                    )
                    response_payload = json.loads(raw_response.decode("utf-8"))
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="ignore")[:1000]
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                friendly_error = format_openai_http_error(exc.code, detail)
                self.append_ai_api_log(f"ERROR HTTP {exc.code} | elapsed_ms={elapsed_ms} | detail={detail}")
                self.append_ai_api_log(f"ERROR FRIENDLY | {friendly_error}")
                raise RuntimeError(friendly_error) from exc
            except urllib.error.URLError as exc:
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                self.append_ai_api_log(f"ERROR NETWORK | elapsed_ms={elapsed_ms} | reason={exc.reason}")
                raise RuntimeError(f"Không kết nối được OpenAI API: {exc.reason}") from exc

            items = response_payload.get("data", [])
            self.append_ai_api_log(f"PARSE OpenAI data={len(items)}")
            for item in items:
                image_b64 = item.get("b64_json")
                if image_b64:
                    result_bytes = base64.b64decode(image_b64)
                    self.append_ai_api_log(f"IMAGE b64_json bytes={len(result_bytes)}")
                    result = bytes_to_bgr_image(result_bytes)
                    if result is not None:
                        out_h, out_w = result.shape[:2]
                        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                        self.append_ai_api_log(f"DONE output={out_w}x{out_h} | elapsed_ms={elapsed_ms}")
                        return result
                image_url = item.get("url")
                if image_url:
                    self.append_ai_api_log(f"IMAGE url={image_url[:180]}")
                    with urllib.request.urlopen(image_url, timeout=180) as image_response:
                        result_bytes = image_response.read()
                    result = bytes_to_bgr_image(result_bytes)
                    if result is not None:
                        out_h, out_w = result.shape[:2]
                        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                        self.append_ai_api_log(f"DONE output={out_w}x{out_h} | elapsed_ms={elapsed_ms}")
                        return result
            self.append_ai_api_log("ERROR OpenAI không trả về ảnh kết quả")
            raise RuntimeError("OpenAI không trả về ảnh kết quả.")
        finally:
            self.gemini_request_in_flight = False

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

    def update_ai_status_badge(self):
        if self.ai_status_badge is None or self.ai_status_text is None:
            return
        is_on = bool(self.gemini_ai_switch.value and self.active_preset_key == "more_clear")
        provider = self.get_ai_provider()
        self.ai_status_text.value = f"AI On - {provider}" if is_on else "AI Off"
        self.ai_status_text.color = ft.Colors.WHITE if is_on else ft.Colors.GREY_700
        self.ai_status_badge.bgcolor = ft.Colors.BLUE_700 if is_on else ft.Colors.GREY_200
        self.ai_status_badge.border = ft.border.all(
            1,
            ft.Colors.BLUE_800 if is_on else ft.Colors.GREY_300,
        )

    def on_ai_setting_change(self, e=None):
        self.update_ai_status_badge()
        self.refresh_page()

    def get_config_display_name(self) -> str:
        if self.active_preset_key == "custom":
            return "Custom"
        return PRESET_LABELS.get(self.active_preset_key, "Custom")

    def update_config_status_display(self):
        display_name = self.get_config_display_name()
        if self.batch_config_status_text is not None:
            self.batch_config_status_text.value = display_name

    def set_batch_paths(self, input_dir: Path, output_dir: Path):
        self.batch_input_dir = input_dir
        self.batch_output_dir = output_dir
        self.batch_input_text.value = f"Input: {self.batch_input_dir}"
        self.batch_output_text.value = f"Output: {self.batch_output_dir}"

    def get_default_batch_output_dir(self, input_dir: Path) -> Path:
        return input_dir / "vdnc_pro"

    def load_batch_task_into_form(self, task: BatchTask):
        self.set_batch_paths(task.input_dir, task.output_dir)
        self.batch_output_manual = True
        self.active_preset_key = task.preset_key
        self.cfg = ProcessConfig(**asdict(task.cfg))
        self.apply_config_to_controls(self.cfg)
        if self.batch_config_status_text is not None:
            self.batch_config_status_text.value = task.config_label
        self.update_ai_status_badge()
        self.update_status(f"Đã nạp Task #{task.task_id} vào Batch xử lý thư mục.")
        self.set_active_tab(2)

    def select_batch_task(self, task_id: int):
        task = self.find_batch_task(task_id)
        if task is None:
            return
        self.load_batch_task_into_form(task)

    def open_batch_folder(self, folder: Optional[Path], label: str):
        if folder is None:
            self.show_snack(f"Chưa chọn thư mục {label}.")
            return
        if not folder.exists():
            self.show_snack(f"Thư mục {label} chưa tồn tại: {folder}")
            return
        try:
            os.startfile(folder)
        except Exception as exc:
            self.show_snack(f"Không mở được thư mục {label}: {exc}")

    def open_batch_input_folder(self, e=None):
        self.open_batch_folder(self.batch_input_dir, "nguồn")

    def open_batch_output_folder(self, e=None):
        self.open_batch_folder(self.batch_output_dir, "đích")

    def set_config_status(self):
        display_name = self.get_config_display_name()
        self.update_config_status_display()
        self.update_status(f"Cấu hình xử lý: {display_name}")

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
        if self.preview_panel_body is not None and self.preview_panel_body.content is not self.main_tabs:
            self.preview_panel_body.content = self.main_tabs
        self.main_tabs.selected_index = index
        self.refresh_page()

    def set_review_processing_mode(self, enabled: bool):
        if self.preview_panel_body is None or self.main_tabs is None:
            return
        if self.review_intro_card is not None:
            self.review_intro_card.visible = not enabled
        for split_checkbox in (
            self.review_train_checkbox,
            self.review_valid_checkbox,
            self.review_test_checkbox,
        ):
            if split_checkbox is not None:
                split_checkbox.visible = enabled
        if enabled:
            self.preview_panel_body.content = self.review_tab_content or self.main_tabs
        else:
            self.preview_panel_body.content = self.main_tabs
            self.main_tabs.selected_index = 1
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
            self.batch_queue_text.value = "Chưa có batch task."
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
            value=f"0/{task.total_files} ảnh | Output: {task.output_dir}",
            size=11,
            color=ft.Colors.GREY_600,
        )
        task.progress_bar = ft.ProgressBar(
            value=0 if task.total_files > 0 else None,
            bar_height=10,
            color=ft.Colors.AMBER_700,
            bgcolor=ft.Colors.AMBER_100,
        )
        task.pause_button = ft.OutlinedButton(
            text="Dừng",
            icon=ft.Icons.PAUSE_CIRCLE_OUTLINE,
            on_click=lambda e, task_id=task.task_id: self.pause_batch_task(task_id),
        )
        task.stop_button = ft.OutlinedButton(
            text="Dừng hẳn",
            icon=ft.Icons.STOP_CIRCLE_OUTLINED,
            on_click=lambda e, task_id=task.task_id: self.stop_batch_task(task_id),
        )
        task.resume_button = ft.OutlinedButton(
            text="Tiep tuc",
            icon=ft.Icons.PLAY_CIRCLE_OUTLINE,
            on_click=lambda e, task_id=task.task_id: self.resume_batch_task(task_id),
        )
        task.delete_button = ft.OutlinedButton(
            text="Xóa",
            icon=ft.Icons.DELETE_OUTLINE,
            on_click=lambda e, task_id=task.task_id: self.delete_batch_task(task_id),
        )
        task.card = ft.Container(
            padding=12,
            border_radius=14,
            bgcolor=ft.Colors.AMBER_50,
            border=ft.border.all(1, ft.Colors.AMBER_100),
            on_click=lambda e, task_id=task.task_id: self.select_batch_task(task_id),
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

        status_color = ft.Colors.AMBER_800
        card_color = ft.Colors.AMBER_50
        border_color = ft.Colors.AMBER_100
        progress_color = ft.Colors.AMBER_700
        progress_bgcolor = ft.Colors.AMBER_100

        if task.status == "Running":
            status_color = ft.Colors.AMBER_800
            card_color = ft.Colors.AMBER_50
            border_color = ft.Colors.AMBER_100
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
            card_color = ft.Colors.GREEN_50
            border_color = ft.Colors.GREEN_100
            progress_color = ft.Colors.GREEN_700
            progress_bgcolor = ft.Colors.GREEN_100
        elif task.status in {"Error", "Cancelled"}:
            status_color = ft.Colors.RED_700
            card_color = ft.Colors.RED_50
            border_color = ft.Colors.RED_100
            progress_color = ft.Colors.RED_700
            progress_bgcolor = ft.Colors.RED_100

        task.status_text.value = task.status
        task.status_text.color = status_color
        task.progress_bar.color = progress_color
        task.progress_bar.bgcolor = progress_bgcolor

        if task.card is not None:
            task.card.bgcolor = card_color
            task.card.border = ft.border.all(1, border_color)

        current_file = f" | File: {task.current_file}" if task.current_file else ""
        error_text = f" | Error: {task.error}" if task.error else ""
        task.detail_text.value = (
            f"{done}/{task.total_files} ảnh | OK: {task.processed_count} | Lỗi: {task.skipped_count}"
            f"{current_file}{error_text}"
        )

        if task.pause_button is not None:
            task.pause_button.disabled = task.status not in {"Queued", "Running"}
        if task.stop_button is not None:
            task.stop_button.disabled = task.status not in {"Queued", "Running", "Paused"}
            task.stop_button.text = "Đang dừng hẳn" if task.status == "Stopping" else "Dừng hẳn"
        if task.resume_button is not None:
            task.resume_button.disabled = task.status != "Paused"
        if task.delete_button is not None:
            task.delete_button.disabled = task.delete_requested
            task.delete_button.text = "Đang xóa" if task.delete_requested else "Xóa"

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
        self.update_status(f"Đã tạm dừng Task #{task.task_id}.")

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
        self.update_status(f"Đang dừng hẳn Task #{task.task_id}.")

    def resume_batch_task(self, task_id: int):
        task = self.find_batch_task(task_id)
        if task is None:
            return
        if task.status != "Paused":
            return
        task.pause_requested = False
        task.status = "Running"
        self.update_batch_task_ui(task, force=True)
        self.update_status(f"Đã tiếp tục Task #{task.task_id}.")

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
            self.update_status(f"Task #{task.task_id} sẽ bị xóa sau khi dừng.")
            return
        self.remove_batch_task(task_id)
        self.update_status(f"Đã xóa Task #{task_id} khỏi danh sách.")
        self.show_snack(f"Đã xóa Task #{task_id}.")

    def process_batch_task(self, task: BatchTask):
        if task.hard_stop_requested:
            task.status = "Cancelled"
        else:
            task.status = "Paused" if task.pause_requested else "Running"
        self.update_batch_task_ui(task, force=True)
        if task.status == "Running":
            self.update_status(f"Task #{task.task_id} đang xử lý {task.total_files} ảnh...")

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
            self.update_status(f"Đã xóa Task #{task.task_id} khỏi danh sách.")
            self.show_snack(f"Đã xóa Task #{task.task_id}.")
            return

        summary = (
            f"Task #{task.task_id} xong | OK: {task.processed_count} | Lỗi: {task.skipped_count}"
        )
        if task.status == "Cancelled":
            summary = (
                f"Task #{task.task_id} đã dừng | OK: {task.processed_count} | Lỗi: {task.skipped_count}"
            )
        elif task.error:
            summary += f" | Lỗi đầu tiên: {task.error}"

        self.update_status(summary)
        self.show_snack(summary)

    # -----------------------------------------------------
    # Events
    # -----------------------------------------------------

    def on_control_change(self, e):
        self.active_preset_key = "custom"
        self.update_ai_status_badge()
        self.cfg = self.get_config_from_controls()
        self.set_config_status()

        if self.instant_switch.value:
            self.update_preview()

    def apply_preset(self, key: str):
        cfg = PRESETS[key]

        self.active_preset_key = key
        self.cfg = ProcessConfig(**asdict(cfg))

        self.apply_config_to_controls(self.cfg)
        self.update_ai_status_badge()

        self.update_preview()

        self.set_config_status()

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
            self.show_snack("File không hợp lệ. Hãy chọn ảnh jpg/jpeg/png/bmp/webp.")
            return

        img = read_image_bgr(file_path)

        if img is None:
            self.show_snack("Không đọc được ảnh.")
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
        self.processed_info.value = "Đang tạo preview..."

        if self.header_status_card is not None:
            self.header_status_card.visible = True

        self.set_preview_state(True)
        self.set_active_tab(0)
        self.update_preview()
        self.update_status(f"Đã mở ảnh: {file_path.name}")

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
            ai_suffix = ""
            if self.should_use_gemini_ai():
                self.update_status(f"Đang phục hồi ảnh bằng {self.get_ai_provider()} AI...")
                self.processed_img = self.enhance_with_ai(self.original_img)
                ai_suffix = f" | {self.get_ai_provider()} AI"

            processed_b64 = cv2_to_base64_png(self.processed_img)
            self.processed_preview.src_base64 = processed_b64
            self.review_processed_preview.src_base64 = processed_b64

            h, w = self.processed_img.shape[:2]

            info_text = (
                f"Output {w} x {h} | "
                f"{self.cfg.resize_mode} | "
                f"AC {self.cfg.auto_contrast:.1f} | "
                f"CLAHE {self.cfg.clahe_clip:.1f} | "
                f"Denoise {self.cfg.denoise_method} | "
                f"Sharpen {self.cfg.sharpen_amount:.2f}{ai_suffix}"
            )
            self.processed_info.value = info_text
            self.review_processed_info.value = info_text
            if self.save_image_button is not None:
                self.save_image_button.disabled = False
            self.set_preview_state(True)

        except Exception as exc:
            self.processed_img = None
            self.processed_preview.src_base64 = EMPTY_PREVIEW_BASE64
            self.processed_info.value = "Chưa xử lý."
            if self.save_image_button is not None:
                self.save_image_button.disabled = True
            self.refresh_page()
            self.show_snack(f"Lỗi xử lý ảnh: {exc}")

    def open_save_dialog(self, e):
        if self.processed_img is None:
            self.show_snack("Chưa có ảnh processed để lưu.")
            return

        default_name = "processed_image.png"

        if self.current_path:
            default_name = f"{self.current_path.stem}_preprocessed.png"

        self.file_picker_save.save_file(
            dialog_title="Lưu ảnh processed",
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
            self.show_snack(f"Đã lưu ảnh: {output_path}")
        else:
            self.show_snack("Không lưu được ảnh.")

    def update_review_scan_button(self):
        if self.review_scan_button is None:
            return
        self.review_scan_button.disabled = not (
            self.review_input_dir is not None and self.review_output_dir is not None
        )

    def on_review_input_result(self, e: ft.FilePickerResultEvent):
        if not e.path:
            return
        self.review_input_dir = Path(e.path)
        self.review_input_text.value = f"Nguồn: {self.review_input_dir}"
        self.update_status(f"Folder nguồn: {self.review_input_dir}")
        if self.review_project_text is not None:
            self.review_project_text.value = self.review_input_dir.name.upper()
        self.update_review_scan_button()
        self.refresh_page()

    def on_review_output_result(self, e: ft.FilePickerResultEvent):
        if not e.path:
            return
        self.review_output_dir = Path(e.path)
        self.review_output_text.value = f"Đích: {self.review_output_dir}"
        self.update_status(f"Folder đích: {self.review_output_dir}")
        self.update_review_scan_button()
        self.refresh_page()

    def get_review_split(self) -> str:
        if self.review_valid_checkbox is not None and self.review_valid_checkbox.value:
            return "valid"
        if self.review_test_checkbox is not None and self.review_test_checkbox.value:
            return "test"
        return "train"

    def get_review_output_path(self, src: Path, split: Optional[str] = None) -> Path:
        if self.review_input_dir is None or self.review_output_dir is None:
            return Path.cwd() / f"{src.stem}_preprocessed.png"
        try:
            rel = src.relative_to(self.review_input_dir)
        except ValueError:
            rel = Path(src.name)
        output_split = split or self.get_review_split()
        output_name = rel.with_name(f"{rel.stem}_preprocessed.png")
        return self.review_output_dir / output_split / output_name

    def get_review_output_paths(self, src: Path) -> list[Path]:
        return [self.get_review_output_path(src, split) for split in ("train", "valid", "test")]

    def get_valid_review_output_path(self, src: Path) -> Optional[Path]:
        for output_path in self.get_review_output_paths(src):
            if output_path.exists() and output_path.stat().st_size > 0 and read_image_bgr(output_path) is not None:
                return output_path
        return None

    def is_inside_review_output(self, src: Path) -> bool:
        if self.review_output_dir is None:
            return False
        try:
            src.resolve().relative_to(self.review_output_dir.resolve())
            return True
        except (OSError, ValueError):
            return False

    def has_valid_review_output(self, src: Path) -> bool:
        return self.get_valid_review_output_path(src) is not None

    def scan_review_folder(self, e=None):
        if self.review_input_dir is None:
            self.show_snack("Hãy chọn folder nguồn trước.")
            return
        if self.review_output_dir is None:
            self.show_snack("Hãy chọn folder đích trước.")
            return
        self.review_output_dir.mkdir(parents=True, exist_ok=True)
        all_files = sorted(
            src for src in self.review_input_dir.rglob("*")
            if src.suffix.lower() in SUPPORTED_EXTS
            and not self.is_inside_review_output(src)
        )
        done_files = [src for src in all_files if self.has_valid_review_output(src)]
        invalid_output = sum(
            1 for src in all_files
            if any(output_path.exists() for output_path in self.get_review_output_paths(src)) and src not in done_files
        )
        skip_done = bool(self.review_skip_done.value) if self.review_skip_done is not None else True
        self.review_files = [
            src for src in all_files
            if not skip_done or src not in done_files
        ]
        self.review_index = 0
        if not all_files:
            self.review_status_text.value = (
                "Không tìm thấy ảnh trong folder nguồn. Hỗ trợ: "
                f"{', '.join(sorted(SUPPORTED_EXTS))}"
            )
            self.set_review_buttons(False)
            self.refresh_page()
            self.show_snack("Không tìm thấy ảnh hợp lệ trong folder nguồn.")
            return
        if not self.review_files:
            self.review_status_text.value = (
                f"Đã xử lý hết {len(all_files)} ảnh trong folder nguồn. "
                f"Đã bỏ qua {len(done_files)} output hợp lệ."
            )
            self.set_review_buttons(False)
            self.refresh_page()
            self.show_snack("Không còn ảnh chưa xử lý.")
            return
        self.review_status_text.value = (
            f"Tìm thấy {len(all_files)} ảnh | Chưa xử lý: {len(self.review_files)} | "
            f"Output hợp lệ: {len(done_files)} | Output lỗi/rỗng: {invalid_output}"
        )
        self.set_review_processing_mode(True)
        self.set_review_buttons(True)
        if self.show_review_details:
            self.toggle_review_details()
        self.load_review_current()

    def set_review_buttons(self, enabled: bool):
        if self.review_save_button is not None:
            self.review_save_button.disabled = not enabled
        if self.review_next_button is not None:
            self.review_next_button.disabled = not enabled
        if self.review_prev_button is not None:
            self.review_prev_button.disabled = not enabled
        if self.review_counter_next_button is not None:
            self.review_counter_next_button.disabled = not enabled
        if self.review_more_button is not None:
            self.review_more_button.disabled = not enabled
        for split_checkbox in (
            self.review_train_checkbox,
            self.review_valid_checkbox,
            self.review_test_checkbox,
        ):
            if split_checkbox is not None:
                split_checkbox.disabled = not enabled
        self.update_review_counter()

    def on_review_split_change(self, e=None):
        changed = getattr(e, "control", None)
        if changed is None or not changed.value:
            if not any(
                checkbox is not None and checkbox.value
                for checkbox in (
                    self.review_train_checkbox,
                    self.review_valid_checkbox,
                    self.review_test_checkbox,
                )
            ) and self.review_train_checkbox is not None:
                self.review_train_checkbox.value = True
            self.refresh_page()
            return
        for split_checkbox in (
            self.review_train_checkbox,
            self.review_valid_checkbox,
            self.review_test_checkbox,
        ):
            if split_checkbox is not None and split_checkbox is not changed:
                split_checkbox.value = False
        self.refresh_page()

    def update_review_counter(self):
        if self.review_counter_text is None:
            return
        total = len(self.review_files)
        current = 0 if total == 0 else self.review_index + 1
        counter_value = f"{current} / {total}"
        self.review_counter_text.value = counter_value
        if self.review_toolbar_counter_text is not None:
            self.review_toolbar_counter_text.value = counter_value

    def toggle_review_details(self, e=None):
        self.show_review_details = not self.show_review_details
        if self.review_folder_details is not None:
            self.review_folder_details.visible = self.show_review_details
        if self.review_details_button is not None:
            self.review_details_button.text = (
                "Ẩn chi tiết nguồn/đích" if self.show_review_details else "Hiện chi tiết nguồn/đích"
            )
            self.review_details_button.icon = (
                ft.Icons.EXPAND_LESS if self.show_review_details else ft.Icons.EXPAND_MORE
            )
        self.refresh_page()

    def prev_review_image(self, e=None):
        if not self.review_files:
            return
        self.review_index = (self.review_index - 1) % len(self.review_files)
        self.load_review_current()

    def load_review_current(self):
        if not self.review_files:
            self.set_review_buttons(False)
            return
        self.review_index = min(self.review_index, len(self.review_files) - 1)
        src = self.review_files[self.review_index]
        img = read_image_bgr(src)
        if img is None:
            self.review_status_text.value = f"Không đọc được: {src.name}"
            self.next_review_image(None, skip_save=True)
            return
        self.current_path = src
        self.original_img = img
        self.processed_img = None
        preview_b64 = cv2_to_base64_png(img)
        self.original_preview.src_base64 = preview_b64
        self.review_original_preview.src_base64 = preview_b64
        self.original_info.value = f"{src.name} | {img.shape[1]} x {img.shape[0]}"
        self.review_original_info.value = self.original_info.value
        self.processed_preview.src_base64 = EMPTY_PREVIEW_BASE64
        self.review_processed_preview.src_base64 = EMPTY_PREVIEW_BASE64
        self.processed_info.value = "Đang tạo preview..."
        self.review_processed_info.value = "Đang tạo preview..."
        output_path = self.get_review_output_path(src)
        output_name = f"{output_path.parent.name}/{output_path.name}"
        if self.review_project_text is not None:
            source_name = self.review_input_dir.name if self.review_input_dir is not None else src.parent.name
            self.review_project_text.value = source_name.upper()
        if self.review_toolbar_file_text is not None:
            self.review_toolbar_file_text.value = src.name
        self.review_status_text.value = (
            f"Ảnh {self.review_index + 1}/{len(self.review_files)}: {src.name} | "
            f"Lưu tới: {output_name}"
        )
        if self.header_status_card is not None:
            self.header_status_card.visible = True
        self.set_preview_state(True)
        self.update_preview()
        self.update_status(f"Đang duyệt: {src.name}")

    def save_review_current(self, e=None) -> bool:
        if self.current_path is None or self.original_img is None:
            self.show_snack("Chưa có ảnh hiện tại để lưu.")
            return False
        if self.review_output_dir is None:
            self.show_snack("Hãy chọn folder đích trước.")
            return False
        self.cfg = self.get_config_from_controls()
        self.processed_img = preprocess_cv2(self.original_img, self.cfg)
        if self.should_use_gemini_ai():
            self.update_status(f"Đang phục hồi ảnh bằng {self.get_ai_provider()} AI...")
            self.processed_img = self.enhance_with_ai(self.original_img)
        output_path = self.get_review_output_path(self.current_path)
        ok = save_image(output_path, self.processed_img)
        if ok:
            self.show_snack(f"Đã lưu: {output_path.parent.name}/{output_path.name}")
            return True
        self.show_snack("Không lưu được ảnh hiện tại.")
        return False

    def show_review_setup(self, e=None):
        self.set_review_processing_mode(False)
        if not self.show_review_details:
            self.toggle_review_details()
        else:
            self.refresh_page()

    def copy_review_image(self, e=None):
        if self.current_path is None:
            self.show_snack("Chưa có ảnh để copy.")
            return
        output_path = self.get_valid_review_output_path(self.current_path)
        copy_path = output_path if output_path is not None else self.current_path
        self.page.set_clipboard(str(copy_path))
        self.show_snack(f"Đã copy đường dẫn ảnh: {copy_path.name}")

    def remove_review_current(self, e=None):
        if not self.review_files or self.current_path is None:
            self.show_snack("Chưa có ảnh để xoá khỏi danh sách.")
            return
        removed_name = self.current_path.name
        if self.current_path in self.review_files:
            self.review_files.pop(self.review_index)
        if self.review_index >= len(self.review_files):
            self.review_index = 0
        if not self.review_files:
            self.current_path = None
            self.review_status_text.value = "Đã xoá ảnh cuối cùng khỏi danh sách xử lý."
            if self.review_toolbar_file_text is not None:
                self.review_toolbar_file_text.value = "Không còn ảnh trong danh sách"
            self.set_review_buttons(False)
            self.refresh_page()
            self.show_snack(f"Đã xoá khỏi Project: {removed_name}")
            return
        self.load_review_current()
        self.show_snack(f"Đã xoá khỏi Project: {removed_name}")

    def next_review_image(self, e=None, skip_save: bool = False):
        if not self.review_files:
            self.scan_review_folder()
            return

        should_remove_current = False
        if not skip_save and self.review_auto_save.value:
            if not self.save_review_current(None):
                return
            should_remove_current = True
        elif self.current_path is not None and self.has_valid_review_output(self.current_path):
            should_remove_current = True

        if should_remove_current and self.current_path in self.review_files:
            self.review_files.pop(self.review_index)
        elif not should_remove_current:
            self.review_index += 1

        if self.review_index >= len(self.review_files):
            self.review_index = 0
        if not self.review_files:
            self.review_status_text.value = "Đã xử lý hết ảnh chưa lưu trong folder."
            self.set_review_buttons(False)
            self.refresh_page()
            self.show_snack("Đã xử lý hết folder.")
            return
        self.load_review_current()

    def on_batch_input_result(self, e: ft.FilePickerResultEvent):
        if not e.path:
            return

        self.batch_input_dir = Path(e.path)
        output_dir = self.batch_output_dir
        if output_dir is None or not self.batch_output_manual:
            output_dir = self.get_default_batch_output_dir(self.batch_input_dir)
        self.set_batch_paths(self.batch_input_dir, output_dir)

        self.update_status(f"Batch input: {self.batch_input_dir}")

    def on_batch_output_result(self, e: ft.FilePickerResultEvent):
        if not e.path:
            return

        self.batch_output_dir = Path(e.path)
        self.batch_output_manual = True
        self.batch_output_text.value = f"Output: {self.batch_output_dir}"

        self.update_status(f"Batch output: {self.batch_output_dir}")

    def run_batch(self, e):
        if self.batch_input_dir is None:
            self.show_snack("Hãy chọn thư mục input trước.")
            return

        if self.batch_output_dir is None:
            self.show_snack("Hãy chọn thư mục output trước.")
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
            self.show_snack("Folder input không có ảnh hợp lệ.")
            return

        task = BatchTask(
            task_id=self.next_batch_task_id,
            input_dir=input_dir,
            output_dir=output_dir,
            cfg=ProcessConfig(**asdict(cfg)),
            total_files=len(files),
            preset_key=self.active_preset_key,
            config_label=self.get_config_display_name(),
        )
        self.next_batch_task_id += 1

        self.add_batch_task(task)
        self.set_active_tab(2)
        self.update_status(
            f"Đã tạo Task #{task.task_id} | {task.total_files} ảnh | preview vẫn hoạt động độc lập."
        )
        self.show_snack(f"Đã thêm Task #{task.task_id} vào batch queue.")
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

        self.show_snack("Đã copy config JSON vào clipboard.")

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

        self.show_snack(f"Đã lưu config tại: {output_path}")


def main(page: ft.Page):
    app = CowSkinPreprocessApp(page)
    app.setup()


if __name__ == "__main__":
    ft.app(target=main)


