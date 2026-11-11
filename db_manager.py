import sqlite3
from typing import List, Optional, Tuple
from classes import Category, Product, Client, OrderItem, Order, Supplier


class DatabaseManager:
    """Клас для здійснення операцій з базою даних SQLite"""

    def __init__(self, db_name: str = "computer_shop.db"):
        self.db_name = db_name
        self._init_supplier_tables()
        self._init_receipt_tables()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_supplier_tables(self):
        """Створення таблиці постачальників та додавання supplier_id до products"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS suppliers (
                    supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    phone TEXT,
                    email TEXT,
                    address TEXT
                )
            """)

            cursor.execute("PRAGMA table_info(products)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'supplier_id' not in columns:
                cursor.execute("""
                    ALTER TABLE products 
                    ADD COLUMN supplier_id INTEGER REFERENCES suppliers(supplier_id) ON DELETE SET NULL
                """)
            conn.commit()

    def _init_receipt_tables(self):
        """Додавання колонки receipt_path у таблицю orders"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(orders)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'receipt_path' not in columns:
                cursor.execute("ALTER TABLE orders ADD COLUMN receipt_path TEXT")
            conn.commit()

    # --- ОПЕРАЦІЇ З КАТЕГОРІЯМИ ---

    def get_all_categories(self) -> List[Category]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT category_id, name, description FROM categories")
            rows = cursor.fetchall()
            return [Category(category_id=row[0], name=row[1], description=row[2]) for row in rows]

    # --- ОПЕРАЦІЇ З ПОСТАЧАЛЬНИКАМИ ---

    def get_all_suppliers(self) -> List[Supplier]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT supplier_id, name, phone, email, address FROM suppliers ORDER BY name ASC")
            rows = cursor.fetchall()
            return [Supplier(supplier_id=r[0], name=r[1], phone=r[2], email=r[3], address=r[4]) for r in rows]

    def add_supplier(self, supplier: Supplier) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO suppliers (name, phone, email, address)
                VALUES (?, ?, ?, ?)
            """, (supplier.name, supplier.phone, supplier.email, supplier.address))
            conn.commit()
            return cursor.lastrowid

    def update_supplier(self, supplier: Supplier):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE suppliers
                SET name = ?, phone = ?, email = ?, address = ?
                WHERE supplier_id = ?
            """, (supplier.name, supplier.phone, supplier.email, supplier.address, supplier.supplier_id))
            conn.commit()

    def search_suppliers(self, query: str = "") -> List[Supplier]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            pattern = f"%{query.strip()}%"
            cursor.execute("""
                SELECT supplier_id, name, phone, email, address 
                FROM suppliers 
                WHERE LOWER(name) LIKE LOWER(?) OR LOWER(phone) LIKE LOWER(?)
                ORDER BY name ASC
            """, (pattern, pattern))
            rows = cursor.fetchall()
            return [Supplier(supplier_id=r[0], name=r[1], phone=r[2], email=r[3], address=r[4]) for r in rows]

    # --- ОПЕРАЦІЇ З ТОВАРАМИ ---

    def get_all_products(self) -> List[Product]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT product_id, category_id, title, brand, price, stock_quantity, description, supplier_id 
                FROM products
            """)
            rows = cursor.fetchall()
            return [
                Product(
                    product_id=row[0], category_id=row[1], title=row[2], 
                    brand=row[3], price=row[4], stock_quantity=row[5], description=row[6],
                    supplier_id=row[7]
                ) for row in rows
            ]

    def get_products_by_category(self, category_id: int) -> List[Product]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT product_id, category_id, title, brand, price, stock_quantity, description, supplier_id 
                FROM products WHERE category_id = ?
            """, (category_id,))
            rows = cursor.fetchall()
            return [
                Product(
                    product_id=row[0], category_id=row[1], title=row[2], 
                    brand=row[3], price=row[4], stock_quantity=row[5], description=row[6],
                    supplier_id=row[7]
                ) for row in rows
            ]

    def add_product(self, product: Product) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO products (category_id, title, brand, price, stock_quantity, description, supplier_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (product.category_id, product.title, product.brand, product.price, 
                  product.stock_quantity, product.description, product.supplier_id))
            conn.commit()
            return cursor.lastrowid

    def update_product(self, product: Product):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE products
                SET category_id = ?, title = ?, brand = ?, price = ?, stock_quantity = ?, description = ?, supplier_id = ?
                WHERE product_id = ?
            """, (product.category_id, product.title, product.brand, product.price, 
                  product.stock_quantity, product.description, product.supplier_id, product.product_id))
            conn.commit()

    def delete_product(self, product_id: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
            conn.commit()

    def get_product_by_id(self, product_id: int) -> Optional[Product]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT product_id, category_id, title, brand, price, stock_quantity, description, supplier_id
                FROM products WHERE product_id = ?
            """, (product_id,))
            row = cursor.fetchone()
            if row:
                return Product(
                    product_id=row[0], category_id=row[1], title=row[2],
                    brand=row[3], price=row[4], stock_quantity=row[5], description=row[6],
                    supplier_id=row[7]
                )
            return None

    def search_products(
        self, 
        query: str = "", 
        category_id: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        sort_by: str = "default"
    ) -> List[Product]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            search_pattern = f"%{query.strip()}%"
            
            sql = """
                SELECT product_id, category_id, title, brand, price, stock_quantity, description, supplier_id 
                FROM products 
                WHERE (LOWER(title) LIKE LOWER(?) OR LOWER(brand) LIKE LOWER(?))
            """
            params = [search_pattern, search_pattern]

            if category_id is not None:
                sql += " AND category_id = ?"
                params.append(category_id)

            if min_price is not None:
                sql += " AND price >= ?"
                params.append(min_price)

            if max_price is not None:
                sql += " AND price <= ?"
                params.append(max_price)

            if sort_by == "price_asc":
                sql += " ORDER BY price ASC"
            elif sort_by == "price_desc":
                sql += " ORDER BY price DESC"
            elif sort_by == "stock_desc":
                sql += " ORDER BY stock_quantity DESC"
            elif sort_by == "stock_asc":
                sql += " ORDER BY stock_quantity ASC"
            else:
                sql += " ORDER BY product_id ASC"

            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [
                Product(
                    product_id=row[0], category_id=row[1], title=row[2], 
                    brand=row[3], price=row[4], stock_quantity=row[5], description=row[6],
                    supplier_id=row[7]
                ) for row in rows
            ]

    # --- ОПЕРАЦІЇ З ЗАМОВЛЕННЯМИ ---

    def create_order(self, client: Client, items: List[OrderItem]) -> Tuple[int, int]:
        """Створення клієнта та замовлення. Повертає кортеж (order_id, client_id)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO clients (full_name, phone, email, address)
                VALUES (?, ?, ?, ?)
            """, (client.full_name, client.phone, client.email, client.address))
            client_id = cursor.lastrowid

            total_amount = sum(item.quantity * item.price_per_unit for item in items)

            cursor.execute("""
                INSERT INTO orders (client_id, total_amount, status)
                VALUES (?, ?, 'Нове')
            """, (client_id, total_amount))
            order_id = cursor.lastrowid

            for item in items:
                cursor.execute("""
                    INSERT INTO order_items (order_id, product_id, quantity, price_per_unit)
                    VALUES (?, ?, ?, ?)
                """, (order_id, item.product_id, item.quantity, item.price_per_unit))

                cursor.execute("""
                    UPDATE products 
                    SET stock_quantity = stock_quantity - ? 
                    WHERE product_id = ?
                """, (item.quantity, item.product_id))

            conn.commit()
            return order_id, client_id

    def update_order_receipt_path(self, order_id: int, receipt_path: str):
        """Запис шляху до PDF-чека у базу даних"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE orders
                SET receipt_path = ?
                WHERE order_id = ?
            """, (receipt_path, order_id))
            conn.commit()

    def get_orders(self, client_id: Optional[int] = None, is_admin: bool = False) -> list:
        """
        Отримання замовлень за ролями:
        - якщо is_admin=True: повертаються всі замовлення.
        - якщо is_admin=False і client_id існує: фільтрація STRICTLY WHERE o.client_id = ?.
        - якщо is_admin=False і client_id is None: повертає порожній список (без авторизації/замовлень).
        """
        if not is_admin and client_id is None:
            return []

        with self._get_connection() as conn:
            cursor = conn.cursor()
            sql = """
                SELECT o.order_id, c.full_name, c.phone, o.order_date, o.status, o.total_amount, o.receipt_path, o.client_id
                FROM orders o
                JOIN clients c ON o.client_id = c.client_id
            """
            params = []

            if not is_admin and client_id is not None:
                sql += " WHERE o.client_id = ?"
                params.append(client_id)

            sql += " ORDER BY o.order_id DESC"
            cursor.execute(sql, params)
            return cursor.fetchall()

    def get_order_full_info(self, order_id: int) -> Optional[dict]:
        """Отримання повної інформації для відновлення чека"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT o.order_id, c.full_name, c.phone, o.order_date, o.status, o.total_amount, o.receipt_path, o.client_id
                FROM orders o
                JOIN clients c ON o.client_id = c.client_id
                WHERE o.order_id = ?
            """, (order_id,))
            order_row = cursor.fetchone()
            if not order_row:
                return None

            cursor.execute("""
                SELECT p.title, oi.quantity, oi.price_per_unit
                FROM order_items oi
                JOIN products p ON oi.product_id = p.product_id
                WHERE oi.order_id = ?
            """, (order_id,))
            items_rows = cursor.fetchall()

            return {
                "order_id": order_row[0],
                "client_name": order_row[1],
                "phone": order_row[2],
                "order_date": str(order_row[3]),
                "status": order_row[4],
                "total_amount": order_row[5],
                "receipt_path": order_row[6],
                "client_id": order_row[7],
                "items": [
                    {"title": r[0], "quantity": r[1], "price_per_unit": r[2]}
                    for r in items_rows
                ]
            }

    def get_all_orders(self) -> list:
        return self.get_orders(client_id=None, is_admin=True)
    