import os
import inspect
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QDialog, QMessageBox, QSplitter
)
from PyQt5.QtCore import Qt, pyqtSignal, QUrl
from PyQt5.QtGui import QDesktopServices
from admin_products import get_sqlite_connection, get_table_columns


def award_bonuses_once_on_delivery(db_manager, order_id: int, new_status: str):
    """
    Змінює статус замовлення та гарантує одноразове нарахування бонусів покупцю
    виключно після переходу замовлення у статус «Доставлено».
    """
    conn = get_sqlite_connection(db_manager)
    cursor = conn.cursor()
    order_cols = get_table_columns(conn, "orders")

    was_awarded_before = 0
    if "bonus_awarded" in order_cols:
        cursor.execute("SELECT COALESCE(bonus_awarded, 0) FROM orders WHERE order_id = ?", (order_id,))
        row = cursor.fetchone()
        if row:
            was_awarded_before = int(row[0] or 0)

    if hasattr(db_manager, "update_order_status"):
        db_manager.update_order_status(order_id, new_status)
    else:
        cursor.execute("UPDATE orders SET status = ? WHERE order_id = ?", (new_status, order_id))
        conn.commit()

    if new_status.strip().lower() != "доставлено":
        return

    select_fields = ["client_id", "COALESCE(total_amount, 0)"]
    select_fields.append("COALESCE(bonus_earned, 0)" if "bonus_earned" in order_cols else "0")
    select_fields.append("COALESCE(bonus_awarded, 0)" if "bonus_awarded" in order_cols else "0")

    cursor.execute(
        f"SELECT {', '.join(select_fields)} FROM orders WHERE order_id = ?",
        (order_id,)
    )
    order_row = cursor.fetchone()
    if not order_row:
        return

    client_id, total_amount, bonus_earned, is_awarded_now = order_row
    if was_awarded_before == 1 or int(is_awarded_now or 0) == 1:
        return

    earned = int(bonus_earned) if int(bonus_earned or 0) > 0 else int(float(total_amount or 0) // 100)

    if client_id is not None and earned > 0:
        client_cols = get_table_columns(conn, "clients")
        bonus_col = None
        for candidate in ("bonus_balance", "bonuses", "bonus_points"):
            if candidate in client_cols:
                bonus_col = candidate
                break

        if bonus_col:
            cursor.execute(
                f"UPDATE clients SET {bonus_col} = COALESCE({bonus_col}, 0) + ? WHERE client_id = ?",
                (earned, client_id)
            )

    if "bonus_awarded" in order_cols and "bonus_earned" in order_cols:
        cursor.execute(
            "UPDATE orders SET bonus_awarded = 1, bonus_earned = ? WHERE order_id = ?",
            (earned, order_id)
        )
    elif "bonus_awarded" in order_cols:
        cursor.execute(
            "UPDATE orders SET bonus_awarded = 1 WHERE order_id = ?",
            (order_id,)
        )

    conn.commit()


def open_or_generate_order_receipt(db_manager, order_id: int, parent=None):
    """Відкриває PDF-чек замовлення (або генерує його, якщо файл ще не створено)"""
    order_data = db_manager.get_order_full_info(order_id) if hasattr(db_manager, "get_order_full_info") else None
    if not order_data:
        QMessageBox.warning(parent, "Помилка", f"Не вдалося отримати дані замовлення №{order_id}.")
        return

    receipt_path = order_data.get("receipt_path") or ""
    if receipt_path and os.path.exists(receipt_path):
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(receipt_path)))
        return

    try:
        from receipt_generator import ReceiptGenerator
        from classes import Client, Product

        generator = ReceiptGenerator()
        gen_method = getattr(generator, "generate_receipt", None)
        if callable(gen_method):
            client_obj = Client(
                full_name=order_data.get("client_name", "Покупець"),
                phone=order_data.get("phone", ""),
                email=order_data.get("email", ""),
                address=order_data.get("delivery_address", "")
            )
            cart_pairs = []
            for item in order_data.get("items", []):
                prod = Product(
                    category_id=0,
                    supplier_id=None,
                    title=item.get("title", "Товар"),
                    brand=item.get("brand", ""),
                    price=float(item.get("price_per_unit", 0.0)),
                    stock_quantity=0,
                    description="",
                    product_id=item.get("product_id", 0)
                )
                cart_pairs.append((prod, int(item.get("quantity", 1))))

            sig = inspect.signature(gen_method)
            params = sig.parameters
            kwargs = {}
            if "order_id" in params:
                kwargs["order_id"] = order_id
            if "client" in params:
                kwargs["client"] = client_obj
            elif "client_data" in params:
                kwargs["client_data"] = client_obj
            elif "client_name" in params:
                kwargs["client_name"] = client_obj.full_name
            if "cart_items" in params:
                kwargs["cart_items"] = cart_pairs
            elif "items" in params:
                kwargs["items"] = cart_pairs
            if "total_amount" in params:
                kwargs["total_amount"] = float(order_data.get("total_amount", 0.0))
            if "delivery_method" in params:
                kwargs["delivery_method"] = order_data.get("delivery_method", "")
            if "delivery_address" in params:
                kwargs["delivery_address"] = order_data.get("delivery_address", "")
            if "payment_method" in params:
                kwargs["payment_method"] = order_data.get("payment_method", "")
            if "bonus_used" in params:
                kwargs["bonus_used"] = int(order_data.get("bonus_used", 0))

            generated_path = gen_method(**kwargs)
            if generated_path and os.path.exists(generated_path):
                for method_name in ("update_order_receipt", "set_order_receipt_path", "save_order_receipt"):
                    if hasattr(db_manager, method_name):
                        getattr(db_manager, method_name)(order_id, generated_path)
                        break
                QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(generated_path)))
                return
    except Exception:
        pass

    QMessageBox.information(
        parent,
        "Чек замовлення",
        f"PDF-чек для замовлення №{order_id} не знайдено на диску."
    )


class AdminOrderDetailsDialog(QDialog):
    """Детальний перегляд замовлення для адміністратора зі зміною статусу та чеком"""
    status_updated = pyqtSignal()

    STATUSES = ["Нове", "В обробці", "Відправлено", "Доставлено", "Скасовано"]

    def __init__(self, db_manager, order_id: int, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.order_id = order_id
        self.setWindowTitle(f"Замовлення №{order_id} — Детальна інформація")
        self.resize(720, 560)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        self.header_lbl = QLabel(f"<b>Замовлення №{self.order_id}</b>")
        top_row.addWidget(self.header_lbl)
        top_row.addStretch()

        top_row.addWidget(QLabel("Статус:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(self.STATUSES)
        top_row.addWidget(self.status_combo)

        self.save_status_btn = QPushButton("Зберегти статус")
        self.save_status_btn.clicked.connect(self.save_status)
        top_row.addWidget(self.save_status_btn)

        layout.addLayout(top_row)

        info_box = QGroupBox("Інформація про покупця, доставку та оплату")
        info_grid = QGridLayout(info_box)
        info_grid.setSpacing(6)

        self.date_lbl = QLabel("—")
        self.client_lbl = QLabel("—")
        self.phone_lbl = QLabel("—")
        self.email_lbl = QLabel("—")
        self.delivery_lbl = QLabel("—")
        self.address_lbl = QLabel("—")
        self.address_lbl.setWordWrap(True)
        self.payment_lbl = QLabel("—")
        self.comment_lbl = QLabel("—")
        self.comment_lbl.setWordWrap(True)

        info_grid.addWidget(QLabel("<b>Дата замовлення:</b>"), 0, 0)
        info_grid.addWidget(self.date_lbl, 0, 1)
        info_grid.addWidget(QLabel("<b>Спосіб оплати:</b>"), 0, 2)
        info_grid.addWidget(self.payment_lbl, 0, 3)

        info_grid.addWidget(QLabel("<b>Покупець:</b>"), 1, 0)
        info_grid.addWidget(self.client_lbl, 1, 1)
        info_grid.addWidget(QLabel("<b>Спосіб доставки:</b>"), 1, 2)
        info_grid.addWidget(self.delivery_lbl, 1, 3)

        info_grid.addWidget(QLabel("<b>Телефон:</b>"), 2, 0)
        info_grid.addWidget(self.phone_lbl, 2, 1)
        info_grid.addWidget(QLabel("<b>Email:</b>"), 2, 2)
        info_grid.addWidget(self.email_lbl, 2, 3)

        info_grid.addWidget(QLabel("<b>Адреса доставки:</b>"), 3, 0)
        info_grid.addWidget(self.address_lbl, 3, 1, 1, 3)

        info_grid.addWidget(QLabel("<b>Коментар:</b>"), 4, 0)
        info_grid.addWidget(self.comment_lbl, 4, 1, 1, 3)

        info_grid.setColumnStretch(1, 1)
        info_grid.setColumnStretch(3, 1)

        layout.addWidget(info_box)

        items_box = QGroupBox("Склад замовлення")
        items_layout = QVBoxLayout(items_box)

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(4)
        self.items_table.setHorizontalHeaderLabels(["Назва товару", "Кількість", "Ціна за од.", "Сума"])
        self.items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.items_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.items_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.items_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.items_table.setSelectionMode(QTableWidget.NoSelection)
        items_layout.addWidget(self.items_table)

        layout.addWidget(items_box, stretch=1)

        summary_box = QGroupBox("Фінансовий підсумок")
        sum_layout = QVBoxLayout(summary_box)
        sum_layout.setSpacing(4)

        self.subtotal_lbl = QLabel("Вартість товарів: 0.00 грн")
        self.bonus_used_lbl = QLabel("Використано бонусів: 0 бонусів")
        self.total_lbl = QLabel("<b>Загальна сума замовлення: 0.00 грн</b>")
        self.bonus_award_lbl = QLabel("Бонуси за замовлення: —")

        sum_layout.addWidget(self.subtotal_lbl)
        sum_layout.addWidget(self.bonus_used_lbl)
        sum_layout.addWidget(self.total_lbl)
        sum_layout.addWidget(self.bonus_award_lbl)

        layout.addWidget(summary_box)

        bottom_row = QHBoxLayout()
        self.receipt_btn = QPushButton("Переглянути чек (PDF)")
        self.receipt_btn.clicked.connect(
            lambda: open_or_generate_order_receipt(self.db, self.order_id, parent=self)
        )
        bottom_row.addWidget(self.receipt_btn)

        bottom_row.addStretch()

        close_btn = QPushButton("Закрити")
        close_btn.clicked.connect(self.accept)
        bottom_row.addWidget(close_btn)

        layout.addLayout(bottom_row)

    def load_data(self):
        order_data = self.db.get_order_full_info(self.order_id) if hasattr(self.db, "get_order_full_info") else None
        if not order_data:
            QMessageBox.warning(self, "Помилка", "Не вдалося завантажити інформацію про замовлення.")
            return

        status = order_data.get("status", "Нове")
        idx = self.status_combo.findText(status)
        if idx >= 0:
            self.status_combo.setCurrentIndex(idx)

        self.date_lbl.setText(str(order_data.get("order_date", "—")))
        self.client_lbl.setText(str(order_data.get("client_name", "—")))
        self.phone_lbl.setText(str(order_data.get("phone", "—")))
        self.email_lbl.setText(str(order_data.get("email") or "Не вказано"))
        self.delivery_lbl.setText(str(order_data.get("delivery_method", "—")))
        self.address_lbl.setText(str(order_data.get("delivery_address") or "Не вказано"))
        self.payment_lbl.setText(str(order_data.get("payment_method", "—")))
        self.comment_lbl.setText(str(order_data.get("comment") or "Без коментаря"))

        items = order_data.get("items", [])
        self.items_table.setRowCount(len(items))
        subtotal = 0.0
        for row, item in enumerate(items):
            qty = int(item.get("quantity", 0))
            price = float(item.get("price_per_unit", 0.0))
            line_total = qty * price
            subtotal += line_total

            self.items_table.setItem(row, 0, QTableWidgetItem(str(item.get("title", ""))))
            self.items_table.setItem(row, 1, QTableWidgetItem(f"{qty} шт."))
            self.items_table.setItem(row, 2, QTableWidgetItem(f"{price:.2f} грн"))
            self.items_table.setItem(row, 3, QTableWidgetItem(f"{line_total:.2f} грн"))

        bonus_used = int(order_data.get("bonus_used", 0))
        total_amount = float(order_data.get("total_amount", 0.0))
        bonus_earned = int(order_data.get("bonus_earned", 0))
        bonus_awarded = int(order_data.get("bonus_awarded", 0))
        expected_bonus = bonus_earned if bonus_earned > 0 else int(total_amount // 100)

        self.subtotal_lbl.setText(f"Вартість товарів: {subtotal:.2f} грн")
        self.bonus_used_lbl.setText(f"Використано бонусів: {bonus_used} бонусів (-{bonus_used:.2f} грн)")
        self.total_lbl.setText(f"<b>Загальна сума замовлення: {total_amount:.2f} грн</b>")

        if status.strip().lower() == "доставлено" and bonus_awarded:
            self.bonus_award_lbl.setText(f"Бонуси покупцю нараховано: <b>+{expected_bonus} бонусів</b>")
        elif status.strip().lower() == "скасовано":
            self.bonus_award_lbl.setText("Замовлення скасовано — бонуси не нараховуються.")
        else:
            self.bonus_award_lbl.setText(
                f"Очікується нарахування після статусу «Доставлено»: +{expected_bonus} бонусів"
            )

    def save_status(self):
        new_status = self.status_combo.currentText()
        award_bonuses_once_on_delivery(self.db, self.order_id, new_status)
        self.load_data()
        self.status_updated.emit()
        QMessageBox.information(
            self,
            "Статус оновлено",
            f"Статус замовлення №{self.order_id} змінено на «{new_status}»."
        )


class OrdersAdminTab(QWidget):
    """
    Вкладка керування замовленнями:
    - Верхній блок: нові замовлення, які очікують підтвердження
    - Нижній блок: усі замовлення (в обробці, відправлені, доставлені, скасовані)
    """
    orders_changed = pyqtSignal()

    ALL_STATUSES = ["Нове", "В обробці", "Відправлено", "Доставлено", "Скасовано"]

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        splitter = QSplitter(Qt.Vertical)

        # 1. БЛОК НОВИХ ЗАМОВЛЕНЬ, ЯКІ ОЧІКУЮТЬ ПІДТВЕРДЖЕННЯ
        self.new_orders_box = QGroupBox("Нові замовлення, які очікують підтвердження (0)")
        new_layout = QVBoxLayout(self.new_orders_box)
        new_layout.setSpacing(8)

        self.new_orders_table = QTableWidget()
        self.new_orders_table.setColumnCount(9)
        self.new_orders_table.setHorizontalHeaderLabels([
            "№", "Дата", "Покупець", "Телефон", "Товари",
            "К-сть", "Сума (грн)", "Доставка", "Оплата"
        ])
        self._configure_orders_table_headers(self.new_orders_table, has_status_col=False)
        self.new_orders_table.cellDoubleClicked.connect(
            lambda r, _c: self._open_details_from_table(self.new_orders_table, r)
        )
        new_layout.addWidget(self.new_orders_table)

        new_actions = QHBoxLayout()
        self.accept_order_btn = QPushButton("Прийняти замовлення в обробку")
        self.accept_order_btn.clicked.connect(self.accept_selected_new_order)
        new_actions.addWidget(self.accept_order_btn)

        self.new_details_btn = QPushButton("Деталі замовлення")
        self.new_details_btn.clicked.connect(
            lambda: self._open_details_from_table(self.new_orders_table, self.new_orders_table.currentRow())
        )
        new_actions.addWidget(self.new_details_btn)

        self.new_receipt_btn = QPushButton("Переглянути чек")
        self.new_receipt_btn.clicked.connect(
            lambda: self._open_receipt_from_table(self.new_orders_table, self.new_orders_table.currentRow())
        )
        new_actions.addWidget(self.new_receipt_btn)

        new_actions.addStretch()

        self.cancel_new_btn = QPushButton("Скасувати замовлення")
        self.cancel_new_btn.clicked.connect(self.cancel_selected_new_order)
        new_actions.addWidget(self.cancel_new_btn)

        new_layout.addLayout(new_actions)
        splitter.addWidget(self.new_orders_box)

        # 2. БЛОК УСІХ ЗАМОВЛЕНЬ (АКТИВНІ, ЗАВЕРШЕНІ, СКАСОВАНІ)
        self.all_orders_box = QGroupBox("Усі замовлення (0)")
        all_layout = QVBoxLayout(self.all_orders_box)
        all_layout.setSpacing(8)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Фільтр за статусом:"))

        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItem("Усі замовлення", "ALL")
        for st in self.ALL_STATUSES:
            self.status_filter_combo.addItem(st, st)
        self.status_filter_combo.currentIndexChanged.connect(self.load_orders)
        filter_row.addWidget(self.status_filter_combo)

        filter_row.addSpacing(12)
        filter_row.addWidget(QLabel("Пошук (№ або покупець):"))
        self.order_search_input = QLineEdit()
        self.order_search_input.setPlaceholderText("Номер замовлення, ПІБ або телефон...")
        self.order_search_input.setMaximumWidth(280)
        self.order_search_input.textChanged.connect(self.load_orders)
        filter_row.addWidget(self.order_search_input)

        filter_row.addStretch()

        refresh_btn = QPushButton("Оновити список")
        refresh_btn.clicked.connect(self.load_orders)
        filter_row.addWidget(refresh_btn)

        all_layout.addLayout(filter_row)

        self.all_orders_table = QTableWidget()
        self.all_orders_table.setColumnCount(10)
        self.all_orders_table.setHorizontalHeaderLabels([
            "№", "Дата", "Покупець", "Телефон", "Товари",
            "К-сть", "Сума (грн)", "Доставка", "Оплата", "Статус"
        ])
        self._configure_orders_table_headers(self.all_orders_table, has_status_col=True)
        self.all_orders_table.itemSelectionChanged.connect(self._sync_status_combo_with_selected)
        self.all_orders_table.cellDoubleClicked.connect(
            lambda r, _c: self._open_details_from_table(self.all_orders_table, r)
        )
        all_layout.addWidget(self.all_orders_table)

        all_actions = QHBoxLayout()
        all_actions.addWidget(QLabel("Змінити статус на:"))

        self.change_status_combo = QComboBox()
        self.change_status_combo.addItems(self.ALL_STATUSES)
        all_actions.addWidget(self.change_status_combo)

        self.apply_status_btn = QPushButton("Застосувати статус")
        self.apply_status_btn.clicked.connect(self.change_selected_order_status)
        all_actions.addWidget(self.apply_status_btn)

        all_actions.addSpacing(12)

        self.all_details_btn = QPushButton("Деталі замовлення")
        self.all_details_btn.clicked.connect(
            lambda: self._open_details_from_table(self.all_orders_table, self.all_orders_table.currentRow())
        )
        all_actions.addWidget(self.all_details_btn)

        self.all_receipt_btn = QPushButton("Переглянути чек")
        self.all_receipt_btn.clicked.connect(
            lambda: self._open_receipt_from_table(self.all_orders_table, self.all_orders_table.currentRow())
        )
        all_actions.addWidget(self.all_receipt_btn)

        all_actions.addStretch()
        all_layout.addLayout(all_actions)

        splitter.addWidget(self.all_orders_box)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        layout.addWidget(splitter)
        self.load_orders()

    def _configure_orders_table_headers(self, table: QTableWidget, has_status_col: bool):
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)
        if has_status_col:
            header.setSectionResizeMode(9, QHeaderView.ResizeToContents)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)

    def _fetch_orders_rows(self):
        conn = get_sqlite_connection(self.db)
        cursor = conn.cursor()
        order_cols = get_table_columns(conn, "orders")

        delivery_expr = "COALESCE(o.delivery_method, '—')" if "delivery_method" in order_cols else "'—'"
        payment_expr = "COALESCE(o.payment_method, '—')" if "payment_method" in order_cols else "'—'"

        sql = f"""
            SELECT
                o.order_id,
                o.order_date,
                COALESCE(c.full_name, 'Покупець') AS client_name,
                COALESCE(c.phone, '—') AS phone,
                COALESCE(GROUP_CONCAT(p.title || ' (x' || oi.quantity || ')', ', '), '—') AS items_summary,
                COALESCE(SUM(oi.quantity), 0) AS total_qty,
                COALESCE(o.total_amount, 0.0) AS total_amount,
                {delivery_expr} AS delivery_method,
                {payment_expr} AS payment_method,
                COALESCE(o.status, 'Нове') AS status
            FROM orders o
            LEFT JOIN clients c ON o.client_id = c.client_id
            LEFT JOIN order_items oi ON o.order_id = oi.order_id
            LEFT JOIN products p ON oi.product_id = p.product_id
            GROUP BY o.order_id
            ORDER BY o.order_id DESC
        """
        cursor.execute(sql)
        return cursor.fetchall()

    def load_orders(self):
        rows = self._fetch_orders_rows()

        new_orders = [r for r in rows if str(r[9]).strip().lower() == "нове"]
        self.new_orders_box.setTitle(f"Нові замовлення, які очікують підтвердження ({len(new_orders)})")
        self._fill_orders_table(self.new_orders_table, new_orders, include_status=False)

        status_filter = self.status_filter_combo.currentData() or "ALL"
        search_q = self.order_search_input.text().strip().lower()

        filtered_all = []
        for r in rows:
            oid_str = str(r[0])
            client_name = str(r[2]).lower()
            phone = str(r[3]).lower()
            status = str(r[9])

            if status_filter != "ALL" and status.strip().lower() != status_filter.strip().lower():
                continue

            if search_q and (search_q not in oid_str and search_q not in client_name and search_q not in phone):
                continue

            filtered_all.append(r)

        self.all_orders_box.setTitle(f"Усі замовлення ({len(filtered_all)})")
        self._fill_orders_table(self.all_orders_table, filtered_all, include_status=True)

    def _fill_orders_table(self, table: QTableWidget, rows: list, include_status: bool):
        table.setRowCount(len(rows))
        for idx, r in enumerate(rows):
            oid, odate, cname, phone, items_txt, qty, total_sum, delivery, payment, status = r

            id_item = QTableWidgetItem(f"№{oid}")
            id_item.setData(Qt.UserRole, oid)
            items_item = QTableWidgetItem(str(items_txt))
            items_item.setToolTip(str(items_txt))

            table.setItem(idx, 0, id_item)
            table.setItem(idx, 1, QTableWidgetItem(str(odate)))
            table.setItem(idx, 2, QTableWidgetItem(str(cname)))
            table.setItem(idx, 3, QTableWidgetItem(str(phone)))
            table.setItem(idx, 4, items_item)
            table.setItem(idx, 5, QTableWidgetItem(f"{int(qty)} шт."))
            table.setItem(idx, 6, QTableWidgetItem(f"{float(total_sum):.2f}"))
            table.setItem(idx, 7, QTableWidgetItem(str(delivery)))
            table.setItem(idx, 8, QTableWidgetItem(str(payment)))
            if include_status:
                table.setItem(idx, 9, QTableWidgetItem(str(status)))

    def _get_order_id_from_row(self, table: QTableWidget, row: int):
        if row < 0:
            QMessageBox.warning(self, "Увага", "Оберіть замовлення у таблиці.")
            return None
        item = table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _sync_status_combo_with_selected(self):
        row = self.all_orders_table.currentRow()
        if row < 0:
            return
        status_item = self.all_orders_table.item(row, 9)
        if status_item:
            idx = self.change_status_combo.findText(status_item.text())
            if idx >= 0:
                self.change_status_combo.setCurrentIndex(idx)

    def accept_selected_new_order(self):
        oid = self._get_order_id_from_row(self.new_orders_table, self.new_orders_table.currentRow())
        if oid is None:
            return

        award_bonuses_once_on_delivery(self.db, oid, "В обробці")
        self.load_orders()
        self.orders_changed.emit()
        QMessageBox.information(
            self,
            "Замовлення прийнято",
            f"Замовлення №{oid} прийнято в обробку."
        )

    def cancel_selected_new_order(self):
        oid = self._get_order_id_from_row(self.new_orders_table, self.new_orders_table.currentRow())
        if oid is None:
            return

        confirm = QMessageBox.question(
            self,
            "Скасування замовлення",
            f"Ви дійсно бажаєте скасувати нове замовлення №{oid}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        award_bonuses_once_on_delivery(self.db, oid, "Скасовано")
        self.load_orders()
        self.orders_changed.emit()

    def change_selected_order_status(self):
        oid = self._get_order_id_from_row(self.all_orders_table, self.all_orders_table.currentRow())
        if oid is None:
            return

        new_status = self.change_status_combo.currentText()
        award_bonuses_once_on_delivery(self.db, oid, new_status)
        self.load_orders()
        self.orders_changed.emit()

        extra_msg = ""
        if new_status.strip().lower() == "доставлено":
            extra_msg = "\nБонуси за замовлення нараховано покупцю (якщо не були нараховані раніше)."

        QMessageBox.information(
            self,
            "Статус змінено",
            f"Статус замовлення №{oid} змінено на «{new_status}».{extra_msg}"
        )

    def _open_details_from_table(self, table: QTableWidget, row: int):
        oid = self._get_order_id_from_row(table, row)
        if oid is None:
            return

        dialog = AdminOrderDetailsDialog(self.db, oid, parent=self)
        dialog.status_updated.connect(self._on_dialog_status_updated)
        dialog.exec_()

    def _on_dialog_status_updated(self):
        self.load_orders()
        self.orders_changed.emit()

    def _open_receipt_from_table(self, table: QTableWidget, row: int):
        oid = self._get_order_id_from_row(table, row)
        if oid is None:
            return
        open_or_generate_order_receipt(self.db, oid, parent=self)
        