"""
daily_log.py - 每日日志管理

功能：
  - 创建每日日志文件 memory/YYYY-MM-DD.md
  - 记录当天对话摘要
  - 归档旧日志
"""
from __future__ import annotations
from datetime import datetime, timedelta
from pathlib import Path


def get_daily_log_path(workspace_dir: Path | str | None = None) -> Path:
    """
    获取今天的日志文件路径
    
    Args:
        workspace_dir: workspace 目录
    
    Returns:
        日志文件路径 memory/YYYY-MM-DD.md
    """
    if workspace_dir is None:
        from .workspace import _DEFAULT_WORKSPACE
        workspace_dir = _DEFAULT_WORKSPACE
    
    memory_dir = Path(workspace_dir) / "memory"
    memory_dir.mkdir(exist_ok=True)
    
    today = datetime.now().strftime("%Y-%m-%d")
    return memory_dir / f"{today}.md"


def create_daily_log(summary: str = "", workspace_dir: Path | str | None = None) -> Path:
    """
    创建今天的日志文件
    
    Args:
        summary: 今天的摘要
        workspace_dir: workspace 目录
    
    Returns:
        创建的文件路径
    """
    log_path = get_daily_log_path(workspace_dir)
    
    if log_path.exists():
        return log_path
    
    today = datetime.now().strftime("%Y-%m-%d")
    weekday = datetime.now().strftime("%A")
    
    content = f"""# {today} ({weekday})

## 摘要
{summary if summary else "今天的对话记录"}

## 对话列表
- 

## 重要事项
- 

## 待办
- 
"""
    
    log_path.write_text(content, encoding="utf-8")
    return log_path


def append_to_daily_log(
    entry: str,
    section: str = "对话列表",
    workspace_dir: Path | str | None = None
) -> bool:
    """
    追加内容到今天的日志
    
    Args:
        entry: 要追加的内容
        section: 目标 section
        workspace_dir: workspace 目录
    
    Returns:
        是否成功
    """
    log_path = get_daily_log_path(workspace_dir)
    
    # 如果文件不存在，先创建
    if not log_path.exists():
        create_daily_log(workspace_dir=workspace_dir)
    
    try:
        content = log_path.read_text(encoding="utf-8")
        
        # 查找 section 并追加
        section_pattern = f"## {section}"
        if section_pattern in content:
            # 在 section 后追加
            lines = content.split("\n")
            new_lines = []
            in_target_section = False
            inserted = False
            
            for line in lines:
                new_lines.append(line)
                
                if line.strip() == section_pattern:
                    in_target_section = True
                    continue
                
                if in_target_section and not inserted:
                    # 检查是否到了下一个 section
                    if line.startswith("## "):
                        # 在之前插入
                        new_lines.insert(-1, f"- {entry}")
                        inserted = True
                        in_target_section = False
                    elif line.strip() == "" and len(new_lines) > 1:
                        # 空行，可以插入
                        new_lines.append(f"- {entry}")
                        inserted = True
            
            if not inserted:
                # 在末尾追加
                new_lines.append(f"- {entry}")
            
            content = "\n".join(new_lines)
        else:
            # 添加新 section
            content += f"\n## {section}\n- {entry}\n"
        
        log_path.write_text(content, encoding="utf-8")
        return True
    
    except Exception as e:
        print(f"Error appending to daily log: {e}")
        return False


def archive_old_logs(days: int = 30, workspace_dir: Path | str | None = None) -> int:
    """
    归档超过 N 天的旧日志
    
    Args:
        days: 保留天数，默认 30 天
        workspace_dir: workspace 目录
    
    Returns:
        归档的文件数量
    """
    if workspace_dir is None:
        from .workspace import _DEFAULT_WORKSPACE
        workspace_dir = _DEFAULT_WORKSPACE
    
    memory_dir = Path(workspace_dir) / "memory"
    if not memory_dir.exists():
        return 0
    
    archive_dir = memory_dir / "archive"
    archive_dir.mkdir(exist_ok=True)
    
    cutoff_date = datetime.now() - timedelta(days=days)
    archived_count = 0
    
    for log_file in memory_dir.glob("*.md"):
        try:
            # 从文件名解析日期
            date_str = log_file.stem
            log_date = datetime.strptime(date_str, "%Y-%m-%d")
            
            if log_date < cutoff_date:
                # 移动到归档目录
                archive_path = archive_dir / log_file.name
                log_file.rename(archive_path)
                archived_count += 1
        except ValueError:
            # 文件名不是日期格式，跳过
            continue
    
    return archived_count


def list_recent_logs(days: int = 7, workspace_dir: Path | str | None = None) -> list[Path]:
    """
    列出最近 N 天的日志
    
    Args:
        days: 天数
        workspace_dir: workspace 目录
    
    Returns:
        日志文件路径列表
    """
    if workspace_dir is None:
        from .workspace import _DEFAULT_WORKSPACE
        workspace_dir = _DEFAULT_WORKSPACE
    
    memory_dir = Path(workspace_dir) / "memory"
    if not memory_dir.exists():
        return []
    
    cutoff_date = datetime.now() - timedelta(days=days)
    recent_logs = []
    
    for log_file in memory_dir.glob("*.md"):
        try:
            date_str = log_file.stem
            log_date = datetime.strptime(date_str, "%Y-%m-%d")
            
            if log_date >= cutoff_date:
                recent_logs.append((log_date, log_file))
        except ValueError:
            continue
    
    # 按日期排序
    recent_logs.sort(reverse=True)
    return [path for _, path in recent_logs]
