# Con Bo Cuoi

AI cattle monitoring app plus model-training toolkit.

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Flet](https://img.shields.io/badge/Flet-0.28.x-00A8E8?style=flat-square)](https://flet.dev)
[![YOLO](https://img.shields.io/badge/YOLO-Ultralytics-FF6B35?style=flat-square)](https://ultralytics.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

## Overview

`main` now keeps the two app folders copied from `devH` as-is:

- `webapp_system/`: Flet desktop/web app for cattle monitoring, role dashboards, AI consulting, alerts, camera streaming, Telegram notifications, and PostgreSQL-backed app data.
- `tool_train/`: desktop toolkit for dataset preparation, model training, model testing, batch evaluation, augmentation, and training artifacts.

## Features

| Area | Capability |
| --- | --- |
| Monitoring | Live camera feed, YOLO detection, behavior/disease alert workflows |
| Roles | Admin, expert, farmer dashboards and profile/settings pages |
| Consulting | Farmer AI chat, snapshots, expert review, local chat history |
| Alerts | Telegram bot/alert services and PostgreSQL-backed alert records |
| Training | Dataset split/copy/augment tools and YOLO/classification trainers |
| Testing | Model registry, inference, segment, artifact, history, and batch evaluation services |

## Structure

```text
Con_Bo_Cuoi/
|-- webapp_system/
|   |-- README.md
|   |-- data/
|   |-- skill/
|   `-- src/
|       |-- main.py
|       |-- bll/
|       |-- dal/
|       |   |-- base_repo.py
|       |   `-- db/app_config.json
|       `-- ui/
|           |-- theme.py
|           `-- components/
|-- tool_train/
|   `-- src/
|       |-- main_test.py
|       |-- bll/
|       |-- dal/jsonb/
|       `-- ui/
|-- docs/
|-- guide/
|-- LICENSE
|-- SECURITY.md
`-- CLAUDE.md
```

## Architecture

`webapp_system/src` uses a strict layered flow:

```text
UI components -> BLL services/admin/user modules -> DAL repositories -> PostgreSQL
```

- UI lives under `webapp_system/src/ui/components/` and shared UI helpers live in `webapp_system/src/ui/theme.py`.
- BLL lives under `webapp_system/src/bll/` and owns auth, monitoring, chat, alert, Telegram, admin, expert, and farmer workflows.
- DAL lives under `webapp_system/src/dal/`. `base_repo.py` stores data in PostgreSQL table `json_store`; entity wrappers stay in `*_repo.py`.

`tool_train/src` mirrors the same separation at a toolkit level: `ui/`, `bll/`, and `dal/jsonb/`.

## Requirements

- Python 3.10+ recommended.
- PostgreSQL local database named `ConBoCuoi_DB`, unless you change config.
- Windows 10/11 for the main desktop flow. Web mode can run where Flet/OpenCV work.
- Camera optional for setup, required for live monitoring.
- CUDA GPU recommended for training/inference; CPU mode is possible.

No pinned `requirements.txt` is tracked on `main` right now. Install dependencies manually or create a local requirements file for your machine.

## Setup

```bash
git clone https://github.com/ngngochieuu05/Con_Bo_Cuoi.git
cd Con_Bo_Cuoi

python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip

pip install flet opencv-python ultralytics pillow numpy requests qrcode psycopg2-binary cryptography google-generativeai customtkinter albumentations

# CUDA 12.x
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# CPU only alternative
# pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

PostgreSQL setup:

1. Create database `ConBoCuoi_DB`.
2. Adjust local DB credentials in `webapp_system/src/dal/base_repo.py` and `webapp_system/src/dal/db/app_config.json` if needed.
3. Run the app once so DAL seed functions initialize data through `json_store`.

## Run

Monitoring app:

```bash
python webapp_system/src/main.py
```

Training/testing toolkit:

```bash
python tool_train/src/main_test.py
```

Web mode is controlled by `webapp_system/src/dal/db/app_config.json`:

```text
app_mode = web
app_port = 8080
```

When web mode starts, the app checks the configured port, falls back to a nearby free port if needed, prints LAN URLs, and generates `qr_access.png` for phone access on the same network.

## Default Accounts

| Role | Username | Password |
| --- | --- | --- |
| Admin | `admin` | `admin123` |
| Expert | `expert01` | `expert123` |
| Farmer | `farmer01` | `farmer123` |

Change these before any shared or production deployment.

## Config Notes

- App mode, port, camera indexes, model mode, Telegram settings, and alert thresholds live in `webapp_system/src/dal/db/app_config.json`.
- PostgreSQL defaults are currently in `webapp_system/src/dal/base_repo.py`.
- Telegram services live in `webapp_system/src/bll/services/telegram_*.py`.
- Toolkit local configs live in `tool_train/src/dal/jsonb/`.

## Security

- Do not commit real production passwords, Telegram tokens, API keys, model secrets, or `.env` files.
- Rotate local credentials before deploying outside a private development machine.
- Seed accounts use weak passwords for development only.
- See [SECURITY.md](SECURITY.md).

## Development Notes

- Keep UI calls behind BLL services; UI should not call DAL directly.
- Keep DAL access behind repository wrappers; `BaseRepo` owns persistence details.
- Use `ft.Colors.*` and `ft.Icons.*` in Flet code.
- Use helpers from `webapp_system/src/ui/theme.py` instead of inline UI styling.
- Keep `tool_train` code under `tool_train/src`; do not recreate duplicated top-level `tool_train/bll`, `tool_train/dal`, or `tool_train/ui` folders.

## Tieng Viet

Du an co hai phan chinh tren `main`: `webapp_system/` cho ung dung giam sat bo AI va `tool_train/` cho bo cong cu train/test model. Hien tai `main` khong track `requirements.txt`, nen cai dependencies theo muc Setup. Can PostgreSQL database `ConBoCuoi_DB` truoc khi chay app chinh.

Chay app: `python webapp_system/src/main.py`

Chay toolkit: `python tool_train/src/main_test.py`

## License

Distributed under the MIT License. See [LICENSE](LICENSE).
