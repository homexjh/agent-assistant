"""
browser 工具：用 Playwright 控制本地浏览器

支持的 actions:
  status      - 检查 Playwright 是否可用
  open        - 打开 URL（启动浏览器/新标签）
  snapshot    - 获取页面 ARIA 树（文本形式）
  screenshot  - 截图（返回文件路径）
  navigate    - 导航到 URL
  act         - 执行 UI 交互（click/type/press/evaluate）
                  有 text   → fill（输入）
                  有 key    → press（键盘按键，如 Enter、Tab、Escape）
                  有 script → evaluate（执行 JS）
                  否则      → click
  scroll      - 滚动页面
  tabs        - 列出所有标签页
  close       - 关闭浏览器
  record      - 开始/停止录屏（生成视频）

依赖：playwright（可选）
安装：uv add playwright && uv run playwright install chromium
"""
from __future__ import annotations
import asyncio
import os
import tempfile
import time
from .types import RegisteredTool, ToolDefinition

# 全局浏览器状态（进程内单例）
_browser = None
_page = None
_playwright = None
_video_dir = None  # 视频录制目录
_step_counter = 0  # 步骤计数器用于截图命名


def _is_playwright_available() -> bool:
    try:
        import playwright  # noqa
        return True
    except ImportError:
        return False


def _is_browser_installed() -> bool:
    """检查 Chromium 浏览器是否已下载安装"""
    try:
        # 方法1: 尝试导入并使用 playwright 获取路径
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            path = p.chromium.executable_path
            if path and os.path.exists(path):
                return True
    except Exception:
        pass
    
    # 方法2: 直接检查常见的安装路径
    home = os.path.expanduser("~")
    possible_paths = [
        # macOS ARM64
        f"{home}/Library/Caches/ms-playwright/chromium-*/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
        # macOS Intel
        f"{home}/Library/Caches/ms-playwright/chromium-*/chrome-mac/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
        # Linux
        f"{home}/.cache/ms-playwright/chromium-*/chrome-linux/chrome",
    ]
    
    import glob
    for pattern in possible_paths:
        matches = glob.glob(pattern)
        for match in matches:
            if os.path.exists(match) and os.access(match, os.X_OK):
                return True
    
    return False


def _get_screenshot_dir() -> str:
    """获取截图保存目录"""
    ss_dir = os.path.join(tempfile.gettempdir(), "aiagent_browser")
    os.makedirs(ss_dir, exist_ok=True)
    return ss_dir


async def _auto_screenshot(page, name: str) -> str | None:
    """自动截图并返回路径"""
    global _step_counter
    try:
        _step_counter += 1
        ss_dir = _get_screenshot_dir()
        timestamp = time.strftime("%H%M%S")
        filename = f"step_{_step_counter:03d}_{timestamp}_{name}.png"
        filepath = os.path.join(ss_dir, filename)
        await page.screenshot(path=filepath, full_page=True)
        return filepath
    except Exception:
        return None


async def _ensure_browser(headless: bool = True, record_video: bool = False):
    global _browser, _page, _playwright, _video_dir
    if _browser is None:
        from playwright.async_api import async_playwright
        _playwright = await async_playwright().start()
        
        if record_video:
            _video_dir = os.path.join(tempfile.gettempdir(), "aiagent_videos")
            os.makedirs(_video_dir, exist_ok=True)
            _browser = await _playwright.chromium.launch(headless=headless)
            context = await _browser.new_context(
                record_video_dir=_video_dir,
                record_video_size={"width": 1280, "height": 720}
            )
            _page = await context.new_page()
        else:
            _browser = await _playwright.chromium.launch(headless=headless)
            _page = await _browser.new_page()
    return _browser, _page


def _detect_headless() -> bool:
    """自动检测是否应该使用无头模式"""
    import platform
    # Linux: 检查 DISPLAY 环境变量
    if platform.system() == "Linux":
        return os.environ.get("DISPLAY") is None
    # macOS: 检查是否有图形会话（近似判断）
    if platform.system() == "Darwin":
        # macOS 通常有图形界面，但 CI/SSH 环境可能没有
        return os.environ.get("SSH_CONNECTION") is not None or os.environ.get("CI") is not None
    # Windows: 检查是否有图形会话
    if platform.system() == "Windows":
        return os.environ.get("CI") is not None
    return True  # 默认无头


async def _browser_handler(
    action: str,
    url: str | None = None,
    ref: str | None = None,
    text: str | None = None,
    key: str | None = None,
    script: str | None = None,
    output: str | None = None,
    headless: bool | None = None,  # None 表示自动检测
    timeout_ms: int = 10000,
    scroll_x: int = 0,
    scroll_y: int = 300,
    auto_screenshot: bool = True,  # 自动截图开关
) -> str:
    # 自动检测 headless
    if headless is None:
        headless = _detect_headless()
    global _browser, _page, _playwright, _step_counter

    if not _is_playwright_available():
        return (
            "Error: playwright Python package is not installed.\n"
            "Install: uv add playwright && uv run playwright install chromium"
        )
    
    if not _is_browser_installed():
        return (
            "Error: Playwright browser (Chromium) is not installed.\n"
            "Please run the following command to download it:\n\n"
            "  uv run playwright install chromium\n\n"
            "Note: This downloads about 100MB and may take a few minutes depending on your network."
        )

    if action == "status":
        status = "running" if _browser else "stopped"
        ss_dir = _get_screenshot_dir()
        screenshots = sorted([f for f in os.listdir(ss_dir) if f.endswith('.png')]) if os.path.exists(ss_dir) else []
        result = f"Browser status: {status}"
        if screenshots:
            result += f"\nScreenshots ({len(screenshots)}): {ss_dir}"
        return result

    if action == "close":
        if _browser:
            await _browser.close()
            if _playwright:
                await _playwright.stop()
            _browser = None
            _page = None
            _playwright = None
        ss_dir = _get_screenshot_dir()
        return f"Browser closed. Screenshots saved at: {ss_dir}"

    if action == "tabs":
        if not _browser:
            return "Browser is not running. Use action=open first."
        pages = _browser.contexts[0].pages if _browser.contexts else []
        tab_list = "\n".join(
            f"  [{i}] {'[ACTIVE] ' if p == _page else ''}{p.url[:80]}..." if len(p.url) > 80 else f"  [{i}] {'[ACTIVE] ' if p == _page else ''}{p.url}" for i, p in enumerate(pages)
        ) or "  (no tabs)"
        return f"Open tabs:\n{tab_list}"
    
    if action == "switch_tab":
        """切换到指定索引的标签页"""
        if not _browser or not _browser.contexts:
            return "Browser is not running. Use action=open first."
        
        tab_index = ref  # 使用 ref 参数传递索引
        if tab_index is None:
            return "Error: 'ref' (tab index) is required for action=switch_tab."
        
        try:
            idx = int(tab_index)
            pages = _browser.contexts[0].pages
            if idx < 0 or idx >= len(pages):
                return f"Error: Invalid tab index {idx}. Available: 0-{len(pages)-1}. Use action=tabs to list."
            _page = pages[idx]
            await _page.bring_to_front()
            ss_path = await _auto_screenshot(_page, "switch_tab") if auto_screenshot else None
            result = f"Switched to tab [{idx}]: {_page.url}"
            if ss_path:
                result += f"\n📸 Screenshot: {ss_path}"
            return result
        except ValueError:
            return f"Error: 'ref' must be a number (tab index). Got: {tab_index}"

    if action == "open":
        if not url:
            return "Error: 'url' is required for action=open."
        _, page = await _ensure_browser(headless=headless)
        await page.goto(url, timeout=timeout_ms)
        await page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
        ss_path = await _auto_screenshot(page, "open") if auto_screenshot else None
        result = f"Opened: {page.url}"
        if ss_path:
            result += f"\n📸 Screenshot: {ss_path}"
        return result

    if action == "navigate":
        if not url:
            return "Error: 'url' is required for action=navigate."
        _, page = await _ensure_browser(headless=headless)
        await page.goto(url, timeout=timeout_ms)
        await page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
        ss_path = await _auto_screenshot(page, "navigate") if auto_screenshot else None
        result = f"Navigated to: {page.url}"
        if ss_path:
            result += f"\n📸 Screenshot: {ss_path}"
        return result

    if action == "snapshot":
        _, page = await _ensure_browser(headless=headless)
        # 返回页面可见文本内容（简化 ARIA 树）
        text_content = await page.evaluate("""() => {
            function getText(el, depth=0) {
                // 文本节点
                if (el.nodeType === 3) return el.textContent.trim();
                // 非 Element 节点（注释、CDATA等）
                if (el.nodeType !== 1) return '';
                // 跳过脚本和样式
                if (['SCRIPT','STYLE','NOSCRIPT'].includes(el.tagName)) return '';
                const role = el.getAttribute('aria-label') || el.getAttribute('alt') || '';
                const tag = el.tagName.toLowerCase();
                const children = Array.from(el.childNodes).map(c => getText(c, depth+1)).filter(Boolean).join(' ');
                if (role) return `[${tag}:${role}] ${children}`;
                return children;
            }
            return getText(document.body);
        }""")
        title = await page.title()
        url_now = page.url
        snippet = (text_content or "").strip()
        if len(snippet) > 4000:
            snippet = snippet[:4000] + "\n...[truncated]"
        ss_path = await _auto_screenshot(page, "snapshot") if auto_screenshot else None
        result = f"URL: {url_now}\nTitle: {title}\n\n{snippet}"
        if ss_path:
            result += f"\n\n📸 Screenshot: {ss_path}"
        return result

    if action == "screenshot":
        _, page = await _ensure_browser(headless=headless)
        out = output or os.path.join(_get_screenshot_dir(), f"manual_{int(time.time())}.png")
        await page.screenshot(path=out, full_page=True)
        return f"📸 Screenshot saved to: {out}"

    if action == "act":
        if not ref and not script:
            return "Error: 'ref' (CSS selector) or 'script' is required for action=act."
        _, page = await _ensure_browser(headless=headless)

        if script:
            result = await page.evaluate(script)
            ss_path = await _auto_screenshot(page, "act_script") if auto_screenshot else None
            result_str = f"evaluate result: {result}"
            if ss_path:
                result_str += f"\n📸 Screenshot: {ss_path}"
            return result_str

        # ref 是 CSS selector
        el = page.locator(ref)
        count = await el.count()
        if count == 0:
            return f"Error: no element found for selector '{ref}'."

        # 根据参数判断操作类型
        action_name = ""
        if text is not None:
            await el.fill(text, timeout=timeout_ms)
            action_name = f"type_{text[:20]}"
            result = f"Typed '{text}' into '{ref}'."
        elif key is not None:
            await el.press(key, timeout=timeout_ms)
            action_name = f"press_{key}"
            result = f"Pressed key '{key}' on '{ref}'."
        else:
            # 获取点击前的标签页数量
            initial_pages = len(_browser.contexts[0].pages) if _browser and _browser.contexts else 0
            await el.click(timeout=timeout_ms)
            action_name = "click"
            await page.wait_for_timeout(1000)  # 等待新标签页打开
            
            # 检测是否有新标签页打开，自动切换到最新标签页
            current_pages = len(_browser.contexts[0].pages) if _browser and _browser.contexts else 0
            if current_pages > initial_pages:
                new_tabs = current_pages - initial_pages
                # 自动切换到最新的标签页（最后一个）
                _page = _browser.contexts[0].pages[-1]
                await _page.bring_to_front()
                page = _page  # 同时更新局部变量，确保后续截图在新页面
                result = f"Clicked '{ref}'.\n✅ 检测到 {new_tabs} 个新标签页，已自动切换到最新标签页: {_page.url[:80]}..."
            else:
                result = f"Clicked '{ref}'."
        
        # 操作后等待一下再截图（注意：如果切换了标签页，page 已更新为新页面）
        await page.wait_for_timeout(500)
        ss_path = await _auto_screenshot(page, action_name) if auto_screenshot else None
        if ss_path:
            result += f"\n📸 Screenshot: {ss_path}"
        return result

    if action == "scroll":
        _, page = await _ensure_browser(headless=headless)
        await page.evaluate(f"window.scrollBy({scroll_x}, {scroll_y})")
        await page.wait_for_timeout(300)
        ss_path = await _auto_screenshot(page, "scroll") if auto_screenshot else None
        result = f"Scrolled by ({scroll_x}, {scroll_y})."
        if ss_path:
            result += f"\n📸 Screenshot: {ss_path}"
        return result
    
    if action == "list_screenshots":
        """列出所有截图"""
        ss_dir = _get_screenshot_dir()
        if not os.path.exists(ss_dir):
            return "No screenshots yet."
        files = sorted([f for f in os.listdir(ss_dir) if f.endswith('.png')])
        if not files:
            return "No screenshots yet."
        lines = [f"Screenshots in {ss_dir}:", ""]
        for i, f in enumerate(files, 1):
            filepath = os.path.join(ss_dir, f)
            size = os.path.getsize(filepath)
            lines.append(f"  {i}. {f} ({size//1024}KB)")
        lines.append(f"\nTotal: {len(files)} screenshots")
        return "\n".join(lines)
    
    if action == "clear_screenshots":
        """清除所有截图"""
        global _step_counter
        ss_dir = _get_screenshot_dir()
        if os.path.exists(ss_dir):
            for f in os.listdir(ss_dir):
                if f.endswith('.png'):
                    os.remove(os.path.join(ss_dir, f))
        _step_counter = 0
        return f"Screenshots cleared from {ss_dir}"

    return f"Error: unknown action '{action}'. Valid: status/open/navigate/snapshot/screenshot/act/scroll/tabs/close/list_screenshots/clear_screenshots"


browser_tool = RegisteredTool(
    definition=ToolDefinition(
        type="function",
        function={
            "name": "browser",
           "description": (
                "Control a local browser using Playwright. "
                "Requires: uv add playwright && uv run playwright install chromium. "
                "Actions: status, open, navigate, snapshot (get page text), "
                "screenshot, act (click/type/press/evaluate via CSS selector or JS), scroll, tabs, "
                "switch_tab (switch to tab by index), list_screenshots, clear_screenshots, close. "
                "NOTE: After click that opens new tab, use action=tabs to see all tabs, then switch_tab to change."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["status", "open", "navigate", "snapshot", "screenshot",
                                 "act", "scroll", "tabs", "switch_tab", "list_screenshots", "clear_screenshots", "close"],
                        "description": "Browser action to perform.",
                    },
                    "url": {
                        "type": "string",
                        "description": "URL for open/navigate actions.",
                    },
                    "ref": {
                        "type": "string",
                        "description": "CSS selector for act action (e.g. '#submit', 'input[name=q]'). For switch_tab action, this is the tab index (0, 1, 2...).",
                    },
                    "text": {
                        "type": "string",
                        "description": "Text to type into element (act action with ref). Performs fill.",
                    },
                    "key": {
                        "type": "string",
                        "description": (
                            "Keyboard key to press on element (act action with ref). "
                            "Examples: 'Enter', 'Tab', 'Escape', 'ArrowDown'. "
                            "Takes priority over click when both ref and key are provided."
                        ),
                    },
                    "script": {
                        "type": "string",
                        "description": "JavaScript to evaluate in page context (act action, no ref needed).",
                    },
                    "output": {
                        "type": "string",
                        "description": "Output file path for screenshot action.",
                    },
                    "headless": {
                        "type": "boolean",
                        "description": "Run browser in headless mode. If not specified, auto-detects based on environment (headless on Linux without DISPLAY or SSH, GUI mode on macOS/Windows desktop).",
                    },
                    "timeout_ms": {
                        "type": "integer",
                        "description": "Action timeout in milliseconds (default 10000).",
                    },
                    "scroll_x": {
                        "type": "integer",
                        "description": "Horizontal scroll amount in pixels (scroll action).",
                    },
                    "scroll_y": {
                        "type": "integer",
                        "description": "Vertical scroll amount in pixels (scroll action, default 300).",
                    },
                    "auto_screenshot": {
                        "type": "boolean",
                        "description": "Automatically take screenshot after each action (default true).",
                    },
                },
                "required": ["action"],
            },
        },
    ),
    handler=_browser_handler,  # type: ignore[arg-type]
)
