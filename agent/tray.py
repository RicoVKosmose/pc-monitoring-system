from pathlib import Path
from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
import keyboard


class HotkeyBridge(QObject):
    """Мост для безопасной передачи нажатия хоткея из фонового потока в GUI-поток Qt."""
    triggered = Signal()


def load_tray_icon() -> QIcon:
    """Загругка иконки """
    icon_path = Path(__file__).resolve().parent.parent / "assets" / "icon.jpg"
    if icon_path.exists():
        return QIcon(str(icon_path))

    # Резервная программная иконка
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

        # Иконка в системном трее
        self.tray = QSystemTrayIcon(load_tray_icon(), parent=self.overlay)
        self.tray.setToolTip(f"PC Monitor ({hotkey.upper()})")

        # Контекстное меню
        menu = QMenu()
        self.toggle_action = QAction(f"Показать / Скрыть ({hotkey.upper()})", menu)
        self.toggle_action.triggered.connect(self.toggle_overlay)

        quit_action = QAction("Выход", menu)
        quit_action.triggered.connect(self.quit_app)

        menu.addAction(self.toggle_action)
        menu.addSeparator()
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

        # Глобальная горячая клавиша
        self.hotkey_bridge = HotkeyBridge()
        self.hotkey_bridge.triggered.connect(self.toggle_overlay)
        keyboard.add_hotkey(self.hotkey, self.hotkey_bridge.triggered.emit)

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