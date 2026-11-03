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


def get_projects_keyboard(projects: list[dict]) -> InlineKeyboardMarkup:
    """Keyboard listing available projects with action buttons."""
    buttons = []
    # Up to 8 projects
    for p in projects[:8]:
        git_badge = " 🐙" if p.get("git") else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"📂 {p['name']}{git_badge} ({p['modified']})",
                callback_data=f"proj_info:{p['name']}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(text="➕ New Project", callback_data="prompt_new_project"),
        InlineKeyboardButton(text="🔙 Back", callback_data="back_to_menu"),
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
