# NAS FMS 系统集成总结与后续规划

> **实施状态**: ✅ Phase 1-4 已完成（2026-03-28）
> **测试状态**: ✅ 26次工具调用无错误，下载功能待测试
> **分支**: `feature/fms-integration-20260326`

---

## 一、当前实现总结

### 1.1 已完成功能

| 功能       | 工具                                 | 状态 | 说明                 |
| ---------- | ------------------------------------ | ---- | -------------------- |
| 文本搜文档 | `fms_retrieve(type="text2doc")`    | ✅   | 关键词搜索PDF/Word等 |
| 文本搜图片 | `fms_retrieve(type="text2image")`  | ✅   | 英文关键词效果较好   |
| 以图搜图   | `fms_retrieve(type="image2image")` | ✅   | 找到相似图片         |
| 文本搜视频 | `fms_retrieve(type="text2video")`  | ✅   | 预留支持             |
| 文档相似度 | `fms_retrieve(type="doc2doc")`     | ✅   | 找相似文档           |
| 知识库问答 | `fms_chat`                         | ✅   | 基于文档内容问答     |
| 文件列表   | `fms_list_files`                   | ✅   | 按类型筛选           |
| **文件下载** | **`fms_download`**                 | **✅** | **新增：下载NAS文件到本地** |

### 1.2 技术实现细节

**基于 FMS 接口文档的实现方式：**

```
┌─────────────────────────────────────────────────────────────┐
│                    我们的实现层                              │
├─────────────────────────────────────────────────────────────┤
│  1. aiagent/tools/fms.py                                    │
│     - _fms_request()       → 封装 aiohttp HTTP 请求         │
│     - fms_retrieve_handler() → 调用 POST /api/fms/retrieve  │
│     - fms_chat_handler()     → 调用 POST /api/fms/chat      │
│     - fms_list_files_handler() → 调用 GET /api/fms/get_knowledge_files │
├─────────────────────────────────────────────────────────────┤
│  2. aiagent/tools/__init__.py                               │
│     - 注册3个工具到工具注册表                                │
├─────────────────────────────────────────────────────────────┤
│  3. skills/system/fms/SKILL.md                              │
│     - 触发词："搜索NAS", "知识库问答" 等                      │
│     - 使用示例和场景说明                                     │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP API
┌─────────────────────────▼───────────────────────────────────┐
│                    FMS 服务端层                              │
│              172.16.50.51:8001                               │
│  - /api/fms/retrieve      → 向量检索（返回片段）             │
│  - /api/fms/chat          → RAG问答（返回生成回答）          │
│  - /api/fms/get_knowledge_files → 文件列表                   │
└─────────────────────────────────────────────────────────────┘
```

**核心设计决策：**

1. **异步 HTTP 客户端**：使用 `aiohttp` 进行异步请求，避免阻塞
2. **结构化返回**：Markdown 表格展示检索结果，易读性好
3. **参数验证**：前置校验检索类型和文件类型，提前报错
4. **阈值调整**：图片检索默认阈值从 0.5 降到 0.3，提高召回率

---

## 二、当前限制与问题

### ✅ 2.1 文件下载功能（2026-03-28 已实现）

**实现方式：**

```python
# 使用 fms_download 工具
fms_download(file_path="/data/docs/report.pdf")

# 返回：
# ✅ 文件下载成功
# 📁 NAS 路径: /data/docs/report.pdf
# 💾 本地路径: ~/Downloads/fms/report.pdf
# 📊 文件大小: 2.50 MB
```

**配合其他工具使用：**

```python
# 1. 先下载NAS文件
local_path = await fms_download_handler("/data/docs/班车路线.pdf")

# 2. 再用 pdf 工具读取
from aiagent.tools.pdf import pdf_handler
content = await pdf_handler("~/Downloads/fms/班车路线.pdf")

# 3. 或用 image 工具分析图片
from aiagent.tools.image import image_handler
analysis = await image_handler(image="~/Downloads/fms/photo.jpg")
```

**接口说明：**

| 功能         | 状态      | 接口                                      | 说明               |
| ------------ | --------- | ----------------------------------------- | ------------------ |
| 文件下载     | ✅ 已实现 | `GET /api/fms/download_file`            | 普通文件下载       |
| 流式下载     | ✅ 已实现 | `GET /api/fms/download_file/stream`     | 大文件推荐使用     |
| 完整内容获取 | ✅ 已实现 | 下载后配合 pdf/image/read 工具          | 可完整阅读文件内容 |

### ✅ 2.2 图片本地预览（2026-03-28 已解决）

**解决方案：**

```python
# 步骤1: 下载图片到本地
await fms_download_handler("/data/images/baby-2972221_1280.jpg")

# 步骤2: 用 image 工具分析
await image_handler(image="~/Downloads/fms/baby-2972221_1280.jpg")
```

**工作流程：**
```
用户: "显示NAS上的图片"
  ↓
fms_download 下载到 ~/Downloads/fms/
  ↓
image 工具分析本地文件
  ↓
展示分析结果
```

---

## 三、需要 NAS 配合的方案

### ✅ 方案 A：文件下载接口（2026-03-28 已完成）

**NAS 提供的接口：**

```yaml
# 已实现: GET /api/fms/download_file
功能: 下载NAS上的文件到本地临时目录
请求:
  method: GET
  url: /api/fms/download_file?file_path=/data/docs/file.pdf
  
响应:
  success:
    content-type: application/octet-stream
    body: 文件二进制流
  error:
    code: 404
    message: "文件不存在"
```

**我们实现的 fms_download 工具：**

```python
# aiagent/tools/fms.py 已实现

async def fms_download_handler(
    file_path: str,
    save_path: Optional[str] = None,
    use_stream: bool = False,
) -> str:
    """
    从 NAS FMS 下载文件到本地
    
    支持：
    - 普通下载：适合小文件 (< 100MB)
    - 流式下载：适合大文件 (> 100MB)，设置 use_stream=True
    - 自定义保存路径：通过 save_path 参数
    - 默认保存到：~/Downloads/fms/
    """
    # 实现细节见源码...
```

**使用示例：**

```python
# 基本使用 - 下载到默认目录
await fms_download_handler("/data/docs/班车路线.pdf")
# 返回: 文件已保存到 ~/Downloads/fms/班车路线.pdf

# 自定义保存路径
await fms_download_handler(
    file_path="/data/docs/report.pdf",
    save_path="/tmp/myreport.pdf"
)

# 大文件流式下载
await fms_download_handler(
    file_path="/data/videos/tutorial.mp4",
    use_stream=True
)
```

### 方案 B：Samba/NFS 共享挂载（系统级）

**NAS 配置：**

```bash
# NAS 开启 Samba 共享
[share]
  path = /workspace/yangxinlong/NAS_data
  read only = yes
  guest ok = yes
```

**我们这边配置：**

```bash
# 挂载到本地
mount -t cifs //172.16.50.51/share /mnt/nas -o guest

# 然后直接访问
read /mnt/nas/recall_files_test/pdf/亿道班车路线.pdf
```

**优缺点：**

| 方案         | 优点                           | 缺点                               |
| ------------ | ------------------------------ | ---------------------------------- |
| A (HTTP下载) | 简单、无需系统配置、权限控制好 | 需要NAS开发接口                    |
| B (共享挂载) | 无需开发、直接访问             | 需要系统配置、权限复杂、跨平台麻烦 |

### 方案 C：基于现有接口增强（无需NAS改动）

**利用现有 retrieve + chat 组合：**

```python
async def fms_read_document(file_path: str) -> str:
    """
    通过多次检索获取文档完整内容
    适合：无法下载时，尽可能获取更多信息
    """
    # 1. 获取文档基本信息
    list_result = await fms_list_files_handler(file_type="document")
  
    # 2. 用 doc2doc 找相似文档（可能获取更多上下文）
    similar = await fms_retrieve_handler(
        query=file_path,
        type="doc2doc",
        top_k=5
    )
  
    # 3. 用 chat 获取文档详细摘要
    summary = await fms_chat_handler(
        f"请详细总结文档 {file_path} 的全部内容"
    )
  
    return f"{summary}\n\n相似文档:\n{similar}"
```

**局限性：** 无法获取原文，只能获取片段和AI生成的摘要

---

## 四、图片处理方案

### 当前问题

```
用户想查看NAS图片 → image 工具读取本地路径失败
```

### 解决方案

**方案 A：下载后本地预览（需要下载接口）**

```python
async def fms_view_image(image_path: str):
    # 1. 下载图片到本地
    local_path = await fms_download_handler(image_path)
  
    # 2. 用 image 工具分析
    from aiagent.tools.image import image_tool
    return await image_tool.handler(image=local_path)
```

**方案 B：URL 直接显示（需要HTTP访问）**

如果NAS提供静态文件HTTP访问：

```python
# 直接返回URL让前端显示
image_url = f"http://172.16.50.51:8001/static{image_path}"
return f"![图片]({image_url})"
```

---

## 五、推荐后续行动

### 短期（无需NAS改动）

| 优先级 | 任务          | 说明                                       |
| ------ | ------------- | ------------------------------------------ |
| P0     | 合并到 master | 当前功能已稳定可用                         |
| P1     | 文档完善      | 更新使用文档，说明当前限制                 |
| P2     | 用户引导      | 告知用户目前只能获取片段，无法下载完整文件 |

### 中期（已完成）

| 优先级 | 任务     | 状态 | 说明                              |
| ------ | -------- | ---- | --------------------------------- |
| ~~P1~~ | ~~文件下载~~ | ✅ | ~~`/api/fms/download_file` 接口已实现~~ |
| P2     | 批量下载 | 待办 | 支持多文件同时下载                |
| P3     | 自动打开 | 待办 | 下载后自动用对应工具打开          |

### 新需求（可选增强）

| 优先级 | 任务     | 说明                              |
| ------ | -------- | --------------------------------- |
| P2     | 下载缓存 | 避免重复下载同一文件              |
| P3     | 断点续传 | 大文件下载中断后恢复              |

### 长期（可选增强）

- 文件同步：定期同步NAS文件到本地缓存
- 增量更新：只同步变更的文件
- 权限集成：对接NAS的权限系统

---

## 六、测试验证记录

| 测试项           | 次数         | 结果                  | 备注             |
| ---------------- | ------------ | --------------------- | ---------------- |
| text2doc 检索    | 8            | ✅ 通过               | 能找到班车文档   |
| text2image 检索  | 3            | ✅ 通过               | 英文关键词效果好 |
| image2image 检索 | 2            | ✅ 通过               | 找到3个相似图片  |
| fms_chat 问答    | 7            | ✅ 通过               | 回答准确         |
| fms_list_files   | 5            | ✅ 通过               | 正确统计7个文件  |
| 边界情况测试     | 1            | ✅ 通过               | 高阈值/错别字等  |
| **fms_download** | **待测试**   | **⏳ 新增功能**       | 需要NAS配合测试  |
| **总计**   | **26+** | **✅ 全部通过** | 等待下载功能验证 |

### 下载功能测试计划

```bash
# 测试1: 基本下载
curl "http://172.16.50.51:8001/api/fms/download_file?file_path=/data/docs/test.pdf"

# 测试2: 流式下载
curl "http://172.16.50.51:8001/api/fms/download_file/stream?file_path=/data/videos/test.mp4"

# 测试3: 通过 Agent 工具下载
# 在 Web UI 中测试：
# "下载NAS上的 /data/docs/班车路线.pdf"
```

---

## 七、相关文档

| 文档                                                                                                           | 说明              |
| -------------------------------------------------------------------------------------------------------------- | ----------------- |
| [FMS_INTEGRATION_PLAN.md](./FMS_INTEGRATION_PLAN.md)                                                              | 详细实施方案      |
| [FMS API 文档](http://172.16.50.63:10880/zengzhiyun/agentone-fms/src/feature/agentone_fms/pc/api/api_document.md) *(内网地址)* | NAS提供的接口文档 |
| skills/system/fms/SKILL.md                                                                                     | Skill 使用指南    |

---

**创建日期**: 2026-03-26
**更新日期**: 2026-03-28
**作者**: emdoor 谢建辉
**状态**: Phase 1-4 已完成，`fms_download` 工具已实现待测试
