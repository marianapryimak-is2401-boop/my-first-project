import inspect
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QWidget, QGroupBox, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from classes import OrderItem


class CartItemCard(QFrame):
    """Вертикальна картка окремого товару в кошику"""
    increase_requested = pyqtSignal(int)
    decrease_requested = pyqtSignal(int)
    remove_requested = pyqtSignal(int)

    def __init__(self, index: int, product, quantity: int, parent=None):
        super().__init__(parent)
        self.index = index
        self.product = product
        self.quantity = quantity

        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(12)

        # Ліва частина: назва, бренд, ціна за одиницю
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        title_lbl = QLabel(f"<b>{self.product.title}</b>")
        title_lbl.setWordWrap(True)
        info_layout.addWidget(title_lbl)

        brand_text = self.product.brand if getattr(self.product, "brand", None) else "Не вказано"
        meta_lbl = QLabel(f"Бренд: {brand_text}  |  Ціна за 1 од.: {self.product.price:.2f} грн")
        info_layout.addWidget(meta_lbl)

        main_layout.addLayout(info_layout, stretch=1)

        # Права частина: керування кількістю (− / +), сума за позицією, видалення
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)

        self.minus_btn = QPushButton("−")
        self.minus_btn.setFixedSize(30, 30)
        self.minus_btn.setCursor(Qt.PointingHandCursor)
        self.minus_btn.setEnabled(self.quantity > 1)
        self.minus_btn.clicked.connect(lambda: self.decrease_requested.emit(self.index))
        controls_layout.addWidget(self.minus_btn)

        self.qty_lbl = QLabel(f"<b>{self.quantity} шт.</b>")
        self.qty_lbl.setAlignment(Qt.AlignCenter)
        self.qty_lbl.setMinimumWidth(48)
        controls_layout.addWidget(self.qty_lbl)

        self.plus_btn = QPushButton("+")
        self.plus_btn.setFixedSize(30, 30)
        self.plus_btn.setCursor(Qt.PointingHandCursor)
        self.plus_btn.clicked.connect(lambda: self.increase_requested.emit(self.index))
        controls_layout.addWidget(self.plus_btn)

        item_total = self.product.price * self.quantity
        self.item_total_lbl = QLabel(f"<b>{item_total:.2f} грн</b>")
        self.item_total_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.item_total_lbl.setMinimumWidth(110)
        controls_layout.addWidget(self.item_total_lbl)

        self.remove_btn = QPushButton("Видалити")
        self.remove_btn.setCursor(Qt.PointingHandCursor)
        self.remove_btn.clicked.connect(lambda: self.remove_requested.emit(self.index))
        controls_layout.addWidget(self.remove_btn)

        main_layout.addLayout(controls_layout)


class CartDialog(QDialog):
    """Діалогове вікно кошика з вертикальними картками товарів та розрахунком бонусів"""
    def __init__(self, cart_items, db_manager, parent=None, client_id=None):
        super().__init__(parent)
        self.cart = cart_items
        self.db = db_manager
        self.client_id = client_id

        if self.client_id is None and parent is not None and hasattr(parent, "get_client_id"):
            self.client_id = parent.get_client_id()

        self.setWindowTitle("Кошик покупок")
        self.resize(740, 560)
        self.init_ui()
        self.refresh_cart_ui()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(14, 12, 14, 12)
        root_layout.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.addWidget(QLabel("<b>Товари у кошику</b>"))
        header_row.addStretch()
        self.items_count_lbl = QLabel("Позицій: 0")
        header_row.addWidget(self.items_count_lbl)
        root_layout.addLayout(header_row)

        # Прокручувана область із вертикальними картками товарів
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(2, 2, 6, 2)
        self.cards_layout.setSpacing(8)
        self.scroll_area.setWidget(self.cards_container)

        root_layout.addWidget(self.scroll_area, stretch=1)

        # Підсумок замовлення та нарахування бонусів
        summary_box = QGroupBox("Підсумок замовлення")
        summary_layout = QVBoxLayout(summary_box)
        summary_layout.setSpacing(6)

        self.total_sum_lbl = QLabel("<b>Загальна сума замовлення: 0.00 грн</b>")
        total_font = self.total_sum_lbl.font()
        total_font.setPointSize(total_font.pointSize() + 1)
        self.total_sum_lbl.setFont(total_font)
        summary_layout.addWidget(self.total_sum_lbl)

        self.expected_bonus_lbl = QLabel(
            "Бонуси за це замовлення: <b>+0 бонусів</b> (1 бонус за кожні 100 грн замовлення)"
        )
        summary_layout.addWidget(self.expected_bonus_lbl)

        self.bonus_note_lbl = QLabel(
            "1 бонус = 1 грн знижки на наступне замовлення. "
            "Бонуси нараховуються тільки після зміни статусу замовлення на «Доставлено», а не під час оформлення."
        )
        self.bonus_note_lbl.setWordWrap(True)
        summary_layout.addWidget(self.bonus_note_lbl)

        root_layout.addWidget(summary_box)

        # Нижня панель кнопок
        bottom_row = QHBoxLayout()

        self.close_btn = QPushButton("Закрити")
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.clicked.connect(self.reject)
        bottom_row.addWidget(self.close_btn)

        bottom_row.addStretch()

        self.checkout_btn = QPushButton("Оформити замовлення")
        self.checkout_btn.setCursor(Qt.PointingHandCursor)
        self.checkout_btn.clicked.connect(self.checkout)
        bottom_row.addWidget(self.checkout_btn)

        root_layout.addLayout(bottom_row)

    def refresh_cart_ui(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        total_sum = 0.0
        total_qty = 0

        if not self.cart:
            empty_lbl = QLabel("Кошик порожній. Додайте товари з каталогу.")
            empty_lbl.setAlignment(Qt.AlignCenter)
            self.cards_layout.addWidget(empty_lbl)
            self.cards_layout.addStretch()
            self.checkout_btn.setEnabled(False)
        else:
            for idx, (prod, qty) in enumerate(self.cart):
                card = CartItemCard(idx, prod, qty, parent=self.cards_container)
                card.increase_requested.connect(self.increase_item_qty)
                card.decrease_requested.connect(self.decrease_item_qty)
                card.remove_requested.connect(self.remove_item)
                self.cards_layout.addWidget(card)

                total_sum += prod.price * qty
                total_qty += qty

            self.cards_layout.addStretch()
            self.checkout_btn.setEnabled(True)

        expected_bonuses = int(total_sum // 100)

        self.items_count_lbl.setText(f"Товарів: {total_qty} шт.")
        self.total_sum_lbl.setText(f"<b>Загальна сума замовлення: {total_sum:.2f} грн</b>")
        self.expected_bonus_lbl.setText(
            f"Бонуси за це замовлення: <b>+{expected_bonuses} бонусів</b> "
            f"(1 бонус за кожні 100 грн замовлення)"
        )

    def increase_item_qty(self, index: int):
        if not (0 <= index < len(self.cart)):
            return

        prod, qty = self.cart[index]
        fresh_prod = self.db.get_product_by_id(prod.product_id) if hasattr(self.db, "get_product_by_id") else prod
        max_stock = fresh_prod.stock_quantity if fresh_prod else prod.stock_quantity

        if qty + 1 > max_stock:
            QMessageBox.warning(
                self,
                "Обмеження складу",
                f"Недостатньо товару «{prod.title}» на складі.\nМаксимально доступно: {max_stock} шт."
            )
            return

        self.cart[index] = (fresh_prod or prod, qty + 1)
        self.refresh_cart_ui()

    def decrease_item_qty(self, index: int):
        if not (0 <= index < len(self.cart)):
            return

        prod, qty = self.cart[index]
        if qty > 1:
            self.cart[index] = (prod, qty - 1)
            self.refresh_cart_ui()

    def remove_item(self, index: int):
        if 0 <= index < len(self.cart):
            self.cart.pop(index)
            self.refresh_cart_ui()

    def checkout(self):
        if not self.cart:
            QMessageBox.warning(self, "Кошик порожній", "Додайте товари до кошика перед оформленням замовлення.")
            return

        # Перевірка актуальної наявності на складі перед оформленням
        if hasattr(self.db, "get_product_by_id"):
            for prod, qty in self.cart:
                fresh_prod = self.db.get_product_by_id(prod.product_id)
                if not fresh_prod or fresh_prod.stock_quantity < qty:
                    avail = fresh_prod.stock_quantity if fresh_prod else 0
                    QMessageBox.warning(
                        self,
                        "Недостатньо товару",
                        f"Товар «{prod.title}» доступний у кількості {avail} шт."
                    )
                    return

        from catalog_tab import OrderDialog, OrderSuccessDialog

        order_dialog = OrderDialog(
            cart_items=self.cart,
            db_manager=self.db,
            client_id=self.client_id,
            parent=self
        )
        if order_dialog.exec_() != QDialog.Accepted:
            return

        client_data = order_dialog.get_client_data()
        order_details = order_dialog.get_order_details()

        subtotal = sum(prod.price * qty for prod, qty in self.cart)
        bonus_used = int(order_details.get("bonus_used", 0))
        final_total = max(0.0, subtotal - bonus_used)
        bonus_earned = int(final_total // 100)

        active_client_id = self.client_id
        if active_client_id is not None:
            if hasattr(self.db, "update_client_profile"):
                self.db.update_client_profile(
                    client_id=active_client_id,
                    full_name=client_data.full_name,
                    phone=client_data.phone,
                    email=client_data.email
                )
        elif hasattr(self.db, "add_client"):
            active_client_id = self.db.add_client(client_data)

        order_items = [
            OrderItem(product_id=prod.product_id, quantity=qty, price_per_unit=prod.price)
            for prod, qty in self.cart
        ]

        order_id = self._save_order_to_db(
            active_client_id=active_client_id,
            client_data=client_data,
            order_items=order_items,
            final_total=final_total,
            order_details=order_details,
            bonus_used=bonus_used,
            bonus_earned=bonus_earned
        )

        pdf_path = self._generate_receipt(
            order_id=order_id,
            client_data=client_data,
            final_total=final_total,
            order_details=order_details,
            bonus_used=bonus_used
        )

        if pdf_path:
            for method_name in ("update_order_receipt", "set_order_receipt_path", "save_order_receipt"):
                if hasattr(self.db, method_name):
                    getattr(self.db, method_name)(order_id, pdf_path)
                    break

        success_dialog = OrderSuccessDialog(
            order_id=order_id,
            client_name=client_data.full_name,
            delivery_address=order_details["delivery_address"],
            payment_method=order_details["payment_method"],
            total_amount=final_total,
            pdf_path=pdf_path or "",
            bonus_used=bonus_used,
            parent=self
        )
        success_dialog.exec_()

        self.cart.clear()
        self.accept()

    def _save_order_to_db(self, active_client_id, client_data, order_items,
                          final_total, order_details, bonus_used, bonus_earned):
        sig = inspect.signature(self.db.create_order)
        params = sig.parameters
        kwargs = {}

        if "client_id" in params:
            kwargs["client_id"] = active_client_id
        if "client_data" in params:
            kwargs["client_data"] = client_data
        elif "client" in params:
            kwargs["client"] = client_data
        if "items" in params:
            kwargs["items"] = order_items
        elif "order_items" in params:
            kwargs["order_items"] = order_items
        elif "cart_items" in params:
            kwargs["cart_items"] = self.cart
        if "total_amount" in params:
            kwargs["total_amount"] = final_total
        if "delivery_method" in params:
            kwargs["delivery_method"] = order_details["delivery_method"]
        if "delivery_address" in params:
            kwargs["delivery_address"] = order_details["delivery_address"]
        if "payment_method" in params:
            kwargs["payment_method"] = order_details["payment_method"]
        if "comment" in params:
            kwargs["comment"] = order_details["comment"]
        if "bonus_used" in params:
            kwargs["bonus_used"] = bonus_used
        if "bonus_earned" in params:
            kwargs["bonus_earned"] = bonus_earned
        if "order_details" in params:
            kwargs["order_details"] = order_details

        return self.db.create_order(**kwargs)

    def _generate_receipt(self, order_id, client_data, final_total, order_details, bonus_used):
        try:
            from receipt_generator import ReceiptGenerator
        except ImportError:
            return None

        generator = ReceiptGenerator()
        gen_method = getattr(generator, "generate_receipt", None)
        if not callable(gen_method):
            return None

        sig = inspect.signature(gen_method)
        params = sig.parameters
        kwargs = {}

        if "order_id" in params:
            kwargs["order_id"] = order_id
        if "client" in params:
            kwargs["client"] = client_data
        elif "client_data" in params:
            kwargs["client_data"] = client_data
        elif "client_name" in params:
            kwargs["client_name"] = client_data.full_name
        if "cart_items" in params:
            kwargs["cart_items"] = self.cart
        elif "items" in params:
            kwargs["items"] = self.cart
        if "total_amount" in params:
            kwargs["total_amount"] = final_total
        if "delivery_method" in params:
            kwargs["delivery_method"] = order_details["delivery_method"]
        if "delivery_address" in params:
            kwargs["delivery_address"] = order_details["delivery_address"]
        if "payment_method" in params:
            kwargs["payment_method"] = order_details["payment_method"]
        if "bonus_used" in params:
            kwargs["bonus_used"] = bonus_used

        return gen_method(**kwargs)
    