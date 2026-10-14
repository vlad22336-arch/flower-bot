from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_IDS
from data.database import add_category, get_categories, delete_category

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


class CatAdd(StatesGroup):
    code = State()
    name = State()
    emoji = State()


def cat_menu_kb():
    b = InlineKeyboardBuilder()
    b.button(text="➕ Добавить категорию", callback_data="cat_add")
    b.button(text="📋 Список категорий", callback_data="cat_list")
    b.button(text="⬅️ Назад", callback_data="admin_back")
    b.adjust(1)
    return b.as_markup()


@router.callback_query(F.data == "admin_categories")
async def cat_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not is_admin(callback.from_user.id):
        return
    try:
        await callback.message.edit_text(
            "📁 <b>Категории товаров</b>",
            reply_markup=cat_menu_kb(),
            parse_mode="HTML",
        )
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data == "cat_add")
async def cat_add_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(CatAdd.code)
    try:
        await callback.message.edit_text(
            "📁 <b>Новая категория</b>\n\n"
            "Введите <b>код</b> категории (латиницей, без пробелов).\n"
            "Например: <code>roses</code> или <code>gifts</code>",
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer("Введите код категории (латиницей):")
    await callback.answer()


@router.message(CatAdd.code)
async def cat_add_code(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    code = message.text.strip().lower().replace(" ", "_")
    if not code.replace("_", "").isalnum():
        await message.answer("⚠️ Только латинские буквы, цифры и знак _. Попробуйте ещё раз:")
        return
    await state.update_data(code=code)
    await state.set_state(CatAdd.name)
    await message.answer("Введите <b>название</b> категории (как её увидят клиенты):", parse_mode="HTML")


@router.message(CatAdd.name)
async def cat_add_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(name=message.text.strip())
    await state.set_state(CatAdd.emoji)
    await message.answer(
        "Отправьте <b>эмодзи</b> для категории (например: 💐).\n"
        "Или напишите «-», чтобы пропустить.",
        parse_mode="HTML",
    )


@router.message(CatAdd.emoji)
async def cat_add_emoji(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    emoji = "" if message.text.strip() == "-" else message.text.strip()
    data = await state.get_data()
    await state.clear()

    await add_category(data["code"], data["name"], emoji)
    await message.answer(
        f"✅ Категория <b>{data['name']}</b> добавлена!",
        reply_markup=cat_menu_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "cat_list")
async def cat_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    cats = await get_categories()
    if not cats:
        # Если в базе нет категорий — покажем дефолтные
        cats = [
            {"code": "bouquets", "name": "Букеты", "emoji": "💐"},
            {"code": "boxes", "name": "Цветы в коробке", "emoji": "🎁"},
            {"code": "plants", "name": "Растения", "emoji": "🪴"},
        ]
        text = (
            "📋 <b>Категории по умолчанию:</b>\n\n"
            "💐 Букеты (<code>bouquets</code>)\n"
            "🎁 Цветы в коробке (<code>boxes</code>)\n"
            "🪴 Растения (<code>plants</code>)\n\n"
            "<i>В базе пока нет пользовательских категорий.</i>"
        )
        b = InlineKeyboardBuilder()
        b.button(text="⬅️ Назад", callback_data="admin_categories")
        b.adjust(1)
        try:
            await callback.message.edit_text(text, reply_markup=b.as_markup(), parse_mode="HTML")
        except Exception:
            pass
        await callback.answer()
        return

    b = InlineKeyboardBuilder()
    for c in cats:
        b.button(
            text=f"{c.get('emoji') or '📁'} {c['name']} — {c['code']}",
            callback_data=f"cat_del:{c['code']}"
        )
    b.button(text="⬅️ Назад", callback_data="admin_categories")
    b.adjust(1)
    text = f"📋 <b>Категории ({len(cats)}):</b>\n\nНажмите, чтобы удалить."
    try:
        await callback.message.edit_text(text, reply_markup=b.as_markup(), parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("cat_del:"))
async def cat_delete(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    code = callback.data.split(":")[1]
    await delete_category(code)
    await callback.answer("🗑 Категория удалена", show_alert=True)
    await cat_list(callback)