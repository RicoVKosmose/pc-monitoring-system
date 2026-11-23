import platform
import socket
import time
from datetime import datetime, timezone
import psutil


class TelemetryCollector:
    def __init__(self):
        self._last_net = psutil.net_io_counters()
        self._last_time = time.time()
        psutil.cpu_percent(interval=None)

    def collect(self) -> dict:
        now = time.time()
        dt = max(now - self._last_time, 0.1)

        # Расчёт скорости сети (Мбит/с)
        net = psutil.net_io_counters()
        download_mbps = ((net.bytes_recv - self._last_net.bytes_recv) * 8) / (dt * 1_000_000)
        upload_mbps = ((net.bytes_sent - self._last_net.bytes_sent) * 8) / (dt * 1_000_000)
        self._last_net = net
        self._last_time = now

        # Память
        mem = psutil.virtual_memory()

        # Основной системный диск (C:\ на Windows)
        disk = psutil.disk_usage("C:\\")

        return {
            "host": {
                "hostname": socket.gethostname(),
                "os": f"{platform.system()} {platform.release()}",
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cpu": {
                "usage_percent": psutil.cpu_percent(interval=None),
                "cores_logical": psutil.cpu_count(logical=True),
            },
            "memory": {
                "total_gb": round(mem.total / (1024 ** 3), 1),
                "used_gb": round(mem.used / (1024 ** 3), 1),
                "percent": mem.percent,
            },
            "disk": {
                "device": "C:",
                "total_gb": round(disk.total / (1024 ** 3), 1),
                "used_gb": round(disk.used / (1024 ** 3), 1),
                "percent": disk.percent,
            },
            "network": {
                "download_mbps": round(download_mbps, 2),
                "upload_mbps": round(upload_mbps, 2),
            },
        }


if __name__ == "__main__":
    collector = TelemetryCollector()
    time.sleep(1)
    print(collector.collect())