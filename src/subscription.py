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

def generate_igareck_style_header(profile_title: str, count: int) -> str:
    """Точная шапка как в примере igareck — для больших RAW подписок"""
    # Формат даты как в примере: 2026-07-22 / 11:47 (Moscow)
    msk = datetime.now(MSK)
    date_str = msk.strftime("%Y-%m-%d / %H:%M (Moscow)")
    return "\n".join([
        f"# profile-title: {profile_title}",
        f"# profile-update-interval: 1",
        f"# Date/Time: {date_str}",
        f"# Количество: {count}",
        f"# For more info and VPN-configs - visit: www.github.com/igareck/vpn-configs-for-russia",
        f"",
        f"# RU: Эта подписка может содержать Trojan/Hysteria2/Hy2 с legacy-параметрами insecure=1 или allowInsecure=1.",
        f"# RU: Такие конфигурации могут вызывать ошибку запуска Xray-core v26.2.6 и новее в клиентах, использующих ядро Xray-core.",
        f"# RU: Для совместимости используйте Sing-box для Trojan/Hysteria2/Hy2 или Xray-core v26.1.23 (последняя проверенная рабочая версия для таких конфигов).",
        f"",
        f"# EN: This subscription may contain Trojan/Hysteria2/Hy2 configs with legacy parameters: insecure=1 or allowInsecure=1.",
        f"# EN: Such configs may cause Xray-core startup errors with Xray-core v26.2.6 and newer in clients that use the Xray-core engine.",
        f"# EN: For compatibility, use Sing-box for Trojan/Hysteria2/Hy2 or Xray-core v26.1.23, the last confirmed working version for such configs.",
        f"",
    ])

def generate_aggregated_content(profile_title: str, configs: list) -> str:
    header = generate_igareck_style_header(profile_title, len(configs))
    return make_subscription_content(configs, header)

def save_subscription_files(base_dir: str, category_key: str, configs: list, profile_title: str, use_igareck_header: bool = False):
    """
    Сохраняет 2 файла:
    - {key}.txt (plain)
    - {key}_base64.txt (base64)
    Возвращает пути
    """
    os.makedirs(base_dir, exist_ok=True)
    if use_igareck_header:
        header = generate_igareck_style_header(profile_title, len(configs))
    else:
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

def save_aggregated_file(base_dir: str, filename: str, profile_title: str, configs: list):
    """Сохраняет одну большую подписку в стиле igareck (с расширенной шапкой)"""
    os.makedirs(base_dir, exist_ok=True)
    content = generate_aggregated_content(profile_title, configs)
    # plain
    path = os.path.join(base_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    # base64 вариант тоже делаем
    b64_path = os.path.join(base_dir, filename.replace(".txt", "_base64.txt"))
    b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    with open(b64_path, "w", encoding="utf-8") as f:
        f.write(b64)
    return path, b64_path, content, b64

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
