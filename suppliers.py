from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFormLayout
)
from classes import Supplier


class SupplierEditDialog(QDialog):
    """Діалогове вікно додавання/редагування постачальника"""
    def __init__(self, supplier: Supplier = None, parent=None):
        super().__init__(parent)
        self.supplier = supplier
        self.setWindowTitle("Редагування постачальника" if supplier else "Додати постачальника")
        self.resize(350, 220)

        layout = QFormLayout(self)

        self.name_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.email_input = QLineEdit()
        self.address_input = QLineEdit()

        layout.addRow("Назва / Компанія:", self.name_input)
        layout.addRow("Телефон:", self.phone_input)
        layout.addRow("Email:", self.email_input)
        layout.addRow("Адреса:", self.address_input)

        if self.supplier:
            self.name_input.setText(self.supplier.name)
            self.phone_input.setText(self.supplier.phone)
            self.email_input.setText(self.supplier.email)
            self.address_input.setText(self.supplier.address)

        self.save_btn = QPushButton("Зберегти")
        self.save_btn.clicked.connect(self.save)
        layout.addRow(self.save_btn)

    def save(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Помилка", "Введіть назву постачальника.")
            return
        self.accept()

    def get_supplier_data(self) -> Supplier:
        s_id = self.supplier.supplier_id if self.supplier else None
        return Supplier(
            supplier_id=s_id,
            name=self.name_input.text().strip(),
            phone=self.phone_input.text().strip(),
            email=self.email_input.text().strip(),
            address=self.address_input.text().strip()
        )


class SuppliersWindow(QDialog):
    """Вікно керування постачальниками (для Адміністратора)"""
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.setWindowTitle("Керування постачальниками")
        self.resize(700, 450)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Пошук та кнопки додавання
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Пошук:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Назва або телефон...")
        self.search_input.textChanged.connect(self.load_suppliers)
        top_layout.addWidget(self.search_input)

        self.add_btn = QPushButton("➕ Додати постачальника")
        self.add_btn.clicked.connect(self.add_supplier)
        top_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("✏️ Редагувати")
        self.edit_btn.clicked.connect(self.edit_supplier)
        top_layout.addWidget(self.edit_btn)

        layout.addLayout(top_layout)

        # Таблиця
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Назва", "Телефон", "Email", "Адреса"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        self.load_suppliers()

    def load_suppliers(self):
        query = self.search_input.text().strip()
        suppliers = self.db.search_suppliers(query)

        self.table.setRowCount(len(suppliers))
        for row, s in enumerate(suppliers):
            self.table.setItem(row, 0, QTableWidgetItem(str(s.supplier_id)))
            self.table.setItem(row, 1, QTableWidgetItem(s.name))
            self.table.setItem(row, 2, QTableWidgetItem(s.phone))
            self.table.setItem(row, 3, QTableWidgetItem(s.email))
            self.table.setItem(row, 4, QTableWidgetItem(s.address))

    def _get_selected_supplier(self) -> Supplier:
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Увага", "Оберіть постачальника з таблиці.")
            return None
        
        s_id = int(self.table.item(selected, 0).text())
        name = self.table.item(selected, 1).text()
        phone = self.table.item(selected, 2).text()
        email = self.table.item(selected, 3).text()
        address = self.table.item(selected, 4).text()
        return Supplier(name=name, phone=phone, email=email, address=address, supplier_id=s_id)

    def add_supplier(self):
        dialog = SupplierEditDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            new_s = dialog.get_supplier_data()
            self.db.add_supplier(new_s)
            QMessageBox.information(self, "Успіх", "Постачальника додано!")
            self.load_suppliers()

    def edit_supplier(self):
        supplier = self._get_selected_supplier()
        if not supplier:
            return

        dialog = SupplierEditDialog(supplier=supplier, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            updated_s = dialog.get_supplier_data()
            self.db.update_supplier(updated_s)
            QMessageBox.information(self, "Успіх", "Дані постачальника оновлено!")
            self.load_suppliers()
            