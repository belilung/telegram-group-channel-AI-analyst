# Telegram Group/Channel AI Analyst

> 🌐 **[English](README.md)** | **[Русский](README.ru.md)**

24/7 мониторинг Telegram-групп и каналов. Подключается к Telegram как
**user-аккаунт** через MTProto (не как бот), слушает сообщения в группах
и каналах, которые ты выбрал, прогоняет каждое сообщение через Claude,
чтобы отфильтровать шум, и показывает только релевантные элементы в
локальном веб-dashboard и ежедневном дайджесте.

Построен на **WAT-фреймворке** (Workflows, Agents, Tools): детерминированные
Python-инструменты делают работу, AI принимает решения, markdown-workflow'ы
документируют каждый сквозной сценарий.

---

## Быстрый старт (с Claude Code)

Если ты новичок в Telegram MTProto, Python virtualenv'ах или даже самом
Claude Code — **не читай документацию первым делом**. Просто сделай так:

```bash
git clone https://github.com/belilung/telegram-group-channel-AI-analyst.git TelegramWatcher
cd TelegramWatcher
claude
```

Потом скажи Claude:

> **"помоги мне всё настроить"**

Claude проведёт тебя по каждому шагу: получение Telegram API-креденшалов,
запись `.env`, создание virtualenv'а, выбор групп и темы мониторинга,
логин в Telegram и запуск watcher'а. Около 10–15 минут. Никакого
предварительного опыта с Python или Telegram API не требуется.

Хочешь вручную? Переходи к [`INSTALL.ru.md`](INSTALL.ru.md) или смотри
секцию **Ручной быстрый старт** ниже.

> ⚠️ **Нужна активная подписка Claude Pro** — watcher классифицирует
> сообщения через `claude` CLI, а не через Anthropic API-ключ. Установи
> CLI с <https://claude.ai/code> и запусти `claude /login` один раз перед
> стартом.

---

## Что ты получаешь

- **Realtime listener.** Каждое сообщение из watched-группы попадает в
  локальную SQLite-БД.
- **AI-фильтр релевантности.** Каждое сообщение оценивается Claude'ом по
  `topic_hint` группы (например `gamedev`, `ai-startups`, `3d`). Только
  релевантным сообщениям присваиваются `topic` и `summary`.
- **Локальный dashboard** на `http://127.0.0.1:8000` с тремя видами:
  - **Feed** — последние релевантные сообщения по всем группам, фильтр по
    временному окну.
  - **Daily digest** — релевантные элементы по дням и группам.
  - **Digest window** — мульти-дневный дайджест для ретроспективного
    сканирования.
- **Ежедневный cron-дайджест.** В заданный час каждый день watcher
  пере-сканирует прошедшие 24 часа каждой группы — на случай, если
  realtime listener что-то упустил или был оффлайн.
- **Готов к Docker.** Один `docker compose up -d` крутит всё 24/7.

Что **не** делает (специально): не классифицирует приватные DM, не делает
lead scoring, не экспортирует в Google Sheets, не использует Telegram bot
API, не транскрибирует голос. Если нужно — форкай и дописывай.

---

## Архитектура (WAT)

Три слоя, каждый с одной ответственностью:

```
┌──────────────────────────────────────────────────────────┐
│  workflows/   markdown SOPs — что должно происходить      │
│                  (scan_group_daily.md, build_digest.md)   │
├──────────────────────────────────────────────────────────┤
│  agent        Claude — принимает решения, зовёт tools     │
│                  (run-time через tools/classifier.py)     │
├──────────────────────────────────────────────────────────┤
│  tools/       Python — детерминированно делает работу     │
│                  (telegram_client.py, message_store.py,   │
│                   classifier.py, group_scanner.py)        │
└──────────────────────────────────────────────────────────┘
```

Единственная точка входа `app/supervisor.py` объединяет Telethon
(group listener), APScheduler (cron дайджеста) и Uvicorn (dashboard) в
один async event loop.

```
TelegramWatcher/
├── app/
│   ├── supervisor.py        ← запускай это
│   ├── setup_session.py     ← одноразовый Telegram login
│   ├── run_listener.py      ← realtime обработчик группы
│   ├── run_daily_digest.py  ← cron-задание ежедневного дайджеста
│   ├── build_digest_from_db.py
│   ├── scheduler.py
│   ├── dashboard.py
│   ├── config.py
│   ├── templates/           ← Jinja2-шаблоны
│   └── static/              ← CSS / JS
├── tools/
│   ├── telegram_client.py   ← Telethon-обёртка + flood retry
│   ├── claude_chat.py       ← вызов `claude` CLI
│   ├── classifier.py        ← judge_group() — LLM-вызов релевантности
│   ├── message_store.py     ← SQLite-репозиторий (3 таблицы)
│   ├── group_scanner.py     ← daily/window сканирование
│   └── resolve_groups.py    ← конвертер @links → chat_ids
├── system_prompts/
│   └── group_relevance_filter.md  ← редактируй под свою нишу
├── workflows/
│   ├── scan_group_daily.md
│   ├── build_daily_digest.md
│   └── onboarding.ru.md     ← полный пошаговый онбординг (этот workflow)
├── tests/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── INSTALL.ru.md
```

---

## Ручной быстрый старт

Для тех, кто не хочет использовать Claude Code как мастер настройки.
Полная пошаговка — в [`INSTALL.ru.md`](INSTALL.ru.md).

Кратко:

```bash
# 1. Склонировать и поднять Python
git clone https://github.com/belilung/telegram-group-channel-AI-analyst.git TelegramWatcher
cd TelegramWatcher
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Получить Telegram API креденшалы на https://my.telegram.org → API development tools
cp .env.example .env
# заполнить TG_API_ID, TG_API_HASH, TG_PHONE, WATCHED_GROUPS_INIT

# 3. Установить Claude CLI с https://claude.ai/code и залогиниться (Claude Pro)
claude --version

# 4. Одноразовый Telegram login (введи код, который Telegram пришлёт)
python -m app.setup_session

# 5. Запустить watcher
python -m app.supervisor
```

Открой `http://127.0.0.1:8000`.

### Docker

```bash
# один раз залогиниться на хосте, чтобы auth Claude CLI пережил перезапуск
claude --version

# одноразовый Telegram code prompt
docker compose run --rm watcher python -m app.setup_session

# запуск 24/7
docker compose up -d
docker compose logs -f watcher
```

---

## Конфигурация

Вся конфигурация в `.env`. Полный список — в `.env.example`.

Чаще всего нужные тумблеры:

| Переменная | Эффект |
|------------|--------|
| `WATCHED_GROUPS_INIT` | Seed-список `<ссылка>|<topic_hint>;...` при первом запуске |
| `CLAUDE_MODEL` | Какую модель Claude использовать (по умолч. `claude-haiku-4-5`) |
| `REALTIME_AI_FILTER` | `true` = классифицировать сразу; `false` = только дневной cron |
| `DIGEST_CRON_HOUR` | Час суток для ежедневного дайджеста (в `LOCAL_TZ`) |
| `MAX_MSGS_PER_GROUP` | Лимит сообщений в группе на дневное сканирование |
| `CLASSIFY_CONCURRENCY` | Сколько параллельных Claude-вызовов (по умолч. 4) |

Чтобы изменить правила релевантности под свою нишу, редактируй
`system_prompts/group_relevance_filter.md`. Это единственный AI-промпт в
проекте.

---

## Добавление / удаление watched-групп

Три способа:

1. **`.env` при первом запуске.** Заполни `WATCHED_GROUPS_INIT` и запусти
   watcher. Он один раз вызовет `tools.resolve_groups.resolve_and_persist`,
   если таблица `groups_watched` пуста.
2. **Ручной CLI.** Перезапусти `python -m app.setup_session` — он
   перечитает env-список.
3. **Прямо в БД.** Отредактируй `data/telegram_watcher.db` →
   `groups_watched`. Поставь `enabled=0`, чтобы поставить группу на паузу,
   `1` — чтобы возобновить.

Ссылки на группы могут быть:
- `@username` для публичных каналов/групп
- `https://t.me/<username>` (то же самое)
- `https://t.me/c/<internal_id>/<msg_id>` для приватных супергрупп, в
  которых ты уже состоишь

---

## Тесты

```bash
pytest -q
```

---

## Лицензия

MIT. Используй, форкай, продавай, передавай студентам — на твоё
усмотрение.
