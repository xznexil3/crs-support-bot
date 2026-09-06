from aiohttp import web
import asyncio
import os

async def health(request):
    return web.Response(text="OK - VLESS parser bot is running", content_type="text/plain")

async def stats(request):
    from pathlib import Path
    import json
    data_dir = Path(__file__).parent.parent / "data"
    files = list(data_dir.glob("*.txt"))
    info = {f.name: f.stat().st_size for f in files if f.is_file()}
    return web.json_response({"status": "ok", "files": info})

def create_health_app():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    app.router.add_get("/stats", stats)
    return app

async def start_health_server():
    port = int(os.getenv("PORT", "8080"))
    app = create_health_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"✅ Health server on 0.0.0.0:{port}")
    return runner
