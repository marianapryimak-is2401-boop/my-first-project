import sys
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QPushButton, QLabel, QMessageBox
from db_manager import DatabaseManager
from client_window import ClientWindow
from admin_window import AdminWindow


class ModeSelectionDialog(QDialog):
    """Діалог вибору інтерфейсу (Клієнт / Адміністратор)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Вибір режиму роботи")
        self.resize(300, 160)
        self.selected_mode = None

        layout = QVBoxLayout(self)

        label = QLabel("Оберіть інтерфейс для запуску:")
        layout.addWidget(label)

        self.client_btn = QPushButton("Увійти як Клієнт")
        self.client_btn.clicked.connect(self.select_client)
        layout.addWidget(self.client_btn)

        self.admin_btn = QPushButton("Увійти як Адміністратор")
        self.admin_btn.clicked.connect(self.select_admin)
        layout.addWidget(self.admin_btn)

    def select_client(self):
        self.selected_mode = "client"
        self.accept()

    def select_admin(self):
        self.selected_mode = "admin"
        self.accept()


def main():
    app = QApplication(sys.argv)
    
    try:
        db = DatabaseManager()

        # Показуємо вікно вибору інтерфейсу
        dialog = ModeSelectionDialog()
        if dialog.exec_() == QDialog.Accepted:
            if dialog.selected_mode == "client":
                window = ClientWindow(db)
            else:
                window = AdminWindow(db)

            window.show()
            sys.exit(app.exec_())
            
    except Exception as e:
        QMessageBox.critical(None, "Критична помилка", f"Не вдалося запустити додаток:\n{e}")

if __name__ == "__main__":
    main()
    