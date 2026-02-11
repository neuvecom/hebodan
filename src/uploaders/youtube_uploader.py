"""YouTube Data API v3 を使った動画アップロードモジュール"""

import logging
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from src.config import (
  YOUTUBE_CATEGORY_ID,
  YOUTUBE_CLIENT_SECRET,
  YOUTUBE_TOKEN_PATH,
)

logger = logging.getLogger(__name__)

SCOPES = [
  "https://www.googleapis.com/auth/youtube.upload",
  "https://www.googleapis.com/auth/youtube",
]


def _get_credentials() -> Credentials:
  """OAuth2 認証情報を取得する（トークンファイルがあれば再利用）"""
  creds = None
  if YOUTUBE_TOKEN_PATH.exists():
    creds = Credentials.from_authorized_user_file(str(YOUTUBE_TOKEN_PATH), SCOPES)

  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      if not YOUTUBE_CLIENT_SECRET.exists():
        raise FileNotFoundError(
          f"YouTube OAuth クライアントシークレットが見つかりません: {YOUTUBE_CLIENT_SECRET}\n"
          "Google Cloud Console で OAuth 2.0 クライアント ID を作成し、\n"
          f"{YOUTUBE_CLIENT_SECRET} に配置してください。"
        )
      flow = InstalledAppFlow.from_client_secrets_file(
        str(YOUTUBE_CLIENT_SECRET), SCOPES,
      )
      creds = flow.run_local_server(port=0)

    YOUTUBE_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    YOUTUBE_TOKEN_PATH.write_text(creds.to_json())
    logger.info("YouTube トークンを保存しました: %s", YOUTUBE_TOKEN_PATH)

  return creds


def upload_to_youtube(
  video_path: Path,
  title: str,
  description: str,
  thumbnail_path: Path | None = None,
  tags: list[str] | None = None,
  privacy: str = "private",
) -> str:
  """YouTubeに動画をアップロードし、動画URLを返す

  Args:
    video_path: アップロードする動画ファイルパス
    title: 動画タイトル
    description: 動画の説明文
    thumbnail_path: サムネイル画像パス（Noneの場合はスキップ）
    tags: タグリスト
    privacy: プライバシー設定（"private", "unlisted", "public"）

  Returns:
    YouTubeの動画URL（例: https://youtu.be/xxxxx）
  """
  creds = _get_credentials()
  youtube = build("youtube", "v3", credentials=creds)

  body = {
    "snippet": {
      "title": title,
      "description": description,
      "tags": tags or ["へぼ談", "ゆっくり解説"],
      "categoryId": YOUTUBE_CATEGORY_ID,
    },
    "status": {
      "privacyStatus": privacy,
    },
  }

  media = MediaFileUpload(
    str(video_path),
    mimetype="video/mp4",
    resumable=True,
    chunksize=10 * 1024 * 1024,  # 10MB chunks
  )

  logger.info("YouTube アップロード開始: %s", video_path.name)
  request = youtube.videos().insert(
    part="snippet,status",
    body=body,
    media_body=media,
  )

  response = None
  while response is None:
    status, response = request.next_chunk()
    if status:
      logger.info("  アップロード進捗: %d%%", int(status.progress() * 100))

  video_id = response["id"]
  video_url = f"https://youtu.be/{video_id}"
  logger.info("YouTube アップロード完了: %s", video_url)

  # サムネイル設定
  if thumbnail_path and thumbnail_path.exists():
    logger.info("サムネイルを設定中...")
    try:
      youtube.thumbnails().set(
        videoId=video_id,
        media_body=MediaFileUpload(str(thumbnail_path), mimetype="image/png"),
      ).execute()
      logger.info("サムネイル設定完了")
    except Exception as e:
      logger.warning(
        "サムネイル設定に失敗しました: %s\n"
        "  → YouTube Studio でアカウントの電話番号認証を行うと、\n"
        "    カスタムサムネイルが設定できるようになります。\n"
        "  → 動画アップロード自体は成功しています。\n"
        "  → YouTube Studio から手動でサムネイルを設定してください。",
        e,
      )

  return video_url
