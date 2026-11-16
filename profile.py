import os
import re
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QLineEdit, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QUrl
from PyQt5.QtGui import QDesktopServices, QColor


class EditProfileDialog(QDialog):
    """Діалогове вікно редагування особистих даних покупця"""
    def __init__(self, db_manager, client_id: int, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.client_id = client_id
        self.setWindowTitle("Редагування профілю")
        self.resize(440, 310)
        self.init_ui()
        self.load_current_data()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #F8FAFC;
            }
            QLabel#FieldTitle {
                font-size: 12px;
                font-weight: bold;
                color: #334155;
            }
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 8px 10px;
                font-size: 13px;
                color: #0F172A;
            }
            QLineEdit:focus {
                border: 1px solid #2563EB;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        header = QLabel("Редагування особистих даних")
        header.setStyleSheet("font-size: 17px; font-weight: bold; color: #0F172A; margin-bottom: 4px;")
        layout.addWidget(header)

        lbl_name = QLabel("Ім’я та прізвище *")
        lbl_name.setObjectName("FieldTitle")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Введіть ім’я та прізвище")
        layout.addWidget(lbl_name)
        layout.addWidget(self.name_input)

        lbl_phone = QLabel("Номер телефону *")
        lbl_phone.setObjectName("FieldTitle")
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("+380671234567")
        layout.addWidget(lbl_phone)
        layout.addWidget(self.phone_input)

        lbl_email = QLabel("Електронна пошта *")
        lbl_email.setObjectName("FieldTitle")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("buyer@example.com")
        layout.addWidget(lbl_email)
        layout.addWidget(self.email_input)

        layout.addStretch()

        btns_row = QHBoxLayout()
        btns_row.setSpacing(10)

        cancel_btn = QPushButton("Скасувати")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #E2E8F0;
                color: #1E293B;
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #CBD5E1; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btns_row.addWidget(cancel_btn)

        btns_row.addStretch()

        save_btn = QPushButton("Зберегти зміни")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: bold;
                padding: 8px 18px;
                border: none;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #1D4ED8; }
        """)
        save_btn.clicked.connect(self.save_changes)
        btns_row.addWidget(save_btn)

        layout.addLayout(btns_row)

    def load_current_data(self):
        client = self.db.get_client_by_id(self.client_id)
        if client:
            if client.full_name and client.full_name != "Покупець":
                self.name_input.setText(client.full_name)
            else:
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
        self.resize(680, 500)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #F1F5F9; }
            QFrame#InfoCard {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # Заголовок та статус
        top_row = QHBoxLayout()
        title = QLabel(f"Замовлення №{self.order_data['order_id']}")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0F172A;")
        top_row.addWidget(title)
        top_row.addStretch()

        status = self.order_data.get("status", "Нове")
        status_lbl = QLabel(f"Статус: {status}")
        if status.strip().lower() == "доставлено":
            status_style = "background-color: #DCFCE7; color: #166534; border: 1px solid #86EFAC;"
        elif status.strip().lower() == "скасовано":
            status_style = "background-color: #FEE2E2; color: #991B1B; border: 1px solid #FCA5A5;"
        else:
            status_style = "background-color: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE;"
        status_lbl.setStyleSheet(f"{status_style} border-radius: 6px; padding: 5px 12px; font-weight: bold; font-size: 12px;")
        top_row.addWidget(status_lbl)
        layout.addLayout(top_row)

        # Картка з інформацією про доставку та оплату
        info_card = QFrame()
        info_card.setObjectName("InfoCard")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(14, 12, 14, 12)
        info_layout.setSpacing(5)

        info_layout.addWidget(QLabel(f"<b>Дата оформлення:</b> {self.order_data.get('order_date', '—')}"))
        info_layout.addWidget(QLabel(f"<b>Отримувач:</b> {self.order_data.get('client_name', '—')} ({self.order_data.get('phone', '—')})"))
        info_layout.addWidget(QLabel(f"<b>Спосіб доставки:</b> {self.order_data.get('delivery_method', 'Нова пошта')}"))
        info_layout.addWidget(QLabel(f"<b>Адреса / відділення:</b> {self.order_data.get('delivery_address') or 'Не вказано'}"))
        info_layout.addWidget(QLabel(f"<b>Спосіб оплати:</b> {self.order_data.get('payment_method', 'Оплата карткою')}"))
        if self.order_data.get("comment"):
            info_layout.addWidget(QLabel(f"<b>Коментар:</b> {self.order_data['comment']}"))

        layout.addWidget(info_card)

        # Таблиця товарів замовлення
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

        # Підсумок оплати та бонусів
        summary_card = QFrame()
        summary_card.setObjectName("InfoCard")
        sum_layout = QVBoxLayout(summary_card)
        sum_layout.setContentsMargins(14, 10, 14, 10)
        sum_layout.setSpacing(4)

        bonus_used = int(self.order_data.get("bonus_used", 0))
        total_amount = float(self.order_data.get("total_amount", 0.0))
        bonus_earned = int(self.order_data.get("bonus_earned", 0))
        bonus_awarded = int(self.order_data.get("bonus_awarded", 0))

        sum_layout.addWidget(QLabel(f"Вартість товарів: <b>{subtotal:.2f} грн</b>"))
        if bonus_used > 0:
            disc_lbl = QLabel(f"Використано бонусів (знижка): <b>-{bonus_used:.2f} грн</b> ({bonus_used} бонусів)")
            disc_lbl.setStyleSheet("color: #2563EB;")
            sum_layout.addWidget(disc_lbl)

        total_lbl = QLabel(f"Загальна сума замовлення: <b>{total_amount:.2f} грн</b>")
        total_lbl.setStyleSheet("font-size: 15px; color: #15803D;")
        sum_layout.addWidget(total_lbl)

        expected_bonus = int(total_amount // 100)
        if status.strip().lower() == "доставлено" and bonus_awarded:
            b_lbl = QLabel(f"🎁 Нараховано бонусів за замовлення: <b>+{bonus_earned} бонусів</b>")
            b_lbl.setStyleSheet("color: #166534; font-size: 12px;")
            sum_layout.addWidget(b_lbl)
        elif status.strip().lower() != "скасовано" and expected_bonus > 0:
            b_lbl = QLabel(f"ℹ️ Після отримання замовлення (статус «Доставлено») буде нараховано: <b>+{expected_bonus} бонусів</b>")
            b_lbl.setStyleSheet("color: #475569; font-size: 12px;")
            sum_layout.addWidget(b_lbl)

        layout.addWidget(summary_card)

        # Нижні кнопки
        btns_row = QHBoxLayout()
        receipt_path = self.order_data.get("receipt_path")
        if receipt_path and os.path.exists(receipt_path):
            pdf_btn = QPushButton("📄 Відкрити PDF-чек")
            pdf_btn.setCursor(Qt.PointingHandCursor)
            pdf_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2563EB;
                    color: #FFFFFF;
                    font-weight: bold;
                    padding: 7px 14px;
                    border: none;
                    border-radius: 6px;
                }
                QPushButton:hover { background-color: #1D4ED8; }
            """)
            pdf_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(receipt_path))))
            btns_row.addWidget(pdf_btn)

        btns_row.addStretch()

        close_btn = QPushButton("Закрити")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #E2E8F0;
                color: #1E293B;
                font-weight: bold;
                padding: 7px 18px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #CBD5E1; }
        """)
        close_btn.clicked.connect(self.accept)
        btns_row.addWidget(close_btn)

        layout.addLayout(btns_row)


class PersonalAccountWidget(QWidget):
    """
    Головна сторінка особистого кабінету покупця:
    1. Особисті дані покупця + редагування профілю
    2. Блок «Мої бонуси»
    3. Блок «Мої замовлення» з детальним переглядом
    """
    back_to_store_requested = pyqtSignal()
    profile_updated = pyqtSignal()

    def __init__(self, db_manager, get_client_id_func, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.get_client_id = get_client_id_func
        self.orders_cache = []
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QWidget#PersonalAccountRoot {
                background-color: #F1F5F9;
            }
            QFrame#SectionCard {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 10px;
            }
            QLabel#CardTitle {
                font-size: 16px;
                font-weight: bold;
                color: #0F172A;
            }
        """)
        self.setObjectName("PersonalAccountRoot")

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 12, 16, 12)
        root_layout.setSpacing(12)

        # Верхня панель навігації особистого кабінету
        nav_bar = QHBoxLayout()
        self.back_btn = QPushButton("← Повернутися до магазину")
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 7px 14px;
                font-weight: bold;
                color: #1E293B;
            }
            QPushButton:hover { background-color: #E2E8F0; }
        """)
        self.back_btn.clicked.connect(self.back_to_store_requested.emit)
        nav_bar.addWidget(self.back_btn)

        nav_bar.addSpacing(12)
        page_title = QLabel("Особистий кабінет покупця")
        page_title.setStyleSheet("font-size: 19px; font-weight: bold; color: #0F172A;")
        nav_bar.addWidget(page_title)
        nav_bar.addStretch()

        self.refresh_btn = QPushButton("↻ Оновити")
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 7px 12px;
                color: #334155;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #E2E8F0; }
        """)
        self.refresh_btn.clicked.connect(self.refresh_data)
        nav_bar.addWidget(self.refresh_btn)

        root_layout.addLayout(nav_bar)

        # Прокручувана область вмісту особистого кабінету
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(0, 0, 6, 0)
        content_layout.setSpacing(14)

        # ==========================================
        # 1. БЛОК: ОСОБИСТІ ДАНІ ПОКУПЦЯ
        # ==========================================
        profile_card = QFrame()
        profile_card.setObjectName("SectionCard")
        profile_layout = QVBoxLayout(profile_card)
        profile_layout.setContentsMargins(18, 16, 18, 16)
        profile_layout.setSpacing(12)

        prof_header = QHBoxLayout()
        prof_title = QLabel("👤 Особисті дані покупця")
        prof_title.setObjectName("CardTitle")
        prof_header.addWidget(prof_title)
        prof_header.addStretch()

        self.edit_profile_btn = QPushButton("✏️ Редагувати профіль")
        self.edit_profile_btn.setCursor(Qt.PointingHandCursor)
        self.edit_profile_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 13px;
                padding: 7px 16px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #1D4ED8; }
        """)
        self.edit_profile_btn.clicked.connect(self.open_edit_profile)
        prof_header.addWidget(self.edit_profile_btn)
        profile_layout.addLayout(prof_header)

        # Сітка полів профілю
        fields_grid = QGridLayout()
        fields_grid.setHorizontalSpacing(24)
        fields_grid.setVerticalSpacing(6)

        lbl_name_cap = QLabel("Ім’я та прізвище")
        lbl_name_cap.setStyleSheet("font-size: 12px; color: #64748B; font-weight: bold;")
        self.name_val_label = QLabel("—")
        self.name_val_label.setStyleSheet("font-size: 15px; color: #0F172A; font-weight: bold;")

        lbl_phone_cap = QLabel("Номер телефону")
        lbl_phone_cap.setStyleSheet("font-size: 12px; color: #64748B; font-weight: bold;")
        self.phone_val_label = QLabel("Не вказано")
        self.phone_val_label.setStyleSheet("font-size: 15px; color: #0F172A;")

        lbl_email_cap = QLabel("Електронна пошта")
        lbl_email_cap.setStyleSheet("font-size: 12px; color: #64748B; font-weight: bold;")
        self.email_val_label = QLabel("Не вказано")
        self.email_val_label.setStyleSheet("font-size: 15px; color: #0F172A;")

        fields_grid.addWidget(lbl_name_cap, 0, 0)
        fields_grid.addWidget(self.name_val_label, 1, 0)

        fields_grid.addWidget(lbl_phone_cap, 0, 1)
        fields_grid.addWidget(self.phone_val_label, 1, 1)

        fields_grid.addWidget(lbl_email_cap, 0, 2)
        fields_grid.addWidget(self.email_val_label, 1, 2)

        fields_grid.setColumnStretch(0, 2)
        fields_grid.setColumnStretch(1, 1)
        fields_grid.setColumnStretch(2, 2)

        profile_layout.addLayout(fields_grid)
        content_layout.addWidget(profile_card)

        # ==========================================
        # 2. БЛОК: МОЇ БОНУСИ (НА ГОЛОВНІЙ СТОРІНЦІ КАБІНЕТУ)
        # ==========================================
        bonus_card = QFrame()
        bonus_card.setObjectName("SectionCard")
        bonus_layout = QVBoxLayout(bonus_card)
        bonus_layout.setContentsMargins(18, 16, 18, 16)
        bonus_layout.setSpacing(12)

        bonus_header = QHBoxLayout()
        bonus_title = QLabel("🎁 Мої бонуси")
        bonus_title.setObjectName("CardTitle")
        bonus_header.addWidget(bonus_title)
        bonus_header.addStretch()

        bonus_rule_badge = QLabel("1 бонус = 1 грн знижки  •  +1 бонус за кожні 100 грн доставленого замовлення")
        bonus_rule_badge.setStyleSheet("""
            background-color: #FEF9C3;
            color: #854D0E;
            border: 1px solid #FDE047;
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 12px;
            font-weight: bold;
        """)
        bonus_header.addWidget(bonus_rule_badge)
        bonus_layout.addLayout(bonus_header)

        # 4 картки показників бонусного балансу
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(12)

        self.current_bonus_val = self._create_metric_box(
            metrics_row,
            caption="Поточний баланс бонусів",
            initial_value="0 бонусів",
            bg_color="#EFF6FF",
            border_color="#BFDBFE",
            val_color="#1D4ED8"
        )
        self.uah_equiv_val = self._create_metric_box(
            metrics_row,
            caption="Грошовий еквівалент знижки",
            initial_value="0.00 грн",
            bg_color="#F0FDF4",
            border_color="#BBF7D0",
            val_color="#15803D"
        )
        self.total_earned_val = self._create_metric_box(
            metrics_row,
            caption="Накопичено всього бонусів",
            initial_value="0 бонусів",
            bg_color="#F8FAFC",
            border_color="#E2E8F0",
            val_color="#0F172A"
        )
        self.total_spent_val = self._create_metric_box(
            metrics_row,
            caption="Використано бонусів",
            initial_value="0 бонусів",
            bg_color="#F8FAFC",
            border_color="#E2E8F0",
            val_color="#475569"
        )

        bonus_layout.addLayout(metrics_row)
        content_layout.addWidget(bonus_card)

        # ==========================================
        # 3. БЛОК: МОЇ ЗАМОВЛЕННЯ (ІСТОРІЯ ЗАМОВЛЕНЬ)
        # ==========================================
        orders_card = QFrame()
        orders_card.setObjectName("SectionCard")
        orders_layout = QVBoxLayout(orders_card)
        orders_layout.setContentsMargins(18, 16, 18, 16)
        orders_layout.setSpacing(10)

        orders_header = QHBoxLayout()
        orders_title = QLabel("📦 Мої замовлення")
        orders_title.setObjectName("CardTitle")
        orders_header.addWidget(orders_title)
        orders_header.addStretch()

        self.orders_count_label = QLabel("Всього замовлень: 0")
        self.orders_count_label.setStyleSheet("color: #475569; font-weight: bold; font-size: 13px;")
        orders_header.addWidget(self.orders_count_label)
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
        self.orders_table.setColumnWidth(6, 125)
        self.orders_table.verticalHeader().setVisible(False)
        self.orders_table.verticalHeader().setDefaultSectionSize(42)
        self.orders_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.orders_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.orders_table.setMinimumHeight(260)
        self.orders_table.cellDoubleClicked.connect(self.on_order_double_clicked)

        orders_layout.addWidget(self.orders_table)
        content_layout.addWidget(orders_card)

        scroll.setWidget(scroll_content)
        root_layout.addWidget(scroll)

    def _create_metric_box(self, parent_layout, caption: str, initial_value: str,
                           bg_color: str, border_color: str, val_color: str) -> QLabel:
        box = QFrame()
        box.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(14, 12, 14, 12)
        box_layout.setSpacing(4)

        cap_lbl = QLabel(caption)
        cap_lbl.setStyleSheet("font-size: 12px; color: #475569; font-weight: bold;")
        val_lbl = QLabel(initial_value)
        val_lbl.setStyleSheet(f"font-size: 18px; color: {val_color}; font-weight: bold;")

        box_layout.addWidget(cap_lbl)
        box_layout.addWidget(val_lbl)
        parent_layout.addWidget(box, stretch=1)
        return val_lbl

    def refresh_data(self):
        """Завантаження актуальних даних профілю, бонусів та замовлень поточного покупця"""
        client_id = self.get_client_id()
        client = self.db.ensure_client_profile(client_id)

        # 1. Особисті дані
        self.name_val_label.setText(client.full_name or "Покупець")
        self.phone_val_label.setText(client.phone if client.phone else "Не вказано")
        self.email_val_label.setText(client.email if client.email else "Не вказано")

        # 2. Бонусний баланс (із автоматичною синхронізацією доставлених замовлень)
        bonus_info = self.db.get_client_bonus_info(client_id)
        cur_bal = bonus_info["current_balance"]
        uah_eq = bonus_info["uah_equivalent"]
        earned = bonus_info["total_earned"]
        spent = bonus_info["total_spent"]

        self.current_bonus_val.setText(f"{cur_bal} бонусів")
        self.uah_equiv_val.setText(f"{uah_eq:.2f} грн")
        self.total_earned_val.setText(f"{earned} бонусів")
        self.total_spent_val.setText(f"{spent} бонусів")

        # 3. Історія замовлень поточного покупця
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
            if status.strip().lower() == "доставлено":
                status_item.setForeground(QColor("#15803D"))
            elif status.strip().lower() == "скасовано":
                status_item.setForeground(QColor("#DC2626"))
            else:
                status_item.setForeground(QColor("#1D4ED8"))

            self.orders_table.setItem(row, 0, id_item)
            self.orders_table.setItem(row, 1, date_item)
            self.orders_table.setItem(row, 2, items_item)
            self.orders_table.setItem(row, 3, qty_item)
            self.orders_table.setItem(row, 4, sum_item)
            self.orders_table.setItem(row, 5, status_item)

            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(6, 4, 6, 4)

            details_btn = QPushButton("Детальніше")
            details_btn.setCursor(Qt.PointingHandCursor)
            details_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F1F5F9;
                    border: 1px solid #CBD5E1;
                    border-radius: 5px;
                    padding: 4px 10px;
                    font-weight: bold;
                    font-size: 12px;
                    color: #0F172A;
                }
                QPushButton:hover {
                    background-color: #2563EB;
                    color: #FFFFFF;
                    border-color: #2563EB;
                }
            """)
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
        