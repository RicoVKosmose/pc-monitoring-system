import platform
import socket
import time
from datetime import datetime, timezone
import psutil

try:
    import win32pdh
    HAS_WIN32PDH = True
except ImportError:
    HAS_WIN32PDH = False


class GpuMonitor:
    """Чтение общей загрузки GPU через счётчики производительности Windows (как в Диспетчере задач)."""
    def __init__(self):
        self.available = False
        self.query = None
        self.counter = None

        if not HAS_WIN32PDH:
            return

        try:
            self.query = win32pdh.OpenQuery()
            # Счётчик утилизации 3D/вычислительных движков GPU
            path = r"\GPU Engine(*engtype_3D)\Utilization Percentage"
            self.counter = win32pdh.AddEnglishCounter(self.query, path)
            win32pdh.CollectQueryData(self.query)
            self.available = True
        except Exception:
            self.available = False

    def get_usage(self) -> float | None:
        if not self.available:
            return None
        try:
            win32pdh.CollectQueryData(self.query)
            _, values = win32pdh.GetFormattedCounterArray(
                self.counter, win32pdh.PDH_FMT_DOUBLE
            )
            # Суммируем нагрузку по всем активным процессам на 3D-движке (не больше 100%)
            total = sum(v for _, v in values if v >= 0)
            return round(min(total, 100.0), 1)
        except Exception:
            return None


class TelemetryCollector:
    def __init__(self):
        self._last_net = psutil.net_io_counters()
        self._last_time = time.time()
        self._gpu = GpuMonitor()
        psutil.cpu_percent(interval=None)

    def collect(self) -> dict:
        now = time.time()
        dt = max(now - self._last_time, 0.1)

        # Скорость сети (Мбит/с)
        net = psutil.net_io_counters()
        download_mbps = ((net.bytes_recv - self._last_net.bytes_recv) * 8) / (dt * 1_000_000)
        upload_mbps = ((net.bytes_sent - self._last_net.bytes_sent) * 8) / (dt * 1_000_000)
        self._last_net = net
        self._last_time = now

        # Память и диск
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\")
        gpu_usage = self._gpu.get_usage()

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
            "gpu": {
                "available": gpu_usage is not None,
                "usage_percent": gpu_usage,
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