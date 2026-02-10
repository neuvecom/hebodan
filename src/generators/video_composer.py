"""MoviePy を使った動画合成モジュール"""

import logging
from pathlib import Path

import numpy as np
from moviepy import (
  AudioFileClip,
  ColorClip,
  CompositeVideoClip,
  ImageClip,
  concatenate_videoclips,
)
from PIL import Image

from src.config import (
  BG_COLOR,
  FONT_PATH,
  IMAGES_DIR,
  LANDSCAPE_SIZE,
  PORTRAIT_SIZE,
  SUBTITLE_COLOR,
  SUBTITLE_FONT_SIZE,
  SUBTITLE_STROKE_COLOR,
  SUBTITLE_STROKE_WIDTH,
  VIDEO_FPS,
  CHARACTERS,
)
from src.models import DialogueLine
from src.utils.text_renderer import render_text

logger = logging.getLogger(__name__)


def _load_character_image(speaker: str, target_height: int) -> np.ndarray:
  """キャラクター画像を読み込み、指定高さにリサイズする"""
  char_config = CHARACTERS[speaker]
  img_path = IMAGES_DIR / char_config["image"]
  img = Image.open(img_path).convert("RGBA")

  # アスペクト比を維持してリサイズ
  ratio = target_height / img.height
  new_width = int(img.width * ratio)
  img = img.resize((new_width, target_height), Image.LANCZOS)

  return np.array(img)


def _apply_brightness(image_array: np.ndarray, factor: float) -> np.ndarray:
  """画像の明るさを調整する（RGBA対応）"""
  result = image_array.copy().astype(np.float32)
  # RGB チャンネルのみ明るさ調整（アルファは維持）
  result[:, :, :3] = np.clip(result[:, :, :3] * factor, 0, 255)
  return result.astype(np.uint8)


def _create_subtitle_clip(
  text: str, duration: float, max_width: int
) -> ImageClip:
  """字幕用のImageClipを生成する"""
  subtitle_array = render_text(
    text=text,
    font_path=str(FONT_PATH),
    font_size=SUBTITLE_FONT_SIZE,
    color=SUBTITLE_COLOR,
    stroke_width=SUBTITLE_STROKE_WIDTH,
    stroke_color=SUBTITLE_STROKE_COLOR,
    max_width=max_width,
  )
  return ImageClip(subtitle_array, transparent=True).with_duration(duration)


def compose_landscape(
  dialogue: list[DialogueLine],
  audio_paths: list[Path],
  output_path: Path,
) -> None:
  """16:9 横長動画を合成する

  Args:
    dialogue: セリフリスト
    audio_paths: 各セリフに対応するWAVファイルパスのリスト
    output_path: 出力先MP4パス
  """
  width, height = LANDSCAPE_SIZE
  char_height = int(height * 0.7)

  # キャラクター画像を事前読み込み
  ririn_img = _load_character_image("ririn", char_height)
  tsukuyomi_img = _load_character_image("tsukuyomi", char_height)

  clips = []

  for i, (line, audio_path) in enumerate(zip(dialogue, audio_paths)):
    audio = AudioFileClip(str(audio_path))
    duration = audio.duration

    logger.info(
      "動画合成(横) [%d/%d]: %s (%.1f秒)",
      i + 1, len(dialogue), line.text[:15], duration,
    )

    # 背景
    bg = ColorClip(size=(width, height), color=BG_COLOR).with_duration(duration)

    # アクティブスピーカー判定
    ririn_active = line.speaker == "ririn"
    tsukuyomi_active = line.speaker == "tsukuyomi"

    # リリン画像（左側配置）
    ririn_brightness = 1.0 if ririn_active else 0.5
    ririn_scale = 1.1 if ririn_active else 1.0
    ririn_array = _apply_brightness(ririn_img, ririn_brightness)
    ririn_clip = (
      ImageClip(ririn_array, transparent=True)
      .with_duration(duration)
      .resized(ririn_scale)
      .with_position(("left", "center"))
    )

    # つくよみ画像（右側配置）
    tsukuyomi_brightness = 1.0 if tsukuyomi_active else 0.5
    tsukuyomi_scale = 1.1 if tsukuyomi_active else 1.0
    tsukuyomi_array = _apply_brightness(tsukuyomi_img, tsukuyomi_brightness)
    tsukuyomi_clip = (
      ImageClip(tsukuyomi_array, transparent=True)
      .with_duration(duration)
      .resized(tsukuyomi_scale)
      .with_position(("right", "center"))
    )

    # 字幕（下部中央）
    subtitle = _create_subtitle_clip(
      line.text, duration, max_width=int(width * 0.8)
    ).with_position(("center", height - 120))

    # セリフクリップを合成
    scene = CompositeVideoClip(
      [bg, ririn_clip, tsukuyomi_clip, subtitle],
      size=(width, height),
    ).with_duration(duration).with_audio(audio)

    clips.append(scene)

  # 全セリフを結合して出力
  final = concatenate_videoclips(clips, method="compose")
  output_path.parent.mkdir(parents=True, exist_ok=True)
  final.write_videofile(
    str(output_path),
    fps=VIDEO_FPS,
    codec="libx264",
    audio_codec="aac",
    logger="bar",
  )
  final.close()
  logger.info("横長動画出力完了: %s", output_path)


def compose_portrait(
  dialogue: list[DialogueLine],
  audio_paths: list[Path],
  output_path: Path,
) -> None:
  """9:16 縦長動画を合成する

  Args:
    dialogue: セリフリスト
    audio_paths: 各セリフに対応するWAVファイルパスのリスト
    output_path: 出力先MP4パス
  """
  width, height = PORTRAIT_SIZE
  char_height = int(height * 0.3)

  # キャラクター画像を事前読み込み
  ririn_img = _load_character_image("ririn", char_height)
  tsukuyomi_img = _load_character_image("tsukuyomi", char_height)

  clips = []

  for i, (line, audio_path) in enumerate(zip(dialogue, audio_paths)):
    audio = AudioFileClip(str(audio_path))
    duration = audio.duration

    logger.info(
      "動画合成(縦) [%d/%d]: %s (%.1f秒)",
      i + 1, len(dialogue), line.text[:15], duration,
    )

    # 背景
    bg = ColorClip(size=(width, height), color=BG_COLOR).with_duration(duration)

    # アクティブスピーカー判定
    ririn_active = line.speaker == "ririn"
    tsukuyomi_active = line.speaker == "tsukuyomi"

    # リリン画像（上部配置）
    ririn_brightness = 1.0 if ririn_active else 0.5
    ririn_scale = 1.1 if ririn_active else 1.0
    ririn_array = _apply_brightness(ririn_img, ririn_brightness)
    ririn_clip = (
      ImageClip(ririn_array, transparent=True)
      .with_duration(duration)
      .resized(ririn_scale)
      .with_position(("center", int(height * 0.05)))
    )

    # つくよみ画像（下部配置）
    tsukuyomi_brightness = 1.0 if tsukuyomi_active else 0.5
    tsukuyomi_scale = 1.1 if tsukuyomi_active else 1.0
    tsukuyomi_array = _apply_brightness(tsukuyomi_img, tsukuyomi_brightness)
    tsukuyomi_clip = (
      ImageClip(tsukuyomi_array, transparent=True)
      .with_duration(duration)
      .resized(tsukuyomi_scale)
      .with_position(("center", int(height * 0.55)))
    )

    # 字幕（中間エリア）
    subtitle = _create_subtitle_clip(
      line.text, duration, max_width=int(width * 0.9)
    ).with_position(("center", int(height * 0.42)))

    # セリフクリップを合成
    scene = CompositeVideoClip(
      [bg, ririn_clip, tsukuyomi_clip, subtitle],
      size=(width, height),
    ).with_duration(duration).with_audio(audio)

    clips.append(scene)

  # 全セリフを結合して出力
  final = concatenate_videoclips(clips, method="compose")
  output_path.parent.mkdir(parents=True, exist_ok=True)
  final.write_videofile(
    str(output_path),
    fps=VIDEO_FPS,
    codec="libx264",
    audio_codec="aac",
    logger="bar",
  )
  final.close()
  logger.info("縦長動画出力完了: %s", output_path)
