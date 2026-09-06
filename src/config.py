import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or 0)
CHANNEL_ID = os.getenv("CHANNEL_ID", "")
CHECK_MODE = os.getenv("CHECK_MODE", "syntax")  # none | syntax | tcp
UPDATE_INTERVAL = int(os.getenv("UPDATE_INTERVAL", "30"))
PUBLIC_URL = os.getenv("PUBLIC_URL", "")
PORT = int(os.getenv("PORT", "8080"))

# === GitHub RAW публикация ===
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", os.getenv("GH_TOKEN", ""))  # твой ghp_... для пуша подписок
GITHUB_REPO = os.getenv("GITHUB_REPO", "xznexil3/vless-parser-bot")  # куда пушить
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
# Папка в репозитории куда класть сгенерированные подписки (raw ссылка будет .../branch/<path>)
GITHUB_SUB_PATH = os.getenv("GITHUB_SUB_PATH", "")  # пусто = в корень, или "subs" / "subscription"

# === Источники GitHub ===
# Основной репозиторий для РФ - igareck/vpn-configs-for-russia
SOURCES = {
    "black_all": {
        "name": "⬛ Чёрные списки — VLESS (все конфиги)",
        "description": "Полный VPN туннель — весь трафик через VLESS Reality. Для обхода блокировок по чёрным спискам.",
        "urls": [
            "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt",
        ],
        "count_label": "91+ конфигов",
    },
    "black_mobile": {
        "name": "📱 Чёрные списки — VLESS Mobile (150 лучших)",
        "description": "Топ-150 самых быстрых VLESS для телефона. Оптимизировано для мобильных клиентов (Happ, v2rayNG, Streisand).",
        "urls": [
            "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS_mobile.txt",
        ],
        "count_label": "150 конфигов",
    },
    "white_cidr_all": {
        "name": "⬜ Белые списки CIDR — ВСЕ",
        "description": "Обход ЖЁСТКИХ белых списков по CIDR-фильтрации. Содержит все проверенные белые подсети от разных хостеров.",
        "urls": [
            "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",
        ],
        "count_label": "~30 конфигов",
    },
    "white_cidr_checked": {
        "name": "⬜ Белые списки CIDR — VK/YA/CDN/Beeline",
        "description": "Только проверенные белые подсети: VK, Yandex, CDNVideo, Beeline. Самый надёжный вариант для белых списков.",
        "urls": [
            "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-checked.txt",
        ],
        "count_label": "~10 конфигов",
    },
    "white_mobile": {
        "name": "📱 Белые списки — Mobile 150",
        "description": "150 лучших конфигов для белых списков, оптимизировано для телефона.",
        "urls": [
            "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/Vless-Reality-White-Lists-Rus-Mobile.txt",
        ],
        "count_label": "~28 конфигов",
    },
    "white_sni": {
        "name": "⬜ Белые списки SNI (Fake SNI)",
        "description": "Только Fake SNI. CIDR не обходит — для лёгких DPI.",
        "urls": [
            "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt",
        ],
        "count_label": "переменно",
    },
    "ss_black": {
        "name": "🔐 Shadowsocks — Чёрные списки",
        "description": "Shadowsocks + Trojan + Hysteria для чёрных списков. Альтернатива VLESS.",
        "urls": [
            "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_SS+All_RUS.txt",
        ],
        "count_label": "~51 конфиг",
    },
    # Универсальные fallback-источники (если основные пустые)
    "universal": {
        "name": "🌍 Универсальные VLESS",
        "description": "Фолбэк-источники если РФ-репозитории недоступны.",
        "urls": [
            "https://raw.githubusercontent.com/barry-far/V2ray-Config/main/Splitted-By-Protocol/vless.txt",
            "https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/main/V2Ray-Config-By-EbraSha.txt",
            "https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/main/protocols/vless.txt",
        ],
        "count_label": "100+",
    },
}

# Группы для команд
GROUPS = {
    "black": ["black_all", "black_mobile"],
    "white": ["white_cidr_all", "white_cidr_checked", "white_mobile", "white_sni"],
    "all": ["black_all", "black_mobile", "white_cidr_all", "white_cidr_checked", "white_mobile", "ss_black"],
}

# === АГРЕГИРОВАННЫЕ RAW ПОДПИСКИ (одна большая ссылка) ===
# Каждая собирается из указанных категорий, кладётся в GitHub как один файл,
# и отдаётся как raw.githubusercontent.com/.../FILE.txt — вставляешь 1 ссылку в клиент.
AGGREGATED_SUBS = {
    "BLACK_FULL": {
        "filename": "BLACK_FULL.txt",  # будет https://raw.githubusercontent.com/xznexil3/vless-parser-bot/main/BLACK_FULL.txt
        "profile_title": "🏴 ЧЕРНЫЕ СПИСКИ 🏴 BLACK LISTS | Полная • Full | SS, Hy2, Vmess, Trojan",
        "source_keys": ["black_all", "black_mobile", "ss_black"],
        "description": "Все чёрные списки — одна большая подписка (как в примере igareck)",
    },
    "WHITE_FULL": {
        "filename": "WHITE_FULL.txt",
        "profile_title": "🏳️ БЕЛЫЕ СПИСКИ 🏳️ WHITE LISTS | Полная • Full | CIDR",
        "source_keys": ["white_cidr_all", "white_cidr_checked", "white_mobile"],
        "description": "Все белые CIDR — одна подписка для жёстких ТСПУ",
    },
    "COMBINED": {
        "filename": "COMBINED.txt",
        "profile_title": "🌐 COMBINED | Чёрные + Белые | All-in-One",
        "source_keys": ["black_all", "black_mobile", "ss_black", "white_cidr_all", "white_cidr_checked", "white_mobile"],
        "description": "Всё вместе — чёрные + белые в одном файле",
    },
    "UNIVERSAL_PLUS": {
        "filename": "UNIVERSAL_PLUS.txt",
        "profile_title": "🌍 UNIVERSAL PLUS | Все источники + Мировые VLESS",
        "source_keys": ["black_all", "black_mobile", "ss_black", "white_cidr_all", "white_cidr_checked", "white_mobile", "universal"],
        "description": "Все РФ + мировые VLESS (10k+) — максимальная подписка",
    },
}

# Тексты
WELCOME_TEXT = """
🛰️ <b>VLESS Парсер Бот</b> — рабочие конфиги для РФ

Жми кнопки ниже — никаких «/команд» не нужно. Я парсю <b>рабочие VLESS Reality</b> прямо с GitHub и отдаю их как <b>RAW-подписку</b> одной ссылкой.

<b>Два режима:</b>
⬛ <b>Чёрные</b> — весь трафик через VPN (YouTube, Discord, ChatGPT)
⬜ <b>Белые</b> — для жёстких ТСПУ, когда работает только VK/Яндекс

👇 <b>Выбери кнопку:</b>
🔥 <b>RAW</b> — одна большая ссылка с шапкой как у igareck (вставляешь 1 URL в клиент)
📂 Категории — отдельные файлы по типам
"""

HELP_TEXT = """
<b>📖 Как пользоваться — только кнопки</b>

<b>Главное меню (/start):</b>
🔥 <b>RAW ЧЁРНЫЕ FULL</b> — 🏴 Чёрные списки, полная подписка <code>SS, Hy2, Vmess, Trojan</code> с шапкой igareck
🔥 <b>RAW БЕЛЫЕ FULL</b> — 🏳️ Белые CIDR для обхода белых списков
🚀 <b>RAW COMBINED</b> — всё вместе (чёрные + белые)
🌍 <b>UNIVERSAL PLUS</b> — всё + мировые VLESS 10k+

📂 <b>Отдельные категории:</b> нажми <code>⬛ Чёрные VLESS</code>, <code>📱 Mobile</code>, <code>⬜ Белые</code> — бот пришлёт 2 файла: <code>.txt</code> и <code>_base64.txt</code>

<b>Внутри категории:</b>
📄 <i>Получить файл</i> — прислать .txt / base64
📋 <i>Скопировать base64</i> — текст подписки
🔍 <i>Показать 5 примеров</i> — превью конфигов
📷 <i>QR</i> — QR первого конфига
⬅️ <i>Назад</i> — в меню

<b>Как подключить RAW:</b>
1. Нажми кнопку RAW → скопируй ссылку <code>https://raw.githubusercontent.com/.../BLACK_FULL.txt</code>
2. Вставь как <b>URL подписки</b> в Happ / Streisand / v2rayNG / Hiddify / Throne / NekoRay
3. Обнови подписку → выбери сервер с пингом поменьше → Connect

<b>Клиенты:</b>
Android: v2rayNG, v2rayTun, Happ, Hiddify
iOS: Streisand, V2Box, Happ, Shadowrocket
Win: Hiddify, Throne, NekoRay
Linux: Throne, Hiddify, V2rayA

⚠️ Конфиги публичные — обновляй подписку каждые 6-12ч. Не свети один IP на Госуслугах + VPN.
"""

SOURCES_TEXT = """
<b>🔗 Источники GitHub</b>

Основной (РФ): <code>igareck/vpn-configs-for-russia</code>
• BLACK_VLESS_RUS.txt — чёрные VLESS
• BLACK_VLESS_RUS_mobile.txt — 150 лучших для телефона
• WHITE-CIDR-RU-all.txt — белые CIDR все
• WHITE-CIDR-RU-checked.txt — белые VK/YA/CDN/Beeline
• WHITE-SNI-RU-all.txt — Fake SNI
• BLACK_SS+All_RUS.txt — Shadowsocks

Fallback:
• barry-far/V2ray-Config (Splitted-By-Protocol/vless.txt)
• 0xRadikal/Free-v2ray-Configs
• ebrasha/free-v2ray-public-list

Обновляется каждые 15-30 мин на GitHub Actions. Бот проверяет синтаксис + TCP-доступность.
"""
