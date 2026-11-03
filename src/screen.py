import io
import os
import subprocess
import tempfile
import datetime
from PIL import Image


def capture_desktop_screenshot() -> tuple[bytes, str]:
    """
    Capture the current desktop screen with multi-level fallbacks.
    Returns:
        tuple[bytes, str]: (image_bytes, info_string)
    """
    img = None
    last_err = ""

    # Strategy 1: mss
    try:
        import mss
        with mss.mss() as sct:
            monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
    except Exception as e:
        last_err = f"mss: {e}"

    # Strategy 2: Pillow ImageGrab
    if img is None:
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab(all_screens=True)
        except Exception as e:
            last_err = f"{last_err} | ImageGrab: {e}"

    # Strategy 3: PowerShell .NET CopyFromScreen into temp file
    if img is None and os.name == "nt":
        tmp_path = os.path.join(tempfile.gettempdir(), f"orb_screen_{int(datetime.datetime.now().timestamp())}.png")
        ps_code = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
$bmp.Save('{tmp_path}')
$g.Dispose()
$bmp.Dispose()
"""
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_code],
                capture_output=True,
                timeout=10,
            )
            if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 1000:
                img = Image.open(tmp_path)
                # Load data before deleting file
                img.load()
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            else:
                err_out = res.stderr.decode("utf-8", errors="replace").strip()
                if err_out:
                    last_err = f"{last_err} | PS: {err_out}"
        except Exception as e:
            last_err = f"{last_err} | PS: {e}"

    if img is None:
        raise RuntimeError(
            "Экран сейчас недоступен для захвата.\n\n"
            "⚠️ <b>Возможные причины:</b>\n"
            "• Ноутбук заблокирован (экран блокировки Win+L)\n"
            "• Дисплей выключен или ушел в спящий режим\n"
            "• Бот запущен в неинтерактивной фоновой сессии\n\n"
            "💡 <b>Решение:</b> открой ноутбук и запусти <code>run.bat</code> прямо на рабочем столе."
        )

    # Convert RGBA to RGB for JPEG compatibility
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    width, height = img.size
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    info = f"📸 <b>Скриншот экрана ноутбука</b>\n📐 Разрешение: {width}x{height} | ⏱ {timestamp}"

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    buf.seek(0)
    return buf.getvalue(), info
