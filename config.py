import yaml
import os
from pathlib import Path
from loguru import logger


def load_config(config_file="config.yaml") -> dict:
    if not os.path.exists(config_file):
        logger.warning(f"Config file not found: {config_file} — creating defaults")
        cfg = _default_config()
        _write_config(config_file, cfg)
        return cfg
    try:
        with open(config_file, "r") as f:
            cfg = yaml.safe_load(f) or {}
        logger.info(f"Config loaded from {config_file}")
        return cfg
    except Exception as e:
        logger.error(f"Failed to load config: {e} — using defaults")
        return _default_config()


def save_config(config: dict, config_file="config.yaml"):
    try:
        _write_config(config_file, config)
        logger.info("Config saved")
    except Exception as e:
        logger.error(f"Failed to save config: {e}")


def _write_config(path: str, cfg: dict):
    with open(path, "w") as f:
        yaml.safe_dump(cfg, f, default_flow_style=False, allow_unicode=True)


def _default_config() -> dict:
    return {
        "adb": {
            "adb_path": "e:/coc auto bot/adb_tools/platform-tools/adb.exe",
            "device_id": "127.0.0.1:5555",
            "port": 5555,
            "connection_timeout": 10,
        },
        "emulator": {
            "resolution_width": 1280,
            "resolution_height": 720,
        },
        "bot": {
            "template_confidence": 0.35,
            "retry_limit": 5,
            "screenshot_timeout": 15,
            "max_next_attempts": 5,
        },
        "loot": {
            "gold_thresholds": [0],
            "elixir_thresholds": [6000],
            "dark_elixir_thresholds": [0],
            "gold_priority": False,
            "elixir_priority": True,
            "dark_elixir_priority": False,
            "min_gold": 0,
            "min_elixir": 6000,
        },
        "troops": {
            "deploy_speed": 0.08,
            "custom_troops": [],
        },
        "delays": {
            "after_tap": 1.5,
            "after_find_match": 1.5,
            "after_attack_btn": 1.5,
            "next_base_wait": 1.5,
            "battle_check_interval": 2,
            "cycle_end_pause": 2,
        },
    }
