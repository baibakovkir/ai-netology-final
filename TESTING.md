# Проверка работоспособности

## Зафиксированный результат

Локальная автоматическая проверка 31 августа 2026 года:

- Ruff lint: пройден;
- Ruff format check: пройден;
- pytest: 18 тестов пройдено, покрытие 98%;
- Python sdist и wheel: успешно собраны.
- GitHub Actions: полный CI, включая Docker build, успешно пройден.

Docker-сборку необходимо подтвердить в GitHub Actions или на машине с доступным Docker daemon.
В текущем WSL-окружении исполняемый файл Docker Desktop недоступен по правам.

Автоматические тесты не требуют сети или API-ключа:

```bash
python -m pip install -e '.[dev]'
ruff check .
ruff format --check .
pytest
python -m build
docker build -t llm-summarizer:test .
```

## Ручные сценарии

Запустите сервис командой `docker compose up --build`. Примеры используют один и тот же текст,
чтобы cache key не менялся.

### 1. Успешная суммаризация

Укажите рабочие `APP_LLM_API_KEY`, `APP_LLM_BASE_URL` и `APP_LLM_MODEL` в `.env`, затем выполните
пример `curl` из README. Ожидается HTTP 200, `source: "llm"`, `cached: false`.

### 2. Валидация

```bash
curl -i http://localhost:8000/v1/summaries \
  -H 'Content-Type: application/json' \
  -d '{"text":"коротко"}'
```

Ожидается HTTP 422 с описанием нарушения минимальной длины.

### 3. Недоступность LLM и fallback

Оставьте `APP_LLM_API_KEY` пустым и перезапустите контейнер:

```bash
docker compose up --build
```

Отправьте валидный запрос. Ожидается HTTP 503, `source: "fallback"`, `cached: false`; поле
`summary` содержит первые предложения исходного текста. В логах присутствует
`summary_degraded`, но отсутствуют исходный текст и секреты.

### 4. Cache hit

Верните рабочий ключ и дважды отправьте идентичный валидный запрос. Первый ответ должен содержать
`cached: false`, второй — `cached: true`. В логах второго запроса присутствует `cache_hit`, а
нового внешнего вызова нет.

## Материалы для сдачи

В репозитории уже сохранены:

1. `success.png` — успешный LLM-ответ;
2. `validation.png` — HTTP 422;
3. `cached.png` — повторный запрос с `cached=true`.

Перед сдачей необходимо дополнить материалы:

1. `fallback.png` — HTTP 503 с `source=fallback` при пустом или неверном API-ключе;
2. `ci.png` — успешно завершенный GitHub Actions workflow.

Запуск сервиса подтверждается доступностью Swagger UI на существующих снимках. При желании можно
добавить отдельный `startup.png` с выводом `docker compose up` и успешным `/health`.

Скриншоты зависят от локального ключа и опубликованного репозитория, поэтому не генерируются
автоматическими тестами.
