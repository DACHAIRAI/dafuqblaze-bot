from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String)
    first_name = Column(String)
    coins = Column(Integer, default=100)
    total_hunts = Column(Integer, default=0)
    daily_bonus_date = Column(DateTime)
    last_hunt_time = Column(DateTime)
    hunt_count_today = Column(Integer, default=0)

class UserCard(Base):
    __tablename__ = 'user_cards'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    card_id = Column(Integer, nullable=False)
    count = Column(Integer, default=1)
    acquired_at = Column(DateTime, default=datetime.now)

class Giveaway(Base):
    __tablename__ = 'giveaways'
    id = Column(Integer, primary_key=True)
    card_name = Column(String, nullable=False)
    card_rarity = Column(String, nullable=False)
    card_id = Column(Integer, nullable=False)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    is_active = Column(Boolean, default=True)
    participants = Column(Text, default='[]')
    winner_id = Column(Integer, nullable=True)
    chat_id = Column(Integer, nullable=True)

class BotChat(Base):
    __tablename__ = 'bot_chats'
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, unique=True, nullable=False)
    chat_title = Column(String)
    chat_type = Column(String)
    invite_link = Column(String)
    added_at = Column(DateTime, default=datetime.now)

# ==================== ДОБАВЛЯЕМ ЧАТЫ ====================
CHATS_TO_ADD = [
    {
        "chat_id": -1003885120281,
        "chat_title": "Mysterious TV",
        "chat_type": "supergroup",
        "invite_link": "https://t.me/+OODGLKMpAKgwYjdi"
    },
    {
        "chat_id": -1003593746757,
        "chat_title": "Клан АНТИ-ГАББИ",
        "chat_type": "supergroup",
        "invite_link": "https://t.me/AntiTitanGubby"
    },
]

# =========================================================

# СОЗДАЕМ БАЗУ (ЕСЛИ НЕ СУЩЕСТВУЕТ)
db_path = 'chekushka.db'

# НЕ УДАЛЯЕМ СТАРУЮ БАЗУ!
# Просто создаём новую, если её нет

engine = create_engine(f'sqlite:///{db_path}')
Base.metadata.create_all(engine)  # Создаёт таблицы, если их нет
Session = sessionmaker(bind=engine)
session = Session()

# Добавляем чаты, если их ещё нет
for chat_data in CHATS_TO_ADD:
    existing = session.query(BotChat).filter_by(chat_id=chat_data["chat_id"]).first()
    if not existing:
        new_chat = BotChat(
            chat_id=chat_data["chat_id"],
            chat_title=chat_data["chat_title"],
            chat_type=chat_data["chat_type"],
            invite_link=chat_data["invite_link"]
        )
        session.add(new_chat)
        print(f"✅ Чат '{chat_data['chat_title']}' добавлен в базу!")
    else:
        print(f"⏭️ Чат '{chat_data['chat_title']}' уже есть в базе")

session.commit()
print("✅ База данных готова!")