import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, 
    QTableWidget, QTableWidgetItem, QPushButton, 
    QHeaderView, QMessageBox
)
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices
from receipt_generator import generate_pdf_receipt


class OrdersTab(QWidget):
    """Вкладка перегляду замовлень з розмежуванням доступу та відкриттям PDF-чеків"""
    def __init__(self, db_manager, client_id=None, is_admin=False):
        super().__init__()
        self.db = db_manager
        self.client_id = client_id
        self.is_admin = is_admin
        self.init_ui()

    def set_client_id(self, client_id):
        self.client_id = client_id
        self.load_orders()

    def init_ui(self):
        layout = QVBoxLayout(self)

        title_text = "<b>Усі замовлення клієнтів:</b>" if self.is_admin else "<b>Мої замовлення:</b>"
        self.title_label = QLabel(title_text)
        layout.addWidget(self.title_label)

        self.orders_table = QTableWidget()
        self.orders_table.setColumnCount(7)
        self.orders_table.setHorizontalHeaderLabels([
            "№ Замовлення", "Клієнт", "Телефон", "Дата", "Статус", "Сума (грн)", "Чек"
        ])
        self.orders_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.orders_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.orders_table)

        self.refresh_btn = QPushButton("Оновити список")
        self.refresh_btn.clicked.connect(self.load_orders)
        layout.addWidget(self.refresh_btn)

        self.load_orders()

    def load_orders(self):
        """Завантаження тільки власних замовлень (для клієнта) або всіх (для адміна)"""
        orders = self.db.get_orders(client_id=self.client_id, is_admin=self.is_admin)

        self.orders_table.setRowCount(len(orders))
        for row, order in enumerate(orders):
            order_id = order[0]
            client_name = order[1]
            phone = order[2]
            order_date = str(order[3])
            status = order[4]
            total_amount = order[5]
            receipt_path = order[6]
            order_client_id = order[7]

            self.orders_table.setItem(row, 0, QTableWidgetItem(str(order_id)))
            self.orders_table.setItem(row, 1, QTableWidgetItem(client_name))
            self.orders_table.setItem(row, 2, QTableWidgetItem(phone))
            self.orders_table.setItem(row, 3, QTableWidgetItem(order_date))
            self.orders_table.setItem(row, 4, QTableWidgetItem(status))
            self.orders_table.setItem(row, 5, QTableWidgetItem(f"{total_amount:.2f}"))

            # Стовпець "Чек" із кнопкою перегляду
            btn_receipt = QPushButton("📄 Переглянути чек")
            btn_receipt.clicked.connect(
                lambda checked, oid=order_id, rpath=receipt_path, ocid=order_client_id: 
                self.open_receipt(oid, rpath, ocid)
            )
            self.orders_table.setCellWidget(row, 6, btn_receipt)

    def open_receipt(self, order_id: int, receipt_path: str, order_client_id: int):
        """Відкриття чека з перевіркою прав доступу та відновленням у разі відсутності файлу"""
        # Захист доступу: клієнт не може відкрити чужий чек
        if not self.is_admin and self.client_id != order_client_id:
            QMessageBox.critical(self, "Помилка доступу", "Ви не можете переглядати чеки інших користувачів!")
            return

        target_path = receipt_path

        # Якщо файл вилучено або шлях порожній — відновлюємо чек
        if not target_path or not os.path.exists(target_path):
            order_info = self.db.get_order_full_info(order_id)
            if not order_info:
                QMessageBox.critical(self, "Помилка", "Замовлення не знайдено в базі даних.")
                return

            target_path = generate_pdf_receipt(
                order_id=order_info["order_id"],
                client_name=order_info["client_name"],
                phone=order_info["phone"],
                order_date=order_info["order_date"],
                status=order_info["status"],
                total_amount=order_info["total_amount"],
                items=order_info["items"]
            )
            self.db.update_order_receipt_path(order_id, target_path)

        abs_path = os.path.abspath(target_path)
        QDesktopServices.openUrl(QUrl.fromLocalFile(abs_path))
        