"""
diagnose_accuracy.py — Script chẩn đoán accuracy standalone
─────────────────────────────────────────────────────────────
Chạy: python diagnose_accuracy.py <model.pt> <test_folder>

Ví dụ:
  python diagnose_accuracy.py best.pt  D:/Dataset/test
  python diagnose_accuracy.py best.pt  D:/Dataset/jilsa/test

Yêu cầu cấu trúc thư mục test:
  test/
    LumpySkin/     ← tên folder = ground truth class
      img1.jpg
    Ringworm/
      img2.jpg
    Wart/
      img3.jpg

In ra:
  1. Tên class của model (model.names)
  2. Tên thư mục con trong test_folder (ground truth)
  3. Kết quả chuẩn hóa (normalize) của cả 2
  4. Accuracy thực tế cho từng class + tổng
  5. Log từng ảnh sai
"""
import sys
import re
from pathlib import Path
from collections import defaultdict


# ── Chuẩn hóa class name (giống TesterApp._normalize_class_name) ─────────────
def normalize(name: str) -> str:
    name = name.lower().strip()
    name = name.replace("cows", "").replace("cow", "")
    name = name.replace("_", " ").replace("-", " ")
    return " ".join(name.split())


def run(model_path: str, test_folder: str):
    from ultralytics import YOLO

    model = YOLO(model_path, task="classify")
    model_classes = {k: v for k, v in model.names.items()}
    model_classes_norm = {k: normalize(v) for k, v in model_classes.items()}

    print("\n" + "═" * 70)
    print("  MODEL CLASS NAMES")
    print("═" * 70)
    for idx, (cid, cname) in enumerate(sorted(model_classes.items())):
        print(f"  [{cid:>2}] raw='{cname}'   normalized='{model_classes_norm[cid]}'")

    # ── Liệt kê ground-truth folders ─────────────────────────────────────────
    test_dir = Path(test_folder)
    IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".gif"}

    gt_folders = sorted([d for d in test_dir.iterdir() if d.is_dir()])
    all_imgs = []
    for gf in gt_folders:
        imgs = [f for f in gf.rglob("*") if f.suffix.lower() in IMG_EXTS]
        all_imgs.extend((str(f), gf.name) for f in imgs)

    # Also top-level images (no sub-folder → unknown GT)
    top_imgs = [f for f in test_dir.iterdir()
                if f.is_file() and f.suffix.lower() in IMG_EXTS]

    print("\n" + "═" * 70)
    print("  GROUND TRUTH FOLDERS")
    print("═" * 70)
    if not gt_folders:
        print("  ⚠  Không tìm thấy thư mục con trong test_folder!")
        print("  Thư mục cần tổ chức theo: test/ClassName/img.jpg")
    for gf in gt_folders:
        imgs_in = [f for f in gf.rglob("*") if f.suffix.lower() in IMG_EXTS]
        print(f"  folder='{gf.name}'   normalized='{normalize(gf.name)}'   ({len(imgs_in)} ảnh)")
    if top_imgs:
        print(f"  ⚠  {len(top_imgs)} ảnh trực tiếp trong root (không có GT folder) — sẽ bỏ qua")

    if not all_imgs:
        print("\n⚠  Không tìm thấy ảnh! Kiểm tra lại cấu trúc thư mục.")
        return

    # ── Chạy predict ─────────────────────────────────────────────────────────
    print(f"\n{'═'*70}")
    print(f"  PREDICT {len(all_imgs)} ảnh...")
    print("═" * 70)

    sources = [img_path for img_path, _ in all_imgs]
    # NOTE: ultralytics trả r.path = "image0.jpg" khi source là list
    # → phải dùng index để map về path gốc

    results = model.predict(sources, imgsz=224, device="0", verbose=False, save=False)

    # ── Tính accuracy ─────────────────────────────────────────────────────────
    correct = total = 0
    cls_stats: dict = defaultdict(lambda: {"correct": 0, "total": 0})
    mismatches: list = []

    print(f"\n  {'#':>4}  {'File':<30}  {'GT':<18}  {'GT_norm':<18}  "
          f"{'Pred':<18}  {'Pred_norm':<18}  OK?")
    print("  " + "─" * 110)

    for idx, (r, (orig_path, true_name)) in enumerate(zip(results, all_imgs), 1):
        if r.probs is None:
            print(f"  {idx:>4}  {Path(orig_path).name:<30}  {'—':18}  [no probs]")
            continue

        img_path  = orig_path
        pred_id   = int(r.probs.top1)
        pred_name = str(r.names.get(pred_id, f"cls{pred_id}"))
        top1_conf = float(r.probs.top1conf) if hasattr(r.probs, "top1conf") else 0.0

        pred_norm = normalize(pred_name)
        true_norm = normalize(true_name)
        ok = (pred_norm == true_norm)

        total += 1
        cls_stats[true_name]["total"] += 1
        if ok:
            correct += 1
            cls_stats[true_name]["correct"] += 1
            flag = "✅"
        else:
            mismatches.append((true_name, pred_name, Path(img_path).name))
            flag = "❌"

        print(f"  {idx:>4}  {Path(img_path).name:<30}  {true_name:<18}  {true_norm:<18}"
              f"  {pred_name:<18}  {pred_norm:<18}  {flag}  ({top1_conf:.2%})")

    # ── Tổng kết ──────────────────────────────────────────────────────────────
    accuracy = correct / total * 100 if total > 0 else 0.0
    print("\n" + "═" * 70)
    print(f"  🎯 ACCURACY: {accuracy:.2f}%  ({correct}/{total})")
    print("─" * 70)
    for cls_name, stat in sorted(cls_stats.items()):
        cls_acc = stat["correct"] / stat["total"] * 100 if stat["total"] > 0 else 0.0
        bar = "█" * int(cls_acc / 5) + "░" * (20 - int(cls_acc / 5))
        print(f"  GT [{cls_name:<16}]  [{bar}]  {cls_acc:.2f}%  "
              f"({stat['correct']}/{stat['total']})")
    print("═" * 70)

    if mismatches:
        print(f"\n  ⚠  {len(mismatches)} ảnh SAI:")
        for true_n, pred_n, img in mismatches[:30]:
            print(f"     GT='{true_n}'  →  Pred='{pred_n}'  [{img}]")
        if len(mismatches) > 30:
            print(f"     ... và {len(mismatches) - 30} ảnh sai khác")

    if accuracy == 0.0 and total > 0:
        print("\n  ❗ ACCURACY = 0% — Nguyên nhân phổ biến:")
        print("     1. Tên thư mục (GT) không khớp với tên class của model")
        print("     2. Kiểm tra cột 'GT_norm' vs 'Pred_norm' ở trên")
        print("     3. Nếu GT_norm và Pred_norm không bao giờ match → cần thêm alias")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        print("\nUsage: python diagnose_accuracy.py <model.pt> <test_folder>")
        sys.exit(1)
    run(sys.argv[1], sys.argv[2])
