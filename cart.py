from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QTableWidget, QTableWidgetItem, QPushButton, 
    QHeaderView, QMessageBox, QSpinBox
)
from classes import OrderItem
from receipt_generator import generate_pdf_receipt


class CartDialog(QDialog):
    """Вікно кошика покупок"""
    def __init__(self, cart, db_manager, parent=None):
        super().__init__(parent)
        self.cart = cart
        self.db = db_manager
        self.setWindowTitle("Кошик покупок")
        self.resize(650, 420)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(5)
        self.cart_table.setHorizontalHeaderLabels(["ID", "Назва товару", "Ціна за од.", "Кількість", "Загальна сума"])
        self.cart_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cart_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.cart_table)

        edit_layout = QHBoxLayout()
        edit_layout.addWidget(QLabel("Кількість:"))
        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 1000)
        edit_layout.addWidget(self.qty_spin)

        self.update_qty_btn = QPushButton("Змінити кількість")
        self.update_qty_btn.clicked.connect(self.update_quantity)
        edit_layout.addWidget(self.update_qty_btn)

        self.remove_item_btn = QPushButton("Видалити з кошика")
        self.remove_item_btn.clicked.connect(self.remove_item)
        edit_layout.addWidget(self.remove_item_btn)

        layout.addLayout(edit_layout)

        self.total_label = QLabel("<b>Загальна сума: 0.00 грн</b>")
        layout.addWidget(self.total_label)

        bottom_layout = QHBoxLayout()

        self.checkout_btn = QPushButton("Оформити замовлення")
        self.checkout_btn.clicked.connect(self.checkout)
        bottom_layout.addWidget(self.checkout_btn)

        self.close_btn = QPushButton("Закрити")
        self.close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(self.close_btn)

        layout.addLayout(bottom_layout)

        self.cart_table.itemSelectionChanged.connect(self.on_selection_changed)
        self.refresh_cart_table()

    def refresh_cart_table(self):
        self.cart_table.setRowCount(len(self.cart))
        total = 0.0
        for row, (prod, qty) in enumerate(self.cart):
            item_total = prod.price * qty
            total += item_total
            self.cart_table.setItem(row, 0, QTableWidgetItem(str(prod.product_id)))
            self.cart_table.setItem(row, 1, QTableWidgetItem(prod.title))
            self.cart_table.setItem(row, 2, QTableWidgetItem(f"{prod.price:.2f} грн"))
            self.cart_table.setItem(row, 3, QTableWidgetItem(str(qty)))
            self.cart_table.setItem(row, 4, QTableWidgetItem(f"{item_total:.2f} грн"))

        self.total_label.setText(f"<b>Загальна сума: {total:.2f} грн</b>")

    def on_selection_changed(self):
        selected = self.cart_table.currentRow()
        if selected >= 0 and selected < len(self.cart):
            _, qty = self.cart[selected]
            self.qty_spin.setValue(qty)

    def update_quantity(self):
        selected = self.cart_table.currentRow()
        if selected < 0 or selected >= len(self.cart):
            QMessageBox.warning(self, "Увага", "Оберіть товар у кошику.")
            return
        
        prod, _ = self.cart[selected]
        new_qty = self.qty_spin.value()
        if new_qty > prod.stock_quantity:
            QMessageBox.warning(self, "Помилка", f"Недостатня кількість на складі (Доступно: {prod.stock_quantity}).")
            return
        
        self.cart[selected] = (prod, new_qty)
        self.refresh_cart_table()

    def remove_item(self):
        selected = self.cart_table.currentRow()
        if selected < 0 or selected >= len(self.cart):
            QMessageBox.warning(self, "Увага", "Оберіть товар у кошику.")
            return
        
        self.cart.pop(selected)
        self.refresh_cart_table()

    def checkout(self):
        if not self.cart:
            QMessageBox.warning(self, "Помилка", "Кошик порожній.")
            return

        from catalog_tab import OrderDialog

        dialog = OrderDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            client = dialog.get_client_data()
            if not client.full_name or not client.phone or not client.address:
                QMessageBox.warning(self, "Помилка", "Заповніть обов'язкові поля (ПІБ, Телефон, Адреса).")
                return

            order_items = [
                OrderItem(product_id=prod.product_id, quantity=qty, price_per_unit=prod.price)
                for prod, qty in self.cart
            ]

            order_id, client_id = self.db.create_order(client, order_items)
            order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            receipt_items = [
                {"title": prod.title, "quantity": qty, "price_per_unit": prod.price}
                for prod, qty in self.cart
            ]
            total_amount = sum(p.price * q for p, q in self.cart)

            pdf_path = generate_pdf_receipt(
                order_id=order_id,
                client_name=client.full_name,
                phone=client.phone,
                order_date=order_date,
                status="Нове",
                total_amount=total_amount,
                items=receipt_items
            )

            self.db.update_order_receipt_path(order_id, pdf_path)

            # Передача нового client_id у головне вікно клієнта
            parent_widget = self.parent()
            while parent_widget and not hasattr(parent_widget, 'set_client_id'):
                parent_widget = parent_widget.parent()
            if parent_widget and hasattr(parent_widget, 'set_client_id'):
                parent_widget.set_client_id(client_id)

            QMessageBox.information(
                self, "Успіх", 
                f"Замовлення №{order_id} успішно створено!\nЧек збережено: {pdf_path}"
            )
            self.cart.clear()
            self.refresh_cart_table()
            
            if self.parent() and hasattr(self.parent(), 'load_products'):
                self.parent().load_products()
                self.parent().update_cart_btn_text()
            
            self.accept()
            