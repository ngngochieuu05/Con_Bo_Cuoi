from pathlib import Path

TOOL_TRAIN_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = TOOL_TRAIN_DIR / "src"
UI_DIR = SRC_DIR / "ui"
BLL_DIR = SRC_DIR / "bll"
DAL_DIR = SRC_DIR / "dal"
JSONB_DIR = DAL_DIR / "jsonb"
RUNS_DIR = TOOL_TRAIN_DIR / "runs"
CONTENT_DIR = TOOL_TRAIN_DIR / "noi_dung"


def bootstrap_sys_path(sys_path) -> None:
    for path in (SRC_DIR, UI_DIR):
        path_str = str(path)
        if path_str not in sys_path:
            sys_path.insert(0, path_str)
