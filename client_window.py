from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QComboBox, QPushButton, QLineEdit, QTabWidget, QTabBar,
    QFrame, QCheckBox, QScrollArea, QStackedWidget
)
from PyQt5.QtCore import Qt, pyqtSignal
from db_manager import DatabaseManager
from cart import CartDialog
from product_detail_page import ProductDetailPage
from favorites_tab import FavoritesTab
from profile import PersonalAccountWidget


class MainTabBar(QTabBar):
    """Базова панель вкладок зі збільшеною вкладкою «Особистий кабінет»"""
    def tabSizeHint(self, index):
        size = super().tabSizeHint(index)
        if self.tabText(index) == "Особистий кабінет":
            size.setWidth(size.width() + 32)
            size.setHeight(size.height() + 8)
        else:
            size.setHeight(size.height() + 4)
        return size


class ProductCard(QFrame):
    """Базова картка товару в загальному каталозі"""
    card_clicked = pyqtSignal(int)
    favorite_clicked = pyqtSignal(int)

    def __init__(self, product, is_favorite: bool = False, parent=None):
        super().__init__(parent)
        self.product = product
        self.is_favorite = is_favorite
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumWidth(250)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        brand_lbl = QLabel(self.product.brand)
        top_row.addWidget(brand_lbl)
        top_row.addStretch()

        self.heart_btn = QPushButton()
        self.heart_btn.setFixedSize(32, 32)
        self.heart_btn.setCursor(Qt.PointingHandCursor)
        self.heart_btn.setToolTip("Додати / видалити з обраного")
        self.heart_btn.clicked.connect(lambda: self.favorite_clicked.emit(self.product.product_id))
        self.update_heart_text()
        top_row.addWidget(self.heart_btn)

        layout.addLayout(top_row)

        title_lbl = QLabel(f"<b>{self.product.title}</b>")
        title_lbl.setWordWrap(True)
        title_lbl.setMinimumHeight(40)
        layout.addWidget(title_lbl)

        if self.product.stock_quantity > 0:
            stock_lbl = QLabel(f"В наявності: {self.product.stock_quantity} шт.")
        else:
            stock_lbl = QLabel("Немає в наявності")
        layout.addWidget(stock_lbl)

        layout.addStretch()

        bottom_row = QHBoxLayout()
        price_lbl = QLabel(f"<b>{self.product.price:.2f} грн</b>")
        bottom_row.addWidget(price_lbl)
        bottom_row.addStretch()

        details_btn = QPushButton("Детальніше")
        details_btn.setCursor(Qt.PointingHandCursor)
        details_btn.clicked.connect(lambda: self.card_clicked.emit(self.product.product_id))
        bottom_row.addWidget(details_btn)

        layout.addLayout(bottom_row)

    def update_heart_text(self):
        self.heart_btn.setText("♥" if self.is_favorite else "♡")

    def set_favorite(self, is_fav: bool):
        self.is_favorite = is_fav
        self.update_heart_text()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.card_clicked.emit(self.product.product_id)
        super().mousePressEvent(event)


class ClientCatalogWidget(QWidget):
    """Віджет каталогу товарів з бічною панеллю фільтрів та сторінкою деталей товару"""
    favorites_changed = pyqtSignal()

    def __init__(self, db_manager, get_client_id_func):
        super().__init__()
        self.db = db_manager
        self.get_client_id = get_client_id_func
        self.cart = []
        self.category_checkboxes = []
        self.card_widgets = {}
        self.current_products = []
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

        # 1. ЛІВА БІЧНА ПАНЕЛЬ ФІЛЬТРІВ ТА КОНТАКТІВ (БАЗОВИЙ ВИГЛЯД)
        self.sidebar_container = QFrame()
        self.sidebar_container.setFrameShape(QFrame.StyledPanel)
        self.sidebar_container.setFixedWidth(270)
        self.sidebar_container.setVisible(False)

        sidebar_layout = QVBoxLayout(self.sidebar_container)
        sidebar_layout.setContentsMargins(12, 10, 12, 10)
        sidebar_layout.setSpacing(8)

        sidebar_header = QHBoxLayout()
        filters_title = QLabel("<b>Фільтри</b>")
        sidebar_header.addWidget(filters_title)
        sidebar_header.addStretch()

        self.close_sidebar_btn = QPushButton("✕")
        self.close_sidebar_btn.setFixedSize(28, 28)
        self.close_sidebar_btn.setCursor(Qt.PointingHandCursor)
        self.close_sidebar_btn.setToolTip("Закрити панель фільтрів")
        self.close_sidebar_btn.clicked.connect(self.close_sidebar)
        sidebar_header.addWidget(self.close_sidebar_btn)
        sidebar_layout.addLayout(sidebar_header)

        line_top = QFrame()
        line_top.setFrameShape(QFrame.HLine)
        sidebar_layout.addWidget(line_top)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        scroll_content = QWidget()
        filters_body_layout = QVBoxLayout(scroll_content)
        filters_body_layout.setContentsMargins(0, 2, 4, 2)
        filters_body_layout.setSpacing(8)

        filters_body_layout.addWidget(QLabel("<b>Категорія</b>"))

        self.categories_box = QVBoxLayout()
        self.categories_box.setSpacing(4)
        filters_body_layout.addLayout(self.categories_box)

        filters_body_layout.addWidget(QLabel("<b>Ціна (грн)</b>"))

        price_from_layout = QHBoxLayout()
        lbl_from = QLabel("Ціна від:")
        lbl_from.setFixedWidth(60)
        self.min_price_input = QLineEdit()
        self.min_price_input.setPlaceholderText("10000")
        price_from_layout.addWidget(lbl_from)
        price_from_layout.addWidget(self.min_price_input)
        filters_body_layout.addLayout(price_from_layout)

        price_to_layout = QHBoxLayout()
        lbl_to = QLabel("Ціна до:")
        lbl_to.setFixedWidth(60)
        self.max_price_input = QLineEdit()
        self.max_price_input.setPlaceholderText("50000")
        price_to_layout.addWidget(lbl_to)
        price_to_layout.addWidget(self.max_price_input)
        filters_body_layout.addLayout(price_to_layout)

        filters_body_layout.addWidget(QLabel("<b>Сортування</b>"))

        self.sort_combo = QComboBox()
        self.sort_combo.addItem("За замовчуванням", "default")
        self.sort_combo.addItem("За ціною (зростанням)", "price_asc")
        self.sort_combo.addItem("За ціною (спаданням)", "price_desc")
        self.sort_combo.addItem("За наявністю", "stock_desc")
        filters_body_layout.addWidget(self.sort_combo)

        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(6)
        buttons_layout.setContentsMargins(0, 6, 0, 4)

        self.apply_btn = QPushButton("Застосувати")
        self.apply_btn.setCursor(Qt.PointingHandCursor)
        self.apply_btn.clicked.connect(self.load_products)
        buttons_layout.addWidget(self.apply_btn)

        self.reset_btn = QPushButton("Скинути фільтри")
        self.reset_btn.setCursor(Qt.PointingHandCursor)
        self.reset_btn.clicked.connect(self.reset_filters)
        buttons_layout.addWidget(self.reset_btn)

        filters_body_layout.addLayout(buttons_layout)
        filters_body_layout.addStretch()

        scroll_area.setWidget(scroll_content)
        sidebar_layout.addWidget(scroll_area, stretch=1)

        # БЛОК: Контакти внизу бічної панелі
        contacts_frame = QFrame()
        contacts_frame.setFrameShape(QFrame.StyledPanel)
        contacts_layout = QVBoxLayout(contacts_frame)
        contacts_layout.setContentsMargins(8, 8, 8, 8)
        contacts_layout.setSpacing(3)

        contacts_layout.addWidget(QLabel("<b>Контакти</b>"))
        contacts_layout.addWidget(QLabel("📞 Телефон: +38 (067) 123-45-67"))
        contacts_layout.addWidget(QLabel("✉ Email: support@pcshop.ua"))
        contacts_layout.addWidget(QLabel("📍 Адреса: м. Київ, вул. Хрещатик, 22"))
        contacts_layout.addWidget(QLabel("Instagram: @pcshop_ua"))
        contacts_layout.addWidget(QLabel("Telegram: @pcshop_support"))

        sidebar_layout.addWidget(contacts_frame)
        root_layout.addWidget(self.sidebar_container)

        # 2. ОСНОВНА ОБЛАСТЬ КАТАЛОГУ
        main_content = QWidget()
        main_layout = QVBoxLayout(main_content)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(10)

        # Верхня панель: [☰ зліва] --- [Пошук по центру] --- [Збільшений Кошик справа]
        top_bar = QHBoxLayout()

        self.menu_btn = QPushButton("☰")
        self.menu_btn.setFixedSize(38, 36)
        self.menu_btn.setCursor(Qt.PointingHandCursor)
        self.menu_btn.setToolTip("Відкрити / закрити фільтри")
        self.menu_btn.clicked.connect(self.toggle_sidebar)
        top_bar.addWidget(self.menu_btn)

        top_bar.addStretch(1)

        search_lbl = QLabel("Пошук:")
        search_lbl_font = search_lbl.font()
        search_lbl_font.setPointSize(search_lbl_font.pointSize() + 1)
        search_lbl.setFont(search_lbl_font)
        top_bar.addWidget(search_lbl)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Назва товару або бренд...")
        self.search_input.setMinimumWidth(340)
        self.search_input.setMaximumWidth(460)
        self.search_input.setFixedHeight(36)
        search_font = self.search_input.font()
        search_font.setPointSize(search_font.pointSize() + 1)
        self.search_input.setFont(search_font)
        self.search_input.textChanged.connect(self.load_products)
        top_bar.addWidget(self.search_input)

        top_bar.addStretch(1)

        self.cart_btn = QPushButton("🛒 Кошик (0)")
        self.cart_btn.setMinimumSize(150, 40)
        cart_font = self.cart_btn.font()
        cart_font.setPointSize(cart_font.pointSize() + 1)
        cart_font.setBold(True)
        self.cart_btn.setFont(cart_font)
        self.cart_btn.setCursor(Qt.PointingHandCursor)
        self.cart_btn.clicked.connect(self.open_cart)
        top_bar.addWidget(self.cart_btn)

        main_layout.addLayout(top_bar)

        # Область прокрутки для карток товарів
        self.cards_scroll = QScrollArea()
        self.cards_scroll.setWidgetResizable(True)
        self.cards_scroll.setFrameShape(QFrame.NoFrame)

        self.cards_container = QWidget()
        self.cards_grid = QGridLayout(self.cards_container)
        self.cards_grid.setContentsMargins(8, 8, 8, 8)
        self.cards_grid.setSpacing(10)
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
        self.sidebar_container.setVisible(not self.sidebar_container.isVisible())
        self.render_product_cards()

    def close_sidebar(self):
        self.sidebar_container.setVisible(False)
        self.render_product_cards()

    def load_categories(self):
        for cb in self.category_checkboxes:
            self.categories_box.removeWidget(cb)
            cb.deleteLater()
        self.category_checkboxes.clear()

        categories = self.db.get_all_categories()
        for cat in categories:
            cb = QCheckBox(cat.name)
            cb.setProperty("category_id", cat.category_id)
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
    """Головне вікно Клієнта з трьома основними розділами"""
    def __init__(self, db_manager=None, client_id=None):
        super().__init__()
        self.db = db_manager or DatabaseManager()
        self.client_id = client_id if client_id is not None else 1
        self.db.ensure_client_profile(self.client_id)

        self.setWindowTitle("Магазин комп'ютерної техніки — Клієнт")
        self.resize(1120, 720)

        self.tabs = QTabWidget()
        self.tabs.setTabBar(MainTabBar())
        tab_font = self.tabs.tabBar().font()
        tab_font.setPointSize(tab_font.pointSize() + 1)
        self.tabs.tabBar().setFont(tab_font)
        self.setCentralWidget(self.tabs)

        # Лише три основні розділи головного вікна:
        self.catalog_widget = ClientCatalogWidget(self.db, self.get_active_client_id)
        self.favorites_widget = FavoritesTab(self.db, self.get_active_client_id)
        self.profile_widget = PersonalAccountWidget(
            db_manager=self.db,
            get_client_id_func=self.get_active_client_id
        )

        self.tabs.addTab(self.catalog_widget, "Каталог товарів")
        self.tabs.addTab(self.favorites_widget, "Обране")
        self.tabs.addTab(self.profile_widget, "Особистий кабінет")

        self.catalog_widget.favorites_changed.connect(self.favorites_widget.load_favorites)
        self.favorites_widget.favorite_removed.connect(lambda _: self.catalog_widget.sync_card_hearts())
        self.favorites_widget.open_product_requested.connect(self.open_product_from_favorites)

        self.tabs.currentChanged.connect(self.on_tab_change)

    def get_active_client_id(self) -> int:
        return self.client_id if self.client_id is not None else 1

    def open_product_from_favorites(self, product_id: int):
        self.tabs.setCurrentIndex(0)
        self.catalog_widget.open_product_detail(
            product_id,
            return_callback=lambda: self.tabs.setCurrentIndex(1)
        )

    def set_client_id(self, client_id):
        self.client_id = client_id
        self.db.ensure_client_profile(self.client_id)
        self.favorites_widget.load_favorites()
        self.catalog_widget.sync_card_hearts()
        self.profile_widget.refresh_data()

    def on_tab_change(self, index):
        if index == 0:
            self.catalog_widget.sync_card_hearts()
        elif index == 1:
            self.favorites_widget.load_favorites()
        elif index == 2:
            self.profile_widget.refresh_data()
            