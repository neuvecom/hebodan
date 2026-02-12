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


def run_post_x(output_dir):
  """X (Twitter) に投稿する

  Args:
    output_dir: 動画の出力ディレクトリパス（str または Path）

  Returns:
    str: 投稿されたツイートの URL
  """
  output_dir = Path(output_dir)
  x_post_path = output_dir / "x_post.txt"

  if not x_post_path.exists():
    raise FileNotFoundError(
      f"X投稿文ファイルが見つかりません: {x_post_path}\n"
      "先に upload でアップロードしてください"
    )

  text = x_post_path.read_text(encoding="utf-8").strip()
  if not text:
    raise ValueError(f"X投稿文が空です: {x_post_path}")

  logger.info("=" * 50)
  logger.info("X 投稿")
  logger.info("投稿文: %s", text[:100])
  logger.info("=" * 50)

  tweet_url = post_to_x(text)
  logger.info("投稿完了: %s", tweet_url)
  return tweet_url


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

  try:
    run_post_x(args.output_dir)
  except (FileNotFoundError, ValueError) as e:
    logger.error("%s", e)
    sys.exit(1)


if __name__ == "__main__":
  main()
