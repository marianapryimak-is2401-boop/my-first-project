from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QComboBox, QPushButton, QLineEdit, QTabWidget,
    QFrame, QCheckBox, QScrollArea, QStackedWidget
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal
from db_manager import DatabaseManager
from cart import CartDialog
from orders_tab import OrdersTab
from product_detail_page import ProductDetailPage
from favorites_tab import FavoritesTab
from profile import PersonalAccountWidget


class ProductCard(QFrame):
    """Картка товару в загальному каталозі"""
    card_clicked = pyqtSignal(int)
    favorite_clicked = pyqtSignal(int)

    def __init__(self, product, is_favorite: bool = False, parent=None):
        super().__init__(parent)
        self.product = product
        self.is_favorite = is_favorite
        self.setObjectName("ProductCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumWidth(250)
        self.setStyleSheet("""
            QFrame#ProductCard {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 10px;
            }
            QFrame#ProductCard:hover {
                border: 1px solid #2563EB;
                background-color: #F8FAFC;
            }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        brand_lbl = QLabel(self.product.brand)
        brand_lbl.setStyleSheet("""
            background-color: #F1F5F9;
            color: #475569;
            font-size: 11px;
            font-weight: bold;
            padding: 3px 8px;
            border-radius: 4px;
        """)
        top_row.addWidget(brand_lbl)
        top_row.addStretch()

        self.heart_btn = QPushButton()
        self.heart_btn.setFixedSize(32, 32)
        self.heart_btn.setCursor(Qt.PointingHandCursor)
        self.heart_btn.setToolTip("Додати / видалити з обраного")
        self.heart_btn.clicked.connect(lambda: self.favorite_clicked.emit(self.product.product_id))
        self.update_heart_style()
        top_row.addWidget(self.heart_btn)

        layout.addLayout(top_row)

        title_lbl = QLabel(self.product.title)
        title_lbl.setWordWrap(True)
        title_lbl.setMinimumHeight(42)
        title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #0F172A; background: transparent;")
        layout.addWidget(title_lbl)

        if self.product.stock_quantity > 0:
            stock_lbl = QLabel(f"● В наявності: {self.product.stock_quantity} шт.")
            stock_lbl.setStyleSheet("font-size: 12px; color: #15803D; font-weight: bold; background: transparent;")
        else:
            stock_lbl = QLabel("● Немає в наявності")
            stock_lbl.setStyleSheet("font-size: 12px; color: #DC2626; font-weight: bold; background: transparent;")
        layout.addWidget(stock_lbl)

        layout.addStretch()

        bottom_row = QHBoxLayout()
        price_lbl = QLabel(f"{self.product.price:.2f} грн")
        price_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #1E293B; background: transparent;")
        bottom_row.addWidget(price_lbl)

        bottom_row.addStretch()

        details_btn = QPushButton("Детальніше")
        details_btn.setCursor(Qt.PointingHandCursor)
        details_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 12px;
                padding: 6px 12px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
        """)
        details_btn.clicked.connect(lambda: self.card_clicked.emit(self.product.product_id))
        bottom_row.addWidget(details_btn)

        layout.addLayout(bottom_row)

    def update_heart_style(self):
        if self.is_favorite:
            self.heart_btn.setText("❤️")
            self.heart_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FEF2F2;
                    border: 1px solid #FECACA;
                    border-radius: 16px;
                    font-size: 15px;
                }
                QPushButton:hover { background-color: #FEE2E2; }
            """)
        else:
            self.heart_btn.setText("♡")
            self.heart_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F8FAFC;
                    border: 1px solid #CBD5E1;
                    border-radius: 16px;
                    font-size: 16px;
                    color: #64748B;
                }
                QPushButton:hover {
                    background-color: #F1F5F9;
                    color: #DC2626;
                }
            """)

    def set_favorite(self, is_fav: bool):
        self.is_favorite = is_fav
        self.update_heart_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.card_clicked.emit(self.product.product_id)
        super().mousePressEvent(event)


class ClientCatalogWidget(QWidget):
    """Віджет каталогу товарів (картки товарів) + окрема сторінка деталей товару"""
    SIDEBAR_WIDTH = 290
    favorites_changed = pyqtSignal()

    def __init__(self, db_manager, get_client_id_func):
        super().__init__()
        self.db = db_manager
        self.get_client_id = get_client_id_func
        self.cart = []
        self.category_checkboxes = []
        self.card_widgets = {}
        self.current_products = []
        self.sidebar_open = False
        self.return_to_favorites_callback = None
        self.init_ui()

    def init_ui(self):
        self.stack = QStackedWidget(self)
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self.stack)

        # ==========================================
        # СТОРІНКА 0: ЗАГАЛЬНИЙ КАТАЛОГ З ФІЛЬТРАМИ
        # ==========================================
        catalog_page = QWidget()
        root_layout = QHBoxLayout(catalog_page)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar_container = QFrame()
        self.sidebar_container.setMaximumWidth(0)
        self.sidebar_container.setMinimumWidth(0)
        self.sidebar_container.setObjectName("SidebarContainer")
        self.sidebar_container.setStyleSheet("""
            QFrame#SidebarContainer {
                background-color: #F8FAFC;
                border-right: 1px solid #CBD5E1;
            }
        """)

        sidebar_outer_layout = QVBoxLayout(self.sidebar_container)
        sidebar_outer_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_outer_layout.setSpacing(0)

        self.sidebar_inner = QWidget()
        self.sidebar_inner.setFixedWidth(self.SIDEBAR_WIDTH)
        sidebar_layout = QVBoxLayout(self.sidebar_inner)
        sidebar_layout.setContentsMargins(14, 12, 14, 12)
        sidebar_layout.setSpacing(10)

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

        line_top = QFrame()
        line_top.setFrameShape(QFrame.HLine)
        line_top.setStyleSheet("color: #CBD5E1;")
        sidebar_layout.addWidget(line_top)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("background-color: transparent;")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        filters_body_layout = QVBoxLayout(scroll_content)
        filters_body_layout.setContentsMargins(0, 2, 4, 2)
        filters_body_layout.setSpacing(10)

        cat_label = QLabel("Категорія")
        cat_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #1E293B;")
        filters_body_layout.addWidget(cat_label)

        self.categories_box = QVBoxLayout()
        self.categories_box.setSpacing(5)
        filters_body_layout.addLayout(self.categories_box)

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
            QPushButton:hover { background-color: #1D4ED8; }
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
            QPushButton:hover { background-color: #CBD5E1; }
        """)
        self.reset_btn.clicked.connect(self.reset_filters)
        buttons_layout.addWidget(self.reset_btn)

        filters_body_layout.addLayout(buttons_layout)
        filters_body_layout.addStretch()

        scroll_area.setWidget(scroll_content)
        sidebar_layout.addWidget(scroll_area, stretch=1)

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

        self.sidebar_anim = QPropertyAnimation(self.sidebar_container, b"maximumWidth")
        self.sidebar_anim.setDuration(220)
        self.sidebar_anim.setEasingCurve(QEasingCurve.InOutCubic)

        root_layout.addWidget(self.sidebar_container)

        main_content = QWidget()
        main_layout = QVBoxLayout(main_content)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(10)

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
            QPushButton:hover { background-color: #E2E8F0; }
        """)
        self.menu_btn.clicked.connect(self.toggle_sidebar)
        top_bar.addWidget(self.menu_btn)

        top_bar.addWidget(QLabel("Пошук:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Назва товару або бренд...")
        self.search_input.textChanged.connect(self.load_products)
        top_bar.addWidget(self.search_input)

        self.cart_btn = QPushButton("🛒 Кошик (0)")
        self.cart_btn.setCursor(Qt.PointingHandCursor)
        self.cart_btn.setStyleSheet("""
            QPushButton {
                background-color: #F8FAFC;
                border: 1px solid #CBD5E1;
                border-radius: 5px;
                padding: 6px 14px;
                font-weight: bold;
                color: #0F172A;
            }
            QPushButton:hover { background-color: #E2E8F0; }
        """)
        self.cart_btn.clicked.connect(self.open_cart)
        top_bar.addWidget(self.cart_btn)

        main_layout.addLayout(top_bar)

        self.cards_scroll = QScrollArea()
        self.cards_scroll.setWidgetResizable(True)
        self.cards_scroll.setFrameShape(QFrame.NoFrame)
        self.cards_scroll.setStyleSheet("background-color: #F1F5F9; border-radius: 8px;")

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background-color: #F1F5F9;")
        self.cards_grid = QGridLayout(self.cards_container)
        self.cards_grid.setContentsMargins(12, 12, 12, 12)
        self.cards_grid.setSpacing(12)
        self.cards_scroll.setWidget(self.cards_container)

        main_layout.addWidget(self.cards_scroll)

        root_layout.addWidget(main_content, stretch=1)
        self.stack.addWidget(catalog_page)

        # ==========================================
        # СТОРІНКА 1: ДЕТАЛЬНА СТОРІНКА ТОВАРУ
        # ==========================================
        self.detail_page = ProductDetailPage(
            db_manager=self.db,
            cart_list=self.cart,
            get_client_id_func=self.get_client_id
        )
        self.detail_page.back_requested.connect(self.close_product_detail)
        self.detail_page.favorite_toggled.connect(self.on_detail_favorite_toggled)
        self.detail_page.cart_updated.connect(self.update_cart_btn_text)
        self.stack.addWidget(self.detail_page)

        self.load_categories()

    def open_product_detail(self, product_id: int, return_callback=None):
        self.return_to_favorites_callback = return_callback
        self.detail_page.load_product(product_id)
        self.stack.setCurrentIndex(1)

    def close_product_detail(self):
        self.stack.setCurrentIndex(0)
        self.sync_card_hearts()
        if self.return_to_favorites_callback:
            cb = self.return_to_favorites_callback
            self.return_to_favorites_callback = None
            cb()

    def on_detail_favorite_toggled(self, product_id: int, is_fav: bool):
        if product_id in self.card_widgets:
            self.card_widgets[product_id].set_favorite(is_fav)
        self.favorites_changed.emit()

    def toggle_sidebar(self):
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

    def load_categories(self):
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
        return [cb.property("category_id") for cb in self.category_checkboxes if cb.isChecked()]

    def load_products(self):
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

        self.current_products = self.db.search_products(
            query=query,
            category_ids=selected_category_ids if selected_category_ids else None,
            min_price=min_price,
            max_price=max_price,
            sort_by=sort_by
        )
        self.render_product_cards()

    def render_product_cards(self):
        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.card_widgets.clear()

        if not self.current_products:
            empty_lbl = QLabel("Товарів за вибраними критеріями не знайдено.")
            empty_lbl.setAlignment(Qt.AlignCenter)
            empty_lbl.setStyleSheet("font-size: 15px; color: #64748B; padding: 30px;")
            self.cards_grid.addWidget(empty_lbl, 0, 0)
            return

        client_id = self.get_client_id()
        favorite_ids = self.db.get_favorite_product_ids(client_id)

        available_width = max(600, self.cards_scroll.viewport().width())
        cols = max(2, available_width // 275)

        for idx, prod in enumerate(self.current_products):
            row = idx // cols
            col = idx % cols
            card = ProductCard(prod, is_favorite=(prod.product_id in favorite_ids))
            card.card_clicked.connect(lambda pid: self.open_product_detail(pid))
            card.favorite_clicked.connect(self.toggle_card_favorite)
            self.cards_grid.addWidget(card, row, col)
            self.card_widgets[prod.product_id] = card

        total_rows = (len(self.current_products) + cols - 1) // cols
        self.cards_grid.setRowStretch(total_rows, 1)

    def toggle_card_favorite(self, product_id: int):
        client_id = self.get_client_id()
        is_fav = self.db.toggle_favorite(client_id, product_id)
        if product_id in self.card_widgets:
            self.card_widgets[product_id].set_favorite(is_fav)
        self.favorites_changed.emit()

    def sync_card_hearts(self):
        client_id = self.get_client_id()
        favorite_ids = self.db.get_favorite_product_ids(client_id)
        for pid, card in self.card_widgets.items():
            card.set_favorite(pid in favorite_ids)

    def reset_filters(self):
        for cb in self.category_checkboxes:
            cb.setChecked(False)

        self.min_price_input.clear()
        self.max_price_input.clear()
        self.sort_combo.setCurrentIndex(0)

        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.blockSignals(False)

        self.load_products()

    def update_cart_btn_text(self):
        total_count = sum(qty for _, qty in self.cart)
        self.cart_btn.setText(f"🛒 Кошик ({total_count})")

    def open_cart(self):
        dialog = CartDialog(self.cart, self.db, parent=self)
        dialog.exec_()
        self.update_cart_btn_text()
        if self.stack.currentIndex() == 1 and self.detail_page.current_product:
            self.detail_page.load_product(self.detail_page.current_product.product_id)


class ClientWindow(QMainWindow):
    """Головне вікно Клієнта з кнопкою «Особистий кабінет»"""
    def __init__(self, db_manager=None, client_id=None):
        super().__init__()
        self.db = db_manager or DatabaseManager()
        self.client_id = client_id if client_id is not None else 1
        self.db.ensure_client_profile(self.client_id)

        self.setWindowTitle("Магазин комп'ютерної техніки — Клієнт")
        self.resize(1120, 720)

        central_container = QWidget()
        self.setCentralWidget(central_container)
        main_vbox = QVBoxLayout(central_container)
        main_vbox.setContentsMargins(0, 0, 0, 0)
        main_vbox.setSpacing(0)

        # --- Верхня панель магазину з кнопкою «Особистий кабінет» ---
        store_header = QFrame()
        store_header.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border-bottom: 1px solid #1E293B;
            }
        """)
        header_layout = QHBoxLayout(store_header)
        header_layout.setContentsMargins(16, 8, 16, 8)

        brand_title = QLabel("🖥️ PC Shop — Онлайн-магазин комп’ютерної техніки")
        brand_title.setStyleSheet("color: #F8FAFC; font-size: 15px; font-weight: bold; border: none;")
        header_layout.addWidget(brand_title)
        header_layout.addStretch()

        self.profile_btn = QPushButton("👤 Особистий кабінет")
        self.profile_btn.setCursor(Qt.PointingHandCursor)
        self.profile_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 13px;
                padding: 7px 16px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
        """)
        self.profile_btn.clicked.connect(self.open_personal_account)
        header_layout.addWidget(self.profile_btn)

        main_vbox.addWidget(store_header)

        # --- Стек сторінок: 0 -> Магазин (вкладки), 1 -> Особистий кабінет ---
        self.main_stack = QStackedWidget()
        main_vbox.addWidget(self.main_stack, stretch=1)

        self.tabs = QTabWidget()
        self.catalog_widget = ClientCatalogWidget(self.db, self.get_active_client_id)
        self.favorites_widget = FavoritesTab(self.db, self.get_active_client_id)
        self.orders_widget = OrdersTab(self.db, client_id=self.client_id, is_admin=False)

        self.tabs.addTab(self.catalog_widget, "Каталог товарів")
        self.tabs.addTab(self.favorites_widget, "❤️ Обране")
        self.tabs.addTab(self.orders_widget, "Мої замовлення")

        self.main_stack.addWidget(self.tabs)

        # Сторінка особистого кабінету з окремого модуля profile.py
        self.profile_widget = PersonalAccountWidget(
            db_manager=self.db,
            get_client_id_func=self.get_active_client_id
        )
        self.profile_widget.back_to_store_requested.connect(self.close_personal_account)
        self.main_stack.addWidget(self.profile_widget)

        self.catalog_widget.favorites_changed.connect(self.favorites_widget.load_favorites)
        self.favorites_widget.favorite_removed.connect(lambda _: self.catalog_widget.sync_card_hearts())
        self.favorites_widget.open_product_requested.connect(self.open_product_from_favorites)

        self.tabs.currentChanged.connect(self.on_tab_change)

    def get_active_client_id(self) -> int:
        return self.client_id if self.client_id is not None else 1

    def open_personal_account(self):
        """Відкриття особистого кабінету покупця з оновленням профілю, бонусів та замовлень"""
        self.profile_widget.refresh_data()
        self.main_stack.setCurrentIndex(1)

    def close_personal_account(self):
        """Повернення з особистого кабінету до каталогу магазину"""
        self.main_stack.setCurrentIndex(0)
        if self.tabs.currentIndex() == 2:
            self.orders_widget.load_orders()

    def open_product_from_favorites(self, product_id: int):
        self.tabs.setCurrentIndex(0)
        self.catalog_widget.open_product_detail(
            product_id,
            return_callback=lambda: self.tabs.setCurrentIndex(1)
        )

    def set_client_id(self, client_id):
        self.client_id = client_id
        self.db.ensure_client_profile(self.client_id)
        self.orders_widget.set_client_id(client_id)
        self.favorites_widget.load_favorites()
        self.catalog_widget.sync_card_hearts()
        if self.main_stack.currentIndex() == 1:
            self.profile_widget.refresh_data()

    def on_tab_change(self, index):
        if index == 0:
            self.catalog_widget.sync_card_hearts()
        elif index == 1:
            self.favorites_widget.load_favorites()
        elif index == 2:
            self.orders_widget.load_orders()
            