from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto
from pathlib import Path
from data.products import CATEGORIES, get_category_products
from keyboards.inline import product_card_kb, extras_kb, back_to_menu_kb
from config import CURRENCY_SYMBOL

router = Router()


def format_product_caption(product: dict) -> str:
    return (
        f"<b>{product['name']}</b>\n\n"
        f"{product['description']}\n\n"
        f"💰 <b>{product['price']} {CURRENCY_SYMBOL}</b>"
    )


@router.callback_query(F.data.startswith("category:"))
async def show_category(callback: CallbackQuery):
    category_id = callback.data.split(":")[1]
    category = CATEGORIES.get(category_id)

    if not category:
        await callback.answer("Категория не найдена", show_alert=True)
        return

    products = get_category_products(category_id)
    if not products:
        await callback.message.edit_text(
            f"{category['name']}\n\nПока нет товаров в этой категории.",
            reply_markup=back_to_menu_kb(),
        )
        await callback.answer()
        return

    await show_product(callback, category_id, 0)


@router.callback_query(F.data.startswith("product:"))
async def navigate_product(callback: CallbackQuery):
    parts = callback.data.split(":")
    category_id = parts[1]
    index = int(parts[2])
    await show_product(callback, category_id, index)


async def show_product(callback: CallbackQuery, category_id: str, index: int):
    products = get_category_products(category_id)
    if not products:
        await callback.answer("Нет товаров", show_alert=True)
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

    try:
        if has_image:
            photo = FSInputFile(image_path)
            if callback.message.photo:
                media = InputMediaPhoto(media=photo, caption=caption, parse_mode="HTML")
                await callback.message.edit_media(media=media, reply_markup=reply_markup)
            else:
                await callback.message.delete()
                await callback.message.answer_photo(
                    photo=photo,
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode="HTML",
                )
        else:
            if callback.message.photo:
                await callback.message.delete()
                await callback.message.answer(
                    caption,
                    reply_markup=reply_markup,
                    parse_mode="HTML",
                )
            else:
                await callback.message.edit_text(
                    caption,
                    reply_markup=reply_markup,
                    parse_mode="HTML",
                )
    except Exception:
        await callback.message.answer(
            caption,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )

    await callback.answer()


@router.callback_query(F.data == "extras")
async def show_extras(callback: CallbackQuery):
    text = (
        "✨ <b>Дополнить заказ</b>\n\n"
        "Добавьте приятные мелочи к букету:"
    )
    try:
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(
                text,
                reply_markup=extras_kb(),
                parse_mode="HTML",
            )
        else:
            await callback.message.edit_text(
                text,
                reply_markup=extras_kb(),
                parse_mode="HTML",
            )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=extras_kb(),
            parse_mode="HTML",
        )
    await callback.answer()
