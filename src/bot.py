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
from subscription import save_subscription_files, generate_qr_bytes, get_subscription_stats, CHUNK_SIZE, save_aggregated_chunks, PROTOCOLS, PROTOCOL_LABELS, filter_by_protocol
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
AGGREGATED_CHUNKS = {}  # filename -> list of (chunk_filename, title, count)
AGGREGATED_PROTO_COUNTS = {}  # filename (base) -> {proto: count}

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

def chunks_keyboard(base_filename: str, chunk_list, back_data: str = "home", back_label: str = "‹ Назад"):
    rows = []
    for idx, (cfname, title, cnt) in enumerate(chunk_list, 1):
        short = cfname.replace(".txt","")
        label = f"{short} · {cnt}"
        if len(rows)==0 or len(rows[-1])==2:
            rows.append([InlineKeyboardButton(label, callback_data=f"chunk:{cfname}")])
        else:
            rows[-1].append(InlineKeyboardButton(label, callback_data=f"chunk:{cfname}"))
    rows.append([InlineKeyboardButton("Скачать полный файл", callback_data=f"rawfile:{base_filename}")])
    rows.append([InlineKeyboardButton(back_label, callback_data=back_data)])
    return InlineKeyboardMarkup(rows)

def protocol_keyboard(agg_key: str):
    """Кнопки выбора протокола для agg_key: WHITE_FULL / BLACK_FULL / FULL"""
    agg = config.AGGREGATED_SUBS.get(agg_key)
    if not agg:
        return InlineKeyboardMarkup([[InlineKeyboardButton("‹ Назад", callback_data="home")]])
    base = agg["filename"]
    total = AGGREGATED_CACHE.get(base, {}).get("count", "?")
    counts = AGGREGATED_PROTO_COUNTS.get(base, {})
    rows = []
    # Все — первым отдельным рядом
    rows.append([InlineKeyboardButton(f"🌐 Все · {total}", callback_data=f"proto:{agg_key}:all")])
    # Протоколы — по 2 в ряд, показываем только те где >0, сортируем по убыванию количества
    available = [(p, counts.get(p, 0)) for p in PROTOCOLS if counts.get(p, 0) > 0]
    # Сортировка: vless всегда первый (самый крупный), остальные по убыванию
    # Но для стабильности — сначала vless, потом остальные по count desc
    if available:
        # вынести vless вперёд если есть
        vless = [x for x in available if x[0]=="vless"]
        rest = [x for x in available if x[0]!="vless"]
        rest.sort(key=lambda x: x[1], reverse=True)
        ordered = vless + rest
        row = []
        for proto, cnt in ordered:
            label = f"{PROTOCOL_LABELS.get(proto, proto.upper())} · {cnt}"
            btn = InlineKeyboardButton(label, callback_data=f"proto:{agg_key}:{proto}")
            row.append(btn)
            if len(row)==2:
                rows.append(row)
                row=[]
        if row:
            rows.append(row)
    else:
        # если ещё нет данных — показываем хотя бы VLESS
        pass
    rows.append([InlineKeyboardButton("‹ Назад", callback_data="home")])
    return InlineKeyboardMarkup(rows)

# ---------- Aggregated ----------

def build_aggregated_configs():
    from subscription import generate_aggregated_content
    results = {}
    chunk_map = {}
    proto_counts_map = {}
    seen_filenames = set()
    for agg_key, agg in config.AGGREGATED_SUBS.items():
        filename = agg["filename"]
        if filename in seen_filenames:
            continue
        seen_filenames.add(filename)
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
            chunk_list = []
            for cfname, ctitle, cnt, ccontent in chunk_infos:
                results[cfname] = {"content": ccontent, "count": cnt, "configs": [], "is_chunk": True}
                chunk_list.append((cfname, ctitle, cnt))
            chunk_map[filename] = chunk_list
            logger.info(f"Aggregated {filename}: {len(all_cfgs)} -> {len(chunk_infos)} чанков")
            # --- Протокольные срезы ---
            base_name = filename.replace(".txt", "")
            proto_counts = {}
            for proto in PROTOCOLS:
                filtered = filter_by_protocol(all_cfgs, proto)
                proto_counts[proto] = len(filtered)
                if not filtered:
                    continue
                proto_filename = f"{base_name}_{proto.upper()}.txt"
                proto_title = f"{title} — {PROTOCOL_LABELS.get(proto, proto.upper())}"
                try:
                    p_full_path, p_full_b64, p_full_content, p_full_b64c, p_chunk_infos = save_aggregated_chunks(str(DATA_DIR), proto_filename, proto_title, filtered, CHUNK_SIZE)
                    results[proto_filename] = {"content": p_full_content, "count": len(filtered), "configs": filtered}
                    p_chunk_list = []
                    for cfname, ctitle, cnt, ccontent in p_chunk_infos:
                        results[cfname] = {"content": ccontent, "count": cnt, "configs": [], "is_chunk": True}
                        p_chunk_list.append((cfname, ctitle, cnt))
                    chunk_map[proto_filename] = p_chunk_list
                    logger.info(f"  └─ {proto_filename}: {len(filtered)} -> {len(p_chunk_infos)} чанков")
                except Exception as e:
                    logger.error(f"proto build {proto_filename} error: {e}")
            proto_counts_map[filename] = proto_counts
        except Exception as e:
            logger.error(f"aggregated build {filename} error: {e}")
    global AGGREGATED_CHUNKS, AGGREGATED_PROTO_COUNTS
    AGGREGATED_CHUNKS = chunk_map
    AGGREGATED_PROTO_COUNTS = proto_counts_map
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
    await update.message.reply_text(
        f"{config.PREMIUM['sparkles']} Клавиатура обновлена — жми «Главное меню» внизу {config.PREMIUM['thumbsup']}",
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

def get_cached(k): return CACHE.get(k)

async def send_chunk_file(query, fname, back_data="home"):
    path = DATA_DIR / fname
    if not path.exists():
        await query.message.reply_text("Файл не найден, обновляю…")
        await update_cache()
    if path.exists():
        title = fname
        # try to resolve title from aggregated or proto files
        for v in config.AGGREGATED_SUBS.values():
            if v["filename"] == fname:
                title = v["profile_title"]
                break
            if fname.startswith(v["filename"].replace(".txt","")):
                # e.g., BLACK_FULL_VLESS_1.txt -> title Black — VLESS — 1
                base_title = v["profile_title"]
                # detect proto in filename
                for proto in PROTOCOLS:
                    if f"_{proto.upper()}.txt" in fname or f"_{proto.upper()}_" in fname:
                        base_title = f"{base_title} — {PROTOCOL_LABELS.get(proto, proto.upper())}"
                        break
                title = f"{base_title} — {fname}"
                break
        cnt = AGGREGATED_CACHE.get(fname, {}).get("count", "?")
        raw = get_raw_url(fname)
        await query.message.reply_text(f"{config.PREMIUM['diamond']} <b>{title}</b> {config.PREMIUM['sparkles']}\n<code>{raw}</code>\nКонфигов: <b>{cnt}</b> {config.PREMIUM['fire_crimson']}", parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Скачать файл", callback_data=f"rawfile:{fname}"), InlineKeyboardButton("Копировать ссылку", callback_data=f"rawcopy:{fname}")],[InlineKeyboardButton("‹ Назад", callback_data=back_data)]]))
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
            f"{config.PREMIUM['thumbsup']} <b>Мой профиль</b> {config.PREMIUM['sparkles']}\n\n"
            f"{config.PREMIUM['computer']} ID: <code>{user.id}</code>\n"
            f"Username: @{user.username or '—'}\n"
            f"{config.PREMIUM['heart']} Имя: {user.first_name or '—'}"
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
        await query.message.edit_text(f"{config.PREMIUM['diamond']} <b>Админ панель</b> {config.PREMIUM['sparkles']}\nВыбери действие:", parse_mode=ParseMode.HTML, reply_markup=admin_keyboard())
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
            lines = [f"{config.PREMIUM['computer']} <b>Статистика • {datetime.now(MSK).strftime('%d.%m %H:%M')}</b> {config.PREMIUM['sparkles']}"]
            total=0
            for k,d in CACHE.items():
                cnt=len(d.get("configs",[])); total+=cnt
                lines.append(f"• {k}: <b>{cnt}</b>")
            lines.append(f"\n{config.PREMIUM['fire_crimson']} Всего: <b>{total}</b> {config.PREMIUM['diamond']}")
            for fname, info in AGGREGATED_CACHE.items():
                if info.get("is_chunk"):
                    continue
                # show base + protocol files
                lines.append(f"{config.PREMIUM['diamond']} • {fname}: <b>{info.get('count','?')}</b>")
            await query.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("‹ Назад", callback_data="admin_panel")]]))
            return
        if data == "admin_refresh":
            await query.message.edit_text(f"{config.PREMIUM['lightning']} Обновляю кэш… {config.PREMIUM['sparkles']}")
            await update_cache()
            await query.message.edit_text(f"{config.PREMIUM['thumbsup']} Готово • {datetime.now(MSK).strftime('%H:%M')} {config.PREMIUM['fire_crimson']}", reply_markup=admin_keyboard())
            return

    if data in ("sources", "stats", "refresh"):
        if not config.is_admin(uid):
            await query.answer("Только для админа", show_alert=True)
            return
        if data=="sources": data="admin_sources"
        if data=="stats": data="admin_stats"
        if data=="refresh": data="admin_refresh"
        query.data = data
        await callback_handler(update, context)
        return

    # --- Белые / Черные / Полный теперь показывают выбор протокола ---
    if data == "white":
        agg_key = "WHITE_FULL"
        agg = config.AGGREGATED_SUBS[agg_key]
        base = agg["filename"]
        if base not in AGGREGATED_PROTO_COUNTS:
            await update_cache()
        total = AGGREGATED_CACHE.get(base, {}).get("count", "?")
        text = (
            f"{config.PREMIUM['ghost']} <b>Белые списки</b> — для жёстких ТСПУ (VK, Яндекс) {config.PREMIUM['sparkles']}\n"
            f"Всего: <b>{total}</b> • делю по 300 {config.PREMIUM['diamond']}\n\n"
            f"{config.PREMIUM['lightning']} Выбери протокол (режим):"
        )
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=protocol_keyboard(agg_key))
        return

    if data == "black":
        agg_key = "BLACK_FULL"
        agg = config.AGGREGATED_SUBS[agg_key]
        base = agg["filename"]
        if base not in AGGREGATED_PROTO_COUNTS:
            await update_cache()
        total = AGGREGATED_CACHE.get(base, {}).get("count", "?")
        text = (
            f"{config.PREMIUM['shield']} <b>Чёрные списки</b> — весь трафик через VPN {config.PREMIUM['fire_crimson']}\n"
            f"Всего: <b>{total}</b> • делю по 300 {config.PREMIUM['diamond']}\n\n"
            f"{config.PREMIUM['lightning']} Выбери протокол (режим):"
        )
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=protocol_keyboard(agg_key))
        return

    if data == "full":
        agg_key = "FULL"
        agg = config.AGGREGATED_SUBS[agg_key]
        base = agg["filename"]
        if base not in AGGREGATED_PROTO_COUNTS:
            await update_cache()
        total = AGGREGATED_CACHE.get(base, {}).get("count", "?")
        text = (
            f"{config.PREMIUM['diamond']} <b>Полный список</b> — все белые + чёрные {config.PREMIUM['sparkles']}\n"
            f"Всего: <b>{total}</b> • делю по 300 {config.PREMIUM['fire_crimson']}\n\n"
            f"{config.PREMIUM['lightning']} Выбери протокол (режим):"
        )
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=protocol_keyboard(agg_key))
        return

    # --- Выбор протокола ---
    if data.startswith("proto:"):
        # proto:BLACK_FULL:vless  or proto:WHITE_FULL:all
        try:
            _, agg_key, proto = data.split(":", 2)
        except:
            await query.answer("Ошибка", show_alert=True)
            return
        agg = config.AGGREGATED_SUBS.get(agg_key)
        if not agg:
            await query.message.reply_text("Неизвестный список")
            return
        base = agg["filename"]
        base_title = agg["profile_title"]
        if proto == "all":
            fname = base
            display_title = base_title
        else:
            fname = f"{base.replace('.txt','')}_{proto.upper()}.txt"
            display_title = f"{base_title} — {PROTOCOL_LABELS.get(proto, proto.upper())}"
        # chunks for this filename
        chunks = AGGREGATED_CHUNKS.get(fname, [])
        # if file empty (proto without configs) handle
        cnt = AGGREGATED_CACHE.get(fname, {}).get("count")
        if cnt is None:
            # try to compute from proto_counts
            cnt = AGGREGATED_PROTO_COUNTS.get(base, {}).get(proto, 0)
        if cnt == 0:
            await query.message.edit_text(
                f"{config.PREMIUM['warning']} <b>{display_title}</b>\nПока нет конфигов для <b>{PROTOCOL_LABELS.get(proto, proto)}</b> в этом списке. {config.PREMIUM['cross']}",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("‹ К протоколам", callback_data=agg_key.lower().replace("_full",""))]])
            )
            return
        raw = get_raw_url(fname)
        # Determine back target: white/black/full
        back_target = agg_key.lower().replace("_full","")  # white / black / full
        if back_target not in ("white","black","full"):
            back_target = "home"
        text = (
            f"{config.PREMIUM['diamond']} <b>{display_title}</b> {config.PREMIUM['sparkles']}\n"
            f"Конфигов: <b>{cnt}</b> • делю по 300 {config.PREMIUM['fire_crimson']}\n"
            f"Файл: <code>{raw}</code>\n\n"
            f"{config.PREMIUM['lightning']} Выбери пакет:"
        )
        if chunks:
            kb = chunks_keyboard(fname, chunks, back_data=back_target, back_label="‹ К протоколам")
        else:
            # single file (<=300)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Скачать файл", callback_data=f"rawfile:{fname}"), InlineKeyboardButton("Копировать", callback_data=f"rawcopy:{fname}")],
                [InlineKeyboardButton("‹ К протоколам", callback_data=back_target)]
            ])
            text = f"{config.PREMIUM['diamond']} <b>{display_title}</b> {config.PREMIUM['sparkles']}\n<code>{raw}</code>\nКонфигов: <b>{cnt}</b> {config.PREMIUM['fire_crimson']}"
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        return

    if data.startswith("chunk:"):
        fname = data.split(":",1)[1]
        # determine back: if proto file, back to proto chooser; else inferred
        back = "home"
        for proto in PROTOCOLS:
            if f"_{proto.upper()}_" in fname or fname.endswith(f"_{proto.upper()}.txt"):
                # find base
                for agg_key, agg in config.AGGREGATED_SUBS.items():
                    base = agg["filename"]
                    if fname.startswith(base.replace(".txt","")):
                        back = agg_key.lower().replace("_full","")
                        break
                break
        # check if it's chunk of base without proto -> also map
        if back == "home":
            for agg_key, agg in config.AGGREGATED_SUBS.items():
                if fname.startswith(agg["filename"].replace(".txt","")):
                    bk = agg_key.lower().replace("_full","")
                    if bk in ("white","black","full"):
                        back = bk
        await send_chunk_file(query, fname, back_data=back)
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
            cnt = AGGREGATED_CACHE.get(fname, {}).get("count", "?")
            await query.message.reply_document(document=open(path, "rb"), filename=fname, caption=f"{title} • {cnt}")
        else:
            await query.message.reply_text(f"{config.PREMIUM['cross']} Файл не найден {config.PREMIUM['warning']}")
        return

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
    if "vless://" in text:
        import re
        m = re.search(r'vless://[^\s]+', text)
        if m:
            link = m.group(0)
            ok, reason = is_valid_vless(link)
            info = parse_vless_info(link)
            if ok:
                await update.message.reply_text(f"{config.PREMIUM['lightning']} VLESS: {info.get('remark')}\n{info.get('host')}:{info.get('port')} • валиден {config.PREMIUM['thumbsup']}", reply_markup=main_keyboard(update.effective_user.id))
            else:
                await update.message.reply_text(f"{config.PREMIUM['cross']} Битый VLESS: {reason} {config.PREMIUM['warning']}")

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
