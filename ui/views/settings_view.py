from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel
)
from qfluentwidgets import (
    ScrollArea, CardWidget, SubtitleLabel, CaptionLabel, StrongBodyLabel,
    BodyLabel, SwitchButton, PushButton, PrimaryPushButton, LineEdit,
    ComboBox, TransparentToolButton, FluentIcon, InfoBar, InfoBarPosition
)
from core.config_manager import ConfigManager
from core.autostart import set_autostart, is_autostart_enabled
from ui.dialogs.pin_dialog import PinSetDialog


class SettingsView(QWidget):
    """
    Settings tab for configuring global switch, hotkeys, PIN protection and behavior.
    """
    settings_changed = Signal()
    hotkey_updated = Signal()

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setObjectName("SettingsView")
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # Header
        self.titleLabel = SubtitleLabel("Параметры StealthGuard", self)
        self.descLabel = CaptionLabel("Настройка системных триггеров, защиты доступа и производительности", self)
        main_layout.addWidget(self.titleLabel)
        main_layout.addWidget(self.descLabel)

        # Scroll Area for Cards
        scroll_area = ScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background: transparent; border: none;")

        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background: transparent;")
        cards_layout = QVBoxLayout(scroll_widget)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(12)

        # 1. Global Protection Switch Card
        self.globalCard = self._create_switch_card(
            title="Глобальная защита Проводника",
            description="Включение и отключение всех правил перехвата в реальном времени",
            checked=self.config_manager.settings.global_protection_enabled,
            callback=self._on_global_switch_toggled
        )
        cards_layout.addWidget(self.globalCard)

        # 2. Recent Files Cleaner Switch Card
        self.recentCard = self._create_switch_card(
            title="Очистка недавних файлов (Recent Cleaner)",
            description="Автоматически стирать ярлыки .lnk защищенных объектов из %AppData%\\Microsoft\\Windows\\Recent",
            checked=self.config_manager.settings.clean_recent,
            callback=self._on_recent_switch_toggled
        )
        cards_layout.addWidget(self.recentCard)

        # 3. Autostart Switch Card
        self.autostartCard = self._create_switch_card(
            title="Автозапуск при старте Windows",
            description="Запуск приложения в скрытом фоновом режиме при входе в систему",
            checked=is_autostart_enabled(),
            callback=self._on_autostart_switch_toggled
        )
        cards_layout.addWidget(self.autostartCard)

        # 4. Tray Icon Card
        self.trayCard = self._create_switch_card(
            title="Иконка в системном трее",
            description="Отображать иконку в области уведомлений Windows (отключите для полной невидимости)",
            checked=self.config_manager.settings.show_tray_icon,
            callback=self._on_tray_switch_toggled
        )
        cards_layout.addWidget(self.trayCard)

        # 5. Global Hotkey Card
        self.hotkeyCard = CardWidget(scroll_widget)
        hotkey_layout = QHBoxLayout(self.hotkeyCard)
        hotkey_layout.setContentsMargins(16, 16, 16, 16)

        hotkey_info = QVBoxLayout()
        hotkey_info.addWidget(StrongBodyLabel("Глобальное сочетание клавиш вызова", self.hotkeyCard))
        hotkey_info.addWidget(CaptionLabel("Хоткей для отображения главного окна из фонового скрытого режима", self.hotkeyCard))
        hotkey_layout.addLayout(hotkey_info, 1)

        self.hotkeyInput = LineEdit(self.hotkeyCard)
        self.hotkeyInput.setText(self.config_manager.settings.hotkey)
        self.hotkeyInput.setFixedWidth(180)

        self.applyHotkeyBtn = PushButton(FluentIcon.ACCEPT, "Применить", self.hotkeyCard)
        self.applyHotkeyBtn.clicked.connect(self._apply_hotkey)

        hotkey_layout.addWidget(self.hotkeyInput)
        hotkey_layout.addWidget(self.applyHotkeyBtn)
        cards_layout.addWidget(self.hotkeyCard)

        # 5b. Protection Toggle Hotkey Card
        self.protHotkeyCard = CardWidget(scroll_widget)
        prot_layout = QHBoxLayout(self.protHotkeyCard)
        prot_layout.setContentsMargins(16, 16, 16, 16)

        prot_info = QVBoxLayout()
        prot_info.addWidget(StrongBodyLabel("Хоткей отключения / включения защиты", self.protHotkeyCard))
        prot_info.addWidget(CaptionLabel("Быстрая пауза и возобновление перехвата и скрытия без открытия окна", self.protHotkeyCard))
        prot_layout.addLayout(prot_info, 1)

        self.protHotkeyInput = LineEdit(self.protHotkeyCard)
        self.protHotkeyInput.setText(self.config_manager.settings.protection_toggle_hotkey)
        self.protHotkeyInput.setFixedWidth(180)

        self.applyProtHotkeyBtn = PushButton(FluentIcon.ACCEPT, "Применить", self.protHotkeyCard)
        self.applyProtHotkeyBtn.clicked.connect(self._apply_protection_hotkey)

        prot_layout.addWidget(self.protHotkeyInput)
        prot_layout.addWidget(self.applyProtHotkeyBtn)
        cards_layout.addWidget(self.protHotkeyCard)

        # 4. PIN Protection Card
        self.pinCard = CardWidget(scroll_widget)
        pin_layout = QHBoxLayout(self.pinCard)
        pin_layout.setContentsMargins(16, 16, 16, 16)

        pin_info = QVBoxLayout()
        pin_info.addWidget(StrongBodyLabel("Мастер-пароль / PIN-код доступа", self.pinCard))
        pin_info.addWidget(CaptionLabel("Запрашивать ввод PIN-кода при разворачивании окна из фона", self.pinCard))
        pin_layout.addLayout(pin_info, 1)

        self.setPinBtn = PushButton(FluentIcon.EDIT, "Сменить пароль", self.pinCard)
        self.setPinBtn.clicked.connect(self._open_set_pin_dialog)

        self.pinSwitch = SwitchButton(self.pinCard)
        self.pinSwitch.setChecked(self.config_manager.settings.pin_enabled)
        self.pinSwitch.checkedChanged.connect(self._on_pin_switch_toggled)

        pin_layout.addWidget(self.setPinBtn)
        pin_layout.addWidget(self.pinSwitch)
        cards_layout.addWidget(self.pinCard)

        # 5. Polling Interval Card
        self.intervalCard = CardWidget(scroll_widget)
        interval_layout = QHBoxLayout(self.intervalCard)
        interval_layout.setContentsMargins(16, 16, 16, 16)
        interval_layout.setSpacing(12)

        interval_info = QVBoxLayout()
        interval_info.addWidget(StrongBodyLabel("Частота опроса Проводника (мс)", self.intervalCard))
        interval_info.addWidget(CaptionLabel("Задержка между проверками вкладок. Рекомендуется 50–100 мс.", self.intervalCard))
        interval_layout.addLayout(interval_info, 1)

        # Controls container
        controls_container = QHBoxLayout()
        controls_container.setSpacing(8)

        # Quick Preset ComboBox
        self.intervalCombo = ComboBox(self.intervalCard)
        self.intervalCombo.addItems([
            "50 мс (Быстрый)",
            "75 мс (Рекомендуется)",
            "100 мс (Стандартный)",
            "150 мс (Экономный)",
            "200 мс (Минимум CPU)",
            "Своё значение"
        ])
        self.intervalCombo.setFixedWidth(170)
        self.intervalCombo.currentIndexChanged.connect(self._on_interval_combo_changed)
        controls_container.addWidget(self.intervalCombo)

        # Minus button
        self.minusBtn = TransparentToolButton(FluentIcon.REMOVE, self.intervalCard)
        self.minusBtn.setToolTip("Уменьшить на 10 мс")
        self.minusBtn.clicked.connect(self._step_interval_down)
        controls_container.addWidget(self.minusBtn)

        # Direct number input (clearly visible, editable)
        self.intervalInput = LineEdit(self.intervalCard)
        self.intervalInput.setFixedWidth(75)
        self.intervalInput.setAlignment(Qt.AlignCenter)
        self.intervalInput.setValidator(QIntValidator(20, 2000, self.intervalCard))
        current_val = self.config_manager.settings.check_interval_ms
        self.intervalInput.setText(str(current_val))
        self.intervalInput.textChanged.connect(self._on_interval_text_changed)
        controls_container.addWidget(self.intervalInput)

        # Plus button
        self.plusBtn = TransparentToolButton(FluentIcon.ADD, self.intervalCard)
        self.plusBtn.setToolTip("Увеличить на 10 мс")
        self.plusBtn.clicked.connect(self._step_interval_up)
        controls_container.addWidget(self.plusBtn)

        ms_lbl = CaptionLabel("мс", self.intervalCard)
        ms_lbl.setStyleSheet("color: #a0a0a0; font-weight: bold;")
        controls_container.addWidget(ms_lbl)

        interval_layout.addLayout(controls_container)
        cards_layout.addWidget(self.intervalCard)

        # Sync initial combo selection with current interval
        self._sync_combo_with_val(current_val)

        cards_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area, 1)

    def _create_switch_card(self, title: str, description: str, checked: bool, callback) -> CardWidget:
        card = CardWidget(self)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)

        info = QVBoxLayout()
        info.addWidget(StrongBodyLabel(title, card))
        info.addWidget(CaptionLabel(description, card))
        layout.addLayout(info, 1)

        switch = SwitchButton(card)
        switch.setChecked(checked)
        switch.checkedChanged.connect(callback)
        layout.addWidget(switch)
        return card

    def _on_global_switch_toggled(self, checked: bool):
        self.config_manager.settings.global_protection_enabled = checked
        self.config_manager.save()
        try:
            from core.drive_cloaker import sync_drives_from_config
            sync_drives_from_config(self.config_manager)
        except Exception:
            pass

        # Асинхронное переключение видимости папок и приманок
        def _async_sync_folders():
            try:
                from core.config_manager import sync_rules_cloaking
                sync_rules_cloaking(self.config_manager, protection_enabled=checked)
            except Exception:
                pass
        from core.config_manager import _run_async
        _run_async(_async_sync_folders)

        self.settings_changed.emit()
        status_text = "включена" if checked else "приостановлена"
        InfoBar.info(
            title="Глобальная защита",
            content=f"Защита Проводника {status_text}.",
            parent=self,
            position=InfoBarPosition.TOP_RIGHT,
            duration=2000
        )

    def _on_recent_switch_toggled(self, checked: bool):
        self.config_manager.settings.clean_recent = checked
        self.config_manager.save()
        self.settings_changed.emit()

    def _on_autostart_switch_toggled(self, checked: bool):
        self.config_manager.settings.autostart = checked
        self.config_manager.save()
        success = set_autostart(checked)
        if success:
            msg = "Автозапуск включен" if checked else "Автозапуск отключен"
            InfoBar.success(
                title="Автозапуск",
                content=msg,
                parent=self,
                position=InfoBarPosition.TOP_RIGHT,
                duration=2000
            )
        else:
            InfoBar.error(
                title="Ошибка",
                content="Не удалось изменить запись в реестре Windows.",
                parent=self,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3000
            )

    def _on_tray_switch_toggled(self, checked: bool):
        self.config_manager.settings.show_tray_icon = checked
        self.config_manager.save()
        win = self.window()
        if hasattr(win, "tray_icon"):
            win.tray_icon.setVisible(checked)
        self.settings_changed.emit()

    def _apply_hotkey(self):
        new_hk = self.hotkeyInput.text().strip().lower()
        if not new_hk:
            return
        self.config_manager.settings.hotkey = new_hk
        self.config_manager.save()
        self.hotkey_updated.emit()
        InfoBar.success(
            title="Горячая клавиша обновлена",
            content=f"Хоткей вызова окна: {new_hk.upper()}",
            parent=self,
            position=InfoBarPosition.TOP_RIGHT,
            duration=2500
        )

    def _apply_protection_hotkey(self):
        new_hk = self.protHotkeyInput.text().strip().lower()
        if not new_hk:
            return
        self.config_manager.settings.protection_toggle_hotkey = new_hk
        self.config_manager.save()
        self.hotkey_updated.emit()
        InfoBar.success(
            title="Горячая клавиша обновлена",
            content=f"Хоткей отключения/включения защиты: {new_hk.upper()}",
            parent=self,
            position=InfoBarPosition.TOP_RIGHT,
            duration=2500
        )

    def _on_pin_switch_toggled(self, checked: bool):
        if checked and not self.config_manager.settings.pin_hash:
            # Need to set PIN first
            self._open_set_pin_dialog()
            if not self.config_manager.settings.pin_hash:
                self.pinSwitch.setChecked(False)
                return

        self.config_manager.settings.pin_enabled = checked
        self.config_manager.save()
        self.settings_changed.emit()

    def _open_set_pin_dialog(self):
        dialog = PinSetDialog(self.config_manager, None)
        if dialog.exec():
            pin = dialog.get_pin()
            self.config_manager.settings.pin_hash = ConfigManager.hash_pin(pin)
            self.config_manager.settings.pin_enabled = True
            self.pinSwitch.setChecked(True)
            self.config_manager.save()
            InfoBar.success(
                title="Мастер-пароль установлен",
                content="PIN-код успешно сохранен и активирован.",
                parent=self,
                position=InfoBarPosition.TOP_RIGHT,
                duration=2500
            )

    def _on_interval_combo_changed(self, index: int):
        presets = [50, 75, 100, 150, 200]
        if index < len(presets):
            val = presets[index]
            self.intervalInput.blockSignals(True)
            self.intervalInput.setText(str(val))
            self.intervalInput.blockSignals(False)
            self._save_interval(val)

    def _on_interval_text_changed(self, text: str):
        if text.isdigit():
            val = int(text)
            if 20 <= val <= 2000:
                self._sync_combo_with_val(val)
                self._save_interval(val)

    def _step_interval_down(self):
        cur = self._get_current_interval()
        new_val = max(20, cur - 10)
        self.intervalInput.setText(str(new_val))

    def _step_interval_up(self):
        cur = self._get_current_interval()
        new_val = min(2000, cur + 10)
        self.intervalInput.setText(str(new_val))

    def _get_current_interval(self) -> int:
        text = self.intervalInput.text()
        return int(text) if text.isdigit() else 75

    def _sync_combo_with_val(self, val: int):
        presets = {50: 0, 75: 1, 100: 2, 150: 3, 200: 4}
        idx = presets.get(val, 5)
        self.intervalCombo.blockSignals(True)
        self.intervalCombo.setCurrentIndex(idx)
        self.intervalCombo.blockSignals(False)

    def _save_interval(self, value: int):
        self.config_manager.settings.check_interval_ms = value
        self.config_manager.save()
        self.settings_changed.emit()
