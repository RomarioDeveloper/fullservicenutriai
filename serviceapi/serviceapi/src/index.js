require('dotenv').config();
const express = require('express');
const cors = require('cors');
const permissionsRoutes = require('./routes/permissions');
const UserService = require('./services/UserService');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.use('/permissions', permissionsRoutes);

app.get('/health', (req, res) => {
  res.json({ status: 'ok', message: 'Service is running' });
});

app.use((req, res) => {
  res.status(404).json({
    error: 'Not Found',
    message: 'Маршрут не найден'
  });
});

app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({
    error: 'Internal server error',
    message: err.message
  });
});

// Инициализация БД и запуск сервера
UserService.initDatabase().then(() => {
  app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
  });
});

module.exports = app;
