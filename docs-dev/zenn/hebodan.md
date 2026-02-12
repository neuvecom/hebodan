---
title: "Pythonだけで YouTube 動画を全自動生成するパイプラインを作った話"
emoji: "🎬"
type: "tech"
topics: ["Python", "MoviePy", "GeminiAPI", "YouTube", "自動化"]
published: false
---

## はじめに

「テーマを入力するだけで、YouTube の動画が1本できあがる」

そんなパイプラインを Python だけで構築しました。Gemini API で台本を生成し、COEIROINK で音声合成し、MoviePy で動画を合成する。YouTube へのアップロードや X への投稿まで、コマンドひとつで完結します。

この記事では、個人開発の YouTube チャンネル「へぼ談」を支えるこのシステムの全体像と、構築の過程で得た技術的な知見を共有します。

## 何ができるのか

```bash
python -m src run "AIの未来"
```

このコマンドを実行すると、以下が自動生成されます。

- 2 人のキャラクターが掛け合う台本（30〜50 セリフ）
- 各セリフの音声（COEIROINK による合成音声）
- テーマに合った背景画像（Gemini API による画像生成）
- 横長動画 (1920x1080) — YouTube 本編用
- 縦長動画 (1080x1920) — Shorts / TikTok 用
- サムネイル画像 (1280x720)
- note 記事テキスト、X 投稿文

さらにインタラクティブに YouTube アップロード、Shorts アップロード、X 投稿まで進められます。

## 技術スタック

| 役割 | 技術 |
|---|---|
| 台本生成 | Gemini API（`google-genai`） |
| 音声合成 | COEIROINK v2 API（ローカル稼働） |
| 動画合成 | MoviePy 2.x + Pillow + NumPy |
| 背景画像生成 | Gemini API（画像生成モデル） |
| YouTube アップロード | YouTube Data API v3 |
| X 投稿 | X API v2（tweepy） |
| 設定管理 | python-dotenv |
| 開発支援 | Claude Code（AI ペアプログラミング） |

外部の動画編集ソフト（YMM4 など）は一切使わず、Python のみで完結しています。

## アーキテクチャ

```
テーマ入力
  ↓
ScriptGenerator（Gemini API）
  → 台本 JSON（セリフ・表情・メタ情報・SNS テキスト）
  ↓
BackgroundGenerator（Gemini API 画像生成）
  → 背景画像（横長・縦長）
  ↓
AudioGenerator（COEIROINK API）
  → WAV ファイル群（セリフごと）
  ↓
VideoComposer（MoviePy）
  → landscape.mp4（横長）
  → portrait.mp4（縦長）
  ↓
YouTube / X アップローダー
  → 自動投稿
```

### ディレクトリ構成

```
src/
├── cli.py                      # 統合 CLI（argparse + サブコマンド）
├── main.py                     # パイプライン統合エントリポイント
├── models.py                   # dataclass 定義
├── config.py                   # 全設定の中央管理
├── generators/
│   ├── script_generator.py     # Gemini 台本生成
│   ├── audio_generator.py      # COEIROINK 音声合成
│   ├── video_composer.py       # MoviePy 動画合成
│   ├── background_generator.py # Gemini 背景画像生成
│   └── thumbnail_generator.py  # サムネイル生成
├── uploaders/
│   ├── youtube_uploader.py     # YouTube Data API
│   └── x_poster.py             # X API
└── utils/
    ├── text_renderer.py        # PIL テロップ描画
    ├── character_assets.py     # キャラ画像ロード
    ├── audio_analyzer.py       # リップシンク解析
    └── reading_annotations.py  # 読みアノテーション処理
```

## 台本生成 — Gemini API の活用

### プロンプト設計

台本生成の核心は、Gemini API へのプロンプト設計です。システムプロンプトにキャラクター設定と出力フォーマットを厳密に指定し、JSON で構造化された台本を出力させます。

```python
_SYSTEM_PROMPT = """
あなたは雑談形式の解説動画の台本ライターです。
2人のキャラクターが掛け合いをしながらテーマについて面白おかしく解説する台本を書いてください。

## キャラクター設定
- **つの** (tsuno): 毒舌でボケ担当。口が悪く斜に構えているが、どこか憎めない。
- **めがね** (megane): 冷静でクール。ツッコミ・解説担当。知的で落ち着いている。

## 出力ルール
- セリフは15〜25往復程度（合計30〜50行）
- emotion は "normal", "happy", "angry", "sad", "surprised" のいずれか
- shorts_skip: ショート動画で省略しても会話が成立するセリフに true を付ける
...
"""
```

Gemini の `response_mime_type="application/json"` を指定することで、確実に JSON 形式で返してもらいます。パースエラー時はリトライし、429 レート制限には指数バックオフで対応しています。

### 台本データモデル

```python
@dataclass
class DialogueLine:
    speaker: str        # "tsuno" or "megane"
    text: str           # セリフ本文
    emotion: str        # 表情（5 種類）
    shorts_skip: bool   # Shorts で省略可能か

@dataclass
class ScriptData:
    meta: ScriptMeta           # テーマ・タイトル
    dialogue: list[DialogueLine]
    note_content: str          # note 記事テンプレート
    x_post_content: str        # X 投稿文テンプレート
```

`shorts_skip` は後から追加したフィールドです。Shorts の 3 分制限に収めるため、Gemini に「脱線・雑談・補足の行にフラグを付けて」と指示します。縦動画の推定尺が 3 分を超える場合のみ、このフラグが付いたセリフを除外します。

## 音声合成 — COEIROINK との連携

### TTS 前処理パイプライン

音声合成の前に、テキストを 4 段階で前処理します。

```
元テキスト: サーモヒーター[[（凍結防止帯<とうけつぼうしたい>）]]つけるか
    ↓ ① 表示専用テキスト除去   → サーモヒーターつけるか
    ↓ ② 読み辞書の適用         → サーモヒーターつけるか
    ↓ ③ 読みアノテーション変換  → サーモヒーターつけるか
    ↓ ④ COEIROINK API 送信
```

- `[[...]]` は画面には表示するが読み上げない「表示専用テキスト」
- `漢字<よみがな>` は TTS 向けの読み指定。テロップでは漢字のみ表示
- `reading_dict.txt` で頻出単語の読みを一括管理

### 記号のみテキストへの対応

「…？」のような記号だけのセリフは COEIROINK が 500 エラーを返します。正規表現で発音可能な文字の有無を判定し、なければ 0.5 秒の無音 WAV を生成して回避しています。

```python
if not re.search(r"[\w\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]", tts_text):
    wav_data = self._generate_silence(0.5)
    output_path.write_bytes(wav_data)
    continue
```

## 動画合成 — MoviePy で実現した演出

### リップシンク（口パク）

キャラクターの口パクは、WAV の振幅解析で実現しています。

```python
def analyze_mouth_states(wav_path, fps, threshold=0.15, min_open_frames=2):
    """各フレームの口の開閉状態を振幅閾値で判定する"""
```

WAV を読み込み、フレームごとの RMS 振幅を計算し、閾値を超えたフレームを「口が開いている」と判定します。`min_open_frames` でチャタリング（口がパクパクしすぎる）を防止しています。

各キャラクターは表情 5 種 x 口の開閉 2 種 = 10 枚の画像を持ち、セリフの `emotion` と口パク判定の組み合わせで、フレームごとに適切な画像を選択します。

### キャラクターアニメーション

キャラクターは sin 関数で「ふわふわ浮遊」します。

```python
# ふわふわ浮遊（8px 振幅、0.4Hz）
y_offset = 8 * math.sin(2 * math.pi * 0.4 * t)
```

ロゴは「プルプル震え」で存在感を出します。

```python
# プルプル震え（3px 振幅、2.5〜3Hz のランダム周波数）
x_shake = 3 * math.sin(2 * math.pi * random_freq * t)
```

### 横長と縦長で異なるレイアウト

横長（16:9）は従来のゆっくり解説風：キャラが左右に立ち、下部にテロップ。

縦長（9:16）は LINE チャット風に全面書き換えしました。

- つの → 左側、LINEグリーンの吹き出し、白文字
- めがね → 右側、白の吹き出し、黒文字
- 会話が下から上へ積み上がっていく
- 過去のメッセージは半透明化
- 3 レイヤー構成：背景 → ロゴ（プルプル） → チャットオーバーレイ（RGBA）

PIL の `ImageDraw.rounded_rectangle()` で角丸吹き出しを描画し、`alpha.point(lambda)` で過去メッセージの半透明化を実現しています。

### オープニングとエンディング

**OP（7 秒）**: 白背景にロゴがズームイン → タイトル表示 → SE + ボイス

**ED**: チャンネル登録誘導テキスト → 撤収雑談ボイス（字幕なし） → キャラのみフェードアウト。横長ではキャラが浮遊、縦長ではブロック崩しのボールのように跳ね回る演出です。

```python
def _bounce(t, total, start, end):
    """ピンポン反復（0→1→0→1...）"""
    pos = start + (end - start) * (t / total)
    pos_mod = pos % 2.0
    return pos_mod if pos_mod <= 1.0 else 2.0 - pos_mod
```

## 背景画像生成 — Gemini の画像生成

テーマに連動した背景画像を Gemini API で自動生成しています。プロンプトで「暗めのトーン」「下部はテロップ用に特に暗く」「文字やキャラクターは含めない」と指定し、動画の背景に適した画像を生成します。

```python
prompt = f"""
Generate a background image for a YouTube video about: {theme}
- Style: atmospheric, cinematic, slightly blurred/bokeh feel
- Color tone: dark and moody
- The bottom 20% should be especially dark for subtitle readability
- No text, no characters, no faces, no logos
"""
```

レート制限時は指数バックオフで自動リトライし、生成に失敗した場合はソリッドカラー（濃紺）にフォールバックします。

## キャラクター画像の生成と透過処理

### Gemini によるキャラ画像生成

1 枚のキャラ原画（`chara.png`）を左右に分割し、それぞれをリファレンスとして Gemini API に表情バリエーションを生成させます。

```
chara.png → 左右分割
  → tsuno_ref.png / megane_ref.png
  → Gemini API で表情 5 種 x 口 2 種 = 10 枚/キャラ
  → rembg で背景透過
```

### rembg による背景除去

当初は PIL の flood-fill で背景を除去しようとしましたが、グラデーションのある画像では誤爆が頻発。最終的に rembg（U2Net）を採用しました。

```bash
pip install rembg[cpu]
python scripts/bake_transparency.py
```

画像ファイル自体にアルファチャンネルを焼き込む方式にし、コード側では透過処理を一切行いません。MoviePy では `ImageClip(arr, transparent=True)` でアルファを自動的にマスクとして利用できます。

:::message
**学び**: PIL の `convert("RGBA")` は形式上のアルファチャンネルを付与するだけで、alpha=255（不透明）で全ピクセルが埋まります。`sips -g hasAlpha` も形式チェックのみ。実際の透過は画像のピクセルデータで確認する必要があります。
:::

## 統合 CLI — ワークフローの一元化

開発初期は 4 つのコマンドを順番に手動実行していました。

```bash
python -m src.main "テーマ"          # 動画生成
python -m src.upload output/XXXX     # YouTube
python -m src.upload_shorts output/XXXX  # Shorts
python -m src.post_x output/XXXX     # X 投稿
```

これを統合 CLI にまとめ、インタラクティブに全工程を進められるようにしました。

```bash
python -m src run "AIの未来"
```

各ステップで `[Y/n]` の確認を挟み、台本の確認では `edit` と入力すると `$EDITOR` で script.json を開けます。途中で中断しても `-s` オプションで再開可能です。

```python
class HebodanCLI:
    def cmd_run(self, args):
        """インタラクティブ全工程"""
        # [1] 台本＋背景を生成
        # [2] 台本を確認しますか？ [Y/n/edit]
        # [3] 音声＋動画を生成しますか？ [Y/n]
        #     動画を確認してから Enter...
        # [5] YouTube にアップロードしますか？ [Y/n]
        # [6] Shorts もアップロードしますか？ [Y/n]
        # [7] X に投稿しますか？ [Y/n]
        # [8] 完了サマリー
```

argparse の subparsers で `run` / `generate` / `upload` / `shorts` / `post` / `status` の各サブコマンドを管理。既存の個別コマンド（`python -m src.main` 等）もそのまま動作する後方互換を維持しています。

## 開発プロセス — Claude Code との協働

このプロジェクトは、ほぼ全てのコードを Claude Code（AI ペアプログラミングツール）との対話で開発しました。

### 初期構築（Day 1）

最初のコミットで、以下のコアシステムを一気に実装しました。

- データモデル（dataclass）
- Gemini 台本生成
- COEIROINK 音声合成
- MoviePy 動画合成（横長・縦長）
- CLI エントリポイント

### 段階的な機能追加

以降は実際に動画を作って投稿しながら、対話的に改善を重ねました。

1. **OP/ED の追加** — 動画としての体裁を整える
2. **表情・口パク** — キャラの表現力を向上
3. **LINE チャット風の縦動画** — Shorts 向けに全面リデザイン
4. **YouTube/X 投稿の自動化** — 手動作業を削減
5. **読みアノテーション** — 音声品質の向上
6. **統合 CLI** — ワークフロー全体の効率化

### エラーとの戦い

実運用で遭遇したエラーと対処も記録しておきます。

| エラー | 原因 | 対処 |
|---|---|---|
| COEIROINK 500 | 記号のみテキスト（`…？`） | 無音 WAV を生成 |
| YouTube サムネイル 403 | 電話番号認証未完了 | try-except でグレースフル処理 |
| X 投稿 403/401 | アプリ権限が Read のみ | Read and Write に変更 |
| Shorts として認識されない | API 経由ではタグが必要 | タイトルに `#Shorts` を自動付与 |
| 動画倍速でピッチ上昇 | MoviePy の `with_speed_scaled()` | shorts_skip タグで自然に尺を調整 |

## 今後の展望

- テーマのネタ帳を自動で消化する定期実行（GitHub Actions）
- 視聴データに基づくサムネイル / タイトルの A/B テスト
- より自然な音声のための TTS エンジン検討

## まとめ

Python と各種 API を組み合わせることで、テーマ入力から YouTube 投稿までを全自動化できました。MoviePy 2.x は動画編集ソフトなしでかなりの表現ができますし、Gemini API は台本・画像の両方で活用できます。

個人開発の YouTube チャンネル運営で「コンテンツ制作の自動化」に興味がある方の参考になれば幸いです。

:::message
リポジトリは非公開ですが、アーキテクチャや技術的な質問があればコメントでお気軽にどうぞ。
:::
