import json
from pathlib import Path

from bll.test.history_service import cmp_history_from_results_csv, paper_find_history_data, safe_float_or_none


def find_latest_eval_json(model_path: str, eval_base_dir: Path, runs_dir: Path):
    model_file = Path(model_path).resolve()
    target_norm = str(model_file).replace("\\", "/").lower()
    target_name = model_file.name.lower()
    candidates = []
    for base in (model_file.parent, model_file.parent.parent, eval_base_dir, runs_dir):
        if base and base.exists():
            try:
                candidates.extend(base.rglob("eval*.json"))
            except Exception:
                pass

    best = None
    best_mtime = -1.0
    for path in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        model_field = str(payload.get("model") or payload.get("model_path") or "").replace("\\", "/").lower()
        if model_field:
            matched = model_field == target_norm or Path(model_field).name.lower() == target_name
        else:
            matched = target_name in path.name.lower()
        if not matched:
            continue
        try:
            mtime = path.stat().st_mtime
        except Exception:
            mtime = 0.0
        if mtime > best_mtime:
            best = payload
            best_mtime = mtime
    return best


def load_saved_eval_artifacts(
    path: str,
    model_type: str,
    *,
    runs_dir: Path,
    eval_base_dir: Path,
    eval_run_dir_finder,
):
    history = []
    summary = {}
    metric_updates = {}

    if model_type == "pth":
        lower_path = path.lower()
        which = "plos" if ("mobilenet" in lower_path or "plos" in lower_path) else "jilsa"
        history = paper_find_history_data(which, path, runs_dir) or []
    else:
        run_dir = eval_run_dir_finder(path)
        if run_dir is not None:
            history = cmp_history_from_results_csv(run_dir)

    payload = find_latest_eval_json(path, eval_base_dir, runs_dir) or {}
    if payload:
        acc = safe_float_or_none(payload.get("accuracy"))
        macro_f1 = safe_float_or_none(payload.get("macro_f1"))
        val_loss = safe_float_or_none(payload.get("val_loss"))
        gflops = safe_float_or_none(payload.get("gflops"))
        params = safe_float_or_none(payload.get("params"))
        summary = {
            "accuracy": acc,
            "macro_f1": macro_f1,
            "val_loss": val_loss,
            "gflops": gflops,
            "params": params,
            "val_map50": payload.get("val_map50"),
            "val_map50_95": payload.get("val_map50_95"),
            "val_top1": payload.get("val_top1"),
            "val_top5": payload.get("val_top5"),
            "class_names": payload.get("class_names") or [],
            "confusion_matrix": payload.get("confusion_matrix") or [],
        }
        metric_map = {
            "accuracy": "accuracy",
            "macro_f1": "macro_f1",
            "val_loss": "val_loss",
            "val_map50": "val_map50",
            "val_map50_95": "val_map50_95",
            "val_top1": "val_top1",
            "val_top5": "val_top5",
        }
        for dst, src in metric_map.items():
            value = payload.get(src)
            if value is not None:
                metric_updates[dst] = value
        if params is not None:
            metric_updates["parameters"] = int(params)
            metric_updates["params_m"] = f"{params / 1e6:.4f}"
        if gflops is not None:
            metric_updates["gflops_num"] = float(gflops)
            metric_updates["gflops"] = f"{float(gflops):.3f}"
        class_names = payload.get("class_names") or []
        confusion_matrix = payload.get("confusion_matrix") or []
        if class_names:
            metric_updates["_class_names"] = class_names
        if confusion_matrix:
            metric_updates["_confusion_matrix"] = confusion_matrix

    return {
        "history": history,
        "summary": summary,
        "metric_updates": metric_updates,
    }
