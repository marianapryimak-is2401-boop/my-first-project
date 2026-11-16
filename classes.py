from typing import Optional


class Category:
    """Сутність Категорія товарів"""
    def __init__(self, name: str, description: str = "", category_id: Optional[int] = None):
        self.category_id = category_id
        self.name = name
        self.description = description

    def __repr__(self):
        return f"<Category {self.category_id}: {self.name}>"


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

    def __repr__(self):
        return f"<Product {self.product_id}: {self.title} ({self.price} грн)>"


class Client:
    """Сутність Клієнт"""
    def __init__(self, full_name: str, phone: str, email: str = "", address: str = "", client_id: Optional[int] = None):
        self.client_id = client_id
        self.full_name = full_name
        self.phone = phone
        self.email = email
        self.address = address


class OrderItem:
    """Позиція у замовленні"""
    def __init__(self, product_id: int, quantity: int, price_per_unit: float, order_id: Optional[int] = None, item_id: Optional[int] = None):
        self.item_id = item_id
        self.order_id = order_id
        self.product_id = product_id
        self.quantity = quantity
        self.price_per_unit = price_per_unit


class Order:
    """Сутність Замовлення"""
    def __init__(
        self,
        client_id: int,
        total_amount: float,
        status: str = "Нове",
        delivery_method: str = "Нова пошта",
        delivery_address: str = "",
        payment_method: str = "Оплата карткою",
        comment: str = "",
        order_date: Optional[str] = None,
        order_id: Optional[int] = None
    ):
        self.order_id = order_id
        self.client_id = client_id
        self.order_date = order_date
        self.status = status
        self.total_amount = total_amount
        self.delivery_method = delivery_method
        self.delivery_address = delivery_address
        self.payment_method = payment_method
        self.comment = comment
        