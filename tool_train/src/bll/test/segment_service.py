from pathlib import Path
import time


def run_segment_preview(model_path: str, image_path: str, imgsz: int, conf: float, device: str):
    from ultralytics import YOLO
    from PIL import Image

    model_file = Path(model_path)
    image_file = Path(image_path)
    if not model_file.is_file():
        raise FileNotFoundError(f"Không tìm thấy model segment:\n{model_file}")
    if not image_file.is_file():
        raise FileNotFoundError(f"Không tìm thấy ảnh:\n{image_file}")

    t0 = time.perf_counter()
    model = YOLO(str(model_file), task="segment")
    results = model.predict(
        source=str(image_file),
        imgsz=int(imgsz),
        conf=float(conf),
        device=str(device),
        save=False,
        verbose=False,
    )
    infer_ms = (time.perf_counter() - t0) * 1000.0
    if not results:
        raise RuntimeError("Model segment không trả về kết quả.")
    result = results[0]
    rendered = result.plot()
    image = Image.fromarray(rendered[..., ::-1])
    boxes = result.boxes
    class_counts = {}
    total = 0
    if boxes is not None and hasattr(boxes, "cls") and boxes.cls is not None:
        for cls_id in boxes.cls.tolist():
            idx = int(cls_id)
            name = result.names.get(idx, f"cls{idx}")
            class_counts[name] = class_counts.get(name, 0) + 1
            total += 1
    mask_count = 0
    if getattr(result, "masks", None) is not None and getattr(result.masks, "data", None) is not None:
        try:
            mask_count = int(len(result.masks.data))
        except Exception:
            mask_count = total
    return {
        "image": image,
        "infer_ms": infer_ms,
        "total_objects": total,
        "mask_count": mask_count,
        "class_counts": class_counts,
        "model_name": model_file.name,
        "image_name": image_file.name,
    }
