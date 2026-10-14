from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.database import (
    add_important_date, get_important_dates, delete_important_date,
)

router = Router()


class AddDate(StatesGroup):
    name = State()
    date = State()
    contact = State()


def dates_menu_kb(dates_list):
    b = InlineKeyboardBuilder()
    for d in dates_list:
        text = f"❌ {d['date']} — {d['name']}"
        if d.get("contact"):
            text += f" ({d['contact']})"
        b.button(text=text, callback_data=f"del_date:{d['id']}")
    b.button(text="➕ Добавить дату", callback_data="add_date")
    b.button(text="◀️ В меню", callback_data="main_menu")
    b.adjust(1)
    return b.as_markup()


@router.message(F.text == "🎂 Важные даты")
async def cmd_dates(message: Message):
    dates_list = await get_important_dates(message.from_user.id)

    if not dates_list:
        text = (
            "🎂 <b>Важные даты</b>\n\n"
            "Здесь можно сохранить дни рождения и годовщины близких.\n\n"
            "Можно прикрепить <b>@username</b> — и бот напомнит, кому написать.\n\n"
            "Пока у вас нет сохранённых дат.\n\n"
            "Нажмите «➕ Добавить дату», чтобы создать первую."
        )
    else:
        text = (
            "🎂 <b>Ваши важные даты</b>\n\n"
            "Нажмите на ❌ рядом с датой, чтобы удалить её.\n\n"
            f"Всего сохранено: <b>{len(dates_list)}</b>"
        )

    await message.answer(
        text,
        reply_markup=dates_menu_kb(dates_list),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "add_date")
async def add_date_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddDate.name)
    try:
        await callback.message.edit_text(
            "🎂 <b>Новая важная дата</b>\n\n"
            "Шаг 1 из 3. Введите <b>имя</b> человека.\n"
            "Например: <i>Мама</i>, <i>Жена</i>, <i>Друг Сергей</i>",
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer("Введите имя человека:")
    await callback.answer()


@router.message(AddDate.name)
async def add_date_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AddDate.date)
    await message.answer(
        "📅 Шаг 2 из 3. Введите <b>дату</b> в формате <code>ДД.ММ</code>.\n\n"
        "Например: <code>15.03</code> (15 марта) или <code>01.01</code> (1 января)",
        parse_mode="HTML",
    )


@router.message(AddDate.date)
async def add_date_date(message: Message, state: FSMContext):
    text = message.text.strip()
    parts = text.split(".")

    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        await message.answer(
            "⚠️ Неверный формат. Введите как <code>15.03</code>",
            parse_mode="HTML",
        )
        return

    day, month = int(parts[0]), int(parts[1])
    if not (1 <= day <= 31 and 1 <= month <= 12):
        await message.answer("⚠️ Некорректная дата. Проверьте день и месяц.")
        return

    await state.update_data(date=text)
    await state.set_state(AddDate.contact)
    await message.answer(
        "👤 Шаг 3 из 3. Прикрепите <b>Telegram-контакт</b> (необязательно).\n\n"
        "Введите <code>@username</code> человека или отправьте «-», чтобы пропустить.\n\n"
        "Пример: <code>@ivan_petrov</code>",
        parse_mode="HTML",
    )


@router.message(AddDate.contact)
async def add_date_contact(message: Message, state: FSMContext):
    text = message.text.strip()
    contact = None

    if text != "-":
        contact = text.lstrip("@")
        if not contact.replace("_", "").isalnum():
            await message.answer(
                "⚠️ Неверный формат. Введите как <code>@username</code> или «-» чтобы пропустить.",
                parse_mode="HTML",
            )
            return
        contact = "@" + contact

    data = await state.get_data()
    name = data["name"]
    date = data["date"]
    await add_important_date(message.from_user.id, name, date, contact)
    await state.clear()

    text_out = (
        f"✅ <b>Дата сохранена!</b>\n\n"
        f"👤 Имя: <b>{name}</b>\n"
        f"📅 Дата: <b>{date}</b>\n"
    )
    if contact:
        text_out += f"🔗 Контакт: <b>{contact}</b>\n"
    text_out += "\nМы напомним вам заранее."

    await message.answer(text_out, parse_mode="HTML")


@router.callback_query(F.data.startswith("del_date:"))
async def delete_date(callback: CallbackQuery):
    date_id = int(callback.data.split(":")[1])
    await delete_important_date(date_id)
    await callback.answer("🗑 Дата удалена", show_alert=True)

    dates_list = await get_important_dates(callback.from_user.id)
    if not dates_list:
        try:
            await callback.message.edit_text(
                "🎂 <b>Важные даты</b>\n\n"
                "У вас больше нет сохранённых дат.\n\n"
                "Нажмите «➕ Добавить дату», чтобы создать новую.",
                reply_markup=dates_menu_kb([]),
                parse_mode="HTML",
            )
        except Exception:
            pass
    else:
        try:
            await callback.message.edit_text(
                f"🎂 <b>Ваши важные даты</b>\n\n"
                f"Всего сохранено: <b>{len(dates_list)}</b>",
                reply_markup=dates_menu_kb(dates_list),
                parse_mode="HTML",
            )
        except Exception:
            pass