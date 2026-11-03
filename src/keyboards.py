from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_keyboard() -> InlineKeyboardMarkup:
    """Generate main interactive inline keyboard."""
    buttons = [
        [
            InlineKeyboardButton(text="🔄 Обновить статус", callback_data="refresh_status"),
            InlineKeyboardButton(text="📸 Скриншот", callback_data="take_screenshot"),
        ],
        [
            InlineKeyboardButton(text="📁 Мои проекты", callback_data="list_projects"),
            InlineKeyboardButton(text="➕ Новый проект", callback_data="prompt_new_project"),
        ],
        [
            InlineKeyboardButton(text="❓ Справка", callback_data="show_help"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_projects_keyboard(projects: list[dict]) -> InlineKeyboardMarkup:
    """Keyboard listing available projects with action buttons."""
    buttons = []
    # Up to 6 recent projects
    for p in projects[:6]:
        git_badge = " [git]" if p.get("git") else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"📂 {p['name']}{git_badge} ({p['modified']})",
                callback_data=f"proj_info:{p['name']}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(text="➕ Создать проект", callback_data="prompt_new_project"),
        InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_menu"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_templates_keyboard(project_name: str) -> InlineKeyboardMarkup:
    """Template selection for a new project."""
    buttons = [
        [
            InlineKeyboardButton(text="🐍 Python App", callback_data=f"scaffold:{project_name}:python"),
            InlineKeyboardButton(text="⚡ FastAPI Service", callback_data=f"scaffold:{project_name}:fastapi"),
        ],
        [
            InlineKeyboardButton(text="🌐 Web (HTML/JS)", callback_data=f"scaffold:{project_name}:web"),
            InlineKeyboardButton(text="📁 Чистый Git репо", callback_data=f"scaffold:{project_name}:empty"),
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_menu"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Simple back button keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]]
    )
