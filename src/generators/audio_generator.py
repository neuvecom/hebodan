"""COEIROINK API を使った音声合成モジュール"""

import logging
import re
import struct
import wave
from pathlib import Path

import requests

from src.config import COEIROINK_HOST, CHARACTERS, READING_DICT_PATH
from src.models import DialogueLine
from src.utils.reading_annotations import (
  apply_reading_dict,
  convert_reading_annotations,
  load_reading_dict,
  remove_reading_annotations,
  strip_display_only,
)

logger = logging.getLogger(__name__)


class AudioGenerator:
  """COEIROINK APIで音声を合成するクラス"""

  def __init__(self):
    self.host = COEIROINK_HOST
    self._reading_dict = load_reading_dict(READING_DICT_PATH)
    self._check_connection()

  def _check_connection(self):
    """COEIROINK APIへの接続確認"""
    try:
      resp = requests.get(f"{self.host}/v1/speakers", timeout=5)
      resp.raise_for_status()
      logger.info("COEIROINK API 接続確認OK")
    except requests.ConnectionError:
      raise ConnectionError(
        f"COEIROINK API に接続できません ({self.host})。"
        "COEIROINKが起動しているか確認してください。"
      )

  @staticmethod
  def _generate_silence(duration: float, sample_rate: int = 44100) -> bytes:
    """指定秒数の無音WAVバイナリを生成する"""
    import io
    num_samples = int(sample_rate * duration)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
      wf.setnchannels(1)
      wf.setsampwidth(2)
      wf.setframerate(sample_rate)
      wf.writeframes(struct.pack(f"<{num_samples}h", *([0] * num_samples)))
    return buf.getvalue()

  def _estimate_prosody(self, text: str, speaker_uuid: str, style_id: int) -> dict:
    """プロソディ（韻律）を推定する"""
    resp = requests.post(
      f"{self.host}/v1/estimate_prosody",
      json={"text": text},
      timeout=30,
    )
    resp.raise_for_status()
    return resp.json()

  def _synthesize(
    self, text: str, prosody: dict, speaker_uuid: str, style_id: int
  ) -> bytes:
    """音声合成を実行してWAVバイナリを取得する"""
    payload = {
      "speakerUuid": speaker_uuid,
      "styleId": style_id,
      "text": text,
      "prosodyDetail": prosody.get("detail", []),
      "speedScale": 1.0,
      "volumeScale": 1.0,
      "pitchScale": 0.0,
      "intonationScale": 1.0,
      "prePhonemeLength": 0.1,
      "postPhonemeLength": 0.1,
      "outputSamplingRate": 44100,
    }
    resp = requests.post(
      f"{self.host}/v1/synthesis",
      json=payload,
      timeout=60,
    )
    resp.raise_for_status()
    return resp.content

  def generate(
    self, dialogue: list[DialogueLine], output_dir: Path
  ) -> list[Path]:
    """対話リストから音声ファイルを一括生成する

    Args:
      dialogue: セリフのリスト
      output_dir: WAVファイルの出力先ディレクトリ

    Returns:
      生成されたWAVファイルパスのリスト
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_paths: list[Path] = []

    for i, line in enumerate(dialogue):
      char_config = CHARACTERS.get(line.speaker)
      if not char_config:
        raise ValueError(f"不明なキャラクター: {line.speaker}")

      speaker_uuid = char_config["speaker_uuid"]
      style_id = char_config["style_id"]

      if not speaker_uuid:
        raise ValueError(
          f"{line.speaker} の speaker_uuid が未設定です。"
          ".env ファイルを確認してください。"
        )

      filename = f"{i + 1:03d}_{line.speaker}.wav"
      output_path = output_dir / filename

      # TTS用テキスト前処理:
      # 1. [[表示専用]] 除去 → 2. 漢字アノテーション変換 → 3. 残余タグ除去 → 4. 辞書適用
      tts_text = strip_display_only(line.text)
      tts_text = convert_reading_annotations(tts_text)
      tts_text = remove_reading_annotations(tts_text)
      tts_text = apply_reading_dict(tts_text, self._reading_dict)

      logger.info(
        "音声生成中 [%d/%d]: %s「%s」",
        i + 1, len(dialogue), char_config["name"], line.text[:20],
      )

      # 発音可能な文字がない場合（記号・句読点のみ）は短い無音WAVを生成
      if not re.search(r"[\w\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]", tts_text):
        logger.info("  → 発音テキストなし、無音WAVを生成: %s", repr(tts_text))
        wav_data = self._generate_silence(0.5)
        output_path.write_bytes(wav_data)
        audio_paths.append(output_path)
        continue

      prosody = self._estimate_prosody(tts_text, speaker_uuid, style_id)
      wav_data = self._synthesize(tts_text, prosody, speaker_uuid, style_id)

      output_path.write_bytes(wav_data)
      audio_paths.append(output_path)
      logger.info("  → %s (%.1f KB)", filename, len(wav_data) / 1024)

    logger.info("音声生成完了: %d ファイル", len(audio_paths))
    return audio_paths
