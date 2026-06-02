import asyncio
import json
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# ============ НАСТРОЙКИ ============
BOT_TOKEN = "8014541670:AAHje0MwNKwoIxjtWsqsbLJGUKXgMgDnWxY"
ADMIN_ID = 7837849241  # Твой Telegram ID

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

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
        payer_id = args[1].replace("pay_genius_", "")
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
        [InlineKeyboardButton(text="💬 Помощь", callback_data="help")],
        [InlineKeyboardButton(text="📊 Статус", callback_data="status")]
    ])
    
    await message.answer(
        f"🤖 <b>DafuqBlaze Codex Bot</b>\n\n"
        f"👤 <b>{message.from_user.full_name}</b>\n"
        f"📊 Запросов: {db[user_id]['requests']}\n"
        f"⭐ Статус: {paid_status}\n\n"
        f"<b>Команды:</b>\n"
        f"💎 /pay — купить Гений\n"
        f"📊 /status — проверить статус\n"
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
        "✅ <b>Оплата получена!</b>\n\n"
        "🧠 Гений активирован!\n"
        "💵 $5.99\n\n"
        "🔄 Возвращайся на сайт и нажми <b>Проверить оплату</b>"
    )
    
    await bot.send_message(
        ADMIN_ID,
        f"💰 <b>ОПЛАТА STARS!</b>\n\n"
        f"👤 {message.from_user.full_name}\n"
        f"📱 @{message.from_user.username or 'нет'}\n"
        f"🆔 {user_id}\n"
        f"💵 $5.99\n"
        f"⭐ Оплачено Stars\n"
        f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )

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
            f"📅 Оплачен: {user.get('paid_at', 'Неизвестно')[:10]}\n"
            f"💵 Сумма: $5.99\n"
            f"♾ Безлимит навсегда"
        )
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 Купить $5.99", callback_data="buy_genius")]
        ])
        await message.answer(
            "💡 <b>Статус: ОБЫЧНЫЙ</b>\n\n"
            "Купи Гений за $5.99!",
            reply_markup=kb
        )

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

# ============ /help ============
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "<b>📚 ПОМОЩЬ</b>\n\n"
        "💎 /pay — купить Гений $5.99\n"
        "📊 /status — статус\n"
        "🔍 /check_payment — проверка\n"
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

@dp.callback_query(F.data == "status")
async def cb_status(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    user = db.get(user_id, {})
    if user.get("paid"):
        await callback.message.answer(f"🧠 Гений активен!\n📅 С {user.get('paid_at','?')[:10]}")
    else:
        await callback.message.answer("💡 Обычный\nКупи: /pay")
    await callback.answer()

@dp.callback_query(F.data == "help")
async def cb_help(callback: types.CallbackQuery):
    await callback.message.answer("💎 /pay • 📊 /status • 🔍 /check_payment")
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
        f"👋 Я бот оплаты DafuqBlaze Codex!\n\n"
        f"💎 /pay — купить Гений $5.99\n"
        f"🌐 Сайт: dafuqblazecodex.site.je"
    )

# ============ ЗАПУСК ============
async def main():
    print("🤖 DafuqBlaze Codex Bot запущен!")
    print("💎 Гений $5.99")
    print("👤 Админ: 7837849241")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())