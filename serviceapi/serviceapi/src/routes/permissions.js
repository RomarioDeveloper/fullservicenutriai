const express = require('express');
const router = express.Router();
const UserService = require('../services/UserService');
const TokenService = require('../services/TokenService');

const validateToken = (req, res, next) => {
  const token = req.body?.token || req.query?.token;
  if (!token) {
    return res.status(400).json({
      error: 'Token is required',
      message: 'Токен обязателен для выполнения запроса'
    });
  }
  if (!TokenService.isValidToken(token)) {
    return res.status(401).json({
      error: 'Invalid token',
      message: 'Токен недействителен или не найден'
    });
  }
  next();
};

// Получить список всех пользователей
router.get('/users/list', validateToken, async (req, res) => {
  try {
    const users = await UserService.getAllUsers();
    res.json({
      success: true,
      data: { users }
    });
  } catch (error) {
    console.error('Error in /permissions/users/list:', error);
    res.status(500).json({
      error: 'Internal server error',
      message: error.message
    });
  }
});

// Получить права конкретного пользователя по его ID
router.get('/users/:userId/rights', validateToken, async (req, res) => {
  try {
    const userId = parseInt(req.params.userId);
    const rights = await UserService.getUserRights(userId);
    
    if (rights === null) {
      return res.status(404).json({
        error: 'User not found',
        message: 'Пользователь не найден'
      });
    }
    
    res.json({
      success: true,
      data: { userId, rights, hasRights: rights > 0 }
    });
  } catch (error) {
    console.error('Error in /permissions/users/:userId/rights:', error);
    res.status(500).json({
      error: 'Internal server error',
      message: error.message
    });
  }
});

// Установить права пользователю
router.post('/users/:userId/rights', validateToken, async (req, res) => {
  try {
    const userId = parseInt(req.params.userId);
    const { rights } = req.body;
    
    if (typeof rights !== 'number') {
      return res.status(400).json({
        error: 'Invalid rights value',
        message: 'rights должен быть числом'
      });
    }
    
    const success = await UserService.setUserRights(userId, rights);
    
    if (!success) {
      return res.status(500).json({
        error: 'Failed to update rights',
        message: 'Не удалось обновить права'
      });
    }
    
    res.json({
      success: true,
      data: { userId, rights }
    });
  } catch (error) {
    console.error('Error in /permissions/users/:userId/rights:', error);
    res.status(500).json({
      error: 'Internal server error',
      message: error.message
    });
  }
});

// Проверить права по Telegram ID (для удобства)
router.get('/check/:telegramUserId', validateToken, async (req, res) => {
  try {
    const telegramUserId = parseInt(req.params.telegramUserId);
    const user = await UserService.getUserByTelegramId(telegramUserId);
    
    if (!user) {
      return res.status(404).json({
        error: 'User not found',
        message: 'Пользователь не найден'
      });
    }
    
    res.json({
      success: true,
      data: {
        ...user,
        hasRights: user.rights > 0
      }
    });
  } catch (error) {
    console.error('Error in /permissions/check/:telegramUserId:', error);
    res.status(500).json({
      error: 'Internal server error',
      message: error.message
    });
  }
});

module.exports = router;
