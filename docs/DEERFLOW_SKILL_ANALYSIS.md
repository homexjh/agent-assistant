# DeerFlow 技能系统分析报告

> 项目: https://github.com/bytedance/deer-flow  
> 性质: ByteDance 开源的 Super Agent Harness (LangGraph + LangChain)

---

## 1. 技能系统架构对比

### 1.1 目录结构对比

**DeerFlow (字节跳动)**
```
skills/
├── public/              # 系统内置技能 (17个)
│   ├── deep-research/
│   ├── skill-creator/
│   ├── bootstrap/
│   ├── find-skills/
│   └── ...
└── custom/              # 用户安装技能
    └── (用户从市场安装)
```

**我们的项目 (AI Agent OS)**
```
skills/
├── kimi-cli-help/
├── todo/
├── memory/
└── ... (12个技能)
```

**对比分析**:
| 特性 | DeerFlow | 我们的项目 |
|-----|----------|-----------|
| 分级 | `public/` + `custom/` 两级 | 扁平结构 |
| 安全区分 | 通过目录 + 安装来源区分 | 计划中 (system/user/market) |
| 数量 | 17个内置 | 12个 |
| 技能市场 | 支持 `.skill` 包安装 | 暂无 |

---

## 2. 核心代码借鉴

### 2.1 技能加载器 (loader.py)

**DeerFlow 实现** (98行，非常简洁):
```python
def load_skills(skills_path: Path | None = None, 
                use_config: bool = True, 
                enabled_only: bool = False) -> list[Skill]:
    skills = []
    
    # 扫描 public 和 custom 目录
    for category in ["public", "custom"]:
        category_path = skills_path / category
        if not category_path.exists():
            continue

        for current_root, dir_names, file_names in os.walk(category_path):
            # 跳过隐藏目录
            dir_names[:] = sorted(name for name in dir_names 
                                  if not name.startswith("."))
            if "SKILL.md" not in file_names:
                continue

            skill_file = Path(current_root) / "SKILL.md"
            relative_path = skill_file.parent.relative_to(category_path)

            skill = parse_skill_file(skill_file, 
                                     category=category, 
                                     relative_path=relative_path)
            if skill:
                skills.append(skill)
    
    # 从配置加载 enabled 状态
    extensions_config = ExtensionsConfig.from_file()
    for skill in skills:
        skill.enabled = extensions_config.is_skill_enabled(skill.name, 
                                                           skill.category)
    return skills
```

**借鉴价值**: ⭐⭐⭐⭐⭐
- 递归扫描 + 自动分类 (public/custom)
- 配置分离: SKILL.md 与启用状态分离
- 简洁高效，仅 98 行

---

### 2.2 Skill 数据模型 (types.py)

```python
@dataclass
class Skill:
    name: str
    description: str
    license: str | None
    skill_dir: Path
    skill_file: Path
    relative_path: Path
    category: str  # 'public' or 'custom'
    enabled: bool = False

    def get_container_path(self, base: str = "/mnt/skills") -> str:
        # 返回沙箱容器内的路径
        ...
```

**借鉴价值**: ⭐⭐⭐⭐
- 区分 `category` (public/custom) 对应我们的 (system/user/market)
- 容器路径映射支持 (沙箱执行)

---

### 2.3 Frontmatter 解析 (parser.py)

**DeerFlow 实现**:
```python
def parse_skill_file(skill_file: Path, category: str, ...) -> Skill | None:
    content = skill_file.read_text(encoding="utf-8")

    # 提取 YAML front matter
    front_matter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not front_matter_match:
        return None

    front_matter = front_matter_match.group(1)

    # 简单 key-value 解析
    metadata = {}
    for line in front_matter.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()

    name = metadata.get("name")
    description = metadata.get("description")
    license_text = metadata.get("license")
    
    return Skill(...)
```

**借鉴价值**: ⭐⭐⭐
- 简单实用的 YAML 解析
- 允许可选字段 (license)

---

### 2.4 Frontmatter 验证 (validation.py)

**DeerFlow 的验证规则**:
```python
ALLOWED_FRONTMATTER_PROPERTIES = {
    "name", "description", "license", 
    "allowed-tools", "metadata", "compatibility", 
    "version", "author"
}

def _validate_skill_frontmatter(skill_dir: Path) -> tuple[bool, str, str | None]:
    # 1. 检查必填字段 (name, description)
    # 2. 检查命名规范: hyphen-case (小写字母+数字+连字符)
    # 3. 检查长度限制: name <= 64, description <= 1024
    # 4. 拒绝 angle brackets (< >) 防止 XSS
    # 5. 使用 yaml.safe_load 解析
    ...
```

**借鉴价值**: ⭐⭐⭐⭐⭐
- 允许的字段白名单
- 命名规范检查 (防止 `--`、`---` 等)
- 长度限制 (防御性编程)
- XSS 防护 (angle bracket 检查)

---

### 2.5 Skill 安装与沙箱 (skills.py 路由)

**DeerFlow 的安全安装**:
```python
def _safe_extract_skill_archive(zip_ref: zipfile.ZipFile, dest_path: Path) -> None:
    """安全的 .skill 文件解压"""
    for info in zip_ref.infolist():
        # 1. 拒绝绝对路径
        if Path(info.filename).is_absolute():
            raise HTTPException(400, "Unsafe member path")
        
        # 2. 拒绝目录穿越 (..)
        if ".." in Path(info.filename).parts:
            raise HTTPException(400, "Directory traversal")
        
        # 3. 跳过符号链接
        if _is_symlink_member(info):
            continue
        
        # 4. 限制总大小 (防 zip bomb)
        total_size += max(info.file_size, 0)
        if total_size > 512 * 1024 * 1024:  # 512MB
            raise HTTPException(400, "Too large")
```

**借鉴价值**: ⭐⭐⭐⭐⭐
- 完整的 ZIP 安全解压
- 防路径遍历、zip bomb、符号链接攻击

---

## 3. 技能设计模式借鉴

### 3.1 Skill-Creator 技能 (自举设计)

DeerFlow 有一个 `skill-creator` 技能，用于**创建和改进其他技能**！

**核心功能**:
- 引导用户创建新技能
- 自动生成测试用例 (evals)
- 并行运行对比测试 (with-skill vs without-skill)
- 评估与迭代循环
- Description 优化 (提高触发准确率)

**借鉴价值**: ⭐⭐⭐⭐⭐
- 我们可以实现类似的 `skill-creator` 技能
- 帮助用户快速创建高质量技能

---

### 3.2 渐进式加载 (Progressive Disclosure)

**DeerFlow 设计**:
```
Level 1: Metadata (name + description) - Always in context (~100 words)
Level 2: SKILL.md body - In context when skill triggers (<500 lines ideal)
Level 3: Bundled resources - As needed (scripts, references, assets)
```

**借鉴价值**: ⭐⭐⭐⭐
- 保持上下文精简
- 按需加载详细信息

---

### 3.3 Bootstrap 技能 (SOUL.md)

DeerFlow 通过对话生成用户的 `SOUL.md` (类似我们的 USER.md):

**对话阶段**:
1. Hello - 语言选择
2. You - 用户角色、痛点、AI 名称
3. Personality - AI 行为风格、自主性
4. Depth - 愿景、边界

**借鉴价值**: ⭐⭐⭐⭐
- 比我们当前的 USER.md 生成更系统
- 可以参考其对话流程

---

## 4. 可直接复用的代码

### 4.1 技能验证逻辑 (validation.py)

可以直接改造使用:
```python
ALLOWED_FRONTMATTER_PROPERTIES = {"name", "description", "license"}

def validate_skill_frontmatter(skill_dir: Path) -> tuple[bool, str]:
    # 1. 检查必填字段
    # 2. 命名规范: ^[a-z0-9-]+$ (hyphen-case)
    # 3. 长度限制
    # 4. XSS 防护
```

### 4.2 安全 ZIP 解压

可以直接复制到我们的 skill_security.py:
```python
def _safe_extract_skill_archive(zip_ref, dest_path, max_size=512*1024*1024):
    # 路径安全检查
    # 符号链接检查
    # 大小限制
```

---

## 5. 技能市场生态系统

DeerFlow 连接 https://skills.sh/ 市场:

```bash
# 发现技能
npx skills find [query]

# 安装技能
npx skills add owner/repo@skill-name
```

**借鉴价值**: ⭐⭐⭐
- 长期可以对接 skills.sh 生态
- 现在可以设计类似的 `.skill` 包格式

---

## 6. 建议复制/改造的技能

| 技能名 | DeerFlow 功能 | 我们改造建议 |
|--------|--------------|-------------|
| **skill-creator** | 创建/改进技能 | ✅ 直接借鉴，实现技能创建向导 |
| **find-skills** | 发现技能 | ✅ 适配到我们的技能系统 |
| **bootstrap** | 生成 SOUL.md | ✅ 参考改进 USER.md 生成流程 |
| **deep-research** | 深度研究 | ✅ 内容可直接参考 |

---

## 7. 技术实现差异

| 方面 | DeerFlow | 我们的项目 |
|------|----------|-----------|
| 框架 | LangGraph + LangChain | 原生 + FastAPI |
| 沙箱 | Docker 容器 | SubAgent (计划) |
| 前端 | React + Node.js | CLI 优先 |
| 配置 | YAML + JSON | YAML + Markdown |

---

## 8. 总结

### 强烈推荐借鉴:
1. **validation.py** - 完整的 frontmatter 验证
2. **loader.py** - 递归扫描 + 分类加载
3. **skill-creator** - 自举式技能创建
4. **安全 ZIP 解压** - 市场技能安装

### 可以复制的技能:
1. **skill-creator** - 帮助用户创建技能
2. **find-skills** - 技能发现助手

### 核心代码文件位置 (DeerFlow):
```
backend/packages/harness/deerflow/skills/
├── __init__.py
├── loader.py      # 技能加载
├── parser.py      # frontmatter 解析
├── types.py       # Skill 模型
└── validation.py  # 验证逻辑

skills/public/
├── skill-creator/SKILL.md   # 技能创建向导
├── bootstrap/SKILL.md       # SOUL.md 生成
├── find-skills/SKILL.md     # 技能发现
└── deep-research/SKILL.md   # 深度研究
```

---

**下一步行动建议**:
1. 复制 `validation.py` 作为我们技能安全的基础
2. 参考 `skill-creator` 设计我们的技能创建向导
3. 参考 `bootstrap` 改进 USER.md 生成流程
