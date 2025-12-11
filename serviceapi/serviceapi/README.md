# Микросервис управления правами доступа

Микросервис для управления правами доступа на основе Express.js. Прототип без подключения к базе данных.

## Структура проекта

```
serviceapi/
├── src/
│   ├── index.js                    # Главный файл приложения
│   ├── models/                     # Модели данных
│   │   ├── Token.js               # Модель токена
│   │   ├── User.js                 # Модель пользователя
│   │   └── Permission.js           # Модель прав и категорий прав
│   ├── services/                   # Бизнес-логика
│   │   ├── TokenService.js         # Сервис работы с токенами
│   │   ├── UserService.js          # Сервис работы с пользователями
│   │   ├── PermissionService.js    # Сервис работы с правами
│   │   └── PermissionManagerService.js  # Основной сервис управления правами
│   └── routes/
│       └── permissions.js          # Маршруты API
├── package.json
└── README.md
```

## API Endpoints

### POST /permissions/sets/V0Post
Установка прав пользователям (замена существующих прав).

**Request Body:**
```json
{
  "token": "Токен с правами",
  "categories": [1, 2],
  "indexes": [10, 20],
  "permissions_values": [1, 2, 3]
}
```

### POST /permissions/adds/V0Post
Добавление прав пользователям.

**Request Body:**
```json
{
  "token": "Токен с правами",
  "categories": [1, 2],
  "indexes": [10, 20],
  "permissions_values": [1, 2, 3]
}
```

### POST /permissions/removes/V0Post
Удаление прав у пользователей.

**Request Body:**
```json
{
  "token": "Токен с правами",
  "categories": [1, 2],
  "indexes": [10, 20],
  "permissions_values": [1, 2, 3]
}
```

### GET /permissions/lists/V0Get
Получение списка прав пользователей.

**Query Parameters:**
- `token` (required) - Токен с правами
- `categories` (optional) - Индексы категорий (через запятую)
- `indexes` (optional) - Индексы указанной категории (через запятую)

**Example:**
```
GET /permissions/lists/V0Get?token=abc123&categories=1,2&indexes=10,20
```

## Установка и запуск

1. Установите зависимости:
```bash
npm install
```

2. Запустите сервер:
```bash
npm start
```

Для разработки с автоперезагрузкой:
```bash
npm run dev
```

Сервер запустится на порту 3000 (или порту, указанному в переменной окружения PORT).

## Тестирование

### Примеры запросов для Postman

Смотрите файл `POSTMAN_EXAMPLES.md` для подробных примеров всех запросов.

Или импортируйте готовую коллекцию Postman из файла `postman_collection.json`:
1. Откройте Postman
2. Нажмите Import
3. Выберите файл `postman_collection.json`

### Быстрый тест через curl:

```bash
# Health check
curl http://localhost:3000/health

# Установка прав
curl -X POST http://localhost:3000/permissions/sets/V0Post \
  -H "Content-Type: application/json" \
  -d '{
    "token": "admin_token_123",
    "categories": [1],
    "indexes": [10],
    "permissions_values": [1, 2, 3, 4]
  }'

# Получение списка прав
curl "http://localhost:3000/permissions/lists/V0Get?token=admin_token_123&categories=1&indexes=10"
```

## Особенности прототипа

- Данные хранятся в памяти (Map) и не сохраняются между перезапусками
- Валидация входных данных
- Обработка ошибок
- Логика работы с правами согласно схеме:
  - Если список пользователей пуст, возвращаются все допустимые права для выдачи и отнятия исходя из прав токена
  - Права фильтруются на основе прав токена

## Следующие шаги для доработки

1. Подключение MySQL базы данных
2. Создание таблиц для tokens, users, permissions и их категорий
3. Миграция логики хранения данных из памяти в БД
4. Добавление аутентификации и авторизации
5. Добавление логирования
6. Добавление тестов

