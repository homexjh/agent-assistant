# NAS FMS 系统对接设计方案

## 系统概述

**FMS (File Management System)** - 智能文件管理系统，支持多模态检索和自动分类。

**API 地址**: `http://172.16.50.51:8001`

## FMS 核心功能

| 功能类别             | 接口                                                                | 说明                                               |
| -------------------- | ------------------------------------------------------------------- | -------------------------------------------------- |
| **智能对话**   | `POST /api/fms/chat`                                              | 基于文档上下文的问答                               |
| **文件入库**   | `POST /api/fms/ingest_file`                                       | 文件上传/索引                                      |
| **多模态检索** | `POST /api/fms/retrieve`                                          | text2doc/doc2doc/image2image/text2image/text2video |
| **任务管理**   | `POST /api/fms/{pause/resume/cancel}_task`                        | 管理入库任务                                       |
| **文件管理**   | `GET/POST /api/fms/{search_file/delete_file/get_knowledge_files}` | 文件操作                                           |

## 对接架构设计

```
用户查询
    ↓
┌─────────────────┐
│   fms Skill     │ ← 触发词："搜索NAS", "查找文件", "知识库问答"
└────────┬────────┘
         ↓
┌─────────────────────────┐
│  fms_chat (智能对话)    │ ← 自然语言问答
│  fms_retrieve (检索)    │ ← 多模态检索
│  fms_ingest (入库)      │ ← 文件入库
│  fms_task (任务管理)    │ ← 任务控制
└─────────────────────────┘
         ↓
    HTTP API
         ↓
   FMS Server
(172.16.50.51:8001)
```

## 核心封装方案

### 1. FMS Tool (底层工具)

创建 `aiagent/tools/fms.py`：

```python
"""FMS (File Management System) 工具

支持多模态文件检索和管理
"""

FMS_BASE_URL = "http://172.16.50.51:8001"

# ========== 检索工具 ==========

async def fms_retrieve(
    type: str,           # text2doc/doc2doc/image2image/text2image/text2video
    query: str,          # 查询内容（文本或文件路径）
    top_k: int = 10,     # 返回结果数
    score_threshold: float = 0.5,  # 相似度阈值
) -> str:
    """多模态检索 - 核心功能"""
    ...

async def fms_chat(
    query: str,          # 用户问题
) -> str:
    """基于知识库的智能问答"""
    ...

# ========== 文件管理 ==========

async def fms_ingest(
    paths: list[str],    # 文件/目录路径列表
) -> str:
    """文件入库（创建索引）"""
    ...

async def fms_delete(
    paths: list[str],    # 要删除的文件路径
) -> str:
    """删除知识库文件"""
    ...

async def fms_list_files(
    file_type: str = None,  # document/image/video
) -> str:
    """获取知识库文件列表"""
    ...

# ========== 任务管理 ==========

async def fms_task_control(
    action: str,         # pause/resume/cancel
    task_id: str,
    task_type: str,      # document/image/video
) -> str:
    """任务管理"""
    ...

async def fms_check_progress(
    task_id: str = None,
) -> str:
    """检查入库进度"""
    ...
```

### 2. FMS Skill (智能封装)

创建 `skills/system/fms/SKILL.md`：

```markdown
---
name: fms
description: 智能文件管理系统，支持多模态检索（文本搜文档/图片/视频、以图搜图等）
triggers:
  - "搜索NAS"
  - "查找文件"
  - "知识库问答"
  - "检索图片"
  - "以图搜图"
---

# FMS 智能文件管理

## 能力范围

1. **多模态检索**
   - 🔍 文本搜文档: "搜索关于人工智能的文档"
   - 🖼️ 文本搜图片: "找风景优美的图片"
   - 🎬 文本搜视频: "搜索产品介绍视频"
   - 🔄 以图搜图: 上传图片找相似图片
   - 📄 文档相似度: 找与某文档相似的其他文档

2. **智能问答**
   - 💬 基于知识库回答: "我们公司今年的销售目标是多少？"

3. **文件管理**
   - 📤 文件入库: 将新文件加入知识库
   - 📋 查看文件列表
   - 🗑️ 删除文件

4. **任务监控**
   - ⏸️ 暂停/恢复/取消入库任务
   - 📊 查看入库进度

## 使用示例

用户: "搜索关于机器学习的PDF文档"
→ 调用 fms_retrieve(type="text2doc", query="机器学习")

用户: "上传了 /tmp/photo.jpg，找相似的图片"
→ 调用 fms_retrieve(type="image2image", query="/tmp/photo.jpg")

用户: "把 /data/reports 目录下的文件都入库"
→ 调用 fms_ingest(paths=["/data/reports"])

用户: "知识库里有多少视频文件？"
→ 调用 fms_list_files(file_type="video")
```

## 详细接口映射

| 用户需求       | 调用工具               | FMS API                                       |
| -------------- | ---------------------- | --------------------------------------------- |
| "搜索文档"     | `fms_retrieve`       | `POST /api/fms/retrieve` (type=text2doc)    |
| "以图搜图"     | `fms_retrieve`       | `POST /api/fms/retrieve` (type=image2image) |
| "知识库问答"   | `fms_chat`           | `POST /api/fms/chat`                        |
| "文件入库"     | `fms_ingest`         | `POST /api/fms/ingest_file`                 |
| "查看入库进度" | `fms_check_progress` | `GET /api/fms/ingest_progress`              |
| "删除文件"     | `fms_delete`         | `POST /api/fms/delete_file`                 |
| "列出所有文件" | `fms_list_files`     | `GET /api/fms/get_knowledge_files`          |
| "暂停任务"     | `fms_task_control`   | `POST /api/fms/pause_task`                  |

## 技术实现要点

### 1. 错误处理

```python
# 封装 HTTP 错误为标准化错误
if response.status == 404:
    return AgentError(
        code="FMS_NOT_FOUND",
        type=ErrorType.PERMANENT,
        message="FMS服务未找到，请检查服务是否运行"
    )
elif response.status == 500:
    return AgentError(
        code="FMS_SERVER_ERROR",
        type=ErrorType.TEMPORARY,
        message="FMS服务内部错误",
        retryable=True
    )
```

### 2. 结果格式化

```python
# 检索结果格式化为表格
def format_retrieve_results(results: list) -> str:
    lines = ["| 分数 | 文件路径 | 类型 | 片段 |", "|------|----------|------|------|"]
    for r in results:
        lines.append(f"| {r['score']:.2f} | {r['file_path']} | {r['file_class']} | {r.get('doc_chunk', '')[:50]}... |")
    return "\n".join(lines)
```

### 3. 异步处理

- 入库任务异步执行，立即返回 task_id
- 提供进度查询接口
- 支持任务暂停/恢复
