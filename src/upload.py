"""YouTube アップロード + note/X テキスト生成 CLI

使い方:
  python -m src.upload output/20260211_043037
  python -m src.upload output/20260211_043037 --public
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from src.models import ScriptData
from src.uploaders.youtube_uploader import upload_to_youtube

logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
  datefmt="%H:%M:%S",
)
logger = logging.getLogger("hebodan.upload")


def _extract_intro(note_content: str) -> str:
  """note_content から H1 直下の段落（最初の ## まで）を抽出する"""
  lines = note_content.split("\n")
  intro_lines = []
  found_h1 = False
  for line in lines:
    stripped = line.strip()
    if not found_h1:
      if stripped.startswith("# ") and not stripped.startswith("## "):
        found_h1 = True
      continue
    # 次の見出しに到達したら終了
    if stripped.startswith("## "):
      break
    intro_lines.append(line)
  # 前後の空行を除去
  text = "\n".join(intro_lines).strip()
  return text if text else note_content[:200]


def run_upload(output_dir, public=False):
  """YouTube にアップロードし、note記事/X投稿文を URL 入りで保存する

  Args:
    output_dir: 動画の出力ディレクトリパス（str または Path）
    public: True で公開、False で非公開

  Returns:
    str: アップロードされた YouTube URL
  """
  output_dir = Path(output_dir)
  if not output_dir.exists():
    raise FileNotFoundError(f"出力ディレクトリが見つかりません: {output_dir}")

  script_path = output_dir / "script.json"
  video_path = output_dir / "landscape.mp4"
  thumbnail_path = output_dir / "thumbnail.png"

  if not script_path.exists():
    raise FileNotFoundError(f"台本ファイルが見つかりません: {script_path}")
  if not video_path.exists():
    raise FileNotFoundError(f"動画ファイルが見つかりません: {video_path}")

  raw = json.loads(script_path.read_text(encoding="utf-8"))
  script = ScriptData.from_dict(raw)

  privacy = "public" if public else "private"
  description = _extract_intro(script.note_content)
  description += "\n\n#へぼ談 #ゆっくり解説"
  yt_title = script.meta.title.replace("\n", "")

  logger.info("=" * 50)
  logger.info("YouTube アップロード開始")
  logger.info("タイトル: %s", yt_title)
  logger.info("プライバシー: %s", privacy)
  logger.info("=" * 50)

  youtube_url = upload_to_youtube(
    video_path=video_path,
    title=yt_title,
    description=description,
    thumbnail_path=thumbnail_path if thumbnail_path.exists() else None,
    privacy=privacy,
  )

  note_content = script.note_content.replace("{youtube_url}", youtube_url)
  note_path = output_dir / "note.md"
  note_path.write_text(note_content, encoding="utf-8")
  logger.info("note記事保存: %s", note_path)

  x_content = script.x_post_content.replace("{youtube_url}", youtube_url)
  x_post_path = output_dir / "x_post.txt"
  x_post_path.write_text(x_content, encoding="utf-8")
  logger.info("X投稿文保存: %s", x_post_path)

  upload_info = {
    "youtube_url": youtube_url,
    "privacy": privacy,
    "title": script.meta.title,
  }
  info_path = output_dir / "upload_info.json"
  info_path.write_text(
    json.dumps(upload_info, ensure_ascii=False, indent=2),
    encoding="utf-8",
  )

  logger.info("アップロード完了: %s", youtube_url)
  return youtube_url


def main():
  parser = argparse.ArgumentParser(
    description="Hebodan - YouTube アップロード + テキスト生成",
  )
  parser.add_argument(
    "output_dir",
    type=str,
    help="動画の出力ディレクトリパス（例: output/20260211_043037）",
  )
  parser.add_argument(
    "--public",
    action="store_true",
    help="YouTube のプライバシーを public にする（デフォルトは private）",
  )
  args = parser.parse_args()

  try:
    youtube_url = run_upload(args.output_dir, public=args.public)
  except FileNotFoundError as e:
    logger.error("%s", e)
    sys.exit(1)

  logger.info("=" * 50)
  logger.info("  YouTube: %s", youtube_url)
  logger.info("=" * 50)


if __name__ == "__main__":
  main()
