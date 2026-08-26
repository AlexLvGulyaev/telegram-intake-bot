# 🔌 Telegram Intake Bot · API_CONTRACT

**Проект:** telegram-intake-bot  
**Дата:** 2026-08-09  
**Статус:** as-built

---

## 🎯 1. Назначение

Этот документ описывает внешние и внутренние контракты Telegram Intake Bot.

---

## 🌐 2. Внешние интеграции

Бот взаимодействует с двумя внешними системами:

1. **Telegram Bot API** — получение сообщений и отправка заявок.
2. **OpenAI API** — генерация ответа и извлечение полей заявки.

> 📌 **SOT:** официальная документация внешних систем является единственным источником истины для их API. Контракты ниже описывают фактическое использование в проекте и ссылаются на официальные документы.

---

## 🤖 3. Telegram Bot API

### 3.1. Source of Truth

- **Документация:** https://core.telegram.org/bots/api
- **Библиотека:** https://docs.aiogram.dev/en/latest/
- **Создание бота:** https://t.me/botfather

### 3.2. Получение сообщений

Бот использует long polling через aiogram 3.x.

```python
from aiogram import Bot, Dispatcher

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
```

### 3.3. Отправка сообщений

Заявка отправляется через `send_message`:

```python
await bot.send_message(
    chat_id=OPERATOR_CHAT_ID,
    text=rendered_ticket_text,
)
```

### 3.4. Требования к боту

- Бот создан через [@BotFather](https://t.me/botfather).
- Бот добавлен в группу/канал операторов.
- У бота есть право на отправку сообщений в группе.

### 3.5. Пример получения `OPERATOR_CHAT_ID`

1. Добавьте бота в группу операторов.
2. Отправьте в группу сообщение от лица бота или любое сообщение.
3. Используйте запрос:

```bash
curl -s "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getUpdates" | jq '.result[-1].message.chat.id'
```

Для супергрупп ID обычно начинается с `-100`.

---

## 🧠 4. OpenAI API

### 4.1. Source of Truth

- **OpenAI API Reference:** https://platform.openai.com/docs/api-reference
- **Chat Completions:** https://platform.openai.com/docs/api-reference/chat/create
- **Structured Outputs / JSON Schema:** https://platform.openai.com/docs/guides/structured-outputs

### 4.2. Endpoint

```text
POST {OPENAI_BASE_URL}/chat/completions
```

По умолчанию `OPENAI_BASE_URL=https://api.openai.com/v1`.

Модель по умолчанию в проекте — `gpt-4.1-mini`. Актуальные версии моделей и возможности см. в официальной документации OpenAI.

### 4.3. Заголовки

```http
Authorization: Bearer <OPENAI_API_KEY>
Content-Type: application/json
```

### 4.4. Request body

```json
{
  "model": "gpt-4.1-mini",
  "temperature": 0.2,
  "messages": [
    {
      "role": "system",
      "content": "<system prompt для выбранного сценария>"
    },
    {
      "role": "user",
      "content": "is_new_session: false\ncurrent_ticket:\n{...}\ncurrent_lead:\n{...}\nconversation_history:\n[...]\nlast_assistant_message:\n...\nlatest_user_message:\n..."
    }
  ],
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "assistant_turn",
      "strict": true,
      "schema": { ... }
    }
  }
}
```

### 4.5. Response format (JSON Schema)

```json
{
  "name": "assistant_turn",
  "strict": true,
  "schema": {
    "type": "object",
    "properties": {
      "reply": { "type": "string" },
      "extracted_ticket": {
        "type": "object",
        "properties": {
          "name": { "type": ["string", "null"] },
          "contact": { "type": ["string", "null"] },
          "problem_summary": { "type": ["string", "null"] },
          "occurred_at": { "type": ["string", "null"] },
          "location": { "type": ["string", "null"] },
          "priority": {
            "type": ["string", "null"],
            "enum": ["срочно", "средне", "низкий приоритет", null]
          }
        },
        "required": ["name", "contact", "problem_summary", "occurred_at", "location", "priority"],
        "additionalProperties": false
      },
      "extracted_lead": {
        "type": "object",
        "properties": {
          "name": { "type": ["string", "null"] },
          "contact": { "type": ["string", "null"] },
          "company": { "type": ["string", "null"] },
          "service_interest": { "type": ["string", "null"] },
          "budget_range": { "type": ["string", "null"] },
          "timeframe": { "type": ["string", "null"] },
          "status": {
            "type": ["string", "null"],
            "enum": ["горячий", "теплый", "холодный", null]
          }
        },
        "required": ["name", "contact", "company", "service_interest", "budget_range", "timeframe", "status"],
        "additionalProperties": false
      },
      "ready_to_submit": { "type": "boolean" }
    },
    "required": ["reply", "extracted_ticket", "extracted_lead", "ready_to_submit"],
    "additionalProperties": false
  }
}
```

### 4.6. Пример ответа LLM

```json
{
  "reply": "Спасибо! Всё собрано. Сейчас передаю заявку менеджеру.",
  "extracted_ticket": {
    "name": null,
    "contact": null,
    "problem_summary": null,
    "occurred_at": null,
    "location": null,
    "priority": null
  },
  "extracted_lead": {
    "name": "Алексей",
    "contact": "+79001234567",
    "company": "ООО Ромашка",
    "service_interest": "Автоматизация продаж через Telegram-бота",
    "budget_range": "100–200 тыс. руб.",
    "timeframe": "В течение недели",
    "status": "теплый"
  },
  "ready_to_submit": true
}
```

### 4.7. curl-пример

```bash
export OPENAI_API_KEY="your_openai_api_key"

curl -s https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4.1-mini",
    "temperature": 0.2,
    "messages": [
      {"role": "system", "content": "Ты AI-ассистент по сбору заявок для отдела продаж. Верни JSON с reply, extracted_lead и ready_to_submit."},
      {"role": "user", "content": "latest_user_message: привет, хочу автоматизацию продаж"}
    ],
    "response_format": {
      "type": "json_schema",
      "json_schema": {
        "name": "assistant_turn",
        "strict": true,
        "schema": {
          "type": "object",
          "properties": {
            "reply": {"type": "string"},
            "extracted_lead": {
              "type": "object",
              "properties": {
                "name": {"type": ["string", "null"]},
                "contact": {"type": ["string", "null"]},
                "company": {"type": ["string", "null"]},
                "service_interest": {"type": ["string", "null"]},
                "budget_range": {"type": ["string", "null"]},
                "timeframe": {"type": ["string", "null"]},
                "status": {"type": ["string", "null"], "enum": ["горячий", "теплый", "холодный", null]}
              },
              "required": ["name", "contact", "company", "service_interest", "budget_range", "timeframe", "status"],
              "additionalProperties": false
            },
            "ready_to_submit": {"type": "boolean"}
          },
          "required": ["reply", "extracted_lead", "ready_to_submit"],
          "additionalProperties": false
        }
      }
    }
  }'
```

---

## 🧩 5. Внутренние контракты

### 5.1. AssistantTurn

| Поле | Тип | Описание |
|------|-----|----------|
| `reply` | `str` | Текст ответа пользователю |
| `extracted_ticket` | `SupportTicket` | Поля заявки в ТП |
| `extracted_lead` | `SalesLead` | Поля заявки в продажи |
| `ready_to_submit` | `bool` | Готовность к отправке |

### 5.2. OperatorNotifier.send

```python
async def send(session: SupportSession) -> None
```

Формирует и отправляет сообщение в чат операторов на основе `session.scenario`.

---

## 📝 6. Примеры итоговых сообщений в чате операторов

### 6.1. Заявка в техподдержку

```text
=== НОВАЯ ЗАЯВКА В ТП ===

Имя: Александр
Контакт: +79991234567

Проблема:
Не включается ноутбук после обновления

Когда возникло: сегодня утром
Где: ноутбук

Приоритет: срочно

Telegram user id: 331349444
Telegram username: @alex_example

=== КОНЕЦ ===
```

### 6.2. Лид для отдела продаж

```text
=== НОВЫЙ ЛИД ===

Имя: Алексей
Контакт: @alexei_sales
Компания: ООО Ромашка

Интерес:
Автоматизация продаж через Telegram-бота

Бюджет: 100–200 тыс. руб.
Сроки: В течение недели
Статус: теплый

Telegram user id: 331349444
Telegram username: @alexei_sales

=== КОНЕЦ ===
```

---

## 📚 Связанные документы

- [🏠 `README.md`](../README.md) — главная страница проекта.
- [🏗️ `docs/ARCHITECTURE.md`](ARCHITECTURE.md) — архитектура системы.
- [📝 `docs/PROMPT_ARCHITECTURE.md`](PROMPT_ARCHITECTURE.md) — архитектура промптов и JSON Schema.
- [🧪 `docs/TESTING.md`](TESTING.md) — результаты E2E-прогонов.
- [🚀 `docs/DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) — развёртывание.
