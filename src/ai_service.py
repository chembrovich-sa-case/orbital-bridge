import logging
from src.config import GEMINI_API_KEY

logger = logging.getLogger(__name__)


async def ask_gemini(prompt: str, system_instruction: str | None = None) -> str:
    """
    Send prompt to Gemini model using official google-genai SDK.
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

        config = types.GenerateContentConfig()
        if system_instruction:
            config.system_instruction = system_instruction
        else:
            config.system_instruction = (
                "Ты — автономный ассистент Orbital Bridge, работающий на личном ноутбуке разработчика. "
                "Отвечай кратко, чётко, информативно. Если пишешь код, используй Markdown-блоки."
            )

        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=config,
        )

        return response.text or "<i>(Пустой ответ от модели)</i>"

    except Exception as e:
        logger.error(f"Gemini error: {e}", exc_info=True)
        return f"❌ <b>Ошибка Gemini API:</b>\n<code>{str(e)[:400]}</code>"
