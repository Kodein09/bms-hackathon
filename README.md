# BMS Hackathon 2026 — C&C Culture and Code

Внутренний мини-хакатон по улучшению продукта **BMS**  
**Даты:** 20–21 августа 2026

## Команда

| Участник | Роль |
|----------|------|
| Вильям | Frontend |
| Рой | Backend |
| Ерасыл | DevOps |

## Текущий статус

- [x] Frontend (Dashboard, Hiring, Profile, Messenger, IAM)
- [ ] Backend
- [ ] Docker Compose
- [ ] Интеграция Frontend ↔ Backend

## Структура
bms-hackathon/
├── frontend/
│   ├── index.html
│   ├── exchange.html
│   ├── my.html
│   ├── messenger.html
│   ├── iam.html
│   ├── js/theme.js
│   └── Dockerfile
├── .gitignore
└── README.md
text## Запуск Frontend

```bash
cd frontend
# Просто открыть index.html в браузере
# или через Docker:
docker build -t bms-frontend .
docker run -p 8080:80 bms-frontend
text**2. Всё остальное выглядит нормально** по размеру и по концам файлов.

## Запуск Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Для автоматических тестов:

```bash
pip install -r requirements-dev.txt
pytest -q
```

После запуска:

- Health check: http://127.0.0.1:8000/health
- Swagger: http://127.0.0.1:8000/docs
- Регистрация: `POST /api/v1/auth/register`
- Login в Swagger использует OAuth2 form-поля `username` и `password`: `POST /api/v1/auth/login`
- Обновление токена: `POST /api/v1/auth/refresh`

Уведомления:

- Список: `GET /api/v1/notifications/?skip=0&limit=20&unread_only=false`
- Непрочитанные: `GET /api/v1/notifications/unread-count`
- Прочитать одно: `PUT /api/v1/notifications/{id}/read`
- Прочитать все: `PUT /api/v1/notifications/read-all`
- Удалить: `DELETE /api/v1/notifications/{id}`
- Создать системное уведомление: `POST /api/v1/notifications/`
- WebSocket: `ws://127.0.0.1:8000/ws/notifications/{user_id}?token=<access_token>`

Пример тела системного уведомления:

```json
{
	"user_id": "uuid-пользователя",
	"title": "Документ обработан",
	"message": "Ваш документ готов к просмотру.",
	"type": "success"
}
```

Документы:

- Загрузка нескольких файлов: `POST /api/v1/documents/upload`
- Список с фильтрами: `GET /api/v1/documents/?status=pending&direction=outgoing&skip=0&limit=20&sort_by=created_at&sort_order=desc`
- Информация: `GET /api/v1/documents/{id}/info`
- Скачать: `GET /api/v1/documents/{id}`
- Мягкое удаление: `DELETE /api/v1/documents/{id}`
- Изменить статус: `PUT /api/v1/documents/{id}/status`

Для MIME-проверки на macOS нужен системный `libmagic`:

```bash
brew install libmagic
```

В upload можно отправлять поля `files` повторно для multiple upload. Поддерживаются изображения, документы, архивы, видео, аудио, тексты и исходный код из whitelist в `app/core/file_validation.py`.

---