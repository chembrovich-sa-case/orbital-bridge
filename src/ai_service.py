import logging
from src.config import GEMINI_API_KEY
from src.ag_manager import restart_ag_process, get_ag_status

logger = logging.getLogger(__name__)

# In-memory conversation history per user_id
user_histories: dict[int, list[dict[str, str]]] = {}


def reset_conversation(user_id: int) -> int:
    """Clear conversation history for a user. Returns count of cleared messages."""
    count = len(user_histories.get(user_id, []))
    user_histories[user_id] = []
    return count


async def ask_gemini(user_id: int, prompt: str) -> str:
    """
    Send prompt to Gemini model with conversation memory and AG actions.
    """
    lower = prompt.lower().strip()

    # Fast-path intent: restart Antigravity / AG.exe
    if any(k in lower for k in ("перезапусти ag", "рестарт ag", "restart ag", "перезапусти антигравити", "подними ag", "ag завис", "перезагрузи ag")):
        logger.info(f"Intent recognized: restart AG by user {user_id}")
        res = await restart_ag_process(as_admin=True)
        status_icon = "🟢" if res["success"] else "⚠️"
        return f"{status_icon} <b>Выполнен перезапуск Antigravity (AG.exe):</b>\n\n{res['message']}"

    # Fast-path intent: check AG status
    if any(k in lower for k in ("статус ag", "ag работает", "работает ли ag", "antigravity запущен")):
        stat = get_ag_status()
        if stat["running"]:
            return f"🟢 <b>Antigravity (AG.exe) активен!</b>\nPID: <code>{stat['pid']}</code> | RAM: <code>{stat['memory_mb']} MB</code>"
        else:
            return "🔴 <b>Antigravity (AG.exe) остановлен или не запущен.</b>\nТы можешь написать <i>«перезапусти AG»</i> или нажать кнопку в меню."

    if not GEMINI_API_KEY:
        return (
            "⚠️ <b>Gemini API не настроен</b>\n\n"
            "Чтобы я мог отвечать на вопросы и писать код прямо в Telegram, "
            "добавь <code>GEMINI_API_KEY=...</code> в свой файл <code>.env</code>."
        )

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GEMINI_API_KEY)

        if user_id not in user_histories:
            user_histories[user_id] = []

        history = user_histories[user_id]
        history.append({"role": "user", "text": prompt})

        if len(history) > 16:
            history = history[-16:]
            user_histories[user_id] = history

        contents = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg["text"])]
                )
            )

        config = types.GenerateContentConfig(
            system_instruction=(
                "Ты — автономный ассистент Orbital Bridge, работающий на персональном ноутбуке разработчика. "
                "Проекты находятся в D:\\Orbital Bridge, там же находится системный конфигуратор AG.exe. "
                "Отвечай емко, профессионально, с красивым форматированием в Markdown. "
                "Помни контекст предыдущих сообщений диалога."
            )
        )

        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=config,
        )

        reply_text = response.text or "<i>(Пустой ответ от модели)</i>"
        history.append({"role": "model", "text": reply_text})
        return reply_text

    except Exception as e:
        logger.error(f"Gemini error: {e}", exc_info=True)
        return f"❌ <b>Ошибка Gemini API:</b>\n<code>{str(e)[:400]}</code>"
