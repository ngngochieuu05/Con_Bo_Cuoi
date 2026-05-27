from __future__ import annotations

import shutil
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def copy_dataset_safe(
    source_dir: str,
    output_dir: str | None = None,
    add_class_prefix: bool = True,
    log_callback=None,
) -> dict:
    def log(msg: str):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    source = Path(source_dir)
    if not source.is_dir():
        raise NotADirectoryError(f"Thư mục nguồn không tồn tại: {source}")

    dest_root = Path(output_dir) if output_dir else source.parent / f"{source.name}_copied_safe"
    dest_root.mkdir(parents=True, exist_ok=True)

    log(f"📂 Nguồn  : {source}")
    log(f"📁 Đích   : {dest_root}\n")

    copied_count = 0
    skipped = 0

    for class_dir in sorted(source.iterdir()):
        if not class_dir.is_dir():
            continue

        class_name = class_dir.name
        dest_class = dest_root / class_name
        dest_class.mkdir(exist_ok=True)

        img_files = [f for f in class_dir.glob("*.*") if f.suffix.lower() in IMAGE_EXTS]
        log(f"  📌 Class [{class_name}] — {len(img_files)} ảnh")

        for img_file in sorted(img_files):
            new_name = f"{class_name}_{img_file.name}" if add_class_prefix else img_file.name
            dest_file = dest_class / new_name
            counter = 1
            original_dest = dest_file
            while dest_file.exists():
                dest_file = original_dest.with_name(
                    f"{original_dest.stem}_{counter}{original_dest.suffix}"
                )
                counter += 1

            try:
                shutil.copy2(img_file, dest_file)
                copied_count += 1
                if counter > 1:
                    log(f"    ⚠ Đổi tên tránh trùng: {img_file.name} → {dest_file.name}")
            except Exception as exc:
                log(f"    ✗ Lỗi copy {img_file.name}: {exc}")
                skipped += 1

    log("\n" + "=" * 60)
    log("✅ HOÀN THÀNH!")
    log(f"   Tổng ảnh đã copy : {copied_count}")
    log(f"   Bị skip           : {skipped}")
    log(f"   Thư mục đích      : {dest_root.resolve()}")
    log("=" * 60)

    return {
        "copied": copied_count,
        "skipped": skipped,
        "output_dir": str(dest_root.resolve()),
    }
