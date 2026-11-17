import os
import sqlite3
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from catalog_tab import ProductDialog


def get_sqlite_connection(db_manager):
    """Повертає активне з'єднання SQLite із наявного DatabaseManager"""
    if hasattr(db_manager, "__dict__"):
        for attr_val in vars(db_manager).values():
            if isinstance(attr_val, sqlite3.Connection):
                return attr_val

    for method_name in ("get_connection", "_get_connection", "connect", "_connect", "create_connection"):
        method = getattr(db_manager, method_name, None)
        if callable(method):
            conn = method()
            if isinstance(conn, sqlite3.Connection):
                return conn

    db_file = None
    for attr_name in ("db_name", "db_path", "database", "db_file", "path", "filename"):
        val = getattr(db_manager, attr_name, None)
        if isinstance(val, str) and val.strip():
            db_file = val.strip()
            break

    if not db_file and hasattr(db_manager, "__dict__"):
        for attr_val in vars(db_manager).values():
            if isinstance(attr_val, str) and attr_val.strip().endswith((".db", ".sqlite", ".sqlite3")):
                db_file = attr_val.strip()
                break

    if not db_file:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        for search_dir in (os.getcwd(), base_dir):
            if os.path.isdir(search_dir):
                for fname in os.listdir(search_dir):
                    full_path = os.path.join(search_dir, fname)
                    if fname.endswith((".db", ".sqlite", ".sqlite3")) and os.path.getsize(full_path) > 0:
                        db_file = full_path
                        break
            if db_file:
                break

    if not db_file:
        db_file = "shop.db"

    return sqlite3.connect(db_file)


def get_table_columns(conn, table_name: str) -> set:
    """Повертає множину назв стовпців таблиці SQLite"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}


def ensure_suppliers_schema(conn):
    """Перевіряє наявність таблиці suppliers та потрібних контактних стовпців"""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            address TEXT
        )
    """)
    cols = get_table_columns(conn, "suppliers")
    for col_name in ("phone", "email", "address"):
        if col_name not in cols:
            cursor.execute(f"ALTER TABLE suppliers ADD COLUMN {col_name} TEXT")
    if "contact_info" in cols:
        cursor.execute(
            "UPDATE suppliers SET phone = contact_info WHERE (phone IS NULL OR phone = '') AND contact_info IS NOT NULL"
        )
    conn.commit()


class ProductsAdminTab(QWidget):
    """Вкладка керування товарами (пошук за назвою/брендом, додавання, редагування, видалення)"""
    data_changed = pyqtSignal()

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # Панель пошуку та кнопок дій
        toolbar = QFrame()
        toolbar.setObjectName("toolbarCard")
        top_bar = QHBoxLayout(toolbar)
        top_bar.setContentsMargins(12, 10, 12, 10)
        top_bar.setSpacing(10)

        search_lbl = QLabel("Пошук товару:")
        search_lbl.setProperty("role", "sectionTitle")
        top_bar.addWidget(search_lbl)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchInput")
        self.search_input.setPlaceholderText("Введіть назву товару або бренд...")
        self.search_input.setMinimumWidth(300)
        self.search_input.setMaximumWidth(400)
        self.search_input.textChanged.connect(self.load_products)
        top_bar.addWidget(self.search_input)

        top_bar.addStretch()

        self.add_btn = QPushButton("Додати товар")
        self.add_btn.setProperty("variant", "primary")
        self.add_btn.clicked.connect(self.add_product)
        top_bar.addWidget(self.add_btn)

        self.edit_btn = QPushButton("Редагувати товар")
        self.edit_btn.setProperty("variant", "secondary")
        self.edit_btn.clicked.connect(self.edit_product)
        top_bar.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Видалити")
        self.delete_btn.setProperty("variant", "danger")
        self.delete_btn.clicked.connect(self.delete_product)
        top_bar.addWidget(self.delete_btn)

        layout.addWidget(toolbar)

        # Таблиця товарів
        self.products_table = QTableWidget()
        self.products_table.setAlternatingRowColors(True)
        self.products_table.setColumnCount(8)
        self.products_table.setHorizontalHeaderLabels([
            "ID", "Назва товару", "Бренд", "Категорія", "Постачальник",
            "Ціна (грн)", "На складі", "Опис"
        ])
        self.products_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.products_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.products_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.products_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.products_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.products_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.products_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.products_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Stretch)
        self.products_table.verticalHeader().setVisible(False)
        self.products_table.verticalHeader().setDefaultSectionSize(38)
        self.products_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.products_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.products_table.cellDoubleClicked.connect(lambda _r, _c: self.edit_product())

        layout.addWidget(self.products_table)
        self.load_products()

    def load_products(self):
        query = self.search_input.text().strip().lower()
        conn = get_sqlite_connection(self.db)
        ensure_suppliers_schema(conn)
        cursor = conn.cursor()

        prod_cols = get_table_columns(conn, "products")
        has_supplier_col = "supplier_id" in prod_cols

        if has_supplier_col:
            sql = """
                SELECT
                    p.product_id,
                    p.title,
                    p.brand,
                    COALESCE(c.name, 'Без категорії') AS category_name,
                    COALESCE(s.name, 'Не вказано') AS supplier_name,
                    p.price,
                    p.stock_quantity,
                    COALESCE(p.description, '')
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.category_id
                LEFT JOIN suppliers s ON p.supplier_id = s.supplier_id
                ORDER BY p.product_id DESC
            """
        else:
            sql = """
                SELECT
                    p.product_id,
                    p.title,
                    p.brand,
                    COALESCE(c.name, 'Без категорії') AS category_name,
                    'Не вказано' AS supplier_name,
                    p.price,
                    p.stock_quantity,
                    COALESCE(p.description, '')
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.category_id
                ORDER BY p.product_id DESC
            """

        cursor.execute(sql)
        all_rows = cursor.fetchall()

        if query:
            rows = [
                r for r in all_rows
                if query in str(r[1] or "").lower() or query in str(r[2] or "").lower()
            ]
        else:
            rows = all_rows

        self.products_table.setRowCount(len(rows))
        for r_idx, row in enumerate(rows):
            pid, title, brand, cat_name, sup_name, price, stock, desc = row
            id_item = QTableWidgetItem(str(pid))
            id_item.setData(Qt.UserRole, pid)

            self.products_table.setItem(r_idx, 0, id_item)
            self.products_table.setItem(r_idx, 1, QTableWidgetItem(str(title)))
            self.products_table.setItem(r_idx, 2, QTableWidgetItem(str(brand or "")))
            self.products_table.setItem(r_idx, 3, QTableWidgetItem(str(cat_name)))
            self.products_table.setItem(r_idx, 4, QTableWidgetItem(str(sup_name)))
            self.products_table.setItem(r_idx, 5, QTableWidgetItem(f"{float(price):.2f}"))
            self.products_table.setItem(r_idx, 6, QTableWidgetItem(f"{int(stock)} шт."))
            self.products_table.setItem(r_idx, 7, QTableWidgetItem(str(desc)))

    def _get_selected_product_id(self):
        row = self.products_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Увага", "Оберіть товар у таблиці.")
            return None
        item = self.products_table.item(row, 0)
        if not item:
            return None
        return item.data(Qt.UserRole)

    def add_product(self):
        dialog = ProductDialog(self.db, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            new_prod = dialog.get_product_data()
            self.db.add_product(new_prod)
            self.load_products()
            self.data_changed.emit()
            QMessageBox.information(self, "Успіх", "Товар успішно додано до каталогу!")

    def edit_product(self):
        prod_id = self._get_selected_product_id()
        if prod_id is None:
            return

        prod = self.db.get_product_by_id(prod_id)
        if not prod:
            QMessageBox.warning(self, "Помилка", "Товар не знайдено у базі даних.")
            return

        dialog = ProductDialog(self.db, product=prod, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            updated_prod = dialog.get_product_data()
            self.db.update_product(updated_prod)
            self.load_products()
            self.data_changed.emit()
            QMessageBox.information(self, "Успіх", "Дані товару успішно оновлено!")

    def delete_product(self):
        prod_id = self._get_selected_product_id()
        if prod_id is None:
            return

        confirm = QMessageBox.question(
            self,
            "Підтвердження видалення",
            "Ви дійсно бажаєте видалити обраний товар?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            self.db.delete_product(prod_id)
            self.load_products()
            self.data_changed.emit()
            QMessageBox.information(self, "Успіх", "Товар видалено.")
        except sqlite3.IntegrityError:
            QMessageBox.critical(
                self,
                "Помилка видалення",
                "Неможливо видалити товар, оскільки він уже присутній в оформлених замовленнях."
            )
            