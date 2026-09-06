import os
import base64
import qrcode
from io import BytesIO
from datetime import datetime, timezone, timedelta
from parser import make_subscription_content, make_base64_subscription

MSK = timezone(timedelta(hours=3))

def msk_now_str():
    return datetime.now(MSK).strftime("%Y-%m-%d %H:%M МСК")

def generate_header(profile_title: str, count: int) -> str:
    return "\n".join([
        f"# profile-title: {profile_title}",
        f"# profile-update-interval: 1",
        f"# subscription-userinfo: upload=0; download=0; total=10737418240000000; expire=2546249531",
        f"# Date/Time: {msk_now_str()}",
        f"# Количество: {count}",
        f"# Bot: @YourVlessParserBot",
        "",
    ])

def save_subscription_files(base_dir: str, category_key: str, configs: list, profile_title: str):
    """
    Сохраняет 2 файла:
    - {key}.txt (plain)
    - {key}_base64.txt (base64)
    Возвращает пути
    """
    os.makedirs(base_dir, exist_ok=True)
    header = generate_header(profile_title, len(configs))
    plain_content = make_subscription_content(configs, header)
    b64_content = base64.b64encode(plain_content.encode('utf-8')).decode('utf-8')
    
    plain_path = os.path.join(base_dir, f"{category_key}.txt")
    b64_path = os.path.join(base_dir, f"{category_key}_base64.txt")
    
    with open(plain_path, "w", encoding="utf-8") as f:
        f.write(plain_content)
    with open(b64_path, "w", encoding="utf-8") as f:
        f.write(b64_content)
    
    return plain_path, b64_path, plain_content, b64_content

def generate_qr_bytes(text: str) -> bytes:
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def get_subscription_stats(configs: list) -> str:
    if not configs:
        return "0 конфигов (источник пуст, попробуй позже)"
    # Считаем уникальные хосты
    hosts = set()
    for c in configs:
        try:
            host = c.split("@", 1)[1].split(":", 1)[0]
            hosts.add(host)
        except:
            pass
    return f"{len(configs)} конфигов, {len(hosts)} серверов"
