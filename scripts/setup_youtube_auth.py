"""YouTube OAuth2 初回認証セットアップ

使い方:
  python scripts/setup_youtube_auth.py

Google Cloud Console で作成した OAuth 2.0 クライアント ID の JSON ファイルを
credentials/youtube_client_secret.json に配置した上で実行してください。
ブラウザが開き、Google アカウントでの認証後にトークンが保存されます。
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import YOUTUBE_CLIENT_SECRET, YOUTUBE_TOKEN_PATH

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
  "https://www.googleapis.com/auth/youtube.upload",
  "https://www.googleapis.com/auth/youtube",
]


def main():
  if not YOUTUBE_CLIENT_SECRET.exists():
    print(f"エラー: クライアントシークレットが見つかりません: {YOUTUBE_CLIENT_SECRET}")
    print()
    print("セットアップ手順:")
    print("1. Google Cloud Console (https://console.cloud.google.com/) にアクセス")
    print("2. プロジェクトを作成し、YouTube Data API v3 を有効化")
    print("3. OAuth 2.0 クライアント ID を作成（デスクトップアプリ）")
    print(f"4. JSON をダウンロードして {YOUTUBE_CLIENT_SECRET} に配置")
    print("5. このスクリプトを再実行")
    sys.exit(1)

  print("YouTube OAuth2 認証を開始します...")
  print("ブラウザが開きます。Google アカウントでログインしてください。")
  print()

  flow = InstalledAppFlow.from_client_secrets_file(
    str(YOUTUBE_CLIENT_SECRET), SCOPES,
  )
  creds = flow.run_local_server(port=0)

  YOUTUBE_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
  YOUTUBE_TOKEN_PATH.write_text(creds.to_json())

  print()
  print(f"認証成功! トークンを保存しました: {YOUTUBE_TOKEN_PATH}")
  print("これで python -m src.upload でアップロードできます。")


if __name__ == "__main__":
  main()
