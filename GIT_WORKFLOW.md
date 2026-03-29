# Git 工作流程指南

> 适用于 aiagent 项目的多人协作开发
> 
> **远程仓库**: https://github.com/homexjh/agent-assistant.git

---

## 目录

1. [日常开发流程](#一日常开发流程)
2. [协同开发模式](#二协同开发模式)
3. [分支管理规范](#三分支管理规范)
4. [版本回退指南](#四版本回退指南)
5. [常见问题解决](#五常见问题解决)
6. [命令速查表](#六命令速查表)

---

## 一、日常开发流程

### 1.1 每天开始工作（任意电脑）

```bash
# 1. 切换到 master 分支
$ git checkout master

# 2. 拉取最新代码（同步其他设备的更新）
$ git pull origin master

# 3. 创建今天的功能分支
# 命名格式：feature/功能简述-日期
$ git checkout -b feature/tts-20240316
```

### 1.2 开发过程中

```bash
# 查看修改了哪些文件
$ git status

# 添加修改到暂存区
$ git add .
# 或只添加特定文件
$ git add aiagent/agent.py

# 提交修改（写清楚做了什么）
$ git commit -m "feat: 添加语音输入功能"

# 推送到远程（备份，也便于别人查看）
$ git push -u origin 20240316-tts-zhangsan
```

**提交信息规范：**

| 前缀          | 含义      | 示例                           |
| ------------- | --------- | ------------------------------ |
| `feat:`     | 新功能    | `feat: 添加图片上传功能`     |
| `fix:`      | 修复bug   | `fix: 修复工具调用超时问题`  |
| `docs:`     | 文档更新  | `docs: 更新README使用说明`   |
| `refactor:` | 代码重构  | `refactor: 优化工具注册逻辑` |
| `test:`     | 添加测试  | `test: 添加子Agent单元测试`  |
| `chore:`    | 构建/工具 | `chore: 添加.gitignore`      |

### 1.3 完成开发，合并到 master 并推送

功能开发完成并测试通过后，合并回 master：

```bash
# 1. 切回 master
$ git checkout master

# 2. 拉取最新代码（防止另一台设备已推送更新）
$ git pull origin master

# 3. 合并你的功能分支
$ git merge feature/tts-20240316

# 4. 推送到远程 master
$ git push origin master

# 5. 删除本地功能分支
$ git branch -d feature/tts-20240316
```

**单人开发核心原则**：
- **永远不在 master 上直接开发**，所有改动走功能分支
- 换电脑前：**先合并并 `git push origin master`**
- 换电脑后：**先 `git pull origin master`**，再创建新分支
- 冲突时：手动解决后重新 `git push origin master`

---

## 二、多设备开发工作流

### 2.1 核心场景

- **电脑 A**（公司）：白天写代码 → `git push`
- **电脑 B**（家里）：晚上继续 → `git pull` → 写代码 → `git push`
- **电脑 C**（笔记本）：出差时用 → `git pull` → 写代码 → `git push`

### 2.2 新设备首次配置

```bash
# 1. 克隆仓库
git clone https://github.com/homexjh/agent-assistant.git
cd agent-assistant

# 2. 安装依赖
uv sync

# 3. 复制环境变量模板（每台电脑各自配置 API Key）
cp .env.example .env
# 然后编辑 .env，填入该设备上的 API Key
```

### 2.3 跨设备同步流程

**在电脑 A 上结束工作前：**
```bash
git add .
git commit -m "feat: xxx"
git push origin master
```

**在电脑 B 上开始工作前：**
```bash
git pull origin master
```

### 2.4 如果不同账号提交（可选）

如果你在不同电脑上使用不同的 Git 用户名/邮箱，可以在项目内单独配置（不影响全局）：

```bash
# 仅对当前仓库生效
git config user.name "你的名称"
git config user.email "你的邮箱"
```

---

## 三、分支管理规范

### 2.1 分支命名规则

```
格式：feature/功能简述-日期
      fix/问题描述-日期
      docs/文档内容-日期

示例：
- feature/tts-20240316           # 开发语音功能
- feature/image-upload-20240316  # 开发图片上传
- fix/browser-crash-20240316     # 修复浏览器崩溃
- docs/readme-update-20240316    # 更新文档
```

### 2.2 分支是否必须删除？

**情况1：功能已完成，合并到 master → 建议删除**

```bash
# 删除本地分支
$ git branch -d feature/tts-20240316

# 如果提示未合并，强制删除（确定不要了）
$ git branch -D feature/tts-20240316

# 删除远程分支（可选）
$ git push origin --delete feature/tts-20240316
```

**情况2：长期维护的分支 → 保留**

```bash
# 查看所有分支
$ git branch

# 切换到旧分支继续开发
$ git checkout 20240316-tts-zhangsan
```

**情况3：想保留做备份 → 保留**

分支不占用多少空间，可以留着不删，以后还能切回去查看。

### 2.3 查看分支

```bash
# 查看本地分支
$ git branch

# 查看远程分支
$ git branch -r

# 查看本地+远程所有分支
$ git branch -a

# 查看分支合并状态
$ git branch --merged      # 已合并到master的分支
$ git branch --no-merged   # 未合并的分支
```

---

## 四、版本回退指南

### 3.1 场景1：还没提交，想放弃当前修改

```bash
# 查看修改内容
$ git diff

# 放弃所有修改（回到上次提交状态）⚠️ 不可恢复
$ git checkout -- .

# 或只放弃某个文件
$ git checkout -- aiagent/agent.py
```

### 3.2 场景2：已提交，但想修改提交信息

```bash
# 修改最后一次提交的信息
$ git commit --amend -m "新的提交信息"

# 如果已推送到远程，需要强制推送（慎用）
$ git push --force
```

### 3.3 场景3：已提交，想回退到上次（保留修改）

```bash
# 回退到上次提交，但保留修改的文件（变成未提交状态）
$ git reset --soft HEAD~1

# 然后可以重新提交
$ git add .
$ git commit -m "新的提交信息"
```

### 3.4 场景4：已提交，彻底回退（丢弃修改）

```bash
# 回退到上次提交，丢弃所有修改 ⚠️ 危险，不可恢复
$ git reset --hard HEAD~1

# 回退到指定版本（通过 git log 查看 commit id）
$ git reset --hard 6ce9e74

# 如果已经推送到远程，需要强制推送
$ git push --force
```

### 3.5 场景5：已推送，想撤销但不删历史（推荐）

```bash
# 产生一个新的提交，撤销上次的修改（安全，历史保留）
$ git revert HEAD

# 会弹出编辑器，保存后推送到远程
$ git push
```

### 3.6 回退方式对比

| 命令              | 是否修改历史 | 是否保留修改 | 安全性 | 适用场景         |
| ----------------- | ------------ | ------------ | ------ | ---------------- |
| `checkout -- .` | 否           | 否           | 中     | 未提交时放弃修改 |
| `reset --soft`  | 是           | 是           | 高     | 重新提交         |
| `reset --hard`  | 是           | 否           | 低     | 彻底丢弃         |
| `revert`        | 否           | 否           | 高     | 已推送的回退     |

### 3.7 查看历史版本

```bash
# 查看提交历史
$ git log --oneline

# 查看详细历史（含图形）
$ git log --oneline --graph --all

# 查看某个文件的历史
$ git log --oneline aiagent/agent.py

# 查看某次提交改了什么
$ git show 6ce9e74

# 临时切换到某个历史版本查看
$ git checkout 6ce9e74
# 查看完切回master
$ git checkout master
```

---

## 五、常见问题解决

### 4.1 合并冲突（Conflict）

**冲突原因**：你和同事修改了同一个文件的同一部分。

**解决步骤**：

```bash
# 1. 合并时提示冲突
$ git merge 20240316-tts-zhangsan
# Auto-merging aiagent/agent.py
# CONFLICT (content): Merge conflict in aiagent/agent.py
# Automatic merge failed; fix conflicts and then commit the result.

# 2. 查看哪些文件冲突
$ git status

# 3. 打开冲突文件，会看到类似：
<<<<<<< HEAD
你的代码
=======
同事的代码
>>>>>>> master

# 4. 手动编辑，保留正确的，删除 <<< === >>> 这些标记

# 5. 标记冲突已解决
$ git add aiagent/agent.py

# 6. 完成合并
$ git commit -m "merge: 解决冲突，合并tts功能"

# 7. 推送
$ git push
```

### 4.2 推送被拒绝（rejected）

```bash
# 提示：! [rejected]        master -> master (fetch first)
# 原因：远程有更新，你本地不是最新的

# 解决：先拉取再推送
$ git pull
$ git push

# 如果pull也失败，加上 --rebase
$ git pull --rebase
$ git push
```

### 4.3 忘记创建分支，直接在 master 上修改了

```bash
# 1. 保存当前修改
$ git stash

# 2. 创建新分支
$ git checkout -b feature/tts-20240316

# 3. 恢复修改
$ git stash pop

# 4. 提交
$ git add .
$ git commit -m "feat: 添加语音功能"
```

### 4.4 误删了分支

```bash
# 查看操作历史（包含已删除的分支）
$ git reflog

# 找到删除前的 commit id，比如：abc1234
$ git checkout -b feature/tts-20240316 abc1234
```

### 4.5 大文件提交失败

```bash
# 如果 .subagent_registry.json 或日志文件太大
# 添加到 .gitignore（已添加则忽略）

# 从暂存区移除大文件
$ git reset HEAD 大文件名

# 重新提交
$ git add .
$ git commit -m "提交信息"
```

---

## 六、命令速查表

### 5.1 基础命令

| 命令                     | 作用                 |
| ------------------------ | -------------------- |
| `git status`           | 查看当前状态         |
| `git add .`            | 添加所有修改到暂存区 |
| `git add 文件名`       | 添加指定文件         |
| `git commit -m "信息"` | 提交修改             |
| `git push`             | 推送到远程           |
| `git pull`             | 拉取远程更新         |
| `git log --oneline`    | 查看提交历史         |

### 5.2 分支命令

| 命令                       | 作用                   |
| -------------------------- | ---------------------- |
| `git branch`             | 查看本地分支           |
| `git branch -a`          | 查看所有分支           |
| `git checkout -b 分支名` | 创建并切换到新分支     |
| `git checkout 分支名`    | 切换到已有分支         |
| `git checkout master`    | 切换到 master          |
| `git merge 分支名`       | 合并指定分支到当前分支 |
| `git branch -d 分支名`   | 删除分支               |
| `git branch -D 分支名`   | 强制删除分支           |

### 5.3 回退命令

| 命令                        | 作用                       |
| --------------------------- | -------------------------- |
| `git checkout -- .`       | 放弃未提交的修改           |
| `git reset --soft HEAD~1` | 回退到上次，保留修改       |
| `git reset --hard HEAD~1` | 回退到上次，丢弃修改 ⚠️  |
| `git revert HEAD`         | 撤销上次提交（产生新提交） |
| `git log --oneline`       | 查看历史commit id          |
| `git show commitid`       | 查看某次提交详情           |

### 5.4 其他实用命令

| 命令              | 作用                       |
| ----------------- | -------------------------- |
| `git stash`     | 临时保存修改               |
| `git stash pop` | 恢复临时保存的修改         |
| `git diff`      | 查看修改内容               |
| `git remote -v` | 查看远程仓库地址           |
| `git reflog`    | 查看操作历史（可找回分支） |

---

## 六、最佳实践

### 6.1 每天工作开始前

```bash
git checkout master
git pull
```

### 6.2 开发新功能时

```bash
git checkout -b feature/xxx-日期
# 开发...
git add .
git commit -m "feat: xxx"
git push -u origin feature/xxx-日期
```

### 6.3 完成开发后

```bash
git checkout master
git pull origin master
git merge feature/xxx-日期
git push origin master
git branch -d feature/xxx-日期
```

### 6.4 重要原则

1. **永远不在 master 上直接开发**
2. **合并前先 `git pull` 更新 master**
3. **分支名要清晰规范**
4. **提交信息要写清楚做了什么**
5. **定期删除已合并的分支，保持整洁**

---

## 附录：完整流程示例

### 示例：开发一个新功能

```bash
# 1. 开始工作
$ git checkout master
$ git pull origin master

# 2. 创建分支
$ git checkout -b feature/image-upload-20240316

# 3. 开发...
$ vim aiagent/serve.py
$ git add .
$ git commit -m "feat: Web界面支持图片上传"

# 4. 继续开发...
$ vim aiagent/serve.py
$ git add .
$ git commit -m "feat: 添加图片压缩功能"
$ git push -u origin feature/image-upload-20240316

# 5. 测试OK，合并到 master
$ git checkout master
$ git pull origin master
$ git merge feature/image-upload-20240316
$ git push origin master

# 6. 清理
$ git branch -d feature/image-upload-20240316
```

---

*最后更新：2026年3月29日（迁移至 GitHub 远程仓库）*
