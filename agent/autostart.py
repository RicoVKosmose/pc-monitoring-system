import sys
import winreg
from pathlib import Path

APP_NAME = "PCMonitorAgent"
RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def get_startup_command() -> str:
    """Формирует команду запуска для реестра Windows."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'

    base_python = Path(getattr(sys, "_base_executable", sys.executable))
    pythonw_exe = base_python.with_name("pythonw.exe")
    interpreter = pythonw_exe if pythonw_exe.exists() else Path(sys.executable)

    main_script = Path(__file__).resolve().parent / "main.py"
    return f'"{interpreter}" "{main_script}"'


def is_autostart_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(value)
    except OSError:
        return False


def set_autostart(enable: bool) -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            if enable:
                cmd = get_startup_command()
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
                print(f"[Autostart] Включено: {cmd}")
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                    print("[Autostart] Отключено")
                except FileNotFoundError:
                    pass
        return True
    except OSError as e:
        print(f"[Autostart] Ошибка реестра: {e}")
        return False