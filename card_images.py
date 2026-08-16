from PIL import Image, ImageDraw
import io
import os

def get_card_image_path(card_id, rarity):
    """Находит фото карточки по ID"""
    folder = os.path.join('images', rarity)
    extensions = ['.jpg', '.jpeg', '.png', '.webp']
    
    for ext in extensions:
        path = os.path.join(folder, f"{card_id}{ext}")
        if os.path.exists(path):
            return path
    return None

def generate_card_image(card_name, rarity, effect, description, card_id):
    """
    Просто возвращает ФОТО чекушки без текста на картинке.
    Весь текст будет в сообщении бота!
    """
    width, height = 512, 512
    
    # Ищем фото
    image_path = get_card_image_path(card_id, rarity)
    
    if image_path and os.path.exists(image_path):
        try:
            # Загружаем фото
            img = Image.open(image_path).convert('RGB')
            
            # Изменяем размер до 512x512 (сохраняя пропорции)
            img.thumbnail((width, height), Image.Resampling.LANCZOS)
            
            # Создаём квадратный фон
            final_img = Image.new('RGB', (width, height), '#FFFFFF')
            
            # Вставляем фото по центру
            x = (width - img.width) // 2
            y = (height - img.height) // 2
            final_img.paste(img, (x, y))
            
        except Exception as e:
            print(f"Ошибка загрузки фото: {e}")
            # Если фото нет — белый квадрат с эмодзи
            final_img = Image.new('RGB', (width, height), '#F0F0F0')
            draw = ImageDraw.Draw(final_img)
            draw.text((width//2-50, height//2-30), "🍾", fill='#000000')
    else:
        # Если фото нет — белый квадрат с эмодзи
        final_img = Image.new('RGB', (width, height), '#F0F0F0')
        draw = ImageDraw.Draw(final_img)
        draw.text((width//2-50, height//2-30), "🍾", fill='#000000')
    
    # Сохраняем
    img_byte_arr = io.BytesIO()
    final_img.save(img_byte_arr, format='PNG', quality=95)
    img_byte_arr.seek(0)
    return img_byte_arr