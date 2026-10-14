from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_IDS
from data.database import add_promo, get_all_promos, delete_promo

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


class PromoAdd(StatesGroup):
    code = State()
    discount = State()
    uses = State()


def promos_menu_kb():
    b = InlineKeyboardBuilder()
    b.button(text="➕ Создать промокод", callback_data="promo_add")
    b.button(text="📋 Список промокодов", callback_data="promo_list")
    b.button(text="⬅️ Назад", callback_data="admin_back")
    b.adjust(1)
    return b.as_markup()


@router.callback_query(F.data == "admin_promos")
async def promos_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not is_admin(callback.from_user.id):
        return
    try:
        await callback.message.edit_text(
            "🎟 <b>Промокоды</b>",
            reply_markup=promos_menu_kb(),
            parse_mode="HTML",
        )
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data == "promo_add")
async def promo_add_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(PromoAdd.code)
    try:
        await callback.message.edit_text("Введите код промокода (например, FLOWER10):")
    except Exception:
        await callback.message.answer("Введите код промокода (например, FLOWER10):")
    await callback.answer()


@router.message(PromoAdd.code)
async def promo_add_code(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(code=message.text.strip().upper())
    await state.set_state(PromoAdd.discount)
    await message.answer("Введите размер скидки в % (только цифры):")


@router.message(PromoAdd.discount)
async def promo_add_discount(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if not message.text.isdigit():
        await message.answer("⚠️ Только цифры!")
        return
    await state.update_data(discount=int(message.text))
    await state.set_state(PromoAdd.uses)
    await message.answer("Сколько раз можно использовать? (цифры):")


@router.message(PromoAdd.uses)
async def promo_add_uses(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if not message.text.isdigit():
        await message.answer("⚠️ Только цифры!")
        return
    data = await state.get_data()
    await add_promo(data["code"], data["discount"], int(message.text))
    await state.clear()
    await message.answer(
        f"✅ Промокод <b>{data['code']}</b> создан!",
        reply_markup=promos_menu_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "promo_list")
async def promo_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    promos = await get_all_promos()
    b = InlineKeyboardBuilder()
    for p in promos:
        b.button(
            text=f"{p['code']} — {p['discount']}% (ост. {p['uses_left']})",
            callback_data=f"promo_del:{p['code']}"
        )
    b.button(text="⬅️ Назад", callback_data="admin_promos")
    b.adjust(1)
    text = f"🎟 <b>Промокоды ({len(promos)}):</b>\n\nНажмите, чтобы удалить."
    try:
        await callback.message.edit_text(text, reply_markup=b.as_markup(), parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("promo_del:"))
async def promo_delete(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    code = callback.data.split(":")[1]
    await delete_promo(code)
    await callback.answer("🗑 Промокод удалён", show_alert=True)
    await promo_list(callback)