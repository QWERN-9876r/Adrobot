# Архитектура Adrobot

Приложение остаётся модульным монолитом: один Python-процесс отдаёт API и сборку React. Существующие маршруты, схема SQLite, протокол публикации и команда `python app.py` сохранены. Перенос файлов не требует новой миграции базы.

## Backend

```text
app.py                         # CLI/ASGI: только запуск приложения
adrobot/
  config.py                    # Корень проекта и путь сборки
  api/
    app.py                     # Сборка FastAPI-приложения
    lifespan.py                # Ресурсы и проверка миграций при запуске
    middleware.py              # Origin/Host, заголовки, ошибки
    dependencies.py            # Сессия БД и сервисы на запрос
    routes.py                  # Маршруты API
    schemas.py                 # Pydantic-контракты входа/выхода
    static.py                  # Интерфейс и разрешённые изображения
  domain/
    errors.py                  # Ошибки приложения
    tracker.py                 # Интерфейс адаптера трекера
    stream_rules.py            # Чистые правила потоков и версий
  services/
    container.py               # Композиция сервисов
    catalog.py                 # Чтение каталогов и кампаний
    creation.py                # Создание кампании, журнал и восстановление
    streams.py                 # Публикация и обнаружение конфликтов
    history.py                 # Сверка истории, закреплений и pending-записей
  infrastructure/
    database.py                # Создание engine
    models.py                  # SQLAlchemy-модели
    locking.py                 # Межпроцессные блокировки ресурсов
    demo.py                    # Демо-адаптер
    seeding.py                 # Начальные данные демо
    keitaro/
      client.py                # HTTP-транспорт Keitaro
      schemas.py               # Проверка формата ответов Keitaro
migrations/                    # Версии схемы, импорт метаданных пакета
```

API валидирует запрос и делегирует действие сервису. Сервисы владеют последовательностью операций и точками сохранения, используя доменные правила и инфраструктуру. Доменные модули не импортируют FastAPI, SQLAlchemy или сетевые библиотеки. Адаптеры реализуют общий `Tracker`.

Не перемещайте `commit()` через сетевые вызовы при последующих рефакторингах: намерение записи должно сохраниться до HTTP-запроса. Блокировки остаются привязаны к ресурсу и пути общей SQLite. Ограничение внешних конкурентных записей Keitaro описано в README и не меняется от этой структуры.

## Frontend

```text
frontend/src/
  main.tsx                     # React entry point
  app/
    App.tsx                    # Композиция страницы
    AppHeader.tsx              # Шапка и бренд
  api/
    types.ts                   # Типы HTTP-контрактов
    validation.ts              # Общие проверки значений
    decoders.ts                # Проверки конкретных ответов
    client.ts                  # Fetch и ApiError
    campaigns.ts               # Типизированные запросы приложения
  features/
    campaigns/
      components/CampaignForm.tsx
      model/creationStorage.ts # Сохранение идентификатора попытки
    streams/
      components/StreamEditor.tsx
      components/OfferPicker.tsx
      components/OfferRow.tsx
      model/shares.ts          # Чистый расчёт долей
    workspace/
      components/CampaignEditor.tsx
      model/useCampaignWorkspace.ts # Связь кампаний, потоков и черновиков
  shared/
    ui/SelectOptions.tsx
    ui/StatusNotice.tsx
    hooks/useUnsavedChanges.ts
  styles/
    base.css                   # Токены, элементы форм
    layout.css                 # Шапка, панели, расположение
    streams.css                # Потоки, таблица, доли
    responsive.css             # Адаптивные правила
    index.css                  # Порядок импорта стилей
frontend/public/brand/         # Иконка шапки и favicon
```

`app` собирает страницу, `workspace` координирует функции, отдельные функции содержат UI и свою модель, `shared` не зависит от функций. Типы контракта доступны через `api/types`; транспорт не импортирует React. Чистые расчёты не обращаются к API или хранилищу браузера.

## Проверки и ассеты

- `tests/` — сервисы, HTTP/ASGI и миграции.
- `frontend/tests/` — отдельные тесты расчётов, API и хранилища попыток.
- `frontend/tests/helpers/load-typescript.mjs` компилирует тестируемые модули с относительными импортами в памяти.
- Новая иконка находится в `frontend/public/brand/`; Vite копирует её в `dist/brand/`. FastAPI отдаёт только два явно разрешённых имени.
- Оригинал и описание генерации — `docs/assets/` и `docs/icon-generation.md`.

Проверки: `npm --prefix frontend test`, `npm --prefix frontend run build`, затем `python -m unittest discover -s tests -v`. Для HTTP-проверки изображений сначала нужна сборка frontend.
