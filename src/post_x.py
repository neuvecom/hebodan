"""X (Twitter) 投稿 CLI

使い方:
  python -m src.post_x output/20260211_043037
"""

import argparse
import logging
import sys
from pathlib import Path

from src.uploaders.x_poster import post_to_x

logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
  datefmt="%H:%M:%S",
)
logger = logging.getLogger("hebodan.post_x")


def main():
  parser = argparse.ArgumentParser(
    description="Hebodan - X (Twitter) に投稿",
  )
  parser.add_argument(
    "output_dir",
    type=str,
    help="動画の出力ディレクトリパス（例: output/20260211_043037）",
  )
  args = parser.parse_args()

  output_dir = Path(args.output_dir)
  x_post_path = output_dir / "x_post.txt"

  if not x_post_path.exists():
    logger.error("X投稿文ファイルが見つかりません: %s", x_post_path)
    logger.error("先に python -m src.upload でアップロードしてください")
    sys.exit(1)

  text = x_post_path.read_text(encoding="utf-8").strip()
  if not text:
    logger.error("X投稿文が空です: %s", x_post_path)
    sys.exit(1)

  logger.info("=" * 50)
  logger.info("X 投稿")
  logger.info("投稿文: %s", text[:100])
  logger.info("=" * 50)

  tweet_url = post_to_x(text)
  logger.info("投稿完了: %s", tweet_url)


if __name__ == "__main__":
  main()
