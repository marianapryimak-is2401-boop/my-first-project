import re
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QSpinBox
)
from PyQt5.QtCore import Qt, pyqtSignal


def build_category_specifications(product, category_name: str) -> list:
    """
    Формує перелік технічних характеристик залежно від категорії товару
    на основі його моделі, бренду та опису.
    """
    title = product.title or ""
    desc = product.description or ""
    combined = f"{title} {desc}"

    specs = [
        ("Бренд / Виробник", product.brand or "Не вказано"),
        ("Модель", product.title),
        ("Категорія", category_name),
    ]

    cat_lower = category_name.lower()

    if "процесор" in cat_lower:
        cores = re.search(r"(\d+\s*ядер(?:\s*/\s*\d+\s*поток[а-яіїє]+)?)", combined, re.IGNORECASE)
        freq = re.search(r"(\d+(?:\.\d+)?(?:\s*-\s*\d+(?:\.\d+)?)?\s*GHz)", combined, re.IGNORECASE)
        socket = re.search(r"(Socket\s*[A-Za-z0-9]+|AM4|AM5|LGA\d+)", combined, re.IGNORECASE)
        specs.append(("Кількість ядер / потоків", cores.group(1) if cores else "Багатоядерна архітектура"))
        specs.append(("Тактова частота", freq.group(1) if freq else "Стандартна для серії"))
        specs.append(("Сокет", socket.group(1) if socket else "Сумісний із платформою виробника"))
        specs.append(("Тип пам'яті", "DDR4 / DDR5 (залежно від платформи)"))

    elif "відеокарт" in cat_lower:
        vram = re.search(r"(\d+\s*GB\s*GDDR\d+[A-Z]*)", combined, re.IGNORECASE)
        bus = re.search(r"(\d+-bit)", combined, re.IGNORECASE)
        specs.append(("Обсяг та тип відеопам'яті", vram.group(1) if vram else "Високошвидкісна GDDR"))
        specs.append(("Розрядність шини пам'яті", bus.group(1) if bus else "Стандартна для моделі"))
        specs.append(("Інтерфейс підключення", "PCI Express 4.0 x16"))
        specs.append(("Підтримка технологій", "DirectX 12 Ultimate, Ray Tracing, Трасування променів"))

    elif "материнськ" in cat_lower:
        socket = re.search(r"(Socket\s*[A-Za-z0-9]+|AM4|AM5|LGA\d+)", combined, re.IGNORECASE)
        form_factor = re.search(r"(E-ATX|Micro-ATX|Mini-ITX|ATX)", combined, re.IGNORECASE)
        ram_type = re.search(r"(DDR5|DDR4)", combined, re.IGNORECASE)
        specs.append(("Сокет процесора", socket.group(1) if socket else "Актуальний сокет"))
        specs.append(("Форм-фактор", form_factor.group(1) if form_factor else "ATX"))
        specs.append(("Тип оперативної пам'яті", ram_type.group(1) if ram_type else "DDR4 / DDR5"))
        specs.append(("Бездротові інтерфейси", "Wi-Fi / Bluetooth" if "wi-fi" in combined.lower() else "Дротовий Gigabit LAN"))

    elif "оперативн" in cat_lower:
        ram_type = re.search(r"(DDR5|DDR4)", combined, re.IGNORECASE)
        capacity = re.search(r"(\d+\s*GB(?:\s*\(\d+x\d+GB\))?)", combined, re.IGNORECASE)
        freq = re.search(r"(\d+\s*MHz)", combined, re.IGNORECASE)
        timings = re.search(r"(CL\d+)", combined, re.IGNORECASE)
        specs.append(("Тип пам'яті", ram_type.group(1) if ram_type else "DDR4 / DDR5"))
        specs.append(("Загальний обсяг", capacity.group(1) if capacity else "Стандартний комплект"))
        specs.append(("Робоча частота", freq.group(1) if freq else "Високочастотна"))
        specs.append(("Таймінги (CAS Latency)", timings.group(1) if timings else "Оптимізовані"))

    elif "ssd" in cat_lower or "hdd" in cat_lower:
        capacity = re.search(r"(\d+\s*(?:TB|GB))", combined, re.IGNORECASE)
        iface = re.search(r"(M\.2\s*NVMe|PCIe\s*\d\.\d(?:\s*x\d)?|SATA\s*III|SATA)", combined, re.IGNORECASE)
        speed = re.search(r"(\d+\s*MB/s)", combined, re.IGNORECASE)
        specs.append(("Обсяг накопичувача", capacity.group(1) if capacity else "Висока ємність"))
        specs.append(("Інтерфейс підключення", iface.group(1) if iface else "M.2 / SATA"))
        specs.append(("Швидкість читання", f"до {speed.group(1)}" if speed else "Висока швидкість передачі даних"))

    elif "монітор" in cat_lower:
        diag = re.search(r'(\d+(?:\.\d+)?")', combined)
        matrix = re.search(r"(Nano\s*IPS|Fast\s*IPS|IPS|VA|OLED|TN)", combined, re.IGNORECASE)
        res = re.search(r"(\d{3,4}x\d{3,4})", combined)
        hz = re.search(r"(\d+\s*Hz)", combined, re.IGNORECASE)
        resp = re.search(r"(\d+(?:\.\d+)?\s*ms)", combined, re.IGNORECASE)
        specs.append(("Діагональ екрана", diag.group(1) if diag else "Широкоформатний"))
        specs.append(("Тип матриці", matrix.group(1) if matrix else "IPS / VA"))
        specs.append(("Роздільна здатність", res.group(1) if res else "Full HD / QHD"))
        specs.append(("Частота оновлення", hz.group(1) if hz else "60–165 Hz"))
        specs.append(("Час відгуку", resp.group(1) if resp else "Мінімальна затримка"))

    elif "клавіатур" in cat_lower:
        kb_type = "Механічна" if "механічн" in combined.lower() else ("Мембранна" if "мембранн" in combined.lower() else "Ігрова / Офісна")
        conn = "Бездротова (Bluetooth / USB)" if ("wireless" in combined.lower() or "bluetooth" in combined.lower()) else "Дротова (USB)"
        specs.append(("Тип клавіатури", kb_type))
        specs.append(("Тип підключення", conn))
        specs.append(("Підсвічування", "RGB" if "rgb" in combined.lower() else "Стандартне"))

    elif "миш" in cat_lower:
        conn = "Бездротова" if ("бездротов" in combined.lower() or "superlight" in combined.lower() or "pro" in combined.lower()) else "Дротова"
        dpi = re.search(r"(\d+K\s*DPI|\d+\s*DPI)", combined, re.IGNORECASE)
        specs.append(("Тип підключення", conn))
        specs.append(("Роздільна здатність сенсора", dpi.group(1) if dpi else "Високоточний оптичний сенсор"))
        specs.append(("Ергономіка", "Для правої руки / Універсальна"))

    elif "навушник" in cat_lower or "гарнітур" in cat_lower:
        conn = "Бездротові" if "wireless" in combined.lower() else "Дротові (USB / 3.5 мм)"
        specs.append(("Тип конструкції", "Повнорозмірні з мікрофоном"))
        specs.append(("Підключення", conn))
        specs.append(("Звучання", "7.1 Virtual Surround / Стерео" if "7.1" in combined else "Чисте стереозвучання"))

    elif "корпус" in cat_lower:
        ff = re.search(r"(Full-Tower|Mid-Tower|Mini-Tower)", combined, re.IGNORECASE)
        specs.append(("Типорозмір корпусу", ff.group(1) if ff else "Mid-Tower"))
        specs.append(("Бокова панель", "Загартоване скло" if "скло" in combined.lower() else "Метал / Скло"))
        specs.append(("Форм-фактор материнських плат", "ATX, Micro-ATX, Mini-ITX"))

    elif "живлення" in cat_lower:
        power = re.search(r"(\d+\s*W)", combined, re.IGNORECASE)
        cert = re.search(r"(80\s*PLUS\s*[A-Za-z]+)", combined, re.IGNORECASE)
        specs.append(("Потужність", power.group(1) if power else "Стабільна вихідна потужність"))
        specs.append(("Сертифікат енергоефективності", cert.group(1) if cert else "80 PLUS"))
        specs.append(("Тип підключення кабелів", "Модульний" if "модульн" in combined.lower() else "Стандартний"))

    elif "охолодження" in cat_lower:
        cool_type = "Рідинне охолодження (СРО / AIO)" if ("рідинн" in combined.lower() or "liquid" in combined.lower()) else "Повітряний кулер"
        specs.append(("Тип системи охолодження", cool_type))
        specs.append(("Сумісність із сокетами", "Intel LGA1700/1200, AMD AM5/AM4"))

    elif "ноутбук" in cat_lower:
        diag = re.search(r'(\d+(?:\.\d+)?")', combined)
        ram_ssd = re.search(r"(\d+/\d+\s*GB|\d+\s*GB\s*RAM)", combined, re.IGNORECASE)
        specs.append(("Діагональ дисплея", diag.group(1) if diag else "13\"–16\""))
        specs.append(("Конфігурація пам'яті", ram_ssd.group(1) if ram_ssd else "Оптимальна конфігурація"))
        specs.append(("Автономність", "До 12–18 годин роботи від акумулятора"))

    elif "мережев" in cat_lower:
        wifi = re.search(r"(Wi-Fi\s*\d+[A-Z]*)", combined, re.IGNORECASE)
        specs.append(("Стандарт бездротового зв'язку", wifi.group(1) if wifi else "Wi-Fi 6 (802.11ax)"))
        specs.append(("Порти", "Gigabit Ethernet (10/100/1000 Мбіт/с)"))

    if desc.strip():
        specs.append(("Додаткові особливості", desc.strip()))

    specs.append(("Гарантія", "Офіційна гарантія 12–36 місяців"))
    return specs


class ProductDetailPage(QWidget):
    """Окрема сторінка з детальною інформацією про товар та вибором кількості"""
    back_requested = pyqtSignal()
    favorite_toggled = pyqtSignal(int, bool)
    cart_updated = pyqtSignal()

    def __init__(self, db_manager, cart_list, get_client_id_func, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.cart = cart_list
        self.get_client_id = get_client_id_func
        self.current_product = None
        self.init_ui()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 12, 16, 12)
        root_layout.setSpacing(12)

        # Верхня панель навігації
        top_nav = QHBoxLayout()
        self.back_btn = QPushButton("← Назад")
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 7px 14px;
                font-weight: bold;
                color: #1E293B;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
            }
        """)
        self.back_btn.clicked.connect(self.back_requested.emit)
        top_nav.addWidget(self.back_btn)

        top_nav.addStretch()

        self.fav_btn = QPushButton("♡ Додати в обране")
        self.fav_btn.setCursor(Qt.PointingHandCursor)
        self.fav_btn.clicked.connect(self.on_toggle_favorite)
        top_nav.addWidget(self.fav_btn)

        root_layout.addLayout(top_nav)

        # Прокручувана область сторінки товару
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 6, 0)
        content_layout.setSpacing(14)

        # --- Основна картка заголовка, ціни, наявності та вибору кількості ---
        header_card = QFrame()
        header_card.setStyleSheet("""
            QFrame#DetailHeaderCard {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 10px;
            }
        """)
        header_card.setObjectName("DetailHeaderCard")
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(18, 16, 18, 16)
        header_layout.setSpacing(10)

        # Категорія та бренд
        meta_row = QHBoxLayout()
        self.category_badge = QLabel("Категорія: —")
        self.category_badge.setStyleSheet("""
            background-color: #EFF6FF;
            color: #1D4ED8;
            border: 1px solid #BFDBFE;
            border-radius: 4px;
            padding: 3px 8px;
            font-weight: bold;
            font-size: 12px;
        """)
        meta_row.addWidget(self.category_badge)

        self.brand_label = QLabel("Бренд: —")
        self.brand_label.setStyleSheet("color: #475569; font-size: 13px; font-weight: bold; margin-left: 8px;")
        meta_row.addWidget(self.brand_label)
        meta_row.addStretch()
        header_layout.addLayout(meta_row)

        # Повна назва товару
        self.title_label = QLabel("Назва товару")
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #0F172A;")
        header_layout.addWidget(self.title_label)

        # Ціна та наявність на складі
        price_stock_row = QHBoxLayout()
        self.price_label = QLabel("0.00 грн")
        self.price_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #16A34A;")
        price_stock_row.addWidget(self.price_label)

        price_stock_row.addSpacing(20)

        self.stock_label = QLabel("На складі: 0 шт.")
        self.stock_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #334155;")
        price_stock_row.addWidget(self.stock_label)
        price_stock_row.addStretch()
        header_layout.addLayout(price_stock_row)

        # Розділювач перед блоком покупки
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #E2E8F0;")
        header_layout.addWidget(sep)

        # --- Блок вибору кількості («−» та «+») + Загальна вартість + «Додати в кошик» ---
        buy_row = QHBoxLayout()
        buy_row.setSpacing(10)

        qty_caption = QLabel("Кількість:")
        qty_caption.setStyleSheet("font-size: 14px; font-weight: bold; color: #1E293B;")
        buy_row.addWidget(qty_caption)

        self.minus_btn = QPushButton("−")
        self.minus_btn.setFixedSize(34, 34)
        self.minus_btn.setCursor(Qt.PointingHandCursor)
        self.minus_btn.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                font-weight: bold;
                background-color: #F1F5F9;
                border: 1px solid #CBD5E1;
                border-radius: 5px;
            }
            QPushButton:hover:enabled { background-color: #E2E8F0; }
            QPushButton:disabled { color: #94A3B8; }
        """)
        self.minus_btn.clicked.connect(self.decrease_quantity)
        buy_row.addWidget(self.minus_btn)

        self.qty_spin = QSpinBox()
        self.qty_spin.setButtonSymbols(QSpinBox.NoButtons)
        self.qty_spin.setAlignment(Qt.AlignCenter)
        self.qty_spin.setFixedSize(64, 34)
        self.qty_spin.setStyleSheet("""
            QSpinBox {
                font-size: 15px;
                font-weight: bold;
                border: 1px solid #CBD5E1;
                border-radius: 5px;
                background-color: #FFFFFF;
            }
        """)
        self.qty_spin.valueChanged.connect(self.on_quantity_changed)
        buy_row.addWidget(self.qty_spin)

        self.plus_btn = QPushButton("+")
        self.plus_btn.setFixedSize(34, 34)
        self.plus_btn.setCursor(Qt.PointingHandCursor)
        self.plus_btn.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                font-weight: bold;
                background-color: #F1F5F9;
                border: 1px solid #CBD5E1;
                border-radius: 5px;
            }
            QPushButton:hover:enabled { background-color: #E2E8F0; }
            QPushButton:disabled { color: #94A3B8; }
        """)
        self.plus_btn.clicked.connect(self.increase_quantity)
        buy_row.addWidget(self.plus_btn)

        buy_row.addSpacing(18)

        self.total_price_label = QLabel("Загальна вартість: 0.00 грн")
        self.total_price_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        buy_row.addWidget(self.total_price_label)

        buy_row.addStretch()

        self.add_to_cart_btn = QPushButton("🛒 Додати в кошик")
        self.add_to_cart_btn.setCursor(Qt.PointingHandCursor)
        self.add_to_cart_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
                padding: 9px 20px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover:enabled {
                background-color: #1D4ED8;
            }
            QPushButton:disabled {
                background-color: #94A3B8;
            }
        """)
        self.add_to_cart_btn.clicked.connect(self.add_current_to_cart)
        buy_row.addWidget(self.add_to_cart_btn)

        header_layout.addLayout(buy_row)
        content_layout.addWidget(header_card)

        # --- Блок детального опису ---
        desc_card = QFrame()
        desc_card.setStyleSheet("""
            QFrame#DetailDescCard {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 10px;
            }
        """)
        desc_card.setObjectName("DetailDescCard")
        desc_layout = QVBoxLayout(desc_card)
        desc_layout.setContentsMargins(18, 14, 18, 14)
        desc_layout.setSpacing(6)

        desc_heading = QLabel("Детальний опис")
        desc_heading.setStyleSheet("font-size: 15px; font-weight: bold; color: #0F172A;")
        desc_layout.addWidget(desc_heading)

        self.description_label = QLabel("Опис відсутній.")
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("font-size: 13px; color: #334155; line-height: 1.4;")
        desc_layout.addWidget(self.description_label)

        content_layout.addWidget(desc_card)

        # --- Блок технічних характеристик ---
        specs_card = QFrame()
        specs_card.setStyleSheet("""
            QFrame#DetailSpecsCard {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 10px;
            }
        """)
        specs_card.setObjectName("DetailSpecsCard")
        specs_layout = QVBoxLayout(specs_card)
        specs_layout.setContentsMargins(18, 14, 18, 14)
        specs_layout.setSpacing(8)

        specs_heading = QLabel("Технічні характеристики")
        specs_heading.setStyleSheet("font-size: 15px; font-weight: bold; color: #0F172A;")
        specs_layout.addWidget(specs_heading)

        self.specs_table = QTableWidget()
        self.specs_table.setColumnCount(2)
        self.specs_table.setHorizontalHeaderLabels(["Характеристика", "Значення"])
        self.specs_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.specs_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.specs_table.verticalHeader().setVisible(False)
        self.specs_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.specs_table.setSelectionMode(QTableWidget.NoSelection)
        self.specs_table.setMinimumHeight(210)
        specs_layout.addWidget(self.specs_table)

        content_layout.addWidget(specs_card)
        content_layout.addStretch()

        scroll.setWidget(content_widget)
        root_layout.addWidget(scroll)

    def load_product(self, product_id: int):
        """Завантаження актуальних даних товару з SQLite на сторінку"""
        product = self.db.get_product_by_id(product_id)
        if not product:
            QMessageBox.warning(self, "Помилка", "Товар не знайдено в базі даних.")
            self.back_requested.emit()
            return

        self.current_product = product
        category_name = self.db.get_category_name_by_id(product.category_id)

        self.category_badge.setText(f"Категорія: {category_name}")
        self.brand_label.setText(f"Бренд: {product.brand}")
        self.title_label.setText(product.title)
        self.price_label.setText(f"{product.price:.2f} грн")

        # Опис
        desc_text = product.description.strip() if product.description else ""
        if not desc_text:
            desc_text = f"{product.title} від бренду {product.brand} — надійне рішення у категорії «{category_name}»."
        self.description_label.setText(desc_text)

        # Налаштування наявності та лічильника кількості
        stock = product.stock_quantity
        self.qty_spin.blockSignals(True)
        if stock > 0:
            self.stock_label.setText(f"В наявності на складі: {stock} шт.")
            self.stock_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #15803D;")
            self.qty_spin.setRange(1, stock)
            self.qty_spin.setValue(1)
            self.qty_spin.setEnabled(True)
            self.minus_btn.setEnabled(True)
            self.plus_btn.setEnabled(True)
            self.add_to_cart_btn.setEnabled(True)
        else:
            self.stock_label.setText("Немає в наявності (0 шт.)")
            self.stock_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #DC2626;")
            self.qty_spin.setRange(0, 0)
            self.qty_spin.setValue(0)
            self.qty_spin.setEnabled(False)
            self.minus_btn.setEnabled(False)
            self.plus_btn.setEnabled(False)
            self.add_to_cart_btn.setEnabled(False)
        self.qty_spin.blockSignals(False)

        self.update_total_price()
        self.update_favorite_button_state()

        # Заповнення таблиці технічних характеристик
        specs = build_category_specifications(product, category_name)
        self.specs_table.setRowCount(len(specs))
        for row, (spec_name, spec_val) in enumerate(specs):
            name_item = QTableWidgetItem(spec_name)
            val_item = QTableWidgetItem(spec_val)
            self.specs_table.setItem(row, 0, name_item)
            self.specs_table.setItem(row, 1, val_item)

    def update_favorite_button_state(self):
        if not self.current_product:
            return
        client_id = self.get_client_id()
        is_fav = self.db.is_favorite(client_id, self.current_product.product_id)
        if is_fav:
            self.fav_btn.setText("❤️ В обраному")
            self.fav_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FEF2F2;
                    border: 1px solid #FECACA;
                    border-radius: 6px;
                    padding: 7px 14px;
                    font-weight: bold;
                    color: #DC2626;
                }
                QPushButton:hover { background-color: #FEE2E2; }
            """)
        else:
            self.fav_btn.setText("♡ Додати в обране")
            self.fav_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    padding: 7px 14px;
                    font-weight: bold;
                    color: #334155;
                }
                QPushButton:hover { background-color: #F8FAFC; }
            """)

    def on_toggle_favorite(self):
        if not self.current_product:
            return
        client_id = self.get_client_id()
        added = self.db.toggle_favorite(client_id, self.current_product.product_id)
        self.update_favorite_button_state()
        self.favorite_toggled.emit(self.current_product.product_id, added)

    def decrease_quantity(self):
        if not self.current_product or self.current_product.stock_quantity <= 0:
            return
        val = self.qty_spin.value()
        if val > 1:
            self.qty_spin.setValue(val - 1)

    def increase_quantity(self):
        if not self.current_product or self.current_product.stock_quantity <= 0:
            return
        val = self.qty_spin.value()
        if val < self.current_product.stock_quantity:
            self.qty_spin.setValue(val + 1)
        else:
            QMessageBox.warning(
                self, "Обмеження складу",
                f"Максимальна доступна кількість на складі: {self.current_product.stock_quantity} шт."
            )

    def on_quantity_changed(self):
        if not self.current_product:
            return
        stock = self.current_product.stock_quantity
        val = self.qty_spin.value()
        if stock > 0 and val > stock:
            self.qty_spin.setValue(stock)
        self.update_total_price()

    def update_total_price(self):
        if not self.current_product:
            self.total_price_label.setText("Загальна вартість: 0.00 грн")
            return
        qty = max(0, self.qty_spin.value())
        total = self.current_product.price * qty
        self.total_price_label.setText(f"Загальна вартість: {total:.2f} грн")

    def add_current_to_cart(self):
        if not self.current_product:
            return

        # Перезавантажуємо актуальний залишок із БД
        fresh_prod = self.db.get_product_by_id(self.current_product.product_id)
        if not fresh_prod or fresh_prod.stock_quantity <= 0:
            QMessageBox.warning(self, "Немає в наявності", "На жаль, цей товар закінчився на складі.")
            if fresh_prod:
                self.load_product(fresh_prod.product_id)
            return

        qty = self.qty_spin.value()
        if qty <= 0:
            QMessageBox.warning(self, "Помилка кількості", "Кількість товару має бути більшою за 0.")
            return

        if qty > fresh_prod.stock_quantity:
            QMessageBox.warning(
                self, "Недостатньо товару",
                f"Неможливо вибрати кількість більшу за складський залишок ({fresh_prod.stock_quantity} шт.)."
            )
            return

        existing_qty = sum(item_qty for p, item_qty in self.cart if p.product_id == fresh_prod.product_id)
        if existing_qty + qty > fresh_prod.stock_quantity:
            QMessageBox.warning(
                self, "Недостатньо товару на складі",
                f"На складі доступно лише {fresh_prod.stock_quantity} шт.\n"
                f"У вашому кошику вже є {existing_qty} шт. цього товару."
            )
            return

        for i, (p, item_qty) in enumerate(self.cart):
            if p.product_id == fresh_prod.product_id:
                self.cart[i] = (fresh_prod, item_qty + qty)
                break
        else:
            self.cart.append((fresh_prod, qty))

        self.cart_updated.emit()
        total_added = fresh_prod.price * qty
        QMessageBox.information(
            self,
            "Товар додано до кошика",
            f"Товар «{fresh_prod.title}» у кількості {qty} шт. успішно додано до кошика!\n"
            f"Сума доданих позицій: {total_added:.2f} грн"
        )
        