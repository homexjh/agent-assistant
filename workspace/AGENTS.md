# Agents

## 何时必须使用子 Agent

以下情况**必须**使用 `sessions_spawn` 派生子 Agent，不要串行执行：

1. **同类任务 ≥ 2 个目标**：如"查询北京、上海的天气"、"用 Python 和 Go 分别实现排序"——每个目标是一个子 Agent
2. **任务可明显分解为独立模块**：各模块之间无数据依赖，可以同时进行
3. **任务预计需要 3+ 轮工具调用**：耗时较长的重型任务，交给子 Agent 后台处理

**判断原则**：只要任务里出现多个并列的、可独立完成的目标，就拆开 spawn，不要一个个串行。

## 派生子 Agent

```
sessions_spawn(task="...", label="short-name")
```

- `task`：完整的任务描述，子 Agent 将独立执行
- `label`：简短标识，便于后续 list/kill/steer
- 立即返回 `run_id`，子 Agent 在后台运行
- 子 Agent 完成后自动 announce 结果给你
- **多个子 Agent 要在同一轮同时 spawn**，不要等上一个完成再 spawn 下一个

## 管理子 Agent

```
subagents(action="list")               # 查看所有子 Agent 状态
subagents(action="kill", target="...")  # 终止（run_id 前缀或 label）
subagents(action="steer", target="...", message="...")  # 中途修正指令
```

## 跨 Session 通信

```
sessions_send(target="...", message="...")  # 向任意 Agent 发送消息
agents_list()                               # 查看所有已知 Agent
```

## 安全限制

- 最大派生深度：3 层（防止无限递归）
- 最大同时活跃子 Agent：5 个
