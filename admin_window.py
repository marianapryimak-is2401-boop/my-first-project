import sqlite3
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QTableWidget, QTableWidgetItem, QPushButton, 
    QHeaderView, QMessageBox, QLineEdit, QTabWidget, QDialog
)
from db_manager import DatabaseManager
from catalog_tab import ProductDialog
from orders_tab import OrdersTab
from suppliers import SuppliersWindow


class AdminCatalogWidget(QWidget):
    """Віджет управління товарами для адміністратора"""
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        filter_row1 = QHBoxLayout()
        
        filter_row1.addWidget(QLabel("Категорія:"))
        self.category_combo = QComboBox()
        self.category_combo.currentIndexChanged.connect(self.load_products)
        filter_row1.addWidget(self.category_combo)

        filter_row1.addWidget(QLabel("Пошук:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Назва або бренд...")
        self.search_input.textChanged.connect(self.load_products)
        filter_row1.addWidget(self.search_input)

        filter_row1.addWidget(QLabel("Сортування:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("За замовчуванням", "default")
        self.sort_combo.addItem("Від дешевших до дорожчих", "price_asc")
        self.sort_combo.addItem("Від дорожчих до дешевших", "price_desc")
        self.sort_combo.addItem("За наявністю (спочатку більше)", "stock_desc")
        self.sort_combo.addItem("За наявністю (спочатку менше)", "stock_asc")
        self.sort_combo.currentIndexChanged.connect(self.load_products)
        filter_row1.addWidget(self.sort_combo)

        main_layout.addLayout(filter_row1)

        filter_row2 = QHBoxLayout()

        filter_row2.addWidget(QLabel("Ціна від:"))
        self.min_price_input = QLineEdit()
        self.min_price_input.setPlaceholderText("0")
        self.min_price_input.textChanged.connect(self.load_products)
        filter_row2.addWidget(self.min_price_input)

        filter_row2.addWidget(QLabel("Ціна до:"))
        self.max_price_input = QLineEdit()
        self.max_price_input.setPlaceholderText("макс")
        self.max_price_input.textChanged.connect(self.load_products)
        filter_row2.addWidget(self.max_price_input)

        self.reset_btn = QPushButton("Скинути фільтри")
        self.reset_btn.clicked.connect(self.reset_filters)
        filter_row2.addWidget(self.reset_btn)

        main_layout.addLayout(filter_row2)

        action_btn_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("➕ Додати товар")
        self.add_btn.clicked.connect(self.add_product)
        action_btn_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("✏️ Редагувати товар / ціну")
        self.edit_btn.clicked.connect(self.edit_product)
        action_btn_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("❌ Видалити товар")
        self.delete_btn.clicked.connect(self.delete_product)
        action_btn_layout.addWidget(self.delete_btn)

        self.details_btn = QPushButton("ℹ️ Деталі")
        self.details_btn.clicked.connect(self.show_details)
        action_btn_layout.addWidget(self.details_btn)

        self.suppliers_btn = QPushButton("📦 Постачальники")
        self.suppliers_btn.clicked.connect(self.open_suppliers)
        action_btn_layout.addWidget(self.suppliers_btn)

        main_layout.addLayout(action_btn_layout)

        self.products_table = QTableWidget()
        self.products_table.setColumnCount(5)
        self.products_table.setHorizontalHeaderLabels(["ID", "Назва", "Бренд", "Ціна (грн)", "На складі"])
        self.products_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.products_table.setSelectionBehavior(QTableWidget.SelectRows)
        main_layout.addWidget(self.products_table)

        self.load_categories()

    def load_categories(self):
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItem("Всі категорії", None)
        categories = self.db.get_all_categories()
        for cat in categories:
            self.category_combo.addItem(cat.name, cat.category_id)
        self.category_combo.blockSignals(False)
        self.load_products()

    def load_products(self):
        category_id = self.category_combo.currentData()
        query = self.search_input.text().strip()
        sort_by = self.sort_combo.currentData() or "default"

        min_price = None
        max_price = None

        min_txt = self.min_price_input.text().strip().replace(',', '.')
        if min_txt:
            try:
                min_price = float(min_txt)
            except ValueError:
                pass

        max_txt = self.max_price_input.text().strip().replace(',', '.')
        if max_txt:
            try:
                max_price = float(max_txt)
            except ValueError:
                pass

        products = self.db.search_products(
            query=query, 
            category_id=category_id,
            min_price=min_price,
            max_price=max_price,
            sort_by=sort_by
        )

        if not products:
            self.products_table.setRowCount(1)
            self.products_table.setItem(0, 0, QTableWidgetItem(""))
            self.products_table.setItem(0, 1, QTableWidgetItem("Товарів не знайдено"))
            self.products_table.setItem(0, 2, QTableWidgetItem(""))
            self.products_table.setItem(0, 3, QTableWidgetItem(""))
            self.products_table.setItem(0, 4, QTableWidgetItem(""))
            return

        self.products_table.setRowCount(len(products))
        for row, prod in enumerate(products):
            self.products_table.setItem(row, 0, QTableWidgetItem(str(prod.product_id)))
            self.products_table.setItem(row, 1, QTableWidgetItem(prod.title))
            self.products_table.setItem(row, 2, QTableWidgetItem(prod.brand))
            self.products_table.setItem(row, 3, QTableWidgetItem(f"{prod.price:.2f}"))
            self.products_table.setItem(row, 4, QTableWidgetItem(str(prod.stock_quantity)))

    def reset_filters(self):
        self.category_combo.blockSignals(True)
        self.search_input.blockSignals(True)
        self.sort_combo.blockSignals(True)
        self.min_price_input.blockSignals(True)
        self.max_price_input.blockSignals(True)

        self.category_combo.setCurrentIndex(0)
        self.search_input.clear()
        self.sort_combo.setCurrentIndex(0)
        self.min_price_input.clear()
        self.max_price_input.clear()

        self.category_combo.blockSignals(False)
        self.search_input.blockSignals(False)
        self.sort_combo.blockSignals(False)
        self.min_price_input.blockSignals(False)
        self.max_price_input.blockSignals(False)

        self.load_products()

    def _get_selected_product_id(self):
        selected = self.products_table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Увага", "Оберіть товар у таблиці.")
            return None
        
        item = self.products_table.item(selected, 0)
        if not item or not item.text().isdigit():
            QMessageBox.warning(self, "Увага", "Обрано порожній рядок або товари відсутні.")
            return None
            
        return int(item.text())

    def add_product(self):
        dialog = ProductDialog(self.db, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            new_prod = dialog.get_product_data()
            self.db.add_product(new_prod)
            QMessageBox.information(self, "Успіх", "Товар успішно додано!")
            self.load_products()

    def edit_product(self):
        prod_id = self._get_selected_product_id()
        if prod_id is None:
            return

        prod = self.db.get_product_by_id(prod_id)
        if not prod:
            QMessageBox.warning(self, "Помилка", "Товар не знайдено.")
            return

        dialog = ProductDialog(self.db, product=prod, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            updated_prod = dialog.get_product_data()
            self.db.update_product(updated_prod)
            QMessageBox.information(self, "Успіх", "Дані товару оновлено!")
            self.load_products()

    def delete_product(self):
        prod_id = self._get_selected_product_id()
        if prod_id is None:
            return

        confirm = QMessageBox.question(
            self, "Підтвердження", 
            "Ви дійсно бажаєте видалити цей товар?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            try:
                self.db.delete_product(prod_id)
                QMessageBox.information(self, "Успіх", "Товар видалено!")
                self.load_products()
            except sqlite3.IntegrityError:
                QMessageBox.critical(
                    self, "Помилка видалення", 
                    "Неможливо видалити товар, оскільки він уже присутній у замовленнях!"
                )

    def show_details(self):
        prod_id = self._get_selected_product_id()
        if prod_id is None:
            return

        prod = self.db.get_product_by_id(prod_id)
        if prod:
            info = (
                f"<b>ID:</b> {prod.product_id}<br>"
                f"<b>Назва:</b> {prod.title}<br>"
                f"<b>Бренд:</b> {prod.brand}<br>"
                f"<b>Ціна:</b> {prod.price:.2f} грн<br>"
                f"<b>Кількість:</b> {prod.stock_quantity} шт.<br><br>"
                f"<b>Опис:</b><br>{prod.description or 'Опис відсутній'}"
            )
            QMessageBox.information(self, f"Деталі товару №{prod.product_id}", info)

    def open_suppliers(self):
        dialog = SuppliersWindow(self.db, parent=self)
        dialog.exec_()


class AdminWindow(QMainWindow):
    """Головне вікно Адміністратора"""
    def __init__(self, db_manager=None):
        super().__init__()
        self.db = db_manager or DatabaseManager()
        self.setWindowTitle("Магазин комп'ютерної техніки — Панель Адміністратора")
        self.resize(1000, 650)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.catalog_widget = AdminCatalogWidget(self.db)
        # Для адміністратора is_admin=True (перегляд усіх замовлень)
        self.orders_widget = OrdersTab(self.db, client_id=None, is_admin=True)

        self.tabs.addTab(self.catalog_widget, "Управління товарами")
        self.tabs.addTab(self.orders_widget, "Усі замовлення")

        self.tabs.currentChanged.connect(self.on_tab_change)

    def on_tab_change(self, index):
        if index == 1:
            self.orders_widget.load_orders()
            