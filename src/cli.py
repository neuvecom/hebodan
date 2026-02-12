"""Hebodan 統合 CLI

使い方:
  python -m src run "AIの未来"                  # テーマから全工程（インタラクティブ）
  python -m src run neta/theme.md               # mdファイルから全工程
  python -m src run -s output/XXX/script.json   # 既存台本から再開

  python -m src generate "AIの未来"             # 動画生成のみ（= src.main）
  python -m src generate -d "AIの未来"          # 台本+背景のみ（下書き）
  python -m src upload output/XXX               # YouTubeアップロード
  python -m src shorts output/XXX               # Shortsアップロード
  python -m src post output/XXX                 # X投稿
  python -m src status output/XXX               # 出力ディレクトリの状態表示
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from src.config import AUDIO_DIR, FONT_PATH, OUTPUT_DIR
from src.models import ScriptData

logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
  datefmt="%H:%M:%S",
)
logger = logging.getLogger("hebodan")

YOUTUBE_STUDIO_URL = "https://studio.youtube.com/channel/UChh3-OwADcoDem5abqD1m4w"
NICONICO_URL = "https://garage.nicovideo.jp/niconico-garage/video/series/549523"
TIKTOK_URL = "https://www.tiktok.com/tiktokstudio/content"


def _confirm(prompt, default=True):
  """Y/n 形式の確認プロンプト"""
  suffix = " [Y/n] " if default else " [y/N] "
  try:
    answer = input(prompt + suffix).strip().lower()
  except (EOFError, KeyboardInterrupt):
    print()
    return False
  if not answer:
    return default
  return answer in ("y", "yes")


def _validate_environment():
  """実行環境の事前チェック"""
  if not FONT_PATH.exists():
    logger.error(
      "フォントが見つかりません: %s\n"
      "bash scripts/download_font.sh を実行してフォントを取得してください。",
      FONT_PATH,
    )
    sys.exit(1)


def _parse_theme(theme_arg):
  """テーマ引数を解析し、(theme, instructions) を返す"""
  if theme_arg.endswith(".md"):
    theme_path = Path(theme_arg)
    if not theme_path.exists():
      logger.error("テーマファイルが見つかりません: %s", theme_path)
      sys.exit(1)
    content = theme_path.read_text(encoding="utf-8").strip()
    instructions = content
    theme = None
    for line in content.split("\n"):
      stripped = line.strip()
      if stripped.startswith("# "):
        theme = stripped[2:].strip()
        break
    if not theme:
      for line in content.split("\n"):
        stripped = line.strip()
        if stripped:
          theme = stripped
          break
    if not theme:
      logger.error("テーマファイルが空です: %s", theme_path)
      sys.exit(1)
    logger.info("テーマファイル読み込み: %s", theme_path)
    return theme, instructions
  return theme_arg, None


class HebodanCLI:
  """統合CLIメインクラス"""

  def cmd_run(self, args):
    """インタラクティブ全工程フロー"""
    _validate_environment()
    start_time = time.time()

    # -s モード: 既存台本から再開
    if args.script:
      script_path = Path(args.script)
      if not script_path.exists():
        logger.error("台本ファイルが見つかりません: %s", script_path)
        sys.exit(1)

      raw = json.loads(script_path.read_text(encoding="utf-8"))
      script = ScriptData.from_dict(raw)
      run_output_dir = script_path.parent
      audio_output_dir = AUDIO_DIR / run_output_dir.name
      audio_output_dir.mkdir(parents=True, exist_ok=True)

      print()
      logger.info("=" * 50)
      logger.info("既存台本から再開")
      logger.info("タイトル: %s", script.meta.title)
      logger.info("セリフ数: %d", len(script.dialogue))
      logger.info("出力先: %s", run_output_dir)
      logger.info("=" * 50)

    else:
      # テーマから新規生成
      if not args.theme:
        logger.error("テーマまたは --script を指定してください")
        sys.exit(1)

      theme, instructions = _parse_theme(args.theme)

      timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
      run_output_dir = OUTPUT_DIR / timestamp
      run_output_dir.mkdir(parents=True, exist_ok=True)
      audio_output_dir = AUDIO_DIR / timestamp
      audio_output_dir.mkdir(parents=True, exist_ok=True)

      # ステップ1: 台本＋背景を生成
      from src.generators.background_generator import generate_backgrounds
      from src.generators.script_generator import ScriptGenerator

      print()
      logger.info("[1] 台本＋背景を生成中...")
      script_gen = ScriptGenerator()
      script = script_gen.generate(theme, instructions=instructions)

      script_path = run_output_dir / "script.json"
      script_path.write_text(
        json.dumps(asdict(script), ensure_ascii=False, indent=2),
        encoding="utf-8",
      )

      generate_backgrounds(theme, run_output_dir)
      logger.info("  台本: %s", script_path)
      logger.info(
        "  タイトル: 「%s」（%d セリフ）",
        script.meta.title, len(script.dialogue),
      )

      # ステップ2: 台本確認
      print()
      try:
        answer = input("[2] 台本を確認しますか？ [Y/n/edit] ").strip().lower()
      except (EOFError, KeyboardInterrupt):
        print()
        answer = "n"

      if answer in ("", "y", "yes"):
        print()
        print(f"  タイトル: {script.meta.title}")
        print(f"  セリフ数: {len(script.dialogue)}")
        print("  --- 冒頭 ---")
        for line in script.dialogue[:5]:
          print(f"  {line.speaker}: {line.text[:60]}")
        if len(script.dialogue) > 5:
          print(f"  ... (残り {len(script.dialogue) - 5} セリフ)")
        print("  --- ここまで ---")
      elif answer == "edit":
        editor = os.environ.get("EDITOR", "vim")
        logger.info("  $EDITOR (%s) で台本を開きます...", editor)
        subprocess.call([editor, str(script_path)])
        # 再読み込み
        raw = json.loads(script_path.read_text(encoding="utf-8"))
        script = ScriptData.from_dict(raw)
        logger.info(
          "  台本を再読み込みしました（%d セリフ）", len(script.dialogue),
        )

      # 音声+動画生成の確認
      if not _confirm("\n[3] 音声＋動画を生成しますか？"):
        elapsed = time.time() - start_time
        logger.info("中断しました（%.1f秒）。続きは以下で再開できます:", elapsed)
        logger.info("  python -m src run -s %s", script_path)
        return

    # ステップ3: 音声＋動画生成
    from src.generators.audio_generator import AudioGenerator
    from src.generators.thumbnail_generator import generate_thumbnail
    from src.generators.video_composer import compose_landscape, compose_portrait

    print()
    logger.info("音声＋動画を生成中...")

    logger.info("  音声を生成中...")
    audio_gen = AudioGenerator()
    audio_paths = audio_gen.generate(script.dialogue, audio_output_dir)

    logger.info("  サムネイルを生成中...")
    thumbnail_path = run_output_dir / "thumbnail.png"
    landscape_bg_path = run_output_dir / "bg_landscape.png"
    portrait_bg_path = run_output_dir / "bg_portrait.png"
    landscape_bg = landscape_bg_path if landscape_bg_path.exists() else None
    portrait_bg = portrait_bg_path if portrait_bg_path.exists() else None
    generate_thumbnail(script.meta.title, thumbnail_path, landscape_bg)

    logger.info("  横長動画 (16:9) を合成中...")
    landscape_path = run_output_dir / "landscape.mp4"
    compose_landscape(
      script.dialogue, audio_paths, landscape_path, landscape_bg,
      title=script.meta.title,
    )

    logger.info("  縦長動画 (9:16) を合成中...")
    portrait_path = run_output_dir / "portrait.mp4"
    compose_portrait(
      script.dialogue, audio_paths, portrait_path, portrait_bg,
      title=script.meta.title,
    )

    # note記事 / X投稿文を保存（テンプレート状態）
    note_path = run_output_dir / "note.md"
    note_path.write_text(script.note_content, encoding="utf-8")
    x_post_path = run_output_dir / "x_post.txt"
    x_post_path.write_text(script.x_post_content, encoding="utf-8")

    print()
    logger.info("動画生成完了:")
    logger.info("  横長: %s", landscape_path)
    logger.info("  縦長: %s", portrait_path)
    logger.info("  サムネ: %s", thumbnail_path)

    # ステップ4: 動画確認
    print()
    try:
      input("動画を確認してから Enter を押してください...")
    except (EOFError, KeyboardInterrupt):
      print()

    # ステップ5: YouTube アップロード
    youtube_url = None
    if _confirm("\nYouTube にアップロードしますか？"):
      from src.upload import run_upload

      youtube_url = run_upload(run_output_dir)
      logger.info("  YouTube: %s", youtube_url)

    # ステップ6: Shorts アップロード
    shorts_url = None
    if youtube_url and _confirm("\nShorts もアップロードしますか？"):
      from src.upload_shorts import run_upload_shorts

      shorts_url = run_upload_shorts(run_output_dir)
      logger.info("  Shorts: %s", shorts_url)

    # ステップ7: X 投稿
    tweet_url = None
    if youtube_url and _confirm("\nX に投稿しますか？"):
      from src.post_x import run_post_x

      tweet_url = run_post_x(run_output_dir)
      logger.info("  X: %s", tweet_url)

    # ステップ8: サマリー
    elapsed = time.time() - start_time
    print()
    print("=" * 50)
    print(f"全工程完了（所要時間: {elapsed:.1f}秒）")
    print()
    print(f"  出力先: {run_output_dir}")
    if youtube_url:
      print(f"  本編: {youtube_url}")
    if shorts_url:
      print(f"  Shorts: {shorts_url}")
    if tweet_url:
      print(f"  X: {tweet_url}")
    print()
    print("残りの手動作業:")
    print(f"  YouTube Studio: {YOUTUBE_STUDIO_URL}")
    print(f"  note記事: {run_output_dir / 'note.md'}")
    print(f"  ニコニコ: {NICONICO_URL}")
    print(f"  TikTok: {TIKTOK_URL}")
    print("=" * 50)

  def cmd_generate(self, args):
    """動画生成（src.main に委譲）"""
    saved_argv = sys.argv
    argv = ["src.main"]
    if args.script:
      argv.extend(["-s", args.script])
      if args.thumbnail:
        argv.append("-t")
    else:
      if args.theme:
        argv.append(args.theme)
      if args.draft:
        argv.append("-d")
    sys.argv = argv
    try:
      from src.main import main as main_main

      main_main()
    finally:
      sys.argv = saved_argv

  def cmd_upload(self, args):
    """YouTubeアップロード"""
    from src.upload import run_upload

    try:
      run_upload(args.output_dir, public=args.public)
    except FileNotFoundError as e:
      logger.error("%s", e)
      sys.exit(1)

  def cmd_shorts(self, args):
    """Shortsアップロード"""
    from src.upload_shorts import run_upload_shorts

    try:
      run_upload_shorts(args.output_dir, public=args.public)
    except FileNotFoundError as e:
      logger.error("%s", e)
      sys.exit(1)

  def cmd_post(self, args):
    """X投稿"""
    from src.post_x import run_post_x

    try:
      run_post_x(args.output_dir)
    except (FileNotFoundError, ValueError) as e:
      logger.error("%s", e)
      sys.exit(1)

  def cmd_status(self, args):
    """出力ディレクトリの状態表示"""
    output_dir = Path(args.output_dir)
    if not output_dir.exists():
      logger.error("ディレクトリが見つかりません: %s", output_dir)
      sys.exit(1)

    print(f"\n{output_dir}")

    # script.json
    script_path = output_dir / "script.json"
    if script_path.exists():
      raw = json.loads(script_path.read_text(encoding="utf-8"))
      script = ScriptData.from_dict(raw)
      title = script.meta.title.replace("\n", " ")
      print(
        f"  [ok] script.json      "
        f"-- 「{title}」({len(script.dialogue)}セリフ)"
      )
    else:
      print("  [  ] script.json")

    # 背景画像
    for name in ("bg_landscape.png", "bg_portrait.png"):
      path = output_dir / name
      mark = "[ok]" if path.exists() else "[  ]"
      print(f"  {mark} {name}")

    # 動画ファイル
    for name in ("landscape.mp4", "portrait.mp4"):
      path = output_dir / name
      if path.exists():
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"  [ok] {name:<17} -- {size_mb:.1f}MB")
      else:
        print(f"  [  ] {name}")

    # サムネイル
    thumb = output_dir / "thumbnail.png"
    mark = "[ok]" if thumb.exists() else "[  ]"
    print(f"  {mark} thumbnail.png")

    # アップロード情報
    info_path = output_dir / "upload_info.json"
    if info_path.exists():
      info = json.loads(info_path.read_text(encoding="utf-8"))
      yt_url = info.get("youtube_url", "")
      print(f"  [ok] YouTube          -- {yt_url}")
      if info.get("shorts_url"):
        print(f"  [ok] Shorts           -- {info['shorts_url']}")
      else:
        print("  [  ] Shorts")
    else:
      print("  [  ] YouTube")
      print("  [  ] Shorts")

    # X投稿状態
    x_post = output_dir / "x_post.txt"
    if x_post.exists():
      content = x_post.read_text(encoding="utf-8").strip()
      if "{youtube_url}" not in content and "https://" in content:
        print("  [ok] X投稿文（URL解決済み）")
      else:
        print("  [--] X投稿文（テンプレート）")
    else:
      print("  [  ] X投稿文")

    print()


def main():
  parser = argparse.ArgumentParser(
    description="Hebodan - 動画パイプライン CLI",
  )
  subparsers = parser.add_subparsers(dest="command")

  # run
  run_p = subparsers.add_parser("run", help="全工程インタラクティブ実行")
  run_p.add_argument("theme", nargs="?", help="テーマまたは .md ファイルパス")
  run_p.add_argument("-s", "--script", help="既存台本JSONパス（再開用）")

  # generate
  gen_p = subparsers.add_parser("generate", help="動画生成（src.main と同等）")
  gen_p.add_argument("theme", nargs="?", help="テーマまたは .md ファイルパス")
  gen_p.add_argument(
    "-d", "--draft", action="store_true", help="台本+背景のみ生成",
  )
  gen_p.add_argument("-s", "--script", help="既存台本JSONパス")
  gen_p.add_argument(
    "-t", "--thumbnail", action="store_true", help="サムネイルのみ再生成",
  )

  # upload
  up_p = subparsers.add_parser("upload", help="YouTube アップロード")
  up_p.add_argument("output_dir", help="出力ディレクトリパス")
  up_p.add_argument("--public", action="store_true", help="公開モード")

  # shorts
  sh_p = subparsers.add_parser("shorts", help="Shorts アップロード")
  sh_p.add_argument("output_dir", help="出力ディレクトリパス")
  sh_p.add_argument("--public", action="store_true", help="公開モード")

  # post
  po_p = subparsers.add_parser("post", help="X に投稿")
  po_p.add_argument("output_dir", help="出力ディレクトリパス")

  # status
  st_p = subparsers.add_parser("status", help="出力ディレクトリの状態表示")
  st_p.add_argument("output_dir", help="出力ディレクトリパス")

  args = parser.parse_args()

  if not args.command:
    parser.print_help()
    sys.exit(1)

  cli = HebodanCLI()
  cmd_map = {
    "run": cli.cmd_run,
    "generate": cli.cmd_generate,
    "upload": cli.cmd_upload,
    "shorts": cli.cmd_shorts,
    "post": cli.cmd_post,
    "status": cli.cmd_status,
  }
  cmd_map[args.command](args)


if __name__ == "__main__":
  main()
