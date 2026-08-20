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

---