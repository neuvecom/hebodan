"""Gemini API を使ったテーマ背景画像生成モジュール"""

import logging
import time
from io import BytesIO
from pathlib import Path

from PIL import Image
from google import genai
from google.genai import types

from src.config import (
  BG_COLOR,
  BG_GENERATION_MAX_RETRIES,
  BG_GENERATION_RETRY_BASE_WAIT,
  BG_IMAGE_MODEL,
  GEMINI_API_KEY,
  LANDSCAPE_SIZE,
  PORTRAIT_SIZE,
)

logger = logging.getLogger(__name__)


def _build_prompt(theme: str, width: int, height: int) -> str:
  """背景画像生成プロンプトを組み立てる"""
  orientation = "horizontal landscape" if width > height else "vertical portrait"
  return (
    f"Generate a background image for a YouTube video about: {theme}\n\n"
    f"Requirements:\n"
    f"- Image size: {width}x{height} pixels, {orientation} orientation\n"
    f"- Style: atmospheric, cinematic, slightly blurred/bokeh feel\n"
    f"- Color tone: dark and moody (similar to dark navy/indigo base)\n"
    f"- The bottom 20% should be especially dark for subtitle readability\n"
    f"- No text, no characters, no faces, no logos\n"
    f"- Abstract or environmental scene that evokes the theme\n"
    f"- Suitable as a background behind animated characters\n"
    f"- Not too busy or distracting - keep it subtle\n"
  )


def _generate_single(
  client: genai.Client,
  theme: str,
  width: int,
  height: int,
  output_path: Path,
) -> bool:
  """1枚の背景画像を生成して保存する"""
  prompt = _build_prompt(theme, width, height)

  for attempt in range(BG_GENERATION_MAX_RETRIES):
    try:
      response = client.models.generate_content(
        model=BG_IMAGE_MODEL,
        contents=[types.Part.from_text(text=prompt)],
        config=types.GenerateContentConfig(
          response_modalities=["IMAGE"],
        ),
      )

      for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
          img = Image.open(BytesIO(part.inline_data.data))
          img = img.convert("RGB")
          img = img.resize((width, height), Image.LANCZOS)
          output_path.parent.mkdir(parents=True, exist_ok=True)
          img.save(str(output_path), format="PNG")
          logger.info(
            "背景画像生成完了: %s (%dx%d)", output_path.name, width, height,
          )
          return True

      logger.warning(
        "背景画像が返されませんでした (試行 %d/%d)",
        attempt + 1, BG_GENERATION_MAX_RETRIES,
      )

    except Exception as e:
      logger.warning(
        "背景画像生成エラー (試行 %d/%d): %s",
        attempt + 1, BG_GENERATION_MAX_RETRIES, e,
      )
      if attempt < BG_GENERATION_MAX_RETRIES - 1:
        wait = 2 ** attempt * BG_GENERATION_RETRY_BASE_WAIT
        logger.info("%d秒後にリトライ...", wait)
        time.sleep(wait)

  return False


def generate_backgrounds(
  theme: str,
  output_dir: Path,
) -> tuple[Path | None, Path | None]:
  """テーマに合った背景画像を生成する

  Args:
    theme: 動画のテーマ（例: "AIの未来"）
    output_dir: 背景画像の保存先ディレクトリ

  Returns:
    (landscape_bg_path, portrait_bg_path) のタプル。
    生成失敗時は各要素が None になる。
  """
  if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY未設定のため背景画像生成をスキップします")
    return (None, None)

  client = genai.Client(api_key=GEMINI_API_KEY)

  landscape_path = output_dir / "bg_landscape.png"
  portrait_path = output_dir / "bg_portrait.png"

  landscape_ok = _generate_single(
    client, theme, *LANDSCAPE_SIZE, landscape_path,
  )

  # レート制限対策
  time.sleep(3)

  portrait_ok = _generate_single(
    client, theme, *PORTRAIT_SIZE, portrait_path,
  )

  return (
    landscape_path if landscape_ok else None,
    portrait_path if portrait_ok else None,
  )
