import os
import hashlib
import aiohttp
import aiofiles
import aiomysql
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'db': os.getenv('DB_NAME', 'telegram_bot'),
    'autocommit': True
}

BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
GRAMS_SERVICE_URL = os.getenv('GRAMS_SERVICE_URL', 'http://localhost:3003')
TRANSLATIONS_SERVICE_URL = os.getenv('TRANSLATIONS_SERVICE_URL', 'http://localhost:3000')
PERMISSIONS_TOKEN = os.getenv('PERMISSIONS_TOKEN', '')

# Директория для хранения изображений
IMAGES_DIR = Path('images')
IMAGES_DIR.mkdir(exist_ok=True)

# Хранилище сессий пользователей для сбора 3-х изображений
# Format: {user_id: {'images': [path1, path2, ...], 'state': 'WAITING'}}
user_sessions = {}


async def init_database():
    """Создает таблицы если их нет"""
    try:
        conn = await aiomysql.connect(**DB_CONFIG)
        cursor = await conn.cursor()
        
        # 1. Таблица users (ID + права)
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                rights INT DEFAULT 0 COMMENT '0 = нет прав, 1+ = есть права',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)

        # 2. Таблица telegram_users (инфа от Телеграма)
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS telegram_users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                telegram_user_id BIGINT UNIQUE NOT NULL,
                user_id INT,
                username VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                language_code VARCHAR(10),
                is_bot BOOLEAN,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        await cursor.close()
        conn.close()
        print("База данных инициализирована (users + telegram_users)")
    except Exception as e:
        print(f"Ошибка инициализации БД: {e}")


async def save_user_info(user):
    """Сохраняет информацию о пользователе в БД"""
    try:
        conn = await aiomysql.connect(**DB_CONFIG)
        async with conn.cursor() as cursor:
            # Проверяем, есть ли пользователь в telegram_users
            await cursor.execute("SELECT user_id FROM telegram_users WHERE telegram_user_id = %s", (user.id,))
            exists = await cursor.fetchone()
            
            if exists:
                # Пользователь есть - обновляем инфо
                await cursor.execute("""
                    UPDATE telegram_users 
                    SET username = %s, first_name = %s, last_name = %s, 
                        language_code = %s, is_bot = %s
                    WHERE telegram_user_id = %s
                """, (
                    user.username,
                    user.first_name,
                    user.last_name,
                    user.language_code,
                    user.is_bot,
                    user.id
                ))
            else:
                # Пользователя нет - создаем
                # 1. Создаем запись в users (с rights = 0 по умолчанию)
                await cursor.execute("INSERT INTO users (rights) VALUES (0)")
                internal_user_id = cursor.lastrowid
                
                # 2. Создаем запись в telegram_users
                await cursor.execute("""
                    INSERT INTO telegram_users (telegram_user_id, user_id, username, first_name, last_name, language_code, is_bot)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    user.id,
                    internal_user_id,
                    user.username,
                    user.first_name,
                    user.last_name,
                    user.language_code,
                    user.is_bot
                ))
            
            await conn.commit()
        
        conn.close()
        return True
    except Exception as e:
        print(f"Ошибка сохранения в БД: {e}")
        return False


async def check_user_permission(telegram_user_id: int) -> bool:
    """Проверяет права пользователя напрямую из БД
    
    Args:
        telegram_user_id: ID пользователя Telegram
    
    Returns:
        True если у пользователя есть права (rights > 0), False иначе
    """
    try:
        conn = await aiomysql.connect(**DB_CONFIG)
        async with conn.cursor() as cursor:
            # Получаем user_id из telegram_users и проверяем rights из users
            await cursor.execute("""
                SELECT u.rights 
                FROM telegram_users tg
                JOIN users u ON tg.user_id = u.id
                WHERE tg.telegram_user_id = %s
            """, (telegram_user_id,))
            
            result = await cursor.fetchone()
            if result:
                rights = result[0]
                return rights > 0  # Если rights больше 0, есть права
            
            return False  # Пользователь не найден
        
        conn.close()
    except Exception as e:
        print(f"Ошибка проверки прав: {e}")
        return False


async def download_image(file_id: str, file_path: Path, bot) -> bool:
    """Скачивает изображение по file_id"""
    try:
        file = await bot.get_file(file_id)
        await file.download_to_drive(file_path)
        return True
    except Exception as e:
        print(f"Ошибка скачивания изображения: {e}")
        return False


async def get_image_hash(file_path: Path) -> str:
    """Вычисляет хэш изображения (асинхронно)"""
    sha256_hash = hashlib.sha256()
    async with aiofiles.open(file_path, "rb") as f:
        while True:
            byte_block = await f.read(4096)
            if not byte_block:
                break
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


# Кэш для типов еды из микросервиса переводов
_food_types_cache = None


async def get_food_types_from_translations_service() -> set:
    """Получает список типов еды из микросервиса переводов
    
    Returns:
        set: Множество типов, которые содержат "Food" в названии
    """
    global _food_types_cache
    
    if _food_types_cache is not None:
        return _food_types_cache
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{TRANSLATIONS_SERVICE_URL}/Translations/Alls/V0Get",
                params={"target": "types"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    food_types = set()
                    
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                for key in ['type', 'name', 'category', 'value']:
                                    if key in item:
                                        type_value = str(item[key])
                                        if 'Food' in type_value or 'food' in type_value.lower():
                                            food_types.add(type_value)
                            elif isinstance(item, str):
                                if 'Food' in item or 'food' in item.lower():
                                    food_types.add(item)
                    elif isinstance(data, dict):
                        for key, value in data.items():
                            if isinstance(value, (list, dict)):
                                if isinstance(value, list):
                                    for v in value:
                                        if isinstance(v, dict):
                                            for k in ['type', 'name', 'category', 'value']:
                                                if k in v:
                                                    type_val = str(v[k])
                                                    if 'Food' in type_val or 'food' in type_val.lower():
                                                        food_types.add(type_val)
                                        elif isinstance(v, str):
                                            if 'Food' in v or 'food' in v.lower():
                                                food_types.add(v)
                            elif isinstance(value, str):
                                if 'Food' in value or 'food' in value.lower():
                                    food_types.add(value)
                    
                    _food_types_cache = food_types
                    print(f"Загружено типов еды из микросервиса: {len(food_types)}")
                    return food_types
                else:
                    print(f"Ошибка получения типов из микросервиса переводов: {response.status}")
                    text = await response.text()
                    print(f"Details: {text}")
                    _food_types_cache = set()
                    return set()
    except Exception as e:
        print(f"Ошибка запроса к микросервису переводов: {e}")
        _food_types_cache = set()
        return set()


async def translate_ingredient(ingredient_name: str) -> str:
    """Переводит название ингредиента через микросервис переводов
    
    Args:
        ingredient_name: Название ингредиента на английском
    
    Returns:
        str: Переведенное название или оригинальное, если перевод не удался
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{TRANSLATIONS_SERVICE_URL}/Translations/Alls/V0Get",
                params={"target": "translations", "term": ingredient_name}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if isinstance(data, dict):
                        for key in ['translation', 'translated', 'value', 'text', 'name']:
                            if key in data:
                                translated = str(data[key])
                                if translated and translated != ingredient_name:
                                    return translated
                    elif isinstance(data, list) and len(data) > 0:
                        first_item = data[0]
                        if isinstance(first_item, dict):
                            for key in ['translation', 'translated', 'value', 'text', 'name']:
                                if key in first_item:
                                    translated = str(first_item[key])
                                    if translated and translated != ingredient_name:
                                        return translated
                        elif isinstance(first_item, str):
                            return first_item
                    
                    return ingredient_name
                else:
                    print(f"Ошибка перевода ингредиента '{ingredient_name}': {response.status}")
                    return ingredient_name
    except Exception as e:
        print(f"Ошибка перевода ингредиента '{ingredient_name}': {e}")
        return ingredient_name


async def get_item_type_from_translations_service(item_name: str) -> str:
    """Получает тип объекта из микросервиса переводов по его названию
    
    Args:
        item_name: Название объекта
    
    Returns:
        str: Тип объекта или пустая строка, если не найден
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{TRANSLATIONS_SERVICE_URL}/Translations/Alls/V0Get",
                params={"target": "type", "term": item_name}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data, dict):
                        for key in ['type', 'category', 'value']:
                            if key in data:
                                return str(data[key])
                    elif isinstance(data, list) and len(data) > 0:
                        first_item = data[0]
                        if isinstance(first_item, dict):
                            for key in ['type', 'category', 'value']:
                                if key in first_item:
                                    return str(first_item[key])
                        elif isinstance(first_item, str):
                            return first_item
    except Exception as e:
        print(f"Ошибка получения типа для '{item_name}': {e}")
    
    return ""


async def filter_food_items(results: list) -> list:
    """Фильтрует результаты, оставляя только еду
    
    Проверяет тип объекта через микросервис переводов.
    Исключает все объекты, которые не входят в тип "Foods, Ingredients".
    
    Args:
        results: Список результатов анализа
    
    Returns:
        list: Отфильтрованный список, содержащий только еду
    """
    filtered_results = []
    
    for item in results:
        food_name = item.get('food', 'неизвестно')
        item_type = item.get('type', '')
        
        is_food = False
        
        if item_type:
            if 'Food' in str(item_type) or 'food' in str(item_type).lower():
                is_food = True
        
        if not is_food and food_name:
            item_type_from_service = await get_item_type_from_translations_service(food_name)
            if item_type_from_service:
                if 'Food' in item_type_from_service or 'food' in item_type_from_service.lower():
                    is_food = True
                    item['type'] = item_type_from_service
        
        if not is_food:
            non_food_keywords = ['bowl', 'fork', 'spoon', 'cup', 'knife', 'bottle', 
                                'plate', 'table', 'dining table', 'glass', 'container',
                                'dish', 'utensil', 'cutlery']
            food_name_lower = food_name.lower()
            
            if not any(keyword in food_name_lower for keyword in non_food_keywords):
                is_food = True
        
        if is_food:
            filtered_results.append(item)
        else:
            print(f"Исключен объект (не еда): {food_name} (тип: {item_type})")
    
    return filtered_results


async def send_to_grams_service(image_paths: list) -> dict:
    """Отправляет список изображений на сервис граммовки (Orchestrator)"""
    try:
        async with aiohttp.ClientSession() as session:
            form_data = aiohttp.FormData()
            
            # Добавляем все изображения в форму
            for path in image_paths:
                file_name = path.name
                file_content = open(path, 'rb').read() # Synchronous read for simplicity in form construction, or use aiofiles
                # Note: aiohttp FormData needs synchronous bytes or file-like object mostly, 
                # but better to read async and pass bytes.
                
                # Correct way for async reading:
                async with aiofiles.open(path, 'rb') as f:
                    content = await f.read()
                    form_data.add_field('images', content, filename=file_name, content_type='image/jpeg')
            
            async with session.post(
                f"{GRAMS_SERVICE_URL}/calculate",
                data=form_data
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"Ошибка сервиса граммовки: {response.status}")
                    text = await response.text()
                    print(f"Details: {text}")
                    return {}
    except Exception as e:
        print(f"Ошибка отправки на сервис граммовки: {e}")
        return {}



async def format_analysis_result(modeling_data: dict) -> str:
    """Форматирует результат анализа в нужный формат с переводом ингредиентов"""
    if not modeling_data or 'results' not in modeling_data:
        return "Ошибка: не удалось получить результаты анализа"
    
    results = modeling_data['results']
    
    if not results:
        return "Не найдено объектов еды на изображениях."
    
    total_calories = 0
    total_weight = 0
    
    lines = []
    for item in results:
        food = item.get('food', 'неизвестно')
        # Переводим название ингредиента
        translated_food = await translate_ingredient(food)
        weight = item.get('weight', 0)
        calories = item.get('calories', 0)
        total_calories += calories
        total_weight += weight
        lines.append(f"- {translated_food}: {weight}~ гр. Калорий: {calories}.")
    
    lines.append(f"\nИтого: {total_calories}~ плотности калорий (насыщенность {total_calories} калорий, реальное количество: {total_weight})")
    
    return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    
    await save_user_info(user)
    
    # Создаем клавиатуру с кнопкой "анализ еды"
    keyboard = [
        [InlineKeyboardButton("Анализ еды", callback_data="food_analysis")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Привет, {user.first_name}!\n\nВыберите действие:",
        reply_markup=reply_markup
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == "food_analysis":
        # Проверяем права пользователя
        has_permission = await check_user_permission(user_id)
        if not has_permission:
            await query.edit_message_text("У вас нет прав для использования этой функции.")
            return
        
        await query.edit_message_text(
            "Отправьте 3 изображения еды с разных ракурсов для анализа.\n"
            "Я буду ждать, пока вы отправите все 3 фотографии.\n"
            "Поддерживаются форматы: JPG, PNG."
        )
        
        # Инициализируем сессию пользователя
        user_sessions[user_id] = {
            'images': [],
            'state': 'WAITING_IMAGES'
        }


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик изображений для анализа еды"""
    user = update.effective_user
    user_id = user.id
    
    # Проверяем права
    has_permission = await check_user_permission(user_id)
    if not has_permission:
        await update.message.reply_text("У вас нет прав для использования этой функции.")
        return
    
    # Проверяем или инициализируем сессию
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            'images': [],
            'state': 'WAITING_IMAGES'
        }
        await update.message.reply_text(
            "Начинаем новый анализ. Пожалуйста, отправьте 3 фотографии еды с разных ракурсов."
        )

    session = user_sessions[user_id]
    
    # Получаем изображение (может быть Photo или Document)
    file_id = None
    file_name = None
    
    if update.message.photo:
        # Изображение отправлено как фото
        photo = update.message.photo[-1]  # Берем самое большое разрешение
        file_id = photo.file_id
        file_name = f"{file_id}.jpg"
    elif update.message.document:
        # Изображение отправлено как файл
        document = update.message.document
        mime_type = document.mime_type or ""
        # Проверяем, что это изображение
        if mime_type.startswith('image/'):
            file_id = document.file_id
            # Определяем расширение из mime_type или имени файла
            if document.file_name:
                file_name = document.file_name
            else:
                ext = 'jpg'
                if 'png' in mime_type:
                    ext = 'png'
                elif 'gif' in mime_type:
                    ext = 'gif'
                elif 'webp' in mime_type:
                    ext = 'webp'
                file_name = f"{file_id}.{ext}"
        else:
            await update.message.reply_text("Пожалуйста, отправьте изображение (JPG, PNG и т.д.)")
            return
    else:
        await update.message.reply_text("Пожалуйста, отправьте изображение.")
        return
    
    # Скачиваем и сохраняем изображение
    try:
        temp_image_path = IMAGES_DIR / file_name
        
        # Скачиваем изображение
        downloaded = await download_image(file_id, temp_image_path, context.bot)
        if not downloaded:
            await update.message.reply_text("Ошибка при скачивании изображения.")
            return
        
        # Добавляем путь к изображению в сессию
        session['images'].append(temp_image_path)
        
        images_count = len(session['images'])
        
        if images_count < 3:
            await update.message.reply_text(f"Получено {images_count} из 3 изображений. Отправьте еще {3 - images_count}.")
            return
            
        # Если получено 3 изображения, начинаем обработку
        await update.message.reply_text("Все изображения получены. Начинаю обработку...")
        
        # Отправляем сообщение о начале обработки
        processing_msg = await update.message.reply_text("Анализ изображений и расчет граммов...")
        
        # Отправляем все фото сразу в сервис граммовки
        final_result = await send_to_grams_service(session['images'])
        
        if not final_result:
            await processing_msg.edit_text("Не удалось проанализировать изображения.")
            del user_sessions[user_id]
            return

        # Фильтруем результаты - оставляем только еду
        if 'results' in final_result:
            filtered_results = await filter_food_items(final_result['results'])
            final_result['results'] = filtered_results

        # Форматируем и отправляем результат (с переводом ингредиентов)
        result_text = await format_analysis_result(final_result)
        await processing_msg.edit_text(result_text)
        
        # Очищаем сессию
        del user_sessions[user_id]
        
    except Exception as e:
        print(f"Ошибка обработки: {e}")
        await update.message.reply_text(f"Произошла ошибка: {str(e)}")
        # Сбрасываем сессию при ошибке
        if user_id in user_sessions:
            del user_sessions[user_id]


async def post_init(application: Application):
    """Выполняется после инициализации приложения, но перед началом poling'а"""
    await init_database()


def main():
    """Запуск бота"""
    if BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("Ошибка: Укажите BOT_TOKEN в файле .env")
        return
    
    # Используем post_init для инициализации БД внутри цикла событий PTB
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    
    # Обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Обработчик изображений (фото и документы с изображениями)
    # Используем комбинированный фильтр для фото и документов-изображений
    # filters.Document.IMAGE уже проверяет основные типы изображений
    image_filter = filters.PHOTO | filters.Document.IMAGE
    
    application.add_handler(MessageHandler(
        image_filter,
        handle_image
    ))
    
    print("Бот запущен...")
    application.run_polling()


if __name__ == '__main__':
    main()
