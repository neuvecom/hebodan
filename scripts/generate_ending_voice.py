"""エンディング用のボイスを生成するスクリプト

使い方:
  COEIROINKを起動した状態で実行:
  .venv/bin/python scripts/generate_ending_voice.py

assets/audio/se/ に以下を保存します:
  - ending_call_tsuno.wav   (つの「チャンネル登録よろしくね！」)
  - ending_call_megane.wav  (めがね「チャンネル登録よろしくね！」)
  - ending_tsuno.wav        (つの「新しい動画の通知が届いて便利なんだよ」)
  - ending_megane.wav       (めがね「でもたくさんのチャンネル登録すると逆に不便ですよね？」)
"""

import sys
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import CHARACTERS, COEIROINK_HOST

OUTPUT_DIR = PROJECT_ROOT / "assets" / "audio" / "se"

# 生成する音声の定義: (ファイル名, キャラキー, テキスト)
VOICES = [
  ("ending_call_tsuno.wav", "tsuno", "チャンネル登録よろしくね！"),
  ("ending_call_megane.wav", "megane", "チャンネル登録よろしくね！"),
  ("ending_tsuno.wav", "tsuno", "新しい動画の通知が届いて便利なんだよ"),
  ("ending_megane.wav", "megane", "でもたくさんのチャンネル登録すると逆に不便ですよね？"),
]


def generate_voice(filename: str, speaker_key: str, text: str) -> None:
  """キャラクターの音声を生成して保存する"""
  char = CHARACTERS[speaker_key]
  speaker_uuid = char["speaker_uuid"]
  style_id = char["style_id"]
  name = char["name"]

  if not speaker_uuid:
    print(f"エラー: {name} の speaker_uuid が未設定です。.env を確認してください。")
    return

  print(f"{name}「{text}」を生成中...")

  # プロソディ推定
  resp = requests.post(
    f"{COEIROINK_HOST}/v1/estimate_prosody",
    json={"text": text},
    timeout=30,
  )
  resp.raise_for_status()
  prosody = resp.json()

  # 音声合成（明るめ・元気な設定）
  payload = {
    "speakerUuid": speaker_uuid,
    "styleId": style_id,
    "text": text,
    "prosodyDetail": prosody.get("detail", []),
    "speedScale": 1.0,
    "volumeScale": 1.0,
    "pitchScale": 0.0,
    "intonationScale": 1.5,
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

  output_path = OUTPUT_DIR / filename
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

  for filename, speaker_key, text in VOICES:
    generate_voice(filename, speaker_key, text)

  print("\n完了！生成ファイル:")
  for filename, _, _ in VOICES:
    print(f"  {OUTPUT_DIR / filename}")


if __name__ == "__main__":
  main()
