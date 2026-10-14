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
    get_orders, search_clients, update_client_tags,
)

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


class SearchClient(StatesGroup):
    query = State()


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
        if c.get("tags"):
            flags += f" [{c['tags']}]"
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
        if c.get("tags"):
            flags += f" [{c['tags']}]"
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
        "User ID", "Имя", "Username", "Теги", "День рождения",
        "Заметка", "В ЧС", "Последний визит"
    ])
    for c in clients:
        writer.writerow([
            c["user_id"],
            c["full_name"],
            c.get("username") or "",
            c.get("tags") or "",
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
    if c.get("tags"):
        flags.append(f"🏷 {c['tags']}")
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
    b.button(text="🏷 Теги", callback_data=f"client_tags:{user_id}")
    b.button(text="📝 Заметка", callback_data=f"client_note:{user_id}")
    b.button(text="🎂 День рождения", callback_data=f"client_bd:{user_id}")
    if c.get("is_blacklisted"):
        b.button(text="✅ Убрать из ЧС", callback_data=f"client_unblock:{user_id}")
    else:
        b.button(text="🚫 В чёрный список", callback_data=f"client_block:{user_id}")
    b.button(text="📦 Заказы клиента", callback_data=f"client_orders:{user_id}")
    b.button(text="⬅️ К списку", callback_data="clients_list")
    b.adjust(2, 2, 2, 1)

    try:
        await callback.message.edit_text(text, reply_markup=b.as_markup(), parse_mode="HTML")
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=b.as_markup(), parse_mode="HTML")
    await callback.answer()