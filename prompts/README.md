# 🗂️ prompts/

**Проект:** telegram-intake-bot  
**Дата:** 2026-08-09  
**Последнее обновление:** 2026-08-22  
**Статус:** as-built

---

## 🎯 1. Назначение

Каталог содержит версионированные системные промпты для Telegram Intake Bot.

---

## 📝 2. Схема нейминга

`<scenario>-assistant-v<version>.md`

| Файл | Версия | Статус | Описание |
|------|--------|--------|----------|
| [📄 `support-assistant-v1.md`](support-assistant-v1.md) | v1 | Устаревшая | Первая версия промпта техподдержки |
| [📄 `support-assistant-v2.md`](support-assistant-v2.md) | v2 | Устаревшая | Усиленный порядок полей и guard replies |
| [📄 `support-assistant-v3.md`](support-assistant-v3.md) | v3 | **Активная** | Упрощённая версия с позитивными командами |
| [📄 `sales-lead-assistant-v1.md`](sales-lead-assistant-v1.md) | v1 | Устаревшая | Первая версия промпта сбора лидов |
| [📄 `sales-lead-assistant-v2.md`](sales-lead-assistant-v2.md) | v2 | Устаревшая | Усиленный порядок полей и guard replies |
| [📄 `sales-lead-assistant-v3.md`](sales-lead-assistant-v3.md) | v3 | **Активная** | Упрощённая версия с автоматическим status |

---

## ✅ 3. Активная версия

В коде используются:

- [📄 `support-assistant-v3.md`](support-assistant-v3.md)
- [📄 `sales-lead-assistant-v3.md`](sales-lead-assistant-v3.md)

---

## 🔄 4. Правило изменений

1. При правке промпта создаётся новый файл с увеличенной версией.
2. Предыдущая версия сохраняется для истории.
3. В [📝 `docs/PROMPT_ARCHITECTURE.md`](../docs/PROMPT_ARCHITECTURE.md) добавляется запись в changelog.
4. После изменения промпта выполняется E2E-прогон и фиксируются результаты в [🧪 `docs/TESTING.md`](../docs/TESTING.md).

---

## 📚 Связанные документы

- [🏠 `README.md`](../README.md) — главная страница проекта.
- [📝 `docs/PROMPT_ARCHITECTURE.md`](../docs/PROMPT_ARCHITECTURE.md) — архитектура промптов и JSON Schema.
- [🧪 `docs/TESTING.md`](../docs/TESTING.md) — результаты E2E-прогонов.
