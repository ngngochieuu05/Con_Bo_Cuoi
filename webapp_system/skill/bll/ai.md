# AI / YOLO Model Management Skills

## Architecture Decision: Model Ownership

### System-level model (Admin > Model management)
- `disease` (Benh tren bo) — anh huong toan bo he thong, admin quan ly

### User-level models (Admin > Tai khoan)
- `cattle_detect` (Nhan dien bo) — phuc vu farmer/expert
- `behavior` (Hanh vi bo) — phuc vu farmer/expert
- Hien thi trong phan "Model nguoi dung" ben duoi danh sach tai khoan

## YOLO Config Parameters
- `conf` — Confidence threshold: 0.05–0.95 (step 0.05)
- `iou`  — IoU threshold for NMS: 0.05–0.95 (step 0.05)
- `duong_dan_file` — absolute or relative path to `.pt` weights file
- Validate: path must end in `.pt` before saving

## DAL Functions (dal/model_repo.py)
- `get_all_models()` — returns all 3 models
- `get_model_by_type(loai)` — fetch single model by type string
- `update_model_config(id, conf, iou, path)` — save YOLO params
- `update_model_status(id, trang_thai)` — toggle online/offline
- `update_model(id, dict)` — generic field update

## UI Patterns
- YOLO sliders: min=0.05, max=0.95, divisions=18, live value `ft.Text` beside slider
- Per-card state: `_state = {"conf": ..., "iou": ...}` dict mutated by lambda
- Collapsible config panel: `ft.Ref[ft.Container]` toggled by button
- `.pt` indicator row: green CHECK_CIRCLE if path ends in `.pt`, else grey
- Status badge uses `status_badge(label, kind)` from theme.py
- `button_style("warning")` for disease model (amber accent)
- `button_style("primary")` for user models (green accent)

## Encoding Pitfall
- PowerShell `Set-Content` writes UTF-16LE (BOM) by default — causes `U+FEFF` SyntaxError
- Always write Python files with `open(path, 'w', encoding='utf-8')` from Python script
- Strip existing BOM: `data[3:]` if `data.startswith(b'\xef\xbb\xbf')`
- Use helper script `_patch_*.py` written via `create_file` tool, then run with Python

## Duplicate Code Prevention
- `replace_string_in_file` can APPEND if `oldString` not found — always verify line count after
- Safe approach: read lines, find cut point by searching for function signature, slice + rewrite
- After rewrite always run `ast.parse()` to validate syntax
