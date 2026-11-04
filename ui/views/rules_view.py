import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog, QSizePolicy
)
from qfluentwidgets import (
    ScrollArea, CardWidget, LineEdit, PushButton, PrimaryPushButton,
    ToolButton, TransparentToolButton, ComboBox, SwitchButton, CheckBox,
    FluentIcon, SubtitleLabel, CaptionLabel, BodyLabel, StrongBodyLabel,
    InfoBar, InfoBarPosition, FlowLayout
)
from core.config_manager import ConfigManager, Rule
from core.decoy_generator import create_visual_clone_decoy, is_visual_clone, delete_decoy_folder


class RuleCard(CardWidget):
    """
    Card representing a single protection rule.
    """
    rule_changed = Signal(Rule)
    rule_deleted = Signal(str)

    def __init__(self, rule: Rule, parent=None):
        super().__init__(parent)
        self.rule = rule
        self.init_ui()

    def init_ui(self):
        self.setFixedHeight(88)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)

        # Left Icon
        self.iconLabel = QLabel(self)
        self._update_icon()
        layout.addWidget(self.iconLabel)

        # Middle Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        info_layout.setContentsMargins(0, 0, 0, 0)

        # Name and badge
        top_info_layout = QHBoxLayout()
        top_info_layout.setSpacing(8)
        self.nameLabel = StrongBodyLabel(self.rule.name or os.path.basename(self.rule.target_path) or "Правило", self)
        top_info_layout.addWidget(self.nameLabel)
        top_info_layout.addStretch()

        # Path details
        self.targetLabel = CaptionLabel(f"🎯 Перехват: {self.rule.target_path}", self)
        self.targetLabel.setStyleSheet("color: #a0a0a0;")

        self.actionLabel = CaptionLabel(self._get_action_desc(), self)
        self.actionLabel.setStyleSheet("color: #0099ff;" if self.rule.mode == "decoy" else "color: #ff5555;")

        info_layout.addLayout(top_info_layout)
        info_layout.addWidget(self.targetLabel)
        info_layout.addWidget(self.actionLabel)

        layout.addLayout(info_layout, 1)

        # Right Controls: Mode ComboBox, Hide Media Checkbox, Switch, Delete button
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(12)

        self.mediaCheck = CheckBox("Анти-мигание", self)
        self.mediaCheck.setToolTip("Делает файлы и подпапки системно скрытыми от Проводника — устраняет задержку и мигание при открытии")
        self.mediaCheck.setChecked(getattr(self.rule, "cloak_all", True))
        self.mediaCheck.stateChanged.connect(self._on_hide_media_toggled)
        controls_layout.addWidget(self.mediaCheck)

        self.modeCombo = ComboBox(self)
        self.modeCombo.addItems(["Подмена", "Блокировка"])
        self.modeCombo.setCurrentIndex(0 if self.rule.mode == "decoy" else 1)
        self.modeCombo.setFixedWidth(135)
        self.modeCombo.currentIndexChanged.connect(self._on_mode_changed)
        controls_layout.addWidget(self.modeCombo)

        # Switch Button for enable/disable
        self.switchBtn = SwitchButton(self)
        self.switchBtn.setChecked(self.rule.enabled)
        self.switchBtn.checkedChanged.connect(self._on_switch_changed)
        controls_layout.addWidget(self.switchBtn)

        # Delete Button
        self.deleteBtn = TransparentToolButton(FluentIcon.DELETE, self)
        self.deleteBtn.setToolTip("Удалить правило")
        self.deleteBtn.clicked.connect(self._on_delete_clicked)
        controls_layout.addWidget(self.deleteBtn)

        layout.addLayout(controls_layout)

    def _update_icon(self):
        icon = FluentIcon.SYNC if self.rule.mode == "decoy" else FluentIcon.CANCEL
        self.iconLabel.setPixmap(icon.icon().pixmap(32, 32))

    def _get_action_desc(self) -> str:
        hide_str = " • 🙈 Анти-мигание активно" if getattr(self.rule, "cloak_all", True) else ""
        if self.rule.mode == "decoy":
            decoy = self.rule.decoy_path or "Документы (по умолчанию)"
            return f"🔄 Подмена -> {decoy}{hide_str}"
        return f"⛔ Блокировка -> Окно ошибки Windows{hide_str}"

    def _on_hide_media_toggled(self, state):
        val = (state == Qt.Checked or state == 2 or bool(state))
        self.rule.hide_media = val
        self.rule.cloak_all = val
        self.actionLabel.setText(self._get_action_desc())
        self.rule_changed.emit(self.rule)

    def _on_mode_changed(self, index: int):
        self.rule.mode = "decoy" if index == 0 else "block"
        self._update_icon()
        self.actionLabel.setText(self._get_action_desc())
        self.actionLabel.setStyleSheet("color: #0099ff;" if self.rule.mode == "decoy" else "color: #ff5555;")
        self.rule_changed.emit(self.rule)

    def _on_switch_changed(self, checked: bool):
        self.rule.enabled = checked
        self.rule_changed.emit(self.rule)

    def _on_delete_clicked(self):
        self.rule_deleted.emit(self.rule.id)


class RulesView(QWidget):
    """
    Main tab view for viewing, adding and editing interception rules.
    """

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self._last_auto_decoy = False
        self.setObjectName("RulesView")
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # Header
        self.titleLabel = SubtitleLabel("Правила защиты Проводника", self)
        self.descLabel = CaptionLabel(
            "Прозрачный перехват при открытии через Проводник Windows 11. "
            "Файловая система и фоновые процессы не блокируются.",
            self
        )
        main_layout.addWidget(self.titleLabel)
        main_layout.addWidget(self.descLabel)

        # Panel: Add New Rule
        self.addCard = CardWidget(self)
        add_layout = QVBoxLayout(self.addCard)
        add_layout.setContentsMargins(16, 16, 16, 16)
        add_layout.setSpacing(12)

        add_title = StrongBodyLabel("➕ Добавить новое правило перехвата", self.addCard)
        add_layout.addWidget(add_title)

        # Row 1: Target path
        r1_layout = QHBoxLayout()
        r1_layout.setSpacing(8)
        self.targetInput = LineEdit(self.addCard)
        self.targetInput.setPlaceholderText("Защищаемая папка или путь (например: D:\\SecretFolder)")
        self.targetInput.setClearButtonEnabled(True)

        self.browseTargetBtn = PushButton(FluentIcon.FOLDER, "Обзор папки", self.addCard)
        self.browseTargetBtn.clicked.connect(self._browse_target)
        r1_layout.addWidget(self.targetInput, 1)
        r1_layout.addWidget(self.browseTargetBtn)
        add_layout.addLayout(r1_layout)

        # Row 2: Mode + Decoy path + Rule name
        r2_layout = QHBoxLayout()
        r2_layout.setSpacing(8)

        mode_label = BodyLabel("Режим:", self.addCard)
        self.modeCombo = ComboBox(self.addCard)
        self.modeCombo.addItems(["Подмена (Decoy)", "Блокировка (Block)"])
        self.modeCombo.setCurrentIndex(0)
        self.modeCombo.currentIndexChanged.connect(self._on_add_mode_changed)

        self.decoyInput = LineEdit(self.addCard)
        self.decoyInput.setPlaceholderText("Папка-приманка (например: C:\\Users\\User\\Documents)")
        self.decoyInput.setClearButtonEnabled(True)

        self.browseDecoyBtn = PushButton(FluentIcon.FOLDER, "Обзор", self.addCard)
        self.browseDecoyBtn.clicked.connect(self._browse_decoy)

        self.autoCloneBtn = PushButton(FluentIcon.COPY, "⚡ Клон-приманка", self.addCard)
        self.autoCloneBtn.setToolTip("Автоматически создать неотличимую папку-двойника (омоглиф) в этой же директории")
        self.autoCloneBtn.clicked.connect(self._create_auto_clone_decoy)

        r2_layout.addWidget(mode_label)
        r2_layout.addWidget(self.modeCombo)
        r2_layout.addWidget(self.decoyInput, 1)
        r2_layout.addWidget(self.browseDecoyBtn)
        r2_layout.addWidget(self.autoCloneBtn)
        add_layout.addLayout(r2_layout)

        # Row 2.5: Anti-flicker / Total Cloaking Checkbox
        self.hideMediaCheck = CheckBox("🔒 Режим анти-мигания (скрывать файлы в папке: System + Hidden)", self.addCard)
        self.hideMediaCheck.setChecked(True)
        self.hideMediaCheck.setToolTip("Делает файлы и подпапки невидимыми для Проводника, полностью устраняя мигание при переходе в приманку")
        add_layout.addWidget(self.hideMediaCheck)

        # Row 3: Name & Add Button
        r3_layout = QHBoxLayout()
        r3_layout.setSpacing(8)

        self.nameInput = LineEdit(self.addCard)
        self.nameInput.setPlaceholderText("Название правила (опционально)")
        self.nameInput.setClearButtonEnabled(True)

        self.addRuleBtn = PrimaryPushButton(FluentIcon.ADD, "Создать правило", self.addCard)
        self.addRuleBtn.clicked.connect(self._create_rule)

        r3_layout.addWidget(self.nameInput, 1)
        r3_layout.addWidget(self.addRuleBtn)
        add_layout.addLayout(r3_layout)

        main_layout.addWidget(self.addCard)

        # Rules List Header
        self.rulesHeader = StrongBodyLabel("Активные правила", self)
        main_layout.addWidget(self.rulesHeader)

        # Scroll Area for Rules
        self.scrollArea = ScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setStyleSheet("background: transparent; border: none;")

        self.scrollWidget = QWidget()
        self.scrollWidget.setStyleSheet("background: transparent;")
        self.rulesLayout = QVBoxLayout(self.scrollWidget)
        self.rulesLayout.setContentsMargins(0, 0, 0, 0)
        self.rulesLayout.setSpacing(10)
        self.rulesLayout.addStretch()

        self.scrollArea.setWidget(self.scrollWidget)
        main_layout.addWidget(self.scrollArea, 1)

        # Populate rules
        self.refresh_rules_list()

    def _browse_target(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите защищаемую папку")
        if folder:
            self.targetInput.setText(os.path.normpath(folder))
            if not self.nameInput.text():
                self.nameInput.setText(os.path.basename(os.path.normpath(folder)))

    def _browse_decoy(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку-приманку для подмены")
        if folder:
            self.decoyInput.setText(os.path.normpath(folder))
            self._last_auto_decoy = False

    def _on_add_mode_changed(self, index: int):
        is_decoy = (index == 0)
        self.decoyInput.setEnabled(is_decoy)
        self.browseDecoyBtn.setEnabled(is_decoy)
        self.autoCloneBtn.setEnabled(is_decoy)
        if not is_decoy:
            self.decoyInput.setPlaceholderText("Для блокировки папка-приманка не требуется")
        else:
            self.decoyInput.setPlaceholderText("Папка-приманка (например: C:\\Users\\User\\Documents)")

    def _create_auto_clone_decoy(self):
        target = self.targetInput.text().strip()
        if not target:
            InfoBar.warning(
                title="Укажите целевую папку",
                content="Сначала выберите или введите защищаемую папку выше, чтобы создать для неё папку-двойника.",
                parent=self,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3500
            )
            return

        # If previous decoy was generated and not yet added, delete it to avoid clutter
        prev_decoy = self.decoyInput.text().strip()
        if self._last_auto_decoy and prev_decoy and os.path.exists(prev_decoy):
            if is_visual_clone(target, prev_decoy):
                delete_decoy_folder(prev_decoy)

        success, decoy_path, msg = create_visual_clone_decoy(target, create_on_disk=True)
        if success:
            self._last_auto_decoy = True
            self.decoyInput.setText(decoy_path)
            title = "Папка-приманка создана!"
            content = f"Создан визуальный клон:\n{decoy_path}\n(Папка скрыта атрибутами System+Hidden и не видна в родительском каталоге)"

            InfoBar.success(
                title=title,
                content=content,
                parent=self,
                position=InfoBarPosition.TOP_RIGHT,
                duration=5000
            )
        else:
            InfoBar.error(
                title="Ошибка создания приманки",
                content=msg,
                parent=self,
                position=InfoBarPosition.TOP_RIGHT,
                duration=4000
            )

    def _create_rule(self):
        target = self.targetInput.text().strip()
        if not target:
            InfoBar.warning(
                title="Укажите путь",
                content="Необходимо указать целевую защищаемую папку или путь.",
                parent=self,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3000
            )
            return

        mode = "decoy" if self.modeCombo.currentIndex() == 0 else "block"
        decoy = self.decoyInput.text().strip()
        auto_decoy = self._last_auto_decoy
        if mode == "decoy" and not decoy:
            from core.drive_cloaker import is_drive_root, get_drive_letter, mount_virtual_decoy_drive
            if is_drive_root(target):
                ok, decoy_drive, _ = mount_virtual_decoy_drive(get_drive_letter(target))
                if ok:
                    decoy = decoy_drive
                    auto_decoy = True
            if not decoy:
                # Default decoy: User Documents
                decoy = os.path.join(os.path.expanduser("~"), "Documents")

        name = self.nameInput.text().strip() or os.path.basename(os.path.normpath(target)) or "Защита"
        cloak_all = self.hideMediaCheck.isChecked()
        hide_media = cloak_all

        new_rule = Rule(
            name=name,
            target_path=target,
            mode=mode,
            decoy_path=decoy,
            enabled=True,
            notify_on_block=True,
            hide_media=hide_media,
            auto_decoy=auto_decoy,
            cloak_all=cloak_all
        )

        self.config_manager.add_rule(new_rule)
        self._last_auto_decoy = False

        # Cloak decoy folder if it exists
        if mode == "decoy" and decoy and os.path.exists(decoy):
            try:
                from core.file_cloaker import cloak_directory
                cloak_directory(decoy)
            except Exception:
                pass

        # Clear inputs
        self.targetInput.clear()
        self.decoyInput.clear()
        self.nameInput.clear()

        self.refresh_rules_list()

        msg = f"Правило для «{name}» успешно активировано."
        if cloak_all:
            msg += " Включен режим анти-мигания (файлы системно скрыты)."

        InfoBar.success(
            title="Правило сохранено",
            content=msg,
            parent=self,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3000
        )

    def refresh_rules_list(self):
        # Clear existing rule cards
        while self.rulesLayout.count() > 1:
            item = self.rulesLayout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for rule in self.config_manager.rules:
            card = RuleCard(rule, self.scrollWidget)
            card.rule_changed.connect(self._on_rule_modified)
            card.rule_deleted.connect(self._on_rule_deleted)
            self.rulesLayout.insertWidget(self.rulesLayout.count() - 1, card)

        count = len(self.config_manager.rules)
        self.rulesHeader.setText(f"Активные правила ({count})")

    def _on_rule_modified(self, rule: Rule):
        self.config_manager.update_rule(rule)

    def _on_rule_deleted(self, rule_id: str):
        target_rule = next((r for r in self.config_manager.rules if r.id == rule_id), None)
        decoy_removed = False
        if target_rule and target_rule.mode == "decoy" and target_rule.decoy_path:
            is_auto = getattr(target_rule, "auto_decoy", False) or is_visual_clone(
                target_rule.target_path, target_rule.decoy_path
            )
            if is_auto and os.path.exists(target_rule.decoy_path):
                decoy_removed = True

        self.config_manager.remove_rule(rule_id)
        self.refresh_rules_list()

        msg = "Правило защиты удалено из конфигурации."
        if decoy_removed:
            msg += " Автоматически созданная папка-приманка удалена с диска."

        InfoBar.info(
            title="Правило удалено",
            content=msg,
            parent=self,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3500
        )
