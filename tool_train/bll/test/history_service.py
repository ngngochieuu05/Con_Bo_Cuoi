import csv
import json
from pathlib import Path


def safe_float_or_none(value):
    if value is None:
        return None
    try:
        text = str(value).strip()
        if not text or text.lower() in {"none", "n/a", "na", "-", "—", "nan"}:
            return None
        return float(text)
    except Exception:
        return None


def cmp_history_from_results_csv(run_dir: Path):
    csv_path = run_dir / "results.csv"
    if not csv_path.exists():
        return []
    try:
        with open(csv_path, newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    except Exception:
        return []

    history = []
    for row in rows:
        try:
            epoch = row.get("epoch") or row.get(" epoch") or row.get("Epoch") or str(len(history) + 1)
            item = {
                "epoch": int(float(str(epoch).strip())),
                "train_loss": safe_float_or_none(row.get("train/box_loss"))
                or safe_float_or_none(row.get("train/loss"))
                or safe_float_or_none(row.get("train_loss")),
                "val_loss": safe_float_or_none(row.get("val/box_loss"))
                or safe_float_or_none(row.get("val/loss"))
                or safe_float_or_none(row.get("val_loss")),
                "val_acc": safe_float_or_none(row.get("metrics/accuracy_top1"))
                or safe_float_or_none(row.get("metrics/mAP50(B)"))
                or safe_float_or_none(row.get("metrics/mAP50(M)"))
                or safe_float_or_none(row.get("val_acc")),
                "lr": safe_float_or_none(row.get("lr/pg0")) or safe_float_or_none(row.get("lr")),
            }
            if any(v is not None for k, v in item.items() if k != "epoch"):
                history.append(item)
        except Exception:
            continue
    return history


def paper_history_candidates(which: str, model_path: str, runs_dir: Path):
    model_file = Path(model_path).resolve()
    names = (
        ("results_jilsa.csv", "history_jilsa.json")
        if which == "jilsa"
        else ("results_plos.csv", "history_plos.json")
    )
    search_dirs = []
    for folder in (model_file.parent, model_file.parent.parent, runs_dir):
        if folder and folder not in search_dirs and folder.exists():
            search_dirs.append(folder)
    candidates = []
    for folder in search_dirs:
        for name in names:
            path = folder / name
            if path.exists() and path not in candidates:
                candidates.append(path)
        for path in folder.glob(f"**/{names[0]}"):
            if path.exists() and path not in candidates:
                candidates.append(path)
        for path in folder.glob(f"**/{names[1]}"):
            if path.exists() and path not in candidates:
                candidates.append(path)
    return candidates


def paper_find_history_data(which: str, model_path: str, runs_dir: Path):
    candidates = paper_history_candidates(which, model_path, runs_dir)

    csv_path = next((path for path in candidates if path.suffix == ".csv" and path.exists()), None)
    if csv_path is not None:
        try:
            with open(csv_path, newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            history = []
            for row in rows:
                epoch = safe_float_or_none(row.get("epoch"))
                train_loss = safe_float_or_none(row.get("train_loss"))
                val_loss = safe_float_or_none(row.get("val_loss"))
                val_acc = safe_float_or_none(row.get("val_acc"))
                lr = safe_float_or_none(row.get("lr"))
                if epoch is None and train_loss is None and val_loss is None and val_acc is None:
                    continue
                history.append(
                    {
                        "epoch": int(epoch or (len(history) + 1)),
                        "train_loss": train_loss,
                        "val_loss": val_loss,
                        "val_acc": val_acc,
                        "lr": lr,
                    }
                )
            if history:
                return history
        except Exception:
            pass

    json_path = next((path for path in candidates if path.suffix == ".json" and path.exists()), None)
    if json_path is not None:
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            history = payload.get("history") or []
            if isinstance(history, list):
                normalized = []
                for item in history:
                    if not isinstance(item, dict):
                        continue
                    normalized.append(
                        {
                            "epoch": int(safe_float_or_none(item.get("epoch")) or (len(normalized) + 1)),
                            "train_loss": safe_float_or_none(item.get("train_loss")),
                            "val_loss": safe_float_or_none(item.get("val_loss")),
                            "val_acc": safe_float_or_none(item.get("val_acc")),
                            "lr": safe_float_or_none(item.get("lr")),
                        }
                    )
                return normalized
            return []
        except Exception:
            return []
    return []


def make_paper_benchmark_info(which: str, imgsz: int, total_images, metrics: dict):
    bench_name = "JILSA 2022" if which == "jilsa" else "PLOS ONE 2024"
    architecture = "CustomCNN (JILSA 2022)" if which == "jilsa" else "MobileNetV2 (PLOS ONE 2024)"
    params_m = None
    try:
        params = metrics.get("params")
        if params:
            params_m = float(params) / 1e6
    except Exception:
        params_m = None
    return {
        "_bench_name": bench_name,
        "architecture": architecture,
        "classes": len(metrics.get("classes", {})) or "—",
        "input_size": f"{imgsz}×{imgsz}",
        "params_m": params_m,
        "gflops": metrics.get("gflops"),
        "optimizer": "Adam / AdamW",
        "loss_fn": "CrossEntropyLoss",
        "accuracy": (float(metrics["accuracy"]) * 100.0) if metrics.get("accuracy") is not None else None,
        "accuracy_str": f"{float(metrics['accuracy']) * 100:.2f}%" if metrics.get("accuracy") is not None else "—",
        "map50": None,
        "map50_95": None,
        "test_images": total_images if total_images is not None else "—",
        "augmentation": "Theo cấu hình train/eval hiện tại",
        "val_loss": metrics.get("val_loss"),
        "macro_f1": metrics.get("macro_f1"),
    }
