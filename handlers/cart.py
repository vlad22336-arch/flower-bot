from aiogram import Router, F, Bot
from aiogram.types import (
    Message,
    CallbackQuery,
    LabeledPrice,
    PreCheckoutQuery,
    ContentType,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from data.products import get_product_by_id
from keyboards.inline import (
    cart_kb, confirm_order_kb, main_menu_kb,
    confirm_order_with_promo_kb,
)
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
from data.database import add_order

router = Router()

user_promos = {}


class OrderComment(StatesGroup):
    waiting = State()


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
                await event.message.answer(text, reply_markup=cart_kb(has_items), parse_mode="HTML")
            else:
                await event.message.edit_text(text, reply_markup=cart_kb(has_items), parse_mode="HTML")
        except Exception:
            try:
                await event.message.delete()
            except Exception:
                pass
            await event.message.answer(text, reply_markup=cart_kb(has_items), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=cart_kb(has_items), parse_mode="HTML")


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
    try:
        await callback.message.edit_text(
            "🛒 Корзина очищена.",
            reply_markup=cart_kb(has_items=False),
        )
    except Exception:
        await callback.message.answer(
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

    if PROVIDER_TOKEN:
        prices = []
        for product_id, qty in cart.items():
            product = get_product_by_id(product_id)
            if product:
                prices.append(LabeledPrice(label=f"{product['name']} × {qty}", amount=product["price"] * qty * 100))
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

    text = format_cart(user_id)
    text += f"\n\n📦 <b>Оформление заказа</b>\nСумма: <b>{total} {CURRENCY_SYMBOL}</b>\n\n"
    if DEMO_MODE:
        text += "⚠️ <i>Демо-режим: реальная оплата отключена.</i>"
    else:
        text += "Подтвердите заказ — заявка будет отправлена флористу."

    try:
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=confirm_order_with_promo_kb(), parse_mode="HTML")
        else:
            await callback.message.edit_text(text, reply_markup=confirm_order_with_promo_kb(), parse_mode="HTML")
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=confirm_order_with_promo_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "confirm_order")
async def cb_confirm_order(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    cart = get_cart(user_id)
    if not cart:
        await callback.answer("Корзина пуста", show_alert=True)
        return
    await state.set_state(OrderComment.waiting)
    try:
        await callback.message.edit_text(
            "💬 <b>Есть пожелания к заказу?</b>\n\n"
            "Напишите их одним сообщением (например, «без лилий» или «доставить к 18:00»).\n"
            "Или отправьте «-», чтобы пропустить.",
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            "💬 <b>Есть пожелания к заказу?</b>\n\n"
            "Напишите их одним сообщением (например, «без лилий» или «доставить к 18:00»).\n"
            "Или отправьте «-», чтобы пропустить.",
            parse_mode="HTML",
        )
    await callback.answer()


@router.message(OrderComment.waiting)
async def cb_order_comment(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    cart = get_cart(user_id)
    if not cart:
        await state.clear()
        await message.answer("Корзина пуста.", reply_markup=main_menu_kb())
        return

    comment = "" if message.text.strip() == "-" else message.text.strip()
    total = get_cart_total(user_id)
    items = format_cart(user_id)
    user = message.from_user

    # Сначала сбрасываем состояние, потом сохраняем
    await state.clear()

    promo_code, discount = user_promos.pop(user_id, (None, 0))
    final_total = int(total * (100 - discount) / 100) if discount else total

    try:
        order_id = await add_order(
            user_id=user.id,
            username=user.username or "",
            full_name=user.full_name,
            phone="",
            comment=comment,
            items=items,
            total=final_total,
            promo=promo_code,
            discount=discount,
        )
    except Exception as e:
        await message.answer(
            f"⚠️ Ошибка сохранения заказа: {e}\n\nПопробуйте оформить заново.",
            reply_markup=main_menu_kb(),
        )
        return

    order_text = (
        f"🆕 <b>Новый заказ #{order_id}!</b>\n"
        f"От: {user.full_name} (@{user.username or 'нет'})\n"
        f"ID: <code>{user.id}</code>\n"
    )
    if comment:
        order_text += f"💬 Комментарий: <i>{comment}</i>\n"
    if discount:
        order_text += f"🎟 Промокод: <b>{promo_code}</b> (-{discount}%)\n"
        order_text += f"\n{items}\n\n💰 Сумма со скидкой: <b>{final_total} {CURRENCY_SYMBOL}</b>"
    else:
        order_text += f"\n{items}\n\n💰 Сумма: <b>{total} {CURRENCY_SYMBOL}</b>"

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, order_text, parse_mode="HTML")
        except Exception:
            pass

    clear_cart(user_id)

    await message.answer(
        f"✅ <b>Заказ #{order_id} принят!</b>\n\n"
        + (f"💬 Комментарий: <i>{comment}</i>\n\n" if comment else "")
        + (f"🎟 Промокод: <b>{promo_code}</b> (-{discount}%)\n" if discount else "")
        + f"Сумма: <b>{final_total} {CURRENCY_SYMBOL}</b>\n\nФлорист свяжется с вами.",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )


@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@router.message(F.content_type == ContentType.SUCCESSFUL_PAYMENT)
async def process_successful_payment(message: Message, bot: Bot):
    payment = message.successful_payment
    user = message.from_user
    total = payment.total_amount / 100

    await add_order(
        user_id=user.id, username=user.username or "", full_name=user.full_name,
        phone="", comment="Оплачено через Telegram", items=format_cart(user.id), total=int(total),
    )
    clear_cart(user.id)

    await message.answer(
        f"✅ <b>Оплата прошла успешно!</b>\n\nСумма: <b>{total:.0f} {CURRENCY_SYMBOL}</b>\n"
        f"ID платежа: <code>{payment.telegram_payment_charge_id}</code>\n\n"
        "Флорист уже получил ваш заказ и скоро свяжется с вами.",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )

    admin_text = (
        f"💰 <b>Оплаченный заказ!</b>\nОт: {user.full_name} (@{user.username or 'нет'})\n"
        f"ID: <code>{user.id}</code>\nСумма: <b>{total:.0f} {CURRENCY_SYMBOL}</b>\n"
        f"Telegram charge: <code>{payment.telegram_payment_charge_id}</code>"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_text, parse_mode="HTML")
        except Exception:
            pass