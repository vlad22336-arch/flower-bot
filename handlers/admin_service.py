from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import os

from config import ADMIN_IDS
from data.database import (
    backup_db, delete_old_orders, get_all_orders, DB_PATH,
)

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


class CleanupDays(StatesGroup):
    days = State()


def service_menu_kb():
    b = InlineKeyboardBuilder()
    b.button(text="💾 Скачать базу", callback_data="srv_backup")
    b.button(text="🗑 Очистить старые заказы", callback_data="srv_cleanup")
    b.button(text="⬅️ Назад", callback_data="admin_back")
    b.adjust(1)
    return b.as_markup()


@router.callback_query(F.data == "admin_service")
async def service_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not is_admin(callback.from_user.id):
        return
    try:
        await callback.message.edit_text(
            "🔧 <b>Сервис</b>\n\nВыберите действие:",
            reply_markup=service_menu_kb(),
            parse_mode="HTML",
        )
    except Exception:
        pass
    await callback.answer()


# ===== РЕЗЕРВНОЕ КОПИРОВАНИЕ =====

@router.callback_query(F.data == "srv_backup")
async def backup(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    path = await backup_db()
    if not path or not os.path.exists(path):
        await callback.answer("❌ Файл базы не найден", show_alert=True)
        return

    try:
        with open(path, "rb") as f:
            data = f.read()
        file = BufferedInputFile(data, filename="orders_backup.db")
        await callback.message.answer_document(
            file,
            caption=(
                "💾 <b>Резервная копия базы</b>\n\n"
                "Сохраните этот файл — в нём все заказы, товары, клиенты и промокоды.\n\n"
                "Чтобы восстановить базу — загрузите её через «Файлы» на хостинге в папку <code>data/</code>."
            ),
            parse_mode="HTML",
        )
        await callback.answer("Файл отправлен!")
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


# ===== ОЧИСТКА СТАРЫХ ЗАКАЗОВ =====

@router.callback_query(F.data == "srv_cleanup")
async def cleanup_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(CleanupDays.days)
    try:
        await callback.message.edit_text(
            "🗑 <b>Очистка старых заказов</b>\n\n"
            "Введите, за сколько дней удалить заказы.\n"
            "Например: <code>90</code> — удалит заказы старше 90 дней.\n\n"
            "Отправьте «-» чтобы отменить.",
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer("Введите количество дней:")
    await callback.answer()


@router.message(CleanupDays.days)
async def cleanup_apply(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    if message.text.strip() == "-":
        await state.clear()
        await message.answer("Отменено.", reply_markup=service_menu_kb())
        return

    if not message.text.isdigit():
        await message.answer("⚠️ Введите число.")
        return

    days = int(message.text)
    if days < 1:
        await message.answer("⚠️ Дней должно быть больше 0.")
        return

    # Считаем, сколько будет удалено
    all_orders = await get_all_orders()
    await delete_old_orders(days)
    await state.clear()

    await message.answer(
        f"✅ Заказы старше <b>{days}</b> дней удалены.",
        reply_markup=service_menu_kb(),
        parse_mode="HTML",
    )