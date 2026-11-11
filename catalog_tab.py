import sqlite3
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QTableWidget, QTableWidgetItem, QPushButton, QHeaderView, 
    QMessageBox, QDialog, QFormLayout, QLineEdit, QSpinBox, 
    QDoubleSpinBox, QTextEdit
)
from classes import Product, Client, OrderItem
from cart import CartDialog  # Імпорт класу вікна кошика з файла cart.py


class ProductDialog(QDialog):
    """Діалогове вікно додавання/редагування товару"""
    def __init__(self, db_manager, product: Product = None, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.product = product
        self.setWindowTitle("Редагування товару" if product else "Додавання товару")
        self.resize(400, 350)

        layout = QFormLayout(self)

        self.category_combo = QComboBox()
        categories = self.db.get_all_categories()
        for cat in categories:
            self.category_combo.addItem(cat.name, cat.category_id)

        self.title_input = QLineEdit()
        self.brand_input = QLineEdit()

        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0.0, 1000000.0)
        self.price_spin.setDecimals(2)
        self.price_spin.setSuffix(" грн")

        self.stock_spin = QSpinBox()
        self.stock_spin.setRange(0, 100000)

        self.description_input = QTextEdit()

        layout.addRow("Категорія:", self.category_combo)
        layout.addRow("Назва:", self.title_input)
        layout.addRow("Бренд:", self.brand_input)
        layout.addRow("Ціна:", self.price_spin)
        layout.addRow("Кількість на складі:", self.stock_spin)
        layout.addRow("Опис:", self.description_input)

        self.save_btn = QPushButton("Зберегти")
        self.save_btn.clicked.connect(self.save)
        layout.addRow(self.save_btn)

        if self.product:
            idx = self.category_combo.findData(self.product.category_id)
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)
            self.title_input.setText(self.product.title)
            self.brand_input.setText(self.product.brand)
            self.price_spin.setValue(self.product.price)
            self.stock_spin.setValue(self.product.stock_quantity)
            self.description_input.setPlainText(self.product.description)
            
            # Вибір постачальника (у ProductDialog)
        self.supplier_combo = QComboBox()
        self.supplier_combo.addItem("Без постачальника", None)
        suppliers = self.db.get_all_suppliers()
        for s in suppliers:
            self.supplier_combo.addItem(s.name, s.supplier_id)
        
        layout.addRow("Постачальник:", self.supplier_combo)
        

    def save(self):
        if not self.title_input.text().strip():
            QMessageBox.warning(self, "Помилка", "Введіть назву товару.")
            return
        self.accept()

    def get_product_data(self) -> Product:
        category_id = self.category_combo.currentData()
        title = self.title_input.text().strip()
        brand = self.brand_input.text().strip()
        price = self.price_spin.value()
        stock = self.stock_spin.value()
        description = self.description_input.toPlainText().strip()
        
        prod_id = self.product.product_id if self.product else None
        return Product(
            category_id=category_id,
            title=title,
            brand=brand,
            price=price,
            stock_quantity=stock,
            description=description,
            product_id=prod_id
        )
        
  
        


class OrderDialog(QDialog):
    """Діалогове вікно для введення даних клієнта"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Оформлення замовлення")
        self.resize(350, 200)

        layout = QFormLayout(self)

        self.name_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.email_input = QLineEdit()
        self.address_input = QLineEdit()

        layout.addRow("ПІБ:", self.name_input)
        layout.addRow("Телефон:", self.phone_input)
        layout.addRow("Email:", self.email_input)
        layout.addRow("Адреса доставки:", self.address_input)

        self.submit_btn = QPushButton("Підтвердити замовлення")
        self.submit_btn.clicked.connect(self.accept)
        layout.addRow(self.submit_btn)

    def get_client_data(self) -> Client:
        return Client(
            full_name=self.name_input.text().strip(),
            phone=self.phone_input.text().strip(),
            email=self.email_input.text().strip(),
            address=self.address_input.text().strip()
        )


class CatalogTab(QWidget):
    """Вкладка каталогу товарів"""
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.cart = []
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # 1. Верхня панель фільтрів, пошуку та сортування
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

        # Кнопка відкриття окремого вікна кошика
        self.cart_btn = QPushButton("🛒 Кошик (0)")
        self.cart_btn.clicked.connect(self.open_cart)
        filter_row1.addWidget(self.cart_btn)

        main_layout.addLayout(filter_row1)

        # 2. Фільтр за діапазоном цін
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

        # 3. Кнопки управління товарами (CRUD)
        action_btn_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("Додати товар")
        self.add_btn.clicked.connect(self.add_product)
        action_btn_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("Редагувати")
        self.edit_btn.clicked.connect(self.edit_product)
        action_btn_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Видалити")
        self.delete_btn.clicked.connect(self.delete_product)
        action_btn_layout.addWidget(self.delete_btn)

        self.details_btn = QPushButton("Деталі")
        self.details_btn.clicked.connect(self.show_details)
        action_btn_layout.addWidget(self.details_btn)

        main_layout.addLayout(action_btn_layout)

        # 4. Таблиця товарів
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(5)
        self.products_table.setHorizontalHeaderLabels(["ID", "Назва", "Бренд", "Ціна (грн)", "На складі"])
        self.products_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.products_table.setSelectionBehavior(QTableWidget.SelectRows)
        main_layout.addWidget(self.products_table)

        # 5. Панель вибору кількості та додавання до кошика
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

    # --- ДІЇ З ТОВАРАМИ ---

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

    # --- ДІЇ З КОШИКОМ ---

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
        """Відкриття окремого вікна кошика із модуля cart.py"""
        dialog = CartDialog(self.cart, self.db, parent=self)
        dialog.exec_()
        self.update_cart_btn_text()
        