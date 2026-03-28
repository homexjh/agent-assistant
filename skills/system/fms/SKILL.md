---
name: nas-fms
description: NAS智能文件管理系统，支持多模态检索、知识库问答和文件下载
triggers:
  - "搜索NAS"
  - "NAS上"
  - "知识库"
  - "查找文件"
  - "以图搜图"
  - "搜索图片"
  - "搜索视频"
  - "公司文档"
  - "下载NAS文件"
  - "打开NAS文件"
  - "查看NAS图片"
---

# NAS FMS 智能文件管理

## 功能概述

连接 NAS 上的 FMS (File Management System) 文件管理系统，实现：
- 🔍 **多模态文件检索**：用关键词搜索文档、图片、视频
- 🖼️ **以图搜图**：上传图片找相似图片
- 💬 **知识库问答**：基于公司内部文档智能问答
- 📋 **文件列表**：查看知识库中所有文件
- ⬇️ **文件下载**：将 NAS 文件下载到本地，支持用 pdf/image 工具打开

## 触发场景

| 用户意图 | 示例 | 调用工具 |
|----------|------|----------|
| 搜索文档 | "搜索NAS上关于班车的文档" | `fms_retrieve(type="text2doc")` |
| 搜索图片 | "找风景优美的图片" | `fms_retrieve(type="text2image")` |
| 以图搜图 | "用这张图片找相似的" | `fms_retrieve(type="image2image")` |
| 搜索视频 | "搜索产品介绍视频" | `fms_retrieve(type="text2video")` |
| 知识问答 | "公司班车有哪些路线" | `fms_chat` |
| 查看文件 | "NAS里有多少文件" | `fms_list_files` |
| 下载文件 | "下载NAS上的班车文档" | `fms_download` |
| 打开文件 | "打开NAS上的report.pdf" | `fms_download` + pdf/read |

## 使用示例

### 示例 1：文档搜索
用户："搜索NAS上关于人工智能的文档"

思考过程：
1. 用户提到 "NAS" 和 "搜索文档"
2. 使用 `fms_retrieve` 工具
3. type="text2doc"（文本搜文档）
4. query="人工智能"

工具调用：
```json
{
  "tool": "fms_retrieve",
  "arguments": {
    "type": "text2doc",
    "query": "人工智能",
    "top_k": 10
  }
}
```

### 示例 2：知识库问答
用户："介绍一下公司的班车路线"

思考过程：
1. 用户询问公司内部信息
2. 这是知识库问答场景
3. 使用 `fms_chat` 工具

工具调用：
```json
{
  "tool": "fms_chat",
  "arguments": {
    "query": "介绍一下公司的班车路线"
  }
}
```

### 示例 3：图片搜索
用户："找关于风景的图片"

工具调用：
```json
{
  "tool": "fms_retrieve",
  "arguments": {
    "type": "text2image",
    "query": "风景",
    "top_k": 10
  }
}
```

### 示例 4：查看文件列表
用户："知识库里有哪些文档？"

工具调用：
```json
{
  "tool": "fms_list_files",
  "arguments": {
    "file_type": "document"
  }
}
```

### 示例 5：下载并打开文件
用户："打开NAS上的 /data/docs/班车路线.pdf"

思考过程：
1. 用户要求打开 NAS 上的文件
2. 首先使用 `fms_download` 下载到本地
3. 然后用 `pdf` 工具读取内容

步骤1 - 下载：
```json
{
  "tool": "fms_download",
  "arguments": {
    "file_path": "/data/docs/班车路线.pdf"
  }
}
```

步骤2 - 读取（下载成功后）：
```json
{
  "tool": "pdf",
  "arguments": {
    "pdf": "~/Downloads/fms/班车路线.pdf"
  }
}
```

### 示例 6：下载并查看图片
用户："显示NAS上的 /data/images/风景.jpg"

步骤1 - 下载：
```json
{
  "tool": "fms_download",
  "arguments": {
    "file_path": "/data/images/风景.jpg"
  }
}
```

步骤2 - 分析图片（下载成功后）：
```json
{
  "tool": "image",
  "arguments": {
    "image": "~/Downloads/fms/风景.jpg"
  }
}
```

## 注意事项

1. **路径格式**：以图搜图时需要提供 NAS 上的完整路径，如 `/workspace/.../photo.jpg`
2. **检索类型选择**：
   - 文本关键词 → `text2doc` / `text2image` / `text2video`
   - 已有文件找相似 → `doc2doc` / `image2image`
3. **结果解读**：相似度分数越接近 1 越相关，低于 0.5 的结果可信度较低

## 相关工具

- `fms_retrieve` - 多模态检索（核心工具）
- `fms_chat` - 知识库问答
- `fms_list_files` - 获取文件列表
- `fms_download` - 下载文件到本地（支持配合 pdf/image/read 使用）

## 文件下载使用指南

### 何时使用 fms_download
- 用户说"打开/查看/阅读 NAS 上的文件"
- 需要配合 pdf、image、read 等工具处理 NAS 文件时
- 需要先下载到本地才能进行后续操作

### 文件保存位置
- 默认：`~/Downloads/fms/`（保留原始文件名）
- 自定义：通过 `save_path` 参数指定完整路径

### 完整工作流程
```
用户: "打开NAS上的文档.pdf"
  ↓
调用 fms_download(file_path="/data/docs/文档.pdf")
  ↓
获取本地路径: ~/Downloads/fms/文档.pdf
  ↓
根据文件类型选择工具:
  - PDF → pdf 工具
  - 图片 → image 工具
  - 文本 → read 工具
  ↓
展示内容给用户
```
