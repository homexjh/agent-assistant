"""read / write / edit / apply_patch 文件工具"""
from __future__ import annotations
import os
import re
from .types import RegisteredTool, ToolDefinition


async def _read_handler(
    path: str,
    offset: int | None = None,
    limit: int | None = None,
) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return f'Error reading file "{path}": {e}'

    if offset is not None or limit is not None:
        lines = content.splitlines(keepends=True)
        start = max(0, (offset or 1) - 1)
        end = start + limit if limit is not None else len(lines)
        content = "".join(lines[start:end])

    return content


read_tool = RegisteredTool(
    definition=ToolDefinition(
        type="function",
        function={
            "name": "read",
            "description": (
                "Read the contents of a file. "
                "Returns the file content as a string. "
                "Optionally specify offset (1-based line number) and limit (number of lines)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute or relative path of the file to read.",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Line number to start reading from (1-based, optional).",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of lines to read (optional).",
                    },
                },
                "required": ["path"],
            },
        },
    ),
    handler=_read_handler,  # type: ignore[arg-type]
)


async def _write_handler(path: str, content: str) -> str:
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f'Successfully wrote {len(content)} characters to "{path}".'
    except Exception as e:
        return f'Error writing file "{path}": {e}'


write_tool = RegisteredTool(
    definition=ToolDefinition(
        type="function",
        function={
            "name": "write",
            "description": (
                "Write content to a file. "
                "Creates the file and any missing parent directories if they don't exist. "
                "Overwrites existing content."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute or relative path of the file to write.",
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write into the file.",
                    },
                },
                "required": ["path", "content"],
            },
        },
    ),
    handler=_write_handler,  # type: ignore[arg-type]
)


# ── edit ──────────────────────────────────────────────────

import shutil
from pathlib import Path
from datetime import datetime


def _is_python_file(path: str) -> bool:
    """检查是否为 Python 文件"""
    return path.endswith('.py')


def _validate_python_syntax(content: str, filename: str) -> tuple[bool, str]:
    """验证 Python 语法，返回 (是否合法, 错误信息)"""
    try:
        compile(content, filename, 'exec')
        return True, ""
    except SyntaxError as e:
        return False, f"语法错误 (行{e.lineno}): {e.msg}"


def _format_with_black(path: str) -> bool:
    """使用 black 格式化文件，返回是否成功"""
    try:
        result = shutil.which('black')
        if not result:
            return False
        import subprocess
        subprocess.run(['black', '-q', path], capture_output=True, timeout=10)
        return True
    except:
        return False


async def _edit_handler(path: str, old_str: str, new_str: str) -> str:
    """
    增强版 edit 工具：安全编辑，自动备份，语法检查，自动格式化。
    
    功能：
    1. 编辑前自动创建备份 (.aiagent/backups/)
    2. Python 文件自动语法验证（编辑前检查）
    3. Python 文件自动格式化（black）
    """
    # 1. 读取原文件
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return f'❌ Error reading file "{path}": {e}'

    # 2. 检查 old_str 唯一性
    count = content.count(old_str)
    if count == 0:
        return f'❌ Error: old_str not found in "{path}".'
    if count > 1:
        return (
            f'❌ Error: old_str appears {count} times in "{path}". '
            "Provide more context to make it unique."
        )

    # 3. 生成新内容
    new_content = content.replace(old_str, new_str, 1)
    
    # 4. Python 语法检查（关键！）
    if _is_python_file(path):
        is_valid, error_msg = _validate_python_syntax(new_content, path)
        if not is_valid:
            return f'❌ 编辑被拒绝：会导致语法错误\n   {error_msg}\n   请检查 new_str 中的缩进和语法。'
    
    # 5. 创建备份
    backup_path = None
    try:
        backup_dir = Path(".aiagent/backups")
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"{Path(path).name}.{timestamp}.bak"
        shutil.copy2(path, backup_path)
    except Exception as e:
        # 备份失败不阻止编辑，但记录警告
        backup_path = None
    
    # 6. 写入文件
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
    except Exception as e:
        return f'❌ Error writing file "{path}": {e}'
    
    # 7. 自动格式化（Python）
    formatted = False
    if _is_python_file(path):
        formatted = _format_with_black(path)
    
    # 8. 构建成功消息
    messages = [f'✅ Successfully edited "{path}".']
    if backup_path:
        messages.append(f'💾 Backup: {backup_path}')
    if _is_python_file(path):
        messages.append('✅ Python syntax validated.')
        if formatted:
            messages.append('🎨 Auto-formatted with black.')
        else:
            messages.append('💡 Install black for auto-formatting: uv add --dev black')
    
    return '\n'.join(messages)


edit_tool = RegisteredTool(
    definition=ToolDefinition(
        type="function",
        function={
            "name": "edit",
            "description": (
                "Precisely replace a unique string in a file with new content. "
                "old_str must appear exactly once in the file. "
                "SAFETY FEATURES: (1) Auto-backup to .aiagent/backups/ "
                "(2) Python syntax validation before save "
                "(3) Auto-format with black (if installed). "
                "Use this for targeted edits instead of rewriting the whole file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path of the file to edit.",
                    },
                    "old_str": {
                        "type": "string",
                        "description": "The exact string to find (must be unique in the file). Include enough context (indentation, surrounding lines) to make it unique.",
                    },
                    "new_str": {
                        "type": "string",
                        "description": "The replacement string. For Python files, ensure proper indentation and syntax.",
                    },
                },
                "required": ["path", "old_str", "new_str"],
            },
        },
    ),
    handler=_edit_handler,  # type: ignore[arg-type]
)


# ── restore ───────────────────────────────────────────────

async def _restore_handler(backup_path: str, target_path: str = "") -> str:
    """从备份文件恢复原始文件"""
    try:
        backup_file = Path(backup_path)
        if not backup_file.exists():
            # 尝试在备份目录中查找
            if not backup_path.startswith("/"):
                backup_file = Path(".aiagent/backups") / backup_path
            if not backup_file.exists():
                return f'❌ Backup file not found: {backup_path}'
        
        # 确定目标路径
        if target_path:
            restore_to = Path(target_path)
        else:
            # 从备份文件名解析：filename.timestamp.bak -> filename
            name = backup_file.name
            if "." in name:
                # 去掉 .timestamp.bak 后缀
                parts = name.split(".")
                if len(parts) >= 3 and parts[-1] == "bak":
                    restore_to = Path(".").joinpath(*parts[:-2])
                else:
                    restore_to = Path(name)
            else:
                restore_to = Path(name)
        
        # 再次确认（避免覆盖错误）
        if restore_to.exists():
            # 创建当前文件的备份
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            current_backup = Path(".aiagent/backups") / f"{restore_to.name}.{timestamp}.auto.bak"
            shutil.copy2(restore_to, current_backup)
        
        # 恢复文件
        shutil.copy2(backup_file, restore_to)
        
        return f'✅ Successfully restored "{backup_file.name}" to "{restore_to}"'
        
    except Exception as e:
        return f'❌ Error restoring file: {e}'


restore_tool = RegisteredTool(
    definition=ToolDefinition(
        type="function",
        function={
            "name": "restore",
            "description": (
                "Restore a file from its backup. "
                "Backups are automatically created by the 'edit' tool and stored in .aiagent/backups/. "
                "Use this to undo changes made by edit or apply_patch."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "backup_path": {
                        "type": "string",
                        "description": "Path to the backup file (e.g., '.aiagent/backups/file.py.20240315_120000.bak' or just 'file.py.20240315_120000.bak')",
                    },
                    "target_path": {
                        "type": "string",
                        "description": "Optional: where to restore the file. If not specified, restores to the original location.",
                    },
                },
                "required": ["backup_path"],
            },
        },
    ),
    handler=_restore_handler,  # type: ignore[arg-type]
)


# ── apply_patch ───────────────────────────────────────────

def _apply_unified_patch(original: str, patch: str) -> str:
    """
    应用简化版 unified diff patch。
    支持格式：
      --- a/file
      +++ b/file
      @@ ... @@
       context
      -removed line
      +added line
    """
    lines = original.splitlines(keepends=True)
    result: list[str] = list(lines)
    offset = 0  # 已应用 patch 导致的行偏移

    hunk_re = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

    patch_lines = patch.splitlines(keepends=True)
    i = 0
    while i < len(patch_lines):
        line = patch_lines[i]
        m = hunk_re.match(line)
        if m:
            src_start = int(m.group(1)) - 1  # 转 0-based
            i += 1
            removes: list[tuple[int, str]] = []
            adds: list[str] = []
            ctx_pos = src_start

            while i < len(patch_lines) and not hunk_re.match(patch_lines[i]):
                pl = patch_lines[i]
                if pl.startswith("-"):
                    removes.append((ctx_pos + offset, pl[1:]))
                    ctx_pos += 1
                elif pl.startswith("+"):
                    adds.append(pl[1:])
                else:
                    ctx_pos += 1
                i += 1

            # 从后往前删，防止下标乱掉
            del_indices = sorted({r[0] for r in removes}, reverse=True)
            for idx in del_indices:
                if 0 <= idx < len(result):
                    del result[idx]
                    offset -= 1

            ins_pos = src_start + offset
            for add_line in reversed(adds):
                result.insert(ins_pos, add_line)
                offset += 1
        else:
            i += 1

    return "".join(result)


async def _apply_patch_handler(path: str, patch: str) -> str:
    """应用 unified diff patch 到文件。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            original = f.read()
    except Exception as e:
        return f'Error reading file "{path}": {e}'

    try:
        patched = _apply_unified_patch(original, patch)
    except Exception as e:
        return f"Error applying patch: {e}"

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(patched)
    except Exception as e:
        return f'Error writing file "{path}": {e}'

    return f'Successfully applied patch to "{path}".'


apply_patch_tool = RegisteredTool(
    definition=ToolDefinition(
        type="function",
        function={
            "name": "apply_patch",
            "description": (
                "Apply a unified diff patch to a file. "
                "Use standard unified diff format (--- +++ @@ lines). "
                "Useful for making multiple structured changes at once."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path of the file to patch.",
                    },
                    "patch": {
                        "type": "string",
                        "description": "Unified diff patch string.",
                    },
                },
                "required": ["path", "patch"],
            },
        },
    ),
    handler=_apply_patch_handler,  # type: ignore[arg-type]
)
