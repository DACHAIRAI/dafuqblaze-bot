import asyncio
import json
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext

# ============ НАСТРОЙКИ ============
BOT_TOKEN = os.getenv("BOT_TOKEN", "8014541670:AAHje0MwNKwoIxjtWsqsbLJGUKXgMgDnWxY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7837849241"))

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# ============ БАЗА ДАННЫХ ============
DB_FILE = "users.json"

def load_db():
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

db = load_db()

# ============ СОСТОЯНИЯ ДЛЯ FSM ============
class FeedbackState(StatesGroup):
    waiting_for_message = State()

class ReplyState(StatesGroup):
    waiting_for_reply = State()
    waiting_for_message = State()

# ============ ХРАНЕНИЕ ПОСЛЕДНИХ ОТПРАВИТЕЛЕЙ ============
last_senders = {}  # {admin_id: user_id} - чтобы модератор мог ответить

# ============ /start ============
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    args = message.text.split()
    user_id = str(message.from_user.id)
    
    if user_id not in db:
        db[user_id] = {
            "username": message.from_user.username or message.from_user.full_name,
            "full_name": message.from_user.full_name,
            "requests": 0,
            "paid": False,
            "joined": datetime.now().isoformat()
        }
        save_db(db)
    
    # Проверка оплаты
    if len(args) > 1 and args[1].startswith("pay_genius_"):
        db[user_id]["paid"] = True
        db[user_id]["paid_at"] = datetime.now().isoformat()
        save_db(db)
        
        await message.answer(
            "✅ <b>Гений активирован!</b>\n\n"
            "💵 Оплата $5.99 получена!\n"
            "🧠 Максимальный интеллект доступен!\n\n"
            "🔄 Возвращайся на сайт и нажми <b>Проверить оплату</b>"
        )
        
        await bot.send_message(
            ADMIN_ID,
            f"💰 <b>НОВАЯ ОПЛАТА!</b>\n\n"
            f"👤 {message.from_user.full_name}\n"
            f"📱 @{message.from_user.username or 'нет'}\n"
            f"🆔 {user_id}\n"
            f"💵 $5.99\n"
            f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        return
    
    paid_status = "🧠 Гений" if db[user_id]["paid"] else "💡 Обычный"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 Купить Гений ($5.99)", callback_data="buy_genius")],
        [InlineKeyboardButton(text="💬 Написать модератору", callback_data="feedback")],
        [InlineKeyboardButton(text="📊 Статус", callback_data="status")]
    ])
    
    await message.answer(
        f"🤖 <b>DafuqBlaze Codex Bot</b>\n\n"
        f"👤 <b>{message.from_user.full_name}</b>\n"
        f"📊 Запросов: {db[user_id]['requests']}\n"
        f"⭐ Статус: {paid_status}\n\n"
        f"<b>Команды:</b>\n"
        f"💎 /pay — купить Гений\n"
        f"💬 /feedback — написать модератору\n"
        f"📊 /status — статус\n"
        f"❓ /help — помощь",
        reply_markup=kb
    )

# ============ /pay ============
@dp.message(Command("pay"))
async def cmd_pay(message: types.Message):
    user_id = str(message.from_user.id)
    
    if db.get(user_id, {}).get("paid"):
        await message.answer("✅ У вас уже активирован Гений!")
        return
    
    prices = [LabeledPrice(label="Гений доступ", amount=599)]
    
    await bot.send_invoice(
        chat_id=message.chat.id,
        title="DafuqBlaze Codex - Гений",
        description="Максимальный интеллект • Безлимит • Навсегда",
        payload="genius_access",
        provider_token="",
        currency="XTR",
        prices=prices,
        start_parameter="genius"
    )

# ============ ПЛАТЕЖИ ============
@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout.id, ok=True)

@dp.message(F.successful_payment)
async def process_payment(message: types.Message):
    user_id = str(message.from_user.id)
    
    if user_id not in db:
        db[user_id] = {"username": message.from_user.username, "full_name": message.from_user.full_name, "requests": 0}
    
    db[user_id]["paid"] = True
    db[user_id]["paid_at"] = datetime.now().isoformat()
    db[user_id]["paid_amount"] = 5.99
    save_db(db)
    
    await message.answer(
        "✅ <b>Оплата получена!</b>\n\n🧠 Гений активирован!\n💵 $5.99\n\n🔄 Возвращайся на сайт и нажми <b>Проверить оплату</b>"
    )
    
    await bot.send_message(
        ADMIN_ID,
        f"💰 <b>ОПЛАТА STARS!</b>\n\n"
        f"👤 {message.from_user.full_name}\n"
        f"📱 @{message.from_user.username or 'нет'}\n"
        f"🆔 {user_id}\n"
        f"💵 $5.99\n"
        f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )

# ============ /feedback - НАПИСАТЬ МОДЕРАТОРУ ============
@dp.message(Command("feedback"))
async def cmd_feedback(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    
    await message.answer(
        "💬 <b>Напишите ваше сообщение:</b>\n\n"
        "Опишите ваш вопрос или проблему.\n"
        "Модератор ответит вам в ближайшее время.\n\n"
        "Для отмены нажмите /cancel"
    )
    
    await state.set_state(FeedbackState.waiting_for_message)

@dp.message(FeedbackState.waiting_for_message)
async def process_feedback(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    username = message.from_user.username or message.from_user.full_name
    
    # Отправляем модератору
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✉️ Ответить", callback_data=f"reply_{user_id}")]
    ])
    
    await bot.send_message(
        ADMIN_ID,
        f"📩 <b>НОВОЕ СООБЩЕНИЕ!</b>\n\n"
        f"👤 <b>От:</b> {message.from_user.full_name}\n"
        f"📱 @{message.from_user.username or 'нет'}\n"
        f"🆔: <code>{user_id}</code>\n\n"
        f"💬 <b>Сообщение:</b>\n{message.text}",
        reply_markup=kb
    )
    
    await message.answer(
        "✅ <b>Сообщение отправлено!</b>\n\n"
        "Модератор ответит вам в ближайшее время.\n"
        "Спасибо за обращение! 🙏"
    )
    
    # Сохраняем отправителя для ответа
    last_senders[ADMIN_ID] = user_id
    
    await state.clear()

# ============ ОТВЕТ МОДЕРАТОРА ПОЛЬЗОВАТЕЛЮ ============
@dp.callback_query(F.data.startswith("reply_"))
async def cb_reply(callback: types.CallbackQuery, state: FSMContext):
    # Только модератор может отвечать
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Только модератор может отвечать!")
        return
    
    user_id = callback.data.replace("reply_", "")
    last_senders[ADMIN_ID] = user_id
    
    await callback.message.answer(
        f"✉️ <b>Ответ пользователю {user_id}:</b>\n\n"
        f"Напишите ваше сообщение.\n"
        f"Для отмены: /cancel"
    )
    
    await state.set_state(ReplyState.waiting_for_message)
    await callback.answer()

# ============ /reply - БЫСТРЫЙ ОТВЕТ (ДЛЯ МОДЕРАТОРА) ============
@dp.message(Command("reply"))
async def cmd_reply(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Только модератор может отвечать!")
        return
    
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.answer(
            "❌ <b>Использование:</b>\n"
            "<code>/reply ID_пользователя</code>\n\n"
            "Пример: <code>/reply 123456789</code>"
        )
        return
    
    try:
        user_id = args[1]
        last_senders[ADMIN_ID] = user_id
        
        await message.answer(
            f"✉️ <b>Ответ пользователю {user_id}:</b>\n\n"
            f"Напишите сообщение.\n"
            f"Для отмены: /cancel"
        )
        
        await state.set_state(ReplyState.waiting_for_message)
    except:
        await message.answer("❌ Неверный ID пользователя")

@dp.message(ReplyState.waiting_for_message)
async def process_reply(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Только модератор может отвечать!")
        await state.clear()
        return
    
    user_id = last_senders.get(ADMIN_ID)
    
    if not user_id:
        await message.answer("❌ Нет активного пользователя для ответа.\nИспользуйте /reply ID")
        await state.clear()
        return
    
    try:
        await bot.send_message(
            user_id,
            f"📩 <b>Ответ от модератора:</b>\n\n"
            f"{message.text}\n\n"
            f"💡 Чтобы ответить, используйте /feedback"
        )
        
        await message.answer(
            f"✅ <b>Ответ отправлен!</b>\n\n"
            f"👤 Пользователь: <code>{user_id}</code>\n"
            f"💬 Сообщение: {message.text[:100]}"
        )
        
        # Уведомление пользователю что ответили
        user_info = db.get(user_id, {})
        if user_info:
            db[user_id]["last_reply"] = datetime.now().isoformat()
            save_db(db)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}")
    
    await state.clear()

# ============ /cancel ============
@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Операция отменена.")

# ============ /status ============
@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    user_id = str(message.from_user.id)
    user = db.get(user_id, {})
    is_paid = user.get("paid", False)
    
    if is_paid:
        await message.answer(
            f"🧠 <b>Статус: ГЕНИЙ</b>\n\n"
            f"✅ Активирован\n"
            f"📅 С: {user.get('paid_at', 'Неизвестно')[:10]}\n"
            f"💵 $5.99\n"
            f"♾ Навсегда"
        )
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 Купить $5.99", callback_data="buy_genius")]
        ])
        await message.answer("💡 <b>Обычный</b>\n\nКупи Гений:", reply_markup=kb)

# ============ /check_payment ============
@dp.message(Command("check_payment"))
async def cmd_check(message: types.Message):
    args = message.text.split()
    user_id = str(message.from_user.id)
    
    if len(args) > 1:
        check_id = args[1]
        if db.get(user_id, {}).get("paid", False):
            await message.answer(f"PAID_{check_id}")
        else:
            await message.answer(f"NOT_PAID_{check_id}")
    else:
        is_paid = db.get(user_id, {}).get("paid", False)
        await message.answer(f"STATUS: {'PAID' if is_paid else 'NOT_PAID'}")

# ============ /users - СПИСОК ПОЛЬЗОВАТЕЛЕЙ (ДЛЯ МОДЕРАТОРА) ============
@dp.message(Command("users"))
async def cmd_users(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Только модератор может смотреть список!")
        return
    
    if not db:
        await message.answer("📭 Нет пользователей")
        return
    
    text = "👥 <b>ПОЛЬЗОВАТЕЛИ:</b>\n\n"
    for uid, data in list(db.items())[-20:]:
        paid = "🧠" if data.get("paid") else "💡"
        text += f"{paid} <code>{uid}</code> — {data.get('full_name','?')}\n"
    
    await message.answer(text)

# ============ /help ============
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(
            "<b>📚 КОМАНДЫ МОДЕРАТОРА:</b>\n\n"
            "💬 /reply ID — ответить пользователю\n"
            "👥 /users — список пользователей\n"
            "📊 /status — статистика\n\n"
            "<b>Обычные команды:</b>\n"
            "💎 /pay — оплата\n"
            "💬 /feedback — написать модератору"
        )
    else:
        await message.answer(
            "<b>📚 ПОМОЩЬ:</b>\n\n"
            "💎 /pay — купить Гений $5.99\n"
            "💬 /feedback — написать модератору\n"
            "📊 /status — статус\n"
            "❓ /help — помощь\n\n"
            "🌐 Сайт: dafuqblazecodex.site.je"
        )

# ============ CALLBACK ============
@dp.callback_query(F.data == "buy_genius")
async def cb_buy(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    
    if db.get(user_id, {}).get("paid"):
        await callback.message.answer("✅ Уже активирован!")
        await callback.answer()
        return
    
    prices = [LabeledPrice(label="Гений доступ", amount=599)]
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title="DafuqBlaze Codex - Гений",
        description="Максимальный интеллект • Безлимит • Навсегда",
        payload="genius_access",
        provider_token="",
        currency="XTR",
        prices=prices,
        start_parameter="genius"
    )
    await callback.answer()

@dp.callback_query(F.data == "feedback")
async def cb_feedback(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "💬 <b>Напишите ваше сообщение:</b>\n\n"
        "Опишите ваш вопрос.\n"
        "Модератор ответит вам.\n\n"
        "Для отмены: /cancel"
    )
    await state.set_state(FeedbackState.waiting_for_message)
    await callback.answer()

@dp.callback_query(F.data == "status")
async def cb_status(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    user = db.get(user_id, {})
    if user.get("paid"):
        await callback.message.answer(f"🧠 Гений активен!\n📅 С {user.get('paid_at','?')[:10]}")
    else:
        await callback.message.answer("💡 Обычный\nКупи: /pay")
    await callback.answer()

# ============ СООБЩЕНИЯ ============
@dp.message()
async def handle_message(message: types.Message):
    user_id = str(message.from_user.id)
    
    if user_id not in db:
        db[user_id] = {"username": message.from_user.username, "full_name": message.from_user.full_name, "requests": 0, "paid": False}
    
    db[user_id]["requests"] += 1
    save_db(db)
    
    await message.answer(
        f"👋 Я бот DafuqBlaze Codex!\n\n"
        f"💎 /pay — купить Гений $5.99\n"
        f"💬 /feedback — написать модератору\n"
        f"🌐 Сайт: dafuqblazecodex.site.je"
    )

# ============ ЗАПУСК ============
async def main():
    print("🤖 DafuqBlaze Codex Bot запущен!")
    print("💎 Гений $5.99")
    print("💬 Обратная связь включена")
    print(f"👤 Модератор: {ADMIN_ID}")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
