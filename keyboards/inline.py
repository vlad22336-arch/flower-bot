from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from data.products import CATEGORIES, PRODUCTS, EXTRAS


def main_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню бота."""
    builder = InlineKeyboardBuilder()
    builder.button(text="💐 Букеты", callback_data="category:bouquets")
    builder.button(text="🎁 Цветы в коробке", callback_data="category:boxes")
    builder.button(text="🪴 Растения", callback_data="category:plants")
    builder.button(text="✨ Дополнить заказ", callback_data="extras")
    builder.button(text="🛒 Корзина", callback_data="cart")
    builder.button(text="🎂 Важные даты", callback_data="dates")
    builder.button(text="💬 Менеджер", callback_data="manager")
    builder.button(text="📍 Контакты", callback_data="contacts")
    builder.adjust(1)
    return builder.as_markup()


def product_card_kb(
    category_id: str,
    product_id: str,
    current_index: int,
    total: int,
) -> InlineKeyboardMarkup:
    """Клавиатура карточки товара с пагинацией."""
    builder = InlineKeyboardBuilder()

    # Навигация
    prev_index = (current_index - 1) % total
    next_index = (current_index + 1) % total

    builder.button(text="◀️", callback_data=f"product:{category_id}:{prev_index}")
    builder.button(text=f"{current_index + 1}/{total}", callback_data="noop")
    builder.button(text="▶️", callback_data=f"product:{category_id}:{next_index}")

    # Действия
    builder.button(text="➕ В корзину", callback_data=f"add_to_cart:{product_id}")
    builder.button(text="◀️ В меню", callback_data="main_menu")

    builder.adjust(3, 1, 1)
    return builder.as_markup()


def extras_kb() -> InlineKeyboardMarkup:
    """Клавиатура дополнительных товаров."""
    builder = InlineKeyboardBuilder()
    for item in EXTRAS:
        builder.button(
            text=f"{item['name']} — {item['price']} ₽",
            callback_data=f"add_to_cart:{item['id']}"
        )
    builder.button(text="◀️ В меню", callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()


def cart_kb(has_items: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура корзины."""
    builder = InlineKeyboardBuilder()
    if has_items:
        builder.button(text="✅ Оформить заказ", callback_data="checkout")
        builder.button(text="🗑 Очистить корзину", callback_data="clear_cart")
    builder.button(text="◀️ В меню", callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()


def cart_item_kb(product_id: str) -> InlineKeyboardMarkup:
    """Кнопки для отдельного товара в корзине."""
    builder = InlineKeyboardBuilder()
    builder.button(text="➖", callback_data=f"cart_dec:{product_id}")
    builder.button(text="➕", callback_data=f"cart_inc:{product_id}")
    builder.button(text="❌", callback_data=f"cart_remove:{product_id}")
    builder.adjust(3)
    return builder.as_markup()


def back_to_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ В меню", callback_data="main_menu")
    return builder.as_markup()


def confirm_order_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm_order")
    builder.button(text="❌ Отмена", callback_data="cart")
    builder.adjust(2)
    return builder.as_markup()
