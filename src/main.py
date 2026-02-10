"""Hebodan メインパイプライン

使い方:
  python -m src.main "トークテーマ"

テーマを入力すると以下を自動生成します:
  - YouTube動画 (16:9)
  - Shorts/TikTok動画 (9:16)
  - note記事 (Markdown)
  - X投稿文 (テキスト)
"""

import argparse
import json
import logging
import sys
import time
from dataclasses import asdict
from datetime import datetime

from src.config import AUDIO_DIR, FONT_PATH, OUTPUT_DIR
from src.generators.audio_generator import AudioGenerator
from src.generators.script_generator import ScriptGenerator
from src.generators.video_composer import compose_landscape, compose_portrait

logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
  datefmt="%H:%M:%S",
)
logger = logging.getLogger("hebodan")


def _validate_environment():
  """実行環境の事前チェック"""
  if not FONT_PATH.exists():
    logger.error(
      "フォントが見つかりません: %s\n"
      "bash scripts/download_font.sh を実行してフォントを取得してください。",
      FONT_PATH,
    )
    sys.exit(1)


def main():
  parser = argparse.ArgumentParser(
    description="Hebodan - テーマから動画を自動生成",
  )
  parser.add_argument(
    "theme",
    type=str,
    help="トークテーマ（例: 「AIの未来」）",
  )
  args = parser.parse_args()

  _validate_environment()

  start_time = time.time()
  timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
  run_output_dir = OUTPUT_DIR / timestamp
  run_output_dir.mkdir(parents=True, exist_ok=True)
  audio_output_dir = AUDIO_DIR / timestamp
  audio_output_dir.mkdir(parents=True, exist_ok=True)

  logger.info("=" * 50)
  logger.info("Hebodan 動画生成パイプライン開始")
  logger.info("テーマ: %s", args.theme)
  logger.info("出力先: %s", run_output_dir)
  logger.info("=" * 50)

  # ステップ1: 台本生成
  logger.info("[1/4] 台本を生成中...")
  script_gen = ScriptGenerator()
  script = script_gen.generate(args.theme)
  logger.info(
    "台本生成完了: 「%s」（セリフ数: %d）",
    script.meta.title, len(script.dialogue),
  )

  # 台本JSONを保存
  script_path = run_output_dir / "script.json"
  script_path.write_text(
    json.dumps(asdict(script), ensure_ascii=False, indent=2),
    encoding="utf-8",
  )

  # ステップ2: 音声生成
  logger.info("[2/4] 音声を生成中...")
  audio_gen = AudioGenerator()
  audio_paths = audio_gen.generate(script.dialogue, audio_output_dir)

  # ステップ3: 横長動画合成 (16:9)
  logger.info("[3/4] 横長動画 (16:9) を合成中...")
  landscape_path = run_output_dir / "landscape.mp4"
  compose_landscape(script.dialogue, audio_paths, landscape_path)

  # ステップ4: 縦長動画合成 (9:16)
  logger.info("[4/4] 縦長動画 (9:16) を合成中...")
  portrait_path = run_output_dir / "portrait.mp4"
  compose_portrait(script.dialogue, audio_paths, portrait_path)

  # note記事を保存
  note_path = run_output_dir / "note.md"
  note_path.write_text(script.note_content, encoding="utf-8")

  # X投稿文を保存
  x_post_path = run_output_dir / "x_post.txt"
  x_post_path.write_text(script.x_post_content, encoding="utf-8")

  elapsed = time.time() - start_time
  logger.info("=" * 50)
  logger.info("全工程完了（所要時間: %.1f秒）", elapsed)
  logger.info("出力ファイル:")
  logger.info("  動画(横):  %s", landscape_path)
  logger.info("  動画(縦):  %s", portrait_path)
  logger.info("  note記事:  %s", note_path)
  logger.info("  X投稿文:   %s", x_post_path)
  logger.info("  台本JSON:  %s", script_path)
  logger.info("=" * 50)


if __name__ == "__main__":
  main()
