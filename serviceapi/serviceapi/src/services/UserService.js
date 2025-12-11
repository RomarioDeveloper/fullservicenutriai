const pool = require('../config/db');

class UserService {
  static async initDatabase() {
    try {
      const connection = await pool.getConnection();
      
      // Проверяем, что таблицы users уже существует (ее создает бот)
      // Сервис прав НИЧЕГО не создает, только читает
      
      connection.release();
      console.log('Сервис прав готов к работе (использует таблицы users и telegram_users из базы бота)');
    } catch (error) {
      console.error('Ошибка подключения к БД:', error);
    }
  }

  // Получает права пользователя по его ID
  static async getUserRights(userId) {
    try {
      const [rows] = await pool.query('SELECT rights FROM users WHERE id = ?', [userId]);
      if (rows.length === 0) return null;
      
      return rows[0].rights;
    } catch (error) {
      console.error('Ошибка получения прав пользователя:', error);
      return null;
    }
  }

  // Устанавливает права пользователю
  static async setUserRights(userId, rights) {
    try {
      await pool.query('UPDATE users SET rights = ? WHERE id = ?', [rights, userId]);
      return true;
    } catch (error) {
      console.error('Ошибка установки прав:', error);
      return false;
    }
  }

  // Получает список всех пользователей с их правами
  static async getAllUsers() {
    try {
      const [rows] = await pool.query(`
        SELECT u.id, u.rights, tg.telegram_user_id, tg.username, tg.first_name, tg.last_name
        FROM users u
        LEFT JOIN telegram_users tg ON u.id = tg.user_id
      `);
      
      return rows.map(row => ({
        userId: row.id,
        rights: row.rights,
        telegramUserId: row.telegram_user_id,
        username: row.username,
        firstName: row.first_name,
        lastName: row.last_name
      }));
    } catch (error) {
      console.error('Ошибка получения списка пользователей:', error);
      return [];
    }
  }

  // Получает пользователя по Telegram ID
  static async getUserByTelegramId(telegramUserId) {
    try {
      const [rows] = await pool.query(`
        SELECT u.id, u.rights, tg.username, tg.first_name
        FROM telegram_users tg
        JOIN users u ON tg.user_id = u.id
        WHERE tg.telegram_user_id = ?
      `, [telegramUserId]);
      
      if (rows.length === 0) return null;
      
      return {
        userId: rows[0].id,
        rights: rows[0].rights,
        username: rows[0].username,
        firstName: rows[0].first_name
      };
    } catch (error) {
      console.error('Ошибка поиска пользователя по Telegram ID:', error);
      return null;
    }
  }
}

module.exports = UserService;
