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
    "queue_name": "pc_telemetry",
    "send_interval_sec": 3,
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**DEFAULT_CONFIG, **data}
        except Exception:
            pass

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
    return DEFAULT_CONFIG.copy()