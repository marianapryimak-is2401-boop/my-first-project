from typing import List, Optional

class Supplier:
    """Сутність Постачальник"""
    def __init__(self, name: str, phone: str = "", email: str = "", address: str = "", supplier_id: Optional[int] = None):
        self.supplier_id = supplier_id
        self.name = name
        self.phone = phone
        self.email = email
        self.address = address

    def __repr__(self):
        return f"<Supplier {self.supplier_id}: {self.name}>"


class Category:
    """Сутність Категорія товару"""
    def __init__(self, name: str, description: str = "", category_id: Optional[int] = None):
        self.category_id = category_id
        self.name = name
        self.description = description

    def __repr__(self):
        return f"<Category {self.category_id}: {self.name}>"


class Product:
    """Сутність Товар"""
    def __init__(self, category_id: int, title: str, brand: str, price: float, 
                 stock_quantity: int, description: str = "", supplier_id: Optional[int] = None, 
                 product_id: Optional[int] = None):
        self.product_id = product_id
        self.category_id = category_id
        self.supplier_id = supplier_id
        self.title = title
        self.brand = brand
        self.price = price
        self.stock_quantity = stock_quantity
        self.description = description
        


class Client:
    """Сутність Клієнт"""
    def __init__(self, full_name: str, phone: str, address: str, email: str = "", client_id: Optional[int] = None):
        self.client_id = client_id
        self.full_name = full_name
        self.phone = phone
        self.email = email
        self.address = address

    def __repr__(self):
        return f"<Client {self.client_id}: {self.full_name}>"


class OrderItem:
    """Сутність Позиція у замовленні"""
    def __init__(self, product_id: int, quantity: int, price_per_unit: float, 
                 order_id: Optional[int] = None, item_id: Optional[int] = None):
        self.item_id = item_id
        self.order_id = order_id
        self.product_id = product_id
        self.quantity = quantity
        self.price_per_unit = price_per_unit

    @property
    def total_price(self) -> float:
        return self.quantity * self.price_per_unit


class Order:
    """Сутність Замовлення"""
    def __init__(self, client_id: int, status: str = "Нове", order_date: Optional[str] = None, 
                 total_amount: float = 0.0, order_id: Optional[int] = None):
        self.order_id = order_id
        self.client_id = client_id
        self.order_date = order_date
        self.status = status
        self.total_amount = total_amount
        self.items: List[OrderItem] = []

    def add_item(self, item: OrderItem):
        self.items.append(item)
        self.recalculate_total()

    def recalculate_total(self):
        self.total_amount = sum(item.total_price for item in self.items)