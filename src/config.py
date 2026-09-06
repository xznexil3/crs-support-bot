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

Я парсю <b>рабочие VLESS Reality</b> конфиги прямо с GitHub и отдаю их в виде <b>подписок</b>.

<b>Два режима:</b>
⬛ <b>Чёрные списки</b> — классический VPN, весь трафик через сервер. Для YouTube, Discord, X/Twitter, ChatGPT.
⬜ <b>Белые списки</b> — обход ЖЁСТКИХ блокировок (ТСПУ), когда работают только VK/Госуслуги/Яндекс. Только такие сервера и подойдут.

Выбери что тебе нужно 👇
"""

HELP_TEXT = """
<b>📖 Помощь — как пользоваться</b>

<b>🔥 RAW подписки (одна ссылка — вся категория):</b>
/raw — все RAW ссылки (чёрные/белые/combined)
/raw_black — ЧЁРНЫЕ FULL (SS, Hy2, Vmess, Trojan, VLESS) — шапка как у igareck
/raw_white — БЕЛЫЕ FULL (CIDR)
/raw_combined — Всё вместе

<b>Отдельные категории:</b>
/black — Чёрные списки (VLESS, 91-150 шт)
/black_mobile — 150 лучших для телефона
/white — Белые списки (все варианты CIDR)
/white_cidr — Белые CIDR ALL (~30 шт)
/white_checked — VK/YA/CDN/Beeline (~10 шт, самые надёжные)
/white_mobile — Белые для телефона
/all — Всё вместе (групповой файл)
/sources — Показать все источники GitHub
/check — Проверка твоего vless:// ссылку
/update — Обновить кэш вручную
/sub — Мои подписки (файлы)
/stats — Статистика

<b>Как подключить RAW:</b>
1. Скопируй RAW ссылку: <code>https://raw.githubusercontent.com/.../BLACK_FULL.txt</code>
2. Вставь в клиент как <b>URL подписки</b>: <b>Happ / Streisand / v2rayNG / NekoRay / Throne / Hiddify</b>
3. Обнови подписку в клиенте → выбери сервер с минимальной задержкой → Connect

<b>Рекомендуемые клиенты:</b>
• <b>Android:</b> v2rayNG, v2rayTun, Happ, Hiddify
• <b>iOS:</b> Streisand, V2Box, Happ, Shadowrocket
• <b>Windows:</b> Hiddify, Throne, NekoRay, v2rayN
• <b>Linux:</b> Throne, Hiddify, V2rayA

⚠️ <i>Конфиги публичные — меняй их каждые 6-12 часов. Не используй один IP для белых сервисов (госуслуги, банки) + VPN — палишь сервер.</i>
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
