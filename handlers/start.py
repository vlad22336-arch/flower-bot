from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from keyboards.inline import main_menu_kb
from keyboards.reply import main_reply_kb
from config import DEMO_MODE

router = Router()

WELCOME_TEXT = (
    "🌷 <b>Цветочная мастерская</b>\n\n"
    "{demo}"
    "Свежие цветы и авторские букеты.\n"
    "Собираем в день заказа.\n\n"
    "Соберите заказ прямо здесь — заявка уйдёт флористу сразу."
)

DEMO_NOTICE = (
    "<i>Демонстрационный бот. Заказы не выполняются.</i>\n\n"
)


@router.message(CommandStart())
async def cmd_start(message: Message):
    demo = DEMO_NOTICE if DEMO_MODE else ""
    await message.answer(
        WELCOME_TEXT.format(demo=demo),
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )
    # Также показываем reply-клавиатуру
    await message.answer(
        "Используйте кнопки ниже или меню выше 👇",
        reply_markup=main_reply_kb(),
    )


@router.message(Command("menu"))
@router.message(F.text == "🏠 Меню")
async def cmd_menu(message: Message):
    demo = DEMO_NOTICE if DEMO_MODE else ""
    await message.answer(
        WELCOME_TEXT.format(demo=demo),
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery):
    demo = DEMO_NOTICE if DEMO_MODE else ""
    text = WELCOME_TEXT.format(demo=demo)
    try:
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(
                text,
                reply_markup=main_menu_kb(),
                parse_mode="HTML",
            )
        else:
            await callback.message.edit_text(
                text,
                reply_markup=main_menu_kb(),
                parse_mode="HTML",
            )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=main_menu_kb(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()
