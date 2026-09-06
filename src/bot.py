import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode

import config
from parser import fetch_all, is_valid_vless, parse_vless_info
from subscription import save_subscription_files, generate_qr_bytes, get_subscription_stats, CHUNK_SIZE, save_aggregated_chunks
import aiohttp
try:
    from health import start_health_server
except ImportError:
    start_health_server = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

CACHE = {}
LAST_UPDATE = None
AGGREGATED_CACHE = {}
AGGREGATED_CHUNKS = {}  # filename -> list of (chunk_filename, count)

MSK = timezone(timedelta(hours=3))
def msk_time():
    return datetime.now(MSK).strftime("%d.%m.%Y %H:%M МСК")

REPLY_MENU = ReplyKeyboardMarkup([[KeyboardButton("Главное меню")]], resize_keyboard=True, is_persistent=True)

def main_keyboard(user_id: int = None):
    kb = [
        [InlineKeyboardButton("Мой профиль", callback_data="profile")],
        [InlineKeyboardButton("Белые списки", callback_data="white"),
         InlineKeyboardButton("Черные списки", callback_data="black")],
        [InlineKeyboardButton("Полный список", callback_data="full")],
        [InlineKeyboardButton("Помощь", callback_data="help")],
    ]
    if user_id and config.is_admin(user_id):
        kb.append([InlineKeyboardButton("Админ панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(kb)

def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Статистика", callback_data="admin_stats"),
         InlineKeyboardButton("Обновить кэш", callback_data="admin_refresh")],
        [InlineKeyboardButton("Источники", callback_data="admin_sources")],
        [InlineKeyboardButton("‹ Назад", callback_data="home")],
    ])

def category_keyboard(category_key: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Получить файл", callback_data=f"file:{category_key}"),
         InlineKeyboardButton("Копировать", callback_data=f"copy:{category_key}")],
        [InlineKeyboardButton("Показать 5", callback_data=f"preview:{category_key}"),
         InlineKeyboardButton("QR", callback_data=f"qr:{category_key}")],
        [InlineKeyboardButton("‹ Назад", callback_data="home")],
    ])

def chunks_keyboard(base_filename: str, chunk_list):
    # chunk_list = [(chunk_filename, title, count), ...]
    rows = []
    for idx, (cfname, title, cnt) in enumerate(chunk_list, 1):
        # label like "Whitelist 1 · 300" or "Full 1 · 300"
        short = cfname.replace(".txt","")
        # extract number
        num = cfname.split("_")[-1].replace(".txt","")
        label = f"{short} · {cnt}"
        # Use 2 per row
        if len(rows)==0 or len(rows[-1])==2:
            rows.append([InlineKeyboardButton(label, callback_data=f"chunk:{cfname}")])
        else:
            rows[-1].append(InlineKeyboardButton(label, callback_data=f"chunk:{cfname}"))
    # add full file button
    rows.append([InlineKeyboardButton("Скачать полный файл", callback_data=f"rawfile:{base_filename}")])
    rows.append([InlineKeyboardButton("‹ Назад", callback_data="home")])
    return InlineKeyboardMarkup(rows)

# ---------- Aggregated ----------

def build_aggregated_configs():
    from subscription import generate_aggregated_content
    results = {}
    chunk_map = {}
    for agg_key, agg in config.AGGREGATED_SUBS.items():
        filename = agg["filename"]
        title = agg["profile_title"]
        source_keys = agg["source_keys"]
        all_cfgs = []
        seen = set()
        for sk in source_keys:
            data = CACHE.get(sk, {})
            for c in data.get("configs", []):
                if c not in seen:
                    seen.add(c)
                    all_cfgs.append(c)
        try:
            full_path, full_b64, full_content, full_b64c, chunk_infos = save_aggregated_chunks(str(DATA_DIR), filename, title, all_cfgs, CHUNK_SIZE)
            results[filename] = {"content": full_content, "count": len(all_cfgs), "configs": all_cfgs}
            # chunks
            chunk_list = []
            for cfname, ctitle, cnt, ccontent in chunk_infos:
                results[cfname] = {"content": ccontent, "count": cnt, "configs": [], "is_chunk": True}
                chunk_list.append((cfname, ctitle, cnt))
            chunk_map[filename] = chunk_list
            logger.info(f"Aggregated {filename}: {len(all_cfgs)} -> {len(chunk_infos)} чанков")
        except Exception as e:
            logger.error(f"aggregated build {filename} error: {e}")
    # store chunk map globally
    global AGGREGATED_CHUNKS
    AGGREGATED_CHUNKS = chunk_map
    return results

async def push_aggregated_to_github(aggregated_results):
    if not config.GITHUB_TOKEN or not config.GITHUB_REPO:
        logger.info("GITHUB пуш пропущен")
        return {}
    try:
        from github_sync import push_aggregated_subscriptions
        to_push = {}
        for filename, info in aggregated_results.items():
            path = f"{config.GITHUB_SUB_PATH}/{filename}" if config.GITHUB_SUB_PATH else filename
            path = path.lstrip("/")
            to_push[path] = info["content"]
        raw_map = await push_aggregated_subscriptions(to_push, config.GITHUB_REPO, config.GITHUB_TOKEN, config.GITHUB_BRANCH)
        for path, raw_url in raw_map.items():
            fname = path.split("/")[-1]
            if fname in aggregated_results:
                AGGREGATED_CACHE[fname] = {"raw_url": raw_url, "count": aggregated_results[fname]["count"], "content": aggregated_results[fname]["content"]}
        return raw_map
    except Exception as e:
        logger.error(f"push error: {e}")
        return {}

async def update_cache(categories=None, mode=None):
    global CACHE, LAST_UPDATE
    mode = mode or config.CHECK_MODE
    if categories is None:
        categories = list(config.SOURCES.keys())
    logger.info(f"Updating cache for {categories}")
    result = await fetch_all(mode=mode, categories=categories)
    for key, data in result.items():
        configs = data.get("configs", [])
        title = config.SOURCES.get(key, {}).get("name", key)
        if configs:
            try:
                save_subscription_files(str(DATA_DIR), key, configs, title)
            except Exception as e:
                logger.error(f"save error {key}: {e}")
        CACHE[key] = data
    global LAST_UPDATE
    LAST_UPDATE = datetime.now(MSK)
    try:
        agg = build_aggregated_configs()
        for fname, info in agg.items():
            if fname not in AGGREGATED_CACHE:
                AGGREGATED_CACHE[fname] = {"count": info["count"], "content": info["content"], "raw_url": get_raw_url(fname)}
            else:
                AGGREGATED_CACHE[fname].update({"count": info["count"], "content": info["content"]})
        if config.GITHUB_TOKEN and agg:
            asyncio.create_task(push_aggregated_to_github(agg))
    except Exception as e:
        logger.error(f"aggregated error: {e}")
    return result

def get_raw_url(filename: str) -> str:
    cached = AGGREGATED_CACHE.get(filename, {})
    if cached.get("raw_url"):
        return cached["raw_url"]
    repo = config.GITHUB_REPO
    branch = config.GITHUB_BRANCH
    path = f"{config.GITHUB_SUB_PATH}/{filename}" if config.GITHUB_SUB_PATH else filename
    path = path.lstrip("/")
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"

# ---------- Handlers ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id if update.effective_user else None
    # Reply keyboard for Главное меню
    await update.message.reply_text(
        "Клавиатура обновлена — жми «Главное меню» внизу",
        reply_markup=REPLY_MENU
    )
    await update.message.reply_text(
        config.WELCOME_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=main_keyboard(uid)
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id if update.effective_user else None
    await update.message.reply_text(config.HELP_TEXT, parse_mode=ParseMode.HTML, reply_markup=main_keyboard(uid))

async def handle_main_menu_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Главное меню":
        uid = update.effective_user.id if update.effective_user else None
        await update.message.reply_text(config.WELCOME_TEXT, parse_mode=ParseMode.HTML, reply_markup=main_keyboard(uid))
        return True
    return False

# legacy simple handlers for admin via text (not needed)

def get_cached(k): return CACHE.get(k)

async def send_chunk_file(query, fname):
    path = DATA_DIR / fname
    if not path.exists():
        await query.message.reply_text("Файл не найден, обновляю…")
        await update_cache()
    if path.exists():
        title = fname
        for v in config.AGGREGATED_SUBS.values():
            if v["filename"] == fname:
                title = v["profile_title"]
                break
            # also chunk title
            if fname.startswith(v["filename"].replace(".txt","")):
                title = f"{v['profile_title']} — {fname}"
        cnt = AGGREGATED_CACHE.get(fname, {}).get("count", "?")
        raw = get_raw_url(fname)
        await query.message.reply_text(f"<b>{title}</b>\n<code>{raw}</code>\nКонфигов: <b>{cnt}</b>", parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Скачать файл", callback_data=f"rawfile:{fname}"), InlineKeyboardButton("Копировать ссылку", callback_data=f"rawcopy:{fname}")],[InlineKeyboardButton("‹ Назад", callback_data="home")]]))
        try:
            await query.message.reply_document(document=open(path, "rb"), filename=fname, caption=f"{title} • {cnt}")
        except Exception as e:
            logger.error(e)

# ---------- Callback ----------

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    uid = query.from_user.id if query.from_user else 0

    if data == "home":
        await query.message.edit_text(config.WELCOME_TEXT, parse_mode=ParseMode.HTML, reply_markup=main_keyboard(uid))
        return

    if data == "profile":
        user = query.from_user
        text = (
            f"<b>Мой профиль</b>\n\n"
            f"ID: <code>{user.id}</code>\n"
            f"Username: @{user.username or '—'}\n"
            f"Имя: {user.first_name or '—'}"
        )
        await query.message.reply_text(text, parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("‹ Назад", callback_data="home")]]))
        return

    if data == "help":
        await query.message.reply_text(config.HELP_TEXT, parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("‹ Назад", callback_data="home")]]))
        return

    if data == "admin_panel":
        if not config.is_admin(uid):
            await query.answer("Только для админа", show_alert=True)
            return
        await query.message.edit_text("<b>Админ панель</b>\nВыбери действие:", parse_mode=ParseMode.HTML, reply_markup=admin_keyboard())
        return

    if data in ("admin_stats", "admin_refresh", "admin_sources"):
        if not config.is_admin(uid):
            await query.answer("Только для админа", show_alert=True)
            return
        if data == "admin_sources":
            await query.message.reply_text(config.SOURCES_TEXT, parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("‹ Назад", callback_data="admin_panel")]]))
            return
        if data == "admin_stats":
            if not CACHE:
                await update_cache()
            lines = [f"<b>Статистика • {datetime.now(MSK).strftime('%d.%m %H:%M')}</b>"]
            total=0
            for k,d in CACHE.items():
                cnt=len(d.get("configs",[])); total+=cnt
                lines.append(f"• {k}: <b>{cnt}</b>")
            lines.append(f"\nВсего: <b>{total}</b>")
            for fname, info in AGGREGATED_CACHE.items():
                if info.get("is_chunk"): continue
                # only main files
                if fname in [v["filename"] for v in config.AGGREGATED_SUBS.values()]:
                    lines.append(f"• {fname}: <b>{info.get('count','?')}</b>")
            await query.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("‹ Назад", callback_data="admin_panel")]]))
            return
        if data == "admin_refresh":
            await query.message.edit_text("Обновляю кэш…")
            await update_cache()
            await query.message.edit_text(f"Готово • {datetime.now(MSK).strftime('%H:%M')}", reply_markup=admin_keyboard())
            return

    # hidden legacy admin callbacks
    if data in ("sources", "stats", "refresh"):
        if not config.is_admin(uid):
            await query.answer("Только для админа", show_alert=True)
            return
        # redirect to admin
        if data=="sources": data="admin_sources"
        if data=="stats": data="admin_stats"
        if data=="refresh": data="admin_refresh"
        # re-invoke
        query.data = data
        await callback_handler(update, context)
        return

    # minimal RAW
    if data == "white":
        # show chunk list for white
        base = config.AGGREGATED_SUBS["WHITE_FULL"]["filename"]
        chunks = AGGREGATED_CHUNKS.get(base, [])
        if not chunks:
            # build if not yet
            await update_cache()
            chunks = AGGREGATED_CHUNKS.get(base, [])
        cnt = AGGREGATED_CACHE.get(base, {}).get("count", "?")
        raw = get_raw_url(base)
        text = (
            f"<b>Белые списки</b>\n"
            f"Всего: <b>{cnt}</b> • делю по 300\n"
            f"Полный файл: <code>{raw}</code>\n\n"
            f"Выбери пакет:"
        )
        kb = chunks_keyboard(base, chunks) if chunks else InlineKeyboardMarkup([[InlineKeyboardButton("Скачать полный", callback_data=f"rawfile:{base}")],[InlineKeyboardButton("‹ Назад", callback_data="home")]])
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        return

    if data == "black":
        base = config.AGGREGATED_SUBS["BLACK_FULL"]["filename"]
        chunks = AGGREGATED_CHUNKS.get(base, [])
        if not chunks:
            await update_cache()
            chunks = AGGREGATED_CHUNKS.get(base, [])
        cnt = AGGREGATED_CACHE.get(base, {}).get("count", "?")
        raw = get_raw_url(base)
        text = (
            f"<b>Черные списки</b>\n"
            f"Всего: <b>{cnt}</b> • делю по 300\n"
            f"Полный файл: <code>{raw}</code>\n\n"
            f"Выбери пакет:"
        )
        kb = chunks_keyboard(base, chunks) if chunks else InlineKeyboardMarkup([[InlineKeyboardButton("Скачать полный", callback_data=f"rawfile:{base}")],[InlineKeyboardButton("‹ Назад", callback_data="home")]])
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        return

    if data == "full":
        base = config.AGGREGATED_SUBS["FULL"]["filename"]
        chunks = AGGREGATED_CHUNKS.get(base, [])
        if not chunks:
            await update_cache()
            chunks = AGGREGATED_CHUNKS.get(base, [])
        cnt = AGGREGATED_CACHE.get(base, {}).get("count", "?")
        raw = get_raw_url(base)
        text = (
            f"<b>Полный список</b>\n"
            f"Все белые + черные • <b>{cnt}</b> • делю по 300\n"
            f"Полный: <code>{raw}</code>\n\n"
            f"Выбери пакет:"
        )
        kb = chunks_keyboard(base, chunks) if chunks else InlineKeyboardMarkup([[InlineKeyboardButton("Скачать полный", callback_data=f"rawfile:{base}")],[InlineKeyboardButton("‹ Назад", callback_data="home")]])
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        return

    if data.startswith("chunk:"):
        fname = data.split(":",1)[1]
        await send_chunk_file(query, fname)
        return

    if data.startswith("rawcopy:"):
        fname = data.split(":",1)[1]
        raw = get_raw_url(fname)
        await query.message.reply_text(f"<code>{raw}</code>", parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("‹ Назад", callback_data="home")]]))
        return

    if data.startswith("rawfile:"):
        fname = data.split(":",1)[1]
        path = DATA_DIR / fname
        if not path.exists():
            await update_cache()
        if path.exists():
            title = fname
            for v in config.AGGREGATED_SUBS.values():
                if v["filename"]==fname:
                    title=v["profile_title"]
            cnt = AGGREGATED_CACHE.get(fname, {}).get("count", "?")
            await query.message.reply_document(document=open(path, "rb"), filename=fname, caption=f"{title} • {cnt}")
        else:
            await query.message.reply_text("Файл не найден")
        return

    # legacy raw
    if data.startswith("raw:"):
        agg_key = data.split(":",1)[1]
        if agg_key not in config.AGGREGATED_SUBS:
            await query.message.reply_text("Неизвестная подписка")
            return
        fname = config.AGGREGATED_SUBS[agg_key]["filename"]
        title = config.AGGREGATED_SUBS[agg_key]["profile_title"]
        cnt = AGGREGATED_CACHE.get(fname, {}).get("count", "—")
        raw = get_raw_url(fname)
        text = f"<b>{title}</b>\n<code>{raw}</code>\nКонфигов: <b>{cnt}</b>"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Скопировать", callback_data=f"rawcopy:{fname}"), InlineKeyboardButton("Скачать", callback_data=f"rawfile:{fname}")],[InlineKeyboardButton("‹ Назад", callback_data="home")]])
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        return

    # legacy get
    if data.startswith("get:"):
        await query.answer("Раздел перенесён в «Полный список»", show_alert=False)
        await query.message.edit_text(config.WELCOME_TEXT, parse_mode=ParseMode.HTML, reply_markup=main_keyboard(uid))
        return

# ---------- Message handlers ----------

async def message_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "Главное меню":
        uid = update.effective_user.id if update.effective_user else None
        await update.message.reply_text(config.WELCOME_TEXT, parse_mode=ParseMode.HTML, reply_markup=main_keyboard(uid))
        return
    # vless check
    if "vless://" in text:
        import re
        m = re.search(r'vless://[^\s]+', text)
        if m:
            link = m.group(0)
            ok, reason = is_valid_vless(link)
            info = parse_vless_info(link)
            if ok:
                await update.message.reply_text(f"🔍 VLESS: {info.get('remark')}\n{info.get('host')}:{info.get('port')} • валиден", reply_markup=main_keyboard(update.effective_user.id))
            else:
                await update.message.reply_text(f"❌ Битый VLESS: {reason}")

def get_raw_url(filename: str) -> str:
    cached = AGGREGATED_CACHE.get(filename, {})
    if cached.get("raw_url"):
        return cached["raw_url"]
    repo = config.GITHUB_REPO
    branch = config.GITHUB_BRANCH
    path = f"{config.GITHUB_SUB_PATH}/{filename}" if config.GITHUB_SUB_PATH else filename
    path = path.lstrip("/")
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"

# ---------- Main ----------

def main():
    if not config.BOT_TOKEN:
        print("BOT_TOKEN не задан")
        return
    app = Application.builder().token(config.BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_text_handler))
    app.add_handler(CallbackQueryHandler(callback_handler))
    print(f"🚀 Crimson bot @wtfparsbot интервальный {config.UPDATE_INTERVAL}м")
    async def _preload():
        try:
            await update_cache()
            print(f"✅ Кэш {sum(len(v.get('configs',[])) for v in CACHE.values())}")
        except Exception as e:
            print(f"⚠️ {e}")
    async def _post_init(app):
        if start_health_server:
            try: await start_health_server()
            except Exception as e: logger.warning(e)
        await _preload()
        asyncio.create_task(auto_update_loop(app))
    app.post_init = _post_init
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

async def auto_update_loop(app):
    await asyncio.sleep(10)
    while True:
        try:
            await update_cache()
        except Exception as e:
            logger.error(e)
        await asyncio.sleep(config.UPDATE_INTERVAL*60)

if __name__ == "__main__":
    main()
