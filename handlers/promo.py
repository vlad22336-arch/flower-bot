from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from data.database import get_promo, use_promo
from keyboards.inline import confirm_order_with_promo_kb

router = Router()


class PromoState(StatesGroup):
    waiting_code = State()


@router.callback_query(F.data == "enter_promo")
async def enter_promo(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PromoState.waiting_code)
    await callback.message.edit_text(
        "🎟 <b>Введите промокод</b>\n\n"
        "Например: <code>FLOWER10</code>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(PromoState.waiting_code)
async def apply_promo(message: Message, state: FSMContext):
    from handlers.cart import user_promos

    code = message.text.strip().upper()
    promo = await get_promo(code)
    await state.clear()

    if not promo:
        await message.answer(
            "❌ Промокод не найден или неактивен.",
            reply_markup=confirm_order_with_promo_kb(),
        )
        return

    user_promos[message.from_user.id] = (code, promo["discount"])
    await use_promo(code)

    await message.answer(
        f"✅ Промокод <b>{code}</b> применён!\n\n"
        f"Скидка: <b>{promo['discount']}%</b>\n\n"
        "Нажмите «Подтвердить заказ», чтобы завершить оформление.",
        reply_markup=confirm_order_with_promo_kb(),
        parse_mode="HTML",
    )