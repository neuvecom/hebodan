"""PIL を使った日本語テキスト描画ユーティリティ"""

import textwrap

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def render_text(
  text: str,
  font_path: str,
  font_size: int = 48,
  color: tuple[int, int, int] = (255, 255, 255),
  stroke_width: int = 2,
  stroke_color: tuple[int, int, int] = (0, 0, 0),
  max_width: int = 0,
  chars_per_line: int = 20,
) -> np.ndarray:
  """日本語テキストを描画してnumpy配列（RGBA）を返す

  MoviePy の ImageClip で直接使用可能な形式で出力する。

  Args:
    text: 描画するテキスト
    font_path: フォントファイルのパス
    font_size: フォントサイズ
    color: テキスト色 (R, G, B)
    stroke_width: 縁取りの太さ
    stroke_color: 縁取り色 (R, G, B)
    max_width: 最大幅（ピクセル）。0の場合はchars_per_lineで折り返し
    chars_per_line: 1行あたりの最大文字数

  Returns:
    RGBA形式のnumpy配列
  """
  font = ImageFont.truetype(str(font_path), font_size)

  # テキスト折り返し
  if max_width > 0:
    # ピクセル幅ベースの折り返し
    lines = _wrap_text_by_width(text, font, max_width - stroke_width * 2)
  else:
    lines = textwrap.wrap(text, width=chars_per_line)

  if not lines:
    lines = [text]

  # テキスト全体のサイズを計算
  line_bboxes = [font.getbbox(line) for line in lines]
  line_heights = [bbox[3] - bbox[1] for bbox in line_bboxes]
  line_widths = [bbox[2] - bbox[0] for bbox in line_bboxes]

  line_spacing = int(font_size * 0.3)
  total_height = sum(line_heights) + line_spacing * (len(lines) - 1)
  total_width = max(line_widths)

  # 縁取り + bbox オフセット分のパディングを追加
  # getbbox の top (bbox[1]) が正の値だと、描画位置から下にずれるため
  # その分を下部パディングに加算しないとグリフの下端が切れる
  max_top_offset = max(bbox[1] for bbox in line_bboxes)
  padding = stroke_width * 2
  bottom_extra = max(0, max_top_offset)
  img_width = total_width + padding * 2
  img_height = total_height + padding * 2 + bottom_extra

  # 透明背景で描画
  img = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
  draw = ImageDraw.Draw(img)

  y_offset = padding
  for i, line in enumerate(lines):
    # 中央揃え
    x_offset = (img_width - line_widths[i]) // 2
    draw.text(
      (x_offset, y_offset),
      line,
      font=font,
      fill=(*color, 255),
      stroke_width=stroke_width,
      stroke_fill=(*stroke_color, 255),
    )
    y_offset += line_heights[i] + line_spacing

  return np.array(img)


def _wrap_text_by_width(
  text: str, font: ImageFont.FreeTypeFont, max_width: int
) -> list[str]:
  """ピクセル幅ベースでテキストを折り返す（\\n による明示的改行に対応）"""
  lines = []

  # まず明示的な改行で分割し、各セグメントをピクセル幅で折り返す
  for segment in text.split("\n"):
    current_line = ""
    for char in segment:
      test_line = current_line + char
      bbox = font.getbbox(test_line)
      width = bbox[2] - bbox[0]

      if width > max_width and current_line:
        lines.append(current_line)
        current_line = char
      else:
        current_line = test_line

    lines.append(current_line)

  return lines
