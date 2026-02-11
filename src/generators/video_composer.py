"""MoviePy を使った動画合成モジュール（口パク・表情対応）"""

import logging
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
  AudioFileClip,
  ColorClip,
  CompositeAudioClip,
  CompositeVideoClip,
  ImageClip,
  VideoClip,
  concatenate_videoclips,
)

from src.config import (
  BG_COLOR,
  DIALOGUE_LOGO_PATH,
  FONT_PATH,
  IMAGES_DIR,
  LANDSCAPE_SIZE,
  LIPSYNC_MIN_OPEN_FRAMES,
  LIPSYNC_THRESHOLD,
  OPENING_BG_COLOR,
  OPENING_DURATION,
  OPENING_LOGO_PATH,
  OPENING_SE_PATH,
  OPENING_TITLE_COLOR,
  OPENING_TITLE_FONT_SIZE,
  OPENING_TITLE_STROKE_COLOR,
  OPENING_TITLE_STROKE_WIDTH,
  OPENING_VOICE_MEGANE_PATH,
  OPENING_VOICE_TSUNO_PATH,
  PORTRAIT_SIZE,
  SUBTITLE_COLOR,
  SUBTITLE_FONT_SIZE,
  SUBTITLE_STROKE_COLOR,
  SUBTITLE_STROKE_WIDTH,
  VIDEO_FPS,
)
from src.models import DialogueLine
from src.utils.audio_analyzer import analyze_mouth_states
from src.utils.character_assets import CharacterFrames, load_character_assets
from src.utils.reading_annotations import remove_reading_annotations, unwrap_display_only
from src.utils.text_renderer import render_text

logger = logging.getLogger(__name__)


def _create_background_clip(
  bg_image_path: Path | None,
  size: tuple[int, int],
  duration: float,
) -> ImageClip | ColorClip:
  """背景クリップを生成する（画像があれば使用、なければソリッドカラー）"""
  if bg_image_path and bg_image_path.exists():
    img = Image.open(bg_image_path).convert("RGB")
    img = img.resize(size, Image.LANCZOS)
    return ImageClip(np.array(img)).with_duration(duration)
  return ColorClip(size=size, color=BG_COLOR).with_duration(duration)


def _create_opening_clip(
  title: str,
  size: tuple[int, int],
) -> CompositeVideoClip:
  """オープニングクリップを生成する（ロゴズーム＋タイトル＋SE＋ボイス）

  Args:
    title: エピソードタイトル
    size: 動画サイズ (width, height)
  """
  width, height = size
  duration = OPENING_DURATION

  # --- ロゴ画像の読み込みとサイズ計算 ---
  logo_pil = Image.open(OPENING_LOGO_PATH).convert("RGBA")
  # ロゴの目標サイズ（画面高さの35%）
  logo_target_h = int(height * 0.35)
  logo_aspect = logo_pil.width / logo_pil.height
  logo_target_w = int(logo_target_h * logo_aspect)

  # ズームアニメーション用にスケール別のロゴを事前計算（24fps × 2秒 = 48フレーム）
  zoom_frames = int(VIDEO_FPS * 2)  # 1.0s-3.0s のズーム区間
  logo_scales = []
  for i in range(zoom_frames):
    progress = i / max(zoom_frames - 1, 1)
    scale = 0.5 + 0.5 * progress  # 50% → 100%
    sw = max(1, int(logo_target_w * scale))
    sh = max(1, int(logo_target_h * scale))
    scaled = logo_pil.resize((sw, sh), Image.LANCZOS)
    logo_scales.append(np.array(scaled))

  # フルサイズのロゴ（ズーム後の保持用）
  logo_full = logo_pil.resize((logo_target_w, logo_target_h), Image.LANCZOS)
  logo_full_arr = np.array(logo_full)

  # ロゴの配置Y座標（画面の30%位置を中心に）
  logo_center_y = int(height * 0.30)

  def _composite_logo_on_canvas(logo_rgba: np.ndarray, opacity: float):
    """ロゴをキャンバスサイズのRGB+Alpha配列に描画する"""
    lh, lw = logo_rgba.shape[:2]
    x = (width - lw) // 2
    y = logo_center_y - lh // 2

    rgb_canvas = np.zeros((height, width, 3), dtype=np.uint8)
    alpha_canvas = np.zeros((height, width), dtype=np.float64)

    # クリッピング
    y1, y2 = max(0, y), min(height, y + lh)
    x1, x2 = max(0, x), min(width, x + lw)
    sy1, sy2 = y1 - y, y2 - y
    sx1, sx2 = x1 - x, x2 - x

    if y2 > y1 and x2 > x1:
      rgb_canvas[y1:y2, x1:x2] = logo_rgba[sy1:sy2, sx1:sx2, :3]
      alpha_canvas[y1:y2, x1:x2] = (
        logo_rgba[sy1:sy2, sx1:sx2, 3].astype(np.float64) / 255.0 * opacity
      )

    return rgb_canvas, alpha_canvas

  def logo_frame(t):
    if t < 1.0 or t > OPENING_DURATION:
      return np.zeros((height, width, 3), dtype=np.uint8)

    # オパシティ計算
    if t < 1.5:
      opacity = (t - 1.0) / 0.5  # フェードイン
    elif t < 6.5:
      opacity = 1.0
    else:
      opacity = max(0.0, 1.0 - (t - 6.5) / 0.5)  # フェードアウト

    # スケール計算
    if t < 3.0:
      frame_idx = min(int((t - 1.0) * VIDEO_FPS), zoom_frames - 1)
      logo_arr = logo_scales[frame_idx]
    else:
      logo_arr = logo_full_arr

    rgb, _ = _composite_logo_on_canvas(logo_arr, opacity)
    return rgb

  def logo_mask(t):
    if t < 1.0 or t > OPENING_DURATION:
      return np.zeros((height, width), dtype=np.float64)

    if t < 1.5:
      opacity = (t - 1.0) / 0.5
    elif t < 6.5:
      opacity = 1.0
    else:
      opacity = max(0.0, 1.0 - (t - 6.5) / 0.5)

    if t < 3.0:
      frame_idx = min(int((t - 1.0) * VIDEO_FPS), zoom_frames - 1)
      logo_arr = logo_scales[frame_idx]
    else:
      logo_arr = logo_full_arr

    _, alpha = _composite_logo_on_canvas(logo_arr, opacity)
    return alpha

  # --- ロゴクリップ ---
  logo_clip = VideoClip(frame_function=logo_frame, duration=duration)
  logo_clip.fps = VIDEO_FPS
  logo_mask_clip = VideoClip(
    frame_function=logo_mask, is_mask=True, duration=duration,
  )
  logo_mask_clip.fps = VIDEO_FPS
  logo_clip = logo_clip.with_mask(logo_mask_clip)

  # --- タイトルテキスト ---
  title_array = render_text(
    text=title,
    font_path=str(FONT_PATH),
    font_size=OPENING_TITLE_FONT_SIZE,
    color=OPENING_TITLE_COLOR,
    stroke_width=OPENING_TITLE_STROKE_WIDTH,
    stroke_color=OPENING_TITLE_STROKE_COLOR,
    max_width=int(width * 0.8),
  )
  # タイトルのフェードイン/アウト用マスク
  title_h, title_w = title_array.shape[:2]
  title_rgb = title_array[:, :, :3]
  title_base_alpha = title_array[:, :, 3].astype(np.float64) / 255.0

  def title_frame(t):
    return title_rgb

  def title_mask(t):
    if t < 3.0:
      return np.zeros((title_h, title_w), dtype=np.float64)
    if t < 3.5:
      opacity = (t - 3.0) / 0.5  # フェードイン
    elif t < 6.5:
      opacity = 1.0
    else:
      opacity = max(0.0, 1.0 - (t - 6.5) / 0.5)  # フェードアウト
    return title_base_alpha * opacity

  title_clip = VideoClip(frame_function=title_frame, duration=duration)
  title_clip.fps = VIDEO_FPS
  title_mask_clip = VideoClip(
    frame_function=title_mask, is_mask=True, duration=duration,
  )
  title_mask_clip.fps = VIDEO_FPS
  title_clip = title_clip.with_mask(title_mask_clip)
  # タイトル配置（ロゴの下）
  title_y = logo_center_y + logo_target_h // 2 + int(height * 0.05)
  title_clip = title_clip.with_position(("center", title_y))

  # --- 白背景 ---
  bg = ColorClip(size=size, color=OPENING_BG_COLOR).with_duration(duration)

  # --- 合成 ---
  opening = CompositeVideoClip(
    [bg, logo_clip, title_clip],
    size=size,
  ).with_duration(duration)

  # --- SE + ボイス音声 ---
  audio_clips = []
  if OPENING_SE_PATH.exists():
    se_audio = AudioFileClip(str(OPENING_SE_PATH))
    audio_clips.append(se_audio.with_start(1.0))
  else:
    logger.warning("SE音声ファイルが見つかりません: %s", OPENING_SE_PATH)

  # SE終了後（約3.5秒）に「へぼだんチャンネル！」ボイスを重ねる
  voice_start = 3.5
  if OPENING_VOICE_TSUNO_PATH.exists():
    audio_clips.append(
      AudioFileClip(str(OPENING_VOICE_TSUNO_PATH)).with_start(voice_start),
    )
  if OPENING_VOICE_MEGANE_PATH.exists():
    audio_clips.append(
      AudioFileClip(str(OPENING_VOICE_MEGANE_PATH)).with_start(voice_start),
    )

  if audio_clips:
    opening = opening.with_audio(
      CompositeAudioClip(audio_clips).with_duration(duration),
    )
  elif not OPENING_SE_PATH.exists():
    logger.warning("オープニング音声ファイルが見つかりません")

  opening.fps = VIDEO_FPS
  logger.info("オープニングクリップ生成完了 (%.1f秒)", duration)
  return opening


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


def _create_static_character_clip(
  assets: CharacterFrames,
  emotion: str,
  duration: float,
  brightness: float,
  scale: float,
) -> ImageClip:
  """静止画のキャラクタークリップを生成する（非アクティブ話者用）"""
  img = assets.mouth_closed.get(emotion, assets.mouth_closed["normal"])
  img = _apply_brightness(img, brightness)
  clip = (
    ImageClip(img, transparent=True)
    .with_duration(duration)
    .resized(scale)
  )
  return clip


def _create_animated_character_clip(
  assets: CharacterFrames,
  emotion: str,
  mouth_states: np.ndarray,
  duration: float,
  brightness: float,
  scale: float,
  fps: int,
) -> VideoClip:
  """口パク・表情付きのキャラクタークリップを生成する

  Args:
    assets: キャラクターの全画像セット
    emotion: 感情名（"normal", "happy", ...）
    mouth_states: フレームごとの口開閉 bool 配列
    duration: クリップの長さ（秒）
    brightness: 明るさ係数
    scale: 拡大率
    fps: フレームレート
  """
  # 表情に合った画像を取得（なければ normal にフォールバック）
  closed_img = _apply_brightness(
    assets.mouth_closed.get(emotion, assets.mouth_closed["normal"]),
    brightness,
  )
  open_img = _apply_brightness(
    assets.mouth_open.get(emotion, assets.mouth_open["normal"]),
    brightness,
  )

  # RGBA を RGB + アルファに分離
  closed_rgb = closed_img[:, :, :3]
  closed_alpha = closed_img[:, :, 3].astype(np.float64) / 255.0
  open_rgb = open_img[:, :, :3]
  open_alpha = open_img[:, :, 3].astype(np.float64) / 255.0

  def frame_function(t):
    frame_idx = min(int(t * fps), len(mouth_states) - 1)
    if mouth_states[frame_idx]:
      return open_rgb
    return closed_rgb

  def mask_function(t):
    frame_idx = min(int(t * fps), len(mouth_states) - 1)
    if mouth_states[frame_idx]:
      return open_alpha
    return closed_alpha

  clip = VideoClip(frame_function=frame_function, duration=duration)
  clip.fps = fps
  mask_clip = VideoClip(
    frame_function=mask_function, is_mask=True, duration=duration,
  )
  mask_clip.fps = fps
  clip = clip.with_mask(mask_clip)

  if scale != 1.0:
    clip = clip.resized(scale)

  return clip


def compose_landscape(
  dialogue: list[DialogueLine],
  audio_paths: list[Path],
  output_path: Path,
  bg_image_path: Path | None = None,
  title: str = "",
) -> None:
  """16:9 横長動画を合成する（口パク・表情対応）

  Args:
    dialogue: セリフリスト
    audio_paths: 各セリフに対応するWAVファイルパスのリスト
    output_path: 出力先MP4パス
    bg_image_path: 背景画像パス（Noneの場合はソリッドカラー）
    title: エピソードタイトル（空文字ならOPスキップ）
  """
  width, height = LANDSCAPE_SIZE
  char_height = int(height * 0.42)  # キャラ小さめ（元の60%）

  # キャラクター画像セットを事前読み込み
  tsuno_assets = load_character_assets("tsuno", char_height)
  megane_assets = load_character_assets("megane", char_height)

  # ダイアログシーン用ロゴ（事前読み込み）
  dialogue_logo_arr = None
  dialogue_logo_w = dialogue_logo_h = 0
  if DIALOGUE_LOGO_PATH.exists():
    _logo_pil = Image.open(DIALOGUE_LOGO_PATH).convert("RGBA")
    dialogue_logo_h = int(height * 0.36)
    _logo_aspect = _logo_pil.width / _logo_pil.height
    dialogue_logo_w = int(dialogue_logo_h * _logo_aspect)
    _logo_pil = _logo_pil.resize(
      (dialogue_logo_w, dialogue_logo_h), Image.LANCZOS,
    )
    dialogue_logo_arr = np.array(_logo_pil)

  # レイアウト定数
  char_center_y = int(height * 0.25) + 20  # キャラ中心（上寄り + 20px下）
  text_area_top = int(height * 0.60)  # 下部40%をテロップエリアに
  float_amp = 8    # ふわふわ振幅（px）
  float_freq = 0.4  # ふわふわ周波数（Hz）

  clips = []

  # オープニングクリップ
  if title and OPENING_LOGO_PATH.exists():
    opening = _create_opening_clip(title, (width, height))
    clips.append(opening)

  for i, (line, audio_path) in enumerate(zip(dialogue, audio_paths)):
    audio = AudioFileClip(str(audio_path))
    duration = audio.duration

    logger.info(
      "動画合成(横) [%d/%d]: %s (%.1f秒)",
      i + 1, len(dialogue), line.text[:15], duration,
    )

    # 背景
    bg = _create_background_clip(bg_image_path, (width, height), duration)

    # アクティブスピーカー判定
    tsuno_active = line.speaker == "tsuno"
    megane_active = line.speaker == "megane"
    emotion = getattr(line, "emotion", "normal") or "normal"

    # 口パク解析
    mouth_states = analyze_mouth_states(
      audio_path, VIDEO_FPS,
      threshold=LIPSYNC_THRESHOLD,
      min_open_frames=LIPSYNC_MIN_OPEN_FRAMES,
    )

    # つのクリップ生成
    tsuno_brightness = 1.0 if tsuno_active else 0.5
    tsuno_scale = 1.1 if tsuno_active else 1.0
    if tsuno_active:
      tsuno_clip = _create_animated_character_clip(
        tsuno_assets, emotion, mouth_states, duration,
        tsuno_brightness, tsuno_scale, VIDEO_FPS,
      )
    else:
      tsuno_clip = _create_static_character_clip(
        tsuno_assets, emotion, duration,
        tsuno_brightness, tsuno_scale,
      )

    # つの位置（左・ふわふわ浮遊）
    ts_w, ts_h = tsuno_clip.size
    tsuno_bx = int(width * 0.02)
    tsuno_by = char_center_y - ts_h // 2
    tsuno_clip = tsuno_clip.with_position(
      lambda t, bx=tsuno_bx, by=tsuno_by: (
        bx, by + int(float_amp * np.sin(2 * np.pi * float_freq * t))
      ),
    )

    # めがねクリップ生成
    megane_brightness = 1.0 if megane_active else 0.5
    megane_scale = 1.1 if megane_active else 1.0
    if megane_active:
      megane_clip = _create_animated_character_clip(
        megane_assets, emotion, mouth_states, duration,
        megane_brightness, megane_scale, VIDEO_FPS,
      )
    else:
      megane_clip = _create_static_character_clip(
        megane_assets, emotion, duration,
        megane_brightness, megane_scale,
      )

    # めがね位置（右・ふわふわ浮遊、位相ずれ）
    mg_w, mg_h = megane_clip.size
    megane_bx = width - mg_w - int(width * 0.02)
    megane_by = char_center_y - mg_h // 2
    megane_clip = megane_clip.with_position(
      lambda t, bx=megane_bx, by=megane_by: (
        bx, by + int(float_amp * np.sin(2 * np.pi * float_freq * t + np.pi / 2))
      ),
    )

    scene_layers = [bg, tsuno_clip, megane_clip]

    # ロゴ（中央・プルプル震え）
    if dialogue_logo_arr is not None:
      logo_clip = (
        ImageClip(dialogue_logo_arr, transparent=True).with_duration(duration)
      )
      logo_bx = (width - dialogue_logo_w) // 2
      char_bottom = max(tsuno_by + ts_h, megane_by + mg_h)
      logo_by = (char_bottom + text_area_top) // 2 - dialogue_logo_h // 2 - 70
      logo_clip = logo_clip.with_position(
        lambda t, bx=logo_bx, by=logo_by: (
          bx + int(3 * np.sin(2 * np.pi * 2.5 * t)),
          by + int(3 * np.sin(2 * np.pi * 3.0 * t + np.pi / 3)),
        ),
      )
      scene_layers.insert(1, logo_clip)  # 背景の上、キャラの下

    # 字幕（下部40%エリア中央）— [[表示専用]]を展開し、読みアノテーションを除去して表示
    display_text = unwrap_display_only(remove_reading_annotations(line.text))
    subtitle = _create_subtitle_clip(
      display_text, duration, max_width=int(width * 0.85),
    )
    sub_h = subtitle.size[1]
    subtitle_y = text_area_top + (height - text_area_top - sub_h) // 2 - 50
    subtitle = subtitle.with_position(("center", subtitle_y))
    scene_layers.append(subtitle)

    # セリフクリップを合成
    scene = CompositeVideoClip(
      scene_layers,
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


# --- LINE チャット風縦動画ヘルパー ---

# チャットレイアウト定数
_CHAT_ICON_SIZE = 80
_CHAT_ICON_MARGIN = 30
_CHAT_ICON_GAP = 12
_CHAT_BUBBLE_MAX_WIDTH = 700
_CHAT_BUBBLE_PADDING = 20
_CHAT_BUBBLE_RADIUS = 20
_CHAT_MSG_SPACING = 25
_CHAT_FONT_SIZE = 36
_CHAT_BOTTOM_MARGIN = 150
_CHAT_TSUNO_COLOR = (92, 210, 96)     # LINE グリーン
_CHAT_MEGANE_COLOR = (255, 255, 255)  # 白
_CHAT_TSUNO_TEXT = (255, 255, 255)    # 白文字
_CHAT_MEGANE_TEXT = (30, 30, 30)      # 黒文字
_CHAT_PAST_OPACITY = 0.7


def _make_circular_icon(img_path: Path, size: int) -> Image.Image:
  """画像を正方形にクロップし円形マスクを適用した RGBA Image を返す"""
  img = Image.open(img_path).convert("RGBA")
  # 正方形クロップ（上部優先＝顔が映りやすい）
  side = min(img.width, img.height)
  left = (img.width - side) // 2
  img = img.crop((left, 0, left + side, side))
  img = img.resize((size, size), Image.LANCZOS)
  # 円形マスク
  mask = Image.new("L", (size, size), 0)
  ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
  img.putalpha(mask)
  return img


def _wrap_text_for_bubble(
  text: str, font: ImageFont.FreeTypeFont, max_width: int,
) -> list[str]:
  """ピクセル幅ベースでテキストを折り返す"""
  lines: list[str] = []
  current = ""
  for char in text:
    test = current + char
    bbox = font.getbbox(test)
    if (bbox[2] - bbox[0]) > max_width and current:
      lines.append(current)
      current = char
    else:
      current = test
  if current:
    lines.append(current)
  return lines or [text]


def _measure_bubble(
  text: str, font: ImageFont.FreeTypeFont, max_text_width: int,
) -> tuple[int, int, list[str]]:
  """吹き出しのサイズ（幅, 高さ）と折り返し済み行リストを返す"""
  lines = _wrap_text_for_bubble(text, font, max_text_width)
  line_bboxes = [font.getbbox(line) for line in lines]
  line_heights = [bb[3] - bb[1] for bb in line_bboxes]
  line_widths = [bb[2] - bb[0] for bb in line_bboxes]
  line_spacing = int(_CHAT_FONT_SIZE * 0.3)

  text_w = max(line_widths) if line_widths else 0
  text_h = sum(line_heights) + line_spacing * max(0, len(lines) - 1)

  bubble_w = text_w + _CHAT_BUBBLE_PADDING * 2
  bubble_h = text_h + _CHAT_BUBBLE_PADDING * 2
  return bubble_w, bubble_h, lines


def _draw_chat_bubble(
  draw: ImageDraw.ImageDraw,
  text: str,
  x: int,
  y: int,
  bubble_color: tuple[int, int, int],
  text_color: tuple[int, int, int],
  font: ImageFont.FreeTypeFont,
  max_text_width: int,
) -> tuple[int, int]:
  """角丸吹き出し + テキストを描画し (bubble_width, bubble_height) を返す"""
  bubble_w, bubble_h, lines = _measure_bubble(text, font, max_text_width)
  r = _CHAT_BUBBLE_RADIUS

  # 角丸矩形
  draw.rounded_rectangle(
    (x, y, x + bubble_w, y + bubble_h),
    radius=r,
    fill=(*bubble_color, 255),
  )

  # テキスト描画
  line_spacing = int(_CHAT_FONT_SIZE * 0.3)
  ty = y + _CHAT_BUBBLE_PADDING
  for line in lines:
    draw.text(
      (x + _CHAT_BUBBLE_PADDING, ty),
      line,
      font=font,
      fill=(*text_color, 255),
    )
    bbox = font.getbbox(line)
    ty += (bbox[3] - bbox[1]) + line_spacing

  return bubble_w, bubble_h


def _render_chat_frame(
  width: int,
  height: int,
  bg_image: Image.Image | None,
  dialogue: list[DialogueLine],
  current_idx: int,
  tsuno_icon: Image.Image,
  megane_icon: Image.Image,
  font: ImageFont.FreeTypeFont,
) -> tuple[np.ndarray, np.ndarray]:
  """チャット画面1フレームを描画して (合成済みRGB, チャットオーバーレイRGBA) を返す"""
  # 背景
  if bg_image:
    canvas = bg_image.copy()
  else:
    canvas = Image.new("RGB", (width, height), BG_COLOR)

  max_text_width = _CHAT_BUBBLE_MAX_WIDTH - _CHAT_BUBBLE_PADDING * 2
  icon_size = _CHAT_ICON_SIZE

  # 各メッセージの表示テキスト（[[表示専用]]展開＋読み仮名アノテーション除去済み）
  display_texts = [
    unwrap_display_only(remove_reading_annotations(dialogue[idx].text))
    for idx in range(current_idx + 1)
  ]

  # 各メッセージの吹き出しサイズを事前計算（0 .. current_idx）
  bubble_infos: list[tuple[int, int, str]] = []  # (w, h, speaker)
  for idx in range(current_idx + 1):
    line = dialogue[idx]
    bw, bh, _ = _measure_bubble(display_texts[idx], font, max_text_width)
    bubble_infos.append((bw, bh, line.speaker))

  # 下から上に配置: 最新メッセージが一番下
  y_bottom = height - _CHAT_BOTTOM_MARGIN
  visible_start = 0

  # 表示に必要な縦幅を計算し、表示開始インデックスを決定
  total_needed = 0
  for idx in range(current_idx, -1, -1):
    _, bh, _ = bubble_infos[idx]
    row_h = max(bh, icon_size) + _CHAT_MSG_SPACING
    total_needed += row_h
    if total_needed > y_bottom - 100:  # 上部100pxマージン
      visible_start = idx + 1
      break

  # チャットオーバーレイ（半透明対応のため RGBA）
  overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
  draw = ImageDraw.Draw(overlay)

  y_cursor = y_bottom
  for idx in range(current_idx, visible_start - 1, -1):
    line = dialogue[idx]
    bw, bh, speaker = bubble_infos[idx]
    is_current = idx == current_idx
    row_h = max(bh, icon_size)
    y_cursor -= row_h

    if speaker == "tsuno":
      icon_x = _CHAT_ICON_MARGIN
      bubble_x = icon_x + icon_size + _CHAT_ICON_GAP
      icon_img = tsuno_icon
      bubble_color = _CHAT_TSUNO_COLOR
      text_color = _CHAT_TSUNO_TEXT
    else:
      bubble_x = width - _CHAT_ICON_MARGIN - icon_size - _CHAT_ICON_GAP - bw
      icon_x = width - _CHAT_ICON_MARGIN - icon_size
      icon_img = megane_icon
      bubble_color = _CHAT_MEGANE_COLOR
      text_color = _CHAT_MEGANE_TEXT

    icon_y = y_cursor + (row_h - icon_size) // 2
    bubble_y = y_cursor + (row_h - bh) // 2

    if not is_current:
      # 過去メッセージ: 半透明のバブルを描画
      bubble_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
      bd = ImageDraw.Draw(bubble_layer)
      _draw_chat_bubble(
        bd, display_texts[idx], bubble_x, bubble_y,
        bubble_color, text_color, font, max_text_width,
      )
      # アイコンも貼り付け
      bubble_layer.paste(icon_img, (icon_x, icon_y), icon_img)
      # 全体の不透明度を下げる
      alpha = bubble_layer.split()[3]
      alpha = alpha.point(lambda a: int(a * _CHAT_PAST_OPACITY))
      bubble_layer.putalpha(alpha)
      overlay = Image.alpha_composite(overlay, bubble_layer)
    else:
      # 現在のメッセージ: 通常描画
      _draw_chat_bubble(
        draw, display_texts[idx], bubble_x, bubble_y,
        bubble_color, text_color, font, max_text_width,
      )
      overlay.paste(icon_img, (icon_x, icon_y), icon_img)

    y_cursor -= _CHAT_MSG_SPACING

  # 背景にオーバーレイ合成
  canvas = canvas.convert("RGBA")
  result = Image.alpha_composite(canvas, overlay)
  return np.array(result.convert("RGB")), np.array(overlay)


def compose_portrait(
  dialogue: list[DialogueLine],
  audio_paths: list[Path],
  output_path: Path,
  bg_image_path: Path | None = None,
  title: str = "",
) -> None:
  """9:16 縦長動画を合成する（LINE チャット風レイアウト）

  Args:
    dialogue: セリフリスト
    audio_paths: 各セリフに対応するWAVファイルパスのリスト
    output_path: 出力先MP4パス
    bg_image_path: 背景画像パス（Noneの場合はソリッドカラー）
    title: エピソードタイトル（空文字ならOPスキップ）
  """
  width, height = PORTRAIT_SIZE

  # 背景画像の準備
  bg_image = None
  if bg_image_path and bg_image_path.exists():
    bg_image = Image.open(bg_image_path).convert("RGB")
    bg_image = bg_image.resize((width, height), Image.LANCZOS)

  # キャラアイコン（normal_closed を使用）
  tsuno_icon_path = IMAGES_DIR / "tsuno" / "normal_closed.png"
  megane_icon_path = IMAGES_DIR / "megane" / "normal_closed.png"
  tsuno_icon = _make_circular_icon(tsuno_icon_path, _CHAT_ICON_SIZE)
  megane_icon = _make_circular_icon(megane_icon_path, _CHAT_ICON_SIZE)

  # フォント
  font = ImageFont.truetype(str(FONT_PATH), _CHAT_FONT_SIZE)

  # ロゴ画像の準備（プルプル用）
  portrait_logo_arr = None
  portrait_logo_w = portrait_logo_h = 0
  if DIALOGUE_LOGO_PATH.exists():
    _p_logo = Image.open(DIALOGUE_LOGO_PATH).convert("RGBA")
    portrait_logo_w = int(width * 0.5)
    _p_logo_aspect = _p_logo.width / _p_logo.height
    portrait_logo_h = int(portrait_logo_w / _p_logo_aspect)
    _p_logo = _p_logo.resize(
      (portrait_logo_w, portrait_logo_h), Image.LANCZOS,
    )
    portrait_logo_arr = np.array(_p_logo)

  clips = []

  # オープニングクリップ
  if title and OPENING_LOGO_PATH.exists():
    opening = _create_opening_clip(title, (width, height))
    clips.append(opening)

  for i, (line, audio_path) in enumerate(zip(dialogue, audio_paths)):
    audio = AudioFileClip(str(audio_path))
    duration = audio.duration

    logger.info(
      "動画合成(縦) [%d/%d]: %s (%.1f秒)",
      i + 1, len(dialogue), line.text[:15], duration,
    )

    # チャットフレーム描画（背景+チャットオーバーレイを分離取得）
    composite_arr, chat_overlay_arr = _render_chat_frame(
      width, height, bg_image, dialogue, i,
      tsuno_icon, megane_icon, font,
    )

    scene_layers = []

    # 1) 背景レイヤー（bg_image または BG_COLOR）
    if bg_image:
      bg_clip = ImageClip(np.array(bg_image)).with_duration(duration)
    else:
      bg_clip = ColorClip(
        size=(width, height), color=BG_COLOR,
      ).with_duration(duration)
    scene_layers.append(bg_clip)

    # 2) ロゴレイヤー（プルプル震え、背景とチャットの間）
    if portrait_logo_arr is not None:
      logo_clip = (
        ImageClip(portrait_logo_arr, transparent=True)
        .with_duration(duration)
      )
      logo_bx = (width - portrait_logo_w) // 2
      logo_by = (height - portrait_logo_h) // 2
      logo_clip = logo_clip.with_position(
        lambda t, bx=logo_bx, by=logo_by: (
          bx + int(3 * np.sin(2 * np.pi * 2.5 * t)),
          by + int(3 * np.sin(2 * np.pi * 3.0 * t + np.pi / 3)),
        ),
      )
      scene_layers.append(logo_clip)

    # 3) チャットオーバーレイレイヤー（吹き出し + アイコン）
    chat_clip = (
      ImageClip(chat_overlay_arr, transparent=True)
      .with_duration(duration)
    )
    scene_layers.append(chat_clip)

    scene = (
      CompositeVideoClip(scene_layers, size=(width, height))
      .with_duration(duration)
      .with_audio(audio)
    )
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
