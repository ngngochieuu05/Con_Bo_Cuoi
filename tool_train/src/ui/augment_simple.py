from __future__ import annotations

import shutil
from pathlib import Path

import albumentations as A
import cv2

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable


def _cv2_read_unicode(path: Path):
    import numpy as np

    data = np.fromfile(str(path), dtype=np.uint8)
    if data.size == 0:
        return None
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def _cv2_write_unicode(path: Path, image) -> bool:
    ext = path.suffix or ".png"
    ok, encoded = cv2.imencode(ext, image)
    if not ok:
        return False
    encoded.tofile(str(path))
    return True


def augment_dataset_simple(source_dir: str, output_dir: str, multiplier: int = 10) -> dict:
    source = Path(source_dir)
    output = Path(output_dir)
    if not source.is_dir():
        raise NotADirectoryError(f"Thu muc nguon khong ton tai: {source}")
    output.mkdir(parents=True, exist_ok=True)

    transform = A.Compose([
        A.Rotate(limit=25, p=0.7),
        A.HorizontalFlip(p=0.5),
        A.VerticalFlip(p=0.3),
        A.RandomBrightnessContrast(brightness_limit=0.25, contrast_limit=0.25, p=0.7),
        A.HueSaturationValue(hue_shift_limit=15, sat_shift_limit=25, val_shift_limit=20, p=0.6),
        A.GaussNoise(var_limit=(10, 40), p=0.4),
        A.CoarseDropout(max_holes=6, max_height=25, max_width=25, p=0.4),
        A.Resize(224, 224),
    ])

    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    total_original = 0
    total_augmented = 0
    total_skipped = 0

    for class_dir in sorted(source.iterdir()):
        if not class_dir.is_dir():
            continue

        dest_class = output / class_dir.name
        dest_class.mkdir(parents=True, exist_ok=True)

        images = [f for f in sorted(class_dir.iterdir()) if f.is_file() and f.suffix.lower() in exts]
        print(f"Class {class_dir.name}: {len(images)} anh")

        for img_path in tqdm(images, desc=class_dir.name):
            shutil.copy2(img_path, dest_class / img_path.name)
            total_original += 1

            image = _cv2_read_unicode(img_path)
            if image is None:
                total_skipped += max(0, multiplier - 1)
                print(f"[SKIP] Khong doc duoc anh: {img_path}")
                continue
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            for idx in range(max(0, multiplier - 1)):
                try:
                    aug = transform(image=image)["image"]
                    aug_bgr = cv2.cvtColor(aug, cv2.COLOR_RGB2BGR)
                    new_name = f"{img_path.stem}_aug{idx + 1}{img_path.suffix.lower()}"
                    save_path = dest_class / new_name
                    if _cv2_write_unicode(save_path, aug_bgr):
                        total_augmented += 1
                    else:
                        total_skipped += 1
                        print(f"[SKIP] Khong ghi duoc anh: {save_path}")
                except Exception as exc:
                    total_skipped += 1
                    print(f"[SKIP] Loi augment {img_path.name} #{idx + 1}: {exc}")

    print("\nHoan thanh!")
    print(f"  Anh goc      : {total_original}")
    print(f"  Anh augment  : {total_augmented}")
    print(f"  Bi skip      : {total_skipped}")
    print(f"  Output       : {output.resolve()}")

    return {
        "original_images": total_original,
        "augmented_images": total_augmented,
        "skipped": total_skipped,
        "output_dir": str(output.resolve()),
    }


if __name__ == "__main__":
    augment_dataset_simple(
        source_dir=r"D:\DACS\Dataset\desease\so_sanh\1.jilsa2022\class\Desease_Cattle_1-Jilsa-_Class.folder_yolo_v2",
        output_dir=r"D:\DACS\Dataset\desease\so_sanh\1.jilsa2022\class\augmented_10x",
        multiplier=10,
    )
