import os
from PyQt5.QtWidgets import QApplication, QWidget, QStyleFactory
from PyQt5.QtGui import QFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STYLES_DIR = os.path.join(BASE_DIR, "styles")


def _read_qss(filename: str) -> str:
    """Зчитує QSS-файл за абсолютним шляхом відносно проєкту."""
    path = os.path.join(STYLES_DIR, filename)
    if not os.path.exists(path):
        print(f"[StyleManager] ПОМИЛКА: не знайдено файл стилів -> {path}")
        return ""
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def build_stylesheet(mode: str = "common") -> str:
    """Формує об'єднаний QSS для режиму: 'common', 'client' або 'admin'."""
    parts = [_read_qss("common.qss")]
    if mode == "client":
        parts.append(_read_qss("client.qss"))
    elif mode == "admin":
        parts.append(_read_qss("admin.qss"))
    return "\n\n".join(part for part in parts if part.strip())


def apply_theme(target=None, mode: str = "common") -> None:
    """Застосовує єдину дизайн-систему до QApplication та вікон без дублювання."""
    app = QApplication.instance()
    if app is not None:
        if not app.property("_theme_base_initialized"):
            fusion = QStyleFactory.create("Fusion")
            if fusion is not None:
                app.setStyle(fusion)
            base_font = QFont("Segoe UI", 10)
            app.setFont(base_font)
            app.setProperty("_theme_base_initialized", True)

        current_mode = app.property("_active_theme_mode")
        if current_mode != mode:
            qss = build_stylesheet(mode)
            app.setStyleSheet(qss)
            app.setProperty("_active_theme_mode", mode)

    if isinstance(target, QWidget) and target is not app:
        target.style().unpolish(target)
        target.style().polish(target)
        target.update()


def set_variant(widget: QWidget, variant: str) -> None:
    """Призначає варіант кнопки ('primary', 'secondary', 'danger', 'ghost') і оновлює вигляд."""
    if widget is None:
        return
    widget.setProperty("variant", variant)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    