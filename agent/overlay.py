from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
)
from collector import TelemetryCollector


class HudOverlay(QWidget):
    def __init__(self, collector: TelemetryCollector):
        super().__init__()
        self.collector = collector
        self._drag_pos: QPoint | None = None

        self._init_window()
        self._init_ui()
        self._init_timer()

    def _init_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(250)

        screen_geo = self.screen().availableGeometry()
        self.move(screen_geo.right() - self.width() - 20, screen_geo.top() + 20)

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        self.container = QFrame()
        self.container.setObjectName("hudContainer")
        self.container.setStyleSheet("""
            QFrame#hudContainer {
                background-color: rgba(15, 23, 42, 215);
                border: 1px solid rgba(56, 189, 248, 120);
                border-radius: 10px;
            }
            QLabel {
                color: #E2E8F0;
                font-family: 'Segoe UI', sans-serif;
                background: transparent;
            }
            QPushButton#closeBtn {
                color: #94A3B8;
                background: transparent;
                border: none;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#closeBtn:hover {
                color: #F87171;
            }
        """)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(12, 8, 12, 10)
        layout.setSpacing(6)

        header = QHBoxLayout()
        self.title_label = QLabel("PC MONITOR")
        self.title_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #38BDF8; letter-spacing: 1px;")

        close_btn = QPushButton("×")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(18, 18)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.hide)

        header.addWidget(self.title_label)
        header.addStretch()
        header.addWidget(close_btn)
        layout.addLayout(header)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: rgba(148, 163, 184, 50); max-height: 1px;")
        layout.addWidget(line)

        _, self.cpu_val = self._add_metric_row(layout, "CPU")
        self.gpu_row, self.gpu_val = self._add_metric_row(layout, "GPU")
        _, self.ram_val = self._add_metric_row(layout, "RAM")
        _, self.disk_val = self._add_metric_row(layout, "DISK C:")
        _, self.net_val = self._add_metric_row(layout, "NET")

        root_layout.addWidget(self.container)

    def _add_metric_row(self, parent_layout: QVBoxLayout, name: str) -> tuple[QWidget, QLabel]:
        row_widget = QWidget()
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(0, 0, 0, 0)

        name_lbl = QLabel(name)
        name_lbl.setFont(QFont("Segoe UI", 9))
        name_lbl.setStyleSheet("color: #94A3B8;")

        val_lbl = QLabel("...")
        val_lbl.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        row.addWidget(name_lbl)
        row.addStretch()
        row.addWidget(val_lbl)
        parent_layout.addWidget(row_widget)
        return row_widget, val_lbl

    def _init_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_metrics)
        self.timer.start(1000)
        self.update_metrics()

    def _get_status_color(self, percent: float) -> str:
        if percent >= 85:
            return "#F87171"
        if percent >= 65:
            return "#FBBF24"
        return "#34D399"

    def update_metrics(self):
        data = self.collector.collect()

        self.title_label.setText(f"● {data['host']['hostname']}")

        cpu_p = data["cpu"]["usage_percent"]
        self.cpu_val.setText(f"{cpu_p:.1f}%")
        self.cpu_val.setStyleSheet(f"color: {self._get_status_color(cpu_p)};")

        gpu = data["gpu"]
        if gpu["available"] and gpu["usage_percent"] is not None:
            self.gpu_row.show()
            gpu_p = gpu["usage_percent"]
            self.gpu_val.setText(f"{gpu_p:.1f}%")
            self.gpu_val.setStyleSheet(f"color: {self._get_status_color(gpu_p)};")
        else:
            self.gpu_row.hide()
            self.adjustSize()

        ram = data["memory"]
        self.ram_val.setText(f"{ram['used_gb']}/{ram['total_gb']} GB ({ram['percent']}%)")
        self.ram_val.setStyleSheet(f"color: {self._get_status_color(ram['percent'])};")

        disk = data["disk"]
        self.disk_val.setText(f"{disk['percent']}% ({disk['used_gb']} GB)")
        self.disk_val.setStyleSheet("color: #E2E8F0;")

        net = data["network"]
        self.net_val.setText(f"↓{net['download_mbps']:.1f}  ↑{net['upload_mbps']:.1f} Mbps")
        self.net_val.setStyleSheet("color: #38BDF8;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            target = event.globalPosition().toPoint() - self._drag_pos
            screen_geo = self.screen().availableGeometry()

            min_x = screen_geo.left()
            max_x = screen_geo.right() - self.width() + 1
            min_y = screen_geo.top()
            max_y = screen_geo.bottom() - self.height() + 1

            clamped_x = max(min_x, min(target.x(), max_x))
            clamped_y = max(min_y, min(target.y(), max_y))

            self.move(clamped_x, clamped_y)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None