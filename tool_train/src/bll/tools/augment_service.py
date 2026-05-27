from __future__ import annotations

from pathlib import Path

from bll.tools.copy_service import IMAGE_EXTS

AUGMENT_PIPELINES = {
    "rotate": {"label": "Rotate", "note": "Xoay anh nhe quanh tam."},
    "zoom": {"label": "Zoom", "note": "Phong to hoac thu nho nhe."},
    "hflip": {"label": "HFlip", "note": "Lat ngang anh."},
    "vflip": {"label": "VFlip", "note": "Lat doc anh."},
    "brightness": {"label": "Brightness", "note": "Tang giam do sang."},
    "contrast": {"label": "Contrast", "note": "Tang giam do tuong phan."},
    "hsv": {"label": "HSV", "note": "Doi hue, saturation, value."},
    "noise": {"label": "Noise", "note": "Them nhieu hat vao anh."},
    "dropout": {"label": "Dropout", "note": "Che ngau nhien mot vai vung."},
}


def iter_class_roots(source: Path) -> list[tuple[str | None, Path]]:
    split_dirs = [
        d for d in sorted(source.iterdir())
        if d.is_dir() and d.name.lower() in {"train", "val", "valid", "test"}
    ]
    if split_dirs:
        roots = []
        for split_dir in split_dirs:
            for class_dir in sorted(split_dir.iterdir()):
                if class_dir.is_dir():
                    roots.append((split_dir.name, class_dir))
        return roots
    return [(None, class_dir) for class_dir in sorted(source.iterdir()) if class_dir.is_dir()]


def cv2_read_unicode(path: Path):
    import cv2
    import numpy as np

    data = np.fromfile(str(path), dtype=np.uint8)
    if data.size == 0:
        return None
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def cv2_write_unicode(path: Path, image) -> bool:
    import cv2

    ext = path.suffix or ".png"
    ok, encoded = cv2.imencode(ext, image)
    if not ok:
        return False
    encoded.tofile(str(path))
    return True


def normalize_augment_options(options: dict | None) -> dict:
    normalized = {key: True for key in AUGMENT_PIPELINES}
    if options:
        for key in normalized:
            if key in options:
                normalized[key] = bool(options[key])
    return normalized


def normalize_pipeline_multipliers(multipliers: dict | None, fallback_multiplier: int = 4) -> dict:
    normalized = {key: max(1, int(fallback_multiplier)) for key in AUGMENT_PIPELINES}
    if multipliers:
        for key in normalized:
            if key in multipliers:
                try:
                    normalized[key] = max(1, int(multipliers[key]))
                except (TypeError, ValueError):
                    normalized[key] = max(1, int(fallback_multiplier))
    return normalized


def build_single_pipeline_transform(A, pipeline_key: str):
    if pipeline_key == "rotate":
        return A.Rotate(limit=25, p=1.0)
    if pipeline_key == "zoom":
        return A.Affine(scale=(0.85, 1.15), translate_percent=0.0, rotate=0, shear=0, p=1.0)
    if pipeline_key == "hflip":
        return A.HorizontalFlip(p=1.0)
    if pipeline_key == "vflip":
        return A.VerticalFlip(p=1.0)
    if pipeline_key == "brightness":
        return A.RandomBrightnessContrast(brightness_limit=0.25, contrast_limit=0.0, p=1.0)
    if pipeline_key == "contrast":
        return A.RandomBrightnessContrast(brightness_limit=0.0, contrast_limit=0.25, p=1.0)
    if pipeline_key == "hsv":
        return A.HueSaturationValue(hue_shift_limit=15, sat_shift_limit=25, val_shift_limit=20, p=1.0)
    if pipeline_key == "noise":
        return A.GaussNoise(var_limit=(10, 40), p=1.0)
    if pipeline_key == "dropout":
        return A.CoarseDropout(max_holes=6, max_height=25, max_width=25, p=1.0)
    raise KeyError(f"Khong ho tro pipeline: {pipeline_key}")


def build_albumentations_pipelines(
    image_width: int,
    image_height: int,
    options: dict | None = None,
    multipliers: dict | None = None,
    fallback_multiplier: int = 4,
):
    import albumentations as A

    enabled = normalize_augment_options(options)
    normalized_multipliers = normalize_pipeline_multipliers(
        multipliers,
        fallback_multiplier=fallback_multiplier,
    )
    pipelines = []
    resize = A.Resize(height=max(8, int(image_height)), width=max(8, int(image_width)))
    for key, meta in AUGMENT_PIPELINES.items():
        if enabled.get(key):
            pipelines.append(
                (
                    key,
                    meta["label"],
                    normalized_multipliers[key],
                    A.Compose([build_single_pipeline_transform(A, key), resize]),
                )
            )
    return pipelines, enabled, normalized_multipliers


def count_dataset_images(source: Path) -> int:
    class_roots = iter_class_roots(source)
    count = 0
    for _, class_dir in class_roots:
        for img_path in class_dir.iterdir():
            if img_path.is_file() and img_path.suffix.lower() in IMAGE_EXTS:
                count += 1
    return count


def augment_dataset_albumentations(
    source_dir: str,
    output_dir: str,
    multiplier: int = 4,
    keep_original: bool = True,
    image_width: int = 224,
    image_height: int = 224,
    options: dict | None = None,
    pipeline_multipliers: dict | None = None,
    log_callback=None,
    should_stop=None,
) -> dict:
    def log(msg: str):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    source = Path(source_dir)
    if not source.is_dir():
        raise NotADirectoryError(f"Thu muc nguon khong ton tai: {source}")
    dest_root = Path(output_dir)
    dest_root.mkdir(parents=True, exist_ok=True)

    try:
        import cv2  # noqa: F401
        import albumentations  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "Chua cai albumentations/cv2. Cai dat: pip install albumentations opencv-python"
        ) from exc

    pipeline_transforms, enabled_options, normalized_multipliers = build_albumentations_pipelines(
        image_width=image_width,
        image_height=image_height,
        options=options,
        multipliers=pipeline_multipliers,
        fallback_multiplier=multiplier,
    )

    class_roots = iter_class_roots(source)
    if not class_roots:
        raise FileNotFoundError("Khong tim thay class folder trong dataset.")

    image_items = []
    for split_name, class_dir in class_roots:
        for img_path in sorted(class_dir.iterdir()):
            if img_path.is_file() and img_path.suffix.lower() in IMAGE_EXTS:
                image_items.append((split_name, class_dir.name, img_path))
    if not image_items:
        raise FileNotFoundError("Khong tim thay anh trong dataset.")
    if not pipeline_transforms:
        raise ValueError("Hay chon it nhat 1 pipeline augment.")

    copied = 0
    augmented = 0
    skipped = 0
    total_augments_per_image = sum(multiplier_value for _, _, multiplier_value, _ in pipeline_transforms)
    total_ops = len(image_items) * (total_augments_per_image + (1 if keep_original else 0))
    done_ops = 0

    log(f"Dataset nguon : {source.resolve()}")
    log(f"Thu muc dich  : {dest_root.resolve()}")
    log(f"So anh goc    : {len(image_items)}")
    log("So ban/pipeline:")
    for key, meta in AUGMENT_PIPELINES.items():
        if enabled_options.get(key):
            log(f"  - {meta['label']}: {normalized_multipliers[key]}")
    log(f"Resize        : {image_width}x{image_height}")
    enabled_names = [meta["label"] for key, meta in AUGMENT_PIPELINES.items() if enabled_options.get(key)]
    log(f"Pipeline      : {' + '.join(enabled_names) if enabled_names else 'Khong bat pipeline nao'}")
    log("")

    for split_name, class_name, img_path in image_items:
        if should_stop and should_stop():
            log("[STOP] Da nhan yeu cau dung.")
            break

        split_dest = dest_root / split_name if split_name else dest_root
        dest_class_dir = split_dest / class_name
        dest_class_dir.mkdir(parents=True, exist_ok=True)

        image = cv2_read_unicode(img_path)
        if image is None:
            log(f"[WARN] Bo qua anh loi: {img_path.name}")
            skipped += 1
            continue

        stem = img_path.stem
        suffix = img_path.suffix.lower() or ".jpg"

        if keep_original:
            dest_original = dest_class_dir / img_path.name
            if cv2_write_unicode(dest_original, image):
                copied += 1
            else:
                skipped += 1
                log(f"[WARN] Khong ghi duoc anh goc: {dest_original.name}")
            done_ops += 1

        for pipeline_key, pipeline_name, pipeline_count, transform in pipeline_transforms:
            for idx in range(pipeline_count):
                if should_stop and should_stop():
                    log("[STOP] Da nhan yeu cau dung.")
                    break
                try:
                    transformed = transform(image=image)["image"]
                    out_name = f"{stem}_{pipeline_key}_{idx + 1}{suffix}"
                    out_path = dest_class_dir / out_name
                    if cv2_write_unicode(out_path, transformed):
                        augmented += 1
                    else:
                        skipped += 1
                        log(f"[WARN] Khong ghi duoc anh augment: {out_name}")
                except Exception as exc:
                    skipped += 1
                    log(f"[WARN] Loi augment {img_path.name} [{pipeline_name} #{idx + 1}]: {exc}")
                finally:
                    done_ops += 1
            if should_stop and should_stop():
                break

        if total_ops > 0:
            percent = min(100.0, (done_ops / total_ops) * 100.0)
            log(f"[PROGRESS] {percent:.1f}% | {class_name} | {img_path.name}")

    total_created = copied + augmented
    stopped = bool(should_stop and should_stop())
    if stopped:
        log("[DONE] Da dung theo yeu cau nguoi dung.")
    else:
        log("[DONE] Hoan thanh augment dataset.")

    return {
        "original_images": len(image_items),
        "copied": copied,
        "augmented": augmented,
        "skipped": skipped,
        "total_created": total_created,
        "output_dir": str(dest_root.resolve()),
        "stopped": stopped,
    }
