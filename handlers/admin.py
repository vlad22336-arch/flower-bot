from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import os

from config import ADMIN_IDS
from data.database import (
    get_orders, get_order_by_id, update_order_status, get_stats,
    add_product, get_products, get_product_by_id, update_product, delete_product,
    get_clients, count_clients, set_setting, get_setting, count_products,
)

router = Router()


# ===== СОСТОЯНИЯ =====

class AddProduct(StatesGroup):
    category = State()
    name = State()
    price = State()
    description = State()
    image = State()


class EditProduct(StatesGroup):
    name = State()
    price = State()
    description = State()


class SearchOrder(StatesGroup):
    query = State()


class Broadcast(StatesGroup):
    message = State()


class EditSetting(StatesGroup):
    key = State()
    value = State()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ===== ГЛАВНОЕ МЕНЮ =====

def admin_menu_kb():
    b = InlineKeyboardBuilder()
    b.button(text="📦 Заказы", callback_data="admin_orders")
    b.button(text="🛍 Товары", callback_data="admin_products")
    b.button(text="📊 Статистика", callback_data="admin_stats")
    b.button(text="👥 Клиенты / Рассылка", callback_data="admin_clients")
    b.button(text="🔍 Поиск заказа", callback_data="admin_search")
    b.button(text="📝 Тексты бота", callback_data="admin_texts")
    b.adjust(2, 2, 1, 1)
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
    await callback.message.edit_text(
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
    b.button(text="⬅️ Назад", callback_data="admin_back")
    b.adjust(2, 2, 1, 1)
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
    await callback.message.edit_text(
        "📦 <b>Заказы</b>\n\nВыберите фильтр:",
        reply_markup=orders_filter_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ordf:"))
async def show_orders(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    status = callback.data.split(":")[1]
    status = None if status == "all" else status
    orders = await get_orders(30, status)

    if not orders:
        await callback.message.edit_text(
            "📭 Заказов нет.",
            reply_markup=orders_filter_kb(),
        )
        await callback.answer()
        return

    title = f"📦 <b>Заказы ({status or 'все'}):</b>\n\nВсего: {len(orders)}"
    await callback.message.edit_text(
        title,
        reply_markup=orders_list_kb(orders),
        parse_mode="HTML",
    )
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
        f"🛒 {o['items']}\n\n"
        f"💰 Сумма: <b>{o['total']}₽</b>\n"
        f"📌 Статус: <b>{o['status']}</b>"
    )
    await callback.message.edit_text(text, reply_markup=order_status_kb(order_id), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("status:"))
async def set_status(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    _, status, order_id = callback.data.split(":")
    await update_order_status(int(order_id), status)
    await callback.answer(f"Статус: {status}", show_alert=True)
    await view_order(callback)


# ===== ПОИСК ЗАКАЗА =====

@router.callback_query(F.data == "admin_search")
async def search_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(SearchOrder.query)
    await callback.message.edit_text("🔍 Введите номер заказа (например: 5):")
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
    products = await count_products()
    await callback.message.edit_text(
        f"📊 <b>Статистика</b>\n\n"
        f"📦 Всего заказов: <b>{count}</b>\n"
        f"🆕 Новых: <b>{new_count}</b>\n"
        f"💰 Выручка: <b>{total}₽</b>\n"
        f"👥 Клиентов: <b>{clients}</b>\n"
        f"🛍 Товаров: <b>{products}</b>",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


# ===== ТОВАРЫ =====

def products_menu_kb():
    b = InlineKeyboardBuilder()
    b.button(text="➕ Добавить товар", callback_data="product_add")
    b.button(text="📋 Список товаров", callback_data="product_list")
    b.button(text="⬅️ Назад", callback_data="admin_back")
    b.adjust(1)
    return b.as_markup()


def categories_kb():
    b = InlineKeyboardBuilder()
    b.button(text="💐 Букеты", callback_data="cat:bouquets")
    b.button(text="🎁 Коробки", callback_data="cat:boxes")
    b.button(text="🪴 Растения", callback_data="cat:plants")
    b.button(text="⬅️ Отмена", callback_data="admin_products")
    b.adjust(1)
    return b.as_markup()


@router.callback_query(F.data == "admin_products")
async def products_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "🛍 <b>Управление товарами</b>",
        reply_markup=products_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "product_list")
async def product_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    products = await get_products()
    if not products:
        await callback.message.edit_text("📭 Товаров нет.", reply_markup=products_menu_kb())
        await callback.answer()
        return
    b = InlineKeyboardBuilder()
    for p in products:
        b.button(text=f"{p['name']} — {p['price']}₽", callback_data=f"prod_view:{p['id']}")
    b.button(text="⬅️ Назад", callback_data="admin_products")
    b.adjust(1)
    await callback.message.edit_text(
        f"📋 <b>Товары ({len(products)}):</b>",
        reply_markup=b.as_markup(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("prod_view:"))
async def product_view(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    p = await get_product_by_id(int(callback.data.split(":")[1]))
    if not p:
        await callback.answer("Не найдено", show_alert=True)
        return
    b = InlineKeyboardBuilder()
    b.button(text="✏️ Изменить", callback_data=f"prod_edit:{p['id']}")
    b.button(text="🖼 Картинка", callback_data=f"prod_img:{p['id']}")
    b.button(text="🗑 Удалить", callback_data=f"prod_del:{p['id']}")
    b.button(text="⬅️ Назад", callback_data="product_list")
    b.adjust(2, 1, 1)
    text = (
        f"🛍 <b>{p['name']}</b>\n\n"
        f"📁 {p['category']}\n"
        f"💰 <b>{p['price']}₽</b>\n"
        f"📝 {p['description']}\n"
        f"🖼 {p['image'] or 'нет'}"
    )
    await callback.message.edit_text(text, reply_markup=b.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("prod_del:"))
async def product_delete(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    await delete_product(int(callback.data.split(":")[1]))
    await callback.answer("🗑 Удалено", show_alert=True)
    await product_list(callback)


# --- РЕДАКТИРОВАНИЕ ТОВАРА ---

@router.callback_query(F.data.startswith("prod_edit:"))
async def product_edit(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    pid = int(callback.data.split(":")[1])
    await state.update_data(edit_id=pid)
    await state.set_state(EditProduct.name)
    p = await get_product_by_id(pid)
    await callback.message.edit_text(
        f"✏️ <b>{p['name']}</b>\n\nВведите новое название (или «-» чтобы пропустить):",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(EditProduct.name)
async def edit_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    name = None if message.text == "-" else message.text
    await state.update_data(name=name)
    await state.set_state(EditProduct.price)
    await message.answer("Введите новую цену (цифры) или «-» чтобы пропустить:")


@router.message(EditProduct.price)
async def edit_price(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    price = None if message.text == "-" else (int(message.text) if message.text.isdigit() else None)
    await state.update_data(price=price)
    await state.set_state(EditProduct.description)
    await message.answer("Введите новое описание или «-» чтобы пропустить:")


@router.message(EditProduct.description)
async def edit_description(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    desc = None if message.text == "-" else message.text
    await update_product(
        product_id=data["edit_id"],
        name=data.get("name"),
        price=data.get("price"),
        description=desc,
    )
    await state.clear()
    await message.answer("✅ Товар обновлён.", reply_markup=admin_menu_kb())


# --- КАРТИНКА ТОВАРА ---

@router.callback_query(F.data.startswith("prod_img:"))
async def product_img_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    pid = int(callback.data.split(":")[1])
    await state.update_data(edit_id=pid)
    await state.set_state(AddProduct.image)
    await callback.message.edit_text(
        "🖼 Отправьте картинку для товара (или «-» чтобы удалить):"
    )
    await callback.answer()


@router.message(AddProduct.image, F.photo)
async def product_img_set(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    pid = data.get("edit_id")
    os.makedirs("images", exist_ok=True)
    file_path = f"images/product_{pid}.jpg"
    await message.bot.download(message.photo[-1], destination=file_path)
    await update_product(pid, image=file_path)
    await state.clear()
    await message.answer("✅ Картинка обновлена.", reply_markup=admin_menu_kb())


# --- ДОБАВЛЕНИЕ ТОВАРА ---

@router.callback_query(F.data == "product_add")
async def product_add_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.clear()
    await callback.message.edit_text(
        "🛍 <b>Добавление товара</b>\n\nВыберите категорию:",
        reply_markup=categories_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat:"))
async def product_add_cat(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.update_data(category=callback.data.split(":")[1])
    await state.set_state(AddProduct.name)
    await callback.message.edit_text("Введите <b>название</b> товара:", parse_mode="HTML")
    await callback.answer()


@router.message(AddProduct.name)
async def add_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(name=message.text)
    await state.set_state(AddProduct.price)
    await message.answer("Введите <b>цену</b> (цифры, в рублях):", parse_mode="HTML")


@router.message(AddProduct.price)
async def add_price(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if not message.text.isdigit():
        await message.answer("⚠️ Только цифры!")
        return
    await state.update_data(price=int(message.text))
    await state.set_state(AddProduct.description)
    await message.answer("Введите <b>описание</b>:", parse_mode="HTML")


@router.message(AddProduct.description)
async def add_description(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(description=message.text)
    await state.set_state(AddProduct.image)
    await message.answer(
        "🖼 Отправьте <b>картинку</b> или напишите «-» чтобы пропустить:",
        parse_mode="HTML",
    )


@router.message(AddProduct.image, F.photo)
async def add_image(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    os.makedirs("images", exist_ok=True)
    path = f"images/new_{message.from_user.id}.jpg"
    await message.bot.download(message.photo[-1], destination=path)
    pid = await add_product(
        category=data["category"],
        name=data["name"],
        price=data["price"],
        description=data["description"],
        image=path,
    )
    await state.clear()
    await message.answer(
        f"✅ Товар <b>{data['name']}</b> добавлен (ID {pid}).",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML",
    )


@router.message(AddProduct.image, F.text == "-")
async def add_no_image(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    pid = await add_product(
        category=data["category"],
        name=data["name"],
        price=data["price"],
        description=data["description"],
        image=None,
    )
    await state.clear()
    await message.answer(
        f"✅ Товар <b>{data['name']}</b> добавлен (ID {pid}).",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML",
    )


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
    await callback.message.edit_text(
        "👥 <b>Клиенты</b>",
        reply_markup=b.as_markup(),
        parse_mode="HTML",
    )
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
    await callback.message.edit_text(text, reply_markup=b.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(Broadcast.message)
    await callback.message.edit_text("📢 Напишите сообщение для рассылки всем клиентам:")
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
    await callback.message.edit_text(
        "📝 <b>Тексты бота</b>\n\nВыберите что изменить:",
        reply_markup=b.as_markup(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set:"))
async def setting_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    key = callback.data.split(":")[1]
    await state.update_data(key=key)
    await state.set_state(EditSetting.value)
    current = await get_setting(key, "не задано")
    await callback.message.edit_text(
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