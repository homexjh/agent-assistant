"""exec 工具：执行 shell 命令，是 Agent 操作计算机的核心"""
from __future__ import annotations
import subprocess
from .types import RegisteredTool, ToolDefinition


async def _exec_handler(
    command: str,
    cwd: str | None = None,
    timeout: int = 30,
) -> str:
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            timeout=timeout,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {timeout}s\ncommand: {command}"
    except Exception as e:
        return f"Error spawning process: {e}"

    parts: list[str] = []
    if result.stdout:
        parts.append(f"stdout:\n{result.stdout.rstrip()}")
    if result.stderr:
        parts.append(f"stderr:\n{result.stderr.rstrip()}")
    parts.append(f"exit_code: {result.returncode}")

    return "\n\n".join(parts)


exec_tool = RegisteredTool(
    definition=ToolDefinition(
        type="function",
        function={
            "name": "exec",
            "description": (
                "Execute a shell command on the local system. "
                "Use this to run programs, scripts, manage files via CLI, "
                "install packages, etc. Returns stdout, stderr, and exit code."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute.",
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Optional working directory. Defaults to current directory.",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Optional timeout in seconds. Defaults to 30.",
                    },
                },
                "required": ["command"],
            },
        },
    ),
    handler=_exec_handler,  # type: ignore[arg-type]
)
