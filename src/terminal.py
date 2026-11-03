import asyncio
import time
import os


async def run_terminal_command(command: str, timeout: int = 60, cwd: str | None = None) -> dict:
    """
    Execute a shell command locally on the laptop.
    Returns:
        dict: {
            "success": bool,
            "exit_code": int,
            "stdout": str,
            "stderr": str,
            "elapsed": float,
            "timed_out": bool
        }
    """
    t0 = time.perf_counter()
    timed_out = False

    # On Windows, use PowerShell
    if os.name == "nt":
        shell_cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command]
    else:
        shell_cmd = ["/bin/bash", "-c", command]

    try:
        process = await asyncio.create_subprocess_exec(
            *shell_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )

        try:
            stdout_data, stderr_data = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            exit_code = process.returncode or 0
        except asyncio.TimeoutError:
            process.kill()
            timed_out = True
            stdout_data, stderr_data = await process.communicate()
            exit_code = -1

        elapsed = round(time.perf_counter() - t0, 2)

        # Decode with fallback for Windows encodings (utf-8, cp1251, cp866)
        def safe_decode(b: bytes) -> str:
            for enc in ("utf-8", "cp1251", "cp866", "latin-1"):
                try:
                    return b.decode(enc)
                except UnicodeDecodeError:
                    continue
            return b.decode("utf-8", errors="replace")

        stdout_str = safe_decode(stdout_data).strip()
        stderr_str = safe_decode(stderr_data).strip()

        return {
            "success": (exit_code == 0) and not timed_out,
            "exit_code": exit_code,
            "stdout": stdout_str,
            "stderr": stderr_str,
            "elapsed": elapsed,
            "timed_out": timed_out,
        }

    except Exception as e:
        elapsed = round(time.perf_counter() - t0, 2)
        return {
            "success": False,
            "exit_code": 1,
            "stdout": "",
            "stderr": f"System error executing command: {str(e)}",
            "elapsed": elapsed,
            "timed_out": False,
        }


def format_command_output(command: str, result: dict) -> str:
    """Format command execution result for a clean Telegram message."""
    status_icon = "🟢" if result["success"] else "🔴"
    status_text = "УСПЕШНО" if result["success"] else "ОШИБКА"
    if result.get("timed_out"):
        status_text = "ТАЙМАУТ (>60с)"

    header = (
        f"{status_icon} <b>Команда:</b> <code>{command}</code>\n"
        f"⏱ <b>Время:</b> {result['elapsed']}s | <b>Код:</b> <code>{result['exit_code']}</code>\n"
        f"<b>Статус:</b> {status_text}\n\n"
    )

    body = ""
    if result["stdout"]:
        out = result["stdout"]
        if len(out) > 2500:
            out = out[:2500] + "\n... [вывод обрезан из-за лимита TG]"
        body += f"<b>Вывод (stdout):</b>\n<pre>{out}</pre>\n"

    if result["stderr"]:
        err = result["stderr"]
        if len(err) > 1000:
            err = err[:1000] + "\n... [ошибка обрезана]"
        body += f"<b>Ошибки (stderr):</b>\n<pre>{err}</pre>\n"

    if not body:
        body = "<i>(Команда завершилась без текстового вывода)</i>"

    return header + body
