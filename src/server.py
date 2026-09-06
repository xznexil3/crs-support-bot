"""
Мини HTTP-сервер для отдачи подписок по ссылке.
Запускается параллельно с ботом, если нужно раздавать подписки как URL.

GET /sub/black_all       -> plain подписка
GET /sub/black_all/b64   -> base64
GET /                    -> список всех подписок
"""
import os
from pathlib import Path
from aiohttp import web
import config

DATA_DIR = Path(__file__).parent.parent / "data"

async def handle_list(request):
    html = ["<h1>VLESS Подписки</h1><ul>"]
    for key, cfg in config.SOURCES.items():
        html.append(f"<li><b>{cfg['name']}</b> — {cfg['description']}<br>")
        html.append(f"Plain: <a href='/sub/{key}'>/sub/{key}</a> | ")
        html.append(f"Base64: <a href='/sub/{key}/b64'>/sub/{key}/b64</a> | ")
        html.append(f"Файл: <code>{key}.txt</code></li>")
    html.append("</ul><p>Добавь ссылку в клиент как подписку. Обновляется каждые 30 мин.</p>")
    return web.Response(text="".join(html), content_type="text/html")

async def handle_sub(request):
    key = request.match_info.get("key")
    b64 = request.match_info.get("b64", "")
    if key not in config.SOURCES and not key.startswith("GROUP"):
        return web.Response(text="unknown key", status=404)
    filename = f"{key}_base64.txt" if b64 else f"{key}.txt"
    path = DATA_DIR / filename
    if not path.exists():
        return web.Response(text="not generated yet, try later", status=404)
    content = path.read_text(encoding="utf-8")
    ctype = "text/plain; charset=utf-8"
    # Для base64 некоторые клиенты ждут именно base64 строку без заголовков
    return web.Response(text=content, content_type=ctype, headers={
        "Content-Disposition": f"inline; filename={filename}",
        "Cache-Control": "no-cache",
    })

def create_app():
    app = web.Application()
    app.router.add_get("/", handle_list)
    app.router.add_get("/sub/{key}", handle_sub)
    app.router.add_get("/sub/{key}/{b64}", handle_sub)
    return app

if __name__ == "__main__":
    app = create_app()
    port = config.PORT
    print(f"🌐 HTTP подписок на http://0.0.0.0:{port}/sub/black_all")
    web.run_app(app, host="0.0.0.0", port=port)
