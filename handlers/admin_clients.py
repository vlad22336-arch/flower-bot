from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import csv
import io

from config import ADMIN_IDS
from data.database import (
    get_clients, get_client, update_client,
    get_orders, search_clients,
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


class SearchClient(StatesGroup):
    query = State()


# ===== МЕНЮ КЛИЕНТОВ =====

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


@router.callback_query(F.data == "admin_clients")
async def clients_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not is_admin(callback.from_user.id):
        return
    try:
        await callback.message.edit_text(
            "👥 <b>Управление клиентами</b>",
            reply_markup=clients_menu_kb(),
            parse_mode="HTML",
        )
    except Exception:
        pass
    await callback.answer()


# ===== СПИСОК КЛИЕНТОВ =====

@router.callback_query(F.data == "clients_list")
async def clients_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    clients = await get_clients()
    if not clients:
        try:
            await callback.message.edit_text("📭 Клиентов пока нет.", reply_markup=clients_menu_kb())
        except Exception:
            pass
        await callback.answer()
        return

    b = InlineKeyboardBuilder()
    for c in clients[:30]:
        flags = ""
        if c.get("is_blacklisted"):
            flags += " 🚫"
        if c.get("birthday"):
            flags += " 🎂"
        b.button(
            text=f"{c['full_name']}{flags}",
            callback_data=f"client_view:{c['user_id']}"
        )
    b.button(text="⬅️ Назад", callback_data="admin_clients")
    b.adjust(1)
    try:
        await callback.message.edit_text(
            f"👥 <b>Клиенты ({len(clients)}):</b>\n\nНажмите для просмотра.",
            reply_markup=b.as_markup(),
            parse_mode="HTML",
        )
    except Exception:
        pass
    await callback.answer()


# ===== ПОИСК КЛИЕНТА =====

@router.callback_query(F.data == "client_search")
async def client_search_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(SearchClient.query)
    try:
        await callback.message.edit_text(
            "🔍 <b>Поиск клиента</b>\n\n"
            "Введите имя, @username или ID клиента.\n\n"
            "Например: <code>Иван</code> или <code>@ivan</code> или <code>123456789</code>",
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer("Введите имя, @username или ID клиента:")
    await callback.answer()


@router.message(SearchClient.query)
async def client_search_result(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    query = message.text.strip().lstrip("@")
    await state.clear()

    results = await search_clients(query)

    if not results:
        await message.answer(
            "❌ Ничего не найдено.\n\nПопробуйте другой запрос.",
            reply_markup=clients_menu_kb(),
        )
        return

    b = InlineKeyboardBuilder()
    for c in results:
        flags = ""
        if c.get("is_blacklisted"):
            flags += " 🚫"
        if c.get("birthday"):
            flags += " 🎂"
        b.button(
            text=f"{c['full_name']} (@{c['username'] or '—'}){flags}",
            callback_data=f"client_view:{c['user_id']}"
        )
    b.button(text="🔍 Новый поиск", callback_data="client_search")
    b.button(text="⬅️ К меню клиентов", callback_data="admin_clients")
    b.adjust(1)

    await message.answer(
        f"🔍 <b>Найдено: {len(results)}</b>\n\nВыберите клиента:",
        reply_markup=b.as_markup(),
        parse_mode="HTML",
    )


# ===== ЭКСПОРТ КЛИЕНТОВ В CSV =====

@router.callback_query(F.data == "clients_export")
async def clients_export(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    clients = await get_clients()
    if not clients:
        await callback.answer("Клиентов нет", show_alert=True)
        return

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow([
        "User ID", "Имя", "Username", "День рождения",
        "Заметка", "В ЧС", "Последний визит"
    ])
    for c in clients:
        writer.writerow([
            c["user_id"],
            c["full_name"],
            c.get("username") or "",
            c.get("birthday") or "",
            (c.get("note") or "").replace("\n", " "),
            "Да" if c.get("is_blacklisted") else "Нет",
            c.get("last_seen") or "",
        ])

    csv_bytes = output.getvalue().encode("utf-8-sig")
    file = BufferedInputFile(csv_bytes, filename="clients.csv")
    await callback.message.answer_document(
        file,
        caption=f"📥 Экспорт клиентов\n\nВсего: <b>{len(clients)}</b>",
        parse_mode="HTML",
    )
    await callback.answer("Файл отправлен!")


# ===== КАРТОЧКА КЛИЕНТА =====

@router.callback_query(F.data.startswith("client_view:"))
async def client_view(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    user_id = int(callback.data.split(":")[1])
    c = await get_client(user_id)
    if not c:
        await callback.answer("Клиент не найден", show_alert=True)
        return

    all_orders = await get_orders(1000)
    client_orders = [o for o in all_orders if o["user_id"] == user_id]
    total_spent = sum(o["total"] for o in client_orders)
    orders_count = len(client_orders)

    flags = []
    if c.get("is_blacklisted"):
        flags.append("🚫 В чёрном списке")
    if c.get("birthday"):
        flags.append(f"🎂 {c['birthday']}")
    flags_text = "\n".join(flags) if flags else "—"

    note = c.get("note") or "—"

    text = (
        f"👤 <b>{c['full_name']}</b>\n\n"
        f"🆔 <code>{c['user_id']}</code>\n"
        f"🔗 @{c['username'] or '—'}\n"
        f"📅 Последний визит: {c.get('last_seen', '—')}\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"• Заказов: <b>{orders_count}</b>\n"
        f"• Сумма покупок: <b>{total_spent}₽</b>\n\n"
        f"🏷 <b>Метки:</b>\n{flags_text}\n\n"
        f"📝 <b>Заметка:</b>\n<i>{note}</i>"
    )

    b = InlineKeyboardBuilder()
    b.button(text="📝 Заметка", callback_data=f"client_note:{user_id}")
    b.button(text="🎂 День рождения", callback_data=f"client_bd:{user_id}")
    if c.get("is_blacklisted"):
        b.button(text="✅ Убрать из ЧС", callback_data=f"client_unblock:{user_id}")
    else:
        b.button(text="🚫 В чёрный список", callback_data=f"client_block:{user_id}")
    b.button(text="📦 Заказы клиента", callback_data=f"client_orders:{user_id}")
    b.button(text="⬅️ К списку", callback_data="clients_list")
    b.adjust(2, 2, 1, 1)

    try:
        await callback.message.edit_text(text, reply_markup=b.as_markup(), parse_mode="HTML")
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=b.as_markup(), parse_mode="HTML")
    await callback.answer()


# ===== ЗАМЕТКА =====

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


# ===== ДЕНЬ РОЖДЕНИЯ =====

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


# ===== ЧЁРНЫЙ СПИСОК =====

@router.callback_query(F.data.startswith("client_block:"))
async def client_block(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    user_id = int(callback.data.split(":")[1])
    await update_client(user_id, is_blacklisted=1)
    await callback.answer("🚫 Клиент в чёрном списке", show_alert=True)
    await client_view(callback)


@router.callback_query(F.data.startswith("client_unblock:"))
async def client_unblock(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    user_id = int(callback.data.split(":")[1])
    await update_client(user_id, is_blacklisted=0)
    await callback.answer("✅ Клиент убран из ЧС", show_alert=True)
    await client_view(callback)


# ===== ЗАКАЗЫ КЛИЕНТА =====

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


# ===== ДНИ РОЖДЕНИЯ =====

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
                "Пока ни у кого не сохранён день рождения.\n"
                "Откройте карточку клиента и укажите дату.",
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

    text = f"🎂 <b>Дни рождения клиентов ({len(bd_clients)}):</b>\n\n"
    for c in bd_clients[:30]:
        text += f"• <b>{c['birthday']}</b> — {c['full_name']} (@{c['username'] or '—'})\n"

    b = InlineKeyboardBuilder()
    b.button(text="⬅️ Назад", callback_data="admin_clients")
    b.adjust(1)
    try:
        await callback.message.edit_text(text, reply_markup=b.as_markup(), parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()


# ===== РАССЫЛКА =====

@router.callback_query(F.data == "broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(Broadcast.message)
    try:
        await callback.message.edit_text(
            "📢 <b>Рассылка</b>\n\n"
            "Напишите сообщение, которое получат все клиенты (кроме ЧС).",
            parse_mode="HTML",
        )
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
        f"📢 <b>Готово!</b>\n\n"
        f"✅ Отправлено: {sent}\n"
        f"❌ Ошибок: {failed}\n"
        f"🚫 Пропущено (ЧС): {skipped}",
        reply_markup=clients_menu_kb(),
        parse_mode="HTML",
    )