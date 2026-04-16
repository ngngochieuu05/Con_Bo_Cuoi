# AI Core — Nghiệp vụ tích hợp YOLOv8 cho chức năng Tư Vấn Nhanh

> Phân tích từ `models/train/test_model.py` — cốt lõi logic inference để port vào `health_consulting.py` / `dal/ai_service.py`

---

## 1. Kiến trúc tổng thể

```
[Ảnh đầu vào]
      │
      ▼
load_model(path, task)          ← YOLO(.pt|.onnx, task="detect"|"segment")
      │  warm-up 1 lần với dummy array
      ▼
run_inference(source, conf=0.01, iou, imgsz, device, half)
      │  conf dùng thấp (0.01) để lấy ALL raw boxes
      ▼
filter_by_conf(result, conf_thresh)   ← lọc client-side, không chạy lại model
      │
      ├─► draw_result()              → PIL.Image (bbox + polygon mask)
      ├─► build_predictions_json()   → list[dict] predictions
      ├─► update_diagnosis()         → dict {cls_id: best_conf}
      └─► call_gemini_ai()           → str tư vấn văn bản
```

---

## 2. Tham số inference

| Tham số | Giá trị mặc định | Mô tả |
|---------|-----------------|-------|
| `conf` | **0.01** (raw predict) / **0.25** (hiển thị) | Predict với conf thấp để giữ hết box, lọc hiển thị sau |
| `iou` | 0.45 | NMS IoU threshold |
| `imgsz` | 640 | Kích thước resize trước khi đưa vào model |
| `device` | `"0"` (GPU) / `"cpu"` | RTX 4060 mặc định |
| `half` | False | FP16 — chỉ dùng khi device != "cpu" |
| `save` | False | Không lưu file kết quả |
| `verbose` | False | **Bắt buộc False** — verbose=True gây KeyError khi names thiếu class id |

> **Quan trọng:** Luôn predict với `conf=0.01` (lấy hết raw), sau đó lọc theo ngưỡng người dùng chọn. Không predict lại mỗi khi người dùng đổi conf.

---

## 3. Load Model

```python
from ultralytics import YOLO
import numpy as np

TASK_MAP = {"detect": "detect", "segment": "segment"}

def load_model(model_path: str, task: str = "detect") -> YOLO:
    model = YOLO(model_path, task=task)
    # Warm-up BẮT BUỘC — tránh ONNX tạo lại session lần 2 khi predict thật
    dummy = np.zeros((640, 640, 3), dtype=np.uint8)
    model.predict(source=dummy, imgsz=640, device="0", verbose=False)
    return model
```

**Lưu ý ONNX:**
- Cần install: `onnx`, `onnxslim`, `onnxruntime-gpu`
- Tắt log noise: `onnxruntime.set_default_logger_severity(3)`

---

## 4. Run Inference & Kết quả thô

```python
def run_inference(model, source, conf=0.01, iou=0.45, imgsz=640, device="0", half=False):
    results = model.predict(
        source=source,   # path ảnh | np.ndarray | int (webcam index)
        conf=conf,
        iou=iou,
        imgsz=imgsz,
        device=device,
        half=half and device != "cpu",
        save=False,
        verbose=False,   # KHÔNG đổi thành True
    )
    return results[0]   # result object của ảnh đầu tiên
```

**Cấu trúc `result` object:**
```
result.orig_img       → np.ndarray (H,W,3) BGR — ảnh gốc
result.boxes          → Boxes object | None
  .boxes[i].conf[0]   → float  — confidence của box thứ i
  .boxes[i].cls[0]    → int    — class id
  .boxes[i].xyxy[0]   → [x1,y1,x2,y2] absolute pixels
  .boxes[i].xywh[0]   → [cx,cy,w,h] absolute pixels
result.masks          → Masks object | None  (chỉ có khi task=segment)
  .masks.xy[i]        → np.ndarray(N,2) — polygon coords ảnh gốc
result.names          → dict {int: str} — map class_id → class_name
```

---

## 5. Filter theo Confidence (client-side)

```python
def filter_detections(result, conf_thresh: float) -> list[dict]:
    """Lọc boxes đạt ngưỡng, trả về list detection đã sort theo conf giảm dần."""
    if result.boxes is None:
        return []
    names = result.names or {}
    detections = []
    for i, box in enumerate(result.boxes):
        conf = float(box.conf[0])
        if conf < conf_thresh:
            continue
        cls_id = int(box.cls[0])
        detections.append({
            "class_id":   cls_id,
            "class_name": names.get(cls_id, f"cls{cls_id}"),
            "confidence": round(conf, 3),
            "bbox_xyxy":  [round(float(v), 1) for v in box.xyxy[0].tolist()],
            "bbox_xywh":  [round(float(v), 1) for v in box.xywh[0].tolist()],
            "mask_poly":  None,  # điền ở bước dưới nếu task=segment
        })
    # Gắn polygon mask nếu có
    if result.masks is not None:
        for i, det in enumerate(detections):
            orig_idx = det.get("_orig_idx", i)
            if orig_idx < len(result.masks.xy):
                poly = result.masks.xy[orig_idx]
                if len(poly) >= 3:
                    det["mask_poly"] = poly.tolist()
    return sorted(detections, key=lambda x: -x["confidence"])
```

---

## 6. Build Predictions JSON

Schema chuẩn (tương thích Roboflow format):

```python
import json, uuid

def build_predictions_json(result, conf_thresh: float = 0.25) -> dict:
    names     = result.names or {}
    has_masks = result.masks is not None
    preds     = []

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
        # Thêm polygon nếu là segmentation
        if has_masks and result.masks.xy is not None and i < len(result.masks.xy):
            poly = result.masks.xy[i]
            if len(poly) >= 3:
                pred["points"] = [
                    {"x": round(float(p[0]), 1), "y": round(float(p[1]), 1)}
                    for p in poly
                ]
        preds.append(pred)

    return {"predictions": preds}
```

---

## 7. Build Diagnosis Summary

Mục đích: biết lớp nào **phát hiện** / **không phát hiện**, lấy confidence cao nhất mỗi lớp.

```python
def build_diagnosis(result, conf_thresh: float = 0.25) -> dict:
    """
    Returns:
        {
            "detected":     [{"class": str, "confidence": float}, ...],  # sort by conf desc
            "not_detected": [str, ...],
            "total_classes": int,
        }
    """
    if result is None or result.boxes is None:
        return {"detected": [], "not_detected": list((result.names or {}).values()), "total_classes": 0}

    names = result.names or {}
    best: dict[int, float] = {}

    for box in result.boxes:
        conf   = float(box.conf[0])
        cls_id = int(box.cls[0])
        if conf >= conf_thresh:
            if cls_id not in best or conf > best[cls_id]:
                best[cls_id] = conf

    detected = sorted(
        [{"class": names.get(cid, f"cls{cid}"), "confidence": round(c, 3)}
         for cid, c in best.items()],
        key=lambda x: -x["confidence"]
    )
    detected_names = {d["class"] for d in detected}
    not_detected   = [n for n in names.values() if n not in detected_names]

    return {
        "detected":      detected,
        "not_detected":  not_detected,
        "total_classes": len(names),
    }
```

---

## 8. Gọi Gemini AI (Tư vấn văn bản)

### Prompt chuẩn:

```python
def build_gemini_prompt(diagnosis: dict) -> str:
    detected     = diagnosis["detected"]
    not_detected = diagnosis["not_detected"]

    lines_det = "\n".join(
        f"  - {d['class']} (confidence: {d['confidence']:.0%})" for d in detected
    ) or "  (không có)"
    lines_not = "\n".join(f"  - {c}" for c in not_detected) or "  (không có)"

    return (
        "Bạn là bác sĩ thú y chuyên về bệnh ở bò. "
        "Hệ thống AI thị giác (YOLOv8 Instance Segmentation) "
        "đã phân tích ảnh và cho kết quả:\n\n"
        f"✅ Phát hiện:\n{lines_det}\n\n"
        f"❌ Không phát hiện:\n{lines_not}\n\n"
        "Dựa vào kết quả trên, hãy:\n"
        "1. Nhận xét tình trạng sức khỏe con bò\n"
        "2. Mô tả ngắn gọn từng bệnh được phát hiện (triệu chứng, mức độ nguy hiểm)\n"
        "3. Đề xuất hướng xử lý / điều trị\n"
        "Trả lời bằng tiếng Việt, ngắn gọn và chuyên nghiệp."
    )
```

### Gọi API (async-compatible pattern):

```python
import google.generativeai as genai
import threading

def call_gemini_async(api_key: str, prompt: str, callback):
    """
    callback(text: str) được gọi trên thread phụ sau khi có kết quả.
    Trong Flet: dùng page.run_task() hoặc threading.Thread.
    """
    def _do():
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            resp  = model.generate_content(prompt)
            callback(resp.text)
        except Exception as e:
            callback(f"❌ Lỗi Gemini: {e}")
    threading.Thread(target=_do, daemon=True).start()
```

**Model Gemini dùng:** `gemini-2.5-flash` (nhanh, đủ chất lượng cho tư vấn)

---

## 9. Vẽ kết quả lên ảnh (Draw Result)

Dùng PIL thuần (không dùng result.plot() vì không kiểm soát được conf filter):

```python
from PIL import Image, ImageDraw
import cv2, numpy as np

CLASS_COLORS = [
    "#ef4444","#f97316","#eab308","#22c55e","#14b8a6",
    "#3b82f6","#8b5cf6","#ec4899","#06b6d4","#84cc16",
]

def draw_result(result, conf_thresh=0.25, opacity=75, is_seg=False) -> Image.Image:
    """Trả về PIL.Image RGB với bbox + mask đã vẽ."""
    orig = result.orig_img
    if orig is None:
        return Image.new("RGB", (640, 480), "black")

    # Chuẩn hóa orig_img (có thể là CHW hoặc NCHW)
    if orig.ndim == 4:
        orig = orig[0]
    if orig.ndim == 3 and orig.shape[0] in (1, 3, 4) and orig.shape[0] < orig.shape[1]:
        orig = np.transpose(orig, (1, 2, 0))
    if orig.dtype != np.uint8:
        mx = orig.max()
        orig = (orig * (255.0 / mx if mx > 1.0 else 255.0)).clip(0, 255).astype(np.uint8)

    img_rgb = cv2.cvtColor(orig, cv2.COLOR_BGR2RGB)
    base    = Image.fromarray(img_rgb).convert("RGBA")
    names   = result.names or {}
    alpha   = int(max(0, min(100, opacity)) / 100.0 * 255)

    # Lọc valid boxes
    valid = []
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
            r_c, g_c, b_c = int(ch[1:3],16), int(ch[3:5],16), int(ch[5:7],16)
            pts = [(float(x), float(y)) for x, y in polys[i]]
            layer = Image.new("RGBA", base.size, (0,0,0,0))
            ImageDraw.Draw(layer).polygon(pts, fill=(r_c,g_c,b_c,alpha))
            base = Image.alpha_composite(base, layer)

    # Vẽ bbox + label
    draw = ImageDraw.Draw(base)
    for i, box in valid:
        cls_id = int(box.cls[0])
        conf   = float(box.conf[0])
        name   = names.get(cls_id, f"cls{cls_id}")
        lbl    = f"{name}  {conf:.0%}"
        ch     = CLASS_COLORS[cls_id % len(CLASS_COLORS)]
        r_c, g_c, b_c = int(ch[1:3],16), int(ch[3:5],16), int(ch[5:7],16)
        x1,y1,x2,y2 = [int(v) for v in box.xyxy[0].tolist()]
        for th in range(3):
            draw.rectangle([x1-th,y1-th,x2+th,y2+th], outline=(r_c,g_c,b_c,255))
        tw = len(lbl)*6+8
        draw.rectangle([x1,y1-20,x1+tw,y1], fill=(r_c,g_c,b_c,210))
        draw.text((x1+4,y1-18), lbl, fill=(255,255,255,255))

    return base.convert("RGB")
```

> **Chuyển PIL.Image → Flet:** dùng `src_base64` (KHÔNG dùng `src` với data URI)
> ```python
> import base64, io
> buf = io.BytesIO()
> pil_img.save(buf, format="JPEG", quality=85)
> b64 = base64.b64encode(buf.getvalue()).decode()
> ft.Image(src_base64=b64, ...)
> ```

---

## 10. Luồng tích hợp vào Health Consulting (Tư vấn nhanh)

```
[Farmer chụp/upload ảnh bò]
         │
         ▼
1. load_model(model_path, task="segment")   ← load 1 lần, cache trong service
         │
         ▼
2. run_inference(source=img_array, conf=0.01)
         │
         ▼
3. build_diagnosis(result, conf_thresh=0.25)
         │                │
         ▼                ▼
4. draw_result()    build_predictions_json()
   → PIL.Image         → dict predictions
   → base64 string
         │
         ▼
5. build_gemini_prompt(diagnosis)
         │
         ▼
6. call_gemini_async(api_key, prompt, callback)
         │
         ▼
7. Hiển thị:
   - Ảnh annotated (ft.Image src_base64=...)
   - Danh sách bệnh detected / not_detected
   - Văn bản tư vấn từ Gemini
   - Lưu vào canh_bao_repo / lich_su_kiem_duyet nếu cần
```

---

## 11. Lưu ý khi tích hợp vào Flet

| Vấn đề | Giải pháp |
|--------|-----------|
| Inference blocking UI | Dùng `threading.Thread` hoặc `asyncio` + `page.run_task()` |
| Hiển thị ảnh kết quả | `ft.Image(src_base64=b64)` — KHÔNG dùng `src` với data URI |
| Model load 1 lần | Cache trong `MonitorService` hoặc class-level singleton |
| GPU OOM | Giải phóng VRAM: `import torch; torch.cuda.empty_cache()` sau inference |
| ONNX log spam | `onnxruntime.set_default_logger_severity(3)` trước khi load |
| warm-up bắt buộc | Predict 1 lần với dummy array ngay sau `YOLO(path)` |
| task mismatch | `.pt` segment model → `task="segment"`, detect model → `task="detect"` |

---

## 12. Class names bệnh trong model

Lấy động từ `model.names` sau khi load. Ví dụ với model cattle disease:

```python
model.names  
# {0: "Lumpy skin disease", 1: "Foot and mouth disease", 2: "Ringworm", ...}
```

Không hardcode class names — luôn đọc từ `model.names` để tương thích mọi version model.
