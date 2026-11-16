from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QPushButton,
    QHeaderView, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal


class FavoritesTab(QWidget):
    """Вкладка «Обране» в особистому кабінеті покупця"""
    open_product_requested = pyqtSignal(int)
    favorite_removed = pyqtSignal(int)

    def __init__(self, db_manager, get_client_id_func, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.get_client_id = get_client_id_func
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        title_label = QLabel("<b>❤️ Мої обрані товари</b>")
        title_label.setStyleSheet("font-size: 16px; color: #0F172A;")
        header_row.addWidget(title_label)
        header_row.addStretch()

        self.count_label = QLabel("Товарів у списку: 0")
        self.count_label.setStyleSheet("color: #475569; font-weight: bold;")
        header_row.addWidget(self.count_label)
        layout.addLayout(header_row)

        self.favorites_table = QTableWidget()
        self.favorites_table.setColumnCount(5)
        self.favorites_table.setHorizontalHeaderLabels([
            "Назва товару", "Бренд", "Ціна (грн)", "Наявність", "Дії"
        ])
        self.favorites_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.favorites_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.favorites_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.favorites_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.favorites_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.favorites_table.setColumnWidth(4, 270)
        self.favorites_table.verticalHeader().setDefaultSectionSize(42)
        self.favorites_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.favorites_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.favorites_table.cellDoubleClicked.connect(self.on_row_double_clicked)
        layout.addWidget(self.favorites_table)

        self.load_favorites()

    def load_favorites(self):
        """Завантаження списку обраного поточного користувача з SQLite"""
        client_id = self.get_client_id()
        products = self.db.get_favorite_products(client_id)
        self.count_label.setText(f"Товарів у списку: {len(products)}")

        self.favorites_table.setRowCount(len(products))
        for row, prod in enumerate(products):
            title_item = QTableWidgetItem(prod.title)
            title_item.setData(Qt.UserRole, prod.product_id)

            brand_item = QTableWidgetItem(prod.brand)
            price_item = QTableWidgetItem(f"{prod.price:.2f} грн")

            if prod.stock_quantity > 0:
                stock_text = f"В наявності ({prod.stock_quantity} шт.)"
                stock_item = QTableWidgetItem(stock_text)
                stock_item.setForeground(Qt.darkGreen)
            else:
                stock_item = QTableWidgetItem("Немає в наявності")
                stock_item.setForeground(Qt.red)

            self.favorites_table.setItem(row, 0, title_item)
            self.favorites_table.setItem(row, 1, brand_item)
            self.favorites_table.setItem(row, 2, price_item)
            self.favorites_table.setItem(row, 3, stock_item)

            # Кнопки дій у рядку: перехід на сторінку товару та видалення з обраного
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 3, 4, 3)
            actions_layout.setSpacing(6)

            open_btn = QPushButton("Детальніше")
            open_btn.setCursor(Qt.PointingHandCursor)
            open_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2563EB;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 10px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #1D4ED8; }
            """)
            open_btn.clicked.connect(lambda checked, pid=prod.product_id: self.open_product_requested.emit(pid))
            actions_layout.addWidget(open_btn)

            remove_btn = QPushButton("💔 Видалити")
            remove_btn.setCursor(Qt.PointingHandCursor)
            remove_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FEF2F2;
                    color: #DC2626;
                    border: 1px solid #FECACA;
                    border-radius: 4px;
                    padding: 4px 10px;
                }
                QPushButton:hover { background-color: #FEE2E2; }
            """)
            remove_btn.clicked.connect(lambda checked, pid=prod.product_id: self.remove_favorite(pid))
            actions_layout.addWidget(remove_btn)

            self.favorites_table.setCellWidget(row, 4, actions_widget)

    def on_row_double_clicked(self, row, column):
        item = self.favorites_table.item(row, 0)
        if item:
            pid = item.data(Qt.UserRole)
            if pid is not None:
                self.open_product_requested.emit(pid)

    def remove_favorite(self, product_id: int):
        client_id = self.get_client_id()
        self.db.remove_from_favorites(client_id, product_id)
        self.load_favorites()
        self.favorite_removed.emit(product_id)
        