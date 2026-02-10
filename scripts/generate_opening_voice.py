"""オープニング用の「へぼだんチャンネル！」音声を生成するスクリプト

使い方:
  COEIROINKを起動した状態で実行:
  .venv/bin/python scripts/generate_opening_voice.py

assets/audio/se/ に以下を保存します:
  - opening_tsuno.wav  (つのの声)
  - opening_megane.wav  (めがねの声)
"""

import sys
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import CHARACTERS, COEIROINK_HOST

OUTPUT_DIR = PROJECT_ROOT / "assets" / "audio" / "se"
TEXT = "へぼだんチャンネル！"


def generate_voice(speaker_key: str) -> None:
  """キャラクターの音声を生成して保存する"""
  char = CHARACTERS[speaker_key]
  speaker_uuid = char["speaker_uuid"]
  style_id = char["style_id"]
  name = char["name"]

  if not speaker_uuid:
    print(f"エラー: {name} の speaker_uuid が未設定です。.env を確認してください。")
    return

  print(f"{name}「{TEXT}」を生成中...")

  # プロソディ推定
  resp = requests.post(
    f"{COEIROINK_HOST}/v1/estimate_prosody",
    json={"text": TEXT},
    timeout=30,
  )
  resp.raise_for_status()
  prosody = resp.json()

  # 音声合成（少し明るめ・元気な設定）
  payload = {
    "speakerUuid": speaker_uuid,
    "styleId": style_id,
    "text": TEXT,
    "prosodyDetail": prosody.get("detail", []),
    "speedScale": 1.0,
    "volumeScale": 1.0,
    "pitchScale": 0.0,
    "intonationScale": 1.5,  # イントネーション強め（元気に）
    "prePhonemeLength": 0.05,
    "postPhonemeLength": 0.1,
    "outputSamplingRate": 44100,
  }
  resp = requests.post(
    f"{COEIROINK_HOST}/v1/synthesis",
    json=payload,
    timeout=60,
  )
  resp.raise_for_status()

  output_path = OUTPUT_DIR / f"opening_{speaker_key}.wav"
  output_path.write_bytes(resp.content)
  print(f"  → {output_path} ({len(resp.content) / 1024:.1f} KB)")


def main():
  # COEIROINK 接続確認
  try:
    resp = requests.get(f"{COEIROINK_HOST}/v1/speakers", timeout=5)
    resp.raise_for_status()
  except requests.ConnectionError:
    print(f"エラー: COEIROINK に接続できません ({COEIROINK_HOST})")
    print("COEIROINKを起動してから再実行してください。")
    sys.exit(1)

  OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

  generate_voice("tsuno")
  generate_voice("megane")

  print("\n完了！")
  print(f"  {OUTPUT_DIR / 'opening_tsuno.wav'}")
  print(f"  {OUTPUT_DIR / 'opening_megane.wav'}")


if __name__ == "__main__":
  main()
