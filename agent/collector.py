import platform
import shutil
import socket
import subprocess
import time
from datetime import datetime, timezone
import psutil

try:
    import pynvml
    HAS_NVML = True
except ImportError:
    HAS_NVML = False

try:
    import win32pdh
    HAS_WIN32PDH = True
except ImportError:
    HAS_WIN32PDH = False


class GpuMonitor:
    """Универсальный сборщик нагрузки GPU (NVML -> nvidia-smi -> Windows PDH)."""
    def __init__(self):
        self.mode = None
        self.nvml_handle = None
        self.nvidia_smi_path = None
        self.query = None
        self.counter = None

        # 1. Пробуем NVIDIA NVML
        if HAS_NVML:
            try:
                pynvml.nvmlInit()
                if pynvml.nvmlDeviceGetCount() > 0:
                    self.nvml_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    self.mode = "nvml"
                    print("[GPU] Инициализирован через NVML")
                    return
            except Exception as e:
                print(f"[GPU] NVML недоступен: {e}")

        # 2. Пробуем системную утилиту nvidia-smi (идёт с драйвером NVIDIA)
        smi = shutil.which("nvidia-smi")
        if smi:
            self.nvidia_smi_path = smi
            self.mode = "nvidia-smi"
            print(f"[GPU] Инициализирован через {smi}")
            return

        # 3. Пробуем Windows Performance Counter (для Intel HD Graphics / AMD)
        if HAS_WIN32PDH:
            for path in (
                r"\GPU Engine(*engtype_3D)\Utilization Percentage",
                r"\GPU Engine(*)\Utilization Percentage",
            ):
                try:
                    q = win32pdh.OpenQuery()
                    c = win32pdh.AddEnglishCounter(q, path)
                    win32pdh.CollectQueryData(q)
                    self.query = q
                    self.counter = c
                    self.mode = "pdh"
                    print(f"[GPU] Инициализирован через PDH ({path})")
                    return
                except Exception as e:
                    print(f"[GPU] PDH ({path}) недоступен: {e}")

        print("[GPU] Не удалось найти поддерживаемый источник телеметрии GPU")

    def get_usage(self) -> float | None:
        if self.mode == "nvml":
            try:
                util = pynvml.nvmlDeviceGetUtilizationRates(self.nvml_handle)
                return round(float(util.gpu), 1)
            except Exception:
                return None

        if self.mode == "nvidia-smi":
            try:
                out = subprocess.check_output(
                    [
                        self.nvidia_smi_path,
                        "--query-gpu=utilization.gpu",
                        "--format=csv,noheader,nounits",
                    ],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=1,
                )
                return round(float(out.decode().strip().splitlines()[0]), 1)
            except Exception:
                return None

        if self.mode == "pdh":
            try:
                win32pdh.CollectQueryData(self.query)
                _, values = win32pdh.GetFormattedCounterArray(
                    self.counter, win32pdh.PDH_FMT_DOUBLE
                )
                if not values:
                    return 0.0
                total = sum(v for name, v in values if v >= 0 and "engtype_3D" in name)
                if total == 0.0:
                    total = max((v for _, v in values if v >= 0), default=0.0)
                return round(min(total, 100.0), 1)
            except Exception:
                return 0.0

        return None


class TelemetryCollector:
    """Сбор системных метрик текущего ПК."""
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