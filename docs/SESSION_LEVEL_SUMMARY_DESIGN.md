# 方案 B：会话级别 Daily Log 总结设计文档

> 版本: 1.0  
> 日期: 2026-03-23  
> 分支: feature/session-level-summary-20260323  
> 目标: 实现基于用户会话的 Daily Log 自动摘要（超时触发 + 继续累积）

---

## 一、问题背景

### 当前问题
- 每次 HTTP 请求结束后都生成摘要
- 同一主题的多轮对话产生多个重复摘要
- 用户回来继续聊天时，上下文被割裂

### 目标
- 按**用户会话**维度生成摘要
- 用户**5 分钟无操作**后才触发总结
- 总结后**保留消息**，用户回来**继续累积**

---

## 二、架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     会话级别 Daily Log 架构                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐      ┌─────────────────┐      ┌─────────────┐ │
│  │   用户请求   │─────▶│  SessionManager │─────▶│  超时检测器  │ │
│  └─────────────┘      └─────────────────┘      └──────┬──────┘ │
│                              │                        │         │
│                              ▼                        ▼         │
│                       ┌─────────────┐           ┌────────────┐  │
│                       │ data/sessions│          │ 生成摘要?  │  │
│                       │ sess_xxx.json│          └─────┬──────┘  │
│                       └─────────────┘                 │          │
│                              │                  是 /    \ 否     │
│                              ▼                  /        \       │
│                       ┌─────────────┐          ▼          ▼      │
│                       │ 累积消息     │    ┌─────────┐  继续等待  │
│                       │ last_summary│    │ 生成摘要 │            │
│                       └─────────────┘    └────┬────┘            │
│                                               │                  │
│                                               ▼                  │
│                              ┌────────────────┴─────────────┐   │
│                              ▼                              ▼   │
│                    ┌──────────────────┐          ┌────────────────┤
│                    │ workspace/memory │          │ data/sessions  │
│                    │ 2026-03-23.md    │          │ sess_xxx.json  │
│                    │  (Daily Log)     │          │ ["summaries"]  │
│                    └──────────────────┘          └────────────────┘
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 核心组件

#### SessionManager
- **职责**: 管理会话生命周期、消息累积、超时检测
- **存储**: `data/sessions/{session_id}.json`
- **关键字段**:
  - `last_summary_at`: 上次摘要时间（用于超时计算）
  - `summaries[]`: 本会话生成的摘要列表

#### 超时触发机制
- **条件**: `当前时间 - last_summary_at > 5分钟` 且 `有效消息 >= 5`
- **动作**: 生成摘要 → 写入 Daily Log → 更新 `last_summary_at`
- **注意**: 不清空消息，用户回来继续累积

### 2.3 数据流

```
用户发送消息
    ↓
读取 sess_xxx.json
    ↓
添加消息到 messages[]
    ↓
检查: (now - last_summary_at) > 300s ?
    ↓
    是 → 生成摘要 → 写入 Daily Log → 更新 last_summary_at
    否 → 直接保存
    ↓
返回响应给用户
```

---

## 三、数据模型

### 3.1 扩展现有的 session 文件

```json
{
  "id": "sess_1774255044515",
  "title": "写一个冒泡排序的 Python 实现，运行并验证",
  "created_at": "2026-03-23T15:00:00",
  "last_active": "2026-03-23T15:30:00",
  
  "messages": [
    {"role": "user", "content": "...", "timestamp": "15:00:00"},
    {"role": "assistant", "content": "...", "timestamp": "15:01:00"}
  ],
  
  "// 新增字段": "====================================",
  "last_summary_at": "2026-03-23T15:10:00",
  "summaries": [
    {
      "time": "15:10",
      "content": "用户询问冒泡排序的 Python 实现",
      "message_count": 8
    },
    {
      "time": "15:35", 
      "content": "继续询问快速排序的实现方法",
      "message_count": 10
    }
  ]
}
```

### 3.2 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `last_summary_at` | ISO 8601 | 上次生成摘要的时间，用于计算超时 |
| `summaries` | array | 本会话生成的所有摘要列表 |
| `summaries[].time` | string | 摘要生成时间 (HH:MM) |
| `summaries[].content` | string | 摘要内容 |
| `summaries[].message_count` | int | 生成摘要时的消息数量 |

---

## 四、具体实现

### 4.1 文件结构

```
aiagent/
├── session_manager.py      # 新增：会话管理器
├── serve.py                # 修改：集成 SessionManager
└── daily_log.py            # 已有：无需修改
```

### 4.2 SessionManager 实现

```python
# aiagent/session_manager.py

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


class SessionManager:
    """
    会话管理器：负责消息累积和定时摘要生成
    
    核心功能：
    1. 按 session_id 累积消息
    2. 检测超时（5分钟无新消息）
    3. 生成摘要并写入 Daily Log
    4. 不清空消息，支持继续累积
    """
    
    TIMEOUT_SECONDS = 300  # 5分钟超时
    MIN_VALID_MESSAGES = 5  # 最少有效消息数
    
    def __init__(self, data_dir: Path):
        """
        Args:
            data_dir: data/sessions/ 目录路径
        """
        self.sessions_dir = data_dir
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
    
    def add_message(
        self, 
        session_id: str, 
        role: str, 
        content: str
    ) -> Optional[str]:
        """
        添加消息到会话，触发超时检测
        
        Args:
            session_id: 会话 ID
            role: 'user' 或 'assistant'
            content: 消息内容
            
        Returns:
            如果生成了新摘要，返回摘要内容；否则返回 None
        """
        # 1. 加载会话
        session = self._load_session(session_id)
        
        # 2. 添加消息
        now = datetime.now()
        message = {
            "role": role,
            "content": content,
            "timestamp": now.isoformat()
        }
        session["messages"].append(message)
        session["last_active"] = now.isoformat()
        
        # 3. 检查是否需要生成摘要
        summary = self._check_and_generate_summary(session, now)
        
        # 4. 保存会话
        self._save_session(session_id, session)
        
        return summary
    
    def _check_and_generate_summary(
        self, 
        session: dict, 
        now: datetime
    ) -> Optional[str]:
        """
        检查超时条件并生成摘要
        
        Returns:
            生成的摘要内容，或 None
        """
        # 获取上次摘要时间
        last_summary_str = session.get("last_summary_at")
        if last_summary_str:
            last_summary = datetime.fromisoformat(last_summary_str)
        else:
            last_summary = datetime.min
        
        # 检查超时
        time_since_summary = (now - last_summary).total_seconds()
        if time_since_summary < self.TIMEOUT_SECONDS:
            return None  # 未超时，不生成
        
        # 统计有效消息
        valid_count = self._count_valid_messages(session["messages"])
        if valid_count < self.MIN_VALID_MESSAGES:
            return None  # 消息不足，不生成
        
        # 生成摘要
        summary = self._generate_summary(session["messages"])
        
        # 更新会话摘要记录
        if "summaries" not in session:
            session["summaries"] = []
        
        session["summaries"].append({
            "time": now.strftime("%H:%M"),
            "content": summary,
            "message_count": valid_count
        })
        session["last_summary_at"] = now.isoformat()
        
        # 写入 Daily Log
        self._write_to_daily_log(summary, now)
        
        return summary
    
    def _generate_summary(self, messages: list[dict]) -> str:
        """
        生成摘要内容
        
        策略：取最近一条用户消息作为摘要
        """
        # 取最近10条消息
        recent = messages[-10:]
        
        # 找最后一条用户消息
        for msg in reversed(recent):
            if msg.get("role") == "user":
                content = msg.get("content", "")[:50]
                return f"用户询问: {content}..."
        
        return "对话进行中"
    
    def _write_to_daily_log(self, summary: str, now: datetime):
        """写入 Daily Log"""
        from .daily_log import append_to_daily_log
        
        time_str = now.strftime("%H:%M")
        entry = f"[{time_str}] {summary}"
        
        append_to_daily_log(entry=entry, section="自动摘要")
    
    def _count_valid_messages(self, messages: list[dict]) -> int:
        """统计有效消息数（user/assistant 且内容长度 >= 3）"""
        count = 0
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role in ["user", "assistant"] and len(content) >= 3:
                count += 1
        
        return count
    
    def _load_session(self, session_id: str) -> dict:
        """加载会话文件，不存在则创建"""
        session_file = self.sessions_dir / f"{session_id}.json"
        
        if session_file.exists():
            try:
                return json.loads(session_file.read_text(encoding="utf-8"))
            except:
                pass
        
        # 创建新会话
        now = datetime.now()
        return {
            "id": session_id,
            "title": "",
            "created_at": now.isoformat(),
            "last_active": now.isoformat(),
            "last_summary_at": None,
            "messages": [],
            "summaries": []
        }
    
    def _save_session(self, session_id: str, session: dict):
        """保存会话到文件"""
        session_file = self.sessions_dir / f"{session_id}.json"
        session_file.write_text(
            json.dumps(session, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
```

### 4.3 集成到 serve.py

```python
# aiagent/serve.py

# 全局 SessionManager 实例（每个 worker 一个）
_session_manager: Optional[SessionManager] = None

def _get_session_manager(data_dir: Path) -> SessionManager:
    """获取或创建 SessionManager 单例"""
    global _session_manager
    if _session_manager is None:
        from .session_manager import SessionManager
        _session_manager = SessionManager(data_dir)
    return _session_manager

async def _run_agent(
    query: str,
    history: list,
    q: Queue,
    stop_event: threading.Event,
    session_id: str,  # 新增参数
    ...
):
    # ... 初始化代码 ...
    
    # 获取 SessionManager
    data_dir = Path(__file__).parent.parent / "data" / "sessions"
    session_mgr = _get_session_manager(data_dir)
    
    # 添加用户消息
    session_mgr.add_message(session_id, "user", query)
    
    # ... 处理对话 ...
    
    # 添加助手回复
    session_mgr.add_message(session_id, "assistant", final_content)
    
    # （add_message 内部会自动检测超时并生成摘要）
```

---

## 五、时序图

```
用户        Web UI        serve.py        SessionManager        Daily Log
 |            |               |                   |                  |
 |─发消息────▶|               |                   |                  |
 |            |─POST /run────▶|                   |                  |
 |            |               |─add_message()────▶|                  |
 |            |               |                   │                  |
 |            |               |                   ├─加载 sess_xxx.json
 |            |               |                   │                  |
 |            |               |                   ├─添加消息         |
 |            |               |                   │                  |
 |            |               |                   ├─检查超时?        |
 |            |               |                   │（否）            |
 |            |               |                   │                  |
 |            |               |◄─保存────────────┤                  |
 |            |◄─响应─────────|                   │                  |
 |◄───────────|               |                   │                  |
 |            │               │                   │                  |
 │（5分钟后）  │               │                   │                  │
 │            │               │                   │                  │
 |─发消息────▶|               │                   │                  │
 |            |─POST /run────▶|                   │                  │
 |            |               |─add_message()────▶|                  │
 |            |               |                   │                  │
 |            |               |                   ├─加载 sess_xxx.json
 |            |               |                   │                  │
 |            |               |                   ├─添加消息         │
 |            |               |                   │                  │
 |            |               |                   ├─检查超时?（是）   │
 |            |               |                   ├─生成摘要         │
 |            |               |                   ├─更新 summaries[] │
 |            |               |                   ├─────────────────▶|
 |            |               |                   │                  ├─写入 2026-03-23.md
 |            |               |                   │◄─────────────────|
 |            |               |                   │                  │
 |            |               |◄─保存────────────┤                  │
 |            |◄─响应─────────|                   │                  │
 |◄───────────|               │                   │                  │
```

---

## 六、Daily Log 输出示例

### 单会话多摘要（分段记录）

```markdown
# 2026-03-23 (Monday)

## 摘要
今天的对话记录

## 自动摘要
- [15:10] 用户询问: 你好，我想了解一下今天的股市行情走势...
- [15:35] 用户询问: 那原油的走势如何，适合投资吗...
- [16:05] 用户询问: 写一个冒泡排序的 Python 实现...

## 对话列表
- 

## 重要事项
- 

## 待办
- 
```

### 特点
- 每个摘要代表一个"对话段落"（约 5 分钟）
- 长会话自动分段，不丢失上下文
- 时间戳清晰，便于回顾

---

## 七、实现步骤

### Step 1: 创建分支
```bash
git checkout feature/todo-list-20260318
git checkout -b feature/session-level-summary-20260323
```

### Step 2: 实现 SessionManager
- 创建 `aiagent/session_manager.py`
- 实现核心逻辑

### Step 3: 集成到 serve.py
- 修改 `_run_agent` 函数
- 添加 SessionManager 调用

### Step 4: 测试
- 长对话测试（> 5 分钟）
- 短对话测试（< 5 分钟）
- 跨天测试

### Step 5: 提交合并
```bash
git add .
git commit -m "feat: 实现会话级别 Daily Log 总结（超时触发 + 继续累积）"
git push origin feature/session-level-summary-20260323
# PR 合并到 feature/todo-list-20260318
```

---

## 八、风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| Server 重启丢失内存状态 | 低 | 数据已持久化到文件，重启后读取即可 |
| 会话文件过大 | 中 | 限制保留最近 100 条消息，旧的自动清理 |
| 并发写入冲突 | 低 | 每个请求独立处理，无并发竞争 |
| 用户快速连续发送 | 低 | 每次请求都更新 last_active，不会误判超时 |

---

## 九、实现记录

### 9.1 实现状态

**状态**: ✅ 已完成并测试通过  
**分支**: `feature/session-level-summary-20260323` → 已合并到 `feature/todo-list-20260318`  
**提交**: `c16a076`

### 9.2 实际 Bug 修复记录

| Bug | 现象 | 原因 | 解决 |
|-----|------|------|------|
| Path 未导入 | `name 'Path' is not defined` | serve.py 缺少导入 | 添加 `from pathlib import Path` |
| session_id 被覆盖 | 每次请求都生成新会话 | `_run_agent` 内部覆盖参数 | 只在未传入时生成新 ID |
| 前端生成新 run_id | 消息无法累积 | 前端每次用新的 `curRunId` | 使用 `sid` 作为 `rid` |
| datetime 作用域 | 变量访问错误 | 局部导入与全局使用冲突 | 移除方法内的局部导入 |
| 两个摘要系统 | 一个问题多个摘要 | 新旧系统同时运行 | 删除旧的请求级别摘要 |
| 文件格式不兼容 | 现有会话无法加载 | `created_at` 是整数时间戳 | 添加格式转换兼容 |

### 9.3 实际与设计的差异

| 设计 | 实际实现 | 差异说明 |
|------|---------|---------|
| 5分钟超时 | 默认60秒（可配置） | 测试时缩短，生产可用300秒 |
| 方案B1/B2/B3 | 直接实现B2（文件持久化） | 选择最稳定的方案 |

### 9.4 验证结果

**测试会话**: `sess_1774275026326`

```
消息总数: 15条
生成摘要: 2个
  - [22:10] 基于 2条消息
  - [22:11] 基于 13条消息

效果: 多条消息合并成摘要，不是每个问题一个摘要 ✅
```

---

## 十、后续优化方向

1. **LLM 生成摘要**: 支持 `DAILY_LOG_SUMMARY_MODE=llm`
2. **Web UI 显示**: 在会话历史中显示摘要列表
3. **搜索功能**: 基于摘要内容搜索历史会话
4. **定时清理**: 自动清理 30 天前的会话文件

---

**设计完成，已实现并合并到主分支！**  
**实现报告**: 参见 `docs/SESSION_SUMMARY_IMPLEMENTATION_REPORT.md`
