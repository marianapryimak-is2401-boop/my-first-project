import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QGroupBox, QTabWidget
)

from db_manager import DatabaseManager
from admin_products import ProductsAdminTab, get_sqlite_connection
from admin_orders import OrdersAdminTab
from admin_suppliers import SuppliersAdminTab
from admin_statistics import StatsAdminTab


class AdminWindow(QMainWindow):
    """Головне вікно панелі адміністратора з 4 вкладками та інформаційним блоком"""
    def __init__(self, db_manager=None, parent=None):
        super().__init__(parent)
        self.db = db_manager or DatabaseManager()
        self.setWindowTitle("Магазин комп'ютерної техніки — Панель адміністратора")
        self.resize(1180, 760)
        self.init_ui()
        self.refresh_overview_banner()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(10)

        overview_box = QGroupBox("Поточний стан роботи магазину")
        overview_layout = QHBoxLayout(overview_box)
        overview_layout.setSpacing(16)

        self.new_orders_info_lbl = QLabel("<b>Нових замовлень очікують обробки: 0</b>")
        overview_layout.addWidget(self.new_orders_info_lbl)

        self.active_orders_info_lbl = QLabel("Замовлень в роботі: 0")
        overview_layout.addWidget(self.active_orders_info_lbl)

        self.products_info_lbl = QLabel("Товарів у каталозі: 0 (малий залишок: 0)")
        overview_layout.addWidget(self.products_info_lbl)

        overview_layout.addStretch()

        self.go_to_orders_btn = QPushButton("Перейти до нових замовлень")
        self.go_to_orders_btn.clicked.connect(self.open_orders_tab)
        overview_layout.addWidget(self.go_to_orders_btn)

        self.refresh_all_btn = QPushButton("Оновити")
        self.refresh_all_btn.clicked.connect(self.refresh_all)
        overview_layout.addWidget(self.refresh_all_btn)

        main_layout.addWidget(overview_box)

        self.tabs = QTabWidget()

        self.products_tab = ProductsAdminTab(self.db)
        self.orders_tab = OrdersAdminTab(self.db)
        self.suppliers_tab = SuppliersAdminTab(self.db)
        self.stats_tab = StatsAdminTab(self.db)

        self.tabs.addTab(self.products_tab, "Товари")
        self.tabs.addTab(self.orders_tab, "Замовлення")
        self.tabs.addTab(self.suppliers_tab, "Постачальники")
        self.tabs.addTab(self.stats_tab, "Статистика")

        self.products_tab.data_changed.connect(self._on_products_or_suppliers_changed)
        self.suppliers_tab.suppliers_changed.connect(self._on_products_or_suppliers_changed)
        self.orders_tab.orders_changed.connect(self._on_orders_changed)
        self.stats_tab.stock_updated.connect(self._on_stock_updated)
        self.tabs.currentChanged.connect(self._on_tab_changed)

        main_layout.addWidget(self.tabs)

    def refresh_overview_banner(self):
        conn = get_sqlite_connection(self.db)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                SUM(CASE WHEN LOWER(TRIM(status)) = 'нове' THEN 1 ELSE 0 END),
                SUM(CASE WHEN LOWER(TRIM(status)) IN ('в обробці', 'відправлено') THEN 1 ELSE 0 END)
            FROM orders
        """)
        new_cnt, in_work_cnt = cursor.fetchone()
        new_cnt = int(new_cnt or 0)
        in_work_cnt = int(in_work_cnt or 0)

        cursor.execute("""
            SELECT
                COUNT(*),
                SUM(CASE WHEN stock_quantity <= 5 THEN 1 ELSE 0 END)
            FROM products
        """)
        total_prods, low_prods = cursor.fetchone()
        total_prods = int(total_prods or 0)
        low_prods = int(low_prods or 0)

        self.new_orders_info_lbl.setText(f"<b>Нових замовлень очікують обробки: {new_cnt}</b>")
        self.active_orders_info_lbl.setText(f"Замовлень в роботі: {in_work_cnt}")
        self.products_info_lbl.setText(f"Товарів у каталозі: {total_prods} (малий залишок: {low_prods})")

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
    db = DatabaseManager()
    window = AdminWindow(db)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
    