# Установка

> 🌐 **[English](INSTALL.md)** | **[Русский](INSTALL.ru.md)**
>
> **Первый раз? Путь проще:** склонируй репо, запусти `claude` в директории
> проекта и скажи *"помоги мне всё настроить"* — Claude проведёт по каждому
> шагу интерактивно. См. [README.ru.md § Быстрый старт](README.ru.md#быстрый-старт-с-claude-code).
> Документ ниже — для тех, кто предпочитает делать всё руками.

Два способа запустить watcher: напрямую через Python или через Docker.
В любом случае понадобятся три вещи:

1. **Telegram API креденшалы** (бесплатно, с `my.telegram.org`)
2. **Подписка Claude Pro** + установленный `claude` CLI
3. **Python 3.11+** (только для не-Docker пути)

---

## 1. Получить Telegram API креденшалы

1. Открой <https://my.telegram.org> в браузере. Залогинься по своему
   телефону.
2. Кликни **API development tools**.
3. Создай application (любое name, любое short name, platform = "Desktop").
4. Скопируй **api_id** (число) и **api_hash** (длинная строка).

Важно: относись к `api_hash` как к паролю. Не вставляй в чаты и не
коммить.

---

## 2. Установить Claude CLI

Watcher использует твою подписку Claude Pro через `claude` CLI — ключ
Anthropic API не нужен.

```bash
# macOS / Linux
curl -fsSL https://claude.ai/install.sh | bash

# Залогиниться (откроется браузер)
claude /login
```

Проверка:

```bash
claude --version
```

Убедись, что подписка Claude Pro активна на <https://claude.ai>.

---

## 3a. Установка — Python напрямую (рекомендуется для разработки)

Нужен Python 3.11 или новее.

```bash
git clone https://github.com/belilung/telegram-group-channel-AI-analyst.git TelegramWatcher
cd TelegramWatcher

python -m venv .venv
source .venv/bin/activate         # macOS / Linux
# .venv\Scripts\activate          # Windows

pip install -r requirements.txt
```

### Настройка

```bash
cp .env.example .env
```

Открой `.env` и заполни:

```dotenv
TG_API_ID=123456
TG_API_HASH=<your-32-char-hex-from-my.telegram.org>
TG_PHONE=+380XXXXXXXXX
TG_SESSION_NAME=telegram_watcher
CLAUDE_MODEL=claude-haiku-4-5

# Стартовый список групп/каналов для мониторинга.
# Каждая запись:  <ссылка или @username>|<topic_hint>
# Topic hint — короткий тег (gamedev, ai-startups, 3d, frontend-jobs, ...).
WATCHED_GROUPS_INIT=@my_gamedev_channel|gamedev;https://t.me/c/1234567890/4350|3d
```

### Одноразовый Telegram login

```bash
python -m app.setup_session
```

Telegram пришлёт код прямо в Telegram-приложение. Вставь его. Если у
аккаунта есть 2FA, спросит пароль.

Это создаёт session-файл `data/sessions/telegram_watcher.session` —
храни его в безопасности (эквивалент того, что ты залогинен на новом
устройстве). Уже в `.gitignore`.

### Запуск

```bash
python -m app.supervisor
```

Должно появиться:

```
Supervisor: logged in id=12345 username=@you realtime_ai=True
Realtime group handler armed
Scheduler armed: daily_digest at 08:00 Europe/Kyiv
Dashboard at http://127.0.0.1:8000
```

Открой <http://127.0.0.1:8000> в браузере.

Остановить: `Ctrl-C`.

Для 24/7 на Linux используй systemd unit, `pm2` или просто `nohup`:

```bash
nohup .venv/bin/python -m app.supervisor > watcher.log 2>&1 &
```

---

## 3b. Установка — Docker (рекомендуется для VPS или always-on бокса)

```bash
git clone https://github.com/belilung/telegram-group-channel-AI-analyst.git TelegramWatcher
cd TelegramWatcher
cp .env.example .env
# заполнить TG_API_ID / TG_API_HASH / TG_PHONE / WATCHED_GROUPS_INIT
```

### Claude CLI внутри Docker

CLI использует `~/.claude/` хоста для auth. Убедись, что выполнил
`claude /login` на хосте; compose-файл монтирует `~/.claude` в контейнер
с read-write.

```bash
claude /login          # на хосте
claude --version       # проверка
```

### Одноразовый Telegram code prompt

```bash
docker compose run --rm watcher python -m app.setup_session
```

Вставь код из Telegram. То же для 2FA-пароля, если есть.

### Запуск 24/7

```bash
docker compose up -d
docker compose logs -f watcher
```

Остановить:

```bash
docker compose down
```

Session-файл и SQLite-БД живут в `./data/` на хосте — они переживают
рестарт контейнера. Бекапь их, если важна история.

---

## Диагностика

**`Code expired`** — запусти `setup_session` снова, вставляй код быстрее
(или удали старый код, который Telegram прислал ранее).

**`claude CLI not found`** — установи с <https://claude.ai/code>, потом
перезапусти shell. Внутри Docker убедись, что `~/.claude` примонтирован
и содержит auth-state.

**`FloodWaitError`** — Telegram ограничивает твой аккаунт rate-limit'ом.
Watcher отступает автоматически; просто жди. Если повторяется, снизь
`MAX_MSGS_PER_GROUP` и `CLASSIFY_CONCURRENCY` в `.env`.

**Dashboard ничего не показывает** — убедись, что группы действительно
в таблице `groups_watched`:

```bash
sqlite3 data/telegram_watcher.db 'SELECT chat_id, title, enabled, topic_hint FROM groups_watched;'
```

Если пусто — перезапусти `python -m app.setup_session` с непустым
`WATCHED_GROUPS_INIT`.

**Хочешь, чтобы бот классифицировал только в момент дайджеста, а не
realtime?** Поставь `REALTIME_AI_FILTER=false` в `.env`. Сообщения всё
равно логируются сразу; классификация ждёт дневного cron'а.

---

## Безопасность

Watcher работает от твоего собственного Telegram-аккаунта через MTProto.
Относись к его state-файлам так же, как к Telegram-логину на новом
устройстве.

### Закрой секреты на диске

После `cp .env.example .env` ограничь доступ к файлу:

```bash
chmod 600 .env
chmod 700 data/sessions/      # если уже существует
```

Supervisor и `setup_session` также автоматически делают `chmod 0600` для
`.session`, SQLite-БД и временного файла 2FA-пароля — но только *после*
создания файла. На Windows эти вызовы — silent no-op (NTFS ACL'ы
работают иначе).

### Публикация dashboard за пределы localhost

Dashboard по умолчанию слушает `127.0.0.1`. Если изменишь `DASHBOARD_HOST`
на что-то другое (например `0.0.0.0` на VPS), supervisor **откажется
стартовать** без `DASHBOARD_TOKEN`. Сгенерировать токен:

```bash
openssl rand -hex 32
```

Положи в `.env` как `DASHBOARD_TOKEN=...` и вызывай dashboard так:

```bash
curl -H "Authorization: Bearer $DASHBOARD_TOKEN" http://your-host:8000/feed
```

Эндпоинт `/healthz` остаётся открытым для liveness-проб.

### Если подозреваешь, что аккаунт скомпрометирован

1. Telegram-приложение → **Настройки → Устройства → Завершить все
   остальные сессии**.
2. <https://my.telegram.org> → **API development tools** → ротируй
   application: это инвалидирует старую пару `api_id`/`api_hash`.
3. Удали `data/sessions/*.session` локально и перезапусти
   `python -m app.setup_session` с новыми креденшалами.
4. Если утечка прошла через чат или скриншот, ротируй ещё и 2FA cloud
   password в **Настройки → Конфиденциальность → Двухэтапная
   аутентификация**.

### Что важно знать перед запуском

- **Telegram ToS**: мониторинг каналов через user-аккаунт — это серая
  зона. Используй **отдельный, второй номер телефона** для watcher'а, а
  не свой основной.
- **Shared hosting / multi-tenant машины**: `.env` и SQLite-БД видны
  любому с root или с тем же UID. Лучше личный VPS или Docker secrets /
  системный keyring.
- **Pre-commit (опционально, для контрибьюторов)**: установи hook'и,
  чтобы блокировать случайные коммиты с секретами:

  ```bash
  pip install pre-commit
  pre-commit install
  ```

  В репозитории уже включены `gitleaks` и `detect-private-key`.

## Что держать в приватности

Эти файлы никогда не должны покидать твою машину; держи их вне git,
чатов, скриншотов:

- `.env`
- `data/sessions/*.session`
- `data/telegram_watcher.db`
- Auth Claude CLI в `~/.claude/`

Все четыре уже в `.gitignore` по умолчанию.
