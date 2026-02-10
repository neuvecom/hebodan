# プロジェクト設定

## Claude Code使用時の重要な指示
- **回答言語**: 必ず日本語で回答すること（英語での回答は禁止）
- **出力スタイル**: Explanatory（説明的）モードを使用
  - 実行する操作の理由を明確に説明
  - コードの変更内容を詳細に解説
  - 各ステップの目的と結果を記述

## ドキュメント管理フロー
- ドラフト作成 → レビュー → 本番公開（main）の流れ
- 機能別ドキュメントは`docs/機能名`で分類
- 変更はプルリクエストでレビュー後にマージ

## コミット・PR規則
- コミットメッセージとGitHubのコメントは日本語で記載
- コミットメッセージ形式：`[種類] 変更内容の説明`
  - 例：`[feat] ユーザー認証機能を追加`、`[fix] ログイン時のバリデーションエラーを修正`
- PRタイトルも日本語で記載し、変更内容を簡潔に説明

## 作業ログ管理
- Claude Codeとの会話は作業ログとして`docs-dev/work_log/YYYY-MM-DD.md`に保存・追記
- **重要**: 日付は必ず環境設定の`Today's date`を優先して使用すること（ファイル名や既存の日付に惑わされない）
- 日付形式はYYYY-MM-DD（例：2025-08-14）
- 既存ファイルがある場合は追記、ない場合は新規作成

## ブランチ運用
- main: 公開ドキュメント（直接プッシュ禁止、PRベースで更新）
- docs/*: ドキュメント更新・追加用ブランチ（例：docs/user-auth、docs/api-guide）

## デプロイ
- **Hosting**: GitHub Actions（mainへのプッシュで自動デプロイ）
- **Functions**: 手動デプロイ `firebase deploy --only functions`
  - `functions/index.js` を変更した場合は手動でデプロイが必要

## よく使うコマンド
- ドキュメント更新開始: `git checkout main && git pull origin main && git checkout -b docs/更新内容`
- 変更確認: `git status && git diff`
- コミット・プッシュ: `git add . && git commit -m "[docs] 変更内容" && git push origin ブランチ名`
- Functionsデプロイ: `firebase deploy --only functions`
- 手動作業開始: `dev_tools/scripts/start_work.sh`
- 手動作業終了: `dev_tools/scripts/end_work.sh`
- 手動休憩保存: `dev_tools/scripts/take_break.sh`

## バージョン管理
- **バージョン形式**: メジャー.マイナー.パッチ（例：v1.0.0）
- **リリースタグ**: Gitタグでバージョン管理
- **変更履歴**: CHANGELOG.mdで管理

## コードスタイル
- インデント: 2スペース
- 文字コード: UTF-8
- 改行コード: LF
