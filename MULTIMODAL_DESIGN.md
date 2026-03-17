# 多模态接入设计方案

## 一、OpenClaw多模态处理详细流程图

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    通道层 (20+ Channels)                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐                      │
│  │ Telegram │ │ WhatsApp │ │  Slack   │ │ Discord  │ │ iMessage │  ...                 │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘                      │
│       │            │            │            │            │                            │
│       └────────────┴────────────┴────────────┴────────────┘                            │
│                              │                                                          │
│                              ▼                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                        Inbound Message (带附件)                                  │   │
│  │  {                                                                               │   │
│  │    text: "用户消息",                                                             │   │
│  │    MediaPaths: ["/path/to/img1.jpg"],                                           │   │
│  │    MediaUrls: ["https://..."],                                                  │   │
│  │    MediaTypes: ["image/jpeg"]                                                   │   │
│  │  }                                                                               │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              附件标准化层 (Attachments)                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                        normalizeAttachments()                                    │   │
│  │                                                                                  │   │
│  │  输入: MsgContext {MediaPaths, MediaUrls, MediaTypes}                           │   │
│  │       │                                                                          │   │
│  │       ▼                                                                          │   │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐    │   │
│  │  │ 1. 路径标准化                                                            │    │   │
│  │  │    - file:// 协议转换                                                    │    │   │
│  │  │    - 相对路径转绝对路径                                                   │    │   │
│  │  │    - 提取文件名                                                          │    │   │
│  │  └─────────────────────────────────────────────────────────────────────────┘    │   │
│  │       │                                                                          │   │
│  │       ▼                                                                          │   │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐    │   │
│  │  │ 2. MIME类型识别                                                          │    │   │
│  │  │    - 从MediaTypes获取                                                    │    │   │
│  │  │    - 或从文件扩展名推断                                                  │    │   │
│  │  │    - 或读取文件头魔数识别                                                │    │   │
│  │  └─────────────────────────────────────────────────────────────────────────┘    │   │
│  │       │                                                                          │   │
│  │       ▼                                                                          │   │
│  │  输出: MediaAttachment[]                                                        │   │
│  │  [                                                                               │   │
│  │    { path: "/tmp/img1.jpg", url: null, mime: "image/jpeg", index: 0 },         │   │
│  │    { path: null, url: "https://...", mime: "image/png", index: 1 }              │   │
│  │  ]                                                                               │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                            附件过滤与选择层 (Select)                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                         selectAttachments()                                      │   │
│  │                                                                                  │   │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐    │   │
│  │  │ 过滤条件                                                                  │    │   │
│  │  │ ├── 类型过滤: 只处理 image/audio/video                                    │    │   │
│  │  │ ├── 大小限制: maxBytes (默认10MB图片/5MB文件)                            │    │   │
│  │  │ ├── 数量限制: maxAttachments (默认10个)                                  │    │   │
│  │  │ ├── 安全检查: SSRF防护(阻止内网IP)                                        │    │   │
│  │  │ └── 去重: 相同URL/path只保留一个                                          │    │   │
│  │  └─────────────────────────────────────────────────────────────────────────┘    │   │
│  │                                                                                  │   │
│  │  输出: 过滤后的MediaAttachment[]                                                │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           媒体缓存层 (Cache)                                             │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                      MediaAttachmentCache                                        │   │
│  │                                                                                  │   │
│  │  功能:                                                                           │   │
│  │  ├── 二进制数据缓存: 避免重复读取文件                                           │   │
│  │  ├── URL拉取缓存: 避免重复下载远程文件                                          │   │
│  │  ├── Base64编码缓存: 避免重复编码                                               │   │
│  │  └── 缓存失效: 基于文件mtime或URL ETag                                         │   │
│  │                                                                                  │   │
│  │  缓存键: `${attachment.path || attachment.url}:${mtime}`                        │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           媒体理解管道 (Media Understanding)                             │
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                        能力识别与路由                                             │   │
│  │                                                                                  │   │
│  │  resolveAttachmentKind(attachment) → "image" | "audio" | "video" | "document"   │   │
│  │                                                                                  │   │
│  │       ┌─────────────┬─────────────┬─────────────┐                               │   │
│  │       ▼             ▼             ▼             ▼                               │   │
│  │  ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐                             │   │
│  │  │ Image  │   │ Audio  │   │ Video  │   │  Doc   │                             │   │
│  │  └───┬────┘   └───┬────┘   └───┬────┘   └───┬────┘                             │   │
│  │      │            │            │            │                                   │   │
│  │      ▼            ▼            ▼            ▼                                   │   │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐   │   │
│  │  │                     执行对应理解任务                                       │   │   │
│  │  └─────────────────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐   │   │
│  │  │                         图片理解 (Vision)                                │   │   │
│  │  │                                                                          │   │   │
│  │  │  1. 图片预处理                                                           │   │   │
│  │  │     ├── 格式转换: 统一转为JPEG/PNG                                       │   │   │
│  │  │     ├── 尺寸调整: 过大图片缩放(最大4096x4096)                            │   │   │
│  │  │     └── 质量压缩: 控制文件大小在合理范围                                  │   │   │
│  │  │                                                                          │   │   │
│  │  │  2. 选择Vision模型                                                       │   │   │
│  │  │     ├── 检查配置: tools.mediaUnderstanding.imageModel                     │   │   │
│  │  │     ├── 模型选择: gpt-4o/gemini-pro-vision/claude-3-opus 等               │   │   │
│  │  │     └── 获取API Key: 从配置或环境变量                                     │   │   │
│  │  │                                                                          │   │   │
│  │  │  3. 调用Vision API                                                       │   │   │
│  │  │     ┌─────────────────────────────────────────────────────────────────┐  │   │   │
│  │  │     │ Request Body                                                    │  │   │   │
│  │  │     │ {                                                               │  │   │   │
│  │  │     │   model: "gpt-4o",                                              │  │   │   │
│  │  │     │   messages: [{                                                 │  │   │   │
│  │  │     │     role: "user",                                               │  │   │   │
│  │  │     │     content: [                                                  │  │   │   │
│  │  │     │       { type: "text", text: "描述这张图片" },                    │  │   │   │
│  │  │     │       { type: "image_url", image_url: {                         │  │   │   │
│  │  │     │         url: "data:image/jpeg;base64,/9j/4AAQ..."               │  │   │   │
│  │  │     │       }}                                                        │  │   │   │
│  │  │     │     ]                                                           │  │   │   │
│  │  │     │   }]                                                            │  │   │   │
│  │  │     │ }                                                               │  │   │   │
│  │  │     └─────────────────────────────────────────────────────────────────┘  │   │   │
│  │  │                                                                          │   │   │
│  │  │  4. 结果处理                                                             │   │   │
│  │  │     ├── 提取description文本                                            │   │   │
│  │  │     ├── 失败重试: 换模型或Provider                                       │   │   │
│  │  │     └── 缓存结果: 避免重复分析相同图片                                    │   │   │
│  │  │                                                                          │   │   │
│  │  │  输出: "图片显示一只橘色的猫坐在窗台上，阳光照在它身上..."              │   │   │
│  │  └─────────────────────────────────────────────────────────────────────────┘   │   │
│  │                                                                                  │   │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐   │   │
│  │  │                       音频转录 (Whisper)                                 │   │   │
│  │  │                                                                          │   │   │
│  │  │  1. 音频预处理                                                           │   │   │
│  │  │     ├── 格式转换: 统一转为MP3/WAV (使用ffmpeg)                           │   │   │
│  │  │     ├── 采样率: 16kHz (Whisper推荐)                                      │   │   │
│  │  │     ├── 分割处理: 长音频切分(每10分钟一段)                                │   │   │
│  │  │     └── 噪音过滤: 可选的音频增强                                         │   │   │
│  │  │                                                                          │   │   │
│  │  │  2. 选择转录服务                                                         │   │   │
│  │  │     ├── 优先级: 配置中的audioModel > 默认Whisper                         │   │   │
│  │  │     ├── 支持Provider: OpenAI/Deepgram/Groq                               │   │   │
│  │  │     └── 语言检测: 自动识别或指定语言                                     │   │   │
│  │  │                                                                          │   │   │
│  │  │  3. 调用转录API                                                          │   │   │
│  │  │     ┌─────────────────────────────────────────────────────────────────┐  │   │   │
│  │  │     │ curl https://api.openai.com/v1/audio/transcriptions \         │  │   │   │
│  │  │     │   -H "Authorization: Bearer $KEY" \                             │  │   │   │
│  │  │     │   -F file="@audio.mp3" \                                        │  │   │   │
│  │  │     │   -F model="whisper-1" \                                        │  │   │   │
│  │  │     │   -F language="zh"                                              │  │   │   │
│  │  │     └─────────────────────────────────────────────────────────────────┘  │   │   │
│  │  │                                                                          │   │   │
│  │  │  4. 后处理                                                               │   │   │
│  │  │     ├── 时间戳提取: 可选的word-level timestamp                           │   │   │
│  │  │     ├── 说话人分离: 多人对话区分(如果支持)                                │   │   │
│  │  │     └── 文本清理: 去除填充词、修正标点                                   │   │   │
│  │  │                                                                          │   │   │
│  │  │  输出: "今天的会议主要讨论了Q4的营收目标..."                             │   │   │
│  │  └─────────────────────────────────────────────────────────────────────────┘   │   │
│  │                                                                                  │   │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐   │   │
│  │  │                        视频处理                                          │   │   │
│  │  │                                                                          │   │   │
│  │  │  1. 视频解封装: 提取音频轨道 + 关键帧截图                                 │   │   │
│  │  │  2. 音频: 转文字 (同上)                                                   │   │   │
│  │  │  3. 关键帧: 图片理解 (多帧截图)                                           │   │   │
│  │  │  4. 合并: 音频文本 + 图片描述 → 完整视频描述                              │   │   │
│  │  │                                                                          │   │   │
│  │  │  输出: "视频开始是一段产品介绍，然后展示了..."                             │   │   │
│  │  └─────────────────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                           Provider Registry                                      │   │
│  │                                                                                  │   │
│  │  每个Provider实现统一的接口:                                                     │   │
│  │  - describeImage(req: ImageDescriptionRequest) => Promise<ImageDescriptionResult>│   │
│  │  - transcribeAudio(req: AudioTranscriptionRequest) => Promise<AudioTranscriptionResult>│   │
│  │  - describeVideo(req: VideoDescriptionRequest) => Promise<VideoDescriptionResult>│   │
│  │                                                                                  │   │
│  │  支持Provider: OpenAI, Anthropic, Google, Moonshot, Deepgram, Groq...           │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           结果格式化与注入层                                             │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                        formatMediaOutputs()                                      │   │
│  │                                                                                  │   │
│  │  输入: MediaUnderstandingOutput[]                                               │   │
│  │  [                                                                               │   │
│  │    { kind: "image.description", attachmentIndex: 0, text: "一只橘猫...", ... }, │   │
│  │    { kind: "audio.transcription", attachmentIndex: 1, text: "会议讨论...", ... }│   │
│  │  ]                                                                               │   │
│  │       │                                                                          │   │
│  │       ▼                                                                          │   │
│  │  格式化:                                                                         │   │
│  │  "\n\n[附件 1 - 图片]: 一只橘猫坐在窗台上...\n\n" +                              │   │
│  │  "[附件 2 - 音频转录]: 会议讨论了Q4营收目标...\n\n"                              │   │
│  │       │                                                                          │   │
│  │       ▼                                                                          │   │
│  │  与原消息合并:                                                                   │   │
│  │  finalText = originalText + formattedMediaContext                               │   │
│  │                                                                                  │   │
│  │  输出: "用户消息\n\n[附件 1 - 图片]: 一只橘猫..."                               │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              Agent输入层                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                           Agent Prompt                                           │   │
│  │                                                                                  │   │
│  │  system: "You are a helpful assistant..."                                        │   │
│  │                                                                                  │   │
│  │  user: "用户消息\n\n[附件 1 - 图片]: 一只橘猫坐在窗台上，阳光照在它身上..."    │   │
│  │                                                                                  │   │
│  │  → Agent可以"看到"图片内容并回复                                                │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、aiagent_2接入多模态的方案

### 方案对比

| 方案 | 复杂度 | 优点 | 缺点 | 适用场景 |
|------|--------|------|------|----------|
| **A: 预处理模式** (推荐) | 低 | 改动小，兼容性好 | 非真正多模态 | 快速落地 |
| **B: 真多模态模式** | 中 | 原生支持，体验好 | 需要改动Agent | 长期演进 |
| **C: 混合模式** | 高 | 兼顾两者 | 实现复杂 | 完整方案 |

---

### 方案A: 预处理模式 (推荐第一步)

**核心思想**: 在消息进入Agent前，将图片/文件预处理成文本描述

```
用户上传图片
    │
    ▼
┌─────────────────────────────────────┐
│         多模态预处理层 (新)          │
│  ┌───────────────────────────────┐  │
│  │ 1. 接收文件/图片               │  │
│  │    - Web: FormData上传         │  │
│  │    - CLI: 文件路径参数         │  │
│  └───────────────────────────────┘  │
│               │                     │
│               ▼                     │
│  ┌───────────────────────────────┐  │
│  │ 2. 类型识别与路由              │  │
│  │    图片 ──→ Vision模型        │  │
│  │    音频 ──→ Whisper           │  │
│  │    PDF  ──→ pdfminer          │  │
│  │    代码 ──→ 直接读取          │  │
│  └───────────────────────────────┘  │
│               │                     │
│               ▼                     │
│  ┌───────────────────────────────┐  │
│  │ 3. 转换为文本描述              │  │
│  │    "[图片] 一只橘猫坐在..."   │  │
│  │    "[PDF] 这是一份财报..."    │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│         Agent (无需改动)             │
│  接收到的消息已经是带描述的文本      │
│  原有Tool-Use循环完全兼容            │
└─────────────────────────────────────┘
```

#### 具体实现步骤

**Step 1: Web上传组件** (Day 1)
```html
<!-- web_ui.html 添加 -->
<div class="input-area">
  <input type="file" id="fileInput" accept="image/*,.pdf,.py,.txt" multiple hidden>
  <button onclick="document.getElementById('fileInput').click()">📎</button>
  <div id="filePreview"></div>
  <input type="text" id="textInput" placeholder="输入消息...">
  <button onclick="send()">发送</button>
</div>

<script>
document.getElementById('fileInput').onchange = (e) => {
  const files = e.target.files;
  // 显示预览
  files.forEach(file => {
    if (file.type.startsWith('image/')) {
      const img = document.createElement('img');
      img.src = URL.createObjectURL(file);
      document.getElementById('filePreview').appendChild(img);
    }
  });
};

async function send() {
  const formData = new FormData();
  formData.append('text', document.getElementById('textInput').value);
  
  const files = document.getElementById('fileInput').files;
  for (let file of files) {
    formData.append('files', file);
  }
  
  // SSE发送
  const eventSource = new EventSource('/run?' + new URLSearchParams({...}));
  // ... 原有SSE处理
}
</script>
```

**Step 2: 后端接收与处理** (Day 2-3)
```python
# serve.py 修改
async def _run_agent(query: str, files: List[UploadFile], ...):
    # 1. 处理上传的文件
    file_descriptions = []
    
    for file in files:
        content = await file.read()
        mime = file.content_type
        
        if mime.startswith('image/'):
            # 调用Vision模型
            description = await describe_image(content, mime)
            file_descriptions.append(f"[图片 {file.filename}]: {description}")
            
        elif mime == 'application/pdf':
            # 提取PDF文本
            text = extract_pdf_text(content)
            file_descriptions.append(f"[PDF {file.filename}]: {text[:2000]}...")
            
        elif mime.startswith('text/') or file.filename.endswith('.py'):
            # 文本文件直接读取
            text = content.decode('utf-8')
            file_descriptions.append(f"[文件 {file.filename}]:\n```\n{text[:3000]}\n```")
    
    # 2. 合并到用户消息
    if file_descriptions:
        enriched_query = query + "\n\n" + "\n\n".join(file_descriptions)
    else:
        enriched_query = query
    
    # 3. 原有Agent流程
    agent = Agent()
    async for event in agent.run_stream(enriched_query):
        yield event
```

**Step 3: Vision工具封装** (Day 3)
```python
# tools/vision.py (新增)
import base64

async def describe_image(image_data: bytes, mime_type: str) -> str:
    """调用Vision模型描述图片"""
    
    # Base64编码
    base64_image = base64.b64encode(image_data).decode()
    
    # 调用LLM Vision API
    client = AsyncOpenAI(...)
    response = await client.chat.completions.create(
        model="kimi-k2-0711-preview",  # 或其他Vision模型
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "详细描述这张图片的内容"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        max_tokens=1000
    )
    
    return response.choices[0].message.content
```

**Step 4: CLI支持** (Day 4)
```python
# main.py 添加
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', action='append', help='图片路径')
    parser.add_argument('--file', action='append', help='文件路径')
    args = parser.parse_args()
    
    # 预加载文件描述
    descriptions = []
    
    if args.image:
        for img_path in args.image:
            with open(img_path, 'rb') as f:
                desc = asyncio.run(describe_image(f.read(), 'image/jpeg'))
                descriptions.append(f"[图片 {img_path}]: {desc}")
    
    # 合并到第一条消息
    initial_context = "\n\n".join(descriptions) if descriptions else None
    
    # 启动对话
    chat_loop(initial_context=initial_context)
```

**优点**:
- Agent核心完全不用改
- 兼容所有现有功能
- 实现简单，1周内完成

**缺点**:
- 不是真正的多模态(Agent看不到原始图片)
- 图片描述可能丢失细节
- 无法让用户在对话中指着图片某处问问题

---

### 方案B: 真多模态模式 (长期演进)

**核心思想**: 改造Agent支持OpenAI标准的多模态消息格式

```
用户上传图片
    │
    ▼
┌─────────────────────────────────────┐
│         Agent (改造后)              │
│  messages = [                       │
│    {                                │
│      "role": "user",                │
│      "content": [                   │
│        {"type": "text", "text": "描述"},
│        {"type": "image_url", ...},  │
│      ]                              │
│    }                                │
│  ]                                  │
│       │                             │
│       ▼                             │
│  LLM.chat.completions.create(       │
│    model="gpt-4o",                  │
│    messages=messages  ← 原生支持    │
│  )                                  │
└─────────────────────────────────────┘
```

#### 改造点

**1. 消息格式改造** (agent.py)
```python
# 当前: content只能是字符串
Message = {"role": "user", "content": "文本"}

# 改造后: content可以是数组
Message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "描述"},
        {"type": "image_url", "image_url": {"url": "base64://..."}},
    ]
}
```

**2. Agent.run改造**
```python
class Agent:
    async def run(self, user_message, attachments=None):
        messages = []
        
        # 构建多模态消息
        content = [{"type": "text", "text": user_message}]
        
        if attachments:
            for att in attachments:
                if att['type'] == 'image':
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{att['mime']};base64,{att['data']}"}
                    })
        
        messages.append({"role": "user", "content": content})
        
        # 原有Tool-Use循环
        ...
```

**3. 存储改造** (历史记录)
```python
# 多模态消息需要特殊存储
{
    "timestamp": "...",
    "role": "user",
    "content": [...],  # 数组格式
    "attachments_metadata": [...]  # 附件元数据(便于展示)
}
```

**优点**:
- 真正的多模态体验
- Agent可以看到原始图片
- 支持更复杂的交互(指着某处问问题)

**缺点**:
- 需要改Agent核心
- 历史记录格式要变
- 测试工作量大

---

### 方案C: 混合模式 (最终形态)

结合A和B的优点:
- 简单场景用方案A(快速)
- 复杂场景用方案B(精准)

```python
async def handle_user_input(text, files):
    # 判断文件大小和类型
    total_size = sum(len(f['data']) for f in files)
    
    if total_size < 100KB and len(files) <= 2:
        # 小文件：直接用真多模态
        return await agent.run_with_multimodal(text, files)
    else:
        # 大文件：预处理后发送
        descriptions = await preprocess_files(files)
        return await agent.run(text + descriptions)
```

---

## 三、推荐实施路线

```
Week 1: 方案A (预处理模式)
  ├── Day 1: Web上传组件
  ├── Day 2-3: 后端文件接收+Vision调用
  ├── Day 4: CLI支持
  └── Day 5: 测试优化

Week 2: 扩展更多文件类型
  ├── PDF处理
  ├── 音频转录(Whisper)
  └── 代码文件语法高亮

Week 3+: (可选) 方案B改造
  ├── Agent消息格式改造
  ├── 历史记录改造
  └── 全面测试
```

---

## 四、关键决策点

**Q1: 是否必须真多模态？**
- 如果主要用例是"总结图片内容" → 方案A足够
- 如果需要用例是"图片里第三行代码什么意思" → 需要方案B

**Q2: 图片存储在哪？**
- 临时方案: 内存/临时文件(重启丢失)
- 长期方案: 本地存储 + 定期清理

**Q3: 大图片怎么处理？**
- 压缩: PIL/Pillow调整尺寸
- 分块: 大图切分多次分析
- 限制: 拒绝超大文件(>10MB)

**推荐**: 先做方案A快速落地，验证需求后再考虑方案B。
