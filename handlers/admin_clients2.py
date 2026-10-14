from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_IDS
from data.database import (
    get_clients, get_client, update_client,
    get_orders, update_client_tags,
)

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


class ClientNote(StatesGroup):
    text = State()


class ClientBirthday(StatesGroup):
    date = State()


class Broadcast(StatesGroup):
    message = State()


def clients_menu_kb():
    b = InlineKeyboardBuilder()
    b.button(text="👥 Список клиентов", callback_data="clients_list")
    b.button(text="🔍 Найти клиента", callback_data="client_search")
    b.button(text="🎂 Дни рождения", callback_data="clients_birthdays")
    b.button(text="📥 Экспорт в CSV", callback_data="clients_export")
    b.button(text="📢 Сделать рассылку", callback_data="broadcast")
    b.button(text="⬅️ Назад", callback_data="admin_back")
    b.adjust(1)
    return b.as_markup()


def tags_kb(user_id: int, current_tags: str):
    tags_list = ["VIP", "Постоянный", "Новый", "Проблемный", "Оптовый"]
    current = set((current_tags or "").split(",")) if current_tags else set()
    current.discard("")

    b = InlineKeyboardBuilder()
    for tag in tags_list:
        mark = "✅ " if tag in current else ""
        b.button(text=f"{mark}{tag}", callback_data=f"tag_toggle:{user_id}:{tag}")
    b.button(text="❌ Очистить все", callback_data=f"tag_clear:{user_id}")
    b.button(text="⬅️ Назад", callback_data=f"client_view:{user_id}")
    b.adjust(2, 2, 1, 1, 1)
    return b.as_markup()


@router.callback_query(F.data.startswith("client_tags:"))
async def client_tags(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    user_id = int(callback.data.split(":")[1])
    c = await get_client(user_id)
    if not c:
        await callback.answer("Клиент не найден", show_alert=True)
        return
    try:
        await callback.message.edit_text(
            f"🏷 <b>Теги клиента {c['full_name']}</b>\n\n"
            "Нажмите, чтобы включить/выключить тег:",
            reply_markup=tags_kb(user_id, c.get("tags") or ""),
            parse_mode="HTML",
        )
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("tag_toggle:"))
async def tag_toggle(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    parts = callback.data.split(":")
    user_id = int(parts[1])
    tag = parts[2]

    c = await get_client(user_id)
    current = set((c.get("tags") or "").split(",")) if c.get("tags") else set()
    current.discard("")

    if tag in current:
        current.remove(tag)
    else:
        current.add(tag)

    new_tags = ",".join(sorted(current))
    await update_client_tags(user_id, new_tags)
    await client_tags(callback)


@router.callback_query(F.data.startswith("tag_clear:"))
async def tag_clear(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    user_id = int(callback.data.split(":")[1])
    await update_client_tags(user_id, "")
    await callback.answer("Теги очищены", show_alert=True)
    await client_tags(callback)


@router.callback_query(F.data.startswith("client_note:"))
async def client_note_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    user_id = int(callback.data.split(":")[1])
    await state.update_data(user_id=user_id)
    await state.set_state(ClientNote.text)
    c = await get_client(user_id)
    current = c.get("note") or "—"
    try:
        await callback.message.edit_text(
            f"📝 <b>Заметка о клиенте</b>\n\n"
            f"Текущая: <i>{current}</i>\n\n"
            f"Введите новую заметку или «-» чтобы удалить:",
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer("Введите заметку:")
    await callback.answer()


@router.message(ClientNote.text)
async def client_note_save(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    user_id = data["user_id"]
    note = None if message.text.strip() == "-" else message.text.strip()
    await update_client(user_id, note=note)
    await state.clear()
    await message.answer("✅ Заметка сохранена.", reply_markup=clients_menu_kb())


@router.callback_query(F.data.startswith("client_bd:"))
async def client_bd_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    user_id = int(callback.data.split(":")[1])
    await state.update_data(user_id=user_id)
    await state.set_state(ClientBirthday.date)
    c = await get_client(user_id)
    current = c.get("birthday") or "—"
    try:
        await callback.message.edit_text(
            f"🎂 <b>День рождения клиента</b>\n\n"
            f"Текущая дата: <b>{current}</b>\n\n"
            f"Введите дату в формате <code>ДД.ММ</code> (например, <code>15.03</code>)\n"
            f"Или «-» чтобы удалить:",
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer("Введите дату в формате ДД.ММ:")
    await callback.answer()


@router.message(ClientBirthday.date)
async def client_bd_save(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    user_id = data["user_id"]
    text = message.text.strip()

    if text == "-":
        await update_client(user_id, birthday=None)
        await state.clear()
        await message.answer("✅ Дата удалена.", reply_markup=clients_menu_kb())
        return

    parts = text.split(".")
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        await message.answer("⚠️ Неверный формат. Введите как <code>15.03</code>", parse_mode="HTML")
        return
    day, month = int(parts[0]), int(parts[1])
    if not (1 <= day <= 31 and 1 <= month <= 12):
        await message.answer("⚠️ Некорректная дата. Проверьте день и месяц.")
        return

    await update_client(user_id, birthday=text)
    await state.clear()
    await message.answer(f"✅ Дата сохранена: <b>{text}</b>", reply_markup=clients_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data.startswith("client_block:"))
async def client_block(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    user_id = int(callback.data.split(":")[1])
    await update_client(user_id, is_blacklisted=1)
    await callback.answer("🚫 Клиент в чёрном списке", show_alert=True)


@router.callback_query(F.data.startswith("client_unblock:"))
async def client_unblock(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    user_id = int(callback.data.split(":")[1])
    await update_client(user_id, is_blacklisted=0)
    await callback.answer("✅ Клиент убран из ЧС", show_alert=True)


@router.callback_query(F.data.startswith("client_orders:"))
async def client_orders(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    user_id = int(callback.data.split(":")[1])
    all_orders = await get_orders(1000)
    client_orders_list = [o for o in all_orders if o["user_id"] == user_id]

    if not client_orders_list:
        try:
            await callback.message.edit_text(
                "📭 У клиента ещё нет заказов.",
                reply_markup=clients_menu_kb(),
            )
        except Exception:
            pass
        await callback.answer()
        return

    text = f"📦 <b>Заказы клиента ({len(client_orders_list)}):</b>\n\n"
    for o in client_orders_list[:10]:
        text += f"• #{o['id']} — {o['total']}₽ — {o['status']} — {o['created_at'][:10]}\n"

    b = InlineKeyboardBuilder()
    b.button(text="⬅️ Назад", callback_data=f"client_view:{user_id}")
    b.adjust(1)
    try:
        await callback.message.edit_text(text, reply_markup=b.as_markup(), parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data == "clients_birthdays")
async def clients_birthdays(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    clients = await get_clients()
    bd_clients = [c for c in clients if c.get("birthday")]

    if not bd_clients:
        try:
            await callback.message.edit_text(
                "🎂 <b>Дни рождения</b>\n\n"
                "Пока ни у кого не сохранён день рождения.",
                reply_markup=clients_menu_kb(),
                parse_mode="HTML",
            )
        except Exception:
            pass
        await callback.answer()
        return

    def sort_key(c):
        parts = c["birthday"].split(".")
        return (int(parts[1]), int(parts[0]))
    bd_clients.sort(key=sort_key)

    text = f"🎂 <b>Дни рождения ({len(bd_clients)}):</b>\n\n"
    for c in bd_clients[:30]:
        text += f"• <b>{c['birthday']}</b> — {c['full_name']}\n"

    b = InlineKeyboardBuilder()
    b.button(text="⬅️ Назад", callback_data="admin_clients")
    b.adjust(1)
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
        await callback.message.edit_text("📢 Напишите сообщение для рассылки:")
    except Exception:
        await callback.message.answer("Напишите сообщение для рассылки:")
    await callback.answer()


@router.message(Broadcast.message)
async def broadcast_send(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    clients = await get_clients()
    sent = failed = skipped = 0
    for c in clients:
        if c.get("is_blacklisted"):
            skipped += 1
            continue
        try:
            await message.bot.send_message(c["user_id"], message.text)
            sent += 1
        except Exception:
            failed += 1
    await state.clear()
    await message.answer(
        f"📢 Готово!\n\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}\n🚫 Пропущено (ЧС): {skipped}",
        reply_markup=clients_menu_kb(),
    )