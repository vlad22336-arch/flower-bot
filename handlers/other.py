from aiogram import Router, F
from aiogram.types import CallbackQuery
from keyboards.inline import back_to_menu_kb
from config import DEMO_MODE

router = Router()


async def safe_edit_or_send(callback: CallbackQuery, text: str):
    """Редактирует текст или отправляет новое сообщение, если было фото."""
    try:
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(
                text,
                reply_markup=back_to_menu_kb(),
                parse_mode="HTML",
            )
        else:
            await callback.message.edit_text(
                text,
                reply_markup=back_to_menu_kb(),
                parse_mode="HTML",
            )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=back_to_menu_kb(),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "dates")
async def show_dates(callback: CallbackQuery):
    text = (
        "🎂 <b>Важные даты</b>\n\n"
        "Здесь можно сохранить дни рождения и годовщины близких.\n"
        "Бот напомнит заранее и предложит подходящий букет.\n\n"
    )
    if DEMO_MODE:
        text += "<i>Функция в разработке (демо-режим).</i>"
    else:
        text += "Напишите дату в формате ДД.ММ и имя — мы сохраним."

    await safe_edit_or_send(callback, text)
    await callback.answer()


@router.callback_query(F.data == "manager")
async def show_manager(callback: CallbackQuery):
    text = (
        "💬 <b>Связь с менеджером</b>\n\n"
        "Напишите ваш вопрос прямо в этот чат — "
        "менеджер ответит в ближайшее время.\n\n"
        "Или позвоните: +7 (999) 123-45-67"
    )
    await safe_edit_or_send(callback, text)
    await callback.answer()


@router.callback_query(F.data == "contacts")
async def show_contacts(callback: CallbackQuery):
    text = (
        "📍 <b>Контакты</b>\n\n"
        "🌷 Цветочная мастерская\n\n"
        "📱 Телефон: +7 (999) 123-45-67\n"
        "📧 Email: flowers@example.com\n"
        "🕒 Режим работы: ежедневно 9:00–21:00\n"
        "📍 Адрес: г. Москва, ул. Цветочная, 15\n\n"
        "Доставка по городу от 300 ₽"
    )
    await safe_edit_or_send(callback, text)
    await callback.answer()
