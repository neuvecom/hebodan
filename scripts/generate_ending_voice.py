"""エンディング用のボイスを生成するスクリプト

使い方:
  COEIROINKを起動した状態で実行:
  .venv/bin/python scripts/generate_ending_voice.py

assets/audio/se/ に以下を保存します:
  - ending_call_tsuno.wav      (つの「チャンネル登録よろしくね！」)
  - ending_call_megane.wav     (めがね「チャンネル登録よろしくね！」)
  - ending_tsuno_01.wav        (つの雑談)
  - ending_megane_01〜10.wav   (めがね雑談 10パターン)
"""

import sys
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import CHARACTERS, COEIROINK_HOST

OUTPUT_DIR = PROJECT_ROOT / "assets" / "audio" / "se"

# 生成する音声の定義: (ファイル名, キャラキー, テキスト)
# --- 固定ボイス（チャンネル登録呼びかけ） ---
VOICES_CALL = [
  ("ending_call_tsuno.wav", "tsuno", "チャンネル登録よろしくね！"),
  ("ending_call_megane.wav", "megane", "チャンネル登録よろしくね！"),
]

# --- つの雑談（固定1パターン） ---
VOICES_TSUNO_CHAT = [
  ("ending_tsuno_01.wav", "tsuno", "新しい動画の通知が届いて便利なんだよ"),
]

# --- めがね雑談（10パターン・ランダム選択用） ---
VOICES_MEGANE_CHAT = [
  ("ending_megane_01.wav", "megane", "でもたくさんのチャンネル登録すると逆に不便ですよね？"),
  ("ending_megane_02.wav", "megane", "通知オフにしてる人って結構多いらしいですよ"),
  ("ending_megane_03.wav", "megane", "通知たまりすぎると見ないですよね？"),
  ("ending_megane_04.wav", "megane", "あと、忘れないようにってことですよね"),
  ("ending_megane_05.wav", "megane", "通知きて3秒で開く人、めちゃくちゃ暇ですよね"),
  ("ending_megane_06.wav", "megane", "まあ、押して損することはないですからね"),
  ("ending_megane_07.wav", "megane", "いいねも押してもらわないとですよね？"),
  ("ending_megane_08.wav", "megane", "通知よりコメントの方が嬉しいんじゃないですか？"),
  ("ending_megane_09.wav", "megane", "登録ボタンの位置、意外とわかりにくいですよね"),
  ("ending_megane_10.wav", "megane", "いいね2回押してくれる人ありがたいですが、無意味なんですよね"),
]

VOICES = VOICES_CALL + VOICES_TSUNO_CHAT + VOICES_MEGANE_CHAT


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

  skip_existing = "--skip-existing" in sys.argv
  failed = []
  for filename, speaker_key, text in VOICES:
    if skip_existing and (OUTPUT_DIR / filename).exists():
      print(f"スキップ（既存）: {filename}")
      continue
    try:
      generate_voice(filename, speaker_key, text)
    except requests.HTTPError as e:
      print(f"  ✗ 失敗: {filename}「{text}」- {e}")
      failed.append((filename, text))

  print("\n完了！生成ファイル:")
  for filename, _, _ in VOICES:
    path = OUTPUT_DIR / filename
    mark = "✓" if path.exists() else "✗"
    print(f"  {mark} {path}")
  if failed:
    print(f"\n⚠ {len(failed)}件の生成に失敗しました:")
    for fn, txt in failed:
      print(f"  - {fn}「{txt}」")


if __name__ == "__main__":
  main()
