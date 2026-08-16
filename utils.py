import json

def format_time(seconds):
    """Форматирует время в читаемый вид"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}ч {minutes}м {seconds}с"
    elif minutes > 0:
        return f"{minutes}м {seconds}с"
    else:
        return f"{seconds}с"

def get_rarity_emoji(rarity):
    emojis = {
        'common': '⚪',
        'uncommon': '🟢',
        'rare': '🔵',
        'epic': '🟣',
        'legendary': '🟠',
        'mythic': '🔴',
        'secret': '⭐'
    }
    return emojis.get(rarity, '⚪')

def get_rarity_name(rarity):
    names = {
        'common': 'Обычная',
        'uncommon': 'Необычная',
        'rare': 'Редкая',
        'epic': 'Эпическая',
        'legendary': 'Легендарная',
        'mythic': 'Мифическая',
        'secret': 'Секретная'
    }
    return names.get(rarity, rarity.capitalize())

def parse_participants(participants_json):
    try:
        return json.loads(participants_json)
    except:
        return []

def set_participants(participants_list):
    return json.dumps(participants_list)