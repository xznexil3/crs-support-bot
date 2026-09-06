import os
import base64
import aiohttp
import logging

logger = logging.getLogger(__name__)

async def get_file_sha(session, repo, path, token, branch="main"):
    """Получает sha файла если существует, иначе None"""
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "VLESS-Parser-Bot"
    }
    params = {"ref": branch}
    try:
        async with session.get(url, headers=headers, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("sha")
            elif resp.status == 404:
                return None
            else:
                txt = await resp.text()
                logger.warning(f"get sha {path} -> {resp.status}: {txt[:200]}")
                return None
    except Exception as e:
        logger.error(f"get sha error: {e}")
        return None

async def push_file_to_github(repo, path, content_str, token, branch="main", message=None, retries=2):
    """
    Заливает файл в GitHub через API. Content_str - обычный текст, внутри закодируем в base64.
    Возвращает raw_url или None. При 409 пробует перечитать sha и повторить.
    """
    if not token:
        logger.warning("GITHUB_TOKEN не задан, пропуск push")
        return None
    if not repo or "/" not in repo:
        logger.warning(f"Неверный repo: {repo}")
        return None

    for attempt in range(retries + 1):
        async with aiohttp.ClientSession() as session:
            sha = await get_file_sha(session, repo, path, token, branch)
            url = f"https://api.github.com/repos/{repo}/contents/{path}"
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "VLESS-Parser-Bot"
            }
            b64 = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
            payload = {
                "message": message or f"update {path}",
                "content": b64,
                "branch": branch,
            }
            if sha:
                payload["sha"] = sha

            async with session.put(url, headers=headers, json=payload) as resp:
                txt = await resp.text()
                if resp.status in (200, 201):
                    logger.info(f"✅ GitHub push OK: {path} -> {resp.status} (attempt {attempt+1})")
                    raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
                    return raw_url
                elif resp.status == 409 and attempt < retries:
                    logger.warning(f"409 conflict {path}, retry {attempt+1}/{retries}...")
                    import asyncio
                    await asyncio.sleep(1)
                    continue
                else:
                    logger.error(f"❌ GitHub push FAIL {path} -> {resp.status}: {txt[:500]}")
                    return None
    return None

async def push_aggregated_subscriptions(aggregated_files: dict, repo, token, branch="main"):
    """
    aggregated_files: dict {path: content_str}
    Заливает каждый и возвращает dict {path: raw_url}
    """
    results = {}
    for path, content in aggregated_files.items():
        # Делаем понятный коммит
        lines = content.count("\n")
        raw = await push_file_to_github(repo, path, content, token, branch, message=f"update {path} — {lines} lines")
        if raw:
            results[path] = raw
        # Чтобы неупереться в rate limit, небольшая пауза
        import asyncio
        await asyncio.sleep(0.5)
    return results
