from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QDialog, QMessageBox, QSplitter
)
from PyQt5.QtCore import Qt, pyqtSignal
from admin_products import get_sqlite_connection, get_table_columns, ensure_suppliers_schema


class SupplierDialog(QDialog):
    """Діалогове вікно додавання / редагування постачальника"""
    def __init__(self, supplier_data: dict = None, parent=None):
        super().__init__(parent)
        self.supplier_data = supplier_data
        self.setWindowTitle("Редагування постачальника" if supplier_data else "Додавання постачальника")
        self.resize(430, 260)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(8)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Наприклад: ТОВ «ТехноПостач»")

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("+380 (67) 000-00-00")

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("supplier@company.ua")

        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("м. Київ, вул. Промислова, 10")

        form.addRow("Назва постачальника *:", self.name_input)
        form.addRow("Телефон *:", self.phone_input)
        form.addRow("Електронна пошта:", self.email_input)
        form.addRow("Адреса:", self.address_input)

        layout.addLayout(form)
        layout.addStretch()

        btns_row = QHBoxLayout()
        cancel_btn = QPushButton("Скасувати")
        cancel_btn.clicked.connect(self.reject)
        btns_row.addWidget(cancel_btn)

        btns_row.addStretch()

        save_btn = QPushButton("Зберегти")
        save_btn.clicked.connect(self.validate_and_accept)
        btns_row.addWidget(save_btn)

        layout.addLayout(btns_row)

        if self.supplier_data:
            self.name_input.setText(self.supplier_data.get("name", ""))
            self.phone_input.setText(self.supplier_data.get("phone", ""))
            self.email_input.setText(self.supplier_data.get("email", ""))
            self.address_input.setText(self.supplier_data.get("address", ""))

    def validate_and_accept(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Помилка", "Введіть назву постачальника.")
            self.name_input.setFocus()
            return
        if not self.phone_input.text().strip():
            QMessageBox.warning(self, "Помилка", "Введіть контактний телефон постачальника.")
            self.phone_input.setFocus()
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "supplier_id": self.supplier_data.get("supplier_id") if self.supplier_data else None,
            "name": self.name_input.text().strip(),
            "phone": self.phone_input.text().strip(),
            "email": self.email_input.text().strip(),
            "address": self.address_input.text().strip(),
        }


class SuppliersAdminTab(QWidget):
    """
    Вкладка постачальників:
    - Список постачальників, пошук за назвою
    - Додавання, редагування та видалення постачальників
    - Перегляд товарів, пов'язаних з конкретним постачальником
    """
    suppliers_changed = pyqtSignal()

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Пошук постачальника за назвою:"))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Введіть назву постачальника...")
        self.search_input.setMaximumWidth(320)
        self.search_input.textChanged.connect(self.load_suppliers)
        top_bar.addWidget(self.search_input)

        top_bar.addStretch()

        self.add_btn = QPushButton("Додати постачальника")
        self.add_btn.clicked.connect(self.add_supplier)
        top_bar.addWidget(self.add_btn)

        self.edit_btn = QPushButton("Редагувати")
        self.edit_btn.clicked.connect(self.edit_supplier)
        top_bar.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Видалити")
        self.delete_btn.clicked.connect(self.delete_supplier)
        top_bar.addWidget(self.delete_btn)

        layout.addLayout(top_bar)

        splitter = QSplitter(Qt.Vertical)

        suppliers_box = QGroupBox("Список постачальників")
        sup_layout = QVBoxLayout(suppliers_box)

        self.suppliers_table = QTableWidget()
        self.suppliers_table.setColumnCount(6)
        self.suppliers_table.setHorizontalHeaderLabels([
            "ID", "Назва постачальника", "Телефон", "Електронна пошта", "Адреса", "Товарів"
        ])
        self.suppliers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.suppliers_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.suppliers_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.suppliers_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.suppliers_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.suppliers_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.suppliers_table.verticalHeader().setVisible(False)
        self.suppliers_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.suppliers_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.suppliers_table.itemSelectionChanged.connect(self.load_selected_supplier_products)
        self.suppliers_table.cellDoubleClicked.connect(lambda _r, _c: self.edit_supplier())

        sup_layout.addWidget(self.suppliers_table)
        splitter.addWidget(suppliers_box)

        self.linked_products_box = QGroupBox("Товари обраного постачальника")
        linked_layout = QVBoxLayout(self.linked_products_box)

        self.linked_products_table = QTableWidget()
        self.linked_products_table.setColumnCount(6)
        self.linked_products_table.setHorizontalHeaderLabels([
            "ID", "Назва товару", "Бренд", "Категорія", "Ціна (грн)", "На складі"
        ])
        self.linked_products_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.linked_products_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.linked_products_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.linked_products_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.linked_products_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.linked_products_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.linked_products_table.verticalHeader().setVisible(False)
        self.linked_products_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.linked_products_table.setEditTriggers(QTableWidget.NoEditTriggers)

        linked_layout.addWidget(self.linked_products_table)
        splitter.addWidget(self.linked_products_box)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)

        self.load_suppliers()

    def load_suppliers(self):
        query = self.search_input.text().strip().lower()
        conn = get_sqlite_connection(self.db)
        ensure_suppliers_schema(conn)
        cursor = conn.cursor()

        prod_cols = get_table_columns(conn, "products")
        has_supplier_col = "supplier_id" in prod_cols

        if has_supplier_col:
            sql = """
                SELECT
                    s.supplier_id,
                    s.name,
                    COALESCE(s.phone, ''),
                    COALESCE(s.email, ''),
                    COALESCE(s.address, ''),
                    COUNT(p.product_id) AS products_count
                FROM suppliers s
                LEFT JOIN products p ON s.supplier_id = p.supplier_id
            """
        else:
            sql = """
                SELECT
                    s.supplier_id,
                    s.name,
                    COALESCE(s.phone, ''),
                    COALESCE(s.email, ''),
                    COALESCE(s.address, ''),
                    0 AS products_count
                FROM suppliers s
            """

        params = []
        if query:
            sql += " WHERE LOWER(s.name) LIKE ?"
            params.append(f"%{query}%")

        sql += " GROUP BY s.supplier_id ORDER BY s.name ASC"
        cursor.execute(sql, params)
        rows = cursor.fetchall()

        self.suppliers_table.setRowCount(len(rows))
        for idx, r in enumerate(rows):
            sid, name, phone, email, address, p_count = r
            id_item = QTableWidgetItem(str(sid))
            id_item.setData(Qt.UserRole, sid)

            self.suppliers_table.setItem(idx, 0, id_item)
            self.suppliers_table.setItem(idx, 1, QTableWidgetItem(str(name)))
            self.suppliers_table.setItem(idx, 2, QTableWidgetItem(str(phone)))
            self.suppliers_table.setItem(idx, 3, QTableWidgetItem(str(email)))
            self.suppliers_table.setItem(idx, 4, QTableWidgetItem(str(address)))
            self.suppliers_table.setItem(idx, 5, QTableWidgetItem(f"{int(p_count)} шт."))

        if rows:
            self.suppliers_table.selectRow(0)
        else:
            self.linked_products_box.setTitle("Товари обраного постачальника")
            self.linked_products_table.setRowCount(0)

    def _get_selected_supplier(self):
        row = self.suppliers_table.currentRow()
        if row < 0:
            return None
        id_item = self.suppliers_table.item(row, 0)
        if not id_item:
            return None
        return {
            "supplier_id": id_item.data(Qt.UserRole),
            "name": self.suppliers_table.item(row, 1).text(),
            "phone": self.suppliers_table.item(row, 2).text(),
            "email": self.suppliers_table.item(row, 3).text(),
            "address": self.suppliers_table.item(row, 4).text(),
        }

    def load_selected_supplier_products(self):
        sup = self._get_selected_supplier()
        if not sup:
            self.linked_products_box.setTitle("Товари обраного постачальника")
            self.linked_products_table.setRowCount(0)
            return

        sid = sup["supplier_id"]
        sname = sup["name"]
        conn = get_sqlite_connection(self.db)
        prod_cols = get_table_columns(conn, "products")
        if "supplier_id" not in prod_cols:
            self.linked_products_box.setTitle(f"Товари постачальника «{sname}» (0 шт.)")
            self.linked_products_table.setRowCount(0)
            return

        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                p.product_id,
                p.title,
                COALESCE(p.brand, ''),
                COALESCE(c.name, 'Без категорії'),
                p.price,
                p.stock_quantity
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.category_id
            WHERE p.supplier_id = ?
            ORDER BY p.title ASC
            """,
            (sid,)
        )
        products = cursor.fetchall()

        self.linked_products_box.setTitle(f"Товари постачальника «{sname}» ({len(products)} шт.)")
        self.linked_products_table.setRowCount(len(products))
        for idx, p in enumerate(products):
            pid, title, brand, cat_name, price, stock = p
            self.linked_products_table.setItem(idx, 0, QTableWidgetItem(str(pid)))
            self.linked_products_table.setItem(idx, 1, QTableWidgetItem(str(title)))
            self.linked_products_table.setItem(idx, 2, QTableWidgetItem(str(brand)))
            self.linked_products_table.setItem(idx, 3, QTableWidgetItem(str(cat_name)))
            self.linked_products_table.setItem(idx, 4, QTableWidgetItem(f"{float(price):.2f}"))
            self.linked_products_table.setItem(idx, 5, QTableWidgetItem(f"{int(stock)} шт."))

    def add_supplier(self):
        dialog = SupplierDialog(parent=self)
        if dialog.exec_() != QDialog.Accepted:
            return

        data = dialog.get_data()
        conn = get_sqlite_connection(self.db)
        ensure_suppliers_schema(conn)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO suppliers (name, phone, email, address) VALUES (?, ?, ?, ?)",
            (data["name"], data["phone"], data["email"], data["address"])
        )
        conn.commit()

        self.load_suppliers()
        self.suppliers_changed.emit()
        QMessageBox.information(self, "Успіх", "Постачальника успішно додано!")

    def edit_supplier(self):
        sup = self._get_selected_supplier()
        if not sup:
            QMessageBox.warning(self, "Увага", "Оберіть постачальника у таблиці.")
            return

        dialog = SupplierDialog(supplier_data=sup, parent=self)
        if dialog.exec_() != QDialog.Accepted:
            return

        data = dialog.get_data()
        conn = get_sqlite_connection(self.db)
        ensure_suppliers_schema(conn)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE suppliers
            SET name = ?, phone = ?, email = ?, address = ?
            WHERE supplier_id = ?
            """,
            (data["name"], data["phone"], data["email"], data["address"], data["supplier_id"])
        )
        conn.commit()

        self.load_suppliers()
        self.suppliers_changed.emit()
        QMessageBox.information(self, "Успіх", "Контактні дані постачальника оновлено!")

    def delete_supplier(self):
        sup = self._get_selected_supplier()
        if not sup:
            QMessageBox.warning(self, "Увага", "Оберіть постачальника у таблиці.")
            return

        sid = sup["supplier_id"]
        conn = get_sqlite_connection(self.db)
        ensure_suppliers_schema(conn)
        cursor = conn.cursor()
        prod_cols = get_table_columns(conn, "products")

        linked_count = 0
        if "supplier_id" in prod_cols:
            cursor.execute("SELECT COUNT(*) FROM products WHERE supplier_id = ?", (sid,))
            linked_count = cursor.fetchone()[0]

        msg = f"Ви дійсно бажаєте видалити постачальника «{sup['name']}»?"
        if linked_count > 0:
            msg += (
                f"\n\nДо цього постачальника прив’язано товарів: {linked_count} шт."
                "\nПісля видалення у цих товарів буде знято прив’язку до постачальника."
            )

        confirm = QMessageBox.question(self, "Підтвердження видалення", msg, QMessageBox.Yes | QMessageBox.No)
        if confirm != QMessageBox.Yes:
            return

        if linked_count > 0:
            cursor.execute("UPDATE products SET supplier_id = NULL WHERE supplier_id = ?", (sid,))
        cursor.execute("DELETE FROM suppliers WHERE supplier_id = ?", (sid,))
        conn.commit()

        self.load_suppliers()
        self.suppliers_changed.emit()
        QMessageBox.information(self, "Успіх", "Постачальника видалено.")
        