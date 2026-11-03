import time
import datetime
from pathlib import Path
import psutil
import httpx
from src.config import GEMINI_API_KEY, PROJECTS_DIR


def make_bar(percent: float, length: int = 10) -> str:
    """Generate a clean ASCII progress bar."""
    percent = max(0.0, min(100.0, percent))
    filled = int(round(length * percent / 100.0))
    return "■" * filled + "□" * (length - filled)


def format_duration(seconds: float) -> str:
    """Format seconds into readable days/hours/minutes."""
    mins, _ = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    days, hours = divmod(hours, 24)
    parts = []
    if days > 0:
        parts.append(f"{days}д")
    if hours > 0 or days > 0:
        parts.append(f"{hours}ч")
    parts.append(f"{mins}м")
    return " ".join(parts)


async def check_internet_latency() -> tuple[bool, float]:
    """Test internet connectivity and measure latency in milliseconds."""
    test_urls = ["https://1.1.1.1", "https://8.8.8.8", "https://www.google.com"]
    async with httpx.AsyncClient(timeout=2.5, follow_redirects=True) as client:
        for url in test_urls:
            try:
                t0 = time.perf_counter()
                resp = await client.get(url)
                latency = (time.perf_counter() - t0) * 1000
                if resp.status_code in (200, 204, 301, 302):
                    return True, round(latency, 1)
            except Exception:
                continue
    return False, 0.0


async def check_gemini_api() -> tuple[bool, str]:
    """Test Gemini / Google API connectivity."""
    if not GEMINI_API_KEY:
        return False, "API ключ не задан"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
            )
            if resp.status_code == 200:
                return True, "Online (Gemini 2.5/3.8)"
            else:
                return False, f"HTTP {resp.status_code}"
    except Exception as e:
        return False, f"Ошибка сети: {str(e)[:30]}"


async def get_system_dashboard() -> str:
    """Generate a high-aesthetic Telegram dashboard text."""
    # Uptime
    boot_time = psutil.boot_time()
    uptime_sec = time.time() - boot_time
    uptime_str = format_duration(uptime_sec)

    # CPU
    cpu_percent = psutil.cpu_percent(interval=0.2)
    cpu_bar = make_bar(cpu_percent)
    cpu_count = psutil.cpu_count(logical=True)

    # RAM
    ram = psutil.virtual_memory()
    ram_bar = make_bar(ram.percent)
    ram_used_gb = ram.used / (1024**3)
    ram_total_gb = ram.total / (1024**3)

    # Disk C:
    disk_lines = []
    try:
        disk_c = psutil.disk_usage("C:\\")
        disk_c_bar = make_bar(disk_c.percent)
        disk_c_free = disk_c.free / (1024**3)
        disk_lines.append(f"├─ <b>Диск C:</b> <code>[{disk_c_bar}]</code> {disk_c_free:.1f} GB своб.")
    except Exception:
        pass

    # Disk D: (Orbital Bridge projects disk)
    try:
        disk_d = psutil.disk_usage("D:\\")
        disk_d_bar = make_bar(disk_d.percent)
        disk_d_free = disk_d.free / (1024**3)
        disk_lines.append(f"├─ <b>Диск D:</b> <code>[{disk_d_bar}]</code> {disk_d_free:.1f} GB своб. <i>(Projects)</i>")
    except Exception:
        pass

    disk_section = "\n".join(disk_lines) if disk_lines else "├─ <b>Диск:</b> Доступен"

    # Battery
    battery = psutil.sensors_battery()
    if battery:
        bat_percent = int(battery.percent)
        is_charging = battery.power_plugged
        bat_status = "⚡ Заряжается" if is_charging else "🔋 От батареи"
        bat_str = f"{bat_status} ({bat_percent}%)"
    else:
        bat_str = "🔌 Питание от сети"

    # Internet check
    net_ok, latency = await check_internet_latency()
    net_str = f"🟢 {latency} ms (Стабильно)" if net_ok else "🔴 Оффлайн / Нет связи"

    # Gemini API check
    gem_ok, gem_msg = await check_gemini_api()
    gem_str = f"🟢 {gem_msg}" if gem_ok else f"⚪ {gem_msg}"

    now_str = datetime.datetime.now().strftime("%H:%M:%S")

    dashboard = (
        "<code>╔══════════════════════════════════════╗\n"
        "║         ⚡ ORBITAL BRIDGE v1.0       ║\n"
        "╚══════════════════════════════════════╝</code>\n\n"
        f"🟢 <b>Статус:</b> В сети (Online)\n"
        f"⏱ <b>Uptime ноута:</b> <code>{uptime_str}</code> (Обновлено: {now_str})\n"
        f"📁 <b>Воркспейс:</b> <code>{PROJECTS_DIR}</code>\n\n"
        "<b>💻 СИСТЕМА</b>\n"
        f"├─ <b>CPU:</b>  <code>[{cpu_bar}]</code> {cpu_percent:.1f}% ({cpu_count} ядер)\n"
        f"├─ <b>RAM:</b>  <code>[{ram_bar}]</code> {ram.percent:.1f}% ({ram_used_gb:.1f}/{ram_total_gb:.1f} GB)\n"
        f"{disk_section}\n"
        f"└─ <b>Батарея:</b> {bat_str}\n\n"
        "<b>🌐 СЕТЬ И СЕРВИСЫ</b>\n"
        f"├─ <b>Интернет:</b> {net_str}\n"
        f"├─ <b>Gemini AI:</b> {gem_str}\n"
        f"└─ <b>Режим:</b> 🛡️ <code>Full Access (Owner Only)</code>"
    )
    return dashboard
