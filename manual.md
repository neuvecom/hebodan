# Hebodan（へぼ談）マニュアル

YouTube 動画自動生成パイプライン。テーマを入力すると、Gemini API で台本生成 → COEIROINK で音声合成 → MoviePy で動画合成を自動で行います。

## クイックスタート

### コマンド体系

`python -m src <サブコマンド>` で全操作を統合的に実行できます。

```bash
# 全工程インタラクティブ実行（メインで使用）
.venv/bin/python -m src run "AIの未来"
.venv/bin/python -m src run neta/theme.md
.venv/bin/python -m src run -s output/XXXX/script.json   # 既存台本から再開

# 個別コマンド
.venv/bin/python -m src generate "AIの未来"     # 動画生成のみ
.venv/bin/python -m src generate -d "AIの未来"  # 台本+背景のみ（下書き）
.venv/bin/python -m src upload output/XXXX      # YouTubeアップロード
.venv/bin/python -m src shorts output/XXXX      # Shortsアップロード
.venv/bin/python -m src post output/XXXX        # X投稿
.venv/bin/python -m src status output/XXXX      # 出力ディレクトリの状態表示
```

### `run` のインタラクティブフロー

`run` コマンドは対話的に全工程を進めます。各ステップで確認を挟むため、途中で中断・再開が可能です。

```
[1] 台本＋背景を生成中...
    → 生成完了: output/20260212_200000/script.json

[2] 台本を確認しますか？ [Y/n/edit]
    y    → 台本の要約を表示（タイトル、セリフ数、冒頭5行）
    edit → $EDITOR で script.json を開いて編集
    n    → スキップ

[3] 音声＋動画を生成しますか？ [Y/n]
    → 音声生成 → サムネイル → 横長動画 → 縦長動画

    続行しますか？ [Y/edit/n]
    y    → アップロードへ進む
    edit → $EDITOR で台本を修正し、音声＋動画を再生成
    n    → 中断（-s で再開可能）

[5] YouTube にアップロードしますか？ [Y/n]
    → アップロード完了: https://youtu.be/xxxxx

[6] YouTube Studio で動画を公開してください
    ※ 非公開のままだと X 投稿時にサムネイルが展開されません
    公開設定が完了したら Enter を押してください...

[7] Shorts もアップロードしますか？ [Y/n]
    → アップロード完了: https://youtu.be/yyyyy

[8] X に投稿しますか？ [Y/n]
    ※ 動画が非公開の場合、サムネイルは展開されません
    → 投稿完了

完了サマリー:
  本編: https://youtu.be/xxxxx
  Shorts: https://youtu.be/yyyyy
  残りの手動作業:
    note記事投稿 / ニコニコ / TikTok
```

途中で `n` を選んで中断した場合、以下で再開できます:

```bash
.venv/bin/python -m src run -s output/YYYYMMDD_HHMMSS/script.json
```

---

## 全体ワークフロー

```
【全自動モード】
1. 動画生成         .venv/bin/python -m src.main "テーマ"
2. 読み上げチェック   生成された動画を確認
3. 台本修正          script.json を手動編集（読みの修正など）
4. 再生成            .venv/bin/python -m src.main -s output/YYYYMMDD_HHMMSS/script.json
5. YouTube投稿       .venv/bin/python -m src.upload output/YYYYMMDD_HHMMSS
6. X投稿            .venv/bin/python -m src.post_x output/YYYYMMDD_HHMMSS
7. その他投稿        TikTok / ニコニコ / note → 手動

【下書きモード（台本を先にチェックしたい場合）】
1. 下書き生成        .venv/bin/python -m src.main -d "テーマ"
2. 台本チェック       output/YYYYMMDD_HHMMSS/script.json を確認・編集
3. 再生成            .venv/bin/python -m src.main -s output/YYYYMMDD_HHMMSS/script.json
4. YouTube投稿〜     上記と同じ
```

---

## セットアップ

### 1. Python 仮想環境

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 環境変数（.env）

プロジェクトルートに `.env` ファイルを作成し、以下を設定します。

```env
# Gemini API（必須）
GEMINI_API_KEY=your_gemini_api_key

# COEIROINK キャラクター設定（必須）
TSUNO_SPEAKER_UUID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
TSUNO_STYLE_ID=0
MEGANE_SPEAKER_UUID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
MEGANE_STYLE_ID=0

# X (Twitter) API（X投稿する場合のみ）
X_API_KEY=your_api_key
X_API_SECRET=your_api_secret
X_ACCESS_TOKEN=your_access_token
X_ACCESS_TOKEN_SECRET=your_access_token_secret
```

### 3. COEIROINK

音声合成に [COEIROINK](https://coeiroink.com/) を使用します。
動画生成・再生成時は COEIROINK を起動しておいてください（デフォルト: `http://localhost:50032`）。

### 4. フォント

`assets/fonts/` に `TAユニバーサルライン_DSP_E.ttf` を配置してください。
`.env` で `FONT_NAME` を変更すれば別フォントも使用できます。

### 5. YouTube API セットアップ

YouTube にコマンドからアップロードするための設定です。

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. プロジェクトを作成
3. 「YouTube Data API v3」を有効化
4. 「認証情報」→「OAuth 2.0 クライアント ID」を作成（アプリの種類: デスクトップアプリ）
5. JSON をダウンロードして `credentials/youtube_client_secret.json` に配置
6. 初回認証を実行:

```bash
python scripts/setup_youtube_auth.py
```

ブラウザが開くので Google アカウントでログインすると、トークンが `credentials/youtube_token.json` に保存されます。以降は自動で再利用されます。

### 6. X (Twitter) API セットアップ

1. [X Developer Portal](https://developer.x.com/) でアプリを作成
2. 「Keys and Tokens」からキーとトークンを取得
3. `.env` に `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET` を設定

---

## 使用料金の確認方法

各 API の使用量・料金は Web ダッシュボードで確認します。API 経由で残高を取得するエンドポイントはどちらも提供されていません。

| サービス | 課金方式 | 確認先 |
|---|---|---|
| Gemini API | 無料枠あり / 有料は従量課金 | [AI Studio Dashboard](https://aistudio.google.com/) → Usage and Limits |
| X (Twitter) API | Pay-Per-Use（クレジット事前購入） | [Developer Console](https://developer.x.com/) |

- **Gemini API**: Google Cloud Billing と連携しており、[Cloud Console](https://console.cloud.google.com/billing) で支出トラッキングが可能。予算アラート機能で自動通知も設定できます。
- **X API**: クレジットを事前購入し、API コールごとに残高が減る方式。残高は Developer Console で確認します。

---

## コマンド一覧

### 動画生成

```bash
# テーマキーワードから全自動生成
.venv/bin/python -m src.main "AIの未来"

# マークダウンファイルで詳細指示
.venv/bin/python -m src.main neta/asa-touketsu.md

# 下書きモード（台本+背景だけ生成して止める → 確認・編集用）
.venv/bin/python -m src.main -d neta/asa-touketsu.md

# 既存の台本から再生成（音声+動画のみ）
.venv/bin/python -m src.main -s output/20260210_123456/script.json

# サムネイルだけ再生成
.venv/bin/python -m src.main -s output/20260210_123456/script.json -t
```

### YouTube アップロード

```bash
# private（非公開）でアップロード（デフォルト）
.venv/bin/python -m src.upload output/20260210_123456

# public（公開）でアップロード
.venv/bin/python -m src.upload output/20260210_123456 --public
```

アップロード後、YouTube URL を埋め込んだ以下のファイルが生成されます:
- `note.md` — note 記事用テキスト
- `x_post.txt` — X 投稿用テキスト
- `upload_info.json` — アップロード情報

### X 投稿

```bash
.venv/bin/python -m src.post_x output/20260210_123456
```

`x_post.txt` の内容を X に投稿します。先に `src.upload` を実行して YouTube URL 入りの投稿文を生成しておく必要があります。

---

## テーマファイル（.md）の書き方

キーワードだけでなく、マークダウンファイルで趣旨や追加指示を渡せます。

```markdown
# AIの未来

## 趣旨
AIが人間の仕事を奪うのかという議論を、具体例を交えて面白おかしく解説する

## 指示
- つのにAI推進派をやらせる
- 具体的な事例を3つ以上入れる
- 最後はポジティブにまとめる
- 専門用語には読みアノテーションを付ける
```

- `# 見出し` がテーマキーワード（背景画像の生成にも使用）
- `## 趣旨` / `## 指示` などの内容はすべて台本生成 AI への指示になる
- 見出し名や構成は自由（全文がそのまま Gemini に渡される）

---

## 読みアノテーション

台本（`script.json`）のセリフ内で `漢字<よみがな>` と書くと、音声合成時に正しい読みが使われます。画面上のテロップには漢字のみが表示されます。

```
大賢者<だいけんじゃ>が言うには...
```

- 音声: 「だいけんじゃ が言うには...」
- テロップ: 「大賢者が言うには...」

台本生成時に Gemini が自動で付与しますが、手動で script.json を編集して追加・修正もできます。

### 読み辞書（reading_dict.txt）

毎回同じ読みを script.json で編集するのが手間な場合、プロジェクトルートに `reading_dict.txt` を作成すると TTS 時に自動で適用されます。

```
# 読み辞書（1行に1エントリ、「単語<よみ>」形式）
大賢者<だいけんじゃ>
異世界<いせかい>
魔導具<まどうぐ>
```

- インラインアノテーションと同じ `単語<よみ>` 形式で記載
- `#` で始まる行はコメント、空行はスキップ
- script.json 内のインラインアノテーションが辞書より優先される
- テロップ表示には影響しない（漢字のまま表示）
- ファイルがなくても正常に動作する

### 表示専用テキスト（[[...]]）

セリフ内で `[[テキスト]]` と書くと、テロップには表示されますが音声では読み上げられません。カッコ付きの補足説明などに使えます。

```
サーモヒーター[[（凍結防止帯<とうけつぼうしたい>）]]つけるか
```

- 音声: 「サーモヒーターつけるか」
- テロップ: 「サーモヒーター（凍結防止帯）つけるか」

`[[]]` 内でも読みアノテーション `<>` は使用可能です（テロップ表示時に漢字のみ残ります）。台本生成時に Gemini が適宜使いますが、手動で script.json に追加もできます。

---

## 出力ファイル

`output/YYYYMMDD_HHMMSS/` に以下が生成されます:

| ファイル | 内容 |
|---|---|
| `script.json` | 台本（セリフ・メタ情報・note/X テキスト） |
| `landscape.mp4` | 横長動画 (1920x1080) — YouTube 用 |
| `portrait.mp4` | 縦長動画 (1080x1920) — Shorts / TikTok 用 |
| `thumbnail.png` | サムネイル画像 (1280x720) |
| `bg_landscape.png` | 背景画像（横） |
| `bg_portrait.png` | 背景画像（縦） |
| `note.md` | note 記事テキスト（`src.upload` 後に YouTube URL 入り） |
| `x_post.txt` | X 投稿テキスト（`src.upload` 後に YouTube URL 入り） |
| `upload_info.json` | アップロード情報（`src.upload` 後に生成） |

---

## ユーティリティスクリプト

`scripts/` 配下のスクリプトは初期セットアップやアセット管理用です。

```bash
# キャラクター表情画像の一括生成（Gemini API 使用）
python scripts/generate_character_assets.py
python scripts/generate_character_assets.py --force  # 全て再生成

# オープニング SE の生成
python scripts/generate_opening_se.py

# オープニング音声の生成（COEIROINK 起動必須）
python scripts/generate_opening_voice.py

# キャラクター画像の背景透過処理（rembg 使用）
python scripts/bake_transparency.py

# YouTube OAuth2 初回認証
python scripts/setup_youtube_auth.py
```

---

## アセット構成

```
assets/
├── audio/se/          # SE・OP音声（opening.wav, opening_tsuno.wav, opening_megane.wav）
├── fonts/             # フォントファイル（.ttf）
└── images/
    ├── logo/          # ロゴ（logo_normal.png: OP用, logo_white.png: 本編用）
    ├── tsuno/         # つの表情画像（{emotion}_{open|closed}.png × 5表情）
    ├── megane/        # めがね表情画像（同上）
    ├── chara.png      # キャラ原画（左右分割の元画像）
    ├── tsuno_ref.png  # つのリファレンス画像（表情生成用）
    └── megane_ref.png # めがねリファレンス画像（表情生成用）
```

表情は `normal`, `happy`, `angry`, `sad`, `surprised` の 5 種 × 口の開閉 2 種 = 10 画像/キャラ。

---

## script.json の構造

```json
{
  "meta": {
    "theme": "テーマ名",
    "title": "動画タイトル"
  },
  "dialogue": [
    { "speaker": "tsuno", "text": "セリフ", "emotion": "happy" },
    { "speaker": "megane", "text": "セリフ", "emotion": "normal" }
  ],
  "note_content": "# タイトル\n\n本文...\n\n動画はこちら: {youtube_url}",
  "x_post_content": "投稿文 {youtube_url} #へぼ談"
}
```

- `speaker`: `tsuno`（つの）または `megane`（めがね）
- `emotion`: `normal`, `happy`, `angry`, `sad`, `surprised`
- `{youtube_url}`: `src.upload` 実行時に実際の YouTube URL に置換される
