import sqlite3

def create_database(db_name="computer_shop.db"):
    # Підключення до бази даних (якщо файлу немає, він створиться)
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Увімкнення підтримки зовнішніх ключів (Foreign Keys)
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Таблиця категорій товарів
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT
        )
    ''')

    # 2. Таблиця товарів
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            brand TEXT,
            price REAL NOT NULL CHECK(price >= 0),
            stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK(stock_quantity >= 0),
            description TEXT,
            FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE CASCADE
        )
    ''')

    # 3. Таблиця клієнтів
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            client_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            address TEXT NOT NULL
        )
    ''')

    # 4. Таблиця замовлень
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'Нове' CHECK(status IN ('Нове', 'В обробці', 'Відправлено', 'Завершено', 'Скасовано')),
            total_amount REAL DEFAULT 0.0 CHECK(total_amount >= 0),
            FOREIGN KEY (client_id) REFERENCES clients(client_id) ON DELETE CASCADE
        )
    ''')

    # 5. Таблиця елементів замовлення (зв'язок багатьох до багатьох)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL CHECK(quantity > 0),
            price_per_unit REAL NOT NULL CHECK(price_per_unit >= 0),
            FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE RESTRICT
        )
    ''')

    # Заповнення тестовими даними (за бажанням)
    _seed_initial_data(cursor)

    conn.commit()
    conn.close()
    print(f"Базу даних '{db_name}' успішно створено та заповнено початковими даними.")

def _seed_initial_data(cursor):
    """Приватна функція для додавання початкових товарів та категорій."""
    # Перевіряємо, чи база вже має дані
    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] > 0:
        return

    # Додавання категорій
    categories = [
        ('Ноутбуки', 'Портативні комп’ютери для роботи та ігор'),
        ('Процесори', 'Центральні процесори Intel та AMD'),
        ('Відеокарти', 'Графічні адаптери для ігор та рендерингу')
    ]
    cursor.executemany("INSERT INTO categories (name, description) VALUES (?, ?)", categories)

    # Додавання товарів
    products = [
        (1, 'ASUS ROG Strix G16', 'ASUS', 54999.00, 5, 'Intel Core i7, 16GB RAM, RTX 4060'),
        (1, 'Lenovo IdeaPad Slim 3', 'Lenovo', 18500.00, 10, 'AMD Ryzen 5, 8GB RAM, 512GB SSD'),
        (2, 'Intel Core i5-13600K', 'Intel', 12300.00, 8, '14 ядер, до 5.1 GHz'),
        (2, 'AMD Ryzen 7 7800X3D', 'AMD', 16800.00, 4, '8 ядер, L3 кєш 96MB'),
        (3, 'NVIDIA GeForce RTX 4070', 'Gigabyte', 28999.00, 3, '12GB GDDR6X')
    ]
    cursor.executemany(
        "INSERT INTO products (category_id, title, brand, price, stock_quantity, description) VALUES (?, ?, ?, ?, ?, ?)",
        products
    )

if __name__ == "__main__":
    create_database()