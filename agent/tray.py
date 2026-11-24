import ctypes
from ctypes import wintypes
from pathlib import Path
from PySide6.QtCore import Qt, QAbstractNativeEventFilter
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication

from autostart import is_autostart_enabled, set_autostart

# Константы Windows API для RegisterHotKey
WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_NOREPEAT = 0x4000
VK_Y = 0x59  # Виртуальный код клавиши Y
HOTKEY_ID = 1


class WinHotkeyFilter(QAbstractNativeEventFilter):
    """Перехватывает системное событие WM_HOTKEY от Windows API."""
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def nativeEventFilter(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            msg = ctypes.cast(int(message), ctypes.POINTER(wintypes.MSG)).contents
            if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                self.callback()
                return True, 0
        return False, 0


def load_tray_icon() -> QIcon:
    icon_path = Path(__file__).resolve().parent.parent / "assets" / "icon1.png"
    if icon_path.exists():
        return QIcon(str(icon_path))

    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#0F172A"))
    painter.setPen(QColor("#38BDF8"))
    painter.drawRoundedRect(4, 4, 56, 56, 14, 14)
    painter.end()
    return QIcon(pixmap)


class SystemTrayManager:
    def __init__(self, overlay_widget):
        self.overlay = overlay_widget

        # Иконка в трее
        self.tray = QSystemTrayIcon(load_tray_icon(), parent=self.overlay)
        self.tray.setToolTip("PC Monitor (Alt+Y)")

        menu = QMenu()
        self.toggle_action = QAction("Показать / Скрыть (Alt+Y)", menu)
        self.toggle_action.triggered.connect(self.toggle_overlay)

        self.autostart_action = QAction("Запускать вместе с Windows", menu)
        self.autostart_action.setCheckable(True)
        self.autostart_action.setChecked(is_autostart_enabled())
        self.autostart_action.triggered.connect(self._on_autostart_toggled)

        quit_action = QAction("Выход", menu)
        quit_action.triggered.connect(self.quit_app)

        menu.addAction(self.toggle_action)
        menu.addAction(self.autostart_action)
        menu.addSeparator()
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

        self._hotkey_filter = WinHotkeyFilter(self.toggle_overlay)
        QApplication.instance().installNativeEventFilter(self._hotkey_filter)
        ok = ctypes.windll.user32.RegisterHotKey(None, HOTKEY_ID, MOD_ALT | MOD_NOREPEAT, VK_Y)
        if not ok:
            print("[Hotkey] Не удалось зарегистрировать Alt+Y (сочетание уже занято другой программой)")

    def _on_autostart_toggled(self, checked: bool):
        if not set_autostart(checked):
            self.autostart_action.setChecked(not checked)

    def toggle_overlay(self):
        if self.overlay.isVisible():
            self.overlay.hide()
        else:
            self.overlay.show()
            self.overlay.raise_()

    def _on_tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.toggle_overlay()

    def quit_app(self):
        ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_ID)
        self.tray.hide()
        QApplication.quit()