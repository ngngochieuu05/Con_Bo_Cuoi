from __future__ import annotations

import os
import re
import time
from pathlib import Path
from uuid import uuid4

import flet as ft


_DEFAULT_UPLOAD_SECRET = "con-bo-cuoi-local-upload-key-2026"


def get_upload_dir(page: ft.Page | None) -> Path | None:
    data = getattr(page, "data", None)
    if isinstance(data, dict):
        raw = data.get("upload_dir")
        if raw:
            return Path(raw)
    return None


def get_app_mode(page: ft.Page | None) -> str:
    data = getattr(page, "data", None)
    if isinstance(data, dict):
        return str(data.get("app_mode", "desktop") or "desktop").lower()
    return "desktop"


def is_web_picker_file(file_obj) -> bool:
    return not bool(getattr(file_obj, "path", None))


def is_web_session(page: ft.Page | None) -> bool:
    if page is None:
        return False
    if get_app_mode(page) == "web":
        return True
    try:
        if bool(getattr(page, "web", False)):
            return True
    except Exception:
        pass
    platform = getattr(page, "platform", None)
    name = getattr(platform, "name", str(platform or "")).lower()
    return name in {"android", "ios", "web"}


def build_public_upload_src(relative_path: str) -> str:
    return f"/uploads/{relative_path.replace('\\', '/')}"


def wait_for_uploaded_file(path: str | Path, timeout_seconds: float = 5.0) -> Path | None:
    target = Path(path)
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            if target.exists() and target.stat().st_size > 0:
                return target
        except Exception:
            pass
        time.sleep(0.1)
    return target if target.exists() else None


def ensure_upload_secret_key() -> str:
    key = os.environ.get("FLET_SECRET_KEY") or _DEFAULT_UPLOAD_SECRET
    os.environ["FLET_SECRET_KEY"] = key
    return key


def _safe_get_upload_url(page: ft.Page, rel_path: str, expires_seconds: int) -> str:
    try:
        return page.get_upload_url(rel_path, expires_seconds)
    except Exception as exc:
        if "secret_key" not in str(exc).lower() and "flet_secret_key" not in str(exc).lower():
            raise
        ensure_upload_secret_key()
        return page.get_upload_url(rel_path, expires_seconds)


def build_upload_batch(
    page: ft.Page,
    files: list,
    subdir: str,
    expires_seconds: int = 600,
) -> tuple[list[dict], list[ft.FilePickerUploadFile]]:
    ensure_upload_secret_key()
    upload_dir = get_upload_dir(page)
    if upload_dir is None:
        raise ValueError("Không tìm thấy upload_dir trong page.data.")

    prefix = time.strftime("%Y%m%d_%H%M%S")
    subdir = re.sub(r"[^A-Za-z0-9._-]", "_", subdir.strip("/\\") or "picked")

    items: list[dict] = []
    jobs: list[ft.FilePickerUploadFile] = []
    for index, file_obj in enumerate(files):
        original_name = getattr(file_obj, "name", None) or f"file_{index}"
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", original_name)
        rel_path = f"{subdir}_{prefix}_{index}_{uuid4().hex[:8]}_{safe_name}"
        items.append(
            {
                "name": original_name,
                "relative_path": rel_path,
                "server_path": str(upload_dir / rel_path),
                "public_src": build_public_upload_src(rel_path),
                "done": False,
            }
        )
        jobs.append(
            ft.FilePickerUploadFile(
                original_name,
                _safe_get_upload_url(page, rel_path, expires_seconds),
                id=getattr(file_obj, "id", None),
            )
        )
    return items, jobs
