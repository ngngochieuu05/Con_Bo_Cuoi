"""
BLL — Tư Vấn AI (Farmer)
Nghiệp vụ nhận diện bệnh bò bằng YOLOv8 và tư vấn qua Gemini AI.

Tầng này KHÔNG được import bất kỳ thứ gì từ UI (flet).
Nhận: đường dẫn ảnh / np.ndarray / bytes
Trả:  dict kết quả thuần Python (base64 str, list, dict)
"""
from __future__ import annotations

import base64
import io
import threading
import uuid
from pathlib import Path
from typing import Any

# ─── Màu sắc nhãn lớp (dùng khi vẽ bbox + mask) ────────────────────────────
CLASS_COLORS = [
    "#ef4444", "#f97316", "#eab308", "#22c55e", "#14b8a6",
    "#3b82f6", "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16",
]

# ─── Module-level model cache (load 1 lần, dùng nhiều lần) ──────────────────
_model_cache: dict[str, Any] = {}
_cache_lock = threading.Lock()


# ─────────────────────────────────────────────────────────────────────────────
# PRIVATE: lazy imports (tránh crash nếu chưa cài thư viện)
# ─────────────────────────────────────────────────────────────────────────────

def _cv2():
    import cv2
    return cv2


def _pil():
    from PIL import Image, ImageDraw
    return Image, ImageDraw


def _np():
    import numpy as np
    return np


def _YOLO():
    from ultralytics import YOLO
    return YOLO


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC: LOAD MODEL
# ─────────────────────────────────────────────────────────────────────────────

def load_model(model_path: str, task: str = "segment") -> Any:
    """
    Load YOLO model với warm-up bắt buộc. Cached theo đường dẫn.
    Gọi an toàn nhiều lần — trả về cached instance nếu đã load.
    """
    with _cache_lock:
        if model_path in _model_cache:
            return _model_cache[model_path]

    # Tắt log ONNX Runtime nếu dùng .onnx
    try:
        import onnxruntime as _ort
        _ort.set_default_logger_severity(3)
    except Exception:
        pass

    YOLO = _YOLO()
    model = YOLO(model_path, task=task)

    # Warm-up BẮT BUỘC — tránh ORT tạo lại session khi predict thật
    np = _np()
    dummy = np.zeros((640, 640, 3), dtype=np.uint8)
    model.predict(source=dummy, imgsz=640, device="0", verbose=False)

    with _cache_lock:
        _model_cache[model_path] = model

    return model


def get_disease_model() -> tuple[Any, dict]:
    """
    Lấy model disease (loai_mo_hinh='disease') từ DAL model_repo.
    Trả về (YOLO instance, model_record dict).
    Raise FileNotFoundError nếu chưa cấu hình đường dẫn.
    Raise RuntimeError nếu không tìm thấy record trong DB.
    """
    from dal.model_repo import get_model_by_type
    rec = get_model_by_type("disease")
    if not rec:
        raise RuntimeError("Không tìm thấy model disease trong DB.")
    path = rec.get("duong_dan_file", "").strip()
    if not path or not Path(path).exists():
        raise FileNotFoundError(
            f"File model không tồn tại: '{path}'\n"
            "Vui lòng cập nhật đường dẫn model trong phần Quản lý Mô hình."
        )
    task = "segment" if "seg" in Path(path).stem.lower() else "detect"
    model = load_model(path, task=task)
    return model, rec


def clear_model_cache() -> None:
    """Xoá cache model (dùng khi admin cập nhật model mới)."""
    with _cache_lock:
        _model_cache.clear()
    try:
        import torch
        torch.cuda.empty_cache()
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC: INFERENCE
# ─────────────────────────────────────────────────────────────────────────────

def run_inference(model, source, conf: float = 0.01, iou: float = 0.45,
                  imgsz: int = 640, device: str = "0", half: bool = False):
    """
    Chạy YOLOv8 inference một lần với conf cố định.
    Dùng nội bộ bởi predict_dynamic_conf().
    """
    return model.predict(
        source=source,
        conf=conf,
        iou=iou,
        imgsz=imgsz,
        device=device,
        half=half and device != "cpu",
        save=False,
        verbose=False,
    )[0]


def predict_dynamic_conf(
    model,
    source,
    start_conf: float = 0.50,
    min_conf: float = 0.05,
    step: float = 0.05,
    iou: float = 0.45,
    imgsz: int = 640,
    device: str = "0",
):
    """
    Tự động hạ Confidence Score cho đến khi tìm thấy box/mask.

    Thuật toán:
        1. Thử predict với start_conf (ví dụ 0.50)
        2. Nếu KHÔNG có box → hạ conf xuống (step=0.05) và thử lại
        3. Lặp cho đến khi tìm thấy box HOẶC đạt min_conf

    Returns:
        (result, final_conf)
        - result:     kết quả inference (ultralytics Result object)
        - final_conf: mức conf tại đó tìm thấy box;
                      0.0 nếu không tìm thấy gì (bò khỏe mạnh)
    """
    current_conf = round(start_conf, 4)
    last_result = None

    while current_conf >= min_conf - 1e-9:
        result = run_inference(
            model, source,
            conf=current_conf,
            iou=iou,
            imgsz=imgsz,
            device=device,
        )
        last_result = result

        boxes = result.boxes
        if boxes is not None and len(boxes) > 0:
            return result, current_conf

        current_conf = round(current_conf - step, 4)

    # Không tìm thấy bất kỳ mức conf nào
    return last_result, 0.0


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC: XÂY DỰNG KẾT QUẢ
# ─────────────────────────────────────────────────────────────────────────────

def build_diagnosis(result, conf_thresh: float = 0.25) -> dict:
    """
    Trả về dict chẩn đoán:
        detected:      list[{class, confidence}] — sort by conf giảm dần
        not_detected:  list[str]
        total_classes: int
        n_objects:     int — số bbox >= conf_thresh
    """
    names: dict = getattr(result, "names", None) or {}
    if result.boxes is None:
        return {
            "detected": [],
            "not_detected": list(names.values()),
            "total_classes": len(names),
            "n_objects": 0,
        }

    best: dict[int, float] = {}
    n_objects = 0
    for box in result.boxes:
        conf = float(box.conf[0])
        cls_id = int(box.cls[0])
        if conf >= conf_thresh:
            n_objects += 1
            if cls_id not in best or conf > best[cls_id]:
                best[cls_id] = conf

    detected = sorted(
        [{"class": names.get(cid, f"cls{cid}"), "confidence": round(c, 3)}
         for cid, c in best.items()],
        key=lambda x: -x["confidence"],
    )
    detected_names = {d["class"] for d in detected}
    not_detected = [n for n in names.values() if n not in detected_names]

    return {
        "detected": detected,
        "not_detected": not_detected,
        "total_classes": len(names),
        "n_objects": n_objects,
    }


def build_predictions_json(result, conf_thresh: float = 0.25) -> dict:
    """
    Schema JSON tương thích Roboflow.
    Gồm x, y, width, height, confidence, class, class_id, detection_id.
    Kèm 'points' (polygon) nếu có mask (segmentation).
    """
    names: dict = getattr(result, "names", None) or {}
    has_masks = result.masks is not None
    preds = []

    if result.boxes is None:
        return {"predictions": []}

    for i, box in enumerate(result.boxes):
        conf = float(box.conf[0])
        if conf < conf_thresh:
            continue
        cls_id = int(box.cls[0])
        cx, cy, w, h = box.xywh[0].tolist()
        pred = {
            "x":            round(cx, 1),
            "y":            round(cy, 1),
            "width":        round(w, 1),
            "height":       round(h, 1),
            "confidence":   round(conf, 3),
            "class":        names.get(cls_id, f"cls{cls_id}"),
            "class_id":     cls_id,
            "detection_id": str(uuid.uuid4()),
        }
        if has_masks and result.masks.xy is not None and i < len(result.masks.xy):
            poly = result.masks.xy[i]
            if len(poly) >= 3:
                pred["points"] = [
                    {"x": round(float(p[0]), 1), "y": round(float(p[1]), 1)}
                    for p in poly
                ]
        preds.append(pred)

    return {"predictions": preds}


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC: VẼ KẾT QUẢ → PIL.Image
# ─────────────────────────────────────────────────────────────────────────────

def draw_result(result, conf_thresh: float = 0.25,
                opacity: int = 70, is_seg: bool = True) -> Any:
    """
    Vẽ bbox + polygon mask lên ảnh gốc.
    Trả về PIL.Image (RGB). Không dùng result.plot() để kiểm soát conf filter.

    Ghi chú quan trọng:
    - orig_img có thể là BGR (OpenCV) hoặc CHW / NCHW — cần chuẩn hoá
    - alpha = opacity/100 * 255, áp lên mask polygon RGBA
    """
    cv2 = _cv2()
    Image, ImageDraw = _pil()
    np = _np()

    orig = result.orig_img
    if orig is None:
        return Image.new("RGB", (640, 480), "black")

    # Chuẩn hoá shape
    if orig.ndim == 4:
        orig = orig[0]
    if orig.ndim == 3 and orig.shape[0] in (1, 3, 4) and orig.shape[0] < orig.shape[1]:
        orig = np.transpose(orig, (1, 2, 0))    # CHW → HWC
    if orig.dtype != np.uint8:
        mx = orig.max()
        orig = (orig * (255.0 / mx if mx > 1.0 else 255.0)).clip(0, 255).astype(np.uint8)

    img_rgb = cv2.cvtColor(orig, cv2.COLOR_BGR2RGB)
    base = Image.fromarray(img_rgb).convert("RGBA")
    names: dict = getattr(result, "names", None) or {}
    alpha = int(max(0, min(100, opacity)) / 100.0 * 255)

    # Lọc box đạt ngưỡng
    valid: list[tuple[int, Any]] = []
    if result.boxes is not None:
        for i, box in enumerate(result.boxes):
            if float(box.conf[0]) >= conf_thresh:
                valid.append((i, box))

    # Vẽ polygon mask (segmentation)
    if is_seg and result.masks is not None:
        polys = result.masks.xy
        for i, box in valid:
            if i >= len(polys) or len(polys[i]) < 3:
                continue
            cls_id = int(box.cls[0])
            ch = CLASS_COLORS[cls_id % len(CLASS_COLORS)]
            r_c, g_c, b_c = int(ch[1:3], 16), int(ch[3:5], 16), int(ch[5:7], 16)
            pts = [(float(x), float(y)) for x, y in polys[i]]
            layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
            ImageDraw.Draw(layer).polygon(pts, fill=(r_c, g_c, b_c, alpha))
            base = Image.alpha_composite(base, layer)

    # Vẽ bbox + label
    draw = ImageDraw.Draw(base)
    for i, box in valid:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        name = names.get(cls_id, f"cls{cls_id}")
        lbl = f"{name}  {conf:.0%}"
        ch = CLASS_COLORS[cls_id % len(CLASS_COLORS)]
        r_c, g_c, b_c = int(ch[1:3], 16), int(ch[3:5], 16), int(ch[5:7], 16)
        x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
        for th in range(3):
            draw.rectangle([x1 - th, y1 - th, x2 + th, y2 + th],
                           outline=(r_c, g_c, b_c, 255))
        tw = len(lbl) * 6 + 8
        draw.rectangle([x1, y1 - 20, x1 + tw, y1], fill=(r_c, g_c, b_c, 210))
        draw.text((x1 + 4, y1 - 18), lbl, fill=(255, 255, 255, 255))

    return base.convert("RGB")


def pil_to_base64(pil_img, quality: int = 85) -> str:
    """
    Chuyển PIL.Image → base64 string.
    Dùng với ft.Image(src_base64=...) trong Flet.
    KHÔNG dùng với ft.Image(src=...) — sẽ không hiển thị.
    """
    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode()


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC: GEMINI AI
# ─────────────────────────────────────────────────────────────────────────────

def build_gemini_prompt(diagnosis: dict) -> str:
    """Xây dựng prompt tư vấn bệnh cho Gemini AI từ kết quả chẩn đoán."""
    detected = diagnosis.get("detected", [])
    not_detected = diagnosis.get("not_detected", [])

    lines_det = "\n".join(
        f"  - {d['class']} (confidence: {d['confidence']:.0%})" for d in detected
    ) or "  (không có)"
    lines_not = "\n".join(f"  - {c}" for c in not_detected) or "  (không có)"

    return (
        "Bạn là bác sĩ thú y chuyên về bệnh ở bò. "
        "Hệ thống AI thị giác (YOLOv8) đã phân tích ảnh và cho kết quả:\n\n"
        f"✅ Phát hiện:\n{lines_det}\n\n"
        f"❌ Không phát hiện:\n{lines_not}\n\n"
        "Dựa vào kết quả trên, hãy:\n"
        "1. Nhận xét tình trạng sức khỏe con bò\n"
        "2. Mô tả ngắn gọn từng bệnh được phát hiện (triệu chứng, mức độ nguy hiểm)\n"
        "3. Đề xuất hướng xử lý / điều trị\n"
        "Trả lời bằng tiếng Việt, ngắn gọn và chuyên nghiệp."
    )


def call_gemini(api_key: str, prompt: str) -> str:
    """Gọi Gemini API đồng bộ. Chạy trong thread riêng từ caller."""
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    resp = model.generate_content(prompt)
    return resp.text


def call_gemini_async(api_key: str, prompt: str,
                      callback) -> None:
    """
    Gọi Gemini bất đồng bộ.
    callback(text: str) được gọi trên thread phụ sau khi có kết quả.
    Trong Flet: cần gọi page.update() bên trong callback.
    """
    def _do():
        try:
            callback(call_gemini(api_key, prompt))
        except Exception as ex:
            callback(f"❌ Lỗi Gemini: {ex}")

    threading.Thread(target=_do, daemon=True).start()


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC: HIGH-LEVEL API (dùng trực tiếp từ UI layer)
# ─────────────────────────────────────────────────────────────────────────────

def analyze_image_async(
    img_source,             # str path | np.ndarray | bytes
    conf_thresh: float,
    on_result,              # callback(result_dict: dict)
    on_error,               # callback(msg: str)
    device: str = "0",
    imgsz: int = 640,
) -> None:
    """
    Pipeline đầy đủ chạy không đồng bộ trong thread riêng:
      1. get_disease_model() — lấy model từ DAL, load + cache
      2. run_inference(conf=0.01) — lấy toàn bộ raw boxes
      3. draw_result() → PIL.Image → base64
      4. build_diagnosis() + build_predictions_json()
      5. Trả về qua on_result(dict)

    result_dict schema:
        annotated_b64:  str       — base64 JPEG
        diagnosis:      dict      — detected / not_detected / n_objects
        predictions:    dict      — JSON Roboflow-compatible
        conf_thresh:    float     — mức conf thực tế tìm thấy box (0.0 = không thấy)
        model_name:     str
        is_seg:         bool
    """
    def _do():
        try:
            model, rec = get_disease_model()
            iou_model  = float(rec.get("iou", 0.45))
            is_seg     = getattr(model, "task", "detect") == "segment"

            # bytes → np.ndarray
            np = _np()
            if isinstance(img_source, (bytes, bytearray)):
                cv2 = _cv2()
                nparr = np.frombuffer(img_source, np.uint8)
                source = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            else:
                source = img_source

            # ── Dynamic Confidence: tự động hạ conf cho đến khi thấy box ──
            result, final_conf = predict_dynamic_conf(
                model, source,
                start_conf=conf_thresh,   # conf_thresh là điểm xuất phát
                min_conf=0.05,
                step=0.05,
                iou=iou_model,
                imgsz=imgsz,
                device=device,
            )

            # Dùng final_conf để vẽ + build kết quả
            # Nếu final_conf == 0.0 → không thấy gì, vẫn trả về (bò khỏe)
            draw_conf = final_conf if final_conf > 0 else conf_thresh
            pil_img        = draw_result(result, conf_thresh=draw_conf,
                                         opacity=70, is_seg=is_seg)
            annotated_b64  = pil_to_base64(pil_img, quality=85)
            diagnosis      = build_diagnosis(result, draw_conf)
            predictions    = build_predictions_json(result, draw_conf)

            on_result({
                "annotated_b64": annotated_b64,
                "diagnosis":     diagnosis,
                "predictions":   predictions,
                "conf_thresh":   final_conf,
                "model_name":    rec.get("ten_mo_hinh", "Disease Model"),
                "is_seg":        is_seg,
            })

        except FileNotFoundError as e:
            on_error(f"⚠️ Chưa cấu hình model: {e}")
        except Exception as e:
            import traceback
            on_error(f"❌ Lỗi phân tích: {e}\n{traceback.format_exc()}")

    threading.Thread(target=_do, daemon=True).start()
