import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QPushButton, QTabWidget
)
from PyQt5.QtCore import Qt

from db_manager import DatabaseManager
from style_manager import apply_theme
from admin_products import ProductsAdminTab, get_sqlite_connection
from admin_orders import OrdersAdminTab
from admin_suppliers import SuppliersAdminTab
from admin_statistics import StatsAdminTab


class AdminWindow(QMainWindow):
    """Головне вікно панелі адміністратора з фірмовою шапкою, оглядом, 4 вкладками та футером"""
    def __init__(self, db_manager=None, parent=None):
        super().__init__(parent)
        self.db = db_manager or DatabaseManager()
        self.setWindowTitle("TechStore — Панель адміністратора магазину комп'ютерної техніки")
        self.resize(1240, 820)
        self.init_ui()
        apply_theme(self, "admin")
        self.refresh_overview_banner()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. ФІРМОВА ВЕРХНЯ ШАПКА МАГАЗИНУ
        top_header = QFrame()
        top_header.setObjectName("storeTopHeader")
        header_layout = QHBoxLayout(top_header)
        header_layout.setContentsMargins(18, 12, 18, 12)
        header_layout.setSpacing(12)

        brand_col = QVBoxLayout()
        brand_col.setSpacing(2)
        brand_title = QLabel("TECHSTORE  |  Панель керування магазином")
        brand_title.setObjectName("storeBrandTitle")
        brand_col.addWidget(brand_title)

        brand_sub = QLabel("Адміністрування каталогу, замовлень клієнтів, постачальників та фінансової статистики")
        brand_sub.setObjectName("storeBrandSubtitle")
        brand_col.addWidget(brand_sub)
        header_layout.addLayout(brand_col)

        header_layout.addStretch()

        role_badge = QLabel("Режим: Адміністратор")
        role_badge.setObjectName("storeRoleBadge")
        header_layout.addWidget(role_badge)

        self.refresh_all_btn = QPushButton("Оновити всі дані")
        self.refresh_all_btn.setProperty("variant", "header")
        self.refresh_all_btn.clicked.connect(self.refresh_all)
        header_layout.addWidget(self.refresh_all_btn)

        root_layout.addWidget(top_header)

        # 2. ОСНОВНА РОБОЧА ОБЛАСТЬ
        workspace = QWidget()
        main_layout = QVBoxLayout(workspace)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(12)

        # Інформаційна панель поточного стану магазину
        overview_strip = QFrame()
        overview_strip.setObjectName("adminOverviewStrip")
        overview_layout = QHBoxLayout(overview_strip)
        overview_layout.setContentsMargins(14, 10, 14, 10)
        overview_layout.setSpacing(12)

        self.new_orders_info_lbl = self._create_metric_chip(
            overview_layout, "Нові заявки (очікують):", "0"
        )
        self.active_orders_info_lbl = self._create_metric_chip(
            overview_layout, "Замовлень в роботі:", "0"
        )
        self.products_info_lbl = self._create_metric_chip(
            overview_layout, "Товарів у каталозі:", "0 (малий залишок: 0)"
        )

        overview_layout.addStretch()

        self.go_to_orders_btn = QPushButton("Перейти до нових замовлень")
        self.go_to_orders_btn.setProperty("variant", "primary")
        self.go_to_orders_btn.clicked.connect(self.open_orders_tab)
        overview_layout.addWidget(self.go_to_orders_btn)

        main_layout.addWidget(overview_strip)

        # Чотири основні вкладки панелі адміністратора
        self.tabs = QTabWidget()

        self.products_tab = ProductsAdminTab(self.db)
        self.orders_tab = OrdersAdminTab(self.db)
        self.suppliers_tab = SuppliersAdminTab(self.db)
        self.stats_tab = StatsAdminTab(self.db)

        self.tabs.addTab(self.products_tab, "  Товари  ")
        self.tabs.addTab(self.orders_tab, "  Замовлення  ")
        self.tabs.addTab(self.suppliers_tab, "  Постачальники  ")
        self.tabs.addTab(self.stats_tab, "  Статистика  ")

        self.products_tab.data_changed.connect(self._on_products_or_suppliers_changed)
        self.suppliers_tab.suppliers_changed.connect(self._on_products_or_suppliers_changed)
        self.orders_tab.orders_changed.connect(self._on_orders_changed)
        self.stats_tab.stock_updated.connect(self._on_stock_updated)
        self.tabs.currentChanged.connect(self._on_tab_changed)

        main_layout.addWidget(self.tabs, stretch=1)
        root_layout.addWidget(workspace, stretch=1)

        # 3. НИЖНЯ ПАНЕЛЬ КОНТАКТІВ ТА РЕКВІЗИТІВ МАГАЗИНУ
        footer = self._build_store_footer()
        root_layout.addWidget(footer)

    def _create_metric_chip(self, parent_layout, caption: str, initial_value: str) -> QLabel:
        chip = QFrame()
        chip.setObjectName("overviewMetricChip")
        chip_layout = QHBoxLayout(chip)
        chip_layout.setContentsMargins(12, 6, 12, 6)
        chip_layout.setSpacing(6)

        cap_lbl = QLabel(caption)
        cap_lbl.setProperty("role", "muted")
        chip_layout.addWidget(cap_lbl)

        val_lbl = QLabel(f"<b>{initial_value}</b>")
        chip_layout.addWidget(val_lbl)

        parent_layout.addWidget(chip)
        return val_lbl

    def _build_store_footer(self) -> QFrame:
        footer = QFrame()
        footer.setObjectName("storeFooter")
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(18, 10, 18, 10)
        layout.setSpacing(18)

        brand_lbl = QLabel("TECHSTORE")
        brand_lbl.setObjectName("footerBrandTitle")
        layout.addWidget(brand_lbl)

        self._add_footer_contact(layout, "Гаряча лінія магазину", "+380 (67) 555-01-99  |  +380 (44) 234-56-78")
        self._add_footer_contact(layout, "Графік роботи", "Пн–Пт: 09:00–20:00, Сб–Нд: 10:00–18:00")
        self._add_footer_contact(layout, "Точка видачі та офіс", "м. Київ, вул. Політехнічна, 14-Б")
        self._add_footer_contact(layout, "Електронна пошта", "support@techstore.ua")

        layout.addStretch()
        return footer

    def _add_footer_contact(self, parent_layout, title: str, value: str):
        divider = QFrame()
        divider.setObjectName("footerDivider")
        divider.setFrameShape(QFrame.VLine)
        parent_layout.addWidget(divider)

        col = QVBoxLayout()
        col.setSpacing(1)
        t_lbl = QLabel(title)
        t_lbl.setObjectName("footerItemTitle")
        v_lbl = QLabel(value)
        v_lbl.setObjectName("footerItemValue")
        col.addWidget(t_lbl)
        col.addWidget(v_lbl)
        parent_layout.addLayout(col)

    def refresh_overview_banner(self):
        conn = get_sqlite_connection(self.db)
        cursor = conn.cursor()

        cursor.execute("SELECT COALESCE(status, '') FROM orders")
        statuses = [str(row[0]).strip().lower() for row in cursor.fetchall()]

        new_cnt = sum(1 for st in statuses if st == "нове")
        in_work_cnt = sum(1 for st in statuses if st in ("в обробці", "відправлено"))

        cursor.execute("""
            SELECT
                COUNT(*),
                SUM(CASE WHEN stock_quantity <= 5 THEN 1 ELSE 0 END)
            FROM products
        """)
        total_prods, low_prods = cursor.fetchone()
        total_prods = int(total_prods or 0)
        low_prods = int(low_prods or 0)

        self.new_orders_info_lbl.setText(f"<b>{new_cnt}</b>")
        self.active_orders_info_lbl.setText(f"<b>{in_work_cnt}</b>")
        self.products_info_lbl.setText(f"<b>{total_prods}</b> (малий залишок: {low_prods})")

    def open_orders_tab(self):
        self.tabs.setCurrentWidget(self.orders_tab)
        self.orders_tab.load_orders()

    def _on_products_or_suppliers_changed(self):
        self.products_tab.load_products()
        self.stats_tab.refresh_stats()
        self.refresh_overview_banner()

    def _on_orders_changed(self):
        self.stats_tab.refresh_stats()
        self.refresh_overview_banner()

    def _on_stock_updated(self):
        self.products_tab.load_products()
        self.suppliers_tab.load_suppliers()
        self.refresh_overview_banner()

    def _on_tab_changed(self, index: int):
        self.refresh_overview_banner()
        if index == 0:
            self.products_tab.load_products()
        elif index == 1:
            self.orders_tab.load_orders()
        elif index == 2:
            self.suppliers_tab.load_suppliers()
        elif index == 3:
            self.stats_tab.refresh_stats()

    def refresh_all(self):
        self.refresh_overview_banner()
        self.products_tab.load_products()
        self.orders_tab.load_orders()
        self.suppliers_tab.load_suppliers()
        self.stats_tab.refresh_stats()

    refresh_data = refresh_all


def main():
    app = QApplication(sys.argv)
    apply_theme(app, "admin")
    db = DatabaseManager()
    window = AdminWindow(db)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
    