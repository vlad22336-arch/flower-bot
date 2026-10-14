from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_IDS
from data.database import (
    get_top_products, get_avg_check, get_orders_by_days,
    get_stats, count_clients, count_products,
)

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def analytics_menu_kb():
    b = InlineKeyboardBuilder()
    b.button(text="🔥 Топ товаров", callback_data="an_top")
    b.button(text="💰 Средний чек", callback_data="an_avg")
    b.button(text="📅 За 7 дней", callback_data="an_week")
    b.button(text="📊 Общая сводка", callback_data="an_summary")
    b.button(text="⬅️ Назад", callback_data="admin_back")
    b.adjust(1)
    return b.as_markup()


@router.callback_query(F.data == "admin_analytics")
async def analytics_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    try:
        await callback.message.edit_text(
            "📊 <b>Аналитика</b>\n\nВыберите раздел:",
            reply_markup=analytics_menu_kb(),
            parse_mode="HTML",
        )
    except Exception:
        pass
    await callback.answer()


# ===== ТОП ТОВАРОВ =====

@router.callback_query(F.data == "an_top")
async def top_products(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    top = await get_top_products(10)

    if not top:
        try:
            await callback.message.edit_text(
                "🔥 <b>Топ товаров</b>\n\nПока нет данных — не было заказов.",
                reply_markup=analytics_menu_kb(),
                parse_mode="HTML",
            )
        except Exception:
            pass
        await callback.answer()
        return

    text = "🔥 <b>Топ-10 товаров:</b>\n\n"
    for i, (name, count) in enumerate(top, start=1):
        medal = ["🥇", "🥈", "🥉"][i - 1] if i <= 3 else f"{i}."
        text += f"{medal} {name} — <b>{count}</b> раз\n"

    try:
        await callback.message.edit_text(text, reply_markup=analytics_menu_kb(), parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()


# ===== СРЕДНИЙ ЧЕК =====

@router.callback_query(F.data == "an_avg")
async def avg_check(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    avg = await get_avg_check()
    count, total, new_count = await get_stats()

    text = (
        "💰 <b>Средний чек</b>\n\n"
        f"Средняя сумма заказа: <b>{avg}₽</b>\n\n"
        f"📦 Всего заказов: <b>{count}</b>\n"
        f"💵 Общая выручка: <b>{total}₽</b>\n"
        f"🆕 Новых заказов: <b>{new_count}</b>\n"
    )
    try:
        await callback.message.edit_text(text, reply_markup=analytics_menu_kb(), parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()


# ===== ЗА 7 ДНЕЙ =====

@router.callback_query(F.data == "an_week")
async def week_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    rows = await get_orders_by_days(7)

    if not rows:
        try:
            await callback.message.edit_text(
                "📅 <b>За 7 дней</b>\n\nПока нет заказов за этот период.",
                reply_markup=analytics_menu_kb(),
                parse_mode="HTML",
            )
        except Exception:
            pass
        await callback.answer()
        return

    text = "📅 <b>Заказы за 7 дней:</b>\n\n"
    total_sum = 0
    total_count = 0
    for date, count, summa in rows:
        text += f"• <b>{date}</b>: {count} зак. на {summa}₽\n"
        total_sum += summa
        total_count += count

    text += f"\n💵 Итого: <b>{total_count}</b> заказов на <b>{total_sum}₽</b>"

    try:
        await callback.message.edit_text(text, reply_markup=analytics_menu_kb(), parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()


# ===== ОБЩАЯ СВОДКА =====

@router.callback_query(F.data == "an_summary")
async def summary(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    count, total, new_count = await get_stats()
    clients = await count_clients()
    products = await count_products()
    avg = await get_avg_check()
    top = await get_top_products(3)

    text = (
        "📊 <b>Общая сводка</b>\n\n"
        f"📦 Заказов всего: <b>{count}</b>\n"
        f"🆕 Новых: <b>{new_count}</b>\n"
        f"💰 Выручка: <b>{total}₽</b>\n"
        f"💵 Средний чек: <b>{avg}₽</b>\n"
        f"👥 Клиентов: <b>{clients}</b>\n"
        f"🛍 Товаров: <b>{products}</b>\n"
    )
    if top:
        text += "\n🔥 <b>Топ-3 товара:</b>\n"
        for i, (name, cnt) in enumerate(top, start=1):
            text += f"{i}. {name} — {cnt} раз\n"

    try:
        await callback.message.edit_text(text, reply_markup=analytics_menu_kb(), parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()