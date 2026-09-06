import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "768223541") or 768223541)
# Доп. админы через запятую
_extra_admins = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = {ADMIN_ID}
if _extra_admins:
    for x in _extra_admins.split(","):
        try:
            ADMIN_IDS.add(int(x.strip()))
        except: pass
CHANNEL_ID = os.getenv("CHANNEL_ID", "")
CHECK_MODE = os.getenv("CHECK_MODE", "syntax")
UPDATE_INTERVAL = int(os.getenv("UPDATE_INTERVAL", "30"))
PUBLIC_URL = os.getenv("PUBLIC_URL", "")
PORT = int(os.getenv("PORT", "8080"))

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", os.getenv("GH_TOKEN", ""))
GITHUB_REPO = os.getenv("GITHUB_REPO", "xznexil3/crs-support-bot")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
GITHUB_SUB_PATH = os.getenv("GITHUB_SUB_PATH", "")

def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS

# === Источники ===
# igareck — база, + дополнительные подписки против БС
SOURCES = {
    "black_all": {
        "name": "Чёрные списки — VLESS",
        "description": "Весь трафик через VPN",
        "urls": [
            "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt",
        ],
    },
    "black_mobile": {
        "name": "Чёрные списки — Mobile",
        "description": "150 лучших для телефона",
        "urls": [
            "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS_mobile.txt",
        ],
    },
    "white_cidr_all": {
        "name": "Белые списки — CIDR ALL",
        "description": "Все белые подсети",
        "urls": [
            "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",
        ],
    },
    "white_cidr_checked": {
        "name": "Белые списки — VK / YA / CDN",
        "description": "Только VK, Yandex, CDNVideo, Beeline — самые стабильные",
        "urls": [
            "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-checked.txt",
        ],
    },
    "white_mobile": {
        "name": "Белые списки — Mobile",
        "description": "Для телефона, CIDR",
        "urls": [
            "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/Vless-Reality-White-Lists-Rus-Mobile.txt",
        ],
    },
    "white_sni": {
        "name": "Белые — SNI",
        "description": "Только Fake SNI",
        "urls": [
            "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt",
        ],
    },
    "ss_black": {
        "name": "Shadowsocks — Чёрные",
        "description": "SS, Trojan, Hysteria2 для чёрных",
        "urls": [
            "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_SS+All_RUS.txt",
        ],
    },
    # === Дополнительные подписки против БС (по твоему списку) ===
    "extra_zieng2": {
        "name": "Подписка от zieng2",
        "description": "Белые списки от zieng2",
        "urls": [
            "https://raw.githubusercontent.com/zieng2/wl/main/vless_universal.txt",
            "https://codeberg.org/zieng2/wl/raw/branch/main/vless_universal.txt",
            "https://gitlab.com/zieng2/wl/-/raw/main/vless_universal.txt",
        ],
    },
    "extra_etoneya_white": {
        "name": "Подписка от etoneya — белые",
        "description": "whitelist etoneya",
        "urls": [
            "https://etoneya.su/whitelist",
            "https://raw.githubusercontent.com/EtoNeYaProject/etoneyaproject.github.io/refs/heads/main/whitelist",
            "https://ety.twinkvibe.gay/whitelist",
            "https://etoneya.vercel.app/whitelist",
            "https://alley.serv00.net/whitelist",
        ],
    },
    "extra_etoneya_black": {
        "name": "Подписка от etoneya — чёрные",
        "description": "etoneya other/blacklist",
        "urls": [
            "https://etoneya.su/other",
            "https://etoneya.su/1",
            "https://raw.githubusercontent.com/EtoNeYaProject/etoneyaproject.github.io/refs/heads/main/1",
            "https://raw.githubusercontent.com/EtoNeYaProject/etoneyaproject.github.io/refs/heads/main/2",
        ],
    },
    "extra_bye2": {
        "name": "ByeWhiteLists 2.0",
        "description": "Подписка ByeWhiteLists 2.0",
        "urls": [
            "https://raw.githubusercontent.com/ByeWhiteLists/ByeWhiteLists2/refs/heads/main/ByeWhiteLists2.txt",
        ],
    },
    "extra_cid": {
        "name": "CID VPN",
        "description": "Подписка CID VPN — placeholder, замени url если есть актуальный",
        "urls": [
            # TODO: вставь актуальный raw url CID VPN, если есть
            # "https://raw.githubusercontent.com/.../cid.txt",
            "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/1.1.txt",
        ],
    },
    "extra_wrtrmmu": {
        "name": "Подписка от wrtrmmu",
        "description": "WARP / TURN VK Calls — placeholder",
        "urls": [
            # TODO: вставь raw от wrtrmmu
            "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/2.1.txt",
        ],
    },
    "extra_vercel": {
        "name": "Подписка от Vercel",
        "description": "Зеркало через Vercel",
        "urls": [
            "https://etoneya.vercel.app/whitelist",
            "https://etoneya.vercel.app/1",
            "https://raw.githubusercontent.com/AvenCores/goida-vpn-configs/refs/heads/main/githubmirror/26.txt",
        ],
    },
    "extra_bolt": {
        "name": "VPN bolt",
        "description": "Подписка VPN bolt — placeholder",
        "urls": [
            "https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/3.1.txt",
        ],
    },
    "extra_sbornik": {
        "name": "Сборник подписок против БС",
        "description": "Сборник: все белые + чёрные в одном месте",
        "urls": [
            "https://raw.githubusercontent.com/VAL41K/bypass-rkn-blocks/main/README.md",  # парсер вытянет vless из описания, если будут
        ],
    },
    "universal": {
        "name": "Универсальные VLESS",
        "description": "Фолбэк, если РФ-источники пустые",
        "urls": [
            "https://raw.githubusercontent.com/barry-far/V2ray-Config/main/Splitted-By-Protocol/vless.txt",
            "https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/main/V2Ray-Config-By-EbraSha.txt",
            "https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/main/protocols/vless.txt",
        ],
    },
}

GROUPS = {
    "black": ["black_all", "black_mobile", "ss_black", "extra_etoneya_black", "extra_bolt", "extra_vercel"],
    "white": ["white_cidr_all", "white_cidr_checked", "white_mobile", "white_sni", "extra_zieng2", "extra_etoneya_white", "extra_bye2", "extra_cid", "extra_wrtrmmu", "extra_sbornik"],
    "all": ["black_all", "black_mobile", "ss_black", "white_cidr_all", "white_cidr_checked", "white_mobile", "extra_zieng2", "extra_etoneya_white", "extra_bye2", "extra_etoneya_black"],
}

# Одна большая подписка = все спарсенные (белые + чёрные) вместе, но и раздельно
AGGREGATED_SUBS = {
    "BLACK_FULL": {
        "filename": "BLACK_FULL.txt",
        "profile_title": "Free VPN • Crimson — Black",
        "source_keys": ["black_all", "black_mobile", "ss_black", "extra_etoneya_black", "extra_bolt", "extra_vercel"],
        "description": "Чёрные списки",
    },
    "WHITE_FULL": {
        "filename": "WHITE_FULL.txt",
        "profile_title": "Free VPN • Crimson — White",
        "source_keys": ["white_cidr_all", "white_cidr_checked", "white_mobile", "white_sni", "extra_zieng2", "extra_etoneya_white", "extra_bye2", "extra_cid", "extra_wrtrmmu", "extra_sbornik"],
        "description": "Белые списки",
    },
    "FULL": {
        "filename": "FULL.txt",
        "profile_title": "Free VPN • Crimson — Full",
        "source_keys": ["black_all", "black_mobile", "ss_black", "white_cidr_all", "white_cidr_checked", "white_mobile", "white_sni", "extra_zieng2", "extra_etoneya_white", "extra_bye2", "extra_etoneya_black", "extra_cid", "extra_wrtrmmu", "extra_vercel", "extra_bolt", "extra_sbornik"],
        "description": "Полный список — все белые и чёрные вместе",
    },
}

# Для совместимости старые ключи FULL/COMBINED/BLACK_FULL/WHITE_FULL пусть указывают на новые
# COMBINED = FULL
AGGREGATED_SUBS["COMBINED"] = AGGREGATED_SUBS["FULL"]

WELCOME_TEXT = """<b>Free VPN • Crimson</b> — рабочие автообновляемые конфиги для вашего «суверенного» интернета.

• Два режима:
[⬛] Чёрные — весь трафик через VPN
[⬜] Белые — для жёстких ТСПУ, когда работает только VK / Яндекс

• Выбери кнопку:
• <b>Полный список</b> — одна большая ссылка (вставляешь 1 URL в клиент)
• <b>Белые / Чёрные</b> — раздельные подписки по типам
"""

HELP_TEXT = """<b>Free VPN • Crimson — помощь</b>

Нажми кнопку в меню:

<b>Мой профиль</b> — твой ID, статистика
<b>Белые списки</b> — подписка для белых ТСПУ (VK, Яндекс, CDN)
<b>Чёрные списки</b> — классический VPN для YouTube, Discord и т.д.
<b>Полный список</b> — всё вместе, одна RAW-ссылка
<b>Помощь</b> — это окно

<b>Как подключить:</b>
1. Нажми <b>Полный список</b> или <b>Белые / Чёрные</b>
2. Скопируй ссылку вида <code>https://raw.githubusercontent.com/.../FULL.txt</code>
3. Вставь как <b>URL подписки</b> в Happ / Streisand / v2rayNG / Hiddify / Throne / NekoBox
4. Обнови подписку → выбери сервер с меньшей задержкой → Connect

Клиенты: <b>Happ, Streisand, v2rayNG, Hiddify, Throne, NekoRay, Karing, Exclave</b>
Автообновление в клиенте — раз в час.

Вопросы — @wtfparsbot
"""

SOURCES_TEXT = """<b>Free VPN • Crimson — источники</b>
Основное: igareck, zieng2, etoneya, ByeWhiteLists 2.0, CID, wrtrmmu, Vercel, VPN bolt + зеркала.
Полный список зеркал — в конфиге бота (src/config.py → SOURCES).
"""
