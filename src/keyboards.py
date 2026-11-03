from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_keyboard() -> InlineKeyboardMarkup:
    """Generate main interactive inline keyboard with AG control."""
    buttons = [
        [
            InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh_status"),
            InlineKeyboardButton(text="📸 Screenshot", callback_data="take_screenshot"),
        ],
        [
            InlineKeyboardButton(text="📁 Projects", callback_data="list_projects"),
            InlineKeyboardButton(text="➕ New Project", callback_data="prompt_new_project"),
        ],
        [
            InlineKeyboardButton(text="⚡ Restart AG (Admin)", callback_data="restart_ag"),
            InlineKeyboardButton(text="💬 New conversation", callback_data="new_conversation"),
        ],
        [
            InlineKeyboardButton(text="❓ Help", callback_data="show_help"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_projects_keyboard(projects: list[dict], active_proj: str | None = None) -> InlineKeyboardMarkup:
    """Keyboard listing available projects with action buttons and active mark."""
    buttons = []
    for p in projects[:10]:
        name = p["name"]
        badge = " 🎯 [Активен]" if name == active_proj else (" 🚀 [AG]" if p.get("antigravity") else "")
        buttons.append([
            InlineKeyboardButton(
                text=f"📂 {name}{badge} ({p['modified']})",
                callback_data=f"proj_info:{name}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(text="➕ New Project", callback_data="prompt_new_project"),
        InlineKeyboardButton(text="🔙 Back", callback_data="back_to_menu"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_project_actions_keyboard(project_name: str, is_active: bool = False) -> InlineKeyboardMarkup:
    """Action buttons for an inspected project."""
    active_btn_text = "✅ Проект уже активен" if is_active else "🎯 Сделать активным проектом"
    buttons = [
        [
            InlineKeyboardButton(text=active_btn_text, callback_data=f"set_active:{project_name}"),
        ],
        [
            InlineKeyboardButton(text="📄 Список файлов", callback_data=f"proj_files:{project_name}"),
            InlineKeyboardButton(text="💻 Запустить git status", callback_data=f"proj_git:{project_name}"),
        ],
        [
            InlineKeyboardButton(text="🔙 К проектам", callback_data="list_projects"),
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_templates_keyboard(project_name: str) -> InlineKeyboardMarkup:
    """Template selection for a new project including FULL Antigravity."""
    buttons = [
        [
            InlineKeyboardButton(text="🚀 FULL Antigravity", callback_data=f"scaffold:{project_name}:antigravity"),
        ],
        [
            InlineKeyboardButton(text="🐍 Python App", callback_data=f"scaffold:{project_name}:python"),
            InlineKeyboardButton(text="⚡ FastAPI Service", callback_data=f"scaffold:{project_name}:fastapi"),
        ],
        [
            InlineKeyboardButton(text="🌐 Web (HTML/JS)", callback_data=f"scaffold:{project_name}:web"),
            InlineKeyboardButton(text="📁 Clean Git Repo", callback_data=f"scaffold:{project_name}:empty"),
        ],
        [
            InlineKeyboardButton(text="❌ Cancel", callback_data="back_to_menu"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Simple back button keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Back to Dashboard", callback_data="back_to_menu")]]
    )
