import io
from pathlib import Path
import datetime
from PIL import Image


def capture_desktop_screenshot() -> tuple[bytes, str]:
    """
    Capture the current desktop screen.
    Returns:
        tuple[bytes, str]: (image_bytes, info_string)
    """
    try:
        import mss
        with mss.mss() as sct:
            # Capture the primary monitor
            monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            sct_img = sct.grab(monitor)
            # Convert to PIL Image
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
    except Exception:
        # Fallback to Pillow ImageGrab
        from PIL import ImageGrab
        img = ImageGrab.grab()

    width, height = img.size
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    info = f"📸 <b>Скриншот экрана</b>\n📐 Разрешение: {width}x{height} | ⏱ {timestamp}"

    # Compress slightly to JPEG for quick sending in Telegram
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    buf.seek(0)
    return buf.getvalue(), info
