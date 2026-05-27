from pathlib import Path

from bll.train.common import _has_classification_images, _resolve_classification_root


def prepare_jilsa_training(config: dict) -> dict:
    raw_data_path = Path(config["data_path"])
    data_path = _resolve_classification_root(raw_data_path)
    val_folder = config["val_folder"]
    train_path = data_path / "train"
    val_path = data_path / val_folder
    use_validation = _has_classification_images(val_path)

    if not train_path.is_dir():
        raise ValueError(f"Không tìm thấy thư mục train/:\n{data_path}")
    if not _has_classification_images(train_path):
        raise ValueError(f"Thư mục train/ không có ảnh hợp lệ:\n{train_path}")

    imgsz = int(config["imgsz"])
    batch = int(config["batch"])
    epochs = int(config["epochs"])
    lr = float(config["lr"])
    patience = int(config["patience"])
    workers = int(config["workers"])
    device = str(config["device"])
    out_dir = str(config["out_dir"])
    amp = bool(config["amp"])
    cos_lr = bool(config["cos_lr"])

    script = f"""
import sys, time, csv, json
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from pathlib import Path
try:
    from sklearn.metrics import accuracy_score
except ImportError:
    def accuracy_score(y_true, y_pred):
        return sum(a==b for a,b in zip(y_true,y_pred)) / max(len(y_true),1)

DEVICE = torch.device("{device}" if "{device}" == "cpu" or not torch.cuda.is_available() else "cuda")
USE_VALIDATION = {use_validation}
print(f"[INFO] Device: {{DEVICE}}", flush=True)
if DEVICE.type == "cuda":
    print(f"[INFO] GPU: {{torch.cuda.get_device_name(0)}}  VRAM: {{torch.cuda.get_device_properties(0).total_memory//1024**2}}MB", flush=True)
else:
    print("[WARN] GPU not available - using CPU", flush=True)

train_tf = transforms.Compose([
    transforms.Resize(({imgsz}, {imgsz})),
    transforms.RandomRotation(15),
    transforms.RandomHorizontalFlip(),
    transforms.RandomVerticalFlip(p=0.5),
    transforms.ColorJitter(brightness=0.2, contrast=0.2),
    transforms.ToTensor(),
    transforms.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225]),
])
val_tf = transforms.Compose([
    transforms.Resize(({imgsz}, {imgsz})),
    transforms.ToTensor(),
    transforms.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225]),
])

train_ds = datasets.ImageFolder(r"{data_path}/train", transform=train_tf)
val_ds   = datasets.ImageFolder(r"{data_path}/{val_folder}", transform=val_tf) if USE_VALIDATION else None
num_classes = len(train_ds.classes)
print(f"[INFO] Classes ({{num_classes}}): {{train_ds.classes}}", flush=True)
if USE_VALIDATION:
    print(f"[INFO] Train: {{len(train_ds)}} | {val_folder.upper()}: {{len(val_ds)}}", flush=True)
else:
    print(f"[INFO] Train: {{len(train_ds)}} | Validation: disabled", flush=True)

train_loader = DataLoader(train_ds, batch_size={batch}, shuffle=True,
                          num_workers={workers}, pin_memory=(DEVICE.type=="cuda"))
val_loader   = (
    DataLoader(val_ds, batch_size={batch}, shuffle=False,
               num_workers={workers}, pin_memory=(DEVICE.type=="cuda"))
    if USE_VALIDATION else None
)

class CustomCNN(nn.Module):
    def __init__(self, nc):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3,   32, 3, padding=1), nn.BatchNorm2d(32),  nn.ReLU(True), nn.MaxPool2d(2),
            nn.Conv2d(32,  64, 3, padding=1), nn.BatchNorm2d(64),  nn.ReLU(True), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(True), nn.MaxPool2d(2),
            nn.Conv2d(128,256, 3, padding=1), nn.BatchNorm2d(256), nn.ReLU(True), nn.MaxPool2d(2),
            nn.AdaptiveAvgPool2d((9, 9)),
        )
        flat = 256 * 9 * 9
        self.classifier = nn.Sequential(
            nn.Flatten(), nn.Linear(flat,512), nn.ReLU(True), nn.Dropout(0.5), nn.Linear(512,nc)
        )
    def forward(self, x): return self.classifier(self.features(x))

model = CustomCNN(num_classes).to(DEVICE)
total_p = sum(p.numel() for p in model.parameters())
print(f"[INFO] Params: {{total_p:,}}", flush=True)

criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr={lr})
use_amp = {amp} and DEVICE.type == "cuda"
use_cos_lr = {cos_lr}
scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
if use_cos_lr:
    scheduler = optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=max({epochs}, 1), eta_min=max({lr} * 0.01, 1e-6)
    )
else:
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5,
                                                      min_lr=1e-6)
print(f"[INFO] AMP: {{use_amp}} | Cosine LR: {{use_cos_lr}}", flush=True)

save_path = Path(r"{out_dir}") / "custom_cnn_jilsa_best.pth"
save_path.parent.mkdir(parents=True, exist_ok=True)
print(f"[INFO] Save to: {{save_path}}", flush=True)

best_acc  = 0.0
best_train_loss = float("inf")
no_improve = 0
patience_v = {patience} if USE_VALIDATION else 0
history = []
history_json_path = save_path.parent / "history_jilsa.json"
results_csv_path = save_path.parent / "results_jilsa.csv"

for epoch in range(1, {epochs}+1):
    model.train()
    run_loss = 0.0
    t0 = time.time()
    for imgs, lbls in train_loader:
        imgs, lbls = imgs.to(DEVICE), lbls.to(DEVICE)
        optimizer.zero_grad()
        with torch.amp.autocast("cuda", enabled=use_amp):
            loss = criterion(model(imgs), lbls)
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        run_loss += float(loss.item())

    avg_loss = run_loss / len(train_loader)
    acc = None
    avg_val_loss = None
    if USE_VALIDATION:
        model.eval()
        preds_all, lbls_all = [], []
        val_loss_sum = 0.0
        with torch.no_grad():
            for imgs, lbls in val_loader:
                imgs_dev = imgs.to(DEVICE)
                lbls_dev = lbls.to(DEVICE)
                logits = model(imgs_dev)
                val_loss_sum += float(criterion(logits, lbls_dev).item())
                _, p = torch.max(logits, 1)
                preds_all.extend(p.cpu().numpy())
                lbls_all.extend(lbls.numpy())
        acc = accuracy_score(lbls_all, preds_all)
        avg_val_loss = val_loss_sum / max(len(val_loader), 1)
    if use_cos_lr:
        scheduler.step()
    else:
        scheduler.step(avg_loss)
    ep_time  = time.time() - t0
    current_lr = optimizer.param_groups[0]["lr"]
    history.append({{
        "epoch": epoch,
        "train_loss": round(avg_loss, 6),
        "val_loss": round(avg_val_loss, 6) if avg_val_loss is not None else None,
        "val_acc": round(float(acc), 6) if acc is not None else None,
        "lr": round(float(current_lr), 10),
        "time_sec": round(float(ep_time), 4),
    }})
    val_loss_text = f"{{avg_val_loss:.4f}}" if avg_val_loss is not None else "N/A"
    val_acc_text = f"{{acc:.4f}}" if acc is not None else "N/A"
    print(f"[EPOCH] {{epoch}}/{epochs} | Loss: {{avg_loss:.4f}} | Val Loss: {{val_loss_text}} | Val Acc: {{val_acc_text}} | LR: {{current_lr:.6f}} | Time: {{ep_time:.1f}}s", flush=True)

    is_better = (acc > best_acc) if USE_VALIDATION else (avg_loss < best_train_loss)
    if is_better:
        if USE_VALIDATION:
            best_acc = acc
        else:
            best_train_loss = avg_loss
        _ckpt = {{
            'model_weights': model.state_dict(),
            'class_names': list(train_ds.classes),
            'history': history,
            'best_val_accuracy': float(best_acc) if USE_VALIDATION else None,
            'best_train_loss': float(best_train_loss) if not USE_VALIDATION else None,
        }}
        torch.save(_ckpt, str(save_path))
        if USE_VALIDATION:
            print(f"[BEST] epoch={{epoch}} acc={{best_acc:.4f}}", flush=True)
        else:
            print(f"[BEST] epoch={{epoch}} train_loss={{best_train_loss:.4f}}", flush=True)
        no_improve = 0
    else:
        no_improve += 1
    if patience_v > 0 and no_improve >= patience_v:
        print(f"[INFO] Early stopping tại epoch {{epoch}} (patience={{patience_v}})", flush=True)
        break

history_json_path.write_text(json.dumps({{
    "class_names": list(train_ds.classes),
    "best_val_accuracy": best_acc if USE_VALIDATION else None,
    "best_train_loss": best_train_loss if not USE_VALIDATION else None,
    "used_validation": USE_VALIDATION,
    "history": history,
}}, ensure_ascii=False, indent=2), encoding="utf-8")
with open(results_csv_path, "w", newline="", encoding="utf-8") as _csv_f:
    writer = csv.DictWriter(_csv_f, fieldnames=["epoch", "train_loss", "val_loss", "val_acc", "lr", "time_sec"])
    writer.writeheader()
    writer.writerows(history)
print(f"[RESULT] History JSON: {{history_json_path}}", flush=True)
print(f"[RESULT] Results CSV: {{results_csv_path}}", flush=True)
print("[DONE] Training complete!", flush=True)
if USE_VALIDATION:
    print(f"[RESULT] Best Val Accuracy = {{best_acc:.4f}}", flush=True)
else:
    print(f"[RESULT] Best Train Loss = {{best_train_loss:.4f}}", flush=True)
print(f"[RESULT] Model saved: {{save_path}}", flush=True)
print(f"[RESULT] Class names: {{train_ds.classes}}", flush=True)
sys.stdout.flush()
import os as _os
_os._exit(0)
"""
    return {
        "raw_data_path": raw_data_path,
        "data_path": data_path,
        "use_validation": use_validation,
        "val_folder": val_folder,
        "imgsz": imgsz,
        "batch": batch,
        "epochs": epochs,
        "lr": lr,
        "patience": patience,
        "workers": workers,
        "device": device,
        "out_dir": out_dir,
        "amp": amp,
        "cos_lr": cos_lr,
        "script": script,
    }


def prepare_plos_training(config: dict) -> dict:
    raw_data_path = Path(config["data_path"])
    data_path = _resolve_classification_root(raw_data_path)
    train_path = data_path / "train"
    val_path = data_path / "val"
    use_validation = _has_classification_images(val_path)

    if not train_path.is_dir():
        raise ValueError(f"Không tìm thấy thư mục train/:\n{data_path}")
    if not _has_classification_images(train_path):
        raise ValueError(f"Thư mục train/ không có ảnh hợp lệ:\n{train_path}")

    imgsz = int(config["imgsz"])
    batch = int(config["batch"])
    epochs = int(config["epochs"])
    lr = float(config["lr"])
    patience = int(config["patience"])
    workers = int(config["workers"])
    device = str(config["device"])
    optimizer = str(config["optimizer"])
    freeze = bool(config["freeze"])
    out_dir = str(config["out_dir"])
    weights_path = str(config.get("weights_path", "")).strip()
    amp = bool(config["amp"])
    cos_lr = bool(config["cos_lr"])
    freeze_str = "True" if freeze else "False"
    local_weights_str = weights_path.replace("\\", "\\\\") if weights_path else ""

    script = f"""
import sys, time, csv, json
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
from pathlib import Path
try:
    from sklearn.metrics import accuracy_score
except ImportError:
    def accuracy_score(y_true, y_pred):
        return sum(a==b for a,b in zip(y_true,y_pred)) / max(len(y_true),1)

DEVICE = torch.device("{device}" if "{device}" == "cpu" or not torch.cuda.is_available() else "cuda")
USE_VALIDATION = {use_validation}
print(f"[INFO] Device: {{DEVICE}}", flush=True)
if DEVICE.type == "cuda":
    print(f"[INFO] GPU: {{torch.cuda.get_device_name(0)}}  VRAM: {{torch.cuda.get_device_properties(0).total_memory//1024**2}}MB", flush=True)
else:
    print("[WARN] GPU not available - using CPU", flush=True)

train_tf = transforms.Compose([
    transforms.Resize(({imgsz}, {imgsz})),
    transforms.RandomRotation(15),
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
    transforms.ToTensor(),
    transforms.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225]),
])
val_tf = transforms.Compose([
    transforms.Resize(({imgsz}, {imgsz})),
    transforms.ToTensor(),
    transforms.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225]),
])

train_ds = datasets.ImageFolder(r"{data_path}/train", transform=train_tf)
val_ds   = datasets.ImageFolder(r"{data_path}/val", transform=val_tf) if USE_VALIDATION else None
num_classes = len(train_ds.classes)
print(f"[INFO] Classes ({{num_classes}}): {{train_ds.classes}}", flush=True)
if USE_VALIDATION:
    print(f"[INFO] Train: {{len(train_ds)}} | Val: {{len(val_ds)}}", flush=True)
else:
    print(f"[INFO] Train: {{len(train_ds)}} | Validation: disabled", flush=True)

train_loader = DataLoader(train_ds, batch_size={batch}, shuffle=True,
                          num_workers={workers}, pin_memory=(DEVICE.type=="cuda"))
val_loader   = (
    DataLoader(val_ds, batch_size={batch}, shuffle=False,
               num_workers={workers}, pin_memory=(DEVICE.type=="cuda"))
    if USE_VALIDATION else None
)

_local_weights = r"{local_weights_str}"
if _local_weights:
    print(f"[INFO] Load weights từ local: {{_local_weights}}", flush=True)
    model = models.mobilenet_v2(weights=None)
    state = torch.load(_local_weights, map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    print("[INFO] MobileNetV2 loaded (local weights)", flush=True)
else:
    try:
        model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.IMAGENET1K_V1)
        print("[INFO] MobileNetV2 loaded (ImageNet weights, online)", flush=True)
    except Exception as _e:
        print(f"[WARN] Tải ImageNet thất bại ({{_e}}), dùng random weights!", flush=True)
        model = models.mobilenet_v2(weights=None)
        print("[INFO] MobileNetV2 loaded (random weights - không có pretrained)", flush=True)

if {freeze_str}:
    for param in model.features.parameters():
        param.requires_grad = False
    print("[INFO] Backbone frozen - chỉ train Classifier Head", flush=True)
else:
    print("[INFO] Fine-tuning toàn bộ mạng (không freeze)", flush=True)

model.classifier = nn.Sequential(
    nn.Dropout(p=0.2),
    nn.Linear(model.last_channel, 128),
    nn.ReLU(inplace=True),
    nn.Dropout(p=0.2),
    nn.Linear(128, num_classes),
)
model = model.to(DEVICE)
trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
total_p   = sum(p.numel() for p in model.parameters())
print(f"[INFO] Params: {{trainable:,}} trainable / {{total_p:,}} total", flush=True)

criterion = nn.CrossEntropyLoss()
params_to_train = [p for p in model.parameters() if p.requires_grad]
opt_name = "{optimizer}"
if opt_name == "AdamW":
    optimizer = optim.AdamW(params_to_train, lr={lr}, weight_decay=1e-4)
elif opt_name == "RMSprop":
    optimizer = optim.RMSprop(params_to_train, lr={lr}, alpha=0.9, momentum=0.9, weight_decay=1e-5)
elif opt_name == "SGD":
    optimizer = optim.SGD(params_to_train, lr={lr}, momentum=0.9, weight_decay=1e-4)
else:
    optimizer = optim.Adam(params_to_train, lr={lr})
use_amp = {amp} and DEVICE.type == "cuda"
use_cos_lr = {cos_lr}
scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
if use_cos_lr:
    scheduler = optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=max({epochs}, 1), eta_min=max({lr} * 0.01, 1e-7)
    )
else:
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5,
                                                      min_lr=1e-7)
print(f"[INFO] AMP: {{use_amp}} | Cosine LR: {{use_cos_lr}}", flush=True)

save_path = Path(r"{out_dir}") / "mobilenetv2_plos_best.pth"
save_path.parent.mkdir(parents=True, exist_ok=True)
print(f"[INFO] Save to: {{save_path}}", flush=True)

best_acc   = 0.0
best_train_loss = float("inf")
no_improve = 0
patience_v = {patience} if USE_VALIDATION else 0
history = []
history_json_path = save_path.parent / "history_plos.json"
results_csv_path = save_path.parent / "results_plos.csv"

for epoch in range(1, {epochs}+1):
    model.train()
    run_loss = 0.0
    t0 = time.time()
    total_batches = max(len(train_loader), 1)
    log_every = max(1, total_batches // 8)
    for batch_idx, (imgs, lbls) in enumerate(train_loader, start=1):
        imgs, lbls = imgs.to(DEVICE), lbls.to(DEVICE)
        optimizer.zero_grad()
        with torch.amp.autocast("cuda", enabled=use_amp):
            loss = criterion(model(imgs), lbls)
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        run_loss += float(loss.item())
        if batch_idx == 1 or batch_idx % log_every == 0 or batch_idx == total_batches:
            avg_so_far = run_loss / batch_idx
            print(f"[BATCH] epoch={{epoch}} batch={{batch_idx}}/{{total_batches}} loss={{avg_so_far:.4f}}", flush=True)

    avg_loss = run_loss / len(train_loader)
    acc = None
    avg_val_loss = None
    if USE_VALIDATION:
        model.eval()
        preds_all, lbls_all = [], []
        val_loss_sum = 0.0
        with torch.no_grad():
            for imgs, lbls in val_loader:
                imgs_dev = imgs.to(DEVICE)
                lbls_dev = lbls.to(DEVICE)
                logits = model(imgs_dev)
                val_loss_sum += float(criterion(logits, lbls_dev).item())
                _, p = torch.max(logits, 1)
                preds_all.extend(p.cpu().numpy())
                lbls_all.extend(lbls.numpy())
        acc = accuracy_score(lbls_all, preds_all)
        avg_val_loss = val_loss_sum / max(len(val_loader), 1)
    if use_cos_lr:
        scheduler.step()
    else:
        scheduler.step(avg_loss)
    ep_time  = time.time() - t0
    current_lr = optimizer.param_groups[0]["lr"]
    history.append({{
        "epoch": epoch,
        "train_loss": round(avg_loss, 6),
        "val_loss": round(avg_val_loss, 6) if avg_val_loss is not None else None,
        "val_acc": round(float(acc), 6) if acc is not None else None,
        "lr": round(float(current_lr), 10),
        "time_sec": round(float(ep_time), 4),
    }})
    val_loss_text = f"{{avg_val_loss:.4f}}" if avg_val_loss is not None else "N/A"
    val_acc_text = f"{{acc:.4f}}" if acc is not None else "N/A"
    print(f"[EPOCH] {{epoch}}/{epochs} | Loss: {{avg_loss:.4f}} | Val Loss: {{val_loss_text}} | Val Acc: {{val_acc_text}} | LR: {{current_lr:.6f}} | Time: {{ep_time:.1f}}s", flush=True)

    is_better = (acc > best_acc) if USE_VALIDATION else (avg_loss < best_train_loss)
    if is_better:
        if USE_VALIDATION:
            best_acc = acc
        else:
            best_train_loss = avg_loss
        _ckpt = {{
            'model_weights': model.state_dict(),
            'class_names': list(train_ds.classes),
            'history': history,
            'best_val_accuracy': float(best_acc) if USE_VALIDATION else None,
            'best_train_loss': float(best_train_loss) if not USE_VALIDATION else None,
        }}
        torch.save(_ckpt, str(save_path))
        if USE_VALIDATION:
            print(f"[BEST] epoch={{epoch}} acc={{best_acc:.4f}}", flush=True)
        else:
            print(f"[BEST] epoch={{epoch}} train_loss={{best_train_loss:.4f}}", flush=True)
        no_improve = 0
    else:
        no_improve += 1
    if patience_v > 0 and no_improve >= patience_v:
        print(f"[INFO] Early stopping tại epoch {{epoch}} (patience={{patience_v}})", flush=True)
        break

history_json_path.write_text(json.dumps({{
    "class_names": list(train_ds.classes),
    "best_val_accuracy": best_acc if USE_VALIDATION else None,
    "best_train_loss": best_train_loss if not USE_VALIDATION else None,
    "used_validation": USE_VALIDATION,
    "history": history,
}}, ensure_ascii=False, indent=2), encoding="utf-8")
with open(results_csv_path, "w", newline="", encoding="utf-8") as _csv_f:
    writer = csv.DictWriter(_csv_f, fieldnames=["epoch", "train_loss", "val_loss", "val_acc", "lr", "time_sec"])
    writer.writeheader()
    writer.writerows(history)
print(f"[RESULT] History JSON: {{history_json_path}}", flush=True)
print(f"[RESULT] Results CSV: {{results_csv_path}}", flush=True)
print("[DONE] Training complete!", flush=True)
if USE_VALIDATION:
    print(f"[RESULT] Best Val Accuracy = {{best_acc:.4f}}", flush=True)
else:
    print(f"[RESULT] Best Train Loss = {{best_train_loss:.4f}}", flush=True)
print(f"[RESULT] Model saved: {{save_path}}", flush=True)
print(f"[RESULT] Class names: {{train_ds.classes}}", flush=True)
"""
    return {
        "raw_data_path": raw_data_path,
        "data_path": data_path,
        "use_validation": use_validation,
        "imgsz": imgsz,
        "batch": batch,
        "epochs": epochs,
        "lr": lr,
        "patience": patience,
        "workers": workers,
        "device": device,
        "optimizer": optimizer,
        "freeze": freeze,
        "out_dir": out_dir,
        "weights_path": weights_path,
        "amp": amp,
        "cos_lr": cos_lr,
        "script": script,
    }
