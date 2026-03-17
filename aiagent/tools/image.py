"""
image 工具：用 LLM 视觉能力分析本地图片或图片 URL

支持：
  - 本地文件路径（自动转 base64）
  - http/https URL（直接传给 LLM）
  - data: URL（直接传）
  - 多张图片（images 参数）
"""
from __future__ import annotations
import base64
import mimetypes
import os
import urllib.request
from .types import RegisteredTool, ToolDefinition

_SUPPORTED_MIME = {"image/jpeg", "image/png", "image/gif", "image/webp"}


def _load_image_url(path_or_url: str) -> tuple[str, str]:
    """
    返回 (url_or_data_uri, media_type)
    本地文件 → base64 data URI
    http/data URL → 原样返回
    """
    p = path_or_url.strip()
    if p.startswith("data:"):
        mime = p.split(";")[0].split(":")[1]
        return p, mime

    if p.startswith("http://") or p.startswith("https://"):
        # 猜 mime
        mime, _ = mimetypes.guess_type(p)
        return p, mime or "image/jpeg"

    # 本地文件
    expanded = os.path.expanduser(p)
    if not os.path.exists(expanded):
        raise FileNotFoundError(f"Image file not found: {expanded!r}")

    mime, _ = mimetypes.guess_type(expanded)
    mime = mime or "image/jpeg"
    if mime not in _SUPPORTED_MIME:
        raise ValueError(f"Unsupported image type: {mime}")

    with open(expanded, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{data}", mime


async def _image_handler(
    prompt: str = "Describe the image.",
    image: str | None = None,
    images: list[str] | None = None,
) -> str:
    """分析一张或多张图片，返回 LLM 的分析结果。"""
    # 收集所有图片
    paths: list[str] = []
    if image:
        paths.append(image)
    if images:
        paths.extend(images)
    if not paths:
        return "Error: must provide 'image' or 'images' parameter."
    if len(paths) > 20:
        return "Error: too many images (max 20)."

    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.moonshot.cn/v1")
    model = os.getenv("MODEL", "kimi-k2-0711-preview")
    is_moonshot = "moonshot" in base_url or "kimi" in base_url.lower()

    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    # 构建 content
    content: list[dict] = [{"type": "text", "text": prompt}]
    for p in paths:
        try:
            url_or_data, mime = _load_image_url(p)
        except Exception as e:
            return f"Error loading image {p!r}: {e}"

        if url_or_data.startswith("data:") and is_moonshot:
            # kimi 不支持 base64 inline，需要先上传文件
            try:
                raw_path = os.path.expanduser(p.strip())
                with open(raw_path, "rb") as f:
                    fname = os.path.basename(raw_path)
                    upload_resp = await client.files.create(
                        file=(fname, f, mime),
                        purpose="vision",
                    )
                file_id = upload_resp.id
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"moonshot://{file_id}"},
                })
            except Exception as e:
                return f"Error uploading image to moonshot {p!r}: {e}"
        elif url_or_data.startswith("data:"):
            # 标准 OpenAI base64
            data_part = url_or_data.split(",", 1)[1]
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{data_part}"},
            })
        else:
            # http/https URL
            content.append({
                "type": "image_url",
                "image_url": {"url": url_or_data},
            })

    # 调用 LLM
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": content}],  # type: ignore
            max_tokens=2048,
        )
        return response.choices[0].message.content or "(empty response)"
    except Exception as e:
        return f"Error calling LLM for image analysis: {e}"


image_tool = RegisteredTool(
    definition=ToolDefinition(
        type="function",
        function={
            "name": "image",
            "description": (
                "Analyze one or more images using the configured vision model. "
                "Supports local file paths, http/https URLs, or data URIs. "
                "Use 'image' for a single image or 'images' for multiple (max 20)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Instruction for image analysis. Default: 'Describe the image.'",
                    },
                    "image": {
                        "type": "string",
                        "description": "Single image: local file path or URL.",
                    },
                    "images": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Multiple images: list of local paths or URLs (max 20).",
                    },
                },
                "required": [],
            },
        },
    ),
    handler=_image_handler,  # type: ignore[arg-type]
)
