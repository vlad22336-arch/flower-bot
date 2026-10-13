from aiogram import Router, F, Bot
from aiogram.types import (
    Message,
    CallbackQuery,
    LabeledPrice,
    PreCheckoutQuery,
    ContentType,
)
from data.products import get_product_by_id
from keyboards.inline import cart_kb, confirm_order_kb, main_menu_kb
from utils.cart import (
    add_to_cart,
    remove_from_cart,
    change_quantity,
    get_cart,
    clear_cart,
    get_cart_total,
    format_cart,
    get_cart_items_count,
)
from config import DEMO_MODE, CURRENCY, CURRENCY_SYMBOL, PROVIDER_TOKEN, ADMIN_IDS

router = Router()


@router.callback_query(F.data.startswith("add_to_cart:"))
async def cb_add_to_cart(callback: CallbackQuery):
    product_id = callback.data.split(":")[1]
    product = get_product_by_id(product_id)

    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return

    add_to_cart(callback.from_user.id, product_id)
    count = get_cart_items_count(callback.from_user.id)

    await callback.answer(
        f"✅ {product['name']} добавлен!\nВ корзине: {count} шт.",
        show_alert=False,
    )


@router.message(F.text == "🛒 Корзина")
@router.callback_query(F.data == "cart")
async def show_cart(event: Message | CallbackQuery):
    user_id = event.from_user.id
    text = format_cart(user_id)
    has_items = bool(get_cart(user_id))

    if isinstance(event, CallbackQuery):
        try:
            if event.message.photo:
                await event.message.delete()
                await event.message.answer(
                    text,
                    reply_markup=cart_kb(has_items),
                    parse_mode="HTML",
                )
            else:
                await event.message.edit_text(
                    text,
                    reply_markup=cart_kb(has_items),
                    parse_mode="HTML",
                )
        except Exception:
            await event.message.answer(
                text,
                reply_markup=cart_kb(has_items),
                parse_mode="HTML",
            )
        await event.answer()
    else:
        await event.answer(
            text,
            reply_markup=cart_kb(has_items),
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("cart_inc:"))
async def cart_increase(callback: CallbackQuery):
    product_id = callback.data.split(":")[1]
    change_quantity(callback.from_user.id, product_id, 1)
    await show_cart(callback)


@router.callback_query(F.data.startswith("cart_dec:"))
async def cart_decrease(callback: CallbackQuery):
    product_id = callback.data.split(":")[1]
    change_quantity(callback.from_user.id, product_id, -1)
    await show_cart(callback)


@router.callback_query(F.data.startswith("cart_remove:"))
async def cart_remove(callback: CallbackQuery):
    product_id = callback.data.split(":")[1]
    remove_from_cart(callback.from_user.id, product_id)
    await callback.answer("Товар удалён")
    await show_cart(callback)


@router.callback_query(F.data == "clear_cart")
async def cb_clear_cart(callback: CallbackQuery):
    clear_cart(callback.from_user.id)
    await callback.message.edit_text(
        "🛒 Корзина очищена.",
        reply_markup=cart_kb(has_items=False),
    )
    await callback.answer()


@router.callback_query(F.data == "checkout")
async def cb_checkout(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    cart = get_cart(user_id)

    if not cart:
        await callback.answer("Корзина пуста", show_alert=True)
        return

    total = get_cart_total(user_id)

    # Реальная оплата через Telegram Payments
    if PROVIDER_TOKEN:
        prices = []
        for product_id, qty in cart.items():
            product = get_product_by_id(product_id)
            if product:
                prices.append(
                    LabeledPrice(
                        label=f"{product['name']} × {qty}",
                        amount=product["price"] * qty * 100,  # копейки
                    )
                )

        payload = f"order_{user_id}_{total}"

        await bot.send_invoice(
            chat_id=callback.message.chat.id,
            title="Заказ в Цветочной мастерской",
            description=f"Оплата заказа на сумму {total} {CURRENCY_SYMBOL}",
            payload=payload,
            provider_token=PROVIDER_TOKEN,
            currency=CURRENCY,
            prices=prices,
            start_parameter="flower-order",
            need_name=True,
            need_phone_number=True,
            need_shipping_address=False,
            is_flexible=False,
        )
        await callback.answer()
        return

    # Демо без реального провайдера
    text = format_cart(user_id)
    text += (
        f"\n\n📦 <b>Оформление заказа</b>\n"
        f"Сумма: <b>{total} {CURRENCY_SYMBOL}</b>\n\n"
    )

    if DEMO_MODE:
        text += (
            "⚠️ <i>Демо-режим: реальная оплата отключена.</i>\n\n"
            "Чтобы включить оплату:\n"
            "1. Получите <code>PROVIDER_TOKEN</code> у @BotFather → Payments\n"
            "2. Добавьте его в файл <code>.env</code>\n\n"
            "Сейчас можно «подтвердить» заказ без оплаты."
        )
    else:
        text += "Подтвердите заказ — заявка будет отправлена флористу."

    try:
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(
                text,
                reply_markup=confirm_order_kb(),
                parse_mode="HTML",
            )
        else:
            await callback.message.edit_text(
                text,
                reply_markup=confirm_order_kb(),
                parse_mode="HTML",
            )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=confirm_order_kb(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data == "confirm_order")
async def cb_confirm_order(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    cart = get_cart(user_id)
    total = get_cart_total(user_id)
    user = callback.from_user

    if not cart:
        await callback.answer("Корзина пуста", show_alert=True)
        return

    order_text = (
        f"🆕 <b>Новый заказ!</b>\n"
        f"От: {user.full_name} (@{user.username or 'нет'})\n"
        f"ID: <code>{user.id}</code>\n\n"
        f"{format_cart(user_id)}"
    )

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, order_text, parse_mode="HTML")
        except Exception:
            pass

    clear_cart(user_id)

    await callback.message.edit_text(
        "✅ <b>Заказ принят!</b>\n\n"
        + (
            "В демо-режиме оплата не списывалась.\n"
            if DEMO_MODE
            else "Флорист получил заявку и скоро свяжется с вами.\n"
        )
        + f"\nСумма: <b>{total} {CURRENCY_SYMBOL}</b>",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer("Заказ оформлен!")


# ===== Telegram Payments =====

@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@router.message(F.content_type == ContentType.SUCCESSFUL_PAYMENT)
async def process_successful_payment(message: Message, bot: Bot):
    payment = message.successful_payment
    user = message.from_user
    total = payment.total_amount / 100

    clear_cart(user.id)

    await message.answer(
        f"✅ <b>Оплата прошла успешно!</b>\n\n"
        f"Сумма: <b>{total:.0f} {CURRENCY_SYMBOL}</b>\n"
        f"ID платежа: <code>{payment.telegram_payment_charge_id}</code>\n\n"
        "Флорист уже получил ваш заказ и скоро свяжется с вами.",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )

    admin_text = (
        f"💰 <b>Оплаченный заказ!</b>\n"
        f"От: {user.full_name} (@{user.username or 'нет'})\n"
        f"ID: <code>{user.id}</code>\n"
        f"Сумма: <b>{total:.0f} {CURRENCY_SYMBOL}</b>\n"
        f"Telegram charge: <code>{payment.telegram_payment_charge_id}</code>"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_text, parse_mode="HTML")
        except Exception:
            pass
