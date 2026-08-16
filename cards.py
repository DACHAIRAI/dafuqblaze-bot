import random

CARDS = {
    'common': [
        {"id": 1, "name": "Чекушка Белуга", "effect": None, "description": "Классика жанра"},
        {"id": 2, "name": "Чекушка Пшеничная", "effect": None, "description": "Хлебный вкус"},
    ],
    'uncommon': [
        {"id": 3, "name": "Чекушка Медовая с перцем", "effect": "Двойной опыт", "description": "Жжет!"},
        {"id": 4, "name": "Чекушка Лесная ягода", "effect": "Удача", "description": "Ароматная"},
    ],
    'rare': [
        {"id": 5, "name": "Чекушка Кедровая настойка", "effect": "Двойной опыт+", "description": "Аромат тайги"},
        {"id": 6, "name": "Чекушка Облепиховая", "effect": "Удача+", "description": "Витаминная"},
    ],
    'epic': [
        {"id": 7, "name": "Чекушка Золотой корень", "effect": "Супер удача", "description": "Дает силу"},
    ],
    'legendary': [
        {"id": 8, "name": "Самогон деда", "effect": "Легендарный буст", "description": "Секретный рецепт"},
    ],
    'mythic': [
        {"id": 9, "name": "Чекушка Бессмертия", "effect": "Мифическая сила", "description": "Вечная молодость"},
    ],
    'secret': [
        {"id": 10, "name": "Чебурашковая чекушка", "effect": "Секретная редкость", "description": "УУУ!"},
    ]
}

ALL_CARDS = []
for rarity, cards in CARDS.items():
    for card in cards:
        ALL_CARDS.append({**card, "rarity": rarity})

def get_card_by_id(card_id):
    for card in ALL_CARDS:
        if card['id'] == card_id:
            return card
    return None

def get_card_by_name_and_rarity(card_name, rarity):
    for card in CARDS.get(rarity, []):
        if card['name'].lower() == card_name.lower():
            return {**card, "rarity": rarity}
    return None

RARITY_WEIGHTS = {
    'common': 40,
    'uncommon': 25,
    'rare': 18,
    'epic': 10,
    'legendary': 5,
    'mythic': 1.5,
    'secret': 0.5
}

def get_random_card():
    rarities = list(RARITY_WEIGHTS.keys())
    weights = list(RARITY_WEIGHTS.values())
    total = sum(weights)
    weights = [w/total for w in weights]
    rarity = random.choices(rarities, weights=weights, k=1)[0]
    card = random.choice(CARDS[rarity])
    return {**card, "rarity": rarity}