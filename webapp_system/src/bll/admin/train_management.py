"""
BLL — Train Management (Admin)
Quản lý việc chạy subprocess train YOLOv8, stream log, theo dõi tiến độ.
Chỉ Admin mới có quyền sử dụng.
Chuyển từ bll/services/train_service.py sang đúng tầng admin.
"""
from __future__ import annotations

import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Callable

# ─── Đường dẫn gốc dataset / output ────────────────────────────────────────
_MODELS_DIR  = Path(__file__).parent.parent.parent.parent / "models"
DEFAULT_YAML = _MODELS_DIR / "dataset" / "Cattle Desease.v1i.yolov8" / "data.yaml"
DEFAULT_OUT  = _MODELS_DIR / "runs"
PYTHON_EXE   = sys.executable

# ─── Preset theo VRAM (RTX 4060 8GB) ────────────────────────────────────────
PRESETS: dict[str, dict] = {
    "Nhanh (yolov8n)":      {"model": "yolov8n", "batch": 32, "imgsz": 640, "workers": 8},
    "Cân bằng (yolov8s)":   {"model": "yolov8s", "batch": 16, "imgsz": 640, "workers": 8},
    "Chất lượng (yolov8m)": {"model": "yolov8m", "batch": 8,  "imgsz": 640, "workers": 8},
    "Cao (yolov8l)":        {"model": "yolov8l", "batch": 4,  "imgsz": 640, "workers": 4},
    "Tối đa (yolov8x)":     {"model": "yolov8x", "batch": 2,  "imgsz": 640, "workers": 4},
}

TASK_TYPES     = ["detect", "segment"]
OPTIMIZERS     = ["auto", "SGD", "Adam", "AdamW"]
EXPORT_FORMATS = ["pt", "onnx", "pt+onnx"]


def _fmt_time(seconds: float) -> str:
    seconds = int(seconds)
    h, r = divmod(seconds, 3600)
    m, s = divmod(r, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


class TrainJob:
    """Đại diện cho một job train đang chạy / đã kết thúc."""

    def __init__(self, job_id: str, total_epochs: int):
        self.job_id       = job_id
        self.total_epochs = total_epochs
        self.status       = "running"   # running | done | error | stopped
        self.epoch_cur    = 0
        self.pct          = 0
        self.elapsed      = "0s"
        self.eta          = "—"
        self.result_path  = ""
        self.log_lines: list[str] = []
        self._start_time  = time.time()
        self._process: subprocess.Popen | None = None
        self._lock        = threading.Lock()

    # ── ghi log ──
    def append_log(self, line: str):
        with self._lock:
            self.log_lines.append(line)
            if len(self.log_lines) > 1000:          # giới hạn 1000 dòng
                self.log_lines = self.log_lines[-800:]

    # ── cập nhật tiến độ từ stdout ──
    def parse_line(self, line: str):
        self.append_log(line.rstrip())
        if "Epoch" in line and "/" in line:
            try:
                for part in line.split():
                    if "/" in part:
                        c, t = part.split("/")
                        cur = int(c.strip())
                        tot = int(t.strip())
                        elapsed = time.time() - self._start_time
                        eta_s   = (elapsed / cur) * (tot - cur) if cur > 0 else 0
                        with self._lock:
                            self.epoch_cur = cur
                            self.pct       = int(cur / tot * 100)
                            self.elapsed   = _fmt_time(elapsed)
                            self.eta       = _fmt_time(eta_s)
                        break
            except Exception:
                pass
        if "[RESULT]" in line:
            # "[RESULT] Saved to: <path>"
            try:
                path = line.split("Saved to:")[-1].strip()
                with self._lock:
                    self.result_path = path
            except Exception:
                pass

    # ── trạng thái snapshot (an toàn để đọc từ UI thread) ──
    def snapshot(self) -> dict:
        with self._lock:
            return {
                "job_id":      self.job_id,
                "status":      self.status,
                "epoch_cur":   self.epoch_cur,
                "epoch_total": self.total_epochs,
                "pct":         self.pct,
                "elapsed":     self.elapsed,
                "eta":         self.eta,
                "result_path": self.result_path,
                "log_lines":   list(self.log_lines[-50:]),   # 50 dòng cuối cho UI
            }

    def stop(self):
        if self._process and self._process.poll() is None:
            self._process.terminate()
            with self._lock:
                self.status = "stopped"


# ─── Singleton job manager ───────────────────────────────────────────────────
_current_job: TrainJob | None = None
_job_lock = threading.Lock()


def get_current_job() -> TrainJob | None:
    return _current_job


def is_training() -> bool:
    return _current_job is not None and _current_job.status == "running"


def stop_training():
    if _current_job:
        _current_job.stop()


def start_training(
    *,
    yaml_path: str    = str(DEFAULT_YAML),
    model: str        = "yolov8s.pt",
    task: str         = "detect",
    epochs: int       = 50,
    batch: int        = 16,
    imgsz: int        = 640,
    lr0: float        = 0.001,
    patience: int     = 30,
    workers: int      = 8,
    device: str       = "0",
    optimizer: str    = "AdamW",
    amp: bool         = True,
    cache: bool       = False,
    cos_lr: bool      = True,
    mosaic: float     = 1.0,
    mixup: float      = 0.2,
    degrees: int      = 15,
    hsv_s: float      = 0.5,
    hsv_v: float      = 0.4,
    output_dir: str   = str(DEFAULT_OUT),
    export_format: str = "pt",
    on_done: Callable[[TrainJob], None] | None = None,
) -> tuple[bool, str]:
    """
    Khởi động job train.  
    Trả về (success, message).
    Nếu đang train → từ chối.
    """
    global _current_job

    with _job_lock:
        if is_training():
            return False, "Đang có job train đang chạy. Dừng lại trước."

        yaml_p = Path(yaml_path)
        if not yaml_p.exists():
            return False, f"Không tìm thấy data.yaml:\n{yaml_path}"

        job_id    = uuid.uuid4().hex[:8]
        run_name  = f"train_{model.replace('.pt','').replace('-seg','seg')}_{epochs}ep"
        is_seg    = task == "segment"
        task_arg  = "segment" if is_seg else "detect"
        export_onnx = "onnx" in export_format
        export_pt   = "pt"   in export_format

        # ── sinh inline script ──
        script = f"""\
import os, sys, torch
from pathlib import Path
from ultralytics import YOLO

print(f"[INFO] PyTorch: {{torch.__version__}}")
print(f"[INFO] CUDA: {{torch.cuda.is_available()}}")
if torch.cuda.is_available():
    print(f"[INFO] GPU: {{torch.cuda.get_device_name(0)}}")
print(f"[INFO] Task: {task_arg}")

model = YOLO("{model}", task="{task_arg}")
results = model.train(
    data      = r"{yaml_path}",
    task      = "{task_arg}",
    epochs    = {epochs},
    batch     = {batch},
    imgsz     = {imgsz},
    lr0       = {lr0},
    cos_lr    = {cos_lr},
    optimizer = "{optimizer}",
    patience  = {patience},
    workers   = {workers},
    device    = "{device}",
    amp       = {amp},
    cache     = {cache},
    mosaic    = {mosaic},
    mixup     = {mixup},
    degrees   = {degrees},
    hsv_s     = {hsv_s},
    hsv_v     = {hsv_v},
    project   = r"{output_dir}",
    name      = "{run_name}",
    exist_ok  = True,
    verbose   = True,
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
        print(f"[INFO] Cai {{pkg}}...")
        _sp.run([_sys.executable, "-m", "pip", "install", pkg, "-q"])
        print(f"[INFO] Da cai {{pkg}}.")

_ensure("onnx")
_ensure("onnxslim")

best_pt = Path(results.save_dir) / 'weights' / 'best.pt'
print(f"[INFO] Xuat ONNX tu: {{best_pt}}")
export_model = __import__('ultralytics').YOLO(str(best_pt), task="{task_arg}")
onnx_path = export_model.export(format='onnx', imgsz={imgsz}, dynamic=False)
print(f"[DONE] ONNX: {{onnx_path}}")
"""

        if not export_pt and export_onnx:
            script += """
import shutil
weights_dir = Path(results.save_dir) / 'weights'
for f in weights_dir.glob('*.pt'):
    f.unlink()
print("[INFO] Da xoa file .pt (chi giu .onnx)")
"""

        job = TrainJob(job_id, epochs)
        _current_job = job

    # ── chạy trong daemon thread ──
    def _run():
        global _current_job
        try:
            job._process = subprocess.Popen(
                [PYTHON_EXE, "-c", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True, bufsize=1,
                encoding="utf-8", errors="replace",
                cwd=str(_MODELS_DIR),
            )
            for line in job._process.stdout:
                if job.status != "running":
                    break
                job.parse_line(line)
            job._process.wait()
            rc = job._process.returncode
        except Exception as ex:
            job.append_log(f"[ERROR] {ex}")
            rc = -1
        finally:
            with _job_lock:
                if rc == 0:
                    job.status = "done"
                    job.pct    = 100
                    job.epoch_cur = epochs
                elif job.status == "running":
                    job.status = "error"
            if on_done:
                on_done(job)

    threading.Thread(target=_run, daemon=True).start()
    return True, job_id


def check_ultralytics() -> bool:
    """Kiểm tra ultralytics đã cài chưa."""
    try:
        import importlib
        importlib.import_module("ultralytics")
        return True
    except ImportError:
        return False


def install_ultralytics(on_log: Callable[[str], None] | None = None):
    """Cài ultralytics nếu chưa có (chạy trong thread riêng)."""
    def _install():
        if on_log:
            on_log("[INFO] Đang cài ultralytics...")
        r = subprocess.run(
            [PYTHON_EXE, "-m", "pip", "install", "ultralytics"],
            capture_output=True, text=True
        )
        if r.returncode == 0:
            if on_log:
                on_log("[DONE] Đã cài ultralytics thành công!")
        else:
            if on_log:
                on_log(f"[ERROR] Lỗi cài ultralytics:\n{r.stderr}")

    threading.Thread(target=_install, daemon=True).start()
