---
name: find-skills
description: 发现和管理 AI Agent 技能。当用户问"有什么技能"、"怎么安装技能"、"技能列表"、"找一下 XX 技能"或"怎么扩展功能"时使用。帮助用户了解已安装技能、安装新技能、理解技能分级。
---

# Find Skills - 技能发现与管理

## 概述

本 skill 帮助用户发现、安装和管理 AI Agent 的技能扩展。

## 何时使用

**触发场景：**
- 用户问"有什么技能"
- 用户问"怎么安装技能"
- 用户问"怎么扩展功能"
- 用户说"找一下 XX 技能"
- 用户想了解技能系统

## 技能系统架构

### 三级目录结构

```
skills/
├── system/     # 系统内置技能（完全信任）
├── user/       # 用户创建技能（基本信任）
└── market/     # 外部下载技能（需安全检查）
```

| 级别 | 目录 | 来源 | 说明 |
|-----|------|-----|------|
| **System** | `skills/system/` | 官方/系统内置 | 开箱即用，无需安装 |
| **User** | `skills/user/` | 用户自己创建 | 个人定制技能 |
| **Market** | `skills/market/` | 外部社区下载 | 需通过安全扫描 |

## 查看已安装技能

### 方法 1: 直接查看目录

```bash
# 查看所有已安装技能
ls skills/system/
ls skills/user/
ls skills/market/
```

### 方法 2: 查看 System Prompt

在对话开始时，系统会显示 "# Available Skills" 列表，包含：
- 技能名称
- 描述
- 路径
- 分类

## 安装新技能

### 方式 1: 从 GitHub 下载（推荐）

许多开发者在 GitHub 上分享 skill，格式为 `.skill` 文件（ZIP 压缩包）。

**步骤：**

1. **找到 skill**
   - 搜索 GitHub: `site:github.com skill-name.skill`
   - 或访问社区分享页面

2. **下载 .skill 文件**
   ```bash
   # 示例：下载某个 skill
   curl -L https://github.com/user/awesome-skill/releases/download/v1.0/awesome-skill.skill \
     -o skills/market/awesome-skill.skill
   ```

3. **解压安装**
   ```bash
   cd skills/market
   unzip awesome-skill.skill
   rm awesome-skill.skill
   ```

4. **验证安装**
   ```bash
   # 检查 SKILL.md 是否存在
   ls skills/market/awesome-skill/SKILL.md
   ```

5. **重启或刷新**
   - 新技能会自动加载

### 方式 2: 手动创建

如果要创建自己的 skill：

```bash
# 使用 skill-creator 初始化
python skills/system/skill-creator/scripts/init_skill.py my-skill --path skills/user

# 编辑 SKILL.md
# 添加 scripts/ references/ assets/ 等

# 打包（可选）
python skills/system/skill-creator/scripts/package_skill.py skills/user/my-skill
```

## 安全提示

### Market 级技能自动检查

安装在 `skills/market/` 的技能会自动进行安全检查：
- 扫描危险代码模式（`rm -rf`, `eval`, 等）
- 检查可疑网络操作

**如果检查失败，会提示风险，建议审查后再使用。**

### 手动安全检查

```bash
# 手动检查 skill 安全性
python -m aiagent.skill_security skills/market/suspicious-skill
```

## 技能推荐

### 内置技能（已安装）

| 技能 | 用途 |
|-----|------|
| research | 系统性网络研究 |
| skill-creator | 创建新技能 |
| github | GitHub 操作 |
| weather | 天气查询 |
| summarize | 内容摘要 |

### 可安装的技能类型

| 类型 | 示例 | 来源 |
|-----|------|------|
| **开发工具** | docker-helper, git-advanced | GitHub |
| **内容处理** | docx-handler, pdf-tools | GitHub |
| **数据分析** | pandas-helper, chart-gen | GitHub |
| **API 集成** | slack-bot, notion-api | GitHub |

## 故障排除

### Skill 不生效

1. **检查路径**
   - 确认 `SKILL.md` 在正确位置
   - 路径应为 `skills/{level}/{name}/SKILL.md`

2. **检查 frontmatter**
   - 必须包含 `name` 和 `description`
   - 格式：
     ```yaml
     ---
     name: skill-name
     description: What this skill does
     ---
     ```

3. **重启服务**
   - 某些更改需要重启才能生效

### 安装失败

1. **检查文件完整性**
   ```bash
   # 验证 ZIP 文件
   unzip -t skill-file.skill
   ```

2. **检查目录权限**
   ```bash
   # 确保有写入权限
   ls -la skills/market/
   ```

3. **手动安装**
   - 解压到临时目录检查
   - 确认 SKILL.md 存在且格式正确
   - 手动复制到目标目录

## 示例对话

### 示例 1: 用户想了解有什么技能

**用户**: "有什么技能可以用？"

**助手**:
```
当前已安装 13 个技能：

## System Skills (Built-in)
- research: 系统性网络研究
- skill-creator: 创建新技能
- github: GitHub 操作
- weather: 天气查询
- ...

你可以：
1. 直接使用这些技能（提及关键词即可触发）
2. 安装更多技能到 skills/market/
3. 创建自己的技能到 skills/user/
```

### 示例 2: 用户想安装新技能

**用户**: "怎么安装 docx 处理技能？"

**助手**:
```
安装 docx 技能的步骤：

1. 搜索 GitHub:
   site:github.com docx skill.skill

2. 下载到 market 目录:
   curl -L [URL] -o skills/market/docx-skill.skill

3. 解压:
   cd skills/market && unzip docx-skill.skill

4. 验证:
   python -m aiagent.skill_security skills/market/docx-skill

5. 完成后告诉我，我会帮你测试
```

### 示例 3: 用户技能不工作

**用户**: "我装了一个 skill 但是不生效"

**助手**:
```
让我帮你排查：

1. 检查路径:
   ls skills/market/your-skill/SKILL.md

2. 检查 frontmatter:
   head -10 skills/market/your-skill/SKILL.md

3. 检查扫描结果:
   python -m aiagent.skill_security skills/market/your-skill

请执行以上命令，把输出给我看看。
```
