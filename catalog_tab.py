import os
import re
import sqlite3
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QTableWidget, QTableWidgetItem, QPushButton, QHeaderView, 
    QMessageBox, QDialog, QFormLayout, QLineEdit, QSpinBox, 
    QDoubleSpinBox, QTextEdit, QFrame, QStackedWidget
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices
from classes import Product, Client, OrderItem
from cart import CartDialog


class ProductDialog(QDialog):
    """Діалогове вікно додавання/редагування товару"""
    def __init__(self, db_manager, product: Product = None, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.product = product
        self.setWindowTitle("Редагування товару" if product else "Додавання товару")
        self.resize(400, 380)

        layout = QFormLayout(self)

        self.category_combo = QComboBox()
        categories = self.db.get_all_categories()
        for cat in categories:
            self.category_combo.addItem(cat.name, cat.category_id)

        self.supplier_combo = QComboBox()
        self.supplier_combo.addItem("Без постачальника", None)
        if hasattr(self.db, "get_all_suppliers"):
            for sup in self.db.get_all_suppliers():
                self.supplier_combo.addItem(sup.name, sup.supplier_id)

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
        layout.addRow("Постачальник:", self.supplier_combo)
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
            if getattr(self.product, "supplier_id", None) is not None:
                s_idx = self.supplier_combo.findData(self.product.supplier_id)
                if s_idx >= 0:
                    self.supplier_combo.setCurrentIndex(s_idx)
            self.title_input.setText(self.product.title)
            self.brand_input.setText(self.product.brand)
            self.price_spin.setValue(self.product.price)
            self.stock_spin.setValue(self.product.stock_quantity)
            self.description_input.setPlainText(self.product.description)

    def save(self):
        if not self.title_input.text().strip():
            QMessageBox.warning(self, "Помилка", "Введіть назву товару.")
            return
        self.accept()

    def get_product_data(self) -> Product:
        category_id = self.category_combo.currentData()
        supplier_id = self.supplier_combo.currentData()
        title = self.title_input.text().strip()
        brand = self.brand_input.text().strip()
        price = self.price_spin.value()
        stock = self.stock_spin.value()
        description = self.description_input.toPlainText().strip()
        
        prod_id = self.product.product_id if self.product else None
        return Product(
            category_id=category_id,
            supplier_id=supplier_id,
            title=title,
            brand=brand,
            price=price,
            stock_quantity=stock,
            description=description,
            product_id=prod_id
        )


class OrderDialog(QDialog):
    """Сторінка оформлення замовлення з валідацією, підсумком та списанням бонусів"""
    PICKUP_ADDRESS = "м. Київ, вул. Хрещатик, 22 (Пункт самовивозу магазину)"

    def __init__(self, cart_items=None, db_manager=None, client_id=None, parent=None):
        super().__init__(parent)
        self.cart_items = cart_items or []
        self.db = db_manager
        self.client_id = client_id
        self.subtotal = sum(prod.price * qty for prod, qty in self.cart_items)
        self.available_bonuses = 0

        if self.db is not None and self.client_id is not None:
            bonus_info = self.db.get_client_bonus_info(self.client_id)
            self.available_bonuses = bonus_info.get("current_balance", 0)

        self.setWindowTitle("Оформлення замовлення")
        self.resize(880, 660)
        self.init_ui()
        self.prefill_client_profile()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #F1F5F9;
            }
            QFrame#CardPanel {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 10px;
            }
            QLabel#SectionTitle {
                font-size: 14px;
                font-weight: bold;
                color: #0F172A;
            }
            QLabel#FieldLabel {
                font-size: 12px;
                font-weight: bold;
                color: #334155;
            }
            QLineEdit, QComboBox, QTextEdit, QSpinBox {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 7px 10px;
                font-size: 13px;
                color: #0F172A;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QSpinBox:focus {
                border: 1px solid #2563EB;
            }
        """)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 14, 16, 14)
        root_layout.setSpacing(12)

        header_lbl = QLabel("Оформлення замовлення")
        header_lbl.setStyleSheet("font-size: 19px; font-weight: bold; color: #0F172A;")
        root_layout.addWidget(header_lbl)

        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(14)

        # ==========================================
        # ЛІВА КОЛОНКА: ДАНІ ПОКУПЦЯ, ДОСТАВКА, ОПЛАТА
        # ==========================================
        left_panel = QFrame()
        left_panel.setObjectName("CardPanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(16, 14, 16, 14)
        left_layout.setSpacing(10)

        buyer_title = QLabel("1. Контактні дані покупця")
        buyer_title.setObjectName("SectionTitle")
        left_layout.addWidget(buyer_title)

        lbl_name = QLabel("ПІБ покупця *")
        lbl_name.setObjectName("FieldLabel")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Наприклад: Шевченко Тарас Григорович")
        left_layout.addWidget(lbl_name)
        left_layout.addWidget(self.name_input)

        contact_row = QHBoxLayout()
        contact_row.setSpacing(10)

        phone_col = QVBoxLayout()
        lbl_phone = QLabel("Номер телефону *")
        lbl_phone.setObjectName("FieldLabel")
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("+380 (67) 123-45-67")
        phone_col.addWidget(lbl_phone)
        phone_col.addWidget(self.phone_input)

        email_col = QVBoxLayout()
        lbl_email = QLabel("Електронна пошта *")
        lbl_email.setObjectName("FieldLabel")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("client@example.com")
        email_col.addWidget(lbl_email)
        email_col.addWidget(self.email_input)

        contact_row.addLayout(phone_col)
        contact_row.addLayout(email_col)
        left_layout.addLayout(contact_row)

        # 2. Спосіб доставки та динамічні поля адреси
        delivery_title = QLabel("2. Спосіб та адреса доставки")
        delivery_title.setObjectName("SectionTitle")
        delivery_title.setStyleSheet("margin-top: 6px;")
        left_layout.addWidget(delivery_title)

        lbl_delivery = QLabel("Оберіть службу доставки *")
        lbl_delivery.setObjectName("FieldLabel")
        self.delivery_combo = QComboBox()
        self.delivery_combo.addItems(["Нова пошта", "Укрпошта", "Самовивіз"])
        self.delivery_combo.currentIndexChanged.connect(self.on_delivery_method_changed)
        left_layout.addWidget(lbl_delivery)
        left_layout.addWidget(self.delivery_combo)

        self.address_stack = QStackedWidget()

        # Сторінка 0: Нова пошта
        np_page = QWidget()
        np_layout = QHBoxLayout(np_page)
        np_layout.setContentsMargins(0, 4, 0, 0)
        np_layout.setSpacing(10)

        np_city_col = QVBoxLayout()
        np_city_lbl = QLabel("Місто *")
        np_city_lbl.setObjectName("FieldLabel")
        self.np_city_input = QLineEdit()
        self.np_city_input.setPlaceholderText("Введіть місто (напр. Київ)")
        np_city_col.addWidget(np_city_lbl)
        np_city_col.addWidget(self.np_city_input)

        np_branch_col = QVBoxLayout()
        np_branch_lbl = QLabel("Відділення Нової пошти *")
        np_branch_lbl.setObjectName("FieldLabel")
        self.np_branch_input = QLineEdit()
        self.np_branch_input.setPlaceholderText("Напр. Відділення №12")
        np_branch_col.addWidget(np_branch_lbl)
        np_branch_col.addWidget(self.np_branch_input)

        np_layout.addLayout(np_city_col)
        np_layout.addLayout(np_branch_col)
        self.address_stack.addWidget(np_page)

        # Сторінка 1: Укрпошта
        up_page = QWidget()
        up_layout = QHBoxLayout(up_page)
        up_layout.setContentsMargins(0, 4, 0, 0)
        up_layout.setSpacing(10)

        up_city_col = QVBoxLayout()
        up_city_lbl = QLabel("Місто / населений пункт *")
        up_city_lbl.setObjectName("FieldLabel")
        self.up_city_input = QLineEdit()
        self.up_city_input.setPlaceholderText("Введіть населений пункт")
        up_city_col.addWidget(up_city_lbl)
        up_city_col.addWidget(self.up_city_input)

        up_branch_col = QVBoxLayout()
        up_branch_lbl = QLabel("Відділення Укрпошти / індекс *")
        up_branch_lbl.setObjectName("FieldLabel")
        self.up_branch_input = QLineEdit()
        self.up_branch_input.setPlaceholderText("Напр. Відділення №5 або 01001")
        up_branch_col.addWidget(up_branch_lbl)
        up_branch_col.addWidget(self.up_branch_input)

        up_layout.addLayout(up_city_col)
        up_layout.addLayout(up_branch_col)
        self.address_stack.addWidget(up_page)

        # Сторінка 2: Самовивіз
        pickup_page = QWidget()
        pickup_layout = QVBoxLayout(pickup_page)
        pickup_layout.setContentsMargins(0, 4, 0, 0)
        pickup_info = QLabel(
            f"📍 Адреса самовивозу: {self.PICKUP_ADDRESS}\n"
            "🕒 Графік видачі замовлень: Пн–Нд з 09:00 до 20:00 (безкоштовно)"
        )
        pickup_info.setWordWrap(True)
        pickup_info.setStyleSheet("""
            background-color: #EFF6FF;
            border: 1px solid #BFDBFE;
            border-radius: 6px;
            padding: 8px 10px;
            color: #1E3A8A;
            font-size: 12px;
        """)
        pickup_layout.addWidget(pickup_info)
        self.address_stack.addWidget(pickup_page)

        left_layout.addWidget(self.address_stack)

        # 3. Спосіб оплати та коментар
        pay_title = QLabel("3. Спосіб оплати та коментар")
        pay_title.setObjectName("SectionTitle")
        pay_title.setStyleSheet("margin-top: 6px;")
        left_layout.addWidget(pay_title)

        lbl_payment = QLabel("Спосіб оплати *")
        lbl_payment.setObjectName("FieldLabel")
        self.payment_combo = QComboBox()
        self.payment_combo.addItems(["Оплата карткою", "Післяплата"])
        self.payment_combo.currentTextChanged.connect(self.update_summary_meta)
        left_layout.addWidget(lbl_payment)
        left_layout.addWidget(self.payment_combo)

        lbl_comment = QLabel("Коментар до замовлення (необов’язково)")
        lbl_comment.setObjectName("FieldLabel")
        self.comment_input = QTextEdit()
        self.comment_input.setPlaceholderText("Додаткові побажання до замовлення...")
        self.comment_input.setFixedHeight(58)
        left_layout.addWidget(lbl_comment)
        left_layout.addWidget(self.comment_input)

        left_layout.addStretch()
        columns_layout.addWidget(left_panel, stretch=3)

        # ==========================================
        # ПРАВА КОЛОНКА: ПІДСУМОК ТА БОНУСИ (БЕЗ ФОТО)
        # ==========================================
        right_panel = QFrame()
        right_panel.setObjectName("CardPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 14, 16, 14)
        right_layout.setSpacing(10)

        summary_title = QLabel("Підсумок замовлення")
        summary_title.setObjectName("SectionTitle")
        right_layout.addWidget(summary_title)

        self.summary_table = QTableWidget()
        self.summary_table.setColumnCount(3)
        self.summary_table.setHorizontalHeaderLabels(["Товар", "К-сть", "Вартість"])
        self.summary_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.summary_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.summary_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.summary_table.verticalHeader().setVisible(False)
        self.summary_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.summary_table.setSelectionMode(QTableWidget.NoSelection)
        right_layout.addWidget(self.summary_table)

        # --- Блок використання бонусів ---
        bonus_box = QFrame()
        bonus_box.setStyleSheet("""
            QFrame {
                background-color: #EFF6FF;
                border: 1px solid #BFDBFE;
                border-radius: 8px;
            }
            QLabel {
                border: none;
                background: transparent;
                color: #1E3A8A;
                font-size: 12px;
            }
        """)
        bonus_box_layout = QVBoxLayout(bonus_box)
        bonus_box_layout.setContentsMargins(10, 8, 10, 8)
        bonus_box_layout.setSpacing(6)

        max_usable = max(0, min(self.available_bonuses, int(self.subtotal)))

        bonus_hdr = QLabel(f"🎁 Доступно бонусів: <b>{self.available_bonuses}</b> (еквівалент <b>{self.available_bonuses:.2f} грн</b>)")
        bonus_box_layout.addWidget(bonus_hdr)

        bonus_ctrl_row = QHBoxLayout()
        bonus_ctrl_row.addWidget(QLabel("Списати бонусів:"))

        self.bonus_spin = QSpinBox()
        self.bonus_spin.setRange(0, max_usable)
        self.bonus_spin.setValue(0)
        self.bonus_spin.setSuffix(" бонусів")
        self.bonus_spin.setEnabled(max_usable > 0)
        self.bonus_spin.valueChanged.connect(self.recalculate_totals)
        bonus_ctrl_row.addWidget(self.bonus_spin)

        self.use_max_bonus_btn = QPushButton("Макс.")
        self.use_max_bonus_btn.setCursor(Qt.PointingHandCursor)
        self.use_max_bonus_btn.setEnabled(max_usable > 0)
        self.use_max_bonus_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                border: none;
                border-radius: 5px;
                padding: 5px 10px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover:enabled { background-color: #1D4ED8; }
            QPushButton:disabled { background-color: #94A3B8; }
        """)
        self.use_max_bonus_btn.clicked.connect(lambda: self.bonus_spin.setValue(max_usable))
        bonus_ctrl_row.addWidget(self.use_max_bonus_btn)

        bonus_box_layout.addLayout(bonus_ctrl_row)
        right_layout.addWidget(bonus_box)

        # Інформаційний блок обраних параметрів
        meta_box = QFrame()
        meta_box.setStyleSheet("""
            QFrame {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
            }
            QLabel {
                border: none;
                background: transparent;
                font-size: 12px;
                color: #334155;
            }
        """)
        meta_layout = QVBoxLayout(meta_box)
        meta_layout.setContentsMargins(10, 8, 10, 8)
        meta_layout.setSpacing(4)

        self.items_count_label = QLabel("Позицій у замовленні: 0 шт.")
        self.delivery_preview_label = QLabel("Доставка: Нова пошта")
        self.payment_preview_label = QLabel("Оплата: Оплата карткою")
        self.subtotal_label = QLabel(f"Сума товарів: {self.subtotal:.2f} грн")
        self.bonus_discount_label = QLabel("Знижка бонусами: 0.00 грн")
        self.bonus_discount_label.setStyleSheet("color: #2563EB; font-weight: bold; border: none; background: transparent;")

        meta_layout.addWidget(self.items_count_label)
        meta_layout.addWidget(self.delivery_preview_label)
        meta_layout.addWidget(self.payment_preview_label)
        meta_layout.addWidget(self.subtotal_label)
        meta_layout.addWidget(self.bonus_discount_label)
        right_layout.addWidget(meta_box)

        # Загальна вартість до сплати
        total_box = QFrame()
        total_box.setStyleSheet("""
            QFrame {
                background-color: #F0FDF4;
                border: 1px solid #BBF7D0;
                border-radius: 8px;
            }
        """)
        total_layout = QHBoxLayout(total_box)
        total_layout.setContentsMargins(12, 10, 12, 10)

        total_caption = QLabel("До сплати:")
        total_caption.setStyleSheet("font-size: 14px; font-weight: bold; color: #166534; border: none;")
        self.total_sum_label = QLabel("0.00 грн")
        self.total_sum_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #15803D; border: none;")

        total_layout.addWidget(total_caption)
        total_layout.addStretch()
        total_layout.addWidget(self.total_sum_label)
        right_layout.addWidget(total_box)

        self.confirm_btn = QPushButton("✓ Підтвердити замовлення")
        self.confirm_btn.setCursor(Qt.PointingHandCursor)
        self.confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #16A34A;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #15803D;
            }
        """)
        self.confirm_btn.clicked.connect(self.validate_and_accept)
        right_layout.addWidget(self.confirm_btn)

        self.cancel_btn = QPushButton("Повернутися до кошика")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #E2E8F0;
                color: #1E293B;
                font-size: 13px;
                padding: 7px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #CBD5E1;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        right_layout.addWidget(self.cancel_btn)

        columns_layout.addWidget(right_panel, stretch=2)
        root_layout.addLayout(columns_layout)

        self.populate_summary_table()

    def prefill_client_profile(self):
        """Автопідстановка збережених контактних даних із особистого кабінету"""
        if self.db is not None and self.client_id is not None:
            client = self.db.get_client_by_id(self.client_id)
            if client:
                if client.full_name and client.full_name != "Покупець":
                    self.name_input.setText(client.full_name)
                if client.phone:
                    self.phone_input.setText(client.phone)
                if client.email:
                    self.email_input.setText(client.email)

    def populate_summary_table(self):
        self.summary_table.setRowCount(len(self.cart_items))
        total_qty = 0

        for row, (prod, qty) in enumerate(self.cart_items):
            row_sum = prod.price * qty
            total_qty += qty

            self.summary_table.setItem(row, 0, QTableWidgetItem(prod.title))
            self.summary_table.setItem(row, 1, QTableWidgetItem(f"{qty} шт."))
            self.summary_table.setItem(row, 2, QTableWidgetItem(f"{row_sum:.2f} грн"))

        self.items_count_label.setText(f"Всього товарів: {total_qty} шт.")
        self.recalculate_totals()

    def recalculate_totals(self):
        bonus_used = self.get_bonus_used()
        final_total = max(0.0, self.subtotal - bonus_used)
        self.subtotal_label.setText(f"Сума товарів: {self.subtotal:.2f} грн")
        self.bonus_discount_label.setText(f"Знижка бонусами: -{bonus_used:.2f} грн")
        self.total_sum_label.setText(f"{final_total:.2f} грн")

    def get_bonus_used(self) -> int:
        max_usable = max(0, min(self.available_bonuses, int(self.subtotal)))
        return max(0, min(self.bonus_spin.value(), max_usable))

    def on_delivery_method_changed(self, index: int):
        self.address_stack.setCurrentIndex(index)
        self.update_summary_meta()

    def update_summary_meta(self):
        self.delivery_preview_label.setText(f"Доставка: {self.delivery_combo.currentText()}")
        self.payment_preview_label.setText(f"Оплата: {self.payment_combo.currentText()}")

    def _validate_phone(self, phone: str) -> bool:
        cleaned = re.sub(r"[\s\-\(\)]", "", phone.strip())
        return bool(re.match(r"^(\+?38)?0\d{9}$", cleaned))

    def _validate_email(self, email: str) -> bool:
        return bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email.strip()))

    def validate_and_accept(self):
        full_name = self.name_input.text().strip()
        phone = self.phone_input.text().strip()
        email = self.email_input.text().strip()
        delivery_method = self.delivery_combo.currentText()

        if len(full_name) < 3:
            QMessageBox.warning(self, "Помилка заповнення", "Введіть коректне ПІБ покупця (мінімум 3 символи).")
            self.name_input.setFocus()
            return

        if not phone or not self._validate_phone(phone):
            QMessageBox.warning(
                self, "Некоректний номер телефону",
                "Введіть коректний український номер телефону.\nПриклад: +380671234567 або 0671234567."
            )
            self.phone_input.setFocus()
            return

        if not email or not self._validate_email(email):
            QMessageBox.warning(
                self, "Некоректний Email",
                "Введіть коректну електронну пошту.\nПриклад: user@gmail.com"
            )
            self.email_input.setFocus()
            return

        if delivery_method == "Нова пошта":
            city = self.np_city_input.text().strip()
            branch = self.np_branch_input.text().strip()
            if not city or not branch:
                QMessageBox.warning(
                    self, "Помилка адреси доставки",
                    "Для доставки «Нова пошта» обов’язково вкажіть місто та номер відділення."
                )
                if not city:
                    self.np_city_input.setFocus()
                else:
                    self.np_branch_input.setFocus()
                return

        elif delivery_method == "Укрпошта":
            city = self.up_city_input.text().strip()
            branch = self.up_branch_input.text().strip()
            if not city or not branch:
                QMessageBox.warning(
                    self, "Помилка адреси доставки",
                    "Для доставки «Укрпошта» обов’язково вкажіть населений пункт та номер відділення / індекс."
                )
                if not city:
                    self.up_city_input.setFocus()
                else:
                    self.up_branch_input.setFocus()
                return

        self.accept()

    def get_formatted_delivery_address(self) -> str:
        method = self.delivery_combo.currentText()
        if method == "Нова пошта":
            return f"Нова пошта: м. {self.np_city_input.text().strip()}, {self.np_branch_input.text().strip()}"
        elif method == "Укрпошта":
            return f"Укрпошта: {self.up_city_input.text().strip()}, {self.up_branch_input.text().strip()}"
        else:
            return f"Самовивіз: {self.PICKUP_ADDRESS}"

    def get_client_data(self) -> Client:
        return Client(
            full_name=self.name_input.text().strip(),
            phone=self.phone_input.text().strip(),
            email=self.email_input.text().strip(),
            address=self.get_formatted_delivery_address()
        )

    def get_order_details(self) -> dict:
        return {
            "delivery_method": self.delivery_combo.currentText(),
            "delivery_address": self.get_formatted_delivery_address(),
            "payment_method": self.payment_combo.currentText(),
            "comment": self.comment_input.toPlainText().strip(),
            "bonus_used": self.get_bonus_used()
        }


class OrderSuccessDialog(QDialog):
    """Екран успішного оформлення замовлення з унікальним номером"""
    def __init__(self, order_id: int, client_name: str, delivery_address: str,
                 payment_method: str, total_amount: float, pdf_path: str,
                 bonus_used: int = 0, parent=None):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.setWindowTitle(f"Замовлення №{order_id} оформлено")
        self.resize(480, 380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(12)

        badge = QLabel("✅")
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet("font-size: 40px;")
        layout.addWidget(badge)

        title = QLabel("Замовлення успішно оформлено!")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 19px; font-weight: bold; color: #15803D;")
        layout.addWidget(title)

        order_num = QLabel(f"Унікальний номер замовлення: №{order_id}")
        order_num.setAlignment(Qt.AlignCenter)
        order_num.setStyleSheet("""
            background-color: #EFF6FF;
            color: #1D4ED8;
            border: 1px solid #BFDBFE;
            border-radius: 6px;
            padding: 8px;
            font-size: 15px;
            font-weight: bold;
        """)
        layout.addWidget(order_num)

        details_card = QFrame()
        details_card.setStyleSheet("""
            QFrame {
                background-color: #F8FAFC;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
            }
            QLabel {
                border: none;
                background: transparent;
                color: #1E293B;
                font-size: 13px;
            }
        """)
        card_layout = QVBoxLayout(details_card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(6)

        card_layout.addWidget(QLabel(f"<b>Покупець:</b> {client_name}"))
        card_layout.addWidget(QLabel(f"<b>Доставка:</b> {delivery_address}"))
        card_layout.addWidget(QLabel(f"<b>Оплата:</b> {payment_method}"))
        if bonus_used > 0:
            card_layout.addWidget(QLabel(f"<b>Списано бонусів:</b> {bonus_used} бонусів (-{bonus_used:.2f} грн)"))
        card_layout.addWidget(QLabel(f"<b>Сума до сплати:</b> {total_amount:.2f} грн"))
        layout.addWidget(details_card)

        note = QLabel("PDF-чек збережено та доступний в особистому кабінеті й розділі «Мої замовлення».")
        note.setWordWrap(True)
        note.setAlignment(Qt.AlignCenter)
        note.setStyleSheet("font-size: 12px; color: #475569;")
        layout.addWidget(note)

        btns_row = QHBoxLayout()
        btns_row.setSpacing(10)

        open_pdf_btn = QPushButton("📄 Відкрити PDF-чек")
        open_pdf_btn.setCursor(Qt.PointingHandCursor)
        open_pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: bold;
                padding: 8px 14px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #1D4ED8; }
        """)
        open_pdf_btn.clicked.connect(self.open_pdf)
        btns_row.addWidget(open_pdf_btn)

        ok_btn = QPushButton("Готово")
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #16A34A;
                color: #FFFFFF;
                font-weight: bold;
                padding: 8px 18px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #15803D; }
        """)
        ok_btn.clicked.connect(self.accept)
        btns_row.addWidget(ok_btn)

        layout.addLayout(btns_row)

    def open_pdf(self):
        if self.pdf_path and os.path.exists(self.pdf_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(self.pdf_path)))


class CatalogTab(QWidget):
    """Вкладка каталогу товарів"""
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
        