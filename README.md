# Hebodan (へぼ談)

トークテーマ1つから YouTube動画・Shorts・note記事・X投稿文を一気通貫で自動生成する Python アプリケーション。

## 概要

2人のキャラクター（リリン＆つくよみ）が掛け合いをしながらテーマを解説する雑談動画を、テーマ入力だけで全自動生成します。

### 生成コンテンツ
- **YouTube動画 (16:9)**: 横長の雑談解説動画
- **Shorts/TikTok動画 (9:16)**: スマホ向け縦長動画
- **note記事**: Markdown形式のブログ記事
- **X投稿文**: 宣伝用の短文

### キャラクター
| 名前 | 役割 | 性格 |
|------|------|------|
| リリン (Ririn) | 毒舌 / ボケ | 口が悪く斜に構えているが、どこか憎めない |
| つくよみ (Tsukuyomi) | 冷静 / ツッコミ・解説 | 知的で落ち着いている。リリンを論理的に諭す |

## 技術スタック
- **言語**: Python 3.10+
- **LLM**: Gemini API (`google-generativeai`) — 台本・記事・SNS文の生成
- **音声合成**: COEIROINK API v2 (`localhost:50032`)
- **動画生成**: MoviePy + Pillow — Pythonコードのみで完結

## ディレクトリ構成

```
hebodan/
├── src/
│   ├── main.py                   # パイプライン実行エントリポイント
│   ├── config.py                 # 設定管理
│   ├── models.py                 # データモデル
│   ├── generators/
│   │   ├── script_generator.py   # Gemini台本生成
│   │   ├── audio_generator.py    # COEIROINK音声合成
│   │   └── video_composer.py     # MoviePy動画合成
│   └── utils/
│       └── text_renderer.py      # PIL日本語テキスト描画
├── assets/
│   ├── images/                   # キャラクター画像
│   ├── audio/                    # 生成音声（一時）
│   └── fonts/                    # 日本語フォント
├── output/                       # 最終成果物出力先
└── scripts/
    └── download_font.sh          # フォントダウンロード
```

## セットアップ

```bash
# 1. 依存インストール
pip install -r requirements.txt
# または uv を使用する場合:
# uv pip install -r requirements.txt

# 2. 日本語フォントを取得
bash scripts/download_font.sh

# 3. 環境変数を設定
cp .env.example .env
# .env を編集して以下を設定:
#   GEMINI_API_KEY    — Gemini APIキー
#   RIRIN_SPEAKER_UUID / TSUKUYOMI_SPEAKER_UUID — COEIROINK話者UUID
```

## 使い方

```bash
# COEIROINKを起動した状態で実行
python -m src.main "AIの未来"
```

`output/YYYYMMDD_HHMMSS/` 配下に以下が生成されます:
- `landscape.mp4` — YouTube動画 (16:9)
- `portrait.mp4` — Shorts/TikTok動画 (9:16)
- `note.md` — note記事
- `x_post.txt` — X投稿文
- `script.json` — 生成された台本

## 動画合成の特徴

- **横長 (16:9)**: リリン左・つくよみ右配置、字幕は下部中央
- **縦長 (9:16)**: リリン上部・つくよみ下部配置、字幕は中間エリア
- **アクティブスピーカー演出**: 話しているキャラクターを明るく拡大表示、非アクティブ側を暗くする

## ライセンス

Private
