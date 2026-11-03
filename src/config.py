import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Allowed user IDs (comma-separated or single)
raw_users = os.getenv("ALLOWED_USER_IDS", "").strip()
if raw_users:
    ALLOWED_USER_IDS = [int(u.strip()) for u in raw_users.split(",") if u.strip().isdigit()]
else:
    ALLOWED_USER_IDS = []

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# Base directory where /new_project creates projects
DEFAULT_PROJECTS_DIR = str(ROOT_DIR.parent)
PROJECTS_DIR = Path(os.getenv("PROJECTS_DIR", DEFAULT_PROJECTS_DIR)).resolve()

# Watchdog settings
WATCHDOG_ENABLED = os.getenv("WATCHDOG_ENABLED", "true").lower() in ("true", "1", "yes")
WATCHDOG_INTERVAL = int(os.getenv("WATCHDOG_INTERVAL", "60"))
BATTERY_ALERT_THRESHOLD = int(os.getenv("BATTERY_ALERT_THRESHOLD", "20"))


def is_user_allowed(user_id: int) -> bool:
    """Check if the user is authorized to use the bot."""
    if not ALLOWED_USER_IDS:
        return True  # If not set yet, allow for initial configuration
    return user_id in ALLOWED_USER_IDS
