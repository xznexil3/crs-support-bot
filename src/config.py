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

<b>Команды:</b>
/black — Чёрные списки (VLESS, 91-150 шт)
/black_mobile — 150 лучших для телефона
/white — Белые списки (все варианты CIDR)
/white_cidr — Белые CIDR ALL (~30 шт)
/white_checked — VK/YA/CDN/Beeline (~10 шт, самые надёжные)
/white_mobile — Белые для телефона
/all — Всё вместе
/sources — Показать все источники GitHub
/check — Проверка твоего vless:// ссылку
/update — Обновить кэш вручную
/sub — Мои подписки (файлы)

<b>Как подключить:</b>
1. Скопируй подписку (base64-ссылку или raw-ссылку)
2. Вставь в клиент: <b>Happ / Streisand / v2rayNG / NekoRay / Throne / Hiddify</b>
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
