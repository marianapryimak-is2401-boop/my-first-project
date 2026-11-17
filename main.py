import sys
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QPushButton, QMessageBox
)
from PyQt5.QtCore import Qt

from db_manager import DatabaseManager
from client_window import ClientWindow
from admin_window import AdminWindow
from style_manager import apply_theme


class ModeSelectionDialog(QDialog):
    """Стартове вікно вибору режиму роботи магазину"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_mode = None
        self.setWindowTitle("TechStore — Магазин комп'ютерної техніки")
        self.setFixedSize(540, 340)
        self.init_ui()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Фірмова верхня шапка
        header = QFrame()
        header.setObjectName("storeTopHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(24, 18, 24, 18)
        header_layout.setSpacing(4)

        brand_lbl = QLabel("TECHSTORE  |  Комп'ютерна техніка та комплектуючі")
        brand_lbl.setObjectName("storeBrandTitle")
        header_layout.addWidget(brand_lbl)

        sub_lbl = QLabel("Оберіть режим входу в систему інтернет-магазину")
        sub_lbl.setObjectName("storeBrandSubtitle")
        header_layout.addWidget(sub_lbl)

        root_layout.addWidget(header)

        # Центральна область з двома картками вибору
        body = QFrame()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(22, 20, 22, 20)
        body_layout.setSpacing(14)

        # Картка покупця
        client_card = QFrame()
        client_card.setProperty("block", "card")
        c_layout = QVBoxLayout(client_card)
        c_layout.setContentsMargins(16, 16, 16, 16)
        c_layout.setSpacing(8)

        c_title = QLabel("Вітрина покупця")
        c_title.setProperty("role", "sectionTitle")
        c_layout.addWidget(c_title)

        c_desc = QLabel("Каталог товарів, фільтри, кошик, бонусна програма та історія замовлень.")
        c_desc.setProperty("role", "muted")
        c_desc.setWordWrap(True)
        c_layout.addWidget(c_desc)

        c_layout.addStretch()

        self.client_btn = QPushButton("Увійти як покупець")
        self.client_btn.setProperty("variant", "primary")
        self.client_btn.setMinimumHeight(38)
        self.client_btn.clicked.connect(self.select_client)
        c_layout.addWidget(self.client_btn)

        body_layout.addWidget(client_card, stretch=1)

        # Картка адміністратора
        admin_card = QFrame()
        admin_card.setProperty("block", "card")
        a_layout = QVBoxLayout(admin_card)
        a_layout.setContentsMargins(16, 16, 16, 16)
        a_layout.setSpacing(8)

        a_title = QLabel("Панель адміністратора")
        a_title.setProperty("role", "sectionTitle")
        a_layout.addWidget(a_title)

        a_desc = QLabel("Обробка замовлень, керування складом, постачальники та аналітика продажів.")
        a_desc.setProperty("role", "muted")
        a_desc.setWordWrap(True)
        a_layout.addWidget(a_desc)

        a_layout.addStretch()

        self.admin_btn = QPushButton("Увійти як адміністратор")
        self.admin_btn.setProperty("variant", "secondary")
        self.admin_btn.setMinimumHeight(38)
        self.admin_btn.clicked.connect(self.select_admin)
        a_layout.addWidget(self.admin_btn)

        body_layout.addWidget(admin_card, stretch=1)

        root_layout.addWidget(body, stretch=1)

        # Нижня контактна смужка
        footer = QFrame()
        footer.setObjectName("storeFooter")
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(24, 10, 24, 10)

        f_info = QLabel("Підтримка: +380 (67) 555-01-99   •   Пн–Нд: 09:00 – 20:00   •   support@techstore.ua")
        f_info.setObjectName("footerItemValue")
        f_info.setAlignment(Qt.AlignCenter)
        f_layout.addWidget(f_info)

        root_layout.addWidget(footer)

    def select_client(self):
        self.selected_mode = "client"
        self.accept()

    def select_admin(self):
        self.selected_mode = "admin"
        self.accept()


def main():
    app = QApplication(sys.argv)
    apply_theme(app, "common")

    try:
        db = DatabaseManager()

        dialog = ModeSelectionDialog()
        if dialog.exec_() == QDialog.Accepted:
            if dialog.selected_mode == "client":
                window = ClientWindow(db)
                apply_theme(window, "client")
            else:
                window = AdminWindow(db)
                apply_theme(window, "admin")

            window.show()
            sys.exit(app.exec_())

    except Exception as e:
        QMessageBox.critical(None, "Критична помилка", f"Не вдалося запустити додаток:\n{e}")


if __name__ == "__main__":
    main()
    