import json
import uuid
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

DEFAULT_CONFIG = {
    "machine_id": str(uuid.uuid4()),
    "rabbitmq_host": "localhost",
    "rabbitmq_port": 5672,
    "rabbitmq_user": "admin",
    "rabbitmq_pass": "admin123",
    "exchange_name": "pc_monitor",
    "send_interval_sec": 3,
    "thresholds": {
        "cpu_percent": 85.0,
        "gpu_percent": 85.0,
        "memory_percent": 85.0,
        "disk_percent": 90.0,
    },
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                merged = {**DEFAULT_CONFIG, **data}
                merged["thresholds"] = {
                    **DEFAULT_CONFIG["thresholds"],
                    **data.get("thresholds", {}),
                }
                return merged
        except Exception:
            pass

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
    return DEFAULT_CONFIG.copy()