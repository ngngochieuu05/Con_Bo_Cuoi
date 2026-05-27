from bll.app_context import JSONB_DIR

INPUT_CONFIG_PATH = JSONB_DIR / "input.json"
TESTER_CONFIG_PATH = JSONB_DIR / "tester_config.json"
COMPARE_CONFIG_PATH = JSONB_DIR / "thong_so.json"


def ensure_jsonb_dir() -> None:
    JSONB_DIR.mkdir(parents=True, exist_ok=True)
