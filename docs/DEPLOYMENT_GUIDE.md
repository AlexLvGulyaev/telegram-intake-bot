# 🚀 Telegram Intake Bot · DEPLOYMENT_GUIDE

**Проект:** telegram-intake-bot  
**Дата:** 2026-08-09  
**Статус:** as-built

---

## 🎯 1. Назначение

Единый Source of Truth для воспроизведения работоспособного экземпляра Telegram Intake Bot в чистом окружении. Если после выполнения руководства система не работает, руководство устарело.

Руководство рассчитано на технически подготовленного пользователя, знакомого с Docker и Linux.

---

## 📚 2. Связанные документы

- [🏠 `README.md`](../README.md) — главная страница проекта и быстрый старт.
- [🏗️ `docs/ARCHITECTURE.md`](ARCHITECTURE.md) — архитектура системы.
- [📖 `docs/USER_GUIDE.md`](USER_GUIDE.md) — как пользоваться ботом.
- [🎛️ `docs/OPERATOR_GUIDE.md`](OPERATOR_GUIDE.md) — как работать с заявками в чате операторов.
- [🧪 `docs/TESTING.md`](TESTING.md) — результаты проверки и E2E-прогонов.
- [🔐 `docs/SECURITY_NOTES.md`](SECURITY_NOTES.md) — рекомендации по безопасности.

---

## 🛠️ 3. Варианты развёртывания

| Вариант | Когда использовать | Требования |
|---|---|---|
| **Локальный запуск** | Разработка, локальное тестирование | Docker |
| **Production на VPS** | Публичный бот для клиентов | VPS, Docker, SSH |

> **Важно:** все примеры токенов, ключей и ID в этом документе — плейсхолдеры. Никогда не используйте значения из примеров в production.

---

## 📋 4. Требования

- VPS с Ubuntu/Debian (рекомендуется 1 CPU, 1 GB RAM, 10 GB SSD).
- Docker установлен на сервере.
- Доступ по SSH.
- Созданный Telegram-бот и группа/канал для операторов.
- OpenAI API key.

---

## 🔧 5. Переменные окружения

Создать файл `.env` на сервере:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
OPERATOR_CHAT_ID=-1001234567890
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4.1-mini
OPENAI_BASE_URL=https://api.openai.com/v1
LOG_LEVEL=INFO
```

### Как получить переменные

- `TELEGRAM_BOT_TOKEN` — от [@BotFather](https://t.me/botfather).
- `OPERATOR_CHAT_ID`:
  1. Добавьте бота в группу операторов.
  2. Отправьте любое сообщение в группу.
  3. Выполните:
     ```bash
     curl -s "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getUpdates" | jq '.result[-1].message.chat.id'
     ```
- `OPENAI_API_KEY` — из личного кабинета OpenAI.
- `OPENAI_MODEL` — модель OpenAI (по умолчанию `gpt-4.1-mini`).
- `OPENAI_BASE_URL` — базовый URL API (по умолчанию `https://api.openai.com/v1`).
- `LOG_LEVEL` — уровень логирования: `DEBUG`, `INFO`, `WARNING`, `ERROR` (по умолчанию `INFO`, опционально).
- `SESSION_STORAGE_TYPE` — `memory` (по умолчанию) или `postgres`.
- `DATABASE_URL` — требуется только для `postgres`, например `postgresql://tib_user:tib_password@your-db-host:5432/tib_db`.

---

## ▶️ 6. Вариант 1 · Локальный запуск

Локальный запуск не требует VPS. Используется для разработки и ручного тестирования.

```bash
# клонировать репозиторий
git clone https://github.com/YOUR_USERNAME/telegram-intake-bot.git
cd telegram-intake-bot

# подготовить .env
cp .env.example .env
# отредактировать .env

# собрать и запустить
docker build -t telegram-intake-bot .
docker run -d --name telegram-intake-bot --env-file .env --restart unless-stopped telegram-intake-bot
```

---

## 🚀 7. Вариант 2 · Production на VPS

### 7.1. Подключиться к серверу

```bash
ssh root@YOUR_VPS_IP
```

### 7.2. Установить Docker

```bash
apt-get update
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### 7.3. Склонировать репозиторий

```bash
cd /opt
git clone https://github.com/YOUR_USERNAME/telegram-intake-bot.git
cd telegram-intake-bot
```

### 7.4. Создать файл окружения

```bash
cp .env.example .env
nano .env
# заполнить все переменные
# Ctrl+O, Enter, Ctrl+X
```

**По умолчанию** сессии хранятся в памяти (`SESSION_STORAGE_TYPE=memory`).
Для PostgreSQL персистентности:

```bash
SESSION_STORAGE_TYPE=postgres
DATABASE_URL=postgresql://tib_user:tib_password@your-db-host:5432/tib_db
```

Пересобрать образ не требуется — `asyncpg` уже входит в базовые зависимости (`requirements.txt`).

Создать пользователя, базу и таблицу (пример для уже установленного Postgres):

```bash
psql -U postgres -c "CREATE DATABASE tib_db;"
psql -U postgres -c "CREATE USER tib_user WITH PASSWORD 'tib_password'; GRANT ALL PRIVILEGES ON DATABASE tib_db TO tib_user; ALTER DATABASE tib_db OWNER TO tib_user;"
psql "$DATABASE_URL" -f docs/schema.sql
```

### 7.5. Собрать и запустить контейнер

```bash
docker build -t telegram-intake-bot .
docker run -d --name telegram-intake-bot --env-file .env --restart unless-stopped telegram-intake-bot
```

### 7.6. Проверить статус

```bash
docker ps
docker logs -f telegram-intake-bot
```

### 7.7. Проверить работу бота

- Написать боту `/start`.
- Выбрать сценарий: `1` — техподдержка, `2` — заявка для продаж.
- Пройти диалог до финального сообщения.
- Убедиться, что заявка пришла в указанный чат операторов.

---

## 🔄 8. Обновление

```bash
cd /opt/telegram-intake-bot
git pull
docker build -t telegram-intake-bot .
docker stop telegram-intake-bot
docker rm telegram-intake-bot
docker run -d --name telegram-intake-bot --env-file .env --restart unless-stopped telegram-intake-bot
```

---

## 🚨 9. Устранение неполадок

| Симптом | Причина | Решение |
|---------|---------|---------|
| Бот не отвечает | Неверный `TELEGRAM_BOT_TOKEN` | Проверить токен в `.env`, пересоздать контейнер |
| Заявка не приходит в чат | Неверный `OPERATOR_CHAT_ID` или бот не в группе | Проверить ID, добавить бота в группу, дать права на отправку сообщений |
| Ошибки LLM | Неверный `OPENAI_API_KEY` или недоступен API | Проверить ключ и баланс, проверить `OPENAI_BASE_URL` |
| Контейнер падает | Ошибка в `.env` или коде | Смотреть `docker logs telegram-intake-bot` |
| Сброс диалога после restart | `SESSION_STORAGE_TYPE=memory` | Перейти на `postgres` и `DATABASE_URL`; см. раздел 7.4 |
| `DATABASE_URL is required` | `SESSION_STORAGE_TYPE=postgres` без `DATABASE_URL` | Добавить корректный `DATABASE_URL` в `.env` |
| Ошибка подключения к Postgres | Неверный хост/порт/пользователь или отсутствует таблица | Проверить сетевой доступ, учётные данные и применить `docs/schema.sql` |

---

## ↩️ 10. Откат

Если обновление или изменение конфигурации привело к неработоспособности бота:

```bash
docker stop telegram-intake-bot
docker rm telegram-intake-bot
# восстановить предыдущий рабочий .env или предыдущую версию кода через git
git log --oneline -5
git checkout <предыдущий_коммит>
# пересобрать и запустить
docker build -t telegram-intake-bot .
docker run -d --name telegram-intake-bot --env-file .env --restart unless-stopped telegram-intake-bot
```

---

## 🧪 11. Проверка после развёртывания (smoke test)

1. Проверить логи старта:
   ```bash
   docker logs -f telegram-intake-bot
   ```
2. Убедиться, что бот отвечает на `/start`.
3. Пройти оба сценария до получения финального сообщения.
4. Проверить, что заявка пришла в указанный `OPERATOR_CHAT_ID`.

---

## 🔐 12. Безопасность

- `.env` не коммитить в репозиторий.
- API keys хранить только на сервере.
- Для продакшена использовать постоянное хранилище и ограничить доступ к серверу.

---

## 📚 Связанные документы

- [🏠 `README.md`](../README.md) — главная страница проекта.
- [🏗️ `docs/ARCHITECTURE.md`](ARCHITECTURE.md) — архитектура системы.
- [📖 `docs/USER_GUIDE.md`](USER_GUIDE.md) — как пользоваться ботом.
- [🎛️ `docs/OPERATOR_GUIDE.md`](OPERATOR_GUIDE.md) — как работать с заявками в чате операторов.
- [🧪 `docs/TESTING.md`](TESTING.md) — результаты проверки и E2E-прогонов.
- [🔐 `docs/SECURITY_NOTES.md`](SECURITY_NOTES.md) — рекомендации по безопасности.
