from dal.jsonb.config_store import COMPARE_CONFIG_PATH, INPUT_CONFIG_PATH, TESTER_CONFIG_PATH
from dal.jsonb.json_store import read_json, write_json


def save_tester_config(data: dict) -> None:
    write_json(TESTER_CONFIG_PATH, data)


def load_tester_config() -> dict:
    return read_json(TESTER_CONFIG_PATH, default={}) or {}


def load_compare_registry() -> dict:
    return read_json(COMPARE_CONFIG_PATH, default={}) or {}


def save_compare_registry(data: dict) -> None:
    write_json(COMPARE_CONFIG_PATH, data)


def load_input_registry() -> dict:
    return read_json(INPUT_CONFIG_PATH, default={}) or {}


def save_input_registry(data: dict) -> None:
    write_json(INPUT_CONFIG_PATH, data)
