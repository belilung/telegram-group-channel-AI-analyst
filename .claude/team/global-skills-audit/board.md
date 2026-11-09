# Design Council — global-skills-audit

**Задача:** Пересмотреть ВСЕ глобальные скиллы пользователя (`~/.claude/`, не репо текущего проекта) и выдать рекомендации: что оставить, что удалить как лишнее, что добавить. Нужен исполнимый план куcollings/pruning, а не просто список. Код не пишем — только дизайн/план.

**Создано:** 2026-06-01 17:34

---

## Хард-данные (собрано оркестратором, проверяемо)

### Источники скиллов
1. **`~/.claude/skills/`** — 164 standalone-директории (плюс 2 UUID-папки кэша, не считаем).
2. **Плагин `everything-claude-code@1.10.0`** — 183 скилла, namespaced как `everything-claude-code:*`.
3. Другие плагины: `buildatscale` (ceo/commit/pr), `nano-banana-pro` (generate), `promo-video`, `document-skills@anthropic` (docx/pptx/xlsx/pdf/frontend-design/...), `codex@openai`.

### КЛЮЧЕВАЯ ПРОБЛЕМА — дублирование
- **149 из 164** standalone-скиллов в `~/.claude/skills/` — это ТОЧНЫЕ ДУБЛИ скиллов из плагина ECC (совпадение имён, проверено `comm -12`).
- То есть пользователь держит один и тот же набор ДВАЖДЫ: как распакованные standalone-копии И как плагин. Оба грузятся в индекс скиллов каждой сессии → раздувание контекста, дубли в выборе (`tdd` vs `everything-claude-code:tdd` и т.д.).

### Только 15 standalone-скиллов НЕ из ECC-плагина (уникальные/другой источник):
`brainstorm`, `gsap`, `hyperframes`, `hyperframes-cli`, `hyperframes-registry`,
`implement`, `learned`, `paperclip`, `paperclip-create-agent`, `paperclip-create-plugin`,
`para-memory-files`, `project-guidelines-example`, `video-use`, `website-to-hyperframes`, `zelta-design`

### Реальный рабочий контекст пользователя (из ~/.claude/projects, последние)
TelegramWatcher (Python/Telethon/FastAPI/SQLite), vertexsms-web-site, imaginus-studio (web),
Imaginus-studio-bot, Capibara, gig-radar-system (+backend), ImaginusAI,
web-курс (MyFirstWebsite), hyperframes-video-redactor, zeltaapp, botforImaginus,
claude-code-plugins (разработка плагинов!), FitnessBot, PresentationSHIFT,
Viral-content, Marinachatbot, LinkedinWorker, emailsSender.

**Профиль:** Python-боты (Telegram/fitness/chatbot), веб-сайты + фронтенд, AI/агентные системы,
контент/видео (hyperframes, viral, promo), разработка Claude Code плагинов, zeltaapp.
**НЕ видно:** Java, Kotlin, Swift, Rust, Go, C++, Perl, PHP/Laravel, .NET, enterprise-вертикали
(healthcare/HIPAA, logistics/freight/carrier, customs, energy, inventory, production scheduling, billing).

---

## Раунд 1 — Proposal (proposer)

### Верификация хард-данных

Проверено самостоятельно:
- `~/.claude/skills/` — **164 директории** (1 UUID-кэш + 163 именованных). Одна (`learned/`) — пустая директория без SKILL.md, фактически мусор.
- Матч имён с ECC cache (`~/.claude/plugins/cache/everything-claude-code/everything-claude-code/1.10.0/skills/`): **149 совпадений по имени**.
- Контентная проверка всех 149 через `diff`: **149 из 149 идентичны побайтово**. Ни одного расхождения.
- Итого: цифры board полностью подтверждены.

Уточнение по 15 non-ECC скиллам из board:
- `paperclip`, `paperclip-create-agent`, `paperclip-create-plugin`, `para-memory-files` — директорий на диске **нет**. Вероятно, были удалены ранее или никогда не создавались. Не учитываем.
- `learned/` — пустая директория. Мусор.
- `project-guidelines-example` — помечен `origin: ECC` внутри, это ECC-шаблон-пример, не персональный скилл.
- **Реально уникальных non-ECC скиллов: 9**: `brainstorm`, `gsap`, `hyperframes`, `hyperframes-cli`, `hyperframes-registry`, `implement`, `video-use`, `website-to-hyperframes`, `zelta-design`.

---

### Дизайн — основная стратегия

**Рекомендация: удалить все 149 standalone-дублей, оставить ECC-плагин.**

Три причины выбрать "плагин, не standalone":

1. **Обновляемость**: `claude plugin update everything-claude-code` — один вызов обновляет всё. Standalone-копии — замороженный снимок ECC v1.10.0, который расходится с апстримом со временем.

2. **Namespace-коллизии и индексный bloat**: Каждый из 149 дублей создаёт два entry в skill-индексе при старте сессии: `agent-sort` (standalone) и `everything-claude-code:agent-sort` (плагин). 149 дублей = ~149 лишних записей, которые Claude вынужден разрешать при skill-routing. Удаление standalone-дублей почти вдвое уменьшает размер skill-индекса.

3. **Правильное разделение ответственностей**: `~/.claude/skills/` — место для **личных** скиллов пользователя (его workflow, его продукты, его нишевые инструменты). ECC-плагин — место для общего "фонда". Сейчас это перемешано.

**Что делать с нерелевантными ECC-скиллами (52 штуки — android, kotlin, swift, rust, golang, laravel, healthcare, logistics, etc.)?** Не удалять из плагина (ECC — не под контролем пользователя). Неиспользуемые скиллы не вставляются в контекст автоматически — они лишь потенциально доступны. Если захочется их явно отключить, это делается через `~/.claude/plugins/blocklist.json`.

---

### Новые/изменённые файлы

Нет изменений в коде. Изменения только в файловой системе пользователя:

- **`~/.claude/skills/`** — после чистки останется 9 директорий (см. KEEP). Убрать 150 директорий (149 дублей + `learned/`). Опционально убрать `project-guidelines-example`.
- **`~/.claude/skills/fastapi-patterns/SKILL.md`** — новый файл (ADD #1)
- **`~/.claude/skills/telethon-patterns/SKILL.md`** — новый файл (ADD #2)
- **`~/.claude/skills/claude-code-plugin-dev/SKILL.md`** — новый файл (ADD #3)

---

### Контракты — бакеты KEEP / REMOVE / ADD

#### KEEP — 9 уникальных standalone-скиллов

**Видео и HyperFrames (core domain пользователя):**
- `hyperframes` — авторский скилл, ~300+ строк, содержит house-style/palettes/patterns/visual-styles — нигде больше нет
- `hyperframes-cli` — CLI reference (init/lint/preview/render/transcribe/tts)
- `hyperframes-registry` — registry-блоки и компоненты HyperFrames
- `website-to-hyperframes` — promo-видео из URL, уникальный pipeline
- `gsap` — GSAP reference специфично для HyperFrames (211 строк)
- `video-use` — полноценный пакет (uv.lock, helpers, install.md), не просто SKILL.md

**Агентные workflow (личные, не в ECC):**
- `brainstorm` — параллельный фиче-анализ через 7 read-only суб-агентов; `disable-model-invocation: true` — личный рабочий процесс
- `implement` — имплементация плана через параллельных суб-агентов; пара к brainstorm

**Дизайн-системы:**
- `zelta-design` — 520 строк, дизайн-система Zelta wallet, brutalist neo-mint, iOS/Android/Web

#### REMOVE — 150 директорий из `~/.claude/skills/`

Все 149 побайтово-идентичных ECC-дублей, плюс 1 пустышка:
```
comm -12 \
  <(ls ~/.claude/skills/ | sort) \
  <(ls ~/.claude/plugins/cache/everything-claude-code/everything-claude-code/1.10.0/skills/ | sort)
```
Эта команда выдаёт точный список. Плюс отдельно `rm -rf ~/.claude/skills/learned`.

Группы для понимания масштаба (все — дубли ECC):
- AI/агентные: agent-eval, agent-harness-construction, agent-introspection-debugging, agent-sort, agentic-engineering, ai-first-engineering, autonomous-loops, continuous-agent-loop, eval-harness, council, blueprint...
- Python/Backend: python-patterns, python-testing, backend-patterns, django-patterns, postgres-patterns, database-migrations...
- Web/Frontend: frontend-patterns, frontend-design, accessibility, api-design, nextjs-turbopack...
- Нерелевантные вертикали (тоже дубли): android-clean-architecture, carrier-*, customs-*, healthcare-*, golang-*, kotlin-*, laravel-*, rust-*, swift-*, dotnet-*, cpp-*, perl-*...

#### ADD — 3 новых standalone-скилла

1. **`fastapi-patterns`**: нет в ECC, нужен для TelegramWatcher dashboard + вероятных будущих FastAPI-проектов. Содержание: dependency injection, lifespan events, Pydantic v2, async routes, SQLite с aiosqlite, background tasks, Jinja2 templates. ~150-200 строк.

2. **`telethon-patterns`**: нет в ECC. Пользователь использует Telethon во всех Telegram-ботах (TelegramWatcher, Imaginus-studio-bot, FitnessBot, Marinachatbot, etc.). Содержание: session management, FloodWaitError handling, event handlers, history iteration, MTProto user-account vs Bot API. ~100-150 строк.

3. **`claude-code-plugin-dev`**: пользователь активно разрабатывает плагины (`claude-code-plugins` проект). ECC имеет `configure-ecc` и `mcp-server-patterns`, но не охватывает создание plugin-пакетов. Содержание: agent.yaml структура, SKILL.md conventions, marketplace publish flow, skills/agents/hooks/commands layout, versioning, blocklist. ~100-150 строк.

---

### Исполнимая последовательность

```bash
# Шаг 0 — Backup (обязателен; ~/.claude/backups уже существует)
cp -r ~/.claude/skills ~/.claude/backups/skills-$(date +%Y%m%d)

# Шаг 1 — Сформировать список к удалению
comm -12 \
  <(ls ~/.claude/skills/ | sort) \
  <(ls ~/.claude/plugins/cache/everything-claude-code/everything-claude-code/1.10.0/skills/ | sort) \
  > /tmp/skills_to_delete.txt
wc -l /tmp/skills_to_delete.txt  # должно быть 149

# Шаг 2 — Удалить дубли
while IFS= read -r skill; do
  rm -rf ~/.claude/skills/"$skill"
done < /tmp/skills_to_delete.txt

# Шаг 3 — Удалить мусор
rm -rf ~/.claude/skills/learned
# rm -rf ~/.claude/skills/project-guidelines-example  # опционально

# Шаг 4 — Проверить результат
ls ~/.claude/skills/
# Ожидается: 9 директорий + UUID-кэш

# Шаг 5 — Создать новые скиллы (ADD)
mkdir -p ~/.claude/skills/fastapi-patterns
mkdir -p ~/.claude/skills/telethon-patterns
mkdir -p ~/.claude/skills/claude-code-plugin-dev
# Написать SKILL.md в каждой (~30-45 мин суммарно)

# Шаг 6 — Верификация (в новой Claude Code сессии)
# /skill-stocktake  ← ECC-скилл, даёт обзор всех доступных скиллов
# /brainstorm       ← должен работать из standalone
# /agent-sort       ← должен работать из ECC-плагина
```

---

### Edge-cases

- **UUID-папка** (`7bad7ee6-e03d-4fb5-84c5-e400c39bbadf`) в `~/.claude/skills/` — внутренний кэш Claude Code. Не трогать.
- **ECC cache vs marketplaces**: плагин реально грузится из `~/.claude/plugins/cache/`, `marketplaces/` — git-клон для обновлений. Оба показывают 183 скилла с одинаковым содержимым.
- **`nano-banana-pro`, `promo-video`, `buildatscale`, `document-skills`, `codex`** — плагины оставить как есть. Они не дублируют standalone и покрывают отдельные нужды пользователя (AI-генерация медиа, документы, commit-workflow).
- **`skill-stocktake`** (ECC-скилл) — после чистки полезно вызвать для сверки финального состояния.
- **`agent-sort`** (ECC-скилл) — продолжит работать из плагина; standalone-дубль будет удалён.
- **Blocklist для нерелевантных ECC-скиллов**: опционально можно добавить в `~/.claude/plugins/blocklist.json` записи для 52 нерелевантных ECC-скиллов (android, kotlin, swift, rust, golang, laravel, healthcare, etc.). Это уменьшит listing, но не даёт значительного прироста производительности — они и так не вызываются сами по себе.

---

### Открытые вопросы к пользователю

1. `project-guidelines-example` — удалить или сохранить как живой шаблон для будущих проектных скиллов?
2. Есть ли уже написанные `fastapi-patterns` / `telethon-patterns` в каком-то проектном CLAUDE.md, которые стоит поднять на глобальный уровень вместо написания с нуля?
3. Планируется ли поддержка Zelta на мобильных (SwiftUI/Compose) — если да, `zelta-design` покрывает это, оставляем; если нет — можно trimmed web-only версию.

---

## Раунд 1 — Critique (critic)

### Возражения

- **#1 [severity: blocking]** Proposal утверждает «149 из 149 побайтово идентичны» и безопасно удалять все. Но `continuous-learning-v2` входит в список комм-12 (подтверждено: `comm -12` выдаёт его). При этом **6 команд в `~/.claude/commands/`** (`prune`, `evolve`, `promote`, `projects`, `instinct-import`, `instinct-status`) содержат жёстко прописанный fallback-путь `python3 ~/.claude/skills/continuous-learning-v2/scripts/instinct-cli.py`. Переменная `${CLAUDE_PLUGIN_ROOT}` устанавливается только при запуске команды *из plugin-контекста*; standalone-команды в `~/.claude/commands/` её не получают и идут по fallback-пути. После удаления standalone-директории все эти команды (`/prune`, `/evolve`, `/promote`, `/projects`, `/instinct-import`, `/instinct-status`) сломаются с `FileNotFoundError`. Proposer не упомянул эту проблему вообще. Проверено: `grep -n "~/.claude/skills/continuous-learning-v2"` в команд-файлах даёт 10 совпадений.

- **#2 [severity: high]** Proposal не объясняет, **почему дубли появились и могут ли появиться снова**. Данные filesystem показывают два пика создания: ~46 директорий `Mar 23` и ~105 директорий `Apr 15`. Это соответствует ручной команде `cp -r everything-claude-code/.agents/skills/* ~/.claude/skills/` из README ECC (подтверждено: `~/.claude/plugins/cache/everything-claude-code/.../README.md` содержит именно эту команду). Если пользователь когда-либо обновит ECC по инструкции из README или запустит скрипт `install.sh` из `~/.claude/plugins/marketplaces/everything-claude-code/`, 149 дублей появятся снова. Proposal не предлагает никакой защиты от рецидива (например, `.gitignore`-style excludes, Note в README, или удаление legacy cp-инструкций).

- **#3 [severity: high]** Proposal утверждает, что `learned/` — «пустая директория, мусор» и рекомендует `rm -rf`. Но **команда `learn.md` явно создаёт файлы в `~/.claude/skills/learned/`** (`Create a skill file at ~/.claude/skills/learned/[pattern-name].md`). Директория пуста сейчас (0 файлов проверено), но это целевое хранилище для будущих `/learn`-сессий. Удалить её без примечания — значит потерять destinat, на которое `/learn` записывает. После удаления `/learn` либо упадёт с ошибкой «directory not found», либо Claude Code создаст директорию заново — поведение не определено proposal'ом. Правильное действие: оставить `learned/` как пустую директорию (или явно указать что она пересоздаётся автоматически).

- **#4 [severity: medium]** ADD-список (`fastapi-patterns`, `telethon-patterns`, `claude-code-plugin-dev`) предлагает создать скиллы с контентом «~150 строк», но **не приводит конкретного черновика SKILL.md** — только перечень тем. Это YAGNI-риск: три пустых `mkdir` создают директории без SKILL.md, а значит step 5 исполнимой последовательности фактически оставлен незавершённым («написать SKILL.md — 30-45 мин суммарно»). Если пользователь выполнит шаги 0-4 (удаление), а шаг 5 не завершит, индекс скиллов окажется хуже, чем до чистки. Порядок исполнения должен быть: сначала создать новые SKILL.md, потом удалять старые.

- **#5 [severity: low]** Bash-последовательность использует `ls | sort` + `comm`. На macOS `ls` не выводит имена со слешами, пробелов/спецсимволов в именах нет (проверено grep на спецсимволы — нет). Однако `while IFS= read -r skill; do rm -rf ...` безопасен для имён с пробелами, если они были бы. Это корректно. Проблема другая: в `~/.claude/skills/` есть симлинк-директория `7bad7ee6-e03d-4fb5-84c5-e400c39bbadf -> ~/.paperclip/instances/...`. `comm -12` не выдаст её (UUID нет в ECC), поэтому случайного удаления нет. Но proposer описывает её как «внутренний кэш Claude Code» — на самом деле это **симлинк на Paperclip** (`~/.paperclip/instances/default/skills/`). Неточная классификация — не ломает план, но важно знать: если Paperclip paperclip переустановится, симлинк может протухнуть независимо от чистки.

### Что хорошо

- Побайтовая верификация всех 149 через `diff -r` — это строгая проверка, не сэмплинг. Тезис об отсутствии расхождений контентно верен (кроме вопроса о данных instinct-cli, которые хранятся в `~/.claude/homunculus/`, а не в директории скилла — проверено).
- KEEP-список из 9 скиллов правильно идентифицирован как персональный (авторские, нигде больше не дублируются). `hyperframes`, `zelta-design`, `brainstorm`, `implement` — реально уникальны.
- Выбор «оставить плагин, удалить standalone» (а не наоборот) правильный по трём причинам: обновляемость, namespace, разделение ответственностей. Логика sound.

---

## Раунд 2 — Revision (proposer)

### Изменения по замечаниям

- **[#1 blocking — hidden coupling]** Проведён полный grep `~/.claude/commands/`, `~/.claude/agents/`, `~/.claude/hooks/`, `~/.claude/settings.json` на все жёсткие пути `~/.claude/skills/<name>`. Результат: **только два имени скилла** фигурируют в fallback-путях: `continuous-learning-v2` (6 команд) и `learned` (команда `learn.md`, `learn-eval.md`). Дополнительно обнаружено: все 79 `~/.claude/commands/*.md` — побайтово-идентичные копии команд ECC-плагина (тот же `cp -r`-пат из README). Когда плагин загружает свои команды, `CLAUDE_PLUGIN_ROOT` устанавливается на кэш-директорию плагина и путь разрешается корректно. Но standalone-копии в `~/.claude/commands/` тоже загружаются параллельно и конкурируют за те же имена (`/prune`, `/evolve` etc.), и для них `CLAUDE_PLUGIN_ROOT` не установлен — они идут по fallback. Это подтверждает блокирующий характер замечания. Решение: исключить `continuous-learning-v2` из списка удаления; `learned` и так не входил в список 149 дублей (non-ECC), удаление `learned` из плана полностью отменено (см. #3). Итоговый DELETE-счёт: **148** (было 149).

- **[#2 high — recurrence]** Добавлен конкретный шаг защиты от рецидива. Подтверждено: `/configure-ecc` скилл (ECC-встроенный) тоже выполняет `cp -r $ECC_ROOT/skills/<skill-name> $TARGET/skills/` при интерактивной установке — аналогичный риск. Три превентивных механизма описаны в "Шаг 5 — Recurrence Guard" ниже.

- **[#3 high — learned/ is NOT garbage]** Полностью отменено удаление `learned/`. Директория включена в KEEP-список. Обоснование: `/learn` команда явно пишет в `~/.claude/skills/learned/[pattern-name].md`; `/learn-eval` тоже ссылается на `~/.claude/skills/learned/` как целевое хранилище. Пустота директории сейчас не означает "мусор" — это ненаполненный контейнер активного workflow.

- **[#4 medium — ADD-скиллы без черновиков]** Порядок исполнимой последовательности инвертирован: шаг "создать новые SKILL.md" теперь идёт ДО удаления дублей. Черновики структуры всех трёх новых скиллов добавлены в секцию "ADD" ниже (frontmatter + заголовки разделов, ~skeleton-уровень). Это блокирует сценарий "удалил старое, не дописал новое".

- **[#5 low — UUID симлинк]** Исправлена классификация: `7bad7ee6-e03d-4fb5-84c5-e400c39bbadf` — это симлинк на `~/.paperclip/instances/default/skills/`, а не "внутренний кэш Claude Code". Добавлено примечание в edge-cases: не трогать, при переустановке Paperclip симлинк может протухнуть независимо от чистки скиллов.

---

### Дизайн — обновлённая стратегия

**Стратегия та же: удалить standalone ECC-дубли, оставить плагин.** Изменилась только точность списка и порядок исполнения.

Итоговая формула:

```
DELETE_SET = (149 побайтово-идентичных ECC-дублей)
             MINUS (continuous-learning-v2)   ← coupling с commands
             MINUS (learned)                  ← /learn write target, не дубль ECC
           = 148 директорий
```

`learned` не входил в 149 дублей (non-ECC), поэтому его исключение из DELETE_SET не меняет счёт. Формально: 148 к удалению.

**Ситуация с командами (новое знание, замечание #1):** Все 79 `~/.claude/commands/*.md` — тоже побайтово-идентичные ECC-копии. Это выходит за scope текущего аудита (задача — skills), но должно быть зафиксировано как технический долг: дублированные команды создают конкурирующие slash-command entries и могут вызывать недетерминированную маршрутизацию (см. changelog строка 1218: "slash commands resolving to the wrong plugin with duplicate name frontmatter"). Рекомендация: отдельный `commands-audit` как follow-up задача.

---

### Обновлённые бакеты KEEP / REMOVE / ADD

#### KEEP — 11 директорий в `~/.claude/skills/`

**Личные авторские скиллы (9, без изменений):**
`hyperframes`, `hyperframes-cli`, `hyperframes-registry`, `website-to-hyperframes`, `gsap`, `video-use`, `brainstorm`, `implement`, `zelta-design`

**Дополнительно оставляем (2, было в REMOVE в раунде 1):**
- `continuous-learning-v2` — жёсткая зависимость 6 команд через fallback путь
- `learned` — активный write-target команды `/learn`; пустота сейчас != мусор

Опционально оставляем (без изменений): `project-guidelines-example`.

#### REMOVE — 148 директорий

Вычислено как:
```bash
comm -12 \
  <(ls ~/.claude/skills/ | sort) \
  <(ls ~/.claude/plugins/cache/everything-claude-code/everything-claude-code/1.10.0/skills/ | sort) \
  | grep -v "^continuous-learning-v2$" \
  > /tmp/skills_to_delete.txt
wc -l /tmp/skills_to_delete.txt  # ожидается 148
```

Все остальные соображения из Раунда 1 (группы, смысловое разбиение) остаются без изменений.

#### ADD — 3 новых standalone-скилла (с skeleton-структурой)

Создаются ДО удаления (шаг 1 в новой последовательности).

**1. `~/.claude/skills/fastapi-patterns/SKILL.md`**
```
---
name: fastapi-patterns
description: FastAPI patterns for async web services — dependency injection, lifespan events, Pydantic v2, Jinja2, SQLite via aiosqlite, background tasks. Relevant for TelegramWatcher dashboard and similar projects.
---
# FastAPI Patterns
## Dependency Injection
## Lifespan Events (startup/shutdown)
## Pydantic v2 Models and Settings
## Async Routes and aiosqlite
## Background Tasks
## Jinja2 Templates
## Error Handling and HTTPException
## Testing with httpx.AsyncClient
```

**2. `~/.claude/skills/telethon-patterns/SKILL.md`**
```
---
name: telethon-patterns
description: Telethon MTProto patterns — session management, FloodWaitError retry, event handlers, history iteration, user-account vs Bot API distinction.
---
# Telethon Patterns
## Session Management (StringSession vs file session)
## FloodWaitError: Retry with Exponential Backoff
## Event Handlers (NewMessage, MessageEdited)
## History Iteration (iter_messages)
## Resolving @username and t.me/c Links to chat_id
## User Account vs Bot API — Key Differences
## Flood-safe Bulk Operations
```

**3. `~/.claude/skills/claude-code-plugin-dev/SKILL.md`**
```
---
name: claude-code-plugin-dev
description: Claude Code plugin authoring — agent.yaml structure, SKILL.md conventions, marketplace publish flow, skills/agents/hooks/commands layout, CLAUDE_PLUGIN_ROOT, blocklist.
---
# Claude Code Plugin Development
## agent.yaml Structure and Required Fields
## SKILL.md Frontmatter and Description Conventions
## Commands: Frontmatter and CLAUDE_PLUGIN_ROOT Usage
## Hooks: hooks.json Schema
## Agents: agent frontmatter
## Plugin Publish Flow (marketplace)
## Versioning and Changelog Conventions
## blocklist.json — Disabling Specific Skills/Commands
## Testing a Plugin Locally (--plugin-dir)
```

---

### Обновлённая исполнимая последовательность

```bash
# === ШАГ 0 — Backup (обязателен) ===
cp -r ~/.claude/skills ~/.claude/backups/skills-$(date +%Y%m%d)
# Опционально: тоже забэкапить команды (они тоже являются standalone-копиями ECC)
cp -r ~/.claude/commands ~/.claude/backups/commands-$(date +%Y%m%d)

# === ШАГ 1 — Создать новые скиллы ПЕРЕД удалением ===
mkdir -p ~/.claude/skills/fastapi-patterns
mkdir -p ~/.claude/skills/telethon-patterns
mkdir -p ~/.claude/skills/claude-code-plugin-dev
# Написать SKILL.md в каждую (skeleton выше — стартовая точка)
# Команды записи: Write tool или editor
# Убедиться что все три SKILL.md существуют перед переходом к шагу 2

# === ШАГ 2 — Сформировать список к удалению (с исключением continuous-learning-v2) ===
comm -12 \
  <(ls ~/.claude/skills/ | sort) \
  <(ls ~/.claude/plugins/cache/everything-claude-code/everything-claude-code/1.10.0/skills/ | sort) \
  | grep -v "^continuous-learning-v2$" \
  > /tmp/skills_to_delete.txt
wc -l /tmp/skills_to_delete.txt  # ожидается 148

# === ШАГ 3 — Dry-run: проверить список перед удалением ===
echo "=== WILL DELETE ===" && cat /tmp/skills_to_delete.txt
echo "=== WILL KEEP ===" && comm -23 \
  <(ls ~/.claude/skills/ | grep -v "^7bad7ee6" | sort) \
  /tmp/skills_to_delete.txt

# === ШАГ 4 — Удалить 148 дублей ===
while IFS= read -r skill; do
  rm -rf ~/.claude/skills/"$skill"
  echo "Deleted: $skill"
done < /tmp/skills_to_delete.txt

# === ШАГ 5 — Recurrence Guard (НОВЫЙ ШАГ) ===
# 5a. Пометить факт чистки в ~/.claude/skills/README.md
cat > ~/.claude/skills/README.md << 'EOF'
# ~/.claude/skills — Personal Skills Only

This directory is for PERSONAL standalone skills.
ECC (everything-claude-code) skills are loaded via the PLUGIN — do NOT copy them here.

## What NOT to do
- Do NOT run: cp -r everything-claude-code/skills/* ~/.claude/skills/
- Do NOT run: cp -r everything-claude-code/.agents/skills/* ~/.claude/skills/
- Do NOT run /configure-ecc with "Install all skills" option for user-level installation
  (it will recreate ECC dupes here)

## Current personal skills
See: ls ~/.claude/skills/

## ECC skills
Available via plugin: /skill-stocktake
EOF

# 5b. Опционально: если захочется явно заблокировать ненужные ECC-скиллы
# (android, kotlin, swift, rust, golang, laravel, healthcare, logistics etc.):
# Создать ~/.claude/plugins/blocklist.json с записями:
# { "everything-claude-code": ["android-clean-architecture", "carrier-*", ...] }
# Но это НЕ обязательно — неиспользуемые скиллы не вставляются в контекст автоматически.

# === ШАГ 6 — Проверить результат ===
echo "Skills remaining:"
ls ~/.claude/skills/ | grep -v "^7bad7ee6"
# Ожидается: brainstorm, claude-code-plugin-dev, continuous-learning-v2, fastapi-patterns,
#            gsap, hyperframes, hyperframes-cli, hyperframes-registry, implement,
#            learned, project-guidelines-example (опционально), telethon-patterns,
#            video-use, website-to-hyperframes, zelta-design
#            + README.md (файл, не директория)

# Итого директорий: 14 (или 15 с project-guidelines-example)

# === ШАГ 7 — Верификация в новой Claude Code сессии ===
# /skill-stocktake  ← ECC-скилл: обзор всех доступных скиллов
# /brainstorm       ← должен работать из standalone
# /learn            ← должен создать файл в ~/.claude/skills/learned/ без ошибок
# /prune            ← должен работать (continuous-learning-v2 на месте)
# /agent-sort       ← должен работать из ECC-плагина
```

---

### Recurrence Prevention — детали

Проблема рецидива подтверждена на двух векторах:

1. **ECC README (ручной install):** Строка `cp -r everything-claude-code/.agents/skills/* ~/.claude/skills/` при следовании README создаст 149 дублей заново. Митигация: README.md в `~/.claude/skills/` с явным предупреждением "не делать cp".

2. **`/configure-ecc` skill (интерактивный wizard):** При выборе "User-level installation" и "Install all skills" `configure-ecc` выполняет `cp -r $ECC_ROOT/skills/<skill-name> $TARGET/skills/` по каждому выбранному скиллу. Митигация: при запуске `/configure-ecc` выбирать только нужные skills, не "all"; или выбирать "Project-level" (`.claude/`) вместо "User-level". README.md в `~/.claude/skills/` служит напоминанием.

3. **`install.sh` скрипт** (если ECC обновляется из marketplace clone): делегирует в Node-installer; деталей маршрутизации не видно, но риск аналогичен. Митигация: та же — не запускать install.sh без проверки, не копировать skills wholesale.

Итоговый guard: `~/.claude/skills/README.md` как постоянная заметка + осознанный выбор при запуске `/configure-ecc`.

---

### Edge-cases (обновлено)

- **`7bad7ee6-e03d-4fb5-84c5-e400c39bbadf`** — это **симлинк на Paperclip** (`~/.paperclip/instances/default/skills/`), НЕ внутренний кэш Claude Code. Не трогать. Если Paperclip переустановится, симлинк может протухнуть независимо от этой чистки.
- **`continuous-learning-v2`** — оставляем standalone. Его данные (homunculus) хранятся в `~/.claude/homunculus/`, а не в директории скилла, поэтому чистка других скиллов не затрагивает накопленные инстинкты.
- **`learned/`** — оставляем как пустую директорию. Это designatedwrite-target `/learn`. Пустота = ненаполненный контейнер, не мусор.
- **Commands (не в scope):** Все 79 `~/.claude/commands/*.md` — тоже побайтово-идентичные ECC-копии. Технический долг: отдельный `commands-audit`. Удаление standalone-команд (при условии что плагин загружает их с правильным `CLAUDE_PLUGIN_ROOT`) устранит конкуренцию slash-command имён.
- **UUID симлинк** и **ECC cache vs marketplaces** — без изменений vs Раунд 1.

---

### Открытые вопросы к пользователю

1. `project-guidelines-example` — удалить или сохранить как живой шаблон?
2. Есть ли уже написанные `fastapi-patterns` / `telethon-patterns` в каком-то проектном `CLAUDE.md`, которые стоит поднять на глобальный уровень вместо написания с нуля?
3. **Новый:** Планируется ли чистка `~/.claude/commands/` от 79 ECC-дублей как отдельная задача? Это закроет риск конкурирующих slash-command entries и сделает `CLAUDE_PLUGIN_ROOT` единственным путём для instinct-команд.

---

## Раунд 2 — Critique (critic)

### Возражения

- **#1 [severity: low]** Proposer утверждает, что `paperclip`, `paperclip-create-agent`, `paperclip-create-plugin`, `para-memory-files` — «директорий на диске нет». Проверено: все четыре **существуют как симлинки** (`ls -la ~/.claude/skills/paperclip*` — четыре `lrwxr-xr-x`, дата `Mar 30`), указывающие на `~/Documents/Apps/paperclip/skills/`. Все четыре цели битые (файлы удалены). Это не влияет на корректность плана — они не входят в ECC-список и не будут удалены. Но описание KEEP-списка в board и ожидаемый вывод `ls` в Шаге 6 расходятся с реальностью: после чистки в директории окажутся 14-15 личных директорий плюс 4 битых симлинка. Severity: low — не ломает план, но README.md-guard и финальный `ls`-ожидаемый список должны быть уточнены.

### Что хорошо

- **Блокер #1 полностью устранён:** grep по `~/.claude/commands/`, `~/.claude/agents/`, `~/.claude/hooks/`, `settings.json` проведён и верифицирован независимо. Только `continuous-learning-v2` и `learned` имеют жёсткие пути. Исключение `continuous-learning-v2` из DELETE_SET корректно: хотя hooks.json разрешает `skills/continuous-learning-v2/hooks/observe.sh` через `CLAUDE_PLUGIN_ROOT` (плагин-копия), standalone-команды в `~/.claude/commands/` НЕ получают `CLAUDE_PLUGIN_ROOT` и идут по fallback — поэтому standalone-директория нужна. Счёт 148 верифицирован (`wc -l` = 148).
- **Блокер #3 полностью устранён:** `learned` не входил в 149 ECC-дублей (проверено `grep "^learned$" /tmp/ecc_skills.txt` — absent), исключение из плана корректно, README-guard добавлен.
- **Bash-логика исключения корректна:** `comm -12 ... | grep -v "^continuous-learning-v2$"` работает точно, `continuous-learning-v2` отсутствует в `/tmp/skills_to_delete_v2.txt` — подтверждено симуляцией.
