import logging
from src.config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

# In-memory conversation history per user_id
# Format: {user_id: [{"role": "user"|"model", "text": str}]}
user_histories: dict[int, list[dict[str, str]]] = {}


def reset_conversation(user_id: int) -> int:
    """Clear conversation history for a user. Returns count of cleared messages."""
    count = len(user_histories.get(user_id, []))
    user_histories[user_id] = []
    return count


async def ask_gemini(user_id: int, prompt: str, system_instruction: str | None = None) -> str:
    """
    Send prompt to Gemini model with multi-turn conversation memory.
    """
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

        # Retrieve or initialize history
        if user_id not in user_histories:
            user_histories[user_id] = []

        history = user_histories[user_id]
        history.append({"role": "user", "text": prompt})

        # Keep history to last 16 turns to avoid context overflow
        if len(history) > 16:
            history = history[-16:]
            user_histories[user_id] = history

        # Format contents for SDK
        contents = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg["text"])]
                )
            )

        config = types.GenerateContentConfig()
        if system_instruction:
            config.system_instruction = system_instruction
        else:
            config.system_instruction = (
                "Ты — автономный ассистент Orbital Bridge, работающий на персональном ноутбуке разработчика. "
                "Проекты находятся в папке D:\\Orbital Bridge. "
                "Отвечай емко, профессионально, с красивым форматированием в Markdown (используй блоки кода). "
                "Помни контекст предыдущих сообщений диалога."
            )

        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=config,
        )

        reply_text = response.text or "<i>(Пустой ответ от модели)</i>"

        # Save model response to history
        history.append({"role": "model", "text": reply_text})
        return reply_text

    except Exception as e:
        logger.error(f"Gemini error: {e}", exc_info=True)
        return f"❌ <b>Ошибка Gemini API:</b>\n<code>{str(e)[:400]}</code>"
