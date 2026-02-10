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
FONT_NAME = os.getenv("FONT_NAME", "NotoSansJP-Bold.ttf")
FONT_PATH = FONTS_DIR / FONT_NAME

# Gemini API 設定
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# COEIROINK API 設定
COEIROINK_HOST = os.getenv("COEIROINK_HOST", "http://localhost:50032")

# キャラクター設定
CHARACTERS = {
  "ririn": {
    "speaker_uuid": os.getenv("RIRIN_SPEAKER_UUID", ""),
    "style_id": int(os.getenv("RIRIN_STYLE_ID", "0")),
    "image": "ririn.png",
    "name": "リリン",
  },
  "tsukuyomi": {
    "speaker_uuid": os.getenv("TSUKUYOMI_SPEAKER_UUID", ""),
    "style_id": int(os.getenv("TSUKUYOMI_STYLE_ID", "0")),
    "image": "tsukuyomi.png",
    "name": "つくよみ",
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
