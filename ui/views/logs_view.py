import csv
from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QHeaderView, QFileDialog
)
from qfluentwidgets import (
    TableWidget, SubtitleLabel, CaptionLabel, TransparentPushButton,
    FluentIcon, InfoBar, InfoBarPosition
)


class LogsView(QWidget):
    """
    Tab view displaying real-time log of folder interception events.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LogsView")
        self.log_entries = []
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # Header with actions
        header_layout = QHBoxLayout()
        header_text_layout = QVBoxLayout()
        header_text_layout.setSpacing(4)

        self.titleLabel = SubtitleLabel("Журнал перехватов", self)
        self.descLabel = CaptionLabel("История попыток доступа к защищенным папкам через Проводник Windows", self)
        header_text_layout.addWidget(self.titleLabel)
        header_text_layout.addWidget(self.descLabel)
        header_layout.addLayout(header_text_layout)
        header_layout.addStretch()

        self.exportBtn = TransparentPushButton(FluentIcon.FOLDER, "Экспорт в CSV", self)
        self.exportBtn.clicked.connect(self._export_csv)
        header_layout.addWidget(self.exportBtn)

        self.clearBtn = TransparentPushButton(FluentIcon.DELETE, "Очистить журнал", self)
        self.clearBtn.clicked.connect(self._clear_logs)
        header_layout.addWidget(self.clearBtn)

        main_layout.addLayout(header_layout)

        # Log Table
        self.table = TableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Время", "Правило", "Защищенный путь", "Действие", "Назначение / Результат"
        ])

        # Configure columns
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)

        self.table.verticalHeader().hide()
        self.table.setBorderVisible(True)
        self.table.setBorderRadius(8)
        self.table.setWordWrap(False)

        main_layout.addWidget(self.table, 1)

    def add_log_entry(self, data: dict):
        """
        Receives event dictionary from ExplorerInterceptor and prepends it to the table.
        """
        self.log_entries.insert(0, data)

        self.table.insertRow(0)
        self.table.setItem(0, 0, self._create_item(data.get("timestamp", "")))
        self.table.setItem(0, 1, self._create_item(data.get("rule_name", "")))
        self.table.setItem(0, 2, self._create_item(data.get("target_path", "")))
        self.table.setItem(0, 3, self._create_item(data.get("mode", "")))
        self.table.setItem(0, 4, self._create_item(data.get("decoy_path", "")))

        # Limit to 500 rows to keep memory small
        if self.table.rowCount() > 500:
            self.table.removeRow(500)
            self.log_entries = self.log_entries[:500]

    def _create_item(self, text: str):
        from PySide6.QtWidgets import QTableWidgetItem
        item = QTableWidgetItem(str(text))
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        return item

    def _clear_logs(self):
        self.table.setRowCount(0)
        self.log_entries.clear()
        InfoBar.info(
            title="Журнал очищен",
            content="Все записи журнала перехватов были удалены.",
            parent=self,
            position=InfoBarPosition.TOP_RIGHT,
            duration=2000
        )

    def _export_csv(self):
        if not self.log_entries:
            InfoBar.warning(
                title="Журнал пуст",
                content="Нет записей для экспорта.",
                parent=self,
                position=InfoBarPosition.TOP_RIGHT,
                duration=2000
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить отчет", "stealthguard_log.csv", "CSV Files (*.csv)"
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Rule Name", "Target Path", "Mode", "Destination"])
                for e in self.log_entries:
                    writer.writerow([
                        e.get("timestamp", ""),
                        e.get("rule_name", ""),
                        e.get("target_path", ""),
                        e.get("mode", ""),
                        e.get("decoy_path", "")
                    ])

            InfoBar.success(
                title="Экспорт завершен",
                content=f"Журнал успешно экспортирован в {file_path}",
                parent=self,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3000
            )
        except Exception as e:
            InfoBar.error(
                title="Ошибка экспорта",
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3000
            )
