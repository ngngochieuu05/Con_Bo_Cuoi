"""
BLL — Tư Vấn AI (Farmer)
Nghiệp vụ nhận diện bệnh bò bằng YOLOv8 và tư vấn qua Gemini AI.

Tầng này KHÔNG được import bất kỳ thứ gì từ UI (flet).
Nhận: đường dẫn ảnh / np.ndarray / bytes
Trả:  dict kết quả thuần Python (base64 str, list, dict)
"""
from __future__ import annotations

import base64
import concurrent.futures
import io
import os
import re
import threading
import unicodedata
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


def _get_configured_mode() -> str:
    """
    Đọc YOLO device mode live: config file > env var > 'cpu' default.
    Trả về lowercase string đã strip.
    """
    try:
        from bll.services.monitor_service import load_config
        mode = str(load_config().get("yolo_model_mode") or "").strip().lower()
        if mode in ("cpu", "gpu", "cuda", "auto"):
            return mode
    except Exception:
        pass
    return os.getenv("YOLO_DEVICE_MODE", "cpu").strip().lower()


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


def _resolve_device(device_mode: str | None = None) -> str:
    """
    Chuẩn hoá device cho Ultralytics.

    Modes:
    - cpu: luôn CPU (default)
    - gpu/cuda: ép GPU=0, fallback CPU nếu CUDA không khả dụng
    - auto: ưu tiên CPU, fallback GPU (user-specified semantics)
    - "0", "0,1", v.v.: giữ nguyên (multi-GPU)

    Nếu device_mode là None/empty → đọc live từ config (_get_configured_mode).
    """
    raw = str(device_mode or "").strip().strip("\"'").lower()
    mode = raw or _get_configured_mode()

    if mode == "cpu":
        return "cpu"

    if mode in ("gpu", "cuda"):
        try:
            import torch
            if torch.cuda.is_available() and torch.cuda.device_count() > 0:
                return "0"
        except Exception:
            pass
        return "cpu"

    if mode == "auto":
        # User spec: prefer CPU, fallback GPU.
        # Vì CPU luôn available → thực tế auto ≡ cpu.
        return "cpu"

    # Giá trị hợp lệ khác (vd "0", "0,1") giữ nguyên
    return mode


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
    warmup_device = _resolve_device(None)  # đọc live từ config
    model.predict(source=dummy, imgsz=640, device=warmup_device, verbose=False)

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


def get_optional_disease_cls_model() -> tuple[Any | None, dict | None]:
    """Lấy model classification cho bệnh nếu đã cấu hình và đang online."""
    from dal.model_repo import get_model_by_type

    rec = get_model_by_type("disease_cls")
    if not rec:
        return None, None
    if str(rec.get("trang_thai", "offline")).lower() != "online":
        return None, rec

    path = str(rec.get("duong_dan_file", "") or "").strip()
    if not path or not Path(path).exists():
        return None, rec

    model = load_model(path, task="classify")
    return model, rec


def get_optional_health_cls_model() -> tuple[Any | None, dict | None]:
    """Lấy model classification lọc bò khỏe/bị bệnh nếu đã cấu hình và đang online."""
    from dal.model_repo import get_model_by_type

    rec = get_model_by_type("health_cls")
    if not rec:
        return None, None
    if str(rec.get("trang_thai", "offline")).lower() != "online":
        return None, rec

    path = str(rec.get("duong_dan_file", "") or "").strip()
    if not path or not Path(path).exists():
        return None, rec

    model = load_model(path, task="classify")
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


def run_inference(
    model,
    source,
    conf: float = 0.01,
    iou: float = 0.45,
    imgsz: int = 640,
    device: str = "auto",
    half: bool = False,
):
    """
    Chạy YOLOv8 inference một lần với conf cố định.
    Dùng nội bộ bởi predict_dynamic_conf().
    """
    resolved_device = _resolve_device(device)
    return model.predict(
        source=source,
        conf=conf,
        iou=iou,
        imgsz=imgsz,
        device=resolved_device,
        half=half and resolved_device != "cpu",
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
    device: str = "auto",
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


def build_classification_summary(result, top_k: int = 3) -> dict:
    """Tóm tắt kết quả classification từ YOLO classify."""
    probs = getattr(result, "probs", None)
    names: dict = getattr(result, "names", None) or {}
    if probs is None:
        return {"top1": None, "topk": []}

    top1_idx = getattr(probs, "top1", None)
    top1_conf = getattr(probs, "top1conf", None)
    top1 = None
    if top1_idx is not None and top1_conf is not None:
        conf_val = float(top1_conf.item() if hasattr(top1_conf, "item") else top1_conf)
        top1 = {
            "class": names.get(int(top1_idx), f"cls{top1_idx}"),
            "confidence": round(conf_val, 3),
        }

    topk_items: list[dict] = []
    top5 = getattr(probs, "top5", None) or []
    top5conf = getattr(probs, "top5conf", None)
    conf_list = []
    if top5conf is not None:
        conf_list = [
            float(v.item() if hasattr(v, "item") else v)
            for v in list(top5conf)
        ]
    for idx, cls_idx in enumerate(list(top5)[:top_k]):
        conf_val = conf_list[idx] if idx < len(conf_list) else 0.0
        topk_items.append({
            "class": names.get(int(cls_idx), f"cls{cls_idx}"),
            "confidence": round(conf_val, 3),
        })

    return {"top1": top1, "topk": topk_items}


def _normalize_class_name(value: str | None) -> str:
    text = str(value or "").strip().lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]+", "", text)


def _is_healthy_gate_prediction(cls_summary: dict | None) -> bool:
    top1 = (cls_summary or {}).get("top1") or {}
    cls_name = _normalize_class_name(top1.get("class"))
    if not cls_name:
        return False
    healthy_tokens = {
        "healthy", "healthycow", "healthycows", "normal", "binhthuong",
        "khoe", "khoemanh", "khongbenh", "nobenh", "nodisease", "none",
    }
    unhealthy_tokens = {
        "disease", "diseased", "sick", "ill", "benh", "cowdisease",
        "sickcow", "lumpy", "lesion", "infected",
    }
    if cls_name in healthy_tokens:
        return True
    if cls_name in unhealthy_tokens:
        return False
    return any(token in cls_name for token in healthy_tokens) and not any(
        token in cls_name for token in unhealthy_tokens
    )


def draw_classification_result(result, cls_summary: dict | None) -> Any:
    """Tạo ảnh tóm tắt classification từ ảnh gốc với panel kết quả."""
    Image, ImageDraw = _pil()
    np = _np()
    cv2 = _cv2()

    orig = getattr(result, "orig_img", None)
    if orig is None:
        canvas = Image.new("RGB", (640, 480), "#111827")
    else:
        if orig.ndim == 4:
            orig = orig[0]
        if orig.ndim == 3 and orig.shape[0] in (1, 3, 4) and orig.shape[0] < orig.shape[1]:
            orig = np.transpose(orig, (1, 2, 0))
        if orig.dtype != np.uint8:
            mx = orig.max()
            orig = (orig * (255.0 / mx if mx > 1.0 else 255.0)).clip(0, 255).astype(np.uint8)
        img_rgb = cv2.cvtColor(orig, cv2.COLOR_BGR2RGB)
        canvas = Image.fromarray(img_rgb).convert("RGBA")

    top1 = (cls_summary or {}).get("top1")
    topk = list((cls_summary or {}).get("topk") or [])
    if not top1 and not topk:
        return canvas.convert("RGB")

    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = canvas.size
    panel_top = max(0, height - 118)
    draw.rounded_rectangle(
        [14, panel_top, width - 14, height - 14],
        radius=18,
        fill=(15, 23, 42, 210),
        outline=(56, 189, 248, 220),
        width=2,
    )
    draw.text((28, panel_top + 18), "Classification", fill=(186, 230, 253, 255))
    if top1:
        draw.text(
            (28, panel_top + 44),
            f"Top 1: {top1['class']} ({top1['confidence']:.0%})",
            fill=(255, 255, 255, 255),
        )
    if topk:
        ranking = "  |  ".join(
            f"{item['class']} {item['confidence']:.0%}" for item in topk[:3]
        )
        draw.text((28, panel_top + 72), ranking, fill=(191, 219, 254, 255))

    return Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")


def _merge_diagnosis_with_classification(diagnosis: dict, cls_summary: dict | None) -> dict:
    merged = {
        "detected": list(diagnosis.get("detected", [])),
        "not_detected": list(diagnosis.get("not_detected", [])),
        "total_classes": diagnosis.get("total_classes", 0),
        "n_objects": diagnosis.get("n_objects", 0),
        "classification": cls_summary or {"top1": None, "topk": []},
    }
    top1 = (cls_summary or {}).get("top1")
    if not top1:
        return merged

    detected = list(merged["detected"])
    existing_names = {d.get("class") for d in detected}
    if top1["class"] not in existing_names:
        detected.insert(0, {
            "class": top1["class"],
            "confidence": top1["confidence"],
            "source": "classification",
        })
    else:
        for item in detected:
            if item.get("class") == top1["class"]:
                item["classification_confidence"] = top1["confidence"]
                break

    merged["detected"] = detected
    merged["not_detected"] = [
        name for name in merged["not_detected"]
        if name != top1["class"]
    ]
    merged["classification_top1"] = top1["class"]
    merged["classification_confidence"] = top1["confidence"]
    return merged


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

_SYSTEM_FEATURE_GUIDE = """
Cac kha nang thuc te cua he thong Con Bo Cuoi:
- Tu van AI: nhan anh bo, sang loc bo khoe/benh, neu nghi benh thi phan loai benh va ve mask vung ton thuong.
- Tu van chuyen gia: farmer chon chuyen gia thu y trong he thong, xem nhanh ho so roi nhan truc tiep.
- Giam sat truc tiep: theo doi camera chuong trai hoac video/anh test, phat hien hanh vi va canh bao.
- Lich su: luu lai phien giam sat, lich su tu van AI, tin nhan va anh da gui.
- Cai dat farmer: cau hinh dia chi may chu, camera chup anh, camera giam sat, lien ket Telegram.
- Cai dat admin: cau hinh che do desktop/web, Gemini API key, YOLO mode va thong so he thong.
- Telegram: nguoi dung co the lien ket bot de nhan canh bao bo bat thuong.
""".strip()

_RESPONSE_RULES = """
Quy tac tra loi:
- Chi duoc tra loi ve bo, chan nuoi bo, benh bo, thu y bo, camera giam sat, canh bao, AI nhan dien va cach dung he thong Con Bo Cuoi.
- Khong tra loi cac chu de ngoai pham vi. Neu lech chu de, tu choi ngan gon va huong nguoi dung quay lai dung pham vi.
- Khong bia ra chuc nang khong ton tai trong he thong.
- Uu tien huong dan thao tac that cu the, theo tung buoc ngan, de lam.
- Khi co dau hieu khan cap, phai neu ro can lien he thu y/chuyen gia som.
- Tra loi bang tieng Viet co dau, ro rang, co cau truc, nhung khong dai dong vo ich.
""".strip()


def _format_chat_history(history: list[dict] | None, limit: int = 8) -> str:
    history = history or []
    turns: list[str] = []
    for item in history[-limit:]:
        sender = "Người dùng" if item.get("sender") == "farmer" else "Trợ lý"
        msg_text = str(item.get("text") or "").strip()
        if msg_text:
            turns.append(f"{sender}: {msg_text}")
    return "\n".join(turns) if turns else "(chưa có ngữ cảnh trước đó)"


def _normalize_topic_text(value: str) -> str:
    raw = (value or "").strip().lower().replace("đ", "d")
    normalized = unicodedata.normalize("NFD", raw)
    ascii_text = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return " ".join(ascii_text.split())


def _build_system_help_context(question: str) -> str:
    text = _normalize_topic_text(question)
    hints: list[str] = []
    if any(k in text for k in ("camera", "giam sat", "canh bao", "chuong")):
        hints.append(
            "- Neu lien quan camera/giam sat: huong dan vao trang Giam sat truc tiep, kiem tra camera chuong, nguon dau vao, trang thai model va lich su phien."
        )
    if any(k in text for k in ("benh", "trieu chung", "phan tich anh", "classification", "segmentation", "tu van ai")):
        hints.append(
            "- Neu lien quan benh/anh: huong dan dung Tu van AI, gui anh ro trieu chung, doc ket qua segmentation/classification, roi can nhac hoi chuyen gia."
        )
    if any(k in text for k in ("chuyen gia", "bac si", "thu y")):
        hints.append(
            "- Neu can nguoi that ho tro: huong dan mo Tu van chuyen gia, xem ho so chuyen gia, chon dung nguoi roi mo ta trieu chung hoac gui anh."
        )
    if any(k in text for k in ("telegram", "bot", "link")):
        hints.append(
            "- Neu lien quan Telegram: huong dan farmer mo Cai dat, tao link lien ket bot, sau do nhan canh bao bat thuong qua Telegram."
        )
    if any(k in text for k in ("lich su", "phien", "da gui", "xem lai")):
        hints.append(
            "- Neu muon xem lai du lieu: huong dan mo Lich su de xem phien giam sat, anh, tin nhan va ket qua AI da luu."
        )
    if any(k in text for k in ("cai dat", "web", "desktop", "port", "server")):
        hints.append(
            "- Neu lien quan cau hinh: farmer chinh camera/server o Cai dat nguoi dung; admin chinh web mode, AI key, YOLO mode o Cai dat he thong."
        )
    if not hints:
        hints.append(
            "- Neu cau hoi chung: uu tien goi y cach dung cac man Tu van AI, Tu van chuyen gia, Giam sat truc tiep, Lich su va Cai dat sao cho sat van de nguoi dung."
        )
    return "\n".join(hints)


def build_gemini_prompt(diagnosis: dict) -> str:
    """Xay dung prompt tu van benh cho Gemini AI tu ket qua chan doan."""
    detected = diagnosis.get("detected", [])
    not_detected = diagnosis.get("not_detected", [])
    cls_top1 = diagnosis.get("classification", {}).get("top1")
    cls_topk = diagnosis.get("classification", {}).get("topk", [])
    n_objects = diagnosis.get("n_objects", 0)

    lines_det = "\n".join(
        f"  - {d['class']} (confidence: {d['confidence']:.0%})" for d in detected
    ) or "  (không có)"
    lines_not = "\n".join(f"  - {c}" for c in not_detected) or "  (không có)"
    lines_cls = "\n".join(
        f"  - {item['class']} (confidence: {item['confidence']:.0%})"
        for item in cls_topk[:3]
    ) or "  (không có)"
    cls_summary = (
        f"{cls_top1['class']} ({cls_top1['confidence']:.0%})"
        if cls_top1
        else "không có"
    )

    return (
        "Bạn là trợ lý AI thú y chuyên hỗ trợ chăn nuôi bò cho hệ thống Con Bò Cười.\n"
        f"{_RESPONSE_RULES}\n\n"
        "Dữ liệu phân tích ảnh hiện tại từ hệ thống:\n"
        f"- Số vùng nghi ngờ được phát hiện: {n_objects}\n"
        f"- Kết quả segmentation phát hiện:\n{lines_det}\n\n"
        f"- Kết quả không phát hiện:\n{lines_not}\n\n"
        f"- Kết quả classification ưu tiên: {cls_summary}\n"
        f"- Top classification gần nhất:\n{lines_cls}\n\n"
        "Hãy trả lời theo đúng cấu trúc sau:\n"
        "1. Đánh giá nhanh: kết luận ngắn gọn tình trạng hiện tại.\n"
        "2. Dấu hiệu đáng chú ý: nêu các bệnh hoặc nghi ngờ chính, mức độ khẩn cấp.\n"
        "3. Việc cần làm ngay: liệt kê 3-5 bước ngắn, thực tế tại trang trại.\n"
        "4. Theo dõi tiếp trong hệ thống: hướng dẫn người dùng nên làm gì tiếp bằng Con Bò Cười (ví dụ gửi thêm ảnh, mở Tư vấn chuyên gia, kiểm tra Giám sát trực tiếp, xem Lịch sử).\n"
        "5. Khi nào cần thú y/chuyên gia: nêu mốc rõ ràng để chuyển sang hỗ trợ người thật.\n"
        "Nếu không có dấu hiệu bệnh rõ ràng, nói thẳng là ảnh hiện chưa đủ bằng chứng, nhưng vẫn hướng dẫn cách chụp lại ảnh rõ hơn và cách theo dõi thêm."
    )


_FARMER_TOPIC_PHRASES = (
    "trang trai", "nong nghiep", "thu y", "gia suc", "trieu chung", "dieu tri",
    "thuc an", "u chua", "nuoc uong", "phoi giong", "sinh san", "giam sat",
    "canh bao", "mo hinh", "he thong", "phan tich anh", "tu van",
    "classification", "segmentation", "upload", "camera", "vaccine", "benh",
    "chuong", "sua",
)

_FARMER_TOPIC_TOKENS = {"bo", "be", "nong", "trai", "vac", "gemini", "ai"}


def is_supported_farmer_topic(question: str) -> bool:
    text = _normalize_topic_text(question)
    if not text:
        return False
    tokens = set(re.findall(r"[a-z0-9_]+", text))
    if any(phrase in text for phrase in _FARMER_TOPIC_PHRASES):
        return True
    return any(token in tokens for token in _FARMER_TOPIC_TOKENS)


def build_farmer_chat_prompt(question: str, history: list[dict] | None = None) -> str:
    history_block = _format_chat_history(history, limit=8)
    help_context = _build_system_help_context(question)
    return (
        "Bạn là trợ lý AI của hệ thống Con Bò Cười.\n"
        f"{_RESPONSE_RULES}\n\n"
        f"{_SYSTEM_FEATURE_GUIDE}\n\n"
        "Hỗ trợ sử dụng nên ưu tiên trong tình huống hiện tại:\n"
        f"{help_context}\n\n"
        f"Lịch sử hội thoại gần đây:\n{history_block}\n\n"
        f"Câu hỏi mới của người dùng: {question}\n\n"
        "Yêu cầu cách trả lời:\n"
        "- Nếu là câu hỏi về bệnh/chăn nuôi: trả lời theo các mục `Nhận định`, `Cần làm ngay`, `Theo dõi thêm`, `Dùng tính năng nào trong hệ thống`.\n"
        "- Nếu là câu hỏi về cách dùng hệ thống: trả lời theo từng bước thao tác cụ thể, chỉ rõ nên vào màn nào.\n"
        "- Nếu người dùng hỏi mơ hồ: chủ động gợi ý 2-4 khả năng và cách kiểm tra trong app.\n"
        "- Nếu ngoài phạm vi: từ chối ngắn gọn, lịch sự, rồi nhắc lại các nhóm chủ đề mà bạn hỗ trợ."
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


def call_farmer_chat_async(
    api_key: str,
    question: str,
    history: list[dict] | None,
    callback,
) -> None:
    question = (question or "").strip()
    if not question:
        callback("⚠️ Vui lòng nhập câu hỏi.")
        return
    if not is_supported_farmer_topic(question):
        callback(
            "Mình chỉ hỗ trợ các chủ đề về chăn nuôi bò, bệnh bò, nông nghiệp liên quan và cách dùng hệ thống Con Bò Cười."
        )
        return
    prompt = build_farmer_chat_prompt(question, history=history)
    call_gemini_async(api_key, prompt, callback)


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC: HIGH-LEVEL API (dùng trực tiếp từ UI layer)
# ─────────────────────────────────────────────────────────────────────────────


def analyze_image_async(
    img_source,  # str path | np.ndarray | bytes
    conf_thresh: float,
    on_result,  # callback(result_dict: dict)
    on_error,  # callback(msg: str)
    device: str = "auto",
    imgsz: int = 640,
) -> None:
    """
    Pipeline farmer:
      1. health_cls  -> lọc bò khỏe / nghi bệnh
      2. disease_cls -> phân loại bệnh nếu bước 1 nghi bệnh
      3. disease     -> segmentation/detection nếu bước 1 nghi bệnh

    Fallback:
      - Nếu chưa cấu hình health_cls -> giữ luồng cũ disease_cls + segmentation
      - Nếu chưa cấu hình disease_cls -> vẫn chạy segmentation
    """
    def _do():
        try:
            health_model, health_rec = get_optional_health_cls_model()
            cls_model, cls_rec = get_optional_disease_cls_model()

            # bytes → np.ndarray
            np = _np()
            if isinstance(img_source, (bytes, bytearray)):
                cv2 = _cv2()
                nparr = np.frombuffer(img_source, np.uint8)
                source = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            else:
                source = img_source

            health_summary = {"top1": None, "topk": []}
            health_pil_img = None
            health_is_healthy = False
            if health_model is not None:
                resolved_device = _resolve_device(device)
                health_result = health_model.predict(
                    source=source,
                    imgsz=imgsz,
                    device=resolved_device,
                    verbose=False,
                )[0]
                health_summary = build_classification_summary(health_result)
                health_pil_img = draw_classification_result(health_result, health_summary)
                health_is_healthy = _is_healthy_gate_prediction(health_summary)

            if health_model is not None and health_is_healthy:
                healthy_diagnosis = {
                    "detected": [],
                    "not_detected": [],
                    "total_classes": 0,
                    "n_objects": 0,
                    "classification": {"top1": None, "topk": []},
                    "health_gate": {
                        "enabled": True,
                        "top1": health_summary.get("top1"),
                        "topk": health_summary.get("topk", []),
                        "is_healthy": True,
                    },
                }
                on_result({
                    "annotated_b64": "",
                    "health_gate_b64": pil_to_base64(health_pil_img, quality=85) if health_pil_img is not None else "",
                    "classification_b64": "",
                    "diagnosis": healthy_diagnosis,
                    "predictions": {"predictions": []},
                    "conf_thresh": 0.0,
                    "model_name": health_rec.get("ten_mo_hinh", "Health Classification") if health_rec else "Health Classification",
                    "health_gate_model_name": health_rec.get("ten_mo_hinh", "Health Classification") if health_rec else None,
                    "classification_model_name": None,
                    "classification_enabled": False,
                    "health_gate_enabled": True,
                    "segmentation_enabled": False,
                    "pipeline_stage": "healthy_gate_only",
                    "is_seg": False,
                })
                return

            seg_model, seg_rec = get_disease_model()
            iou_model = float(seg_rec.get("iou", 0.45))
            is_seg = getattr(seg_model, "task", "detect") == "segment"

            cls_result = None
            cls_summary = {"top1": None, "topk": []}
            cls_pil_img = None
            if cls_model is not None:
                resolved_device = _resolve_device(device)
                cls_result = cls_model.predict(
                    source=source,
                    imgsz=imgsz,
                    device=resolved_device,
                    verbose=False,
                )[0]
                cls_summary = build_classification_summary(cls_result)
                cls_pil_img = draw_classification_result(cls_result, cls_summary)

            result, final_conf = predict_dynamic_conf(
                seg_model, source,
                start_conf=conf_thresh,
                min_conf=0.05,
                step=0.05,
                iou=iou_model,
                imgsz=imgsz,
                device=device,
            )

            draw_conf = final_conf if final_conf > 0 else conf_thresh
            pil_img = draw_result(result, conf_thresh=draw_conf, opacity=70, is_seg=is_seg)
            annotated_b64 = pil_to_base64(pil_img, quality=85)
            seg_diagnosis = build_diagnosis(result, draw_conf)
            diagnosis = _merge_diagnosis_with_classification(seg_diagnosis, cls_summary)
            diagnosis["health_gate"] = {
                "enabled": health_model is not None,
                "top1": health_summary.get("top1"),
                "topk": health_summary.get("topk", []),
                "is_healthy": health_is_healthy,
            }
            predictions = build_predictions_json(result, draw_conf)

            on_result({
                "annotated_b64": annotated_b64,
                "health_gate_b64": pil_to_base64(health_pil_img, quality=85) if health_pil_img is not None else "",
                "classification_b64": pil_to_base64(cls_pil_img, quality=85) if cls_pil_img is not None else "",
                "diagnosis": diagnosis,
                "predictions": predictions,
                "conf_thresh": final_conf,
                "model_name": seg_rec.get("ten_mo_hinh", "Disease Model"),
                "health_gate_model_name": health_rec.get("ten_mo_hinh", "Health Classification") if health_rec else None,
                "classification_model_name": cls_rec.get("ten_mo_hinh", "Disease Classification") if cls_rec else None,
                "classification_enabled": cls_model is not None,
                "health_gate_enabled": health_model is not None,
                "segmentation_enabled": True,
                "pipeline_stage": "disease_pipeline",
                "is_seg": is_seg,
            })

        except FileNotFoundError as e:
            on_error(f"⚠️ Chưa cấu hình model: {e}")
        except Exception as e:
            import traceback
            on_error(f"❌ Lỗi phân tích: {e}\n{traceback.format_exc()}")

    threading.Thread(target=_do, daemon=True).start()
