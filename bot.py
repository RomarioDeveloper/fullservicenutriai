import os
import mysql.connector
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'telegram_bot')
}

BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')


def init_database():
    """Создает таблицу если её нет"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT UNIQUE NOT NULL,
                username VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                language_code VARCHAR(10),
                is_bot BOOLEAN,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
        print("База данных инициализирована")
    except Exception as e:
        print(f"Ошибка инициализации БД: {e}")


def save_user_info(user):
    """Сохраняет информацию о пользователе в БД"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user.id,))
        exists = cursor.fetchone()
        
        if exists:
            cursor.execute("""
                UPDATE users 
                SET username = %s, first_name = %s, last_name = %s, 
                    language_code = %s, is_bot = %s
                WHERE user_id = %s
            """, (
                user.username,
                user.first_name,
                user.last_name,
                user.language_code,
                user.is_bot,
                user.id
            ))
        else:
            cursor.execute("""
                INSERT INTO users (user_id, username, first_name, last_name, language_code, is_bot)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                user.id,
                user.username,
                user.first_name,
                user.last_name,
                user.language_code,
                user.is_bot
            ))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Ошибка сохранения в БД: {e}")
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    
    save_user_info(user)
    
    await update.message.reply_text(f"Привет, {user.first_name}!")


def main():
    """Запуск бота"""
    if BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("Ошибка: Укажите BOT_TOKEN в файле .env")
        return
    
    init_database()
    
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    
    print("Бот запущен...")
    application.run_polling()


if __name__ == '__main__':
    main()

