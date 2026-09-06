# 🛰️ VLESS Парсер Бот — Чёрные и Белые списки

Телеграм-бот, который **парсит рабочие VLESS Reality конфигурации с GitHub** и отдаёт их в виде **подписок** (plain + base64) для Happ / Hiddify / Streisand / v2rayNG / NekoRay / Throne.

Разделяет конфиги на два режима для РФ:

- **⬛ Чёрные списки** — классический VPN, весь трафик через сервер. Для YouTube, Discord, Twitter, ChatGPT.
- **⬜ Белые списки** — обход жёстких блокировок (ТСПУ), когда работают только VK/Госуслуги/Яндекс. Только сервера с белыми IP-подсетями (VK, Yandex, CDNVideo, Beeline).

## 🔗 Источники

Основной: [`igareck/vpn-configs-for-russia`](https://github.com/igareck/vpn-configs-for-russia) — 8.5k ⭐, обновляется каждые 15-30 минут.

| Категория | Файл | Что это |
|-----------|------|---------|
| `black_all` | `BLACK_VLESS_RUS.txt` | Чёрные списки — все VLESS (91 шт) |
| `black_mobile` | `BLACK_VLESS_RUS_mobile.txt` | Топ-150 для телефона |
| `white_cidr_all` | `WHITE-CIDR-RU-all.txt` | Белые CIDR — все хостеры (~30) |
| `white_cidr_checked` | `WHITE-CIDR-RU-checked.txt` | Белые VK/YA/CDN/Beeline (~10, самые надёжные) |
| `white_mobile` | `Vless-Reality-White-Lists-Rus-Mobile.txt` | Белые для телефона (~28) |
| `white_sni` | `WHITE-SNI-RU-all.txt` | Только Fake SNI |
| `ss_black` | `BLACK_SS+All_RUS.txt` | Shadowsocks для чёрных |

Fallback: `barry-far/V2ray-Config`, `0xRadikal/Free-v2ray-Configs`, `ebrasha/free-v2ray-public-list`

## ✨ Что умеет бот

- `/start` — меню с кнопками
- `/black` / `/black_mobile` — чёрные списки
- `/white` / `/white_cidr` / `/white_checked` / `/white_mobile` — белые списки
- `/all` — всё вместе (групповая подписка)
- `/check vless://...` — проверка синтаксиса + TCP
- `/sources` — список GitHub-источников
- `/update` — принудительное обновление
- `/stats` — статистика по количеству
- `/sub` — отправить все подписки файлами

**На каждую категорию бот:**
- Проверяет синтаксис `vless://UUID@host:port` + опционально TCP
- Дедуплицирует
- Генерирует 2 файла: `key.txt` (plain) и `key_base64.txt` (base64-подписка)
- Отдаёт файлы, base64-текст и QR-код
- Автообновляет кэш каждые 30 мин (настраивается) + может постить в канал

## 🚀 Быстрый старт

### 1. Создай бота
1. Напиши [@BotFather](https://t.me/BotFather) → `/newbot` → получи `BOT_TOKEN`
2. Скопируй `.env.example` → `.env` и вставь токен

```bash
cp .env.example .env
nano .env
```

### 2. Локальный запуск

```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python src/bot.py
```

Бот начнёт парсить GitHub и ответит в Telegram.

### 3. Docker

```bash
docker-compose up -d --build
docker logs -f vless-parser-bot
```

### 4. Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `BOT_TOKEN` | Токен от @BotFather | — |
| `ADMIN_ID` | Твой Telegram ID | 0 |
| `CHANNEL_ID` | Канал для автопостинга (`@channel`) | — |
| `CHECK_MODE` | `none` / `syntax` / `tcp` | `syntax` |
| `UPDATE_INTERVAL` | Интервал автообновления, мин | `30` |
| `PUBLIC_URL` | Для мини HTTP-сервера подписок | — |
| `PORT` | Порт HTTP | `8080` |

## 📱 Как подключить подписку

1. В боте нажми **⬛ Чёрные списки** или **⬜ Белые**
2. Нажми **📄 Получить файл .txt** — бот пришлёт 2 файла
3. Открой клиент:
   - **Happ** (iOS/Android/Win) → `+` → `Добавить из буфера` → вставь содержимое `*_base64.txt`
   - **Streisand** → `+` → `Import from Clipboard`
   - **v2rayNG** → `≡` → `Добавить подписку` → вставь ссылку/текст
   - **Hiddify** / **Throne** → `Добавить профиль` → `Вставить`
4. Нажми **Обновить подписку** → выбери сервер с меньшей задержкой → **Connect**

### Какую подписку выбрать?

- **Для обычных блокировок (YouTube, Discord):** `black_mobile` — 150 лучших, быстро.
- **Для белых списков (ничего не грузит кроме VK):** `white_cidr_checked` — VK/YA/CDN, самый надёжный. Если не хватает — `white_cidr_all`.
- **Хочешь всё сразу:** `/all` — бот соберёт групповую подписку.

## 🧠 Как работает парсер

```
GitHub raw (.txt) → fetch_text() → extract_configs(VLESS_REGEX) → validate (UUID, host:port) → dedup → save_subscription_files() → Telegram
```

- Поддерживает plain и base64 исходники (авто-декодирует)
- Игнорирует комментарии `# profile-title`
- Проверяет UUID v4, порт 1-65535
- Опционально TCP-чекает `host:port` (mode=tcp)

## 📂 Структура

```
vless-parser-bot/
├── src/
│   ├── bot.py          # Telegram бот (PTB v20)
│   ├── parser.py       # Парсинг GitHub + валидация
│   ├── subscription.py # Генерация подписок + QR
│   └── config.py       # Источники + тексты
├── data/               # Сгенерированные подписки (*.txt)
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 🔄 Автообновление и канал

Бот каждые `UPDATE_INTERVAL` минут:
- Перепарсит все источники
- Обновит файлы в `data/`
- Если задан `CHANNEL_ID` — отправит сводку в канал

## ⚠️ Важно

- Конфиги **публичные** — могут умереть за часы. Обновляй подписку в клиенте каждые 6-12 часов.
- Не заходи с VPN-IP на Госуслуги/банки — палишь сервер для всех.
- Для белых списков используй **только** белые подписки и включай маршрутизацию `RU-DIRECT`.
- Бот не логирует твои подписки.

## 🛠️ Расширение

Добавить новый источник — просто добавь URL в `src/config.py` → `SOURCES`:

```python
"my_source": {
    "name": "Мой источник",
    "description": "...",
    "urls": ["https://raw.githubusercontent.com/.../vless.txt"],
}
```

## 📄 Лицензия

MIT — делай что хочешь, но без гарантий.

---
Сделано для обхода блокировок в РФ. Подписывайся на [igareck/vpn-configs-for-russia](https://github.com/igareck/vpn-configs-for-russia) — первоисточник.
