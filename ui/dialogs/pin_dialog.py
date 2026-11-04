import sys
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QApplication, QGraphicsDropShadowEffect
)
from PySide6.QtGui import QColor, QMouseEvent

from qfluentwidgets import (
    SubtitleLabel, CaptionLabel, PasswordLineEdit,
    PrimaryPushButton, PushButton, FluentIcon
)
from core.config_manager import ConfigManager


class PinVerifyDialog(QDialog):
    """
    Standalone top-level Fluent modal dialog to verify user PIN before
    restoring StealthGuard from hidden background mode.
    Works independently of whether the main window is visible or hidden.
    """

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager

        # Independent topmost frameless window
        self.setWindowFlags(
            Qt.Window |
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)

        self._drag_pos = QPoint()
        self.init_ui()

    def init_ui(self):
        self.setFixedSize(400, 260)

        # Outer layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Inner container card with shadow and dark Fluent style
        self.card = QFrame(self)
        self.card.setObjectName("dialogCard")
        self.card.setStyleSheet("""
            QFrame#dialogCard {
                background-color: #202020;
                border: 1px solid #383838;
                border-radius: 12px;
            }
        """)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 8)
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(12)

        # Header with icon and title
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        self.iconLabel = QLabel(self.card)
        self.iconLabel.setPixmap(FluentIcon.FINGERPRINT.icon().pixmap(28, 28))
        header_layout.addWidget(self.iconLabel)

        self.titleLabel = SubtitleLabel("StealthGuard Доступ", self.card)
        header_layout.addWidget(self.titleLabel, 1)
        card_layout.addLayout(header_layout)

        self.captionLabel = CaptionLabel("Введите PIN-код или пароль для разблокировки окна:", self.card)
        self.captionLabel.setStyleSheet("color: #a0a0a0;")
        card_layout.addWidget(self.captionLabel)

        # Password input
        self.pinInput = PasswordLineEdit(self.card)
        self.pinInput.setPlaceholderText("PIN-код / Пароль")
        self.pinInput.setClearButtonEnabled(True)
        self.pinInput.returnPressed.connect(self._handle_submit)
        card_layout.addWidget(self.pinInput)

        # Error label (hidden by default)
        self.errorLabel = CaptionLabel("", self.card)
        self.errorLabel.setStyleSheet("color: #ff5555; font-weight: bold;")
        self.errorLabel.hide()
        card_layout.addWidget(self.errorLabel)

        card_layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.cancelBtn = PushButton("Отмена", self.card)
        self.cancelBtn.setFixedWidth(100)
        self.cancelBtn.clicked.connect(self.reject)

        self.loginBtn = PrimaryPushButton("Войти", self.card)
        self.loginBtn.setFixedWidth(110)
        self.loginBtn.clicked.connect(self._handle_submit)

        btn_layout.addWidget(self.cancelBtn)
        btn_layout.addWidget(self.loginBtn)
        card_layout.addLayout(btn_layout)

        main_layout.addWidget(self.card)

    def showEvent(self, event):
        super().showEvent(event)
        # Center dialog on screen
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

        # Auto-focus input
        self.pinInput.setFocus()
        self.pinInput.clear()
        self.errorLabel.hide()

        # Bring window to foreground
        self.raise_()
        self.activateWindow()
        try:
            import win32gui
            win32gui.SetForegroundWindow(int(self.winId()))
        except Exception:
            pass

    def _handle_submit(self):
        pin = self.pinInput.text()
        if self.config_manager.verify_pin(pin):
            self.errorLabel.hide()
            self.accept()
        else:
            self.errorLabel.setText("❌ Неверный PIN-код или пароль")
            self.errorLabel.show()
            self.pinInput.selectAll()
            self.pinInput.setFocus()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()


class PinSetDialog(QDialog):
    """
    Standalone Fluent dialog to set or change the master PIN.
    """

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowFlags(
            Qt.Window |
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self._drag_pos = QPoint()
        self.init_ui()

    def init_ui(self):
        self.setFixedSize(420, 310)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)

        self.card = QFrame(self)
        self.card.setObjectName("dialogCard")
        self.card.setStyleSheet("""
            QFrame#dialogCard {
                background-color: #202020;
                border: 1px solid #383838;
                border-radius: 12px;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 8)
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        icon_label = QLabel(self.card)
        icon_label.setPixmap(FluentIcon.FINGERPRINT.icon().pixmap(28, 28))
        header_layout.addWidget(icon_label)

        title = SubtitleLabel("Установка мастер-пароля", self.card)
        header_layout.addWidget(title, 1)
        card_layout.addLayout(header_layout)

        desc = CaptionLabel("Задайте PIN-код или пароль для скрытого вызова:", self.card)
        desc.setStyleSheet("color: #a0a0a0;")
        card_layout.addWidget(desc)

        self.pinInput = PasswordLineEdit(self.card)
        self.pinInput.setPlaceholderText("Новый PIN-код / Пароль")
        self.pinInput.setClearButtonEnabled(True)
        card_layout.addWidget(self.pinInput)

        self.confirmInput = PasswordLineEdit(self.card)
        self.confirmInput.setPlaceholderText("Повторите PIN-код / Пароль")
        self.confirmInput.setClearButtonEnabled(True)
        self.confirmInput.returnPressed.connect(self._handle_submit)
        card_layout.addWidget(self.confirmInput)

        self.errorLabel = CaptionLabel("", self.card)
        self.errorLabel.setStyleSheet("color: #ff5555; font-weight: bold;")
        self.errorLabel.hide()
        card_layout.addWidget(self.errorLabel)

        card_layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.cancelBtn = PushButton("Отмена", self.card)
        self.cancelBtn.setFixedWidth(100)
        self.cancelBtn.clicked.connect(self.reject)

        self.saveBtn = PrimaryPushButton("Сохранить", self.card)
        self.saveBtn.setFixedWidth(110)
        self.saveBtn.clicked.connect(self._handle_submit)

        btn_layout.addWidget(self.cancelBtn)
        btn_layout.addWidget(self.saveBtn)
        card_layout.addLayout(btn_layout)

        main_layout.addWidget(self.card)

    def showEvent(self, event):
        super().showEvent(event)
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        self.pinInput.setFocus()
        self.pinInput.clear()
        self.confirmInput.clear()
        self.errorLabel.hide()

    def get_pin(self) -> str:
        return self.pinInput.text()

    def _handle_submit(self):
        p1 = self.pinInput.text()
        p2 = self.confirmInput.text()
        if not p1:
            self.errorLabel.setText("❌ Пароль не может быть пустым")
            self.errorLabel.show()
            return
        if p1 != p2:
            self.errorLabel.setText("❌ Пароли не совпадают")
            self.errorLabel.show()
            return
        self.accept()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
