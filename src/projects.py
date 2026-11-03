import os
import json
import uuid
import subprocess
import datetime
from pathlib import Path
from src.config import PROJECTS_DIR

# Global Antigravity config directory where projects are registered
ANTIGRAVITY_PROJECTS_DIR = Path(r"C:\Users\Che\.gemini\config\projects")

# Active project per user: {user_id: project_name}
active_user_projects: dict[int, str] = {}


def get_active_project(user_id: int) -> str | None:
    return active_user_projects.get(user_id)


def set_active_project(user_id: int, project_name: str) -> bool:
    target = PROJECTS_DIR / project_name
    if target.exists() and target.is_dir():
        active_user_projects[user_id] = project_name
        return True
    return False


def register_in_antigravity(project_name: str, project_dir: Path) -> str:
    """
    Register project in Antigravity GUI so it appears in the left sidebar under 'Projects'.
    Returns the project UUID.
    """
    ANTIGRAVITY_PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

    # Check if already registered
    norm_path = str(project_dir).replace("\\", "/").lower()
    for f in ANTIGRAVITY_PROJECTS_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            for res in data.get("projectResources", {}).get("resources", []):
                uri = res.get("folderUri", "").lower()
                if project_name.lower() in uri:
                    return data.get("id", str(uuid.uuid4()))
        except Exception:
            continue

    # Create new registration
    proj_id = str(uuid.uuid4())
    # Format URI like file:///d%3A/Orbital%20Bridge/project_name
    drive = project_dir.drive.replace(":", "%3A").lower()
    rel_path = str(project_dir)[len(project_dir.drive):].replace("\\", "/").strip("/")
    folder_uri = f"file:///{drive}/{rel_path.replace(' ', '%20')}"

    config_data = {
        "id": proj_id,
        "name": project_name,
        "projectResources": {
            "resources": [
                {
                    "folderUri": folder_uri
                }
            ]
        },
        "permissionGrants": {
            "v2Migrated": True
        },
        "settings": {},
        "isWorkspaceOnly": False,
    }

    config_file = ANTIGRAVITY_PROJECTS_DIR / f"{proj_id}.json"
    config_file.write_text(json.dumps(config_data, indent=2, ensure_ascii=False), encoding="utf-8")
    return proj_id


def list_projects() -> list[dict]:
    """List existing projects in PROJECTS_DIR."""
    if not PROJECTS_DIR.exists():
        return []

    projects = []
    for item in PROJECTS_DIR.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            try:
                mtime = item.stat().st_mtime
                mod_date = datetime.datetime.fromtimestamp(mtime).strftime("%d.%m %H:%M")
                has_git = (item / ".git").exists()
                has_gemini = (item / ".gemini").exists() or (item / "GEMINI.md").exists()
                projects.append({
                    "name": item.name,
                    "path": str(item),
                    "modified": mod_date,
                    "git": has_git,
                    "antigravity": has_gemini,
                })
            except Exception:
                continue

    projects.sort(key=lambda x: x["name"].lower())
    return projects


def scaffold_project(name: str, template: str = "antigravity") -> dict:
    """
    Create a new project folder with starter files, git init, and Antigravity registration.
    Supported templates: antigravity, python, fastapi, web, empty.
    """
    safe_name = "".join(c for c in name if c.isalnum() or c in ("-", "_")).strip()
    if not safe_name:
        return {"success": False, "error": "Некорректное имя проекта"}

    target_dir = PROJECTS_DIR / safe_name
    if target_dir.exists():
        # If exists, register it in Antigravity anyway
        proj_id = register_in_antigravity(safe_name, target_dir)
        return {
            "success": True,
            "name": safe_name,
            "path": str(target_dir),
            "template": template,
            "files": [f.name for f in target_dir.iterdir()][:10],
            "git": (target_dir / ".git").exists(),
            "antigravity_id": proj_id,
        }

    target_dir.mkdir(parents=True, exist_ok=True)
    template = template.lower()
    created_files = []

    # Common .gitignore
    gitignore_content = """# Environment & dependencies
.venv/
env/
__pycache__/
*.py[cod]
.env
.env.local

# Node
node_modules/
dist/

# OS & IDE
.DS_Store
Thumbs.db
.idea/
.vscode/
"""
    (target_dir / ".gitignore").write_text(gitignore_content, encoding="utf-8")
    created_files.append(".gitignore")

    if template in ("antigravity", "full antigravity"):
        # Create .gemini configuration directory
        gemini_dir = target_dir / ".gemini"
        rules_dir = gemini_dir / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)

        gemini_md = f"""# {safe_name} (Antigravity Project)

## Project Overview
This project is configured for **Google Antigravity** autonomous agent development.

## Architecture
- Created via Orbital Bridge at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Workspace directory: `{target_dir}`

## Guidelines
- Write clean, modular, documented code.
- Maintain test coverage for core components.
"""
        (target_dir / "GEMINI.md").write_text(gemini_md, encoding="utf-8")
        created_files.append("GEMINI.md")

        coding_rules = """# Code Style & Rules
- Language: Python 3.11+ / TypeScript
- Format code using Black or Prettier
- Provide clear error handling and logs
"""
        (rules_dir / "coding-style.md").write_text(coding_rules, encoding="utf-8")
        created_files.append(".gemini/rules/coding-style.md")

        main_py = f'''"""
{safe_name} - Antigravity entry point
"""

def main():
    print("🚀 {safe_name} is running inside Antigravity workspace!")

if __name__ == "__main__":
    main()
'''
        (target_dir / "main.py").write_text(main_py, encoding="utf-8")
        created_files.append("main.py")

        readme = f"""# {safe_name}

> Google Antigravity Full Workspace Project

### Quickstart
```bash
python main.py
```
"""
        (target_dir / "README.md").write_text(readme, encoding="utf-8")
        created_files.append("README.md")

    elif template == "fastapi":
        main_py = f'''from fastapi import FastAPI

app = FastAPI(title="{safe_name}", version="1.0.0")

@app.get("/")
def read_root():
    return {{"status": "ok", "project": "{safe_name}"}}

@app.get("/health")
def health():
    return {{"alive": True}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
'''
        reqs = "fastapi>=0.115.0\nuvicorn[standard]>=0.30.0\npydantic>=2.0\n"
        (target_dir / "main.py").write_text(main_py, encoding="utf-8")
        (target_dir / "requirements.txt").write_text(reqs, encoding="utf-8")
        (target_dir / "README.md").write_text(f"# {safe_name}\n\nFastAPI Application.\n", encoding="utf-8")
        created_files.extend(["main.py", "requirements.txt", "README.md"])

    elif template == "web":
        html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{safe_name}</title>
</head>
<body style="font-family: sans-serif; padding: 40px; text-align: center; background: #0d1117; color: #fff;">
  <h1>🚀 {safe_name}</h1>
  <p>Web application generated by Orbital Bridge</p>
</body>
</html>
"""
        (target_dir / "index.html").write_text(html, encoding="utf-8")
        (target_dir / "README.md").write_text(f"# {safe_name}\n\nWeb application.\n", encoding="utf-8")
        created_files.extend(["index.html", "README.md"])

    else:
        # Default python
        main_py = f'''"""
{safe_name} - Main script
"""

def main():
    print("🚀 Hello from {safe_name}!")

if __name__ == "__main__":
    main()
'''
        (target_dir / "main.py").write_text(main_py, encoding="utf-8")
        (target_dir / "README.md").write_text(f"# {safe_name}\n\nPython project.\n", encoding="utf-8")
        created_files.extend(["main.py", "README.md"])

    # Git Init
    git_initialized = False
    try:
        subprocess.run(["git", "init"], cwd=str(target_dir), capture_output=True, check=True)
        subprocess.run(["git", "add", "."], cwd=str(target_dir), capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"Initial commit for {safe_name}"],
            cwd=str(target_dir),
            capture_output=True,
            check=True,
        )
        git_initialized = True
    except Exception:
        git_initialized = False

    # Register in Antigravity GUI!
    antigravity_id = register_in_antigravity(safe_name, target_dir)

    return {
        "success": True,
        "name": safe_name,
        "path": str(target_dir),
        "template": template,
        "files": created_files,
        "git": git_initialized,
        "antigravity_id": antigravity_id,
    }
