import sqlite3
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QTableWidget, QTableWidgetItem, QPushButton, 
    QHeaderView, QMessageBox, QLineEdit, QSpinBox, QTabWidget
)
from db_manager import DatabaseManager
from cart import CartDialog
from orders_tab import OrdersTab


class ClientCatalogWidget(QWidget):
    """Віджет каталогу товарів для клієнта"""
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.cart = []
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

        self.cart_btn = QPushButton("🛒 Кошик (0)")
        self.cart_btn.clicked.connect(self.open_cart)
        filter_row1.addWidget(self.cart_btn)

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

        action_layout = QHBoxLayout()
        self.details_btn = QPushButton("Деталі товару")
        self.details_btn.clicked.connect(self.show_details)
        action_layout.addWidget(self.details_btn)
        action_layout.addStretch()
        main_layout.addLayout(action_layout)

        self.products_table = QTableWidget()
        self.products_table.setColumnCount(5)
        self.products_table.setHorizontalHeaderLabels(["ID", "Назва", "Бренд", "Ціна (грн)", "На складі"])
        self.products_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.products_table.setSelectionBehavior(QTableWidget.SelectRows)
        main_layout.addWidget(self.products_table)

        cart_action_layout = QHBoxLayout()
        cart_action_layout.addWidget(QLabel("Кількість для покупки:"))
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 100)
        cart_action_layout.addWidget(self.quantity_spin)

        self.add_to_cart_btn = QPushButton("Додати до кошика")
        self.add_to_cart_btn.clicked.connect(self.add_to_cart)
        cart_action_layout.addWidget(self.add_to_cart_btn)

        main_layout.addLayout(cart_action_layout)

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

    def update_cart_btn_text(self):
        total_count = sum(qty for _, qty in self.cart)
        self.cart_btn.setText(f"🛒 Кошик ({total_count})")

    def add_to_cart(self):
        prod_id = self._get_selected_product_id()
        if prod_id is None:
            return

        prod = self.db.get_product_by_id(prod_id)
        qty = self.quantity_spin.value()

        existing_qty = sum(item_qty for p, item_qty in self.cart if p.product_id == prod.product_id)

        if existing_qty + qty > prod.stock_quantity:
            QMessageBox.warning(
                self, "Помилка", 
                f"Недостатня кількість на складі!\nДоступно: {prod.stock_quantity} шт. (У кошику вже: {existing_qty} шт.)"
            )
            return

        for i, (p, item_qty) in enumerate(self.cart):
            if p.product_id == prod.product_id:
                self.cart[i] = (p, item_qty + qty)
                break
        else:
            self.cart.append((prod, qty))

        self.update_cart_btn_text()
        QMessageBox.information(self, "Кошик", f"Товар «{prod.title}» ({qty} шт.) додано до кошика!")

    def open_cart(self):
        dialog = CartDialog(self.cart, self.db, parent=self)
        dialog.exec_()
        self.update_cart_btn_text()


class ClientWindow(QMainWindow):
    """Головне вікно Клієнта"""
    def __init__(self, db_manager=None, client_id=None):
        super().__init__()
        self.db = db_manager or DatabaseManager()
        self.client_id = client_id
        self.setWindowTitle("Магазин комп'ютерної техніки — Клієнт")
        self.resize(1000, 650)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.catalog_widget = ClientCatalogWidget(self.db)
        # Для клієнта is_admin=False
        self.orders_widget = OrdersTab(self.db, client_id=self.client_id, is_admin=False)

        self.tabs.addTab(self.catalog_widget, "Каталог товарів")
        self.tabs.addTab(self.orders_widget, "Мої замовлення")

        self.tabs.currentChanged.connect(self.on_tab_change)

    def set_client_id(self, client_id):
        self.client_id = client_id
        self.orders_widget.set_client_id(client_id)

    def on_tab_change(self, index):
        if index == 1:
            self.orders_widget.load_orders()
            