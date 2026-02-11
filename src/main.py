"""Hebodan メインパイプライン

使い方:
  # テーマから全自動生成
  python -m src.main "トークテーマ"

  # マークダウンファイルで詳細指示
  python -m src.main theme.md

  # 台本だけ生成して止める（チェック用）
  python -m src.main -d theme.md

  # 既存の台本JSONから音声+動画を再生成
  python -m src.main --script output/20260210_123456/script.json

テーマを入力すると以下を自動生成します:
  - YouTube動画 (16:9)
  - Shorts/TikTok動画 (9:16)
  - サムネイル画像 (1280x720)
  - note記事 (Markdown)
  - X投稿文 (テキスト)

マークダウンファイル形式:
  # テーマキーワード
  ## 趣旨
  解説の方向性や切り口
  ## 指示
  - 追加の指示事項
"""

import argparse
import json
import logging
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from src.config import AUDIO_DIR, FONT_PATH, OUTPUT_DIR
from src.generators.audio_generator import AudioGenerator
from src.generators.background_generator import generate_backgrounds
from src.generators.script_generator import ScriptGenerator
from src.generators.thumbnail_generator import generate_thumbnail
from src.generators.video_composer import compose_landscape, compose_portrait
from src.models import ScriptData

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
    nargs="?",
    default=None,
    help="トークテーマ（例: 「AIの未来」）または .md ファイルパス",
  )
  parser.add_argument(
    "-d", "--draft",
    action="store_true",
    default=False,
    help="台本+背景だけ生成して止める（チェック用）。確認後 -s で再生成",
  )
  parser.add_argument(
    "-s", "--script",
    type=str,
    default=None,
    help="既存の台本JSONパス。指定すると台本生成をスキップし音声+動画を再生成",
  )
  parser.add_argument(
    "-t", "--thumbnail",
    action="store_true",
    default=False,
    help="-s と併用。サムネイルだけ再生成する",
  )
  args = parser.parse_args()

  # 引数バリデーション
  if not args.theme and not args.script:
    parser.error("テーマまたは --script のいずれかを指定してください")

  _validate_environment()

  start_time = time.time()

  # --script モード: 既存台本から再生成
  if args.script:
    script_path = Path(args.script)
    if not script_path.exists():
      logger.error("台本ファイルが見つかりません: %s", script_path)
      sys.exit(1)

    # 台本を読み込み
    raw = json.loads(script_path.read_text(encoding="utf-8"))
    script = ScriptData.from_dict(raw)

    # 出力先は台本と同じディレクトリに上書き
    run_output_dir = script_path.parent
    # 音声出力先: audio/ 配下に同名のディレクトリ
    audio_output_dir = AUDIO_DIR / run_output_dir.name
    audio_output_dir.mkdir(parents=True, exist_ok=True)

    # 既存の背景画像を探す
    landscape_bg_path = run_output_dir / "bg_landscape.png"
    portrait_bg_path = run_output_dir / "bg_portrait.png"
    landscape_bg = landscape_bg_path if landscape_bg_path.exists() else None
    portrait_bg = portrait_bg_path if portrait_bg_path.exists() else None

    # --thumbnail モード: サムネイルだけ再生成
    if args.thumbnail:
      logger.info("=" * 50)
      logger.info("Hebodan サムネイル再生成モード")
      logger.info("タイトル: %s", script.meta.title)
      logger.info("出力先: %s", run_output_dir)
      logger.info("=" * 50)

      thumbnail_path = run_output_dir / "thumbnail.png"
      generate_thumbnail(script.meta.title, thumbnail_path, landscape_bg)

      elapsed = time.time() - start_time
      logger.info("=" * 50)
      logger.info("サムネイル再生成完了（所要時間: %.1f秒）", elapsed)
      logger.info("  サムネ:    %s", thumbnail_path)
      logger.info("=" * 50)
      return

    logger.info("=" * 50)
    logger.info("Hebodan 再生成モード（台本から）")
    logger.info("台本: %s", script_path)
    logger.info("タイトル: %s", script.meta.title)
    logger.info("セリフ数: %d", len(script.dialogue))
    logger.info("出力先: %s", run_output_dir)
    logger.info("=" * 50)

    # 音声再生成
    logger.info("[1/4] 音声を生成中...")
    audio_gen = AudioGenerator()
    audio_paths = audio_gen.generate(script.dialogue, audio_output_dir)

    # サムネイル生成
    logger.info("[2/4] サムネイルを生成中...")
    thumbnail_path = run_output_dir / "thumbnail.png"
    generate_thumbnail(script.meta.title, thumbnail_path, landscape_bg)

    # 横長動画合成
    logger.info("[3/4] 横長動画 (16:9) を合成中...")
    landscape_path = run_output_dir / "landscape.mp4"
    compose_landscape(
      script.dialogue, audio_paths, landscape_path, landscape_bg,
      title=script.meta.title,
    )

    # 縦長動画合成
    logger.info("[4/4] 縦長動画 (9:16) を合成中...")
    portrait_path = run_output_dir / "portrait.mp4"
    compose_portrait(
      script.dialogue, audio_paths, portrait_path, portrait_bg,
      title=script.meta.title,
    )

    elapsed = time.time() - start_time
    logger.info("=" * 50)
    logger.info("再生成完了（所要時間: %.1f秒）", elapsed)
    logger.info("出力ファイル:")
    logger.info("  動画(横):  %s", landscape_path)
    logger.info("  動画(縦):  %s", portrait_path)
    logger.info("  サムネ:    %s", thumbnail_path)
    logger.info("=" * 50)
    return

  # 通常モード: テーマから全自動生成
  theme = args.theme
  instructions = None

  # .md ファイルの場合は読み込んで解析
  if theme.endswith(".md"):
    theme_path = Path(theme)
    if not theme_path.exists():
      logger.error("テーマファイルが見つかりません: %s", theme_path)
      sys.exit(1)
    content = theme_path.read_text(encoding="utf-8").strip()
    instructions = content
    # 最初の # 見出しをテーマキーワードとして抽出
    theme = None
    for line in content.split("\n"):
      stripped = line.strip()
      if stripped.startswith("# "):
        theme = stripped[2:].strip()
        break
    if not theme:
      # 見出しがなければ最初の非空行をテーマとする
      for line in content.split("\n"):
        stripped = line.strip()
        if stripped:
          theme = stripped
          break
    if not theme:
      logger.error("テーマファイルが空です: %s", theme_path)
      sys.exit(1)
    logger.info("テーマファイル読み込み: %s", theme_path)

  timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
  run_output_dir = OUTPUT_DIR / timestamp
  run_output_dir.mkdir(parents=True, exist_ok=True)
  audio_output_dir = AUDIO_DIR / timestamp
  audio_output_dir.mkdir(parents=True, exist_ok=True)

  draft_mode = args.draft
  total_steps = 2 if draft_mode else 6

  logger.info("=" * 50)
  logger.info("Hebodan 動画生成パイプライン開始%s", "（下書きモード）" if draft_mode else "")
  logger.info("テーマ: %s", theme)
  if instructions:
    logger.info("詳細指示: あり（マークダウンファイル）")
  logger.info("出力先: %s", run_output_dir)
  logger.info("=" * 50)

  # ステップ1: 台本生成
  logger.info("[1/%d] 台本を生成中...", total_steps)
  script_gen = ScriptGenerator()
  script = script_gen.generate(theme, instructions=instructions)
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

  # ステップ2: 背景画像生成
  logger.info("[2/%d] 背景画像を生成中...", total_steps)
  landscape_bg, portrait_bg = generate_backgrounds(theme, run_output_dir)
  if landscape_bg:
    logger.info("背景画像(横): %s", landscape_bg)
  if portrait_bg:
    logger.info("背景画像(縦): %s", portrait_bg)
  if not landscape_bg and not portrait_bg:
    logger.info("背景画像生成スキップ（ソリッドカラーを使用）")

  # --draft モード: 台本＋背景まで生成して終了
  if draft_mode:
    elapsed = time.time() - start_time
    logger.info("=" * 50)
    logger.info("下書き生成完了（所要時間: %.1f秒）", elapsed)
    logger.info("出力ファイル:")
    logger.info("  台本JSON:  %s", script_path)
    if landscape_bg:
      logger.info("  背景(横):  %s", landscape_bg)
    if portrait_bg:
      logger.info("  背景(縦):  %s", portrait_bg)
    logger.info("")
    logger.info("台本を確認・編集してから、以下で音声+動画を生成:")
    logger.info("  .venv/bin/python -m src.main -s %s", script_path)
    logger.info("=" * 50)
    return

  # ステップ3: 音声生成
  logger.info("[3/%d] 音声を生成中...", total_steps)
  audio_gen = AudioGenerator()
  audio_paths = audio_gen.generate(script.dialogue, audio_output_dir)

  # ステップ4: サムネイル生成
  logger.info("[4/%d] サムネイルを生成中...", total_steps)
  thumbnail_path = run_output_dir / "thumbnail.png"
  generate_thumbnail(script.meta.title, thumbnail_path, landscape_bg)

  # ステップ5: 横長動画合成 (16:9)
  logger.info("[5/%d] 横長動画 (16:9) を合成中...", total_steps)
  landscape_path = run_output_dir / "landscape.mp4"
  compose_landscape(
    script.dialogue, audio_paths, landscape_path, landscape_bg,
    title=script.meta.title,
  )

  # ステップ6: 縦長動画合成 (9:16)
  logger.info("[6/%d] 縦長動画 (9:16) を合成中...", total_steps)
  portrait_path = run_output_dir / "portrait.mp4"
  compose_portrait(
    script.dialogue, audio_paths, portrait_path, portrait_bg,
    title=script.meta.title,
  )

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
  logger.info("  サムネ:    %s", thumbnail_path)
  if landscape_bg:
    logger.info("  背景(横):  %s", landscape_bg)
  if portrait_bg:
    logger.info("  背景(縦):  %s", portrait_bg)
  logger.info("  note記事:  %s", note_path)
  logger.info("  X投稿文:   %s", x_post_path)
  logger.info("  台本JSON:  %s", script_path)
  logger.info("=" * 50)


if __name__ == "__main__":
  main()
