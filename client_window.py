from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QTableWidget, QTableWidgetItem, QPushButton, 
    QHeaderView, QMessageBox, QLineEdit, QSpinBox, QTabWidget,
    QFrame, QCheckBox, QScrollArea
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve
from db_manager import DatabaseManager
from cart import CartDialog
from orders_tab import OrdersTab


class ClientCatalogWidget(QWidget):
    """Віджет каталогу товарів для клієнта з висувною бічною панеллю фільтрів"""
    SIDEBAR_WIDTH = 290

    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.cart = []
        self.category_checkboxes = []
        self.sidebar_open = False
        self.init_ui()

    def init_ui(self):
        # Головний горизонтальний макет: [Ліва бічна панель] + [Основний контент каталогу]
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ==========================================
        # 1. ЛІВА БІЧНА ПАНЕЛЬ ФІЛЬТРІВ ТА КОНТАКТІВ
        # ==========================================
        self.sidebar_container = QFrame()
        self.sidebar_container.setMaximumWidth(0)
        self.sidebar_container.setMinimumWidth(0)
        self.sidebar_container.setStyleSheet("""
            QFrame#SidebarContainer {
                background-color: #F8FAFC;
                border-right: 1px solid #CBD5E1;
            }
        """)
        self.sidebar_container.setObjectName("SidebarContainer")

        sidebar_outer_layout = QVBoxLayout(self.sidebar_container)
        sidebar_outer_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_outer_layout.setSpacing(0)

        # Внутрішній контейнер фіксованої ширини, щоб елементи не стискалися під час анімації
        self.sidebar_inner = QWidget()
        self.sidebar_inner.setFixedWidth(self.SIDEBAR_WIDTH)
        sidebar_layout = QVBoxLayout(self.sidebar_inner)
        sidebar_layout.setContentsMargins(14, 12, 14, 12)
        sidebar_layout.setSpacing(10)

        # --- Верхня шапка панелі: "Фільтри" + кнопка "✕" ---
        sidebar_header = QHBoxLayout()
        filters_title = QLabel("Фільтри")
        filters_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        sidebar_header.addWidget(filters_title)

        sidebar_header.addStretch()

        self.close_sidebar_btn = QPushButton("✕")
        self.close_sidebar_btn.setFixedSize(28, 28)
        self.close_sidebar_btn.setCursor(Qt.PointingHandCursor)
        self.close_sidebar_btn.setToolTip("Закрити панель фільтрів")
        self.close_sidebar_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
                color: #475569;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
                color: #0F172A;
            }
        """)
        self.close_sidebar_btn.clicked.connect(self.close_sidebar)
        sidebar_header.addWidget(self.close_sidebar_btn)

        sidebar_layout.addLayout(sidebar_header)

        # Розділювач
        line_top = QFrame()
        line_top.setFrameShape(QFrame.HLine)
        line_top.setStyleSheet("color: #CBD5E1;")
        sidebar_layout.addWidget(line_top)

        # --- Прокручувана область для блоків фільтрації ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("background-color: transparent;")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        filters_body_layout = QVBoxLayout(scroll_content)
        filters_body_layout.setContentsMargins(0, 2, 4, 2)
        filters_body_layout.setSpacing(10)

        # БЛОК: Категорія (чекбокси)
        cat_label = QLabel("Категорія")
        cat_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #1E293B;")
        filters_body_layout.addWidget(cat_label)

        self.categories_box = QVBoxLayout()
        self.categories_box.setSpacing(5)
        filters_body_layout.addLayout(self.categories_box)

        # БЛОК: Фільтр ціни
        price_section_label = QLabel("Ціна (грн)")
        price_section_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #1E293B; margin-top: 4px;")
        filters_body_layout.addWidget(price_section_label)

        price_from_layout = QHBoxLayout()
        lbl_from = QLabel("Ціна від:")
        lbl_from.setFixedWidth(60)
        lbl_from.setStyleSheet("color: #334155;")
        self.min_price_input = QLineEdit()
        self.min_price_input.setPlaceholderText("10000")
        self.min_price_input.setStyleSheet("background-color: #FFFFFF; padding: 4px 6px; border: 1px solid #CBD5E1; border-radius: 4px;")
        price_from_layout.addWidget(lbl_from)
        price_from_layout.addWidget(self.min_price_input)
        filters_body_layout.addLayout(price_from_layout)

        price_to_layout = QHBoxLayout()
        lbl_to = QLabel("Ціна до:")
        lbl_to.setFixedWidth(60)
        lbl_to.setStyleSheet("color: #334155;")
        self.max_price_input = QLineEdit()
        self.max_price_input.setPlaceholderText("50000")
        self.max_price_input.setStyleSheet("background-color: #FFFFFF; padding: 4px 6px; border: 1px solid #CBD5E1; border-radius: 4px;")
        price_to_layout.addWidget(lbl_to)
        price_to_layout.addWidget(self.max_price_input)
        filters_body_layout.addLayout(price_to_layout)

        # БЛОК: Сортування
        sort_label = QLabel("Сортування")
        sort_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #1E293B; margin-top: 4px;")
        filters_body_layout.addWidget(sort_label)

        self.sort_combo = QComboBox()
        self.sort_combo.addItem("За замовчуванням", "default")
        self.sort_combo.addItem("За ціною (зростанням)", "price_asc")
        self.sort_combo.addItem("За ціною (спаданням)", "price_desc")
        self.sort_combo.addItem("За наявністю", "stock_desc")
        self.sort_combo.setStyleSheet("background-color: #FFFFFF; padding: 5px; border: 1px solid #CBD5E1; border-radius: 4px;")
        filters_body_layout.addWidget(self.sort_combo)

        # КНОПКИ: Застосувати та Скинути фільтри
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(6)
        buttons_layout.setContentsMargins(0, 8, 0, 4)

        self.apply_btn = QPushButton("Застосувати")
        self.apply_btn.setCursor(Qt.PointingHandCursor)
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: bold;
                padding: 7px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
        """)
        self.apply_btn.clicked.connect(self.load_products)
        buttons_layout.addWidget(self.apply_btn)

        self.reset_btn = QPushButton("Скинути фільтри")
        self.reset_btn.setCursor(Qt.PointingHandCursor)
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #E2E8F0;
                color: #1E293B;
                padding: 6px;
                border: 1px solid #CBD5E1;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #CBD5E1;
            }
        """)
        self.reset_btn.clicked.connect(self.reset_filters)
        buttons_layout.addWidget(self.reset_btn)

        filters_body_layout.addLayout(buttons_layout)
        filters_body_layout.addStretch()

        scroll_area.setWidget(scroll_content)
        sidebar_layout.addWidget(scroll_area, stretch=1)

        # --- БЛОК: Контакти (у самому низу бічної панелі) ---
        contacts_frame = QFrame()
        contacts_frame.setStyleSheet("""
            QFrame {
                background-color: #EEF2FF;
                border: 1px solid #C7D2FE;
                border-radius: 6px;
            }
            QLabel {
                border: none;
                background: transparent;
                color: #1E293B;
                font-size: 11px;
            }
        """)
        contacts_layout = QVBoxLayout(contacts_frame)
        contacts_layout.setContentsMargins(10, 8, 10, 8)
        contacts_layout.setSpacing(4)

        contacts_title = QLabel("Контакти")
        contacts_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #1E3A8A; border: none;")
        contacts_layout.addWidget(contacts_title)

        contacts_layout.addWidget(QLabel("📞 Телефон: +38 (067) 123-45-67"))
        contacts_layout.addWidget(QLabel("✉ Email: support@pcshop.ua"))
        contacts_layout.addWidget(QLabel("📍 Адреса: м. Київ, вул. Хрещатик, 22"))
        contacts_layout.addWidget(QLabel("📷 Instagram: @pcshop_ua"))
        contacts_layout.addWidget(QLabel("✈️ Telegram: @pcshop_support"))

        sidebar_layout.addWidget(contacts_frame)
        sidebar_outer_layout.addWidget(self.sidebar_inner)

        # Анімація відкриття/закриття бічної панелі
        self.sidebar_anim = QPropertyAnimation(self.sidebar_container, b"maximumWidth")
        self.sidebar_anim.setDuration(220)
        self.sidebar_anim.setEasingCurve(QEasingCurve.InOutCubic)

        root_layout.addWidget(self.sidebar_container)

        # ==========================================
        # 2. ОСНОВНИЙ КОНТЕНТ КАТАЛОГУ ТОВАРІВ
        # ==========================================
        main_content = QWidget()
        main_layout = QVBoxLayout(main_content)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(10)

        # Верхня панель: кнопка ☰ зліва, швидкий пошук, деталі та кошик
        top_bar = QHBoxLayout()

        self.menu_btn = QPushButton("☰")
        self.menu_btn.setFixedSize(36, 32)
        self.menu_btn.setCursor(Qt.PointingHandCursor)
        self.menu_btn.setToolTip("Відкрити / закрити фільтри")
        self.menu_btn.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                font-weight: bold;
                background-color: #F1F5F9;
                border: 1px solid #CBD5E1;
                border-radius: 5px;
                color: #0F172A;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
            }
        """)
        self.menu_btn.clicked.connect(self.toggle_sidebar)
        top_bar.addWidget(self.menu_btn)

        top_bar.addWidget(QLabel("Пошук:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Назва товару або бренд...")
        self.search_input.textChanged.connect(self.load_products)
        top_bar.addWidget(self.search_input)

        self.details_btn = QPushButton("Деталі товару")
        self.details_btn.clicked.connect(self.show_details)
        top_bar.addWidget(self.details_btn)

        self.cart_btn = QPushButton("🛒 Кошик (0)")
        self.cart_btn.clicked.connect(self.open_cart)
        top_bar.addWidget(self.cart_btn)

        main_layout.addLayout(top_bar)

        # Таблиця товарів (займає весь простір, коли панель закрита)
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(5)
        self.products_table.setHorizontalHeaderLabels(["ID", "Назва", "Бренд", "Ціна (грн)", "На складі"])
        self.products_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.products_table.setSelectionBehavior(QTableWidget.SelectRows)
        main_layout.addWidget(self.products_table)

        # Нижня панель додавання товару в кошик
        cart_action_layout = QHBoxLayout()
        cart_action_layout.addWidget(QLabel("Кількість для покупки:"))
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 100)
        cart_action_layout.addWidget(self.quantity_spin)

        self.add_to_cart_btn = QPushButton("Додати до кошика")
        self.add_to_cart_btn.clicked.connect(self.add_to_cart)
        cart_action_layout.addWidget(self.add_to_cart_btn)

        main_layout.addLayout(cart_action_layout)

        root_layout.addWidget(main_content, stretch=1)

        self.load_categories()

    # --- УПРАВЛІННЯ БІЧНОЮ ПАНЕЛЛЮ ---

    def toggle_sidebar(self):
        """Відкриття або закриття бічної панелі при натисканні на ☰"""
        if self.sidebar_open:
            self.close_sidebar()
        else:
            self.open_sidebar()

    def open_sidebar(self):
        self.sidebar_open = True
        self.sidebar_anim.stop()
        self.sidebar_anim.setStartValue(self.sidebar_container.width())
        self.sidebar_anim.setEndValue(self.SIDEBAR_WIDTH)
        self.sidebar_anim.start()

    def close_sidebar(self):
        self.sidebar_open = False
        self.sidebar_anim.stop()
        self.sidebar_anim.setStartValue(self.sidebar_container.width())
        self.sidebar_anim.setEndValue(0)
        self.sidebar_anim.start()

    # --- РОБОТА З КАТЕГОРІЯМИ ТА ФІЛЬТРАМИ ---

    def load_categories(self):
        """Динамічне завантаження категорій у вигляді чекбоксів"""
        # Очищення попередніх чекбоксів
        for cb in self.category_checkboxes:
            self.categories_box.removeWidget(cb)
            cb.deleteLater()
        self.category_checkboxes.clear()

        categories = self.db.get_all_categories()
        for cat in categories:
            cb = QCheckBox(cat.name)
            cb.setProperty("category_id", cat.category_id)
            cb.setStyleSheet("color: #334155; font-size: 12px;")
            self.categories_box.addWidget(cb)
            self.category_checkboxes.append(cb)

        self.load_products()

    def _get_selected_category_ids(self):
        """Повертає список ID обраних категорій"""
        selected = []
        for cb in self.category_checkboxes:
            if cb.isChecked():
                selected.append(cb.property("category_id"))
        return selected

    def load_products(self):
        """Застосування обраних категорій, діапазону цін, пошуку та сортування"""
        selected_category_ids = self._get_selected_category_ids()
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
            category_ids=selected_category_ids if selected_category_ids else None,
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
        """Очищення всіх фільтрів та повернення стандартного списку товарів"""
        for cb in self.category_checkboxes:
            cb.setChecked(False)

        self.min_price_input.clear()
        self.max_price_input.clear()
        self.sort_combo.setCurrentIndex(0)

        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.blockSignals(False)

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
        self.resize(1050, 680)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.catalog_widget = ClientCatalogWidget(self.db)
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
            