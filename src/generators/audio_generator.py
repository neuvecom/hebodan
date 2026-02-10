"""COEIROINK API を使った音声合成モジュール"""

import logging
from pathlib import Path

import requests

from src.config import COEIROINK_HOST, CHARACTERS
from src.models import DialogueLine

logger = logging.getLogger(__name__)


class AudioGenerator:
  """COEIROINK APIで音声を合成するクラス"""

  def __init__(self):
    self.host = COEIROINK_HOST
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

      logger.info(
        "音声生成中 [%d/%d]: %s「%s」",
        i + 1, len(dialogue), char_config["name"], line.text[:20],
      )

      prosody = self._estimate_prosody(line.text, speaker_uuid, style_id)
      wav_data = self._synthesize(line.text, prosody, speaker_uuid, style_id)

      output_path.write_bytes(wav_data)
      audio_paths.append(output_path)
      logger.info("  → %s (%.1f KB)", filename, len(wav_data) / 1024)

    logger.info("音声生成完了: %d ファイル", len(audio_paths))
    return audio_paths
