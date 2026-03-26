# NAS FMS 系统集成总结与后续规划

> **实施状态**: ✅ Phase 1-3 已完成（2026-03-26）
> **测试状态**: ✅ 26次工具调用无错误
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

### 2.1 无法直接阅读文件内容

**问题描述：**

```
用户: "打开并阅读 /workspace/.../亿道班车路线.pdf"
当前: Error [FILE_NOT_FOUND]: File not found
原因: 文件在NAS服务器上，不在本地文件系统
```

**FMS 接口文档未提供的功能：**

| 功能         | 是否支持      | 说明                                   |
| ------------ | ------------- | -------------------------------------- |
| 文件下载     | ❌ 不支持     | 无 `/api/fms/download` 接口          |
| 文件预览     | ❌ 不支持     | 无文件内容流式传输                     |
| 完整内容获取 | ⚠️ 部分支持 | retrieve 只返回片段，chat 返回生成摘要 |

### 2.2 图片无法本地预览

**问题描述：**

```
用户: "显示NAS上的 baby-2972221_1280.jpg"
当前: Error [FILE_NOT_FOUND]: File not found
原因: image 工具只能读取本地路径，无法读取NAS路径
```

---

## 三、需要 NAS 配合的方案

### 方案 A：添加文件下载接口（推荐）

**NAS 需要提供的接口：**

```yaml
# 新增接口: GET /api/fms/download
功能: 下载NAS上的文件到本地临时目录
请求:
  method: GET
  url: /api/fms/download?path=/workspace/.../file.pdf
  
响应:
  success:
    content-type: application/octet-stream
    body: 文件二进制流
  error:
    code: 404
    message: "文件不存在"
```

**我们这边实现：**

```python
# aiagent/tools/fms.py 新增

async def fms_download_handler(file_path: str, save_dir: str = "/tmp/fms") -> str:
    """
    从NAS下载文件到本地临时目录
  
    流程:
    1. 调用 GET /api/fms/download?path={file_path}
    2. 保存到本地 /tmp/fms/{filename}
    3. 返回本地路径，供其他工具使用
    """
    import aiohttp
    import os
  
    url = f"{FMS_BASE_URL}/api/fms/download"
  
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params={"path": file_path}) as resp:
            if resp.status != 200:
                return f"Error: 下载失败 {resp.status}"
          
            # 保存到本地
            filename = os.path.basename(file_path)
            local_path = os.path.join(save_dir, filename)
            os.makedirs(save_dir, exist_ok=True)
          
            with open(local_path, 'wb') as f:
                f.write(await resp.read())
          
            return f"文件已下载: {local_path}"


# 使用流程
async def read_nas_file(file_path: str):
    # 1. 先下载到本地
    local_path = await fms_download_handler(file_path)
  
    # 2. 再用现有工具读取
    from aiagent.tools.file import read_file_handler
    return await read_file_handler(local_path)
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

### 中期（需要NAS配合）

| 优先级 | 任务     | 需要NAS提供                | 我们实现              |
| ------ | -------- | -------------------------- | --------------------- |
| P1     | 文件下载 | `/api/fms/download` 接口 | `fms_download` 工具 |
| P2     | 文件预览 | 文件流式传输或静态HTTP访问 | 本地缓存 + 预览       |
| P3     | 批量下载 | 支持多文件下载             | 批量处理工具          |

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
| **总计**   | **26** | **✅ 全部通过** | 无错误           |

---

## 七、相关文档

| 文档                                                                                                           | 说明              |
| -------------------------------------------------------------------------------------------------------------- | ----------------- |
| [FMS_INTEGRATION_PLAN.md](./FMS_INTEGRATION_PLAN.md)                                                              | 详细实施方案      |
| [FMS API 文档](http://172.16.50.63:10880/zengzhiyun/agentone-fms/src/feature/agentone_fms/pc/api/api_document.md) | NAS提供的接口文档 |
| skills/system/fms/SKILL.md                                                                                     | Skill 使用指南    |

---

**创建日期**: 2026-03-26
**作者**: emdoor 谢建辉
**状态**: Phase 1-3 已完成，待NAS配合实现文件下载
