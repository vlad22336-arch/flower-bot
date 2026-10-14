from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import os

from config import ADMIN_IDS
from data.database import (
    add_product, get_products, get_product_by_id,
    update_product, delete_product, change_all_prices, get_categories,
)

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ===== СОСТОЯНИЯ =====

class AddProduct(StatesGroup):
    category = State()
    name = State()
    price = State()
    old_price = State()
    description = State()
    image = State()
    flags = State()


class EditProduct(StatesGroup):
    name = State()
    price = State()
    description = State()


class MassPrice(StatesGroup):
    percent = State()


# ===== МЕНЮ ТОВАРОВ =====

def products_menu_kb():
    b = InlineKeyboardBuilder()
    b.button(text="➕ Добавить товар", callback_data="product_add")
    b.button(text="📋 Список товаров", callback_data="product_list")
    b.button(text="💰 Массовое изменение цен", callback_data="mass_price")
    b.button(text="⬅️ Назад", callback_data="admin_back")
    b.adjust(1)
    return b.as_markup()


@router.callback_query(F.data == "admin_products")
async def products_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not is_admin(callback.from_user.id):
        return
    try:
        await callback.message.edit_text(
            "🛍 <b>Управление товарами</b>",
            reply_markup=products_menu_kb(),
            parse_mode="HTML",
        )
    except Exception:
        pass
    await callback.answer()


# ===== СПИСОК ТОВАРОВ =====

@router.callback_query(F.data == "product_list")
async def product_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    products = await get_products()
    if not products:
        try:
            await callback.message.edit_text("📭 Товаров нет.", reply_markup=products_menu_kb())
        except Exception:
            pass
        await callback.answer()
        return
    b = InlineKeyboardBuilder()
    for p in products:
        flags = ""
        if p.get("is_hit"):
            flags += " 🔥"
        if p.get("is_new"):
            flags += " 🆕"
        if not p.get("in_stock"):
            flags += " ⛔"
        b.button(text=f"{p['name']} — {p['price']}₽{flags}", callback_data=f"prod_view:{p['id']}")
    b.button(text="⬅️ Назад", callback_data="admin_products")
    b.adjust(1)
    try:
        await callback.message.edit_text(
            f"📋 <b>Товары ({len(products)}):</b>",
            reply_markup=b.as_markup(),
            parse_mode="HTML",
        )
    except Exception:
        pass
    await callback.answer()


# ===== КАРТОЧКА ТОВАРА =====

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
    b.button(text="💰 Скидка", callback_data=f"prod_discount:{p['id']}")
    b.button(text="🔥 Хит", callback_data=f"prod_hit:{p['id']}")
    b.button(text="🆕 Новинка", callback_data=f"prod_new:{p['id']}")
    b.button(text="📦 Наличие", callback_data=f"prod_stock:{p['id']}")
    b.button(text="⬆️ Вверх", callback_data=f"prod_up:{p['id']}")
    b.button(text="⬇️ Вниз", callback_data=f"prod_down:{p['id']}")
    b.button(text="🗑 Удалить", callback_data=f"prod_del:{p['id']}")
    b.button(text="⬅️ Назад", callback_data="product_list")
    b.adjust(2, 2, 2, 2, 1, 1)

    old_price = f" (было {p['old_price']}₽)" if p.get("old_price") else ""
    flags = []
    if p.get("is_hit"):
        flags.append("🔥 Хит")
    if p.get("is_new"):
        flags.append("🆕 Новинка")
    if not p.get("in_stock"):
        flags.append("⛔ Нет в наличии")
    flags_text = " | ".join(flags) if flags else "—"

    text = (
        f"🛍 <b>{p['name']}</b>\n\n"
        f"📁 Категория: {p['category']}\n"
        f"💰 Цена: <b>{p['price']}₽</b>{old_price}\n"
        f"📝 Описание: {p['description']}\n"
        f"🏷 Метки: {flags_text}\n"
        f"🖼 Картинка: {'есть' if p.get('image') else 'нет'}"
    )
    try:
        await callback.message.edit_text(text, reply_markup=b.as_markup(), parse_mode="HTML")
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=b.as_markup(), parse_mode="HTML")
    await callback.answer()


# ===== БЫСТРЫЕ ДЕЙСТВИЯ =====

@router.callback_query(F.data.startswith("prod_hit:"))
async def toggle_hit(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    pid = int(callback.data.split(":")[1])
    p = await get_product_by_id(pid)
    new_val = 0 if p.get("is_hit") else 1
    await update_product(pid, is_hit=new_val)
    await callback.answer("🔥 Хит " + ("включён" if new_val else "выключен"), show_alert=True)
    await product_view(callback)


@router.callback_query(F.data.startswith("prod_new:"))
async def toggle_new(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    pid = int(callback.data.split(":")[1])
    p = await get_product_by_id(pid)
    new_val = 0 if p.get("is_new") else 1
    await update_product(pid, is_new=new_val)
    await callback.answer("🆕 Новинка " + ("включена" if new_val else "выключена"), show_alert=True)
    await product_view(callback)


@router.callback_query(F.data.startswith("prod_stock:"))
async def toggle_stock(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    pid = int(callback.data.split(":")[1])
    p = await get_product_by_id(pid)
    new_val = 0 if p.get("in_stock") else 1
    await update_product(pid, in_stock=new_val)
    await callback.answer("📦 " + ("В наличии" if new_val else "Нет в наличии"), show_alert=True)
    await product_view(callback)


@router.callback_query(F.data.startswith("prod_up:"))
async def move_up(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    pid = int(callback.data.split(":")[1])
    p = await get_product_by_id(pid)
    new_order = (p.get("sort_order") or 0) - 1
    await update_product(pid, sort_order=new_order)
    await callback.answer("⬆️ Перемещён вверх", show_alert=True)
    await product_view(callback)


@router.callback_query(F.data.startswith("prod_down:"))
async def move_down(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    pid = int(callback.data.split(":")[1])
    p = await get_product_by_id(pid)
    new_order = (p.get("sort_order") or 0) + 1
    await update_product(pid, sort_order=new_order)
    await callback.answer("⬇️ Перемещён вниз", show_alert=True)
    await product_view(callback)


@router.callback_query(F.data.startswith("prod_del:"))
async def product_delete(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    await delete_product(int(callback.data.split(":")[1]))
    await callback.answer("🗑 Удалено", show_alert=True)
    await product_list(callback)


# ===== СКИДКА =====

class DiscountState(StatesGroup):
    price = State()


@router.callback_query(F.data.startswith("prod_discount:"))
async def discount_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    pid = int(callback.data.split(":")[1])
    await state.update_data(edit_id=pid)
    await state.set_state(DiscountState.price)
    p = await get_product_by_id(pid)
    try:
        await callback.message.edit_text(
            f"💰 Текущая цена: <b>{p['price']}₽</b>\n\n"
            f"Введите <b>новую цену</b> со скидкой (цифры).\n"
            f"Старая цена сохранится в поле «было».\n\n"
            f"Или отправьте «-» чтобы убрать скидку.",
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer("Введите новую цену:")
    await callback.answer()


@router.message(DiscountState.price)
async def discount_save(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    pid = data["edit_id"]
    p = await get_product_by_id(pid)
    await state.clear()

    if message.text == "-":
        await update_product(pid, old_price=None)
        await message.answer("✅ Скидка убрана.", reply_markup=products_menu_kb())
        return

    if not message.text.isdigit():
        await message.answer("⚠️ Только цифры!")
        return

    new_price = int(message.text)
    await update_product(pid, old_price=p["price"], price=new_price)
    await message.answer(
        f"✅ Цена обновлена!\n\nСтарая: <s>{p['price']}₽</s>\nНовая: <b>{new_price}₽</b>",
        reply_markup=products_menu_kb(),
        parse_mode="HTML",
    )


# ===== РЕДАКТИРОВАНИЕ =====

@router.callback_query(F.data.startswith("prod_edit:"))
async def product_edit(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    pid = int(callback.data.split(":")[1])
    await state.update_data(edit_id=pid)
    await state.set_state(EditProduct.name)
    p = await get_product_by_id(pid)
    try:
        await callback.message.edit_text(
            f"✏️ <b>{p['name']}</b>\n\nВведите новое название (или «-» чтобы пропустить):",
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
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
    await message.answer("✅ Товар обновлён.", reply_markup=products_menu_kb())


# ===== КАРТИНКА =====

@router.callback_query(F.data.startswith("prod_img:"))
async def product_img_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    pid = int(callback.data.split(":")[1])
    await state.update_data(edit_id=pid)
    await state.set_state(AddProduct.image)
    try:
        await callback.message.edit_text("🖼 Отправьте картинку для товара:")
    except Exception:
        await callback.message.answer("🖼 Отправьте картинку для товара:")
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
    await message.answer("✅ Картинка обновлена.", reply_markup=products_menu_kb())


# ===== ДОБАВЛЕНИЕ ТОВАРА =====

def categories_kb():
    b = InlineKeyboardBuilder()
    b.button(text="💐 Букеты", callback_data="cat:bouquets")
    b.button(text="🎁 Коробки", callback_data="cat:boxes")
    b.button(text="🪴 Растения", callback_data="cat:plants")
    b.button(text="⬅️ Отмена", callback_data="admin_products")
    b.adjust(1)
    return b.as_markup()


@router.callback_query(F.data == "product_add")
async def product_add_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.clear()
    try:
        await callback.message.edit_text(
            "🛍 <b>Добавление товара</b>\n\nВыберите категорию:",
            reply_markup=categories_kb(),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
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
    try:
        await callback.message.edit_text("Введите <b>название</b> товара:", parse_mode="HTML")
    except Exception:
        await callback.message.answer("Введите <b>название</b> товара:", parse_mode="HTML")
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
    await message.answer("🖼 Отправьте <b>картинку</b> или напишите «-» чтобы пропустить:", parse_mode="HTML")


@router.message(AddProduct.image, F.photo)
async def add_image(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    os.makedirs("images", exist_ok=True)
    path = f"images/new_{message.from_user.id}.jpg"
    await message.bot.download(message.photo[-1], destination=path)
    pid = await add_product(
        category=data["category"], name=data["name"],
        price=data["price"], description=data["description"], image=path,
    )
    await state.clear()
    await message.answer(
        f"✅ Товар <b>{data['name']}</b> добавлен (ID {pid}).",
        reply_markup=products_menu_kb(),
        parse_mode="HTML",
    )


@router.message(AddProduct.image, F.text == "-")
async def add_no_image(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    pid = await add_product(
        category=data["category"], name=data["name"],
        price=data["price"], description=data["description"], image=None,
    )
    await state.clear()
    await message.answer(
        f"✅ Товар <b>{data['name']}</b> добавлен (ID {pid}).",
        reply_markup=products_menu_kb(),
        parse_mode="HTML",
    )


# ===== МАССОВОЕ ИЗМЕНЕНИЕ ЦЕН =====

@router.callback_query(F.data == "mass_price")
async def mass_price_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(MassPrice.percent)
    try:
        await callback.message.edit_text(
            "💰 <b>Массовое изменение цен</b>\n\n"
            "Введите процент изменения.\n\n"
            "Примеры:\n"
            "• <code>10</code> — поднять все цены на 10%\n"
            "• <code>-15</code> — опустить все цены на 15%\n"
            "• <code>0</code> — отмена",
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer("Введите процент изменения:")
    await callback.answer()


@router.message(MassPrice.percent)
async def mass_price_apply(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        percent = int(message.text)
    except ValueError:
        await message.answer("⚠️ Введите целое число (например, 10 или -15).")
        return
    await state.clear()

    if percent == 0:
        await message.answer("Отменено.", reply_markup=products_menu_kb())
        return

    await change_all_prices(percent)
    action = "повышены" if percent > 0 else "понижены"
    await message.answer(
        f"✅ Все цены {action} на <b>{abs(percent)}%</b>.",
        reply_markup=products_menu_kb(),
        parse_mode="HTML",
    )