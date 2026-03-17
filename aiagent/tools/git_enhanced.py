"""
Enhanced Git Tools - Level 3 Optimization
Provides semantic commit, safety checks, and intelligent git operations.
"""

import asyncio
from pathlib import Path

from aiagent.git_utils import (
    is_git_repo,
    get_status,
    get_diff_summary,
    suggest_commit_message,
    check_large_files,
    check_sensitive_patterns,
    get_recent_commits,
    compare_versions,
    create_backup_branch,
    run_git,
    get_staged_diff_content,
)


async def _smart_commit_handler(message: str = "", auto_stage: bool = False, dry_run: bool = False) -> str:
    """
    Smart commit with automatic message generation.
    
    Args:
        message: Custom commit message (if empty, auto-generate)
        auto_stage: Whether to stage all changes automatically
        dry_run: If True, only show what would be committed without doing it
    """
    if not is_git_repo():
        return "❌ Error: Not in a git repository"
    
    status = get_status()
    
    if not status.get("has_changes", False):
        return "📭 No changes to commit"
    
    # Auto-stage if requested
    if auto_stage:
        has_unstaged = bool(status.get("unstaged") or status.get("untracked"))
        if has_unstaged:
            if dry_run:
                return "📝 Would stage all changes and commit\n" + await _format_status()
            
            code, _, stderr = run_git(["add", "-A"])
            if code != 0:
                return f"❌ Failed to stage changes: {stderr}"
            status = get_status()  # Refresh status
    
    # Check if there's anything staged
    if not status.get("staged"):
        return "⚠️ No staged changes. Use auto_stage=True to stage all changes."
    
    # Generate or use provided message
    if not message:
        suggestion = suggest_commit_message()
        if "error" in suggestion:
            return f"❌ {suggestion['error']}"
        message = suggestion["message"]
        
        # Show suggestion and stats
        stats = suggestion["stats"]
        preview = f"""🤖 Suggested commit message:

  {message}

📊 Changes:
  Files: {stats['file_count']}
  Additions: +{stats['total_additions']}
  Deletions: -{stats['total_deletions']}

💡 Use this command with dry_run=False and message="{message}" to commit
"""
        return preview
    
    # Dry run mode
    if dry_run:
        diff_summary = get_diff_summary(staged=True)
        return f"""📝 Would commit with message:

  {message}

📊 Staged changes:
  Files: {diff_summary.get('file_count', 0)}
  Additions: +{diff_summary.get('total_additions', 0)}
  Deletions: -{diff_summary.get('total_deletions', 0)}

Use dry_run=False to actually commit
"""
    
    # Perform commit
    code, stdout, stderr = run_git(["commit", "-m", message])
    if code != 0:
        return f"❌ Commit failed: {stderr}"
    
    return f"✅ Committed successfully:\n  {message}"


async def _safe_commit_handler(message: str = "", auto_stage: bool = True, skip_checks: bool = False) -> str:
    """
    Safe commit with pre-commit checks.
    
    Performs safety checks before committing:
    - Large files detection
    - Sensitive pattern detection
    - Automatic message generation if not provided
    
    Args:
        message: Commit message (auto-generated if empty)
        auto_stage: Stage all changes before commit
        skip_checks: Skip safety checks (not recommended)
    """
    if not is_git_repo():
        return "❌ Error: Not in a git repository"
    
    status = get_status()
    
    if not status.get("has_changes", False):
        return "📭 No changes to commit"
    
    # Auto-stage
    if auto_stage:
        has_unstaged = bool(status.get("unstaged") or status.get("untracked"))
        if has_unstaged:
            code, _, stderr = run_git(["add", "-A"])
            if code != 0:
                return f"❌ Failed to stage changes: {stderr}"
    
    # Run safety checks
    warnings = []
    
    if not skip_checks:
        # Check for large files
        large_files = check_large_files(max_size_mb=10.0)
        for f in large_files:
            warnings.append(f"⚠️ Large file detected ({f['size_mb']}MB): {f['path']}")
        
        # Check for sensitive patterns
        sensitive = check_sensitive_patterns()
        for s in sensitive:
            warnings.append(f"🔒 Potential {s['type']} in: {s['context']}")
    
    # Generate commit message if not provided
    if not message:
        suggestion = suggest_commit_message()
        if "error" not in suggestion:
            message = suggestion["message"]
        else:
            message = "chore: update files"
    
    # Build result
    result_lines = []
    
    if warnings:
        result_lines.append("🛡️ Safety Check Warnings:")
        for w in warnings:
            result_lines.append(f"  {w}")
        result_lines.append("")
    
    result_lines.append(f"📝 Commit message: {message}")
    
    # Show diff summary
    diff_summary = get_diff_summary(staged=True)
    if diff_summary.get("file_count", 0) > 0:
        result_lines.append(f"\n📊 Changes to commit:")
        result_lines.append(f"  Files: {diff_summary['file_count']}")
        result_lines.append(f"  +{diff_summary['total_additions']} / -{diff_summary['total_deletions']}")
        
        result_lines.append(f"\n📁 Files:")
        for f in diff_summary["files"][:10]:  # Show first 10
            result_lines.append(f"  {f['path']} (+{f['additions']}/-{f['deletions']})")
        if len(diff_summary["files"]) > 10:
            result_lines.append(f"  ... and {len(diff_summary['files']) - 10} more")
    
    if warnings and not skip_checks:
        result_lines.append(f"\n⛔ Commit blocked due to warnings.")
        result_lines.append(f"   Use skip_checks=True to force commit, or fix the issues above.")
        return "\n".join(result_lines)
    
    # Perform commit
    code, stdout, stderr = run_git(["commit", "-m", message])
    if code != 0:
        return f"❌ Commit failed: {stderr}"
    
    result_lines.append(f"\n✅ Successfully committed!")
    return "\n".join(result_lines)


async def _git_status_handler(porcelain: bool = False) -> str:
    """
    Enhanced git status with formatted output.
    
    Args:
        porcelain: If True, return machine-readable format
    """
    if not is_git_repo():
        return "❌ Error: Not in a git repository"
    
    status = get_status()
    
    if porcelain:
        lines = []
        for item in status.get("staged", []):
            lines.append(f"S {item['status']} {item['path']}")
        for item in status.get("unstaged", []):
            lines.append(f"U {item['status']} {item['path']}")
        for item in status.get("untracked", []):
            lines.append(f"? ?? {item['path']}")
        return "\n".join(lines) if lines else "Clean"
    
    lines = ["📊 Git Status", ""]
    
    # Staged
    if status.get("staged"):
        lines.append(f"🟢 Staged ({len(status['staged'])}):")
        for item in status["staged"]:
            status_emoji = {"A": "+", "M": "~", "D": "-", "R": "→"}.get(item['status'], item['status'])
            lines.append(f"  {status_emoji} {item['path']}")
        lines.append("")
    
    # Unstaged
    if status.get("unstaged"):
        lines.append(f"🟡 Unstaged ({len(status['unstaged'])}):")
        for item in status["unstaged"]:
            lines.append(f"  ~ {item['path']}")
        lines.append("")
    
    # Untracked
    if status.get("untracked"):
        lines.append(f"⚪ Untracked ({len(status['untracked'])}):")
        for item in status["untracked"]:
            lines.append(f"  ? {item['path']}")
        lines.append("")
    
    if not status.get("has_changes", False):
        lines.append("✨ Working directory clean")
    
    return "\n".join(lines)


async def _git_compare_handler(ref1: str, ref2: str = "HEAD", detailed: bool = False) -> str:
    """
    Compare two git references with semantic summary.
    
    Args:
        ref1: First reference (commit, branch, tag)
        ref2: Second reference (default: HEAD)
        detailed: Show detailed file changes
    """
    if not is_git_repo():
        return "❌ Error: Not in a git repository"
    
    try:
        comparison = compare_versions(ref1, ref2)
    except Exception as e:
        return f"❌ Failed to compare versions: {e}"
    
    lines = [
        f"📊 Version Comparison: {comparison['from']} → {comparison['to']}",
        ""
    ]
    
    # Summary
    lines.append(f"📈 Summary:")
    lines.append(f"  Commits: {comparison['commit_count']}")
    lines.append(f"  Added: {len(comparison['added'])}")
    lines.append(f"  Modified: {len(comparison['modified'])}")
    lines.append(f"  Deleted: {len(comparison['deleted'])}")
    
    # Commit messages
    if comparison['commit_messages']:
        lines.append(f"\n📝 Commits:")
        for msg in comparison['commit_messages'][:10]:
            lines.append(f"  • {msg}")
        if len(comparison['commit_messages']) > 10:
            lines.append(f"  ... and {len(comparison['commit_messages']) - 10} more")
    
    # Files
    if detailed:
        if comparison['added']:
            lines.append(f"\n➕ Added files:")
            for f in comparison['added'][:15]:
                lines.append(f"  + {f}")
            if len(comparison['added']) > 15:
                lines.append(f"  ... and {len(comparison['added']) - 15} more")
        
        if comparison['modified']:
            lines.append(f"\n📝 Modified files:")
            for f in comparison['modified'][:15]:
                lines.append(f"  ~ {f}")
            if len(comparison['modified']) > 15:
                lines.append(f"  ... and {len(comparison['modified']) - 15} more")
        
        if comparison['deleted']:
            lines.append(f"\n➖ Deleted files:")
            for f in comparison['deleted']:
                lines.append(f"  - {f}")
    
    return "\n".join(lines)


async def _git_rollback_handler(target: str = "HEAD~1", mode: str = "soft", create_backup: bool = True) -> str:
    """
    Safe rollback with backup option.
    
    Args:
        target: Target reference to rollback to (default: HEAD~1)
        mode: soft (keep changes), hard (discard changes), or mixed (keep staged)
        create_backup: Create a backup branch before rollback
    """
    if not is_git_repo():
        return "❌ Error: Not in a git repository"
    
    mode = mode.lower()
    if mode not in ("soft", "hard", "mixed"):
        return "❌ Error: mode must be 'soft', 'hard', or 'mixed'"
    
    # Get current state info
    code, current_commit, _ = run_git(["rev-parse", "HEAD"])
    if code != 0:
        return "❌ Failed to get current commit"
    
    current_commit = current_commit.strip()[:8]
    
    # Validate target
    code, target_commit, _ = run_git(["rev-parse", target])
    if code != 0:
        return f"❌ Invalid target reference: {target}"
    
    target_commit = target_commit.strip()[:8]
    
    # Create backup branch
    backup_name = ""
    if create_backup:
        backup_name = create_backup_branch()
        if backup_name:
            pass  # Successfully created
    
    # Build confirmation message
    lines = [
        f"⚠️  Rollback Operation",
        f"",
        f"From: {current_commit}",
        f"To:   {target_commit}",
        f"Mode: {mode}",
    ]
    
    if backup_name:
        lines.append(f"Backup: {backup_name}")
    
    lines.append("")
    
    if mode == "soft":
        lines.append("Changes will be kept as unstaged modifications.")
    elif mode == "hard":
        lines.append("⚠️ WARNING: All changes will be DISCARDED!")
    elif mode == "mixed":
        lines.append("Changes will be kept as staged modifications.")
    
    # Perform rollback
    code, stdout, stderr = run_git(["reset", f"--{mode}", target])
    
    if code != 0:
        return f"❌ Rollback failed: {stderr}"
    
    lines.append(f"\n✅ Successfully rolled back to {target_commit}")
    
    return "\n".join(lines)


async def _git_log_handler(n: int = 10, oneline: bool = True) -> str:
    """
    Show recent commit history.
    
    Args:
        n: Number of commits to show
        oneline: Compact one-line format
    """
    if not is_git_repo():
        return "❌ Error: Not in a git repository"
    
    commits = get_recent_commits(n)
    
    if not commits:
        return "No commits found"
    
    lines = [f"📜 Recent Commits ({len(commits)})", ""]
    
    for commit in commits:
        if oneline:
            lines.append(f"{commit['hash']}  {commit['message'][:50]}")
        else:
            lines.append(f"commit {commit['hash']}")
            lines.append(f"Author: {commit['author']}")
            lines.append(f"Date:   {commit['time']}")
            lines.append(f"")
            lines.append(f"    {commit['message']}")
            lines.append(f"")
    
    return "\n".join(lines)


# Tool schemas
smart_commit_tool = {
    "name": "smart_commit",
    "description": "Smart git commit with automatic message generation based on changes. "
                   "Analyzes staged changes to suggest conventional commit message (type(scope): description). "
                   "Use dry_run=True first to preview, then dry_run=False to commit.",
    "input_schema": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Custom commit message. If empty, AI will auto-generate based on changes."
            },
            "auto_stage": {
                "type": "boolean",
                "description": "Automatically stage all changes before committing",
                "default": False
            },
            "dry_run": {
                "type": "boolean",
                "description": "If True, only show what would be committed without doing it",
                "default": True
            }
        }
    }
}

safe_commit_tool = {
    "name": "safe_commit",
    "description": "Safe git commit with pre-commit safety checks. Detects large files (>10MB) and "
                   "potential secrets (API keys, passwords) before committing. "
                   "Auto-generates conventional commit message if not provided.",
    "input_schema": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Commit message. Auto-generated if empty."
            },
            "auto_stage": {
                "type": "boolean",
                "description": "Automatically stage all changes",
                "default": True
            },
            "skip_checks": {
                "type": "boolean",
                "description": "Skip safety checks (not recommended)",
                "default": False
            }
        }
    }
}

git_status_tool = {
    "name": "git_status",
    "description": "Enhanced git status with formatted output showing staged, unstaged, and untracked files.",
    "input_schema": {
        "type": "object",
        "properties": {
            "porcelain": {
                "type": "boolean",
                "description": "Return machine-readable format",
                "default": False
            }
        }
    }
}

git_compare_tool = {
    "name": "git_compare",
    "description": "Compare two git references (commits, branches, tags) with semantic summary. "
                   "Shows added/modified/deleted files and commit messages between versions.",
    "input_schema": {
        "type": "object",
        "properties": {
            "ref1": {
                "type": "string",
                "description": "First reference (commit hash, branch name, or tag)"
            },
            "ref2": {
                "type": "string",
                "description": "Second reference (default: HEAD)",
                "default": "HEAD"
            },
            "detailed": {
                "type": "boolean",
                "description": "Show detailed file lists",
                "default": False
            }
        },
        "required": ["ref1"]
    }
}

git_rollback_tool = {
    "name": "git_rollback",
    "description": "Safe git rollback to a previous commit with backup option. "
                   "Mode 'soft' keeps changes as unstaged, 'mixed' keeps as staged, 'hard' discards changes.",
    "input_schema": {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Target reference to rollback to (e.g., 'HEAD~1', commit hash)",
                "default": "HEAD~1"
            },
            "mode": {
                "type": "string",
                "description": "Rollback mode: soft (keep unstaged), hard (discard), mixed (keep staged)",
                "enum": ["soft", "hard", "mixed"],
                "default": "soft"
            },
            "create_backup": {
                "type": "boolean",
                "description": "Create a backup branch before rollback",
                "default": True
            }
        }
    }
}

git_log_tool = {
    "name": "git_log",
    "description": "Show recent git commit history with formatted output.",
    "input_schema": {
        "type": "object",
        "properties": {
            "n": {
                "type": "integer",
                "description": "Number of commits to show",
                "default": 10
            },
            "oneline": {
                "type": "boolean",
                "description": "Show compact one-line format",
                "default": True
            }
        }
    }
}


# Export tool definitions and handlers for registration
git_enhanced_tools = [
    ("smart_commit", smart_commit_tool, _smart_commit_handler),
    ("safe_commit", safe_commit_tool, _safe_commit_handler),
    ("git_status", git_status_tool, _git_status_handler),
    ("git_compare", git_compare_tool, _git_compare_handler),
    ("git_rollback", git_rollback_tool, _git_rollback_handler),
    ("git_log", git_log_tool, _git_log_handler),
]
