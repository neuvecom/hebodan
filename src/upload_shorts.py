"""YouTube ショート動画アップロード CLI

使い方:
  python -m src.upload_shorts output/20260211_043037
  python -m src.upload_shorts output/20260211_043037 --public

前提: 先に python -m src.upload で本編をアップロード済みであること
（upload_info.json から本編URLを取得するため）
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
logger = logging.getLogger("hebodan.upload_shorts")

CHANNEL_URL = "https://www.youtube.com/@hebodan"


def _build_description(main_video_url: str, theme: str) -> str:
  """ショート動画の概要欄を組み立てる"""
  tag = theme.replace(" ", "").replace("　", "")
  return (
    f"📺 本編はこちら\n"
    f"{main_video_url}\n"
    f"\n"
    f"#{tag} #へぼ談\n"
    f"\n"
    f"チャンネル登録よろしくお願いします！\n"
    f"{CHANNEL_URL}"
  )


def run_upload_shorts(output_dir, public=False):
  """YouTube にショート動画をアップロードする

  Args:
    output_dir: 動画の出力ディレクトリパス（str または Path）
    public: True で公開、False で非公開

  Returns:
    str: アップロードされた Shorts URL
  """
  output_dir = Path(output_dir)
  if not output_dir.exists():
    raise FileNotFoundError(f"出力ディレクトリが見つかりません: {output_dir}")

  script_path = output_dir / "script.json"
  video_path = output_dir / "portrait.mp4"
  upload_info_path = output_dir / "upload_info.json"

  if not script_path.exists():
    raise FileNotFoundError(f"台本ファイルが見つかりません: {script_path}")
  if not video_path.exists():
    raise FileNotFoundError(f"縦動画が見つかりません: {video_path}")
  if not upload_info_path.exists():
    raise FileNotFoundError(
      f"upload_info.json が見つかりません: {upload_info_path}\n"
      "先に upload で本編をアップロードしてください"
    )

  raw = json.loads(script_path.read_text(encoding="utf-8"))
  script = ScriptData.from_dict(raw)
  upload_info = json.loads(upload_info_path.read_text(encoding="utf-8"))
  main_video_url = upload_info["youtube_url"]

  privacy = "public" if public else "private"
  title = script.meta.title
  description = _build_description(main_video_url, script.meta.theme)

  logger.info("=" * 50)
  logger.info("YouTube ショート動画アップロード開始")
  logger.info("タイトル: %s", title)
  logger.info("本編URL: %s", main_video_url)
  logger.info("プライバシー: %s", privacy)
  logger.info("=" * 50)

  yt_title = title.replace("\n", "")
  if "#Shorts" not in yt_title:
    yt_title = f"{yt_title} #Shorts"
  shorts_url = upload_to_youtube(
    video_path=video_path,
    title=yt_title,
    description=description,
    privacy=privacy,
  )

  upload_info["shorts_url"] = shorts_url
  upload_info_path.write_text(
    json.dumps(upload_info, ensure_ascii=False, indent=2),
    encoding="utf-8",
  )

  logger.info("ショート動画アップロード完了: %s", shorts_url)
  return shorts_url


def main():
  parser = argparse.ArgumentParser(
    description="Hebodan - YouTube ショート動画アップロード",
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
    shorts_url = run_upload_shorts(args.output_dir, public=args.public)
  except FileNotFoundError as e:
    logger.error("%s", e)
    sys.exit(1)

  logger.info("=" * 50)
  logger.info("  Shorts: %s", shorts_url)
  logger.info("=" * 50)


if __name__ == "__main__":
  main()
