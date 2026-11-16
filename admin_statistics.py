from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QFrame, QDialog, QMessageBox, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal
from catalog_tab import ProductDialog
from admin_products import get_sqlite_connection, get_table_columns, ensure_suppliers_schema


class StatsAdminTab(QWidget):
    """
    Вкладка статистики на основі реальних даних SQLite:
    - Загальна кількість замовлень
    - Загальна виручка
    - Кількість проданих товарів
    - Середній чек
    - Найпопулярніші товари
    - Товари з малим залишком на складі
    """
    stock_updated = pyqtSignal()
    LOW_STOCK_THRESHOLD = 5

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.init_ui()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 10, 12, 10)
        root_layout.setSpacing(10)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("<b>Аналітика та статистика роботи інтернет-магазину</b>"))
        top_bar.addStretch()

        refresh_btn = QPushButton("Оновити статистику")
        refresh_btn.clicked.connect(self.refresh_stats)
        top_bar.addWidget(refresh_btn)
        root_layout.addLayout(top_bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 6, 0)
        content_layout.setSpacing(12)

        kpi_box = QGroupBox("Основні показники продажів")
        kpi_layout = QHBoxLayout(kpi_box)
        kpi_layout.setSpacing(10)

        self.total_orders_val, self.orders_sub_lbl = self._create_kpi_card(
            kpi_layout, "Загальна кількість замовлень", "0", "—"
        )
        self.total_revenue_val, self.revenue_sub_lbl = self._create_kpi_card(
            kpi_layout, "Загальна виручка", "0.00 грн", "—"
        )
        self.sold_items_val, self.sold_sub_lbl = self._create_kpi_card(
            kpi_layout, "Кількість проданих товарів", "0 шт.", "—"
        )
        self.avg_check_val, self.avg_sub_lbl = self._create_kpi_card(
            kpi_layout, "Середній чек", "0.00 грн", "—"
        )

        content_layout.addWidget(kpi_box)

        popular_box = QGroupBox("Найпопулярніші товари")
        pop_layout = QVBoxLayout(popular_box)

        self.popular_table = QTableWidget()
        self.popular_table.setColumnCount(6)
        self.popular_table.setHorizontalHeaderLabels([
            "Місце", "Назва товару", "Бренд", "Категорія", "Продано (шт.)", "Сума продажів (грн)"
        ])
        self.popular_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.popular_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.popular_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.popular_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.popular_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.popular_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.popular_table.verticalHeader().setVisible(False)
        self.popular_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.popular_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.popular_table.setMinimumHeight(210)
        pop_layout.addWidget(self.popular_table)

        content_layout.addWidget(popular_box)

        low_stock_box = QGroupBox(f"Товари, які мають малий залишок на складі (≤ {self.LOW_STOCK_THRESHOLD} шт.)")
        low_layout = QVBoxLayout(low_stock_box)

        self.low_stock_table = QTableWidget()
        self.low_stock_table.setColumnCount(7)
        self.low_stock_table.setHorizontalHeaderLabels([
            "ID", "Назва товару", "Бренд", "Категорія", "Постачальник", "Залишок", "Стан"
        ])
        self.low_stock_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.low_stock_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.low_stock_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.low_stock_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.low_stock_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.low_stock_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.low_stock_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.low_stock_table.verticalHeader().setVisible(False)
        self.low_stock_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.low_stock_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.low_stock_table.setMinimumHeight(210)
        low_layout.addWidget(self.low_stock_table)

        low_actions = QHBoxLayout()
        self.restock_btn = QPushButton("Редагувати / поповнити залишок обраного товару")
        self.restock_btn.clicked.connect(self.edit_low_stock_product)
        low_actions.addWidget(self.restock_btn)
        low_actions.addStretch()
        low_layout.addLayout(low_actions)

        content_layout.addWidget(low_stock_box)

        scroll.setWidget(content)
        root_layout.addWidget(scroll)
        self.refresh_stats()

    def _create_kpi_card(self, parent_layout, title: str, initial_val: str, sub_text: str):
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        vbox = QVBoxLayout(frame)
        vbox.setContentsMargins(10, 8, 10, 8)
        vbox.setSpacing(4)

        vbox.addWidget(QLabel(title))
        val_lbl = QLabel(f"<b>{initial_val}</b>")
        f = val_lbl.font()
        f.setPointSize(f.pointSize() + 2)
        val_lbl.setFont(f)
        vbox.addWidget(val_lbl)

        sub_lbl = QLabel(sub_text)
        sub_lbl.setWordWrap(True)
        vbox.addWidget(sub_lbl)

        parent_layout.addWidget(frame, stretch=1)
        return val_lbl, sub_lbl

    def refresh_stats(self):
        conn = get_sqlite_connection(self.db)
        ensure_suppliers_schema(conn)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) AS total_cnt,
                SUM(CASE WHEN LOWER(TRIM(status)) = 'доставлено' THEN 1 ELSE 0 END) AS delivered_cnt,
                SUM(CASE WHEN LOWER(TRIM(status)) = 'скасовано' THEN 1 ELSE 0 END) AS cancelled_cnt,
                SUM(CASE WHEN LOWER(TRIM(status)) NOT IN ('доставлено', 'скасовано') THEN 1 ELSE 0 END) AS active_cnt
            FROM orders
        """)
        total_orders, delivered_cnt, cancelled_cnt, active_cnt = cursor.fetchone()
        total_orders = int(total_orders or 0)
        delivered_cnt = int(delivered_cnt or 0)
        cancelled_cnt = int(cancelled_cnt or 0)
        active_cnt = int(active_cnt or 0)

        self.total_orders_val.setText(f"<b>{total_orders}</b>")
        self.orders_sub_lbl.setText(
            f"Доставлено: {delivered_cnt} | В роботі: {active_cnt} | Скасовано: {cancelled_cnt}"
        )

        cursor.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN LOWER(TRIM(status)) != 'скасовано' THEN total_amount ELSE 0 END), 0.0),
                COALESCE(SUM(CASE WHEN LOWER(TRIM(status)) = 'доставлено' THEN total_amount ELSE 0 END), 0.0),
                COALESCE(AVG(CASE WHEN LOWER(TRIM(status)) != 'скасовано' THEN total_amount END), 0.0)
            FROM orders
        """)
        total_rev, delivered_rev, avg_check = cursor.fetchone()
        total_rev = float(total_rev or 0.0)
        delivered_rev = float(delivered_rev or 0.0)
        avg_check = float(avg_check or 0.0)

        self.total_revenue_val.setText(f"<b>{total_rev:.2f} грн</b>")
        self.revenue_sub_lbl.setText(f"Підтверджено (доставлено): {delivered_rev:.2f} грн")

        self.avg_check_val.setText(f"<b>{avg_check:.2f} грн</b>")
        valid_orders_count = total_orders - cancelled_cnt
        self.avg_sub_lbl.setText(f"Розраховано за {valid_orders_count} активними/виконаними замовленнями")

        cursor.execute("""
            SELECT
                COALESCE(SUM(oi.quantity), 0),
                COUNT(DISTINCT oi.product_id)
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            WHERE LOWER(TRIM(o.status)) != 'скасовано'
        """)
        sold_units, unique_sold_products = cursor.fetchone()
        sold_units = int(sold_units or 0)
        unique_sold_products = int(unique_sold_products or 0)

        self.sold_items_val.setText(f"<b>{sold_units} шт.</b>")
        self.sold_sub_lbl.setText(f"Унікальних позицій продано: {unique_sold_products}")

        oi_cols = get_table_columns(conn, "order_items")
        price_col = "price_per_unit" if "price_per_unit" in oi_cols else ("price" if "price" in oi_cols else "p.price")
        price_expr = f"oi.{price_col}" if not price_col.startswith("p.") else price_col

        cursor.execute(f"""
            SELECT
                p.title,
                COALESCE(p.brand, ''),
                COALESCE(c.name, 'Без категорії'),
                SUM(oi.quantity) AS sold_qty,
                SUM(oi.quantity * {price_expr}) AS item_revenue
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            JOIN products p ON oi.product_id = p.product_id
            LEFT JOIN categories c ON p.category_id = c.category_id
            WHERE LOWER(TRIM(o.status)) != 'скасовано'
            GROUP BY p.product_id
            ORDER BY sold_qty DESC, item_revenue DESC
            LIMIT 10
        """)
        popular_rows = cursor.fetchall()

        self.popular_table.setRowCount(len(popular_rows))
        for idx, row in enumerate(popular_rows):
            title, brand, cat_name, sold_qty, item_rev = row
            self.popular_table.setItem(idx, 0, QTableWidgetItem(f"#{idx + 1}"))
            self.popular_table.setItem(idx, 1, QTableWidgetItem(str(title)))
            self.popular_table.setItem(idx, 2, QTableWidgetItem(str(brand)))
            self.popular_table.setItem(idx, 3, QTableWidgetItem(str(cat_name)))
            self.popular_table.setItem(idx, 4, QTableWidgetItem(f"{int(sold_qty)} шт."))
            self.popular_table.setItem(idx, 5, QTableWidgetItem(f"{float(item_rev):.2f} грн"))

        prod_cols = get_table_columns(conn, "products")
        if "supplier_id" in prod_cols:
            low_sql = """
                SELECT
                    p.product_id,
                    p.title,
                    COALESCE(p.brand, ''),
                    COALESCE(c.name, 'Без категорії'),
                    COALESCE(s.name, 'Не вказано'),
                    p.stock_quantity
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.category_id
                LEFT JOIN suppliers s ON p.supplier_id = s.supplier_id
                WHERE p.stock_quantity <= ?
                ORDER BY p.stock_quantity ASC, p.title ASC
            """
        else:
            low_sql = """
                SELECT
                    p.product_id,
                    p.title,
                    COALESCE(p.brand, ''),
                    COALESCE(c.name, 'Без категорії'),
                    'Не вказано',
                    p.stock_quantity
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.category_id
                WHERE p.stock_quantity <= ?
                ORDER BY p.stock_quantity ASC, p.title ASC
            """

        cursor.execute(low_sql, (self.LOW_STOCK_THRESHOLD,))
        low_rows = cursor.fetchall()

        self.low_stock_table.setRowCount(len(low_rows))
        for idx, row in enumerate(low_rows):
            pid, title, brand, cat_name, sup_name, stock = row
            stock_int = int(stock)
            status_txt = "Немає в наявності" if stock_int == 0 else "Закінчується"

            id_item = QTableWidgetItem(str(pid))
            id_item.setData(Qt.UserRole, pid)

            self.low_stock_table.setItem(idx, 0, id_item)
            self.low_stock_table.setItem(idx, 1, QTableWidgetItem(str(title)))
            self.low_stock_table.setItem(idx, 2, QTableWidgetItem(str(brand)))
            self.low_stock_table.setItem(idx, 3, QTableWidgetItem(str(cat_name)))
            self.low_stock_table.setItem(idx, 4, QTableWidgetItem(str(sup_name)))
            self.low_stock_table.setItem(idx, 5, QTableWidgetItem(f"{stock_int} шт."))
            self.low_stock_table.setItem(idx, 6, QTableWidgetItem(status_txt))

    def edit_low_stock_product(self):
        row = self.low_stock_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Увага", "Оберіть товар із таблиці малого залишку.")
            return

        pid = self.low_stock_table.item(row, 0).data(Qt.UserRole)
        prod = self.db.get_product_by_id(pid)
        if not prod:
            return

        dialog = ProductDialog(self.db, product=prod, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            updated_prod = dialog.get_product_data()
            self.db.update_product(updated_prod)
            self.refresh_stats()
            self.stock_updated.emit()
            QMessageBox.information(self, "Успіх", "Залишок та дані товару оновлено!")
            