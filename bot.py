import logging
import json
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import config
from database import session, User, UserCard, Giveaway, BotChat
from cards import get_random_card, get_card_by_id, get_card_by_name_and_rarity, CARDS
from card_images import generate_card_image
from utils import format_time, get_rarity_emoji, get_rarity_name, parse_participants, set_participants

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def is_admin(username):
    return username == config.ADMIN_USERNAME

def get_all_chats():
    return session.query(BotChat).all()

def get_admin_user():
    return session.query(User).filter_by(username=config.ADMIN_USERNAME).first()

# ==================== ОСНОВНЫЕ КОМАНДЫ ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = session.query(User).filter_by(telegram_id=user.id).first()
    
    if not db_user:
        db_user = User(telegram_id=user.id, username=user.username, first_name=user.first_name)
        session.add(db_user)
        session.commit()
    
    await update.message.reply_text(
        f"🍾 Привет, {user.first_name}!\n\n"
        "📖 Команды:\n"
        "/hunt — найти чекушку (30 мин задержка)\n"
        "/profile — твоя коллекция\n"
        "/index — все карточки по редкостям\n"
        "/top — таблица лидеров\n"
        "/bonus — ежедневный бонус\n"
        "/cards — список всех карточек"
    )

async def hunt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = session.query(User).filter_by(telegram_id=user.id).first()
    
    if not db_user:
        await update.message.reply_text("Сначала /start")
        return
    
    # ===== ПРОВЕРКА ЗАДЕРЖКИ (30 МИНУТ) =====
    if db_user.last_hunt_time:
        time_diff = (datetime.now() - db_user.last_hunt_time).total_seconds()
        if time_diff < config.HUNT_COOLDOWN:
            wait_time = int(config.HUNT_COOLDOWN - time_diff)
            await update.message.reply_text(
                f"⏳ Подожди {format_time(wait_time)} перед новой охотой!"
            )
            return
    
    card_data = get_random_card()
    
    user_card = session.query(UserCard).filter_by(user_id=db_user.id, card_id=card_data['id']).first()
    if user_card:
        user_card.count += 1
    else:
        user_card = UserCard(user_id=db_user.id, card_id=card_data['id'], count=1)
        session.add(user_card)
    
    db_user.total_hunts += 1
    db_user.coins += 5
    db_user.last_hunt_time = datetime.now()  # Запоминаем время последней охоты
    session.commit()
    
    # Генерируем фото
    try:
        img_bytes = generate_card_image(card_data['name'], card_data['rarity'], card_data['effect'], card_data['description'], card_data['id'])
    except:
        img_bytes = None
    
    rarity_emoji = get_rarity_emoji(card_data['rarity'])
    rarity_name = get_rarity_name(card_data['rarity'])
    
    message = f"🍾 **Ты нашел чекушку!**\n\n"
    message += f"**{card_data['name']}**\n"
    message += f"{rarity_emoji} Редкость: {rarity_name}\n"
    message += f"📝 {card_data['description']}\n"
    
    if card_data['effect']:
        message += f"✨ Эффект: {card_data['effect']}\n"
    
    message += f"\n💰 +5 монет\n"
    message += f"📦 Всего карточек: {db_user.total_hunts}\n"
    message += f"⏳ Следующая охота через 30 минут"
    
    if img_bytes:
        await update.message.reply_photo(photo=img_bytes, caption=message, parse_mode='Markdown')
    else:
        await update.message.reply_text(message, parse_mode='Markdown')

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = session.query(User).filter_by(telegram_id=user.id).first()
    
    if not db_user:
        await update.message.reply_text("Сначала /start")
        return
    
    user_cards = session.query(UserCard).filter_by(user_id=db_user.id).all()
    total_cards = sum(card.count for card in user_cards)
    unique_cards = len(user_cards)
    
    rarity_stats = {}
    for user_card in user_cards:
        card_data = get_card_by_id(user_card.card_id)
        if card_data:
            rarity = card_data['rarity']
            rarity_stats[rarity] = rarity_stats.get(rarity, 0) + user_card.count
    
    message = f"👤 **Профиль**\nИмя: {db_user.first_name or 'Игрок'}\n\n📊 Всего: {total_cards}\nУникальных: {unique_cards}\nОхот: {db_user.total_hunts}\n💰 Монет: {db_user.coins}\n"
    if rarity_stats:
        message += "\n**Редкости:**\n"
        for rarity, count in sorted(rarity_stats.items()):
            message += f"{get_rarity_emoji(rarity)} {get_rarity_name(rarity)}: {count}\n"
    
    keyboard = [[InlineKeyboardButton("📚 ИНДЕКС", callback_data="open_index")]]
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def index(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = session.query(User).filter_by(telegram_id=user.id).first()
    
    if not db_user:
        await update.message.reply_text("Сначала /start")
        return
    
    user_cards = session.query(UserCard).filter_by(user_id=db_user.id).all()
    if not user_cards:
        await update.message.reply_text("Нет карточек! Используй /hunt")
        return
    
    rarity_groups = {}
    for user_card in user_cards:
        card_data = get_card_by_id(user_card.card_id)
        if card_data:
            rarity = card_data['rarity']
            if rarity not in rarity_groups:
                rarity_groups[rarity] = []
            rarity_groups[rarity].append({'card': card_data, 'count': user_card.count})
    
    keyboard = []
    for rarity in ['common', 'uncommon', 'rare', 'epic', 'legendary', 'mythic', 'secret']:
        if rarity in rarity_groups:
            keyboard.append([InlineKeyboardButton(f"{get_rarity_emoji(rarity)} {get_rarity_name(rarity)} ({len(rarity_groups[rarity])} шт.)", callback_data=f"rarity_{rarity}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile")])
    await update.message.reply_text("📚 **ИНДЕКС**\nВыбери редкость:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = session.query(User).order_by(User.total_hunts.desc()).limit(10).all()
    
    if not users:
        await update.message.reply_text("Нет игроков!")
        return
    
    message = "🏆 **Топ игроков**\n\n"
    for i, user in enumerate(users, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        name = user.first_name or user.username or f"Игрок {user.telegram_id}"
        message += f"{medal} {name} — {user.total_hunts} карточек\n"
    await update.message.reply_text(message, parse_mode='Markdown')

async def bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = session.query(User).filter_by(telegram_id=user.id).first()
    
    if not db_user:
        await update.message.reply_text("Сначала /start")
        return
    
    today = datetime.now().date()
    if db_user.daily_bonus_date and db_user.daily_bonus_date.date() == today:
        await update.message.reply_text("🎁 Бонус уже получен!")
        return
    
    db_user.coins += 30
    db_user.hunt_count_today = max(0, db_user.hunt_count_today - 3)
    db_user.daily_bonus_date = datetime.now()
    session.commit()
    
    await update.message.reply_text(f"🎁 **Бонус!**\n💰 +30 монет\n🆓 +3 охоты")

async def cards_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = "🃏 **Все карточки:**\n\n"
    for rarity, cards in CARDS.items():
        message += f"{get_rarity_emoji(rarity)} **{get_rarity_name(rarity)}** ({len(cards)} шт.)\n"
        for card in cards:
            message += f"  • {card['name']}\n"
        message += "\n"
    await update.message.reply_text(message, parse_mode='Markdown')

# ==================== АДМИН КОМАНДЫ ====================

async def adduser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not is_admin(user.username):
        await update.message.reply_text("⛔ Нет прав!")
        return
    
    args = context.args
    if len(args) < 1:
        await update.message.reply_text(
            "❌ Использование: /adduser @username\n"
            "Пример: /adduser @Artem30113"
        )
        return
    
    target_username = args[0].replace('@', '')
    
    existing = session.query(User).filter_by(username=target_username).first()
    if existing:
        await update.message.reply_text(f"✅ Пользователь @{target_username} уже есть в базе!")
        return
    
    try:
        chat = await context.bot.get_chat(f"@{target_username}")
        
        new_user = User(
            telegram_id=chat.id,
            username=chat.username,
            first_name=chat.first_name or "Без имени"
        )
        session.add(new_user)
        session.commit()
        
        await update.message.reply_text(
            f"✅ Пользователь @{target_username} добавлен в базу!\n"
            f"ID: {chat.id}\n"
            f"Имя: {chat.first_name or 'Без имени'}"
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Не удалось найти пользователя @{target_username}!\n"
            f"Ошибка: {e}\n\n"
            f"Попробуй добавить по ID: /adduserid ID Имя"
        )

async def adduserid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not is_admin(user.username):
        await update.message.reply_text("⛔ Нет прав!")
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "❌ Использование: /adduserid ID Имя\n"
            "Пример: /adduserid 123456789 Артем\n\n"
            "ID можно получить у бота @getmyid_bot"
        )
        return
    
    try:
        target_id = int(args[0])
        first_name = ' '.join(args[1:])
    except:
        await update.message.reply_text("❌ ID должен быть числом!")
        return
    
    existing = session.query(User).filter_by(telegram_id=target_id).first()
    if existing:
        await update.message.reply_text(f"✅ Пользователь {first_name} (ID: {target_id}) уже есть в базе!")
        return
    
    new_user = User(
        telegram_id=target_id,
        username=None,
        first_name=first_name
    )
    session.add(new_user)
    session.commit()
    
    await update.message.reply_text(
        f"✅ Пользователь добавлен в базу!\n"
        f"ID: {target_id}\n"
        f"Имя: {first_name}"
    )

async def givecard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not is_admin(user.username):
        await update.message.reply_text("⛔ Нет прав!")
        return
    
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "❌ Использование: /givecard @username Название_карты Редкость\n\n"
            "Пример: /givecard @Dafuq_Blaze Чекушка_Белуга common\n"
            "Редкости: common, uncommon, rare, epic, legendary, mythic, secret\n\n"
            "Название пиши без пробелов, через _ (Чекушка_Белуга)"
        )
        return
    
    target_username = args[0].replace('@', '')
    card_name = args[1].replace('_', ' ')
    rarity = args[2].lower()
    
    if rarity not in CARDS:
        await update.message.reply_text(
            f"❌ Редкость '{rarity}' не найдена!\n"
            "Доступные: common, uncommon, rare, epic, legendary, mythic, secret"
        )
        return
    
    target_user = session.query(User).filter_by(username=target_username).first()
    if not target_user:
        await update.message.reply_text(
            f"❌ Пользователь @{target_username} не найден в базе!\n\n"
            f"Сначала добавь его:\n"
            f"/adduser @{target_username} — если есть username\n"
            f"/adduserid ID Имя — если нет username"
        )
        return
    
    card_data = get_card_by_name_and_rarity(card_name, rarity)
    if not card_data:
        await update.message.reply_text(
            f"❌ Карточка '{card_name}' с редкостью '{rarity}' не найдена!\n"
            f"Проверь название и редкость.\n"
            f"Доступные карты: /cards"
        )
        return
    
    user_card = session.query(UserCard).filter_by(
        user_id=target_user.id,
        card_id=card_data['id']
    ).first()
    
    if user_card:
        user_card.count += 1
    else:
        user_card = UserCard(
            user_id=target_user.id,
            card_id=card_data['id'],
            count=1
        )
        session.add(user_card)
    
    session.commit()
    
    rarity_emoji = get_rarity_emoji(rarity)
    rarity_name = get_rarity_name(rarity)
    
    await update.message.reply_text(
        f"✅ **Карточка выдана!**\n\n"
        f"Пользователь: @{target_username}\n"
        f"Карта: {rarity_emoji} **{card_data['name']}**\n"
        f"Редкость: {rarity_name}\n"
        f"ID: #{card_data['id']}"
    )
    
    try:
        await context.bot.send_message(
            chat_id=target_user.telegram_id,
            text=(
                f"🎁 **Тебе выдали карту!**\n\n"
                f"Ты получил: {rarity_emoji} **{card_data['name']}**\n"
                f"Редкость: {rarity_name}\n\n"
                f"Проверь свою коллекцию через /profile"
            ),
            parse_mode='Markdown'
        )
    except Exception as e:
        logging.error(f"Ошибка отправки уведомления: {e}")

async def givecardid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not is_admin(user.username):
        await update.message.reply_text("⛔ Нет прав!")
        return
    
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "❌ Использование: /givecardid ID Название_карты Редкость\n\n"
            "Пример: /givecardid 123456789 Чекушка_Белуга common\n"
            "Редкости: common, uncommon, rare, epic, legendary, mythic, secret\n\n"
            "Название пиши без пробелов, через _ (Чекушка_Белуга)\n"
            "ID можно получить у бота @getmyid_bot"
        )
        return
    
    try:
        target_id = int(args[0])
    except:
        await update.message.reply_text("❌ ID должен быть числом!")
        return
    
    card_name = args[1].replace('_', ' ')
    rarity = args[2].lower()
    
    if rarity not in CARDS:
        await update.message.reply_text(
            f"❌ Редкость '{rarity}' не найдена!\n"
            "Доступные: common, uncommon, rare, epic, legendary, mythic, secret"
        )
        return
    
    target_user = session.query(User).filter_by(telegram_id=target_id).first()
    if not target_user:
        await update.message.reply_text(
            f"❌ Пользователь с ID {target_id} не найден в базе!\n\n"
            f"Сначала добавь его: /adduserid {target_id} Имя"
        )
        return
    
    card_data = get_card_by_name_and_rarity(card_name, rarity)
    if not card_data:
        await update.message.reply_text(
            f"❌ Карточка '{card_name}' с редкостью '{rarity}' не найдена!\n"
            f"Проверь название и редкость.\n"
            f"Доступные карты: /cards"
        )
        return
    
    user_card = session.query(UserCard).filter_by(
        user_id=target_user.id,
        card_id=card_data['id']
    ).first()
    
    if user_card:
        user_card.count += 1
    else:
        user_card = UserCard(
            user_id=target_user.id,
            card_id=card_data['id'],
            count=1
        )
        session.add(user_card)
    
    session.commit()
    
    rarity_emoji = get_rarity_emoji(rarity)
    rarity_name = get_rarity_name(rarity)
    
    await update.message.reply_text(
        f"✅ **Карточка выдана по ID!**\n\n"
        f"Пользователь: {target_user.first_name or 'Без имени'} (ID: {target_id})\n"
        f"Карта: {rarity_emoji} **{card_data['name']}**\n"
        f"Редкость: {rarity_name}\n"
        f"ID: #{card_data['id']}"
    )
    
    try:
        await context.bot.send_message(
            chat_id=target_user.telegram_id,
            text=(
                f"🎁 **Тебе выдали карту!**\n\n"
                f"Ты получил: {rarity_emoji} **{card_data['name']}**\n"
                f"Редкость: {rarity_name}\n\n"
                f"Проверь свою коллекцию через /profile"
            ),
            parse_mode='Markdown'
        )
    except Exception as e:
        logging.error(f"Ошибка отправки уведомления: {e}")

# ==================== /say ====================

async def say(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.username):
        await update.message.reply_text("⛔ Нет прав!")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text("❌ /say Текст\nПример: /say Привет")
        return
    
    text = ' '.join(args).replace('_', ' ')
    chats = get_all_chats()
    
    if not chats:
        await update.message.reply_text("❌ Нет чатов!")
        return
    
    keyboard = []
    for chat in chats:
        keyboard.append([InlineKeyboardButton(
            f"📢 {chat.chat_title}", 
            callback_data=f"say_to_{chat.chat_id}"
        )])
    
    context.user_data['say_text'] = text
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    await update.message.reply_text(
        f"📝 **Выбери чат для отправки:**\n\n{text}", 
        parse_mode='Markdown', 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==================== /giveaway ====================

async def giveaway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.username):
        await update.message.reply_text("⛔ Нет прав!")
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "❌ /giveaway Название Редкость\n"
            "Пример: /giveaway Чекушка_Белуга common\n\n"
            "После выбора чата создастся розыгрыш."
        )
        return
    
    card_name = args[0].replace('_', ' ')
    rarity = args[1].lower()
    
    if rarity not in CARDS:
        await update.message.reply_text(f"❌ Редкость '{rarity}' не найдена!")
        return
    
    card_data = get_card_by_name_and_rarity(card_name, rarity)
    if not card_data:
        await update.message.reply_text(f"❌ Карточка '{card_name}' не найдена!")
        return
    
    context.user_data['giveaway_card_name'] = card_data['name']
    context.user_data['giveaway_rarity'] = rarity
    context.user_data['giveaway_card_id'] = card_data['id']
    
    chats = get_all_chats()
    if not chats:
        await update.message.reply_text("❌ Нет чатов!")
        return
    
    keyboard = []
    for chat in chats:
        keyboard.append([InlineKeyboardButton(
            f"🎯 {chat.chat_title}", 
            callback_data=f"giveaway_to_{chat.chat_id}"
        )])
    
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    await update.message.reply_text(
        f"🎉 **Розыгрыш создаётся!**\n\n"
        f"Приз: {get_rarity_emoji(rarity)} {card_data['name']}\n"
        f"Редкость: {get_rarity_name(rarity)}\n\n"
        f"**Выбери чат для розыгрыша:**",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==================== КНОПКИ ====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    db_user = session.query(User).filter_by(telegram_id=user.id).first()
    
    if not db_user:
        db_user = User(telegram_id=user.id, username=user.username, first_name=user.first_name)
        session.add(db_user)
        session.commit()
    
    data = query.data
    
    # ===== ОТПРАВКА СООБЩЕНИЯ (/say) =====
    if data.startswith("say_to_"):
        chat_id = int(data.replace("say_to_", ""))
        text = context.user_data.get('say_text', '')
        
        if not text:
            await query.edit_message_text("❌ Нет текста!")
            return
        
        try:
            await context.bot.send_message(chat_id=chat_id, text=f"📢 {text}")
            await query.edit_message_text(f"✅ Сообщение отправлено в чат!")
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {e}")
    
    # ===== СОЗДАНИЕ РОЗЫГРЫША =====
    elif data.startswith("giveaway_to_"):
        chat_id = int(data.replace("giveaway_to_", ""))
        
        card_name = context.user_data.get('giveaway_card_name')
        rarity = context.user_data.get('giveaway_rarity')
        card_id = context.user_data.get('giveaway_card_id')
        
        if not card_name or not rarity:
            await query.edit_message_text("❌ Данные розыгрыша потеряны! Начни заново.")
            return
        
        giveaway = Giveaway(
            card_name=card_name,
            card_rarity=rarity,
            card_id=card_id,
            created_by=user.username,
            is_active=True,
            participants='[]',
            chat_id=chat_id
        )
        session.add(giveaway)
        session.commit()
        
        rarity_emoji = get_rarity_emoji(rarity)
        rarity_name = get_rarity_name(rarity)
        
        # В ЧАТ УЧАСТНИКАМ — ТОЛЬКО 1 КНОПКА
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"🎉 **РОЗЫГРЫШ!**\n\n"
                    f"Приз: {rarity_emoji} **{card_name}**\n"
                    f"Редкость: {rarity_name}\n"
                    f"ID: #{giveaway.id}\n\n"
                    f"👇 Нажми кнопку чтобы участвовать!"
                ),
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎯 УЧАСТВОВАТЬ", callback_data=f"join_{giveaway.id}")]
                ])
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка отправки в чат: {e}")
            return
        
        # В ЛИЧКУ АДМИНА — УПРАВЛЕНИЕ (3 КНОПКИ)
        admin_user = get_admin_user()
        if admin_user:
            try:
                await context.bot.send_message(
                    chat_id=admin_user.telegram_id,
                    text=(
                        f"🔔 **УПРАВЛЕНИЕ РОЗЫГРЫШЕМ**\n\n"
                        f"Приз: {rarity_emoji} {card_name}\n"
                        f"Редкость: {rarity_name}\n"
                        f"ID: #{giveaway.id}\n"
                        f"Чат: {chat_id}\n\n"
                        f"👇 Управляй розыгрышем:"
                    ),
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📊 Участники", callback_data=f"list_{giveaway.id}")],
                        [InlineKeyboardButton("🏆 ВЫБРАТЬ ПОБЕДИТЕЛЯ", callback_data=f"finish_{giveaway.id}")],
                        [InlineKeyboardButton("❌ Отменить розыгрыш", callback_data=f"cancel_giveaway_{giveaway.id}")]
                    ])
                )
            except Exception as e:
                logging.error(f"Ошибка отправки админу: {e}")
        
        await query.edit_message_text(f"✅ Розыгрыш создан!\n📢 Отправлен в чат\n📨 Бот написал админу в ЛС")
    
    elif data == "cancel":
        await query.edit_message_text("❌ Отменено")
    
    # ===== ИНДЕКС =====
    elif data == "open_index":
        user_cards = session.query(UserCard).filter_by(user_id=db_user.id).all()
        if not user_cards:
            await query.edit_message_text("Нет карточек!")
            return
        
        rarity_groups = {}
        for user_card in user_cards:
            card_data = get_card_by_id(user_card.card_id)
            if card_data:
                rarity = card_data['rarity']
                if rarity not in rarity_groups:
                    rarity_groups[rarity] = []
                rarity_groups[rarity].append({'card': card_data, 'count': user_card.count})
        
        keyboard = []
        for rarity in ['common', 'uncommon', 'rare', 'epic', 'legendary', 'mythic', 'secret']:
            if rarity in rarity_groups:
                keyboard.append([InlineKeyboardButton(f"{get_rarity_emoji(rarity)} {get_rarity_name(rarity)} ({len(rarity_groups[rarity])} шт.)", callback_data=f"rarity_{rarity}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile")])
        await query.edit_message_text("📚 **ИНДЕКС**\nВыбери редкость:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("rarity_"):
        rarity = data.replace("rarity_", "")
        user_cards = session.query(UserCard).filter_by(user_id=db_user.id).all()
        cards_in_rarity = []
        for user_card in user_cards:
            card_data = get_card_by_id(user_card.card_id)
            if card_data and card_data['rarity'] == rarity:
                cards_in_rarity.append({'card': card_data, 'count': user_card.count})
        
        if not cards_in_rarity:
            await query.edit_message_text("Нет карточек этой редкости!")
            return
        
        message = f"{get_rarity_emoji(rarity)} **{get_rarity_name(rarity)}**\n\n"
        for item in cards_in_rarity:
            message += f"• {item['card']['name']} — {item['count']} шт.\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="open_index")]]
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "back_to_profile":
        user_cards = session.query(UserCard).filter_by(user_id=db_user.id).all()
        total_cards = sum(card.count for card in user_cards)
        unique_cards = len(user_cards)
        
        rarity_stats = {}
        for user_card in user_cards:
            card_data = get_card_by_id(user_card.card_id)
            if card_data:
                rarity = card_data['rarity']
                rarity_stats[rarity] = rarity_stats.get(rarity, 0) + user_card.count
        
        message = f"👤 **Профиль**\nИмя: {db_user.first_name or 'Игрок'}\n\n📊 Всего: {total_cards}\nУникальных: {unique_cards}\nОхот: {db_user.total_hunts}\n💰 Монет: {db_user.coins}\n"
        if rarity_stats:
            message += "\n**Редкости:**\n"
            for rarity, count in sorted(rarity_stats.items()):
                message += f"{get_rarity_emoji(rarity)} {get_rarity_name(rarity)}: {count}\n"
        
        keyboard = [[InlineKeyboardButton("📚 ИНДЕКС", callback_data="open_index")]]
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    # ===== РОЗЫГРЫШ =====
    elif data.startswith("join_"):
        giveaway_id = int(data.replace("join_", ""))
        giveaway = session.query(Giveaway).filter_by(id=giveaway_id).first()
        if not giveaway or not giveaway.is_active:
            await query.edit_message_text("❌ Розыгрыш не активен!")
            return
        
        participants = parse_participants(giveaway.participants)
        if user.telegram_id in participants:
            await query.edit_message_text("❌ Ты уже участвуешь в этом розыгрыше!")
            return
        
        participants.append(user.telegram_id)
        giveaway.participants = set_participants(participants)
        session.commit()
        
        await query.edit_message_text(f"✅ Ты успешно участвуешь в розыгрыше #{giveaway_id}!")
    
    # ===== СПИСОК УЧАСТНИКОВ (в ЛС админа) =====
    elif data.startswith("list_"):
        if not is_admin(user.username):
            await query.edit_message_text("⛔ Только админ может это видеть!")
            return
        
        giveaway_id = int(data.replace("list_", ""))
        giveaway = session.query(Giveaway).filter_by(id=giveaway_id).first()
        if not giveaway:
            await query.edit_message_text("❌ Розыгрыш не найден!")
            return
        
        participants = parse_participants(giveaway.participants)
        if not participants:
            await query.edit_message_text("📊 Пока никто не участвует!")
            return
        
        message = f"📊 **Участники розыгрыша #{giveaway_id}:**\n\n"
        for i, uid in enumerate(participants, 1):
            try:
                member = await context.bot.get_chat(uid)
                name = member.first_name or str(uid)
                if member.username:
                    name += f" (@{member.username})"
            except:
                name = str(uid)
            message += f"{i}. {name}\n"
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Вернуться к управлению", callback_data=f"back_to_control_{giveaway.id}")]
            ])
        )
    
    # ===== ВЕРНУТЬСЯ К УПРАВЛЕНИЮ =====
    elif data.startswith("back_to_control_"):
        giveaway_id = int(data.replace("back_to_control_", ""))
        giveaway = session.query(Giveaway).filter_by(id=giveaway_id).first()
        
        if not giveaway:
            await query.edit_message_text("❌ Розыгрыш не найден!")
            return
        
        card_data = get_card_by_id(giveaway.card_id)
        rarity_emoji = get_rarity_emoji(giveaway.card_rarity)
        rarity_name = get_rarity_name(giveaway.card_rarity)
        
        await query.edit_message_text(
            f"🔔 **УПРАВЛЕНИЕ РОЗЫГРЫШЕМ**\n\n"
            f"Приз: {rarity_emoji} {card_data['name']}\n"
            f"Редкость: {rarity_name}\n"
            f"ID: #{giveaway.id}\n\n"
            f"👇 Управляй розыгрышем:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Участники", callback_data=f"list_{giveaway.id}")],
                [InlineKeyboardButton("🏆 ВЫБРАТЬ ПОБЕДИТЕЛЯ", callback_data=f"finish_{giveaway.id}")],
                [InlineKeyboardButton("❌ Отменить розыгрыш", callback_data=f"cancel_giveaway_{giveaway.id}")]
            ])
        )
    
    # ===== ВЫБРАТЬ ПОБЕДИТЕЛЯ (в ЛС админа) =====
    elif data.startswith("finish_"):
        if not is_admin(user.username):
            await query.edit_message_text("⛔ Только админ может это сделать!")
            return
        
        giveaway_id = int(data.replace("finish_", ""))
        giveaway = session.query(Giveaway).filter_by(id=giveaway_id).first()
        if not giveaway or not giveaway.is_active:
            await query.edit_message_text("❌ Розыгрыш не активен!")
            return
        
        participants = parse_participants(giveaway.participants)
        if not participants:
            await query.edit_message_text("❌ Нет участников!")
            return
        
        winner_id = random.choice(participants)
        giveaway.winner_id = winner_id
        giveaway.is_active = False
        session.commit()
        
        card_data = get_card_by_id(giveaway.card_id)
        rarity_emoji = get_rarity_emoji(giveaway.card_rarity)
        rarity_name = get_rarity_name(giveaway.card_rarity)
        
        winner_user = session.query(User).filter_by(telegram_id=winner_id).first()
        
        if winner_user:
            user_card = session.query(UserCard).filter_by(user_id=winner_user.id, card_id=giveaway.card_id).first()
            if user_card:
                user_card.count += 1
            else:
                user_card = UserCard(user_id=winner_user.id, card_id=giveaway.card_id, count=1)
                session.add(user_card)
            session.commit()
            
            try:
                member = await context.bot.get_chat(winner_id)
                winner_name = member.first_name or str(winner_id)
                if member.username:
                    winner_name += f" (@{member.username})"
            except:
                winner_name = str(winner_id)
            
            # ОТПРАВЛЯЕМ РЕЗУЛЬТАТ В ЧАТ
            try:
                await context.bot.send_message(
                    chat_id=giveaway.chat_id,
                    text=(
                        f"🏆 **РОЗЫГРЫШ ЗАВЕРШЕН!**\n\n"
                        f"Приз: {rarity_emoji} **{card_data['name']}**\n"
                        f"Редкость: {rarity_name}\n\n"
                        f"🎉 **ПОБЕДИТЕЛЬ:** {winner_name}\n\n"
                        f"Поздравляем!"
                    ),
                    parse_mode='Markdown'
                )
            except:
                pass
            
            # БОТ ПИШЕТ АДМИНУ В ЛС
            await query.edit_message_text(
                f"✅ **РОЗЫГРЫШ ЗАВЕРШЕН!**\n\n"
                f"Приз: {rarity_emoji} {card_data['name']}\n"
                f"Редкость: {rarity_name}\n"
                f"ID: #{giveaway.id}\n"
                f"Победитель: {winner_name}\n\n"
                f"Карточка выдана победителю!",
                parse_mode='Markdown'
            )
            
            # УВЕДОМЛЕНИЕ ПОБЕДИТЕЛЮ
            try:
                await context.bot.send_message(
                    winner_id,
                    f"🎉 **Ты победил в розыгрыше!**\n\n"
                    f"Ты получил: {rarity_emoji} **{card_data['name']}**\n"
                    f"Редкость: {rarity_name}\n\n"
                    f"Проверь свою коллекцию через /profile"
                )
            except:
                pass
    
    # ===== ОТМЕНА РОЗЫГРЫША =====
    elif data.startswith("cancel_giveaway_"):
        if not is_admin(user.username):
            await query.edit_message_text("⛔ Только админ может это сделать!")
            return
        
        giveaway_id = int(data.replace("cancel_giveaway_", ""))
        giveaway = session.query(Giveaway).filter_by(id=giveaway_id).first()
        if not giveaway or not giveaway.is_active:
            await query.edit_message_text("❌ Розыгрыш уже не активен!")
            return
        
        giveaway.is_active = False
        session.commit()
        
        await query.edit_message_text(f"❌ Розыгрыш #{giveaway_id} отменён!")

# ==================== ЗАПУСК ====================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Ошибка: {context.error}")

def main():
    print("🤖 Бот запускается...")
    
    app = Application.builder().token(config.BOT_TOKEN).build()
    
    # Основные команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hunt", hunt))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("index", index))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("bonus", bonus))
    app.add_handler(CommandHandler("cards", cards_list))
    
    # Админ команды
    app.add_handler(CommandHandler("adduser", adduser))
    app.add_handler(CommandHandler("adduserid", adduserid))
    app.add_handler(CommandHandler("givecard", givecard))
    app.add_handler(CommandHandler("givecardid", givecardid))
    app.add_handler(CommandHandler("say", say))
    app.add_handler(CommandHandler("giveaway", giveaway))
    
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_error_handler(error_handler)
    
    print("✅ База готова!")
    print("🤖 Бот запущен!")
    print(f"👑 Админ: @{config.ADMIN_USERNAME}")
    print(f"📋 Чаты: Mysterious TV, Клан АНТИ-ГАББИ")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
