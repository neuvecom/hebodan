"""Hebodan 設定管理モジュール"""

import os
from pathlib import Path

from dotenv import load_dotenv

# プロジェクトルートパスの解決
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# ディレクトリパス
ASSETS_DIR = PROJECT_ROOT / "assets"
IMAGES_DIR = ASSETS_DIR / "images"
AUDIO_DIR = ASSETS_DIR / "audio"
FONTS_DIR = ASSETS_DIR / "fonts"
OUTPUT_DIR = PROJECT_ROOT / "output"

# フォント設定
FONT_NAME = os.getenv("FONT_NAME", "TAユニバーサルライン_DSP_E.ttf")
FONT_PATH = FONTS_DIR / FONT_NAME

# Gemini API 設定
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# COEIROINK API 設定
COEIROINK_HOST = os.getenv("COEIROINK_HOST", "http://localhost:50032")

# 読み辞書
READING_DICT_PATH = PROJECT_ROOT / "reading_dict.txt"

# キャラクター設定
CHARACTERS = {
  "tsuno": {
    "speaker_uuid": os.getenv("TSUNO_SPEAKER_UUID", ""),
    "style_id": int(os.getenv("TSUNO_STYLE_ID", "0")),
    "image": "ririn.png",
    "assets_dir": "tsuno",
    "name": "つの",
  },
  "megane": {
    "speaker_uuid": os.getenv("MEGANE_SPEAKER_UUID", ""),
    "style_id": int(os.getenv("MEGANE_STYLE_ID", "0")),
    "image": "tsukuyomi.png",
    "assets_dir": "megane",
    "name": "めがね",
  },
}

# 動画設定
LANDSCAPE_SIZE = (1920, 1080)
PORTRAIT_SIZE = (1080, 1920)
VIDEO_FPS = 24
BG_COLOR = (20, 20, 40)  # 濃紺系背景
SUBTITLE_FONT_SIZE = 48
SUBTITLE_COLOR = (255, 255, 255)
SUBTITLE_STROKE_WIDTH = 2
SUBTITLE_STROKE_COLOR = (0, 0, 0)
DIALOGUE_LOGO_PATH = IMAGES_DIR / "logo" / "logo_white.png"

# 背景画像生成設定
BG_IMAGE_MODEL = "gemini-3-pro-image-preview"
BG_GENERATION_MAX_RETRIES = 3
BG_GENERATION_RETRY_BASE_WAIT = 5  # リトライ待機秒数（指数バックオフ）

# オープニング設定
OPENING_DURATION = 7.0
OPENING_BG_COLOR = (255, 255, 255)  # 白背景
OPENING_SE_PATH = ASSETS_DIR / "audio" / "se" / "opening.wav"
OPENING_LOGO_PATH = IMAGES_DIR / "logo" / "logo_normal.png"
OPENING_TITLE_FONT_SIZE = 60
OPENING_TITLE_COLOR = (0, 0, 0)  # 黒文字
OPENING_TITLE_STROKE_WIDTH = 2
OPENING_TITLE_STROKE_COLOR = (180, 180, 180)  # 薄グレー縁取り
OPENING_VOICE_TSUNO_PATH = ASSETS_DIR / "audio" / "se" / "opening_tsuno.wav"
OPENING_VOICE_MEGANE_PATH = ASSETS_DIR / "audio" / "se" / "opening_megane.wav"

# リップシンク設定
LIPSYNC_THRESHOLD = 0.15       # 口を開く振幅閾値（0.0-1.0、正規化済み）
LIPSYNC_MIN_OPEN_FRAMES = 2   # チャタリング防止の最低フレーム数

# YouTube API 設定
YOUTUBE_CLIENT_SECRET = PROJECT_ROOT / os.getenv(
  "YOUTUBE_CLIENT_SECRET", "credentials/youtube_client_secret.json",
)
YOUTUBE_TOKEN_PATH = PROJECT_ROOT / "credentials" / "youtube_token.json"
YOUTUBE_CATEGORY_ID = os.getenv("YOUTUBE_CATEGORY_ID", "22")

# X (Twitter) API 設定
X_API_KEY = os.getenv("X_API_KEY", "")
X_API_SECRET = os.getenv("X_API_SECRET", "")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN", "")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET", "")
