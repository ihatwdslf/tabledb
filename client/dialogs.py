from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout,
)

from client.api_client import ApiClient, ApiError


def show_error(parent, error):
    QMessageBox.warning(parent, "Помилка", str(error))


def fill_table_widget(widget: QTableWidget, table: dict):
    """Показує таблицю, отриману від сервера, у віджеті-сітці."""
    columns = table["columns"]
    rows = table["rows"]
    widget.clear()
    widget.setColumnCount(len(columns))
    widget.setRowCount(len(rows))
    widget.setHorizontalHeaderLabels([f"{c['name']}\n({c['type']})" for c in columns])
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            widget.setItem(r, c, QTableWidgetItem(str(value)))
    widget.resizeColumnsToContents()


class CreateTableDialog(QDialog):
    """Вікно створення таблиці: назва + список колонок з типами."""

    def __init__(self, types: list[dict], submit, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Створити таблицю")
        self.types = types
        self.submit = submit  # функція, яка надсилає таблицю на сервер

        self.name_edit = QLineEdit()
        self.columns_widget = QTableWidget(0, 2)
        self.columns_widget.setHorizontalHeaderLabels(["Назва колонки", "Тип"])
        self.columns_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        add_button = QPushButton("Додати колонку")
        add_button.clicked.connect(self.add_column)
        remove_button = QPushButton("Видалити колонку")
        remove_button.clicked.connect(self.remove_column)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        form = QFormLayout()
        form.addRow("Назва таблиці:", self.name_edit)
        column_buttons = QHBoxLayout()
        column_buttons.addWidget(add_button)
        column_buttons.addWidget(remove_button)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(QLabel("Колонки:"))
        layout.addWidget(self.columns_widget)
        layout.addLayout(column_buttons)
        layout.addWidget(buttons)
        self.resize(450, 350)

        self.add_column()

    def add_column(self):
        row = self.columns_widget.rowCount()
        self.columns_widget.insertRow(row)
        self.columns_widget.setCellWidget(row, 0, QLineEdit())
        combo = QComboBox()
        for t in self.types:
            combo.addItem(t["name"])
            combo.setItemData(combo.count() - 1, t["hint"], Qt.ToolTipRole)  # підказка при наведенні
        self.columns_widget.setCellWidget(row, 1, combo)

    def remove_column(self):
        row = self.columns_widget.currentRow()
        if row < 0:
            row = self.columns_widget.rowCount() - 1  # якщо нічого не виділено – остання
        if row >= 0:
            self.columns_widget.removeRow(row)

    def columns(self) -> list[dict]:
        result = []
        for row in range(self.columns_widget.rowCount()):
            name = self.columns_widget.cellWidget(row, 0).text()
            field_type = self.columns_widget.cellWidget(row, 1).currentText()
            result.append({"name": name, "type": field_type})
        return result

    def accept(self):
        try:
            self.submit(self.name_edit.text(), self.columns())
        except ApiError as error:
            show_error(self, error)
            return  # вікно не закривається, можна виправити дані
        super().accept()


class AddRowDialog(QDialog):
    """Вікно додавання рядка: по одному полю на кожну колонку."""

    def __init__(self, columns: list[dict], hints: dict[str, str], submit, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Додати рядок")
        self.submit = submit

        form = QFormLayout()
        self.edits = []
        for column in columns:
            edit = QLineEdit()
            edit.setPlaceholderText(hints.get(column["type"], ""))
            form.addRow(f"{column['name']} ({column['type']}):", edit)
            self.edits.append(edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.resize(450, 0)

    def accept(self):
        try:
            self.submit([edit.text() for edit in self.edits])
        except ApiError as error:
            show_error(self, error)
            return
        super().accept()


class JoinDialog(QDialog):
    """JoinDialogUI з VOPC-діаграми: вибір таблиць і спільного поля, показ результату."""

    def __init__(self, api: ApiClient, db: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Сполучення таблиць")
        self.api = api
        self.db = db
        self.tables = {name: api.get_table(db, name) for name in api.list_tables(db)}

        self.table1_combo = QComboBox()
        self.table2_combo = QComboBox()
        self.table1_combo.addItems(self.tables)
        self.table2_combo.addItems(self.tables)
        if len(self.tables) > 1:
            self.table2_combo.setCurrentIndex(1)
        self.field_combo = QComboBox()
        self.table1_combo.currentTextChanged.connect(self.select_common_field)
        self.table2_combo.currentTextChanged.connect(self.select_common_field)

        self.join_button = QPushButton("Виконати сполучення")
        self.join_button.clicked.connect(self.run_join)

        self.result_widget = QTableWidget()
        self.result_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.save_edit = QLineEdit()
        self.save_edit.setPlaceholderText("назва нової таблиці")
        save_button = QPushButton("Зберегти як нову таблицю")
        save_button.clicked.connect(self.save_result)

        form = QFormLayout()
        form.addRow("Таблиця 1:", self.table1_combo)
        form.addRow("Таблиця 2:", self.table2_combo)
        form.addRow("Спільне поле:", self.field_combo)
        save_row = QHBoxLayout()
        save_row.addWidget(self.save_edit)
        save_row.addWidget(save_button)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.join_button)
        layout.addWidget(QLabel("Результат:"))
        layout.addWidget(self.result_widget)
        layout.addLayout(save_row)
        self.resize(700, 500)

        self.select_common_field()

    def select_source_tables(self) -> tuple[str, str]:
        return self.table1_combo.currentText(), self.table2_combo.currentText()

    def select_common_field(self):
        """Показує у списку лише ті поля, які є в обох обраних таблицях."""
        t1, t2 = self.select_source_tables()
        self.field_combo.clear()
        if t1 in self.tables and t2 in self.tables:
            names2 = {c["name"] for c in self.tables[t2]["columns"]}
            common = [c["name"] for c in self.tables[t1]["columns"] if c["name"] in names2]
            self.field_combo.addItems(common)
        self.join_button.setEnabled(self.field_combo.count() > 0)

    def run_join(self):
        t1, t2 = self.select_source_tables()
        try:
            result = self.api.join(self.db, t1, t2, self.field_combo.currentText())
        except ApiError as error:
            show_error(self, error)
            return
        self.show_result_table(result)

    def show_result_table(self, table: dict):
        fill_table_widget(self.result_widget, table)

    def save_result(self):
        t1, t2 = self.select_source_tables()
        try:
            self.api.join(self.db, t1, t2, self.field_combo.currentText(), save_as=self.save_edit.text())
        except ApiError as error:
            show_error(self, error)
            return
        QMessageBox.information(self, "Готово", f"Результат збережено як таблицю '{self.save_edit.text()}'")