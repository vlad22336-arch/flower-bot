"""
Простое хранилище корзин в памяти.
В продакшене замените на БД (Redis / PostgreSQL / SQLite).
"""

from collections import defaultdict
from data.products import get_product_by_id
from config import CURRENCY_SYMBOL

# user_id -> {product_id: quantity}
_carts: dict[int, dict[str, int]] = defaultdict(dict)


def add_to_cart(user_id: int, product_id: str, quantity: int = 1) -> None:
    cart = _carts[user_id]
    cart[product_id] = cart.get(product_id, 0) + quantity


def remove_from_cart(user_id: int, product_id: str) -> None:
    cart = _carts[user_id]
    if product_id in cart:
        del cart[product_id]


def change_quantity(user_id: int, product_id: str, delta: int) -> None:
    cart = _carts[user_id]
    if product_id not in cart:
        return
    cart[product_id] += delta
    if cart[product_id] <= 0:
        del cart[product_id]


def get_cart(user_id: int) -> dict[str, int]:
    return _carts[user_id].copy()


def clear_cart(user_id: int) -> None:
    _carts[user_id].clear()


def get_cart_total(user_id: int) -> int:
    total = 0
    for product_id, qty in _carts[user_id].items():
        product = get_product_by_id(product_id)
        if product:
            total += product["price"] * qty
    return total


def get_cart_items_count(user_id: int) -> int:
    return sum(_carts[user_id].values())


def format_cart(user_id: int) -> str:
    cart = get_cart(user_id)
    if not cart:
        return "🛒 Ваша корзина пуста."

    lines = ["🛒 <b>Ваша корзина:</b>\n"]
    for product_id, qty in cart.items():
        product = get_product_by_id(product_id)
        if product:
            subtotal = product["price"] * qty
            lines.append(
                f"• {product['name']} × {qty} = <b>{subtotal} {CURRENCY_SYMBOL}</b>"
            )

    total = get_cart_total(user_id)
    lines.append(f"\n💰 <b>Итого: {total} {CURRENCY_SYMBOL}</b>")
    return "\n".join(lines)
