import os
import re
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QGroupBox, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QLineEdit, QMessageBox, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QUrl
from PyQt5.QtGui import QDesktopServices


class EditProfileDialog(QDialog):
    """Діалогове вікно редагування особистих даних покупця"""
    def __init__(self, db_manager, client_id: int, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.client_id = client_id
        self.setWindowTitle("Редагування профілю")
        self.resize(420, 270)
        self.init_ui()
        self.load_current_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        layout.addWidget(QLabel("<b>Редагування особистих даних</b>"))

        layout.addWidget(QLabel("Ім’я та прізвище *"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Введіть ім’я та прізвище")
        layout.addWidget(self.name_input)

        layout.addWidget(QLabel("Номер телефону *"))
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("+380671234567")
        layout.addWidget(self.phone_input)

        layout.addWidget(QLabel("Електронна пошта *"))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("buyer@example.com")
        layout.addWidget(self.email_input)

        layout.addStretch()

        btns_row = QHBoxLayout()
        cancel_btn = QPushButton("Скасувати")
        cancel_btn.clicked.connect(self.reject)
        btns_row.addWidget(cancel_btn)

        btns_row.addStretch()

        save_btn = QPushButton("Зберегти зміни")
        save_btn.clicked.connect(self.save_changes)
        btns_row.addWidget(save_btn)

        layout.addLayout(btns_row)

    def load_current_data(self):
        client = self.db.get_client_by_id(self.client_id)
        if client:
            self.name_input.setText(client.full_name or "")
            self.phone_input.setText(client.phone or "")
            self.email_input.setText(client.email or "")

    def _validate_phone(self, phone: str) -> bool:
        cleaned = re.sub(r"[\s\-\(\)]", "", phone.strip())
        return bool(re.match(r"^(\+?38)?0\d{9}$", cleaned))

    def _validate_email(self, email: str) -> bool:
        return bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email.strip()))

    def save_changes(self):
        full_name = self.name_input.text().strip()
        phone = self.phone_input.text().strip()
        email = self.email_input.text().strip()

        if len(full_name) < 2:
            QMessageBox.warning(self, "Помилка", "Введіть коректне ім’я та прізвище (мінімум 2 символи).")
            self.name_input.setFocus()
            return

        if phone and not self._validate_phone(phone):
            QMessageBox.warning(
                self, "Некоректний телефон",
                "Введіть коректний номер телефону.\nПриклад: +380671234567 або 0671234567."
            )
            self.phone_input.setFocus()
            return

        if email and not self._validate_email(email):
            QMessageBox.warning(
                self, "Некоректний Email",
                "Введіть коректну електронну пошту.\nПриклад: client@gmail.com"
            )
            self.email_input.setFocus()
            return

        self.db.update_client_profile(
            client_id=self.client_id,
            full_name=full_name,
            phone=phone,
            email=email
        )
        QMessageBox.information(self, "Профіль оновлено", "Ваші особисті дані успішно збережено!")
        self.accept()


class OrderDetailsDialog(QDialog):
    """Вікно детального перегляду конкретного замовлення покупця (без фото товарів)"""
    def __init__(self, order_data: dict, parent=None):
        super().__init__(parent)
        self.order_data = order_data
        self.setWindowTitle(f"Деталі замовлення №{order_data['order_id']}")
        self.resize(660, 480)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel(f"<b>Замовлення №{self.order_data['order_id']}</b>"))
        top_row.addStretch()
        status = self.order_data.get("status", "Нове")
        top_row.addWidget(QLabel(f"<b>Статус:</b> {status}"))
        layout.addLayout(top_row)

        info_box = QGroupBox("Дані замовлення")
        info_layout = QVBoxLayout(info_box)
        info_layout.setSpacing(4)

        info_layout.addWidget(QLabel(f"<b>Дата оформлення:</b> {self.order_data.get('order_date', '—')}"))
        info_layout.addWidget(QLabel(f"<b>Отримувач:</b> {self.order_data.get('client_name', '—')} ({self.order_data.get('phone', '—')})"))
        info_layout.addWidget(QLabel(f"<b>Спосіб доставки:</b> {self.order_data.get('delivery_method', 'Нова пошта')}"))
        info_layout.addWidget(QLabel(f"<b>Адреса / відділення:</b> {self.order_data.get('delivery_address') or 'Не вказано'}"))
        info_layout.addWidget(QLabel(f"<b>Спосіб оплати:</b> {self.order_data.get('payment_method', 'Оплата карткою')}"))
        if self.order_data.get("comment"):
            info_layout.addWidget(QLabel(f"<b>Коментар:</b> {self.order_data['comment']}"))

        layout.addWidget(info_box)

        items_table = QTableWidget()
        items_table.setColumnCount(4)
        items_table.setHorizontalHeaderLabels(["Назва товару", "Кількість", "Ціна за од.", "Сума"])
        items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        items_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        items_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        items_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        items_table.verticalHeader().setVisible(False)
        items_table.setEditTriggers(QTableWidget.NoEditTriggers)
        items_table.setSelectionMode(QTableWidget.NoSelection)

        items = self.order_data.get("items", [])
        items_table.setRowCount(len(items))
        subtotal = 0.0
        for row, item in enumerate(items):
            line_sum = item["quantity"] * item["price_per_unit"]
            subtotal += line_sum
            items_table.setItem(row, 0, QTableWidgetItem(item["title"]))
            items_table.setItem(row, 1, QTableWidgetItem(f"{item['quantity']} шт."))
            items_table.setItem(row, 2, QTableWidgetItem(f"{item['price_per_unit']:.2f} грн"))
            items_table.setItem(row, 3, QTableWidgetItem(f"{line_sum:.2f} грн"))

        layout.addWidget(items_table)

        summary_box = QGroupBox("Підсумок оплати")
        sum_layout = QVBoxLayout(summary_box)
        sum_layout.setSpacing(4)

        bonus_used = int(self.order_data.get("bonus_used", 0))
        total_amount = float(self.order_data.get("total_amount", 0.0))
        bonus_earned = int(self.order_data.get("bonus_earned", 0))
        bonus_awarded = int(self.order_data.get("bonus_awarded", 0))

        sum_layout.addWidget(QLabel(f"Вартість товарів: <b>{subtotal:.2f} грн</b>"))
        if bonus_used > 0:
            sum_layout.addWidget(QLabel(f"Використано бонусів (знижка): <b>-{bonus_used:.2f} грн</b> ({bonus_used} бонусів)"))

        sum_layout.addWidget(QLabel(f"<b>Загальна сума замовлення: {total_amount:.2f} грн</b>"))

        expected_bonus = int(total_amount // 100)
        if status.strip().lower() == "доставлено" and bonus_awarded:
            sum_layout.addWidget(QLabel(f"Нараховано бонусів за замовлення: <b>+{bonus_earned} бонусів</b>"))
        elif status.strip().lower() != "скасовано" and expected_bonus > 0:
            sum_layout.addWidget(QLabel(f"Після отримання замовлення (статус «Доставлено») буде нараховано: <b>+{expected_bonus} бонусів</b>"))

        layout.addWidget(summary_box)

        btns_row = QHBoxLayout()
        receipt_path = self.order_data.get("receipt_path")
        if receipt_path and os.path.exists(receipt_path):
            pdf_btn = QPushButton("Відкрити PDF-чек")
            pdf_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(receipt_path))))
            btns_row.addWidget(pdf_btn)

        btns_row.addStretch()

        close_btn = QPushButton("Закрити")
        close_btn.clicked.connect(self.accept)
        btns_row.addWidget(close_btn)

        layout.addLayout(btns_row)


class PersonalAccountWidget(QWidget):
    """
    Особистий кабінет покупця (базовий інтерфейс):
    1. Особисті дані покупця + редагування профілю
    2. Блок «Мої бонуси»
    3. Блок «Мої замовлення» з детальним переглядом
    """
    profile_updated = pyqtSignal()

    def __init__(self, db_manager, get_client_id_func, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.get_client_id = get_client_id_func
        self.orders_cache = []
        self.init_ui()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 10, 12, 10)
        root_layout.setSpacing(10)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("<b>Особистий кабінет покупця</b>"))
        top_bar.addStretch()

        self.refresh_btn = QPushButton("Оновити")
        self.refresh_btn.clicked.connect(self.refresh_data)
        top_bar.addWidget(self.refresh_btn)
        root_layout.addLayout(top_bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(0, 0, 6, 0)
        content_layout.setSpacing(12)

        # 1. БЛОК: ОСОБИСТІ ДАНІ ПОКУПЦЯ
        profile_box = QGroupBox("Особисті дані покупця")
        profile_layout = QVBoxLayout(profile_box)
        profile_layout.setSpacing(8)

        fields_grid = QGridLayout()
        fields_grid.setHorizontalSpacing(24)
        fields_grid.setVerticalSpacing(4)

        fields_grid.addWidget(QLabel("Ім’я та прізвище:"), 0, 0)
        self.name_val_label = QLabel("<b>—</b>")
        fields_grid.addWidget(self.name_val_label, 1, 0)

        fields_grid.addWidget(QLabel("Номер телефону:"), 0, 1)
        self.phone_val_label = QLabel("Не вказано")
        fields_grid.addWidget(self.phone_val_label, 1, 1)

        fields_grid.addWidget(QLabel("Електронна пошта:"), 0, 2)
        self.email_val_label = QLabel("Не вказано")
        fields_grid.addWidget(self.email_val_label, 1, 2)

        fields_grid.setColumnStretch(0, 2)
        fields_grid.setColumnStretch(1, 1)
        fields_grid.setColumnStretch(2, 2)

        profile_layout.addLayout(fields_grid)

        prof_btn_row = QHBoxLayout()
        self.edit_profile_btn = QPushButton("Редагувати профіль")
        self.edit_profile_btn.clicked.connect(self.open_edit_profile)
        prof_btn_row.addWidget(self.edit_profile_btn)
        prof_btn_row.addStretch()
        profile_layout.addLayout(prof_btn_row)

        content_layout.addWidget(profile_box)

        # 2. БЛОК: МОЇ БОНУСИ
        bonus_box = QGroupBox("Мої бонуси")
        bonus_layout = QVBoxLayout(bonus_box)
        bonus_layout.setSpacing(8)

        bonus_layout.addWidget(QLabel("Правила програми: 1 бонус = 1 грн знижки (+1 бонус за кожні 100 грн доставленого замовлення)"))

        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(10)

        self.current_bonus_val = self._create_metric_box(metrics_row, "Поточний баланс бонусів", "0 бонусів")
        self.uah_equiv_val = self._create_metric_box(metrics_row, "Грошовий еквівалент", "0.00 грн")
        self.total_earned_val = self._create_metric_box(metrics_row, "Накопичено всього", "0 бонусів")
        self.total_spent_val = self._create_metric_box(metrics_row, "Використано бонусів", "0 бонусів")

        bonus_layout.addLayout(metrics_row)
        content_layout.addWidget(bonus_box)

        # 3. БЛОК: МОЇ ЗАМОВЛЕННЯ
        orders_box = QGroupBox("Мої замовлення")
        orders_layout = QVBoxLayout(orders_box)
        orders_layout.setSpacing(8)

        orders_header = QHBoxLayout()
        self.orders_count_label = QLabel("Всього замовлень: 0")
        orders_header.addWidget(self.orders_count_label)
        orders_header.addStretch()
        orders_layout.addLayout(orders_header)

        self.orders_table = QTableWidget()
        self.orders_table.setColumnCount(7)
        self.orders_table.setHorizontalHeaderLabels([
            "№ замовлення", "Дата оформлення", "Придбані товари",
            "Кількість", "Загальна сума", "Статус", "Деталі"
        ])
        self.orders_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.orders_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.orders_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.orders_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.orders_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.orders_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.orders_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)
        self.orders_table.setColumnWidth(6, 120)
        self.orders_table.verticalHeader().setVisible(False)
        self.orders_table.verticalHeader().setDefaultSectionSize(38)
        self.orders_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.orders_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.orders_table.setMinimumHeight(250)
        self.orders_table.cellDoubleClicked.connect(self.on_order_double_clicked)

        orders_layout.addWidget(self.orders_table)
        content_layout.addWidget(orders_box)

        scroll.setWidget(scroll_content)
        root_layout.addWidget(scroll)

    def _create_metric_box(self, parent_layout, caption: str, initial_value: str) -> QLabel:
        box = QFrame()
        box.setFrameShape(QFrame.StyledPanel)
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(10, 8, 10, 8)
        box_layout.setSpacing(4)

        box_layout.addWidget(QLabel(caption))
        val_lbl = QLabel(f"<b>{initial_value}</b>")
        box_layout.addWidget(val_lbl)
        parent_layout.addWidget(box, stretch=1)
        return val_lbl

    def refresh_data(self):
        client_id = self.get_client_id()
        client = self.db.ensure_client_profile(client_id)

        self.name_val_label.setText(f"<b>{client.full_name or 'Покупець'}</b>")
        self.phone_val_label.setText(client.phone if client.phone else "Не вказано")
        self.email_val_label.setText(client.email if client.email else "Не вказано")

        bonus_info = self.db.get_client_bonus_info(client_id)
        cur_bal = bonus_info["current_balance"]
        uah_eq = bonus_info["uah_equivalent"]
        earned = bonus_info["total_earned"]
        spent = bonus_info["total_spent"]

        self.current_bonus_val.setText(f"<b>{cur_bal} бонусів</b>")
        self.uah_equiv_val.setText(f"<b>{uah_eq:.2f} грн</b>")
        self.total_earned_val.setText(f"<b>{earned} бонусів</b>")
        self.total_spent_val.setText(f"<b>{spent} бонусів</b>")

        self.orders_cache = self.db.get_client_orders_detailed(client_id)
        self.orders_count_label.setText(f"Всього замовлень: {len(self.orders_cache)}")
        self.populate_orders_table()

    def populate_orders_table(self):
        self.orders_table.setRowCount(len(self.orders_cache))
        for row, order in enumerate(self.orders_cache):
            order_id = order["order_id"]
            order_date = str(order["order_date"])
            items_summary = order["items_summary"]
            total_qty = order["total_items_count"]
            total_amount = order["total_amount"]
            status = order["status"]

            id_item = QTableWidgetItem(f"№{order_id}")
            id_item.setData(Qt.UserRole, order_id)
            date_item = QTableWidgetItem(order_date)
            items_item = QTableWidgetItem(items_summary)
            items_item.setToolTip(items_summary)
            qty_item = QTableWidgetItem(f"{total_qty} шт.")
            sum_item = QTableWidgetItem(f"{total_amount:.2f} грн")
            status_item = QTableWidgetItem(status)

            self.orders_table.setItem(row, 0, id_item)
            self.orders_table.setItem(row, 1, date_item)
            self.orders_table.setItem(row, 2, items_item)
            self.orders_table.setItem(row, 3, qty_item)
            self.orders_table.setItem(row, 4, sum_item)
            self.orders_table.setItem(row, 5, status_item)

            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(4, 2, 4, 2)

            details_btn = QPushButton("Детальніше")
            details_btn.clicked.connect(lambda checked, oid=order_id: self.open_order_details(oid))
            btn_layout.addWidget(details_btn)

            self.orders_table.setCellWidget(row, 6, btn_container)

    def open_edit_profile(self):
        client_id = self.get_client_id()
        self.db.ensure_client_profile(client_id)
        dialog = EditProfileDialog(self.db, client_id, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_data()
            self.profile_updated.emit()

    def on_order_double_clicked(self, row, column):
        item = self.orders_table.item(row, 0)
        if item:
            oid = item.data(Qt.UserRole)
            if oid is not None:
                self.open_order_details(oid)

    def open_order_details(self, order_id: int):
        order_data = self.db.get_order_full_info(order_id)
        if not order_data or order_data.get("client_id") != self.get_client_id():
            QMessageBox.warning(self, "Помилка", "Не вдалося завантажити деталі замовлення.")
            return
        dialog = OrderDetailsDialog(order_data, parent=self)
        dialog.exec_()
        