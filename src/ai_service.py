import logging
from pathlib import Path
from src.config import GEMINI_API_KEY, PROJECTS_DIR
from src.ag_manager import restart_ag_process, get_ag_status
from src.projects import get_active_project

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
    Send prompt to Gemini model with active project context and conversation memory.
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

        # Gather active project context
        active_proj = get_active_project(user_id)
        proj_context = ""
        if active_proj:
            proj_path = PROJECTS_DIR / active_proj
            if proj_path.exists():
                files = [f.name for f in proj_path.iterdir()][:15]
                proj_context = (
                    f"\n[АКТИВНЫЙ ПРОЕКТ ПОЛЬЗОВАТЕЛЯ]: {active_proj}\n"
                    f"Путь: {proj_path}\n"
                    f"Файлы в проекте: {', '.join(files)}\n"
                )
                gemini_md_path = proj_path / "GEMINI.md"
                if gemini_md_path.exists():
                    proj_context += f"Инструкции GEMINI.md:\n{gemini_md_path.read_text(encoding='utf-8')[:500]}\n"

        system_instruction = (
            "Ты — автономный ассистент Orbital Bridge, работающий на персональном ноутбуке разработчика. "
            "Отвечай емко, профессионально, с красивым форматированием в Markdown (используй блоки кода). "
            "Помни контекст предыдущих сообщений диалога.\n"
            f"{proj_context}"
        )

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
            system_instruction=system_instruction
        )

        # Update model to gemini-3.8-flash
        response = await client.aio.models.generate_content(
            model="gemini-3.8-flash",
            contents=contents,
            config=config,
        )

        reply_text = response.text or "<i>(Пустой ответ от модели)</i>"
        history.append({"role": "model", "text": reply_text})
        return reply_text

    except Exception as e:
        err_msg = str(e)
        logger.error(f"Gemini error: {err_msg}", exc_info=True)
        if "User location is not supported" in err_msg:
            return (
                "🌐 <b>Ограничение региона Google (User location not supported)</b>\n\n"
                "Google блокирует прямые запросы к Gemini API с локального IP твоего интернет-провайдера без VPN.\n\n"
                "🚀 <b>Как решить это идеально:</b>\n"
                "1. <b>Развернуть бота на Render:</b> сервер Render находится во Франкфурте (Германия) — запросы к Gemini 3.8 Flash будут летать мгновенно и без ограничений!\n"
                "2. <b>Либо включить VPN</b> на ноутбуке."
            )
        return f"❌ <b>Ошибка Gemini API:</b>\n<code>{err_msg[:400]}</code>"
