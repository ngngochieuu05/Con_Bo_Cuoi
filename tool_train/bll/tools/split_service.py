from __future__ import annotations

import random
import shutil
from pathlib import Path

from bll.tools.copy_service import IMAGE_EXTS

SPLIT_NAMES = {"train", "val", "valid", "test"}


def count_images(folder: Path, exts: set[str] | None = None) -> int:
    valid_exts = exts or IMAGE_EXTS
    return sum(
        1
        for path in folder.rglob("*")
        if path.is_file() and path.suffix.lower() in valid_exts
    )


def read_split_ratio(source: Path) -> dict:
    if source.is_file():
        source = source.parent

    splits = {}
    for child in source.iterdir():
        if child.is_dir() and child.name.lower() in SPLIT_NAMES:
            splits[child.name.lower()] = count_images(child)

    report = {
        "source": str(source.resolve()),
        "counts": {},
        "total": 0,
        "note": "",
    }

    if splits:
        report["counts"] = splits
        report["total"] = sum(splits.values())
        report["note"] = "Đã phát hiện thư mục split chuẩn."
        return report

    children = [child for child in source.iterdir() if child.is_dir()]
    if children:
        report["counts"] = {child.name: count_images(child) for child in children}
        report["total"] = sum(report["counts"].values())
        report["note"] = "Không tìm thấy train/val/test, đếm theo các folder con."
        return report

    raise FileNotFoundError("Không tìm thấy thư mục split hoặc lớp ảnh trong dataset.")


def run_split_dataset(
    src: str,
    dst: str,
    train_r: float,
    val_r: float,
    test_r: float,
    seed: int,
    move: bool,
    gen_yaml: bool,
    *,
    progress_callback=None,
    log_callback=None,
) -> dict:
    random.seed(seed)
    src_path = Path(src)
    out_path = Path(dst) if dst else src_path.parent / f"{src_path.name}_split"

    class_dirs = sorted(path for path in src_path.iterdir() if path.is_dir())
    if not class_dirs:
        raise FileNotFoundError("Không tìm thấy class folder nào.")

    all_files = {}
    for class_dir in class_dirs:
        images = [path for path in class_dir.glob("*") if path.is_file() and path.suffix.lower() in IMAGE_EXTS]
        if images:
            all_files[class_dir.name] = images
    if not all_files:
        raise FileNotFoundError("Không tìm thấy ảnh hợp lệ.")

    for split_name in ("train", "val", "test"):
        for class_name in all_files:
            (out_path / split_name / class_name).mkdir(parents=True, exist_ok=True)

    action = shutil.move if move else shutil.copy2
    total_imgs = 0
    summary_rows = []
    total_classes = len(all_files)

    for idx, (class_name, images) in enumerate(all_files.items(), start=1):
        random.shuffle(images)
        total = len(images)
        n_train = int(total * train_r)
        n_val = int(total * val_r)
        split_map = {
            "train": images[:n_train],
            "val": images[n_train:n_train + n_val],
            "test": images[n_train + n_val:],
        }
        for split_name, files in split_map.items():
            for image_path in files:
                try:
                    action(str(image_path), str(out_path / split_name / class_name / image_path.name))
                except Exception as exc:
                    if log_callback:
                        log_callback(f"  [WARN] {image_path.name}: {exc}")

        c_train = len(split_map["train"])
        c_val = len(split_map["val"])
        c_test = len(split_map["test"])
        total_imgs += total
        row = f"{class_name:<20} | {total:5} | {c_train:5} | {c_val:4} | {c_test:5}"
        summary_rows.append(row)
        if log_callback:
            log_callback(row)
        if progress_callback:
            progress_callback(idx / total_classes)

    yaml_path = None
    if gen_yaml:
        yaml_path = out_path / "data.yaml"
        names = list(all_files.keys())
        yaml_path.write_text(
            f"path: {out_path.resolve()}\ntrain: train\nval: val\ntest: test\n\nnc: {len(names)}\nnames: {names}\n",
            encoding="utf-8",
        )

    return {
        "total_imgs": total_imgs,
        "out_path": out_path,
        "yaml_path": yaml_path,
        "summary_rows": summary_rows,
    }
