import re
import asyncio
import base64
import aiohttp
import re as regex
from typing import List, Dict, Tuple
from urllib.parse import urlparse, parse_qs, unquote

from config import SOURCES

# Регулярка для VLESS ссылок
VLESS_REGEX = re.compile(r'vless://[^\s\n\r\"\'<>]+', re.IGNORECASE)
VMESS_REGEX = re.compile(r'vmess://[^\s\n\r\"\'<>]+', re.IGNORECASE)
TROJAN_REGEX = re.compile(r'trojan://[^\s\n\r\"\'<>]+', re.IGNORECASE)
SS_REGEX = re.compile(r'ss://[^\s\n\r\"\'<>]+', re.IGNORECASE)

ALL_REGEX = re.compile(r'(vless|vmess|trojan|ss|ssr|hysteria2|tuic)://[^\s\n\r\"\'<>]+', re.IGNORECASE)

UUID_REGEX = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (VLESS-Parser-Bot/1.0)",
}

async def fetch_text(session: aiohttp.ClientSession, url: str) -> str:
    try:
        async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status == 200:
                text = await resp.text()
                # Если файл base64 (без vless://), пробуем декодировать
                if "vless://" not in text.lower() and "vmess://" not in text.lower() and len(text.strip()) > 100:
                    try:
                        decoded = base64.b64decode(text.strip() + "==").decode('utf-8', errors='ignore')
                        if "vless://" in decoded.lower() or "vmess://" in decoded.lower():
                            return decoded
                    except Exception:
                        pass
                return text
            else:
                print(f"[fetch] {url} -> {resp.status}")
                return ""
    except Exception as e:
        print(f"[fetch error] {url}: {e}")
        return ""

def extract_configs(text: str, proto_filter: str = "vless") -> List[str]:
    """Извлекает конфиги нужного протокола. Если proto_filter == 'all' — все."""
    if not text:
        return []
    # Убираем комментарии profile-title и т.п.
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line)
    clean_text = "\n".join(lines)
    
    if proto_filter == "vless":
        found = VLESS_REGEX.findall(clean_text)
    elif proto_filter == "all":
        found = ALL_REGEX.findall(clean_text)
        # findall вернёт только группу, поэтому используем finditer
        found = [m.group(0) for m in ALL_REGEX.finditer(clean_text)]
    else:
        # по умолчанию vless, но берём все для отладки
        found = VLESS_REGEX.findall(clean_text)
    
    # Дедупликация c сохранением порядка
    seen = set()
    uniq = []
    for f in found:
        f = f.strip()
        # Обрезаем мусор в конце (закрывающие скобки и т.п.)
        f = f.rstrip('.,;\'")')
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    return uniq

def is_valid_vless(link: str) -> Tuple[bool, str]:
    """Синтаксическая валидация vless://"""
    try:
        if not link.startswith("vless://"):
            return False, "не vless://"
        # Парсим как URL
        # vless://uuid@host:port?params#remark
        without_scheme = link[8:]
        # Разделяем remark
        if "#" in without_scheme:
            without_scheme, remark = without_scheme.split("#", 1)
        # Разделяем query
        if "?" in without_scheme:
            host_part, query = without_scheme.split("?", 1)
            params = parse_qs(query)
        else:
            host_part = without_scheme
            params = {}
        
        if "@" not in host_part:
            return False, "нет @ (uuid@host)"
        uuid_part, hostport = host_part.rsplit("@", 1)
        uuid_part = unquote(uuid_part)
        if not UUID_REGEX.match(uuid_part):
            return False, f"невалидный UUID: {uuid_part}"
        if ":" not in hostport:
            return False, "нет порта host:port"
        host, port_str = hostport.rsplit(":", 1)
        if not host:
            return False, "пустой host"
        try:
            port = int(port_str)
            if not (1 <= port <= 65535):
                return False, f"порт вне диапазона: {port}"
        except:
            return False, f"невалидный порт: {port_str}"
        
        # Проверяем обязательные параметры reality
        # Не строго — просто предупреждение, но считаем валидным
        return True, "ok"
    except Exception as e:
        return False, str(e)

async def check_tcp(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
        writer.close()
        try:
            await writer.wait_closed()
        except:
            pass
        return True
    except:
        return False

def is_valid_any(link: str) -> Tuple[bool, str]:
    """Валидация для любого протокола (ss, trojan, vmess и т.д.) — базовая проверка"""
    if "://" not in link or "@" not in link and not link.startswith("vmess://"):
        # vmess может быть без @
        if link.startswith("vmess://"):
            try:
                b64part = link[8:].split("#",1)[0].split("?",1)[0].strip()
                # vmess часто base64 json
                decoded = base64.b64decode(b64part + "==").decode('utf-8', errors='ignore')
                if '"add"' in decoded or '"port"' in decoded:
                    return True, "ok vmess"
                return False, "bad vmess json"
            except Exception as e:
                return False, f"bad vmess: {e}"
        return False, "нет :// или @"
    if link.startswith("vless://"):
        return is_valid_vless(link)
    # Для остальных — просто проверяем что есть host:port или host
    try:
        # Базовая проверка что не пустой и не слишком короткий
        if len(link) < 15:
            return False, "too short"
        if "://" in link and len(link.split("://",1)[1]) < 5:
            return False, "no host"
        return True, "ok generic"
    except Exception as e:
        return False, str(e)

async def validate_configs(links: List[str], mode: str = "syntax", allow_generic: bool = False) -> List[str]:
    """Фильтрует невалидные конфиги. mode: none | syntax | tcp"""
    if mode == "none":
        return links
    valid = []
    for link in links:
        if allow_generic:
            ok, reason = is_valid_any(link)
        else:
            ok, reason = is_valid_vless(link)
        if not ok:
            continue
        if mode == "tcp" and link.startswith("vless://"):
            # Парсим host:port только для vless
            try:
                without_scheme = link[8:].split("#", 1)[0].split("?", 1)[0]
                hostport = without_scheme.rsplit("@", 1)[-1]
                host, port_str = hostport.rsplit(":", 1)
                port = int(port_str)
                if not await check_tcp(host, port, timeout=2.5):
                    continue
            except:
                continue
        valid.append(link)
    return valid

async def fetch_category(session: aiohttp.ClientSession, category_key: str, mode: str = "syntax") -> Dict:
    cfg = SOURCES.get(category_key)
    if not cfg:
        return {"key": category_key, "name": category_key, "configs": [], "raw_text": "", "error": "unknown category"}
    
    proto = "vless" if "VLESS" in cfg["name"] or "vless" in category_key.lower() or "white" in category_key.lower() or "black" in category_key.lower() else "all"
    # Для SS категории берём все
    if category_key == "ss_black":
        proto = "all"
    if category_key == "universal":
        proto = "vless"
    
    all_configs = []
    raw_parts = []
    errors = []
    
    for url in cfg["urls"]:
        text = await fetch_text(session, url)
        if not text:
            errors.append(f"{url} — пусто/ошибка")
            continue
        raw_parts.append(f"# Source: {url}\n{text.strip()}\n")
        configs = extract_configs(text, proto_filter=proto)
        all_configs.extend(configs)
    
    # Дедуп
    seen = set()
    uniq = []
    for c in all_configs:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    
    # Валидация — для ss/universal разрешаем generic
    allow_generic = category_key in ("ss_black", "universal")
    filtered = await validate_configs(uniq, mode=mode, allow_generic=allow_generic)
    
    return {
        "key": category_key,
        "name": cfg["name"],
        "description": cfg["description"],
        "configs": filtered,
        "raw_total": len(uniq),
        "errors": errors,
        "urls": cfg["urls"],
        "raw_text": "\n".join(raw_parts)[:200000],  # лимит
    }

async def fetch_all(mode: str = "syntax", categories: List[str] = None) -> Dict[str, Dict]:
    if categories is None:
        categories = list(SOURCES.keys())
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_category(session, k, mode=mode) for k in categories]
        results = await asyncio.gather(*tasks)
    return {r["key"]: r for r in results}

def make_subscription_content(configs: List[str], header: str = "") -> str:
    lines = []
    if header:
        lines.append(header)
    lines.extend(configs)
    return "\n".join(lines)

def make_base64_subscription(configs: List[str], header: str = "") -> str:
    content = make_subscription_content(configs, header)
    b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    return b64

def parse_vless_info(link: str) -> Dict:
    """Парсит vless для красивого отображения"""
    try:
        # remark после #
        remark = ""
        if "#" in link:
            remark = unquote(link.split("#", 1)[1])
        # uuid и host
        tmp = link[8:].split("#", 1)[0].split("?", 1)[0]
        uuid_part, hostport = tmp.rsplit("@", 1)
        host, port = hostport.rsplit(":", 1)
        # params
        params = {}
        if "?" in link:
            q = link.split("?", 1)[1].split("#", 1)[0]
            params = parse_qs(q)
        def get(k, d=""):
            return params.get(k, [d])[0]
        return {
            "remark": remark or f"{host}:{port}",
            "host": host,
            "port": port,
            "uuid": uuid_part,
            "sni": get("sni", get("serverName", "")),
            "type": get("type", ""),
            "security": get("security", ""),
            "fp": get("fp", ""),
        }
    except Exception as e:
        return {"remark": link[:40], "host": "?", "port": "?", "error": str(e)}
