import asyncio
import os
import subprocess
import time
from pathlib import Path
import psutil

AG_PATH = Path(r"D:\Orbital Bridge\AG.exe")


def get_ag_status() -> dict:
    """
    Check if AG.exe is running on the system.
    Returns:
        dict: {"running": bool, "pid": int | None, "memory_mb": float, "cpu": float}
    """
    for proc in psutil.process_iter(["pid", "name", "memory_info", "cpu_percent"]):
        try:
            if proc.info["name"] and proc.info["name"].lower() in ("ag.exe", "ag"):
                mem = (proc.info["memory_info"].rss / (1024 * 1024)) if proc.info["memory_info"] else 0.0
                cpu = proc.info.get("cpu_percent") or 0.0
                return {
                    "running": True,
                    "pid": proc.info["pid"],
                    "memory_mb": round(mem, 1),
                    "cpu": round(cpu, 1),
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return {"running": False, "pid": None, "memory_mb": 0.0, "cpu": 0.0}


async def restart_ag_process(as_admin: bool = True) -> dict:
    """
    Forcefully kill any running AG.exe and restart it (elevated / as admin).
    Returns:
        dict: {"success": bool, "pid": int | None, "message": str}
    """
    if not AG_PATH.exists():
        return {
            "success": False,
            "pid": None,
            "message": f"Файл {AG_PATH} не найден на диске D:!",
        }

    # 1. Kill any existing instances of AG.exe
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", "AG.exe", "/T"],
            capture_output=True,
            check=False,
        )
    except Exception:
        pass

    await asyncio.sleep(0.5)

    # 2. Launch AG.exe
    working_dir = str(AG_PATH.parent)
    exe_path = str(AG_PATH)

    # Use PowerShell Start-Process with -Verb RunAs for administrator privileges
    verb_param = "-Verb RunAs" if as_admin else ""
    ps_command = f'Start-Process -FilePath "{exe_path}" -WorkingDirectory "{working_dir}" {verb_param}'

    try:
        proc = await asyncio.create_subprocess_exec(
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            ps_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr_data = await proc.communicate()
    except Exception as e:
        return {
            "success": False,
            "pid": None,
            "message": f"Ошибка запуска через PowerShell: {e}",
        }

    # 3. Wait 2 seconds and verify if AG.exe is alive
    await asyncio.sleep(2.0)
    status = get_ag_status()

    if status["running"]:
        return {
            "success": True,
            "pid": status["pid"],
            "memory_mb": status["memory_mb"],
            "message": f"AG.exe успешно запущен от имени администратора! (PID: {status['pid']}, RAM: {status['memory_mb']} MB)",
        }
    else:
        err_msg = stderr_data.decode("utf-8", errors="replace").strip() if stderr_data else ""
        return {
            "success": False,
            "pid": None,
            "message": f"Процесс был отправлен на запуск, но не обнаружен в списке процессов. {err_msg}".strip(),
        }
