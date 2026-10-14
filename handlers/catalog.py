from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InputMediaPhoto
from pathlib import Path
from data.products import CATEGORIES, get_category_products
from keyboards.inline import product_card_kb, extras_kb, back_to_menu_kb
from config import CURRENCY_SYMBOL

router = Router()


# Соответствие между текстом кнопки и кодом категории
TEXT_TO_CATEGORY = {
    "💐 Букеты": "bouquets",
    "🎁 Цветы в коробке": "boxes",
    "🪴 Растения": "plants",
}


def format_product_caption(product: dict) -> str:
    return (
        f"<b>{product['name']}</b>\n\n"
        f"{product['description']}\n\n"
        f"💰 <b>{product['price']} {CURRENCY_SYMBOL}</b>"
    )


# ===== ОТКРЫТИЕ КАТЕГОРИИ ПО ТЕКСТУ КНОПКИ =====

@router.message(F.text.in_(TEXT_TO_CATEGORY.keys()))
async def show_category_from_text(message: Message):
    category_id = TEXT_TO_CATEGORY[message.text]
    await send_category(message, category_id)


# ===== ОТКРЫТИЕ КАТЕГОРИИ ПО CALLBACK =====

@router.callback_query(F.data.startswith("category:"))
async def show_category_from_callback(callback: CallbackQuery):
    category_id = callback.data.split(":")[1]
    await send_category(callback, category_id, is_callback=True)


async def send_category(event, category_id: str, is_callback: bool = False):
    category = CATEGORIES.get(category_id)
    if not category:
        if is_callback:
            await event.answer("Категория не найдена", show_alert=True)
        else:
            await event.answer("Категория не найдена")
        return

    products = get_category_products(category_id)
    if not products:
        text = f"{category['name']}\n\nПока нет товаров в этой категории."
        if is_callback:
            try:
                await event.message.edit_text(text, reply_markup=back_to_menu_kb())
            except Exception:
                await event.message.answer(text, reply_markup=back_to_menu_kb())
            await event.answer()
        else:
            await event.answer(text, reply_markup=back_to_menu_kb())
        return

    await show_product(event, category_id, 0, is_callback)


# ===== КАРУСЕЛЬ ТОВАРОВ =====

@router.callback_query(F.data.startswith("product:"))
async def navigate_product(callback: CallbackQuery):
    parts = callback.data.split(":")
    category_id = parts[1]
    index = int(parts[2])
    await show_product(callback, category_id, index, is_callback=True)


async def show_product(event, category_id: str, index: int, is_callback: bool = False):
    products = get_category_products(category_id)
    if not products:
        if is_callback:
            await event.answer("Нет товаров", show_alert=True)
        return

    index = index % len(products)
    product = products[index]
    caption = format_product_caption(product)
    reply_markup = product_card_kb(
        category_id=category_id,
        product_id=product["id"],
        current_index=index,
        total=len(products),
    )

    image_path = product.get("image")
    has_image = image_path and Path(image_path).exists()

    # Если это callback — редактируем существующее сообщение
    if is_callback:
        try:
            if has_image:
                photo = FSInputFile(image_path)
                if event.message.photo:
                    media = InputMediaPhoto(media=photo, caption=caption, parse_mode="HTML")
                    await event.message.edit_media(media=media, reply_markup=reply_markup)
                else:
                    await event.message.delete()
                    await event.message.answer_photo(
                        photo=photo,
                        caption=caption,
                        reply_markup=reply_markup,
                        parse_mode="HTML",
                    )
            else:
                if event.message.photo:
                    await event.message.delete()
                    await event.message.answer(
                        caption, reply_markup=reply_markup, parse_mode="HTML"
                    )
                else:
                    await event.message.edit_text(
                        caption, reply_markup=reply_markup, parse_mode="HTML"
                    )
        except Exception:
            await event.message.answer(caption, reply_markup=reply_markup, parse_mode="HTML")
        await event.answer()
    else:
        # Если это текстовое сообщение — просто отправляем карточку
        try:
            if has_image:
                photo = FSInputFile(image_path)
                await event.answer_photo(
                    photo=photo,
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode="HTML",
                )
            else:
                await event.answer(
                    caption, reply_markup=reply_markup, parse_mode="HTML"
                )
        except Exception:
            await event.answer(caption, reply_markup=reply_markup, parse_mode="HTML")


# ===== ДОПОЛНИТЕЛЬНЫЕ ТОВАРЫ =====

@router.message(F.text == "✨ Дополнить заказ")
async def show_extras_from_text(message: Message):
    text = "✨ <b>Дополнить заказ</b>\n\nДобавьте приятные мелочи к букету:"
    await message.answer(text, reply_markup=extras_kb(), parse_mode="HTML")


@router.callback_query(F.data == "extras")
async def show_extras(callback: CallbackQuery):
    text = "✨ <b>Дополнить заказ</b>\n\nДобавьте приятные мелочи к букету:"
    try:
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=extras_kb(), parse_mode="HTML")
        else:
            await callback.message.edit_text(text, reply_markup=extras_kb(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=extras_kb(), parse_mode="HTML")
    await callback.answer()