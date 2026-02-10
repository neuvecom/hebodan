#!/bin/bash
# Noto Sans JP フォントをダウンロードして assets/fonts/ に配置するスクリプト

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FONTS_DIR="$PROJECT_ROOT/assets/fonts"

mkdir -p "$FONTS_DIR"

FONT_URL="https://github.com/google/fonts/raw/refs/heads/main/ofl/notosansjp/NotoSansJP%5Bwght%5D.ttf"
FONT_FILE="$FONTS_DIR/NotoSansJP-Bold.ttf"

if [ -f "$FONT_FILE" ]; then
  echo "フォントは既に存在します: $FONT_FILE"
  exit 0
fi

echo "Noto Sans JP Bold をダウンロード中..."
curl -L -o "$FONT_FILE" "$FONT_URL"

if [ $? -eq 0 ] && [ -f "$FONT_FILE" ]; then
  echo "ダウンロード完了: $FONT_FILE"
else
  echo "エラー: フォントのダウンロードに失敗しました"
  exit 1
fi
