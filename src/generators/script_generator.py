"""Gemini API を使った台本生成モジュール"""

import json
import logging
import time

from google import genai
from google.genai import types
from google.genai.errors import ClientError

from src.config import GEMINI_API_KEY, GEMINI_MODEL, CHARACTERS
from src.models import ScriptData

logger = logging.getLogger(__name__)

# キャラクター設定をプロンプト用テキストに整形
_CHARACTER_PROMPT = f"""
## キャラクター設定
- **{CHARACTERS["tsuno"]["name"]}** (tsuno): 毒舌でボケ担当。口が悪く斜に構えているが、どこか憎めない。
- **{CHARACTERS["megane"]["name"]}** (megane): 冷静でクール。ツッコミ・解説担当。知的で落ち着いている。つのを論理的に諭す。
""".strip()

_SYSTEM_PROMPT = f"""
あなたは雑談形式の解説動画の台本ライターです。
2人のキャラクターが掛け合いをしながらテーマについて面白おかしく解説する台本を書いてください。

{_CHARACTER_PROMPT}

## 出力ルール
- セリフは15〜25往復程度（合計30〜50行）
- つのは口語的で砕けた表現を使う
- めがねは丁寧語で論理的に話す
- emotion は "normal", "happy", "angry", "sad", "surprised" のいずれか
- emotion の使用頻度: "normal" と "happy" を中心に使い、"angry" はなるべく使わない（全体の5%以下）
- セリフに読みアノテーション `<>` や `[[]]` は一切付けないこと。プレーンなテキストのみで書く
- note_content はMarkdown形式で1000〜2000文字程度の解説記事。末尾に「動画はこちら: {{youtube_url}}」を含める
- x_post_content は140文字以内のX投稿文（ハッシュタグ含む）。{{youtube_url}} を含める（後から実URLに置換される）

## 出力JSON形式（厳密に従うこと）
{{
  "meta": {{ "theme": "テーマ名", "title": "動画タイトル" }},
  "dialogue": [
    {{ "speaker": "tsuno", "text": "セリフ", "emotion": "感情" }},
    {{ "speaker": "megane", "text": "セリフ", "emotion": "感情" }}
  ],
  "note_content": "# タイトル\\n\\n本文...\\n\\n動画はこちら: {{youtube_url}}",
  "x_post_content": "投稿文 {{youtube_url}} #へぼ談"
}}
""".strip()


class ScriptGenerator:
  """Gemini APIを使って台本を生成するクラス"""

  def __init__(self):
    if not GEMINI_API_KEY:
      raise ValueError(
        "GEMINI_API_KEY が設定されていません。"
        ".env ファイルに GEMINI_API_KEY を設定してください。"
      )
    self.client = genai.Client(api_key=GEMINI_API_KEY)

  def _call_api(self, prompt: str, max_rate_retries: int = 5) -> str:
    """Gemini APIを呼び出す（429レート制限時は自動リトライ）

    Args:
      prompt: ユーザープロンプト
      max_rate_retries: レート制限時の最大リトライ回数

    Returns:
      APIレスポンスのテキスト
    """
    for attempt in range(max_rate_retries + 1):
      try:
        response = self.client.models.generate_content(
          model=GEMINI_MODEL,
          contents=prompt,
          config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.9,
          ),
        )
        return response.text
      except ClientError as e:
        if e.code == 429 and attempt < max_rate_retries:
          wait = 2 ** attempt * 10  # 10s, 20s, 40s, 80s, 160s
          logger.warning(
            "レート制限 (429)。%d秒後にリトライします... (%d/%d)",
            wait, attempt + 1, max_rate_retries,
          )
          time.sleep(wait)
        else:
          raise

  def generate(
    self, theme: str, *, instructions: str | None = None, max_retries: int = 2,
  ) -> ScriptData:
    """テーマから台本を生成する

    Args:
      theme: トークテーマ
      instructions: マークダウン形式の詳細指示（テーマ・趣旨・追加指示など）
      max_retries: JSONパースエラー時のリトライ回数

    Returns:
      ScriptData: 生成された台本データ
    """
    if instructions:
      user_prompt = (
        f"以下の指示に基づいて台本を作成してください。\n\n{instructions}"
      )
    else:
      user_prompt = f"以下のテーマについて台本を作成してください。\n\nテーマ: {theme}"

    for attempt in range(max_retries + 1):
      try:
        logger.info(
          "台本生成中... (試行 %d/%d)", attempt + 1, max_retries + 1
        )
        raw_text = self._call_api(user_prompt)
        data = json.loads(raw_text)
        script = ScriptData.from_dict(data)
        logger.info(
          "台本生成完了: %s（セリフ数: %d）",
          script.meta.title,
          len(script.dialogue),
        )
        return script

      except (json.JSONDecodeError, KeyError) as e:
        logger.warning("台本パースエラー (試行 %d): %s", attempt + 1, e)
        if attempt == max_retries:
          raise RuntimeError(
            f"台本のJSON解析に{max_retries + 1}回失敗しました: {e}"
          ) from e

    raise RuntimeError("台本生成に失敗しました")
