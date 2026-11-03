import asyncio
import logging
import os
import sys
from pathlib import Path
from aiohttp import web

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    BufferedInputFile,
    BotCommand,
)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.config import (
    BOT_TOKEN,
    ALLOWED_USER_IDS,
    is_user_allowed,
    WATCHDOG_ENABLED,
    WATCHDOG_INTERVAL,
    BATTERY_ALERT_THRESHOLD,
    PROJECTS_DIR,
)
from src.dashboard import get_system_dashboard, check_internet_latency
from src.terminal import run_terminal_command, format_command_output
from src.screen import capture_desktop_screenshot
from src.projects import (
    list_projects,
    scaffold_project,
    get_active_project,
    set_active_project,
)
from src.ai_service import ask_gemini, reset_conversation
from src.ag_manager import restart_ag_process, get_ag_status
from src.keyboards import (
    get_main_keyboard,
    get_projects_keyboard,
    get_project_actions_keyboard,
    get_templates_keyboard,
    get_back_keyboard,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("orbital-bridge")

storage = MemoryStorage()
dp = Dispatcher(storage=storage)


class NewProjectStates(StatesGroup):
    waiting_for_name = State()


# ------------------- Security Middleware Filter -------------------
@dp.message.outer_middleware()
@dp.callback_query.outer_middleware()
async def auth_middleware(handler, event, data):
    user = getattr(event, "from_user", None)
    if user:
        if not is_user_allowed(user.id):
            logger.warning(f"Unauthorized access attempt from user_id={user.id} (@{user.username})")
            if isinstance(event, Message):
                await event.answer(
                    f"⛔ <b>Доступ ограничен</b>\n\n"
                    f"Этот бот привязан к персональному аккаунту владельца.\n"
                    f"Твой Telegram ID: <code>{user.id}</code>\n"
                    f"Чтобы получить доступ, добавь этот ID в <code>ALLOWED_USER_IDS</code> в настройках Render / .env."
                )
            elif isinstance(event, CallbackQuery):
                await event.answer("⛔ Доступ запрещен", show_alert=True)
            return
    return await handler(event, data)


# ------------------- Handlers -------------------

@dp.message(CommandStart())
@dp.message(Command("status"))
async def cmd_status(message: Message):
    """Show the real-time system dashboard with active project info."""
    dashboard = await get_system_dashboard()
    active = get_active_project(message.from_user.id)
    if active:
        dashboard += f"\n\n🎯 <b>Активный проект для диалога:</b> <code>{active}</code>"
    await message.answer(dashboard, reply_markup=get_main_keyboard(), parse_mode="HTML")


@dp.callback_query(F.data == "refresh_status")
async def cb_refresh_status(callback: CallbackQuery):
    """Refresh the dashboard."""
    dashboard = await get_system_dashboard()
    active = get_active_project(callback.from_user.id)
    if active:
        dashboard += f"\n\n🎯 <b>Активный проект для диалога:</b> <code>{active}</code>"
    try:
        await callback.message.edit_text(
            dashboard, reply_markup=get_main_keyboard(), parse_mode="HTML"
        )
        await callback.answer("⚡ Refresh complete!")
    except Exception:
        await callback.answer("Данные актуальны")


@dp.callback_query(F.data == "back_to_menu")
async def cb_back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Return to main status dashboard."""
    await state.clear()
    dashboard = await get_system_dashboard()
    active = get_active_project(callback.from_user.id)
    if active:
        dashboard += f"\n\n🎯 <b>Активный проект для диалога:</b> <code>{active}</code>"
    await callback.message.edit_text(
        dashboard, reply_markup=get_main_keyboard(), parse_mode="HTML"
    )
    await callback.answer()


@dp.message(Command("restart_ag"))
@dp.callback_query(F.data == "restart_ag")
async def handle_restart_ag(event: Message | CallbackQuery):
    """Force restart AG.exe as administrator."""
    message = event if isinstance(event, Message) else event.message
    if isinstance(event, CallbackQuery):
        await event.answer("⚡ Перезапускаю AG...")

    wait_msg = await message.answer(
        "⏳ <i>Перезапускаю Antigravity (AG.exe)...</i>",
        parse_mode="HTML",
    )

    result = await restart_ag_process(as_admin=True)

    if result["success"]:
        text = (
            f"🎉 <b>Antigravity успешно перезапущен!</b>\n\n"
            f"📍 Файл: <code>D:\\Orbital Bridge\\AG.exe</code>\n"
            f"🆔 PID: <code>{result['pid']}</code>\n"
            f"📊 Память: <code>{result.get('memory_mb', 0)} MB</code>\n"
            f"🛡️ Права: <b>Administrator (Elevated)</b>"
        )
    else:
        text = f"⚠️ <b>Результат операции:</b>\n{result['message']}"

    await wait_msg.edit_text(text, reply_markup=get_main_keyboard(), parse_mode="HTML")


@dp.message(Command("new_chat"))
@dp.callback_query(F.data == "new_conversation")
async def handle_new_conversation(event: Message | CallbackQuery):
    """Reset AI conversation history for fresh chat."""
    user = event.from_user
    cleared = reset_conversation(user.id)
    active = get_active_project(user.id)
    proj_str = f" по проекту <b>{active}</b>" if active else ""
    text = (
        f"✨ <b>New Conversation{proj_str}</b>\n\n"
        f"История диалога очищена ({cleared} сообщ.). Контекст обновлен.\n"
        "Задавай новый вопрос или команду — агент готов с чистого листа!"
    )
    if isinstance(event, CallbackQuery):
        await event.answer("💬 Новый диалог начат!")
        await event.message.answer(text, reply_markup=get_main_keyboard(), parse_mode="HTML")
    else:
        await event.answer(text, reply_markup=get_main_keyboard(), parse_mode="HTML")


@dp.message(Command("screen"))
@dp.callback_query(F.data == "take_screenshot")
async def handle_screenshot(event: Message | CallbackQuery):
    """Capture screen and send photo."""
    message = event if isinstance(event, Message) else event.message
    if isinstance(event, CallbackQuery):
        await event.answer("📸 Снимаю экран...")

    wait_msg = await message.answer("⏳ <i>Делаю снимок экрана...</i>", parse_mode="HTML")
    try:
        img_bytes, caption = capture_desktop_screenshot()
        photo = BufferedInputFile(img_bytes, filename="screen.jpg")
        await wait_msg.delete()
        await message.answer_photo(photo, caption=caption, parse_mode="HTML")
    except Exception as e:
        await wait_msg.edit_text(f"❌ {str(e)}", parse_mode="HTML")


@dp.message(Command("cmd"))
async def cmd_terminal(message: Message):
    """Execute a shell command locally in active project or projects root."""
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "💻 <b>Консоль</b>\n\n"
            "Использование: <code>/cmd &lt;команда&gt;</code>\n"
            "Пример:\n"
            "• <code>/cmd dir</code>\n"
            "• <code>/cmd git status</code>\n"
            "• <code>/cmd python --version</code>",
            parse_mode="HTML",
        )
        return

    command = parts[1].strip()
    active = get_active_project(message.from_user.id)
    cwd = str(PROJECTS_DIR / active) if (active and (PROJECTS_DIR / active).exists()) else str(PROJECTS_DIR)

    status_msg = await message.answer(
        f"⏳ <i>Выполняю:</i> <code>{command}</code>...",
        parse_mode="HTML",
    )
    result = await run_terminal_command(command, cwd=cwd)
    formatted = format_command_output(command, result)
    await status_msg.edit_text(formatted, parse_mode="HTML")


@dp.message(Command("projects"))
@dp.callback_query(F.data == "list_projects")
async def handle_projects(event: Message | CallbackQuery):
    """List projects in D:\\Orbital Bridge with active highlight."""
    user = event.from_user
    active = get_active_project(user.id)
    projects = list_projects()

    active_info = f"\n🎯 <b>Текущий активный проект:</b> <code>{active}</code>\n" if active else "\n<i>(Активный проект не выбран — выбери из списка ниже)</i>\n"

    text = (
        f"📁 <b>Каталог проектов:</b> <code>{PROJECTS_DIR}</code>\n"
        f"{active_info}\n"
        f"Всего проектов: <b>{len(projects)}</b>\n"
        "Выбери проект для управления, настройки или чтения файлов:"
    )
    keyboard = get_projects_keyboard(projects, active_proj=active)
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=keyboard, parse_mode="HTML")


@dp.callback_query(F.data.startswith("proj_info:"))
async def cb_project_info(callback: CallbackQuery):
    """Show details of a specific project with management buttons."""
    proj_name = callback.data.split(":", 1)[1]
    target_dir = PROJECTS_DIR / proj_name
    if not target_dir.exists():
        await callback.answer("Папка не найдена", show_alert=True)
        return

    user = callback.from_user
    is_active = (get_active_project(user.id) == proj_name)

    has_git = (target_dir / ".git").exists()
    has_ag = (target_dir / ".gemini").exists() or (target_dir / "GEMINI.md").exists()

    git_str = "✅ Git подключен" if has_git else "❌ Нет Git"
    ag_str = "🚀 FULL Antigravity Workspace" if has_ag else "📁 Стандартный проект"
    active_str = "🎯 <b>АКТИВНЫЙ ПРОЕКТ</b> (сообщения отправляются сюда)" if is_active else "⚪ Не активен"

    text = (
        f"📂 <b>Проект:</b> <code>{proj_name}</code>\n"
        f"📍 <b>Путь:</b> <code>{target_dir}</code>\n"
        f"Статус: {active_str}\n"
        f"Тип: {ag_str}\n"
        f"Контроль версий: {git_str}\n\n"
        "Нажми кнопку ниже, чтобы сделать его активным для диалога:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_project_actions_keyboard(proj_name, is_active=is_active),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("set_active:"))
async def cb_set_active(callback: CallbackQuery):
    """Set active project for this user."""
    proj_name = callback.data.split(":", 1)[1]
    user = callback.from_user
    success = set_active_project(user.id, proj_name)
    if success:
        await callback.answer(f"🎯 Проект {proj_name} теперь активен!", show_alert=True)
        text = (
            f"🎯 <b>Проект <code>{proj_name}</code> теперь активен!</b>\n\n"
            f"📍 Путь: <code>{PROJECTS_DIR / proj_name}</code>\n\n"
            "Теперь все твои сообщения без слеша и команды <code>/cmd</code> будут выполняться в контексте этого проекта!"
        )
        await callback.message.edit_text(
            text,
            reply_markup=get_project_actions_keyboard(proj_name, is_active=True),
            parse_mode="HTML",
        )
    else:
        await callback.answer("Ошибка: папка не найдена", show_alert=True)


@dp.callback_query(F.data.startswith("proj_files:"))
async def cb_proj_files(callback: CallbackQuery):
    """Show list of files in project."""
    proj_name = callback.data.split(":", 1)[1]
    target_dir = PROJECTS_DIR / proj_name
    if not target_dir.exists():
        await callback.answer("Папка не найдена", show_alert=True)
        return

    try:
        files = [f.name for f in target_dir.iterdir()][:25]
    except Exception:
        files = []

    text = (
        f"📄 <b>Файлы проекта <code>{proj_name}</code>:</b>\n"
        f"📍 <code>{target_dir}</code>\n\n"
        + ("\n".join(f"• <code>{f}</code>" for f in files) if files else "<i>(папка пуста)</i>")
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_project_actions_keyboard(proj_name, is_active=(get_active_project(callback.from_user.id) == proj_name)),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("proj_git:"))
async def cb_proj_git(callback: CallbackQuery):
    """Run git status in project."""
    proj_name = callback.data.split(":", 1)[1]
    target_dir = PROJECTS_DIR / proj_name
    res = await run_terminal_command("git status", cwd=str(target_dir))
    formatted = format_command_output(f"git status ({proj_name})", res)
    await callback.message.answer(formatted, parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "prompt_new_project")
async def cb_prompt_new_project(callback: CallbackQuery, state: FSMContext):
    """Prompt user for new project name."""
    await state.set_state(NewProjectStates.waiting_for_name)
    await callback.message.edit_text(
        f"➕ <b>New Project в <code>{PROJECTS_DIR}</code></b>\n\n"
        "Отправь в ответном сообщении название проекта (например, <code>api-service</code> или <code>analyzer</code>):",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.message(NewProjectStates.waiting_for_name)
async def process_project_name(message: Message, state: FSMContext):
    """Handle project name input."""
    name = message.text.strip().replace(" ", "-")
    await state.clear()
    await message.answer(
        f"⚙️ Выбери шаблон для проекта <b>{name}</b>:\n\n"
        "💡 <i>Рекомендуем <b>🚀 FULL Antigravity</b> для полной интеграции в панель Antigravity!</i>",
        reply_markup=get_templates_keyboard(name),
        parse_mode="HTML",
    )


@dp.callback_query(F.data.startswith("scaffold:"))
async def cb_scaffold(callback: CallbackQuery):
    """Scaffold the chosen project template and set as active."""
    _, proj_name, template = callback.data.split(":")
    user = callback.from_user
    result = scaffold_project(proj_name, template)
    if result["success"]:
        set_active_project(user.id, proj_name)

        files_str = "\n".join(f"• <code>{f}</code>" for f in result["files"])
        text = (
            f"🎉 <b>Проект успешно создан и зарегистрирован!</b>\n\n"
            f"📁 <b>Имя:</b> <code>{result['name']}</code> 🎯 <i>(Сделан активным)</i>\n"
            f"📍 <b>Путь:</b> <code>{result['path']}</code>\n"
            f"📦 <b>Шаблон:</b> <code>{result['template']}</code>\n"
            f"🚀 <b>Antigravity GUI:</b> ✅ Зарегистрирован в панели Antigravity\n"
            f"🐙 <b>Git:</b> {'✅ Инициализирован' if result['git'] else '❌ Не инициализирован'}\n\n"
            f"<b>Созданные файлы:</b>\n{files_str}\n\n"
            "💬 <i>Теперь ты можешь сразу писать сообщения боту — они пойдут в этот проект!</i>"
        )
    else:
        text = f"❌ <b>Ошибка создания проекта:</b>\n{result.get('error')}"

    await callback.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    await callback.answer()


@dp.message(Command("new_project"))
async def cmd_new_project(message: Message):
    """Shortcut /new_project <name> [template]."""
    parts = message.text.split()
    if len(parts) == 1:
        await message.answer(
            f"➕ <b>New Project в <code>{PROJECTS_DIR}</code></b>\n\n"
            "Использование: <code>/new_project &lt;имя&gt; [шаблон]</code>\n"
            "Шаблоны: <code>antigravity</code> (рекомендуется), <code>python</code>, <code>fastapi</code>, <code>web</code>, <code>empty</code>\n\n"
            "Пример: <code>/new_project my-agent antigravity</code>",
            parse_mode="HTML",
        )
        return

    name = parts[1]
    template = parts[2] if len(parts) > 2 else "antigravity"
    result = scaffold_project(name, template)
    if result["success"]:
        set_active_project(message.from_user.id, name)
        await message.answer(
            f"🎉 <b>Проект <code>{result['name']}</code> создан и зарегистрирован в Antigravity!</b>\n"
            f"📍 Путь: <code>{result['path']}</code>\n"
            f"📦 Шаблон: <code>{result['template']}</code> 🎯 <i>(Активен)</i>",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML",
        )
    else:
        await message.answer(f"❌ <b>Ошибка:</b> {result.get('error')}", parse_mode="HTML")


@dp.message(Command("help"))
@dp.callback_query(F.data == "show_help")
async def show_help(event: Message | CallbackQuery):
    """Show detailed help manual."""
    help_text = (
        "<b>📖 РУКОВОДСТВО ORBITAL BRIDGE</b>\n\n"
        f"📁 <b>Рабочая папка:</b> <code>{PROJECTS_DIR}</code>\n\n"
        "🛰️ <b>Интерактивные кнопки и команды:</b>\n"
        "• <b>🔄 Refresh</b> (<code>/status</code>) — статус хоста, CPU, RAM, дисков, батареи\n"
        "• <b>⚡ Restart AG</b> (<code>/restart_ag</code>) — перезапуск Antigravity (AG.exe)\n"
        "• <b>📸 Screenshot</b> (<code>/screen</code>) — моментальный снимок экрана\n"
        "• <b>📁 Projects</b> (<code>/projects</code>) — список проектов и выбор активного\n"
        "• <b>➕ New Project</b> (<code>/new_project &lt;имя&gt;</code>) — генератор проектов с регистрацией в Antigravity\n"
        "• <b>💬 New conversation</b> (<code>/new_chat</code>) — сброс контекста и старт нового диалога с AI\n"
        "• <b>💻 /cmd &lt;команда&gt;</b> — запуск команд в активном проекте\n\n"
        "💡 <i>Диалог с AI:</i> выбери проект в <b>Projects</b>, и бот будет отвечать с учётом его кода и файлов!"
    )
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(help_text, reply_markup=get_back_keyboard(), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(help_text, reply_markup=get_main_keyboard(), parse_mode="HTML")


@dp.message(Command("chat"))
async def cmd_chat(message: Message):
    """Explicit AI chat command."""
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("🤖 Напиши запрос, например: <code>/chat как оптимизировать код?</code>", parse_mode="HTML")
        return
    prompt = parts[1]
    wait_msg = await message.answer("🤔 <i>Обдумываю ответ...</i>", parse_mode="HTML")
    reply = await ask_gemini(message.from_user.id, prompt)
    await wait_msg.edit_text(reply, parse_mode="HTML")


@dp.message()
async def default_ai_chat(message: Message):
    """Handle plain text messages as AI prompts with conversation and project context."""
    if not message.text:
        return
    wait_msg = await message.answer("🤖 <i>Думаю...</i>", parse_mode="HTML")
    reply = await ask_gemini(message.from_user.id, message.text)
    await wait_msg.edit_text(reply, parse_mode="HTML")


# ------------------- Watchdog Background Loop -------------------

async def watchdog_task(bot: Bot):
    """Background monitor for battery, network, and host status."""
    if not WATCHDOG_ENABLED or not ALLOWED_USER_IDS:
        logger.info("Watchdog disabled or no allowed users configured.")
        return

    import psutil
    last_net_state = True
    battery_warned = False

    logger.info("Watchdog started successfully.")

    while True:
        try:
            await asyncio.sleep(WATCHDOG_INTERVAL)

            # Check network
            net_ok, _ = await check_internet_latency()
            if not net_ok and last_net_state:
                last_net_state = False
                logger.warning("Internet lost!")
            elif net_ok and not last_net_state:
                last_net_state = True
                logger.info("Internet restored!")
                for uid in ALLOWED_USER_IDS:
                    try:
                        await bot.send_message(
                            uid,
                            "🌐 <b>Интернет на хосте восстановлен!</b>\nСвязь стабильна.",
                            parse_mode="HTML",
                        )
                    except Exception:
                        pass

            # Check battery
            battery = psutil.sensors_battery()
            if battery and not battery.power_plugged:
                if battery.percent <= BATTERY_ALERT_THRESHOLD and not battery_warned:
                    battery_warned = True
                    for uid in ALLOWED_USER_IDS:
                        try:
                            await bot.send_message(
                                uid,
                                f"⚠️ <b>Внимание: низкий заряд батареи!</b>\n"
                                f"🔋 Осталось: <b>{int(battery.percent)}%</b>\n"
                                f"Подключи зарядное устройство.",
                                parse_mode="HTML",
                            )
                        except Exception:
                            pass
            elif battery and battery.power_plugged:
                battery_warned = False

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Watchdog error: {e}")


# ------------------- Render Healthcheck HTTP Server -------------------

async def handle_web_health(request):
    """HTTP endpoint for Render free tier healthcheck."""
    return web.Response(
        text="<h1>⚡ Orbital Bridge is Online</h1><p>Telegram Bot is actively polling.</p>",
        content_type="text/html",
        status=200,
    )


# ------------------- Main Entrypoint -------------------

async def main():
    if not BOT_TOKEN:
        print("\n" + "=" * 60)
        print("❌ ОШИБКА: BOT_TOKEN не найден в .env!")
        print("=" * 60 + "\n")
        sys.exit(1)

    bot = Bot(token=BOT_TOKEN)

    try:
        await bot.set_my_commands([
            BotCommand(command="status", description="📊 Refresh / Системный статус"),
            BotCommand(command="restart_ag", description="⚡ Restart AG / Перезапуск Antigravity"),
            BotCommand(command="screen", description="📸 Screenshot / Снимок экрана"),
            BotCommand(command="new_chat", description="💬 New conversation / Сброс контекста"),
            BotCommand(command="projects", description="📁 Projects / Список и выбор активного"),
            BotCommand(command="new_project", description="➕ New Project / Создать FULL Antigravity"),
            BotCommand(command="cmd", description="💻 Terminal / Консоль в активном проекте"),
            BotCommand(command="help", description="❓ Help / Справка"),
        ])
    except Exception as e:
        logger.warning(f"Could not register bot commands: {e}")

    # Launch Render HTTP health server if PORT is provided or on Render
    port_str = os.getenv("PORT")
    web_runner = None
    if port_str:
        try:
            port = int(port_str)
            app = web.Application()
            app.router.add_get("/", handle_web_health)
            app.router.add_get("/health", handle_web_health)
            web_runner = web.AppRunner(app)
            await web_runner.setup()
            site = web.TCPSite(web_runner, "0.0.0.0", port)
            await site.start()
            logger.info(f"Render HTTP health server started on port {port}")
        except Exception as e:
            logger.warning(f"Could not start HTTP health server on port {port_str}: {e}")

    watchdog_bg = asyncio.create_task(watchdog_task(bot))

    logger.info("Orbital Bridge is running. Listening for Telegram updates...")

    try:
        await dp.start_polling(bot)
    finally:
        watchdog_bg.cancel()
        if web_runner:
            await web_runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
