"""キャラクター表情・口パク画像を Gemini API で一括生成するスクリプト

使い方:
  .venv/bin/python scripts/generate_character_assets.py          # 未生成分のみ
  .venv/bin/python scripts/generate_character_assets.py --force   # 全て再生成

assets/images/chara.png から分割した各キャラのリファレンス画像を参考に、
表情・口の状態バリエーションを生成して assets/images/{speaker}/ に保存する。
"""

import argparse
import sys
import time
from io import BytesIO
from pathlib import Path

from PIL import Image

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from google import genai
from google.genai import types

from src.config import GEMINI_API_KEY, IMAGES_DIR

# Gemini 画像生成モデル
IMAGE_MODEL = "gemini-3-pro-image-preview"

# キャラクター定義
CHARACTERS = {
  "tsuno": {
    "image": "tsuno_ref.png",
    "base_prompt": (
      "chibi SD anime style, face-only close-up, head only, "
      "purple short bob hair, two small dark horns on top of head, "
      "pink-purple eyes, light skin, sharp fang tooth, "
      "transparent background (PNG alpha), thick bold outline, "
      "front view, same face size and viewing angle as reference image"
    ),
  },
  "megane": {
    "image": "megane_ref.png",
    "base_prompt": (
      "chibi SD anime style, face-only close-up, head only, "
      "dark navy long hair with straight bangs, round glasses, "
      "blue-grey eyes, light skin, "
      "transparent background (PNG alpha), thick bold outline, "
      "front view, same face size and viewing angle as reference image"
    ),
  },
}

# 表情 × 口の状態
VARIANTS = {
  "normal_closed": "neutral calm expression, mouth closed, lips together",
  "normal_open": "neutral expression, mouth open, speaking",
  "happy_closed": "happy smiling expression, eyes slightly squinting with joy, mouth closed in a smile",
  "happy_open": "happy expression, eyes squinting with joy, mouth wide open laughing",
  "angry_closed": "angry expression, furrowed eyebrows, sharp eyes, mouth closed in a frown",
  "angry_open": "angry expression, furrowed eyebrows, mouth open shouting",
  "sad_closed": "sad expression, slightly downcast eyes, small frown, mouth closed",
  "sad_open": "sad expression, downcast eyes, mouth slightly open, whimpering",
  "surprised_closed": "surprised expression, wide open eyes, raised eyebrows, mouth closed",
  "surprised_open": "surprised expression, wide open eyes, raised eyebrows, mouth wide open in shock",
}


def generate_variant(
  client: genai.Client,
  reference_image_path: Path,
  base_prompt: str,
  variant_prompt: str,
  output_path: Path,
  max_retries: int = 3,
) -> bool:
  """1枚の画像バリエーションを生成して保存する"""
  # 参考画像を読み込み
  ref_img = Image.open(reference_image_path)
  ref_bytes = BytesIO()
  ref_img.save(ref_bytes, format="PNG")
  ref_bytes.seek(0)

  prompt = (
    f"Generate a character face image that looks exactly like the reference image "
    f"but with the following changes in expression and mouth.\n\n"
    f"Character style: {base_prompt}\n"
    f"Expression/mouth: {variant_prompt}\n\n"
    f"IMPORTANT: Keep the exact same character design, hair style, accessories, "
    f"face size, and viewing angle as the reference image. "
    f"Only change the facial expression and mouth state. "
    f"Output as a single character face on transparent background."
  )

  for attempt in range(max_retries):
    try:
      response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=[
          types.Part.from_bytes(
            data=ref_bytes.getvalue(),
            mime_type="image/png",
          ),
          types.Part.from_text(text=prompt),
        ],
        config=types.GenerateContentConfig(
          response_modalities=["IMAGE"],
        ),
      )

      # レスポンスから画像を取得
      for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
          img = Image.open(BytesIO(part.inline_data.data))
          # RGBA に変換して保存
          img = img.convert("RGBA")
          output_path.parent.mkdir(parents=True, exist_ok=True)
          img.save(str(output_path), format="PNG")
          print(f"  ✓ {output_path.name} ({img.size[0]}x{img.size[1]})")
          return True

      print(f"  ✗ {output_path.name}: 画像が返されませんでした (試行 {attempt + 1})")

    except Exception as e:
      print(f"  ✗ {output_path.name}: エラー (試行 {attempt + 1}): {e}")
      if attempt < max_retries - 1:
        wait = 2 ** attempt * 5
        print(f"    {wait}秒後にリトライ...")
        time.sleep(wait)

  return False


def main():
  parser = argparse.ArgumentParser(description="キャラクター表情画像の自動生成")
  parser.add_argument(
    "--force", action="store_true",
    help="既存画像を上書きして全て再生成する",
  )
  args = parser.parse_args()

  if not GEMINI_API_KEY:
    print("エラー: GEMINI_API_KEY が設定されていません。")
    sys.exit(1)

  client = genai.Client(api_key=GEMINI_API_KEY)

  print("=" * 50)
  print("キャラクター表情画像の自動生成")
  if args.force:
    print("(--force: 既存画像を上書き)")
  print("=" * 50)

  total = 0
  success = 0

  for speaker, char_config in CHARACTERS.items():
    ref_path = IMAGES_DIR / char_config["image"]
    output_dir = IMAGES_DIR / speaker

    print(f"\n--- {speaker} ---")
    print(f"参考画像: {ref_path}")
    print(f"出力先: {output_dir}/")

    if not ref_path.exists():
      print(f"  ✗ 参考画像が見つかりません: {ref_path}")
      continue

    for variant_name, variant_prompt in VARIANTS.items():
      output_path = output_dir / f"{variant_name}.png"

      # 既に存在する場合（--force でなければスキップ）
      if output_path.exists() and not args.force:
        print(f"  - {variant_name}.png（既存、スキップ）")
        success += 1
        total += 1
        continue

      total += 1
      print(f"  生成中: {variant_name}...")

      if generate_variant(
        client, ref_path, char_config["base_prompt"],
        variant_prompt, output_path,
      ):
        success += 1

      # レート制限対策
      time.sleep(3)

  print(f"\n{'=' * 50}")
  print(f"完了: {success}/{total} 枚の画像を生成しました")
  print(f"{'=' * 50}")

  if success < total:
    print(f"\n⚠ {total - success}枚の生成に失敗しました。再実行で未生成分のみリトライできます。")


if __name__ == "__main__":
  main()
