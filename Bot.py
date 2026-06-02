import os
import sys
import asyncio
import subprocess
import zipfile
import shutil
from pathlib import Path
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

# ==================== КОНФИГ ====================
BOT_TOKEN = "5001628950:AAHKe0vlHl2fmQ7p2jLCUo97Mr3yBlzsctg/test"
PROCESS_LIMIT = 2  # лимит процессов на пользователя
FILES_DIR = Path("user_files")
FILES_DIR.mkdir(exist_ok=True)

# Хранилище процессов: {user_id: {filename: process}}
user_processes: dict[int, dict[str, subprocess.Popen]] = {}
# Хранилище логов: {user_id: {filename: [lines]}}
user_logs: dict[int, dict[str, list]] = {}

# ==================== КЛАВИАТУРА ====================
def main_keyboard():
    return ReplyKeyboardMarkup([
        ["📁 Мои файлы", "📤 Загрузить файл"],
        ["▶️ Запустить", "⏹ Остановить", "🔄 Перезапустить"],
        ["✏️ Переименовать", "🗑 Удалить", "📋 Логи"],
        ["📦 Скачать архив", "📚 Библиотеки"],
        ["👤 Профиль", "🆘 Тех.Поддержка"],
    ], resize_keyboard=True)

# ==================== УТИЛИТЫ ====================
def get_user_dir(user_id: int) -> Path:
    d = FILES_DIR / str(user_id)
    d.mkdir(exist_ok=True)
    return d

def get_user_files(user_id: int) -> list[str]:
    return [f.name for f in get_user_dir(user_id).glob("*.py")]

def get_process_count(user_id: int) -> int:
    procs = user_processes.get(user_id, {})
    return sum(1 for p in procs.values() if p.poll() is None)

def add_log(user_id: int, filename: str, line: str):
    user_logs.setdefault(user_id, {}).setdefault(filename, [])
    logs = user_logs[user_id][filename]
    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {line}")
    if len(logs) > 100:
        logs.pop(0)

# ==================== КОМАНДЫ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"☁️ *Добро пожаловать в HostlyCloud!*\n\n"
        f"Бесплатный хостинг для ваших ботов и скриптов.\n\n"
        f"📦 *Возможности:*\n"
        f"• Загрузка Python файлов\n"
        f"• Запуск/остановка/перезапуск процессов\n"
        f"• Просмотр логов в реальном времени\n"
        f"• Установка библиотек через pip\n"
        f"• Скачивание архива всех файлов\n\n"
        f"⚡ Ваш лимит: *{PROCESS_LIMIT} процесса*\n\n"
        f"Используйте кнопки меню для управления."
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_keyboard())

# ==================== ФАЙЛЫ ====================
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    doc = update.message.document

    if not doc.file_name.endswith(".py"):
        await update.message.reply_text("❌ Только .py файлы!")
        return

    user_dir = get_user_dir(user_id)
    file_path = user_dir / doc.file_name

    tg_file = await doc.get_file()
    await tg_file.download_to_drive(file_path)

    await update.message.reply_text(
        f"✅ Файл *{doc.file_name}* загружен!\n\nНажми ▶️ Запустить чтобы запустить.",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

async def my_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    files = get_user_files(user_id)
    procs = user_processes.get(user_id, {})

    if not files:
        await update.message.reply_text("📁 У вас нет файлов.\n\nОтправьте .py файл чтобы загрузить.")
        return

    text = "📁 *Ваши файлы:*\n\n"
    for f in files:
        proc = procs.get(f)
        if proc and proc.poll() is None:
            status = "🟢 Запущен"
        else:
            status = "🔴 Остановлен"
        text += f"• `{f}` — {status}\n"

    await update.message.reply_text(text, parse_mode="Markdown")

async def download_archive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_dir = get_user_dir(user_id)
    files = get_user_files(user_id)

    if not files:
        await update.message.reply_text("❌ Нет файлов для архивации.")
        return

    zip_path = user_dir / "archive.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for f in files:
            zf.write(user_dir / f, f)

    await update.message.reply_document(
        document=open(zip_path, "rb"),
        filename="my_scripts.zip",
        caption="📦 Ваш архив готов!"
    )

# ==================== ПРОЦЕССЫ ====================
async def run_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    files = get_user_files(user_id)

    if not files:
        await update.message.reply_text("❌ Нет файлов. Сначала загрузите .py файл.")
        return

    if get_process_count(user_id) >= PROCESS_LIMIT:
        await update.message.reply_text(f"⚡ Лимит процессов: {PROCESS_LIMIT}. Остановите один из запущенных.")
        return

    buttons = [[InlineKeyboardButton(f"▶️ {f}", callback_data=f"run:{f}")] for f in files]
    await update.message.reply_text(
        "Выберите файл для запуска:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def stop_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    procs = user_processes.get(user_id, {})
    running = [f for f, p in procs.items() if p.poll() is None]

    if not running:
        await update.message.reply_text("❌ Нет запущенных процессов.")
        return

    buttons = [[InlineKeyboardButton(f"⏹ {f}", callback_data=f"stop:{f}")] for f in running]
    await update.message.reply_text(
        "Выберите процесс для остановки:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def restart_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    procs = user_processes.get(user_id, {})
    running = [f for f, p in procs.items() if p.poll() is None]

    if not running:
        await update.message.reply_text("❌ Нет запущенных процессов.")
        return

    buttons = [[InlineKeyboardButton(f"🔄 {f}", callback_data=f"restart:{f}")] for f in running]
    await update.message.reply_text(
        "Выберите процесс для перезапуска:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def show_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    files = get_user_files(user_id)

    if not files:
        await update.message.reply_text("❌ Нет файлов.")
        return

    buttons = [[InlineKeyboardButton(f"📋 {f}", callback_data=f"logs:{f}")] for f in files]
    await update.message.reply_text(
        "Выберите файл для просмотра логов:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ==================== УДАЛИТЬ / ПЕРЕИМЕНОВАТЬ ====================
async def delete_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    files = get_user_files(user_id)

    if not files:
        await update.message.reply_text("❌ Нет файлов.")
        return

    buttons = [[InlineKeyboardButton(f"🗑 {f}", callback_data=f"delete:{f}")] for f in files]
    await update.message.reply_text(
        "Выберите файл для удаления:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def rename_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    files = get_user_files(user_id)

    if not files:
        await update.message.reply_text("❌ Нет файлов.")
        return

    buttons = [[InlineKeyboardButton(f"✏️ {f}", callback_data=f"rename:{f}")] for f in files]
    await update.message.reply_text(
        "Выберите файл для переименования:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ==================== БИБЛИОТЕКИ ====================
async def libraries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 *Установка библиотек*\n\n"
        "Отправьте команду в формате:\n"
        "`/pip библиотека`\n\n"
        "Примеры:\n"
        "`/pip requests`\n"
        "`/pip aiogram`\n"
        "`/pip aiohttp`",
        parse_mode="Markdown"
    )

async def pip_install(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Укажите библиотеку: `/pip requests`", parse_mode="Markdown")
        return

    lib = context.args[0].strip()
    msg = await update.message.reply_text(f"⏳ Устанавливаю `{lib}`...", parse_mode="Markdown")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", lib, "--quiet"],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            await msg.edit_text(f"✅ Библиотека `{lib}` установлена!", parse_mode="Markdown")
        else:
            await msg.edit_text(f"❌ Ошибка установки `{lib}`:\n```{result.stderr[:300]}```", parse_mode="Markdown")
    except subprocess.TimeoutExpired:
        await msg.edit_text(f"❌ Таймаут установки `{lib}`.")
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка: {e}")

# ==================== ПРОФИЛЬ ====================
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    files = get_user_files(user_id)
    running = get_process_count(user_id)

    text = (
        f"👤 *Профиль*\n\n"
        f"🆔 ID: `{user_id}`\n"
        f"👤 Имя: {user.first_name}\n"
        f"📁 Файлов: {len(files)}\n"
        f"⚙️ Процессов: {running}/{PROCESS_LIMIT}\n"
        f"💎 Тариф: Бесплатный\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 *Тех.Поддержка*\n\n"
        "По всем вопросам пишите: @ваш_юзернейм",
        parse_mode="Markdown"
    )

# ==================== CALLBACK ОБРАБОТЧИК ====================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    action, filename = data.split(":", 1)
    user_dir = get_user_dir(user_id)

    # --- ЗАПУСК ---
    if action == "run":
        if get_process_count(user_id) >= PROCESS_LIMIT:
            await query.edit_message_text(f"⚡ Лимит процессов: {PROCESS_LIMIT}!")
            return

        file_path = user_dir / filename
        if not file_path.exists():
            await query.edit_message_text("❌ Файл не найден.")
            return

        # Останавливаем если уже запущен
        procs = user_processes.setdefault(user_id, {})
        if filename in procs and procs[filename].poll() is None:
            procs[filename].kill()

        try:
            proc = subprocess.Popen(
                [sys.executable, str(file_path)],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1
            )
            procs[filename] = proc
            add_log(user_id, filename, f"▶️ Процесс запущен (PID: {proc.pid})")
            await query.edit_message_text(f"✅ *{filename}* запущен!\n\nPID: `{proc.pid}`", parse_mode="Markdown")

            # Читаем логи асинхронно
            asyncio.create_task(read_logs(user_id, filename, proc))
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка запуска: {e}")

    # --- СТОП ---
    elif action == "stop":
        procs = user_processes.get(user_id, {})
        proc = procs.get(filename)
        if proc and proc.poll() is None:
            proc.kill()
            add_log(user_id, filename, "⏹ Процесс остановлен")
            await query.edit_message_text(f"⏹ *{filename}* остановлен.", parse_mode="Markdown")
        else:
            await query.edit_message_text("❌ Процесс уже не запущен.")

    # --- ПЕРЕЗАПУСК ---
    elif action == "restart":
        procs = user_processes.setdefault(user_id, {})
        proc = procs.get(filename)
        if proc and proc.poll() is None:
            proc.kill()

        file_path = user_dir / filename
        try:
            new_proc = subprocess.Popen(
                [sys.executable, str(file_path)],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1
            )
            procs[filename] = new_proc
            add_log(user_id, filename, f"🔄 Перезапущен (PID: {new_proc.pid})")
            await query.edit_message_text(f"🔄 *{filename}* перезапущен!\n\nPID: `{new_proc.pid}`", parse_mode="Markdown")
            asyncio.create_task(read_logs(user_id, filename, new_proc))
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка перезапуска: {e}")

    # --- ЛОГИ ---
    elif action == "logs":
        logs = user_logs.get(user_id, {}).get(filename, [])
        if not logs:
            await query.edit_message_text(f"📋 Логи *{filename}*:\n\n_Логов пока нет_", parse_mode="Markdown")
        else:
            last_logs = logs[-20:]
            text = f"📋 Логи *{filename}*:\n\n```\n" + "\n".join(last_logs) + "\n```"
            await query.edit_message_text(text[:4000], parse_mode="Markdown")

    # --- УДАЛЕНИЕ ---
    elif action == "delete":
        # Останавливаем если запущен
        procs = user_processes.get(user_id, {})
        proc = procs.get(filename)
        if proc and proc.poll() is None:
            proc.kill()

        file_path = user_dir / filename
        if file_path.exists():
            file_path.unlink()
            await query.edit_message_text(f"🗑 *{filename}* удалён.", parse_mode="Markdown")
        else:
            await query.edit_message_text("❌ Файл не найден.")

    # --- ПЕРЕИМЕНОВАНИЕ ---
    elif action == "rename":
        context.user_data["rename_file"] = filename
        await query.edit_message_text(
            f"✏️ Введите новое имя для *{filename}*\n\n(без расширения, только название)",
            parse_mode="Markdown"
        )

async def read_logs(user_id: int, filename: str, proc: subprocess.Popen):
    """Асинхронно читает вывод процесса в логи"""
    try:
        loop = asyncio.get_event_loop()
        while True:
            line = await loop.run_in_executor(None, proc.stdout.readline)
            if not line:
                break
            add_log(user_id, filename, line.rstrip())
        add_log(user_id, filename, "🔴 Процесс завершён")
    except Exception:
        pass

# ==================== ТЕКСТОВЫЕ СООБЩЕНИЯ ====================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    # Переименование
    if "rename_file" in context.user_data:
        old_name = context.user_data.pop("rename_file")
        new_name = text.strip()
        if not new_name.endswith(".py"):
            new_name += ".py"

        user_dir = get_user_dir(user_id)
        old_path = user_dir / old_name
        new_path = user_dir / new_name

        if old_path.exists():
            old_path.rename(new_path)
            await update.message.reply_text(
                f"✅ Переименовано: *{old_name}* → *{new_name}*",
                parse_mode="Markdown", reply_markup=main_keyboard()
            )
        else:
            await update.message.reply_text("❌ Файл не найден.", reply_markup=main_keyboard())
        return

    # Кнопки меню
    handlers = {
        "📁 Мои файлы": my_files,
        "📤 Загрузить файл": lambda u, c: u.message.reply_text("📤 Просто отправьте .py файл в чат!"),
        "▶️ Запустить": run_process,
        "⏹ Остановить": stop_process,
        "🔄 Перезапустить": restart_process,
        "✏️ Переименовать": rename_file,
        "🗑 Удалить": delete_file,
        "📋 Логи": show_logs,
        "📦 Скачать архив": download_archive,
        "📚 Библиотеки": libraries,
        "👤 Профиль": profile,
        "🆘 Тех.Поддержка": support,
    }

    handler = handlers.get(text)
    if handler:
        await handler(update, context)
    else:
        await update.message.reply_text("Используйте кнопки меню 👇", reply_markup=main_keyboard())

# ==================== MAIN ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pip", pip_install))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(callback_handler))

    print("✅ HostlyCloud Bot запущен!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
