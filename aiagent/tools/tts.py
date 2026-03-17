"""
tts 工具：文字转语音

优先级：
  1. OpenAI TTS API（有 API Key 时）
  2. macOS say 命令（macOS 原生，零依赖）
  3. 报错提示
"""
from __future__ import annotations
import os
import subprocess
import tempfile
from .types import RegisteredTool, ToolDefinition

_OPENAI_VOICES = {"alloy", "echo", "fable", "onyx", "nova", "shimmer", "ash", "coral"}
_DEFAULT_VOICE_OPENAI = "alloy"
_DEFAULT_VOICE_SAY = "Samantha"  # macOS 默认中英文都好用


async def _tts_openai(text: str, voice: str, model: str, output_path: str) -> str:
    """调用 OpenAI TTS API 生成音频文件。"""
    from openai import AsyncOpenAI
    client = AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY", ""),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )
    response = await client.audio.speech.create(
        model=model,
        voice=voice,  # type: ignore
        input=text,
    )
    response.stream_to_file(output_path)
    return output_path


def _tts_say(text: str, voice: str, output_path: str | None) -> str:
    """使用 macOS say 命令播放或保存语音。"""
    cmd = ["say", "-v", voice]
    if output_path:
        # say -o <file>  自动根据扩展名判断格式（.aiff/.m4a 等）
        cmd += ["-o", output_path]
    cmd.append(text)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "say command failed")
    return output_path or "(played directly)"


async def _tts_handler(
    text: str,
    voice: str | None = None,
    provider: str = "auto",
    output: str | None = None,
    play: bool = True,
) -> str:
    """
    将文本转为语音。

    provider:
      - "auto"：有 OpenAI Key 且 base_url 为 openai 时用 OpenAI，否则用 say
      - "openai"：强制用 OpenAI TTS
      - "say"：强制用 macOS say
    """
    if not text.strip():
        return "Error: text is empty."

    # 自动选择 provider
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL", "")
    use_openai = (
        provider == "openai"
        or (
            provider == "auto"
            and api_key
            and "openai.com" in base_url
        )
    )
    use_say = provider == "say" or (provider == "auto" and not use_openai)

    # 确定输出路径
    out_path = output
    if out_path is None and use_openai:
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()
        out_path = tmp.name

    if use_openai:
        v = voice or _DEFAULT_VOICE_OPENAI
        if v not in _OPENAI_VOICES:
            return f"Error: invalid OpenAI voice '{v}'. Valid: {sorted(_OPENAI_VOICES)}"
        model = "tts-1"
        try:
            saved = await _tts_openai(text, v, model, out_path)
            msg = f"TTS (OpenAI/{v}): audio saved to {saved}"
            if play:
                subprocess.run(["afplay", saved], check=False)
                msg += " and played."
            return msg
        except Exception as e:
            return f"Error using OpenAI TTS: {e}"

    if use_say:
        v = voice or _DEFAULT_VOICE_SAY
        try:
            result = _tts_say(text, v, out_path)
            if out_path:
                return f"TTS (say/{v}): audio saved to {result}"
            return f"TTS (say/{v}): played directly."
        except FileNotFoundError:
            return "Error: 'say' command not found. Only available on macOS."
        except Exception as e:
            return f"Error using say: {e}"

    return "Error: no TTS provider available."


tts_tool = RegisteredTool(
    definition=ToolDefinition(
        type="function",
        function={
            "name": "tts",
            "description": (
                "Convert text to speech. "
                "On macOS uses the built-in 'say' command (no API key needed). "
                "Can also use OpenAI TTS API when configured with openai.com base URL. "
                "Optionally saves the audio to a file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to convert to speech.",
                    },
                    "voice": {
                        "type": "string",
                        "description": (
                            "Voice name. For say: macOS voice name (e.g. 'Samantha', 'Ting-Ting'). "
                            "For OpenAI: alloy/echo/fable/onyx/nova/shimmer/ash/coral."
                        ),
                    },
                    "provider": {
                        "type": "string",
                        "enum": ["auto", "openai", "say"],
                        "description": "TTS provider. Default: 'auto'.",
                    },
                    "output": {
                        "type": "string",
                        "description": "Optional: save audio to this file path.",
                    },
                    "play": {
                        "type": "boolean",
                        "description": "Whether to play audio immediately (macOS only, default true).",
                    },
                },
                "required": ["text"],
            },
        },
    ),
    handler=_tts_handler,  # type: ignore[arg-type]
)
