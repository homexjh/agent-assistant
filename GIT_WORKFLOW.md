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

### 1.1 每天开始工作

```bash
# 1. 切换到 master 分支
$ git checkout master

# 2. 拉取最新代码（获取同事的更新）
$ git pull

# 3. 创建今天的功能分支
# 命名格式：日期-功能-姓名
$ git checkout -b 20240316-tts-zhangsan
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

### 1.3 完成开发，合并到 master（推荐通过 Pull Request）

**方式一：通过 GitHub Pull Request（推荐，适合团队协作）**

```bash
# 1. 推送你的功能分支到远程
$ git push -u origin 20240316-tts-zhangsan

# 2. 打开 GitHub 仓库页面
#    https://github.com/homexjh/agent-assistant

# 3. 点击 "Compare & pull request" 创建 PR
# 4. 填写 PR 标题和描述，请求合并到 master
# 5. 由项目维护者 Review 后点击 "Merge pull request"

# 6. 合并后，本地切换到 master 并拉取最新代码
$ git checkout master
$ git pull

# 7. 删除本地分支（可选）
$ git branch -d 20240316-tts-zhangsan

# 8. 删除远程分支（可选）
$ git push origin --delete 20240316-tts-zhangsan
```

**方式二：本地直接合并（仅适合个人开发或紧急情况）**

```bash
# 1. 切回 master
$ git checkout master

# 2. 拉取最新代码（确保基于最新版本）
$ git pull

# 3. 合并你的分支
$ git merge 20240316-tts-zhangsan

# 4. 推送到远程 master
$ git push

# 5. 删除本地分支（可选）
$ git branch -d 20240316-tts-zhangsan
```

---

## 二、协同开发模式

### 2.1 直接协作（推荐给小团队）

**前提**：项目 Owner 在 GitHub 上添加你为协作者。

1. Owner 打开 https://github.com/homexjh/agent-assistant/settings/access
2. 点击 **Invite a collaborator**，输入你的 GitHub 用户名
3. 接受邀请后，即可直接推送分支和创建 PR

### 2.2 Fork 协作（推荐给外部贡献者）

1. 打开 https://github.com/homexjh/agent-assistant
2. 点击右上角 **Fork** 按钮，复制仓库到自己的账号下
3. 克隆自己的 Fork 到本地：
   ```bash
   git clone https://github.com/你的用户名/agent-assistant.git
   cd agent-assistant
   ```
4. 开发完成后，向原仓库提交 Pull Request

### 2.3 首次克隆项目

```bash
# 克隆仓库
git clone https://github.com/homexjh/agent-assistant.git
cd agent-assistant

# 安装依赖
uv sync

# 复制环境变量模板（各自配置自己的 API Key）
cp .env.example .env
```

---

## 三、分支管理规范

### 2.1 分支命名规则

```
格式：日期-功能-姓名

示例：
- 20240316-tts-zhangsan          # 张三开发语音功能
- 20240316-fix-bug-lisi          # 李四修复bug
- 20240316-docs-readme-wangwu    # 王五更新文档
- 20240316-refactor-tools-emdoor # emdoor重构工具系统
```

### 2.2 分支是否必须删除？

**情况1：功能已完成，合并到 master → 建议删除**

```bash
# 删除本地分支
$ git branch -d 20240316-tts-zhangsan

# 如果提示未合并，强制删除（确定不要了）
$ git branch -D 20240316-tts-zhangsan

# 删除远程分支（可选）
$ git push origin --delete 20240316-tts-zhangsan
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
$ git checkout -b 20240316-tts-zhangsan

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
$ git checkout -b 20240316-tts-zhangsan abc1234
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
git checkout -b 日期-功能-姓名
# 开发...
git add .
git commit -m "feat: xxx"
git push -u origin 日期-功能-姓名
```

### 6.3 完成开发后

```bash
git checkout master
git pull
git merge 日期-功能-姓名
git push
git branch -d 日期-功能-姓名  # 可选
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
$ git pull

# 2. 创建分支
$ git checkout -b 20240316-image-upload-emdoor

# 3. 开发...
$ vim aiagent/serve.py
$ git add .
$ git commit -m "feat: Web界面支持图片上传"

# 4. 继续开发...
$ vim aiagent/serve.py
$ git add .
$ git commit -m "feat: 添加图片压缩功能"
$ git push -u origin 20240316-image-upload-emdoor

# 5. 测试OK，合并
$ git checkout master
$ git pull
$ git merge 20240316-image-upload-emdoor
$ git push

# 6. 清理
$ git branch -d 20240316-image-upload-emdoor
```

---

*最后更新：2026年3月29日（迁移至 GitHub 远程仓库）*
