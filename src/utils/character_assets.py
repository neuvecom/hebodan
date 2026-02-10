"""キャラクター画像アセット管理モジュール

表情・口パク画像のロードとリサイズを管理する。
assets/images/{speaker}/ ディレクトリが存在すれば全バリエーション読み込み、
存在しなければレガシー単一画像にフォールバックする。
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image

from src.config import CHARACTERS, IMAGES_DIR

logger = logging.getLogger(__name__)

VALID_EMOTIONS = ("normal", "happy", "angry", "sad", "surprised")


@dataclass
class CharacterFrames:
  """特定の高さにリサイズ済みのキャラクター画像セット"""
  mouth_closed: dict[str, np.ndarray] = field(default_factory=dict)
  mouth_open: dict[str, np.ndarray] = field(default_factory=dict)


def _load_and_resize(img_path: Path, target_height: int) -> np.ndarray:
  """画像を読み込み、アスペクト比を維持し指定高さにリサイズする（アルファ保持）"""
  img = Image.open(img_path).convert("RGBA")
  ratio = target_height / img.height
  new_width = int(img.width * ratio)
  img = img.resize((new_width, target_height), Image.LANCZOS)
  return np.array(img)


def load_character_assets(
  speaker: str,
  target_height: int,
) -> CharacterFrames:
  """キャラクターの全表情・口パク画像を読み込む

  Args:
    speaker: キャラクター名（"tsuno" or "megane"）
    target_height: リサイズ先の高さ（ピクセル）

  Returns:
    CharacterFrames: mouth_closed と mouth_open の辞書
      キーは表情名（"normal", "happy", ...）、値はRGBA numpy配列
  """
  char_config = CHARACTERS[speaker]
  assets_dir = IMAGES_DIR / char_config.get("assets_dir", speaker)
  frames = CharacterFrames()

  if assets_dir.is_dir():
    # 構造化アセットを読み込み
    loaded_count = 0
    for emotion in VALID_EMOTIONS:
      closed_path = assets_dir / f"{emotion}_closed.png"
      open_path = assets_dir / f"{emotion}_open.png"

      if closed_path.exists():
        frames.mouth_closed[emotion] = _load_and_resize(
          closed_path, target_height,
        )
        loaded_count += 1

      if open_path.exists():
        frames.mouth_open[emotion] = _load_and_resize(
          open_path, target_height,
        )
        loaded_count += 1

    logger.info(
      "キャラクターアセット読み込み: %s（%d枚）", speaker, loaded_count,
    )

    # normal が無い場合はフォールバック
    if "normal" not in frames.mouth_closed:
      logger.warning(
        "%s の normal_closed.png が見つかりません。レガシー画像を使用します。",
        speaker,
      )
      _load_legacy_fallback(speaker, target_height, frames)
  else:
    # レガシーモード: 単一画像を使用
    logger.info(
      "アセットディレクトリ未検出: %s → レガシーモード", assets_dir,
    )
    _load_legacy_fallback(speaker, target_height, frames)

  return frames


def _load_legacy_fallback(
  speaker: str,
  target_height: int,
  frames: CharacterFrames,
) -> None:
  """レガシー単一画像を口閉じ・口開きの両方に設定する"""
  char_config = CHARACTERS[speaker]
  legacy_path = IMAGES_DIR / char_config["image"]
  img_array = _load_and_resize(legacy_path, target_height)

  # 全表情に同じ画像を設定（現行動作と同一）
  for emotion in VALID_EMOTIONS:
    if emotion not in frames.mouth_closed:
      frames.mouth_closed[emotion] = img_array
    if emotion not in frames.mouth_open:
      frames.mouth_open[emotion] = img_array
