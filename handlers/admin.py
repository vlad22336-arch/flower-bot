from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import csv
import io

from config import ADMIN_IDS
from data.database import (
    get_orders, get_order_by_id, update_order_status, get_stats,
    get_clients, count_clients, set_setting, get_setting,
    get_all_orders,
)

router = Router()


class SearchOrder(StatesGroup):
    query = State()


class Broadcast(StatesGroup):
    message = State()


class EditSetting(StatesGroup):
    key = State()
    value = State()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def admin_menu_kb():
    b = InlineKeyboardBuilder()
    b.button(text="📦 Заказы", callback_data="admin_orders")
    b.button(text="🛍 Товары", callback_data="admin_products")
    b.button(text="📊 Статистика", callback_data="admin_stats")
    b.button(text="👥 Клиенты / Рассылка", callback_data="admin_clients")
    b.button(text="🔍 Поиск заказа", callback_data="admin_search")
    b.button(text="🎟 Промокоды", callback_data="admin_promos")
    b.button(text="📝 Тексты бота", callback_data="admin_texts")
    b.adjust(2, 2, 1, 1, 1)
    return b.as_markup()


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


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.edit_text(
            "👑 <b>Админ-панель</b>\n\nВыберите действие:",
            reply_markup=admin_menu_kb(),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            "👑 <b>Админ-панель</b>\n\nВыберите действие:",
            reply_markup=admin_menu_kb(),
            parse_mode="HTML",
        )
    await callback.answer()


# ===== ЗАКАЗЫ =====

def orders_filter_kb():
    b = InlineKeyboardBuilder()
    b.button(text="🆕 Новые", callback_data="ordf:Новый")
    b.button(text="🚚 В доставке", callback_data="ordf:В доставке")
    b.button(text="✔️ Выполненные", callback_data="ordf:Выполнен")
    b.button(text="❌ Отменённые", callback_data="ordf:Отменён")
    b.button(text="📋 Все", callback_data="ordf:all")
    b.button(text="📥 Экспорт в CSV", callback_data="export_csv")
    b.button(text="⬅️ Назад", callback_data="admin_back")
    b.adjust(2, 2, 1, 1, 1)
    return b.as_markup()


def orders_list_kb(orders):
    b = InlineKeyboardBuilder()
    for o in orders:
        b.button(
            text=f"#{o['id']} — {o['total']}₽ — {o['status']}",
            callback_data=f"order_view:{o['id']}"
        )
    b.button(text="🔄 Обновить", callback_data="admin_orders")
    b.button(text="⬅️ Назад", callback_data="admin_back")
    b.adjust(1)
    return b.as_markup()


def order_status_kb(order_id: int):
    b = InlineKeyboardBuilder()
    b.button(text="✅ Принят", callback_data=f"status:Принят:{order_id}")
    b.button(text="🚚 В доставке", callback_data=f"status:В доставке:{order_id}")
    b.button(text="✔️ Выполнен", callback_data=f"status:Выполнен:{order_id}")
    b.button(text="❌ Отменён", callback_data=f"status:Отменён:{order_id}")
    b.button(text="⬅️ К списку", callback_data="admin_orders")
    b.adjust(2, 2, 1)
    return b.as_markup()


@router.callback_query(F.data == "admin_orders")
async def show_orders_filter(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    try:
        await callback.message.edit_text(
            "📦 <b>Заказы</b>\n\nВыберите фильтр:",
            reply_markup=orders_filter_kb(),
            parse_mode="HTML",
        )
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("ordf:"))
async def show_orders(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    status = callback.data.split(":")[1]
    status = None if status == "all" else status
    orders = await get_orders(30, status)
    if not orders:
        try:
            await callback.message.edit_text("📭 Заказов нет.", reply_markup=orders_filter_kb())
        except Exception:
            pass
        await callback.answer()
        return
    title = f"📦 <b>Заказы ({status or 'все'}):</b>\n\nВсего: {len(orders)}"
    try:
        await callback.message.edit_text(title, reply_markup=orders_list_kb(orders), parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("order_view:"))
async def view_order(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    order_id = int(callback.data.split(":")[1])
    o = await get_order_by_id(order_id)
    if not o:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    text = (
        f"📦 <b>Заказ #{o['id']}</b>\n\n"
        f"👤 {o['full_name']} (@{o['username'] or 'нет'})\n"
        f"🆔 <code>{o['user_id']}</code>\n"
        f"📞 {o.get('phone', '—')}\n"
        f"📅 {o['created_at']}\n\n"
    )
    if o.get("comment"):
        text += f"💬 Комментарий: <i>{o['comment']}</i>\n\n"
    if o.get("discount"):
        text += f"🎟 Промокод: <b>{o['promo']}</b> (-{o['discount']}%)\n\n"
    text += (
        f"🛒 {o['items']}\n\n"
        f"💰 Сумма: <b>{o['total']}₽</b>\n"
        f"📌 Статус: <b>{o['status']}</b>"
    )
    try:
        await callback.message.edit_text(text, reply_markup=order_status_kb(order_id), parse_mode="HTML")
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=order_status_kb(order_id), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("status:"))
async def set_status(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return
    _, status, order_id = callback.data.split(":")
    order_id_int = int(order_id)
    order = await get_order_by_id(order_id_int)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    old_status = order["status"]
    await update_order_status(order_id_int, status)
    if old_status != status:
        status_texts = {
            "Принят": "✅ Ваш заказ принят! Флорист приступил к сборке.",
            "В доставке": "🚚 Ваш заказ в пути! Курьер скоро будет у вас.",
            "Выполнен": "✔️ Заказ выполнен. Спасибо за покупку! Будем рады видеть вас снова. 🌷",
            "Отменён": "❌ К сожалению, ваш заказ отменён. Свяжитесь с менеджером для уточнения деталей.",
        }
        text = status_texts.get(status, f"📌 Статус вашего заказа изменён: {status}")
        try:
            await bot.send_message(
                order["user_id"],
                f"<b>Заказ #{order_id_int}</b>\n\n{text}\n\n💰 Сумма: <b>{order['total']}₽</b>",
                parse_mode="HTML",
            )
        except Exception:
            pass
    try:
        await view_order(callback)
    except Exception:
        pass
    try:
        await callback.answer(f"Статус: {status}")
    except Exception:
        pass


@router.callback_query(F.data == "export_csv")
async def export_orders_csv(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    orders = await get_all_orders()
    if not orders:
        await callback.answer("Заказов нет для экспорта", show_alert=True)
        return
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow([
        "ID", "Дата", "Клиент", "Username", "User ID",
        "Телефон", "Комментарий", "Товары", "Промокод",
        "Скидка %", "Сумма", "Статус"
    ])
    for o in orders:
        writer.writerow([
            o["id"], o["created_at"], o["full_name"],
            o.get("username") or "", o["user_id"],
            o.get("phone") or "", o.get("comment") or "",
            (o["items"] or "").replace("\n", " | "),
            o.get("promo") or "", o.get("discount") or 0,
            o["total"], o["status"],
        ])
    csv_bytes = output.getvalue().encode("utf-8-sig")
    file = BufferedInputFile(csv_bytes, filename="orders.csv")
    await callback.message.answer_document(
        file,
        caption=f"📥 Экспорт заказов\n\nВсего: <b>{len(orders)}</b>",
        parse_mode="HTML",
    )
    await callback.answer("Файл отправлен!")


# ===== ПОИСК ЗАКАЗА =====

@router.callback_query(F.data == "admin_search")
async def search_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(SearchOrder.query)
    try:
        await callback.message.edit_text("🔍 Введите номер заказа (например: 5):")
    except Exception:
        await callback.message.answer("🔍 Введите номер заказа (например: 5):")
    await callback.answer()


@router.message(SearchOrder.query)
async def search_result(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if not message.text.isdigit():
        await message.answer("⚠️ Введите только цифры.")
        return
    o = await get_order_by_id(int(message.text))
    await state.clear()
    if not o:
        await message.answer("❌ Заказ не найден.", reply_markup=admin_menu_kb())
        return
    text = (
        f"📦 <b>Заказ #{o['id']}</b>\n\n"
        f"👤 {o['full_name']}\n🆔 <code>{o['user_id']}</code>\n"
        f"🛒 {o['items']}\n💰 {o['total']}₽\n📌 {o['status']}"
    )
    await message.answer(text, reply_markup=order_status_kb(o["id"]), parse_mode="HTML")


# ===== СТАТИСТИКА =====

@router.callback_query(F.data == "admin_stats")
async def show_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    count, total, new_count = await get_stats()
    clients = await count_clients()
    try:
        await callback.message.edit_text(
            f"📊 <b>Статистика</b>\n\n"
            f"📦 Всего заказов: <b>{count}</b>\n"
            f"🆕 Новых: <b>{new_count}</b>\n"
            f"💰 Выручка: <b>{total}₽</b>\n"
            f"👥 Клиентов: <b>{clients}</b>",
            reply_markup=admin_menu_kb(),
            parse_mode="HTML",
        )
    except Exception:
        pass
    await callback.answer()


# ===== КЛИЕНТЫ / РАССЫЛКА =====

@router.callback_query(F.data == "admin_clients")
async def clients_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    b = InlineKeyboardBuilder()
    b.button(text="👥 Список клиентов", callback_data="clients_list")
    b.button(text="📢 Сделать рассылку", callback_data="broadcast")
    b.button(text="⬅️ Назад", callback_data="admin_back")
    b.adjust(1)
    try:
        await callback.message.edit_text(
            "👥 <b>Клиенты</b>",
            reply_markup=b.as_markup(),
            parse_mode="HTML",
        )
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data == "clients_list")
async def clients_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    clients = await get_clients()
    b = InlineKeyboardBuilder()
    b.button(text="⬅️ Назад", callback_data="admin_clients")
    b.adjust(1)
    text = f"👥 <b>Клиентов: {len(clients)}</b>\n\n"
    for c in clients[:30]:
        text += f"• {c['full_name']} (@{c['username'] or '—'})\n"
    try:
        await callback.message.edit_text(text, reply_markup=b.as_markup(), parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data == "broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(Broadcast.message)
    try:
        await callback.message.edit_text("📢 Напишите сообщение для рассылки всем клиентам:")
    except Exception:
        await callback.message.answer("📢 Напишите сообщение для рассылки всем клиентам:")
    await callback.answer()


@router.message(Broadcast.message)
async def broadcast_send(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    clients = await get_clients()
    sent = failed = 0
    for c in clients:
        try:
            await message.bot.send_message(c["user_id"], message.text)
            sent += 1
        except Exception:
            failed += 1
    await state.clear()
    await message.answer(
        f"📢 Готово!\n\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}",
        reply_markup=admin_menu_kb(),
    )


# ===== ТЕКСТЫ БОТА =====

@router.callback_query(F.data == "admin_texts")
async def texts_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    b = InlineKeyboardBuilder()
    b.button(text="📞 Телефон", callback_data="set:phone")
    b.button(text="📍 Адрес", callback_data="set:address")
    b.button(text="✉️ Email", callback_data="set:email")
    b.button(text="🕒 Режим работы", callback_data="set:work_hours")
    b.button(text="⬅️ Назад", callback_data="admin_back")
    b.adjust(2, 2, 1)
    try:
        await callback.message.edit_text(
            "📝 <b>Тексты бота</b>\n\nВыберите что изменить:",
            reply_markup=b.as_markup(),
            parse_mode="HTML",
        )
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("set:"))
async def setting_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    key = callback.data.split(":")[1]
    await state.update_data(key=key)
    await state.set_state(EditSetting.value)
    current = await get_setting(key, "не задано")
    try:
        await callback.message.edit_text(
            f"Текущее значение: <b>{current}</b>\n\nВведите новое значение:",
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            f"Текущее значение: <b>{current}</b>\n\nВведите новое значение:",
            parse_mode="HTML",
        )
    await callback.answer()


@router.message(EditSetting.value)
async def setting_save(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    await set_setting(data["key"], message.text)
    await state.clear()
    await message.answer("✅ Сохранено.", reply_markup=admin_menu_kb())