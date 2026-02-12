#　クイックスタート

以下のセットアップが終了している前提です。

- python
- GeminiのAPI
- YoutubeのAPI
- XのAPI

## 動画制作

- 仮想環境に入る

```
source /Users/yoshiharusato/MyProducts/WEB/Youtube/hebodan/.venv/bin/activate
(hebodan) xxx@xxxx hebodan % python -m src.post_x output/20260211_124924 
```

- `.venv/bin/`をつけることでコマンドを仮想環境から直接実施できる

```
# 1a 通常の自動生成コマンド
python -m src.main "AIの未来"
.venv/bin/python -m src.main "AIの未来"

# 1b 詳細な指示で生成するコマンド
python -m src.main neta/asa-touketsu.md
.venv/bin/python -m src.main neta/asa-touketsu.md

# 1c 台本をチェックするステップで動画作成(メインで使用)
python -m src.main -d "AIの未来"
python -m src.main -d neta/asa-touketsu.md

.venv/bin/python -m src.main -d "AIの未来"
.venv/bin/python -m src.main -d neta/asa-touketsu.md

# 2 手動で台本チェック

# 3 台本チェック後に作業を続行
python -m src.main -s output/20260210_123456/script.json
.venv/bin/python -m src.main -s output/20260210_123456/script.json

# 3' サムネイルのみ再作成
python -m src.main -s output/20260210_123456/script.json -t
.venv/bin/python -m src.main -s output/20260210_123456/script.json -t

# 4 生成された動画を確認

# 5a Youtubeに動画を非公開でアップロード(メインで使用)
## note.mdやx_post.txt、upload_info.jsonなどが生成される
python -m src.upload output/20260210_123456
.venv/bin/python -m src.upload output/20260210_123456

# 6 ダッシュボードを確認して公開
https://studio.youtube.com/channel/UChh3-OwADcoDem5abqD1m4w

# 5b Youtubeに動画をアップロードして公開(あまり使用しない)
python -m src.upload output/20260210_123456 --public
.venv/bin/python -m src.upload output/20260210_123456 --public

# 7 YoutubeのURLを含めてXに投稿
python -m src.post_x output/20260210_123456
.venv/bin/python -m src.post_x output/20260210_123456

# 本編アップロード後に実行
.venv/bin/python -m src.upload_shorts output/20260210_123456

# 8 noteなどを手動で公開
- shortアップロード
- note投稿
- niconico投稿
https://garage.nicovideo.jp/niconico-garage/video/series/549523
- tiktoc
https://www.tiktok.com/tiktokstudio/content

```
