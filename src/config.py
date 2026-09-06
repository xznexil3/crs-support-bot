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

# === Premium эмодзи (custom_emoji) — для @wtfparsbot ===
# Бот может отправлять их бесплатно, но анимация покажется только если у бота куплен collectible username на Fragment.
# До покупки — показывается fallback Unicode внутри тега, всё работает без падений.
# ID проверены через getCustomEmojiStickers (200 OK)
PREMIUM = {
    "fire_crimson": '<tg-emoji emoji-id="5987683322615041517">🔥</tg-emoji>',  # CrimsonEmoji — фирменный огонь Crimson
    "fire": '<tg-emoji emoji-id="5424972470023104089">🔥</tg-emoji>',  # NewsEmoji
    "rocket": '<tg-emoji emoji-id="5445284980978621387">🚀</tg-emoji>',  # RestrictedEmoji
    "sparkles": '<tg-emoji emoji-id="5325547803936572038">✨</tg-emoji>',
    "diamond": '<tg-emoji emoji-id="5427168083074628963">💎</tg-emoji>',
    "shield": '<tg-emoji emoji-id="5251203410396458957">🛡</tg-emoji>',
    "lightning": '<tg-emoji emoji-id="5456140674028019486">⚡️</tg-emoji>',
    "ghost": '<tg-emoji emoji-id="5371017798065592581">👻</tg-emoji>',
    "heart": '<tg-emoji emoji-id="5377860677400536988">❤️</tg-emoji>',
    "black_heart": '<tg-emoji emoji-id="5449692618151695997">🖤</tg-emoji>',
    "thumbsup": '<tg-emoji emoji-id="5368324170671202286">👍</tg-emoji>',
    "warning": '<tg-emoji emoji-id="5420323339723881652">⚠️</tg-emoji>',
    "cross": '<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji>',
    "computer": '<tg-emoji emoji-id="5877565553761062314">💻</tg-emoji>',
    "crystal": '<tg-emoji emoji-id="5471952986970267163">💎</tg-emoji>',  # Restricted diamond
}

def pe(name: str, fallback: str = "") -> str:
    """Быстрый доступ к premium emoji с fallback"""
    return PREMIUM.get(name) or fallback

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

WELCOME_TEXT = f"""{PREMIUM['fire_crimson']} <b>Free VPN • Crimson</b> — рабочие автообновляемые конфиги для вашего «суверенного» интернета.

{PREMIUM['black_heart']} Два режима:
{PREMIUM['shield']} <b>Чёрные</b> — весь трафик через VPN
{PREMIUM['ghost']} <b>Белые</b> — для жёстких ТСПУ, когда работает только VK / Яндекс

{PREMIUM['sparkles']} Режимы протоколов внутри каждого списка:
{PREMIUM['lightning']} <b>VLESS</b> · {PREMIUM['shield']} <b>Trojan</b> · {PREMIUM['ghost']} <b>Shadowsocks</b> · {PREMIUM['computer']} <b>VMess</b> · {PREMIUM['rocket']} <b>Hysteria2</b>

{PREMIUM['diamond']} Выбери кнопку:
• <b>Полный список</b> — одна большая ссылка (делим по 300)
• <b>Белые / Чёрные</b> — выбери протокол, получи пакеты по 300
"""

HELP_TEXT = f"""<b>{PREMIUM['fire_crimson']} Free VPN • Crimson — помощь</b> {PREMIUM['sparkles']}

Нажми кнопку в меню:

{PREMIUM['thumbsup']} <b>Мой профиль</b> — твой ID
{PREMIUM['ghost']} <b>Белые списки</b> — для ТСПУ: выбор протокола → пакеты по 300 (VLESS/Trojan/SS/VMess/Hy2)
{PREMIUM['shield']} <b>Чёрные списки</b> — классический VPN: выбор протокола → пакеты по 300
{PREMIUM['diamond']} <b>Полный список</b> — всё вместе: выбор протокола → пакеты по 300
{PREMIUM['computer']} <b>Помощь</b> — это окно

<b>{PREMIUM['rocket']} Протоколы (режимы):</b>
• {PREMIUM['lightning']} <b>VLESS</b> — основной, Reality, работает везде
• {PREMIUM['shield']} <b>Trojan</b> — для Sing-box / Clash
• {PREMIUM['ghost']} <b>Shadowsocks</b> — SS
• {PREMIUM['computer']} <b>VMess</b> — старый V2Ray
• {PREMIUM['rocket']} <b>Hysteria2 / Hy2</b> — скоростной QUIC {PREMIUM['sparkles']}

<b>{PREMIUM['diamond']} Как подключить:</b>
1. Нажми <b>Белые / Чёрные / Полный</b> → выбери протокол → выбери пакет (1..N по 300)
2. Скопируй ссылку вида <code>https://raw.githubusercontent.com/.../FULL_VLESS_1.txt</code>
3. Вставь как <b>URL подписки</b> в Happ / Streisand / v2rayNG / Hiddify / Throne / NekoBox
4. Обнови подписку → выбери сервер → Connect

Клиенты: <b>Happ, Streisand, v2rayNG, Hiddify, Throne, NekoRay, Karing, Exclave</b>
Автообновление — раз в час. Все файлы по 300 для стабильной загрузки.

{PREMIUM['heart']} Вопросы — @wtfparsbot {PREMIUM['black_heart']}
"""

SOURCES_TEXT = f"""<b>{PREMIUM['diamond']} Free VPN • Crimson — источники</b> {PREMIUM['sparkles']}
Основное: igareck, zieng2, etoneya, ByeWhiteLists 2.0, CID, wrtrmmu, Vercel, VPN bolt + зеркала.
Полный список зеркал — в конфиге бота (src/config.py → SOURCES).

{PREMIUM['computer']} Авто-очистка: {PREMIUM['warning']} приватные IP, {PREMIUM['cross']} битые UUID/порт, дубликаты — удаляются.
{PREMIUM['thumbsup']} Всё делится по протоколам и по 300.
"""
