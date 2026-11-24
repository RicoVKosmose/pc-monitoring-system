from pathlib import Path
from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
import keyboard

from autostart import is_autostart_enabled, set_autostart


class HotkeyBridge(QObject):
    """Мост для безопасной передачи нажатия хоткея из фонового потока в GUI-поток Qt."""
    triggered = Signal()


def load_tray_icon() -> QIcon:
    """Загружает иконку из assets/icon.png с резервной генерацией, если файл отсутствует."""
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
    def __init__(self, overlay_widget, hotkey: str = "alt+r"):
        self.overlay = overlay_widget
        self.hotkey = hotkey

        self.tray = QSystemTrayIcon(load_tray_icon(), parent=self.overlay)
        self.tray.setToolTip(f"PC Monitor ({hotkey.upper()})")

        menu = QMenu()

        self.toggle_action = QAction(f"Показать / Скрыть ({hotkey.upper()})", menu)
        self.toggle_action.triggered.connect(self.toggle_overlay)

        # Пункт управления автозагрузкой с галочкой
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

        self.hotkey_bridge = HotkeyBridge()
        self.hotkey_bridge.triggered.connect(self.toggle_overlay)
        keyboard.add_hotkey(self.hotkey, self.hotkey_bridge.triggered.emit)

    def _on_autostart_toggled(self, checked: bool):
        success = set_autostart(checked)
        if not success:

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
        keyboard.unhook_all()
        self.tray.hide()
        QApplication.quit()