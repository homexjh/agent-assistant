"""
Git utilities for enhanced git operations.
Provides semantic analysis, safety checks, and commit message generation.
"""

import re
import subprocess
from pathlib import Path
from typing import Optional


def run_git(args: list[str], cwd: Optional[str] = None) -> tuple[int, str, str]:
    """Run git command and return (code, stdout, stderr)."""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        cwd=cwd or "."
    )
    return result.returncode, result.stdout, result.stderr


def get_repo_root() -> Optional[str]:
    """Get git repository root directory."""
    code, stdout, _ = run_git(["rev-parse", "--show-toplevel"])
    return stdout.strip() if code == 0 else None


def is_git_repo() -> bool:
    """Check if current directory is in a git repository."""
    return get_repo_root() is not None


def get_status() -> dict:
    """Get detailed git status."""
    code, stdout, _ = run_git(["status", "--porcelain"])
    if code != 0:
        return {"error": "Not a git repository"}
    
    staged = []
    unstaged = []
    untracked = []
    
    for line in stdout.strip().split("\n"):
        if not line:
            continue
        status = line[:2]
        file_path = line[3:]
        
        if status[0] != " " and status[0] != "?":
            staged.append({"status": status[0], "path": file_path})
        if status[1] != " " and status[1] != "?":
            unstaged.append({"status": status[1], "path": file_path})
        if status == "??":
            untracked.append({"path": file_path})
    
    return {
        "staged": staged,
        "unstaged": unstaged,
        "untracked": untracked,
        "has_changes": bool(staged or unstaged or untracked)
    }


def get_diff_summary(staged: bool = False) -> dict:
    """Get summary of changes."""
    args = ["diff", "--stat"] if not staged else ["diff", "--staged", "--stat"]
    code, stdout, _ = run_git(args)
    
    if code != 0:
        return {"error": "Failed to get diff"}
    
    files = []
    total_additions = 0
    total_deletions = 0
    
    for line in stdout.strip().split("\n"):
        if "|" in line and ("+" in line or "-" in line):
            parts = line.split("|")
            file_path = parts[0].strip()
            changes = parts[1].strip()
            
            additions = changes.count("+")
            deletions = changes.count("-")
            
            files.append({
                "path": file_path,
                "additions": additions,
                "deletions": deletions
            })
            total_additions += additions
            total_deletions += deletions
    
    return {
        "files": files,
        "total_additions": total_additions,
        "total_deletions": total_deletions,
        "file_count": len(files)
    }


def get_staged_diff_content() -> str:
    """Get the actual diff content of staged changes."""
    code, stdout, _ = run_git(["diff", "--staged"])
    return stdout if code == 0 else ""


def analyze_change_type(file_path: str, diff_content: str) -> str:
    """Analyze what type of change this is."""
    path_lower = file_path.lower()
    
    # Detect file type patterns
    if any(x in path_lower for x in ["test", "spec"]):
        return "test"
    
    if any(x in path_lower for x in ["doc", "readme", "md", "changelog"]):
        return "docs"
    
    # Analyze diff content for patterns
    if diff_content:
        # New feature patterns
        if any(kw in diff_content for kw in ["+def ", "+class ", "+async def"]):
            # Check if it's new or modification
            if diff_content.count("\n+") > diff_content.count("\n-") * 2:
                return "feat"
        
        # Fix patterns
        if any(kw in diff_content.lower() for kw in ["fix", "bug", "error", "exception"]):
            return "fix"
        
        # Refactor patterns
        if any(kw in diff_content.lower() for kw in ["rename", "move", "refactor", "simplify"]):
            return "refactor"
    
    # Default based on file location
    if "tool" in path_lower:
        return "feat"
    if "config" in path_lower or "setting" in path_lower:
        return "chore"
    
    return "feat"


def detect_scope(file_path: str) -> str:
    """Detect conventional commit scope from file path."""
    parts = file_path.split("/")
    
    # Common scope patterns
    if len(parts) >= 2:
        if parts[0] in ["aiagent", "src"]:
            if len(parts) > 1:
                # aiagent/tools/file.py -> tools
                # aiagent/agent.py -> agent
                scope = parts[1].replace(".py", "")
                return scope
        return parts[0]
    
    return Path(file_path).stem


def check_large_files(max_size_mb: float = 10.0) -> list[dict]:
    """Check for large files that shouldn't be committed."""
    status = get_status()
    large_files = []
    
    for item in status.get("untracked", []) + status.get("staged", []):
        path = item["path"] if isinstance(item, dict) else item
        try:
            size = Path(path).stat().st_size / (1024 * 1024)  # MB
            if size > max_size_mb:
                large_files.append({
                    "path": path,
                    "size_mb": round(size, 2)
                })
        except (FileNotFoundError, OSError):
            continue
    
    return large_files


def check_sensitive_patterns() -> list[dict]:
    """Check for potentially sensitive patterns in staged changes."""
    patterns = [
        (r"(password|passwd|pwd)\s*[=:]\s*[\"'][^\"']{4,}[\"']", "password"),
        (r"(api[_-]?key|apikey)\s*[=:]\s*[\"'][^\"']{10,}[\"']", "api_key"),
        (r"(secret|token)\s*[=:]\s*[\"'][^\"']{10,}[\"']", "secret"),
        (r"sk-[a-zA-Z0-9]{20,}", "openai_key"),
        (r"gh[pousr]_[A-Za-z0-9_]{36}", "github_token"),
        (r"AKIA[0-9A-Z]{16}", "aws_key"),
    ]
    
    warnings = []
    diff_content = get_staged_diff_content()
    
    for pattern, pattern_type in patterns:
        matches = re.finditer(pattern, diff_content, re.IGNORECASE)
        for match in matches:
            # Get context line
            start = max(0, match.start() - 30)
            end = min(len(diff_content), match.end() + 30)
            context = diff_content[start:end].replace("\n", " ")
            
            warnings.append({
                "type": pattern_type,
                "context": context[:80] + "..." if len(context) > 80 else context
            })
    
    return warnings


def generate_commit_description(files: list[dict]) -> str:
    """Generate a human-readable description of changes."""
    descriptions = []
    
    for file_info in files:
        path = file_info["path"]
        additions = file_info.get("additions", 0)
        deletions = file_info.get("deletions", 0)
        
        # Generate description based on file and changes
        filename = Path(path).name
        
        if additions > 0 and deletions == 0:
            action = "add"
        elif deletions > 0 and additions == 0:
            action = "remove"
        elif additions > deletions * 2:
            action = "add"
        elif deletions > additions * 2:
            action = "refactor"
        else:
            action = "update"
        
        # Map to natural language
        action_words = {
            "add": f"add {filename} support",
            "remove": f"remove {filename}",
            "update": f"update {filename}",
            "refactor": f"refactor {filename}"
        }
        
        descriptions.append(action_words.get(action, f"modify {filename}"))
    
    # Deduplicate and join
    unique = list(dict.fromkeys(descriptions))
    if len(unique) == 1:
        return unique[0]
    elif len(unique) <= 3:
        return "; ".join(unique)
    else:
        return f"{unique[0]} and {len(unique)-1} other changes"


def suggest_commit_message() -> dict:
    """Generate a suggested conventional commit message."""
    diff_summary = get_diff_summary(staged=False)
    
    if diff_summary.get("file_count", 0) == 0:
        return {"error": "No changes to commit"}
    
    # Get detailed diff for analysis
    diff_content = ""
    code, stdout, _ = run_git(["diff"])
    if code == 0:
        diff_content = stdout[:5000]  # Limit for analysis
    
    # Analyze each file
    types_count = {"feat": 0, "fix": 0, "docs": 0, "test": 0, "refactor": 0, "chore": 0}
    scopes = []
    
    for file_info in diff_summary["files"]:
        change_type = analyze_change_type(file_info["path"], diff_content)
        types_count[change_type] = types_count.get(change_type, 0) + 1
        scopes.append(detect_scope(file_info["path"]))
    
    # Determine primary type
    primary_type = max(types_count, key=types_count.get)
    if types_count[primary_type] == 0:
        primary_type = "feat"
    
    # Determine scope (most common)
    if scopes:
        from collections import Counter
        scope = Counter(scopes).most_common(1)[0][0]
    else:
        scope = "core"
    
    # Generate description
    description = generate_commit_description(diff_summary["files"])
    
    # Construct message
    message = f"{primary_type}({scope}): {description}"
    
    # Ensure proper length
    if len(message) > 72:
        message = message[:69] + "..."
    
    return {
        "type": primary_type,
        "scope": scope,
        "description": description,
        "message": message,
        "stats": diff_summary,
        "types_distribution": types_count
    }


def get_recent_commits(n: int = 5) -> list[dict]:
    """Get recent commit history."""
    code, stdout, _ = run_git([
        "log", f"-{n}", 
        "--pretty=format:%h|%s|%an|%ar"
    ])
    
    if code != 0:
        return []
    
    commits = []
    for line in stdout.strip().split("\n"):
        if "|" in line:
            parts = line.split("|")
            commits.append({
                "hash": parts[0],
                "message": parts[1],
                "author": parts[2],
                "time": parts[3]
            })
    
    return commits


def compare_versions(ref1: str, ref2: str = "HEAD") -> dict:
    """Compare two git references."""
    # Get diff stat
    code, stat_out, _ = run_git(["diff", f"{ref1}...{ref2}", "--stat"])
    
    # Get file list
    code2, name_out, _ = run_git(["diff", f"{ref1}...{ref2}", "--name-status"])
    
    added = []
    modified = []
    deleted = []
    
    for line in name_out.strip().split("\n"):
        if "\t" in line:
            status, path = line.split("\t", 1)
            if status == "A":
                added.append(path)
            elif status == "M":
                modified.append(path)
            elif status == "D":
                deleted.append(path)
            elif status.startswith("R"):
                # Renamed
                modified.append(path.split("\t")[-1])
    
    # Get commit messages between refs
    code3, log_out, _ = run_git([
        "log", f"{ref1}...{ref2}",
        "--pretty=format:%s"
    ])
    
    commit_messages = [m for m in log_out.strip().split("\n") if m]
    
    return {
        "from": ref1,
        "to": ref2,
        "added": added,
        "modified": modified,
        "deleted": deleted,
        "stats_summary": stat_out.strip().split("\n")[-1] if stat_out else "",
        "commit_messages": commit_messages,
        "commit_count": len(commit_messages)
    }


def create_backup_branch(name: Optional[str] = None) -> str:
    """Create a backup branch before risky operations."""
    if name is None:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"backup/{timestamp}"
    
    # Get current HEAD
    code, stdout, _ = run_git(["rev-parse", "HEAD"])
    if code != 0:
        return ""
    
    current_commit = stdout.strip()
    
    # Create branch
    code, _, stderr = run_git(["branch", name, current_commit])
    if code != 0:
        return ""
    
    return name
