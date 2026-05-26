from pathlib import Path

from bll.train.common import TASK_TYPES


def prepare_yolo_training(config: dict) -> dict:
    yaml_path = Path(config["yaml_path"])
    if not yaml_path.exists():
        raise ValueError(f"Không tìm thấy file:\n{yaml_path}")

    epochs = int(config["epochs"])
    batch = int(config["batch"])
    imgsz = int(config["imgsz"])
    lr = float(config["lr"])
    patience = int(config["patience"])
    workers = int(config["workers"])
    device = str(config["device"])
    model = str(config["model"])
    amp = bool(config["amp"])
    cache = bool(config["cache"])
    project_dir = str(config["project_dir"])
    task = str(config["task"])
    export_fmt = str(config["export_fmt"])
    export_onnx = "onnx" in export_fmt.lower()
    export_pt = ".pt" in export_fmt
    if task == "Instance Segmentation":
        task_arg = "segment"
    elif task == "Classification":
        task_arg = "classify"
    else:
        task_arg = "detect"
    run_name = f"train_{model.replace('.pt','')}_{epochs}ep"
    optimizer = str(config["optimizer"])
    weight_decay = float(config["weight_decay"])
    dropout = float(config["dropout"])
    freeze = int(config["freeze"])
    label_smooth = float(config["label_smooth"])
    cos_lr = bool(config["cos_lr"])
    mosaic = float(config["mosaic"])
    mixup = float(config["mixup"])
    degrees = int(config["degrees"])
    hsv_s = float(config["hsv_s"])
    hsv_v = float(config["hsv_v"])
    cls_extra_args = ""
    cls_hint = ""
    cls_setup = ""
    if task_arg == "classify":
        cls_extra_args = f"""    fliplr    = 0.5,
    translate = 0.1,
    scale     = 0.45,
    hsv_h     = 0.015,
    cutmix    = 0.0,
    erasing   = 0.0,
    freeze    = {freeze},
"""
        cls_hint = (
            f"  Classify anti-overfit: AdamW + CosLR + Freeze={freeze} + WD={weight_decay:.4f} + Dropout={dropout:.2f} + "
            f"Batch={batch} + LR={lr:.5f} + Patience={patience} + Mixup={mixup:.2f}\n"
        )
        cls_setup = '''
from pathlib import Path
from ultralytics.data.utils import check_cls_dataset as _orig_check_cls_dataset
import ultralytics.data.utils as _cls_data_utils
import ultralytics.engine.trainer as _trainer_mod

_IMG_EXTS = {".jpg", ".jpeg", ".png", ".ppm", ".bmp", ".pgm", ".tif", ".tiff", ".webp"}

def _resolve_cls_root(path_value):
    _p = Path(path_value)
    if _p.name.lower() in {"train", "val", "valid", "validation", "test"} and _p.parent.exists():
        return _p.parent
    return _p

def _count_cls_images(split_path):
    _root = Path(split_path) if split_path else None
    if not _root or not _root.is_dir():
        return 0
    return sum(1 for _f in _root.rglob("*") if _f.is_file() and _f.suffix.lower() in _IMG_EXTS)

def _patched_check_cls_dataset(dataset, split=""):
    resolved = _resolve_cls_root(dataset)
    data = _orig_check_cls_dataset(resolved, split=split)
    train_count = _count_cls_images(data.get("train"))
    val_count = _count_cls_images(data.get("val"))
    test_count = _count_cls_images(data.get("test"))
    if Path(resolved) != Path(dataset):
        print(f"[INFO] Classification root auto-resolve: {dataset} -> {resolved}", flush=True)
    if val_count == 0:
        if test_count > 0:
            data["val"] = data.get("test")
            print(f"[WARN] val/ rong, fallback sang test/ ({test_count} anh)", flush=True)
        elif train_count > 0:
            data["val"] = data.get("train")
            print(f"[WARN] val/ va test/ rong, fallback sang train/ ({train_count} anh)", flush=True)
        else:
            raise FileNotFoundError(f"Khong tim thay anh hop le trong train/: {data.get('train')}")
    return data

_cls_data_utils.check_cls_dataset = _patched_check_cls_dataset
_trainer_mod.check_cls_dataset = _patched_check_cls_dataset
'''

    script = f"""
import os, sys, torch
from pathlib import Path
from ultralytics import YOLO
{cls_setup}

print(f"[INFO] PyTorch: {{torch.__version__}}")
print(f"[INFO] CUDA: {{torch.cuda.is_available()}}")
if torch.cuda.is_available():
    print(f"[INFO] GPU: {{torch.cuda.get_device_name(0)}}")
print(f"[INFO] Task: {task}")
print(f"[INFO] Export: {export_fmt}")

model = YOLO("{model}", task="{task_arg}")
results = model.train(
    data     = r"{yaml_path}",
    task     = "{task_arg}",
    epochs   = {epochs},
    batch    = {batch},
    imgsz    = {imgsz},
    lr0      = {lr},
    cos_lr   = {cos_lr},
    optimizer= "{optimizer}",
    patience = {patience},
    workers  = {workers},
    device   = "{device}",
    amp      = {amp},
    cache    = {cache},
    weight_decay = {weight_decay},
    dropout = {dropout},
    label_smoothing = {label_smooth},
    mosaic   = {mosaic},
    mixup    = {mixup},
    degrees  = {degrees},
    hsv_s    = {hsv_s},
    hsv_v    = {hsv_v},
{cls_extra_args}
    project  = r"{project_dir}",
    name     = "{run_name}",
    exist_ok = True,
    verbose  = True,
)
print("[DONE] Training complete!")
print(f"[RESULT] Saved to: {{results.save_dir}}")
"""
    if export_onnx:
        script += f"""
import subprocess as _sp, sys as _sys
def _ensure(pkg, import_name=None):
    try:
        __import__(import_name or pkg)
    except ImportError:
        print(f"[INFO] Đang cài {{pkg}} vào venv...")
        r = _sp.run([_sys.executable, "-m", "pip", "install", pkg, "-q"], capture_output=False)
        if r.returncode != 0:
            raise RuntimeError(f"Không thể cài {{pkg}}")
        print(f"[INFO] Đã cài {{pkg}}.")

_ensure("onnx")
_ensure("onnxslim")

best_pt = Path(results.save_dir) / 'weights' / 'best.pt'
print(f"[INFO] Xuất ONNX từ: {{best_pt}}")
export_model = YOLO(str(best_pt), task="{task_arg}")
onnx_path = export_model.export(format='onnx', imgsz={imgsz}, dynamic=False)
print(f"[DONE] ONNX đã xuất: {{onnx_path}}")
"""
    if not export_pt and export_onnx:
        script += """
import shutil
weights_dir = Path(results.save_dir) / 'weights'
for f in weights_dir.glob('*.pt'):
    f.unlink()
print("[INFO] Đã xóa file .pt (chỉ giữ .onnx)")
"""
    return {
        "yaml_path": yaml_path,
        "epochs": epochs,
        "batch": batch,
        "imgsz": imgsz,
        "lr": lr,
        "patience": patience,
        "workers": workers,
        "device": device,
        "model": model,
        "amp": amp,
        "cache": cache,
        "project_dir": project_dir,
        "task": task,
        "task_arg": task_arg,
        "export_fmt": export_fmt,
        "optimizer": optimizer,
        "weight_decay": weight_decay,
        "dropout": dropout,
        "freeze": freeze,
        "label_smooth": label_smooth,
        "cos_lr": cos_lr,
        "mosaic": mosaic,
        "mixup": mixup,
        "degrees": degrees,
        "hsv_s": hsv_s,
        "hsv_v": hsv_v,
        "cls_hint": cls_hint,
        "script": script,
    }


def prepare_yolo_ablation(config: dict) -> dict:
    yaml_path = Path(config["yaml_path"])
    if not yaml_path.exists():
        raise ValueError(f"Không tìm thấy file:\n{yaml_path}")
    epochs = int(config["epochs"])
    batch = int(config["batch"])
    imgsz = int(config["imgsz"])
    workers = int(config["workers"])
    device = str(config["device"])
    model = str(config["model"])
    project_dir = str(config["project_dir"])
    run_name = f"ablation_det_{model.replace('.pt','')}_{epochs}ep"
    script = f"""
import torch
import csv, json
from pathlib import Path
from ultralytics import YOLO

print(f"[INFO] PyTorch: {{torch.__version__}}")
print(f"[INFO] CUDA: {{torch.cuda.is_available()}}")
if torch.cuda.is_available():
    print(f"[INFO] GPU: {{torch.cuda.get_device_name(0)}}")
print("[INFO] Ablation Study: Seg dataset -> Detection baseline")
print("[INFO] ultralytics sẽ tự convert Polygon -> BBox khi load data")

model = YOLO("{model}", task="detect")
results = model.train(
    data     = r"{yaml_path}",
    task     = "detect",
    epochs   = {epochs},
    batch    = {batch},
    imgsz    = {imgsz},
    workers  = {workers},
    device   = "{device}",
    project  = r"{project_dir}",
    name     = "{run_name}",
    exist_ok = True,
    verbose  = True,
    mosaic   = 0.0,
    mixup    = 0.0,
)
print("[DONE] Ablation training complete!")
print(f"[RESULT] Saved to: {{results.save_dir}}")
print(f"[RESULT] Best model: {{results.save_dir}}/weights/best.pt")
"""
    return {
        "yaml_path": yaml_path,
        "epochs": epochs,
        "batch": batch,
        "imgsz": imgsz,
        "workers": workers,
        "device": device,
        "model": model,
        "project_dir": project_dir,
        "script": script,
    }


def prepare_yolo_cls_training(config: dict) -> dict:
    data_path = Path(config["data_path"])
    if not data_path.is_dir():
        raise ValueError(f"Không tìm thấy folder:\n{data_path}\n\nCần có train/ và val/ bên trong.")
    missing_subdirs = [name for name in ("train", "val") if not (data_path / name).is_dir()]
    if missing_subdirs:
        raise ValueError(
            "Dataset classification cần ít nhất có thư mục train/ và val/.\n"
            f"Thiếu: {', '.join(missing_subdirs)}\n\nĐường dẫn: {data_path}"
        )
    payload = dict(config)
    payload["data_path"] = data_path
    epochs = int(config["epochs"])
    patience = int(config["patience"])
    batch = int(config["batch"])
    imgsz = int(config["imgsz"])
    lr = float(config["lr"])
    weight_decay = float(config["weight_decay"])
    momentum = float(config["momentum"])
    dropout = float(config["dropout"])
    lbl_smooth = float(config["label_smooth"])
    workers = int(config["workers"])
    device = str(config["device"])
    model = str(config["model"])
    optimizer = str(config["optimizer"])
    cos_lr = bool(config["cos_lr"])
    amp = bool(config["amp"])
    project_dir = str(config["project_dir"])
    run_name = f"cls_{model.replace('.pt','')}_{epochs}ep"
    aug_degrees = int(config["degrees"])
    aug_translate = float(config["translate"])
    aug_scale = float(config["scale"])
    aug_hsv_h = float(config["hsv_h"])
    aug_hsv_s = float(config["hsv_s"])
    aug_hsv_v = float(config["hsv_v"])
    aug_mixup = float(config["mixup"])
    aug_cutmix = float(config["cutmix"])
    aug_erasing = float(config["erasing"])
    aug_fliplr = float(config["fliplr"])
    aug_flipud = float(config["flipud"])
    aug_mosaic = float(config["mosaic"])
    script = f"""
import torch
from pathlib import Path
from ultralytics import YOLO

print(f"[INFO] PyTorch: {{torch.__version__}}")
print(f"[INFO] CUDA: {{torch.cuda.is_available()}}")
if torch.cuda.is_available():
    print(f"[INFO] GPU: {{torch.cuda.get_device_name(0)}}")
print("[INFO] Classification Baseline - Map JILSA 2022")
print(r"[INFO] Dataset: {data_path}")
print("[INFO] Ultralytics sẽ tự điều chỉnh Gradient Accumulation để Effective BS = nbs=64")
print("[INFO] Khuyến nghị regularization: LR thấp + weight decay + dropout + mix augment nhẹ")

model = YOLO("{model}")
results = model.train(
    data      = r"{data_path}",
    epochs    = {epochs},
    patience  = {patience},
    batch     = {batch},
    imgsz     = {imgsz},
    optimizer        = "{optimizer}",
    momentum         = {momentum},
    lr0              = {lr},
    lrf              = 0.01,
    cos_lr           = {cos_lr},
    weight_decay     = {weight_decay},
    dropout          = {dropout},
    label_smoothing  = {lbl_smooth},
    degrees   = {aug_degrees},
    translate = {aug_translate},
    scale     = {aug_scale},
    hsv_h     = {aug_hsv_h},
    hsv_s     = {aug_hsv_s},
    hsv_v     = {aug_hsv_v},
    flipud    = {aug_flipud},
    fliplr    = {aug_fliplr},
    mosaic    = {aug_mosaic},
    mixup     = {aug_mixup},
    cutmix    = {aug_cutmix},
    erasing   = {aug_erasing},
    workers   = {workers},
    amp       = {amp},
    device    = {device if device == '0' else repr(device)},
    project   = r"{project_dir}",
    name      = "{run_name}",
    exist_ok  = True,
    verbose   = True,
)
print("[DONE] Classification training complete!")
print(f"[RESULT] Saved to: {{results.save_dir}}")
print(f"[RESULT] Best model: {{results.save_dir}}/weights/best.pt")
"""
    payload.update({
        "epochs": epochs,
        "patience": patience,
        "batch": batch,
        "imgsz": imgsz,
        "lr": lr,
        "weight_decay": weight_decay,
        "momentum": momentum,
        "dropout": dropout,
        "label_smooth": lbl_smooth,
        "workers": workers,
        "device": device,
        "model": model,
        "optimizer": optimizer,
        "cos_lr": cos_lr,
        "amp": amp,
        "project_dir": project_dir,
        "script": script,
    })
    return payload
