from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from bll.app_context import RUNS_DIR, TOOL_TRAIN_DIR

ROOT_DIR = TOOL_TRAIN_DIR
DEFAULT_YAML = ROOT_DIR / "dataset" / "Cattle Desease.v1i.yolov8" / "data.yaml"
OUTPUT_DIR = RUNS_DIR
PYTHON_EXE = Path(sys.executable)

PRESETS = {
    "Nhanh (yolov8n - nhẹ nhất)":  {"model": "yolov8n", "batch": 32, "imgsz": 640, "workers": 8},
    "Cân bằng (yolov8s)":           {"model": "yolov8s", "batch": 16, "imgsz": 640, "workers": 8},
    "Chất lượng (yolov8m)":         {"model": "yolov8m", "batch": 8,  "imgsz": 640, "workers": 8},
    "Cao (yolov8l)":                {"model": "yolov8l", "batch": 4,  "imgsz": 640, "workers": 4},
    "Tối đa (yolov8x - nặng nhất)": {"model": "yolov8x", "batch": 2,  "imgsz": 640, "workers": 4},
}

TASK_TYPES = ["Detection", "Instance Segmentation", "Classification"]
EXPORT_FORMATS = [".pt (PyTorch)", ".onnx (ONNX)", ".pt + .onnx"]
CLASS_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".ppm", ".bmp", ".pgm", ".tif", ".tiff", ".webp"}


def _resolve_classification_root(path_value: str | Path) -> Path:
    path = Path(path_value).expanduser()
    if path.name.lower() in {"train", "val", "valid", "test"} and path.parent.exists():
        return path.parent
    return path


def _has_classification_images(root: Path) -> bool:
    if not root.is_dir():
        return False
    for class_dir in root.iterdir():
        if not class_dir.is_dir():
            continue
        for img_path in class_dir.rglob("*"):
            if img_path.is_file() and img_path.suffix.lower() in CLASS_IMAGE_EXTS:
                return True
    return False
