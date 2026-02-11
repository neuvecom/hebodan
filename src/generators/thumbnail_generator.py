"""YouTube サムネイル自動生成モジュール"""

import logging
import re
from pathlib import Path

import numpy as np
from PIL import Image

from src.config import BG_COLOR, DIALOGUE_LOGO_PATH, FONT_PATH
from src.utils.text_renderer import render_text

logger = logging.getLogger(__name__)

THUMBNAIL_SIZE = (1280, 720)

# タイトルから【...】を除去するパターン
_BRACKET_PATTERN = re.compile(r'【[^】]*】\s*')


def generate_thumbnail(
  title: str,
  output_path: Path,
  bg_image_path: Path | None = None,
) -> Path:
  """YouTube用サムネイル画像を生成する

  Args:
    title: 動画タイトル
    output_path: 出力先PNGパス
    bg_image_path: 背景画像パス（Noneの場合はソリッドカラー）

  Returns:
    生成されたサムネイルのパス
  """
  width, height = THUMBNAIL_SIZE

  # 1) 背景
  if bg_image_path and bg_image_path.exists():
    canvas = Image.open(bg_image_path).convert("RGBA")
    canvas = canvas.resize((width, height), Image.LANCZOS)
  else:
    canvas = Image.new("RGBA", (width, height), (*BG_COLOR, 255))

  # 2) ロゴ（中央上部に大きく配置）
  if DIALOGUE_LOGO_PATH.exists():
    logo = Image.open(DIALOGUE_LOGO_PATH).convert("RGBA")
    logo_h = int(height * 0.55)
    logo_aspect = logo.width / logo.height
    logo_w = int(logo_h * logo_aspect)
    logo = logo.resize((logo_w, logo_h), Image.LANCZOS)
    logo_x = (width - logo_w) // 2
    logo_y = int(height * 0.05)
    canvas.paste(logo, (logo_x, logo_y), logo)

  # 3) タイトルテキスト（下部に配置、【...】は除去）
  display_title = _BRACKET_PATTERN.sub('', title).strip()
  if display_title:
    title_array = render_text(
      text=display_title,
      font_path=str(FONT_PATH),
      font_size=64,
      color=(255, 255, 255),
      stroke_width=4,
      stroke_color=(0, 0, 0),
      max_width=int(width * 0.90),
    )
    title_img = Image.fromarray(title_array)
    title_w, title_h = title_img.size
    title_x = (width - title_w) // 2
    title_y = height - title_h - int(height * 0.05)
    canvas.paste(title_img, (title_x, title_y), title_img)

  # 4) PNG保存
  output_path.parent.mkdir(parents=True, exist_ok=True)
  canvas.convert("RGB").save(str(output_path), format="PNG")
  logger.info("サムネイル生成完了: %s (%dx%d)", output_path.name, width, height)
  return output_path
