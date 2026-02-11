"""tweepy を使った X (Twitter) 投稿モジュール"""

import logging

import tweepy

from src.config import (
  X_ACCESS_TOKEN,
  X_ACCESS_TOKEN_SECRET,
  X_API_KEY,
  X_API_SECRET,
)

logger = logging.getLogger(__name__)


def post_to_x(text: str) -> str | None:
  """Xにテキストを投稿し、投稿URLを返す

  Args:
    text: 投稿テキスト

  Returns:
    投稿URL。API未設定時はNone
  """
  if not all([X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET]):
    raise ValueError(
      "X API の認証情報が未設定です。\n"
      ".env に X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET を設定してください。"
    )

  client = tweepy.Client(
    consumer_key=X_API_KEY,
    consumer_secret=X_API_SECRET,
    access_token=X_ACCESS_TOKEN,
    access_token_secret=X_ACCESS_TOKEN_SECRET,
  )

  response = client.create_tweet(text=text)
  tweet_id = response.data["id"]

  # ユーザー名を取得して投稿URLを構築
  me = client.get_me()
  username = me.data.username
  tweet_url = f"https://x.com/{username}/status/{tweet_id}"

  logger.info("X 投稿完了: %s", tweet_url)
  return tweet_url
