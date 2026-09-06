import os
import asyncio
import logging
import base64
import textwrap
from datetime import datetime, timezone, timedelta
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode

import config
from parser import fetch_category, fetch_all, is_valid_vless, parse_vless_info
from subscription import save_subscription_files, generate_qr_bytes, get_subscription_stats
import aiohttp
try:
    from health import start_health_server
except ImportError:
    start_health_server = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Кэш последних результатов
CACHE = {}
LAST_UPDATE = None

MSK = timezone(timedelta(hours=3))

def msk_time():
    return datetime.now(MSK).strftime("%d.%m.%Y %H:%M МСК")

# ---------- Helpers ----------

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬛ Чёрные списки (VLESS)", callback_data="get:black_all"),
         InlineKeyboardButton("📱 Чёрные Mobile 150", callback_data="get:black_mobile")],
        [InlineKeyboardButton("⬜ Белые CIDR ALL", callback_data="get:white_cidr_all"),
         InlineKeyboardButton("⬜ Белые VK/YA/CDN", callback_data="get:white_cidr_checked")],
        [InlineKeyboardButton("📱 Белые Mobile", callback_data="get:white_mobile"),
         InlineKeyboardButton("⬜ SNI (Fake)", callback_data="get:white_sni")],
        [InlineKeyboardButton("🌍 ВСЁ ВМЕСТЕ (ALL)", callback_data="get:all"),
         InlineKeyboardButton("🔐 Shadowsocks", callback_data="get:ss_black")],
        [InlineKeyboardButton("🔗 Источники", callback_data="sources"),
         InlineKeyboardButton("❓ Помощь", callback_data="help")],
        [InlineKeyboardButton("🔄 Обновить кэш", callback_data="refresh")],
    ])

def category_keyboard(category_key: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Скопировать base64", callback_data=f"copy:{category_key}"),
         InlineKeyboardButton("📄 Получить файл .txt", callback_data=f"file:{category_key}")],
        [InlineKeyboardButton("🔍 Показать 5 примеров", callback_data=f"preview:{category_key}"),
         InlineKeyboardButton("📷 QR подписки", callback_data=f"qr:{category_key}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="home")],
    ])

async def update_cache(categories=None, mode=None):
    global CACHE, LAST_UPDATE
    mode = mode or config.CHECK_MODE
    if categories is None:
        categories = list(config.SOURCES.keys())
    logger.info(f"Updating cache for {categories} mode={mode}")
    result = await fetch_all(mode=mode, categories=categories)
    # Сохраняем файлы
    for key, data in result.items():
        configs = data.get("configs", [])
        title = config.SOURCES.get(key, {}).get("name", key)
        if configs:
            try:
                save_subscription_files(str(DATA_DIR), key, configs, title)
            except Exception as e:
                logger.error(f"save error {key}: {e}")
        CACHE[key] = data
    LAST_UPDATE = datetime.now(MSK)
    return result

def get_cached(category_key: str):
    return CACHE.get(category_key)

def format_category_message(data: dict) -> str:
    name = data.get("name", data.get("key"))
    desc = data.get("description", "")
    configs = data.get("configs", [])
    total = data.get("raw_total", len(configs))
    errors = data.get("errors", [])
    stats = get_subscription_stats(configs)
    
    # Формируем текст
    lines = [
        f"<b>{name}</b>",
        f"<i>{desc}</i>",
        "",
        f"✅ <b>Готово:</b> {stats}",
        f"🔍 Проверено синтаксисом: {total} → {len(configs)} валидных",
        f"🕐 Обновлено: {msk_time()}",
        f"📦 Файлы: <code>{data.get('key')}.txt</code> и <code>{data.get('key')}_base64.txt</code>",
    ]
    if not configs:
        lines.append("")
        lines.append("⚠️ <b>Сейчас пусто.</b> На GitHub нет рабочих конфигов в этой категории (бывает ночью). Попробуй другую категорию или /all")
    if errors:
        lines.append("")
        lines.append(f"⚠️ Ошибки источников: {', '.join(errors[:2])}")
    
    lines.append("")
    lines.append("👇 <b>Как подключить:</b> нажми «📄 Получить файл» или «📋 Скопировать base64» и вставь в Happ / Hiddify / Streisand / v2rayNG → Обновить подписку")
    lines.append("")
    lines.append("💡 Совет: для <b>белых списков</b> используй только VK/YA/CDN — они самые живучие. Для <b>чёрных</b> — black_mobile (топ-150).")
    
    return "\n".join(lines)

# ---------- Handlers ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        config.WELCOME_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=main_keyboard()
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        config.HELP_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ В меню", callback_data="home")]])
    )

async def sources_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        config.SOURCES_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ В меню", callback_data="home")]])
    )

async def update_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🔄 Обновляю кэш с GitHub... (10-20 сек)")
    await update_cache()
    await msg.edit_text(f"✅ Кэш обновлён! {msk_time()}\nВсего категорий: {len(CACHE)}", reply_markup=main_keyboard())

async def get_command_factory(category_key: str, group_keys=None):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Если группа (black/white/all)
        if group_keys:
            await handle_group(update, group_keys)
            return
        # одиночная категория
        data = get_cached(category_key)
        if not data or not data.get("configs"):
            wait = await update.message.reply_text(f"⏳ Гружу <b>{category_key}</b> с GitHub...", parse_mode=ParseMode.HTML)
            await update_cache(categories=[category_key])
            data = get_cached(category_key)
            try:
                await wait.delete()
            except: pass
        if not data:
            await update.message.reply_text("❌ Ошибка загрузки. Попробуй /update")
            return
        text = format_category_message(data)
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=category_keyboard(category_key))
        # Автоматом шлём файл если есть конфиги
        if data.get("configs"):
            await send_files(update, category_key, data)
    return handler

async def handle_group(update: Update, group_keys):
    # Собираем все конфиги группы в один файл
    group_name = " + ".join(group_keys)
    msg = await update.message.reply_text(f"⏳ Собираю группу <b>{group_name}</b>...", parse_mode=ParseMode.HTML)
    # Убедиться что кэш есть
    missing = [k for k in group_keys if k not in CACHE or not CACHE[k].get("configs")]
    if missing:
        await update_cache(categories=missing)
    all_configs = []
    seen = set()
    for k in group_keys:
        d = CACHE.get(k, {})
        for c in d.get("configs", []):
            if c not in seen:
                seen.add(c)
                all_configs.append(c)
    if not all_configs:
        await msg.edit_text("⚠️ В группе сейчас нет конфигов. Попробуй позже или /update")
        return
    # Сохраняем групповой файл
    title = f"GROUP {'+'.join(group_keys)}"
    plain_path, b64_path, plain_content, b64_content = save_subscription_files(str(DATA_DIR), "GROUP_" + "_".join(group_keys), all_configs, title)
    
    # Отправляем
    await msg.delete()
    text = (
        f"<b>📦 Группа: {', '.join([config.SOURCES[k]['name'] for k in group_keys])}</b>\n"
        f"✅ Собрано: <b>{len(all_configs)} уникальных VLESS</b>\n"
        f"🕐 {msk_time()}\n\n"
        f"Файл ниже — просто добавь его как подписку в клиент.\n"
        f"Или скопируй base64 из файла <code>GROUP_..._base64.txt</code>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    # Файлы
    try:
        await update.message.reply_document(document=open(plain_path, "rb"), filename=f"GROUP_{'_'.join(group_keys)}.txt", caption=f"GROUP {len(all_configs)} configs • {msk_time()}")
        await update.message.reply_document(document=open(b64_path, "rb"), filename=f"GROUP_{'_'.join(group_keys)}_base64.txt", caption="Base64 подписка — вставь содержимое как URL подписки или декодируй")
        # Шлём первые 3000 символов base64 как текст (если короткий)
        if len(b64_content) < 4000:
            await update.message.reply_text(f"<code>{b64_content[:4000]}</code>", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(f"Base64 слишком длинный ({len(b64_content)} симв). Используй файл выше.\nПервые 500 симв:\n<code>{b64_content[:500]}...</code>", parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(e)
        await update.message.reply_text(f"Ошибка отправки файлов: {e}")

async def send_files(update_or_query, category_key: str, data: dict):
    configs = data.get("configs", [])
    if not configs:
        return
    plain_path = DATA_DIR / f"{category_key}.txt"
    b64_path = DATA_DIR / f"{category_key}_base64.txt"
    # Если файлов нет — создаём
    if not plain_path.exists():
        save_subscription_files(str(DATA_DIR), category_key, configs, data.get("name", category_key))
    
    # Для CallbackQuery — используем query.message, для Command — update.message
    msg_target = update_or_query.message if hasattr(update_or_query, "message") and update_or_query.message else update_or_query
    # Определяем куда слать
    try:
        if hasattr(update_or_query, "callback_query") and update_or_query.callback_query:
            chat = update_or_query.callback_query.message
            await chat.reply_document(document=open(plain_path, "rb"), filename=f"{category_key}.txt", caption=f"{data.get('name')} • {len(configs)} configs • {msk_time()}")
            await chat.reply_document(document=open(b64_path, "rb"), filename=f"{category_key}_base64.txt", caption="Base64 подписка — скопируй содержимое и вставь в клиент как подписку")
        else:
            await msg_target.reply_document(document=open(plain_path, "rb"), filename=f"{category_key}.txt", caption=f"{data.get('name')} • {len(configs)} configs • {msk_time()}")
            await msg_target.reply_document(document=open(b64_path, "rb"), filename=f"{category_key}_base64.txt", caption="Base64 подписка")
    except Exception as e:
        logger.error(f"send files error: {e}")

async def check_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "🔍 <b>Проверка VLESS</b>\nОтправь ссылку после команды:\n<code>/check vless://uuid@host:port?type=tcp&security=reality#name</code>",
            parse_mode=ParseMode.HTML
        )
        return
    link = " ".join(context.args).strip()
    if not link.startswith("vless://"):
        await update.message.reply_text("❌ Это не vless:// ссылка. Пришли именно vless://")
        return
    ok, reason = is_valid_vless(link)
    info = parse_vless_info(link)
    if ok:
        text = (
            f"✅ <b>Валидный VLESS</b>\n"
            f"🏷️ Имя: <code>{info.get('remark')}</code>\n"
            f"🌐 Хост: <code>{info.get('host')}:{info.get('port')}</code>\n"
            f"🔑 UUID: <code>{info.get('uuid')}</code>\n"
            f"🛡️ SNI: <code>{info.get('sni') or '—'}</code>\n"
            f"🔒 Security: <code>{info.get('security') or '—'}</code>\n"
            f"📡 Type: <code>{info.get('type') or '—'}</code>\n\n"
            f"Попробую TCP-проверку..."
        )
        msg = await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        # TCP check
        import asyncio
        try:
            host = info.get("host")
            port = int(info.get("port"))
            reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=4)
            writer.close()
            try: await writer.wait_closed()
            except: pass
            await msg.edit_text(text + "\n✅ <b>TCP доступен</b> — порт открыт", parse_mode=ParseMode.HTML)
        except Exception as e:
            await msg.edit_text(text + f"\n⚠️ <b>TCP недоступен</b>: {e}\n(сервер может блокировать ICMP/TCP с GitHub, но работать у тебя)", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"❌ <b>Невалидный VLESS</b>\nПричина: {reason}\n\nПроверь что ссылка полная и не обрезана.", parse_mode=ParseMode.HTML)

# ---------- Callback Query Handler ----------

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "home":
        await query.message.edit_text(config.WELCOME_TEXT, parse_mode=ParseMode.HTML, reply_markup=main_keyboard())
        return
    if data == "help":
        await query.message.reply_text(config.HELP_TEXT, parse_mode=ParseMode.HTML)
        return
    if data == "sources":
        await query.message.reply_text(config.SOURCES_TEXT, parse_mode=ParseMode.HTML)
        return
    if data == "refresh":
        await query.message.edit_text("🔄 Обновляю кэш с GitHub... 15 сек")
        await update_cache()
        await query.message.edit_text(f"✅ Кэш обновлён! {msk_time()}", reply_markup=main_keyboard())
        return
    
    if data.startswith("get:"):
        key = data.split(":", 1)[1]
        if key == "all":
            # группа all
            await query.message.delete()
            # создаём фейковый update объект для handle_group
            class FakeUpd:
                def __init__(self, q):
                    self.message = q.message
            await handle_group(FakeUpd(query), config.GROUPS["all"])
            return
        # одиночная категория
        cat_data = get_cached(key)
        if not cat_data or not cat_data.get("configs"):
            await query.message.edit_text(f"⏳ Гружу <b>{config.SOURCES.get(key, {}).get('name', key)}</b>...", parse_mode=ParseMode.HTML)
            await update_cache(categories=[key])
            cat_data = get_cached(key)
        if not cat_data:
            await query.message.edit_text("❌ Ошибка. Попробуй ещё раз.")
            return
        text = format_category_message(cat_data)
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=category_keyboard(key))
        if cat_data.get("configs"):
            await send_files(query, key, cat_data)
        return
    
    if data.startswith("file:"):
        key = data.split(":", 1)[1]
        cat_data = get_cached(key)
        if not cat_data or not cat_data.get("configs"):
            await query.message.reply_text("⚠️ Нет данных. Нажми Обновить.")
            return
        await send_files(query, key, cat_data)
        await query.answer("Файлы отправлены 📄")
        return
    
    if data.startswith("copy:"):
        key = data.split(":", 1)[1]
        cat_data = get_cached(key)
        if not cat_data or not cat_data.get("configs"):
            await query.message.reply_text("⚠️ Пусто.")
            return
        b64_path = DATA_DIR / f"{key}_base64.txt"
        if not b64_path.exists():
            await query.message.reply_text("Файл не найден, обнови кэш.")
            return
        b64 = open(b64_path, encoding="utf-8").read().strip()
        # Telegram лимит 4096
        if len(b64) < 3900:
            await query.message.reply_text(f"📋 <b>Base64 подписка {key}:</b>\n<code>{b64}</code>\n\nСкопируй и вставь в клиент как URL подписки (или декодируй).", parse_mode=ParseMode.HTML)
        else:
            # Шлём как документ + превью
            await query.message.reply_document(document=open(b64_path, "rb"), filename=f"{key}_base64.txt", caption=f"Base64 подписка {key} • {len(b64)} симв • скопируй содержимое файла")
            await query.message.reply_text(f"Подписка слишком длинная для сообщения ({len(b64)} симв). Отправил файлом выше.\nПревью:\n<code>{b64[:800]}...</code>", parse_mode=ParseMode.HTML)
        return
    
    if data.startswith("preview:"):
        key = data.split(":", 1)[1]
        cat_data = get_cached(key)
        if not cat_data or not cat_data.get("configs"):
            await query.message.reply_text("Пусто.")
            return
        configs = cat_data["configs"][:5]
        text = f"<b>🔍 Примеры {key} (5 из {len(cat_data['configs'])}):</b>\n\n"
        for i, c in enumerate(configs, 1):
            info = parse_vless_info(c)
            text += f"{i}. <code>{c[:90]}...</code>\n   → {info.get('remark')} | {info.get('host')}:{info.get('port')} | SNI:{info.get('sni') or '—'}\n\n"
        text += "<i>Полный список — в файле .txt</i>"
        await query.message.reply_text(text, parse_mode=ParseMode.HTML)
        return
    
    if data.startswith("qr:"):
        key = data.split(":", 1)[1]
        cat_data = get_cached(key)
        if not cat_data or not cat_data.get("configs"):
            await query.message.reply_text("Пусто.")
            return
        # QR делаем из base64 подписки, но если длинная — из первого конфига
        b64_path = DATA_DIR / f"{key}_base64.txt"
        content = ""
        if b64_path.exists():
            b64 = open(b64_path, encoding="utf-8").read().strip()
            # QR не вместит 10к символов, поэтому даём ссылку на raw github как fallback
            # Но лучше даём первый конфиг
            if len(b64) > 2000:
                content = cat_data["configs"][0]
                caption = f"QR первого конфига из {key} (подписка слишком длинная для QR)"
            else:
                content = b64
                caption = f"QR подписки {key} (base64)"
        else:
            content = cat_data["configs"][0]
            caption = f"QR первого конфига {key}"
        try:
            qr_bytes = generate_qr_bytes(content)
            await query.message.reply_photo(photo=qr_bytes, caption=caption)
        except Exception as e:
            await query.message.reply_text(f"Ошибка QR: {e}")
        return

# Обработка просто присланного vless:// в личку — автопроверка
async def message_vless_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if "vless://" in text:
        # берём первую ссылку
        import re
        m = re.search(r'vless://[^\s]+', text)
        if m:
            link = m.group(0)
            ok, reason = is_valid_vless(link)
            info = parse_vless_info(link)
            if ok:
                await update.message.reply_text(
                    f"🔍 Нашёл VLESS:\n🏷️ {info.get('remark')}\n🌐 {info.get('host')}:{info.get('port')}\n✅ Синтаксис валиден\n\nХочешь проверить TCP — используй /check",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Проверить TCP", callback_data="home")]])
                )
            else:
                await update.message.reply_text(f"❌ Нашёл битый VLESS: {reason}")

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not CACHE:
        await update.message.reply_text("Кэш пуст. Делаю /update...")
        await update_cache()
    lines = [f"<b>📊 Статистика {msk_time()}</b>"]
    total = 0
    for k, d in CACHE.items():
        cnt = len(d.get("configs", []))
        total += cnt
        name = config.SOURCES.get(k, {}).get("name", k)[:30]
        lines.append(f"• {k}: <b>{cnt}</b> — {name}")
    lines.append(f"\n<b>Всего: {total} VLESS</b>")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

async def sub_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Показать все подписки как файлы
    if not CACHE:
        await update_cache()
    await update.message.reply_text("📦 <b>Все твои подписки:</b> отправляю файлы...", parse_mode=ParseMode.HTML)
    for k, d in CACHE.items():
        if d.get("configs"):
            await send_files(update, k, d)
            await asyncio.sleep(0.5)

# ---------- Auto updater ----------

async def auto_update_loop(app: Application):
    await asyncio.sleep(10)  # первый старт
    while True:
        try:
            logger.info("Auto update tick")
            await update_cache()
            # Опционально постим в канал
            if config.CHANNEL_ID:
                try:
                    # Отправка статистики в канал
                    total = sum(len(v.get("configs", [])) for v in CACHE.values())
                    text = (
                        f"🔄 <b>Автообновление {msk_time()}</b>\n"
                        f"✅ Собрано {total} рабочих VLESS\n"
                        f"⬛ Чёрные: {len(CACHE.get('black_all', {}).get('configs', []))} + {len(CACHE.get('black_mobile', {}).get('configs', []))} mobile\n"
                        f"⬜ Белые CIDR: {len(CACHE.get('white_cidr_all', {}).get('configs', []))} | VK/YA: {len(CACHE.get('white_cidr_checked', {}).get('configs', []))}\n"
                        f"Получи подписку в боте: @{app.bot.username}"
                    )
                    await app.bot.send_message(chat_id=config.CHANNEL_ID, text=text, parse_mode=ParseMode.HTML)
                except Exception as e:
                    logger.error(f"channel post error: {e}")
        except Exception as e:
            logger.error(f"auto update error: {e}")
        await asyncio.sleep(config.UPDATE_INTERVAL * 60)

# ---------- Main ----------

def main():
    if not config.BOT_TOKEN:
        print("❌ BOT_TOKEN не задан! Создай .env из .env.example и впиши токен от @BotFather")
        return
    
    app = Application.builder().token(config.BOT_TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("sources", sources_cmd))
    app.add_handler(CommandHandler("update", update_cmd))
    app.add_handler(CommandHandler("check", check_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("sub", sub_cmd))
    
    # Групповые и одиночные команды
    app.add_handler(CommandHandler("black", get_command_factory("black_all")))
    app.add_handler(CommandHandler("black_mobile", get_command_factory("black_mobile")))
    app.add_handler(CommandHandler("white", get_command_factory(None, group_keys=["white_cidr_all", "white_cidr_checked", "white_mobile"])))
    app.add_handler(CommandHandler("white_cidr", get_command_factory("white_cidr_all")))
    app.add_handler(CommandHandler("white_checked", get_command_factory("white_cidr_checked")))
    app.add_handler(CommandHandler("white_mobile", get_command_factory("white_mobile")))
    app.add_handler(CommandHandler("all", get_command_factory(None, group_keys=config.GROUPS["all"])))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    # Авто-проверка присланных vless
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_vless_handler))
    
    print(f"🚀 Бот запущен! Токен: {config.BOT_TOKEN[:10]}... Интервал: {config.UPDATE_INTERVAL}м")
    print(f"📂 DATA_DIR: {DATA_DIR}")
    # Первичная загрузка кэша
    async def _preload():
        try:
            await update_cache()
            print(f"✅ Кэш загружен: {sum(len(v.get('configs', [])) for v in CACHE.values())} конфигов")
        except Exception as e:
            print(f"⚠️ Ошибка первичной загрузки: {e}")
    
    # Создаём задачу автообновления после старта + health server для Railway
    async def _post_init(app: Application):
        if start_health_server:
            try:
                await start_health_server()
            except Exception as e:
                logger.warning(f"health server failed: {e}")
        await _preload()
        asyncio.create_task(auto_update_loop(app))
    
    app.post_init = _post_init
    
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
