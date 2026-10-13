from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import ADMIN_IDS
from data.database import get_orders, get_order_by_id, update_order_status, get_stats

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def admin_menu_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="📦 Новые заказы", callback_data="admin_orders")
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.adjust(1)
    return builder.as_markup()


def orders_list_kb(orders):
    builder = InlineKeyboardBuilder()
    for order in orders:
        builder.button(
            text=f"#{order['id']} — {order['total']}₽ — {order['status']}",
            callback_data=f"order_view:{order['id']}"
        )
    builder.button(text="⬅️ Назад", callback_data="admin_back")
    builder.adjust(1)
    return builder.as_markup()


def order_status_kb(order_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Принят", callback_data=f"status:Принят:{order_id}")
    builder.button(text="🚚 В доставке", callback_data=f"status:В доставке:{order_id}")
    builder.button(text="✔️ Выполнен", callback_data=f"status:Выполнен:{order_id}")
    builder.button(text="❌ Отменён", callback_data=f"status:Отменён:{order_id}")
    builder.button(text="⬅️ К списку", callback_data="admin_orders")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа.")
        return
    await message.answer(
        "👑 <b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_orders")
async def show_orders(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    orders = await get_orders(20)
    if not orders:
        await callback.message.edit_text(
            "📭 Заказов пока нет.",
            reply_markup=admin_menu_kb(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"📦 <b>Последние заказы ({len(orders)}):</b>\n\nВыберите заказ:",
        reply_markup=orders_list_kb(orders),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("order_view:"))
async def view_order(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    order_id = int(callback.data.split(":")[1])
    order = await get_order_by_id(order_id)

    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    text = (
        f"📦 <b>Заказ #{order['id']}</b>\n\n"
        f"👤 {order['full_name']} (@{order['username'] or 'нет'})\n"
        f"🆔 <code>{order['user_id']}</code>\n"
        f"📞 {order.get('phone', 'не указан')}\n"
        f"📅 {order['created_at']}\n\n"
        f"🛒 <b>Состав:</b>\n{order['items']}\n\n"
        f"💰 Сумма: <b>{order['total']}₽</b>\n"
        f"📌 Статус: <b>{order['status']}</b>"
    )
    await callback.message.edit_text(
        text,
        reply_markup=order_status_kb(order_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("status:"))
async def set_status(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    _, status, order_id = callback.data.split(":")
    await update_order_status(int(order_id), status)
    await callback.answer(f"Статус изменён: {status}", show_alert=True)
    await view_order(callback)


@router.callback_query(F.data == "admin_stats")
async def show_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    count, total = await get_stats()
    await callback.message.edit_text(
        f"📊 <b>Статистика магазина</b>\n\n"
        f"Всего заказов: <b>{count}</b>\n"
        f"Общая сумма: <b>{total}₽</b>",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    await callback.message.edit_text(
        "👑 <b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()