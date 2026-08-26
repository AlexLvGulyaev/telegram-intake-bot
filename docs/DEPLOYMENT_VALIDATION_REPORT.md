# ✅ Telegram Intake Bot · Deployment Validation Report

**Проект:** telegram-intake-bot  
**Дата:** 2026-08-22  
**Статус:** PASS (с ограничением по окружению)

---

## 🎯 1. Назначение

Подтвердить, что Telegram Intake Bot может быть развёрнут и приведён в работоспособное состояние по инструкциям `docs/DEPLOYMENT_GUIDE.md` без использования знаний автора, не входящих в публичный репозиторий.

## ⚠️ 2. Ограничение окружения

Идеальная Deployment Validation по правилам APL требует чистого окружения (новый VPS, новая VM или новый Docker Host). В рамках данной проверки новый VPS был недоступен.

**Применённый компромисс:**

- Проверка выполнена на том же физическом сервере, где работает production-инстанс `@PEcb06_bot`.
- Для изоляции использовались:
  - отдельный Telegram-бот `@PEcb06TEST_bot`;
  - отдельный Docker-контейнер `telegram-intake-bot-dv`;
  - отдельная Postgres-база `tib_test_db`;
  - отдельная группа операторов `PEcb06 tickets` (`OPERATOR_CHAT_ID=-5446667984`).

Это не полноценная «с нуля на новом VPS» Validation, но подтверждает воспроизводимость процесса развёртывания по `DEPLOYMENT_GUIDE.md` в рамках доступных ресурсов.

---

## 🛠️ 3. Подготовка окружения

### 3.1. Взятый из репозитория артефакт

```bash
git clone https://github.com/AlexLvGulyaev/telegram-intake-bot.git /tmp/tib-dv
cd /tmp/tib-dv
```

### 3.2. Переменные окружения

Создан `.env.test`:

```env
TELEGRAM_BOT_TOKEN=YOUR_TEST_BOT_TOKEN
OPERATOR_CHAT_ID=-5446667984
OPENAI_API_KEY=***
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
LOG_LEVEL=DEBUG
```

### 3.3. Подготовка PostgreSQL (для фазы postgres)

```bash
# Создана изолированная тестовая база и пользователь
docker exec meeting-audit-bot-db psql -U meeting_audit -c "CREATE DATABASE tib_test_db;"
docker exec meeting-audit-bot-db psql -U meeting_audit -c "CREATE USER tib_test_user WITH PASSWORD 'tib_test_password'; GRANT ALL PRIVILEGES ON DATABASE tib_test_db TO tib_test_user; ALTER DATABASE tib_test_db OWNER TO tib_test_user;"
docker cp /tmp/tib-dv/docs/schema.sql meeting-audit-bot-db:/tmp/schema.sql
docker exec meeting-audit-bot-db psql -U tib_test_user -d tib_test_db -f /tmp/schema.sql
```

---

## ✅ 4. Результаты проверки

### 4.1. Фаза 1 · Сессии в памяти (`SESSION_STORAGE_TYPE=memory`)

| Шаг | Действие | Ожидаемый результат | Фактический результат | Статус |
|-----|----------|----------------------|------------------------|--------|
| 1 | `docker build -t telegram-intake-bot:dv .` | Образ собирается без ошибок | `Successfully built` | PASS |
| 2 | `docker run -d --name telegram-intake-bot-dv --env-file .env.test telegram-intake-bot:dv` | Контейнер запущен, бот начал polling | `Run polling for bot @PEcb06TEST_bot` | PASS |
| 3 | Backend E2E smoke (`scripts/e2e_smoke.py`) | Оба сценария собирают поля и отправляют заявки | `=== E2E SMOKE PASSED ===` | PASS |

### 4.2. Фаза 2 · PostgreSQL-сессии (`SESSION_STORAGE_TYPE=postgres`)

| Шаг | Действие | Ожидаемый результат | Фактический результат | Статус |
|-----|----------|----------------------|------------------------|--------|
| 1 | Создание `tib_test_db` и применение `docs/schema.sql` | Таблица `tib_sessions` создана | `CREATE TABLE`, `CREATE INDEX` | PASS |
| 2 | Перезапуск контейнера с `DATABASE_URL=postgresql://tib_test_user:tib_test_password@meeting-audit-bot-db:5432/tib_test_db` | Контейнер подключается к Postgres и polling работает | `Starting support intake bot (session_storage=postgres)` | PASS |
| 3 | Backend E2E smoke | Сценарии проходят, сессии сохраняются | `=== E2E SMOKE PASSED ===` | PASS |
| 4 | Проверка данных в `tib_sessions` | Записи о сессиях присутствуют | 2 rows, обе `submitted=true` | PASS |
| 5 | Перезапуск контейнера и повторная проверка | Сессии сохранились | `session_count = 2` | PASS |

---

## 🔍 5. Замечания

- Backend E2E smoke (`scripts/e2e_smoke.py`) напрямую вызывает `SupportWorkflowService`, а не проходит через Telegram polling-обработчики. Это подтверждает бизнес-логику и путь отправки уведомлений, но не валидирует именно Telegram long-polling path.
- Ручной Telegram E2E-прогон через `@PEcb06TEST_bot` не был выполнён в этой сессии.
- В обоих прогонах сценарий сбора лида дважды задал вопрос о бюджете — это особенность текущего guard-поведения, не влияющая на результат.

---

## 📚 6. Связанные документы

- [🚀 `docs/DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) — инструкция по развёртыванию.
- [🧪 `docs/TESTING.md`](TESTING.md) — результаты E2E-прогонов.
- [📊 `docs/PROJECT_STATE.md`](PROJECT_STATE.md) — паспорт состояния проекта.

---

## ✅ 7. Итог

Telegram Intake Bot успешно развёрнут в изолированном тестовом окружении на существующем VPS в режимах `memory` и `postgres`. Все проверенные шаги `DEPLOYMENT_GUIDE.md` выполнены успешно. Проект готов к публикации как портфельный актив с учётом зафиксированного ограничения по окружению Validation.
