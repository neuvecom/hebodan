"""Gemini API を使った台本生成モジュール"""

import json
import logging

import google.generativeai as genai

from src.config import GEMINI_API_KEY, GEMINI_MODEL, CHARACTERS
from src.models import ScriptData

logger = logging.getLogger(__name__)

# キャラクター設定をプロンプト用テキストに整形
_CHARACTER_PROMPT = f"""
## キャラクター設定
- **{CHARACTERS["ririn"]["name"]}** (ririn): 毒舌でボケ担当。口が悪く斜に構えているが、どこか憎めない。
- **{CHARACTERS["tsukuyomi"]["name"]}** (tsukuyomi): 冷静でクール。ツッコミ・解説担当。知的で落ち着いている。リリンを論理的に諭す。
""".strip()

_SYSTEM_PROMPT = f"""
あなたは雑談形式の解説動画の台本ライターです。
2人のキャラクターが掛け合いをしながらテーマについて面白おかしく解説する台本を書いてください。

{_CHARACTER_PROMPT}

## 出力ルール
- セリフは15〜25往復程度（合計30〜50行）
- リリンは口語的で砕けた表現を使う
- つくよみは丁寧語で論理的に話す
- emotion は "normal", "happy", "angry", "sad", "surprised" のいずれか
- note_content はMarkdown形式で1000〜2000文字程度の解説記事
- x_post_content は140文字以内のX投稿文（ハッシュタグ含む）

## 出力JSON形式（厳密に従うこと）
{{
  "meta": {{ "theme": "テーマ名", "title": "動画タイトル" }},
  "dialogue": [
    {{ "speaker": "ririn", "text": "セリフ", "emotion": "感情" }},
    {{ "speaker": "tsukuyomi", "text": "セリフ", "emotion": "感情" }}
  ],
  "note_content": "# タイトル\\n\\n本文...",
  "x_post_content": "投稿文 #へぼ談"
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
    genai.configure(api_key=GEMINI_API_KEY)
    self.model = genai.GenerativeModel(
      model_name=GEMINI_MODEL,
      system_instruction=_SYSTEM_PROMPT,
    )

  def generate(self, theme: str, max_retries: int = 2) -> ScriptData:
    """テーマから台本を生成する

    Args:
      theme: トークテーマ
      max_retries: JSONパースエラー時のリトライ回数

    Returns:
      ScriptData: 生成された台本データ
    """
    user_prompt = f"以下のテーマについて台本を作成してください。\n\nテーマ: {theme}"

    for attempt in range(max_retries + 1):
      try:
        logger.info(
          "台本生成中... (試行 %d/%d)", attempt + 1, max_retries + 1
        )
        response = self.model.generate_content(
          user_prompt,
          generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.9,
          ),
        )
        raw_text = response.text
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
